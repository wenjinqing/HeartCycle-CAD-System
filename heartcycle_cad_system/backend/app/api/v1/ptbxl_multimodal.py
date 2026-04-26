"""PTB-XL 多模态 CAD 推理 API（ECG 波形 + 临床表格 → late fusion）。

端点
----
    GET  /api/v1/ptbxl-multimodal/status
        返回 ECG 分支与表格分支的可用性、元数据、可选融合方法

    POST /api/v1/ptbxl-multimodal/predict
        提供 ECG 波形（base64 / list）和/或表格特征字典 → 融合预测

设计
----
- 与 ``/api/v1/clinical-cad/*`` 互补：那个只用表格分支，本接口加 ECG 多模态融合
- ECG 输入兼容三种格式：
  1. ``signal``: 二维 list，shape (T, n_leads)，从前端 fetch 来的 JSON 数组
  2. ``signal_b64``: base64 编码的 float32 numpy 字节，配合 ``shape`` 字段
  3. 上传 .npy / .csv 文件（multipart） — 通过 /predict/upload 端点

学术合规
--------
两个分支训练用的都是真实公开数据集（PTB-XL CC-BY 4.0 + Z-Alizadeh UCI 公开），
与之前的 ``np.random.randint`` 路径完全切割。
"""
from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.logger import logger
from app.models.response import APIResponse
from app.services.ptbxl_multimodal_service import (
    FUSION_METHODS,
    get_ptbxl_multimodal_service,
)

router = APIRouter(prefix="/ptbxl-multimodal")


# ─── 请求模型 ───────────────────────────────────────────────────────────────

class ECGSignalPayload(BaseModel):
    """ECG 信号包装。signal 与 signal_b64 二选一。"""
    signal: Optional[List[List[float]]] = Field(
        default=None,
        description="二维 list, shape (T, n_leads)，前端友好的 JSON 数组")
    signal_b64: Optional[str] = Field(
        default=None,
        description="base64 编码的 float32 数组字节，配合 shape 字段")
    shape: Optional[List[int]] = Field(
        default=None,
        description="signal_b64 的形状 [T, n_leads]")
    fs: Optional[int] = Field(
        default=100,
        description="采样率，需匹配 PTB-XL ECG 模型（默认 100 Hz）")


class PTBXLMultimodalPredictRequest(BaseModel):
    ecg: Optional[ECGSignalPayload] = Field(
        default=None,
        description="ECG 波形（可选）")
    tabular: Optional[Dict[str, Any]] = Field(
        default=None,
        description="临床表格字段（可选；同 /api/v1/clinical-cad/predict）")
    fusion: str = Field(
        default="mean",
        description=f"融合策略，可选: {list(FUSION_METHODS)}")
    w_ecg: Optional[float] = Field(
        default=None,
        description="fusion='weighted' 时 ECG 分支权重；不填自动按 AUC 算")
    w_tab: Optional[float] = Field(
        default=None,
        description="fusion='weighted' 时表格分支权重")


def _decode_ecg(payload: ECGSignalPayload) -> np.ndarray:
    if payload.signal is not None:
        arr = np.asarray(payload.signal, dtype=np.float32)
        if arr.ndim != 2:
            raise ValueError(f"signal 应为 2D，shape={arr.shape}")
        return arr
    if payload.signal_b64 is not None:
        if not payload.shape or len(payload.shape) != 2:
            raise ValueError("使用 signal_b64 时必须提供 shape=[T, n_leads]")
        raw = base64.b64decode(payload.signal_b64)
        arr = np.frombuffer(raw, dtype=np.float32).reshape(*payload.shape)
        return arr.astype(np.float32, copy=True)  # 让数组可写
    raise ValueError("ECG payload 至少要 signal 或 signal_b64 之一")


# ─── 端点 ───────────────────────────────────────────────────────────────────

@router.get("/status")
def status():
    """返回 ECG / 表格分支的可用性与元数据。"""
    try:
        svc = get_ptbxl_multimodal_service()
        return APIResponse(
            success=True,
            message="OK",
            data=svc.get_status(),
        )
    except Exception as e:
        logger.exception(f"[ptbxl-multimodal] status 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict")
def predict(req: PTBXLMultimodalPredictRequest):
    """提供 ECG 与/或表格字段，返回融合预测结果。"""
    if req.ecg is None and not req.tabular:
        raise HTTPException(
            status_code=400,
            detail="ecg 与 tabular 至少要提供一个")
    if req.fusion not in FUSION_METHODS:
        raise HTTPException(
            status_code=400,
            detail=f"未知 fusion={req.fusion}，可选: {FUSION_METHODS}")

    ecg_arr: Optional[np.ndarray] = None
    if req.ecg is not None:
        try:
            ecg_arr = _decode_ecg(req.ecg)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"ECG 解码失败: {e}")

    try:
        svc = get_ptbxl_multimodal_service()
        result = svc.predict(
            ecg_signal=ecg_arr,
            tabular_features=req.tabular,
            fusion=req.fusion,
            w_ecg=req.w_ecg,
            w_tab=req.w_tab,
        )
        return APIResponse(success=True, message="预测成功", data=result)
    except RuntimeError as e:
        # 模型未加载等服务级错误
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"[ptbxl-multimodal] predict 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fusion-methods")
def fusion_methods():
    """列出可用融合策略与说明，供前端做下拉框。"""
    descs = {
        "mean": "算术平均（baseline，最稳健）",
        "weighted": "按各分支验证集 AUC 加权（推荐）",
        "logit_mean": "logit 空间平均（≈ 几何平均，抑制极端值）",
        "max": "取最大值（保守 → 高敏感度）",
        "min": "取最小值（保守 → 高特异度）",
    }
    return APIResponse(
        success=True,
        message="OK",
        data={"methods": [{"key": k, "description": descs[k]}
                          for k in FUSION_METHODS]},
    )
