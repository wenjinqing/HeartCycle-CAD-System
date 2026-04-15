"""
API限流中间件
"""
import time
from typing import Dict, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """简单的内存限流器"""

    def __init__(self):
        # 存储格式: {key: [(timestamp, count), ...]}
        self.requests: Dict[str, list] = defaultdict(list)
        self.blacklist: set = set()

    def is_blacklisted(self, key: str) -> bool:
        """检查是否在黑名单中"""
        return key in self.blacklist

    def add_to_blacklist(self, key: str):
        """添加到黑名单"""
        self.blacklist.add(key)
        logger.warning(f"Added {key} to blacklist")

    def remove_from_blacklist(self, key: str):
        """从黑名单移除"""
        self.blacklist.discard(key)
        logger.info(f"Removed {key} from blacklist")

    def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, Optional[int]]:
        """
        检查是否允许请求

        Parameters:
        -----------
        key : str
            限流键（IP或用户ID）
        max_requests : int
            时间窗口内最大请求数
        window_seconds : int
            时间窗口（秒）

        Returns:
        --------
        (allowed, retry_after) : tuple
            allowed: 是否允许
            retry_after: 如果不允许，多少秒后重试
        """
        # 检查黑名单
        if self.is_blacklisted(key):
            return False, None

        now = time.time()
        window_start = now - window_seconds

        # 清理过期记录
        self.requests[key] = [
            (ts, count) for ts, count in self.requests[key]
            if ts > window_start
        ]

        # 计算当前窗口内的请求数
        current_requests = sum(count for _, count in self.requests[key])

        if current_requests >= max_requests:
            # 计算最早的请求何时过期
            if self.requests[key]:
                oldest_ts = self.requests[key][0][0]
                retry_after = int(oldest_ts + window_seconds - now) + 1
                return False, retry_after
            return False, window_seconds

        # 记录本次请求
        self.requests[key].append((now, 1))
        return True, None

    def get_stats(self, key: str, window_seconds: int = 60) -> Dict:
        """获取限流统计"""
        now = time.time()
        window_start = now - window_seconds

        recent_requests = [
            (ts, count) for ts, count in self.requests.get(key, [])
            if ts > window_start
        ]

        return {
            'key': key,
            'window_seconds': window_seconds,
            'request_count': sum(count for _, count in recent_requests),
            'is_blacklisted': self.is_blacklisted(key)
        }

    def clear_stats(self, key: Optional[str] = None):
        """清除统计数据"""
        if key:
            self.requests.pop(key, None)
        else:
            self.requests.clear()


# 全局限流器实例
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """API限流中间件"""

    def __init__(
        self,
        app,
        default_max_requests: int = 100,
        default_window_seconds: int = 60,
        ip_max_requests: int = 200,
        ip_window_seconds: int = 60,
        user_max_requests: int = 1000,
        user_window_seconds: int = 3600,
        enable_ip_limit: bool = True,
        enable_user_limit: bool = True
    ):
        super().__init__(app)
        self.default_max_requests = default_max_requests
        self.default_window_seconds = default_window_seconds
        self.ip_max_requests = ip_max_requests
        self.ip_window_seconds = ip_window_seconds
        self.user_max_requests = user_max_requests
        self.user_window_seconds = user_window_seconds
        self.enable_ip_limit = enable_ip_limit
        self.enable_user_limit = enable_user_limit

        # 白名单路径（不限流）
        self.whitelist_paths = {
            '/health',
            '/metrics',
            '/docs',
            '/redoc',
            '/openapi.json'
        }

    @staticmethod
    def _skip_ip_rate_limit_for_path(path: str) -> bool:
        """
        单条/集成推理接口在批量预测时会短时间产生大量请求；
        跳过 IP 级计数，仍受用户级限流（若已登录）约束。
        """
        p = path.rstrip('/')
        if p.endswith('/predict/ensemble'):
            return True
        if p.endswith('/predict/batch'):
            return True
        if p.endswith('/predict'):
            return True
        return False

    def get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        # 优先从X-Forwarded-For获取真实IP
        forwarded = request.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()

        # 从X-Real-IP获取
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip

        # 最后使用客户端地址
        if request.client:
            return request.client.host

        return 'unknown'

    def get_user_id(self, request: Request) -> Optional[str]:
        """从请求中获取用户ID"""
        # 从请求状态中获取（需要在认证中间件中设置）
        return getattr(request.state, 'user_id', None)

    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 检查是否在白名单中
        if request.url.path in self.whitelist_paths:
            return await call_next(request)

        client_ip = self.get_client_ip(request)
        user_id = self.get_user_id(request)

        # IP级别限流（推理路径见 _skip_ip_rate_limit_for_path）
        if self.enable_ip_limit and not self._skip_ip_rate_limit_for_path(request.url.path):
            ip_key = f"ip:{client_ip}"
            allowed, retry_after = rate_limiter.is_allowed(
                ip_key,
                self.ip_max_requests,
                self.ip_window_seconds
            )

            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for IP {client_ip} on {request.url.path}"
                )

                headers = {}
                if retry_after:
                    headers['Retry-After'] = str(retry_after)

                return JSONResponse(
                    status_code=429,
                    content={
                        'success': False,
                        'error_code': 'RateLimitExceeded',
                        'detail': 'IP请求频率超限，请稍后再试',
                        'retry_after': retry_after
                    },
                    headers=headers
                )

        # 用户级别限流
        if self.enable_user_limit and user_id:
            user_key = f"user:{user_id}"
            allowed, retry_after = rate_limiter.is_allowed(
                user_key,
                self.user_max_requests,
                self.user_window_seconds
            )

            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for user {user_id} on {request.url.path}"
                )

                headers = {}
                if retry_after:
                    headers['Retry-After'] = str(retry_after)

                return JSONResponse(
                    status_code=429,
                    content={
                        'success': False,
                        'error_code': 'RateLimitExceeded',
                        'detail': '用户请求频率超限，请稍后再试',
                        'retry_after': retry_after
                    },
                    headers=headers
                )

        # 添加限流信息到响应头
        response = await call_next(request)

        # 获取IP限流统计（跳过 IP 限流的路径不写入计数，此处不附加误导性头）
        if self.enable_ip_limit and not self._skip_ip_rate_limit_for_path(request.url.path):
            ip_key = f"ip:{client_ip}"
            ip_stats = rate_limiter.get_stats(ip_key, self.ip_window_seconds)
            response.headers['X-RateLimit-Limit-IP'] = str(self.ip_max_requests)
            response.headers['X-RateLimit-Remaining-IP'] = str(
                max(0, self.ip_max_requests - ip_stats['request_count'])
            )

        # 获取用户限流统计
        if self.enable_user_limit and user_id:
            user_key = f"user:{user_id}"
            user_stats = rate_limiter.get_stats(user_key, self.user_window_seconds)
            response.headers['X-RateLimit-Limit-User'] = str(self.user_max_requests)
            response.headers['X-RateLimit-Remaining-User'] = str(
                max(0, self.user_max_requests - user_stats['request_count'])
            )

        return response


def get_rate_limiter() -> RateLimiter:
    """获取全局限流器实例"""
    return rate_limiter
