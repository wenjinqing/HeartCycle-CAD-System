"""
FastAPI主应用入口
"""
import logging
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.core.logger import logger, log_with_context
from app.core.exceptions import BaseAPIException
from app.middleware.logging import LoggingMiddleware, performance_metrics
from app.middleware.rate_limit import RateLimitMiddleware
from app.api.v1 import data, features, selection, models, shap, h5_convert, auth, websocket, deep_learning, analysis, patients, reports, model_versions, rate_limit, cache, monitor, tasks, experiment, h5_visualize, multimodal
from app.db.base import (
    engine,
    Base,
    migrate_patients_extended_columns,
    migrate_patients_drop_id_card_column,
)
from app.services.task_queue import start_task_queue, stop_task_queue

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="HeartCycle 冠心病风险预测系统 API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 启动日志
logger.info(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")

# 创建数据库表，并补充患者表扩展列（与 ORM 一致；可重复执行）
try:
    Base.metadata.create_all(bind=engine)
    migrate_patients_extended_columns()
    migrate_patients_drop_id_card_column()
    logger.info("数据库表创建/检查完成")
except Exception as e:
    logger.warning(f"数据库表创建失败: {e}")

# 添加请求日志中间件
app.add_middleware(LoggingMiddleware)

# 添加限流中间件
app.add_middleware(
    RateLimitMiddleware,
    ip_max_requests=200,  # IP每分钟最多200个请求
    ip_window_seconds=60,
    user_max_requests=1000,  # 用户每小时最多1000个请求
    user_window_seconds=3600,
    enable_ip_limit=True,
    enable_user_limit=True
)

# CORS中间件
# 开发环境下使用更宽松的CORS配置
cors_origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:8081",
    "http://localhost:8082",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8081",
    "http://127.0.0.1:8082",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
] if settings.DEBUG else settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# 全局异常处理
@app.exception_handler(BaseAPIException)
async def api_exception_handler(request: Request, exc: BaseAPIException):
    """API异常处理"""
    log_with_context(
        logger,
        logging.ERROR,
        f"API Exception: {exc.detail}",
        error_code=exc.error_code.value,
        status_code=exc.status_code,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code.value,
            "detail": exc.detail,
            "timestamp": datetime.now().isoformat(),
            **exc.extra
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP异常处理"""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": "HTTPException",
            "detail": exc.detail
        }
    )


def _safe_validation_body_preview(body) -> Optional[str]:
    """RequestValidationError.body 可能是 bytes 或不可 JSON 序列化的对象（如 multipart 解析中间态），仅用于日志/调试。"""
    if body is None:
        return None
    if isinstance(body, (bytes, bytearray)):
        return f"<bytes len={len(body)}>"
    if isinstance(body, str):
        return body[:2000] + ("..." if len(body) > 2000 else "")
    return f"<{type(body).__name__}>"


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理（响应中不得包含 exc.body 原始对象，否则 multipart 时无法 JSON 序列化）"""
    logger.error(f"Validation Error: {exc.errors()}")
    content = {
        "success": False,
        "error_code": "ValidationError",
        "detail": exc.errors(),
    }
    if settings.DEBUG:
        content["body_preview"] = _safe_validation_body_preview(exc.body)
    return JSONResponse(status_code=422, content=content)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(f"Unhandled Exception: {type(exc).__name__} - {str(exc)}", exc_info=True)
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "InternalServerError",
            "detail": "服务器内部错误" if not settings.DEBUG else str(exc),
            "message": str(exc) if settings.DEBUG else None,
            "traceback": traceback.format_exc() if settings.DEBUG else None
        }
    )

# 注册路由
app.include_router(data.router, prefix=settings.API_V1_PREFIX, tags=["数据管理"])
app.include_router(features.router, prefix=settings.API_V1_PREFIX, tags=["特征提取"])
app.include_router(selection.router, prefix=settings.API_V1_PREFIX, tags=["特征选择"])
app.include_router(models.router, prefix=settings.API_V1_PREFIX, tags=["模型训练"])
app.include_router(shap.router, prefix=settings.API_V1_PREFIX, tags=["可解释性"])
app.include_router(h5_convert.router, prefix=settings.API_V1_PREFIX + "/h5", tags=["H5格式转换"])
app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["认证"])
app.include_router(websocket.router, tags=["WebSocket"])
app.include_router(deep_learning.router, prefix=settings.API_V1_PREFIX, tags=["深度学习"])
app.include_router(analysis.router, prefix=settings.API_V1_PREFIX, tags=["数据分析"])
app.include_router(patients.router, prefix=settings.API_V1_PREFIX, tags=["患者管理"])
app.include_router(reports.router, prefix=settings.API_V1_PREFIX, tags=["报告生成"])
app.include_router(model_versions.router, prefix=settings.API_V1_PREFIX, tags=["模型版本管理"])
app.include_router(rate_limit.router, prefix=settings.API_V1_PREFIX, tags=["限流管理"])
app.include_router(cache.router, prefix=settings.API_V1_PREFIX, tags=["缓存管理"])
app.include_router(monitor.router, prefix=settings.API_V1_PREFIX, tags=["系统监控"])
app.include_router(tasks.router, prefix=settings.API_V1_PREFIX, tags=["任务队列"])
app.include_router(experiment.router, prefix=settings.API_V1_PREFIX, tags=["论文实验"])
app.include_router(h5_visualize.router, prefix=settings.API_V1_PREFIX, tags=["H5可视化"])
app.include_router(multimodal.router, prefix=settings.API_V1_PREFIX, tags=["多模态融合"])


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("Starting up...")
    migrate_patients_extended_columns()
    migrate_patients_drop_id_card_column()
    # 启动任务队列
    await start_task_queue()
    logger.info("Task queue started")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Shutting down...")
    # 停止任务队列
    await stop_task_queue()
    logger.info("Task queue stopped")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "HeartCycle CAD System API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    import psutil
    from sqlalchemy import text

    health_status = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now().isoformat()
    }

    # 检查数据库连接
    try:
        from app.db.base import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # 检查磁盘空间
    try:
        disk_usage = psutil.disk_usage('.')
        health_status["disk"] = {
            "total_gb": round(disk_usage.total / (1024**3), 2),
            "used_gb": round(disk_usage.used / (1024**3), 2),
            "free_gb": round(disk_usage.free / (1024**3), 2),
            "percent": disk_usage.percent
        }
        if disk_usage.percent > 90:
            health_status["status"] = "warning"
    except Exception as e:
        health_status["disk"] = f"error: {str(e)}"

    # 检查内存使用
    try:
        memory = psutil.virtual_memory()
        health_status["memory"] = {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "percent": memory.percent
        }
    except Exception as e:
        health_status["memory"] = f"error: {str(e)}"

    return health_status


@app.get("/metrics")
async def get_metrics():
    """获取性能指标"""
    return performance_metrics.get_metrics()


@app.post("/metrics/reset")
async def reset_metrics():
    """重置性能指标"""
    performance_metrics.reset()
    return {"message": "性能指标已重置"}

