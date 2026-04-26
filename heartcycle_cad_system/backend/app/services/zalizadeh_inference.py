"""
Z-Alizadeh Sani 真实数据训练模型推理服务
==========================================

把 ``scripts/train_zalizadeh.py`` 训出来的真实数据 CAD 模型
（``data/models/zalizadeh_best.joblib``）封装成可被 FastAPI 调用的服务：

    - 接受**原始临床字段**的字典（不是已工程化后的 95 维向量）
    - 服务端复刻训练时的特征工程 + 标准化 + Youden's J 阈值
    - 返回预测标签、风险等级、阳性概率、置信度、关键贡献特征

设计目标
--------
1. **零侵入**：不依赖现有 ``ModelService`` 的目录扫描逻辑（它的 0-padding 策略
   不适合 78 维原始临床特征 → 95 维工程特征的变换）。
2. **懒加载**：FastAPI 启动时不强制加载，只有首次调用时才打开 joblib，
   失败也不会让整个应用挂掉。
3. **缺值鲁棒**：原始 CSV 的中位数当作缺失值兜底；阈值优先取 bundle 内嵌值，
   退化为 0.5。
4. **schema 自描述**：``get_schema()`` 直接驱动前端表单渲染。

> 该服务对应论文里 RandomForest AUC=0.9044, Sens=0.9697, Acc=0.8913 的模型。
"""

from __future__ import annotations

import math
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

from app.core.logger import logger
from app.core.config import settings


MODEL_FILE = "zalizadeh_best.joblib"
RAW_FEATURES_CSV = "cad_features.csv"
RAW_LABELS_CSV = "cad_labels.csv"


# ---------------------------------------------------------------------------
# 字段语义元信息（驱动前端表单 + 单位提示）
# ---------------------------------------------------------------------------
# 仅描述具有医学意义、且属于 Z-Alizadeh Sani 数据集 78 个原始列的字段。
# 其余 _N/_Y/_Female/_Male 等 one-hot 列在请求中以 0/1 形式直传即可。
RAW_FIELD_META: Dict[str, Dict[str, Any]] = {
    "Age":             {"label": "年龄",       "unit": "岁",   "type": "number", "min": 18, "max": 100},
    "Weight":          {"label": "体重",       "unit": "kg",   "type": "number", "min": 30, "max": 200},
    "Length":          {"label": "身高",       "unit": "cm",   "type": "number", "min": 120, "max": 220},
    "BMI":             {"label": "BMI",         "unit": "kg/m²","type": "number", "min": 12, "max": 60},
    "DM":              {"label": "糖尿病",     "unit": "0/1",  "type": "binary"},
    "HTN":             {"label": "高血压",     "unit": "0/1",  "type": "binary"},
    "Current Smoker":  {"label": "当前吸烟",   "unit": "0/1",  "type": "binary"},
    "EX-Smoker":       {"label": "戒烟",       "unit": "0/1",  "type": "binary"},
    "FH":              {"label": "家族史",     "unit": "0/1",  "type": "binary"},
    "BP":              {"label": "收缩压",     "unit": "mmHg", "type": "number", "min": 60, "max": 250},
    "PR":              {"label": "脉率",       "unit": "bpm",  "type": "number", "min": 30, "max": 200},
    "Edema":           {"label": "水肿",       "unit": "0/1",  "type": "binary"},
    "Typical Chest Pain": {"label": "典型胸痛", "unit": "0/1", "type": "binary"},
    "Function Class":  {"label": "心功能分级 (NYHA)", "unit": "1-4", "type": "number", "min": 0, "max": 4},
    "Q Wave":          {"label": "Q 波异常",   "unit": "0/1",  "type": "binary"},
    "St Elevation":    {"label": "ST 段抬高",  "unit": "0/1",  "type": "binary"},
    "St Depression":   {"label": "ST 段压低",  "unit": "0/1",  "type": "binary"},
    "Tinversion":      {"label": "T 波倒置",   "unit": "0/1",  "type": "binary"},
    "FBS":             {"label": "空腹血糖",   "unit": "mg/dL","type": "number", "min": 30, "max": 500},
    "CR":              {"label": "肌酐",       "unit": "mg/dL","type": "number", "min": 0.1, "max": 15},
    "TG":              {"label": "甘油三酯",   "unit": "mg/dL","type": "number", "min": 20, "max": 1000},
    "LDL":             {"label": "LDL",         "unit": "mg/dL","type": "number", "min": 20, "max": 400},
    "HDL":             {"label": "HDL",         "unit": "mg/dL","type": "number", "min": 10, "max": 150},
    "BUN":             {"label": "尿素氮",     "unit": "mg/dL","type": "number", "min": 1, "max": 200},
    "ESR":             {"label": "血沉",       "unit": "mm/h", "type": "number", "min": 0, "max": 200},
    "HB":              {"label": "血红蛋白",   "unit": "g/dL", "type": "number", "min": 5, "max": 25},
    "K":               {"label": "钾",          "unit": "mEq/L","type": "number", "min": 1, "max": 8},
    "Na":              {"label": "钠",          "unit": "mEq/L","type": "number", "min": 110, "max": 170},
    "WBC":             {"label": "白细胞",     "unit": "/μL",  "type": "number", "min": 1000, "max": 50000},
    "Lymph":           {"label": "淋巴细胞%",  "unit": "%",    "type": "number", "min": 0, "max": 100},
    "Neut":            {"label": "中性粒细胞%","unit": "%",    "type": "number", "min": 0, "max": 100},
    "PLT":             {"label": "血小板",     "unit": "10⁹/L","type": "number", "min": 50, "max": 1000},
    "EF-TTE":          {"label": "射血分数 (TTE)", "unit": "%", "type": "number", "min": 10, "max": 80},
    "Region RWMA":     {"label": "区域室壁运动异常", "unit": "0-4", "type": "number", "min": 0, "max": 4},
}


# ---------------------------------------------------------------------------
# 特征工程（与 scripts/train_zalizadeh.py 中 add_engineered_features 完全一致）
# ---------------------------------------------------------------------------
def _add_engineered_features(X: pd.DataFrame) -> pd.DataFrame:
    """临床先验驱动的特征工程，逻辑必须与训练脚本 1:1 对齐。"""
    out = X.copy()

    if {"LDL", "HDL"}.issubset(out.columns):
        out["LDL_HDL_ratio"] = out["LDL"] / out["HDL"].replace(0, np.nan)
    if {"TG", "HDL"}.issubset(out.columns):
        out["TG_HDL_ratio"] = out["TG"] / out["HDL"].replace(0, np.nan)
    if {"Na", "K"}.issubset(out.columns):
        out["Na_K_ratio"] = out["Na"] / out["K"].replace(0, np.nan)
    if {"Neut", "Lymph"}.issubset(out.columns):
        out["NLR"] = out["Neut"] / out["Lymph"].replace(0, np.nan)

    if "Age" in out.columns:
        for risk in ["HTN", "DM", "Current Smoker", "FH"]:
            if risk in out.columns:
                out[f"Age_x_{risk.replace(' ', '_')}"] = out["Age"] * out[risk]

    if "BMI" in out.columns:
        bmi = out["BMI"]
        out["BMI_underweight"] = (bmi < 18.5).astype(int)
        out["BMI_overweight"] = ((bmi >= 25) & (bmi < 30)).astype(int)
        out["BMI_obese"] = (bmi >= 30).astype(int)

    if "Age" in out.columns:
        age = out["Age"]
        out["Age_lt45"] = (age < 45).astype(int)
        out["Age_45_60"] = ((age >= 45) & (age < 60)).astype(int)
        out["Age_ge60"] = (age >= 60).astype(int)

    angina_cols = [c for c in ["Typical Chest Pain", "Atypical_Y", "Nonanginal_Y", "LowTH Ang_Y"] if c in out.columns]
    if angina_cols:
        out["chest_pain_score"] = out[angina_cols].sum(axis=1)

    ecg_cols = [c for c in ["Q Wave", "St Elevation", "St Depression", "Tinversion", "LVH_Y"] if c in out.columns]
    if ecg_cols:
        out["ecg_abnormal_score"] = out[ecg_cols].sum(axis=1)

    if "Function Class" in out.columns:
        out["FunctionClass_high"] = (out["Function Class"] >= 3).astype(int)

    return out.replace([np.inf, -np.inf], np.nan)


def _risk_level_from_proba(p_pos: float) -> str:
    """与 ``api/v1/models.py:_risk_level_from_probabilities`` 保持一致。"""
    if p_pos >= 0.66:
        return "high"
    if p_pos >= 0.33:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# 推理服务
# ---------------------------------------------------------------------------
class ZalizadehInferenceService:
    """单例：进程内只加载一次 joblib + 一次原始 CSV 元数据。"""

    _instance: Optional["ZalizadehInferenceService"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded = False
        self._load_error: Optional[str] = None
        self._bundle: Optional[Dict[str, Any]] = None
        self._raw_columns: List[str] = []
        self._raw_medians: Dict[str, float] = {}
        self._loaded_at: Optional[str] = None

    # ------------------------------------------------------------------ #
    # 单例
    # ------------------------------------------------------------------ #
    @classmethod
    def get_instance(cls) -> "ZalizadehInferenceService":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------ #
    # 资源路径
    # ------------------------------------------------------------------ #
    @property
    def model_path(self) -> Path:
        return Path(settings.MODELS_DIR) / MODEL_FILE

    @property
    def raw_csv_path(self) -> Path:
        return Path(settings.UPLOAD_DIR) / RAW_FEATURES_CSV

    # ------------------------------------------------------------------ #
    # 加载
    # ------------------------------------------------------------------ #
    def _ensure_loaded(self) -> bool:
        """懒加载 bundle + 原始 CSV 元数据。失败时只记录错误，不抛出。"""
        if self._loaded:
            return True
        with self._lock:
            if self._loaded:
                return True
            try:
                if not self.model_path.exists():
                    self._load_error = f"模型文件不存在: {self.model_path}"
                    logger.warning(self._load_error)
                    return False

                bundle = joblib.load(self.model_path)
                if not isinstance(bundle, dict) or "model" not in bundle:
                    self._load_error = "joblib 加载结果格式异常（缺少 model 键）"
                    logger.error(self._load_error)
                    return False

                self._bundle = bundle

                # 读取原始 CSV 计算列顺序与中位数（用于缺失字段兜底）
                if self.raw_csv_path.exists():
                    df = pd.read_csv(self.raw_csv_path)
                    self._raw_columns = list(df.columns)
                    self._raw_medians = {
                        c: float(df[c].median())
                        for c in df.columns
                        if pd.api.types.is_numeric_dtype(df[c])
                    }
                else:
                    logger.warning(
                        f"未找到原始训练 CSV {self.raw_csv_path}，缺失字段将按 0 处理"
                    )
                    self._raw_columns = []
                    self._raw_medians = {}

                self._loaded = True
                self._loaded_at = datetime.now().isoformat(timespec="seconds")
                logger.info(
                    f"[ZalizadehInference] 模型加载完成: "
                    f"{bundle.get('metadata', {}).get('best_model', 'unknown')}, "
                    f"特征数={len(bundle.get('feature_names', []))}, "
                    f"阈值={bundle.get('threshold', 0.5):.3f}"
                )
                return True
            except Exception as e:
                self._load_error = f"加载 zalizadeh_best.joblib 失败: {type(e).__name__}: {e}"
                logger.error(self._load_error, exc_info=True)
                return False

    # ------------------------------------------------------------------ #
    # 元数据
    # ------------------------------------------------------------------ #
    def is_available(self) -> bool:
        return self._ensure_loaded()

    def get_metadata(self) -> Dict[str, Any]:
        ok = self._ensure_loaded()
        if not ok:
            return {
                "available": False,
                "error": self._load_error,
                "model_path": str(self.model_path),
            }
        meta = dict(self._bundle.get("metadata", {}))
        return {
            "available": True,
            "model_path": str(self.model_path),
            "loaded_at": self._loaded_at,
            "best_model": meta.get("best_model"),
            "best_auc": meta.get("best_auc"),
            "best_accuracy": meta.get("best_accuracy"),
            "best_sensitivity": meta.get("best_sensitivity"),
            "best_specificity": meta.get("best_specificity"),
            "dataset": meta.get("dataset"),
            "n_features_engineered": len(self._bundle.get("feature_names", [])),
            "threshold": float(self._bundle.get("threshold", 0.5)),
            "raw_columns_count": len(self._raw_columns),
        }

    def get_schema(self) -> Dict[str, Any]:
        """返回前端表单渲染所需的字段元信息。"""
        ok = self._ensure_loaded()
        if not ok:
            return {"available": False, "error": self._load_error, "fields": []}

        # 优先用 CSV 顺序；否则退化为 RAW_FIELD_META 的键序
        order = self._raw_columns or list(RAW_FIELD_META.keys())

        clinical_fields: List[Dict[str, Any]] = []
        binary_fields: List[Dict[str, Any]] = []
        for col in order:
            if col in RAW_FIELD_META:
                meta = dict(RAW_FIELD_META[col])
                meta["name"] = col
                meta["default"] = self._raw_medians.get(col)
                clinical_fields.append(meta)
            elif "_" in col and (col.endswith("_Y") or col.endswith("_N") or col.endswith("_Female") or col.endswith("_Male")):
                # one-hot 衍生列：合并展示
                binary_fields.append({"name": col, "type": "binary", "default": self._raw_medians.get(col, 0)})
            else:
                # 兜底
                binary_fields.append({"name": col, "type": "number", "default": self._raw_medians.get(col, 0)})

        return {
            "available": True,
            "fields": clinical_fields,
            "raw_one_hot_fields": binary_fields,
            "engineered_feature_names": list(self._bundle.get("feature_names", [])),
        }

    # ------------------------------------------------------------------ #
    # 预测核心
    # ------------------------------------------------------------------ #
    def _build_engineered_row(self, raw: Dict[str, Any]) -> pd.DataFrame:
        """把单条原始字典转成训练时同等结构的 1 行 DataFrame。"""
        # 1. 用原始列序构建一行；缺失用中位数（数值列）或 0（其它）
        if self._raw_columns:
            row = {}
            for c in self._raw_columns:
                if c in raw and raw[c] is not None and raw[c] != "":
                    row[c] = raw[c]
                elif c in self._raw_medians:
                    row[c] = self._raw_medians[c]
                else:
                    row[c] = 0
        else:
            # 无 CSV 兜底场景：直接照传
            row = dict(raw)

        df = pd.DataFrame([row])

        # 2. 数值化：尽可能 to_numeric，失败置 NaN
        for c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        # 3. 缺失再用中位数补一遍（防止前端把数字传成字符串）
        for c, med in self._raw_medians.items():
            if c in df.columns:
                df[c] = df[c].fillna(med)
        df = df.fillna(0)

        # 4. 特征工程
        df_eng = _add_engineered_features(df)
        df_eng = df_eng.fillna(0)

        return df_eng

    def _align_to_feature_names(self, df_eng: pd.DataFrame) -> np.ndarray:
        feature_names: List[str] = list(self._bundle["feature_names"])
        df_aligned = df_eng.reindex(columns=feature_names, fill_value=0.0)
        return df_aligned.values.astype(np.float64)

    def predict_one(self, raw_features: Dict[str, Any]) -> Dict[str, Any]:
        """单样本预测。``raw_features`` 是 ``RAW_FIELD_META`` 中的字段字典。"""
        if not self._ensure_loaded():
            raise RuntimeError(self._load_error or "模型未加载")
        if not isinstance(raw_features, dict):
            raise ValueError("raw_features 必须是 dict")

        df_eng = self._build_engineered_row(raw_features)
        X = self._align_to_feature_names(df_eng)

        scaler = self._bundle.get("scaler")
        if scaler is not None:
            X = scaler.transform(X)

        model = self._bundle["model"]
        proba_arr = model.predict_proba(X)[0]
        # 兼容二分类 [neg, pos]
        p_pos = float(proba_arr[1]) if len(proba_arr) > 1 else float(proba_arr[0])
        threshold = float(self._bundle.get("threshold", 0.5))
        prediction = 1 if p_pos >= threshold else 0
        confidence = float(max(proba_arr.tolist()))

        return {
            "prediction": int(prediction),
            "probability": [float(1 - p_pos), float(p_pos)],
            "p_positive": p_pos,
            "confidence": confidence,
            "threshold": threshold,
            "risk_level": _risk_level_from_proba(p_pos),
            "model": self._bundle.get("metadata", {}).get("best_model", "RealCAD"),
        }

    def predict_batch(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量预测。直接复用单条接口（量级小、清晰优先于极致性能）。"""
        if not self._ensure_loaded():
            raise RuntimeError(self._load_error or "模型未加载")
        if not isinstance(rows, list) or not rows:
            raise ValueError("rows 必须是非空列表")
        if len(rows) > 5000:
            raise ValueError("单次最多 5000 条")
        return [self.predict_one(r) for r in rows]


def get_zalizadeh_inference_service() -> ZalizadehInferenceService:
    """FastAPI 依赖注入入口。"""
    return ZalizadehInferenceService.get_instance()
