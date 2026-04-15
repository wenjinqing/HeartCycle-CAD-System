"""
系统监控 API
"""
from fastapi import APIRouter, Depends

from ...models.response import APIResponse
from ...services.monitor_service import get_system_monitor
from ..deps import require_admin
from ...models.user import User

router = APIRouter(prefix="/monitor", tags=["系统监控"])


@router.get("/status", response_model=APIResponse, summary="获取系统状态")
async def get_system_status(
    current_user: User = Depends(require_admin)
):
    """
    获取系统整体状态

    包括CPU、内存、磁盘、网络、进程信息

    需要管理员权限
    """
    monitor = get_system_monitor()
    status = monitor.get_system_status()

    return APIResponse(
        success=True,
        message="获取成功",
        data=status
    )


@router.get("/cpu", response_model=APIResponse, summary="获取CPU信息")
async def get_cpu_info(
    current_user: User = Depends(require_admin)
):
    """
    获取CPU详细信息

    需要管理员权限
    """
    monitor = get_system_monitor()
    cpu_info = monitor.get_cpu_info()

    return APIResponse(
        success=True,
        message="获取成功",
        data=cpu_info
    )


@router.get("/memory", response_model=APIResponse, summary="获取内存信息")
async def get_memory_info(
    current_user: User = Depends(require_admin)
):
    """
    获取内存详细信息

    需要管理员权限
    """
    monitor = get_system_monitor()
    memory_info = monitor.get_memory_info()

    return APIResponse(
        success=True,
        message="获取成功",
        data=memory_info
    )


@router.get("/disk", response_model=APIResponse, summary="获取磁盘信息")
async def get_disk_info(
    current_user: User = Depends(require_admin)
):
    """
    获取磁盘详细信息

    需要管理员权限
    """
    monitor = get_system_monitor()
    disk_info = monitor.get_disk_info()

    return APIResponse(
        success=True,
        message="获取成功",
        data=disk_info
    )


@router.get("/network", response_model=APIResponse, summary="获取网络信息")
async def get_network_info(
    current_user: User = Depends(require_admin)
):
    """
    获取网络详细信息

    需要管理员权限
    """
    monitor = get_system_monitor()
    network_info = monitor.get_network_info()

    return APIResponse(
        success=True,
        message="获取成功",
        data=network_info
    )


@router.get("/process", response_model=APIResponse, summary="获取进程信息")
async def get_process_info(
    current_user: User = Depends(require_admin)
):
    """
    获取当前进程详细信息

    需要管理员权限
    """
    monitor = get_system_monitor()
    process_info = monitor.get_process_info()

    return APIResponse(
        success=True,
        message="获取成功",
        data=process_info
    )


@router.get("/history", response_model=APIResponse, summary="获取历史监控数据")
async def get_monitor_history(
    current_user: User = Depends(require_admin)
):
    """
    获取历史监控数据

    包括CPU、内存、磁盘的历史记录

    需要管理员权限
    """
    monitor = get_system_monitor()
    history = monitor.get_history()

    return APIResponse(
        success=True,
        message="获取成功",
        data=history
    )


@router.get("/alerts", response_model=APIResponse, summary="获取系统告警")
async def get_system_alerts(
    current_user: User = Depends(require_admin)
):
    """
    获取系统告警信息

    包括CPU、内存、磁盘的告警

    需要管理员权限
    """
    monitor = get_system_monitor()
    alerts = monitor.get_alerts()

    return APIResponse(
        success=True,
        message=f"找到 {len(alerts)} 个告警",
        data={
            'alerts': alerts,
            'count': len(alerts)
        }
    )


@router.get("/uptime", response_model=APIResponse, summary="获取运行时间")
async def get_uptime(
    current_user: User = Depends(require_admin)
):
    """
    获取系统运行时间

    需要管理员权限
    """
    monitor = get_system_monitor()
    uptime = monitor.get_uptime()

    return APIResponse(
        success=True,
        message="获取成功",
        data=uptime
    )
