"""PTB-XL → CAD 二分类标签预处理。

流程
----
1. 读 ``ptbxl_database.csv``，把 ``scp_codes`` 字符串 dict 解析成 dict
2. 用 ``scp_statements.csv`` 把单条 SCP 码聚合到 5 个超类
   (NORM / MI / STTC / CD / HYP)
3. 按 ``label_strategy`` 生成二分类标签：
   - ``mi_vs_norm``     : MI 阳 vs NORM 阴（最经典 CAD 检测）
   - ``cad_vs_norm``    : (MI ∪ STTC) 阳 vs NORM 阴（更宽，含心肌缺血）
   - ``abnormal_vs_norm``: ¬NORM 阳 vs NORM 阴（最宽）
4. 按 PTB-XL 推荐的 ``strat_fold``：
   - 1-8 → train
   - 9   → val
   - 10  → test
5. 输出三份 CSV，每行：``ecg_id, patient_id, age, sex, scp_codes,
   label, filename_lr, filename_hr, split``

学术诚信
--------
- 聚合策略的代码逻辑在论文 `methods` 章节必须明确写出（哪些 SCP 码算 CAD 阳性）
- 标签来源是 PTB-XL 原始医生标注 + SCP 聚合，**不是合成**
- 如果一条记录同时有 MI 和 NORM 码（极少），按"任何一条 MI 码即阳"原则归为阳

用法
----
    python scripts/preprocess_ptbxl.py --src data/ptbxl

    # 自定义标签策略
    python scripts/preprocess_ptbxl.py --src data/ptbxl \\
        --label-strategy cad_vs_norm \\
        --output-dir data/ptbxl_processed
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = PROJECT_ROOT / "data" / "ptbxl"
DEFAULT_OUT = PROJECT_ROOT / "data" / "ptbxl_processed"

LABEL_STRATEGIES = {
    "mi_vs_norm": {
        "positive_classes": {"MI"},
        "negative_classes": {"NORM"},
        "description": "MI 阳 vs NORM 阴（PTB-XL 上最经典的 CAD 检测设置）",
    },
    "cad_vs_norm": {
        "positive_classes": {"MI", "STTC"},
        "negative_classes": {"NORM"},
        "description": "(MI ∪ STTC) 阳 vs NORM 阴（含心肌缺血迹象）",
    },
    "abnormal_vs_norm": {
        "positive_classes": {"MI", "STTC", "CD", "HYP"},
        "negative_classes": {"NORM"},
        "description": "任意异常 vs NORM 阴（最宽）",
    },
}


def _load_metadata(src: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    db_path = src / "ptbxl_database.csv"
    scp_path = src / "scp_statements.csv"
    if not db_path.exists():
        sys.exit(f"未找到 {db_path}，请先运行 download_ptbxl.py")
    if not scp_path.exists():
        sys.exit(f"未找到 {scp_path}")

    Y = pd.read_csv(db_path, index_col="ecg_id")
    Y["scp_codes"] = Y["scp_codes"].apply(ast.literal_eval)

    # scp_statements: 第一列是 SCP 码，可能列名 'index' 或者 unnamed
    agg = pd.read_csv(scp_path)
    if "index" in agg.columns:
        agg = agg.set_index("index")
    else:
        agg = agg.set_index(agg.columns[0])
    agg = agg[agg["diagnostic"] == 1.0]
    return Y, agg


def _aggregate_to_superclass(scp_codes: Dict[str, float],
                             agg: pd.DataFrame) -> Set[str]:
    classes: Set[str] = set()
    for code in scp_codes:
        if code in agg.index:
            cls = agg.loc[code]
            cls_val = cls["diagnostic_class"] if isinstance(cls, pd.Series) else \
                cls.iloc[0]["diagnostic_class"]
            if isinstance(cls_val, str) and cls_val:
                classes.add(cls_val)
    return classes


def _assign_label(superclasses: Set[str],
                  positive: Set[str], negative: Set[str]) -> Optional[int]:
    """返回 0/1/None。冲突时 (既阳又阴) 视为模糊样本，返回 None 丢弃。"""
    is_pos = bool(superclasses & positive)
    is_neg = bool(superclasses & negative) and not is_pos
    if is_pos:
        return 1
    if is_neg and not is_pos:
        return 0
    return None


def _split_from_strat_fold(fold: int) -> str:
    if fold <= 8:
        return "train"
    if fold == 9:
        return "val"
    return "test"


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--src", type=Path, default=DEFAULT_SRC,
                   help=f"PTB-XL 根目录（默认 {DEFAULT_SRC}）")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUT,
                   help=f"输出目录（默认 {DEFAULT_OUT}）")
    p.add_argument("--label-strategy", choices=list(LABEL_STRATEGIES.keys()),
                   default="mi_vs_norm",
                   help="标签策略，详见 --list-strategies")
    p.add_argument("--list-strategies", action="store_true",
                   help="列出所有标签策略说明并退出")
    p.add_argument("--min-age", type=int, default=18,
                   help="只保留 age >= 该值的样本，默认 18")
    p.add_argument("--require-validated", action="store_true",
                   help="只保留 validated_by_human=True 的高质量样本")
    args = p.parse_args(argv)

    if args.list_strategies:
        print("\n标签策略 (--label-strategy)：")
        for k, v in LABEL_STRATEGIES.items():
            print(f"  {k}")
            print(f"    阳性: {sorted(v['positive_classes'])}")
            print(f"    阴性: {sorted(v['negative_classes'])}")
            print(f"    说明: {v['description']}")
        return 0

    src: Path = args.src.resolve()
    out: Path = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    print(f"==> 读取 PTB-XL 元数据自 {src}")
    Y, agg = _load_metadata(src)
    print(f"   ptbxl_database.csv: {Y.shape}")
    print(f"   scp_statements.csv (diagnostic only): {agg.shape}")

    # 聚合超类
    Y["superclass"] = Y["scp_codes"].apply(
        lambda d: list(_aggregate_to_superclass(d, agg)))

    # 应用标签策略
    strat = LABEL_STRATEGIES[args.label_strategy]
    Y["label"] = Y["superclass"].apply(
        lambda c: _assign_label(set(c), strat["positive_classes"],
                                strat["negative_classes"]))

    n_total = len(Y)
    Y = Y.dropna(subset=["label"]).copy()
    Y["label"] = Y["label"].astype(int)
    n_after_label = len(Y)

    if args.min_age:
        Y = Y[Y["age"].fillna(0) >= args.min_age]
    if args.require_validated and "validated_by_human" in Y.columns:
        Y = Y[Y["validated_by_human"].fillna(False).astype(bool)]
    n_after_filter = len(Y)

    Y["split"] = Y["strat_fold"].apply(_split_from_strat_fold)

    cols_to_keep = [
        "patient_id", "age", "sex", "height", "weight",
        "scp_codes", "superclass", "label", "split",
        "strat_fold", "filename_lr", "filename_hr",
    ]
    cols_to_keep = [c for c in cols_to_keep if c in Y.columns]
    out_df = Y[cols_to_keep].reset_index()  # 把 ecg_id 还原成列

    # 拆分写出
    summary = {
        "label_strategy": args.label_strategy,
        "positive_classes": sorted(strat["positive_classes"]),
        "negative_classes": sorted(strat["negative_classes"]),
        "n_total_records": n_total,
        "n_after_label_filter": n_after_label,
        "n_after_age_validated_filter": n_after_filter,
        "splits": {},
    }

    for split in ("train", "val", "test"):
        sub = out_df[out_df["split"] == split]
        sub_path = out / f"{split}.csv"
        sub.to_csv(sub_path, index=False)
        summary["splits"][split] = {
            "n": int(len(sub)),
            "n_pos": int((sub["label"] == 1).sum()),
            "n_neg": int((sub["label"] == 0).sum()),
            "pos_ratio": float((sub["label"] == 1).mean()) if len(sub) else 0.0,
        }
        print(f"   [{split}] {len(sub):>6d}  阳:{(sub['label']==1).sum():>5d}  "
              f"阴:{(sub['label']==0).sum():>5d}  → {sub_path}")

    summary_path = out / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\n==> 汇总已写入 {summary_path}")

    print("\n下一步:")
    print(f"  python scripts/train_ptbxl_ecg.py --data-dir {out} --src {src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
