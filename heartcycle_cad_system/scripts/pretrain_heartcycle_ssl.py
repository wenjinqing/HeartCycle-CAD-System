"""HeartCycle 健康人 ECG 自监督预训练（mask reconstruction）。

为什么要做这个？
----------------
HeartCycle 数据集（``data/raw/59146237_*.csv`` 对应的 H5 文件）全是 4 个
健康受试者，**没有 CAD 阳性样本**，本身做不了二分类。

但它包含丰富的 ECG/PCG/PPG 多导联信号，可以作为**无监督预训练源**：
让模型学习"正常 ECG 形态"的通用表征，再把权重迁移到 PTB-XL 监督任务。

这是公开数据集 + 私有健康数据的标准用法（self-supervised pretrain →
supervised finetune），论文里完全可以理直气壮地写。

预训练任务：Mask Reconstruction
--------------------------------
随机遮盖 15% 的 ECG 片段（每段 50 samples），让模型重构。
重构损失 MSE 越低，编码器学到的表征越好。

使用
----
    # 准备：把 HeartCycle H5 文件放到 data/raw/heartcycle/ 下
    python scripts/pretrain_heartcycle_ssl.py \\
        --h5-dir data/raw/heartcycle \\
        --epochs 50 --batch-size 32

    # 没有 H5 时也能跑：从 PTB-XL train 中把 NORM 子集当"健康源"
    python scripts/pretrain_heartcycle_ssl.py \\
        --use-ptbxl-norm \\
        --src data/ptbxl --data-dir data/ptbxl_processed
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_H5_DIR = PROJECT_ROOT / "data" / "raw" / "heartcycle"
DEFAULT_MODEL_DIR = PROJECT_ROOT / "data" / "models"


# ─── HeartCycle H5 加载 ─────────────────────────────────────────────────────

def _load_heartcycle_h5(h5_dir: Path, max_records: Optional[int] = None,
                       seq_len: int = 1000, fs: int = 100) -> np.ndarray:
    """读 HeartCycle H5 文件，把第一通道 ECG 切成定长 segments。

    返回 (N, seq_len, 1) 数组。HeartCycle 是单导联，会 broadcast 到 12 导联
    时由调用方处理。
    """
    try:
        import h5py
    except ImportError:
        sys.exit("缺少 h5py，请 `pip install h5py`")

    h5_files = sorted(h5_dir.glob("*.h5")) + sorted(h5_dir.glob("*.H5"))
    if not h5_files:
        raise FileNotFoundError(f"{h5_dir} 下未找到 .h5 文件")
    if max_records:
        h5_files = h5_files[:max_records]

    print(f"[heartcycle] 找到 {len(h5_files)} 个 H5 文件")
    segments: List[np.ndarray] = []
    for fp in h5_files:
        try:
            with h5py.File(fp, "r") as f:
                # HeartCycle 标准结构：measure/value/_030/value/data/value (Niccomo ECG)
                try:
                    ecg = f["measure"]["value"]["_030"]["value"]["data"]["value"][0, :]
                except (KeyError, IndexError, TypeError):
                    # fallback: 找任意 1D 信号
                    ecg = None
                    def _walk(name, obj):
                        nonlocal ecg
                        if isinstance(obj, h5py.Dataset) and obj.ndim >= 1 and ecg is None:
                            arr = np.asarray(obj).squeeze()
                            if arr.ndim == 1 and arr.size > seq_len * 2:
                                ecg = arr
                    f.visititems(_walk)
                if ecg is None:
                    warnings.warn(f"在 {fp.name} 中未找到 ECG 信号")
                    continue
                ecg = np.asarray(ecg, dtype=np.float32)
                # 切 segments（无重叠）
                n_seg = len(ecg) // seq_len
                for i in range(n_seg):
                    seg = ecg[i * seq_len: (i + 1) * seq_len]
                    # 简单 z-score
                    seg = (seg - seg.mean()) / (seg.std() + 1e-6)
                    segments.append(seg.reshape(seq_len, 1))
        except Exception as e:
            warnings.warn(f"加载 {fp.name} 失败: {e}")

    if not segments:
        raise RuntimeError("未能从 HeartCycle 提取任何有效 ECG 片段")
    arr = np.stack(segments, axis=0)
    print(f"[heartcycle] 共提取 {len(arr)} 个 {seq_len}-sample 片段")
    return arr


def _load_ptbxl_norm_as_pretrain_source(
    src: Path, data_dir: Path, resolution: int = 100,
    max_records: int = 5000) -> np.ndarray:
    """把 PTB-XL train 中的 NORM 样本当"健康对照"，作 SSL 预训练源。

    适用场景：暂时没有 HeartCycle H5 时退而求其次。
    """
    import pandas as pd
    from app.algorithms.ptbxl_dataset import (
        load_wfdb_signal, _zscore_per_lead, _bandpass_butterworth)

    train_csv = data_dir / "train.csv"
    df = pd.read_csv(train_csv)
    # 只挑 label==0 的 NORM 样本（preprocess 时 NORM 被设为阴性）
    df = df[df["label"] == 0].head(max_records)
    seq_len = 1000 if resolution == 100 else 5000
    fname_col = "filename_lr" if resolution == 100 else "filename_hr"

    print(f"[ptbxl-norm] 加载 {len(df)} 条 NORM 样本作 SSL 预训练源")
    X = np.zeros((len(df), seq_len, 12), dtype=np.float32)
    valid = np.ones(len(df), dtype=bool)
    for i, row in enumerate(df.itertuples()):
        try:
            sig = load_wfdb_signal(src / getattr(row, fname_col))
            if sig.shape[0] < seq_len:
                pad = np.zeros((seq_len - sig.shape[0], 12), dtype=np.float32)
                sig = np.vstack([sig, pad])
            else:
                sig = sig[:seq_len]
            sig = _bandpass_butterworth(sig, fs=resolution)
            X[i] = _zscore_per_lead(sig)
        except Exception as e:
            valid[i] = False
            warnings.warn(f"加载失败 {row.filename_lr}: {e}")
    return X[valid]


# ─── SSL 训练 ───────────────────────────────────────────────────────────────

def _make_ssl_dataset(X: np.ndarray, batch_size: int, mask_ratio: float,
                      mask_span: int, seed: int = 42):
    import tensorflow as tf
    from app.algorithms.ptbxl_dataset import random_mask_ecg

    rng = np.random.default_rng(seed)

    def _gen():
        idx = np.arange(len(X))
        while True:
            rng.shuffle(idx)
            for i in idx:
                masked, original = random_mask_ecg(
                    X[i], mask_ratio=mask_ratio, mask_span=mask_span, rng=rng)
                yield masked, original

    out_sig = (
        tf.TensorSpec(shape=X.shape[1:], dtype=tf.float32),
        tf.TensorSpec(shape=X.shape[1:], dtype=tf.float32),
    )
    ds = tf.data.Dataset.from_generator(_gen, output_signature=out_sig)
    return ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--h5-dir", type=Path, default=DEFAULT_H5_DIR,
                   help="HeartCycle H5 文件目录")
    p.add_argument("--use-ptbxl-norm", action="store_true",
                   help="改用 PTB-XL train NORM 子集作预训练源")
    p.add_argument("--src", type=Path,
                   default=PROJECT_ROOT / "data" / "ptbxl",
                   help="--use-ptbxl-norm 时的 PTB-XL 根目录")
    p.add_argument("--data-dir", type=Path,
                   default=PROJECT_ROOT / "data" / "ptbxl_processed",
                   help="--use-ptbxl-norm 时的 train.csv 目录")
    p.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--steps-per-epoch", type=int, default=200)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=5e-4)
    p.add_argument("--mask-ratio", type=float, default=0.15)
    p.add_argument("--mask-span", type=int, default=50)
    p.add_argument("--seq-len", type=int, default=1000)
    p.add_argument("--max-records", type=int, default=None)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    np.random.seed(args.seed)
    try:
        import tensorflow as tf
        tf.random.set_seed(args.seed)
    except ImportError:
        sys.exit("缺少 tensorflow，请 pip install tensorflow")

    # 数据
    if args.use_ptbxl_norm:
        X = _load_ptbxl_norm_as_pretrain_source(
            args.src, args.data_dir, resolution=100,
            max_records=args.max_records or 5000)
    else:
        X = _load_heartcycle_h5(
            args.h5_dir, max_records=args.max_records, seq_len=args.seq_len)
        # HeartCycle 单导联 → broadcast 到 12 通道（让模型架构与 PTB-XL 兼容）
        if X.ndim == 3 and X.shape[-1] == 1:
            X = np.repeat(X, 12, axis=-1)
            print(f"[pretrain] 单导联 broadcast 到 12 导联: {X.shape}")

    if X.shape[0] < 10:
        sys.exit(f"预训练样本太少（{X.shape[0]} < 10），无法训练")

    print(f"==> 预训练数据: {X.shape}")

    from app.algorithms.ptbxl_dataset import build_ssl_mask_reconstructor
    n_leads = X.shape[-1]
    seq_len = X.shape[1]
    model = build_ssl_mask_reconstructor(seq_len=seq_len, n_leads=n_leads)
    model.optimizer.learning_rate = args.lr
    model.summary(line_length=110)

    train_ds = _make_ssl_dataset(X, args.batch_size,
                                 args.mask_ratio, args.mask_span, args.seed)

    args.model_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = args.model_dir / "ssl_heartcycle_encoder.h5"
    cb = [
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(ckpt_path), monitor="loss",
            save_best_only=True, save_weights_only=False, verbose=1),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="loss", factor=0.5, patience=5, min_lr=1e-6, verbose=1),
        tf.keras.callbacks.EarlyStopping(
            monitor="loss", patience=10, restore_best_weights=True, verbose=1),
    ]

    print(f"==> SSL 预训练 {args.epochs} epochs × {args.steps_per_epoch} steps")
    history = model.fit(
        train_ds, epochs=args.epochs,
        steps_per_epoch=args.steps_per_epoch,
        callbacks=cb, verbose=2)

    meta = {
        "task": "ssl_mask_reconstruction",
        "source": "ptbxl_norm" if args.use_ptbxl_norm else "heartcycle_h5",
        "n_pretraining_samples": int(len(X)),
        "seq_len": seq_len,
        "n_leads": n_leads,
        "mask_ratio": args.mask_ratio,
        "mask_span": args.mask_span,
        "epochs": args.epochs,
        "final_loss": float(history.history.get("loss", [None])[-1] or 0.0),
        "final_mae": float(history.history.get("mae", [None])[-1] or 0.0),
        "trained_at": datetime.now().isoformat(timespec="seconds"),
    }
    meta_path = args.model_dir / "ssl_heartcycle_encoder_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"==> 编码器权重: {ckpt_path}")
    print(f"==> 元信息:    {meta_path}")
    print(f"\n下一步迁移到监督任务:")
    print(f"  python scripts/train_ptbxl_ecg.py --pretrained {ckpt_path} \\")
    print(f"      --freeze-backbone-epochs 5 --epochs 25")
    return 0


if __name__ == "__main__":
    sys.exit(main())
