"""
简化版模型测试脚本 - 只测试关键模型
"""
import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'backend'))

from algorithms.model_training import ModelTrainer

def test_models():
    print("="*60)
    print("模型性能测试")
    print("="*60)

    # 加载数据
    print("\n[1/4] 加载数据...")
    feature_file = "data/features/train_features.csv"
    label_file = "data/features/train_labels.csv"

    df_features = pd.read_csv(feature_file)
    df_labels = pd.read_csv(label_file)

    X = df_features.values
    y = df_labels.iloc[:, 0].values
    feature_names = df_features.columns.tolist()

    print(f"   样本数: {len(X)}")
    print(f"   特征数: {X.shape[1]}")
    print(f"   类别分布: {dict(zip(*np.unique(y, return_counts=True)))}")

    # 测试模型配置
    models = [
        ('rf', False, '随机森林(无SMOTE)'),
        ('rf', True, '随机森林(有SMOTE)'),
        ('xgb', True, 'XGBoost(有SMOTE)'),
        ('lgb', True, 'LightGBM(有SMOTE)'),
    ]

    results = []

    for i, (model_type, use_smote, desc) in enumerate(models, 1):
        print(f"\n[{i+1}/{len(models)+1}] 测试 {desc}...")

        try:
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

            metrics = result['metrics']
            auc = metrics['roc_auc']['mean'] if metrics['roc_auc']['mean'] else 0.0

            results.append({
                'model': desc,
                'accuracy': metrics['accuracy']['mean'],
                'precision': metrics['precision']['mean'],
                'recall': metrics['recall']['mean'],
                'f1': metrics['f1']['mean'],
                'auc': auc
            })

            print(f"   AUC: {auc:.4f}")
            print(f"   Accuracy: {metrics['accuracy']['mean']:.4f}")
            print(f"   F1: {metrics['f1']['mean']:.4f}")

        except Exception as e:
            print(f"   错误: {str(e)}")
            results.append({
                'model': desc,
                'accuracy': 0,
                'precision': 0,
                'recall': 0,
                'f1': 0,
                'auc': 0
            })

    # 显示对比结果
    print(f"\n{'='*60}")
    print("性能对比")
    print(f"{'='*60}\n")

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('auc', ascending=False)

    print(df_results.to_string(index=False))

    # 保存结果
    output_dir = Path("test_results")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = output_dir / f"quick_test_{timestamp}.csv"
    df_results.to_csv(csv_file, index=False, encoding='utf-8-sig')

    print(f"\n结果已保存: {csv_file}")
    print("\n测试完成!")

if __name__ == '__main__':
    test_models()
