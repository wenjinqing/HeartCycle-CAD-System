"""
SHAP特征重要性分析工具

使用方法:
python analyze_feature_importance.py --model_id your_model_id --feature_file path/to/features.csv --label_file path/to/labels.csv
"""

import sys
import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
import argparse

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'backend'))

from algorithms.model_training import ModelTrainer
import shap

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


def load_data(feature_file: str, label_file: str):
    """加载数据"""
    print(f" 加载数据...")

    # 加载特征
    df_features = pd.read_csv(feature_file)
    X = df_features.values
    feature_names = df_features.columns.tolist()

    # 加载标签
    df_labels = pd.read_csv(label_file)
    if 'label' in df_labels.columns:
        y = df_labels['label'].values
    elif 'target' in df_labels.columns:
        y = df_labels['target'].values
    else:
        y = df_labels.iloc[:, 0].values

    print(f"[OK] 数据加载完成: {len(X)}样本, {X.shape[1]}特征")

    return X, y, feature_names, df_features


def train_model_for_analysis(X, y, feature_names, model_type='xgb', use_smote=True):
    """训练模型用于分析"""
    print(f"\n 训练{model_type.upper()}模型...")

    trainer = ModelTrainer(random_state=42)
    result = trainer.train(
        X=X,
        y=y,
        model_type=model_type,
        cv_folds=5,
        feature_names=feature_names,
        use_smote=use_smote,
        optimize_hyperparams=False
    )

    print(f"[OK] 模型训练完成")
    print(f"   AUC: {result['metrics']['roc_auc']['mean']:.4f}")

    return trainer.model, result


def analyze_feature_importance_builtin(model, feature_names, output_dir):
    """分析内置特征重要性（适用于树模型）"""
    print(f"\n 分析内置特征重要性...")

    if not hasattr(model, 'feature_importances_'):
        print("[WARNING] 模型不支持内置特征重要性")
        return None

    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]

    # 创建DataFrame
    df_importance = pd.DataFrame({
        'feature': [feature_names[i] for i in indices],
        'importance': importances[indices]
    })

    # 打印Top 20
    print(f"\n Top 20 重要特征:")
    for i in range(min(20, len(df_importance))):
        print(f"   {i+1:2d}. {df_importance.iloc[i]['feature']:30s} {df_importance.iloc[i]['importance']:.6f}")

    # 可视化
    plt.figure(figsize=(12, 8))
    top_n = min(30, len(df_importance))
    sns.barplot(data=df_importance.head(top_n), x='importance', y='feature', palette='viridis')
    plt.title(f'Top {top_n} 特征重要性', fontsize=16, fontweight='bold')
    plt.xlabel('重要性', fontsize=12)
    plt.ylabel('特征', fontsize=12)
    plt.tight_layout()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_file = output_path / f"feature_importance_builtin_{timestamp}.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f" 特征重要性图已保存: {plot_file}")
    plt.close()

    # 保存CSV
    csv_file = output_path / f"feature_importance_builtin_{timestamp}.csv"
    df_importance.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f" 特征重要性数据已保存: {csv_file}")

    return df_importance


def analyze_shap_values(model, X, feature_names, output_dir, max_samples=100):
    """使用SHAP分析特征重要性"""
    print(f"\n 计算SHAP值...")

    try:
        # 限制样本数以加快计算
        if len(X) > max_samples:
            indices = np.random.choice(len(X), max_samples, replace=False)
            X_sample = X[indices]
            print(f"   使用{max_samples}个样本进行SHAP分析")
        else:
            X_sample = X
            print(f"   使用全部{len(X)}个样本进行SHAP分析")

        # 创建SHAP解释器
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_sample)

        # 如果是二分类，取正类的SHAP值
        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        print(f"[OK] SHAP值计算完成")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. Summary Plot（特征重要性排序）
        print(f"\n 生成SHAP Summary Plot...")
        plt.figure(figsize=(12, 10))
        shap.summary_plot(shap_values, X_sample, feature_names=feature_names, show=False)
        plt.tight_layout()
        plot_file = output_path / f"shap_summary_{timestamp}.png"
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f" SHAP Summary Plot已保存: {plot_file}")
        plt.close()

        # 2. Bar Plot（平均绝对SHAP值）
        print(f"\n 生成SHAP Bar Plot...")
        plt.figure(figsize=(12, 10))
        shap.summary_plot(shap_values, X_sample, feature_names=feature_names, plot_type="bar", show=False)
        plt.tight_layout()
        plot_file = output_path / f"shap_bar_{timestamp}.png"
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f" SHAP Bar Plot已保存: {plot_file}")
        plt.close()

        # 3. 计算全局特征重要性
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        indices = np.argsort(mean_abs_shap)[::-1]

        df_shap_importance = pd.DataFrame({
            'feature': [feature_names[i] for i in indices],
            'mean_abs_shap': mean_abs_shap[indices]
        })

        print(f"\n Top 20 SHAP重要特征:")
        for i in range(min(20, len(df_shap_importance))):
            print(f"   {i+1:2d}. {df_shap_importance.iloc[i]['feature']:30s} {df_shap_importance.iloc[i]['mean_abs_shap']:.6f}")

        # 保存CSV
        csv_file = output_path / f"shap_importance_{timestamp}.csv"
        df_shap_importance.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f" SHAP重要性数据已保存: {csv_file}")

        # 4. 分析新增特征的重要性
        analyze_new_features(df_shap_importance, output_path, timestamp)

        return df_shap_importance, shap_values

    except Exception as e:
        print(f"[ERROR] SHAP分析失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None


def analyze_new_features(df_importance, output_dir, timestamp):
    """分析新增特征的重要性"""
    print(f"\n[NEW] 分析新增特征...")

    # 定义新增特征列表
    new_features = [
        # 时域新增特征
        'pnn20', 'cv', 'cvsd', 'sdann', 'range_rr', 'q1_rr', 'q3_rr', 'iqr_rr',
        # 频域新增特征
        'lf_peak', 'hf_peak', 'log_total_power', 'log_lf_power', 'log_hf_power', 'spectral_entropy',
        # 非线性新增特征
        'dfa_alpha1', 'dfa_alpha2', 'ac', 'dc', 'complexity_index'
    ]

    # 筛选新增特征
    df_new = df_importance[df_importance['feature'].isin(new_features)].copy()

    if len(df_new) == 0:
        print("[WARNING] 未找到新增特征")
        return

    print(f"\n找到 {len(df_new)} 个新增特征:")
    for i, row in df_new.iterrows():
        rank = df_importance.index[df_importance['feature'] == row['feature']].tolist()[0] + 1
        print(f"   {row['feature']:30s} 排名: {rank:3d}/{len(df_importance)} 重要性: {row.iloc[1]:.6f}")

    # 可视化新增特征重要性
    plt.figure(figsize=(12, 8))
    df_new_sorted = df_new.sort_values(by=df_new.columns[1], ascending=True)
    plt.barh(df_new_sorted['feature'], df_new_sorted.iloc[:, 1], color='coral')
    plt.xlabel('重要性', fontsize=12)
    plt.ylabel('新增特征', fontsize=12)
    plt.title('新增特征重要性分析', fontsize=16, fontweight='bold')
    plt.tight_layout()

    plot_file = output_dir / f"new_features_importance_{timestamp}.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f" 新增特征重要性图已保存: {plot_file}")
    plt.close()

    # 保存CSV
    csv_file = output_dir / f"new_features_importance_{timestamp}.csv"
    df_new_sorted.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f" 新增特征数据已保存: {csv_file}")


def compare_feature_categories(df_importance, output_dir, timestamp):
    """对比不同类别特征的重要性"""
    print(f"\n 对比特征类别...")

    # 定义特征类别
    time_domain = ['mean_rr', 'std_rr', 'min_rr', 'max_rr', 'median_rr', 'sdnn', 'rmssd',
                   'pnn50', 'pnn20', 'sdsd', 'hrv_triangular_index', 'tinn', 'mean_hr',
                   'cv', 'cvsd', 'sdann', 'range_rr', 'q1_rr', 'q3_rr', 'iqr_rr']

    freq_domain = ['total_power', 'vlf_power', 'lf_power', 'hf_power', 'lf_hf_ratio',
                   'lf_norm', 'hf_norm', 'vlf_percent', 'lf_percent', 'hf_percent',
                   'lf_peak', 'hf_peak', 'log_total_power', 'log_lf_power', 'log_hf_power',
                   'spectral_entropy']

    nonlinear = ['sd1', 'sd2', 'sd1_sd2_ratio', 'sample_entropy', 'approximate_entropy',
                 'dfa_alpha1', 'dfa_alpha2', 'ac', 'dc', 'complexity_index']

    # 分类统计
    categories = []
    for _, row in df_importance.iterrows():
        feature = row['feature']
        if feature in time_domain:
            categories.append('时域特征')
        elif feature in freq_domain:
            categories.append('频域特征')
        elif feature in nonlinear:
            categories.append('非线性特征')
        else:
            categories.append('其他特征')

    df_importance['category'] = categories

    # 计算每个类别的平均重要性
    category_importance = df_importance.groupby('category')[df_importance.columns[1]].agg(['mean', 'sum', 'count'])
    category_importance = category_importance.sort_values('mean', ascending=False)

    print(f"\n特征类别重要性:")
    print(category_importance)

    # 可视化
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # 平均重要性
    axes[0].bar(category_importance.index, category_importance['mean'], color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'])
    axes[0].set_ylabel('平均重要性', fontsize=12)
    axes[0].set_title('各类别特征平均重要性', fontsize=14, fontweight='bold')
    axes[0].tick_params(axis='x', rotation=45)

    # 总重要性
    axes[1].bar(category_importance.index, category_importance['sum'], color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'])
    axes[1].set_ylabel('总重要性', fontsize=12)
    axes[1].set_title('各类别特征总重要性', fontsize=14, fontweight='bold')
    axes[1].tick_params(axis='x', rotation=45)

    plt.tight_layout()
    plot_file = output_dir / f"category_importance_{timestamp}.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f" 类别重要性图已保存: {plot_file}")
    plt.close()

    # 保存CSV
    csv_file = output_dir / f"category_importance_{timestamp}.csv"
    category_importance.to_csv(csv_file, encoding='utf-8-sig')
    print(f" 类别重要性数据已保存: {csv_file}")


def generate_report(df_builtin, df_shap, output_dir):
    """生成分析报告"""
    print(f"\n 生成分析报告...")

    output_path = Path(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_path / f"feature_analysis_report_{timestamp}.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 特征重要性分析报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        if df_builtin is not None:
            f.write(f"## 内置特征重要性 (Top 20)\n\n")
            f.write(df_builtin.head(20).to_markdown(index=False))
            f.write(f"\n\n")

        if df_shap is not None:
            f.write(f"## SHAP特征重要性 (Top 20)\n\n")
            f.write(df_shap.head(20).to_markdown(index=False))
            f.write(f"\n\n")

        f.write(f"## 分析结论\n\n")
        f.write(f"1. 特征总数: {len(df_builtin) if df_builtin is not None else 'N/A'}\n")
        f.write(f"2. 分析方法: 内置重要性 + SHAP值\n")
        f.write(f"3. 详细图表请查看输出目录\n\n")

    print(f" 分析报告已保存: {report_file}")


def main():
    parser = argparse.ArgumentParser(description='SHAP特征重要性分析')
    parser.add_argument('--feature_file', type=str, required=True, help='特征文件路径')
    parser.add_argument('--label_file', type=str, required=True, help='标签文件路径')
    parser.add_argument('--model_type', type=str, default='xgb', choices=['rf', 'xgb', 'lgb'], help='模型类型')
    parser.add_argument('--use_smote', action='store_true', default=True, help='使用SMOTE')
    parser.add_argument('--output_dir', type=str, default='./feature_analysis', help='输出目录')
    parser.add_argument('--max_samples', type=int, default=100, help='SHAP分析最大样本数')

    args = parser.parse_args()

    print(f"{'='*80}")
    print(f" 特征重要性分析工具")
    print(f"{'='*80}\n")

    # 加载数据
    X, y, feature_names, df_features = load_data(args.feature_file, args.label_file)

    # 训练模型
    model, result = train_model_for_analysis(X, y, feature_names, args.model_type, args.use_smote)

    # 分析内置特征重要性
    df_builtin = analyze_feature_importance_builtin(model, feature_names, args.output_dir)

    # SHAP分析
    df_shap, shap_values = analyze_shap_values(model, X, feature_names, args.output_dir, args.max_samples)

    # 对比特征类别
    if df_shap is not None:
        output_path = Path(args.output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        compare_feature_categories(df_shap, output_path, timestamp)

    # 生成报告
    generate_report(df_builtin, df_shap, args.output_dir)

    print(f"\n[OK] 特征分析完成！")
    print(f" 所有结果已保存到: {args.output_dir}")


if __name__ == '__main__':
    main()
