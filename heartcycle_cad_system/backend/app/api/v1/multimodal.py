"""
多模态融合模型 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

from ...services.multimodal_ablation_service import MultiModalAblationService
from ...services.multimodal_service import MultiModalService
from ...models.response import APIResponse
from ..deps import require_doctor_or_researcher, require_staff
from ...models.user import User

router = APIRouter(prefix="/multimodal", tags=["多模态融合"])


# ─── 请求/响应模型 ────────────────────────────────────────────────────────────

class TrainMultiModalRequest(BaseModel):
    """多模态训练请求"""
    h5_files: List[str] = Field(..., description="H5 文件路径列表（每个文件一个受试者）")
    epochs: int = Field(default=30, ge=5, le=200, description="训练轮数")
    batch_size: int = Field(default=16, ge=4, le=128, description="批次大小")
    learning_rate: float = Field(default=0.001, gt=0, description="学习率")
    test_size: float = Field(default=0.2, gt=0, lt=1, description="测试集比例")
    val_size: float = Field(default=0.2, gt=0, lt=1, description="验证集比例")
    fs: float = Field(default=500.0, gt=0, description="ECG 采样率 (Hz)")
    label_file: Optional[str] = Field(default=None, description="标签 CSV 文件路径（可选）")
    image_mode: Literal["stft_only", "dual"] = Field(
        default="dual",
        description="ECG 图像：仅 STFT 单通道，或 STFT+CWT 双通道（推荐）",
    )
    fusion_mode: Literal["concat", "interactive"] = Field(
        default="interactive",
        description="融合：concat 为原版拼接；interactive 为 HRV×CNN 交互后再分类",
    )
    use_class_weights: bool = Field(
        default=True,
        description="训练集类别不均衡时启用 balanced sample_weight",
    )
    random_state: int = Field(
        default=42,
        ge=0,
        description="数据划分与 TensorFlow 随机种子，便于复现实验",
    )


class PredictFromH5Request(BaseModel):
    """从 H5 文件预测请求"""
    model_id: str = Field(..., description="模型 ID")
    h5_file: str = Field(..., description="H5 文件路径")
    fs: float = Field(default=500.0, gt=0, description="ECG 采样率 (Hz)")


class PredictFromVectorsRequest(BaseModel):
    """从特征向量预测请求"""
    model_id: str = Field(..., description="模型 ID")
    hrv_vector: List[float] = Field(..., description="HRV 特征向量")
    ecg_signal: List[float] = Field(..., description="ECG 信号数组")
    fs: float = Field(default=500.0, gt=0, description="ECG 采样率 (Hz)")


class MultiModalAblationRequest(BaseModel):
    """多模态消融：同一 train/val/test 划分下对比多种结构，输出验证/测试 AUC 与 F1"""

    h5_files: List[str] = Field(..., description="H5 路径列表，每个文件一名受试者")
    label_file: Optional[str] = Field(default=None, description="标签 CSV：file_path, label")
    random_state: int = Field(default=42, ge=0, description="划分随机种子，保证可复现")
    test_size: float = Field(default=0.2, gt=0, lt=1)
    val_size: float = Field(default=0.2, gt=0, lt=1)
    fs: float = Field(default=500.0, gt=0, description="ECG 采样率 Hz")
    epochs: int = Field(default=25, ge=5, le=120, description="每种配置的训练轮数（消融总时间较长）")
    batch_size: int = Field(default=16, ge=4, le=128)
    learning_rate: float = Field(default=0.001, gt=0)
    configs: Optional[List[str]] = Field(
        default=None,
        description=(
            "要跑的配置 id 列表；默认全集：hrv_mlp, cnn_stft, cnn_dual, "
            "mm_stft_concat, mm_stft_interactive, mm_dual_concat, mm_dual_interactive"
        ),
    )
    include_sample_weight_ablation: bool = Field(
        default=True,
        description="在包含 mm_dual_interactive 时自动追加一行「无 sample_weight」对照",
    )
    persist: bool = Field(
        default=False,
        description="为 True 时将完整 JSON 写入 MODELS_DIR（便于留档写论文）",
    )


# ─── 训练 ─────────────────────────────────────────────────────────────────────

@router.post("/train", response_model=APIResponse, summary="训练多模态融合模型")
async def train_multimodal(
    request: TrainMultiModalRequest,
    current_user: User = Depends(require_doctor_or_researcher),
):
    """
    训练多模态融合模型。

    **数据来源**（同一批 H5 文件）：
    - 模态1：HRV 时域 / 频域 / 非线性特征 → MLP 分支
    - 模态2：ECG → STFT（可选再 + CWT 尺度图）→ 2D-CNN

    **融合**：默认可选交互式融合（HRV 与 CNN 向量 Hadamard + 拼接）；也可用原版 concat。

    **参数**：
    - `h5_files`：H5 文件路径列表（每个文件 = 一个受试者）
    - `label_file`：可选 CSV（含 `file_path` 和 `label` 列），不提供时自动生成演示标签
    """
    service = MultiModalService()
    try:
        result = service.train(
            h5_files=request.h5_files,
            epochs=request.epochs,
            batch_size=request.batch_size,
            learning_rate=request.learning_rate,
            test_size=request.test_size,
            val_size=request.val_size,
            fs=request.fs,
            label_file=request.label_file,
            image_mode=request.image_mode,
            fusion_mode=request.fusion_mode,
            use_class_weights=request.use_class_weights,
            random_state=request.random_state,
        )
        return APIResponse(
            success=True,
            message=f"多模态模型训练成功（准确率 {result['test_accuracy']:.4f}，AUC {result['test_auc']:.4f}）",
            data=result,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"训练失败: {str(e)}")


@router.post("/ablation", response_model=APIResponse, summary="多模态消融实验（固定划分）")
def run_multimodal_ablation(
    request: MultiModalAblationRequest,
    current_user: User = Depends(require_doctor_or_researcher),
):
    """
    在**同一组分层划分**下依次训练多种模型配置，返回**验证集与测试集**的 AUC、F1（不写论文也可用 `markdown_table` 粘贴到文档）。

    默认跑：仅 HRV、仅 STFT-CNN、仅双通道 CNN、多种 HRV+CNN 融合，以及（可选）sample_weight 对照。
    """
    service = MultiModalAblationService()
    try:
        data = service.run(
            h5_files=request.h5_files,
            label_file=request.label_file,
            random_state=request.random_state,
            test_size=request.test_size,
            val_size=request.val_size,
            fs=request.fs,
            epochs=request.epochs,
            batch_size=request.batch_size,
            learning_rate=request.learning_rate,
            configs=request.configs,
            include_sample_weight_ablation=request.include_sample_weight_ablation,
            persist=request.persist,
        )
        return APIResponse(
            success=True,
            message=f"消融完成，共 {len(data.get('rows', []))} 条结果",
            data=data,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"消融失败: {str(e)}")


# ─── 预测 ─────────────────────────────────────────────────────────────────────

@router.post("/predict/h5", response_model=APIResponse, summary="从 H5 文件进行多模态预测")
async def predict_from_h5(
    request: PredictFromH5Request,
    current_user: User = Depends(require_staff),
):
    """使用已训练的多模态模型，对新 H5 文件进行预测。"""
    service = MultiModalService()
    try:
        result = service.predict_from_h5(
            model_id=request.model_id,
            h5_file=request.h5_file,
            fs=request.fs,
        )
        return APIResponse(success=True, message="预测成功", data=result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


@router.post("/predict/vectors", response_model=APIResponse, summary="从特征向量进行多模态预测")
async def predict_from_vectors(
    request: PredictFromVectorsRequest,
    current_user: User = Depends(require_staff),
):
    """使用 HRV 特征向量 + ECG 信号数组进行预测（供前端监测页面调用）。"""
    service = MultiModalService()
    try:
        result = service.predict_from_vectors(
            model_id=request.model_id,
            hrv_vector=request.hrv_vector,
            ecg_signal=request.ecg_signal,
            fs=request.fs,
        )
        return APIResponse(success=True, message="预测成功", data=result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


# ─── 模型管理 ─────────────────────────────────────────────────────────────────

@router.get("/models", response_model=APIResponse, summary="获取多模态模型列表")
async def list_models(current_user: User = Depends(require_staff)):
    """列出所有已训练的多模态融合模型。"""
    service = MultiModalService()
    try:
        models = service.list_models()
        return APIResponse(
            success=True,
            message=f"找到 {len(models)} 个多模态模型",
            data=models,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}", response_model=APIResponse, summary="获取模型详情")
async def get_model_info(
    model_id: str,
    current_user: User = Depends(require_staff),
):
    """获取单个多模态模型的详细信息（含训练历史、评估指标）。"""
    service = MultiModalService()
    try:
        info = service.get_model_info(model_id)
        return APIResponse(success=True, message="获取成功", data=info)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/models/{model_id}", response_model=APIResponse, summary="删除多模态模型")
async def delete_model(
    model_id: str,
    current_user: User = Depends(require_doctor_or_researcher),
):
    """删除指定的多模态融合模型。"""
    service = MultiModalService()
    try:
        service.delete_model(model_id)
        return APIResponse(success=True, message=f"模型 {model_id} 已删除")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
