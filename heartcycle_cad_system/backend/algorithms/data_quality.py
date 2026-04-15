"""
数据质量分析模块
用于评估 ECG 信号质量和数据完整性
"""
import numpy as np
import h5py
from scipy import signal
from scipy.stats import skew, kurtosis
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DataQualityAnalyzer:
    """数据质量分析器"""

    def __init__(self, sampling_rate: int = 200):
        """
        初始化

        Parameters:
        -----------
        sampling_rate : int
            采样率 (Hz)
        """
        self.sampling_rate = sampling_rate

    def analyze_signal_quality(self, ecg_signal: np.ndarray) -> Dict:
        """
        分析单个 ECG 信号质量

        Parameters:
        -----------
        ecg_signal : np.ndarray
            ECG 信号

        Returns:
        --------
        质量指标字典
        """
        metrics = {}

        # 1. 基本统计
        metrics['length'] = len(ecg_signal)
        metrics['mean'] = float(np.mean(ecg_signal))
        metrics['std'] = float(np.std(ecg_signal))
        metrics['min'] = float(np.min(ecg_signal))
        metrics['max'] = float(np.max(ecg_signal))
        metrics['range'] = float(np.ptp(ecg_signal))

        # 2. 分布特征
        metrics['skewness'] = float(skew(ecg_signal))
        metrics['kurtosis'] = float(kurtosis(ecg_signal))

        # 3. 缺失值和异常值
        metrics['has_nan'] = bool(np.isnan(ecg_signal).any())
        metrics['has_inf'] = bool(np.isinf(ecg_signal).any())
        metrics['num_zeros'] = int(np.sum(ecg_signal == 0))
        metrics['zero_ratio'] = float(metrics['num_zeros'] / len(ecg_signal))

        # 4. 信号幅度检查
        # 正常 ECG 信号幅度通常在 -2 到 2 mV 之间
        metrics['amplitude_normal'] = bool(-3 < metrics['mean'] < 3)
        metrics['amplitude_range_normal'] = bool(0.1 < metrics['range'] < 5)

        # 5. 信噪比估计 (SNR)
        try:
            snr = self._estimate_snr(ecg_signal)
            metrics['snr_db'] = float(snr)
            metrics['snr_quality'] = self._classify_snr(snr)
        except Exception as e:
            logger.warning(f"SNR 计算失败: {e}")
            metrics['snr_db'] = None
            metrics['snr_quality'] = 'unknown'

        # 6. 基线漂移检测
        try:
            baseline_drift = self._detect_baseline_drift(ecg_signal)
            metrics['baseline_drift'] = float(baseline_drift)
            metrics['has_baseline_drift'] = bool(baseline_drift > 0.1)
        except Exception as e:
            logger.warning(f"基线漂移检测失败: {e}")
            metrics['baseline_drift'] = None
            metrics['has_baseline_drift'] = False

        # 7. 工频干扰检测 (50/60 Hz)
        try:
            power_line_noise = self._detect_power_line_noise(ecg_signal)
            metrics['power_line_noise'] = float(power_line_noise)
            metrics['has_power_line_noise'] = bool(power_line_noise > 0.05)
        except Exception as e:
            logger.warning(f"工频干扰检测失败: {e}")
            metrics['power_line_noise'] = None
            metrics['has_power_line_noise'] = False

        # 8. 综合质量评分 (0-100)
        quality_score = self._calculate_quality_score(metrics)
        metrics['quality_score'] = float(quality_score)
        metrics['quality_level'] = self._classify_quality(quality_score)

        return metrics

    def _estimate_snr(self, ecg_signal: np.ndarray) -> float:
        """
        估计信噪比 (SNR)

        使用高频成分作为噪声估计
        """
        # 高通滤波提取高频噪声
        sos = signal.butter(4, 40, 'hp', fs=self.sampling_rate, output='sos')
        noise = signal.sosfilt(sos, ecg_signal)

        # 计算信号功率和噪声功率
        signal_power = np.mean(ecg_signal ** 2)
        noise_power = np.mean(noise ** 2)

        # 避免除零
        if noise_power < 1e-10:
            return 100.0

        snr = 10 * np.log10(signal_power / noise_power)
        return snr

    def _classify_snr(self, snr: float) -> str:
        """分类 SNR 质量"""
        if snr >= 20:
            return 'excellent'
        elif snr >= 15:
            return 'good'
        elif snr >= 10:
            return 'fair'
        else:
            return 'poor'

    def _detect_baseline_drift(self, ecg_signal: np.ndarray) -> float:
        """
        检测基线漂移

        使用低通滤波提取基线
        """
        # 低通滤波提取基线
        sos = signal.butter(4, 0.5, 'lp', fs=self.sampling_rate, output='sos')
        baseline = signal.sosfilt(sos, ecg_signal)

        # 计算基线漂移幅度
        drift = np.std(baseline)
        return drift

    def _detect_power_line_noise(self, ecg_signal: np.ndarray) -> float:
        """
        检测工频干扰 (50/60 Hz)

        使用 FFT 分析频谱
        """
        # FFT
        fft = np.fft.fft(ecg_signal)
        freqs = np.fft.fftfreq(len(ecg_signal), 1/self.sampling_rate)

        # 只看正频率
        positive_freqs = freqs[:len(freqs)//2]
        positive_fft = np.abs(fft[:len(fft)//2])

        # 检查 50 Hz 和 60 Hz 附近的能量
        power_50hz = self._get_power_at_frequency(positive_freqs, positive_fft, 50, bandwidth=2)
        power_60hz = self._get_power_at_frequency(positive_freqs, positive_fft, 60, bandwidth=2)

        # 总能量
        total_power = np.sum(positive_fft ** 2)

        # 工频干扰比例
        noise_ratio = (power_50hz + power_60hz) / (total_power + 1e-10)
        return noise_ratio

    def _get_power_at_frequency(
        self,
        freqs: np.ndarray,
        fft: np.ndarray,
        target_freq: float,
        bandwidth: float = 2
    ) -> float:
        """获取指定频率附近的功率"""
        mask = (freqs >= target_freq - bandwidth) & (freqs <= target_freq + bandwidth)
        power = np.sum(fft[mask] ** 2)
        return power

    def _calculate_quality_score(self, metrics: Dict) -> float:
        """
        计算综合质量评分 (0-100)

        考虑多个因素：
        - SNR
        - 基线漂移
        - 工频干扰
        - 幅度范围
        - 缺失值
        """
        score = 100.0

        # SNR 扣分
        if metrics.get('snr_db') is not None:
            snr = metrics['snr_db']
            if snr < 10:
                score -= 30
            elif snr < 15:
                score -= 15
            elif snr < 20:
                score -= 5

        # 基线漂移扣分
        if metrics.get('has_baseline_drift'):
            score -= 15

        # 工频干扰扣分
        if metrics.get('has_power_line_noise'):
            score -= 10

        # 幅度异常扣分
        if not metrics.get('amplitude_normal'):
            score -= 10
        if not metrics.get('amplitude_range_normal'):
            score -= 10

        # 缺失值扣分
        if metrics.get('has_nan') or metrics.get('has_inf'):
            score -= 20

        # 零值过多扣分
        if metrics.get('zero_ratio', 0) > 0.1:
            score -= 15

        return max(0, min(100, score))

    def _classify_quality(self, score: float) -> str:
        """分类质量等级"""
        if score >= 80:
            return 'excellent'
        elif score >= 60:
            return 'good'
        elif score >= 40:
            return 'fair'
        else:
            return 'poor'

    def analyze_dataset(
        self,
        h5_files: List[str],
        sample_size: Optional[int] = None
    ) -> Dict:
        """
        分析整个数据集的质量

        Parameters:
        -----------
        h5_files : List[str]
            H5 文件路径列表
        sample_size : Optional[int]
            采样数量（None 表示全部）

        Returns:
        --------
        数据集质量报告
        """
        if sample_size:
            import random
            h5_files = random.sample(h5_files, min(sample_size, len(h5_files)))

        all_metrics = []
        failed_files = []

        for h5_file in h5_files:
            try:
                with h5py.File(h5_file, 'r') as f:
                    # 读取 ECG 信号
                    if 'ecg' in f:
                        ecg = f['ecg'][:]
                    elif 'signal' in f:
                        ecg = f['signal'][:]
                    else:
                        failed_files.append(h5_file)
                        continue

                    # 分析质量
                    metrics = self.analyze_signal_quality(ecg)
                    metrics['file'] = h5_file
                    all_metrics.append(metrics)

            except Exception as e:
                logger.error(f"分析文件 {h5_file} 失败: {e}")
                failed_files.append(h5_file)

        if not all_metrics:
            raise ValueError("没有成功分析任何文件")

        # 汇总统计
        summary = self._summarize_metrics(all_metrics)
        summary['total_files'] = len(h5_files)
        summary['analyzed_files'] = len(all_metrics)
        summary['failed_files'] = len(failed_files)
        summary['failed_file_list'] = failed_files

        return {
            'summary': summary,
            'details': all_metrics
        }

    def _summarize_metrics(self, all_metrics: List[Dict]) -> Dict:
        """汇总指标统计"""
        summary = {}

        # 质量分布
        quality_levels = [m['quality_level'] for m in all_metrics]
        summary['quality_distribution'] = {
            'excellent': quality_levels.count('excellent'),
            'good': quality_levels.count('good'),
            'fair': quality_levels.count('fair'),
            'poor': quality_levels.count('poor')
        }

        # 平均质量评分
        scores = [m['quality_score'] for m in all_metrics]
        summary['avg_quality_score'] = float(np.mean(scores))
        summary['min_quality_score'] = float(np.min(scores))
        summary['max_quality_score'] = float(np.max(scores))

        # SNR 统计
        snr_values = [m['snr_db'] for m in all_metrics if m['snr_db'] is not None]
        if snr_values:
            summary['avg_snr'] = float(np.mean(snr_values))
            summary['min_snr'] = float(np.min(snr_values))
            summary['max_snr'] = float(np.max(snr_values))

        # 问题统计
        summary['files_with_baseline_drift'] = sum(m['has_baseline_drift'] for m in all_metrics)
        summary['files_with_power_line_noise'] = sum(m['has_power_line_noise'] for m in all_metrics)
        summary['files_with_nan'] = sum(m['has_nan'] for m in all_metrics)
        summary['files_with_inf'] = sum(m['has_inf'] for m in all_metrics)

        # 推荐
        summary['recommendations'] = self._generate_recommendations(summary)

        return summary

    def _generate_recommendations(self, summary: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 质量建议
        poor_ratio = summary['quality_distribution']['poor'] / summary.get('analyzed_files', 1)
        if poor_ratio > 0.2:
            recommendations.append("超过20%的信号质量较差，建议进行数据清洗")

        # SNR 建议
        if summary.get('avg_snr', 100) < 15:
            recommendations.append("平均信噪比较低，建议使用滤波器降噪")

        # 基线漂移建议
        drift_ratio = summary.get('files_with_baseline_drift', 0) / summary.get('analyzed_files', 1)
        if drift_ratio > 0.3:
            recommendations.append("超过30%的信号存在基线漂移，建议使用高通滤波器")

        # 工频干扰建议
        noise_ratio = summary.get('files_with_power_line_noise', 0) / summary.get('analyzed_files', 1)
        if noise_ratio > 0.2:
            recommendations.append("超过20%的信号存在工频干扰，建议使用陷波滤波器")

        # 缺失值建议
        if summary.get('files_with_nan', 0) > 0 or summary.get('files_with_inf', 0) > 0:
            recommendations.append("存在缺失值或无穷值，建议进行数据清洗")

        if not recommendations:
            recommendations.append("数据质量良好，可以直接用于训练")

        return recommendations
