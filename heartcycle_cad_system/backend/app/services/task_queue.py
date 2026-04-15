"""
异步任务队列服务
"""
import asyncio
import uuid
from typing import Dict, Callable, Any, Optional
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    """任务对象"""

    def __init__(
        self,
        task_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        description: str = ""
    ):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.description = description
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.progress = 0

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'description': self.description,
            'status': self.status.value,
            'result': self.result,
            'error': str(self.error) if self.error else None,
            'progress': self.progress,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class TaskQueue:
    """异步任务队列"""

    def __init__(self, max_workers: int = 5):
        """
        初始化任务队列

        Parameters:
        -----------
        max_workers : int
            最大并发工作线程数
        """
        self.max_workers = max_workers
        self.tasks: Dict[str, Task] = {}
        self.queue = asyncio.Queue()
        self.workers = []
        self.running = False

    async def start(self):
        """启动任务队列"""
        if self.running:
            return

        self.running = True
        self.workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.max_workers)
        ]
        logger.info(f"Task queue started with {self.max_workers} workers")

    async def stop(self):
        """停止任务队列"""
        self.running = False

        # 等待所有任务完成
        await self.queue.join()

        # 取消所有工作线程
        for worker in self.workers:
            worker.cancel()

        await asyncio.gather(*self.workers, return_exceptions=True)
        logger.info("Task queue stopped")

    async def _worker(self, worker_id: int):
        """工作线程"""
        logger.info(f"Worker {worker_id} started")

        while self.running:
            try:
                # 从队列获取任务
                task = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )

                # 执行任务
                await self._execute_task(task)

                # 标记任务完成
                self.queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)

        logger.info(f"Worker {worker_id} stopped")

    async def _execute_task(self, task: Task):
        """执行任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        logger.info(f"Executing task {task.task_id}: {task.description}")

        try:
            # 执行任务函数
            if asyncio.iscoroutinefunction(task.func):
                result = await task.func(*task.args, **task.kwargs)
            else:
                result = task.func(*task.args, **task.kwargs)

            task.result = result
            task.status = TaskStatus.COMPLETED
            task.progress = 100

            logger.info(f"Task {task.task_id} completed successfully")

        except Exception as e:
            task.error = e
            task.status = TaskStatus.FAILED

            logger.error(f"Task {task.task_id} failed: {e}", exc_info=True)

        finally:
            task.completed_at = datetime.now()

    def submit(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        description: str = "",
        task_id: Optional[str] = None
    ) -> str:
        """
        提交任务到队列

        Parameters:
        -----------
        func : Callable
            要执行的函数
        args : tuple
            函数参数
        kwargs : dict
            函数关键字参数
        description : str
            任务描述
        task_id : Optional[str]
            任务ID（可选，不提供则自动生成）

        Returns:
        --------
        str : 任务ID
        """
        if task_id is None:
            task_id = str(uuid.uuid4())

        task = Task(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            description=description
        )

        self.tasks[task_id] = task

        # 添加到队列（非阻塞）
        asyncio.create_task(self.queue.put(task))

        logger.info(f"Task {task_id} submitted: {description}")

        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        task = self.get_task(task_id)
        return task.to_dict() if task else None

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.get_task(task_id)
        if not task:
            return False

        if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            task.status = TaskStatus.CANCELLED
            logger.info(f"Task {task_id} cancelled")
            return True

        return False

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> list:
        """
        列出任务

        Parameters:
        -----------
        status : Optional[TaskStatus]
            按状态筛选
        limit : int
            返回数量限制

        Returns:
        --------
        list : 任务列表
        """
        tasks = list(self.tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        # 按创建时间倒序排序
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        return [t.to_dict() for t in tasks[:limit]]

    def clear_completed_tasks(self, keep_recent: int = 100):
        """
        清理已完成的任务

        Parameters:
        -----------
        keep_recent : int
            保留最近的任务数量
        """
        completed_tasks = [
            t for t in self.tasks.values()
            if t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        ]

        # 按完成时间排序
        completed_tasks.sort(key=lambda t: t.completed_at or t.created_at, reverse=True)

        # 删除旧任务
        for task in completed_tasks[keep_recent:]:
            del self.tasks[task.task_id]

        logger.info(f"Cleared {len(completed_tasks) - keep_recent} old tasks")

    def get_stats(self) -> Dict:
        """获取队列统计"""
        stats = {
            'total_tasks': len(self.tasks),
            'pending': 0,
            'running': 0,
            'completed': 0,
            'failed': 0,
            'cancelled': 0,
            'queue_size': self.queue.qsize(),
            'workers': self.max_workers,
            'running': self.running
        }

        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING:
                stats['pending'] += 1
            elif task.status == TaskStatus.RUNNING:
                stats['running'] += 1
            elif task.status == TaskStatus.COMPLETED:
                stats['completed'] += 1
            elif task.status == TaskStatus.FAILED:
                stats['failed'] += 1
            elif task.status == TaskStatus.CANCELLED:
                stats['cancelled'] += 1

        return stats


# 全局任务队列实例
task_queue = TaskQueue(max_workers=5)


def get_task_queue() -> TaskQueue:
    """获取全局任务队列实例"""
    return task_queue


# 启动任务队列的辅助函数
async def start_task_queue():
    """启动任务队列"""
    await task_queue.start()


async def stop_task_queue():
    """停止任务队列"""
    await task_queue.stop()
