"""
请求日志中间件
"""
import time
from collections import defaultdict
from datetime import datetime
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import logger


class PerformanceMetrics:
    """性能指标收集器"""

    def __init__(self):
        self.request_count = defaultdict(int)
        self.request_duration = defaultdict(list)
        self.error_count = defaultdict(int)
        self.last_reset = datetime.now()

    def record_request(self, method: str, path: str, duration: float, status_code: int):
        """记录请求指标"""
        endpoint = f"{method} {path}"
        self.request_count[endpoint] += 1
        self.request_duration[endpoint].append(duration)

        if status_code >= 400:
            self.error_count[endpoint] += 1

    def get_metrics(self):
        """获取性能指标"""
        metrics = {}
        for endpoint, durations in self.request_duration.items():
            if durations:
                metrics[endpoint] = {
                    "count": self.request_count[endpoint],
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "error_count": self.error_count[endpoint],
                    "error_rate": self.error_count[endpoint] / self.request_count[endpoint]
                }
        return {
            "metrics": metrics,
            "since": self.last_reset.isoformat()
        }

    def reset(self):
        """重置指标"""
        self.request_count.clear()
        self.request_duration.clear()
        self.error_count.clear()
        self.last_reset = datetime.now()


# 全局性能指标实例
performance_metrics = PerformanceMetrics()


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # 记录请求信息
        logger.info(
            f"Request: {request.method} {request.url.path} - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)

            # 计算处理时间
            process_time = time.time() - start_time

            # 记录性能指标
            performance_metrics.record_request(
                request.method,
                request.url.path,
                process_time,
                response.status_code
            )

            # 记录响应信息
            logger.info(
                f"Response: {request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.3f}s"
            )

            # 添加处理时间到响应头
            response.headers["X-Process-Time"] = str(process_time)

            # 性能警告
            if process_time > 5.0:
                logger.warning(
                    f"Slow request: {request.method} {request.url.path} - "
                    f"Time: {process_time:.3f}s"
                )

            return response

        except Exception as e:
            process_time = time.time() - start_time

            # 记录错误指标
            performance_metrics.record_request(
                request.method,
                request.url.path,
                process_time,
                500
            )

            logger.error(
                f"Error: {request.method} {request.url.path} - "
                f"Exception: {str(e)} - Time: {process_time:.3f}s"
            )
            raise

