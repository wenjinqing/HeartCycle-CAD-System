"""
模型版本管理服务
"""
import os
import shutil
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional, Dict, Tuple
from datetime import datetime
import logging

from ..models.model_version import ModelVersion
from ..core.config import settings
from ..core.exceptions import ModelNotFoundError

logger = logging.getLogger(__name__)


class ModelVersionService:
    """模型版本管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.models_dir = os.path.join(settings.BASE_DIR, 'models', 'versions')
        os.makedirs(self.models_dir, exist_ok=True)

    def create_version(
        self,
        model_name: str,
        version: str,
        model_type: str,
        model_path: str,
        metrics: Optional[Dict] = None,
        training_info: Optional[Dict] = None,
        feature_info: Optional[Dict] = None,
        description: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> ModelVersion:
        """
        创建模型版本

        Parameters:
        -----------
        model_name : str
            模型名称
        version : str
            版本号
        model_type : str
            模型类型
        model_path : str
            模型文件路径
        metrics : Optional[Dict]
            性能指标
        training_info : Optional[Dict]
            训练信息
        feature_info : Optional[Dict]
            特征信息
        description : Optional[str]
            描述
        created_by : Optional[int]
            创建者ID

        Returns:
        --------
        ModelVersion
        """
        # 检查版本是否已存在
        existing = self.db.query(ModelVersion).filter(
            ModelVersion.model_name == model_name,
            ModelVersion.version == version
        ).first()

        if existing:
            raise ValueError(f"模型版本已存在: {model_name} v{version}")

        # 复制模型文件到版本目录
        version_dir = os.path.join(self.models_dir, model_name, version)
        os.makedirs(version_dir, exist_ok=True)

        if os.path.exists(model_path):
            filename = os.path.basename(model_path)
            dest_path = os.path.join(version_dir, filename)
            shutil.copy2(model_path, dest_path)
            stored_path = dest_path
        else:
            stored_path = model_path

        # 创建版本记录
        model_version = ModelVersion(
            model_name=model_name,
            version=version,
            model_type=model_type,
            model_path=stored_path,
            description=description,
            created_by=created_by
        )

        # 设置性能指标
        if metrics:
            model_version.accuracy = metrics.get('accuracy')
            model_version.precision = metrics.get('precision')
            model_version.recall = metrics.get('recall')
            model_version.f1_score = metrics.get('f1_score')
            model_version.auc = metrics.get('auc')

        # 设置训练信息
        if training_info:
            model_version.training_samples = training_info.get('training_samples')
            model_version.training_time = training_info.get('training_time')
            model_version.hyperparameters = training_info.get('hyperparameters')

        # 设置特征信息
        if feature_info:
            model_version.feature_names = feature_info.get('feature_names')
            model_version.feature_count = feature_info.get('feature_count')

        self.db.add(model_version)
        self.db.commit()
        self.db.refresh(model_version)

        logger.info(f"创建模型版本: {model_name} v{version}")

        return model_version

    def get_version(self, version_id: int) -> Optional[ModelVersion]:
        """获取模型版本"""
        return self.db.query(ModelVersion).filter(ModelVersion.id == version_id).first()

    def get_version_by_name(self, model_name: str, version: str) -> Optional[ModelVersion]:
        """根据名称和版本号获取模型版本"""
        return self.db.query(ModelVersion).filter(
            ModelVersion.model_name == model_name,
            ModelVersion.version == version
        ).first()

    def list_versions(
        self,
        model_name: Optional[str] = None,
        model_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_production: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[ModelVersion], int]:
        """
        列出模型版本

        Parameters:
        -----------
        model_name : Optional[str]
            模型名称筛选
        model_type : Optional[str]
            模型类型筛选
        is_active : Optional[bool]
            是否激活筛选
        is_production : Optional[bool]
            是否生产版本筛选
        skip : int
            跳过数量
        limit : int
            返回数量

        Returns:
        --------
        versions, total
        """
        query = self.db.query(ModelVersion)

        if model_name:
            query = query.filter(ModelVersion.model_name == model_name)

        if model_type:
            query = query.filter(ModelVersion.model_type == model_type)

        if is_active is not None:
            query = query.filter(ModelVersion.is_active == is_active)

        if is_production is not None:
            query = query.filter(ModelVersion.is_production == is_production)

        total = query.count()
        versions = query.order_by(desc(ModelVersion.created_at)).offset(skip).limit(limit).all()

        return versions, total

    def update_version(
        self,
        version_id: int,
        description: Optional[str] = None,
        notes: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_production: Optional[bool] = None
    ) -> ModelVersion:
        """
        更新模型版本

        Parameters:
        -----------
        version_id : int
            版本ID
        description : Optional[str]
            描述
        notes : Optional[str]
            备注
        is_active : Optional[bool]
            是否激活
        is_production : Optional[bool]
            是否生产版本

        Returns:
        --------
        ModelVersion
        """
        version = self.get_version(version_id)
        if not version:
            raise ModelNotFoundError(f"模型版本不存在: {version_id}")

        if description is not None:
            version.description = description

        if notes is not None:
            version.notes = notes

        if is_active is not None:
            # 如果设置为激活，取消同名模型的其他激活版本
            if is_active:
                self.db.query(ModelVersion).filter(
                    ModelVersion.model_name == version.model_name,
                    ModelVersion.id != version_id
                ).update({'is_active': False})

            version.is_active = is_active

        if is_production is not None:
            # 如果设置为生产版本，取消同名模型的其他生产版本
            if is_production:
                self.db.query(ModelVersion).filter(
                    ModelVersion.model_name == version.model_name,
                    ModelVersion.id != version_id
                ).update({'is_production': False})

            version.is_production = is_production

        self.db.commit()
        self.db.refresh(version)

        logger.info(f"更新模型版本: {version.model_name} v{version.version}")

        return version

    def delete_version(self, version_id: int) -> bool:
        """
        删除模型版本

        Parameters:
        -----------
        version_id : int
            版本ID

        Returns:
        --------
        bool
        """
        version = self.get_version(version_id)
        if not version:
            raise ModelNotFoundError(f"模型版本不存在: {version_id}")

        # 不允许删除激活或生产版本
        if version.is_active or version.is_production:
            raise ValueError("不能删除激活或生产版本")

        # 删除模型文件
        if os.path.exists(version.model_path):
            try:
                os.remove(version.model_path)
                # 尝试删除空目录
                version_dir = os.path.dirname(version.model_path)
                if os.path.exists(version_dir) and not os.listdir(version_dir):
                    os.rmdir(version_dir)
            except Exception as e:
                logger.warning(f"删除模型文件失败: {e}")

        # 删除数据库记录
        self.db.delete(version)
        self.db.commit()

        logger.info(f"删除模型版本: {version.model_name} v{version.version}")

        return True

    def compare_versions(self, version_ids: List[int]) -> Dict:
        """
        对比模型版本

        Parameters:
        -----------
        version_ids : List[int]
            版本ID列表

        Returns:
        --------
        Dict : 对比结果
        """
        versions = [self.get_version(vid) for vid in version_ids]
        versions = [v for v in versions if v is not None]

        if not versions:
            return {}

        comparison = {
            'versions': [],
            'metrics_comparison': {},
            'best_version': None
        }

        # 收集版本信息
        for version in versions:
            version_info = {
                'id': version.id,
                'model_name': version.model_name,
                'version': version.version,
                'model_type': version.model_type,
                'accuracy': version.accuracy,
                'precision': version.precision,
                'recall': version.recall,
                'f1_score': version.f1_score,
                'auc': version.auc,
                'training_samples': version.training_samples,
                'training_time': version.training_time,
                'feature_count': version.feature_count,
                'created_at': version.created_at.isoformat() if version.created_at else None
            }
            comparison['versions'].append(version_info)

        # 指标对比
        metrics = ['accuracy', 'precision', 'recall', 'f1_score', 'auc']
        for metric in metrics:
            values = [getattr(v, metric) for v in versions if getattr(v, metric) is not None]
            if values:
                comparison['metrics_comparison'][metric] = {
                    'max': max(values),
                    'min': min(values),
                    'avg': sum(values) / len(values)
                }

        # 找出最佳版本（基于AUC）
        versions_with_auc = [v for v in versions if v.auc is not None]
        if versions_with_auc:
            best = max(versions_with_auc, key=lambda v: v.auc)
            comparison['best_version'] = {
                'id': best.id,
                'model_name': best.model_name,
                'version': best.version,
                'auc': best.auc
            }

        return comparison

    def get_active_version(self, model_name: str) -> Optional[ModelVersion]:
        """
        获取激活版本

        Parameters:
        -----------
        model_name : str
            模型名称

        Returns:
        --------
        Optional[ModelVersion]
        """
        return self.db.query(ModelVersion).filter(
            ModelVersion.model_name == model_name,
            ModelVersion.is_active == True
        ).first()

    def get_production_version(self, model_name: str) -> Optional[ModelVersion]:
        """
        获取生产版本

        Parameters:
        -----------
        model_name : str
            模型名称

        Returns:
        --------
        Optional[ModelVersion]
        """
        return self.db.query(ModelVersion).filter(
            ModelVersion.model_name == model_name,
            ModelVersion.is_production == True
        ).first()

    def rollback_version(self, model_name: str, version: str) -> ModelVersion:
        """
        回滚到指定版本

        Parameters:
        -----------
        model_name : str
            模型名称
        version : str
            版本号

        Returns:
        --------
        ModelVersion
        """
        target_version = self.get_version_by_name(model_name, version)
        if not target_version:
            raise ModelNotFoundError(f"模型版本不存在: {model_name} v{version}")

        # 取消当前激活版本
        self.db.query(ModelVersion).filter(
            ModelVersion.model_name == model_name,
            ModelVersion.is_active == True
        ).update({'is_active': False})

        # 激活目标版本
        target_version.is_active = True
        self.db.commit()
        self.db.refresh(target_version)

        logger.info(f"回滚模型版本: {model_name} -> v{version}")

        return target_version

    def get_version_history(self, model_name: str) -> List[ModelVersion]:
        """
        获取模型版本历史

        Parameters:
        -----------
        model_name : str
            模型名称

        Returns:
        --------
        List[ModelVersion]
        """
        return self.db.query(ModelVersion).filter(
            ModelVersion.model_name == model_name
        ).order_by(desc(ModelVersion.created_at)).all()

    def get_model_statistics(self, model_name: str) -> Dict:
        """
        获取模型统计信息

        Parameters:
        -----------
        model_name : str
            模型名称

        Returns:
        --------
        Dict : 统计信息
        """
        versions = self.get_version_history(model_name)

        if not versions:
            return {}

        # 统计信息
        total_versions = len(versions)
        active_version = next((v for v in versions if v.is_active), None)
        production_version = next((v for v in versions if v.is_production), None)

        # 性能趋势
        performance_trend = []
        for version in reversed(versions):
            if version.auc is not None:
                performance_trend.append({
                    'version': version.version,
                    'auc': version.auc,
                    'created_at': version.created_at.isoformat() if version.created_at else None
                })

        # 最佳性能
        versions_with_auc = [v for v in versions if v.auc is not None]
        best_version = max(versions_with_auc, key=lambda v: v.auc) if versions_with_auc else None

        return {
            'model_name': model_name,
            'total_versions': total_versions,
            'active_version': {
                'version': active_version.version,
                'auc': active_version.auc
            } if active_version else None,
            'production_version': {
                'version': production_version.version,
                'auc': production_version.auc
            } if production_version else None,
            'best_version': {
                'version': best_version.version,
                'auc': best_version.auc
            } if best_version else None,
            'performance_trend': performance_trend
        }
