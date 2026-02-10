"""
FastAPI主应用入口
"""
import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.core.logger import logger, log_with_context
from app.core.exceptions import BaseAPIException
from app.middleware.logging import LoggingMiddleware, performance_metrics
from app.api.v1 import data, features, selection, models, shap, h5_convert

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="HeartCycle 冠心病风险预测系统 API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 启动日志
logger.info(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")

# 添加请求日志中间件
app.add_middleware(LoggingMiddleware)

# CORS中间件
# 开发环境下使用更宽松的CORS配置
cors_origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理"""
    logger.error(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error_code": "ValidationError",
            "detail": exc.errors(),
            "body": exc.body
        }
    )


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
        from app.db.database import engine
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

