"""
自定义异常类
"""
from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """基础API异常"""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class FileNotFoundError(BaseAPIException):
    """文件未找到异常"""
    def __init__(self, file_path: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文件未找到: {file_path}"
        )


class FeatureExtractionError(BaseAPIException):
    """特征提取错误"""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"特征提取失败: {message}"
        )


class ModelTrainingError(BaseAPIException):
    """模型训练错误"""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"模型训练失败: {message}"
        )


class InvalidParameterError(BaseAPIException):
    """参数错误"""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"参数错误: {message}"
        )


