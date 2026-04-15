"""
WebSocket API 路由
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional

from ...services.websocket_manager import manager
from ...services.auth_service import AuthService
from ...db.base import get_db
from sqlalchemy.orm import Session

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket 连接端点

    连接方式: ws://localhost:8000/ws?token=<access_token>

    消息格式:
    - 订阅频道: {"action": "subscribe", "channel": "task:xxx"}
    - 取消订阅: {"action": "unsubscribe", "channel": "task:xxx"}
    - 心跳: {"action": "ping"}
    """
    user_id = None
    username = None

    # 如果提供了 token，验证用户
    if token:
        try:
            db = next(get_db())
            auth_service = AuthService(db)
            payload = auth_service.decode_token(token)
            if payload.type == "access":
                user_id = int(payload.sub)
                username = payload.username
        except Exception:
            pass  # 允许匿名连接

    # 建立连接
    connection_id = await manager.connect(
        websocket,
        user_id=user_id,
        username=username
    )

    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action")

                if action == "subscribe":
                    channel = message.get("channel")
                    if channel:
                        await manager.subscribe(connection_id, channel)
                        await manager.send_personal_message(
                            connection_id,
                            {
                                "type": "subscribed",
                                "channel": channel,
                                "message": f"已订阅频道: {channel}"
                            }
                        )

                elif action == "unsubscribe":
                    channel = message.get("channel")
                    if channel:
                        await manager.unsubscribe(connection_id, channel)
                        await manager.send_personal_message(
                            connection_id,
                            {
                                "type": "unsubscribed",
                                "channel": channel,
                                "message": f"已取消订阅: {channel}"
                            }
                        )

                elif action == "ping":
                    await manager.send_personal_message(
                        connection_id,
                        {"type": "pong", "message": "pong"}
                    )

                else:
                    await manager.send_personal_message(
                        connection_id,
                        {
                            "type": "error",
                            "message": f"未知操作: {action}"
                        }
                    )

            except json.JSONDecodeError:
                await manager.send_personal_message(
                    connection_id,
                    {
                        "type": "error",
                        "message": "无效的 JSON 格式"
                    }
                )

    except WebSocketDisconnect:
        await manager.disconnect(connection_id)


@router.get("/ws/stats", summary="获取 WebSocket 统计信息")
async def get_websocket_stats():
    """获取 WebSocket 连接统计"""
    return {
        "total_connections": manager.get_connection_count(),
        "channels": {
            channel: manager.get_channel_subscriber_count(channel)
            for channel in manager.channel_subscriptions.keys()
        }
    }
