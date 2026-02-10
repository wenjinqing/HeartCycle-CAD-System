"""
特征提取服务
"""
import logging
import os
import sys
import uuid
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from algorithms.feature_extraction import HRVFeatureExtractor
from app.core.config import settings
from app.core.utils import normalize_file_path

logger = logging.getLogger(__name__)


class FeatureService:
    """特征提取服务类"""
    
    def __init__(self):
        self.tasks = {}  # 任务状态存储（实际应用中应使用Redis或数据库）
        self.extractor = HRVFeatureExtractor()
    
    def start_extraction(self, file_path: str, use_existing_rpeaks: bool = True,
                        extract_hrv: bool = True, extract_clinical: bool = True) -> str:
        """
        启动特征提取任务
        
        Parameters:
        -----------
        file_path : str
            HDF5文件路径
        use_existing_rpeaks : bool
            是否使用已有R波标注
        extract_hrv : bool
            是否提取HRV特征
        extract_clinical : bool
            是否提取临床特征
            
        Returns:
        --------
        task_id : str
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        # TODO: 实际应使用Celery异步任务
        # 这里先同步执行（后续改为异步）
        try:
            logger.info(f"开始特征提取任务 {task_id}, 文件: {file_path}")
            logger.info(f"提取参数: use_existing_rpeaks={use_existing_rpeaks}, extract_hrv={extract_hrv}, extract_clinical={extract_clinical}")
            
            # 规范化文件路径
            file_path = normalize_file_path(file_path, is_directory=False)
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            logger.info(f"使用文件路径: {file_path}")
            
            features = self.extractor.extract_all(
                file_path=file_path,
                use_existing_rpeaks=use_existing_rpeaks,
                extract_hrv=extract_hrv,
                extract_clinical=extract_clinical,
                subject_metadata=None  # Monitor页面不提供元数据
            )
            
            logger.info(f"特征提取成功，提取到 {len(features)} 个特征")
            logger.debug(f"特征列表: {list(features.keys())}")
            
            # 检查是否有非零特征
            non_zero_features = {k: v for k, v in features.items() if v != 0}
            if len(non_zero_features) == 0:
                logger.warning("所有特征值都为0，可能存在问题")
            
            self.tasks[task_id] = {
                "status": "completed",
                "result": features,
                "error": None
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"特征提取任务 {task_id} 失败: {error_msg}")
            self.tasks[task_id] = {
                "status": "failed",
                "result": None,
                "error": error_msg
            }
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict:
        """
        获取任务状态
        
        Parameters:
        -----------
        task_id : str
            任务ID
            
        Returns:
        --------
        dict : 任务状态
        """
        if task_id not in self.tasks:
            return {"status": "not_found"}
        
        return self.tasks[task_id]
    
    def list_features(self) -> List[Dict]:
        """
        列出已提取的特征
        
        Returns:
        --------
        list : 特征列表
        """
        # TODO: 从数据库或文件系统读取
        return []

