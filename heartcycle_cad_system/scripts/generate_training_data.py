"""
生成用于训练的测试CSV文件
生成特征文件和标签文件
"""
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def generate_training_data(n_samples=200, output_dir=None):
    """
    生成训练数据
    
    Parameters:
    -----------
    n_samples : int
        样本数量
    output_dir : str, optional
        输出目录，如果为None则使用默认目录
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'features')
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 设置随机种子以确保可重复性
    np.random.seed(42)
    
    print("=" * 60)
    print("生成训练数据")
    print("=" * 60)
    print(f"样本数量: {n_samples}")
    print(f"输出目录: {output_dir}")
    
    # 1. 生成临床特征（5个）
    print("\n生成临床特征...")
    
    # 年龄：20-80岁，正态分布
    age = np.random.normal(50, 15, n_samples)
    age = np.clip(age, 20, 80).astype(int)
    
    # 性别：0或1（0=女，1=男）
    gender = np.random.randint(0, 2, n_samples)
    
    # 身高：150-190cm，正态分布
    height = np.random.normal(170, 10, n_samples)
    height = np.clip(height, 150, 190).astype(int)
    
    # 体重：45-100kg，正态分布
    weight = np.random.normal(70, 15, n_samples)
    weight = np.clip(weight, 45, 100).astype(int)
    
    # BMI：根据身高和体重计算
    height_m = height / 100.0
    bmi = weight / (height_m ** 2)
    bmi = np.round(bmi, 2)
    
    # 2. 生成HRV特征（5个）
    print("生成HRV特征...")
    
    # mean_rr: 平均RR间期，通常600-1200ms
    mean_rr = np.random.normal(900, 150, n_samples)
    mean_rr = np.clip(mean_rr, 600, 1200).astype(int)
    
    # sdnn: SDNN，通常20-100ms
    sdnn = np.random.normal(50, 20, n_samples)
    sdnn = np.clip(sdnn, 20, 100).astype(int)
    
    # rmssd: RMSSD，通常15-60ms
    rmssd = np.random.normal(35, 15, n_samples)
    rmssd = np.clip(rmssd, 15, 60).astype(int)
    
    # pnn50: pNN50，通常0-20%
    pnn50 = np.random.normal(8, 5, n_samples)
    pnn50 = np.clip(pnn50, 0, 20).round(2)
    
    # lf_hf_ratio: LF/HF比值，通常0.5-3.0
    lf_hf_ratio = np.random.normal(1.5, 0.8, n_samples)
    lf_hf_ratio = np.clip(lf_hf_ratio, 0.5, 3.0).round(3)
    
    # 3. 组合特征
    feature_names = [
        'age', 'gender', 'height', 'weight', 'bmi',
        'mean_rr', 'sdnn', 'rmssd', 'pnn50', 'lf_hf_ratio'
    ]
    
    features_data = {
        'age': age,
        'gender': gender,
        'height': height,
        'weight': weight,
        'bmi': bmi,
        'mean_rr': mean_rr,
        'sdnn': sdnn,
        'rmssd': rmssd,
        'pnn50': pnn50,
        'lf_hf_ratio': lf_hf_ratio
    }
    
    df_features = pd.DataFrame(features_data)
    
    # 4. 生成标签（基于特征的组合，模拟真实情况）
    print("生成标签...")
    
    # 基于特征的逻辑组合生成标签（模拟CAD风险）
    # 风险因素：年龄>60, BMI>25, sdnn<40, lf_hf_ratio>2.0
    risk_score = (
        (age > 60).astype(float) * 0.3 +
        (bmi > 25).astype(float) * 0.2 +
        (sdnn < 40).astype(float) * 0.25 +
        (lf_hf_ratio > 2.0).astype(float) * 0.25
    )
    
    # 添加一些随机性
    noise = np.random.rand(n_samples) * 0.2
    risk_score = risk_score + noise
    
    # 转换为二分类标签（0=低风险，1=高风险）
    labels = (risk_score > 0.5).astype(int)
    
    # 确保有正负样本
    positive_ratio = labels.sum() / n_samples
    if positive_ratio < 0.2:
        # 如果正样本太少，增加一些
        high_risk_indices = np.argsort(risk_score)[-int(n_samples * 0.3):]
        labels[high_risk_indices] = 1
    elif positive_ratio > 0.8:
        # 如果正样本太多，减少一些
        low_risk_indices = np.argsort(risk_score)[:int(n_samples * 0.3)]
        labels[low_risk_indices] = 0
    
    df_labels = pd.DataFrame({'label': labels})
    
    # 5. 保存文件
    features_file = os.path.join(output_dir, 'train_features.csv')
    labels_file = os.path.join(output_dir, 'train_labels.csv')
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存文件
    df_features.to_csv(features_file, index=False, encoding='utf-8')
    df_labels.to_csv(labels_file, index=False, encoding='utf-8')
    
    # 验证文件是否成功保存
    if not os.path.exists(features_file):
        raise FileNotFoundError(f"特征文件保存失败: {features_file}")
    if not os.path.exists(labels_file):
        raise FileNotFoundError(f"标签文件保存失败: {labels_file}")
    
    # 验证文件大小
    if os.path.getsize(features_file) == 0:
        raise ValueError(f"特征文件为空: {features_file}")
    if os.path.getsize(labels_file) == 0:
        raise ValueError(f"标签文件为空: {labels_file}")
    
    print("\n" + "=" * 60)
    print("数据生成完成！")
    print("=" * 60)
    print(f"\n特征文件: {features_file}")
    print(f"标签文件: {labels_file}")
    print(f"\n特征统计:")
    print(f"  特征数量: {len(feature_names)}")
    print(f"  样本数量: {n_samples}")
    print(f"  正样本 (label=1): {labels.sum()} ({labels.sum()/n_samples*100:.1f}%)")
    print(f"  负样本 (label=0): {(labels==0).sum()} ({(labels==0).sum()/n_samples*100:.1f}%)")
    print(f"\n特征列:")
    for i, name in enumerate(feature_names, 1):
        print(f"  {i}. {name}")
    
    print(f"\n前5行特征数据预览:")
    print(df_features.head())
    
    print(f"\n前5行标签数据预览:")
    print(df_labels.head())
    
    return features_file, labels_file


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='生成训练数据CSV文件')
    parser.add_argument('--samples', type=int, default=200, help='样本数量 (默认: 200)')
    parser.add_argument('--output', type=str, default=None, help='输出目录 (默认: data/features)')
    
    args = parser.parse_args()
    
    generate_training_data(n_samples=args.samples, output_dir=args.output)

