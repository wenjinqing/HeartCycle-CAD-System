"""
验证模型优化效果
对比优化前后的模型性能
"""
import sys
from pathlib import Path

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_dir))

from algorithms.model_training import ModelTrainer
import pandas as pd
import numpy as np

def test_class_weight_optimization():
    """测试类权重优化是否生效"""
    print("=" * 60)
    print("类权重优化验证")
    print("=" * 60)

    # 创建模拟不平衡数据
    np.random.seed(42)
    n_samples = 100
    n_features = 10

    # 70% 负类，30% 正类
    X = np.random.randn(n_samples, n_features)
    y = np.array([0] * 70 + [1] * 30)

    # 打乱数据
    shuffle_idx = np.random.permutation(n_samples)
    X = X[shuffle_idx]
    y = y[shuffle_idx]

    print(f"\n数据集:")
    print(f"  总样本数: {n_samples}")
    print(f"  负类样本: {sum(y == 0)} ({sum(y == 0) / len(y) * 100:.1f}%)")
    print(f"  正类样本: {sum(y == 1)} ({sum(y == 1) / len(y) * 100:.1f}%)")

    # 测试不同模型
    models_to_test = ['rf', 'xgb', 'lgb']

    for model_type in models_to_test:
        print(f"\n{'='*60}")
        print(f"测试模型: {model_type.upper()}")
        print('='*60)

        try:
            trainer = ModelTrainer(random_state=42)
            trainer._create_model(model_type)

            # 检查类权重配置
            model = trainer.model

            if model_type == 'rf':
                class_weight = getattr(model, 'class_weight', None)
                print(f"  ✓ 随机森林类权重: {class_weight}")
                assert class_weight == 'balanced', "RF类权重未设置为balanced"

            elif model_type == 'xgb':
                scale_pos_weight = model.get_params().get('scale_pos_weight', 1)
                print(f"  ✓ XGBoost scale_pos_weight: {scale_pos_weight}")
                assert scale_pos_weight > 1, "XGBoost scale_pos_weight未设置"

                verbosity = model.get_params().get('verbosity', 1)
                print(f"  ✓ XGBoost verbosity: {verbosity}")
                assert verbosity == 0, "XGBoost警告未抑制"

            elif model_type == 'lgb':
                class_weight = model.get_params().get('class_weight', None)
                print(f"  ✓ LightGBM 类权重: {class_weight}")
                assert class_weight == 'balanced', "LightGBM类权重未设置为balanced"

            # 训练模型
            model.fit(X, y)

            # 预测
            y_pred = model.predict(X)

            # 统计预测结果
            pred_0 = sum(y_pred == 0)
            pred_1 = sum(y_pred == 1)

            print(f"\n  预测结果:")
            print(f"    预测为负类: {pred_0} ({pred_0 / len(y_pred) * 100:.1f}%)")
            print(f"    预测为正类: {pred_1} ({pred_1 / len(y_pred) * 100:.1f}%)")

            # 验证模型不是只预测一个类
            if pred_1 == 0:
                print(f"  ❌ 警告: 模型仍然只预测负类！")
            else:
                print(f"  ✅ 成功: 模型能够预测两个类别")

        except Exception as e:
            print(f"  ❌ 错误: {str(e)}")

    print(f"\n{'='*60}")
    print("验证完成！")
    print('='*60)


def test_warning_suppression():
    """测试警告抑制"""
    print("\n" + "=" * 60)
    print("警告抑制验证")
    print("=" * 60)

    import warnings
    import sys
    from io import StringIO

    # 捕获stderr
    old_stderr = sys.stderr
    sys.stderr = StringIO()

    try:
        # 创建XGBoost模型（通常会产生警告）
        trainer = ModelTrainer()
        trainer._create_model('xgb')

        # 简单训练
        X = np.random.randn(50, 5)
        y = np.array([0] * 30 + [1] * 20)
        trainer.model.fit(X, y)

        # 获取警告输出
        stderr_output = sys.stderr.getvalue()

        if 'WARNING' in stderr_output or 'UserWarning' in stderr_output:
            print("  ❌ 警告未完全抑制")
            print(f"  输出: {stderr_output[:200]}...")
        else:
            print("  ✅ 警告已成功抑制")

    finally:
        sys.stderr = old_stderr


if __name__ == "__main__":
    try:
        # 测试类权重优化
        test_class_weight_optimization()

        # 测试警告抑制
        test_warning_suppression()

        print("\n" + "=" * 60)
        print("✅ 所有优化验证完成！")
        print("=" * 60)
        print("\n建议:")
        print("1. 使用随机森林(RF)模型进行训练")
        print("2. 确保启用SMOTE")
        print("3. 查看ROC-AUC而不是准确率")
        print("4. 收集更多疾病样本以进一步改善")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
