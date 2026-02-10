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


def handle_api_error(error: Exception, default_message: str = "操作失败"):
    """
    统一处理API错误，转换为HTTPException
    
    Parameters:
    -----------
    error : Exception
        异常对象
    default_message : str
        默认错误消息
        
    Returns:
    --------
    HTTPException : HTTP异常对象
    """
    from fastapi import HTTPException
    from app.core.logger import logger
    
    # 如果已经是HTTPException，直接返回
    if isinstance(error, HTTPException):
        return error
    
    # 记录错误日志
    logger.error(f"{default_message}: {str(error)}", exc_info=True)
    
    # 根据错误类型返回适当的HTTP状态码
    error_msg = str(error)
    if isinstance(error, FileNotFoundError):
        return HTTPException(status_code=404, detail=f"文件未找到: {error_msg}")
    elif isinstance(error, ValueError):
        return HTTPException(status_code=400, detail=f"参数错误: {error_msg}")
    elif isinstance(error, PermissionError):
        return HTTPException(status_code=403, detail=f"权限不足: {error_msg}")
    else:
        return HTTPException(status_code=500, detail=f"{default_message}: {error_msg}")


def normalize_file_path(file_path: str, is_directory: bool = False) -> str:
    """
    规范化文件或目录路径
    
    处理相对路径、绝对路径，支持以下路径格式：
    1. 绝对路径（直接使用）
    2. 相对于项目根目录的路径（如 data/features/train_features.csv）
    3. 上传目录中的文件（data/raw/xxx.csv）
    4. 包含 .. 的相对路径（规范化处理）
    
    Parameters:
    -----------
    file_path : str
        文件或目录路径
    is_directory : bool
        是否为目录路径（默认为False，即文件路径）
        
    Returns:
    --------
    str : 规范化的绝对路径
    """
    from app.core.logger import logger
    
    if not file_path:
        raise ValueError("路径不能为空")
    
    # 规范化路径（移除 .. 和 .，转换为标准路径）
    normalized = os.path.normpath(file_path)
    
    # 如果已经是绝对路径且存在，直接返回
    if os.path.isabs(normalized):
        if (is_directory and os.path.isdir(normalized)) or (not is_directory and os.path.isfile(normalized)):
            return normalized
        elif os.path.exists(normalized):
            return normalized
    
    # 提取文件名或目录名（用于在多个目录中查找）
    basename = os.path.basename(normalized) if not is_directory else normalized
    
    # 尝试多个可能的路径
    search_paths = []
    
    # 1. 如果是绝对路径但不存在，尝试移除多余的部分
    if os.path.isabs(normalized):
        search_paths.append(normalized)
        if not is_directory:
            search_paths.append(basename)
    
    # 2. 相对于项目根目录
    base_path = os.path.join(settings.BASE_DIR, normalized)
    search_paths.append(base_path)
    
    # 3. 如果是相对路径，尝试直接使用
    if not os.path.isabs(normalized):
        search_paths.append(normalized)
    
    # 4. 在上传目录中查找（只使用文件名）
    if not is_directory:
        upload_path = os.path.join(settings.UPLOAD_DIR, basename)
        search_paths.append(upload_path)
        
        # 5. 在特征目录中查找（只使用文件名）
        features_path = os.path.join(settings.FEATURES_DIR, basename)
        search_paths.append(features_path)
    
    # 6. 尝试从当前工作目录解析
    if os.path.exists(normalized):
        search_paths.append(os.path.abspath(normalized))
    
    # 遍历所有可能的路径，找到存在的文件或目录
    for path in search_paths:
        abs_path = os.path.abspath(path) if not os.path.isabs(path) else path
        if is_directory:
            if os.path.exists(abs_path) and os.path.isdir(abs_path):
                logger.debug(f"找到目录: {abs_path} (原始路径: {file_path})")
                return abs_path
        else:
            if os.path.exists(abs_path) and os.path.isfile(abs_path):
                logger.debug(f"找到文件: {abs_path} (原始路径: {file_path})")
                return abs_path
    
    # 如果所有尝试都失败，返回规范化后的绝对路径（让后续代码抛出错误）
    final_path = os.path.abspath(normalized) if not os.path.isabs(normalized) else normalized
    logger.warning(f"无法找到{'目录' if is_directory else '文件'}: {file_path} (规范化后: {final_path})")
    return final_path


