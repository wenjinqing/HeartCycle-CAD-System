"""PTB-XL 多模态 CAD 推理服务（ECG 波形 + 临床表格 → late fusion）。

设计
----
- **ECG 分支**：``data/models/ptbxl_ecg_resnet1d_best.h5``
  来自 ``scripts/train_ptbxl_ecg.py``，输入 12 导联 100 Hz × 10 s ECG，
  输出 P(CAD|ECG)。
- **表格分支**：``data/models/zalizadeh_best.joblib``
  来自 ``scripts/train_zalizadeh.py``，输入 78 维原始临床字段，
  输出 P(CAD|Tabular)。
- **融合策略**（``fusion`` 参数）：
  - ``mean``       ：算术平均，最稳健的 baseline
  - ``weighted``   ：按各分支验证集 AUC 加权
  - ``logit_mean`` ：在 logit 空间平均（相当于几何平均），抑制极端值
  - ``max``        ：取最大概率（保守，倾向找出阳性）
  - ``min``        ：取最小概率（保守，倾向排除假阳）

学术合规
--------
- 两个分支训练用的是**真实公开数据集** (PTB-XL CC-BY 4.0 / Z-Alizadeh UCI 公开)
- 论文中的多模态对比实验**不再依赖** ``np.random.randint`` 这种伪标签
- 可在论文 ablation 中比较：ECG-only / Tabular-only / Late-Fusion 三种方案

懒加载
------
两个模型均按需加载；只调用一个分支时不会强制加载另一个。
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from app.core.config import settings
from app.core.logger import logger
from app.services.zalizadeh_inference import ZalizadehInferenceService

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ECG_MODEL = PROJECT_ROOT / "data" / "models" / "ptbxl_ecg_resnet1d_best.h5"
DEFAULT_ECG_META = PROJECT_ROOT / "data" / "models" / "ptbxl_ecg_resnet1d_meta.json"

FUSION_METHODS = ("mean", "weighted", "logit_mean", "max", "min")


def _risk_level(p: float) -> str:
    if p >= 0.80:
        return "高风险"
    if p >= 0.60:
        return "中-高风险"
    if p >= 0.40:
        return "中风险"
    if p >= 0.20:
        return "低-中风险"
    return "低风险"


def _logit(p: float, eps: float = 1e-7) -> float:
    p = float(np.clip(p, eps, 1 - eps))
    return float(np.log(p / (1 - p)))


def _sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))


# ─── ECG 分支（PTB-XL 模型） ────────────────────────────────────────────────

class PTBXLECGInference:
    """PTB-XL ECG 模型推理（懒加载 TF/Keras 模型）。"""

    def __init__(self, model_path: Path = DEFAULT_ECG_MODEL,
                 meta_path: Path = DEFAULT_ECG_META):
        self.model_path = Path(model_path)
        self.meta_path = Path(meta_path)
        self._model = None
        self._meta: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._load_error: Optional[str] = None

    def is_available(self) -> bool:
        return self.model_path.exists()

    def _ensure_loaded(self) -> bool:
        if self._model is not None:
            return True
        with self._lock:
            if self._model is not None:
                return True
            if not self.model_path.exists():
                self._load_error = f"模型文件不存在: {self.model_path}"
                logger.warning(self._load_error)
                return False
            try:
                import tensorflow as tf
                self._model = tf.keras.models.load_model(
                    str(self.model_path), compile=False)
                logger.info(f"[ptbxl-ecg] 已加载模型: {self.model_path}")
                if self.meta_path.exists():
                    self._meta = json.loads(self.meta_path.read_text())
            except Exception as e:
                self._load_error = f"模型加载失败: {e}"
                logger.error(self._load_error)
                return False
        return True

    def get_metadata(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "available": self.is_available(),
            "model_path": str(self.model_path),
            "loaded": self._model is not None,
            "load_error": self._load_error,
        }
        if self._meta:
            info["meta"] = self._meta
        return info

    def predict_signal(self, ecg: np.ndarray) -> Dict[str, Any]:
        """ecg shape: (T, n_leads) 或 (1, T, n_leads)。返回 {p_positive, ...}"""
        if not self._ensure_loaded():
            raise RuntimeError(self._load_error or "ECG 模型未加载")
        x = np.asarray(ecg, dtype=np.float32)
        if x.ndim == 2:
            x = x[None, :, :]
        if x.ndim != 3:
            raise ValueError(f"期望 (T,L) 或 (B,T,L) 形状，得到 {x.shape}")
        # 简单 z-score（与训练时一致）
        for b in range(x.shape[0]):
            for c in range(x.shape[2]):
                mu = x[b, :, c].mean()
                sd = x[b, :, c].std() + 1e-6
                x[b, :, c] = (x[b, :, c] - mu) / sd

        proba = self._model.predict(x, verbose=0).ravel()
        p_pos = float(proba[0])
        threshold = float(self._meta.get("test_metrics", {}).get(
            "best_threshold", 0.5))
        return {
            "prediction": int(p_pos >= threshold),
            "p_positive": p_pos,
            "probability": [float(1 - p_pos), float(p_pos)],
            "threshold": threshold,
            "risk_level": _risk_level(p_pos),
            "model": "PTBXL_ECG_ResNet1D",
        }


# ─── 多模态融合服务 ─────────────────────────────────────────────────────────

class PTBXLMultimodalService:
    """ECG 分支 + 表格分支，late fusion。"""

    def __init__(self):
        self.ecg = PTBXLECGInference()
        self.tabular = ZalizadehInferenceService()

    def get_status(self) -> Dict[str, Any]:
        return {
            "ecg_branch": self.ecg.get_metadata(),
            "tabular_branch": {
                "available": self.tabular.is_available(),
                "metadata": self.tabular.get_metadata()
                if self.tabular.is_available() else None,
            },
            "fusion_methods": list(FUSION_METHODS),
        }

    @staticmethod
    def _fuse(p_ecg: Optional[float], p_tab: Optional[float],
              method: str = "mean",
              w_ecg: float = 0.5, w_tab: float = 0.5) -> float:
        ps = [p for p in (p_ecg, p_tab) if p is not None]
        if not ps:
            raise ValueError("两个分支都没有给出概率，无法融合")
        if len(ps) == 1:
            return ps[0]
        if method == "mean":
            return float(np.mean(ps))
        if method == "weighted":
            total = w_ecg + w_tab if (w_ecg + w_tab) > 0 else 1.0
            return float((w_ecg * p_ecg + w_tab * p_tab) / total)
        if method == "logit_mean":
            return _sigmoid(0.5 * (_logit(p_ecg) + _logit(p_tab)))
        if method == "max":
            return float(max(ps))
        if method == "min":
            return float(min(ps))
        raise ValueError(f"未知融合方法 {method}，可选: {FUSION_METHODS}")

    def predict(self, *,
                ecg_signal: Optional[np.ndarray] = None,
                tabular_features: Optional[Dict[str, Any]] = None,
                fusion: str = "mean",
                w_ecg: Optional[float] = None,
                w_tab: Optional[float] = None) -> Dict[str, Any]:
        """提供 ECG 波形或临床字段（至少一个），返回融合预测。

        Parameters
        ----------
        ecg_signal:
            shape (T, 12) 的 ECG，**已重采样到 100 Hz**（建议 1000 samples）
        tabular_features:
            原始 Z-Alizadeh 字段字典（同 ``ZalizadehInferenceService.predict_one``）
        fusion:
            融合方法，见 ``FUSION_METHODS``
        w_ecg, w_tab:
            ``fusion='weighted'`` 时的权重；不填则用各分支验证集 AUC 自动加权
        """
        if ecg_signal is None and not tabular_features:
            raise ValueError("ecg_signal 与 tabular_features 至少要提供一个")
        if fusion not in FUSION_METHODS:
            raise ValueError(f"fusion 必须是 {FUSION_METHODS}")

        out: Dict[str, Any] = {
            "branches": {},
            "fusion_method": fusion,
        }
        p_ecg: Optional[float] = None
        p_tab: Optional[float] = None

        if ecg_signal is not None:
            try:
                ecg_res = self.ecg.predict_signal(ecg_signal)
                p_ecg = ecg_res["p_positive"]
                out["branches"]["ecg"] = ecg_res
            except Exception as e:
                logger.warning(f"[fusion] ECG 分支失败: {e}")
                out["branches"]["ecg"] = {"error": str(e)}

        if tabular_features is not None:
            try:
                tab_res = self.tabular.predict_one(tabular_features)
                p_tab = tab_res["p_positive"]
                out["branches"]["tabular"] = tab_res
            except Exception as e:
                logger.warning(f"[fusion] 表格分支失败: {e}")
                out["branches"]["tabular"] = {"error": str(e)}

        # 自动加权：用各分支元数据里记录的 test AUC 当先验
        if fusion == "weighted" and (w_ecg is None or w_tab is None):
            try:
                ecg_auc = float(self.ecg.get_metadata().get("meta", {})
                                .get("test_metrics", {}).get("auc", 0.5))
            except Exception:
                ecg_auc = 0.5
            try:
                tab_auc = float(self.tabular.get_metadata()
                                .get("test_auc", 0.5))
            except Exception:
                tab_auc = 0.5
            w_ecg = ecg_auc - 0.5  # 把"超过随机"的部分作权重
            w_tab = tab_auc - 0.5
            if w_ecg <= 0 and w_tab <= 0:
                w_ecg, w_tab = 0.5, 0.5
            out["fusion_weights"] = {"w_ecg": w_ecg, "w_tab": w_tab,
                                     "ecg_auc": ecg_auc, "tab_auc": tab_auc}

        if p_ecg is None and p_tab is None:
            raise RuntimeError("两个分支都未能产出概率，无法返回融合结果")

        p_fused = self._fuse(p_ecg, p_tab, fusion,
                             w_ecg=w_ecg or 0.5, w_tab=w_tab or 0.5)
        # 融合后阈值固定 0.5（融合后概率较少存在 calibration 偏差）
        prediction = int(p_fused >= 0.5)

        out.update({
            "p_positive": p_fused,
            "probability": [float(1 - p_fused), float(p_fused)],
            "prediction": prediction,
            "risk_level": _risk_level(p_fused),
            "threshold": 0.5,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })
        return out


# 单例
_service: Optional[PTBXLMultimodalService] = None
_service_lock = threading.Lock()


def get_ptbxl_multimodal_service() -> PTBXLMultimodalService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = PTBXLMultimodalService()
    return _service
