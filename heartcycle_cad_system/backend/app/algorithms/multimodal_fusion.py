"""
多模态融合深度学习模型
- 模态1：HRV特征向量（表格数据）→ MLP分支
- 模态2：ECG → STFT 频谱图（可选 + CWT 尺度图）→ 2D-CNN
- 融合层：Late Fusion；可选交互式融合（投影 + Hadamard + 拼接）
"""
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
import joblib

logger = logging.getLogger(__name__)

# ─── 频谱图生成 ──────────────────────────────────────────────────────────────

SPEC_HEIGHT = 64   # 频谱图高度（频率维度）
SPEC_WIDTH  = 64   # 频谱图宽度（时间维度）


def ecg_to_spectrogram(ecg_signal: np.ndarray, fs: float = 500.0) -> np.ndarray:
    """
    将 ECG 一维信号转换为 STFT 频谱图（对数幅度）。

    Parameters
    ----------
    ecg_signal : 1-D array, shape (N,)
    fs         : 采样率 Hz

    Returns
    -------
    spec : 2-D float32 array, shape (SPEC_HEIGHT, SPEC_WIDTH)，值域 [0, 1]
    """
    from scipy.signal import stft
    from scipy.ndimage import zoom

    ecg = np.asarray(ecg_signal, dtype=np.float32)

    # 去均值
    ecg = ecg - ecg.mean()

    nperseg = min(128, len(ecg) // 4)
    noverlap = nperseg * 3 // 4

    try:
        _, _, Zxx = stft(ecg, fs=fs, nperseg=nperseg, noverlap=noverlap)
    except Exception:
        # 信号太短时降级处理
        nperseg = max(4, len(ecg) // 2)
        noverlap = nperseg // 2
        _, _, Zxx = stft(ecg, fs=fs, nperseg=nperseg, noverlap=noverlap)

    # 幅度谱，对数压缩
    magnitude = np.abs(Zxx)
    log_magnitude = np.log1p(magnitude).astype(np.float32)

    # resize 到固定尺寸
    if log_magnitude.shape != (SPEC_HEIGHT, SPEC_WIDTH):
        zoom_h = SPEC_HEIGHT / log_magnitude.shape[0]
        zoom_w = SPEC_WIDTH  / log_magnitude.shape[1]
        log_magnitude = zoom(log_magnitude, (zoom_h, zoom_w), order=1)

    # 归一化到 [0, 1]
    mn, mx = log_magnitude.min(), log_magnitude.max()
    if mx > mn:
        log_magnitude = (log_magnitude - mn) / (mx - mn)
    else:
        log_magnitude = np.zeros_like(log_magnitude)

    return log_magnitude.astype(np.float32)


def ecg_to_cwt_scalogram(ecg_signal: np.ndarray, fs: float = 500.0) -> np.ndarray:
    """
    将 ECG 转为 CWT 幅度尺度图（对数压缩），尺寸与 STFT 分支一致，作为第二图像通道。
    对过长信号先重采样以控制 CWT 耗时。
    """
    import pywt
    from scipy.ndimage import zoom
    from scipy.signal import resample

    ecg = np.asarray(ecg_signal, dtype=np.float32).ravel()
    if ecg.size < 32:
        return np.zeros((SPEC_HEIGHT, SPEC_WIDTH), dtype=np.float32)

    ecg = ecg - ecg.mean()
    max_n = 4096
    if ecg.size > max_n:
        ecg = resample(ecg, max_n).astype(np.float32)

    scales = np.linspace(1.0, 64.0, num=32, dtype=np.float64)
    try:
        coef, _ = pywt.cwt(ecg, scales, "morl", sampling_period=1.0 / fs)
    except Exception:
        logger.exception("CWT 失败，返回零尺度图")
        return np.zeros((SPEC_HEIGHT, SPEC_WIDTH), dtype=np.float32)

    magnitude = np.abs(coef).astype(np.float32)
    log_magnitude = np.log1p(magnitude)

    if log_magnitude.shape != (SPEC_HEIGHT, SPEC_WIDTH):
        zh = SPEC_HEIGHT / log_magnitude.shape[0]
        zw = SPEC_WIDTH / log_magnitude.shape[1]
        log_magnitude = zoom(log_magnitude, (zh, zw), order=1)

    mn, mx = log_magnitude.min(), log_magnitude.max()
    if mx > mn:
        log_magnitude = (log_magnitude - mn) / (mx - mn)
    else:
        log_magnitude = np.zeros_like(log_magnitude)

    return log_magnitude.astype(np.float32)


def ecg_to_cnn_input(
    ecg_signal: np.ndarray,
    fs: float = 500.0,
    image_mode: str = "dual",
) -> np.ndarray:
    """
    CNN 输入张量，形状 (H, W, C)。image_mode: stft_only | dual
    """
    ecg = np.asarray(ecg_signal, dtype=np.float32)
    stft = ecg_to_spectrogram(ecg, fs=fs)
    if image_mode == "stft_only":
        return stft[..., np.newaxis]
    cwt = ecg_to_cwt_scalogram(ecg, fs=fs)
    return np.stack([stft, cwt], axis=-1).astype(np.float32)


# ─── Keras 多模态模型 ─────────────────────────────────────────────────────────

def build_multimodal_model(
    n_hrv_features: int,
    spec_shape: Tuple[int, int] = (SPEC_HEIGHT, SPEC_WIDTH),
    num_classes: int = 2,
    dropout_rate: float = 0.4,
    img_channels: int = 1,
    fusion_mode: str = "interactive",
):
    """
    构建多模态融合模型（Functional API）。

    结构
    ----
    HRV 分支（MLP）：
        Input(n_hrv_features) → Dense(128,relu) → BN → Dropout
                              → Dense(64,relu)  → BN → Dropout
                              → Dense(32,relu)

    ECG 图像分支（2D-CNN）：
        Input(H, W, 1) → Conv2D(32,3,relu) → BN → MaxPool(2)
                       → Conv2D(64,3,relu) → BN → MaxPool(2)
                       → Conv2D(128,3,relu)→ BN → GlobalAvgPool
                       → Dense(64,relu)

    融合层：
        Concatenate([hrv_out, cnn_out])  # shape=(32+64,)
        → Dense(64, relu) → Dropout
        → Dense(num_classes, softmax)
    """
    import tensorflow as tf
    from tensorflow.keras import layers, Model

    img_channels = max(1, int(img_channels))
    fusion_mode = fusion_mode if fusion_mode in ("concat", "interactive") else "interactive"

    # HRV branch (MLP)
    hrv_input = layers.Input(shape=(n_hrv_features,), name="hrv_input")
    x_hrv = layers.Dense(128, activation='relu')(hrv_input)
    x_hrv = layers.BatchNormalization()(x_hrv)
    x_hrv = layers.Dropout(dropout_rate)(x_hrv)
    x_hrv = layers.Dense(64, activation='relu')(x_hrv)
    x_hrv = layers.BatchNormalization()(x_hrv)
    x_hrv = layers.Dropout(dropout_rate)(x_hrv)
    hrv_out = layers.Dense(32, activation='relu', name="hrv_out")(x_hrv)

    # ── CNN 分支 ──────────────────────────────
    img_input = layers.Input(
        shape=(spec_shape[0], spec_shape[1], img_channels), name="img_input"
    )

    x_cnn = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(img_input)
    x_cnn = layers.BatchNormalization()(x_cnn)
    x_cnn = layers.MaxPooling2D((2, 2))(x_cnn)
    x_cnn = layers.Dropout(0.25)(x_cnn)

    x_cnn = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(x_cnn)
    x_cnn = layers.BatchNormalization()(x_cnn)
    x_cnn = layers.MaxPooling2D((2, 2))(x_cnn)
    x_cnn = layers.Dropout(0.25)(x_cnn)

    x_cnn = layers.Conv2D(128, (3, 3), activation='relu', padding='same')(x_cnn)
    x_cnn = layers.BatchNormalization()(x_cnn)
    x_cnn = layers.GlobalAveragePooling2D()(x_cnn)
    cnn_out = layers.Dense(64, activation='relu', name="cnn_out")(x_cnn)

    # ── 融合 ───────────────────────────────────
    if fusion_mode == "interactive":
        hrv_proj = layers.Dense(64, activation="relu", name="hrv_proj")(hrv_out)
        had = layers.Multiply(name="hrv_cnn_hadamard")([hrv_proj, cnn_out])
        fused = layers.Concatenate(name="fusion")([hrv_proj, cnn_out, had])
    else:
        fused = layers.Concatenate(name="fusion")([hrv_out, cnn_out])

    x = layers.Dense(64, activation='relu')(fused)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(dropout_rate)(x)
    output = layers.Dense(num_classes, activation='softmax', name="output")(x)

    model = Model(inputs=[hrv_input, img_input], outputs=output, name="MultiModalFusion")
    return model


# ─── 训练器 ──────────────────────────────────────────────────────────────────

class MultiModalTrainer:
    """多模态融合模型训练器"""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.model = None
        self.hrv_scaler = None
        self.feature_names: List[str] = []
        self.n_hrv_features: int = 0
        self.metadata: Dict = {}
        self.image_mode: str = "dual"
        self.img_channels: int = 1
        self.fusion_mode: str = "interactive"

    # ── 数据准备 ──────────────────────────────────────────────────────────────

    def prepare_dataset(
        self,
        hrv_list: List[np.ndarray],
        ecg_list: List[np.ndarray],
        labels: np.ndarray,
        fs: float = 500.0,
        test_size: float = 0.2,
        val_size: float = 0.2,
        image_mode: str = "dual",
    ) -> Tuple:
        """
        准备多模态训练数据集。

        Parameters
        ----------
        hrv_list : list of 1-D arrays, shape (n_features,)  ← HRV 特征向量
        ecg_list : list of 1-D arrays  ← 原始 ECG 信号
        labels   : 1-D int array, shape (N,)
        fs       : ECG 采样率
        test_size, val_size : 分割比例
        image_mode : stft_only | dual（STFT + CWT 双通道）

        Returns
        -------
        (X_hrv_tr, X_img_tr, y_tr,
         X_hrv_va, X_img_va, y_va,
         X_hrv_te, X_img_te, y_te)
        """
        import tensorflow as tf
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        from tensorflow.keras.utils import to_categorical

        np.random.seed(self.random_state)
        tf.random.set_seed(self.random_state)

        N = len(labels)
        assert len(hrv_list) == N and len(ecg_list) == N

        if image_mode not in ("stft_only", "dual"):
            image_mode = "dual"
        self.image_mode = image_mode

        logger.info(
            f"准备数据集：{N} 个样本，HRV 特征数 = {len(hrv_list[0])}，"
            f"ECG 图像模式 = {image_mode}"
        )

        # HRV 矩阵
        X_hrv = np.stack(hrv_list, axis=0).astype(np.float32)   # (N, F)

        specs = []
        for ecg in ecg_list:
            img = ecg_to_cnn_input(np.asarray(ecg, dtype=np.float32), fs=fs, image_mode=image_mode)
            specs.append(img)
        X_img = np.stack(specs, axis=0)                           # (N, H, W, C)
        self.img_channels = int(X_img.shape[-1])

        y = np.asarray(labels, dtype=np.int32)

        # 分割
        idx = np.arange(N)
        idx_tr, idx_te = train_test_split(idx, test_size=test_size,
                                          random_state=self.random_state, stratify=y)
        idx_tr, idx_va = train_test_split(idx_tr, test_size=val_size,
                                          random_state=self.random_state, stratify=y[idx_tr])

        # HRV 标准化
        self.hrv_scaler = StandardScaler()
        X_hrv_tr = self.hrv_scaler.fit_transform(X_hrv[idx_tr])
        X_hrv_va = self.hrv_scaler.transform(X_hrv[idx_va])
        X_hrv_te = self.hrv_scaler.transform(X_hrv[idx_te])

        # one-hot
        num_classes = len(np.unique(y))
        y_tr = to_categorical(y[idx_tr], num_classes=num_classes)
        y_va = to_categorical(y[idx_va], num_classes=num_classes)
        y_te = to_categorical(y[idx_te], num_classes=num_classes)

        self.n_hrv_features = X_hrv.shape[1]
        logger.info(f"训练: {len(idx_tr)}  验证: {len(idx_va)}  测试: {len(idx_te)}")

        return (X_hrv_tr, X_img[idx_tr], y_tr,
                X_hrv_va, X_img[idx_va], y_va,
                X_hrv_te, X_img[idx_te], y_te)

    # ── 训练 ──────────────────────────────────────────────────────────────────

    def train(
        self,
        X_hrv_tr, X_img_tr, y_tr,
        X_hrv_va, X_img_va, y_va,
        epochs: int = 50,
        batch_size: int = 16,
        learning_rate: float = 0.001,
        fusion_mode: str = "interactive",
        use_class_weights: bool = True,
    ) -> Dict:
        """训练多模态模型，返回 history 字典"""
        import tensorflow as tf
        from tensorflow import keras
        from tensorflow.keras import callbacks
        from sklearn.utils.class_weight import compute_class_weight

        if fusion_mode not in ("concat", "interactive"):
            fusion_mode = "interactive"
        self.fusion_mode = fusion_mode

        num_classes = y_tr.shape[1]
        img_ch = int(X_img_tr.shape[-1])
        self.model = build_multimodal_model(
            n_hrv_features=self.n_hrv_features,
            num_classes=num_classes,
            img_channels=img_ch,
            fusion_mode=fusion_mode,
        )

        optimizer = keras.optimizers.Adam(learning_rate=learning_rate)
        self.model.compile(
            optimizer=optimizer,
            loss='categorical_crossentropy',
            metrics=['accuracy', keras.metrics.AUC(name='auc')]
        )

        logger.info("多模态模型架构:")
        self.model.summary(print_fn=lambda s: logger.info(s))

        # 记录每 epoch 末学习率（需在 ReduceLROnPlateau 之后执行，故放在列表最后）
        class _LearningRateLogger(callbacks.Callback):
            def __init__(self):
                super().__init__()
                self.epoch_lrs: List[float] = []

            def on_epoch_end(self, epoch, logs=None):
                try:
                    lr = self.model.optimizer.learning_rate
                    if hasattr(lr, "numpy"):
                        v = float(np.asarray(lr.numpy()).reshape(-1)[0])
                    else:
                        v = float(
                            np.asarray(
                                tf.keras.backend.get_value(lr)
                            ).reshape(-1)[0]
                        )
                except Exception:
                    return
                self.epoch_lrs.append(v)

        lr_logger = _LearningRateLogger()

        cb_list = [
            callbacks.EarlyStopping(
                monitor='val_auc', patience=10,
                restore_best_weights=True, mode='max', verbose=1
            ),
            callbacks.ReduceLROnPlateau(
                monitor='val_loss', factor=0.5, patience=5,
                min_lr=1e-7, verbose=1
            ),
            lr_logger,
        ]

        fit_kw: Dict = {
            "epochs": epochs,
            "batch_size": batch_size,
            "callbacks": cb_list,
            "verbose": 1,
        }
        if use_class_weights and num_classes >= 2:
            y_int = np.argmax(y_tr, axis=1)
            classes = np.arange(num_classes)
            cw = compute_class_weight("balanced", classes=classes, y=y_int)
            fit_kw["sample_weight"] = cw[y_int].astype(np.float32)
            logger.info("已启用 balanced sample_weight（类别不均衡）")

        history = self.model.fit(
            [X_hrv_tr, X_img_tr], y_tr,
            validation_data=([X_hrv_va, X_img_va], y_va),
            **fit_kw,
        )

        logger.info("训练完成")
        hist_out = dict(history.history)
        if lr_logger.epoch_lrs:
            n = len(hist_out.get("loss", []))
            lrs = lr_logger.epoch_lrs[:n] if n else lr_logger.epoch_lrs
            if len(lrs) == n and n > 0:
                hist_out["lr"] = lrs
        return hist_out

    # ── 评估 ──────────────────────────────────────────────────────────────────

    def evaluate(self, X_hrv_te, X_img_te, y_te) -> Dict:
        """在测试集上计算各项指标"""
        from sklearn.metrics import (classification_report, confusion_matrix,
                                     roc_auc_score)

        loss, acc, auc = self.model.evaluate([X_hrv_te, X_img_te], y_te, verbose=0)
        y_pred_proba = self.model.predict([X_hrv_te, X_img_te])
        y_pred = np.argmax(y_pred_proba, axis=1)
        y_true = np.argmax(y_te, axis=1)

        report = classification_report(y_true, y_pred, output_dict=True)
        cm = confusion_matrix(y_true, y_pred)

        try:
            roc_auc = float(roc_auc_score(y_true, y_pred_proba[:, 1]))
        except Exception:
            roc_auc = float(auc)

        results = {
            'test_loss': float(loss),
            'test_accuracy': float(acc),
            'test_auc': roc_auc,
            'classification_report': report,
            'confusion_matrix': cm.tolist(),
        }
        logger.info(f"测试集 Accuracy={acc:.4f}  AUC={roc_auc:.4f}")
        return results

    # ── 预测 ──────────────────────────────────────────────────────────────────

    def predict(
        self,
        hrv_vector: np.ndarray,
        ecg_signal: np.ndarray,
        fs: float = 500.0,
    ) -> Tuple[int, List[float]]:
        """
        单样本预测。

        Returns
        -------
        (predicted_class, probabilities)
        """
        if self.model is None or self.hrv_scaler is None:
            raise ValueError("模型尚未训练或加载")

        hrv = np.asarray(hrv_vector, dtype=np.float32).reshape(1, -1)
        hrv_scaled = self.hrv_scaler.transform(hrv)

        ch = int(self.model.input[1].shape[-1])
        mode = "dual" if ch >= 2 else "stft_only"

        img = ecg_to_cnn_input(np.asarray(ecg_signal, dtype=np.float32), fs=fs, image_mode=mode)
        img = np.expand_dims(img, axis=0)

        proba = self.model.predict([hrv_scaled, img], verbose=0)[0]
        pred_class = int(np.argmax(proba))
        return pred_class, proba.tolist()

    # ── 保存 / 加载 ───────────────────────────────────────────────────────────

    def save(self, save_dir: str, model_id: str):
        """保存模型、标准化器到指定目录"""
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)

        model_file   = save_path / f"{model_id}_mm.h5"
        scaler_file  = save_path / f"{model_id}_mm_scaler.pkl"

        self.model.save(str(model_file))
        joblib.dump(self.hrv_scaler, str(scaler_file))

        logger.info(f"多模态模型已保存: {model_file}")
        return str(model_file), str(scaler_file)

    def load(self, save_dir: str, model_id: str):
        """从指定目录加载模型"""
        from tensorflow.keras.models import load_model

        save_path = Path(save_dir)
        model_file  = save_path / f"{model_id}_mm.h5"
        scaler_file = save_path / f"{model_id}_mm_scaler.pkl"

        if not model_file.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_file}")

        self.model = load_model(str(model_file))
        self.hrv_scaler = joblib.load(str(scaler_file))

        self.n_hrv_features = int(self.model.input[0].shape[-1])
        ch = int(self.model.input[1].shape[-1])
        self.img_channels = ch
        self.image_mode = "dual" if ch >= 2 else "stft_only"
        logger.info(
            f"多模态模型已加载: {model_file}（CNN 输入通道={ch}, image_mode={self.image_mode}）"
        )
