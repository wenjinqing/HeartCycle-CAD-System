"""
将MATLAB格式的H5文件转换为简单格式
"""
import h5py
import numpy as np
from pathlib import Path
import sys

def convert_matlab_h5(input_path, output_path):
    """
    转换MATLAB格式的H5文件为简单格式

    从 measure/value/_XXX/value/data/value
    转换为 ecg 数据集
    """
    print(f"转换: {input_path.name}")

    try:
        with h5py.File(input_path, 'r') as f_in:
            # 收集所有心拍周期的数据
            all_data = []

            measure_group = f_in['measure']['value']

            # 遍历所有心拍周期 (_000, _001, _002, ...)
            beat_keys = [k for k in measure_group.keys() if k.startswith('_')]
            beat_keys.sort()  # 确保顺序

            for beat_key in beat_keys:
                try:
                    data_path = f"measure/value/{beat_key}/value/data/value"
                    if data_path.replace('measure/value/', '').split('/')[0] in measure_group:
                        beat_data = f_in[data_path][:]

                        # 检查数据是否有效
                        if beat_data.size > 0:
                            # 展平数据（从 (1, N) 转为 (N,)）
                            beat_data = beat_data.flatten()

                            # 跳过全零数据
                            if not np.all(beat_data == 0):
                                all_data.append(beat_data)
                except:
                    continue

            if len(all_data) == 0:
                print(f"  警告: 没有找到有效数据")
                return False

            # 合并所有心拍周期
            ecg_data = np.concatenate(all_data)

            print(f"  心拍周期数: {len(all_data)}")
            print(f"  总数据点: {ecg_data.size}")
            print(f"  数据范围: [{ecg_data.min():.2f}, {ecg_data.max():.2f}]")

            # 保存为简单格式
            with h5py.File(output_path, 'w') as f_out:
                f_out.create_dataset('ecg', data=ecg_data, compression='gzip')

            print(f"  转换成功 -> {output_path.name}")
            return True

    except Exception as e:
        print(f"  错误: {str(e)}")
        return False

def convert_directory(input_dir, output_dir):
    """转换整个目录"""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)

    # 获取所有H5文件
    h5_files = list(input_dir.glob('*.h5'))

    print("=" * 60)
    print(f"H5文件格式转换")
    print("=" * 60)
    print(f"输入目录: {input_dir}")
    print(f"输出目录: {output_dir}")
    print(f"文件数量: {len(h5_files)}")
    print()

    success = 0
    failed = 0

    for h5_file in sorted(h5_files):
        output_file = output_dir / h5_file.name

        if convert_matlab_h5(h5_file, output_file):
            success += 1
        else:
            failed += 1

    print()
    print("=" * 60)
    print(f"转换完成")
    print("=" * 60)
    print(f"成功: {success}")
    print(f"失败: {failed}")
    print(f"\n转换后的文件在: {output_dir}")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        input_dir = sys.argv[1]
        output_dir = sys.argv[2]
    else:
        # 默认路径
        input_dir = r"D:\Graduate Work\heartcycle\59146237\measure"
        output_dir = r"D:\Graduate Work\heartcycle\59146237\measure_converted"

    convert_directory(input_dir, output_dir)
