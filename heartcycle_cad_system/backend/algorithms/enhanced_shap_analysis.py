"""
增强的SHAP可解释性分析模块
实现论文第5.5节要求的SHAP分析功能
"""
import numpy as np
import pandas as pd
from scipy.special import expit
import matplotlib.pyplot as plt
import seaborn as sns
import inspect
import shap
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class EnhancedSHAPAnalyzer:
    """增强的SHAP分析器"""

    def __init__(self, model, X_train: pd.DataFrame):
        """
        初始化SHAP分析器

        Parameters:
        -----------
        model : sklearn model
            训练好的模型
        X_train : pd.DataFrame
            训练数据（用于SHAP背景数据）
        """
        self.model = model
        self.X_train = X_train
        self.explainer = None
        self.shap_values = None
        self.feature_importance = None

    def create_explainer(self, explainer_type: str = 'tree',
                        n_background: int = 100):
        """
        创建SHAP解释器

        Parameters:
        -----------
        explainer_type : str
            解释器类型：'tree', 'kernel', 'linear'
        n_background : int
            背景数据样本数量
        """
        logger.info(f"创建SHAP解释器: {explainer_type}")

        if explainer_type == 'tree':
            # 树模型解释器（适用于RF、XGBoost、LightGBM）
            self.explainer = shap.TreeExplainer(self.model)
        elif explainer_type == 'kernel':
            # 核解释器（模型无关，但较慢）
            background = shap.sample(self.X_train, n_background)
            self.explainer = shap.KernelExplainer(
                self.model.predict_proba,
                background
            )
        elif explainer_type == 'linear':
            # 线性解释器（适用于线性模型）
            self.explainer = shap.LinearExplainer(
                self.model,
                self.X_train
            )
        else:
            raise ValueError(f"不支持的解释器类型: {explainer_type}")

        logger.info("SHAP解释器创建完成")

    def compute_shap_values(self, X: pd.DataFrame,
                           check_additivity: bool = False) -> np.ndarray:
        """
        计算SHAP值

        Parameters:
        -----------
        X : pd.DataFrame
            要解释的数据
        check_additivity : bool
            是否检查可加性

        Returns:
        --------
        shap_values : np.ndarray
            SHAP值数组
        """
        logger.info(f"计算SHAP值: {X.shape[0]} 个样本")

        if self.explainer is None:
            raise ValueError("请先调用create_explainer()创建解释器")

        # LinearExplainer 等旧版 shap 的 shap_values 不支持 check_additivity
        _shap_fn = self.explainer.shap_values
        if "check_additivity" in inspect.signature(_shap_fn).parameters:
            self.shap_values = _shap_fn(X, check_additivity=check_additivity)
        else:
            self.shap_values = _shap_fn(X)

        # 如果是二分类，取正类的SHAP值
        if isinstance(self.shap_values, list):
            self.shap_values = self.shap_values[1]

        logger.info(f"SHAP值计算完成: {self.shap_values.shape}")

        return self.shap_values

    def get_global_feature_importance(self, X: pd.DataFrame,
                                     top_k: int = 10) -> pd.DataFrame:
        """
        全局特征重要性分析

        论文要求：识别对整个数据集预测最重要的特征，Top 10排名

        Parameters:
        -----------
        X : pd.DataFrame
            数据
        top_k : int
            返回前k个重要特征

        Returns:
        --------
        importance_df : pd.DataFrame
            特征重要性DataFrame
        """
        logger.info("计算全局特征重要性")

        if self.shap_values is None:
            self.compute_shap_values(X)

        # 计算每个特征的平均绝对SHAP值
        mean_abs_shap = np.abs(self.shap_values).mean(axis=0)

        # 创建DataFrame
        importance_df = pd.DataFrame({
            'feature': X.columns,
            'importance': mean_abs_shap,
            'importance_pct': mean_abs_shap / mean_abs_shap.sum() * 100
        }).sort_values('importance', ascending=False)

        self.feature_importance = importance_df

        # 显示Top K
        logger.info(f"特征重要性Top {top_k}:")
        for idx, row in importance_df.head(top_k).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.4f} ({row['importance_pct']:.2f}%)")

        return importance_df.head(top_k)

    def plot_summary(self, X: pd.DataFrame, max_display: int = 20,
                    save_path: Optional[str] = None):
        """
        绘制SHAP汇总图

        Parameters:
        -----------
        X : pd.DataFrame
            数据
        max_display : int
            显示的最大特征数
        save_path : str, optional
            保存路径
        """
        logger.info("绘制SHAP汇总图")

        if self.shap_values is None:
            self.compute_shap_values(X)

        plt.figure(figsize=(10, 8))
        shap.summary_plot(
            self.shap_values,
            X,
            max_display=max_display,
            show=False
        )
        plt.title('SHAP特征重要性汇总图', fontsize=14, pad=20)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"汇总图已保存: {save_path}")

        plt.show()

    def plot_bar(self, X: pd.DataFrame, max_display: int = 10,
                save_path: Optional[str] = None):
        """
        绘制SHAP条形图

        Parameters:
        -----------
        X : pd.DataFrame
            数据
        max_display : int
            显示的最大特征数
        save_path : str, optional
            保存路径
        """
        logger.info("绘制SHAP条形图")

        if self.shap_values is None:
            self.compute_shap_values(X)

        plt.figure(figsize=(10, 6))
        shap.summary_plot(
            self.shap_values,
            X,
            plot_type='bar',
            max_display=max_display,
            show=False
        )
        plt.title('SHAP特征重要性排名', fontsize=14, pad=20)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"条形图已保存: {save_path}")

        plt.show()

    def plot_force(self, X: pd.DataFrame, sample_idx: int = 0,
                  save_path: Optional[str] = None):
        """
        绘制SHAP力图（个体预测解释）

        论文要求：量化每个特征对个体预测的贡献

        Parameters:
        -----------
        X : pd.DataFrame
            数据
        sample_idx : int
            样本索引
        save_path : str, optional
            保存路径
        """
        logger.info(f"绘制样本 {sample_idx} 的SHAP力图")

        if self.shap_values is None:
            self.compute_shap_values(X)

        # 获取基准值
        if hasattr(self.explainer, 'expected_value'):
            expected_value = self.explainer.expected_value
            if isinstance(expected_value, list):
                expected_value = expected_value[1]
        else:
            expected_value = 0

        # 绘制力图
        shap.force_plot(
            expected_value,
            self.shap_values[sample_idx],
            X.iloc[sample_idx],
            matplotlib=True,
            show=False
        )

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"力图已保存: {save_path}")

        plt.show()

    def plot_dependence(self, X: pd.DataFrame, feature: str,
                       interaction_feature: Optional[str] = None,
                       save_path: Optional[str] = None):
        """
        绘制SHAP依赖图

        Parameters:
        -----------
        X : pd.DataFrame
            数据
        feature : str
            主特征名称
        interaction_feature : str, optional
            交互特征名称
        save_path : str, optional
            保存路径
        """
        logger.info(f"绘制特征 {feature} 的依赖图")

        if self.shap_values is None:
            self.compute_shap_values(X)

        plt.figure(figsize=(10, 6))
        shap.dependence_plot(
            feature,
            self.shap_values,
            X,
            interaction_index=interaction_feature,
            show=False
        )
        plt.title(f'{feature} 的SHAP依赖图', fontsize=14, pad=20)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"依赖图已保存: {save_path}")

        plt.show()

    def explain_prediction(self, X: pd.DataFrame, sample_idx: int,
                          top_k: int = 10) -> Dict:
        """
        解释单个预测

        论文要求：个体预测解释，识别患者特定的风险特征

        Parameters:
        -----------
        X : pd.DataFrame
            数据
        sample_idx : int
            样本索引
        top_k : int
            返回前k个重要特征

        Returns:
        --------
        explanation : dict
            解释结果
        """
        logger.info(f"解释样本 {sample_idx} 的预测")

        if self.shap_values is None:
            self.compute_shap_values(X)

        # 获取该样本的SHAP值
        sample_shap = self.shap_values[sample_idx]
        sample_features = X.iloc[sample_idx]

        # 获取基准值
        if hasattr(self.explainer, 'expected_value'):
            base_value = self.explainer.expected_value
            if isinstance(base_value, list):
                base_value = base_value[1]
        else:
            base_value = 0

        # SHAP 加和为「边际输出」（对数几率等），不是 [0,1] 概率；展示与临床解读须用 predict_proba
        margin = float(base_value + np.sum(sample_shap))
        x_row = X.iloc[[sample_idx]]
        if hasattr(self.model, "predict_proba"):
            prediction = float(self.model.predict_proba(x_row)[0, 1])
        else:
            prediction = float(expit(margin))

        prediction = float(np.clip(prediction, 0.0, 1.0))

        # 创建特征贡献DataFrame
        contributions = pd.DataFrame({
            'feature': X.columns,
            'value': sample_features.values,
            'shap_value': sample_shap,
            'abs_shap': np.abs(sample_shap)
        }).sort_values('abs_shap', ascending=False)

        # 分类为正向和负向贡献
        positive_contrib = contributions[contributions['shap_value'] > 0].head(top_k)
        negative_contrib = contributions[contributions['shap_value'] < 0].head(top_k)

        explanation = {
            'sample_idx': sample_idx,
            'base_value': base_value,
            'prediction': prediction,
            'prediction_margin': margin,
            'top_positive_features': positive_contrib.to_dict('records'),
            'top_negative_features': negative_contrib.to_dict('records'),
            'all_contributions': contributions.to_dict('records')
        }

        # 打印解释
        logger.info(f"基准值: {base_value:.4f}")
        logger.info(f"边际(基线+SHAP和): {margin:.4f}")
        logger.info(f"阳性类概率: {prediction:.4f}")
        logger.info(f"\n正向贡献Top {top_k}:")
        for _, row in positive_contrib.iterrows():
            logger.info(f"  {row['feature']}: {row['value']:.2f} → SHAP={row['shap_value']:.4f}")
        logger.info(f"\n负向贡献Top {top_k}:")
        for _, row in negative_contrib.iterrows():
            logger.info(f"  {row['feature']}: {row['value']:.2f} → SHAP={row['shap_value']:.4f}")

        return explanation

    def generate_clinical_interpretation(self, explanation: Dict) -> str:
        """
        生成临床意义解读

        论文要求：基于特征贡献指导治疗决策

        Parameters:
        -----------
        explanation : dict
            预测解释结果

        Returns:
        --------
        interpretation : str
            临床解读文本
        """
        interpretation = []

        interpretation.append("=== 冠心病风险评估临床解读 ===\n")

        # 风险等级（prediction 为 [0,1] 的阳性类概率）
        prediction = float(np.clip(explanation.get("prediction", 0.0), 0.0, 1.0))
        if prediction > 0.7:
            risk_level = "高风险"
        elif prediction > 0.4:
            risk_level = "中风险"
        else:
            risk_level = "低风险"

        interpretation.append(f"风险等级: {risk_level}")
        interpretation.append(f"风险概率（阳性类）: {prediction:.1%}\n")
        interpretation.append(
            "说明：下列「SHAP」表示该特征对模型决策边际的贡献，数值单位与模型输出一致，不等同于百分点。"
        )

        # 主要风险因素（SHAP>0 推向更高风险预测）
        interpretation.append("\n主要风险因素（SHAP 为正）:")
        for i, feat in enumerate(explanation['top_positive_features'][:5], 1):
            interpretation.append(
                f"{i}. {feat['feature']}: 特征值 {feat['value']:.2f}  |  SHAP {feat['shap_value']:+.4f}"
            )

        # 保护因素
        if explanation['top_negative_features']:
            interpretation.append("\n保护因素（SHAP 为负）:")
            for i, feat in enumerate(explanation['top_negative_features'][:3], 1):
                interpretation.append(
                    f"{i}. {feat['feature']}: 特征值 {feat['value']:.2f}  |  SHAP {feat['shap_value']:+.4f}"
                )

        # 医疗建议
        interpretation.append("\n医疗建议:")
        if prediction > 0.7:
            interpretation.append("1. 建议尽快就医进行进一步检查")
            interpretation.append("2. 控制血压、血脂、血糖水平")
            interpretation.append("3. 改善生活方式：戒烟、适量运动、控制饮食")
        elif prediction > 0.4:
            interpretation.append("1. 定期监测心血管健康指标")
            interpretation.append("2. 保持健康的生活方式")
            interpretation.append("3. 必要时咨询心血管专科医生")
        else:
            interpretation.append("1. 继续保持健康的生活方式")
            interpretation.append("2. 定期体检，监测心血管健康")

        return "\n".join(interpretation)


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    # 生成测试数据
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.datasets import make_classification

    X, y = make_classification(n_samples=1000, n_features=20, random_state=42)
    X = pd.DataFrame(X, columns=[f'feature_{i}' for i in range(20)])

    # 训练模型
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)

    # 创建SHAP分析器
    analyzer = EnhancedSHAPAnalyzer(model, X)
    analyzer.create_explainer(explainer_type='tree')

    # 计算SHAP值
    analyzer.compute_shap_values(X)

    # 全局特征重要性
    importance = analyzer.get_global_feature_importance(X, top_k=10)
    print("\n特征重要性:")
    print(importance)

    # 解释单个预测
    explanation = analyzer.explain_prediction(X, sample_idx=0, top_k=5)

    # 生成临床解读
    interpretation = analyzer.generate_clinical_interpretation(explanation)
    print("\n" + interpretation)
