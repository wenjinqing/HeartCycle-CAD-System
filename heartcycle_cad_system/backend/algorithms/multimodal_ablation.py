"""
多模态消融实验：固定 train/val/test 划分，对比多种结构/训练设置。
指标：验证集与测试集 AUC、F1（论文常用）。
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .multimodal_fusion import SPEC_HEIGHT, SPEC_WIDTH, build_multimodal_model

logger = logging.getLogger(__name__)

# 默认可跑的全集（顺序即建议写入论文表格的顺序）
DEFAULT_ABLATION_CONFIGS: List[str] = [
    "hrv_mlp",
    "cnn_stft",
    "cnn_dual",
    "mm_stft_concat",
    "mm_stft_interactive",
    "mm_dual_concat",
    "mm_dual_interactive",
]

CONFIG_DESCRIPTIONS_ZH: Dict[str, str] = {
    "hrv_mlp": "仅 HRV → MLP",
    "cnn_stft": "仅 STFT 单通道 → CNN",
    "cnn_dual": "仅 STFT+CWT 双通道 → CNN",
    "mm_stft_concat": "HRV + STFT，融合 concat",
    "mm_stft_interactive": "HRV + STFT，融合 interactive",
    "mm_dual_concat": "HRV + 双通道 CNN，融合 concat",
    "mm_dual_interactive": "HRV + 双通道 CNN，融合 interactive（balanced 权重）",
    "mm_dual_interactive_no_sw": "同上结构，不使用 sample_weight（对比用）",
}


def _build_hrv_mlp(n_features: int, num_classes: int, dropout_rate: float = 0.4):
    from tensorflow.keras import layers, Model

    inp = layers.Input(shape=(n_features,), name="hrv_only_in")
    x = layers.Dense(128, activation="relu")(inp)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(dropout_rate)(x)
    x = layers.Dense(64, activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(dropout_rate)(x)
    x = layers.Dense(32, activation="relu")(x)
    out = layers.Dense(num_classes, activation="softmax", name="out")(x)
    return Model(inputs=inp, outputs=out, name="HRV_MLP")


def _build_cnn_only(img_channels: int, num_classes: int, dropout_rate: float = 0.4):
    from tensorflow.keras import layers, Model

    img_channels = max(1, int(img_channels))
    inp = layers.Input(shape=(SPEC_HEIGHT, SPEC_WIDTH, img_channels), name="cnn_only_in")
    x = layers.Conv2D(32, (3, 3), activation="relu", padding="same")(inp)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.25)(x)
    x = layers.Conv2D(64, (3, 3), activation="relu", padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.25)(x)
    x = layers.Conv2D(128, (3, 3), activation="relu", padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(64, activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(dropout_rate)(x)
    out = layers.Dense(num_classes, activation="softmax", name="out")(x)
    return Model(inputs=inp, outputs=out, name="CNN_Only")


def _split_indices(
    y: np.ndarray,
    random_state: int,
    test_size: float,
    val_size: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    from sklearn.model_selection import train_test_split

    idx = np.arange(len(y))
    idx_tr, idx_te = train_test_split(
        idx, test_size=test_size, random_state=random_state, stratify=y
    )
    idx_tr, idx_va = train_test_split(
        idx_tr, test_size=val_size, random_state=random_state, stratify=y[idx_tr]
    )
    return idx_tr, idx_va, idx_te


def _metrics_from_proba(
    y_true: np.ndarray, proba: np.ndarray, num_classes: int
) -> Tuple[float, float]:
    from sklearn.metrics import f1_score, roc_auc_score

    pred = np.argmax(proba, axis=1)
    try:
        if num_classes == 2:
            auc = float(roc_auc_score(y_true, proba[:, 1]))
            f1 = float(f1_score(y_true, pred, average="binary", zero_division=0))
        else:
            auc = float(
                roc_auc_score(y_true, proba, multi_class="ovr", average="macro")
            )
            f1 = float(f1_score(y_true, pred, average="macro", zero_division=0))
    except Exception as e:
        logger.warning("指标计算降级: %s", e)
        auc = float("nan")
        f1 = float("nan")
    return auc, f1


def _sample_weights(y_int: np.ndarray, num_classes: int) -> np.ndarray:
    from sklearn.utils.class_weight import compute_class_weight

    classes = np.arange(num_classes)
    cw = compute_class_weight("balanced", classes=classes, y=y_int)
    return cw[y_int].astype(np.float32)


def _train_eval_one(
    model,
    fit_x,
    y_tr_oh: np.ndarray,
    val_x,
    y_va_oh: np.ndarray,
    te_x,
    y_te_oh: np.ndarray,
    y_va_int: np.ndarray,
    y_te_int: np.ndarray,
    num_classes: int,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    use_sample_weight: bool,
    random_state: int,
) -> Tuple[float, float, float, float]:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import callbacks

    tf.random.set_seed(random_state)
    optimizer = keras.optimizers.Adam(learning_rate=learning_rate)
    model.compile(
        optimizer=optimizer,
        loss="categorical_crossentropy",
        metrics=["accuracy", keras.metrics.AUC(name="auc")],
    )
    cb = [
        callbacks.EarlyStopping(
            monitor="val_auc",
            patience=8,
            restore_best_weights=True,
            mode="max",
            verbose=0,
        ),
        callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=4, min_lr=1e-7, verbose=0
        ),
    ]
    fit_kw: Dict[str, Any] = {
        "epochs": epochs,
        "batch_size": batch_size,
        "callbacks": cb,
        "verbose": 0,
    }
    if use_sample_weight:
        y_int = np.argmax(y_tr_oh, axis=1)
        fit_kw["sample_weight"] = _sample_weights(y_int, num_classes)

    model.fit(fit_x, y_tr_oh, validation_data=(val_x, y_va_oh), **fit_kw)

    p_va = model.predict(val_x, verbose=0)
    p_te = model.predict(te_x, verbose=0)
    v_auc, v_f1 = _metrics_from_proba(y_va_int, p_va, num_classes)
    t_auc, t_f1 = _metrics_from_proba(y_te_int, p_te, num_classes)
    return v_auc, v_f1, t_auc, t_f1


def run_multimodal_ablation(
    X_hrv: np.ndarray,
    X_img_stft: np.ndarray,
    X_img_dual: np.ndarray,
    y: np.ndarray,
    *,
    random_state: int = 42,
    test_size: float = 0.2,
    val_size: float = 0.2,
    epochs: int = 25,
    batch_size: int = 16,
    learning_rate: float = 0.001,
    configs: Optional[List[str]] = None,
    include_sample_weight_ablation: bool = True,
) -> Dict[str, Any]:
    """
    在同一划分下依次训练多种配置并返回指标（不保存权重，仅消融表）。
    """
    import tensorflow as tf
    from sklearn.preprocessing import StandardScaler
    from tensorflow.keras.utils import to_categorical

    y = np.asarray(y, dtype=np.int32).ravel()
    N = len(y)
    if N < 6:
        raise ValueError(f"样本过少（{N}），无法分层划分")

    num_classes = int(len(np.unique(y)))
    if num_classes < 2:
        raise ValueError("标签至少需要 2 个类别")

    cfg_list = list(configs) if configs else list(DEFAULT_ABLATION_CONFIGS)
    allowed = set(DEFAULT_ABLATION_CONFIGS) | {"mm_dual_interactive_no_sw"}
    for c in cfg_list:
        if c not in allowed:
            raise ValueError(f"未知消融配置: {c}，允许: {sorted(allowed)}")

    idx_tr, idx_va, idx_te = _split_indices(y, random_state, test_size, val_size)

    scaler = StandardScaler()
    Xh = X_hrv.astype(np.float32)
    Xh_tr = scaler.fit_transform(Xh[idx_tr])
    Xh_va = scaler.transform(Xh[idx_va])
    Xh_te = scaler.transform(Xh[idx_te])

    Xs_tr, Xs_va, Xs_te = X_img_stft[idx_tr], X_img_stft[idx_va], X_img_stft[idx_te]
    Xd_tr, Xd_va, Xd_te = X_img_dual[idx_tr], X_img_dual[idx_va], X_img_dual[idx_te]

    y_tr = to_categorical(y[idx_tr], num_classes=num_classes)
    y_va = to_categorical(y[idx_va], num_classes=num_classes)
    y_te = to_categorical(y[idx_te], num_classes=num_classes)
    y_va_i, y_te_i = y[idx_va], y[idx_te]

    n_feat = Xh_tr.shape[1]
    rows: List[Dict[str, Any]] = []

    seen: set = set()
    run_list: List[str] = []
    for c in cfg_list:
        if c not in seen:
            seen.add(c)
            run_list.append(c)
    if include_sample_weight_ablation and "mm_dual_interactive" in run_list:
        if "mm_dual_interactive_no_sw" not in run_list:
            run_list.append("mm_dual_interactive_no_sw")

    for config_id in run_list:
        use_sw = config_id != "mm_dual_interactive_no_sw"

        desc = CONFIG_DESCRIPTIONS_ZH.get(config_id, config_id)
        t0 = time.perf_counter()
        tf.keras.backend.clear_session()
        m = None

        try:
            if config_id == "hrv_mlp":
                m = _build_hrv_mlp(n_feat, num_classes)
                v_auc, v_f1, t_auc, t_f1 = _train_eval_one(
                    m,
                    Xh_tr,
                    y_tr,
                    Xh_va,
                    y_va,
                    Xh_te,
                    y_te,
                    y_va_i,
                    y_te_i,
                    num_classes,
                    epochs,
                    batch_size,
                    learning_rate,
                    use_sw,
                    random_state,
                )
            elif config_id == "cnn_stft":
                m = _build_cnn_only(1, num_classes)
                v_auc, v_f1, t_auc, t_f1 = _train_eval_one(
                    m,
                    Xs_tr,
                    y_tr,
                    Xs_va,
                    y_va,
                    Xs_te,
                    y_te,
                    y_va_i,
                    y_te_i,
                    num_classes,
                    epochs,
                    batch_size,
                    learning_rate,
                    use_sw,
                    random_state,
                )
            elif config_id == "cnn_dual":
                m = _build_cnn_only(2, num_classes)
                v_auc, v_f1, t_auc, t_f1 = _train_eval_one(
                    m,
                    Xd_tr,
                    y_tr,
                    Xd_va,
                    y_va,
                    Xd_te,
                    y_te,
                    y_va_i,
                    y_te_i,
                    num_classes,
                    epochs,
                    batch_size,
                    learning_rate,
                    use_sw,
                    random_state,
                )
            elif config_id in (
                "mm_stft_concat",
                "mm_stft_interactive",
                "mm_dual_concat",
                "mm_dual_interactive",
                "mm_dual_interactive_no_sw",
            ):
                fusion = (
                    "interactive"
                    if "interactive" in config_id
                    else "concat"
                )
                img_ch = 1 if "stft" in config_id and "dual" not in config_id else 2
                img_tr, img_va, img_te = (
                    (Xs_tr, Xs_va, Xs_te) if img_ch == 1 else (Xd_tr, Xd_va, Xd_te)
                )
                m = build_multimodal_model(
                    n_hrv_features=n_feat,
                    num_classes=num_classes,
                    img_channels=img_ch,
                    fusion_mode=fusion,
                )
                v_auc, v_f1, t_auc, t_f1 = _train_eval_one(
                    m,
                    [Xh_tr, img_tr],
                    y_tr,
                    [Xh_va, img_va],
                    y_va,
                    [Xh_te, img_te],
                    y_te,
                    y_va_i,
                    y_te_i,
                    num_classes,
                    epochs,
                    batch_size,
                    learning_rate,
                    use_sw,
                    random_state,
                )
            else:
                continue
        except Exception as e:
            logger.exception("消融配置 %s 失败", config_id)
            rows.append(
                {
                    "config_id": config_id,
                    "description_zh": desc,
                    "val_auc": None,
                    "val_f1": None,
                    "test_auc": None,
                    "test_f1": None,
                    "use_sample_weight": use_sw,
                    "seconds": round(time.perf_counter() - t0, 2),
                    "error": str(e),
                }
            )
            if m is not None:
                del m
            tf.keras.backend.clear_session()
            continue

        del m
        tf.keras.backend.clear_session()

        rows.append(
            {
                "config_id": config_id,
                "description_zh": desc,
                "val_auc": round(v_auc, 6) if v_auc == v_auc else None,
                "val_f1": round(v_f1, 6) if v_f1 == v_f1 else None,
                "test_auc": round(t_auc, 6) if t_auc == t_auc else None,
                "test_f1": round(t_f1, 6) if t_f1 == t_f1 else None,
                "use_sample_weight": use_sw,
                "seconds": round(time.perf_counter() - t0, 2),
            }
        )

    md_lines = [
        "| 配置 | 验证 AUC | 验证 F1 | 测试 AUC | 测试 F1 | sample_weight |",
        "|------|----------|---------|----------|---------|---------------|",
    ]
    for r in rows:
        if r.get("error"):
            continue
        md_lines.append(
            f"| {r.get('description_zh', r['config_id'])} | {r.get('val_auc')} | "
            f"{r.get('val_f1')} | {r.get('test_auc')} | {r.get('test_f1')} | "
            f"{r.get('use_sample_weight')} |"
        )
    markdown_table = "\n".join(md_lines)

    return {
        "split": {
            "random_state": random_state,
            "test_size": test_size,
            "val_size": val_size,
            "n_total": N,
            "n_train": int(len(idx_tr)),
            "n_val": int(len(idx_va)),
            "n_test": int(len(idx_te)),
        },
        "num_classes": num_classes,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "rows": rows,
        "markdown_table": markdown_table,
    }
