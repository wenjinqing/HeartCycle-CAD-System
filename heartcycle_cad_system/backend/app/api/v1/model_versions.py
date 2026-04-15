"""
模型版本管理 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
import os
import shutil

from algorithms.model_training import ModelTrainer
from ...core.utils import get_model_file_path
from ...services.training_model_version_registry import (
    register_training_as_model_version,
    sanitize_model_display_name,
)
from ...services.model_version_service import ModelVersionService
from ...models.response import APIResponse
from ...db.base import get_db
from ..deps import require_researcher, require_staff
from ...models.user import User
from sqlalchemy.orm import Session

router = APIRouter(prefix="/model-versions", tags=["模型版本管理"])


class ModelVersionCreate(BaseModel):
    """创建模型版本请求"""
    model_name: str = Field(..., description="模型名称")
    version: str = Field(..., description="版本号")
    model_type: str = Field(..., description="模型类型")
    description: Optional[str] = Field(None, description="描述")

    # 性能指标
    accuracy: Optional[float] = Field(None, description="准确率")
    precision: Optional[float] = Field(None, description="精确率")
    recall: Optional[float] = Field(None, description="召回率")
    f1_score: Optional[float] = Field(None, description="F1分数")
    auc: Optional[float] = Field(None, description="AUC")

    # 训练信息
    training_samples: Optional[int] = Field(None, description="训练样本数")
    training_time: Optional[float] = Field(None, description="训练时长（秒）")
    hyperparameters: Optional[Dict] = Field(None, description="超参数")

    # 特征信息
    feature_names: Optional[List[str]] = Field(None, description="特征名称列表")
    feature_count: Optional[int] = Field(None, description="特征数量")


class ModelVersionUpdate(BaseModel):
    """更新模型版本请求"""
    description: Optional[str] = Field(None, description="描述")
    notes: Optional[str] = Field(None, description="备注")
    is_active: Optional[bool] = Field(None, description="是否激活")
    is_production: Optional[bool] = Field(None, description="是否生产版本")


class RegisterFromTrainingBody(BaseModel):
    """将磁盘上的训练产物登记到模型版本库"""
    model_id: str = Field(..., description="训练返回的 model_id，对应 models 目录下的 joblib")
    model_type: Optional[str] = Field(None, description="模型类型，缺省时从 joblib 读取")
    display_name: Optional[str] = Field(None, description="在模型版本页展示的名称")
    model_description: Optional[str] = Field(None, description="描述")
    n_samples: Optional[int] = Field(None, description="训练样本数")
    n_features: Optional[int] = Field(None, description="特征数")
    metrics: Optional[Dict[str, Any]] = Field(None, description="训练指标（与训练接口返回的 metrics 结构一致）")
    feature_names: Optional[List[str]] = Field(None, description="特征名列表")
    set_active: bool = Field(False, description="登记后是否设为该展示名下的激活版本")


@router.post("", response_model=APIResponse, summary="创建模型版本")
async def create_model_version(
    model_name: str,
    version: str,
    model_type: str,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    accuracy: Optional[float] = None,
    precision: Optional[float] = None,
    recall: Optional[float] = None,
    f1_score: Optional[float] = None,
    auc: Optional[float] = None,
    training_samples: Optional[int] = None,
    training_time: Optional[float] = None,
    current_user: User = Depends(require_researcher),
    db: Session = Depends(get_db)
):
    """
    创建模型版本

    上传模型文件并创建版本记录
    """
    service = ModelVersionService(db)

    try:
        # 保存上传的模型文件
        temp_dir = os.path.join(service.models_dir, 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        temp_path = os.path.join(temp_dir, file.filename)
        with open(temp_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 准备指标和训练信息
        metrics = {}
        if accuracy is not None:
            metrics['accuracy'] = accuracy
        if precision is not None:
            metrics['precision'] = precision
        if recall is not None:
            metrics['recall'] = recall
        if f1_score is not None:
            metrics['f1_score'] = f1_score
        if auc is not None:
            metrics['auc'] = auc

        training_info = {}
        if training_samples is not None:
            training_info['training_samples'] = training_samples
        if training_time is not None:
            training_info['training_time'] = training_time

        # 创建版本
        model_version = service.create_version(
            model_name=model_name,
            version=version,
            model_type=model_type,
            model_path=temp_path,
            metrics=metrics if metrics else None,
            training_info=training_info if training_info else None,
            description=description,
            created_by=current_user.id
        )

        return APIResponse(
            success=True,
            message="模型版本创建成功",
            data={
                'id': model_version.id,
                'model_name': model_version.model_name,
                'version': model_version.version,
                'model_type': model_version.model_type
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"创建模型版本失败: {str(e)}"
        )


@router.get("", response_model=APIResponse, summary="列出模型版本")
async def list_model_versions(
    model_name: Optional[str] = None,
    model_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_production: Optional[bool] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    列出模型版本

    支持按模型名称、类型、状态筛选
    """
    service = ModelVersionService(db)

    try:
        versions, total = service.list_versions(
            model_name=model_name,
            model_type=model_type,
            is_active=is_active,
            is_production=is_production,
            skip=skip,
            limit=limit
        )

        versions_data = []
        for v in versions:
            versions_data.append({
                'id': v.id,
                'model_name': v.model_name,
                'version': v.version,
                'model_type': v.model_type,
                'accuracy': v.accuracy,
                'precision': v.precision,
                'recall': v.recall,
                'f1_score': v.f1_score,
                'auc': v.auc,
                'training_samples': v.training_samples,
                'training_time': v.training_time,
                'feature_count': v.feature_count,
                'description': v.description,
                'is_active': v.is_active,
                'is_production': v.is_production,
                'created_by': v.created_by,
                'created_at': v.created_at.isoformat() if v.created_at else None,
                'updated_at': v.updated_at.isoformat() if v.updated_at else None
            })

        return APIResponse(
            success=True,
            message=f"找到 {total} 个模型版本",
            data={
                'versions': versions_data,
                'total': total,
                'skip': skip,
                'limit': limit
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"列出模型版本失败: {str(e)}"
        )


@router.post("/register-from-training", response_model=APIResponse, summary="将训练产物登记到模型版本")
async def register_training_to_model_versions(
    body: RegisterFromTrainingBody,
    current_user: User = Depends(require_researcher),
    db: Session = Depends(get_db),
):
    """
    从已保存的 joblib 复制到模型版本目录并写入 model_versions 表（与训练完成自动登记逻辑一致）。
    若同一展示名与 model_id 对应版本已存在，返回成功并可选择仅更新激活状态。
    """
    model_id = (body.model_id or "").strip()
    if not model_id:
        raise HTTPException(status_code=400, detail="model_id 不能为空")

    path = get_model_file_path(model_id)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"未找到模型文件，请确认 model_id: {model_id}")

    try:
        model_data = ModelTrainer.load(model_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="模型文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取模型文件失败: {str(e)}")

    model_type = (body.model_type or model_data.get("model_type") or "unknown")
    if isinstance(model_type, str):
        model_type = model_type.strip() or "unknown"
    else:
        model_type = str(model_type)

    metadata = model_data.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    metrics = body.metrics if body.metrics is not None else metadata.get("metrics")
    n_samples = body.n_samples if body.n_samples is not None else metadata.get("n_samples")
    n_features = body.n_features
    if n_features is None:
        n_features = model_data.get("n_features")
    if n_features is None:
        n_features = metadata.get("n_features")

    feature_names = body.feature_names
    if feature_names is None:
        feature_names = model_data.get("feature_names")

    version = str(model_id)[:50]
    fallback_name = f"{model_type}_训练模型"
    model_name = sanitize_model_display_name(body.display_name, fallback_name, 100)

    service = ModelVersionService(db)
    existing = service.get_version_by_name(model_name, version)
    if existing:
        if body.set_active:
            service.update_version(existing.id, is_active=True)
        msg = "该训练结果已在模型版本列表中"
        if body.set_active:
            msg += "，已设为激活版本"
        return APIResponse(
            success=True,
            message=msg,
            data={
                "id": existing.id,
                "already_exists": True,
                "model_name": existing.model_name,
                "version": existing.version,
            },
        )

    register_training_as_model_version(
        db,
        model_id=model_id,
        model_type=model_type,
        model_path=path,
        metrics=metrics,
        n_samples=n_samples,
        n_features=n_features,
        feature_names=feature_names,
        display_name=body.display_name,
        model_description=body.model_description,
        created_by=current_user.id,
    )

    created = service.get_version_by_name(model_name, version)
    if not created:
        raise HTTPException(
            status_code=500,
            detail="登记模型版本失败，请查看服务端日志或确认是否违反唯一约束",
        )

    if body.set_active:
        service.update_version(created.id, is_active=True)

    return APIResponse(
        success=True,
        message="已保存并发布到模型版本",
        data={
            "id": created.id,
            "model_name": created.model_name,
            "version": created.version,
            "already_exists": False,
        },
    )


@router.get("/{version_id}", response_model=APIResponse, summary="获取模型版本详情")
async def get_model_version(
    version_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    获取模型版本详情
    """
    service = ModelVersionService(db)

    try:
        version = service.get_version(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="模型版本不存在")

        return APIResponse(
            success=True,
            message="获取成功",
            data={
                'id': version.id,
                'model_name': version.model_name,
                'version': version.version,
                'model_type': version.model_type,
                'model_path': version.model_path,
                'accuracy': version.accuracy,
                'precision': version.precision,
                'recall': version.recall,
                'f1_score': version.f1_score,
                'auc': version.auc,
                'training_samples': version.training_samples,
                'training_time': version.training_time,
                'hyperparameters': version.hyperparameters,
                'feature_names': version.feature_names,
                'feature_count': version.feature_count,
                'description': version.description,
                'is_active': version.is_active,
                'is_production': version.is_production,
                'notes': version.notes,
                'created_by': version.created_by,
                'created_at': version.created_at.isoformat() if version.created_at else None,
                'updated_at': version.updated_at.isoformat() if version.updated_at else None
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取模型版本失败: {str(e)}"
        )


@router.put("/{version_id}", response_model=APIResponse, summary="更新模型版本")
async def update_model_version(
    version_id: int,
    request: ModelVersionUpdate,
    current_user: User = Depends(require_researcher),
    db: Session = Depends(get_db)
):
    """
    更新模型版本信息
    """
    service = ModelVersionService(db)

    try:
        version = service.update_version(
            version_id=version_id,
            description=request.description,
            notes=request.notes,
            is_active=request.is_active,
            is_production=request.is_production
        )

        return APIResponse(
            success=True,
            message="更新成功",
            data={
                'id': version.id,
                'model_name': version.model_name,
                'version': version.version,
                'is_active': version.is_active,
                'is_production': version.is_production
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新模型版本失败: {str(e)}"
        )


@router.delete("/{version_id}", response_model=APIResponse, summary="删除模型版本")
async def delete_model_version(
    version_id: int,
    current_user: User = Depends(require_researcher),
    db: Session = Depends(get_db)
):
    """
    删除模型版本

    注意：不能删除激活或生产版本
    """
    service = ModelVersionService(db)

    try:
        success = service.delete_version(version_id)

        if success:
            return APIResponse(
                success=True,
                message="模型版本已删除"
            )
        else:
            raise HTTPException(status_code=404, detail="模型版本不存在")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除模型版本失败: {str(e)}"
        )


@router.post("/compare", response_model=APIResponse, summary="对比模型版本")
async def compare_model_versions(
    version_ids: List[int],
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    对比多个模型版本的性能指标
    """
    service = ModelVersionService(db)

    try:
        comparison = service.compare_versions(version_ids)

        return APIResponse(
            success=True,
            message=f"对比了 {len(comparison.get('versions', []))} 个版本",
            data=comparison
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"对比模型版本失败: {str(e)}"
        )


@router.get("/{model_name}/active", response_model=APIResponse, summary="获取激活版本")
async def get_active_version(
    model_name: str,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    获取指定模型的激活版本
    """
    service = ModelVersionService(db)

    try:
        version = service.get_active_version(model_name)

        if not version:
            raise HTTPException(
                status_code=404,
                detail=f"模型 {model_name} 没有激活版本"
            )

        return APIResponse(
            success=True,
            message="获取成功",
            data={
                'id': version.id,
                'model_name': version.model_name,
                'version': version.version,
                'model_type': version.model_type,
                'auc': version.auc,
                'is_active': version.is_active
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取激活版本失败: {str(e)}"
        )


@router.get("/{model_name}/production", response_model=APIResponse, summary="获取生产版本")
async def get_production_version(
    model_name: str,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    获取指定模型的生产版本
    """
    service = ModelVersionService(db)

    try:
        version = service.get_production_version(model_name)

        if not version:
            raise HTTPException(
                status_code=404,
                detail=f"模型 {model_name} 没有生产版本"
            )

        return APIResponse(
            success=True,
            message="获取成功",
            data={
                'id': version.id,
                'model_name': version.model_name,
                'version': version.version,
                'model_type': version.model_type,
                'auc': version.auc,
                'is_production': version.is_production
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取生产版本失败: {str(e)}"
        )


@router.post("/{model_name}/rollback", response_model=APIResponse, summary="回滚模型版本")
async def rollback_model_version(
    model_name: str,
    version: str,
    current_user: User = Depends(require_researcher),
    db: Session = Depends(get_db)
):
    """
    回滚到指定版本

    将指定版本设置为激活版本
    """
    service = ModelVersionService(db)

    try:
        rolled_version = service.rollback_version(model_name, version)

        return APIResponse(
            success=True,
            message=f"已回滚到版本 {version}",
            data={
                'id': rolled_version.id,
                'model_name': rolled_version.model_name,
                'version': rolled_version.version,
                'is_active': rolled_version.is_active
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"回滚模型版本失败: {str(e)}"
        )


@router.get("/{model_name}/history", response_model=APIResponse, summary="获取版本历史")
async def get_version_history(
    model_name: str,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    获取模型的所有版本历史
    """
    service = ModelVersionService(db)

    try:
        versions = service.get_version_history(model_name)

        versions_data = []
        for v in versions:
            versions_data.append({
                'id': v.id,
                'version': v.version,
                'model_type': v.model_type,
                'auc': v.auc,
                'accuracy': v.accuracy,
                'is_active': v.is_active,
                'is_production': v.is_production,
                'created_at': v.created_at.isoformat() if v.created_at else None
            })

        return APIResponse(
            success=True,
            message=f"找到 {len(versions)} 个版本",
            data=versions_data
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取版本历史失败: {str(e)}"
        )


@router.get("/{model_name}/statistics", response_model=APIResponse, summary="获取模型统计")
async def get_model_statistics(
    model_name: str,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """
    获取模型的统计信息

    包括版本数量、性能趋势等
    """
    service = ModelVersionService(db)

    try:
        statistics = service.get_model_statistics(model_name)

        if not statistics:
            raise HTTPException(
                status_code=404,
                detail=f"模型 {model_name} 不存在"
            )

        return APIResponse(
            success=True,
            message="获取成功",
            data=statistics
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取模型统计失败: {str(e)}"
        )
