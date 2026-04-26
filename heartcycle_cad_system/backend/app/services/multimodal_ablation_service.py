"""
多模态消融实验：加载 H5 → 固定划分 → 调用 algorithms.multimodal_ablation
"""
import importlib.util
import logging
import sys
import types
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

_backend_root = Path(__file__).resolve().parents[2]
_algorithms_dir = _backend_root / "algorithms"
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

# 与 multimodal_service 一致：显式注册本项目的 algorithms，避免与其它同名包冲突
if "algorithms" not in sys.modules:
    _alg_pkg = types.ModuleType("algorithms")
    _alg_pkg.__path__ = [str(_algorithms_dir)]
    _alg_pkg.__package__ = "algorithms"
    sys.modules["algorithms"] = _alg_pkg

if "algorithms.multimodal_fusion" not in sys.modules:
    _mm_path = _algorithms_dir / "multimodal_fusion.py"
    _mm_spec = importlib.util.spec_from_file_location(
        "algorithms.multimodal_fusion", _mm_path
    )
    _mm_mod = importlib.util.module_from_spec(_mm_spec)
    sys.modules["algorithms.multimodal_fusion"] = _mm_mod
    _mm_spec.loader.exec_module(_mm_mod)

if "algorithms.multimodal_ablation" not in sys.modules:
    _ab_path = _algorithms_dir / "multimodal_ablation.py"
    _ab_spec = importlib.util.spec_from_file_location(
        "algorithms.multimodal_ablation", _ab_path
    )
    _ab_mod = importlib.util.module_from_spec(_ab_spec)
    sys.modules["algorithms.multimodal_ablation"] = _ab_mod
    _ab_spec.loader.exec_module(_ab_mod)

_run_ab = sys.modules["algorithms.multimodal_ablation"]
_fusion = sys.modules["algorithms.multimodal_fusion"]
run_multimodal_ablation = _run_ab.run_multimodal_ablation
ecg_to_cnn_input = _fusion.ecg_to_cnn_input

from .multimodal_service import (
    _generate_demo_labels,
    _hrv_dict_to_vector,
    _read_ecg_from_h5,
    _read_hrv_from_h5,
    label_for_h5_path,
    load_h5_label_mapping,
)
from ..core.config import settings

logger = logging.getLogger(__name__)


class MultiModalAblationService:
    def run(
        self,
        h5_files: List[str],
        label_file: Optional[str] = None,
        random_state: int = 42,
        test_size: float = 0.2,
        val_size: float = 0.2,
        fs: float = 500.0,
        epochs: int = 25,
        batch_size: int = 16,
        learning_rate: float = 0.001,
        configs: Optional[List[str]] = None,
        include_sample_weight_ablation: bool = True,
        persist: bool = False,
        strict_labels: bool = True,
    ) -> Dict[str, Any]:
        import json

        hrv_list: List[np.ndarray] = []
        ecg_list: List[np.ndarray] = []
        valid_files: List[str] = []

        for fp in h5_files:
            ecg = _read_ecg_from_h5(fp, max_len=int(fs * 60))
            hrv_vec = _hrv_dict_to_vector(_read_hrv_from_h5(fp))
            if ecg is None or len(ecg) < 100:
                logger.warning("跳过（ECG 过短或缺失）: %s", fp)
                continue
            hrv_list.append(hrv_vec)
            ecg_list.append(ecg)
            valid_files.append(fp)

        n = len(valid_files)
        if n < 6:
            raise ValueError(
                f"有效样本不足（{n}），消融至少需要约 6 条以上以便分层划分。"
            )

        if label_file:
            try:
                file_to_label = load_h5_label_mapping(label_file)
            except Exception as e:
                if strict_labels:
                    raise ValueError(
                        f"标签 CSV 解析失败：{e}。strict_labels=True 下不允许回退到随机标签。"
                    ) from e
                logger.warning("标签 CSV 解析失败但 strict_labels=False，回退随机：%s", e)
                labels = _generate_demo_labels(n)
            else:
                labels = np.array(
                    [label_for_h5_path(fp, file_to_label) for fp in valid_files],
                    dtype=np.int32,
                )
                n_pos = int(labels.sum())
                if n_pos == 0 or n_pos == n:
                    msg = f"标签全为同一类（{n_pos}/{n}），消融实验需二分类样本。"
                    if strict_labels:
                        raise ValueError(msg)
                    logger.warning(msg + "（strict_labels=False，回退随机）")
                    labels = _generate_demo_labels(n)
        else:
            if strict_labels:
                raise ValueError(
                    "未提供 label_file。strict_labels=True（默认）下消融实验不允许使用随机演示标签——"
                    " 否则各配置之间的 AUC/F1 对比毫无意义。"
                    " 仅冒烟测试时显式传 strict_labels=False。"
                )
            labels = _generate_demo_labels(n)

        X_hrv = np.stack(hrv_list, axis=0).astype(np.float32)
        stft_ch: List[np.ndarray] = []
        dual_ch: List[np.ndarray] = []
        for ecg in ecg_list:
            stft_ch.append(
                ecg_to_cnn_input(np.asarray(ecg, dtype=np.float32), fs=fs, image_mode="stft_only")
            )
            dual_ch.append(
                ecg_to_cnn_input(np.asarray(ecg, dtype=np.float32), fs=fs, image_mode="dual")
            )
        X_img_stft = np.stack(stft_ch, axis=0)
        X_img_dual = np.stack(dual_ch, axis=0)

        result = run_multimodal_ablation(
            X_hrv,
            X_img_stft,
            X_img_dual,
            labels,
            random_state=random_state,
            test_size=test_size,
            val_size=val_size,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
            configs=configs,
            include_sample_weight_ablation=include_sample_weight_ablation,
        )
        result["valid_files_count"] = n
        result["label_source"] = "csv" if label_file else "demo_or_generated"

        if persist:
            out_dir = Path(settings.MODELS_DIR)
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = out_dir / f"multimodal_ablation_{ts}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            result["saved_path"] = str(path)
            logger.info("消融结果已写入 %s", path)

        return result
