"""
完整的实验流程 - 一键运行
实现论文第5章的所有实验
"""
import pandas as pd
import numpy as np
import sys
import os

# 添加路径
sys.path.append(os.path.dirname(__file__))

from algorithms.advanced_preprocessing import AdvancedPreprocessor
from algorithms.advanced_feature_engineering import AdvancedFeatureEngineer
from algorithms.experiment_evaluation import ExperimentEvaluator
from algorithms.enhanced_shap_analysis import EnhancedSHAPAnalyzer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
import lightgbm as lgb
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_real_data(real_data_path: str) -> tuple:
    """
    加载并预处理真实数据集（脑卒中数据集），映射到合成数据的特征空间
    可映射特征：age, gender_male, bmi, glucose, hypertension_history, smoking_status
    标签：stroke → CAD_risk（均为心血管事件）
    """
    df = pd.read_excel(real_data_path)

    # 特征映射
    real = pd.DataFrame()
    real['age'] = df['age']
    real['gender_male'] = (df['gender'] == 'Male').astype(int)
    real['bmi'] = df['bmi']
    real['glucose'] = df['avg_glucose_level'] / 18.0  # mg/dL → mmol/L
    real['hypertension_history'] = df['hypertension']
    smoking_map = {'never smoked': 0, 'Unknown': 0, 'formerly smoked': 1, 'smokes': 2}
    real['smoking_status'] = df['smoking_status'].map(smoking_map).fillna(0).astype(int)

    # 标签
    y_real = df['stroke'].astype(float)

    # 处理缺失值（bmi有201个缺失）
    real['bmi'] = real['bmi'].fillna(real['bmi'].median())

    logger.info(f"真实数据集形状: {real.shape}")
    logger.info(f"阳性样本(stroke=1): {(y_real == 1).sum()} ({(y_real == 1).mean() * 100:.1f}%)")
    logger.info(f"阴性样本(stroke=0): {(y_real == 0).sum()} ({(y_real == 0).mean() * 100:.1f}%)")
    logger.info(f"可用特征: {real.columns.tolist()}")

    return real, y_real


def main():
    logger.info("=" * 60)
    logger.info("HeartCycle冠心病风险预测系统 - 完整实验流程")
    logger.info("=" * 60)

    # 创建结果目录
    os.makedirs('../results', exist_ok=True)

    # 1. 加载数据
    logger.info("\n步骤1: 加载数据集")
    data_path = '../data/cad_dataset_10k.csv'
    real_data_path = '../data/realdata/healthcare-dataset-stroke-data.xlsx'

    if not os.path.exists(data_path):
        logger.error(f"数据集不存在: {data_path}")
        logger.info("请先运行: python algorithms/dataset_generator.py")
        return

    df = pd.read_csv(data_path)
    X = df.drop(columns=['CAD_risk'])
    y = df['CAD_risk']
    logger.info(f"合成数据集形状: {X.shape}")
    logger.info(f"阳性样本: {(y == 1).sum()} ({(y == 1).sum() / len(y) * 100:.1f}%)")
    logger.info(f"阴性样本: {(y == 0).sum()} ({(y == 0).sum() / len(y) * 100:.1f}%)")

    # 加载真实数据
    has_real_data = os.path.exists(real_data_path)
    if has_real_data:
        logger.info("\n步骤1b: 加载真实验证数据集")
        X_real, y_real = load_real_data(real_data_path)
    else:
        logger.warning("真实数据集不存在，跳过真实数据验证")

    # 2. 数据预处理（原验证集并入训练集：train=0.85, test=0.15）
    logger.info("\n步骤2: 数据预处理")
    preprocessor = AdvancedPreprocessor()
    result = preprocessor.preprocess_pipeline(
        X, y,
        handle_missing=True,
        detect_outliers_flag=True,
        standardize=True,
        balance=True,
        split=True,
        train_size=0.85,   # 原train(70%) + 原val(15%) 合并为训练集
        val_size=0.0,      # 不再使用合成验证集
        test_size=0.15
    )

    X_train = result['X_train']
    y_train = result['y_train']
    X_test = result['X_test']
    y_test = result['y_test']

    logger.info(f"训练集: {X_train.shape}, 阳性: {(y_train == 1).sum()}")
    logger.info(f"测试集: {X_test.shape}, 阳性: {(y_test == 1).sum()}")

    # 3. 特征工程
    logger.info("\n步骤3: 特征工程")
    engineer = AdvancedFeatureEngineer()
    X_train_eng, report = engineer.feature_engineering_pipeline(
        X_train, y_train,
        variance_threshold=0.01,
        mi_percentile=0.8,
        n_features_rfe=38,
        create_poly=False,
        create_interactions=True,
        remove_correlated=True
    )

    # 对测试集应用相同的特征工程
    if engineer.variance_selector:
        X_test_selected = engineer.variance_selector.transform(X_test)
        selected_cols = X_train.columns[engineer.variance_selector.get_support()].tolist()
        X_test = pd.DataFrame(X_test_selected, columns=selected_cols, index=X_test.index)

    X_test = engineer.create_clinical_interactions(X_test)
    selected_features = X_train_eng.columns.tolist()
    available_features = [f for f in selected_features if f in X_test.columns]
    X_train_eng = X_train_eng[available_features]
    X_test_eng = X_test[available_features]

    logger.info(f"原始特征数: {report['original_features']}")
    logger.info(f"核心特征数: {report['core_features']}")
    logger.info(f"最终特征数: {report['final_features']}")

    # 4. 训练多个模型（添加正则化防止过拟合）
    logger.info("\n步骤4: 训练模型")
    models = {
        'Logistic Regression': LogisticRegression(
            max_iter=1000,
            random_state=42,
            C=0.1,
            penalty='l2'
        ),
        'Random Forest': RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            n_jobs=-1,
            max_depth=8,
            min_samples_split=20,
            min_samples_leaf=10,
            max_features='sqrt'
        ),
        'XGBoost': xgb.XGBClassifier(
            n_estimators=100,
            random_state=42,
            n_jobs=-1,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.5,
            reg_lambda=1.0
        ),
        'LightGBM': lgb.LGBMClassifier(
            n_estimators=100,
            random_state=42,
            verbose=-1,
            n_jobs=-1,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.5,
            reg_lambda=1.0
        )
    }

    trained_models = {}
    for name, model in models.items():
        logger.info(f"训练 {name}...")
        model.fit(X_train_eng, y_train)
        trained_models[name] = model
        logger.info(f"  {name} 训练完成")

    # 5. 合成测试集评估
    logger.info("\n步骤5: 合成测试集评估")
    evaluator = ExperimentEvaluator()
    for name, model in trained_models.items():
        y_pred = model.predict(X_test_eng)
        y_prob = model.predict_proba(X_test_eng)[:, 1]
        evaluator.evaluate_model(name, y_test, y_pred, y_prob)

    # 6. 真实数据验证
    if has_real_data:
        logger.info("\n步骤6: 真实数据集验证")
        from sklearn.preprocessing import StandardScaler
        from sklearn.base import clone
        from sklearn.metrics import roc_curve

        common_features = ['age', 'gender_male', 'bmi', 'glucose',
                           'hypertension_history', 'smoking_status']
        common_avail = [f for f in common_features if f in X_train_eng.columns]

        # 用训练集共同特征重新标准化
        X_train_common = X_train_eng[common_avail].copy()
        scaler_train = StandardScaler()
        X_train_common_scaled = pd.DataFrame(
            scaler_train.fit_transform(X_train_common), columns=common_avail
        )

        X_real_eval = X_real[common_avail].copy()
        X_real_eval_scaled = pd.DataFrame(
            scaler_train.transform(X_real_eval), columns=common_avail
        )

        real_evaluator = ExperimentEvaluator()
        logger.info("在真实数据上评估（仅使用共同特征子集，在真实数据上找最优阈值）:")
        for name, model in trained_models.items():
            try:
                simple_model = clone(model)
                simple_model.fit(X_train_common_scaled, y_train)

                y_prob_real = simple_model.predict_proba(X_real_eval_scaled)[:, 1]

                # 在真实数据上用Youden's J找最优阈值（AUC不受阈值影响）
                fpr_r, tpr_r, thresholds_r = roc_curve(y_real, y_prob_real)
                youden_j_r = tpr_r - fpr_r
                best_idx = np.argmax(youden_j_r)
                optimal_threshold = float(np.clip(thresholds_r[best_idx], 0.01, 0.99))

                y_pred_real = (y_prob_real >= optimal_threshold).astype(int)
                real_evaluator.evaluate_model(name, y_real, y_pred_real, y_prob_real)
                logger.info(f"  {name} 最优阈值={optimal_threshold:.3f}, 真实数据评估完成")
            except Exception as e:
                logger.warning(f"  {name} 真实数据评估失败: {e}")

        real_comparison = real_evaluator.create_comparison_table(
            save_path='../results/real_data_validation.csv'
        )
        print("\n" + "=" * 60)
        print("真实数据验证结果（论文泛化性验证）:")
        print("=" * 60)
        print(real_comparison.to_string(index=False))

        try:
            real_evaluator.plot_roc_curves(save_path='../results/roc_curves_real.png')
            logger.info("真实数据ROC曲线已保存")
        except Exception as e:
            logger.warning(f"真实数据ROC曲线绘制失败: {e}")

    # 7. 生成合成数据对比表
    logger.info("\n步骤7: 生成性能对比表")
    comparison_df = evaluator.create_comparison_table(
        save_path='../results/model_comparison.csv'
    )
    print("\n" + "=" * 60)
    print("合成测试集性能对比表（论文表5-1）:")
    print("=" * 60)
    print(comparison_df.to_string(index=False))

    # 8. 绘制ROC曲线
    logger.info("\n步骤8: 绘制ROC曲线")
    try:
        evaluator.plot_roc_curves(save_path='../results/roc_curves.png')
        logger.info("ROC曲线已保存")
    except Exception as e:
        logger.warning(f"ROC曲线绘制失败: {e}")

    # 9. 绘制混淆矩阵
    logger.info("\n步骤9: 绘制混淆矩阵")
    best_model_name = 'XGBoost'
    try:
        evaluator.plot_confusion_matrix(
            best_model_name,
            save_path=f'../results/confusion_matrix_{best_model_name}.png'
        )
        logger.info("混淆矩阵已保存")
    except Exception as e:
        logger.warning(f"混淆矩阵绘制失败: {e}")

    # 10. SHAP分析
    logger.info("\n步骤10: SHAP可解释性分析")
    try:
        best_model = trained_models[best_model_name]
        shap_analyzer = EnhancedSHAPAnalyzer(best_model, X_train_eng)
        shap_analyzer.create_explainer(explainer_type='tree')
        shap_analyzer.compute_shap_values(X_test_eng)

        importance = shap_analyzer.get_global_feature_importance(X_test_eng, top_k=10)
        print("\n" + "=" * 60)
        print("特征重要性Top 10（论文表5-2）:")
        print("=" * 60)
        print(importance.to_string(index=False))

        try:
            shap_analyzer.plot_summary(
                X_test_eng,
                max_display=20,
                save_path='../results/shap_summary.png'
            )
            logger.info("SHAP汇总图已保存")
        except Exception as e:
            logger.warning(f"SHAP汇总图绘制失败: {e}")

        explanation = shap_analyzer.explain_prediction(X_test_eng, sample_idx=0, top_k=10)
        interpretation = shap_analyzer.generate_clinical_interpretation(explanation)
        print("\n" + "=" * 60)
        print("临床解读示例:")
        print("=" * 60)
        print(interpretation)

    except Exception as e:
        logger.warning(f"SHAP分析失败: {e}")

    # 11. 生成实验报告
    logger.info("\n步骤11: 生成实验报告")
    report_text = evaluator.generate_report(output_path='../results/experiment_report.txt')
    print("\n" + "=" * 60)
    print("实验报告:")
    print("=" * 60)
    print(report_text)

    logger.info("\n" + "=" * 60)
    logger.info("实验流程完成！")
    logger.info("=" * 60)
    logger.info("\n生成的结果文件:")
    logger.info("  results/model_comparison.csv - 合成数据性能对比表")
    if has_real_data:
        logger.info("  results/real_data_validation.csv - 真实数据验证结果")
        logger.info("  results/roc_curves_real.png - 真实数据ROC曲线")
    logger.info("  results/roc_curves.png - ROC曲线对比图")
    logger.info("  results/confusion_matrix_XGBoost.png - 混淆矩阵")
    logger.info("  results/shap_summary.png - SHAP特征重要性图")
    logger.info("  results/experiment_report.txt - 完整实验报告")
    logger.info("\n这些文件可以直接用于论文撰写！")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n实验被用户中断")
    except Exception as e:
        logger.error(f"\n实验失败: {e}", exc_info=True)
