#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试H5文件特征提取
验证生成的测试数据是否能正确提取特征
"""

import sys
import os
import io
import h5py
import numpy as np
from pathlib import Path

# 设置输出编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加backend路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

try:
    from algorithms.data_processing import ECGProcessor
    from algorithms.feature_extraction import HRVFeatureExtractor
    print("[OK] 成功导入模块")
except ImportError as e:
    print(f"[ERROR] 导入模块失败: {e}")
    sys.exit(1)

def test_h5_file(file_path):
    """测试单个H5文件"""
    print(f"\n{'='*60}")
    print(f"测试文件: {file_path}")
    print('='*60)

    # 1. 检查H5文件结构
    print("\n1. 检查H5文件结构...")
    try:
        with h5py.File(file_path, 'r') as f:
            print(f"   Keys: {list(f.keys())}")
            if 'ecg' in f:
                print(f"   ECG shape: {f['ecg'].shape}")
                print(f"   ECG dtype: {f['ecg'].dtype}")
                print(f"   ECG range: [{f['ecg'][:].min():.3f}, {f['ecg'][:].max():.3f}]")
            if 'sampling_rate' in f:
                print(f"   Sampling rate: {f['sampling_rate'][()]} Hz")
        print("   [OK] H5文件结构正常")
    except Exception as e:
        print(f"   [X] H5文件结构检查失败: {e}")
        return False

    # 2. 测试加载ECG信号
    print("\n2. 测试加载ECG信号...")
    try:
        processor = ECGProcessor(sampling_rate=500)
        ecg_signal, time_vector = processor.load_hdf5_file(file_path)
        print(f"   ECG信号长度: {len(ecg_signal)}")
        print(f"   时间向量长度: {len(time_vector)}")
        print(f"   信号持续时间: {time_vector[-1]:.2f} 秒")
        print("   [OK] ECG信号加载成功")
    except Exception as e:
        print(f"   [X] ECG信号加载失败: {e}")
        return False

    # 3. 测试R波检测
    print("\n3. 测试R波检测...")
    try:
        # 使用简单的峰值检测（如果Pan-Tompkins不可用）
        from scipy.signal import find_peaks

        # 先尝试在原始信号上检测（因为生成的信号已经比较干净）
        peaks, properties = find_peaks(ecg_signal, distance=int(0.4 * 500), prominence=0.2, height=0.5)

        # 如果检测不到，尝试滤波后检测
        if len(peaks) < 2:
            print("   原始信号检测失败，尝试滤波...")
            filtered_signal = processor.bandpass_filter(ecg_signal, lowcut=5.0, highcut=15.0)
            peaks, properties = find_peaks(filtered_signal, distance=int(0.4 * 500), prominence=0.1)

        print(f"   检测到 {len(peaks)} 个R波")
        if len(peaks) > 1:
            rr_intervals = np.diff(peaks) / 500 * 1000  # 转换为毫秒
            print(f"   平均RR间期: {np.mean(rr_intervals):.1f} ms")
            print(f"   心率: {60000 / np.mean(rr_intervals):.1f} bpm")
            print("   [OK] R波检测成功")

            # 4. 测试特征提取
            print("\n4. 测试HRV特征提取...")
            try:
                extractor = HRVFeatureExtractor()
                time_features = extractor.extract_time_domain_features(rr_intervals)

                print(f"   提取到 {len(time_features)} 个时域特征")
                print("   主要特征:")
                print(f"     - SDNN: {time_features.get('sdnn', 0):.2f} ms")
                print(f"     - RMSSD: {time_features.get('rmssd', 0):.2f} ms")
                print(f"     - pNN50: {time_features.get('pnn50', 0):.2f} %")
                print("   [OK] 特征提取成功")
                return True
            except Exception as e:
                print(f"   [X] 特征提取失败: {e}")
                return False
        else:
            print("   [X] R波数量不足，无法计算HRV特征")
            return False

    except Exception as e:
        print(f"   [X] R波检测失败: {e}")
        return False

def main():
    """主函数"""
    print("="*60)
    print("H5文件特征提取测试工具")
    print("="*60)

    # 测试文件路径
    test_dir = Path(__file__).parent.parent / "测试数据" / "ecg_samples"

    if not test_dir.exists():
        print(f"\n[X] 测试数据目录不存在: {test_dir}")
        print("请先运行 generate_test_data.py 生成测试数据")
        return

    # 测试前3个文件
    test_files = list(test_dir.glob("sample_*.h5"))[:3]

    if not test_files:
        print(f"\n[X] 未找到测试文件")
        return

    print(f"\n找到 {len(test_files)} 个测试文件，开始测试...\n")

    success_count = 0
    for file_path in test_files:
        if test_h5_file(str(file_path)):
            success_count += 1

    # 总结
    print(f"\n{'='*60}")
    print(f"测试完成: {success_count}/{len(test_files)} 个文件通过")
    print('='*60)

    if success_count == len(test_files):
        print("\n[OK] 所有测试通过！H5文件可以正常提取特征。")
    else:
        print(f"\n[X] 有 {len(test_files) - success_count} 个文件测试失败。")

if __name__ == "__main__":
    main()
