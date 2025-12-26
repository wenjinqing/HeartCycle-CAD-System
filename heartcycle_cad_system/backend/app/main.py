"""
FastAPI主应用入口
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import BaseAPIException
from app.middleware.logging import LoggingMiddleware
from app.api.v1 import data, features, selection, models, shap

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
    logger.error(f"API Exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": type(exc).__name__,
            "detail": exc.detail,
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
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
    response = JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "InternalServerError",
            "detail": "服务器内部错误" if not settings.DEBUG else str(exc),
            "message": str(exc) if settings.DEBUG else None,
            "traceback": traceback.format_exc() if settings.DEBUG else None
        }
    )
    # 确保CORS头被添加（即使发生错误）
    origin = request.headers.get("origin", "*")
    if settings.DEBUG or origin in settings.CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin if origin != "*" else "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# 注册路由
app.include_router(data.router, prefix=settings.API_V1_PREFIX, tags=["数据管理"])
app.include_router(features.router, prefix=settings.API_V1_PREFIX, tags=["特征提取"])
app.include_router(selection.router, prefix=settings.API_V1_PREFIX, tags=["特征选择"])
app.include_router(models.router, prefix=settings.API_V1_PREFIX, tags=["模型训练"])
app.include_router(shap.router, prefix=settings.API_V1_PREFIX, tags=["可解释性"])


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
    return {"status": "healthy"}

