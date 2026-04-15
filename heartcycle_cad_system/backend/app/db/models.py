"""
数据库模型
"""
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, Index
from sqlalchemy.sql import func
from datetime import datetime
from app.db.base import Base

# 导入用户相关模型
from app.models.user import User, Patient, PredictionRecord, AuditLog, PatientDoctorBinding


class TrainingTask(Base):
    """训练任务模型"""
    __tablename__ = "training_tasks"
    
    # 主键
    task_id = Column(String(64), primary_key=True, comment="任务ID")
    
    # 任务状态
    status = Column(String(20), nullable=False, default="running", comment="任务状态: running/completed/failed")
    progress = Column(Float, default=0.0, comment="进度 (0.0-1.0)")
    message = Column(Text, comment="状态消息")
    
    # 文件信息
    current_file = Column(String(255), comment="当前处理的文件")
    total_files = Column(Integer, default=0, comment="总文件数")
    processed_files = Column(Integer, default=0, comment="已处理文件数")
    
    # 结果和错误
    result = Column(Text, comment="训练结果（JSON格式）")
    error = Column(Text, comment="错误信息")
    
    # 时间戳
    created_at = Column(DateTime, default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")
    expires_at = Column(DateTime, comment="过期时间")
    
    # 索引
    __table_args__ = (
        Index('idx_status', 'status'),
        Index('idx_created_at', 'created_at'),
        Index('idx_expires_at', 'expires_at'),
    )
    
    def to_dict(self):
        """转换为字典"""
        import json
        result = {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "current_file": self.current_file,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        # 解析JSON结果
        if self.result:
            try:
                result["result"] = json.loads(self.result)
            except:
                result["result"] = self.result
        
        return result

