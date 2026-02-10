"""
任务管理服务 - 负责训练任务的创建、更新和查询
"""
from datetime import datetime
from threading import Lock
from typing import Dict, Optional
from app.core.logger import logger

# 导入任务存储
try:
    from app.utils.mysql_task_storage import get_mysql_task_storage
    TASK_STORAGE_TYPE = "mysql"
except Exception as e:
    logger.warning(f"MySQL任务存储不可用: {e}，将使用内存存储")
    TASK_STORAGE_TYPE = "memory"


class TaskManagementService:
    """任务管理服务"""

    def __init__(self):
        """初始化任务管理服务"""
        self._lock = Lock()

        # 使用MySQL存储任务（如果可用），否则使用内存存储
        if TASK_STORAGE_TYPE == "mysql":
            try:
                self.task_storage = get_mysql_task_storage()
                logger.info("使用MySQL存储训练任务")
            except Exception as e:
                logger.warning(f"MySQL存储初始化失败: {e}，使用内存存储")
                self.training_tasks = {}
                self.task_storage = None
        else:
            self.training_tasks = {}
            self.task_storage = None

    def create_task(self, task_id: str, initial_data: Dict) -> None:
        """
        线程安全地创建训练任务

        Parameters:
        -----------
        task_id : str
            任务ID
        initial_data : Dict
            初始任务数据
        """
        if self.task_storage:
            success = self.task_storage.create_task(task_id, initial_data)
            if not success:
                logger.error(f"创建任务 {task_id} 失败，回退到内存存储")
                with self._lock:
                    if not hasattr(self, 'training_tasks'):
                        self.training_tasks = {}
                    self.training_tasks[task_id] = initial_data
        else:
            with self._lock:
                if not hasattr(self, 'training_tasks'):
                    self.training_tasks = {}
                self.training_tasks[task_id] = initial_data

    def update_task(self, task_id: str, updates: Dict) -> None:
        """
        线程安全地更新训练任务状态

        Parameters:
        -----------
        task_id : str
            任务ID
        updates : Dict
            更新的数据
        """
        if self.task_storage:
            self.task_storage.update_task(task_id, updates)
        else:
            with self._lock:
                if task_id in self.training_tasks:
                    self.training_tasks[task_id].update(updates)

    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        线程安全地获取训练任务

        Parameters:
        -----------
        task_id : str
            任务ID

        Returns:
        --------
        Optional[Dict] : 任务数据，如果不存在返回None
        """
        if self.task_storage:
            return self.task_storage.get_task(task_id)
        else:
            with self._lock:
                return self.training_tasks.get(task_id)

    def get_tasks_count(self) -> int:
        """
        线程安全地获取训练任务数量

        Returns:
        --------
        int : 任务数量
        """
        if self.task_storage:
            return 0  # MySQL存储不需要计数
        else:
            with self._lock:
                return len(self.training_tasks) if hasattr(self, 'training_tasks') else 0

    def task_exists(self, task_id: str) -> bool:
        """
        检查任务是否存在

        Parameters:
        -----------
        task_id : str
            任务ID

        Returns:
        --------
        bool : 任务是否存在
        """
        return self.get_task(task_id) is not None
