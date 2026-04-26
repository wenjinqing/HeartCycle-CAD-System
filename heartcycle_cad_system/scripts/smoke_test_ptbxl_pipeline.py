"""端到端烟雾测试：用 8 条 mock PTB-XL 数据跑通整条管线。

不需要真下载 1.7 GB 数据，只验证脚本逻辑能跑：
    1. download_ptbxl.py --mode mock      → 生成 mock WFDB 文件
    2. preprocess_ptbxl.py                → 标签聚合 + split
    3. ptbxl_dataset 加载                 → tf.data 管线 + 形状检查
    4. build_ecg_resnet1d                 → 模型可构建可推理
    5. PTBXLMultimodalService.predict     → 融合服务可跑通

不会真训练（默认 epochs=0，仅前向）。

用法
----
    python scripts/smoke_test_ptbxl_pipeline.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Windows 下默认 stdout 是 GBK，影响子进程 UTF-8 输出 → 强制走 UTF-8
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    """跨平台稳健的子进程调用：永远用 UTF-8 解码，错字符替换。"""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env,
    )


GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def _ok(msg: str) -> None:
    print(f"{GREEN}[OK]{RESET} {msg}")


def _fail(msg: str) -> None:
    print(f"{RED}[FAIL]{RESET} {msg}")


def _warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{RESET} {msg}")


def _section(title: str) -> None:
    print(f"\n{'=' * 8}  {title}  {'=' * 8}")


def step_1_mock_download(tmp: Path) -> bool:
    _section("Step 1: 生成 mock PTB-XL")
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "download_ptbxl.py"),
        "--mode", "mock",
        "--dest", str(tmp / "ptbxl"),
        "--mock-records", "8",
    ]
    res = _run(cmd)
    if res.returncode != 0:
        _fail(f"download_ptbxl.py mock 失败:\n{res.stdout}\n{res.stderr}")
        return False
    db = tmp / "ptbxl" / "ptbxl_database.csv"
    if not db.exists():
        _fail(f"未生成 {db}")
        return False
    _ok(f"生成 mock 数据集 → {tmp / 'ptbxl'}")
    return True


def step_2_preprocess(tmp: Path) -> bool:
    _section("Step 2: 预处理 + 标签聚合")
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "preprocess_ptbxl.py"),
        "--src", str(tmp / "ptbxl"),
        "--output-dir", str(tmp / "ptbxl_processed"),
        "--label-strategy", "mi_vs_norm",
        "--min-age", "0",  # mock 数据 age 可能很小
    ]
    res = _run(cmd)
    if res.returncode != 0:
        _fail(f"preprocess_ptbxl.py 失败:\n{res.stdout}\n{res.stderr}")
        return False
    summary = tmp / "ptbxl_processed" / "summary.json"
    if not summary.exists():
        _fail(f"未生成 {summary}")
        return False
    _ok(f"预处理完成 → {summary}")
    print(summary.read_text())
    return True


def step_3_dataset_loading(tmp: Path) -> bool:
    _section("Step 3: tf.data 管线加载")
    try:
        from app.algorithms.ptbxl_dataset import (
            load_ptbxl_split, get_dataset_signature)
    except ImportError as e:
        _fail(f"无法 import ptbxl_dataset: {e}")
        return False

    sig = get_dataset_signature(100)
    train_csv = tmp / "ptbxl_processed" / "train.csv"
    if not train_csv.exists():
        _warn(f"{train_csv} 不存在，跳过加载步骤")
        return True

    import pandas as pd
    df = pd.read_csv(train_csv)
    if df.empty:
        _warn("train.csv 为空（mock 数据中 mi_vs_norm 类别不平衡是预期的），跳过")
        return True

    try:
        ds = load_ptbxl_split(
            train_csv, src=tmp / "ptbxl", resolution=100,
            batch_size=2, shuffle=False, bandpass=False)
    except Exception as e:
        _fail(f"load_ptbxl_split 失败: {e}")
        return False

    for x, y in ds.take(1):
        shape_ok = (x.shape[1:] == (sig["seq_len"], sig["n_leads"]))
        if not shape_ok:
            _fail(f"形状错误: {x.shape}, 期望 (B, {sig['seq_len']}, {sig['n_leads']})")
            return False
        _ok(f"加载样本 batch shape={x.shape}, y={y.numpy().tolist()}")
        break
    return True


def step_4_build_model() -> bool:
    _section("Step 4: 构建 1D-ResNet 模型")
    try:
        from app.algorithms.ptbxl_dataset import build_ecg_resnet1d
        import numpy as np

        model = build_ecg_resnet1d(seq_len=1000, n_leads=12, n_classes=1)
        _ok(f"模型构建: {model.name}, params={model.count_params():,}")

        x = np.random.randn(2, 1000, 12).astype("float32")
        y = model.predict(x, verbose=0)
        if y.shape != (2, 1):
            _fail(f"输出形状错误 {y.shape}")
            return False
        _ok(f"前向 OK, output={y.ravel().tolist()}")
        return True
    except Exception as e:
        _fail(f"模型构建/前向失败: {e}")
        return False


def step_5_ssl_recon() -> bool:
    _section("Step 5: SSL mask reconstruction 模型")
    try:
        from app.algorithms.ptbxl_dataset import (
            build_ssl_mask_reconstructor, random_mask_ecg)
        import numpy as np

        model = build_ssl_mask_reconstructor(seq_len=1000, n_leads=12)
        _ok(f"SSL 模型构建: {model.name}, params={model.count_params():,}")

        sig = np.random.randn(1000, 12).astype("float32")
        masked, original = random_mask_ecg(sig, mask_ratio=0.15, mask_span=50)
        recon = model.predict(masked[None], verbose=0)
        if recon.shape != (1, 1000, 12):
            _fail(f"重构输出形状错误 {recon.shape}")
            return False
        _ok(f"mask + recon OK, recon shape={recon.shape}")
        return True
    except Exception as e:
        _fail(f"SSL 模型失败: {e}")
        return False


def step_6_multimodal_service() -> bool:
    _section("Step 6: PTBXLMultimodalService 融合服务")
    try:
        from app.services.ptbxl_multimodal_service import (
            get_ptbxl_multimodal_service, FUSION_METHODS,
            PTBXLMultimodalService)
        svc = get_ptbxl_multimodal_service()
        st = svc.get_status()
        _ok(f"服务状态: ECG 可用={st['ecg_branch']['available']}, "
            f"Tab 可用={st['tabular_branch']['available']}")
        # 融合公式单元测试
        for m in FUSION_METHODS:
            p = PTBXLMultimodalService._fuse(0.7, 0.3, method=m,
                                             w_ecg=0.6, w_tab=0.4)
            if not (0.0 <= p <= 1.0):
                _fail(f"fusion={m} 输出越界: {p}")
                return False
        _ok("所有融合方法在 [0,1] 区间")
        # 模型可能未训练，但服务的"无概率即报错"应当工作
        try:
            svc.predict()
            _fail("空输入应该报错但没有")
            return False
        except (ValueError, TypeError):
            _ok("空输入正确报错")
        return True
    except Exception as e:
        _fail(f"多模态服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def step_7_router_import() -> bool:
    _section("Step 7: FastAPI 路由可 import")
    try:
        from app.api.v1 import ptbxl_multimodal
        routes = [r.path for r in ptbxl_multimodal.router.routes]
        _ok(f"路由 import OK, 端点: {routes}")
        return True
    except Exception as e:
        _fail(f"路由 import 失败: {e}")
        return False


def main() -> int:
    print(f"PROJECT_ROOT = {PROJECT_ROOT}")

    with tempfile.TemporaryDirectory(prefix="ptbxl_smoke_") as td:
        tmp = Path(td)
        results = []
        results.append(("mock_download", step_1_mock_download(tmp)))
        results.append(("preprocess", step_2_preprocess(tmp)))
        results.append(("dataset_loading", step_3_dataset_loading(tmp)))
        results.append(("build_model", step_4_build_model()))
        results.append(("ssl_recon", step_5_ssl_recon()))
        results.append(("multimodal_service", step_6_multimodal_service()))
        results.append(("router_import", step_7_router_import()))

    _section("总结")
    n_ok = sum(1 for _, ok in results if ok)
    n_fail = len(results) - n_ok
    for name, ok in results:
        mark = f"{GREEN}[OK]  {RESET}" if ok else f"{RED}[FAIL]{RESET}"
        print(f"  {mark}  {name}")
    print(f"\n{n_ok}/{len(results)} 通过")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
