"""
限流管理 API
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

from ...models.response import APIResponse
from ...middleware.rate_limit import get_rate_limiter
from ..deps import require_admin
from ...models.user import User

router = APIRouter(prefix="/rate-limit", tags=["限流管理"])


class BlacklistRequest(BaseModel):
    """黑名单请求"""
    key: str = Field(..., description="限流键（IP或用户ID）")
    reason: Optional[str] = Field(None, description="原因")


class StatsRequest(BaseModel):
    """统计请求"""
    key: str = Field(..., description="限流键")
    window_seconds: int = Field(60, description="时间窗口（秒）")


@router.post("/blacklist/add", response_model=APIResponse, summary="添加到黑名单")
async def add_to_blacklist(
    request: BlacklistRequest,
    current_user: User = Depends(require_admin)
):
    """
    添加IP或用户到黑名单

    需要管理员权限
    """
    limiter = get_rate_limiter()
    limiter.add_to_blacklist(request.key)

    return APIResponse(
        success=True,
        message=f"已将 {request.key} 添加到黑名单",
        data={
            'key': request.key,
            'reason': request.reason
        }
    )


@router.post("/blacklist/remove", response_model=APIResponse, summary="从黑名单移除")
async def remove_from_blacklist(
    request: BlacklistRequest,
    current_user: User = Depends(require_admin)
):
    """
    从黑名单移除IP或用户

    需要管理员权限
    """
    limiter = get_rate_limiter()
    limiter.remove_from_blacklist(request.key)

    return APIResponse(
        success=True,
        message=f"已将 {request.key} 从黑名单移除",
        data={'key': request.key}
    )


@router.get("/blacklist", response_model=APIResponse, summary="获取黑名单")
async def get_blacklist(
    current_user: User = Depends(require_admin)
):
    """
    获取黑名单列表

    需要管理员权限
    """
    limiter = get_rate_limiter()

    return APIResponse(
        success=True,
        message=f"找到 {len(limiter.blacklist)} 个黑名单项",
        data={
            'blacklist': list(limiter.blacklist),
            'count': len(limiter.blacklist)
        }
    )


@router.post("/stats", response_model=APIResponse, summary="获取限流统计")
async def get_rate_limit_stats(
    request: StatsRequest,
    current_user: User = Depends(require_admin)
):
    """
    获取指定键的限流统计

    需要管理员权限
    """
    limiter = get_rate_limiter()
    stats = limiter.get_stats(request.key, request.window_seconds)

    return APIResponse(
        success=True,
        message="获取成功",
        data=stats
    )


@router.post("/clear", response_model=APIResponse, summary="清除限流统计")
async def clear_rate_limit_stats(
    key: Optional[str] = None,
    current_user: User = Depends(require_admin)
):
    """
    清除限流统计数据

    如果指定key，只清除该key的统计
    否则清除所有统计

    需要管理员权限
    """
    limiter = get_rate_limiter()
    limiter.clear_stats(key)

    message = f"已清除 {key} 的统计数据" if key else "已清除所有统计数据"

    return APIResponse(
        success=True,
        message=message
    )
