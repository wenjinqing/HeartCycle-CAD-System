"""
HRV特征提取模块
- 时域特征
- 频域特征
- 非线性特征
"""
import numpy as np
import pandas as pd
from scipy import signal as sg
from scipy.stats import entropy
from typing import Dict, Optional
import sys
import os

# 导入数据预处理模块
sys.path.append(os.path.dirname(__file__))
from algorithms.data_processing import ECGProcessor


class HRVFeatureExtractor:
    """HRV特征提取器"""
    
    def __init__(self):
        self.processor = ECGProcessor()
    
    def extract_time_domain_features(self, rr_intervals: np.ndarray) -> Dict[str, float]:
        """
        提取时域特征
        
        Parameters:
        -----------
        rr_intervals : np.ndarray
            RR间期序列（毫秒）
            
        Returns:
        --------
        features : dict
            时域特征字典
        """
        rr_seconds = rr_intervals / 1000.0  # 转换为秒
        
        features = {}
        
        # 基本统计量
        features['mean_rr'] = np.mean(rr_intervals)
        features['std_rr'] = np.std(rr_intervals)
        features['min_rr'] = np.min(rr_intervals)
        features['max_rr'] = np.max(rr_intervals)
        features['median_rr'] = np.median(rr_intervals)
        
        # SDNN: RR间期的标准差
        features['sdnn'] = np.std(rr_intervals)
        
        # RMSSD: 连续RR间期差值的均方根
        diff_rr = np.diff(rr_intervals)
        features['rmssd'] = np.sqrt(np.mean(diff_rr ** 2))
        
        # pNN50: 相邻RR间期差值超过50ms的比例
        if len(diff_rr) > 0:
            features['pnn50'] = np.sum(np.abs(diff_rr) > 50) / len(diff_rr) * 100
        else:
            features['pnn50'] = 0.0

        # pNN20: 相邻RR间期差值超过20ms的比例
        if len(diff_rr) > 0:
            features['pnn20'] = np.sum(np.abs(diff_rr) > 20) / len(diff_rr) * 100
        else:
            features['pnn20'] = 0.0

        # CV: 变异系数 (Coefficient of Variation)
        if features['mean_rr'] > 0:
            features['cv'] = (features['std_rr'] / features['mean_rr']) * 100
        else:
            features['cv'] = 0.0

        # CVSD: 连续差值的变异系数
        if len(diff_rr) > 0 and np.mean(np.abs(diff_rr)) > 0:
            features['cvsd'] = (np.std(diff_rr) / np.mean(np.abs(diff_rr))) * 100
        else:
            features['cvsd'] = 0.0

        # SDANN: 5分钟段平均RR间期的标准差（简化版：使用整体数据）
        features['sdann'] = features['std_rr']

        # 范围特征
        features['range_rr'] = features['max_rr'] - features['min_rr']

        # 四分位数
        features['q1_rr'] = np.percentile(rr_intervals, 25)
        features['q3_rr'] = np.percentile(rr_intervals, 75)
        features['iqr_rr'] = features['q3_rr'] - features['q1_rr']
        
        # SDSD: 连续RR间期差值的标准差
        features['sdsd'] = np.std(diff_rr) if len(diff_rr) > 0 else 0.0
        
        # 心率变异性三角指数 (HRV Triangular Index)
        hist, bins = np.histogram(rr_intervals, bins=128)
        features['hrv_triangular_index'] = len(rr_intervals) / np.max(hist)
        
        # TINN: 三角插值RR间期直方图的基线宽度
        max_bin_idx = np.argmax(hist)
        if max_bin_idx > 0 and max_bin_idx < len(hist) - 1:
            # 简化的TINN计算
            features['tinn'] = bins[-1] - bins[0]
        else:
            features['tinn'] = features['std_rr'] * 4
        
        # 心率相关
        features['mean_hr'] = 60000.0 / features['mean_rr']  # 次/分钟
        
        return features
    
    def extract_frequency_domain_features(self, rr_intervals: np.ndarray,
                                         sampling_rate: float = 4.0) -> Dict[str, float]:
        """
        提取频域特征（基于Welch方法）
        
        Parameters:
        -----------
        rr_intervals : np.ndarray
            RR间期序列（毫秒）
        sampling_rate : float
            重采样率（Hz），用于频谱分析
            
        Returns:
        --------
        features : dict
            频域特征字典
        """
        if len(rr_intervals) < 10:
            # 数据太少，返回默认值
            return {
                'total_power': 0.0,
                'vlf_power': 0.0,
                'lf_power': 0.0,
                'hf_power': 0.0,
                'lf_hf_ratio': 0.0,
                'lf_norm': 0.0,
                'hf_norm': 0.0,
                'vlf_percent': 0.0,
                'lf_percent': 0.0,
                'hf_percent': 0.0
            }
        
        # 将RR间期转换为心率序列
        hr = 60000.0 / rr_intervals  # 次/分钟
        
        # 重采样到均匀时间间隔
        time_original = np.cumsum(rr_intervals / 1000.0)  # 转换为秒
        time_resampled = np.arange(time_original[0], time_original[-1], 1.0 / sampling_rate)
        hr_resampled = np.interp(time_resampled, time_original, hr)
        
        # 去除趋势（去均值）
        hr_resampled = hr_resampled - np.mean(hr_resampled)
        
        # 使用Welch方法计算功率谱密度
        freqs, psd = sg.welch(hr_resampled, fs=sampling_rate, nperseg=min(len(hr_resampled), 256))
        
        # 定义频段（Hz）
        vlf_band = (0.0033, 0.04)  # Very Low Frequency
        lf_band = (0.04, 0.15)     # Low Frequency
        hf_band = (0.15, 0.4)      # High Frequency
        
        # 计算各频段功率
        vlf_idx = np.logical_and(freqs >= vlf_band[0], freqs < vlf_band[1])
        lf_idx = np.logical_and(freqs >= lf_band[0], freqs < lf_band[1])
        hf_idx = np.logical_and(freqs >= hf_band[0], freqs < hf_band[1])
        
        vlf_power = np.trapz(psd[vlf_idx], freqs[vlf_idx])
        lf_power = np.trapz(psd[lf_idx], freqs[lf_idx])
        hf_power = np.trapz(psd[hf_idx], freqs[hf_idx])
        total_power = vlf_power + lf_power + hf_power
        
        features = {
            'total_power': total_power,
            'vlf_power': vlf_power,
            'lf_power': lf_power,
            'hf_power': hf_power,
        }
        
        # LF/HF比值
        if hf_power > 0:
            features['lf_hf_ratio'] = lf_power / hf_power
        else:
            features['lf_hf_ratio'] = 0.0
        
        # 归一化功率
        if total_power > 0:
            features['lf_norm'] = lf_power / (lf_power + hf_power) * 100
            features['hf_norm'] = hf_power / (lf_power + hf_power) * 100
            features['vlf_percent'] = vlf_power / total_power * 100
            features['lf_percent'] = lf_power / total_power * 100
            features['hf_percent'] = hf_power / total_power * 100
        else:
            features['lf_norm'] = 0.0
            features['hf_norm'] = 0.0
            features['vlf_percent'] = 0.0
            features['lf_percent'] = 0.0
            features['hf_percent'] = 0.0

        # 峰值频率
        if len(psd[lf_idx]) > 0:
            features['lf_peak'] = freqs[lf_idx][np.argmax(psd[lf_idx])]
        else:
            features['lf_peak'] = 0.0

        if len(psd[hf_idx]) > 0:
            features['hf_peak'] = freqs[hf_idx][np.argmax(psd[hf_idx])]
        else:
            features['hf_peak'] = 0.0

        # 总功率的对数
        features['log_total_power'] = np.log(total_power + 1e-10)
        features['log_lf_power'] = np.log(lf_power + 1e-10)
        features['log_hf_power'] = np.log(hf_power + 1e-10)

        # 频谱熵
        if total_power > 0:
            psd_norm = psd / np.sum(psd)
            features['spectral_entropy'] = -np.sum(psd_norm * np.log(psd_norm + 1e-10))
        else:
            features['spectral_entropy'] = 0.0

        return features
    
    def extract_nonlinear_features(self, rr_intervals: np.ndarray) -> Dict[str, float]:
        """
        提取非线性特征
        
        Parameters:
        -----------
        rr_intervals : np.ndarray
            RR间期序列（毫秒）
            
        Returns:
        --------
        features : dict
            非线性特征字典
        """
        features = {}
        
        if len(rr_intervals) < 10:
            return {
                'sd1': 0.0,
                'sd2': 0.0,
                'sd1_sd2_ratio': 0.0,
                'sample_entropy': 0.0,
                'approximate_entropy': 0.0
            }
        
        # Poincaré plot参数
        rr_n = rr_intervals[:-1]
        rr_n1 = rr_intervals[1:]
        
        # SD1和SD2（Poincaré plot的标准差）
        diff_rr = rr_n1 - rr_n
        features['sd1'] = np.std(diff_rr) / np.sqrt(2)
        features['sd2'] = np.std(rr_n + rr_n1) / np.sqrt(2)
        
        if features['sd2'] > 0:
            features['sd1_sd2_ratio'] = features['sd1'] / features['sd2']
        else:
            features['sd1_sd2_ratio'] = 0.0
        
        # Sample Entropy（简化版）
        features['sample_entropy'] = self._sample_entropy(rr_intervals, m=2, r=0.2)
        
        # Approximate Entropy（简化版）
        features['approximate_entropy'] = self._approximate_entropy(rr_intervals, m=2, r=0.2)

        # DFA (Detrended Fluctuation Analysis) - 简化版
        features['dfa_alpha1'] = self._dfa(rr_intervals, scale_min=4, scale_max=16)
        features['dfa_alpha2'] = self._dfa(rr_intervals, scale_min=16, scale_max=64)

        # 心率加速度和减速度能力
        features['ac'] = self._acceleration_capacity(rr_intervals)
        features['dc'] = self._deceleration_capacity(rr_intervals)

        # 复杂度指数
        features['complexity_index'] = self._complexity_index(rr_intervals)

        return features
    
    def _sample_entropy(self, data: np.ndarray, m: int = 2, r: float = 0.2) -> float:
        """
        计算样本熵（简化实现）
        """
        N = len(data)
        if N < m + 1:
            return 0.0
        
        r_threshold = r * np.std(data)
        
        def _maxdist(xi, xj, m):
            return max([abs(ua - va) for ua, va in zip(xi, xj)])
        
        def _phi(m):
            patterns = np.array([data[i:i + m] for i in range(N - m + 1)])
            C = 0
            for i in range(len(patterns)):
                matches = sum([1 for j in range(len(patterns)) if i != j and _maxdist(patterns[i], patterns[j], m) <= r_threshold])
                if matches > 0:
                    C += matches / (N - m)
            return C / (N - m + 1)
        
        try:
            phi_m = _phi(m)
            phi_m1 = _phi(m + 1)
            if phi_m > 0 and phi_m1 > 0:
                return -np.log(phi_m1 / phi_m)
            else:
                return 0.0
        except:
            return 0.0
    
    def _approximate_entropy(self, data: np.ndarray, m: int = 2, r: float = 0.2) -> float:
        """
        计算近似熵（简化实现）
        """
        N = len(data)
        if N < m + 1:
            return 0.0
        
        r_threshold = r * np.std(data)
        
        def _phi(m):
            patterns = np.array([data[i:i + m] for i in range(N - m + 1)])
            phi = 0
            for i in range(len(patterns)):
                matches = sum([1 for j in range(len(patterns)) if i != j and np.max(np.abs(patterns[i] - patterns[j])) <= r_threshold])
                if matches > 0:
                    phi += np.log(matches / (N - m + 1))
            return phi / (N - m + 1)
        
        try:
            phi_m = _phi(m)
            phi_m1 = _phi(m + 1)
            return phi_m - phi_m1
        except:
            return 0.0

    def _dfa(self, data: np.ndarray, scale_min: int = 4, scale_max: int = 16) -> float:
        """
        去趋势波动分析 (Detrended Fluctuation Analysis)
        简化实现，计算短期或长期的DFA指数
        """
        N = len(data)
        if N < scale_max:
            return 0.0

        try:
            # 计算累积和
            y = np.cumsum(data - np.mean(data))

            # 在不同尺度上计算波动
            scales = np.arange(scale_min, min(scale_max, N // 4), 2)
            fluctuations = []

            for scale in scales:
                # 将数据分段
                n_segments = N // scale
                if n_segments < 1:
                    continue

                F_n = 0
                for i in range(n_segments):
                    segment = y[i * scale:(i + 1) * scale]
                    # 线性拟合
                    x = np.arange(len(segment))
                    coeffs = np.polyfit(x, segment, 1)
                    fit = np.polyval(coeffs, x)
                    # 计算波动
                    F_n += np.sum((segment - fit) ** 2)

                F_n = np.sqrt(F_n / (n_segments * scale))
                fluctuations.append(F_n)

            if len(fluctuations) < 2:
                return 0.0

            # 对log(F(n))和log(n)进行线性拟合，斜率即为DFA指数
            log_scales = np.log(scales[:len(fluctuations)])
            log_fluctuations = np.log(fluctuations)
            alpha = np.polyfit(log_scales, log_fluctuations, 1)[0]

            return float(alpha)
        except:
            return 0.0

    def _acceleration_capacity(self, rr_intervals: np.ndarray) -> float:
        """
        计算加速度能力 (Acceleration Capacity)
        衡量心率加速的能力
        """
        if len(rr_intervals) < 5:
            return 0.0

        try:
            # 计算相位整流信号
            X = []
            for i in range(2, len(rr_intervals) - 2):
                # 取当前点及其前后各2个点
                anchor = rr_intervals[i]
                neighbors = [rr_intervals[i - 2], rr_intervals[i - 1],
                           rr_intervals[i + 1], rr_intervals[i + 2]]
                # 加速度：RR间期减小
                if anchor < np.mean(neighbors):
                    X.append(anchor)

            if len(X) == 0:
                return 0.0

            return float(np.mean(X))
        except:
            return 0.0

    def _deceleration_capacity(self, rr_intervals: np.ndarray) -> float:
        """
        计算减速度能力 (Deceleration Capacity)
        衡量心率减速的能力
        """
        if len(rr_intervals) < 5:
            return 0.0

        try:
            # 计算相位整流信号
            X = []
            for i in range(2, len(rr_intervals) - 2):
                # 取当前点及其前后各2个点
                anchor = rr_intervals[i]
                neighbors = [rr_intervals[i - 2], rr_intervals[i - 1],
                           rr_intervals[i + 1], rr_intervals[i + 2]]
                # 减速度：RR间期增大
                if anchor > np.mean(neighbors):
                    X.append(anchor)

            if len(X) == 0:
                return 0.0

            return float(np.mean(X))
        except:
            return 0.0

    def _complexity_index(self, rr_intervals: np.ndarray) -> float:
        """
        计算复杂度指数
        基于RR间期序列的变化模式
        """
        if len(rr_intervals) < 10:
            return 0.0

        try:
            # 计算连续差值
            diff = np.diff(rr_intervals)

            # 统计符号变化次数（方向改变）
            sign_changes = 0
            for i in range(len(diff) - 1):
                if diff[i] * diff[i + 1] < 0:  # 符号相反
                    sign_changes += 1

            # 复杂度指数：符号变化次数与总长度的比值
            complexity = sign_changes / (len(diff) - 1) if len(diff) > 1 else 0.0

            return float(complexity)
        except:
            return 0.0

    def extract_clinical_features(self, subject_metadata: Dict) -> Dict[str, float]:
        """
        提取临床特征
        
        Parameters:
        -----------
        subject_metadata : dict
            受试者元数据（年龄、性别、BMI等）
            
        Returns:
        --------
        features : dict
            临床特征字典
        """
        features = {}
        
        # 基本人口学特征
        features['age'] = subject_metadata.get('Age_years', 0)
        features['height_cm'] = subject_metadata.get('Height_cm', 0)
        features['weight_kg'] = subject_metadata.get('Weight_kg', 0)
        features['bmi'] = subject_metadata.get('BMI', 0)
        
        # 性别编码（M=1, F=0）
        gender = subject_metadata.get('Gender', 'M')
        features['gender_male'] = 1.0 if gender == 'M' else 0.0
        
        return features
    
    def extract_all(self, file_path: str, use_existing_rpeaks: bool = True,
                   extract_hrv: bool = True, extract_clinical: bool = True,
                   subject_metadata: Optional[Dict] = None) -> Dict:
        """
        提取所有特征
        
        Parameters:
        -----------
        file_path : str
            HDF5文件路径
        use_existing_rpeaks : bool
            是否使用已有R波标注
        extract_hrv : bool
            是否提取HRV特征
        extract_clinical : bool
            是否提取临床特征
        subject_metadata : dict, optional
            受试者元数据
            
        Returns:
        --------
        features : dict
            所有特征的字典
        """
        import logging
        logger = logging.getLogger(__name__)
        
        all_features = {}
        
        try:
            # 1. 数据预处理，获取RR间期
            logger.info(f"开始处理文件: {file_path}")
            processed_data = self.processor.process_file(file_path, use_existing_rpeaks)
            rr_intervals = processed_data['rr_intervals']
            
            logger.info(f"提取到 {len(rr_intervals)} 个RR间期")
            
            if len(rr_intervals) == 0:
                raise ValueError(f"未能从文件 {file_path} 中提取到RR间期，请检查文件格式是否正确")
            
            # 2. 提取HRV特征
            if extract_hrv:
                if len(rr_intervals) <= 5:
                    logger.warning(f"RR间期数量过少（{len(rr_intervals)}），可能影响特征提取质量")
                    # 即使数量少也尝试提取，但使用更宽松的条件
                
                # 提取时域特征（即使RR间期少也提取基本特征）
                time_features = self.extract_time_domain_features(rr_intervals)
                all_features.update(time_features)
                
                # 频域和非线性特征需要更多数据
                if len(rr_intervals) > 5:
                    freq_features = self.extract_frequency_domain_features(rr_intervals)
                    nonlinear_features = self.extract_nonlinear_features(rr_intervals)
                    all_features.update(freq_features)
                    all_features.update(nonlinear_features)
                else:
                    logger.warning(f"RR间期数量过少（{len(rr_intervals)}），跳过频域和非线性特征提取")
                    # 为缺失的特征设置默认值
                    all_features.update({
                        'total_power': 0.0,
                        'vlf_power': 0.0,
                        'lf_power': 0.0,
                        'hf_power': 0.0,
                        'lf_hf_ratio': 0.0,
                        'sd1': 0.0,
                        'sd2': 0.0,
                        'sd1_sd2_ratio': 0.0,
                        'sample_entropy': 0.0,
                        'approximate_entropy': 0.0
                    })
            else:
                logger.info("跳过HRV特征提取")
            
            # 3. 提取临床特征
            if extract_clinical:
                if subject_metadata:
                    clinical_features = self.extract_clinical_features(subject_metadata)
                    all_features.update(clinical_features)
                    logger.info("已提取临床特征")
                else:
                    logger.warning("请求提取临床特征但未提供subject_metadata，跳过临床特征提取")
            else:
                logger.info("跳过临床特征提取")
            
            logger.info(f"特征提取完成，共提取 {len(all_features)} 个特征")
            
            if len(all_features) == 0:
                raise ValueError("未能提取到任何特征，请检查文件格式和提取参数")
            
        except Exception as e:
            logger.error(f"特征提取失败: {str(e)}")
            raise
        
        return all_features


