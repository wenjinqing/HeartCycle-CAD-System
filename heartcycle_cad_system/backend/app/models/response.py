"""
API响应模型
"""
from pydantic import BaseModel
from typing import Optional, Any, List, Dict
from datetime import datetime


class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = "操作成功"
    timestamp: Optional[datetime] = None

    class Config:
        # 允许额外字段，这样data字段就不会被过滤
        extra = "allow"


# APIResponse是BaseResponse的别名，用于新的API
class APIResponse(BaseModel):
    """API响应模型"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None

    class Config:
        extra = "allow"


class ErrorResponse(BaseResponse):
    """错误响应模型"""
    success: bool = False
    error_code: Optional[str] = None
    detail: Optional[str] = None


class FileUploadResponse(BaseResponse):
    """文件上传响应"""
    filename: str
    file_path: str
    size: int


class FileListResponse(BaseResponse):
    """文件列表响应"""
    files: List[Dict[str, Any]]
    count: int


class TaskResponse(BaseResponse):
    """任务响应"""
    task_id: str
    status: str


class TaskStatusResponse(BaseResponse):
    """任务状态响应"""
    task_id: str
    status: str
    progress: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class FeatureExtractionResponse(TaskStatusResponse):
    """特征提取响应"""
    feature_count: Optional[int] = None
    feature_names: Optional[List[str]] = None


class ModelTrainingResponse(BaseResponse):
    """模型训练响应"""
    model_id: str
    model_type: str
    metrics: Dict[str, Any]
    cv_scores: Optional[Dict[str, List[float]]] = None


class ModelInfoResponse(BaseResponse):
    """模型信息响应"""
    model_id: str
    model_type: str
    metrics: Optional[Dict[str, Any]] = None  # 改为可选，兼容旧模型
    feature_count: int
    created_at: Optional[str] = None  # 改为可选，兼容旧模型
    feature_file: Optional[str] = None  # 训练数据文件路径（用于SHAP全局解释）
    feature_names: Optional[List[str]] = None  # 训练时特征列名（与 CSV 列对齐批量预测）


class PredictionResponse(BaseResponse):
    """预测响应"""
    prediction: int
    probability: List[float]
    confidence: float


class SHAPAnalysisResponse(BaseResponse):
    """SHAP分析响应"""
    model_id: str
    shap_values_shape: tuple
    feature_importance: Dict[str, float]
    visualization_urls: Optional[Dict[str, str]] = None

