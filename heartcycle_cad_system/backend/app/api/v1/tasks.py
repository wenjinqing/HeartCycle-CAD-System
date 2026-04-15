"""
任务队列管理 API
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

from ...models.response import APIResponse
from ...services.task_queue import get_task_queue, TaskStatus
from ..deps import require_admin
from ...models.user import User

router = APIRouter(prefix="/tasks", tags=["任务队列"])


class TaskStatusRequest(BaseModel):
    """任务状态请求"""
    task_id: str = Field(..., description="任务ID")


@router.get("/list", response_model=APIResponse, summary="列出任务")
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(require_admin)
):
    """
    列出任务

    可按状态筛选

    需要管理员权限
    """
    queue = get_task_queue()

    # 转换状态
    task_status = None
    if status:
        try:
            task_status = TaskStatus(status)
        except ValueError:
            pass

    tasks = queue.list_tasks(status=task_status, limit=limit)

    return APIResponse(
        success=True,
        message=f"找到 {len(tasks)} 个任务",
        data={
            'tasks': tasks,
            'count': len(tasks)
        }
    )


@router.get("/stats", response_model=APIResponse, summary="获取队列统计")
async def get_queue_stats(
    current_user: User = Depends(require_admin)
):
    """
    获取任务队列统计信息

    需要管理员权限
    """
    queue = get_task_queue()
    stats = queue.get_stats()

    return APIResponse(
        success=True,
        message="获取成功",
        data=stats
    )


@router.get("/{task_id}", response_model=APIResponse, summary="获取任务状态")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(require_admin)
):
    """
    获取指定任务的状态

    需要管理员权限
    """
    queue = get_task_queue()
    task_status = queue.get_task_status(task_id)

    if not task_status:
        return APIResponse(
            success=False,
            message="任务不存在",
            data=None
        )

    return APIResponse(
        success=True,
        message="获取成功",
        data=task_status
    )


@router.post("/{task_id}/cancel", response_model=APIResponse, summary="取消任务")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(require_admin)
):
    """
    取消指定任务

    需要管理员权限
    """
    queue = get_task_queue()
    success = queue.cancel_task(task_id)

    if success:
        return APIResponse(
            success=True,
            message="任务已取消"
        )
    else:
        return APIResponse(
            success=False,
            message="无法取消任务（任务不存在或已完成）"
        )


@router.post("/cleanup", response_model=APIResponse, summary="清理已完成任务")
async def cleanup_completed_tasks(
    keep_recent: int = 100,
    current_user: User = Depends(require_admin)
):
    """
    清理已完成的任务

    保留最近的指定数量任务

    需要管理员权限
    """
    queue = get_task_queue()
    queue.clear_completed_tasks(keep_recent=keep_recent)

    return APIResponse(
        success=True,
        message=f"已清理旧任务，保留最近 {keep_recent} 个"
    )
