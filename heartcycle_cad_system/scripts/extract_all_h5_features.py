"""
从所有H5文件提取完整特征
"""
import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'backend'))

from algorithms.feature_extraction import HRVFeatureExtractor
from algorithms.data_processing import ECGProcessor
import h5py

def load_h5_data(h5_file):
    """加载H5文件数据"""
    try:
        with h5py.File(h5_file, 'r') as f:
            # 这个H5格式的ECG数据在通道1
            # measure/value/_001/value/data/value
            ecg_data = f['measure/value/_001/value/data/value'][:]

            # 如果是2D数组，取第一行
            if len(ecg_data.shape) == 2:
                ecg_data = ecg_data[0]

            # 检查数据是否有效
            if ecg_data is None or len(ecg_data) == 0:
                return None

            # 检查数据是否全为0
            if np.abs(ecg_data).max() < 1e-6:
                return None

            return ecg_data
    except Exception as e:
        return None


def extract_features_from_h5_dirs(h5_dirs, metadata_files, output_dir):
    """从多个H5目录提取特征"""

    print(f"\n{'='*80}")
    print(f"从H5文件提取完整特征")
    print(f"{'='*80}\n")

    # 加载所有元数据
    all_metadata = []
    for metadata_file in metadata_files:
        if os.path.exists(metadata_file):
            df = pd.read_csv(metadata_file)
            all_metadata.append(df)
            print(f"[OK] 加载元数据: {metadata_file} ({len(df)}条记录)")

    if not all_metadata:
        print("[ERROR] 未找到元数据文件")
        return

    metadata_df = pd.concat(all_metadata, ignore_index=True)
    print(f"\n[OK] 总元数据记录: {len(metadata_df)}")

    # 收集所有H5文件
    all_h5_files = []
    for h5_dir in h5_dirs:
        h5_files = list(Path(h5_dir).rglob("*.h5"))
        all_h5_files.extend(h5_files)
        print(f"[OK] 找到H5文件: {h5_dir} ({len(h5_files)}个)")

    print(f"\n[OK] 总H5文件数: {len(all_h5_files)}")

    # 初始化特征提取器和处理器
    extractor = HRVFeatureExtractor()
    processor = ECGProcessor()

    # 提取特征
    all_features = []
    all_labels = []
    failed_count = 0

    print(f"\n开始提取特征...\n")

    for h5_file in tqdm(all_h5_files, desc="提取特征"):
        # 加载ECG数据
        ecg_data = load_h5_data(h5_file)
        if ecg_data is None:
            failed_count += 1
            continue

        # 提取文件名
        file_name = h5_file.stem

        # 从元数据获取临床信息
        metadata_row = metadata_df[metadata_df['File_Name'] == file_name]

        if len(metadata_row) == 0:
            # 没有元数据，使用默认值
            clinical_data = {
                'age': 30,
                'gender': 1,
                'height': 170,
                'weight': 70,
                'bmi': 24.2
            }
            label = 0  # 默认健康
        else:
            row = metadata_row.iloc[0]
            clinical_data = {
                'age': row.get('Age_years', 30),
                'gender': 1 if row.get('Gender', 'M') == 'M' else 0,
                'height': row.get('Height_cm', 170),
                'weight': row.get('Weight_kg', 70),
                'bmi': row.get('BMI', 24.2)
            }
            # 标签：Healthy=0, 其他=1
            disease_status = row.get('Disease_Status', 'Healthy')
            label = 0 if disease_status == 'Healthy' else 1

        # 提取HRV特征
        try:
            # 1. 滤波处理
            filtered_ecg = processor.bandpass_filter(ecg_data)

            # 2. 去除基线漂移
            clean_ecg = processor.remove_baseline_drift(filtered_ecg)

            # 3. 检测R峰
            rpeaks = processor.detect_rpeaks_pan_tompkins(clean_ecg)

            if rpeaks is None or len(rpeaks) < 10:
                failed_count += 1
                continue

            # 4. 计算RR间期
            rr_intervals = processor.compute_rr_intervals(rpeaks)

            if rr_intervals is None or len(rr_intervals) < 10:
                failed_count += 1
                continue

            # 5. 去除异常RR间期
            rr_intervals = processor.remove_outlier_rr(rr_intervals)

            if rr_intervals is None or len(rr_intervals) < 10:
                failed_count += 1
                continue

            # 6. 提取时域、频域、非线性特征
            time_features = extractor.extract_time_domain_features(rr_intervals)
            freq_features = extractor.extract_frequency_domain_features(rr_intervals)
            nonlinear_features = extractor.extract_nonlinear_features(rr_intervals)

            # 7. 合并所有特征
            features = {**clinical_data, **time_features, **freq_features, **nonlinear_features}

            if features is not None and len(features) > 0:
                all_features.append(features)
                all_labels.append(label)
        except Exception as e:
            failed_count += 1
            continue

    print(f"\n[OK] 特征提取完成")
    print(f"   成功: {len(all_features)}个")
    print(f"   失败: {failed_count}个")

    if len(all_features) == 0:
        print("[ERROR] 没有成功提取任何特征")
        return

    # 转换为DataFrame
    df_features = pd.DataFrame(all_features)
    df_labels = pd.DataFrame({'label': all_labels})

    # 检查特征数量
    print(f"\n[OK] 特征统计:")
    print(f"   样本数: {len(df_features)}")
    print(f"   特征数: {len(df_features.columns)}")
    print(f"   标签分布: {df_labels['label'].value_counts().to_dict()}")

    # 保存
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    feature_file = output_path / 'all_h5_features.csv'
    label_file = output_path / 'all_h5_labels.csv'

    df_features.to_csv(feature_file, index=False)
    df_labels.to_csv(label_file, index=False)

    print(f"\n[OK] 特征已保存: {feature_file}")
    print(f"[OK] 标签已保存: {label_file}")

    # 显示特征列表
    print(f"\n特征列表 ({len(df_features.columns)}个):")
    for i, col in enumerate(df_features.columns, 1):
        print(f"   {i:2d}. {col}")

    return df_features, df_labels


if __name__ == '__main__':
    # H5数据目录
    h5_dirs = [
        r"D:\Graduate Work\heartcycle\59146237\measure",
        r"D:\Graduate Work\heartcycle\59146238\measure",
        r"D:\Graduate Work\heartcycle\59146239\measure"
    ]

    # 元数据文件
    metadata_files = [
        r"D:\Graduate Work\heartcycle\59146237\59146237_SubjectMetadata.csv",
        r"D:\Graduate Work\heartcycle\59146238\59146238_SubjectMetadata.csv",
        r"D:\Graduate Work\heartcycle\59146239\59146239_SubjectMetadata.csv"
    ]

    # 输出目录
    output_dir = r"D:\Graduate Work\heartcycle_cad_system\data\features\complete_h5"

    # 提取特征
    extract_features_from_h5_dirs(h5_dirs, metadata_files, output_dir)
