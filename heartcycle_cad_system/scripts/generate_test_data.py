#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成HeartCycle系统测试数据
包括：H5心电数据文件、元数据CSV、实验数据集
"""

import os
import sys
import h5py
import numpy as np
import pandas as pd
from pathlib import Path

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 设置随机种子以保证可复现
np.random.seed(42)

# 基础路径
BASE_DIR = Path(__file__).parent.parent
TEST_DATA_DIR = BASE_DIR / "测试数据"

def generate_ecg_signal(length=5000, has_disease=False, sampling_rate=500):
    """
    生成更真实的模拟心电信号
    包含P波、QRS波群、T波
    """
    ecg = np.zeros(length)
    t = np.arange(length) / sampling_rate

    # 心率：60-80 bpm (正常) 或 80-100 bpm (疾病)
    if has_disease:
        heart_rate = np.random.uniform(80, 100)
        qrs_amplitude = np.random.uniform(0.8, 1.0)  # 降低振幅
    else:
        heart_rate = np.random.uniform(60, 80)
        qrs_amplitude = np.random.uniform(1.0, 1.5)

    # 计算心跳间隔
    rr_interval = 60.0 / heart_rate  # 秒
    beat_interval = int(rr_interval * sampling_rate)  # 采样点

    # 生成每个心跳
    num_beats = int(length / beat_interval)

    for beat_idx in range(num_beats):
        beat_start = beat_idx * beat_interval

        if beat_start + beat_interval > length:
            break

        # P波 (心房去极化)
        p_start = beat_start + int(0.05 * sampling_rate)
        p_duration = int(0.08 * sampling_rate)
        if p_start + p_duration < length:
            p_wave = 0.15 * np.exp(-((np.arange(p_duration) - p_duration/2) ** 2) / (p_duration/4))
            ecg[p_start:p_start+p_duration] += p_wave

        # QRS波群 (心室去极化) - 最重要的部分
        qrs_start = beat_start + int(0.16 * sampling_rate)
        qrs_duration = int(0.08 * sampling_rate)

        if qrs_start + qrs_duration < length:
            # Q波 (小的负向波)
            q_duration = int(0.02 * sampling_rate)
            q_wave = -0.1 * np.exp(-((np.arange(q_duration) - q_duration/2) ** 2) / (q_duration/6))
            ecg[qrs_start:qrs_start+q_duration] += q_wave

            # R波 (高的正向波) - 这是R波检测的关键
            r_start = qrs_start + q_duration
            r_duration = int(0.04 * sampling_rate)
            r_wave = qrs_amplitude * np.exp(-((np.arange(r_duration) - r_duration/2) ** 2) / (r_duration/8))
            if r_start + r_duration < length:
                ecg[r_start:r_start+r_duration] += r_wave

            # S波 (负向波)
            s_start = r_start + r_duration
            s_duration = int(0.02 * sampling_rate)
            s_wave = -0.2 * np.exp(-((np.arange(s_duration) - s_duration/2) ** 2) / (s_duration/6))
            if s_start + s_duration < length:
                ecg[s_start:s_start+s_duration] += s_wave

        # T波 (心室复极化)
        t_start = beat_start + int(0.32 * sampling_rate)
        t_duration = int(0.16 * sampling_rate)
        if t_start + t_duration < length:
            t_wave = 0.3 * np.exp(-((np.arange(t_duration) - t_duration/2) ** 2) / (t_duration/3))
            ecg[t_start:t_start+t_duration] += t_wave

    # 添加基线漂移
    baseline = 0.05 * np.sin(2 * np.pi * 0.2 * t)
    ecg += baseline

    # 如果有疾病，添加异常特征
    if has_disease:
        # ST段压低
        ecg -= 0.05
        # 添加更多噪声
        ecg += np.random.normal(0, 0.03, length)
        # T波倒置（部分）
        for beat_idx in range(0, num_beats, 3):  # 每3个心跳有一个异常
            t_start = beat_idx * beat_interval + int(0.32 * sampling_rate)
            t_duration = int(0.16 * sampling_rate)
            if t_start + t_duration < length:
                ecg[t_start:t_start+t_duration] *= -0.5
    else:
        # 正常噪声
        ecg += np.random.normal(0, 0.01, length)

    return ecg

def create_h5_file(filepath, ecg_signal, sampling_rate=500):
    """创建H5文件"""
    with h5py.File(filepath, 'w') as f:
        f.create_dataset('ecg', data=ecg_signal)
        f.create_dataset('sampling_rate', data=sampling_rate)
        f.attrs['length'] = len(ecg_signal)
        f.attrs['duration'] = len(ecg_signal) / sampling_rate

def generate_ecg_samples():
    """生成心电数据样本（用于风险监测）"""
    print("生成心电数据样本...")
    ecg_dir = TEST_DATA_DIR / "ecg_samples"
    ecg_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, 11):
        has_disease = i > 5  # 后5个为疾病样本
        ecg = generate_ecg_signal(has_disease=has_disease)
        filepath = ecg_dir / f"sample_{i:03d}.h5"
        create_h5_file(filepath, ecg)
        print(f"  创建: {filepath.name}")

    print(f"[OK] 完成：生成10个心电样本文件")

def generate_h5_training_samples():
    """生成H5训练样本（用于H5快速训练）"""
    print("\n生成H5训练样本...")
    h5_dir = TEST_DATA_DIR / "h5_training_samples"
    h5_dir.mkdir(parents=True, exist_ok=True)

    # 生成元数据
    metadata = []

    for i in range(1, 21):
        subject_id = f"subject_{i:03d}"
        has_disease = i > 10  # 前10个健康，后10个疾病

        # 生成H5文件
        ecg = generate_ecg_signal(length=5000, has_disease=has_disease)
        filepath = h5_dir / f"{subject_id}.h5"
        create_h5_file(filepath, ecg)

        # 添加元数据
        metadata.append({
            'Subject_ID': subject_id,
            'Disease_Status': 'Healthy' if not has_disease else 'CAD',
            'Age': np.random.randint(35, 70),
            'Gender': np.random.choice(['Male', 'Female']),
            'BMI': round(np.random.uniform(20, 35), 1)
        })

        print(f"  创建: {filepath.name} - {'Healthy' if not has_disease else 'CAD'}")

    # 保存元数据
    metadata_df = pd.DataFrame(metadata)
    metadata_path = h5_dir / "SubjectMetadata.csv"
    metadata_df.to_csv(metadata_path, index=False)
    print(f"  创建: SubjectMetadata.csv")

    print(f"[OK] 完成：生成20个H5训练样本和元数据文件")

def generate_matlab_h5_samples():
    """生成MATLAB格式H5样本（用于格式转换）"""
    print("\n生成MATLAB格式H5样本...")
    matlab_dir = TEST_DATA_DIR / "matlab_h5_samples"
    matlab_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, 6):
        ecg = generate_ecg_signal()
        filepath = matlab_dir / f"matlab_sample_{i:03d}.h5"

        # MATLAB格式：使用不同的数据集名称
        with h5py.File(filepath, 'w') as f:
            f.create_dataset('data/ecg_signal', data=ecg)
            f.create_dataset('data/fs', data=500)
            f.attrs['format'] = 'MATLAB'

        print(f"  创建: {filepath.name}")

    print(f"[OK] 完成：生成5个MATLAB格式H5文件")

def generate_experiment_dataset():
    """生成论文实验数据集"""
    print("\n生成论文实验数据集...")

    n_samples = 1000
    n_features = 50

    # 生成特征数据
    X = np.random.randn(n_samples, n_features)

    # 生成标签（30%为阳性）
    y = np.random.choice([0, 1], size=n_samples, p=[0.7, 0.3])

    # 为阳性样本调整特征（使其更容易区分）
    for i in range(n_samples):
        if y[i] == 1:
            X[i, :10] += 1.5  # 前10个特征增强

    # 创建DataFrame
    feature_names = [f'feature_{i+1}' for i in range(n_features)]
    df = pd.DataFrame(X, columns=feature_names)
    df['CAD_risk'] = y

    # 添加一些临床特征名称
    df.rename(columns={
        'feature_1': 'age',
        'feature_2': 'bmi',
        'feature_3': 'systolic_bp',
        'feature_4': 'diastolic_bp',
        'feature_5': 'cholesterol',
        'feature_6': 'glucose',
        'feature_7': 'heart_rate',
        'feature_8': 'hrv_sdnn',
        'feature_9': 'hrv_rmssd',
        'feature_10': 'hrv_pnn50'
    }, inplace=True)

    # 保存
    filepath = TEST_DATA_DIR / "experiment_dataset.csv"
    df.to_csv(filepath, index=False)

    print(f"  创建: experiment_dataset.csv")
    print(f"  样本数: {n_samples}, 特征数: {n_features}, 阳性率: {y.mean():.1%}")
    print(f"[OK] 完成：生成实验数据集")

def generate_metadata_csv():
    """生成SubjectMetadata.csv的说明文件"""
    content = """# SubjectMetadata.csv 格式说明

此文件用于H5快速训练功能，系统会自动读取此文件获取标签信息。

## 必需列

- **Subject_ID**: 受试者ID，必须与H5文件名对应（不含.h5后缀）
- **Disease_Status**: 疾病状态，"Healthy"表示健康（标签0），其他值表示疾病（标签1）

## 可选列

- Age: 年龄
- Gender: 性别
- BMI: 体重指数
- 其他临床特征...

## 示例

```csv
Subject_ID,Disease_Status,Age,Gender,BMI
subject_001,Healthy,45,Male,24.5
subject_002,CAD,52,Female,28.3
subject_003,Healthy,38,Male,22.1
```

## 注意事项

1. 文件必须与H5文件在同一目录
2. Subject_ID必须与H5文件名完全匹配
3. Disease_Status列必须存在
4. 使用UTF-8编码保存
"""

    filepath = TEST_DATA_DIR / "h5_training_samples" / "README_METADATA.md"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n[OK] 创建元数据说明文件: README_METADATA.md")

def main():
    """主函数"""
    print("=" * 60)
    print("HeartCycle 测试数据生成工具")
    print("=" * 60)

    # 创建测试数据目录
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 生成各类测试数据
    generate_ecg_samples()
    generate_h5_training_samples()
    generate_matlab_h5_samples()
    generate_experiment_dataset()
    generate_metadata_csv()

    print("\n" + "=" * 60)
    print("[OK] 所有测试数据生成完成！")
    print("=" * 60)
    print(f"\n测试数据位置: {TEST_DATA_DIR}")
    print("\n请查看 'docs/guides/前端操作手册.md' 了解如何使用这些测试数据。")

if __name__ == "__main__":
    main()
