"""在 PTB-XL 上训练 ECG-only CAD 检测模型（1D-ResNet）。

完整流程
--------
    download_ptbxl.py  →  preprocess_ptbxl.py  →  本脚本  →  推理服务

输出
----
- ``data/models/ptbxl_ecg_resnet1d_best.h5``    最优权重
- ``data/models/ptbxl_ecg_resnet1d_meta.json``  元信息（特征、超参、性能）
- ``results/ptbxl/`` 目录下：
  - ``training_curves.png``   loss / AUC 曲线
  - ``test_metrics.json``     测试集 AUC/Accuracy/Sensitivity/Specificity/F1
  - ``test_roc.png`` / ``test_confusion.png``
  - ``classification_report.txt``

使用
----
    # 模式 A：从 HuggingFace parquet 数据训练（download_ptbxl.py --mode hf 配套）
    python scripts/train_ptbxl_ecg.py --source hf \\
        --hf-data-dir data/ptbxl_hf \\
        --label-strategy mi_vs_norm --epochs 30

    # 模式 B：从 WFDB + preprocess_ptbxl.py 输出训练（PhysioNet 原始）
    python scripts/train_ptbxl_ecg.py --source wfdb \\
        --src data/ptbxl --data-dir data/ptbxl_processed \\
        --epochs 30 --batch-size 64

    # 从 HeartCycle 自监督预训练初始化（迁移学习）
    python scripts/train_ptbxl_ecg.py --source hf \\
        --pretrained data/models/ssl_heartcycle_encoder.h5 \\
        --epochs 20

    # 调试（只跑 200 条）
    python scripts/train_ptbxl_ecg.py --source hf --max-records 200 --epochs 3
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_SRC = PROJECT_ROOT / "data" / "ptbxl"
DEFAULT_PROC = PROJECT_ROOT / "data" / "ptbxl_processed"
DEFAULT_HF = PROJECT_ROOT / "data" / "ptbxl_hf"
DEFAULT_MODEL_DIR = PROJECT_ROOT / "data" / "models"
DEFAULT_RESULTS = PROJECT_ROOT / "results" / "ptbxl"


def _set_seeds(seed: int) -> None:
    import random
    random.seed(seed)
    np.random.seed(seed)
    try:
        import tensorflow as tf
        tf.random.set_seed(seed)
        os.environ["TF_DETERMINISTIC_OPS"] = "1"
    except ImportError:
        pass


def _make_callbacks(model_dir: Path, model_name: str, patience: int = 8):
    import tensorflow as tf
    model_dir.mkdir(parents=True, exist_ok=True)
    return [
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(model_dir / f"{model_name}_best.h5"),
            monitor="val_auc", mode="max",
            save_best_only=True, save_weights_only=False, verbose=1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_auc", mode="max", patience=patience,
            restore_best_weights=True, verbose=1,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=4,
            min_lr=1e-6, verbose=1,
        ),
        tf.keras.callbacks.CSVLogger(
            str(model_dir / f"{model_name}_history.csv"), append=False),
    ]


def _evaluate_full(model, ds, name: str = "test") -> dict:
    """跑一遍数据集，返回完整指标 + 概率/真值数组。"""
    from sklearn.metrics import (
        accuracy_score, roc_auc_score, f1_score, precision_score,
        recall_score, confusion_matrix, classification_report)

    y_true, y_prob = [], []
    for x, y in ds:
        p = model.predict(x, verbose=0).ravel()
        y_true.extend(y.numpy().tolist())
        y_prob.extend(p.tolist())
    y_true = np.array(y_true)
    y_prob = np.array(y_prob)

    # Youden's J 阈值
    from sklearn.metrics import roc_curve
    fpr, tpr, thr = roc_curve(y_true, y_prob)
    j_idx = int(np.argmax(tpr - fpr))
    best_thr = float(thr[j_idx])
    y_pred = (y_prob >= best_thr).astype(int)

    cm = confusion_matrix(y_true, y_pred).tolist()
    tn = cm[0][0]; fp = cm[0][1]; fn = cm[1][0]; tp = cm[1][1]
    spec = tn / (tn + fp + 1e-9)

    metrics = {
        "split": name,
        "n": int(len(y_true)),
        "n_pos": int(y_true.sum()),
        "n_neg": int(len(y_true) - y_true.sum()),
        "best_threshold": best_thr,
        "auc": float(roc_auc_score(y_true, y_prob)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "sensitivity": float(recall_score(y_true, y_pred)),
        "specificity": float(spec),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "confusion_matrix": cm,
        "classification_report": classification_report(
            y_true, y_pred, zero_division=0),
        "_y_true": y_true,
        "_y_prob": y_prob,
    }
    return metrics


def _plot_results(history, test_metrics: dict, out_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out_dir.mkdir(parents=True, exist_ok=True)

    # 训练曲线
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    h = history.history
    axes[0].plot(h.get("loss", []), label="train_loss")
    axes[0].plot(h.get("val_loss", []), label="val_loss")
    axes[0].set_title("Loss"); axes[0].legend(); axes[0].grid(True)
    axes[1].plot(h.get("auc", []), label="train_auc")
    axes[1].plot(h.get("val_auc", []), label="val_auc")
    axes[1].set_title("AUC"); axes[1].legend(); axes[1].grid(True)
    plt.tight_layout()
    plt.savefig(out_dir / "training_curves.png", dpi=150)
    plt.close()

    # ROC
    from sklearn.metrics import roc_curve
    y_true = test_metrics["_y_true"]
    y_prob = test_metrics["_y_prob"]
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    plt.figure(figsize=(6, 6))
    plt.plot(fpr, tpr, label=f"AUC = {test_metrics['auc']:.4f}", linewidth=2)
    plt.plot([0, 1], [0, 1], "k--", alpha=0.5)
    plt.xlabel("False Positive Rate"); plt.ylabel("True Positive Rate")
    plt.title("PTB-XL ECG → CAD: Test ROC")
    plt.legend(); plt.grid(True)
    plt.savefig(out_dir / "test_roc.png", dpi=150)
    plt.close()

    # 混淆矩阵
    cm = np.array(test_metrics["confusion_matrix"])
    plt.figure(figsize=(5, 4))
    import seaborn as sns
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["NORM", "CAD"], yticklabels=["NORM", "CAD"])
    plt.xlabel("Predicted"); plt.ylabel("True")
    plt.title("PTB-XL ECG → CAD: Confusion Matrix")
    plt.savefig(out_dir / "test_confusion.png", dpi=150)
    plt.close()


def _save_metrics_json(metrics: dict, path: Path) -> None:
    serializable = {k: v for k, v in metrics.items() if not k.startswith("_")}
    path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False))


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", choices=["hf", "wfdb"], default="hf",
                   help="hf=HuggingFace parquet 数据(国内推荐); "
                        "wfdb=PhysioNet 原始 WFDB + preprocess_ptbxl.py 产出")
    # WFDB 模式专用
    p.add_argument("--src", type=Path, default=DEFAULT_SRC,
                   help="(--source wfdb) PTB-XL 根目录")
    p.add_argument("--data-dir", type=Path, default=DEFAULT_PROC,
                   help="(--source wfdb) preprocess_ptbxl.py 产出目录")
    # HF 模式专用
    p.add_argument("--hf-data-dir", type=Path, default=DEFAULT_HF,
                   help="(--source hf) download_ptbxl.py --mode hf 的目录")
    p.add_argument("--label-strategy", default="mi_vs_norm",
                   choices=["mi_vs_norm", "cad_vs_norm", "abnormal_vs_norm"],
                   help="(--source hf) 5 类→2 类映射策略")
    # 通用
    p.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    p.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    p.add_argument("--resolution", type=int, choices=[100, 500], default=100)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--patience", type=int, default=8)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--no-bandpass", action="store_true",
                   help="跳过带通滤波（PTB-XL 已是高质量数据，可选）")
    p.add_argument("--max-records", type=int, default=None,
                   help="只用前 N 条（调试）")
    p.add_argument("--pretrained", type=Path, default=None,
                   help="从自监督预训练权重初始化（HeartCycle SSL）")
    p.add_argument("--freeze-backbone-epochs", type=int, default=0,
                   help="迁移学习时前 N 个 epoch 冻结主干")
    args = p.parse_args(argv)

    _set_seeds(args.seed)
    print(f"==> 设备:", end=" ")
    try:
        import tensorflow as tf
        gpus = tf.config.list_physical_devices("GPU")
        print(f"{'GPU(' + str(len(gpus)) + ')' if gpus else 'CPU'}")
        for g in gpus:
            try:
                tf.config.experimental.set_memory_growth(g, True)
            except Exception:
                pass
    except ImportError:
        sys.exit("缺少 tensorflow，请 pip install tensorflow")

    from app.algorithms.ptbxl_dataset import (
        load_ptbxl_split, load_ptbxl_split_hf,
        build_ecg_resnet1d, get_dataset_signature)

    sig = get_dataset_signature(args.resolution)
    print(f"==> 数据签名: {sig}")
    print(f"==> 数据源: {args.source}")

    if args.source == "hf":
        if not args.hf_data_dir.exists():
            sys.exit(
                f"未找到 {args.hf_data_dir}。请先：\n"
                f"  python scripts/download_ptbxl.py --mode hf")
        # HF 数据是 100 Hz，强制对齐
        if args.resolution != 100:
            print(f"[warn] HF parquet 是 100 Hz，已自动覆盖 --resolution 为 100")
            args.resolution = 100
            sig = get_dataset_signature(100)

        print(f"==> 标签策略: {args.label_strategy}")
        print("==> 加载 train (HF parquet)")
        train_ds = load_ptbxl_split_hf(
            args.hf_data_dir, split="train",
            label_strategy=args.label_strategy,
            batch_size=args.batch_size, shuffle=True,
            bandpass=not args.no_bandpass, max_records=args.max_records)
        print("==> 加载 val (HF parquet)")
        val_ds = load_ptbxl_split_hf(
            args.hf_data_dir, split="val",
            label_strategy=args.label_strategy,
            batch_size=args.batch_size, shuffle=False,
            bandpass=not args.no_bandpass, max_records=args.max_records)
        print("==> 加载 test (HF parquet)")
        test_ds = load_ptbxl_split_hf(
            args.hf_data_dir, split="test",
            label_strategy=args.label_strategy,
            batch_size=args.batch_size, shuffle=False,
            bandpass=not args.no_bandpass, max_records=args.max_records)
    else:
        train_csv = args.data_dir / "train.csv"
        val_csv = args.data_dir / "val.csv"
        test_csv = args.data_dir / "test.csv"
        for fp in (train_csv, val_csv, test_csv):
            if not fp.exists():
                sys.exit(f"未找到 {fp}，请先运行 preprocess_ptbxl.py")

        print("==> 加载 train (WFDB)")
        train_ds = load_ptbxl_split(
            train_csv, src=args.src, resolution=args.resolution,
            batch_size=args.batch_size, shuffle=True,
            bandpass=not args.no_bandpass, max_records=args.max_records)
        print("==> 加载 val (WFDB)")
        val_ds = load_ptbxl_split(
            val_csv, src=args.src, resolution=args.resolution,
            batch_size=args.batch_size, shuffle=False,
            bandpass=not args.no_bandpass, max_records=args.max_records)
        print("==> 加载 test (WFDB)")
        test_ds = load_ptbxl_split(
            test_csv, src=args.src, resolution=args.resolution,
            batch_size=args.batch_size, shuffle=False,
            bandpass=not args.no_bandpass, max_records=args.max_records)

    print(f"==> 构建模型 ECG_ResNet1D (seq_len={sig['seq_len']})")
    model = build_ecg_resnet1d(seq_len=sig["seq_len"], n_leads=sig["n_leads"],
                               n_classes=1)
    model.optimizer.learning_rate = args.lr

    if args.pretrained and args.pretrained.exists():
        print(f"==> 加载预训练权重 {args.pretrained}")
        try:
            model.load_weights(str(args.pretrained), by_name=True, skip_mismatch=True)
            print("    成功（按层名匹配，未匹配的层使用随机初始化）")
        except Exception as e:
            warnings.warn(f"加载预训练失败: {e}，将从头训练")

    model.summary(line_length=110)

    # 类别不平衡处理
    n_pos = getattr(train_ds, "n_pos", None)
    n_total = getattr(train_ds, "n_samples", None)
    class_weight = None
    if n_pos and n_total:
        n_neg = n_total - n_pos
        class_weight = {
            0: n_total / (2.0 * max(n_neg, 1)),
            1: n_total / (2.0 * max(n_pos, 1)),
        }
        print(f"==> class_weight = {class_weight}")

    cb = _make_callbacks(args.model_dir, "ptbxl_ecg_resnet1d", args.patience)

    # 选择性冻结主干做"线性 probe + 微调"两段式
    if args.freeze_backbone_epochs > 0 and args.pretrained:
        for layer in model.layers:
            if layer.name not in ("output", "dropout", "embedding"):
                layer.trainable = False
        print(f"==> 冻结主干 {args.freeze_backbone_epochs} epochs")
        history_warm = model.fit(
            train_ds, validation_data=val_ds,
            epochs=args.freeze_backbone_epochs,
            class_weight=class_weight,
            callbacks=cb, verbose=2)
        for layer in model.layers:
            layer.trainable = True
        # 解冻后用更小的 LR 微调
        import tensorflow as tf
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=args.lr * 0.1),
            loss=model.loss,
            metrics=[
                tf.keras.metrics.AUC(name="auc"),
                tf.keras.metrics.BinaryAccuracy(name="acc"),
                tf.keras.metrics.Recall(name="sensitivity"),
                tf.keras.metrics.Precision(name="precision"),
            ],
        )
        remaining_epochs = max(1, args.epochs - args.freeze_backbone_epochs)
    else:
        remaining_epochs = args.epochs

    print(f"==> 训练 {remaining_epochs} epochs")
    history = model.fit(
        train_ds, validation_data=val_ds,
        epochs=remaining_epochs,
        class_weight=class_weight,
        callbacks=cb, verbose=2)

    print("==> 测试集评估")
    test_metrics = _evaluate_full(model, test_ds, name="test")
    print(f"   AUC={test_metrics['auc']:.4f}  Acc={test_metrics['accuracy']:.4f}  "
          f"Sens={test_metrics['sensitivity']:.4f}  Spec={test_metrics['specificity']:.4f}  "
          f"F1={test_metrics['f1']:.4f}")

    args.results_dir.mkdir(parents=True, exist_ok=True)
    _plot_results(history, test_metrics, args.results_dir)
    _save_metrics_json(test_metrics, args.results_dir / "test_metrics.json")
    (args.results_dir / "classification_report.txt").write_text(
        test_metrics["classification_report"])

    meta = {
        "model": "ECG_ResNet1D",
        "framework": "tensorflow",
        "data_source": args.source,
        "resolution_hz": args.resolution,
        "seq_len": sig["seq_len"],
        "n_leads": sig["n_leads"],
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "seed": args.seed,
        "pretrained_from": str(args.pretrained) if args.pretrained else None,
        "test_metrics": {k: v for k, v in test_metrics.items()
                         if not k.startswith("_") and k != "classification_report"},
        "label_strategy": args.label_strategy if args.source == "hf" else None,
        "label_strategy_summary_at": (
            str(args.data_dir / "summary.json") if args.source == "wfdb" else None),
    }
    meta_path = args.model_dir / "ptbxl_ecg_resnet1d_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"==> 元信息: {meta_path}")
    print(f"==> 最优权重: {args.model_dir / 'ptbxl_ecg_resnet1d_best.h5'}")
    print(f"==> 结果可视化: {args.results_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
