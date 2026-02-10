"""
模型使用示例
演示如何训练、保存、加载和使用模型
"""
import sys
import os
import numpy as np
import pandas as pd

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


def example_basic_training(algorithms=None):
    """示例1: 基本模型训练"""
    print("=" * 60)
    print("示例1: 基本模型训练")
    print("=" * 60)
    
    from algorithms.model_training import ModelTrainer
    
    # 生成示例数据
    np.random.seed(42)
    n_samples = 100
    n_features = 20
    X = np.random.rand(n_samples, n_features)
    y = np.random.randint(0, 2, n_samples)
    
    print(f"数据: {n_samples}个样本, {n_features}个特征")
    
    # 创建训练器
    trainer = ModelTrainer(random_state=42)
    
    # 训练随机森林模型
    print("\n训练随机森林模型...")
    result = trainer.train(
        X=X,
        y=y,
        model_type="rf",
        cv_folds=5
    )
    
    print(f"\n训练结果:")
    print(f"  CV AUC: {result['metrics']['roc_auc']['mean']:.4f} ± {result['metrics']['roc_auc']['std']:.4f}")
    print(f"  CV Accuracy: {result['metrics']['accuracy']['mean']:.4f} ± {result['metrics']['accuracy']['std']:.4f}")
    
    # 保存模型
    model_id = "example_model_1"
    model_path = trainer.save(model_id, metadata={
        "description": "基本训练示例",
        "n_samples": n_samples,
        "n_features": n_features
    })
    print(f"\n模型已保存: {model_path}")
    
    return trainer, model_id


def example_model_prediction(trainer, model_id):
    """示例2: 使用模型预测"""
    print("\n" + "=" * 60)
    print("示例2: 模型预测")
    print("=" * 60)
    
    # 生成测试数据
    np.random.seed(123)
    X_test = np.random.rand(5, 20)
    
    print(f"预测 {len(X_test)} 个新样本...")
    
    # 使用训练器预测
    predictions, probabilities = trainer.predict(X_test)
    
    print(f"\n预测结果:")
    for i, (pred, prob) in enumerate(zip(predictions, probabilities if probabilities is not None else [])):
        print(f"  样本{i+1}: 类别={pred}, 概率={prob}")
    
    return X_test, predictions


def example_load_model(model_id):
    """示例3: 加载已保存的模型"""
    print("\n" + "=" * 60)
    print("示例3: 加载已保存的模型")
    print("=" * 60)
    
    from algorithms.model_training import ModelTrainer
    
    # 加载模型
    model_data = ModelTrainer.load(model_id)
    
    print(f"模型信息:")
    print(f"  模型类型: {model_data['model_type']}")
    print(f"  特征数量: {len(model_data.get('feature_names', []))}")
    print(f"  创建时间: {model_data.get('metadata', {}).get('created_at', 'N/A')}")
    
    # 使用加载的模型
    model = model_data['model']
    print(f"\n模型对象: {type(model).__name__}")
    
    return model_data


def example_compare_models():
    """示例4: 比较不同模型"""
    print("\n" + "=" * 60)
    print("示例4: 比较不同模型")
    print("=" * 60)
    
    from algorithms.model_training import ModelTrainer
    
    # 准备数据
    np.random.seed(42)
    X = np.random.rand(100, 20)
    y = np.random.randint(0, 2, 100)
    
    # 比较三种模型
    models = ["lr", "svm", "rf"]
    results = {}
    
    for model_type in models:
        print(f"\n训练 {model_type} 模型...")
        trainer = ModelTrainer(random_state=42)
        result = trainer.train(X, y, model_type=model_type, cv_folds=5)
        
        results[model_type] = {
            'auc': result['metrics']['roc_auc']['mean'],
            'accuracy': result['metrics']['accuracy']['mean'],
            'f1': result['metrics']['f1']['mean']
        }
        
        print(f"  AUC: {results[model_type]['auc']:.4f}")
        print(f"  Accuracy: {results[model_type]['accuracy']:.4f}")
    
    # 找出最佳模型
    best_model = max(results.items(), key=lambda x: x[1]['auc'])
    print(f"\n最佳模型: {best_model[0]}")
    print(f"  AUC: {best_model[1]['auc']:.4f}")
    print(f"  Accuracy: {best_model[1]['accuracy']:.4f}")
    
    return best_model[0]


def example_save_and_load_features():
    """示例5: 保存和加载特征数据"""
    print("\n" + "=" * 60)
    print("示例5: 保存和加载特征数据")
    print("=" * 60)
    
    from algorithms.model_training import ModelTrainer
    
    # 生成数据
    np.random.seed(42)
    X = np.random.rand(100, 20)
    y = np.random.randint(0, 2, 100)
    
    # 保存为CSV
    feature_names = [f'feature_{i}' for i in range(20)]
    df_features = pd.DataFrame(X, columns=feature_names)
    df_labels = pd.DataFrame(y, columns=['label'])
    
    df_features.to_csv("example_features.csv", index=False)
    df_labels.to_csv("example_labels.csv", index=False)
    
    print("数据已保存:")
    print(f"  特征文件: example_features.csv ({len(df_features)} 样本, {len(feature_names)} 特征)")
    print(f"  标签文件: example_labels.csv ({len(df_labels)} 样本)")
    
    # 从CSV加载并训练
    print("\n从CSV加载数据并训练模型...")
    X_loaded = df_features.values
    y_loaded = df_labels.values.ravel()
    
    trainer = ModelTrainer(random_state=42)
    result = trainer.train(
        X=X_loaded,
        y=y_loaded,
        model_type="rf",
        cv_folds=5,
        feature_names=feature_names
    )
    
    print(f"训练完成，AUC: {result['metrics']['roc_auc']['mean']:.4f}")
    
    # 保存模型（包含特征名称）
    model_id = "example_model_with_features"
    trainer.save(model_id, metadata={
        "feature_names": feature_names,
        "feature_file": "example_features.csv",
        "label_file": "example_labels.csv"
    })
    print(f"模型已保存: {model_id}")


def example_api_usage():
    """示例6: 使用API接口（需要后端服务运行）"""
    print("\n" + "=" * 60)
    print("示例6: 使用API接口")
    print("=" * 60)
    
    try:
        import requests
        
        BASE_URL = "http://localhost:8000/api/v1"
        
        # 检查服务是否运行
        try:
            response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health", timeout=2)
            if response.status_code != 200:
                print("[提示] 后端服务未运行，跳过API示例")
                print("      请先启动后端: python scripts/start_backend.py")
                return
        except:
            print("[提示] 后端服务未运行，跳过API示例")
            print("      请先启动后端: python scripts/start_backend.py")
            return
        
        # 获取模型列表
        print("\n获取模型列表...")
        response = requests.get(f"{BASE_URL}/models")
        if response.status_code == 200:
            models = response.json()
            model_list = models.get('data', {}).get('models', models.get('models', []))
            print(f"  共有 {len(model_list)} 个模型")
            if model_list:
                model_id = model_list[0]['model_id']
                print(f"  使用模型: {model_id}")
                
                # 进行预测
                print("\n使用API进行预测...")
                test_features = np.random.rand(20).tolist()
                response = requests.post(
                    f"{BASE_URL}/predict",
                    json={
                        "model_id": model_id,
                        "features": test_features
                    }
                )
                if response.status_code == 200:
                    result = response.json()
                    print(f"  预测类别: {result['prediction']}")
                    print(f"  预测概率: {result['probability']}")
                else:
                    print(f"  预测失败: {response.text}")
        else:
            print(f"  获取模型列表失败: {response.status_code}")
            
    except ImportError:
        print("[提示] requests库未安装，跳过API示例")
        print("      安装: pip install requests")
    except Exception as e:
        print(f"[错误] API调用失败: {e}")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("模型使用示例")
    print("=" * 60)
    
    # 示例1: 基本训练
    trainer, model_id = example_basic_training()
    
    # 示例2: 预测
    X_test, predictions = example_model_prediction(trainer, model_id)
    
    # 示例3: 加载模型
    model_data = example_load_model(model_id)
    
    # 示例4: 比较模型
    best_model = example_compare_models()
    
    # 示例5: 保存和加载特征
    example_save_and_load_features()
    
    # 示例6: API使用
    example_api_usage()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)
    print("\n更多信息请查看 模型使用指南.md")


if __name__ == "__main__":
    main()


