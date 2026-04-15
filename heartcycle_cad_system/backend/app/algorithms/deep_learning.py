"""
深度学习模型 - 1D-CNN、LSTM、混合模型
用于直接处理原始 ECG 信号进行冠心病风险预测
"""
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models, callbacks
from tensorflow.keras.utils import to_categorical
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
import json
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


class DeepLearningModel:
    """深度学习模型基类"""

    def __init__(
        self,
        model_type: str = "cnn",
        input_shape: Tuple[int, int] = (5000, 1),
        num_classes: int = 2,
        random_state: int = 42
    ):
        """
        初始化深度学习模型

        Parameters:
        -----------
        model_type : str
            模型类型: 'cnn', 'lstm', 'gru', 'cnn_lstm'
        input_shape : tuple
            输入形状 (时间步长, 特征数)
        num_classes : int
            分类数量
        random_state : int
            随机种子
        """
        self.model_type = model_type
        self.input_shape = input_shape
        self.num_classes = num_classes
        self.random_state = random_state

        # 设置随机种子
        np.random.seed(random_state)
        tf.random.set_seed(random_state)

        self.model = None
        self.scaler = StandardScaler()
        self.history = None

    def build_cnn_model(self) -> keras.Model:
        """
        构建 1D-CNN 模型

        架构:
        - 3个卷积块（Conv1D + BatchNorm + MaxPooling + Dropout）
        - 全局平均池化
        - 全连接层
        """
        model = models.Sequential([
            # 第一个卷积块
            layers.Conv1D(64, kernel_size=7, activation='relu', input_shape=self.input_shape),
            layers.BatchNormalization(),
            layers.MaxPooling1D(pool_size=2),
            layers.Dropout(0.3),

            # 第二个卷积块
            layers.Conv1D(128, kernel_size=5, activation='relu'),
            layers.BatchNormalization(),
            layers.MaxPooling1D(pool_size=2),
            layers.Dropout(0.3),

            # 第三个卷积块
            layers.Conv1D(256, kernel_size=3, activation='relu'),
            layers.BatchNormalization(),
            layers.MaxPooling1D(pool_size=2),
            layers.Dropout(0.3),

            # 全局平均池化
            layers.GlobalAveragePooling1D(),

            # 全连接层
            layers.Dense(128, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.5),

            layers.Dense(64, activation='relu'),
            layers.Dropout(0.3),

            # 输出层
            layers.Dense(self.num_classes, activation='softmax')
        ])

        return model

    def build_lstm_model(self) -> keras.Model:
        """
        构建 LSTM 模型

        架构:
        - 2个 LSTM 层
        - 全连接层
        """
        model = models.Sequential([
            # 第一个 LSTM 层
            layers.LSTM(128, return_sequences=True, input_shape=self.input_shape),
            layers.BatchNormalization(),
            layers.Dropout(0.3),

            # 第二个 LSTM 层
            layers.LSTM(64, return_sequences=False),
            layers.BatchNormalization(),
            layers.Dropout(0.3),

            # 全连接层
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.3),

            # 输出层
            layers.Dense(self.num_classes, activation='softmax')
        ])

        return model

    def build_gru_model(self) -> keras.Model:
        """
        构建 GRU 模型

        架构:
        - 2个 GRU 层
        - 全连接层
        """
        model = models.Sequential([
            # 第一个 GRU 层
            layers.GRU(128, return_sequences=True, input_shape=self.input_shape),
            layers.BatchNormalization(),
            layers.Dropout(0.3),

            # 第二个 GRU 层
            layers.GRU(64, return_sequences=False),
            layers.BatchNormalization(),
            layers.Dropout(0.3),

            # 全连接层
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.3),

            # 输出层
            layers.Dense(self.num_classes, activation='softmax')
        ])

        return model

    def build_cnn_lstm_model(self) -> keras.Model:
        """
        构建 CNN-LSTM 混合模型

        架构:
        - CNN 层提取空间特征
        - LSTM 层提取时序特征
        - 全连接层
        """
        model = models.Sequential([
            # CNN 层
            layers.Conv1D(64, kernel_size=7, activation='relu', input_shape=self.input_shape),
            layers.BatchNormalization(),
            layers.MaxPooling1D(pool_size=2),
            layers.Dropout(0.3),

            layers.Conv1D(128, kernel_size=5, activation='relu'),
            layers.BatchNormalization(),
            layers.MaxPooling1D(pool_size=2),
            layers.Dropout(0.3),

            # LSTM 层
            layers.LSTM(64, return_sequences=False),
            layers.BatchNormalization(),
            layers.Dropout(0.3),

            # 全连接层
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.3),

            # 输出层
            layers.Dense(self.num_classes, activation='softmax')
        ])

        return model

    def build_model(self) -> keras.Model:
        """根据模型类型构建模型"""
        if self.model_type == 'cnn':
            return self.build_cnn_model()
        elif self.model_type == 'lstm':
            return self.build_lstm_model()
        elif self.model_type == 'gru':
            return self.build_gru_model()
        elif self.model_type == 'cnn_lstm':
            return self.build_cnn_lstm_model()
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")

    def prepare_data(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.2,
        validation_split: float = 0.2
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        准备训练数据

        Parameters:
        -----------
        X : np.ndarray
            输入数据 (n_samples, n_timesteps) 或 (n_samples, n_timesteps, n_features)
        y : np.ndarray
            标签 (n_samples,)
        test_size : float
            测试集比例
        validation_split : float
            验证集比例（从训练集中划分）

        Returns:
        --------
        X_train, X_val, X_test, y_train, y_val, y_test
        """
        # 确保输入是3D的 (n_samples, n_timesteps, n_features)
        if X.ndim == 2:
            X = X.reshape(X.shape[0], X.shape[1], 1)

        # 标准化
        n_samples, n_timesteps, n_features = X.shape
        X_reshaped = X.reshape(-1, n_features)
        X_scaled = self.scaler.fit_transform(X_reshaped)
        X = X_scaled.reshape(n_samples, n_timesteps, n_features)

        # 划分训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=self.random_state, stratify=y
        )

        # 从训练集中划分验证集
        X_train, X_val, y_train, y_val = train_test_split(
            X_train, y_train, test_size=validation_split,
            random_state=self.random_state, stratify=y_train
        )

        # 转换为 one-hot 编码
        y_train = to_categorical(y_train, num_classes=self.num_classes)
        y_val = to_categorical(y_val, num_classes=self.num_classes)
        y_test = to_categorical(y_test, num_classes=self.num_classes)

        logger.info(f"训练集: {X_train.shape}, 验证集: {X_val.shape}, 测试集: {X_test.shape}")

        return X_train, X_val, X_test, y_train, y_val, y_test

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        epochs: int = 50,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        early_stopping_patience: int = 10,
        reduce_lr_patience: int = 5
    ) -> Dict:
        """
        训练模型

        Parameters:
        -----------
        X_train, y_train : 训练数据
        X_val, y_val : 验证数据
        epochs : 训练轮数
        batch_size : 批次大小
        learning_rate : 学习率
        early_stopping_patience : 早停耐心值
        reduce_lr_patience : 学习率衰减耐心值

        Returns:
        --------
        训练历史
        """
        # 构建模型
        self.model = self.build_model()

        # 编译模型
        optimizer = keras.optimizers.Adam(learning_rate=learning_rate)
        self.model.compile(
            optimizer=optimizer,
            loss='categorical_crossentropy',
            metrics=['accuracy', keras.metrics.AUC(name='auc')]
        )

        logger.info(f"模型架构:\n{self.model.summary()}")

        # 回调函数
        callback_list = [
            # 早停
            callbacks.EarlyStopping(
                monitor='val_loss',
                patience=early_stopping_patience,
                restore_best_weights=True,
                verbose=1
            ),
            # 学习率衰减
            callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=reduce_lr_patience,
                min_lr=1e-7,
                verbose=1
            ),
            # 模型检查点
            callbacks.ModelCheckpoint(
                'best_model.h5',
                monitor='val_auc',
                save_best_only=True,
                mode='max',
                verbose=1
            )
        ]

        # 训练
        logger.info("开始训练...")
        self.history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callback_list,
            verbose=1
        )

        logger.info("训练完成")

        return self.history.history

    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict:
        """
        评估模型

        Returns:
        --------
        评估指标字典
        """
        if self.model is None:
            raise ValueError("模型未训练")

        # 预测
        y_pred_proba = self.model.predict(X_test)
        y_pred = np.argmax(y_pred_proba, axis=1)
        y_true = np.argmax(y_test, axis=1)

        # 计算指标
        test_loss, test_acc, test_auc = self.model.evaluate(X_test, y_test, verbose=0)

        # 分类报告
        report = classification_report(y_true, y_pred, output_dict=True)

        # 混淆矩阵
        cm = confusion_matrix(y_true, y_pred)

        results = {
            'test_loss': float(test_loss),
            'test_accuracy': float(test_acc),
            'test_auc': float(test_auc),
            'classification_report': report,
            'confusion_matrix': cm.tolist(),
            'predictions': {
                'y_true': y_true.tolist(),
                'y_pred': y_pred.tolist(),
                'y_pred_proba': y_pred_proba.tolist()
            }
        }

        logger.info(f"测试集准确率: {test_acc:.4f}, AUC: {test_auc:.4f}")

        return results

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        预测

        Returns:
        --------
        predictions, probabilities
        """
        if self.model is None:
            raise ValueError("模型未训练")

        # 确保输入是3D的
        if X.ndim == 2:
            X = X.reshape(X.shape[0], X.shape[1], 1)

        # 标准化
        n_samples, n_timesteps, n_features = X.shape
        X_reshaped = X.reshape(-1, n_features)
        X_scaled = self.scaler.transform(X_reshaped)
        X = X_scaled.reshape(n_samples, n_timesteps, n_features)

        # 预测
        y_pred_proba = self.model.predict(X)
        y_pred = np.argmax(y_pred_proba, axis=1)

        return y_pred, y_pred_proba

    def save(self, model_path: str, scaler_path: str):
        """保存模型和标准化器"""
        if self.model is None:
            raise ValueError("模型未训练")

        # 保存模型
        self.model.save(model_path)
        logger.info(f"模型已保存到: {model_path}")

        # 保存标准化器
        joblib.dump(self.scaler, scaler_path)
        logger.info(f"标准化器已保存到: {scaler_path}")

    def load(self, model_path: str, scaler_path: str):
        """加载模型和标准化器"""
        self.model = keras.models.load_model(model_path)
        self.scaler = joblib.load(scaler_path)
        logger.info(f"模型已从 {model_path} 加载")

    def get_model_summary(self) -> str:
        """获取模型摘要"""
        if self.model is None:
            return "模型未构建"

        from io import StringIO
        stream = StringIO()
        self.model.summary(print_fn=lambda x: stream.write(x + '\n'))
        return stream.getvalue()
