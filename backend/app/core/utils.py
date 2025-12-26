"""
工具函数
"""
import os
import json
import pickle
import joblib
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
from app.core.config import settings


def ensure_dir(file_path: str) -> str:
    """
    确保目录存在，如果不存在则创建
    
    Parameters:
    -----------
    file_path : str
        文件路径
        
    Returns:
    --------
    str : 文件路径
    """
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    return file_path


def save_json(data: Dict, file_path: str) -> None:
    """
    保存数据为JSON文件
    
    Parameters:
    -----------
    data : dict
        要保存的数据
    file_path : str
        文件路径
    """
    file_path = ensure_dir(file_path)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(file_path: str) -> Dict:
    """
    从JSON文件加载数据
    
    Parameters:
    -----------
    file_path : str
        文件路径
        
    Returns:
    --------
    dict : 加载的数据
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_pickle(obj: Any, file_path: str) -> None:
    """
    保存对象为pickle文件
    
    Parameters:
    -----------
    obj : Any
        要保存的对象
    file_path : str
        文件路径
    """
    file_path = ensure_dir(file_path)
    with open(file_path, 'wb') as f:
        pickle.dump(obj, f)


def load_pickle(file_path: str) -> Any:
    """
    从pickle文件加载对象
    
    Parameters:
    -----------
    file_path : str
        文件路径
        
    Returns:
    --------
    Any : 加载的对象
    """
    with open(file_path, 'rb') as f:
        return pickle.load(f)


def save_model(model: Any, file_path: str) -> None:
    """
    保存机器学习模型
    
    Parameters:
    -----------
    model : Any
        要保存的模型
    file_path : str
        文件路径
    """
    file_path = ensure_dir(file_path)
    joblib.dump(model, file_path)


def load_model(file_path: str) -> Any:
    """
    加载机器学习模型
    
    Parameters:
    -----------
    file_path : str
        文件路径
        
    Returns:
    --------
    Any : 加载的模型
    """
    return joblib.load(file_path)


def validate_file_path(file_path: str, check_exists: bool = True) -> bool:
    """
    验证文件路径
    
    Parameters:
    -----------
    file_path : str
        文件路径
    check_exists : bool
        是否检查文件存在
        
    Returns:
    --------
    bool : 是否有效
    """
    if not file_path or not isinstance(file_path, str):
        return False
    
    # 安全检查：防止路径遍历攻击
    if '..' in file_path or file_path.startswith('/'):
        return False
    
    if check_exists:
        return os.path.exists(file_path)
    
    return True


def validate_hdf5_file(file_path: str) -> bool:
    """
    验证HDF5文件
    
    Parameters:
    -----------
    file_path : str
        文件路径
        
    Returns:
    --------
    bool : 是否有效
    """
    if not validate_file_path(file_path, check_exists=True):
        return False
    
    if not file_path.endswith('.h5'):
        return False
    
    try:
        import h5py
        with h5py.File(file_path, 'r') as f:
            # 尝试访问基本结构
            if 'measure' not in f:
                return False
        return True
    except Exception:
        return False


def normalize_feature_vector(features: List[float], 
                            feature_names: Optional[List[str]] = None) -> np.ndarray:
    """
    标准化特征向量
    
    Parameters:
    -----------
    features : List[float]
        特征值列表
    feature_names : List[str], optional
        特征名称列表（用于验证）
        
    Returns:
    --------
    np.ndarray : 标准化后的特征向量
    """
    arr = np.array(features, dtype=np.float64)
    
    # 检查NaN和Inf
    if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
        raise ValueError("特征向量包含NaN或Inf值")
    
    return arr


def get_feature_file_path(file_id: str) -> str:
    """
    获取特征文件路径
    
    Parameters:
    -----------
    file_id : str
        文件ID或文件名
        
    Returns:
    --------
    str : 文件路径
    """
    return os.path.join(settings.FEATURES_DIR, f"{file_id}.csv")


def get_model_file_path(model_id: str) -> str:
    """
    获取模型文件路径
    
    Parameters:
    -----------
    model_id : str
        模型ID
        
    Returns:
    --------
    str : 文件路径
    """
    return os.path.join(settings.MODELS_DIR, f"{model_id}.joblib")


def format_error_message(error: Exception) -> str:
    """
    格式化错误消息
    
    Parameters:
    -----------
    error : Exception
        异常对象
        
    Returns:
    --------
    str : 格式化的错误消息
    """
    error_type = type(error).__name__
    error_msg = str(error)
    return f"{error_type}: {error_msg}"


