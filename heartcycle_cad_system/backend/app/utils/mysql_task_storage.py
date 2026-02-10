"""
任务存储工具 - MySQL实现（使用SQLAlchemy）
"""
import json
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.core.logger import logger

try:
    from app.db.base import SessionLocal, init_db, check_db_connection
    from app.db.models import TrainingTask
    DB_AVAILABLE = True
except ImportError as e:
    DB_AVAILABLE = False
    logger.warning(f"数据库模块不可用: {e}")


class MySQLTaskStorage:
    """使用MySQL存储任务状态"""
    
    def __init__(self):
        """初始化MySQL任务存储"""
        if not DB_AVAILABLE:
            raise ImportError("数据库模块不可用，请检查数据库配置")
        
        # 检查数据库连接
        if not check_db_connection():
            raise ConnectionError("无法连接到数据库，请检查DATABASE_URL配置")
        
        # 初始化数据库表
        try:
            init_db()
            logger.info("MySQL任务存储已初始化")
        except Exception as e:
            logger.warning(f"数据库表可能已存在: {e}")
    
    def _get_session(self) -> Session:
        """获取数据库会话"""
        return SessionLocal()
    
    def create_task(self, task_id: str, initial_data: Optional[Dict] = None) -> bool:
        """
        创建任务
        
        Parameters:
        -----------
        task_id : str
            任务ID
        initial_data : dict, optional
            初始任务数据
            
        Returns:
        --------
        bool : 是否创建成功
        """
        db = self._get_session()
        try:
            data = initial_data or {}
            
            # 设置过期时间（默认7天后）
            expires_at = datetime.now() + timedelta(days=7)
            if "expires_at" in data and isinstance(data["expires_at"], datetime):
                expires_at = data["expires_at"]
            
            # 处理result字段（转换为JSON）
            result_json = None
            if data.get("result"):
                try:
                    result_json = json.dumps(data["result"], default=str)
                except:
                    result_json = str(data["result"])
            
            task = TrainingTask(
                task_id=task_id,
                status=data.get("status", "running"),
                progress=data.get("progress", 0.0),
                message=data.get("message", "任务启动中..."),
                current_file=data.get("current_file"),
                total_files=data.get("total_files", 0),
                processed_files=data.get("processed_files", 0),
                result=result_json,
                error=data.get("error"),
                expires_at=expires_at
            )
            
            db.add(task)
            db.commit()
            logger.debug(f"任务 {task_id} 已创建")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"创建任务失败: {e}")
            return False
        finally:
            db.close()
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        获取任务状态
        
        Parameters:
        -----------
        task_id : str
            任务ID
            
        Returns:
        --------
        dict : 任务状态，如果不存在返回None
        """
        db = self._get_session()
        try:
            task = db.query(TrainingTask).filter(TrainingTask.task_id == task_id).first()
            if task:
                return task.to_dict()
            return None
        except Exception as e:
            logger.error(f"获取任务失败: {e}")
            return None
        finally:
            db.close()
    
    def update_task(self, task_id: str, updates: Dict) -> bool:
        """
        更新任务状态
        
        Parameters:
        -----------
        task_id : str
            任务ID
        updates : dict
            要更新的字段
            
        Returns:
        --------
        bool : 是否更新成功
        """
        db = self._get_session()
        try:
            task = db.query(TrainingTask).filter(TrainingTask.task_id == task_id).first()
            if not task:
                logger.warning(f"任务 {task_id} 不存在，无法更新")
                return False
            
            # 更新字段
            for key, value in updates.items():
                if key == "result" and value is not None:
                    try:
                        task.result = json.dumps(value, default=str)
                    except:
                        task.result = str(value)
                elif hasattr(task, key):
                    setattr(task, key, value)
            
            task.updated_at = datetime.now()
            
            db.commit()
            logger.debug(f"任务 {task_id} 已更新: {list(updates.keys())}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"更新任务失败: {e}")
            return False
        finally:
            db.close()
    
    def delete_task(self, task_id: str) -> bool:
        """
        删除任务
        
        Parameters:
        -----------
        task_id : str
            任务ID
            
        Returns:
        --------
        bool : 是否删除成功
        """
        db = self._get_session()
        try:
            task = db.query(TrainingTask).filter(TrainingTask.task_id == task_id).first()
            if task:
                db.delete(task)
                db.commit()
                logger.debug(f"任务 {task_id} 已删除")
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"删除任务失败: {e}")
            return False
        finally:
            db.close()
    
    def cleanup_expired_tasks(self, days: int = 7) -> int:
        """
        清理过期任务
        
        Parameters:
        -----------
        days : int
            保留天数，默认7天
            
        Returns:
        --------
        int : 清理的任务数量
        """
        db = self._get_session()
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 删除过期任务或已完成/失败且超过保留期的任务
            deleted = db.query(TrainingTask).filter(
                or_(
                    TrainingTask.expires_at < cutoff_date,
                    and_(
                        TrainingTask.status.in_(["completed", "failed"]),
                        TrainingTask.updated_at < cutoff_date
                    )
                )
            ).delete()
            
            db.commit()
            
            if deleted > 0:
                logger.info(f"清理了 {deleted} 个过期任务")
            return deleted
        except Exception as e:
            db.rollback()
            logger.error(f"清理过期任务失败: {e}")
            return 0
        finally:
            db.close()
    
    def list_tasks(self, status: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        列出任务
        
        Parameters:
        -----------
        status : str, optional
            筛选状态
        limit : int
            返回数量限制
            
        Returns:
        --------
        list : 任务列表
        """
        db = self._get_session()
        try:
            query = db.query(TrainingTask)
            
            if status:
                query = query.filter(TrainingTask.status == status)
            
            tasks = query.order_by(TrainingTask.created_at.desc()).limit(limit).all()
            
            return [task.to_dict() for task in tasks]
        except Exception as e:
            logger.error(f"列出任务失败: {e}")
            return []
        finally:
            db.close()


# 全局任务存储实例
_mysql_task_storage: Optional[MySQLTaskStorage] = None


def get_mysql_task_storage() -> MySQLTaskStorage:
    """获取MySQL任务存储实例（单例模式）"""
    global _mysql_task_storage
    if _mysql_task_storage is None:
        _mysql_task_storage = MySQLTaskStorage()
    return _mysql_task_storage

