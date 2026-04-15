"""
WebSocket 管理器 - 实时通知服务
"""
import json
import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConnection:
    """WebSocket 连接信息"""
    websocket: WebSocket
    user_id: Optional[int] = None
    username: Optional[str] = None
    connected_at: datetime = field(default_factory=datetime.utcnow)
    subscriptions: Set[str] = field(default_factory=set)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 所有活跃连接 {connection_id: WebSocketConnection}
        self.active_connections: Dict[str, WebSocketConnection] = {}
        # 用户ID到连接ID的映射 {user_id: set(connection_ids)}
        self.user_connections: Dict[int, Set[str]] = {}
        # 频道订阅 {channel: set(connection_ids)}
        self.channel_subscriptions: Dict[str, Set[str]] = {}
        # 连接计数器
        self._connection_counter = 0

    def _generate_connection_id(self) -> str:
        """生成连接ID"""
        self._connection_counter += 1
        return f"conn_{self._connection_counter}_{datetime.utcnow().timestamp()}"

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[int] = None,
        username: Optional[str] = None
    ) -> str:
        """建立连接"""
        await websocket.accept()

        connection_id = self._generate_connection_id()
        connection = WebSocketConnection(
            websocket=websocket,
            user_id=user_id,
            username=username
        )

        self.active_connections[connection_id] = connection

        # 如果有用户ID，建立用户映射
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)

        logger.info(f"WebSocket connected: {connection_id}, user_id: {user_id}")

        # 发送连接成功消息
        await self.send_personal_message(
            connection_id,
            {
                "type": "connected",
                "connection_id": connection_id,
                "message": "连接成功"
            }
        )

        return connection_id

    async def disconnect(self, connection_id: str):
        """断开连接"""
        if connection_id not in self.active_connections:
            return

        connection = self.active_connections[connection_id]

        # 移除用户映射
        if connection.user_id and connection.user_id in self.user_connections:
            self.user_connections[connection.user_id].discard(connection_id)
            if not self.user_connections[connection.user_id]:
                del self.user_connections[connection.user_id]

        # 移除频道订阅
        for channel in connection.subscriptions:
            if channel in self.channel_subscriptions:
                self.channel_subscriptions[channel].discard(connection_id)
                if not self.channel_subscriptions[channel]:
                    del self.channel_subscriptions[channel]

        # 移除连接
        del self.active_connections[connection_id]

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def subscribe(self, connection_id: str, channel: str):
        """订阅频道"""
        if connection_id not in self.active_connections:
            return

        connection = self.active_connections[connection_id]
        connection.subscriptions.add(channel)

        if channel not in self.channel_subscriptions:
            self.channel_subscriptions[channel] = set()
        self.channel_subscriptions[channel].add(connection_id)

        logger.info(f"Connection {connection_id} subscribed to channel: {channel}")

    async def unsubscribe(self, connection_id: str, channel: str):
        """取消订阅"""
        if connection_id not in self.active_connections:
            return

        connection = self.active_connections[connection_id]
        connection.subscriptions.discard(channel)

        if channel in self.channel_subscriptions:
            self.channel_subscriptions[channel].discard(connection_id)
            if not self.channel_subscriptions[channel]:
                del self.channel_subscriptions[channel]

    async def send_personal_message(self, connection_id: str, message: dict):
        """发送个人消息"""
        if connection_id not in self.active_connections:
            return

        connection = self.active_connections[connection_id]
        try:
            await connection.websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
            await self.disconnect(connection_id)

    async def send_to_user(self, user_id: int, message: dict):
        """发送消息给指定用户的所有连接"""
        if user_id not in self.user_connections:
            return

        for connection_id in list(self.user_connections[user_id]):
            await self.send_personal_message(connection_id, message)

    async def broadcast_to_channel(self, channel: str, message: dict):
        """广播消息到频道"""
        if channel not in self.channel_subscriptions:
            return

        for connection_id in list(self.channel_subscriptions[channel]):
            await self.send_personal_message(connection_id, message)

    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        for connection_id in list(self.active_connections.keys()):
            await self.send_personal_message(connection_id, message)

    def get_connection_count(self) -> int:
        """获取连接数"""
        return len(self.active_connections)

    def get_user_connection_count(self, user_id: int) -> int:
        """获取用户连接数"""
        return len(self.user_connections.get(user_id, set()))

    def get_channel_subscriber_count(self, channel: str) -> int:
        """获取频道订阅数"""
        return len(self.channel_subscriptions.get(channel, set()))


# 全局连接管理器实例
manager = ConnectionManager()


# ==================== 通知辅助函数 ====================

async def notify_training_progress(
    task_id: str,
    user_id: Optional[int],
    progress: float,
    message: str,
    status: str = "running"
):
    """通知训练进度"""
    notification = {
        "type": "training_progress",
        "task_id": task_id,
        "progress": progress,
        "message": message,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }

    # 发送到任务频道
    await manager.broadcast_to_channel(f"task:{task_id}", notification)

    # 如果有用户ID，也发送给用户
    if user_id:
        await manager.send_to_user(user_id, notification)


async def notify_training_complete(
    task_id: str,
    user_id: Optional[int],
    result: dict
):
    """通知训练完成"""
    notification = {
        "type": "training_complete",
        "task_id": task_id,
        "result": result,
        "status": "completed",
        "timestamp": datetime.utcnow().isoformat()
    }

    await manager.broadcast_to_channel(f"task:{task_id}", notification)
    if user_id:
        await manager.send_to_user(user_id, notification)


async def notify_training_error(
    task_id: str,
    user_id: Optional[int],
    error: str
):
    """通知训练错误"""
    notification = {
        "type": "training_error",
        "task_id": task_id,
        "error": error,
        "status": "failed",
        "timestamp": datetime.utcnow().isoformat()
    }

    await manager.broadcast_to_channel(f"task:{task_id}", notification)
    if user_id:
        await manager.send_to_user(user_id, notification)


async def notify_prediction_complete(
    user_id: int,
    prediction_id: int,
    result: dict
):
    """通知预测完成"""
    notification = {
        "type": "prediction_complete",
        "prediction_id": prediction_id,
        "result": result,
        "timestamp": datetime.utcnow().isoformat()
    }

    await manager.send_to_user(user_id, notification)


async def notify_system_message(message: str, level: str = "info"):
    """系统广播消息"""
    notification = {
        "type": "system_message",
        "message": message,
        "level": level,
        "timestamp": datetime.utcnow().isoformat()
    }

    await manager.broadcast(notification)
