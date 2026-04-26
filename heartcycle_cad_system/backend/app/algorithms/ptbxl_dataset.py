"""PTB-XL ECG 数据加载与 1D-ResNet 模型定义（TensorFlow/Keras）。

设计原则
--------
- 与项目现有 deep_learning.py / multimodal_fusion.py 保持同栈（TF 2.x）
- 内存受限友好：用 tf.data 流式读取 WFDB，不一次性加载 21k 条
- 只读 12 导联 100 Hz（每条 1000 × 12 = 12000 float32，≈ 48 KB）
  - 默认整批 21k 条 ≈ 1 GB，可放进内存；500 Hz 太大，必要时再用流式
- 模型：1D-ResNet18（Strodthoff et al. 2021 在 PTB-XL 上 SOTA 之一）

使用
----
    from app.algorithms.ptbxl_dataset import (
        load_ptbxl_split, build_ecg_resnet1d, get_dataset_signature)

    train_ds = load_ptbxl_split("data/ptbxl_processed/train.csv",
                                src="data/ptbxl",
                                resolution=100, batch_size=64)
    model = build_ecg_resnet1d(seq_len=1000, n_leads=12, n_classes=1)
    model.fit(train_ds, ...)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ─── WFDB 加载工具 ──────────────────────────────────────────────────────────

def load_wfdb_signal(record_path: str | Path) -> np.ndarray:
    """读取一条 WFDB 记录，返回 (T, 12) float32 数组。

    Parameters
    ----------
    record_path:
        WFDB 记录路径（不含扩展名），如 ``data/ptbxl/records100/00000/00001_lr``
    """
    try:
        import wfdb  # type: ignore
    except ImportError:
        raise ImportError(
            "需要 wfdb 库读取 PTB-XL，请 `pip install wfdb`")
    rec = wfdb.rdsamp(str(record_path))
    sig = np.asarray(rec[0], dtype=np.float32)  # (T, n_leads)
    return sig


def _zscore_per_lead(sig: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """按导联做 z-score（消除增益差异，PTB-XL 论文标准做法）。"""
    mean = sig.mean(axis=0, keepdims=True)
    std = sig.std(axis=0, keepdims=True)
    return ((sig - mean) / (std + eps)).astype(np.float32)


def _bandpass_butterworth(sig: np.ndarray, fs: int = 100,
                          low: float = 0.5, high: float = 40.0,
                          order: int = 3) -> np.ndarray:
    """3 阶 Butterworth 带通滤波，去基线漂移和肌电高频。"""
    from scipy.signal import butter, filtfilt
    nyq = fs / 2.0
    b, a = butter(order, [low / nyq, high / nyq], btype="band")
    out = np.zeros_like(sig)
    for c in range(sig.shape[1]):
        out[:, c] = filtfilt(b, a, sig[:, c])
    return out.astype(np.float32)


# ─── tf.data 管线 ───────────────────────────────────────────────────────────

def load_ptbxl_split(
    split_csv: str | Path,
    src: str | Path,
    resolution: int = 100,
    batch_size: int = 64,
    shuffle: bool = True,
    bandpass: bool = True,
    cache_in_memory: bool = True,
    max_records: Optional[int] = None,
):
    """构造 tf.data.Dataset。

    Parameters
    ----------
    split_csv:
        ``train.csv`` / ``val.csv`` / ``test.csv``，由 preprocess_ptbxl.py 产出
    src:
        PTB-XL 根目录（含 records100/ records500/）
    resolution:
        100 或 500 Hz
    batch_size:
        批大小
    shuffle:
        是否打乱（仅 train 设 True）
    bandpass:
        是否做 0.5-40 Hz 带通滤波（推荐 True）
    cache_in_memory:
        True 时一次性加载并缓存（21k × 12000 ≈ 1 GB，足够 RAM 时建议开）
    max_records:
        调试时限制条数，None 表示不限
    """
    import tensorflow as tf

    df = pd.read_csv(split_csv)
    if max_records:
        df = df.head(max_records)

    src = Path(src)
    fname_col = "filename_lr" if resolution == 100 else "filename_hr"
    seq_len = 1000 if resolution == 100 else 5000

    if cache_in_memory:
        logger.info(f"[ptbxl] 一次性加载 {len(df)} 条到内存 ({resolution} Hz)")
        X = np.zeros((len(df), seq_len, 12), dtype=np.float32)
        y = np.zeros(len(df), dtype=np.float32)
        valid = np.ones(len(df), dtype=bool)
        for i, row in enumerate(df.itertuples()):
            rec_path = src / getattr(row, fname_col)
            try:
                sig = load_wfdb_signal(rec_path)
                if sig.shape[0] < seq_len:
                    pad = np.zeros((seq_len - sig.shape[0], 12), dtype=np.float32)
                    sig = np.vstack([sig, pad])
                else:
                    sig = sig[:seq_len]
                if sig.shape[1] != 12:
                    valid[i] = False
                    continue
                if bandpass:
                    sig = _bandpass_butterworth(sig, fs=resolution)
                X[i] = _zscore_per_lead(sig)
                y[i] = float(row.label)
            except Exception as e:
                logger.warning(f"加载失败 {rec_path}: {e}")
                valid[i] = False
        X = X[valid]
        y = y[valid]
        logger.info(f"[ptbxl] 实际加载 {valid.sum()}/{len(df)} 条")

        ds = tf.data.Dataset.from_tensor_slices((X, y))
        if shuffle:
            ds = ds.shuffle(buffer_size=min(8192, len(X)), reshuffle_each_iteration=True)
        ds = ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
        ds.cardinality_hint = (valid.sum() + batch_size - 1) // batch_size  # type: ignore
        ds.n_samples = int(valid.sum())  # type: ignore
        ds.n_pos = int(y.sum())  # type: ignore
        return ds

    # 流式版本（暂未实现，500 Hz 大数据时启用）
    raise NotImplementedError(
        "流式 tf.data.Dataset.from_generator 版本待添加；"
        "对 100 Hz 21k 数据 cache_in_memory=True 已足够")


def get_dataset_signature(resolution: int = 100) -> dict:
    """返回数据集形状元信息，供模型构建用。"""
    seq_len = 1000 if resolution == 100 else 5000
    return {
        "seq_len": seq_len,
        "n_leads": 12,
        "fs": resolution,
        "n_classes": 1,  # 二分类用 sigmoid + BCE
    }


# ─── HuggingFace parquet 直读分支（与 download_ptbxl.py --mode hf 配套） ────

# BLOSSOM-framework/PTB-XL 的 5 类原始 label 索引
HF_LABEL_NAMES = ["NORM", "MI", "STTC", "CD", "HYP"]


def _binarize_hf_label(label_idx: int, strategy: str) -> int:
    """把 BLOSSOM 5 类 label 转成二分类。

    Parameters
    ----------
    label_idx:
        原始 5 类索引（0=NORM, 1=MI, 2=STTC, 3=CD, 4=HYP）
    strategy:
        - ``mi_vs_norm`` : NORM→0, MI→1, 其它→-1（丢弃）
        - ``cad_vs_norm``: NORM→0, MI/STTC/CD→1, HYP→-1
        - ``abnormal_vs_norm`` : NORM→0, 其它任何→1
    """
    if strategy == "mi_vs_norm":
        if label_idx == 0:
            return 0
        if label_idx == 1:
            return 1
        return -1
    if strategy == "cad_vs_norm":
        if label_idx == 0:
            return 0
        if label_idx in (1, 2, 3):  # MI / STTC / CD
            return 1
        return -1  # HYP 单独丢
    if strategy == "abnormal_vs_norm":
        return 0 if label_idx == 0 else 1
    raise ValueError(f"未知 strategy: {strategy}")


def load_ptbxl_split_hf(
    hf_data_dir: str | Path,
    split: str = "train",
    label_strategy: str = "mi_vs_norm",
    batch_size: int = 64,
    shuffle: bool = True,
    bandpass: bool = False,  # parquet 数据已 z-score 处理，默认关
    max_records: Optional[int] = None,
    val_ratio: float = 0.1,
    seed: int = 42,
):
    """从 ``download_ptbxl.py --mode hf`` 下载的 parquet 数据加载训练集。

    BLOSSOM-framework/PTB-XL 的 schema（已 100 Hz/10s 切片好）::

        i_to_avf : float32 (1000, 6)  ← I, II, III, aVR, aVL, aVF
        v1_to_v6 : float32 (1000, 6)  ← V1, V2, V3, V4, V5, V6
        label    : 5 类 ClassLabel
        site_id  : str
        split    : str  ← 'train' / 'val' / 'test' ；某些版本只有 'train'

    若 parquet 中 split 列只有 ``train``，按 ``site_id`` 与 ``val_ratio`` 切分。

    Parameters
    ----------
    hf_data_dir:
        HF 下载目录（含 ``data/*.parquet``），即 ``download_ptbxl.py --mode hf`` 的 dest
    split:
        ``train`` / ``val`` / ``test``
    label_strategy:
        见 :func:`_binarize_hf_label`
    batch_size, shuffle, max_records:
        与 :func:`load_ptbxl_split` 一致
    bandpass:
        是否在加载后再做带通滤波（parquet 中数据已归一化，默认 False）
    val_ratio:
        当 parquet 没有 val/test 列时，从 train 切出做验证 + 测试的比例
    """
    import tensorflow as tf

    hf_dir = Path(hf_data_dir)
    parquet_files = sorted((hf_dir / "data").glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(
            f"未在 {hf_dir/'data'} 找到 *.parquet 文件。"
            "请先 `python scripts/download_ptbxl.py --mode hf`。")

    logger.info(f"[ptbxl-hf] 发现 {len(parquet_files)} 个 parquet 文件")

    # 用 datasets 库加载（能自动还原 Array2D 类型）
    try:
        from datasets import load_dataset, Features, Array2D, ClassLabel, Value
    except ImportError:
        raise ImportError(
            "需要 datasets 库读取 HF parquet，请 `pip install datasets`")

    features = Features({
        "i_to_avf": Array2D(shape=(1000, 6), dtype="float32"),
        "v1_to_v6": Array2D(shape=(1000, 6), dtype="float32"),
        "label": ClassLabel(names=HF_LABEL_NAMES),
        "site_id": Value("string"),
        "split": Value("string"),
    })

    ds_raw = load_dataset(
        "parquet",
        data_files=[str(p) for p in parquet_files],
        features=features,
        split="train",  # 这里的 'train' 是 datasets 库的拼接概念，与 PTB-XL split 列无关
    )

    # 按 PTB-XL 自带 split 列过滤
    available_splits = set(ds_raw.unique("split"))
    logger.info(f"[ptbxl-hf] parquet 中 split 列取值: {available_splits}")

    if split in available_splits:
        ds_split = ds_raw.filter(lambda r: r["split"] == split)
    else:
        # 没有原生 split 列时，用 site_id 哈希切：稳定可复现
        logger.info(f"[ptbxl-hf] parquet 无 '{split}' split，按 site_id 哈希切分")
        rng = np.random.default_rng(seed)
        # site_id → 桶（0..9）
        unique_sites = sorted(ds_raw.unique("site_id"))
        bucket = {sid: int(rng.integers(0, 10)) for sid in unique_sites}
        # 0..7 → train, 8 → val, 9 → test
        if split == "train":
            keep = lambda r: bucket[r["site_id"]] < 8
        elif split == "val":
            keep = lambda r: bucket[r["site_id"]] == 8
        elif split == "test":
            keep = lambda r: bucket[r["site_id"]] == 9
        else:
            raise ValueError(f"未知 split: {split}")
        ds_split = ds_raw.filter(keep)

    logger.info(f"[ptbxl-hf] split={split} 过滤后剩 {len(ds_split)} 条")

    # 二值化 label，丢掉 -1
    binarized = []
    for idx, ex in enumerate(ds_split):
        y = _binarize_hf_label(int(ex["label"]), label_strategy)
        if y < 0:
            continue
        binarized.append((idx, y))
        if max_records and len(binarized) >= max_records:
            break

    if not binarized:
        raise RuntimeError(
            f"[ptbxl-hf] 标签策略 '{label_strategy}' 在 split={split} "
            "下没有保留任何样本，请换 strategy 或 split")

    logger.info(f"[ptbxl-hf] 应用 label_strategy={label_strategy}：保留 {len(binarized)} 条")

    n = len(binarized)
    X = np.zeros((n, 1000, 12), dtype=np.float32)
    y = np.zeros(n, dtype=np.float32)
    for j, (idx, lbl) in enumerate(binarized):
        ex = ds_split[idx]
        # (1000, 6) + (1000, 6) → (1000, 12)
        sig = np.concatenate(
            [np.asarray(ex["i_to_avf"], dtype=np.float32),
             np.asarray(ex["v1_to_v6"], dtype=np.float32)],
            axis=1,
        )
        if sig.shape != (1000, 12):
            logger.warning(f"[ptbxl-hf] 跳过 shape={sig.shape} 的样本")
            continue
        if bandpass:
            sig = _bandpass_butterworth(sig, fs=100)
        X[j] = _zscore_per_lead(sig)
        y[j] = float(lbl)

    n_pos = int(y.sum())
    logger.info(
        f"[ptbxl-hf] 加载完成 split={split}: {n} 条, 正样本 {n_pos} ({n_pos/n:.1%})")

    ds = tf.data.Dataset.from_tensor_slices((X, y))
    if shuffle:
        ds = ds.shuffle(buffer_size=min(8192, n), reshuffle_each_iteration=True)
    ds = ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    ds.cardinality_hint = (n + batch_size - 1) // batch_size  # type: ignore
    ds.n_samples = n  # type: ignore
    ds.n_pos = n_pos  # type: ignore
    return ds


# ─── 1D-ResNet 模型 ─────────────────────────────────────────────────────────

def _resnet_block(x, filters: int, kernel: int = 7,
                  stride: int = 1, name: str = ""):
    """ResNet 基础块：Conv-BN-ReLU-Conv-BN + skip。"""
    import tensorflow as tf
    from tensorflow.keras import layers

    shortcut = x
    if stride != 1 or x.shape[-1] != filters:
        shortcut = layers.Conv1D(filters, 1, strides=stride,
                                 padding="same", name=f"{name}_shortcut")(shortcut)
        shortcut = layers.BatchNormalization(name=f"{name}_shortcut_bn")(shortcut)

    x = layers.Conv1D(filters, kernel, strides=stride,
                      padding="same", name=f"{name}_conv1")(x)
    x = layers.BatchNormalization(name=f"{name}_bn1")(x)
    x = layers.ReLU(name=f"{name}_relu1")(x)
    x = layers.Conv1D(filters, kernel, strides=1,
                      padding="same", name=f"{name}_conv2")(x)
    x = layers.BatchNormalization(name=f"{name}_bn2")(x)

    x = layers.Add(name=f"{name}_add")([x, shortcut])
    x = layers.ReLU(name=f"{name}_relu2")(x)
    return x


def build_ecg_resnet1d(
    seq_len: int = 1000,
    n_leads: int = 12,
    n_classes: int = 1,
    base_filters: int = 64,
    n_blocks: int = 4,
    dropout: float = 0.3,
    return_embedding: bool = False,
):
    """1D-ResNet for ECG（PTB-XL benchmark 标配架构之一）。

    架构
    ----
        Input(seq_len, n_leads)
        Conv1D(64, 15, /2) → BN → ReLU → MaxPool(2)
        4× ResBlock (64→128→256→512), 每个 stride=2
        GlobalAvgPool1D → Dropout → Dense(n_classes)

    参考
    ----
    Strodthoff et al., "Deep learning for ECG analysis", JBHI 2021.
    """
    import tensorflow as tf
    from tensorflow.keras import layers, Model

    inputs = layers.Input(shape=(seq_len, n_leads), name="ecg_input")

    x = layers.Conv1D(base_filters, 15, strides=2, padding="same",
                      name="stem_conv")(inputs)
    x = layers.BatchNormalization(name="stem_bn")(x)
    x = layers.ReLU(name="stem_relu")(x)
    x = layers.MaxPool1D(pool_size=2, strides=2, padding="same",
                         name="stem_pool")(x)

    filters_seq = [base_filters * (2 ** i) for i in range(n_blocks)]
    for i, filt in enumerate(filters_seq):
        stride = 1 if i == 0 else 2
        x = _resnet_block(x, filt, stride=stride, name=f"block{i+1}")

    embedding = layers.GlobalAveragePooling1D(name="embedding")(x)
    x = layers.Dropout(dropout, name="dropout")(embedding)

    if n_classes == 1:
        output = layers.Dense(1, activation="sigmoid", name="output")(x)
        loss = "binary_crossentropy"
    else:
        output = layers.Dense(n_classes, activation="softmax", name="output")(x)
        loss = "sparse_categorical_crossentropy"

    if return_embedding:
        return Model(inputs=inputs, outputs=[output, embedding], name="ECG_ResNet1D")
    model = Model(inputs=inputs, outputs=output, name="ECG_ResNet1D")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss=loss,
        metrics=[
            tf.keras.metrics.AUC(name="auc"),
            tf.keras.metrics.BinaryAccuracy(name="acc"),
            tf.keras.metrics.Recall(name="sensitivity"),
            tf.keras.metrics.Precision(name="precision"),
        ],
    )
    return model


# ─── 自监督头（mask reconstruction） ────────────────────────────────────────

def build_ssl_mask_reconstructor(seq_len: int = 1000, n_leads: int = 12,
                                 base_filters: int = 64):
    """自监督预训练头：随机掩盖 ECG 片段，让模型重构。

    用于 HeartCycle 健康人 ECG 预训练，得到通用 ECG 表征，
    再迁移到 PTB-XL CAD 监督任务。

    架构: Encoder (1D-ResNet 主干) → Decoder (转置卷积) → 重构信号
    """
    import tensorflow as tf
    from tensorflow.keras import layers, Model

    inputs = layers.Input(shape=(seq_len, n_leads), name="ecg_masked")

    # Encoder = 缩减版 ResNet（3 次 stride=2，长度缩 8 倍）
    x = layers.Conv1D(base_filters, 15, strides=1, padding="same")(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)

    for i in range(3):
        filt = base_filters * (2 ** i)
        x = _resnet_block(x, filt, stride=2, name=f"enc{i+1}")

    # Decoder: 3 次转置卷积，对称还原长度
    for i, filt in enumerate(reversed([base_filters * (2 ** k) for k in range(3)])):
        x = layers.Conv1DTranspose(filt, 7, strides=2, padding="same")(x)
        x = layers.BatchNormalization()(x)
        x = layers.ReLU()(x)

    output = layers.Conv1D(n_leads, 1, padding="same", activation="linear",
                           name="reconstructed")(x)
    # 输入长度不被 8 整除时，裁剪/填充对齐
    output_len = output.shape[1]
    if output_len is not None and output_len != seq_len:
        if output_len > seq_len:
            output = layers.Cropping1D(
                ((output_len - seq_len) // 2,
                 output_len - seq_len - (output_len - seq_len) // 2),
                name="recon_crop")(output)
        else:
            pad = seq_len - output_len
            output = layers.ZeroPadding1D(
                (pad // 2, pad - pad // 2),
                name="recon_pad")(output)

    model = Model(inputs=inputs, outputs=output, name="ECG_MaskRecon")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=5e-4),
        loss="mse",
        metrics=["mae"],
    )
    return model


def random_mask_ecg(sig: np.ndarray, mask_ratio: float = 0.15,
                    mask_span: int = 50,
                    rng: Optional[np.random.Generator] = None) -> Tuple[np.ndarray, np.ndarray]:
    """随机掩盖 ECG 片段，返回 (masked_signal, original_signal)。"""
    if rng is None:
        rng = np.random.default_rng()
    masked = sig.copy()
    T, _ = sig.shape
    n_spans = max(1, int((T * mask_ratio) // mask_span))
    starts = rng.integers(0, T - mask_span, size=n_spans)
    for s in starts:
        masked[s:s + mask_span] = 0.0
    return masked, sig
