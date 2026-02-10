"""
模型服务协调器 - 整合各个专注的服务，保持向后兼容
"""
from typing import Dict, List, Optional, Callable
from app.services.task_management_service import TaskManagementService
from app.services.model_prediction_service import ModelPredictionService
from app.services.model_storage_service import ModelStorageService
from app.core.logger import logger


class ModelServiceFacade:
    """
    模型服务门面类
    整合TaskManagementService、ModelPredictionService和ModelStorageService
    保持与原有ModelService的接口兼容
    """

    def __init__(self):
        """初始化服务协调器"""
        self.task_service = TaskManagementService()
        self.prediction_service = ModelPredictionService()
        self.storage_service = ModelStorageService()

        # 保持向后兼容的属性
        self.models = self.storage_service.models
        self.task_storage = self.task_service.task_storage
        if hasattr(self.task_service, 'training_tasks'):
            self.training_tasks = self.task_service.training_tasks
        self._lock = self.task_service._lock

    # ==================== 任务管理方法 ====================

    def _create_training_task(self, task_id: str, initial_data: Dict) -> None:
        """线程安全地创建训练任务"""
        return self.task_service.create_task(task_id, initial_data)

    def _update_training_task(self, task_id: str, updates: Dict) -> None:
        """线程安全地更新训练任务状态"""
        return self.task_service.update_task(task_id, updates)

    def _get_training_task(self, task_id: str) -> Optional[Dict]:
        """线程安全地获取训练任务"""
        return self.task_service.get_task(task_id)

    def _get_training_tasks_count(self) -> int:
        """线程安全地获取训练任务数量"""
        return self.task_service.get_tasks_count()

    def get_h5_training_status(self, task_id: str) -> Dict:
        """
        获取H5训练任务状态

        Parameters:
        -----------
        task_id : str
            任务ID

        Returns:
        --------
        dict : 任务状态
        """
        task = self.task_service.get_task(task_id)
        if task:
            return task
        else:
            logger.warning(f"任务 {task_id} 不存在")
            return {"status": "not_found", "error": f"任务 {task_id} 不存在"}

    # ==================== 预测方法 ====================

    def predict(self, model_id: str, features: List[float]) -> Dict:
        """
        预测

        Parameters:
        -----------
        model_id : str
            模型ID
        features : List[float]
            特征向量

        Returns:
        --------
        dict : 预测结果
        """
        return self.prediction_service.predict(model_id, features)

    def batch_predict(self, model_id: str, features_list: List[List[float]]) -> List[Dict]:
        """
        批量预测

        Parameters:
        -----------
        model_id : str
            模型ID
        features_list : List[List[float]]
            特征向量列表

        Returns:
        --------
        List[Dict] : 预测结果列表
        """
        return self.prediction_service.batch_predict(model_id, features_list)

    # ==================== 存储管理方法 ====================

    def list_models(self) -> List[Dict]:
        """
        列出所有模型

        Returns:
        --------
        List[Dict] : 模型列表
        """
        return self.storage_service.list_models()

    def get_model_info(self, model_id: str) -> Dict:
        """
        获取模型信息

        Parameters:
        -----------
        model_id : str
            模型ID

        Returns:
        --------
        Dict : 模型信息
        """
        return self.storage_service.get_model_info(model_id)

    def delete_model(self, model_id: str) -> Dict:
        """
        删除模型

        Parameters:
        -----------
        model_id : str
            模型ID

        Returns:
        --------
        Dict : 删除结果
        """
        return self.storage_service.delete_model(model_id)

    def model_exists(self, model_id: str) -> bool:
        """
        检查模型是否存在

        Parameters:
        -----------
        model_id : str
            模型ID

        Returns:
        --------
        bool : 模型是否存在
        """
        return self.storage_service.model_exists(model_id)


# 为了保持向后兼容，创建别名
ModelService = ModelServiceFacade
