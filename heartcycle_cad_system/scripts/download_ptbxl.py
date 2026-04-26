"""下载 PTB-XL 公开 ECG 数据集（PhysioNet v1.0.3）。

PTB-XL 是当前 ECG 深度学习研究最常用的公开数据集：
    21,799 条 12 导联静息 ECG，18,869 名患者，含 71 个 SCP-ECG 诊断标签
    (聚合为 5 个超类：NORM / MI / STTC / CD / HYP)，CC-BY 4.0 许可。

本脚本支持五种下载方式：
    1. ``--mode hf``     ：HuggingFace 镜像（**国内强烈推荐**），744 MB parquet
                          走 hf-mirror.com，速度通常 1-10 MB/s
    2. ``--mode wget``   ：调用系统 wget（Linux/macOS 友好）
    3. ``--mode python`` ：纯 Python（requests + tqdm，断点续传，跨平台首选）
    4. ``--mode aws``    ：AWS CLI 匿名访问 s3://physionet-open
    5. ``--mode mock``   ：仅生成 5 条假记录，用于 smoke 测试，不联网

下载到 ``<project>/data/ptbxl/`` 默认目录，可用 ``--dest`` 覆盖。
HF 模式默认下到 ``<project>/data/ptbxl_hf/``。

使用示例
--------
    # 国内首选：HuggingFace 镜像（约 744 MB，已 parquet 化）
    python scripts/download_ptbxl.py --mode hf

    # 纯 Python 模式 + 仅 100 Hz 子集 (≈ 800 MB)，要求能稳定访问 physionet.org
    python scripts/download_ptbxl.py --mode python --resolution 100

    # CI/单元测试：5 条 mock 数据
    python scripts/download_ptbxl.py --mode mock

参考
----
- 主页:   https://physionet.org/content/ptb-xl/1.0.3/
- 论文:   Wagner et al., Sci Data 2020. https://doi.org/10.1038/s41597-020-0495-6
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = PROJECT_ROOT / "data" / "ptbxl"

PTBXL_VERSION = "1.0.3"
PTBXL_HTTP_BASE = f"https://physionet.org/files/ptb-xl/{PTBXL_VERSION}/"
PTBXL_S3_BASE = f"s3://physionet-open/ptb-xl/{PTBXL_VERSION}/"

# HuggingFace 镜像（国内访问推荐）：BLOSSOM-framework/PTB-XL，744 MB parquet，
# 已切片为 (1000, 12) ECG + 5 类 label + split 列
HF_REPO_ID = "BLOSSOM-framework/PTB-XL"
HF_REPO_TYPE = "dataset"
HF_DEFAULT_ENDPOINT = "https://hf-mirror.com"  # 国内代理；想用官方 HF 时设 https://huggingface.co

# 必下文件（≈ 6 MB），有它们就能跑预处理脚本
META_FILES = [
    "ptbxl_database.csv",
    "scp_statements.csv",
    "RECORDS",
    "SHA256SUMS.txt",
    "example_physionet.py",
    "LICENSE.txt",
]


# ─── Mock 模式：生成最小可用数据集，用于 CI/烟雾测试 ─────────────────────────

def _make_mock_dataset(dest: Path, n_records: int = 8) -> None:
    """创建 5-8 条假记录的 mock PTB-XL，足以让预处理脚本跑通。

    注意:
        Mock 数据**不可用于实际训练或论文**。仅用于验证管线代码逻辑。
    """
    import numpy as np

    dest.mkdir(parents=True, exist_ok=True)
    print(f"[mock] 在 {dest} 生成 {n_records} 条假记录")

    # 1) ptbxl_database.csv（最小子集列）
    rows = []
    scp_pool = [
        "{'NORM': 100.0, 'SR': 0.0}",
        "{'IMI': 35.0, 'ABQRS': 0.0, 'SR': 0.0}",
        "{'NDT': 100.0, 'SR': 0.0}",
        "{'AMI': 80.0, 'IMI': 20.0, 'SR': 0.0}",
        "{'NORM': 100.0, 'SBRAD': 50.0}",
    ]
    for ecg_id in range(1, n_records + 1):
        rows.append({
            "ecg_id": ecg_id,
            "patient_id": 10000 + ecg_id,
            "age": 40 + (ecg_id * 3) % 35,
            "sex": ecg_id % 2,
            "height": 170,
            "weight": 70,
            "scp_codes": scp_pool[ecg_id % len(scp_pool)],
            "report": "mock report",
            "strat_fold": (ecg_id % 10) + 1,
            "filename_lr": f"records100/00000/{ecg_id:05d}_lr",
            "filename_hr": f"records500/00000/{ecg_id:05d}_hr",
        })
    import pandas as pd
    pd.DataFrame(rows).to_csv(dest / "ptbxl_database.csv", index=False)

    # 2) scp_statements.csv（最小子集，覆盖上面用到的码）
    scp_stmt = pd.DataFrame([
        {"index": "NORM", "description": "normal ECG", "diagnostic": 1.0,
         "diagnostic_class": "NORM", "diagnostic_subclass": "NORM"},
        {"index": "IMI", "description": "inferior myocardial infarction", "diagnostic": 1.0,
         "diagnostic_class": "MI", "diagnostic_subclass": "IMI"},
        {"index": "AMI", "description": "anterior myocardial infarction", "diagnostic": 1.0,
         "diagnostic_class": "MI", "diagnostic_subclass": "AMI"},
        {"index": "NDT", "description": "non-diagnostic T abnormalities", "diagnostic": 1.0,
         "diagnostic_class": "STTC", "diagnostic_subclass": "STTC"},
        {"index": "SR", "description": "sinus rhythm", "diagnostic": 0.0,
         "diagnostic_class": "", "diagnostic_subclass": ""},
        {"index": "SBRAD", "description": "sinus bradycardia", "diagnostic": 0.0,
         "diagnostic_class": "", "diagnostic_subclass": ""},
        {"index": "ABQRS", "description": "abnormal QRS", "diagnostic": 0.0,
         "diagnostic_class": "", "diagnostic_subclass": ""},
    ])
    scp_stmt.to_csv(dest / "scp_statements.csv", index=False)

    # 3) records100/00000/<id>_lr.dat + .hea  (用 wfdb 写最小 WFDB)
    try:
        import wfdb  # type: ignore
    except ImportError:
        print("[mock] 缺少 wfdb 库，跳过 WFDB 文件生成。"
              "运行 `pip install wfdb` 后再试。")
        return

    sub_dir_lr = dest / "records100" / "00000"
    sub_dir_lr.mkdir(parents=True, exist_ok=True)
    sub_dir_hr = dest / "records500" / "00000"
    sub_dir_hr.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(42)
    leads = ["I", "II", "III", "aVR", "aVL", "aVF",
             "V1", "V2", "V3", "V4", "V5", "V6"]

    for ecg_id in range(1, n_records + 1):
        # 100 Hz, 10 秒 → 1000 samples × 12 leads
        sig_lr = rng.normal(0, 0.1, size=(1000, 12)).astype(np.float32)
        # 在第一个导联加一个伪 QRS（5 个 spike）
        for k in range(5):
            sig_lr[150 + k * 200: 158 + k * 200, 0] += 1.5
        wfdb.wrsamp(
            record_name=f"{ecg_id:05d}_lr",
            fs=100, units=["mV"] * 12, sig_name=leads,
            p_signal=sig_lr, fmt=["16"] * 12,
            write_dir=str(sub_dir_lr),
        )
        sig_hr = np.repeat(sig_lr, 5, axis=0)  # 简易上采样到 500 Hz × 10 s
        wfdb.wrsamp(
            record_name=f"{ecg_id:05d}_hr",
            fs=500, units=["mV"] * 12, sig_name=leads,
            p_signal=sig_hr, fmt=["16"] * 12,
            write_dir=str(sub_dir_hr),
        )
    # RECORDS 索引
    (dest / "RECORDS").write_text("\n".join(
        f"records100/00000/{i:05d}_lr" for i in range(1, n_records + 1)
    ) + "\n")
    print(f"[mock] 完成。可在 {dest} 跑 preprocess_ptbxl.py 验证。")


# ─── wget 模式 ──────────────────────────────────────────────────────────────

def _download_via_wget(dest: Path, resolution: Optional[int]) -> None:
    """调用系统 wget 镜像站点。不带 -m 全镜像，按需要的子目录抓取。"""
    if shutil.which("wget") is None:
        sys.exit("[wget] 未找到 wget，请改用 --mode python 或安装 wget。")
    dest.mkdir(parents=True, exist_ok=True)
    # 元数据
    cmd_meta = ["wget", "-r", "-N", "-c", "-np", "-nH", "--cut-dirs=3",
                "-P", str(dest), "-A", ",".join(META_FILES), PTBXL_HTTP_BASE]
    print("[wget] 拉取元数据 ...")
    subprocess.run(cmd_meta, check=True)
    # 波形（按分辨率）
    targets = []
    if resolution is None or resolution == 100:
        targets.append(f"{PTBXL_HTTP_BASE}records100/")
    if resolution is None or resolution == 500:
        targets.append(f"{PTBXL_HTTP_BASE}records500/")
    for url in targets:
        cmd = ["wget", "-r", "-N", "-c", "-np", "-nH",
               "--cut-dirs=3", "-P", str(dest), url]
        print(f"[wget] 拉取 {url}")
        subprocess.run(cmd, check=True)


# ─── AWS 模式 ───────────────────────────────────────────────────────────────

def _download_via_aws(dest: Path, resolution: Optional[int]) -> None:
    if shutil.which("aws") is None:
        sys.exit("[aws] 未找到 aws CLI。请 `pip install awscli` 或改 --mode python。")
    dest.mkdir(parents=True, exist_ok=True)
    excludes: List[str] = []
    if resolution == 100:
        excludes = ["--exclude", "records500/*"]
    elif resolution == 500:
        excludes = ["--exclude", "records100/*"]
    cmd = ["aws", "s3", "sync", "--no-sign-request",
           PTBXL_S3_BASE, str(dest)] + excludes
    print(f"[aws] 同步 {PTBXL_S3_BASE} → {dest}")
    subprocess.run(cmd, check=True)


# ─── Pure Python 模式（推荐，跨平台） ───────────────────────────────────────

@dataclass
class _DownloadTask:
    url: str
    rel_path: str  # 相对 dest 的路径
    expected_size: Optional[int] = None


def _http_download_one(task: _DownloadTask, dest: Path,
                       chunk: int = 1 << 20) -> None:
    """单文件 HTTP 下载，支持断点续传。"""
    import requests  # 延迟导入

    target = dest / task.rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    headers = {}
    mode = "wb"
    if target.exists():
        size = target.stat().st_size
        if task.expected_size and size >= task.expected_size:
            print(f"[skip ] {task.rel_path}（已完成 {size} 字节）")
            return
        headers["Range"] = f"bytes={size}-"
        mode = "ab"

    with requests.get(task.url, stream=True, headers=headers, timeout=60) as r:
        if r.status_code in (200, 206):
            try:
                from tqdm import tqdm  # type: ignore
                total = int(r.headers.get("Content-Length", 0))
                pbar = tqdm(total=total, unit="B", unit_scale=True,
                            desc=task.rel_path[-40:], leave=False)
            except ImportError:
                pbar = None
            with open(target, mode) as f:
                for piece in r.iter_content(chunk_size=chunk):
                    if not piece:
                        continue
                    f.write(piece)
                    if pbar:
                        pbar.update(len(piece))
            if pbar:
                pbar.close()
        else:
            raise RuntimeError(f"HTTP {r.status_code} for {task.url}")


def _enumerate_records_via_records_index(dest: Path) -> List[str]:
    records_idx = dest / "RECORDS"
    if not records_idx.exists():
        raise FileNotFoundError(
            f"未找到 {records_idx}。请先用 --mode python 拉取元数据。")
    lines = [ln.strip() for ln in records_idx.read_text().splitlines() if ln.strip()]
    return lines


def _download_via_python(dest: Path, resolution: Optional[int],
                         max_workers: int = 8,
                         meta_only: bool = False) -> None:
    """纯 Python 下载：先取元数据，再按 RECORDS 索引拉波形。

    特点:
        - 自动断点续传
        - 跨平台（Windows 友好）
        - 多线程并发
        - 失败可重跑，已完成文件自动跳过
    """
    try:
        import requests  # noqa: F401
    except ImportError:
        sys.exit("缺少 requests。请 `pip install requests tqdm`")

    dest.mkdir(parents=True, exist_ok=True)

    # 1) 元数据
    print(f"[python] 拉取元数据到 {dest}")
    for fname in META_FILES:
        try:
            _http_download_one(
                _DownloadTask(url=PTBXL_HTTP_BASE + fname, rel_path=fname),
                dest)
        except Exception as e:
            print(f"  [warn] {fname} 下载失败: {e}")

    if meta_only:
        print("[python] meta_only=True，跳过波形下载")
        return

    # 2) 波形
    waveform_paths = _enumerate_records_via_records_index(dest)
    print(f"[python] RECORDS 索引含 {len(waveform_paths)} 条记录")

    targets: List[_DownloadTask] = []
    for rec_path in waveform_paths:
        # rec_path 形如 records100/00000/00001_lr
        if resolution == 100 and "records500" in rec_path:
            continue
        if resolution == 500 and "records100" in rec_path:
            continue
        # 一条记录有 .dat 和 .hea 两个文件
        for ext in (".dat", ".hea"):
            targets.append(_DownloadTask(
                url=PTBXL_HTTP_BASE + rec_path + ext,
                rel_path=rec_path + ext,
            ))
        # 如果 resolution=None 且当前是 records100 路径，那 records500 文件也要拉
        # records500 路径不在 RECORDS 里，需要从 records100 推断
        if resolution is None and "records100" in rec_path:
            hr_path = rec_path.replace("records100", "records500").replace("_lr", "_hr")
            for ext in (".dat", ".hea"):
                targets.append(_DownloadTask(
                    url=PTBXL_HTTP_BASE + hr_path + ext,
                    rel_path=hr_path + ext,
                ))

    print(f"[python] 计划下载 {len(targets)} 个波形文件，并发 {max_workers}")
    from concurrent.futures import ThreadPoolExecutor, as_completed

    failed: List[str] = []
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_http_download_one, t, dest): t for t in targets}
        for fut in as_completed(futures):
            t = futures[fut]
            try:
                fut.result()
                completed += 1
                if completed % 200 == 0:
                    print(f"  [progress] {completed}/{len(targets)}")
            except Exception as e:
                failed.append(f"{t.rel_path}: {e}")

    print(f"[python] 完成 {completed}/{len(targets)} 个文件")
    if failed:
        log_path = dest / "_download_failures.log"
        log_path.write_text("\n".join(failed))
        print(f"[python] {len(failed)} 个失败，详见 {log_path}")


# ─── HuggingFace 镜像模式（国内首选） ───────────────────────────────────────

def _download_via_hf(dest: Path, endpoint: str, repo_id: str = HF_REPO_ID) -> None:
    """从 HuggingFace 镜像下载 BLOSSOM-framework/PTB-XL（parquet，744 MB）。

    优势:
        - 走 hf-mirror.com，国内访问稳定
        - parquet 格式紧凑，已切片 (1000, 12) ECG + 5 类 label
        - 与 ``backend/app/algorithms/ptbxl_dataset.py`` 的 parquet 加载分支配套
        - 预处理可直接读 parquet，跳过 wfdb 解码步骤

    数据 schema:
        - i_to_avf : float32 (1000, 6)  ← I, II, III, aVR, aVL, aVF
        - v1_to_v6 : float32 (1000, 6)  ← V1, V2, V3, V4, V5, V6
        - label    : 5 类 ClassLabel (NORM=0, MI=1, STTC=2, CD=3, HYP=4)
        - site_id  : str                ← 患者站点
        - split    : str                ← train / val / test
    """
    try:
        from huggingface_hub import snapshot_download  # type: ignore
    except ImportError:
        sys.exit("[hf] 缺少 huggingface_hub。请 `pip install huggingface_hub`")

    os.environ.setdefault("HF_ENDPOINT", endpoint)
    dest.mkdir(parents=True, exist_ok=True)

    print(f"[hf] endpoint = {os.environ.get('HF_ENDPOINT')}")
    print(f"[hf] 仓库     = {repo_id}")
    print(f"[hf] 目标目录 = {dest}")
    print("[hf] 下载约 744 MB parquet（数据 + README）。可断点续传，已下文件会跳过。")

    try:
        local_dir = snapshot_download(
            repo_id=repo_id,
            repo_type=HF_REPO_TYPE,
            local_dir=str(dest),
            local_dir_use_symlinks=False,
            allow_patterns=["data/*.parquet", "README.md"],
            max_workers=4,
        )
    except Exception as exc:
        print(f"[hf] 下载失败: {exc}")
        print("[hf] 请检查网络是否能访问 hf-mirror.com，或尝试 --mode wget/python")
        raise

    parquet_files = list(Path(local_dir).glob("data/*.parquet"))
    print(f"[hf] 完成。共 {len(parquet_files)} 个 parquet 文件:")
    for fp in parquet_files:
        size_mb = fp.stat().st_size / 1024 / 1024
        print(f"   - {fp.name}  ({size_mb:.1f} MB)")


# ─── SHA256 校验 ────────────────────────────────────────────────────────────

def _verify_checksums(dest: Path, sample: int = 50) -> None:
    """随机抽 sample 个文件做 SHA256 校验。完整校验需 1-2 小时，默认抽样。"""
    sumfile = dest / "SHA256SUMS.txt"
    if not sumfile.exists():
        print("[verify] 未找到 SHA256SUMS.txt，跳过")
        return

    import random
    entries = []
    for ln in sumfile.read_text().splitlines():
        ln = ln.strip()
        if not ln:
            continue
        parts = ln.split(maxsplit=1)
        if len(parts) == 2:
            entries.append(tuple(parts))  # (sha256_hex, rel_path)

    random.seed(0)
    chosen = random.sample(entries, min(sample, len(entries)))

    failed = []
    for sha, rel in chosen:
        rel = rel.lstrip("./")
        f = dest / rel
        if not f.exists():
            failed.append((rel, "missing"))
            continue
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            for blk in iter(lambda: fh.read(1 << 20), b""):
                h.update(blk)
        if h.hexdigest() != sha:
            failed.append((rel, "mismatch"))
    print(f"[verify] {len(chosen)} 抽样：{len(chosen) - len(failed)} 通过, "
          f"{len(failed)} 失败")
    if failed:
        for rel, why in failed[:10]:
            print(f"   - {rel}: {why}")


# ─── 主入口 ─────────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="下载 PTB-XL ECG 公开数据集",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--mode", choices=["hf", "python", "wget", "aws", "mock"],
                   default="hf",
                   help="hf=HuggingFace 镜像(国内推荐)；python=纯 Python; "
                        "wget=系统 wget; aws=AWS CLI; mock=仅 8 条假记录")
    p.add_argument("--dest", type=Path, default=None,
                   help=f"目标目录（默认 {DEFAULT_DEST}，hf 模式默认 {DEFAULT_DEST.parent / 'ptbxl_hf'}）")
    p.add_argument("--resolution", type=int, choices=[100, 500],
                   default=None,
                   help="只下指定采样率（100 或 500），不填则全下；HF 模式忽略此参数")
    p.add_argument("--workers", type=int, default=8,
                   help="--mode python 并发线程数")
    p.add_argument("--meta-only", action="store_true",
                   help="--mode python 只拉元数据 CSV，不下波形（≈ 6 MB，秒级）")
    p.add_argument("--mock-records", type=int, default=8,
                   help="--mode mock 生成多少条假记录")
    p.add_argument("--verify", action="store_true",
                   help="下载完后随机抽 50 个文件做 SHA256 校验")
    p.add_argument("--hf-endpoint", default=HF_DEFAULT_ENDPOINT,
                   help=f"HuggingFace endpoint（默认 {HF_DEFAULT_ENDPOINT}, "
                        f"想用官方设 https://huggingface.co）")
    p.add_argument("--hf-repo", default=HF_REPO_ID,
                   help=f"HuggingFace 数据集仓库（默认 {HF_REPO_ID}）")
    args = p.parse_args(argv)

    if args.dest is None:
        dest = (DEFAULT_DEST.parent / "ptbxl_hf") if args.mode == "hf" else DEFAULT_DEST
    else:
        dest = args.dest
    dest = dest.resolve()
    print(f"==> 目标目录: {dest}")
    print(f"==> 模式: {args.mode}")

    if args.mode == "mock":
        _make_mock_dataset(dest, n_records=args.mock_records)
    elif args.mode == "hf":
        _download_via_hf(dest, endpoint=args.hf_endpoint, repo_id=args.hf_repo)
    elif args.mode == "wget":
        _download_via_wget(dest, args.resolution)
    elif args.mode == "aws":
        _download_via_aws(dest, args.resolution)
    else:
        _download_via_python(dest, args.resolution,
                             max_workers=args.workers,
                             meta_only=args.meta_only)

    if args.verify and args.mode not in ("mock", "hf"):
        _verify_checksums(dest)

    print("\n下一步:")
    if args.mode == "hf":
        print(f"  python scripts/train_ptbxl_ecg.py --source hf --hf-data-dir {dest}")
    else:
        print(f"  python scripts/preprocess_ptbxl.py --src {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
