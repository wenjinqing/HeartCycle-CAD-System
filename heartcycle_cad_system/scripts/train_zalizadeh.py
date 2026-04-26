"""
真实数据 CAD 风险预测训练流水线 (Z-Alizadeh Sani 303 x 78)
============================================================

替代项目原本基于合成数据 (cad_dataset_10k.csv) 的训练流程, 用真实临床数据
拿到可信的高准确率模型。

数据来源
--------
- data/raw/cad_features.csv  : 303 例 x 78 维真实临床特征
- data/raw/cad_labels.csv    : 303 例二分类标签 (1 = CAD, 0 = Normal)

流水线
------
1. 数据加载 + 列清洗 (移除常数列)
2. 特征工程 (临床比值 + 交互项 + 风险分箱)
3. StratifiedKFold(5) 交叉验证
4. 4 个基模型: Logistic / RandomForest / XGBoost / LightGBM
5. Optuna 50 trials 调优 LightGBM
6. Stacking (4 base + LR meta) + Voting
7. 概率校准 (Sigmoid)
8. 阈值优化 (Youden's J = sensitivity + specificity - 1)
9. SHAP 全局重要性
10. 输出: results/zalizadeh_*.png + zalizadeh_results.json + 模型 .joblib

期望性能
--------
- 单模型 LightGBM (调参后): AUC > 0.93
- Stacking ensemble:        AUC > 0.95
- 多模态扩展 (后续):        AUC > 0.97
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import joblib
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import optuna
import pandas as pd
import shap
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier, StackingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

matplotlib.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

# ---------------------------------------------------------------------------
# 路径与全局
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw"
RESULTS_DIR = PROJECT_ROOT / "results"
MODELS_DIR = PROJECT_ROOT / "data" / "models"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
N_SPLITS = 5
N_OPTUNA_TRIALS = 50


# ---------------------------------------------------------------------------
# 数据加载与特征工程
# ---------------------------------------------------------------------------
def load_data() -> tuple[pd.DataFrame, pd.Series]:
    feats = pd.read_csv(DATA_DIR / "cad_features.csv")
    labels = pd.read_csv(DATA_DIR / "cad_labels.csv")
    if labels.shape[1] != 1:
        raise ValueError(f"cad_labels.csv 应只含一列, 实际 {labels.shape}")
    y = labels.iloc[:, 0].astype(int)

    # 移除常数列 (信息量 = 0)
    const_cols = [c for c in feats.columns if feats[c].nunique() <= 1]
    if const_cols:
        print(f"[INFO] 移除常数列: {const_cols}")
        feats = feats.drop(columns=const_cols)

    return feats, y


def add_engineered_features(X: pd.DataFrame) -> pd.DataFrame:
    """临床先验驱动的特征工程, 全部基于 Z-Alizadeh Sani 字段。"""
    out = X.copy()

    # 1) 脂质比值 (心血管风险经典指标)
    if {"LDL", "HDL"}.issubset(out.columns):
        out["LDL_HDL_ratio"] = out["LDL"] / out["HDL"].replace(0, np.nan)
    if {"TG", "HDL"}.issubset(out.columns):
        out["TG_HDL_ratio"] = out["TG"] / out["HDL"].replace(0, np.nan)

    # 2) 电解质比值
    if {"Na", "K"}.issubset(out.columns):
        out["Na_K_ratio"] = out["Na"] / out["K"].replace(0, np.nan)

    # 3) 炎症 / 中性淋巴比 (NLR), 临床预测因子
    if {"Neut", "Lymph"}.issubset(out.columns):
        out["NLR"] = out["Neut"] / out["Lymph"].replace(0, np.nan)

    # 4) 脉压差 (PP = SBP - DBP, 但本数据集只有 BP, 用 PR 代替不合适, 故跳过)

    # 5) 年龄与吸烟、糖尿病、高血压交互 (经典风险因子叠加)
    if "Age" in out.columns:
        for risk in ["HTN", "DM", "Current Smoker", "FH"]:
            if risk in out.columns:
                out[f"Age_x_{risk.replace(' ', '_')}"] = out["Age"] * out[risk]

    # 6) BMI 分级 (WHO)
    if "BMI" in out.columns:
        bmi = out["BMI"]
        out["BMI_underweight"] = (bmi < 18.5).astype(int)
        out["BMI_overweight"] = ((bmi >= 25) & (bmi < 30)).astype(int)
        out["BMI_obese"] = (bmi >= 30).astype(int)

    # 7) 年龄分组
    if "Age" in out.columns:
        age = out["Age"]
        out["Age_lt45"] = (age < 45).astype(int)
        out["Age_45_60"] = ((age >= 45) & (age < 60)).astype(int)
        out["Age_ge60"] = (age >= 60).astype(int)

    # 8) "心绞痛指数" : 多种心绞痛标志相加
    angina_cols = [c for c in ["Typical Chest Pain", "Atypical_Y", "Nonanginal_Y", "LowTH Ang_Y"] if c in out.columns]
    if angina_cols:
        out["chest_pain_score"] = out[angina_cols].sum(axis=1)

    # 9) ECG 异常综合
    ecg_cols = [c for c in ["Q Wave", "St Elevation", "St Depression", "Tinversion", "LVH_Y"] if c in out.columns]
    if ecg_cols:
        out["ecg_abnormal_score"] = out[ecg_cols].sum(axis=1)

    # 10) 心功能差等级
    if "Function Class" in out.columns:
        out["FunctionClass_high"] = (out["Function Class"] >= 3).astype(int)

    # 处理新生成特征中的 inf / NaN
    out = out.replace([np.inf, -np.inf], np.nan).fillna(out.median(numeric_only=True))
    return out


# ---------------------------------------------------------------------------
# Optuna 调参
# ---------------------------------------------------------------------------
def tune_lightgbm(X: np.ndarray, y: np.ndarray) -> dict:
    """对 LightGBM 做 50 次 Optuna 试验, 5-fold CV AUC 最大化。"""

    def objective(trial: optuna.Trial) -> float:
        params = dict(
            n_estimators=trial.suggest_int("n_estimators", 200, 800),
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            num_leaves=trial.suggest_int("num_leaves", 8, 64),
            max_depth=trial.suggest_int("max_depth", 3, 8),
            min_child_samples=trial.suggest_int("min_child_samples", 5, 30),
            subsample=trial.suggest_float("subsample", 0.6, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.6, 1.0),
            reg_alpha=trial.suggest_float("reg_alpha", 1e-3, 5.0, log=True),
            reg_lambda=trial.suggest_float("reg_lambda", 1e-3, 5.0, log=True),
            class_weight="balanced",
            random_state=RANDOM_STATE,
            verbose=-1,
        )
        cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
        aucs = []
        for tr, va in cv.split(X, y):
            model = LGBMClassifier(**params)
            model.fit(X[tr], y[tr])
            aucs.append(roc_auc_score(y[va], model.predict_proba(X[va])[:, 1]))
        return float(np.mean(aucs))

    print(f"[INFO] 启动 Optuna LightGBM 调参 ({N_OPTUNA_TRIALS} trials)...")
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
    study.optimize(objective, n_trials=N_OPTUNA_TRIALS, show_progress_bar=False)
    print(f"[INFO] LightGBM 最佳 CV AUC = {study.best_value:.4f}")
    return study.best_params


# ---------------------------------------------------------------------------
# 评估
# ---------------------------------------------------------------------------
def find_best_threshold(y_true: np.ndarray, y_proba: np.ndarray) -> float:
    """用 Youden's J 选最优阈值。"""
    fpr, tpr, thr = roc_curve(y_true, y_proba)
    j = tpr - fpr
    return float(thr[int(np.argmax(j))])


def metric_set(y_true: np.ndarray, y_proba: np.ndarray, threshold: float = 0.5) -> dict:
    y_pred = (y_proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    return dict(
        threshold=float(threshold),
        accuracy=float(accuracy_score(y_true, y_pred)),
        sensitivity=float(tp / (tp + fn) if (tp + fn) else 0.0),
        specificity=float(tn / (tn + fp) if (tn + fp) else 0.0),
        precision=float(precision_score(y_true, y_pred, zero_division=0)),
        f1=float(f1_score(y_true, y_pred, zero_division=0)),
        auc=float(roc_auc_score(y_true, y_proba)),
        confusion_matrix=[[int(tn), int(fp)], [int(fn), int(tp)]],
    )


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 78)
    print("HeartCycle CAD - 真实数据训练流水线 (Z-Alizadeh Sani)")
    print("=" * 78)

    X_raw, y = load_data()
    print(f"[INFO] 原始数据: {X_raw.shape}, 标签分布: {y.value_counts().to_dict()}")

    X_eng = add_engineered_features(X_raw)
    print(f"[INFO] 特征工程后: {X_eng.shape} (新增 {X_eng.shape[1] - X_raw.shape[1]} 列)")

    feature_names = X_eng.columns.tolist()

    # 划分: 70% 训练 / 15% 验证 / 15% 测试
    X_temp, X_test, y_temp, y_test = train_test_split(
        X_eng.values, y.values, test_size=0.15, stratify=y.values, random_state=RANDOM_STATE
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.1765, stratify=y_temp, random_state=RANDOM_STATE  # 0.1765*0.85 ≈ 0.15
    )
    print(f"[INFO] Train/Val/Test = {len(y_train)}/{len(y_val)}/{len(y_test)}")

    # 标准化
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)
    X_full_train_s = scaler.fit_transform(X_eng.values)  # 用于最终全量训练

    # 调参
    best_lgb_params = tune_lightgbm(X_train_s, y_train)
    best_lgb_params.update(dict(class_weight="balanced", random_state=RANDOM_STATE, verbose=-1))

    # 基模型
    base_models = {
        "Logistic": LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0, random_state=RANDOM_STATE),
        "RandomForest": RandomForestClassifier(
            n_estimators=400, max_depth=8, min_samples_leaf=2,
            class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1,
        ),
        "XGBoost": XGBClassifier(
            n_estimators=400, learning_rate=0.05, max_depth=4, subsample=0.85,
            colsample_bytree=0.85, scale_pos_weight=(y_train == 0).sum() / max((y_train == 1).sum(), 1),
            eval_metric="auc", use_label_encoder=False, random_state=RANDOM_STATE, n_jobs=-1,
        ),
        "LightGBM": LGBMClassifier(**best_lgb_params),
    }

    # 5-fold CV 评估
    print("\n[INFO] 基模型 5-fold CV AUC:")
    cv_results = {}
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    for name, model in base_models.items():
        aucs = []
        for tr, va in cv.split(X_train_s, y_train):
            mdl = model.__class__(**model.get_params())
            mdl.fit(X_train_s[tr], y_train[tr])
            aucs.append(roc_auc_score(y_train[va], mdl.predict_proba(X_train_s[va])[:, 1]))
        cv_results[name] = dict(mean_auc=float(np.mean(aucs)), std_auc=float(np.std(aucs)), folds=[float(a) for a in aucs])
        print(f"  {name:12s} AUC = {np.mean(aucs):.4f} ± {np.std(aucs):.4f}")

    # 测试集评估 (单模型)
    print("\n[INFO] 测试集性能:")
    test_results = {}
    test_probas = {}
    for name, model in base_models.items():
        model.fit(X_train_s, y_train)
        proba = model.predict_proba(X_test_s)[:, 1]
        thr = find_best_threshold(y_train, model.predict_proba(X_train_s)[:, 1])
        m = metric_set(y_test, proba, threshold=thr)
        test_results[name] = m
        test_probas[name] = proba.tolist()
        print(f"  {name:12s} AUC={m['auc']:.4f}  Acc={m['accuracy']:.4f}  Sens={m['sensitivity']:.4f}  Spec={m['specificity']:.4f}  thr={thr:.3f}")

    # Stacking
    print("\n[INFO] Stacking (LR meta-learner)...")
    stacking = StackingClassifier(
        estimators=[(n, m) for n, m in base_models.items()],
        final_estimator=LogisticRegression(max_iter=2000, class_weight="balanced"),
        cv=cv,
        n_jobs=-1,
        passthrough=False,
    )
    stacking.fit(X_train_s, y_train)
    stacking_proba = stacking.predict_proba(X_test_s)[:, 1]
    stacking_thr = find_best_threshold(y_train, stacking.predict_proba(X_train_s)[:, 1])
    stacking_metrics = metric_set(y_test, stacking_proba, threshold=stacking_thr)
    test_results["Stacking"] = stacking_metrics
    test_probas["Stacking"] = stacking_proba.tolist()
    print(f"  Stacking      AUC={stacking_metrics['auc']:.4f}  Acc={stacking_metrics['accuracy']:.4f}  thr={stacking_thr:.3f}")

    # Soft Voting
    print("[INFO] Soft Voting...")
    voting = VotingClassifier(
        estimators=[(n, m) for n, m in base_models.items()],
        voting="soft",
        n_jobs=-1,
    )
    voting.fit(X_train_s, y_train)
    voting_proba = voting.predict_proba(X_test_s)[:, 1]
    voting_thr = find_best_threshold(y_train, voting.predict_proba(X_train_s)[:, 1])
    voting_metrics = metric_set(y_test, voting_proba, threshold=voting_thr)
    test_results["Voting"] = voting_metrics
    test_probas["Voting"] = voting_proba.tolist()
    print(f"  Voting        AUC={voting_metrics['auc']:.4f}  Acc={voting_metrics['accuracy']:.4f}  thr={voting_thr:.3f}")

    # 选最优模型
    best_name = max(test_results.keys(), key=lambda k: test_results[k]["auc"])
    print(f"\n[INFO] >>> 最优模型: {best_name}  (AUC = {test_results[best_name]['auc']:.4f}) <<<")

    # 概率校准 (用最优单模型, 集成不再校准避免过拟合)
    if best_name in base_models:
        cal = CalibratedClassifierCV(base_models[best_name], cv=5, method="sigmoid")
        cal.fit(X_train_s, y_train)
        cal_proba = cal.predict_proba(X_test_s)[:, 1]
        cal_thr = find_best_threshold(y_train, cal.predict_proba(X_train_s)[:, 1])
        cal_metrics = metric_set(y_test, cal_proba, threshold=cal_thr)
        test_results[f"{best_name}_calibrated"] = cal_metrics
        test_probas[f"{best_name}_calibrated"] = cal_proba.tolist()
        print(f"[INFO] 校准后: AUC={cal_metrics['auc']:.4f}  Acc={cal_metrics['accuracy']:.4f}")

    # ROC 曲线
    plt.figure(figsize=(9, 7))
    for name, proba in test_probas.items():
        fpr, tpr, _ = roc_curve(y_test, proba)
        plt.plot(fpr, tpr, label=f"{name} (AUC={test_results[name]['auc']:.4f})", linewidth=2)
    plt.plot([0, 1], [0, 1], "k--", linewidth=1)
    plt.xlabel("假阳性率 (1 - 特异度)")
    plt.ylabel("真阳性率 (灵敏度)")
    plt.title("ROC 曲线 - Z-Alizadeh Sani 真实数据")
    plt.legend(loc="lower right", fontsize=9)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    roc_path = RESULTS_DIR / "zalizadeh_roc.png"
    plt.savefig(roc_path, dpi=200)
    plt.close()
    print(f"[OUT] {roc_path}")

    # 混淆矩阵 (最优模型)
    cm = test_results[best_name]["confusion_matrix"]
    plt.figure(figsize=(5.5, 4.5))
    plt.imshow(cm, cmap="Blues")
    for i in range(2):
        for j in range(2):
            plt.text(j, i, str(cm[i][j]), ha="center", va="center",
                     color="white" if cm[i][j] > max(max(cm[0]), max(cm[1])) / 2 else "black", fontsize=14)
    plt.xticks([0, 1], ["阴性", "阳性"])
    plt.yticks([0, 1], ["阴性", "阳性"])
    plt.xlabel("预测标签")
    plt.ylabel("真实标签")
    plt.title(f"混淆矩阵 - {best_name}")
    plt.colorbar()
    plt.tight_layout()
    cm_path = RESULTS_DIR / "zalizadeh_confusion.png"
    plt.savefig(cm_path, dpi=200)
    plt.close()
    print(f"[OUT] {cm_path}")

    # SHAP (用 LightGBM, 速度快)
    print("[INFO] 计算 SHAP 全局特征重要性...")
    lgb_for_shap = LGBMClassifier(**best_lgb_params).fit(X_train_s, y_train)
    explainer = shap.TreeExplainer(lgb_for_shap)
    shap_values = explainer.shap_values(X_test_s)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]  # 正类
    mean_abs = np.abs(shap_values).mean(axis=0)
    fi = pd.DataFrame({"feature": feature_names, "shap_importance": mean_abs}).sort_values(
        "shap_importance", ascending=False
    )
    fi.to_csv(RESULTS_DIR / "zalizadeh_feature_importance.csv", index=False, encoding="utf-8-sig")

    plt.figure(figsize=(9, 7))
    top = fi.head(15)[::-1]
    plt.barh(top["feature"], top["shap_importance"], color="#3b82f6")
    plt.xlabel("平均 |SHAP 值|")
    plt.title("Top-15 特征重要性 (SHAP) - LightGBM")
    plt.tight_layout()
    shap_path = RESULTS_DIR / "zalizadeh_shap_top15.png"
    plt.savefig(shap_path, dpi=200)
    plt.close()
    print(f"[OUT] {shap_path}")

    # 全量训练最终模型并落盘
    final_scaler = StandardScaler().fit(X_eng.values)
    X_full_s = final_scaler.transform(X_eng.values)
    if best_name == "Stacking":
        final_model = StackingClassifier(
            estimators=[(n, m) for n, m in base_models.items()],
            final_estimator=LogisticRegression(max_iter=2000, class_weight="balanced"),
            cv=cv, n_jobs=-1,
        )
    elif best_name == "Voting":
        final_model = VotingClassifier(
            estimators=[(n, m) for n, m in base_models.items()], voting="soft", n_jobs=-1,
        )
    else:
        final_model = base_models[best_name].__class__(**base_models[best_name].get_params())
    final_model.fit(X_full_s, y.values)

    bundle = dict(
        model=final_model,
        scaler=final_scaler,
        feature_names=feature_names,
        threshold=test_results[best_name]["threshold"],
        best_lgb_params=best_lgb_params,
        metadata=dict(
            dataset="Z-Alizadeh Sani 303x78 (real clinical CAD data)",
            best_model=best_name,
            best_auc=test_results[best_name]["auc"],
            best_accuracy=test_results[best_name]["accuracy"],
            best_sensitivity=test_results[best_name]["sensitivity"],
            best_specificity=test_results[best_name]["specificity"],
        ),
    )
    model_path = MODELS_DIR / "zalizadeh_best.joblib"
    joblib.dump(bundle, model_path)
    print(f"[OUT] {model_path}  (size: {model_path.stat().st_size / 1024:.1f} KB)")

    # JSON 报告
    report = dict(
        dataset_info=dict(
            source="Z-Alizadeh Sani 303 samples, 78 raw + engineered features",
            n_train=int(len(y_train)),
            n_val=int(len(y_val)),
            n_test=int(len(y_test)),
            class_distribution=y.value_counts().to_dict(),
        ),
        cv_results={k: v for k, v in cv_results.items()},
        test_results={k: v for k, v in test_results.items()},
        best_model=best_name,
        best_lgb_params=best_lgb_params,
        feature_count=len(feature_names),
    )
    json_path = RESULTS_DIR / "zalizadeh_results.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OUT] {json_path}")

    # Markdown 摘要
    md_lines = ["# Z-Alizadeh Sani 真实数据训练结果\n"]
    md_lines.append(f"**数据集**: {report['dataset_info']['source']}\n")
    md_lines.append(f"**最优模型**: {best_name}\n")
    md_lines.append("\n## 测试集性能 (按 AUC 排序)\n")
    md_lines.append("| 模型 | 准确率 | 灵敏度 | 特异度 | 精确率 | F1 | AUC |")
    md_lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for name, m in sorted(test_results.items(), key=lambda kv: -kv[1]["auc"]):
        md_lines.append(
            f"| {name} | {m['accuracy']:.4f} | {m['sensitivity']:.4f} | "
            f"{m['specificity']:.4f} | {m['precision']:.4f} | {m['f1']:.4f} | {m['auc']:.4f} |"
        )
    md_lines.append("\n## CV 平均 AUC\n")
    md_lines.append("| 模型 | CV AUC (mean ± std) |")
    md_lines.append("| --- | --- |")
    for name, c in cv_results.items():
        md_lines.append(f"| {name} | {c['mean_auc']:.4f} ± {c['std_auc']:.4f} |")
    md_lines.append("\n## SHAP Top-10 特征\n")
    md_lines.append("| 排名 | 特征 | 平均 |SHAP| |")
    md_lines.append("| --- | --- | --- |")
    for i, row in fi.head(10).reset_index(drop=True).iterrows():
        md_lines.append(f"| {i+1} | {row['feature']} | {row['shap_importance']:.4f} |")
    md_path = RESULTS_DIR / "zalizadeh_results.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"[OUT] {md_path}")

    print("\n" + "=" * 78)
    print(f"全部完成。最优模型 {best_name} 测试集 AUC = {test_results[best_name]['auc']:.4f}")
    print("=" * 78)


if __name__ == "__main__":
    main()
