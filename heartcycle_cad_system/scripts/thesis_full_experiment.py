"""
论文实验完整复现脚本（thesis_full_experiment.py）。

目标：
1. 在 data/cad_dataset_10k.csv 上完成与论文一致的 70/15/15 分层划分；
2. 训练 LR / RF / XGBoost / LightGBM / CNN / LSTM 6 个模型；
3. 5 折分层交叉验证统计 AUC（均值 ± 标准差）；
4. 生成 ROC 曲线对比图、最佳模型混淆矩阵热力图、SHAP 全局特征重要性 Top10；
5. 输出 Markdown / JSON / PNG 结果文件，便于直接写入毕业论文。

运行：
    cd heartcycle_cad_system
    python scripts/thesis_full_experiment.py
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import lightgbm as lgb
from imblearn.over_sampling import SMOTE

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "cad_dataset_10k.csv"
OUT_DIR = ROOT / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_JSON = OUT_DIR / "thesis_full_experiment.json"
OUT_MD = OUT_DIR / "thesis_full_experiment.md"
OUT_ROC = OUT_DIR / "thesis_roc_curves.png"
OUT_CM = OUT_DIR / "thesis_confusion_matrix.png"
OUT_SHAP_BAR = OUT_DIR / "thesis_shap_top.png"
OUT_FEATURE_TABLE = OUT_DIR / "thesis_feature_importance.csv"

RANDOM_STATE = 42

CHINESE_LABEL = {
    "age": "年龄",
    "gender_male": "性别(男)",
    "height_cm": "身高",
    "weight_kg": "体重",
    "bmi": "BMI",
    "sbp": "收缩压",
    "dbp": "舒张压",
    "heart_rate": "心率",
    "respiratory_rate": "呼吸频率",
    "temperature": "体温",
    "cholesterol": "总胆固醇",
    "ldl": "LDL-C",
    "hdl": "HDL-C",
    "triglycerides": "甘油三酯",
    "glucose": "空腹血糖",
    "hba1c": "糖化血红蛋白",
    "creatinine": "肌酐",
    "uric_acid": "尿酸",
    "crp": "C反应蛋白",
    "homocysteine": "同型半胱氨酸",
    "sdnn": "SDNN",
    "rmssd": "RMSSD",
    "pnn50": "pNN50",
    "sdsd": "SDSD",
    "lf_power": "LF功率",
    "hf_power": "HF功率",
    "lf_hf_ratio": "LF/HF",
    "vlf_power": "VLF功率",
    "total_power": "总功率",
    "sd1": "SD1",
    "sd2": "SD2",
    "sd1_sd2_ratio": "SD1/SD2",
    "sample_entropy": "样本熵",
    "approximate_entropy": "近似熵",
    "dfa_alpha1": "DFA α1",
    "dfa_alpha2": "DFA α2",
    "smoking_status": "吸烟状态",
    "alcohol_status": "饮酒状态",
    "exercise_frequency": "运动频率",
    "diabetes_history": "糖尿病史",
    "hypertension_history": "高血压史",
    "family_history": "家族史",
}


@dataclass
class Row:
    model: str
    accuracy: float
    sensitivity: float
    specificity: float
    precision: float
    f1: float
    auc: float
    cv_auc_mean: float
    cv_auc_std: float
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
        X[idx_train], X[idx_val], X[idx_test],
        y_train, y_val, y_test,
    )


def preprocess(X_train, X_val, X_test):
    imp = SimpleImputer(strategy="median")
    X_tr_i = imp.fit_transform(X_train)
    X_va_i = imp.transform(X_val)
    X_te_i = imp.transform(X_test)
    sc = StandardScaler()
    X_tr = sc.fit_transform(X_tr_i)
    X_va = sc.transform(X_va_i)
    X_te = sc.transform(X_te_i)
    return X_tr, X_va, X_te


def smote_train(X_tr, y_tr):
    sm = SMOTE(random_state=RANDOM_STATE)
    return sm.fit_resample(X_tr, y_tr)


def metrics(y_true, y_pred, y_score):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    spec = tn / (tn + fp) if (tn + fp) else 0.0
    sens = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "sensitivity": float(sens),
        "specificity": float(spec),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "auc": float(roc_auc_score(y_true, y_score)),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def make_sk_models():
    return {
        "Logistic Regression": LogisticRegression(
            max_iter=2000, random_state=RANDOM_STATE, class_weight="balanced"
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, max_depth=15, class_weight="balanced",
            random_state=RANDOM_STATE, n_jobs=-1,
        ),
        "XGBoost": xgb.XGBClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            objective="binary:logistic", eval_metric="auc",
            random_state=RANDOM_STATE, n_jobs=-1, verbosity=0,
        ),
        "LightGBM": lgb.LGBMClassifier(
            n_estimators=300, learning_rate=0.05, num_leaves=31,
            subsample=0.8, colsample_bytree=0.8,
            class_weight="balanced", objective="binary",
            random_state=RANDOM_STATE, n_jobs=-1, verbosity=-1,
        ),
    }


def cv_auc_sk(name, X, y, n_splits=5):
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    aucs = []
    for tr_idx, va_idx in skf.split(X, y):
        Xt, Xv = X[tr_idx], X[va_idx]
        yt, yv = y[tr_idx], y[va_idx]
        Xt2, yt2 = smote_train(Xt, yt)
        clf = make_sk_models()[name]
        clf.fit(Xt2, yt2)
        proba = clf.predict_proba(Xv)[:, 1]
        aucs.append(roc_auc_score(yv, proba))
    return float(np.mean(aucs)), float(np.std(aucs))


def train_sklearn(X_train, y_train, X_test, y_test, X_full_for_cv, y_full_for_cv):
    rows: List[Row] = []
    proba_dict: Dict[str, np.ndarray] = {}
    cm_dict: Dict[str, Dict[str, int]] = {}

    Xs, ys = smote_train(X_train, y_train)
    for name, model in make_sk_models().items():
        model.fit(Xs, ys)
        proba = model.predict_proba(X_test)[:, 1]
        y_pred = (proba >= 0.5).astype(int)
        m = metrics(y_test, y_pred, proba)
        cv_mean, cv_std = cv_auc_sk(name, X_full_for_cv, y_full_for_cv)
        rows.append(Row(
            model=name,
            accuracy=m["accuracy"], sensitivity=m["sensitivity"],
            specificity=m["specificity"], precision=m["precision"],
            f1=m["f1"], auc=m["auc"],
            cv_auc_mean=cv_mean, cv_auc_std=cv_std,
            notes="SMOTE only on train; threshold=0.5",
        ))
        proba_dict[name] = proba
        cm_dict[name] = {k: m[k] for k in ("tn", "fp", "fn", "tp")}
        print(f"  [OK] {name:20s} acc={m['accuracy']:.4f} auc={m['auc']:.4f} (5CV-AUC={cv_mean:.4f}±{cv_std:.4f})")
    return rows, proba_dict, cm_dict


def train_tf_model(model_type, X_train, y_train, X_val, y_val, X_test, y_test, epochs=50):
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, models, callbacks
    from tensorflow.keras.utils import to_categorical

    tf.random.set_seed(RANDOM_STATE)
    np.random.seed(RANDOM_STATE)

    Xs, ys = smote_train(X_train, y_train)

    def to3d(X2d):
        return X2d.reshape(X2d.shape[0], X2d.shape[1], 1).astype("float32")

    Xt, Xv, Xe = to3d(Xs), to3d(X_val), to3d(X_test)
    y_tr = to_categorical(ys, 2)
    y_va = to_categorical(y_val, 2)
    y_te_oh = to_categorical(y_test, 2)

    n_steps, n_feat = Xt.shape[1], Xt.shape[2]

    if model_type == "cnn":
        mdl = models.Sequential([
            layers.Input(shape=(n_steps, n_feat)),
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
        ])
    else:
        mdl = models.Sequential([
            layers.Input(shape=(n_steps, n_feat)),
            layers.LSTM(64, return_sequences=False),
            layers.Dropout(0.3),
            layers.Dense(32, activation="relu"),
            layers.Dense(2, activation="softmax"),
        ])

    mdl.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy", keras.metrics.AUC(name="auc")],
    )
    es = callbacks.EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True, verbose=0)
    mdl.fit(Xt, y_tr, validation_data=(Xv, y_va), epochs=epochs, batch_size=64, callbacks=[es], verbose=0)
    proba = mdl.predict(Xe, verbose=0)[:, 1]
    y_pred = (proba >= 0.5).astype(int)
    m = metrics(y_test, y_pred, proba)
    print(f"  [OK] {model_type.upper():20s} acc={m['accuracy']:.4f} auc={m['auc']:.4f}")
    return m, proba


def shap_top_features(X_train, y_train, X_test, feature_names, top_k=10):
    import shap
    Xs, ys = smote_train(X_train, y_train)
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=15, class_weight="balanced",
        random_state=RANDOM_STATE, n_jobs=-1,
    )
    rf.fit(Xs, ys)
    bg = shap.sample(Xs, 800, random_state=RANDOM_STATE)
    explainer = shap.TreeExplainer(rf, data=bg)
    sv = explainer.shap_values(X_test[:500])
    if isinstance(sv, list):
        sv = sv[1]
    mean_abs = np.mean(np.abs(sv), axis=0)
    total = float(mean_abs.sum()) or 1.0
    order = np.argsort(-mean_abs)
    rows = []
    for rank, i in enumerate(order, 1):
        f_en = feature_names[int(i)]
        rows.append({
            "rank": rank,
            "feature_en": f_en,
            "feature_zh": CHINESE_LABEL.get(f_en, f_en),
            "mean_abs_shap": float(mean_abs[i]),
            "share": float(mean_abs[i] / total),
        })
    return rows[:top_k], rows  # top_k for paper, full for CSV


def plot_roc(proba_dict, y_test, out_path):
    plt.figure(figsize=(8, 6))
    for name, proba in proba_dict.items():
        fpr, tpr, _ = roc_curve(y_test, proba)
        auc_v = roc_auc_score(y_test, proba)
        plt.plot(fpr, tpr, label=f"{name} (AUC={auc_v:.3f})", linewidth=2)
    plt.plot([0, 1], [0, 1], "k--", linewidth=1)
    plt.xlabel("False Positive Rate (1 - Specificity)", fontsize=12)
    plt.ylabel("True Positive Rate (Sensitivity)", fontsize=12)
    plt.title("ROC Curves on Held-out Test Set", fontsize=13)
    plt.legend(loc="lower right", fontsize=10)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def plot_cm(cm_data, model_name, out_path):
    cm = np.array([[cm_data["tn"], cm_data["fp"]],
                   [cm_data["fn"], cm_data["tp"]]])
    plt.figure(figsize=(6, 5))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=["Pred Negative", "Pred Positive"],
        yticklabels=["True Negative", "True Positive"],
        cbar=True, annot_kws={"size": 14},
    )
    plt.title(f"Confusion Matrix - {model_name}", fontsize=13)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def plot_shap_bar(shap_top, out_path):
    feats = [r["feature_zh"] for r in shap_top][::-1]
    shares = [100 * r["share"] for r in shap_top][::-1]
    plt.figure(figsize=(8, 6))
    bars = plt.barh(feats, shares, color=plt.cm.viridis(np.linspace(0.2, 0.9, len(feats))))
    for bar, val in zip(bars, shares):
        plt.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                 f"{val:.2f}%", va="center", fontsize=9)
    plt.xlabel("相对贡献占比 (%)", fontsize=11)
    plt.title("SHAP 全局特征重要性 (Top 10) - 随机森林", fontsize=12)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def main():
    print("=" * 70)
    print("HeartCycle 论文实验 - 全模型复现")
    print("=" * 70)

    if not CSV_PATH.is_file():
        print(f"ERROR: missing dataset {CSV_PATH}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(CSV_PATH)
    if "CAD_risk" not in df.columns:
        print("ERROR: column CAD_risk required", file=sys.stderr)
        sys.exit(1)

    y = df["CAD_risk"].astype(int).values
    X_df = df.drop(columns=["CAD_risk"])
    feature_names = X_df.columns.tolist()
    X = X_df.values.astype(float)

    print(f"\n[Data] samples={len(y)}, features={X.shape[1]}, "
          f"pos_ratio={y.mean():.3f}, missing_total={int(df.isna().sum().sum())}")

    X_train, X_val, X_test, y_train, y_val, y_test = stratified_three_way(X, y)
    print(f"[Split] train={len(y_train)}, val={len(y_val)}, test={len(y_test)}")

    # preprocess: median imputer + standard scaler (fit on train only)
    X_tr_p, X_val_p, X_te_p = preprocess(X_train, X_val, X_test)
    # for CV, use the entire train+val pool (after preprocessing fit on train+val combined)
    X_pool = np.vstack([X_train, X_val])
    y_pool = np.concatenate([y_train, y_val])
    imp = SimpleImputer(strategy="median").fit(X_pool)
    X_pool_i = imp.transform(X_pool)
    sc = StandardScaler().fit(X_pool_i)
    X_pool_s = sc.transform(X_pool_i)

    print("\n[Train Sklearn / Boosting Models]")
    rows, proba_dict, cm_dict = train_sklearn(
        X_tr_p, y_train, X_te_p, y_test, X_pool_s, y_pool
    )

    print("\n[Train Deep Learning Models]")
    cnn_m, cnn_proba = train_tf_model("cnn", X_tr_p, y_train, X_val_p, y_val, X_te_p, y_test)
    lstm_m, lstm_proba = train_tf_model("lstm", X_tr_p, y_train, X_val_p, y_val, X_te_p, y_test)
    rows.append(Row(
        model="CNN",
        accuracy=cnn_m["accuracy"], sensitivity=cnn_m["sensitivity"],
        specificity=cnn_m["specificity"], precision=cnn_m["precision"],
        f1=cnn_m["f1"], auc=cnn_m["auc"],
        cv_auc_mean=float("nan"), cv_auc_std=float("nan"),
        notes="1D-CNN over 42 features as length-T sequence",
    ))
    rows.append(Row(
        model="LSTM",
        accuracy=lstm_m["accuracy"], sensitivity=lstm_m["sensitivity"],
        specificity=lstm_m["specificity"], precision=lstm_m["precision"],
        f1=lstm_m["f1"], auc=lstm_m["auc"],
        cv_auc_mean=float("nan"), cv_auc_std=float("nan"),
        notes="LSTM over 42 features as length-T sequence",
    ))
    proba_dict["CNN"] = cnn_proba
    proba_dict["LSTM"] = lstm_proba
    cm_dict["CNN"] = {"tn": cnn_m["tn"], "fp": cnn_m["fp"], "fn": cnn_m["fn"], "tp": cnn_m["tp"]}
    cm_dict["LSTM"] = {"tn": lstm_m["tn"], "fp": lstm_m["fp"], "fn": lstm_m["fn"], "tp": lstm_m["tp"]}

    print("\n[SHAP Analysis - top 10 features]")
    shap_top, shap_full = shap_top_features(X_tr_p, y_train, X_te_p, feature_names)

    # Identify best model by AUC
    best = max(rows, key=lambda r: r.auc)
    print(f"\n[BEST] {best.model}: AUC={best.auc:.4f}, Acc={best.accuracy:.4f}")

    # Generate plots
    print("\n[Plots]")
    plot_roc(proba_dict, y_test, OUT_ROC)
    print(f"  ROC curves saved -> {OUT_ROC}")
    plot_cm(cm_dict[best.model], best.model, OUT_CM)
    print(f"  Confusion matrix ({best.model}) -> {OUT_CM}")
    try:
        plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
        plt.rcParams["axes.unicode_minus"] = False
        plot_shap_bar(shap_top, OUT_SHAP_BAR)
        print(f"  SHAP bar -> {OUT_SHAP_BAR}")
    except Exception as e:
        print(f"  SHAP plot failed: {e}")

    pd.DataFrame(shap_full).to_csv(OUT_FEATURE_TABLE, index=False, encoding="utf-8-sig")
    print(f"  Full importance table -> {OUT_FEATURE_TABLE}")

    # Save outputs
    payload = {
        "meta": {
            "csv": str(CSV_PATH),
            "n_total": int(len(y)),
            "n_features": int(X.shape[1]),
            "pos_count": int(y.sum()),
            "neg_count": int(len(y) - y.sum()),
            "missing_total": int(df.isna().sum().sum()),
            "split_train_val_test": [int(len(y_train)), int(len(y_val)), int(len(y_test))],
            "random_state": RANDOM_STATE,
            "pipeline": "median imputer + standard scaler (fit on train); SMOTE on train only; threshold=0.5",
        },
        "metrics_test_set": [asdict(r) for r in rows],
        "confusion_matrices": cm_dict,
        "shap_top10": shap_top,
        "best_model": {
            "model": best.model, "auc": best.auc, "accuracy": best.accuracy,
            "sensitivity": best.sensitivity, "specificity": best.specificity,
            "precision": best.precision, "f1": best.f1,
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown
    lines = [
        "# 论文实验复现 - 真实结果",
        "",
        f"- 数据文件: `{CSV_PATH.name}`",
        f"- 样本总数: **{payload['meta']['n_total']}** （阳性={payload['meta']['pos_count']}，阴性={payload['meta']['neg_count']}，正样本占比={y.mean():.3f}）",
        f"- 特征维度: **{payload['meta']['n_features']}**（不含目标列）",
        f"- 缺失值总数: **{payload['meta']['missing_total']}**",
        f"- 划分: 训练 / 验证 / 测试 = {payload['meta']['split_train_val_test']}（7:1.5:1.5 分层）",
        f"- 随机种子: {RANDOM_STATE}",
        "",
        "## 1. 测试集模型性能对比",
        "",
        "| 模型 | 准确率 | 灵敏度 | 特异性 | 精确率 | F1 | AUC | 5折CV AUC |",
        "|------|--------|--------|--------|--------|----|-----|-----------|",
    ]
    for r in rows:
        cv = (
            f"{r.cv_auc_mean:.4f} ± {r.cv_auc_std:.4f}"
            if not np.isnan(r.cv_auc_mean) else "—"
        )
        lines.append(
            f"| {r.model} | {r.accuracy*100:.2f}% | {r.sensitivity*100:.2f}% | "
            f"{r.specificity*100:.2f}% | {r.precision*100:.2f}% | "
            f"{r.f1*100:.2f}% | {r.auc:.4f} | {cv} |"
        )
    lines += [
        "",
        f"**最佳模型**：{best.model}（AUC={best.auc:.4f}，Accuracy={best.accuracy*100:.2f}%）",
        "",
        f"## 2. 最佳模型 ({best.model}) 混淆矩阵",
        "",
        "|  | 预测 阴性 | 预测 阳性 |",
        "|---|---|---|",
        f"| 实际 阴性 | {cm_dict[best.model]['tn']} (TN) | {cm_dict[best.model]['fp']} (FP) |",
        f"| 实际 阳性 | {cm_dict[best.model]['fn']} (FN) | {cm_dict[best.model]['tp']} (TP) |",
        "",
        "## 3. SHAP 全局特征重要性 Top 10（基于随机森林）",
        "",
        "| 排名 | 特征 (English) | 特征 (中文) | mean &#124;SHAP&#124; | 相对占比 |",
        "|------|----------------|-------------|----------------------|----------|",
    ]
    for r in shap_top:
        lines.append(
            f"| {r['rank']} | {r['feature_en']} | {r['feature_zh']} | "
            f"{r['mean_abs_shap']:.6f} | {r['share']*100:.2f}% |"
        )
    lines += [
        "",
        f"完整数据：`{OUT_JSON.name}` | `{OUT_FEATURE_TABLE.name}`",
        f"图表：`{OUT_ROC.name}`、`{OUT_CM.name}`、`{OUT_SHAP_BAR.name}`",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print("\n[Done]")
    print(f"  Markdown: {OUT_MD}")
    print(f"  JSON:     {OUT_JSON}")


if __name__ == "__main__":
    main()
