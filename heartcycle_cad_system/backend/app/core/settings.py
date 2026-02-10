"""
应用设置（增强版配置）
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
from pathlib import Path
import os


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基本信息
    APP_NAME: str = "HeartCycle CAD System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # 文件路径
    # __file__ 是 backend/app/core/settings.py
    # .parent.parent.parent 是 backend 目录
    # 需要再向上一步到项目根目录
    BACKEND_DIR: Path = Path(__file__).parent.parent.parent  # backend目录
    BASE_DIR: Path = BACKEND_DIR.parent  # 项目根目录 (heartcycle_cad_system)
    DATA_ROOT: str = str(BASE_DIR / "data")
    UPLOAD_DIR: str = str(BASE_DIR / "data" / "raw")
    PROCESSED_DIR: str = str(BASE_DIR / "data" / "processed")
    FEATURES_DIR: str = str(BASE_DIR / "data" / "features")
    MODELS_DIR: str = str(BASE_DIR / "data" / "models")
    RESULTS_DIR: str = "./results"
    LOGS_DIR: str = "./logs"
    
    # 数据库配置
    # SQLite: sqlite:///绝对路径（在model_post_init中设置为绝对路径）
    # MySQL: mysql+pymysql://user:password@host:port/database
    # PostgreSQL: postgresql://user:password@host:port/database
    DATABASE_URL: str = "sqlite:///./data/heartcycle.db"  # 默认值，会在model_post_init中转换为绝对路径
    
    # API配置
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:5173", "http://127.0.0.1:5173"]
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    # 性能配置
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    REQUEST_TIMEOUT: int = 300  # 5分钟
    
    # 模型配置
    DEFAULT_MODEL_TYPE: str = "rf"
    DEFAULT_CV_FOLDS: int = 5
    DEFAULT_RANDOM_STATE: int = 42
    
    # 缓存配置
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600  # 1小时
    
    class Config:

        case_sensitive = True
    
    def model_post_init(self, __context):
        """在模型初始化后处理"""
        super().model_post_init(__context)
        # 如果DATABASE_URL是默认的相对路径，则使用绝对路径
        if self.DATABASE_URL.startswith('sqlite:///./') or self.DATABASE_URL == "sqlite:///./data/heartcycle.db":
            # 使用绝对路径设置SQLite数据库
            db_path = str(self.BASE_DIR / "data" / "heartcycle.db")
            object.__setattr__(self, 'DATABASE_URL', f"sqlite:///{db_path}")
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.UPLOAD_DIR,
            self.PROCESSED_DIR,
            self.FEATURES_DIR,
            self.MODELS_DIR,
            self.RESULTS_DIR,
            self.LOGS_DIR,
        ]
        
        # 如果使用SQLite，确保数据库目录存在
        if self.DATABASE_URL.startswith('sqlite:///'):
            db_path = self.DATABASE_URL.replace('sqlite:///', '')
            db_dir = os.path.dirname(db_path)
            if db_dir:
                directories.append(db_dir)
        
        for directory in directories:
            if directory:
                os.makedirs(directory, exist_ok=True)


# 创建配置实例
settings = Settings()

