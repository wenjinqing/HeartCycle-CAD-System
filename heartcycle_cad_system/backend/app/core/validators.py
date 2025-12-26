"""
数据验证器
"""
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, validator, Field


class FeatureVectorValidator:
    """特征向量验证器"""
    
    @staticmethod
    def validate_features(features: List[float], 
                         expected_length: Optional[int] = None,
                         min_value: Optional[float] = None,
                         max_value: Optional[float] = None) -> np.ndarray:
        """
        验证特征向量
        
        Parameters:
        -----------
        features : List[float]
            特征向量
        expected_length : int, optional
            期望的长度
        min_value : float, optional
            最小值
        max_value : float, optional
            最大值
            
        Returns:
        --------
        np.ndarray : 验证后的特征向量
            
        Raises:
        -------
        ValueError : 如果验证失败
        """
        if not features:
            raise ValueError("特征向量不能为空")
        
        if not isinstance(features, (list, np.ndarray)):
            raise ValueError(f"特征向量必须是列表或numpy数组，当前类型: {type(features)}")
        
        arr = np.array(features, dtype=np.float64)
        
        # 检查长度
        if expected_length and len(arr) != expected_length:
            raise ValueError(
                f"特征向量长度不匹配：期望 {expected_length}，实际 {len(arr)}"
            )
        
        # 检查NaN和Inf
        if np.any(np.isnan(arr)):
            raise ValueError("特征向量包含NaN值")
        
        if np.any(np.isinf(arr)):
            raise ValueError("特征向量包含Inf值")
        
        # 检查范围
        if min_value is not None:
            if np.any(arr < min_value):
                raise ValueError(f"特征向量包含小于 {min_value} 的值")
        
        if max_value is not None:
            if np.any(arr > max_value):
                raise ValueError(f"特征向量包含大于 {max_value} 的值")
        
        return arr


class ModelInputValidator(BaseModel):
    """模型输入验证模型"""
    model_id: str = Field(..., min_length=1, description="模型ID")
    features: List[float] = Field(..., min_items=1, description="特征向量")
    
    @validator('features')
    def validate_features(cls, v):
        if not v:
            raise ValueError('特征向量不能为空')
        if len(v) < 1:
            raise ValueError('特征向量至少需要1个特征')
        # 检查是否为有效数字
        for i, val in enumerate(v):
            if not isinstance(val, (int, float)):
                raise ValueError(f'特征 {i} 必须是数字')
            if np.isnan(val) or np.isinf(val):
                raise ValueError(f'特征 {i} 包含无效值 (NaN或Inf)')
        return v


class TrainingDataValidator:
    """训练数据验证器"""
    
    @staticmethod
    def validate_training_data(X: np.ndarray, y: np.ndarray) -> tuple:
        """
        验证训练数据
        
        Parameters:
        -----------
        X : np.ndarray
            特征矩阵
        y : np.ndarray
            标签向量
            
        Returns:
        --------
        tuple : (X, y) 验证后的数据
            
        Raises:
        -------
        ValueError : 如果验证失败
        """
        # 转换为numpy数组
        X = np.asarray(X)
        y = np.asarray(y)
        
        # 检查维度
        if X.ndim != 2:
            raise ValueError(f"特征矩阵必须是2维，当前维度: {X.ndim}")
        
        if y.ndim != 1:
            raise ValueError(f"标签向量必须是1维，当前维度: {y.ndim}")
        
        # 检查样本数是否匹配
        if len(X) != len(y):
            raise ValueError(
                f"样本数不匹配：特征 {len(X)}，标签 {len(y)}"
            )
        
        # 检查是否有样本
        if len(X) == 0:
            raise ValueError("训练数据为空")
        
        # 检查是否有特征
        if X.shape[1] == 0:
            raise ValueError("特征数量为0")
        
        # 检查NaN和Inf
        if np.any(np.isnan(X)) or np.any(np.isinf(X)):
            raise ValueError("特征矩阵包含NaN或Inf值")
        
        if np.any(np.isnan(y)) or np.any(np.isinf(y)):
            raise ValueError("标签向量包含NaN或Inf值")
        
        # 检查标签类型（应该是整数）
        if not np.issubdtype(y.dtype, np.integer):
            y = y.astype(np.int32)
        
        # 检查标签值（二分类应该是0和1）
        unique_labels = np.unique(y)
        if len(unique_labels) < 2:
            raise ValueError(f"标签类别数不足：{len(unique_labels)}，至少需要2个类别")
        
        if not np.all((unique_labels == 0) | (unique_labels == 1)):
            raise ValueError("标签值必须是0或1（二分类）")
        
        return X, y


