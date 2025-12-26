"""
特征提取服务
"""
from typing import Dict, List
import uuid
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from algorithms.feature_extraction import HRVFeatureExtractor


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
            features = self.extractor.extract_all(
                file_path=file_path,
                use_existing_rpeaks=use_existing_rpeaks,
                extract_hrv=extract_hrv,
                extract_clinical=extract_clinical
            )
            
            self.tasks[task_id] = {
                "status": "completed",
                "result": features,
                "error": None
            }
        except Exception as e:
            self.tasks[task_id] = {
                "status": "failed",
                "result": None,
                "error": str(e)
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

