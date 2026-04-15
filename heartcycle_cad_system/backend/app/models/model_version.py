"""
模型版本管理数据模型
"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, JSON
from datetime import datetime

from ..db.base import Base


class ModelVersion(Base):
    """模型版本表"""
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False, index=True)
    version = Column(String(50), nullable=False, index=True)
    model_type = Column(String(50), nullable=False)  # lr, rf, xgb, cnn, lstm等
    model_path = Column(String(500), nullable=False)

    # 性能指标
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    auc = Column(Float, nullable=True)

    # 训练信息
    training_samples = Column(Integer, nullable=True)
    training_time = Column(Float, nullable=True)  # 训练时长（秒）
    hyperparameters = Column(JSON, nullable=True)  # 超参数

    # 特征信息
    feature_names = Column(JSON, nullable=True)  # 特征名称列表
    feature_count = Column(Integer, nullable=True)

    # 版本信息
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)  # 是否为当前激活版本
    is_production = Column(Boolean, default=False)  # 是否为生产版本

    # 创建者
    created_by = Column(Integer, nullable=True)  # 用户ID
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 备注
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<ModelVersion(name={self.model_name}, version={self.version}, type={self.model_type})>"
