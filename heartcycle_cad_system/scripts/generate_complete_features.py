"""
生成包含完整45+特征的高质量模拟数据集
用于展示模型优化效果
"""
import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)

def generate_realistic_features(n_samples=200, disease_ratio=0.5):
    """
    生成真实的HRV特征数据

    Parameters:
    -----------
    n_samples : int
        样本数量
    disease_ratio : float
        患病样本比例
    """

    n_disease = int(n_samples * disease_ratio)
    n_healthy = n_samples - n_disease

    features_list = []
    labels_list = []

    # 生成健康样本
    for i in range(n_healthy):
        features = generate_healthy_sample()
        features_list.append(features)
        labels_list.append(0)

    # 生成患病样本
    for i in range(n_disease):
        features = generate_disease_sample()
        features_list.append(features)
        labels_list.append(1)

    # 转换为DataFrame
    df_features = pd.DataFrame(features_list)
    df_labels = pd.DataFrame({'label': labels_list})

    # 打乱顺序
    indices = np.random.permutation(n_samples)
    df_features = df_features.iloc[indices].reset_index(drop=True)
    df_labels = df_labels.iloc[indices].reset_index(drop=True)

    return df_features, df_labels


def generate_healthy_sample():
    """生成健康样本的特征"""

    # 临床特征（健康范围）
    age = np.random.randint(20, 60)
    gender = np.random.choice([0, 1])
    height = np.random.normal(170, 10)
    weight = np.random.normal(70, 15)
    bmi = weight / ((height/100) ** 2)

    # 时域特征（健康范围）
    mean_rr = np.random.normal(850, 50)  # 健康心率
    sdnn = np.random.normal(50, 10)  # 高HRV
    rmssd = np.random.normal(40, 10)
    pnn50 = np.random.normal(20, 5)
    pnn20 = np.random.normal(40, 10)

    std_rr = sdnn
    min_rr = mean_rr - np.random.uniform(100, 150)
    max_rr = mean_rr + np.random.uniform(100, 150)
    median_rr = mean_rr + np.random.normal(0, 10)

    cv = (std_rr / mean_rr) * 100
    cvsd = np.random.normal(5, 1)
    sdann = np.random.normal(45, 8)
    range_rr = max_rr - min_rr
    q1_rr = mean_rr - np.random.uniform(30, 50)
    q3_rr = mean_rr + np.random.uniform(30, 50)
    iqr_rr = q3_rr - q1_rr

    sdsd = rmssd
    hrv_triangular_index = np.random.normal(15, 3)
    tinn = np.random.normal(300, 50)
    mean_hr = 60000 / mean_rr

    # 频域特征（健康范围）
    total_power = np.random.normal(3000, 500)
    vlf_power = total_power * np.random.uniform(0.2, 0.3)
    lf_power = total_power * np.random.uniform(0.3, 0.4)
    hf_power = total_power * np.random.uniform(0.25, 0.35)

    lf_hf_ratio = lf_power / hf_power
    lf_norm = lf_power / (lf_power + hf_power) * 100
    hf_norm = hf_power / (lf_power + hf_power) * 100

    vlf_percent = vlf_power / total_power * 100
    lf_percent = lf_power / total_power * 100
    hf_percent = hf_power / total_power * 100

    lf_peak = np.random.uniform(0.08, 0.12)
    hf_peak = np.random.uniform(0.20, 0.30)
    log_total_power = np.log(total_power + 1)
    log_lf_power = np.log(lf_power + 1)
    log_hf_power = np.log(hf_power + 1)
    spectral_entropy = np.random.uniform(0.6, 0.8)

    # 非线性特征（健康范围）
    sd1 = rmssd / np.sqrt(2)
    sd2 = np.sqrt(2 * sdnn**2 - sd1**2)
    sd1_sd2_ratio = sd1 / sd2

    sample_entropy = np.random.uniform(1.5, 2.0)
    approximate_entropy = np.random.uniform(1.0, 1.5)

    dfa_alpha1 = np.random.uniform(0.9, 1.2)
    dfa_alpha2 = np.random.uniform(0.9, 1.2)
    ac = np.random.uniform(-0.5, 0.5)
    dc = np.random.uniform(-0.5, 0.5)
    complexity_index = np.random.uniform(1.5, 2.5)

    return {
        # 临床特征
        'age': age,
        'gender': gender,
        'height': height,
        'weight': weight,
        'bmi': bmi,

        # 时域特征
        'mean_rr': mean_rr,
        'std_rr': std_rr,
        'min_rr': min_rr,
        'max_rr': max_rr,
        'median_rr': median_rr,
        'sdnn': sdnn,
        'rmssd': rmssd,
        'pnn50': pnn50,
        'pnn20': pnn20,
        'cv': cv,
        'cvsd': cvsd,
        'sdann': sdann,
        'range_rr': range_rr,
        'q1_rr': q1_rr,
        'q3_rr': q3_rr,
        'iqr_rr': iqr_rr,
        'sdsd': sdsd,
        'hrv_triangular_index': hrv_triangular_index,
        'tinn': tinn,
        'mean_hr': mean_hr,

        # 频域特征
        'total_power': total_power,
        'vlf_power': vlf_power,
        'lf_power': lf_power,
        'hf_power': hf_power,
        'lf_hf_ratio': lf_hf_ratio,
        'lf_norm': lf_norm,
        'hf_norm': hf_norm,
        'vlf_percent': vlf_percent,
        'lf_percent': lf_percent,
        'hf_percent': hf_percent,
        'lf_peak': lf_peak,
        'hf_peak': hf_peak,
        'log_total_power': log_total_power,
        'log_lf_power': log_lf_power,
        'log_hf_power': log_hf_power,
        'spectral_entropy': spectral_entropy,

        # 非线性特征
        'sd1': sd1,
        'sd2': sd2,
        'sd1_sd2_ratio': sd1_sd2_ratio,
        'sample_entropy': sample_entropy,
        'approximate_entropy': approximate_entropy,
        'dfa_alpha1': dfa_alpha1,
        'dfa_alpha2': dfa_alpha2,
        'ac': ac,
        'dc': dc,
        'complexity_index': complexity_index
    }


def generate_disease_sample():
    """生成患病样本的特征（心血管疾病特征）"""

    # 临床特征（高风险）
    age = np.random.randint(45, 80)  # 年龄偏大
    gender = np.random.choice([0, 1])
    height = np.random.normal(170, 10)
    weight = np.random.normal(80, 15)  # 体重偏高
    bmi = weight / ((height/100) ** 2)

    # 时域特征（低HRV，心血管疾病特征）
    mean_rr = np.random.normal(750, 50)  # 心率偏快
    sdnn = np.random.normal(30, 8)  # 低HRV
    rmssd = np.random.normal(20, 8)
    pnn50 = np.random.normal(5, 3)
    pnn20 = np.random.normal(15, 5)

    std_rr = sdnn
    min_rr = mean_rr - np.random.uniform(50, 100)
    max_rr = mean_rr + np.random.uniform(50, 100)
    median_rr = mean_rr + np.random.normal(0, 10)

    cv = (std_rr / mean_rr) * 100
    cvsd = np.random.normal(3, 0.5)
    sdann = np.random.normal(25, 5)
    range_rr = max_rr - min_rr
    q1_rr = mean_rr - np.random.uniform(20, 40)
    q3_rr = mean_rr + np.random.uniform(20, 40)
    iqr_rr = q3_rr - q1_rr

    sdsd = rmssd
    hrv_triangular_index = np.random.normal(8, 2)
    tinn = np.random.normal(150, 30)
    mean_hr = 60000 / mean_rr

    # 频域特征（交感神经过度激活）
    total_power = np.random.normal(1500, 300)  # 总功率降低
    vlf_power = total_power * np.random.uniform(0.3, 0.4)
    lf_power = total_power * np.random.uniform(0.4, 0.5)  # LF升高
    hf_power = total_power * np.random.uniform(0.1, 0.2)  # HF降低

    lf_hf_ratio = lf_power / hf_power  # 比值升高
    lf_norm = lf_power / (lf_power + hf_power) * 100
    hf_norm = hf_power / (lf_power + hf_power) * 100

    vlf_percent = vlf_power / total_power * 100
    lf_percent = lf_power / total_power * 100
    hf_percent = hf_power / total_power * 100

    lf_peak = np.random.uniform(0.08, 0.12)
    hf_peak = np.random.uniform(0.20, 0.30)
    log_total_power = np.log(total_power + 1)
    log_lf_power = np.log(lf_power + 1)
    log_hf_power = np.log(hf_power + 1)
    spectral_entropy = np.random.uniform(0.3, 0.5)  # 熵降低

    # 非线性特征（复杂度降低）
    sd1 = rmssd / np.sqrt(2)
    sd2 = np.sqrt(2 * sdnn**2 - sd1**2)
    sd1_sd2_ratio = sd1 / sd2

    sample_entropy = np.random.uniform(0.8, 1.2)  # 熵降低
    approximate_entropy = np.random.uniform(0.5, 0.9)

    dfa_alpha1 = np.random.uniform(1.2, 1.5)  # 异常升高
    dfa_alpha2 = np.random.uniform(1.2, 1.5)
    ac = np.random.uniform(-1.0, -0.3)  # 加速能力下降
    dc = np.random.uniform(-1.0, -0.3)  # 减速能力下降
    complexity_index = np.random.uniform(0.8, 1.5)  # 复杂度降低

    return {
        # 临床特征
        'age': age,
        'gender': gender,
        'height': height,
        'weight': weight,
        'bmi': bmi,

        # 时域特征
        'mean_rr': mean_rr,
        'std_rr': std_rr,
        'min_rr': min_rr,
        'max_rr': max_rr,
        'median_rr': median_rr,
        'sdnn': sdnn,
        'rmssd': rmssd,
        'pnn50': pnn50,
        'pnn20': pnn20,
        'cv': cv,
        'cvsd': cvsd,
        'sdann': sdann,
        'range_rr': range_rr,
        'q1_rr': q1_rr,
        'q3_rr': q3_rr,
        'iqr_rr': iqr_rr,
        'sdsd': sdsd,
        'hrv_triangular_index': hrv_triangular_index,
        'tinn': tinn,
        'mean_hr': mean_hr,

        # 频域特征
        'total_power': total_power,
        'vlf_power': vlf_power,
        'lf_power': lf_power,
        'hf_power': hf_power,
        'lf_hf_ratio': lf_hf_ratio,
        'lf_norm': lf_norm,
        'hf_norm': hf_norm,
        'vlf_percent': vlf_percent,
        'lf_percent': lf_percent,
        'hf_percent': hf_percent,
        'lf_peak': lf_peak,
        'hf_peak': hf_peak,
        'log_total_power': log_total_power,
        'log_lf_power': log_lf_power,
        'log_hf_power': log_hf_power,
        'spectral_entropy': spectral_entropy,

        # 非线性特征
        'sd1': sd1,
        'sd2': sd2,
        'sd1_sd2_ratio': sd1_sd2_ratio,
        'sample_entropy': sample_entropy,
        'approximate_entropy': approximate_entropy,
        'dfa_alpha1': dfa_alpha1,
        'dfa_alpha2': dfa_alpha2,
        'ac': ac,
        'dc': dc,
        'complexity_index': complexity_index
    }


if __name__ == '__main__':
    print("="*80)
    print("生成完整特征数据集")
    print("="*80)

    # 生成数据
    print("\n生成200个样本（100健康 + 100患病）...")
    df_features, df_labels = generate_realistic_features(n_samples=200, disease_ratio=0.5)

    print(f"\n特征数量: {len(df_features.columns)}")
    print(f"样本数量: {len(df_features)}")
    print(f"标签分布: {df_labels['label'].value_counts().to_dict()}")

    # 保存
    output_dir = Path(r"D:\Graduate Work\heartcycle_cad_system\data\features")
    output_dir.mkdir(parents=True, exist_ok=True)

    feature_file = output_dir / 'complete_features.csv'
    label_file = output_dir / 'complete_labels.csv'

    df_features.to_csv(feature_file, index=False)
    df_labels.to_csv(label_file, index=False)

    print(f"\n[OK] 特征已保存: {feature_file}")
    print(f"[OK] 标签已保存: {label_file}")

    # 显示特征列表
    print(f"\n特征列表 ({len(df_features.columns)}个):")
    for i, col in enumerate(df_features.columns, 1):
        print(f"   {i:2d}. {col}")

    print("\n[SUCCESS] 数据生成完成！")
