"""
模型校准 - Platt Scaling 和 Isotonic Regression
用于提高概率预测的可靠性
"""
import numpy as np
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
import matplotlib.pyplot as plt
import joblib
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ModelCalibrator:
    """模型校准器"""

    def __init__(self, method: str = 'platt'):
        """
        初始化校准器

        Parameters:
        -----------
        method : str
            校准方法: 'platt' (Platt Scaling) 或 'isotonic' (Isotonic Regression)
        """
        self.method = method
        self.calibrator = None

        if method == 'platt':
            # Platt Scaling 使用逻辑回归
            self.calibrator = LogisticRegression()
        elif method == 'isotonic':
            # Isotonic Regression
            self.calibrator = IsotonicRegression(out_of_bounds='clip')
        else:
            raise ValueError(f"不支持的校准方法: {method}")

    def fit(self, y_true: np.ndarray, y_pred_proba: np.ndarray):
        """
        拟合校准器

        Parameters:
        -----------
        y_true : np.ndarray
            真实标签 (n_samples,)
        y_pred_proba : np.ndarray
            预测概率 (n_samples,) 或 (n_samples, n_classes)
        """
        # 如果是多分类，只使用正类的概率
        if y_pred_proba.ndim == 2:
            y_pred_proba = y_pred_proba[:, 1]

        if self.method == 'platt':
            # Platt Scaling 需要 reshape
            X = y_pred_proba.reshape(-1, 1)
            self.calibrator.fit(X, y_true)
        else:
            # Isotonic Regression
            self.calibrator.fit(y_pred_proba, y_true)

        logger.info(f"校准器已拟合 (方法: {self.method})")

    def transform(self, y_pred_proba: np.ndarray) -> np.ndarray:
        """
        校准概率

        Parameters:
        -----------
        y_pred_proba : np.ndarray
            原始预测概率

        Returns:
        --------
        校准后的概率
        """
        if self.calibrator is None:
            raise ValueError("校准器未拟合")

        # 如果是多分类，只使用正类的概率
        if y_pred_proba.ndim == 2:
            y_pred_proba = y_pred_proba[:, 1]

        if self.method == 'platt':
            X = y_pred_proba.reshape(-1, 1)
            calibrated_proba = self.calibrator.predict_proba(X)[:, 1]
        else:
            calibrated_proba = self.calibrator.transform(y_pred_proba)

        return calibrated_proba

    def fit_transform(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray
    ) -> np.ndarray:
        """拟合并转换"""
        self.fit(y_true, y_pred_proba)
        return self.transform(y_pred_proba)

    def save(self, path: str):
        """保存校准器"""
        if self.calibrator is None:
            raise ValueError("校准器未拟合")

        joblib.dump({
            'method': self.method,
            'calibrator': self.calibrator
        }, path)
        logger.info(f"校准器已保存到: {path}")

    def load(self, path: str):
        """加载校准器"""
        data = joblib.load(path)
        self.method = data['method']
        self.calibrator = data['calibrator']
        logger.info(f"校准器已从 {path} 加载")


def plot_calibration_curve(
    y_true: np.ndarray,
    y_pred_proba: np.ndarray,
    y_calibrated_proba: Optional[np.ndarray] = None,
    n_bins: int = 10,
    save_path: Optional[str] = None
) -> Dict:
    """
    绘制校准曲线

    Parameters:
    -----------
    y_true : 真实标签
    y_pred_proba : 原始预测概率
    y_calibrated_proba : 校准后的概率（可选）
    n_bins : 分箱数量
    save_path : 保存路径

    Returns:
    --------
    校准指标字典
    """
    # 如果是多分类，只使用正类的概率
    if y_pred_proba.ndim == 2:
        y_pred_proba = y_pred_proba[:, 1]
    if y_calibrated_proba is not None and y_calibrated_proba.ndim == 2:
        y_calibrated_proba = y_calibrated_proba[:, 1]

    # 计算校准曲线
    fraction_of_positives, mean_predicted_value = calibration_curve(
        y_true, y_pred_proba, n_bins=n_bins, strategy='uniform'
    )

    # 绘图
    plt.figure(figsize=(10, 6))

    # 完美校准线
    plt.plot([0, 1], [0, 1], 'k--', label='完美校准')

    # 原始预测
    plt.plot(
        mean_predicted_value,
        fraction_of_positives,
        's-',
        label='原始预测',
        linewidth=2
    )

    # 校准后的预测
    if y_calibrated_proba is not None:
        fraction_of_positives_cal, mean_predicted_value_cal = calibration_curve(
            y_true, y_calibrated_proba, n_bins=n_bins, strategy='uniform'
        )
        plt.plot(
            mean_predicted_value_cal,
            fraction_of_positives_cal,
            'o-',
            label='校准后预测',
            linewidth=2
        )

    plt.xlabel('平均预测概率', fontsize=12)
    plt.ylabel('实际正类比例', fontsize=12)
    plt.title('校准曲线', fontsize=14)
    plt.legend(loc='best', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"校准曲线已保存到: {save_path}")

    plt.close()

    # 计算校准误差 (Expected Calibration Error)
    ece = np.mean(np.abs(fraction_of_positives - mean_predicted_value))

    results = {
        'expected_calibration_error': float(ece),
        'fraction_of_positives': fraction_of_positives.tolist(),
        'mean_predicted_value': mean_predicted_value.tolist()
    }

    if y_calibrated_proba is not None:
        ece_cal = np.mean(np.abs(fraction_of_positives_cal - mean_predicted_value_cal))
        results['expected_calibration_error_calibrated'] = float(ece_cal)
        results['fraction_of_positives_calibrated'] = fraction_of_positives_cal.tolist()
        results['mean_predicted_value_calibrated'] = mean_predicted_value_cal.tolist()

    return results


def calibrate_model(
    model,
    X_cal: np.ndarray,
    y_cal: np.ndarray,
    method: str = 'platt'
) -> Tuple[ModelCalibrator, Dict]:
    """
    校准模型

    Parameters:
    -----------
    model : 已训练的模型
    X_cal : 校准数据
    y_cal : 校准标签
    method : 校准方法

    Returns:
    --------
    calibrator, metrics
    """
    # 获取原始预测概率
    if hasattr(model, 'predict_proba'):
        y_pred_proba = model.predict_proba(X_cal)
    elif hasattr(model, 'predict'):
        y_pred_proba = model.predict(X_cal)
    else:
        raise ValueError("模型没有 predict_proba 或 predict 方法")

    # 创建并拟合校准器
    calibrator = ModelCalibrator(method=method)
    calibrator.fit(y_cal, y_pred_proba)

    # 校准概率
    y_calibrated_proba = calibrator.transform(y_pred_proba)

    # 计算校准指标
    metrics = plot_calibration_curve(y_cal, y_pred_proba, y_calibrated_proba)

    logger.info(f"原始 ECE: {metrics['expected_calibration_error']:.4f}")
    if 'expected_calibration_error_calibrated' in metrics:
        logger.info(f"校准后 ECE: {metrics['expected_calibration_error_calibrated']:.4f}")

    return calibrator, metrics


class CalibratedModel:
    """校准后的模型包装器"""

    def __init__(self, model, calibrator: ModelCalibrator):
        """
        初始化

        Parameters:
        -----------
        model : 原始模型
        calibrator : 校准器
        """
        self.model = model
        self.calibrator = calibrator

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测类别"""
        proba = self.predict_proba(X)
        return (proba[:, 1] >= 0.5).astype(int)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """预测校准后的概率"""
        # 获取原始概率
        if hasattr(self.model, 'predict_proba'):
            y_pred_proba = self.model.predict_proba(X)
        else:
            y_pred_proba = self.model.predict(X)

        # 校准
        calibrated_proba = self.calibrator.transform(y_pred_proba)

        # 返回两列概率
        return np.column_stack([1 - calibrated_proba, calibrated_proba])

    def save(self, model_path: str, calibrator_path: str):
        """保存模型和校准器"""
        joblib.dump(self.model, model_path)
        self.calibrator.save(calibrator_path)
        logger.info(f"校准模型已保存")

    @classmethod
    def load(cls, model_path: str, calibrator_path: str):
        """加载模型和校准器"""
        model = joblib.load(model_path)
        calibrator = ModelCalibrator(method='platt')  # 临时创建
        calibrator.load(calibrator_path)
        return cls(model, calibrator)
