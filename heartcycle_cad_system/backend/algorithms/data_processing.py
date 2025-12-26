"""
数据预处理模块
- HDF5数据读取
- ECG信号滤波
- R波检测
- RR间期计算
"""
import h5py
import numpy as np
import pandas as pd
from scipy import signal as sg
from typing import Tuple, Optional, Dict
import sys
import os

# 添加heartcycle目录到路径（用于导入pan_tompkins）
sys.path.append(os.path.join(os.path.dirname(__file__), '../../heartcycle'))
try:
    from pan_tompkins import Pan_Tompkins_QRS, heart_rate
except ImportError:
    print("警告: 无法导入pan_tompkins模块，R波检测功能可能受限")


class ECGProcessor:
    """ECG信号处理器"""
    
    def __init__(self, sampling_rate: int = 200):
        """
        初始化ECG处理器
        
        Parameters:
        -----------
        sampling_rate : int
            采样率 (Hz)，默认200Hz（HeartCycle数据集标准）
        """
        self.sampling_rate = sampling_rate
        self.qrs_detector = None
        
    def load_hdf5_file(self, file_path: str, signal_key: str = '_030') -> Tuple[np.ndarray, np.ndarray]:
        """
        加载HDF5文件中的ECG信号
        
        Parameters:
        -----------
        file_path : str
            HDF5文件路径
        signal_key : str
            信号组ID，'_030'表示Niccomo设备的ECG信号
            
        Returns:
        --------
        ecg_signal : np.ndarray
            ECG信号数据
        time_vector : np.ndarray
            时间向量
        """
        try:
            with h5py.File(file_path, 'r') as f:
                ecg_data = f['measure']['value'][signal_key]['value']['data']['value'][0, :]
                time_data = f['measure']['value'][signal_key]['value']['time']['value'][0, :]
            return ecg_data, time_data
        except Exception as e:
            raise ValueError(f"无法读取HDF5文件 {file_path}: {str(e)}")
    
    def load_rpeaks_from_hdf5(self, file_path: str, rpeaks_key: str = '_032') -> Optional[np.ndarray]:
        """
        从HDF5文件加载已标注的R波位置
        
        Parameters:
        -----------
        file_path : str
            HDF5文件路径
        rpeaks_key : str
            R波位置组ID，'_032'表示Niccomo设备的R波位置
            
        Returns:
        --------
        rpeaks : np.ndarray or None
            R波位置（时间戳），如果不存在则返回None
        """
        try:
            with h5py.File(file_path, 'r') as f:
                if rpeaks_key in f['measure']['value']:
                    rpeaks = f['measure']['value'][rpeaks_key]['value']['data']['value'][0, :]
                    return rpeaks
                return None
        except Exception:
            return None
    
    def bandpass_filter(self, signal: np.ndarray, lowcut: float = 5.0, 
                       highcut: float = 15.0, order: int = 4) -> np.ndarray:
        """
        带通滤波（5-15 Hz用于QRS检测）
        
        Parameters:
        -----------
        signal : np.ndarray
            输入信号
        lowcut : float
            低截止频率 (Hz)
        highcut : float
            高截止频率 (Hz)
        order : int
            滤波器阶数
            
        Returns:
        --------
        filtered_signal : np.ndarray
            滤波后的信号
        """
        nyquist = self.sampling_rate / 2
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = sg.butter(order, [low, high], btype='band')
        filtered = sg.filtfilt(b, a, signal)
        return filtered
    
    def remove_baseline_drift(self, signal: np.ndarray, window_size: int = None) -> np.ndarray:
        """
        去除基线漂移（使用移动平均）
        
        Parameters:
        -----------
        signal : np.ndarray
            输入信号
        window_size : int
            移动平均窗口大小，如果为None则使用采样率的整数倍
            
        Returns:
        --------
        corrected_signal : np.ndarray
            去除基线漂移后的信号
        """
        if window_size is None:
            window_size = int(self.sampling_rate * 0.2)  # 200ms窗口
        
        baseline = sg.savgol_filter(signal, window_size, 3)
        return signal - baseline
    
    def detect_rpeaks_pan_tompkins(self, ecg_signal: np.ndarray, 
                                   time_vector: np.ndarray) -> np.ndarray:
        """
        使用Pan-Tompkins算法检测R波
        
        Parameters:
        -----------
        ecg_signal : np.ndarray
            ECG信号
        time_vector : np.ndarray
            时间向量
            
        Returns:
        --------
        rpeaks : np.ndarray
            R波位置（采样点索引）
        """
        try:
            # 初始化Pan-Tompkins检测器
            if self.qrs_detector is None:
                self.qrs_detector = Pan_Tompkins_QRS(self.sampling_rate)
            
            # 转换为DataFrame格式（pan_tompkins期望的格式）
            ecg_df = pd.DataFrame({
                'TimeStamp': time_vector,
                'ecg': ecg_signal
            })
            
            # 处理信号
            processed_signal = self.qrs_detector.solve(ecg_df)
            
            # 使用heart_rate类检测R波
            hr_detector = heart_rate(ecg_signal, self.sampling_rate)
            hr_detector.m_win = processed_signal
            hr_detector.b_pass = self.bandpass_filter(ecg_signal)
            
            rpeaks = hr_detector.find_r_peaks()
            rpeaks = np.array(rpeaks)
            
            # 过滤掉负值（学习阶段）
            rpeaks = rpeaks[rpeaks > 0]
            
            return rpeaks
            
        except Exception as e:
            raise ValueError(f"R波检测失败: {str(e)}")
    
    def compute_rr_intervals(self, rpeaks: np.ndarray, time_vector: np.ndarray = None) -> np.ndarray:
        """
        计算RR间期序列
        
        Parameters:
        -----------
        rpeaks : np.ndarray
            R波位置（采样点索引或时间戳）
        time_vector : np.ndarray, optional
            时间向量，如果提供则rpeaks为时间戳，否则为采样点索引
            
        Returns:
        --------
        rr_intervals : np.ndarray
            RR间期序列（毫秒）
        """
        if time_vector is not None:
            # rpeaks是时间戳
            rr_intervals = np.diff(rpeaks) * 1000  # 转换为毫秒
        else:
            # rpeaks是采样点索引
            rr_intervals = np.diff(rpeaks) / self.sampling_rate * 1000  # 转换为毫秒
        
        return rr_intervals
    
    def remove_outlier_rr(self, rr_intervals: np.ndarray, 
                         threshold_low: float = 0.3, 
                         threshold_high: float = 2.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        去除异常RR间期
        
        Parameters:
        -----------
        rr_intervals : np.ndarray
            RR间期序列（毫秒）
        threshold_low : float
            低阈值（相对于中位数的倍数）
        threshold_high : float
            高阈值（相对于中位数的倍数）
            
        Returns:
        --------
        cleaned_rr : np.ndarray
            清理后的RR间期序列
        valid_mask : np.ndarray
            有效数据的布尔掩码
        """
        median_rr = np.median(rr_intervals)
        lower_bound = median_rr * threshold_low
        upper_bound = median_rr * threshold_high
        
        valid_mask = (rr_intervals >= lower_bound) & (rr_intervals <= upper_bound)
        cleaned_rr = rr_intervals[valid_mask]
        
        return cleaned_rr, valid_mask
    
    def process_file(self, file_path: str, use_existing_rpeaks: bool = True) -> Dict:
        """
        完整的数据处理流程
        
        Parameters:
        -----------
        file_path : str
            HDF5文件路径
        use_existing_rpeaks : bool
            是否优先使用文件中已有的R波标注
            
        Returns:
        --------
        result : dict
            包含处理结果的字典：
            - ecg_signal: 滤波后的ECG信号
            - time_vector: 时间向量
            - rpeaks: R波位置（采样点索引）
            - rr_intervals: RR间期序列（毫秒）
            - sampling_rate: 采样率
        """
        # 1. 加载ECG信号
        ecg_signal, time_vector = self.load_hdf5_file(file_path)
        
        # 2. 信号预处理
        # 去除基线漂移
        ecg_signal = self.remove_baseline_drift(ecg_signal)
        # 带通滤波
        ecg_signal = self.bandpass_filter(ecg_signal)
        
        # 3. R波检测
        rpeaks = None
        if use_existing_rpeaks:
            # 尝试从文件加载R波位置
            rpeaks_time = self.load_rpeaks_from_hdf5(file_path)
            if rpeaks_time is not None:
                # 将时间戳转换为采样点索引
                rpeaks = np.searchsorted(time_vector, rpeaks_time)
        
        if rpeaks is None or len(rpeaks) == 0:
            # 使用Pan-Tompkins算法检测
            rpeaks = self.detect_rpeaks_pan_tompkins(ecg_signal, time_vector)
        
        # 4. 计算RR间期
        rr_intervals = self.compute_rr_intervals(rpeaks, time_vector=None)
        
        # 5. 去除异常RR间期
        rr_intervals_clean, valid_mask = self.remove_outlier_rr(rr_intervals)
        
        return {
            'ecg_signal': ecg_signal,
            'time_vector': time_vector,
            'rpeaks': rpeaks,
            'rr_intervals': rr_intervals_clean,
            'rr_intervals_raw': rr_intervals,
            'valid_mask': valid_mask,
            'sampling_rate': self.sampling_rate,
            'file_path': file_path
        }


if __name__ == "__main__":
    # 测试代码
    processor = ECGProcessor(sampling_rate=200)
    # 这里需要实际的HDF5文件路径
    # result = processor.process_file("path/to/file.h5")
    # print(f"检测到 {len(result['rpeaks'])} 个R波")
    # print(f"RR间期数量: {len(result['rr_intervals'])}")


