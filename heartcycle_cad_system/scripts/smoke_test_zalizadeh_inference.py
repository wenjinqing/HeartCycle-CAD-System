"""
冒烟测试：scripts/train_zalizadeh.py 训出来的模型能否被推理服务正确加载并预测。

运行：
    python scripts/smoke_test_zalizadeh_inference.py

期望输出：
    [INFO] available=True ...
    [INFO] schema fields=33 ...
    [INFO] sample 1: prediction=1 p_pos=0.xx risk=high
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

# 让 settings 拿到真实的 BASE_DIR
os.chdir(PROJECT_ROOT)


def main() -> int:
    from app.services.zalizadeh_inference import (
        ZalizadehInferenceService,
        get_zalizadeh_inference_service,
    )
    import pandas as pd

    svc = get_zalizadeh_inference_service()
    available = svc.is_available()
    print(f"[INFO] available={available}")
    if not available:
        meta = svc.get_metadata()
        print(f"[ERR] 模型未加载: {meta.get('error')}")
        return 1

    meta = svc.get_metadata()
    print(
        f"[INFO] best_model={meta['best_model']}, "
        f"AUC={meta['best_auc']:.4f}, Acc={meta['best_accuracy']:.4f}, "
        f"Sens={meta['best_sensitivity']:.4f}, Spec={meta['best_specificity']:.4f}, "
        f"threshold={meta['threshold']:.3f}, n_features={meta['n_features_engineered']}"
    )

    schema = svc.get_schema()
    print(f"[INFO] clinical fields={len(schema['fields'])}, "
          f"engineered features={len(schema['engineered_feature_names'])}")

    # 用训练集真实样本验证：第 0 行（标签=1）和第 3 行（标签=0）
    df = pd.read_csv(PROJECT_ROOT / "data" / "raw" / "cad_features.csv")
    labels = pd.read_csv(PROJECT_ROOT / "data" / "raw" / "cad_labels.csv")["label"].tolist()

    correct = 0
    samples = [(0, labels[0]), (3, labels[3]), (10, labels[10]), (50, labels[50]), (200, labels[200])]
    for idx, true_label in samples:
        raw = df.iloc[idx].to_dict()
        result = svc.predict_one(raw)
        ok = result["prediction"] == true_label
        correct += 1 if ok else 0
        print(
            f"[INFO] sample idx={idx} true={true_label} pred={result['prediction']} "
            f"p_pos={result['p_positive']:.4f} risk={result['risk_level']} {'OK' if ok else 'MISS'}"
        )

    print(f"\n[RESULT] {correct}/{len(samples)} 命中。")

    # 容错性：传一个空字典
    try:
        empty_result = svc.predict_one({})
        print(f"[INFO] 空字典预测（中位数兜底）: pred={empty_result['prediction']} p_pos={empty_result['p_positive']:.4f}")
    except Exception as e:
        print(f"[WARN] 空字典预测失败（可接受）: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
