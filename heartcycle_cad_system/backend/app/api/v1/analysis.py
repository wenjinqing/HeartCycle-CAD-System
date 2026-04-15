"""
数据分析 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional

from ...services.data_analysis_service import DataAnalysisService
from ...models.response import APIResponse
from ..deps import require_doctor_or_researcher
from ...models.user import User

router = APIRouter(prefix="/analysis", tags=["数据分析"])


class DataQualityRequest(BaseModel):
    """数据质量分析请求"""
    h5_files: List[str] = Field(..., description="H5文件路径列表")
    sample_size: Optional[int] = Field(None, description="采样数量（None表示全部）")


class FeatureAnalysisRequest(BaseModel):
    """特征分析请求"""
    features_file: str = Field(..., description="特征文件路径")
    labels_file: str = Field(..., description="标签文件路径")


class AutoMLRequest(BaseModel):
    """AutoML 请求"""
    features_file: str = Field(..., description="特征文件路径")
    labels_file: str = Field(..., description="标签文件路径")
    time_budget: int = Field(default=300, ge=60, le=3600, description="时间预算（秒）")
    feature_selection: bool = Field(default=True, description="是否进行特征选择")
    test_size: float = Field(default=0.2, gt=0, lt=0.5, description="测试集比例")


class ModelComparisonRequest(BaseModel):
    """模型对比请求"""
    features_file: str = Field(..., description="特征文件路径")
    labels_file: str = Field(..., description="标签文件路径")
    model_types: List[str] = Field(..., description="模型类型列表")


@router.post("/data-quality", response_model=APIResponse, summary="数据质量分析")
async def analyze_data_quality(
    request: DataQualityRequest,
    current_user: User = Depends(require_doctor_or_researcher)
):
    """
    分析 ECG 数据质量

    评估指标:
    - 信噪比 (SNR)
    - 基线漂移
    - 工频干扰
    - 幅度范围
    - 缺失值
    - 综合质量评分

    返回:
    - 质量分布统计
    - 问题文件列表
    - 改进建议
    """
    service = DataAnalysisService()

    try:
        result = service.analyze_data_quality(
            h5_files=request.h5_files,
            sample_size=request.sample_size
        )

        return APIResponse(
            success=True,
            message="数据质量分析完成",
            data=result
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"数据质量分析失败: {str(e)}"
        )


@router.post("/features", response_model=APIResponse, summary="特征分析")
async def analyze_features(
    request: FeatureAnalysisRequest,
    current_user: User = Depends(require_doctor_or_researcher)
):
    """
    分析特征

    分析内容:
    - 特征相关性
    - 特征重要性
    - 特征分布（按类别）
    - 异常值检测
    - 特征交互

    返回:
    - 完整的特征分析报告
    - 特征工程建议
    """
    service = DataAnalysisService()

    try:
        result = service.analyze_features(
            features_file=request.features_file,
            labels_file=request.labels_file
        )

        return APIResponse(
            success=True,
            message="特征分析完成",
            data=result
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"特征分析失败: {str(e)}"
        )


@router.post("/automl", response_model=APIResponse, summary="AutoML 自动机器学习")
async def run_automl(
    request: AutoMLRequest,
    current_user: User = Depends(require_doctor_or_researcher)
):
    """
    AutoML - 自动选择最佳模型和超参数

    流程:
    1. 自动特征选择（可选）
    2. 尝试多种模型（LR, RF, SVM, KNN, GB, XGB, LGB）
    3. 超参数优化
    4. 选择最佳模型

    参数:
    - **time_budget**: 时间预算（秒），建议300-600秒
    - **feature_selection**: 是否进行特征选择
    - **test_size**: 测试集比例

    返回:
    - 最佳模型信息
    - 所有模型的性能对比
    - 选择的特征（如果启用特征选择）
    """
    service = DataAnalysisService()

    try:
        result = service.run_automl(
            features_file=request.features_file,
            labels_file=request.labels_file,
            time_budget=request.time_budget,
            feature_selection=request.feature_selection,
            test_size=request.test_size
        )

        return APIResponse(
            success=True,
            message="AutoML 完成",
            data=result
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AutoML 失败: {str(e)}"
        )


@router.post("/compare-models", response_model=APIResponse, summary="模型对比")
async def compare_models(
    request: ModelComparisonRequest,
    current_user: User = Depends(require_doctor_or_researcher)
):
    """
    对比多个模型的性能

    支持的模型:
    - lr: Logistic Regression
    - svm: Support Vector Machine
    - rf: Random Forest
    - xgb: XGBoost
    - lgb: LightGBM
    - stacking: Stacking Ensemble
    - voting: Voting Ensemble

    返回:
    - 每个模型的性能指标
    - 按 AUC 排序的结果
    """
    service = DataAnalysisService()

    try:
        result = service.compare_models(
            features_file=request.features_file,
            labels_file=request.labels_file,
            model_types=request.model_types
        )

        return APIResponse(
            success=True,
            message="模型对比完成",
            data=result
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"模型对比失败: {str(e)}"
        )


@router.get("/recommendations", response_model=APIResponse, summary="获取分析建议")
async def get_recommendations(
    current_user: User = Depends(require_doctor_or_researcher)
):
    """
    获取数据分析和模型优化建议

    返回常见的最佳实践和建议
    """
    recommendations = {
        "data_quality": [
            "定期检查数据质量，确保 SNR > 15 dB",
            "使用滤波器去除基线漂移和工频干扰",
            "处理缺失值和异常值",
            "确保数据集类别平衡"
        ],
        "feature_engineering": [
            "移除高相关性特征（相关系数 > 0.9）",
            "关注特征重要性排名前10的特征",
            "考虑创建特征交互项",
            "标准化或归一化特征"
        ],
        "model_selection": [
            "使用 AutoML 快速找到最佳模型",
            "对比多个模型，选择性能最优的",
            "使用交叉验证评估模型稳定性",
            "考虑使用集成学习提升性能"
        ],
        "hyperparameter_tuning": [
            "使用网格搜索或随机搜索优化超参数",
            "关注学习率、树深度、正则化参数",
            "使用验证集避免过拟合",
            "记录最佳超参数组合"
        ],
        "model_evaluation": [
            "不仅关注准确率，还要看 AUC、F1 等指标",
            "分析混淆矩阵，了解误分类情况",
            "使用 SHAP 解释模型预测",
            "在独立测试集上验证模型性能"
        ]
    }

    return APIResponse(
        success=True,
        message="分析建议",
        data=recommendations
    )
