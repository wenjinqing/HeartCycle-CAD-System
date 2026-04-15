"""
缓存管理 API
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

from ...models.response import APIResponse
from ...services.cache_service import get_cache_service
from ..deps import require_admin
from ...models.user import User

router = APIRouter(prefix="/cache", tags=["缓存管理"])


class CacheKeyRequest(BaseModel):
    """缓存键请求"""
    key: str = Field(..., description="缓存键")


@router.get("/stats", response_model=APIResponse, summary="获取缓存统计")
async def get_cache_stats(
    current_user: User = Depends(require_admin)
):
    """
    获取缓存统计信息

    需要管理员权限
    """
    cache = get_cache_service()
    stats = cache.get_stats()

    return APIResponse(
        success=True,
        message="获取成功",
        data=stats
    )


@router.post("/clear", response_model=APIResponse, summary="清空缓存")
async def clear_cache(
    current_user: User = Depends(require_admin)
):
    """
    清空所有缓存

    需要管理员权限
    """
    cache = get_cache_service()
    cache.clear()

    return APIResponse(
        success=True,
        message="缓存已清空"
    )


@router.post("/delete", response_model=APIResponse, summary="删除指定缓存")
async def delete_cache_key(
    request: CacheKeyRequest,
    current_user: User = Depends(require_admin)
):
    """
    删除指定的缓存键

    需要管理员权限
    """
    cache = get_cache_service()
    cache.delete(request.key)

    return APIResponse(
        success=True,
        message=f"已删除缓存键: {request.key}"
    )


@router.post("/cleanup", response_model=APIResponse, summary="清理过期缓存")
async def cleanup_expired_cache(
    current_user: User = Depends(require_admin)
):
    """
    清理过期的缓存条目

    需要管理员权限
    """
    cache = get_cache_service()
    cleaned_count = cache.cleanup_expired()

    return APIResponse(
        success=True,
        message=f"已清理 {cleaned_count} 个过期缓存",
        data={'cleaned_count': cleaned_count}
    )
