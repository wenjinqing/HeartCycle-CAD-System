"""
基础使用示例
演示如何使用核心功能模块
"""
import sys
import os
import numpy as np
import pandas as pd

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


def example_data_processing():
    """示例1: 数据预处理"""
    print("=" * 60)
    print("示例1: 数据预处理")
    print("=" * 60)
    
    from algorithms.data_processing import ECGProcessor
    
    # 创建处理器
    processor = ECGProcessor(sampling_rate=200)
    
    # 处理文件（需要实际的HDF5文件路径）
    # file_path = "path/to/your/file.h5"
    # result = processor.process_file(file_path)
    
    # print(f"检测到 {len(result['rpeaks'])} 个R波")
    # print(f"RR间期数量: {len(result['rr_intervals'])}")
    # print(f"平均RR间期: {np.mean(result['rr_intervals']):.2f} ms")
    
    print("注意: 需要实际的HDF5文件才能运行")


def example_feature_extraction():
    """示例2: 特征提取"""
    print("\n" + "=" * 60)
    print("示例2: 特征提取")
    print("=" * 60)
    
    from algorithms.feature_extraction import HRVFeatureExtractor
    
    # 创建特征提取器
    extractor = HRVFeatureExtractor()
    
    # 提取特征（需要实际的HDF5文件路径）
    # file_path = "path/to/your/file.h5"
    # features = extractor.extract_all(
    #     file_path=file_path,
    #     extract_hrv=True,
    #     extract_clinical=True
    # )
    
    # print(f"提取了 {len(features)} 个特征")
    # print("\n前10个特征:")
    # for i, (key, value) in enumerate(list(features.items())[:10]):
    #     print(f"  {key}: {value}")
    
    print("注意: 需要实际的HDF5文件才能运行")


def example_model_training():
    """示例3: 模型训练"""
    print("\n" + "=" * 60)
    print("示例3: 模型训练")
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
    print(f"  CV Precision: {result['metrics']['precision']['mean']:.4f} ± {result['metrics']['precision']['std']:.4f}")
    print(f"  CV Recall: {result['metrics']['recall']['mean']:.4f} ± {result['metrics']['recall']['std']:.4f}")
    print(f"  CV F1: {result['metrics']['f1']['mean']:.4f} ± {result['metrics']['f1']['std']:.4f}")
    
    # 保存模型
    model_id = "example_model"
    model_path = trainer.save(model_id, metadata={"description": "示例模型"})
    print(f"\n模型已保存: {model_path}")
    
    # 加载模型
    model_data = ModelTrainer.load(model_id)
    print(f"模型类型: {model_data['model_type']}")
    
    # 预测
    X_test = np.random.rand(5, n_features)
    predictions, probabilities = trainer.predict(X_test)
    print(f"\n预测结果:")
    print(f"  预测类别: {predictions}")
    if probabilities is not None:
        print(f"  预测概率: {probabilities}")


def example_complete_pipeline():
    """示例4: 完整流程"""
    print("\n" + "=" * 60)
    print("示例4: 完整流程（模拟数据）")
    print("=" * 60)
    
    from algorithms.model_training import ModelTrainer
    
    # 步骤1: 生成模拟特征数据
    print("步骤1: 生成模拟特征数据...")
    np.random.seed(42)
    n_samples = 200
    n_features = 30
    
    # 模拟HRV特征
    feature_names = [
        'mean_rr', 'sdnn', 'rmssd', 'pnn50',
        'lf_power', 'hf_power', 'lf_hf_ratio',
        'sd1', 'sd2', 'sample_entropy',
        # ... 更多特征
    ]
    
    # 生成特征数据（实际应该从HDF5文件提取）
    X = np.random.rand(n_samples, n_features)
    
    # 生成标签（实际应该有真实标签）
    y = np.random.randint(0, 2, n_samples)
    
    print(f"  生成了 {n_samples} 个样本，{n_features} 个特征")
    
    # 步骤2: 保存特征和标签
    print("\n步骤2: 保存特征和标签...")
    df_features = pd.DataFrame(X, columns=[f'feature_{i}' for i in range(n_features)])
    df_labels = pd.DataFrame(y, columns=['label'])
    
    df_features.to_csv("example_features.csv", index=False)
    df_labels.to_csv("example_labels.csv", index=False)
    print("  已保存到 example_features.csv 和 example_labels.csv")
    
    # 步骤3: 训练模型
    print("\n步骤3: 训练模型...")
    trainer = ModelTrainer(random_state=42)
    
    result = trainer.train(
        X=X,
        y=y,
        model_type="rf",
        cv_folds=5,
        feature_names=df_features.columns.tolist()
    )
    
    print(f"  训练完成")
    print(f"  CV AUC: {result['metrics']['roc_auc']['mean']:.4f}")
    
    # 步骤4: 保存模型
    print("\n步骤4: 保存模型...")
    model_id = "complete_pipeline_model"
    trainer.save(model_id)
    print(f"  模型已保存: {model_id}")
    
    # 步骤5: 使用模型预测
    print("\n步骤5: 预测新样本...")
    X_new = np.random.rand(3, n_features)
    predictions, probabilities = trainer.predict(X_new)
    
    print(f"  新样本预测:")
    for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
        print(f"    样本{i+1}: 类别={pred}, 概率={prob}")
    
    print("\n完整流程完成！")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("HeartCycle CAD System - 使用示例")
    print("=" * 60)
    
    # 运行示例
    example_data_processing()
    example_feature_extraction()
    example_model_training()
    example_complete_pipeline()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)
    print("\n更多信息请查看 USAGE.md")


if __name__ == "__main__":
    main()


