"""
深度学习模型服务
"""
import os
import numpy as np
import h5py
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import json

from ..algorithms.deep_learning import DeepLearningModel
from ..algorithms.calibration import ModelCalibrator, calibrate_model, CalibratedModel
from ..core.config import settings
from .multimodal_service import _read_ecg_from_h5, _generate_demo_labels

logger = logging.getLogger(__name__)


def _resolve_h5_training_path(raw: str) -> Optional[Path]:
    """
    将前端传来的路径解析为服务器上真实存在的文件。
    先按原路径；不存在则用 UPLOAD_DIR + 文件名（避免盘符/斜杠不一致）。
    """
    if not raw or not str(raw).strip():
        return None
    s = os.path.normpath(str(raw).strip())
    p = Path(s)
    if p.is_file():
        return p
    name = p.name
    if not name:
        return None
    cand = Path(os.path.normpath(os.path.join(settings.UPLOAD_DIR, name)))
    if cand.is_file():
        logger.info("H5 路径回退到上传目录: %s -> %s", raw, cand)
        return cand
    return None


class DeepLearningService:
    """深度学习模型服务"""

    def __init__(self):
        self.models_dir = Path(settings.MODELS_DIR)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def load_ecg_data_from_h5(
        self,
        h5_files: List[str],
        signal_length: int = 5000
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        从 H5 文件加载 ECG 数据

        Parameters:
        -----------
        h5_files : List[str]
            H5 文件路径列表
        signal_length : int
            信号长度（采样点数）

        Returns:
        --------
        X, y : ECG 信号和标签
        """
        X_list: List[np.ndarray] = []
        y_list: List[Optional[int]] = []

        for h5_file in h5_files:
            resolved = _resolve_h5_training_path(h5_file)
            if resolved is None:
                logger.warning("H5 不存在或不可读: %s", h5_file)
                continue
            p = str(resolved)
            ecg: Optional[np.ndarray] = None
            label: Optional[int] = None
            try:
                with h5py.File(p, 'r') as f:
                    if 'ecg' in f:
                        ecg = np.asarray(f['ecg'][:], dtype=np.float32).ravel()
                    elif 'signal' in f:
                        ecg = np.asarray(f['signal'][:], dtype=np.float32).ravel()

                    if ecg is None or len(ecg) < 10:
                        # HeartCycle：measure/_030（与多模态训练一致）
                        ecg = _read_ecg_from_h5(
                            p, max_len=max(signal_length, 30000)
                        )
                        if ecg is not None:
                            ecg = np.asarray(ecg, dtype=np.float32).ravel()

                    if ecg is None or len(ecg) < 10:
                        logger.warning("文件 %s 中未读到有效 ECG", p)
                        continue

                    if 'label' in f:
                        label = int(np.asarray(f['label'][()]).ravel()[0])
                    elif 'cad' in f:
                        label = int(np.asarray(f['cad'][()]).ravel()[0])

                if len(ecg) > signal_length:
                    ecg = ecg[:signal_length]
                else:
                    ecg = np.pad(ecg, (0, signal_length - len(ecg)), mode='constant')

                X_list.append(ecg.astype(np.float32))
                y_list.append(label)
            except Exception as e:
                logger.error("读取文件 %s 失败: %s", h5_file, e)
                continue

        if not X_list:
            raise ValueError("没有成功加载任何数据")

        if all(v is None for v in y_list):
            logger.warning(
                "所选 H5 根级无 label/cad（HeartCycle 常见）；已用演示二分类标签，"
                "论文/上线请使用带标签数据或后续标签 CSV 接口。"
            )
            y = _generate_demo_labels(len(X_list))
        else:
            y = np.array(
                [0 if v is None else int(v) for v in y_list],
                dtype=np.int32,
            )

        X = np.array(X_list)

        logger.info(f"加载了 {len(X)} 个样本，信号长度: {signal_length}")
        logger.info(f"标签分布: {np.bincount(y)}")

        return X, y

    def train_deep_model(
        self,
        h5_files: List[str],
        model_type: str = 'cnn',
        signal_length: int = 5000,
        epochs: int = 50,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        test_size: float = 0.2,
        validation_split: float = 0.2,
        use_calibration: bool = True,
        calibration_method: str = 'platt'
    ) -> Dict:
        """
        训练深度学习模型

        Parameters:
        -----------
        h5_files : List[str]
            H5 文件路径列表
        model_type : str
            模型类型: 'cnn', 'lstm', 'gru', 'cnn_lstm'
        signal_length : int
            信号长度
        epochs : int
            训练轮数
        batch_size : int
            批次大小
        learning_rate : float
            学习率
        test_size : float
            测试集比例
        validation_split : float
            验证集比例
        use_calibration : bool
            是否使用模型校准
        calibration_method : str
            校准方法

        Returns:
        --------
        训练结果字典
        """
        logger.info(f"开始训练深度学习模型: {model_type}")

        # 加载数据
        X, y = self.load_ecg_data_from_h5(h5_files, signal_length)

        # 创建模型
        model = DeepLearningModel(
            model_type=model_type,
            input_shape=(signal_length, 1),
            num_classes=2
        )

        # 准备数据
        X_train, X_val, X_test, y_train, y_val, y_test = model.prepare_data(
            X, y, test_size=test_size, validation_split=validation_split
        )

        # 训练
        history = model.train(
            X_train, y_train,
            X_val, y_val,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate
        )

        # 评估
        results = model.evaluate(X_test, y_test)

        # 模型校准
        calibrator = None
        calibration_metrics = None
        if use_calibration:
            logger.info("开始模型校准...")
            try:
                # 使用验证集进行校准
                y_val_true = np.argmax(y_val, axis=1)
                y_val_pred_proba = model.model.predict(X_val)

                calibrator = ModelCalibrator(method=calibration_method)
                calibrator.fit(y_val_true, y_val_pred_proba)

                # 在测试集上评估校准效果
                y_test_true = np.argmax(y_test, axis=1)
                y_test_pred_proba = model.model.predict(X_test)
                y_test_calibrated_proba = calibrator.transform(y_test_pred_proba)

                from ..algorithms.calibration import plot_calibration_curve
                calibration_metrics = plot_calibration_curve(
                    y_test_true,
                    y_test_pred_proba,
                    y_test_calibrated_proba
                )

                logger.info(f"校准完成，ECE: {calibration_metrics['expected_calibration_error']:.4f} -> "
                           f"{calibration_metrics.get('expected_calibration_error_calibrated', 0):.4f}")

            except Exception as e:
                logger.error(f"模型校准失败: {e}")
                calibrator = None

        # 保存模型
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_id = f"{model_type}_dl_{timestamp}"
        model_path = self.models_dir / f"{model_id}.h5"
        scaler_path = self.models_dir / f"{model_id}_scaler.pkl"
        calibrator_path = self.models_dir / f"{model_id}_calibrator.pkl"

        model.save(str(model_path), str(scaler_path))

        if calibrator:
            calibrator.save(str(calibrator_path))

        # 保存元数据
        metadata = {
            'model_id': model_id,
            'model_type': model_type,
            'signal_length': signal_length,
            'num_samples': len(X),
            'train_samples': len(X_train),
            'val_samples': len(X_val),
            'test_samples': len(X_test),
            'epochs': epochs,
            'batch_size': batch_size,
            'learning_rate': learning_rate,
            'use_calibration': use_calibration,
            'calibration_method': calibration_method if use_calibration else None,
            'created_at': timestamp,
            'model_path': str(model_path),
            'scaler_path': str(scaler_path),
            'calibrator_path': str(calibrator_path) if calibrator else None,
            'results': results,
            'history': history,
            'calibration_metrics': calibration_metrics
        }

        metadata_path = self.models_dir / f"{model_id}_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"模型已保存: {model_id}")

        return {
            'model_id': model_id,
            'model_type': model_type,
            'test_accuracy': results['test_accuracy'],
            'test_auc': results['test_auc'],
            'calibration_metrics': calibration_metrics,
            'metadata': metadata
        }

    def predict_with_deep_model(
        self,
        model_id: str,
        ecg_signal: np.ndarray
    ) -> Dict:
        """
        使用深度学习模型预测

        Parameters:
        -----------
        model_id : str
            模型ID
        ecg_signal : np.ndarray
            ECG 信号 (n_samples, signal_length) 或 (signal_length,)

        Returns:
        --------
        预测结果
        """
        # 加载模型
        model_path = self.models_dir / f"{model_id}.h5"
        scaler_path = self.models_dir / f"{model_id}_scaler.pkl"
        calibrator_path = self.models_dir / f"{model_id}_calibrator.pkl"

        if not model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_path}")

        # 加载元数据
        metadata_path = self.models_dir / f"{model_id}_metadata.json"
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        model_type = metadata['model_type']
        signal_length = metadata['signal_length']

        # 创建模型并加载
        model = DeepLearningModel(
            model_type=model_type,
            input_shape=(signal_length, 1),
            num_classes=2
        )
        model.load(str(model_path), str(scaler_path))

        # 确保输入形状正确
        if ecg_signal.ndim == 1:
            ecg_signal = ecg_signal.reshape(1, -1)

        # 调整信号长度
        if ecg_signal.shape[1] != signal_length:
            if ecg_signal.shape[1] > signal_length:
                ecg_signal = ecg_signal[:, :signal_length]
            else:
                pad_width = ((0, 0), (0, signal_length - ecg_signal.shape[1]))
                ecg_signal = np.pad(ecg_signal, pad_width, mode='constant')

        # 预测
        predictions, probabilities = model.predict(ecg_signal)

        # 如果有校准器，使用校准后的概率
        if calibrator_path.exists():
            calibrator = ModelCalibrator(method=metadata.get('calibration_method', 'platt'))
            calibrator.load(str(calibrator_path))
            probabilities = calibrator.transform(probabilities)
            # 重新计算预测类别
            predictions = (probabilities[:, 1] >= 0.5).astype(int)

        results = {
            'predictions': predictions.tolist(),
            'probabilities': probabilities.tolist(),
            'model_id': model_id,
            'model_type': model_type,
            'calibrated': calibrator_path.exists()
        }

        return results

    def list_deep_models(self) -> List[Dict]:
        """列出所有深度学习模型"""
        models = []

        for metadata_file in self.models_dir.glob("*_dl_*_metadata.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    models.append({
                        'model_id': metadata['model_id'],
                        'model_type': metadata['model_type'],
                        'test_accuracy': metadata['results']['test_accuracy'],
                        'test_auc': metadata['results']['test_auc'],
                        'created_at': metadata['created_at'],
                        'use_calibration': metadata.get('use_calibration', False)
                    })
            except Exception as e:
                logger.error(f"读取模型元数据失败 {metadata_file}: {e}")
                continue

        return sorted(models, key=lambda x: x['created_at'], reverse=True)

    def get_deep_model_metadata(self, model_id: str) -> Dict:
        """读取深度学习模型完整元数据（供详情页）。"""
        metadata_path = self.models_dir / f"{model_id}_metadata.json"
        if not metadata_path.is_file():
            raise FileNotFoundError(f"深度学习模型不存在: {model_id}")
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def delete_deep_model(self, model_id: str) -> bool:
        """删除深度学习模型"""
        try:
            # 删除模型文件
            model_path = self.models_dir / f"{model_id}.h5"
            scaler_path = self.models_dir / f"{model_id}_scaler.pkl"
            calibrator_path = self.models_dir / f"{model_id}_calibrator.pkl"
            metadata_path = self.models_dir / f"{model_id}_metadata.json"

            for path in [model_path, scaler_path, calibrator_path, metadata_path]:
                if path.exists():
                    path.unlink()

            logger.info(f"模型已删除: {model_id}")
            return True

        except Exception as e:
            logger.error(f"删除模型失败: {e}")
            return False
