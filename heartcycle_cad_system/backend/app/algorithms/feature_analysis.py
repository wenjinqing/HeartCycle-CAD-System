"""
高级特征分析模块
包括特征相关性、重要性、分布分析等
"""
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr, chi2_contingency
from sklearn.feature_selection import mutual_info_classif, f_classif
from sklearn.ensemble import RandomForestClassifier
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class FeatureAnalyzer:
    """特征分析器"""

    def __init__(self):
        pass

    def analyze_correlation(
        self,
        X: pd.DataFrame,
        method: str = 'pearson',
        threshold: float = 0.8
    ) -> Dict:
        """
        分析特征相关性

        Parameters:
        -----------
        X : pd.DataFrame
            特征数据
        method : str
            相关性方法: 'pearson', 'spearman', 'kendall'
        threshold : float
            高相关性阈值

        Returns:
        --------
        相关性分析结果
        """
        # 计算相关性矩阵
        corr_matrix = X.corr(method=method)

        # 找出高相关性特征对
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) >= threshold:
                    high_corr_pairs.append({
                        'feature1': corr_matrix.columns[i],
                        'feature2': corr_matrix.columns[j],
                        'correlation': float(corr_value)
                    })

        # 排序
        high_corr_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)

        results = {
            'correlation_matrix': corr_matrix.to_dict(),
            'high_correlation_pairs': high_corr_pairs,
            'num_high_corr_pairs': len(high_corr_pairs),
            'method': method,
            'threshold': threshold
        }

        return results

    def analyze_feature_importance(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
        method: str = 'random_forest'
    ) -> Dict:
        """
        分析特征重要性

        Parameters:
        -----------
        X : pd.DataFrame
            特征数据
        y : np.ndarray
            标签
        method : str
            方法: 'random_forest', 'mutual_info', 'f_test'

        Returns:
        --------
        特征重要性结果
        """
        feature_names = X.columns.tolist()

        if method == 'random_forest':
            # 随机森林特征重要性
            rf = RandomForestClassifier(n_estimators=100, random_state=42)
            rf.fit(X, y)
            importances = rf.feature_importances_

        elif method == 'mutual_info':
            # 互信息
            importances = mutual_info_classif(X, y, random_state=42)

        elif method == 'f_test':
            # F检验
            f_scores, _ = f_classif(X, y)
            importances = f_scores / f_scores.max()  # 归一化

        else:
            raise ValueError(f"不支持的方法: {method}")

        # 创建特征重要性列表
        feature_importance = [
            {
                'feature': feature_names[i],
                'importance': float(importances[i])
            }
            for i in range(len(feature_names))
        ]

        # 排序
        feature_importance.sort(key=lambda x: x['importance'], reverse=True)

        results = {
            'feature_importance': feature_importance,
            'method': method,
            'top_10_features': [f['feature'] for f in feature_importance[:10]]
        }

        return results

    def analyze_distribution(
        self,
        X: pd.DataFrame,
        y: np.ndarray
    ) -> Dict:
        """
        分析特征分布（按类别）

        Parameters:
        -----------
        X : pd.DataFrame
            特征数据
        y : np.ndarray
            标签

        Returns:
        --------
        分布分析结果
        """
        results = {}

        for feature in X.columns:
            feature_data = X[feature].values

            # 按类别分组
            class_0_data = feature_data[y == 0]
            class_1_data = feature_data[y == 1]

            # 统计量
            stats = {
                'class_0': {
                    'mean': float(np.mean(class_0_data)),
                    'std': float(np.std(class_0_data)),
                    'median': float(np.median(class_0_data)),
                    'min': float(np.min(class_0_data)),
                    'max': float(np.max(class_0_data))
                },
                'class_1': {
                    'mean': float(np.mean(class_1_data)),
                    'std': float(np.std(class_1_data)),
                    'median': float(np.median(class_1_data)),
                    'min': float(np.min(class_1_data)),
                    'max': float(np.max(class_1_data))
                },
                'difference': {
                    'mean_diff': float(np.mean(class_1_data) - np.mean(class_0_data)),
                    'median_diff': float(np.median(class_1_data) - np.median(class_0_data))
                }
            }

            results[feature] = stats

        return results

    def detect_outliers(
        self,
        X: pd.DataFrame,
        method: str = 'iqr',
        threshold: float = 1.5
    ) -> Dict:
        """
        检测异常值

        Parameters:
        -----------
        X : pd.DataFrame
            特征数据
        method : str
            方法: 'iqr' (四分位距), 'zscore' (Z分数)
        threshold : float
            阈值

        Returns:
        --------
        异常值检测结果
        """
        outliers = {}

        for feature in X.columns:
            feature_data = X[feature].values

            if method == 'iqr':
                # IQR 方法
                q1 = np.percentile(feature_data, 25)
                q3 = np.percentile(feature_data, 75)
                iqr = q3 - q1
                lower_bound = q1 - threshold * iqr
                upper_bound = q3 + threshold * iqr

                outlier_mask = (feature_data < lower_bound) | (feature_data > upper_bound)

            elif method == 'zscore':
                # Z分数方法
                mean = np.mean(feature_data)
                std = np.std(feature_data)
                z_scores = np.abs((feature_data - mean) / std)
                outlier_mask = z_scores > threshold

            else:
                raise ValueError(f"不支持的方法: {method}")

            num_outliers = int(np.sum(outlier_mask))
            outlier_ratio = float(num_outliers / len(feature_data))

            outliers[feature] = {
                'num_outliers': num_outliers,
                'outlier_ratio': outlier_ratio,
                'outlier_indices': np.where(outlier_mask)[0].tolist()
            }

        return {
            'outliers': outliers,
            'method': method,
            'threshold': threshold
        }

    def analyze_feature_interactions(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
        top_n: int = 10
    ) -> Dict:
        """
        分析特征交互

        使用随机森林的特征重要性来识别可能的交互特征

        Parameters:
        -----------
        X : pd.DataFrame
            特征数据
        y : np.ndarray
            标签
        top_n : int
            返回前N个交互特征对

        Returns:
        --------
        特征交互分析结果
        """
        feature_names = X.columns.tolist()
        interactions = []

        # 对于每对特征，创建交互特征并评估重要性
        for i in range(len(feature_names)):
            for j in range(i+1, min(i+10, len(feature_names))):  # 限制计算量
                feature1 = feature_names[i]
                feature2 = feature_names[j]

                # 创建交互特征（乘积）
                interaction_feature = X[feature1] * X[feature2]

                # 计算互信息
                mi = mutual_info_classif(
                    interaction_feature.values.reshape(-1, 1),
                    y,
                    random_state=42
                )[0]

                interactions.append({
                    'feature1': feature1,
                    'feature2': feature2,
                    'interaction_score': float(mi)
                })

        # 排序并返回前N个
        interactions.sort(key=lambda x: x['interaction_score'], reverse=True)

        return {
            'top_interactions': interactions[:top_n],
            'total_evaluated': len(interactions)
        }

    def generate_feature_report(
        self,
        X: pd.DataFrame,
        y: np.ndarray
    ) -> Dict:
        """
        生成完整的特征分析报告

        Parameters:
        -----------
        X : pd.DataFrame
            特征数据
        y : np.ndarray
            标签

        Returns:
        --------
        完整的特征分析报告
        """
        logger.info("开始生成特征分析报告...")

        report = {}

        # 1. 基本信息
        report['basic_info'] = {
            'num_samples': len(X),
            'num_features': len(X.columns),
            'feature_names': X.columns.tolist(),
            'class_distribution': {
                'class_0': int(np.sum(y == 0)),
                'class_1': int(np.sum(y == 1))
            }
        }

        # 2. 相关性分析
        logger.info("分析特征相关性...")
        report['correlation'] = self.analyze_correlation(X)

        # 3. 特征重要性
        logger.info("分析特征重要性...")
        report['importance'] = self.analyze_feature_importance(X, y)

        # 4. 分布分析
        logger.info("分析特征分布...")
        report['distribution'] = self.analyze_distribution(X, y)

        # 5. 异常值检测
        logger.info("检测异常值...")
        report['outliers'] = self.detect_outliers(X)

        # 6. 特征交互
        logger.info("分析特征交互...")
        report['interactions'] = self.analyze_feature_interactions(X, y)

        # 7. 建议
        report['recommendations'] = self._generate_feature_recommendations(report)

        logger.info("特征分析报告生成完成")

        return report

    def _generate_feature_recommendations(self, report: Dict) -> List[str]:
        """生成特征工程建议"""
        recommendations = []

        # 高相关性建议
        num_high_corr = report['correlation']['num_high_corr_pairs']
        if num_high_corr > 0:
            recommendations.append(
                f"发现 {num_high_corr} 对高相关性特征，建议移除冗余特征以减少多重共线性"
            )

        # 特征重要性建议
        top_features = report['importance']['top_10_features']
        recommendations.append(
            f"前10个重要特征: {', '.join(top_features[:5])}等，建议重点关注这些特征"
        )

        # 异常值建议
        outlier_features = [
            f for f, info in report['outliers']['outliers'].items()
            if info['outlier_ratio'] > 0.05
        ]
        if outlier_features:
            recommendations.append(
                f"特征 {', '.join(outlier_features[:3])} 等存在较多异常值，建议进行异常值处理"
            )

        # 特征交互建议
        if report['interactions']['top_interactions']:
            top_interaction = report['interactions']['top_interactions'][0]
            recommendations.append(
                f"发现潜在的特征交互: {top_interaction['feature1']} × {top_interaction['feature2']}，"
                f"建议创建交互特征"
            )

        return recommendations
