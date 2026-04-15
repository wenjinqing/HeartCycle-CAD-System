"""
将 heartcycle/CAD.xlsx（Sheet 1 - Table 1）导出为系统「特征 CSV + 单列标签 CSV」格式。

清洗：
  - Sex: Fmale -> Female，再与其它类别一起做 get_dummies
  - Cath: Cad -> 1, Normal -> 0

用法（在 heartcycle_cad_system 目录下）:
  python scripts/export_cad_xlsx_for_training.py
  python scripts/export_cad_xlsx_for_training.py --xlsx ../heartcycle/CAD.xlsx --out data/processed/cad_clinical

训练时在 API / 前端使用:
  feature_file = .../cad_features.csv
  label_file   = .../cad_labels.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="导出 CAD.xlsx 为训练用 CSV")
    repo = Path(__file__).resolve().parent.parent
    default_xlsx = repo.parent / "heartcycle" / "CAD.xlsx"
    parser.add_argument(
        "--xlsx",
        type=Path,
        default=default_xlsx,
        help="CAD.xlsx 路径",
    )
    parser.add_argument(
        "--sheet",
        type=str,
        default="Sheet 1 - Table 1",
        help="工作表名称",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=repo / "data" / "processed" / "cad_clinical",
        help="输出目录（将写入 cad_features.csv / cad_labels.csv）",
    )
    args = parser.parse_args()

    if not args.xlsx.is_file():
        raise SystemExit(f"找不到 Excel 文件: {args.xlsx}")

    df = pd.read_excel(args.xlsx, sheet_name=args.sheet, header=0)
    if "Cath" not in df.columns:
        raise SystemExit("表中缺少结局列 Cath（应为 Cad / Normal）")

    y_raw = df["Cath"].astype(str).str.strip()
    map_y = {"Cad": 1, "CAD": 1, "cad": 1, "Normal": 0, "NORMAL": 0, "normal": 0}
    y = y_raw.map(map_y)
    if y.isna().any():
        bad = y_raw[y.isna()].unique().tolist()
        raise SystemExit(f"Cath 存在无法映射的值: {bad[:20]}")

    X = df.drop(columns=["Cath"]).copy()
    if "Sex" in X.columns:
        X["Sex"] = (
            X["Sex"]
            .astype(str)
            .str.strip()
            .replace({"Fmale": "Female", "fmale": "Female", "FMALE": "Female"})
        )

    # 布尔列一并转 dummy
    obj_cols = X.select_dtypes(include=["object", "bool"]).columns.tolist()
    if obj_cols:
        X = pd.get_dummies(X, columns=obj_cols, drop_first=False, dtype=np.int8)

    # 确保全为数值（避免残留 category 等）
    for c in X.columns:
        if not np.issubdtype(X[c].dtype, np.number):
            X[c] = pd.to_numeric(X[c], errors="coerce")

    if X.isna().any().any():
        na_cols = X.columns[X.isna().any()].tolist()
        print(f"警告: 以下列存在 NaN，将用 0 填充: {na_cols}")
        X = X.fillna(0)

    args.out.mkdir(parents=True, exist_ok=True)
    feat_path = args.out / "cad_features.csv"
    lab_path = args.out / "cad_labels.csv"

    X.to_csv(feat_path, index=False, encoding="utf-8-sig")
    pd.DataFrame({"label": y.astype(int)}).to_csv(lab_path, index=False, encoding="utf-8-sig")

    print("导出完成:")
    print(f"  特征: {feat_path}  shape={X.shape}")
    print(f"  标签: {lab_path}  n={len(y)}  Cad=1: {(y==1).sum()}  Normal=0: {(y==0).sum()}")
    print("  特征列数:", len(X.columns))


if __name__ == "__main__":
    main()
