"""
高级特征工程模块
实现论文第5.3节要求的特征工程方法：
1. 多阶段特征选择（方差阈值、互信息、RFE）
2. 多项式特征扩展（二阶）
3. 特征交叉（临床有意义的特征对）
4. 特征重要性分析
"""
import numpy as np
import pandas as pd
from sklearn.feature_selection import (
    VarianceThreshold,
    mutual_info_classif,
    RFE
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import PolynomialFeatures
from typing import List, Tuple, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AdvancedFeatureEngineer:
    """高级特征工程器"""

    def __init__(self):
        self.variance_selector = None
        self.rfe_selector = None
        self.poly_features = None
        self.selected_features = None
        self.feature_scores = {}
        self.mi_selected_columns_: Optional[List[str]] = None
        self.correlation_dropped_columns_: List[str] = []
        self._poly_subset_columns: Optional[List[str]] = None
        self._fit_create_poly: bool = False
        self._fit_create_interactions: bool = False
        self._fit_remove_correlated: bool = False

    def variance_threshold_selection(self, X: pd.DataFrame,
                                     threshold: float = 0.01) -> pd.DataFrame:
        """
        方差阈值法特征选择

        论文要求：第一阶段使用方差阈值法（阈值=0.01）剔除低方差特征

        Parameters:
        -----------
        X : pd.DataFrame
            输入特征
        threshold : float
            方差阈值，默认0.01

        Returns:
        --------
        X_selected : pd.DataFrame
            选择后的特征
        """
        logger.info(f"开始方差阈值选择，threshold={threshold}")
        logger.info(f"原始特征数: {X.shape[1]}")

        # 初始化方差选择器
        self.variance_selector = VarianceThreshold(threshold=threshold)

        # 拟合并转换
        X_selected = self.variance_selector.fit_transform(X)

        # 获取保留的特征名
        selected_mask = self.variance_selector.get_support()
        selected_features = X.columns[selected_mask].tolist()

        X_selected = pd.DataFrame(X_selected, columns=selected_features, index=X.index)

        logger.info(f"保留特征数: {X_selected.shape[1]}")
        logger.info(f"移除特征数: {X.shape[1] - X_selected.shape[1]}")

        # 记录特征方差
        variances = X.var()
        self.feature_scores['variance'] = variances.to_dict()

        return X_selected

    def mutual_information_selection(self, X: pd.DataFrame, y: pd.Series,
                                     top_k: Optional[int] = None,
                                     percentile: float = 0.8) -> pd.DataFrame:
        """
        互信息法特征选择

        论文要求：第二阶段采用互信息法评估特征与目标变量的相关性，
        保留互信息值前80%的特征

        Parameters:
        -----------
        X : pd.DataFrame
            输入特征
        y : pd.Series
            目标变量
        top_k : int, optional
            保留前k个特征，如果为None则使用percentile
        percentile : float
            保留的特征百分比，默认0.8（80%）

        Returns:
        --------
        X_selected : pd.DataFrame
            选择后的特征
        """
        logger.info("开始互信息特征选择")
        logger.info(f"原始特征数: {X.shape[1]}")

        # 计算互信息
        mi_scores = mutual_info_classif(X, y, random_state=42)

        # 创建特征-分数DataFrame
        mi_df = pd.DataFrame({
            'feature': X.columns,
            'mi_score': mi_scores
        }).sort_values('mi_score', ascending=False)

        # 确定保留的特征数量
        if top_k is None:
            top_k = int(len(X.columns) * percentile)

        # 选择特征
        selected_features = mi_df.head(top_k)['feature'].tolist()
        self.mi_selected_columns_ = list(selected_features)
        X_selected = X[selected_features]

        logger.info(f"保留特征数: {len(selected_features)}")
        logger.info(f"移除特征数: {X.shape[1] - len(selected_features)}")

        # 记录互信息分数
        self.feature_scores['mutual_info'] = mi_df.set_index('feature')['mi_score'].to_dict()

        # 显示Top 10特征
        logger.info("互信息Top 10特征:")
        for idx, row in mi_df.head(10).iterrows():
            logger.info(f"  {row['feature']}: {row['mi_score']:.4f}")

        return X_selected

    def rfe_selection(self, X: pd.DataFrame, y: pd.Series,
                     n_features_to_select: Optional[int] = None,
                     step: int = 1) -> pd.DataFrame:
        """
        递归特征消除（RFE）

        论文要求：第三阶段使用基于树模型的特征重要性排序，
        结合递归特征消除（RFE）方法确定最优特征子集

        Parameters:
        -----------
        X : pd.DataFrame
            输入特征
        y : pd.Series
            目标变量
        n_features_to_select : int, optional
            要选择的特征数量，如果为None则自动确定
        step : int
            每次迭代移除的特征数量

        Returns:
        --------
        X_selected : pd.DataFrame
            选择后的特征
        """
        logger.info("开始RFE特征选择")
        logger.info(f"原始特征数: {X.shape[1]}")

        # 使用随机森林作为基础估计器
        estimator = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            n_jobs=-1
        )

        # 初始化RFE
        self.rfe_selector = RFE(
            estimator=estimator,
            n_features_to_select=n_features_to_select,
            step=step
        )

        # 拟合并转换
        X_selected = self.rfe_selector.fit_transform(X, y)

        # 获取保留的特征名
        selected_mask = self.rfe_selector.get_support()
        selected_features = X.columns[selected_mask].tolist()

        X_selected = pd.DataFrame(X_selected, columns=selected_features, index=X.index)

        logger.info(f"保留特征数: {X_selected.shape[1]}")
        logger.info(f"移除特征数: {X.shape[1] - X_selected.shape[1]}")

        # 记录特征排名
        feature_ranking = pd.DataFrame({
            'feature': X.columns,
            'ranking': self.rfe_selector.ranking_,
            'selected': selected_mask
        }).sort_values('ranking')

        self.feature_scores['rfe_ranking'] = feature_ranking.set_index('feature')['ranking'].to_dict()

        # 显示选中的特征
        logger.info("RFE选中的特征:")
        for feature in selected_features:
            logger.info(f"  {feature}")

        return X_selected

    def create_polynomial_features(self, X: pd.DataFrame,
                                   degree: int = 2,
                                   interaction_only: bool = False,
                                   include_bias: bool = False) -> pd.DataFrame:
        """
        多项式特征扩展

        论文要求：对连续型特征进行二阶多项式扩展，生成平方项和交互项

        Parameters:
        -----------
        X : pd.DataFrame
            输入特征
        degree : int
            多项式阶数，默认2
        interaction_only : bool
            是否只生成交互项（不生成平方项）
        include_bias : bool
            是否包含偏置项

        Returns:
        --------
        X_poly : pd.DataFrame
            扩展后的特征
        """
        logger.info(f"开始多项式特征扩展，degree={degree}")
        logger.info(f"原始特征数: {X.shape[1]}")

        # 初始化多项式特征生成器
        self.poly_features = PolynomialFeatures(
            degree=degree,
            interaction_only=interaction_only,
            include_bias=include_bias
        )

        # 生成多项式特征
        X_poly = self.poly_features.fit_transform(X)

        # 获取特征名称
        feature_names = self.poly_features.get_feature_names_out(X.columns)

        X_poly = pd.DataFrame(X_poly, columns=feature_names, index=X.index)

        logger.info(f"扩展后特征数: {X_poly.shape[1]}")
        logger.info(f"新增特征数: {X_poly.shape[1] - X.shape[1]}")

        return X_poly

    def create_clinical_interactions(self, X: pd.DataFrame,
                                     interaction_pairs: Optional[List[Tuple[str, str]]] = None
                                     ) -> pd.DataFrame:
        """
        创建临床有意义的特征交叉

        论文要求：针对具有明确临床交互意义的特征对（如年龄与收缩压、
        LDL-C与HDL-C比值）构建人工交叉特征

        Parameters:
        -----------
        X : pd.DataFrame
            输入特征
        interaction_pairs : list of tuples, optional
            特征对列表，如果为None则使用默认的临床特征对

        Returns:
        --------
        X_with_interactions : pd.DataFrame
            包含交互特征的数据
        """
        logger.info("开始创建临床交互特征")

        X_with_interactions = X.copy()

        # 默认的临床特征对
        if interaction_pairs is None:
            interaction_pairs = [
                ('age', 'sbp'),  # 年龄 × 收缩压
                ('age', 'dbp'),  # 年龄 × 舒张压
                ('age', 'cholesterol'),  # 年龄 × 总胆固醇
                ('sbp', 'dbp'),  # 收缩压 × 舒张压
                ('ldl', 'hdl'),  # LDL × HDL
                ('cholesterol', 'ldl'),  # 总胆固醇 × LDL
                ('bmi', 'age'),  # BMI × 年龄
                ('glucose', 'age'),  # 血糖 × 年龄
                ('heart_rate', 'age'),  # 心率 × 年龄
            ]

        # 创建交互特征
        n_created = 0
        for feat1, feat2 in interaction_pairs:
            # 检查特征是否存在
            if feat1 in X.columns and feat2 in X.columns:
                # 乘法交互
                interaction_name = f'{feat1}_x_{feat2}'
                X_with_interactions[interaction_name] = X[feat1] * X[feat2]
                n_created += 1

                # 比值交互（避免除零）
                if (X[feat2] != 0).all():
                    ratio_name = f'{feat1}_div_{feat2}'
                    X_with_interactions[ratio_name] = X[feat1] / (X[feat2] + 1e-10)
                    n_created += 1

        logger.info(f"创建了 {n_created} 个交互特征")
        logger.info(f"总特征数: {X_with_interactions.shape[1]}")

        return X_with_interactions

    def remove_correlated_features(self, X: pd.DataFrame,
                                   threshold: float = 0.95) -> pd.DataFrame:
        """
        移除高度相关的特征

        论文要求：特征扩展后经相关性分析剔除高度冗余的特征组合

        Parameters:
        -----------
        X : pd.DataFrame
            输入特征
        threshold : float
            相关系数阈值，默认0.95

        Returns:
        --------
        X_reduced : pd.DataFrame
            移除相关特征后的数据
        """
        logger.info(f"开始移除高度相关特征，threshold={threshold}")
        logger.info(f"原始特征数: {X.shape[1]}")

        # 计算相关矩阵
        corr_matrix = X.corr().abs()

        # 找到高度相关的特征对
        upper_triangle = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )

        # 找到需要移除的特征
        to_drop = [column for column in upper_triangle.columns
                  if any(upper_triangle[column] > threshold)]

        # 移除特征（训练集上确定的列表，用于 val/test 同步删除）
        self.correlation_dropped_columns_ = list(to_drop)
        X_reduced = X.drop(columns=to_drop)

        logger.info(f"移除了 {len(to_drop)} 个高度相关特征")
        logger.info(f"保留特征数: {X_reduced.shape[1]}")

        if to_drop:
            logger.info("移除的特征:")
            for feature in to_drop:
                logger.info(f"  {feature}")

        return X_reduced

    def get_feature_importance(self, X: pd.DataFrame, y: pd.Series,
                              n_estimators: int = 100) -> pd.DataFrame:
        """
        计算特征重要性

        Parameters:
        -----------
        X : pd.DataFrame
            输入特征
        y : pd.Series
            目标变量
        n_estimators : int
            随机森林树的数量

        Returns:
        --------
        importance_df : pd.DataFrame
            特征重要性DataFrame
        """
        logger.info("计算特征重要性")

        # 训练随机森林
        rf = RandomForestClassifier(
            n_estimators=n_estimators,
            random_state=42,
            n_jobs=-1
        )
        rf.fit(X, y)

        # 获取特征重要性
        importance_df = pd.DataFrame({
            'feature': X.columns,
            'importance': rf.feature_importances_
        }).sort_values('importance', ascending=False)

        # 记录特征重要性
        self.feature_scores['rf_importance'] = importance_df.set_index('feature')['importance'].to_dict()

        # 显示Top 10特征
        logger.info("特征重要性Top 10:")
        for idx, row in importance_df.head(10).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.4f}")

        return importance_df

    def feature_engineering_pipeline(self, X: pd.DataFrame, y: pd.Series,
                                    variance_threshold: float = 0.01,
                                    mi_percentile: float = 0.8,
                                    n_features_rfe: Optional[int] = None,
                                    create_poly: bool = True,
                                    poly_degree: int = 2,
                                    create_interactions: bool = True,
                                    remove_correlated: bool = True,
                                    corr_threshold: float = 0.95) -> Tuple[pd.DataFrame, Dict]:
        """
        完整的特征工程流程

        论文要求：从52个原始特征筛选到38个核心特征，扩展到45维

        Parameters:
        -----------
        X : pd.DataFrame
            输入特征
        y : pd.Series
            目标变量
        variance_threshold : float
            方差阈值
        mi_percentile : float
            互信息保留百分比
        n_features_rfe : int, optional
            RFE选择的特征数量
        create_poly : bool
            是否创建多项式特征
        poly_degree : int
            多项式阶数
        create_interactions : bool
            是否创建临床交互特征
        remove_correlated : bool
            是否移除相关特征
        corr_threshold : float
            相关系数阈值

        Returns:
        --------
        X_engineered : pd.DataFrame
            特征工程后的数据
        report : dict
            特征工程报告
        """
        logger.info("=" * 60)
        logger.info("开始完整特征工程流程")
        logger.info("=" * 60)

        self._fit_create_poly = create_poly
        self._fit_create_interactions = create_interactions
        self._fit_remove_correlated = remove_correlated
        self.correlation_dropped_columns_ = []

        report = {
            'original_features': X.shape[1],
            'steps': []
        }

        X_engineered = X.copy()

        # 阶段1：方差阈值选择
        X_engineered = self.variance_threshold_selection(X_engineered, variance_threshold)
        report['steps'].append({
            'step': 'variance_threshold',
            'n_features': X_engineered.shape[1]
        })

        # 阶段2：互信息选择
        X_engineered = self.mutual_information_selection(X_engineered, y, percentile=mi_percentile)
        report['steps'].append({
            'step': 'mutual_information',
            'n_features': X_engineered.shape[1]
        })

        # 阶段3：RFE选择
        if n_features_rfe is None:
            # 论文要求：从52个特征筛选到38个
            n_features_rfe = min(38, X_engineered.shape[1])

        X_engineered = self.rfe_selection(X_engineered, y, n_features_rfe)
        report['steps'].append({
            'step': 'rfe',
            'n_features': X_engineered.shape[1]
        })
        report['core_features'] = X_engineered.shape[1]

        # 阶段4：创建临床交互特征
        if create_interactions:
            X_engineered = self.create_clinical_interactions(X_engineered)
            report['steps'].append({
                'step': 'clinical_interactions',
                'n_features': X_engineered.shape[1]
            })

        # 阶段5：多项式特征扩展（可选）
        if create_poly:
            # 只对部分特征进行多项式扩展，避免特征爆炸
            # 选择重要性最高的特征
            importance_df = self.get_feature_importance(X_engineered, y)
            top_features = importance_df.head(10)['feature'].tolist()
            self._poly_subset_columns = list(top_features)

            X_poly = self.create_polynomial_features(
                X_engineered[top_features],
                degree=poly_degree,
                interaction_only=True  # 只生成交互项
            )

            # 合并原始特征和多项式特征
            X_engineered = pd.concat([X_engineered, X_poly], axis=1)
            report['steps'].append({
                'step': 'polynomial_features',
                'n_features': X_engineered.shape[1]
            })

        # 阶段6：移除高度相关特征
        if remove_correlated:
            X_engineered = self.remove_correlated_features(X_engineered, corr_threshold)
            report['steps'].append({
                'step': 'remove_correlated',
                'n_features': X_engineered.shape[1]
            })

        report['final_features'] = X_engineered.shape[1]
        self.selected_features = X_engineered.columns.tolist()

        logger.info("=" * 60)
        logger.info("特征工程流程完成")
        logger.info(f"原始特征数: {report['original_features']}")
        logger.info(f"核心特征数: {report['core_features']}")
        logger.info(f"最终特征数: {report['final_features']}")
        logger.info("=" * 60)

        return X_engineered, report

    def transform_pipeline(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        将已在训练集上拟合好的流程应用到验证集/测试集。

        训练阶段会生成交互项、多项式项等，这些列不会出现在原始 X_val/X_test 上，
        不能简单用列名子集索引，必须重复方差筛选 → MI 列 → RFE → 交互 → 多项式 → 删相关列。
        """
        if self.variance_selector is None or self.rfe_selector is None:
            raise ValueError("请先调用 feature_engineering_pipeline 在训练集上拟合")
        if not self.mi_selected_columns_:
            raise ValueError("缺少互信息阶段保留的列名，无法变换新数据")

        X = X.copy()
        mask_v = self.variance_selector.get_support()
        var_cols = X.columns[mask_v].tolist()
        X_v = pd.DataFrame(
            self.variance_selector.transform(X),
            columns=var_cols,
            index=X.index,
        )

        X_mi = X_v[self.mi_selected_columns_]

        rfe_mask = self.rfe_selector.get_support()
        rfe_cols = X_mi.columns[rfe_mask].tolist()
        X_rfe = pd.DataFrame(
            self.rfe_selector.transform(X_mi),
            columns=rfe_cols,
            index=X.index,
        )

        if self._fit_create_interactions:
            X_eng = self.create_clinical_interactions(X_rfe)
        else:
            X_eng = X_rfe

        if self._fit_create_poly:
            if self.poly_features is None or not self._poly_subset_columns:
                raise ValueError("多项式分支未正确拟合，无法变换新数据")
            sub = [c for c in self._poly_subset_columns if c in X_eng.columns]
            if len(sub) != len(self._poly_subset_columns):
                missing = set(self._poly_subset_columns) - set(X_eng.columns)
                raise ValueError(f"变换数据缺少多项式输入列: {missing}")
            X_poly_arr = self.poly_features.transform(X_eng[self._poly_subset_columns])
            poly_names = list(self.poly_features.get_feature_names_out(self._poly_subset_columns))
            X_poly = pd.DataFrame(X_poly_arr, columns=poly_names, index=X.index)
            X_eng = pd.concat([X_eng, X_poly], axis=1)

        if self._fit_remove_correlated and self.correlation_dropped_columns_:
            drop_here = [c for c in self.correlation_dropped_columns_ if c in X_eng.columns]
            if drop_here:
                X_eng = X_eng.drop(columns=drop_here)

        if self.selected_features is None:
            raise ValueError("selected_features 未设置")
        return X_eng.reindex(columns=self.selected_features, fill_value=0.0)


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    # 生成测试数据
    np.random.seed(42)
    n_samples = 1000
    n_features = 52  # 论文中的原始特征数

    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)]
    )

    # 添加一些命名特征用于测试临床交互
    X['age'] = np.random.randint(30, 80, n_samples)
    X['sbp'] = np.random.randint(100, 180, n_samples)
    X['dbp'] = np.random.randint(60, 100, n_samples)
    X['cholesterol'] = np.random.uniform(3.0, 7.0, n_samples)
    X['ldl'] = np.random.uniform(1.5, 5.0, n_samples)
    X['hdl'] = np.random.uniform(0.8, 2.5, n_samples)
    X['bmi'] = np.random.uniform(18, 35, n_samples)
    X['glucose'] = np.random.uniform(4.0, 10.0, n_samples)
    X['heart_rate'] = np.random.randint(60, 100, n_samples)

    # 生成标签
    y = pd.Series(np.random.choice([0, 1], size=n_samples, p=[0.7, 0.3]), name='target')

    # 执行特征工程
    engineer = AdvancedFeatureEngineer()
    X_engineered, report = engineer.feature_engineering_pipeline(
        X, y,
        variance_threshold=0.01,
        mi_percentile=0.8,
        n_features_rfe=38,
        create_poly=False,  # 暂时关闭多项式扩展
        create_interactions=True,
        remove_correlated=True
    )

    print("\n特征工程完成！")
    print(f"原始特征数: {report['original_features']}")
    print(f"最终特征数: {report['final_features']}")
    print("\n各阶段特征数:")
    for step in report['steps']:
        print(f"  {step['step']}: {step['n_features']}")
