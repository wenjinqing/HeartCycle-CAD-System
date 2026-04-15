"""
高级数据预处理模块
实现论文第5.2节要求的数据预处理方法：
1. KNN插补法处理缺失值
2. 孤立森林异常检测
3. Z-score标准化
4. SMOTE过采样处理类别不平衡
5. 数据集划分（分层抽样）
"""
import numpy as np
import pandas as pd
from sklearn.impute import KNNImputer
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE
from typing import Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class AdvancedPreprocessor:
    """高级数据预处理器"""

    def __init__(self):
        self.knn_imputer = None
        self.scaler = None
        self.isolation_forest = None
        self.smote = None

    def handle_missing_values(self, X: pd.DataFrame, n_neighbors: int = 5) -> pd.DataFrame:
        """
        使用KNN插补法处理缺失值

        论文要求：采用K近邻（KNN）插补法，基于欧氏距离寻找最相似的k个样本（k=5），
        以邻居样本的加权平均值填补缺失值

        Parameters:
        -----------
        X : pd.DataFrame
            输入数据
        n_neighbors : int
            KNN的邻居数量，默认5

        Returns:
        --------
        X_imputed : pd.DataFrame
            填补缺失值后的数据
        """
        logger.info(f"开始KNN插补，邻居数={n_neighbors}")

        # 记录原始缺失情况
        missing_before = X.isnull().sum().sum()
        missing_rate = missing_before / (X.shape[0] * X.shape[1]) * 100
        logger.info(f"缺失值数量: {missing_before}, 缺失率: {missing_rate:.2f}%")

        if missing_before == 0:
            logger.info("数据无缺失值，跳过插补")
            return X

        # 初始化KNN插补器
        self.knn_imputer = KNNImputer(
            n_neighbors=n_neighbors,
            weights='distance',  # 使用距离加权
            metric='nan_euclidean'  # 处理包含NaN的欧氏距离
        )

        # 执行插补
        X_imputed = self.knn_imputer.fit_transform(X)
        X_imputed = pd.DataFrame(X_imputed, columns=X.columns, index=X.index)

        # 验证插补结果
        missing_after = X_imputed.isnull().sum().sum()
        logger.info(f"插补完成，剩余缺失值: {missing_after}")

        return X_imputed

    def detect_outliers(self, X: pd.DataFrame, contamination: float = 0.05,
                       remove_outliers: bool = False) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        使用孤立森林检测异常值

        论文要求：使用孤立森林（Isolation Forest）算法进行二次验证，
        设置异常样本比例为5%

        Parameters:
        -----------
        X : pd.DataFrame
            输入数据
        contamination : float
            异常样本比例，默认0.05（5%）
        remove_outliers : bool
            是否移除异常值，默认False（使用边界值替换）

        Returns:
        --------
        X_processed : pd.DataFrame
            处理后的数据
        outlier_mask : np.ndarray
            异常值掩码（True表示异常）
        """
        logger.info(f"开始异常检测，contamination={contamination}")

        # 初始化孤立森林
        self.isolation_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )

        # 检测异常值
        outlier_pred = self.isolation_forest.fit_predict(X)
        outlier_mask = outlier_pred == -1  # -1表示异常

        n_outliers = outlier_mask.sum()
        outlier_rate = n_outliers / len(X) * 100
        logger.info(f"检测到 {n_outliers} 个异常样本 ({outlier_rate:.2f}%)")

        if remove_outliers:
            # 移除异常样本
            X_processed = X[~outlier_mask].copy()
            logger.info(f"移除异常样本后，剩余 {len(X_processed)} 个样本")
        else:
            # 使用边界值替换异常值
            X_processed = X.copy()
            for col in X.columns:
                # 计算IQR边界
                Q1 = X[col].quantile(0.25)
                Q3 = X[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR

                # 替换超出边界的值
                X_processed.loc[X_processed[col] < lower_bound, col] = lower_bound
                X_processed.loc[X_processed[col] > upper_bound, col] = upper_bound

            logger.info("使用边界值替换异常值")

        return X_processed, outlier_mask

    def standardize_features(self, X: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """
        Z-score标准化

        论文要求：采用Z-score标准化方法对连续型特征进行归一化处理。
        标准化公式为：z = (x - μ) / σ

        Parameters:
        -----------
        X : pd.DataFrame
            输入数据
        fit : bool
            是否拟合标准化器，默认True

        Returns:
        --------
        X_scaled : pd.DataFrame
            标准化后的数据
        """
        logger.info("开始Z-score标准化")

        if fit or self.scaler is None:
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            logger.info("拟合并转换数据")
        else:
            X_scaled = self.scaler.transform(X)
            logger.info("使用已有标准化器转换数据")

        X_scaled = pd.DataFrame(X_scaled, columns=X.columns, index=X.index)

        # 验证标准化结果
        mean_after = X_scaled.mean().mean()
        std_after = X_scaled.std().mean()
        logger.info(f"标准化后均值: {mean_after:.6f}, 标准差: {std_after:.6f}")

        return X_scaled

    def balance_classes(self, X: pd.DataFrame, y: pd.Series,
                       sampling_strategy: str = 'auto',
                       k_neighbors: int = 5) -> Tuple[pd.DataFrame, pd.Series]:
        """
        使用SMOTE过采样处理类别不平衡

        论文要求：采用SMOTE（Synthetic Minority Over-sampling Technique）过采样技术。
        SMOTE通过在少数类样本的k近邻之间进行线性插值，合成新的少数类样本。
        设置k=5，采样后训练集中正负样本比例调整为1:1。

        Parameters:
        -----------
        X : pd.DataFrame
            特征数据
        y : pd.Series
            标签数据
        sampling_strategy : str or float
            采样策略，'auto'表示自动平衡到1:1
        k_neighbors : int
            SMOTE的邻居数量，默认5

        Returns:
        --------
        X_resampled : pd.DataFrame
            重采样后的特征数据
        y_resampled : pd.Series
            重采样后的标签数据
        """
        logger.info(f"开始SMOTE过采样，k_neighbors={k_neighbors}")

        # 记录原始类别分布
        class_counts_before = y.value_counts()
        logger.info(f"原始类别分布:\n{class_counts_before}")

        # 初始化SMOTE
        self.smote = SMOTE(
            sampling_strategy=sampling_strategy,
            k_neighbors=k_neighbors,
            random_state=42
        )

        # 执行过采样
        X_resampled, y_resampled = self.smote.fit_resample(X, y)

        # 转换回DataFrame和Series
        X_resampled = pd.DataFrame(X_resampled, columns=X.columns)
        y_resampled = pd.Series(y_resampled, name=y.name)

        # 记录重采样后的类别分布
        class_counts_after = y_resampled.value_counts()
        logger.info(f"重采样后类别分布:\n{class_counts_after}")

        return X_resampled, y_resampled

    def split_dataset(self, X: pd.DataFrame, y: pd.Series,
                     train_size: float = 0.7,
                     val_size: float = 0.15,
                     test_size: float = 0.15,
                     stratify: bool = True,
                     random_state: int = 42) -> Dict[str, pd.DataFrame]:
        """
        数据集划分（分层抽样）

        论文要求：数据集按照7:1.5:1.5的比例划分为训练集（7,000例）、
        验证集（1,500例）和测试集（1,500例）。划分过程采用分层抽样策略，
        确保各子集中正负样本比例与原始数据集保持一致。

        Parameters:
        -----------
        X : pd.DataFrame
            特征数据
        y : pd.Series
            标签数据
        train_size : float
            训练集比例，默认0.7
        val_size : float
            验证集比例，默认0.15
        test_size : float
            测试集比例，默认0.15
        stratify : bool
            是否使用分层抽样，默认True
        random_state : int
            随机种子

        Returns:
        --------
        splits : dict
            包含训练集、验证集、测试集的字典
        """
        logger.info(f"开始数据集划分: train={train_size}, val={val_size}, test={test_size}")

        # 验证比例
        assert abs(train_size + val_size + test_size - 1.0) < 1e-6, \
            "训练集、验证集、测试集比例之和必须为1"

        # 第一次划分：分离出测试集
        stratify_y = y if stratify else None
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y,
            test_size=test_size,
            stratify=stratify_y,
            random_state=random_state
        )

        # 第二次划分：从剩余数据中分离出验证集（val_size=0时跳过）
        if val_size > 0:
            val_ratio = val_size / (train_size + val_size)
            stratify_y_temp = y_temp if stratify else None
            X_train, X_val, y_train, y_val = train_test_split(
                X_temp, y_temp,
                test_size=val_ratio,
                stratify=stratify_y_temp,
                random_state=random_state
            )
        else:
            X_train, y_train = X_temp, y_temp
            X_val = pd.DataFrame(columns=X.columns)
            y_val = pd.Series([], dtype=y.dtype, name=y.name)

        # 记录划分结果
        logger.info(f"训练集: {len(X_train)} 样本")
        logger.info(f"  类别分布: {y_train.value_counts().to_dict()}")
        if len(X_val) > 0:
            logger.info(f"验证集: {len(X_val)} 样本")
            logger.info(f"  类别分布: {y_val.value_counts().to_dict()}")
        logger.info(f"测试集: {len(X_test)} 样本")
        logger.info(f"  类别分布: {y_test.value_counts().to_dict()}")

        return {
            'X_train': X_train,
            'y_train': y_train,
            'X_val': X_val,
            'y_val': y_val,
            'X_test': X_test,
            'y_test': y_test
        }

    def preprocess_pipeline(self, X: pd.DataFrame, y: pd.Series,
                           handle_missing: bool = True,
                           detect_outliers_flag: bool = True,
                           standardize: bool = True,
                           balance: bool = True,
                           split: bool = True,
                           **kwargs) -> Dict:
        """
        完整的预处理流程

        Parameters:
        -----------
        X : pd.DataFrame
            特征数据
        y : pd.Series
            标签数据
        handle_missing : bool
            是否处理缺失值
        detect_outliers_flag : bool
            是否检测异常值
        standardize : bool
            是否标准化
        balance : bool
            是否平衡类别
        split : bool
            是否划分数据集
        **kwargs : dict
            其他参数

        Returns:
        --------
        result : dict
            预处理结果
        """
        logger.info("=" * 60)
        logger.info("开始完整预处理流程")
        logger.info("=" * 60)

        result = {}
        X_processed = X.copy()
        y_processed = y.copy()

        # 1. 处理缺失值
        if handle_missing:
            X_processed = self.handle_missing_values(
                X_processed,
                n_neighbors=kwargs.get('knn_neighbors', 5)
            )
            result['missing_handled'] = True

        # 2. 检测异常值
        if detect_outliers_flag:
            X_processed, outlier_mask = self.detect_outliers(
                X_processed,
                contamination=kwargs.get('contamination', 0.05),
                remove_outliers=kwargs.get('remove_outliers', False)
            )
            result['outliers_detected'] = True
            result['outlier_mask'] = outlier_mask

        # 3. 数据集划分（在标准化和平衡之前）
        if split:
            splits = self.split_dataset(
                X_processed, y_processed,
                train_size=kwargs.get('train_size', 0.7),
                val_size=kwargs.get('val_size', 0.15),
                test_size=kwargs.get('test_size', 0.15),
                stratify=kwargs.get('stratify', True),
                random_state=kwargs.get('random_state', 42)
            )
            result.update(splits)

            # 4. 标准化（只在训练集上拟合）
            if standardize:
                result['X_train'] = self.standardize_features(
                    result['X_train'], fit=True
                )
                if len(result['X_val']) > 0:
                    result['X_val'] = self.standardize_features(
                        result['X_val'], fit=False
                    )
                result['X_test'] = self.standardize_features(
                    result['X_test'], fit=False
                )
                result['standardized'] = True

            # 5. 平衡类别（只在训练集上）
            if balance:
                result['X_train'], result['y_train'] = self.balance_classes(
                    result['X_train'],
                    result['y_train'],
                    sampling_strategy=kwargs.get('sampling_strategy', 'auto'),
                    k_neighbors=kwargs.get('smote_neighbors', 5)
                )
                result['balanced'] = True
        else:
            # 不划分数据集的情况
            if standardize:
                X_processed = self.standardize_features(X_processed, fit=True)
                result['standardized'] = True

            if balance:
                X_processed, y_processed = self.balance_classes(
                    X_processed, y_processed,
                    sampling_strategy=kwargs.get('sampling_strategy', 'auto'),
                    k_neighbors=kwargs.get('smote_neighbors', 5)
                )
                result['balanced'] = True

            result['X'] = X_processed
            result['y'] = y_processed

        logger.info("=" * 60)
        logger.info("预处理流程完成")
        logger.info("=" * 60)

        return result


def preprocess_for_training(data_path: str, target_column: str = 'target',
                            **kwargs) -> Dict:
    """
    便捷函数：从CSV文件加载数据并执行完整预处理

    Parameters:
    -----------
    data_path : str
        CSV文件路径
    target_column : str
        目标列名称
    **kwargs : dict
        传递给preprocess_pipeline的参数

    Returns:
    --------
    result : dict
        预处理结果
    """
    logger.info(f"从文件加载数据: {data_path}")

    # 加载数据
    df = pd.read_csv(data_path)
    logger.info(f"数据形状: {df.shape}")

    # 分离特征和标签
    X = df.drop(columns=[target_column])
    y = df[target_column]

    # 执行预处理
    preprocessor = AdvancedPreprocessor()
    result = preprocessor.preprocess_pipeline(X, y, **kwargs)
    result['preprocessor'] = preprocessor

    return result


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    # 生成测试数据
    np.random.seed(42)
    n_samples = 1000
    n_features = 10

    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)]
    )

    # 添加缺失值
    missing_mask = np.random.rand(n_samples, n_features) < 0.05
    X[missing_mask] = np.nan

    # 生成不平衡标签
    y = pd.Series(np.random.choice([0, 1], size=n_samples, p=[0.7, 0.3]), name='target')

    # 执行预处理
    preprocessor = AdvancedPreprocessor()
    result = preprocessor.preprocess_pipeline(
        X, y,
        handle_missing=True,
        detect_outliers_flag=True,
        standardize=True,
        balance=True,
        split=True
    )

    print("\n预处理完成！")
    print(f"训练集形状: {result['X_train'].shape}")
    print(f"验证集形状: {result['X_val'].shape}")
    print(f"测试集形状: {result['X_test'].shape}")
