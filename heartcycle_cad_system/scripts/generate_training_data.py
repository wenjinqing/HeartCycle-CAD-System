"""
生成用于训练的测试CSV文件
生成特征文件和标签文件
"""
import os
import sys
from pathlib import Path
from typing import Tuple, Optional, Dict, List

import pandas as pd
import numpy as np

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# 特征参数常量
class FeatureParams:
    """特征生成参数常量"""
    # 年龄范围
    AGE_MEAN = 50
    AGE_STD = 15
    AGE_MIN = 20
    AGE_MAX = 80
    
    # 身高范围 (cm)
    HEIGHT_MEAN = 170
    HEIGHT_STD = 10
    HEIGHT_MIN = 150
    HEIGHT_MAX = 190
    
    # 体重范围 (kg)
    WEIGHT_MEAN = 70
    WEIGHT_STD = 15
    WEIGHT_MIN = 45
    WEIGHT_MAX = 100
    
    # HRV特征范围
    MEAN_RR_MEAN = 900  # ms
    MEAN_RR_STD = 150
    MEAN_RR_MIN = 600
    MEAN_RR_MAX = 1200
    
    SDNN_MEAN = 50  # ms
    SDNN_STD = 20
    SDNN_MIN = 20
    SDNN_MAX = 100
    
    RMSSD_MEAN = 35  # ms
    RMSSD_STD = 15
    RMSSD_MIN = 15
    RMSSD_MAX = 60
    
    PNN50_MEAN = 8  # %
    PNN50_STD = 5
    PNN50_MIN = 0
    PNN50_MAX = 20
    
    LF_HF_RATIO_MEAN = 1.5
    LF_HF_RATIO_STD = 0.8
    LF_HF_RATIO_MIN = 0.5
    LF_HF_RATIO_MAX = 3.0
    
    # 标签生成参数
    RISK_AGE_THRESHOLD = 60
    RISK_BMI_THRESHOLD = 25
    RISK_SDNN_THRESHOLD = 40
    RISK_LF_HF_THRESHOLD = 2.0
    RISK_AGE_WEIGHT = 0.3
    RISK_BMI_WEIGHT = 0.2
    RISK_SDNN_WEIGHT = 0.25
    RISK_LF_HF_WEIGHT = 0.25
    RISK_NOISE_SCALE = 0.2
    RISK_THRESHOLD = 0.5
    MIN_POSITIVE_RATIO = 0.2
    MAX_POSITIVE_RATIO = 0.8
    BALANCE_RATIO = 0.3

# 特征名称
FEATURE_NAMES: List[str] = [
    'age', 'gender', 'height', 'weight', 'bmi',
    'mean_rr', 'sdnn', 'rmssd', 'pnn50', 'lf_hf_ratio'
]

def generate_training_data(n_samples: int = 200, output_dir: Optional[str] = None) -> Tuple[str, str]:
    """
    生成训练数据
    
    Parameters:
    -----------
    n_samples : int
        样本数量
    output_dir : str, optional
        输出目录，如果为None则使用默认目录
        
    Returns:
    --------
    Tuple[str, str]
        特征文件路径和标签文件路径
    """
    # 确定输出目录
    if output_dir is None:
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent / 'data' / 'features'
    else:
        output_dir = Path(output_dir)
    
    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 设置随机种子以确保可重复性
    np.random.seed(42)
    
    print("=" * 60)
    print("生成训练数据")
    print("=" * 60)
    print(f"样本数量: {n_samples}")
    print(f"输出目录: {output_dir}")
    
    # 1. 生成临床特征（5个）
    print("\n生成临床特征...")
    clinical_features = _generate_clinical_features(n_samples)
    
    # 2. 生成HRV特征（5个）
    print("生成HRV特征...")
    hrv_features = _generate_hrv_features(n_samples)
    
    # 3. 组合特征
    features_data = {**clinical_features, **hrv_features}
    df_features = pd.DataFrame(features_data)
    
    # 4. 生成标签（基于特征的组合，模拟真实情况）
    print("生成标签...")
    labels = _generate_labels(
        age=clinical_features['age'],
        bmi=clinical_features['bmi'],
        sdnn=hrv_features['sdnn'],
        lf_hf_ratio=hrv_features['lf_hf_ratio'],
        n_samples=n_samples
    )
    
    df_labels = pd.DataFrame({'label': labels})
    
    # 5. 保存文件
    features_file = output_dir / 'train_features.csv'
    labels_file = output_dir / 'train_labels.csv'
    
    # 保存文件
    df_features.to_csv(features_file, index=False, encoding='utf-8')
    df_labels.to_csv(labels_file, index=False, encoding='utf-8')
    
    # 验证文件是否成功保存
    if not features_file.exists():
        raise FileNotFoundError(f"特征文件保存失败: {features_file}")
    if not labels_file.exists():
        raise FileNotFoundError(f"标签文件保存失败: {labels_file}")
    
    # 验证文件大小
    if features_file.stat().st_size == 0:
        raise ValueError(f"特征文件为空: {features_file}")
    if labels_file.stat().st_size == 0:
        raise ValueError(f"标签文件为空: {labels_file}")
    
    # 输出统计信息
    _print_statistics(features_file, labels_file, df_features, df_labels, labels, n_samples)
    
    return str(features_file), str(labels_file)


def _generate_clinical_features(n_samples: int) -> Dict[str, np.ndarray]:
    """生成临床特征"""
    params = FeatureParams
    
    # 年龄：正态分布
    age = np.random.normal(params.AGE_MEAN, params.AGE_STD, n_samples)
    age = np.clip(age, params.AGE_MIN, params.AGE_MAX).astype(int)
    
    # 性别：0或1（0=女，1=男）
    gender = np.random.randint(0, 2, n_samples)
    
    # 身高：正态分布
    height = np.random.normal(params.HEIGHT_MEAN, params.HEIGHT_STD, n_samples)
    height = np.clip(height, params.HEIGHT_MIN, params.HEIGHT_MAX).astype(int)
    
    # 体重：正态分布
    weight = np.random.normal(params.WEIGHT_MEAN, params.WEIGHT_STD, n_samples)
    weight = np.clip(weight, params.WEIGHT_MIN, params.WEIGHT_MAX).astype(int)
    
    # BMI：根据身高和体重计算
    height_m = height / 100.0
    bmi = weight / (height_m ** 2)
    bmi = np.round(bmi, 2)
    
    return {
        'age': age,
        'gender': gender,
        'height': height,
        'weight': weight,
        'bmi': bmi
    }


def _generate_hrv_features(n_samples: int) -> Dict[str, np.ndarray]:
    """生成HRV特征"""
    params = FeatureParams
    
    # mean_rr: 平均RR间期
    mean_rr = np.random.normal(params.MEAN_RR_MEAN, params.MEAN_RR_STD, n_samples)
    mean_rr = np.clip(mean_rr, params.MEAN_RR_MIN, params.MEAN_RR_MAX).astype(int)
    
    # sdnn: SDNN
    sdnn = np.random.normal(params.SDNN_MEAN, params.SDNN_STD, n_samples)
    sdnn = np.clip(sdnn, params.SDNN_MIN, params.SDNN_MAX).astype(int)
    
    # rmssd: RMSSD
    rmssd = np.random.normal(params.RMSSD_MEAN, params.RMSSD_STD, n_samples)
    rmssd = np.clip(rmssd, params.RMSSD_MIN, params.RMSSD_MAX).astype(int)
    
    # pnn50: pNN50
    pnn50 = np.random.normal(params.PNN50_MEAN, params.PNN50_STD, n_samples)
    pnn50 = np.clip(pnn50, params.PNN50_MIN, params.PNN50_MAX).round(2)
    
    # lf_hf_ratio: LF/HF比值
    lf_hf_ratio = np.random.normal(params.LF_HF_RATIO_MEAN, params.LF_HF_RATIO_STD, n_samples)
    lf_hf_ratio = np.clip(lf_hf_ratio, params.LF_HF_RATIO_MIN, params.LF_HF_RATIO_MAX).round(3)
    
    return {
        'mean_rr': mean_rr,
        'sdnn': sdnn,
        'rmssd': rmssd,
        'pnn50': pnn50,
        'lf_hf_ratio': lf_hf_ratio
    }


def _generate_labels(
    age: np.ndarray,
    bmi: np.ndarray,
    sdnn: np.ndarray,
    lf_hf_ratio: np.ndarray,
    n_samples: int
) -> np.ndarray:
    """生成标签（基于特征的组合，模拟CAD风险）"""
    params = FeatureParams
    
    # 基于特征的逻辑组合生成标签（模拟CAD风险）
    risk_score = (
        (age > params.RISK_AGE_THRESHOLD).astype(float) * params.RISK_AGE_WEIGHT +
        (bmi > params.RISK_BMI_THRESHOLD).astype(float) * params.RISK_BMI_WEIGHT +
        (sdnn < params.RISK_SDNN_THRESHOLD).astype(float) * params.RISK_SDNN_WEIGHT +
        (lf_hf_ratio > params.RISK_LF_HF_THRESHOLD).astype(float) * params.RISK_LF_HF_WEIGHT
    )
    
    # 添加一些随机性
    noise = np.random.rand(n_samples) * params.RISK_NOISE_SCALE
    risk_score = risk_score + noise
    
    # 转换为二分类标签（0=低风险，1=高风险）
    labels = (risk_score > params.RISK_THRESHOLD).astype(int)
    
    # 确保有正负样本
    positive_ratio = labels.sum() / n_samples
    if positive_ratio < params.MIN_POSITIVE_RATIO:
        # 如果正样本太少，增加一些
        high_risk_indices = np.argsort(risk_score)[-int(n_samples * params.BALANCE_RATIO):]
        labels[high_risk_indices] = 1
    elif positive_ratio > params.MAX_POSITIVE_RATIO:
        # 如果正样本太多，减少一些
        low_risk_indices = np.argsort(risk_score)[:int(n_samples * params.BALANCE_RATIO)]
        labels[low_risk_indices] = 0
    
    return labels


def _print_statistics(
    features_file: Path,
    labels_file: Path,
    df_features: pd.DataFrame,
    df_labels: pd.DataFrame,
    labels: np.ndarray,
    n_samples: int
) -> None:
    """打印统计信息"""
    print("\n" + "=" * 60)
    print("数据生成完成！")
    print("=" * 60)
    print(f"\n特征文件: {features_file}")
    print(f"标签文件: {labels_file}")
    print(f"\n特征统计:")
    print(f"  特征数量: {len(FEATURE_NAMES)}")
    print(f"  样本数量: {n_samples}")
    print(f"  正样本 (label=1): {labels.sum()} ({labels.sum()/n_samples*100:.1f}%)")
    print(f"  负样本 (label=0): {(labels==0).sum()} ({(labels==0).sum()/n_samples*100:.1f}%)")
    print(f"\n特征列:")
    for i, name in enumerate(FEATURE_NAMES, 1):
        print(f"  {i}. {name}")
    
    print(f"\n前5行特征数据预览:")
    print(df_features.head())
    
    print(f"\n前5行标签数据预览:")
    print(df_labels.head())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='生成训练数据CSV文件')
    parser.add_argument('--samples', type=int, default=200, help='样本数量 (默认: 200)')
    parser.add_argument('--output', type=str, default=None, help='输出目录 (默认: data/features)')
    
    args = parser.parse_args()
    
    generate_training_data(n_samples=args.samples, output_dir=args.output)

