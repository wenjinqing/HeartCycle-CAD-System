"""
深度学习模型 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Optional
import numpy as np

from ...services.deep_learning_service import DeepLearningService
from ...models.response import APIResponse
from ..deps import require_doctor_or_researcher, require_staff
from ...models.user import User

router = APIRouter(prefix="/deep-learning", tags=["深度学习"])


class TrainDeepModelRequest(BaseModel):
    """训练深度学习模型请求"""
    h5_files: List[str] = Field(..., description="H5文件路径列表")
    model_type: str = Field(default="cnn", description="模型类型: cnn/lstm/gru/cnn_lstm")
    signal_length: int = Field(default=5000, description="信号长度")
    epochs: int = Field(default=50, ge=1, le=200, description="训练轮数")
    batch_size: int = Field(default=32, ge=8, le=256, description="批次大小")
    learning_rate: float = Field(default=0.001, gt=0, description="学习率")
    test_size: float = Field(default=0.2, gt=0, lt=1, description="测试集比例")
    validation_split: float = Field(default=0.2, gt=0, lt=1, description="验证集比例")
    use_calibration: bool = Field(default=True, description="是否使用模型校准")
    calibration_method: str = Field(default="platt", description="校准方法: platt/isotonic")


class PredictDeepModelRequest(BaseModel):
    """深度学习模型预测请求"""
    model_id: str = Field(..., description="模型ID")
    ecg_signal: List[float] = Field(..., description="ECG信号数据")


@router.post("/train", response_model=APIResponse, summary="训练深度学习模型")
async def train_deep_model(
    request: TrainDeepModelRequest,
    current_user: User = Depends(require_doctor_or_researcher)
):
    """
    训练深度学习模型（需要医生或研究人员权限）

    支持的模型类型:
    - **cnn**: 1D-CNN 模型
    - **lstm**: LSTM 模型
    - **gru**: GRU 模型
    - **cnn_lstm**: CNN-LSTM 混合模型

    校准方法:
    - **platt**: Platt Scaling (逻辑回归)
    - **isotonic**: Isotonic Regression
    """
    service = DeepLearningService()

    try:
        result = service.train_deep_model(
            h5_files=request.h5_files,
            model_type=request.model_type,
            signal_length=request.signal_length,
            epochs=request.epochs,
            batch_size=request.batch_size,
            learning_rate=request.learning_rate,
            test_size=request.test_size,
            validation_split=request.validation_split,
            use_calibration=request.use_calibration,
            calibration_method=request.calibration_method
        )

        return APIResponse(
            success=True,
            message="深度学习模型训练成功",
            data=result
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"模型训练失败: {str(e)}"
        )


@router.post("/predict", response_model=APIResponse, summary="深度学习模型预测")
async def predict_with_deep_model(
    request: PredictDeepModelRequest,
    current_user: User = Depends(require_staff)
):
    """
    使用深度学习模型进行预测

    输入:
    - **model_id**: 模型ID
    - **ecg_signal**: ECG信号数据（一维数组）

    输出:
    - **predictions**: 预测类别 (0: 健康, 1: 冠心病)
    - **probabilities**: 预测概率
    - **calibrated**: 是否使用了校准
    """
    service = DeepLearningService()

    try:
        ecg_signal = np.array(request.ecg_signal)
        result = service.predict_with_deep_model(
            model_id=request.model_id,
            ecg_signal=ecg_signal
        )

        return APIResponse(
            success=True,
            message="预测成功",
            data=result
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"预测失败: {str(e)}"
        )


@router.get("/models", response_model=APIResponse, summary="获取深度学习模型列表")
async def list_deep_models(
    current_user: User = Depends(require_staff)
):
    """
    获取所有深度学习模型列表

    返回模型的基本信息:
    - model_id
    - model_type
    - test_accuracy
    - test_auc
    - created_at
    - use_calibration
    """
    service = DeepLearningService()

    try:
        models = service.list_deep_models()

        return APIResponse(
            success=True,
            message=f"找到 {len(models)} 个深度学习模型",
            data=models
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取模型列表失败: {str(e)}"
        )


@router.get("/models/{model_id}", response_model=APIResponse, summary="获取深度学习模型详情（元数据）")
async def get_deep_model(
    model_id: str,
    current_user: User = Depends(require_staff),
):
    service = DeepLearningService()
    try:
        meta = service.get_deep_model_metadata(model_id)
        return APIResponse(success=True, message="获取成功", data=meta)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/models/{model_id}", response_model=APIResponse, summary="删除深度学习模型")
async def delete_deep_model(
    model_id: str,
    current_user: User = Depends(require_doctor_or_researcher)
):
    """
    删除深度学习模型（需要医生或研究人员权限）
    """
    service = DeepLearningService()

    try:
        success = service.delete_deep_model(model_id)

        if success:
            return APIResponse(
                success=True,
                message=f"模型 {model_id} 已删除"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="删除模型失败"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除模型失败: {str(e)}"
        )


@router.get("/model-types", response_model=APIResponse, summary="获取支持的模型类型")
async def get_model_types(current_user: User = Depends(require_staff)):
    """
    获取支持的深度学习模型类型

    返回每种模型的说明
    """
    model_types = {
        "cnn": {
            "name": "1D-CNN",
            "description": "一维卷积神经网络，适合提取ECG信号的局部特征",
            "advantages": ["训练速度快", "参数量少", "适合短时序列"],
            "recommended_for": "快速原型和基线模型"
        },
        "lstm": {
            "name": "LSTM",
            "description": "长短期记忆网络，适合捕捉ECG信号的长期依赖关系",
            "advantages": ["捕捉长期依赖", "处理变长序列", "记忆能力强"],
            "recommended_for": "复杂时序模式识别"
        },
        "gru": {
            "name": "GRU",
            "description": "门控循环单元，LSTM的简化版本",
            "advantages": ["训练速度比LSTM快", "参数量少", "性能接近LSTM"],
            "recommended_for": "平衡性能和速度"
        },
        "cnn_lstm": {
            "name": "CNN-LSTM",
            "description": "CNN和LSTM的混合模型，结合空间和时序特征",
            "advantages": ["提取多层次特征", "性能最优", "鲁棒性强"],
            "recommended_for": "追求最佳性能"
        }
    }

    return APIResponse(
        success=True,
        message="支持的模型类型",
        data=model_types
    )
