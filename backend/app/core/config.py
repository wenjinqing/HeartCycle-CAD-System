"""
应用配置管理（向后兼容，使用新的Settings）
"""
from app.core.settings import Settings as NewSettings

# 为了向后兼容，创建settings实例
settings = NewSettings()
