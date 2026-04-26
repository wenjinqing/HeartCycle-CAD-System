"""
冒烟：确认重要 import 路径全部能成功（合并算法目录后必须验证）。

运行：
    python scripts/smoke_import_all.py

会依次尝试：
    1. main.py（含全部 21 个路由）
    2. 通过 ``from algorithms.X`` 形式（shim）：multimodal_fusion / multimodal_ablation
       / experiment_evaluation / advanced_preprocessing
    3. 通过 ``from app.algorithms.X`` 形式（B 真源码）
    4. 推理服务 ZalizadehInferenceService.is_available()

任何一步失败立即返回非零。
"""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(PROJECT_ROOT)


def step(label: str, fn) -> bool:
    try:
        fn()
        print(f"[OK]  {label}")
        return True
    except Exception:
        print(f"[ERR] {label}")
        traceback.print_exc()
        return False


def main() -> int:
    # 1. main.py（含全部路由 + middleware + lifespan）
    def import_main():
        import importlib
        importlib.import_module("app.main")

    # 2. 兼容 shim 导入（backend/algorithms/*.py）
    def import_shim_layer():
        import sys as _sys
        # 让 backend/ 出现在 sys.path 顶部，模拟 multimodal_service 的 hack
        if str(BACKEND) not in _sys.path:
            _sys.path.insert(0, str(BACKEND))
        import importlib
        for m in (
            "algorithms.multimodal_fusion",
            "algorithms.multimodal_ablation",
            "algorithms.experiment_evaluation",
            "algorithms.advanced_preprocessing",
            "algorithms.dataset_generator",
        ):
            importlib.import_module(m)

    # 3. 真源码（backend/app/algorithms/*.py）
    def import_canonical():
        import importlib
        for m in (
            "app.algorithms.multimodal_fusion",
            "app.algorithms.multimodal_ablation",
            "app.algorithms.experiment_evaluation",
            "app.algorithms.advanced_preprocessing",
            "app.algorithms.dataset_generator",
            "app.algorithms.feature_extraction",
            "app.algorithms.model_training",
            "app.algorithms.data_processing",
        ):
            importlib.import_module(m)

    # 4. 真实数据 CAD 推理可用
    def real_model_ok():
        from app.services.zalizadeh_inference import (
            get_zalizadeh_inference_service,
        )
        svc = get_zalizadeh_inference_service()
        assert svc.is_available(), svc.get_metadata().get("error")

    results = [
        step("import app.main (FastAPI app + 21 routers)", import_main),
        step("import 'from algorithms.X' shim layer", import_shim_layer),
        step("import 'from app.algorithms.X' canonical", import_canonical),
        step("ZalizadehInferenceService.is_available()", real_model_ok),
    ]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
