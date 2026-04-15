"""
多模态融合模型服务
"""
import sys
import os
import numpy as np
import h5py
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# 确保 backend 目录在路径中（使 algorithms 包可被导入）
_backend_dir = str(Path(__file__).resolve().parents[2])
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# 用 importlib 按绝对路径预加载 multimodal_fusion，避免 sys.path 问题
import importlib.util as _ilu
import types as _types

# 注册 algorithms 包本身（如果尚未存在）
if "algorithms" not in sys.modules:
    _alg_pkg = _types.ModuleType("algorithms")
    _alg_pkg.__path__ = [str(Path(__file__).resolve().parents[2] / "algorithms")]
    _alg_pkg.__package__ = "algorithms"
    sys.modules["algorithms"] = _alg_pkg

# 加载 multimodal_fusion 模块
if "algorithms.multimodal_fusion" not in sys.modules:
    _mm_path = Path(__file__).resolve().parents[2] / "algorithms" / "multimodal_fusion.py"
    _mm_spec = _ilu.spec_from_file_location("algorithms.multimodal_fusion", _mm_path)
    _mm_mod  = _ilu.module_from_spec(_mm_spec)
    sys.modules["algorithms.multimodal_fusion"] = _mm_mod
    _mm_spec.loader.exec_module(_mm_mod)

from ..core.config import settings

logger = logging.getLogger(__name__)


# ─── H5 数据读取工具 ──────────────────────────────────────────────────────────

def _read_ecg_from_h5(h5_file: str, max_len: int = 10000) -> Optional[np.ndarray]:
    """从 H5 文件中读取 ECG 信号（_030 键）。"""
    try:
        with h5py.File(h5_file, 'r') as f:
            measure = f.get('measure', {}).get('value', {})
            if measure and '_030' in measure:
                ecg = measure['_030']['value']['data']['value'][0, :]
                ecg = np.asarray(ecg, dtype=np.float32)
                if len(ecg) > max_len:
                    ecg = ecg[:max_len]
                return ecg
    except Exception as e:
        logger.warning(f"读取 ECG 失败 {h5_file}: {e}")
    return None


def _read_hrv_from_h5(h5_file: str) -> Optional[Dict[str, float]]:
    """
    从 H5 文件中提取 HRV 特征（使用现有 feature_extraction 管线）。
    失败时返回全零占位特征。
    """
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        from algorithms.feature_extraction import HRVFeatureExtractor
        extractor = HRVFeatureExtractor()
        features = extractor.extract_all(
            h5_file,
            use_existing_rpeaks=True,
            extract_hrv=True,
            extract_clinical=False,
        )
        return features
    except Exception as e:
        logger.warning(f"HRV 提取失败 {h5_file}: {e}")
        return None


# HRV 特征顺序（固定，确保训练与推理一致）
_HRV_FEATURE_KEYS = [
    'mean_rr', 'std_rr', 'min_rr', 'max_rr', 'median_rr',
    'sdnn', 'rmssd', 'pnn50', 'pnn20', 'cv', 'cvsd', 'sdann',
    'range_rr', 'q1_rr', 'q3_rr', 'iqr_rr', 'sdsd',
    'hrv_triangular_index', 'tinn', 'mean_hr',
    'total_power', 'vlf_power', 'lf_power', 'hf_power',
    'lf_hf_ratio', 'lf_norm', 'hf_norm',
    'vlf_percent', 'lf_percent', 'hf_percent',
    'lf_peak', 'hf_peak',
    'log_total_power', 'log_lf_power', 'log_hf_power',
    'spectral_entropy',
    'sd1', 'sd2', 'sd1_sd2_ratio',
    'sample_entropy', 'approximate_entropy',
    'dfa_alpha1', 'dfa_alpha2',
    'ac', 'dc', 'complexity_index',
]


def _hrv_dict_to_vector(hrv_dict: Optional[Dict]) -> np.ndarray:
    """将 HRV 特征字典转换为固定长度向量（缺失值补 0）。"""
    if hrv_dict is None:
        return np.zeros(len(_HRV_FEATURE_KEYS), dtype=np.float32)
    vec = []
    for k in _HRV_FEATURE_KEYS:
        v = hrv_dict.get(k, 0.0)
        try:
            vec.append(float(v) if not (np.isnan(float(v)) or np.isinf(float(v))) else 0.0)
        except Exception:
            vec.append(0.0)
    return np.array(vec, dtype=np.float32)


# ─── 标签生成 ─────────────────────────────────────────────────────────────────

def _generate_demo_labels(n: int, cad_ratio: float = 0.35, seed: int = 42) -> np.ndarray:
    """若 H5 文件无真实标签，自动生成演示标签（约 35% 阳性）。"""
    rng = np.random.RandomState(seed)
    labels = (rng.rand(n) < cad_ratio).astype(np.int32)
    logger.warning(
        f"使用演示标签（{int(labels.sum())} 阳性 / {n} 总计），"
        "正式使用请提供真实标签文件。"
    )
    return labels


def _norm_csv_col(name: Any) -> str:
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")


def _coerce_label_cell(raw: Any) -> int:
    """数值或文本疾病状态（如 HeartCycle SubjectMetadata 的 Healthy）转为 0/1。"""
    import math

    import numpy as np
    import pandas as pd

    if pd.isna(raw):
        return 0
    if isinstance(raw, (bool, np.bool_)):
        return int(raw)
    if isinstance(raw, (int, np.integer)):
        return int(raw)
    if isinstance(raw, float):
        if math.isnan(raw):
            return 0
        return int(raw)
    s = str(raw).strip().lower()
    if not s or s == "nan":
        return 0
    try:
        return int(float(s.replace(",", ".")))
    except ValueError:
        pass
    if "unhealthy" in s:
        return 1
    if "healthy" in s or s in ("normal", "control", "negative", "hc"):
        return 0
    if any(k in s for k in ("cad", "chd", "coronary", "patient", "disease", "positive")):
        return 1
    if s in ("0", "no", "false"):
        return 0
    if s in ("1", "yes", "true"):
        return 1
    logger.warning("未识别标签文本 %r，按 0 处理", raw)
    return 0


def load_h5_label_mapping(label_file: str) -> Dict[str, int]:
    """
    从 CSV 读取「路径 -> 标签」。
    - 路径列：file_path / path / file_name(File_Name) / filepath 等，或第一列
    - 标签列：label / disease_status(Disease_Status) / y / target 等
    - 支持 HeartCycle *SubjectMetadata.csv（File_Name + Disease_Status）
    - *FileMetadata.csv 为通道说明表，不可用，会明确报错
    """
    import os

    import pandas as pd

    base_l = os.path.basename(label_file).lower()
    if "filemetadata" in base_l and "subject" not in base_l:
        raise ValueError(
            "所选文件是 HeartCycle 的 FileMetadata.csv（记录各信号通道含义），不能作为训练标签。"
            "请改用同目录下的 *_SubjectMetadata.csv（含 File_Name、Disease_Status），"
            "或自建两列表格：路径列 + 数值标签列（0/1）。"
        )

    df = pd.read_csv(label_file)
    if df.empty:
        raise ValueError("标签 CSV 为空")

    c0n = _norm_csv_col(df.columns[0])
    if len(df.columns) <= 3 and ("niccomo" in c0n or "stethoscope" in c0n):
        raise ValueError(
            "该 CSV 表头像 HeartCycle FileMetadata（信号说明），不是受试者标签表。"
            "请使用 SubjectMetadata.csv 或含 file_path + label 的文件。"
        )

    orig_by_norm = {_norm_csv_col(c): c for c in df.columns}
    path_candidates = (
        "file_path",
        "path",
        "filepath",
        "h5_path",
        "file_name",
        "filename",
        "file",
    )
    path_col = None
    for cand in path_candidates:
        if cand in orig_by_norm:
            path_col = orig_by_norm[cand]
            break
    if path_col is None:
        path_col = df.columns[0]

    label_col = None
    for cand in ("label", "disease_status", "y", "target", "cad", "class"):
        if cand in orig_by_norm:
            c0 = orig_by_norm[cand]
            if c0 != path_col:
                label_col = c0
                break
    if label_col is None:
        for c in df.columns:
            if c != path_col:
                label_col = c
                break
    if label_col is None:
        raise ValueError("标签 CSV 需包含标签列（如 label 或 Disease_Status）")

    mapping: Dict[str, int] = {}
    for _, row in df.iterrows():
        p = str(row[path_col]).strip()
        if not p or p.lower() in ("nan", "none"):
            continue
        yv = _coerce_label_cell(row[label_col])
        stem = p[:-3] if p.lower().endswith(".h5") else p
        mapping[p] = yv
        mapping[os.path.normpath(p)] = yv
        mapping[os.path.basename(p)] = yv
        mapping[stem] = yv
        mapping[os.path.basename(stem)] = yv
    if not mapping:
        raise ValueError("标签 CSV 未解析到任何有效行")
    return mapping


def label_for_h5_path(h5_path: str, file_to_label: Dict[str, int]) -> int:
    """按完整路径、规范化路径、文件名或去扩展名匹配（对齐 SubjectMetadata 的 File_Name）。"""
    import os

    if h5_path in file_to_label:
        return int(file_to_label[h5_path])
    norm = os.path.normpath(h5_path)
    if norm in file_to_label:
        return int(file_to_label[norm])
    base = os.path.basename(h5_path)
    if base in file_to_label:
        return int(file_to_label[base])
    stem, _ext = os.path.splitext(base)
    if stem and stem in file_to_label:
        return int(file_to_label[stem])
    return 0


# ─── 服务类 ───────────────────────────────────────────────────────────────────

class MultiModalService:
    """多模态融合模型服务"""

    def __init__(self):
        self.models_dir = Path(settings.MODELS_DIR)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    # ── 训练入口 ──────────────────────────────────────────────────────────────

    def train(
        self,
        h5_files: List[str],
        epochs: int = 30,
        batch_size: int = 16,
        learning_rate: float = 0.001,
        test_size: float = 0.2,
        val_size: float = 0.2,
        fs: float = 500.0,
        label_file: Optional[str] = None,
        image_mode: str = "dual",
        fusion_mode: str = "interactive",
        use_class_weights: bool = True,
        random_state: int = 42,
    ) -> Dict:
        """
        从 H5 文件列表训练多模态融合模型。

        Parameters
        ----------
        h5_files   : H5 文件路径列表（每个文件 = 一个受试者）
        epochs     : 训练轮数
        batch_size : 批次大小
        learning_rate : 学习率
        test_size  : 测试集比例
        val_size   : 验证集比例（从训练集中划分）
        fs         : ECG 采样率（Hz）
        label_file : 可选 CSV 文件，含 file_path 和 label 两列
        image_mode : stft_only（单通道 STFT）| dual（STFT+CWT 双通道）
        fusion_mode : concat（原版拼接）| interactive（HRV-CNN Hadamard 交互）
        use_class_weights : 是否对训练集使用 balanced sample_weight
        random_state : 划分与 TensorFlow 随机种子，便于复现
        """
        from algorithms.multimodal_fusion import MultiModalTrainer

        logger.info(f"多模态训练开始，文件数={len(h5_files)}，random_state={random_state}")

        # ── 1. 读取数据 ────────────────────────────────────────────────────────
        hrv_list: List[np.ndarray] = []
        ecg_list: List[np.ndarray] = []
        valid_files: List[str] = []

        for fp in h5_files:
            ecg = _read_ecg_from_h5(fp, max_len=int(fs * 60))  # 最长 60 秒
            hrv_dict = _read_hrv_from_h5(fp)
            hrv_vec = _hrv_dict_to_vector(hrv_dict)

            if ecg is None or len(ecg) < 100:
                logger.warning(f"跳过（ECG 过短或缺失）: {fp}")
                continue

            hrv_list.append(hrv_vec)
            ecg_list.append(ecg)
            valid_files.append(fp)

        if len(valid_files) < 4:
            raise ValueError(
                f"有效样本不足（{len(valid_files)} 个），无法训练。"
                "请确保 H5 文件包含 measure/value/_030 路径的 ECG 数据。"
            )

        n = len(valid_files)
        logger.info(f"有效样本数: {n}")

        # ── 2. 标签 ────────────────────────────────────────────────────────────
        label_source = "demo_random"
        if label_file:
            file_to_label = load_h5_label_mapping(label_file)
            labels = np.array(
                [label_for_h5_path(fp, file_to_label) for fp in valid_files],
                dtype=np.int32,
            )
            n_pos = int(labels.sum())
            if n_pos == 0 or n_pos == n:
                logger.warning("标签全为同一类，切换到演示标签")
                labels = _generate_demo_labels(n)
                label_source = "demo_fallback_single_class"
            else:
                label_source = "csv"
        else:
            labels = _generate_demo_labels(n)

        # ── 3. 准备数据集 ─────���────────────────────────────────────────────────
        trainer = MultiModalTrainer(random_state=random_state)
        (X_hrv_tr, X_img_tr, y_tr,
         X_hrv_va, X_img_va, y_va,
         X_hrv_te, X_img_te, y_te) = trainer.prepare_dataset(
            hrv_list, ecg_list, labels,
            fs=fs, test_size=test_size, val_size=val_size,
            image_mode=image_mode,
        )

        # ── 4. 训练 ────────────────────────────────────────────────────────────
        history = trainer.train(
            X_hrv_tr, X_img_tr, y_tr,
            X_hrv_va, X_img_va, y_va,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
            fusion_mode=fusion_mode,
            use_class_weights=use_class_weights,
        )

        # ── 5. 评估 ────────────────────────────────────────────────────────────
        results = trainer.evaluate(X_hrv_te, X_img_te, y_te)

        # ── 6. 保存 ────────────────────────────────────────────────────────────
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_id = f"mm_fusion_{timestamp}"
        trainer.save(str(self.models_dir), model_id)

        # 保存元数据
        # history 的 value 可能含 numpy float，需转换
        def _safe(v):
            if isinstance(v, list):
                return [float(x) for x in v]
            return v

        hist_dict = {k: _safe(v) for k, v in history.items()}
        best_val_auc = None
        best_val_loss = None
        if isinstance(hist_dict, dict):
            va = hist_dict.get("val_auc")
            if isinstance(va, list) and va:
                best_val_auc = float(max(va))
            vl = hist_dict.get("val_loss")
            if isinstance(vl, list) and vl:
                best_val_loss = float(min(vl))

        loss_hist = hist_dict.get("loss") if isinstance(hist_dict, dict) else None
        epochs_trained = len(loss_hist) if isinstance(loss_hist, list) else 0

        metadata = {
            'model_id': model_id,
            'model_type': 'multimodal_fusion',
            'n_hrv_features': trainer.n_hrv_features,
            'image_mode': getattr(trainer, 'image_mode', image_mode),
            'img_channels': getattr(trainer, 'img_channels', 1),
            'fusion_mode': getattr(trainer, 'fusion_mode', fusion_mode),
            'use_class_weights': use_class_weights,
            'random_state': random_state,
            'label_source': label_source,
            'label_file': label_file,
            'test_size': test_size,
            'val_size': val_size,
            'hrv_feature_keys': _HRV_FEATURE_KEYS,
            'num_samples': n,
            'train_samples': int(X_hrv_tr.shape[0]),
            'val_samples': int(X_hrv_va.shape[0]),
            'test_samples': int(X_hrv_te.shape[0]),
            'epochs': epochs,
            'epochs_trained': epochs_trained,
            'batch_size': batch_size,
            'learning_rate': learning_rate,
            'fs': fs,
            'created_at': timestamp,
            'results': results,
            'history': hist_dict,
            'best_val_auc': best_val_auc,
            'best_val_loss': best_val_loss,
        }
        meta_path = self.models_dir / f"{model_id}_mm_metadata.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"多模态模型已保存: {model_id}")

        return {
            'model_id': model_id,
            'test_accuracy': results['test_accuracy'],
            'test_auc': results['test_auc'],
            'confusion_matrix': results['confusion_matrix'],
            'n_samples': n,
            'history': metadata['history'],
            'metadata': metadata,
        }

    # ── 预测 ──────────────────────────────────────────────────────────────────

    def predict_from_h5(
        self,
        model_id: str,
        h5_file: str,
        fs: float = 500.0,
    ) -> Dict:
        """
        从 H5 文件进行多模态预测。
        自动提取 HRV 特征 + ECG 信号后调用模型。
        """
        from algorithms.multimodal_fusion import MultiModalTrainer

        meta_path = self.models_dir / f"{model_id}_mm_metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"模型元数据不存在: {meta_path}")
        with open(meta_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        trainer = MultiModalTrainer()
        trainer.n_hrv_features = metadata['n_hrv_features']
        trainer.load(str(self.models_dir), model_id)

        ecg = _read_ecg_from_h5(h5_file, max_len=int(fs * 60))
        hrv_dict = _read_hrv_from_h5(h5_file)
        hrv_vec = _hrv_dict_to_vector(hrv_dict)

        if ecg is None or len(ecg) < 100:
            raise ValueError("H5 文件中未找到有效 ECG 信号")

        pred_class, proba = trainer.predict(hrv_vec, ecg, fs=fs)

        return {
            'model_id': model_id,
            'prediction': pred_class,
            'probability': proba,
            'confidence': float(max(proba)),
            'h5_file': h5_file,
        }

    def predict_from_vectors(
        self,
        model_id: str,
        hrv_vector: List[float],
        ecg_signal: List[float],
        fs: float = 500.0,
    ) -> Dict:
        """
        直接使用特征向量和 ECG 信号进行预测（用于 Monitor 页面）。
        """
        from algorithms.multimodal_fusion import MultiModalTrainer

        meta_path = self.models_dir / f"{model_id}_mm_metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"模型元数据不存在: {meta_path}")
        with open(meta_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        trainer = MultiModalTrainer()
        trainer.n_hrv_features = metadata['n_hrv_features']
        trainer.load(str(self.models_dir), model_id)

        hrv_vec = np.asarray(hrv_vector, dtype=np.float32)
        ecg_arr = np.asarray(ecg_signal, dtype=np.float32)

        pred_class, proba = trainer.predict(hrv_vec, ecg_arr, fs=fs)

        return {
            'model_id': model_id,
            'prediction': pred_class,
            'probability': proba,
            'confidence': float(max(proba)),
        }

    # ── 列表 / 删除 ───────────────────────────────────────────────────────────

    def list_models(self) -> List[Dict]:
        """列出所有多模态融合模型"""
        result = []
        for meta_file in self.models_dir.glob("mm_fusion_*_mm_metadata.json"):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                result.append({
                    'model_id': meta['model_id'],
                    'model_type': 'multimodal_fusion',
                    'test_accuracy': meta['results']['test_accuracy'],
                    'test_auc': meta['results']['test_auc'],
                    'n_samples': meta.get('num_samples', 0),
                    'n_hrv_features': meta.get('n_hrv_features', 0),
                    'created_at': meta['created_at'],
                    'image_mode': meta.get('image_mode'),
                    'fusion_mode': meta.get('fusion_mode'),
                    'img_channels': meta.get('img_channels'),
                    'label_source': meta.get('label_source'),
                    'best_val_auc': meta.get('best_val_auc'),
                    'epochs_trained': meta.get('epochs_trained'),
                    'epochs': meta.get('epochs'),
                })
            except Exception as e:
                logger.error(f"读取元数据失败 {meta_file}: {e}")
        return sorted(result, key=lambda x: x['created_at'], reverse=True)

    def delete_model(self, model_id: str) -> bool:
        """删除多模态模型所有文件"""
        suffixes = ['_mm.h5', '_mm_scaler.pkl', '_mm_metadata.json']
        for s in suffixes:
            p = self.models_dir / f"{model_id}{s}"
            if p.exists():
                p.unlink()
        logger.info(f"多模态模型已删除: {model_id}")
        return True

    def get_model_info(self, model_id: str) -> Dict:
        """获取单个模型详情"""
        meta_path = self.models_dir / f"{model_id}_mm_metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"模型不存在: {model_id}")
        with open(meta_path, 'r', encoding='utf-8') as f:
            return json.load(f)
