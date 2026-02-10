"""
自定义异常类
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from app.core.error_codes import ErrorCode, ERROR_CODE_TO_STATUS


class BaseAPIException(HTTPException):
    """基础API异常"""
    def __init__(
        self, 
        status_code: int, 
        detail: str,
        error_code: Optional[ErrorCode] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code or ErrorCode.INTERNAL_SERVER_ERROR
        self.extra = extra or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "success": False,
            "error_code": self.error_code.value,
            "detail": self.detail,
            "status_code": self.status_code
        }
        if self.extra:
            result.update(self.extra)
        return result


class APIFileNotFoundError(BaseAPIException):
    """文件未找到异常（API异常，避免与Python内置FileNotFoundError冲突）"""
    def __init__(self, file_path: str):
        super().__init__(
            status_code=ERROR_CODE_TO_STATUS[ErrorCode.FILE_NOT_FOUND],
            detail=f"文件未找到: {file_path}",
            error_code=ErrorCode.FILE_NOT_FOUND,
            extra={"file_path": file_path}
        )


# 为了向后兼容，保留别名
FileNotFoundError = APIFileNotFoundError


class FeatureExtractionError(BaseAPIException):
    """特征提取错误"""
    def __init__(self, message: str, file_path: Optional[str] = None):
        super().__init__(
            status_code=ERROR_CODE_TO_STATUS[ErrorCode.FEATURE_EXTRACTION_FAILED],
            detail=f"特征提取失败: {message}",
            error_code=ErrorCode.FEATURE_EXTRACTION_FAILED,
            extra={"file_path": file_path} if file_path else {}
        )


class ModelTrainingError(BaseAPIException):
    """模型训练错误"""
    def __init__(self, message: str, task_id: Optional[str] = None):
        super().__init__(
            status_code=ERROR_CODE_TO_STATUS[ErrorCode.MODEL_TRAINING_FAILED],
            detail=f"模型训练失败: {message}",
            error_code=ErrorCode.MODEL_TRAINING_FAILED,
            extra={"task_id": task_id} if task_id else {}
        )


class InvalidParameterError(BaseAPIException):
    """参数错误"""
    def __init__(self, message: str, parameter: Optional[str] = None):
        super().__init__(
            status_code=ERROR_CODE_TO_STATUS[ErrorCode.INVALID_PARAMETER],
            detail=f"参数错误: {message}",
            error_code=ErrorCode.INVALID_PARAMETER,
            extra={"parameter": parameter} if parameter else {}
        )


