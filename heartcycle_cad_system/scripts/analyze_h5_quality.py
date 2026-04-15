"""
分析H5文件数据质量
检查是否存在导致训练失败的数据问题
"""
import h5py
import numpy as np
import sys
from pathlib import Path

def analyze_h5_file(h5_path):
    """分析单个H5文件"""
    result = {
        'file': h5_path.name,
        'status': 'ok',
        'issues': [],
        'stats': {}
    }

    try:
        with h5py.File(h5_path, 'r') as f:
            # 检查数据集结构
            if 'ecg' not in f:
                result['status'] = 'error'
                result['issues'].append('缺少ecg数据集')
                return result

            ecg_data = f['ecg'][:]

            # 基本统计
            result['stats']['shape'] = ecg_data.shape
            result['stats']['dtype'] = str(ecg_data.dtype)
            result['stats']['size'] = ecg_data.size

            # 检查NaN
            nan_count = np.isnan(ecg_data).sum()
            if nan_count > 0:
                result['issues'].append(f'包含{nan_count}个NaN值')
                result['stats']['nan_count'] = int(nan_count)
                result['stats']['nan_percent'] = float(nan_count / ecg_data.size * 100)

            # 检查Inf
            inf_count = np.isinf(ecg_data).sum()
            if inf_count > 0:
                result['issues'].append(f'包含{inf_count}个Inf值')
                result['stats']['inf_count'] = int(inf_count)

            # 检查全零
            if np.all(ecg_data == 0):
                result['status'] = 'warning'
                result['issues'].append('数据全为0')

            # 检查数据范围
            if not np.all(np.isnan(ecg_data)) and not np.all(np.isinf(ecg_data)):
                result['stats']['min'] = float(np.nanmin(ecg_data))
                result['stats']['max'] = float(np.nanmax(ecg_data))
                result['stats']['mean'] = float(np.nanmean(ecg_data))
                result['stats']['std'] = float(np.nanstd(ecg_data))

                # 检查异常值
                if result['stats']['std'] == 0:
                    result['issues'].append('标准差为0（所有值相同）')

                # 检查数据长度
                if ecg_data.size < 100:
                    result['issues'].append(f'数据点过少({ecg_data.size})')

            # 设置状态
            if result['issues']:
                if result['status'] == 'ok':
                    result['status'] = 'warning'

    except Exception as e:
        result['status'] = 'error'
        result['issues'].append(f'读取失败: {str(e)}')

    return result

def analyze_directory(dir_path):
    """分析整个目录"""
    dir_path = Path(dir_path)
    h5_files = list(dir_path.glob('*.h5'))

    print("=" * 80)
    print(f"H5文件数据质量分析报告")
    print("=" * 80)
    print(f"\n目录: {dir_path}")
    print(f"文件数量: {len(h5_files)}")
    print("\n" + "-" * 80)

    results = []
    ok_count = 0
    warning_count = 0
    error_count = 0

    for h5_file in sorted(h5_files):
        result = analyze_h5_file(h5_file)
        results.append(result)

        if result['status'] == 'ok':
            ok_count += 1
        elif result['status'] == 'warning':
            warning_count += 1
        else:
            error_count += 1

    # 打印汇总
    print("\n## 状态汇总")
    print(f"  正常: {ok_count}")
    print(f"  警告: {warning_count}")
    print(f"  错误: {error_count}")

    # 打印问题文件
    if warning_count > 0 or error_count > 0:
        print("\n## 问题文件详情")
        for result in results:
            if result['status'] != 'ok':
                print(f"\n文件: {result['file']}")
                print(f"  状态: {result['status']}")
                if result['issues']:
                    for issue in result['issues']:
                        print(f"  - {issue}")
                if result['stats']:
                    print(f"  统计: {result['stats']}")

    # 统计常见问题
    print("\n## 常见问题统计")
    issue_types = {}
    for result in results:
        for issue in result['issues']:
            issue_type = issue.split('(')[0].strip()
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

    if issue_types:
        for issue_type, count in sorted(issue_types.items(), key=lambda x: -x[1]):
            print(f"  {issue_type}: {count} 个文件")
    else:
        print("  无问题")

    # 数据统计汇总
    print("\n## 数据统计汇总")
    all_stats = [r['stats'] for r in results if 'min' in r['stats']]
    if all_stats:
        print(f"  数据范围:")
        print(f"    最小值: {min(s['min'] for s in all_stats):.2f}")
        print(f"    最大值: {max(s['max'] for s in all_stats):.2f}")
        print(f"  均值范围: {min(s['mean'] for s in all_stats):.2f} ~ {max(s['mean'] for s in all_stats):.2f}")
        print(f"  标准差范围: {min(s['std'] for s in all_stats):.2f} ~ {max(s['std'] for s in all_stats):.2f}")

    # 结论
    print("\n" + "=" * 80)
    print("## 诊断结论")
    print("=" * 80)

    if error_count == 0 and warning_count == 0:
        print("✓ 数据质量良好，没有发现问题")
        print("✓ 训练失败的原因不是数据质量问题")
        print("→ 建议检查程序逻辑和特征提取过程")
    elif error_count > 0:
        print(f"✗ 发现 {error_count} 个严重错误文件")
        print("→ 这些文件可能导致训练失败")
        print("→ 建议修复或删除这些文件")
    else:
        print(f"[提示] 发现 {warning_count} 个警告文件")
        print("→ 这些文件的数据质量有待改善，但应该不影响训练")
        print("→ 如果训练仍然失败，问题可能在特征提取或模型训练阶段")

    print("\n" + "=" * 80)

    return results

if __name__ == "__main__":
    if len(sys.argv) > 1:
        dir_path = sys.argv[1]
    else:
        dir_path = r"D:\Graduate Work\heartcycle\59146237\measure"

    analyze_directory(dir_path)
