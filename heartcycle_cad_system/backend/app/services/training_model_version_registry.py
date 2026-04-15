"""
训练完成后写入「模型版本管理」表，供前端模型管理页展示名称与描述。
"""
from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.model_version_service import ModelVersionService

logger = logging.getLogger(__name__)

_INVALID_FS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_model_display_name(name: Optional[str], fallback: str, max_len: int = 100) -> str:
    s = (name or "").strip()
    if not s:
        s = fallback
    s = _INVALID_FS.sub("_", s)
    s = s.strip(" .")
    if not s:
        s = fallback
    return s[:max_len]


def flatten_metrics_for_model_version(metrics: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """将训练 metrics 转为 model_versions 表上的标量字段。"""
    out: Dict[str, float] = {}
    if not metrics or not isinstance(metrics, dict):
        return out

    def pick_float(*keys: str) -> Optional[float]:
        for k in keys:
            v = metrics.get(k)
            if v is None:
                continue
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
        return None

    # 与前端一致：优先 K 折 CV 均值（泛化估计），避免把全量训练集回测的 final_* 写入管理页造成「全是 1」的错觉
    fa = None
    if isinstance(metrics.get("accuracy"), dict):
        m = metrics["accuracy"].get("mean")
        if m is not None:
            try:
                fa = float(m)
            except (TypeError, ValueError):
                fa = None
    if fa is None:
        fa = pick_float("final_accuracy")
    if fa is not None:
        out["accuracy"] = fa

    fp = None
    if isinstance(metrics.get("precision"), dict):
        m = metrics["precision"].get("mean")
        if m is not None:
            try:
                fp = float(m)
            except (TypeError, ValueError):
                fp = None
    if fp is None:
        fp = pick_float("final_precision")
    if fp is not None:
        out["precision"] = fp

    fr = None
    if isinstance(metrics.get("recall"), dict):
        m = metrics["recall"].get("mean")
        if m is not None:
            try:
                fr = float(m)
            except (TypeError, ValueError):
                fr = None
    if fr is None:
        fr = pick_float("final_recall")
    if fr is not None:
        out["recall"] = fr

    ff = None
    if isinstance(metrics.get("f1"), dict):
        m = metrics["f1"].get("mean")
        if m is not None:
            try:
                ff = float(m)
            except (TypeError, ValueError):
                ff = None
    if ff is None:
        ff = pick_float("final_f1")
    if ff is not None:
        out["f1_score"] = ff

    auc = None
    if isinstance(metrics.get("roc_auc"), dict):
        m = metrics["roc_auc"].get("mean")
        if m is not None:
            try:
                auc = float(m)
            except (TypeError, ValueError):
                auc = None
    if auc is None:
        auc = pick_float("final_roc_auc")
    if auc is not None:
        out["auc"] = auc

    return out


def register_training_as_model_version(
    db: Session,
    *,
    model_id: str,
    model_type: str,
    model_path: str,
    metrics: Optional[Dict[str, Any]] = None,
    n_samples: Optional[int] = None,
    n_features: Optional[int] = None,
    feature_names: Optional[List[str]] = None,
    display_name: Optional[str] = None,
    model_description: Optional[str] = None,
    created_by: Optional[int] = None,
) -> None:
    """
    在训练成功后创建一条 model_versions 记录（会复制模型文件到 versions 目录）。
    model_id 用作 version 字段，保证与磁盘上的预测用 model_id 一致且唯一。
    """
    if not model_id or not model_path:
        logger.warning("跳过模型版本登记：缺少 model_id 或 model_path")
        return

    version = str(model_id)[:50]
    fallback_name = f"{model_type}_训练模型"
    model_name = sanitize_model_display_name(display_name, fallback_name, 100)

    desc = (model_description or "").strip() or None

    mflat = flatten_metrics_for_model_version(metrics)
    metrics_arg = mflat if mflat else None

    training_info = None
    if n_samples is not None:
        training_info = {"training_samples": int(n_samples)}

    feature_info = None
    if n_features is not None or feature_names:
        fn = feature_names
        if isinstance(fn, list) and len(fn) > 500:
            fn = fn[:500]
        feature_info = {
            "feature_count": int(n_features) if n_features is not None else (len(fn) if fn else None),
            "feature_names": fn,
        }

    svc = ModelVersionService(db)
    try:
        svc.create_version(
            model_name=model_name,
            version=version,
            model_type=model_type,
            model_path=model_path,
            metrics=metrics_arg,
            training_info=training_info,
            feature_info=feature_info,
            description=desc,
            created_by=created_by,
        )
        logger.info("已登记模型版本: %s / %s", model_name, version)
    except ValueError as e:
        logger.warning("模型版本登记跳过（可能已存在）: %s", e)
    except Exception as e:
        logger.error("模型版本登记失败: %s", e, exc_info=True)
