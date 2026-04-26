"""
复现论文级指标：使用仓库内 data/cad_dataset_10k.csv，固定随机种子，
70% / 15% / 15% 分层划分；训练集上 Imputer+Scaler+SMOTE，测试集仅变换后评估。
输出 JSON + Markdown 表，便于写入论文（请说明数据来源为项目内置 CSV，非临床采集）。

运行（在 heartcycle_cad_system 目录）:
  python scripts/repro_thesis_metrics.py
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import lightgbm as lgb
from imblearn.over_sampling import SMOTE

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "cad_dataset_10k.csv"
OUT_JSON = ROOT / "results" / "thesis_metrics_repro.json"
OUT_MD = ROOT / "results" / "thesis_metrics_repro.md"

RANDOM_STATE = 42


@dataclass
class Row:
    model: str
    accuracy: float
    sensitivity: float  # recall (positive class)
    specificity: float
    precision: float
    auc: float
    notes: str = ""


def stratified_three_way(
    X: np.ndarray, y: np.ndarray, seed: int = RANDOM_STATE
) -> Tuple[np.ndarray, ...]:
    idx = np.arange(len(y))
    idx_rem, idx_test, y_rem, y_test = train_test_split(
        idx, y, test_size=0.15, stratify=y, random_state=seed
    )
    rel_val = 0.15 / 0.85
    idx_train, idx_val, y_train, y_val = train_test_split(
        idx_rem, y_rem, test_size=rel_val, stratify=y_rem, random_state=seed
    )
    return (
        X[idx_train],
        X[idx_val],
        X[idx_test],
        y_train,
        y_val,
        y_test,
    )


def preprocess_train_apply(
    X_train: np.ndarray,
    X_val: np.ndarray,
    X_test: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, SimpleImputer, StandardScaler]:
    imp = SimpleImputer(strategy="median")
    X_tr_i = imp.fit_transform(X_train)
    X_va_i = imp.transform(X_val)
    X_te_i = imp.transform(X_test)
    sc = StandardScaler()
    X_tr = sc.fit_transform(X_tr_i)
    X_va = sc.transform(X_va_i)
    X_te = sc.transform(X_te_i)
    return X_tr, X_va, X_te, imp, sc


def smote_train_only(X_tr: np.ndarray, y_tr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    sm = SMOTE(random_state=RANDOM_STATE)
    return sm.fit_resample(X_tr, y_tr)


def binary_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_score: np.ndarray) -> Dict[str, float]:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    sens = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    auc = float(roc_auc_score(y_true, y_score))
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "sensitivity": float(sens),
        "specificity": float(spec),
        "auc": auc,
    }


def train_sklearn_models(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> List[Row]:
    X_trs, y_trs = smote_train_only(X_train, y_train)
    rows: List[Row] = []

    configs = [
        (
            "lr",
            LogisticRegression(
                max_iter=2000,
                random_state=RANDOM_STATE,
                class_weight="balanced",
            ),
        ),
        (
            "rf",
            RandomForestClassifier(
                n_estimators=200,
                max_depth=15,
                class_weight="balanced",
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
        ),
        (
            "xgb",
            xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                objective="binary:logistic",
                eval_metric="auc",
                use_label_encoder=False,
                random_state=RANDOM_STATE,
                n_jobs=-1,
                verbosity=0,
            ),
        ),
        (
            "lgb",
            lgb.LGBMClassifier(
                n_estimators=200,
                learning_rate=0.05,
                num_leaves=31,
                subsample=0.8,
                colsample_bytree=0.8,
                class_weight="balanced",
                objective="binary",
                random_state=RANDOM_STATE,
                n_jobs=-1,
                verbosity=-1,
            ),
        ),
    ]

    for name, clf in configs:
        clf.fit(X_trs, y_trs)
        if hasattr(clf, "predict_proba"):
            proba = clf.predict_proba(X_test)[:, 1]
        else:
            proba = clf.decision_function(X_test)
        y_pred = (proba >= 0.5).astype(int)
        m = binary_metrics(y_test, y_pred, proba)
        rows.append(
            Row(
                model=name.upper(),
                accuracy=m["accuracy"],
                sensitivity=m["sensitivity"],
                specificity=m["specificity"],
                precision=m["precision"],
                auc=m["auc"],
                notes="Test set; SMOTE only on train",
            )
        )
    return rows


def train_tf_model(
    model_type: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    epochs: int = 40,
) -> Row:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, models, callbacks
    from tensorflow.keras.utils import to_categorical

    tf.random.set_seed(RANDOM_STATE)
    np.random.seed(RANDOM_STATE)

    def reshape3d(X2d: np.ndarray) -> np.ndarray:
        return X2d.reshape(X2d.shape[0], X2d.shape[1], 1).astype("float32")

    Xt, Xv, Xe = reshape3d(X_train), reshape3d(X_val), reshape3d(X_test)
    y_tr = to_categorical(y_train, 2)
    y_va = to_categorical(y_val, 2)
    y_te = to_categorical(y_test, 2)

    n_timesteps, n_feat = Xt.shape[1], Xt.shape[2]

    if model_type == "cnn":
        mdl = models.Sequential(
            [
                layers.Input(shape=(n_timesteps, n_feat)),
                layers.Conv1D(64, 5, activation="relu", padding="same"),
                layers.BatchNormalization(),
                layers.MaxPooling1D(2),
                layers.Dropout(0.25),
                layers.Conv1D(128, 3, activation="relu", padding="same"),
                layers.BatchNormalization(),
                layers.MaxPooling1D(2),
                layers.Dropout(0.25),
                layers.GlobalAveragePooling1D(),
                layers.Dense(64, activation="relu"),
                layers.Dropout(0.3),
                layers.Dense(2, activation="softmax"),
            ]
        )
    else:  # lstm
        mdl = models.Sequential(
            [
                layers.Input(shape=(n_timesteps, n_feat)),
                layers.LSTM(64, return_sequences=False),
                layers.Dropout(0.3),
                layers.Dense(32, activation="relu"),
                layers.Dense(2, activation="softmax"),
            ]
        )

    mdl.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy", keras.metrics.AUC(name="auc")],
    )
    es = callbacks.EarlyStopping(
        monitor="val_loss", patience=8, restore_best_weights=True, verbose=0
    )
    mdl.fit(
        Xt,
        y_tr,
        validation_data=(Xv, y_va),
        epochs=epochs,
        batch_size=64,
        callbacks=[es],
        verbose=0,
    )
    proba = mdl.predict(Xe, verbose=0)[:, 1]
    y_pred = (proba >= 0.5).astype(int)
    met = binary_metrics(y_test, y_pred, proba)
    return Row(
        model=model_type.upper(),
        accuracy=met["accuracy"],
        sensitivity=met["sensitivity"],
        specificity=met["specificity"],
        precision=met["precision"],
        auc=met["auc"],
        notes="Tabular features as length-T sequence (T=n_features, 1 channel); test set",
    )


def shap_top_features(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    feature_names: List[str],
    max_background: int = 800,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    try:
        import shap
    except ImportError:
        return [{"error": "shap not installed"}]

    X_trs, y_trs = smote_train_only(X_train, y_train)
    bg_n = min(max_background, X_trs.shape[0])
    bg = shap.sample(X_trs, bg_n, random_state=RANDOM_STATE)
    rf = RandomForestClassifier(
        n_estimators=120,
        max_depth=12,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    rf.fit(X_trs, y_trs)
    explainer = shap.TreeExplainer(rf, data=bg)
    sv = explainer.shap_values(X_test[: min(500, X_test.shape[0])])
    if isinstance(sv, list):
        sv = sv[1]
    mean_abs = np.mean(np.abs(sv), axis=0)
    order = np.argsort(-mean_abs)[:top_k]
    total = float(mean_abs.sum()) or 1.0
    out = []
    for i in order:
        out.append(
            {
                "feature": feature_names[int(i)],
                "mean_abs_shap": float(mean_abs[i]),
                "share_approx": float(mean_abs[i] / total),
            }
        )
    return out


def main() -> None:
    if not CSV_PATH.is_file():
        print(f"Missing dataset: {CSV_PATH}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(CSV_PATH)
    if "CAD_risk" not in df.columns:
        print("Expected column CAD_risk", file=sys.stderr)
        sys.exit(1)

    y = df["CAD_risk"].astype(int).values
    X_df = df.drop(columns=["CAD_risk"])
    feature_names = X_df.columns.tolist()
    X = X_df.values.astype(float)

    X_train, X_val, X_test, y_train, y_val, y_test = stratified_three_way(X, y)

    meta = {
        "csv": str(CSV_PATH),
        "n_total": int(len(y)),
        "n_features": int(X.shape[1]),
        "class_counts_total": {int(k): int(v) for k, v in zip(*np.unique(y, return_counts=True))},
        "split_train_val_test": [int(len(y_train)), int(len(y_val)), int(len(y_test))],
        "random_state": RANDOM_STATE,
        "pipeline": "median imputer + standard scaler (fit train); SMOTE only on train; metrics on held-out test",
    }

    X_train_p, X_val_p, X_test_p, _, _ = preprocess_train_apply(X_train, X_val, X_test)

    rows = train_sklearn_models(X_train_p, y_train, X_test_p, y_test)

    # TensorFlow models (tabular-as-sequence); may take 1–3 min each
    try:
        rows.append(train_tf_model("cnn", X_train_p, y_train, X_val_p, y_val, X_test_p, y_test, epochs=35))
        rows.append(train_tf_model("lstm", X_train_p, y_train, X_val_p, y_val, X_test_p, y_test, epochs=35))
    except Exception as e:
        rows.append(
            Row(
                model="CNN",
                accuracy=0.0,
                sensitivity=0.0,
                specificity=0.0,
                precision=0.0,
                auc=0.0,
                notes=f"failed: {e}",
            )
        )

    shap_rows = shap_top_features(X_train_p, y_train, X_test_p, feature_names)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": meta,
        "metrics_test_set": [asdict(r) for r in rows],
        "shap_mean_abs_rf_top10": shap_rows,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown table for thesis
    lines = [
        "# 复现实验指标（自动生成）",
        "",
        f"- 数据文件: `{meta['csv']}`",
        f"- 样本数: {meta['n_total']}，特征数: {meta['n_features']}",
        f"- 划分: 训练/验证/测试 = {meta['split_train_val_test']}",
        f"- 随机种子: {meta['random_state']}",
        "",
        "## 测试集指标",
        "",
        "| 模型 | 准确率 | 灵敏度 | 特异性 | 精确率 | AUC |",
        "|------|--------|--------|--------|--------|-----|",
    ]
    for r in rows:
        lines.append(
            f"| {r.model} | {r.accuracy:.4f} | {r.sensitivity:.4f} | {r.specificity:.4f} | {r.precision:.4f} | {r.auc:.4f} |"
        )
    lines += ["", "## SHAP（随机森林，测试子集）Top 特征（mean |SHAP|）", ""]
    for item in shap_rows:
        if "error" in item:
            lines.append(str(item))
        else:
            lines.append(
                f"- **{item['feature']}**: mean|SHAP|={item['mean_abs_shap']:.6f}, 相对份额≈{100*item['share_approx']:.2f}%"
            )
    lines += ["", f"JSON: `{OUT_JSON}`", ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
