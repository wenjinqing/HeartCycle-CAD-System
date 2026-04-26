"""
真实数据 (Z-Alizadeh Sani) CAD 推理 API
=========================================

把 ``data/models/zalizadeh_best.joblib``（``scripts/train_zalizadeh.py`` 训出来的
真实临床模型）暴露成 4 个端点供前端 ``/monitor`` 调用：

    GET  /api/v1/clinical-cad/status        # 模型是否就绪 + 元数据
    GET  /api/v1/clinical-cad/schema        # 表单字段规范（驱动前端）
    POST /api/v1/clinical-cad/predict       # 单条预测
    POST /api/v1/clinical-cad/predict/batch # 批量预测

与已有 ``/api/v1/predict`` 不同点：
- 输入是**结构化原始临床字段字典**（非 95 维已工程化特征向量），更符合医生填写习惯；
- 服务端复刻训练时的特征工程 + 标准化 + Youden's J 阈值；
- 返回风险等级、阳性概率、阈值、当前模型名（RandomForest / LightGBM / Stacking 等）。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import (
    assert_user_can_access_patient,
    get_current_user_optional,
)
from app.core.logger import logger
from app.db.base import get_db
from app.models.response import APIResponse
from app.models.user import User
from app.services.patient_service import PatientService
from app.services.zalizadeh_inference import (
    ZalizadehInferenceService,
    get_zalizadeh_inference_service,
)


router = APIRouter(prefix="/clinical-cad", tags=["真实数据 CAD 推理"])


# ─── 请求模型 ────────────────────────────────────────────────────────────
class ClinicalPredictRequest(BaseModel):
    """单条临床预测请求"""
    raw_features: Dict[str, Any] = Field(
        ...,
        description=(
            "原始临床字段字典（如 {'Age': 55, 'BP': 140, 'LDL': 130, "
            "'Typical Chest Pain': 1, ...}）。允许缺字段——服务端按训练集中位数兜底。"
        ),
    )
    patient_id: Optional[int] = Field(
        None,
        description="可选：写入该患者的预测记录（需要登录且有访问权限）",
    )


class ClinicalBatchPredictRequest(BaseModel):
    """批量预测请求"""
    rows: List[Dict[str, Any]] = Field(
        ...,
        description="每行一条原始字典；最多 5000 行",
        min_length=1,
        max_length=5000,
    )


# ─── 工具函数 ────────────────────────────────────────────────────────────
def _persist_prediction(
    db: Session,
    current_user: Optional[User],
    patient_id: int,
    prediction: int,
    probabilities: List[float],
    risk_level: str,
    raw_features: Dict[str, Any],
    model_name: str,
) -> None:
    """复刻 ``api/v1/models.py::_persist_patient_prediction`` 的行为，写入患者记录。"""
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="保存预测记录需要登录；请登录后从患者详情「新建预测」进入再分析",
        )
    ps = PatientService(db)
    patient = ps.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")
    assert_user_can_access_patient(current_user, patient, db)
    model_id = f"zalizadeh_real:{model_name}"[:100]
    ps.create_prediction_record(
        user_id=current_user.id,
        patient_id=patient_id,
        model_id=model_id,
        prediction=int(prediction),
        probability=json.dumps(probabilities),
        risk_level=risk_level,
        input_features=json.dumps(raw_features, ensure_ascii=False),
        shap_values=None,
    )


# ─── 端点 ────────────────────────────────────────────────────────────────
@router.get("/status", response_model=APIResponse, summary="真实数据模型状态")
def status(
    service: ZalizadehInferenceService = Depends(get_zalizadeh_inference_service),
):
    """返回真实数据 CAD 模型是否可用 + 性能指标 + 阈值。"""
    return APIResponse(success=True, message="ok", data=service.get_metadata())


@router.get("/schema", response_model=APIResponse, summary="临床表单字段规范")
def schema(
    service: ZalizadehInferenceService = Depends(get_zalizadeh_inference_service),
):
    """返回前端 ``/monitor`` 临床预测表单需要的字段（按训练集真实列序）。"""
    return APIResponse(success=True, message="ok", data=service.get_schema())


@router.post("/predict", response_model=APIResponse, summary="单条临床预测")
def predict(
    request: ClinicalPredictRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    service: ZalizadehInferenceService = Depends(get_zalizadeh_inference_service),
):
    """
    用 Z-Alizadeh Sani 真实数据训练的最优模型做一次单样本风险预测。

    - 输入：原始临床字段字典（自由缺失，会用中位数兜底）；
    - 输出：``prediction`` + ``probability`` + ``risk_level`` + 概率阈值 + 模型名。
    """
    if not service.is_available():
        meta = service.get_metadata()
        raise HTTPException(
            status_code=503,
            detail=meta.get("error") or "真实数据 CAD 模型未就绪，请先运行 scripts/train_zalizadeh.py",
        )
    try:
        result = service.predict_one(request.raw_features)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"真实数据 CAD 预测失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"预测失败: {e}")

    if request.patient_id is not None:
        _persist_prediction(
            db=db,
            current_user=current_user,
            patient_id=request.patient_id,
            prediction=result["prediction"],
            probabilities=result["probability"],
            risk_level=result["risk_level"],
            raw_features=request.raw_features,
            model_name=str(result.get("model", "RealCAD")),
        )

    return APIResponse(success=True, message="预测成功", data=result)


@router.post("/predict/batch", response_model=APIResponse, summary="批量临床预测")
def predict_batch(
    request: ClinicalBatchPredictRequest,
    service: ZalizadehInferenceService = Depends(get_zalizadeh_inference_service),
):
    """批量预测：一次最多 5000 行。"""
    if not service.is_available():
        meta = service.get_metadata()
        raise HTTPException(
            status_code=503,
            detail=meta.get("error") or "真实数据 CAD 模型未就绪",
        )
    try:
        items = service.predict_batch(request.rows)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"真实数据 CAD 批量预测失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量预测失败: {e}")

    return APIResponse(
        success=True,
        message=f"批量预测成功（共 {len(items)} 条）",
        data={"count": len(items), "results": items},
    )
