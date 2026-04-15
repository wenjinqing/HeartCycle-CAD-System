"""
系统监控服务
"""
import psutil
import time
from datetime import datetime
from typing import Dict, List
from collections import deque
import logging

logger = logging.getLogger(__name__)


class SystemMonitor:
    """系统监控服务"""

    def __init__(self, history_size: int = 100):
        """
        初始化监控服务

        Parameters:
        -----------
        history_size : int
            保留的历史记录数量
        """
        self.history_size = history_size
        self.cpu_history = deque(maxlen=history_size)
        self.memory_history = deque(maxlen=history_size)
        self.disk_history = deque(maxlen=history_size)
        self.start_time = time.time()

    def get_cpu_info(self) -> Dict:
        """获取CPU信息"""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()

        info = {
            'percent': cpu_percent,
            'count': cpu_count,
            'frequency': {
                'current': cpu_freq.current if cpu_freq else None,
                'min': cpu_freq.min if cpu_freq else None,
                'max': cpu_freq.max if cpu_freq else None
            }
        }

        # 记录历史
        self.cpu_history.append({
            'timestamp': datetime.now().isoformat(),
            'percent': cpu_percent
        })

        return info

    def get_memory_info(self) -> Dict:
        """获取内存信息"""
        memory = psutil.virtual_memory()

        info = {
            'total_gb': round(memory.total / (1024**3), 2),
            'available_gb': round(memory.available / (1024**3), 2),
            'used_gb': round(memory.used / (1024**3), 2),
            'percent': memory.percent,
            'free_gb': round(memory.free / (1024**3), 2)
        }

        # 记录历史
        self.memory_history.append({
            'timestamp': datetime.now().isoformat(),
            'percent': memory.percent,
            'used_gb': info['used_gb']
        })

        return info

    def get_disk_info(self) -> Dict:
        """获取磁盘信息"""
        disk = psutil.disk_usage('.')

        info = {
            'total_gb': round(disk.total / (1024**3), 2),
            'used_gb': round(disk.used / (1024**3), 2),
            'free_gb': round(disk.free / (1024**3), 2),
            'percent': disk.percent
        }

        # 记录历史
        self.disk_history.append({
            'timestamp': datetime.now().isoformat(),
            'percent': disk.percent,
            'used_gb': info['used_gb']
        })

        return info

    def get_network_info(self) -> Dict:
        """获取网络信息"""
        net_io = psutil.net_io_counters()

        return {
            'bytes_sent_mb': round(net_io.bytes_sent / (1024**2), 2),
            'bytes_recv_mb': round(net_io.bytes_recv / (1024**2), 2),
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'errors_in': net_io.errin,
            'errors_out': net_io.errout,
            'drops_in': net_io.dropin,
            'drops_out': net_io.dropout
        }

    def get_process_info(self) -> Dict:
        """获取当前进程信息"""
        process = psutil.Process()

        with process.oneshot():
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_info = process.memory_info()
            num_threads = process.num_threads()
            num_fds = process.num_fds() if hasattr(process, 'num_fds') else None

        return {
            'pid': process.pid,
            'cpu_percent': cpu_percent,
            'memory_mb': round(memory_info.rss / (1024**2), 2),
            'num_threads': num_threads,
            'num_fds': num_fds,
            'status': process.status()
        }

    def get_uptime(self) -> Dict:
        """获取运行时间"""
        uptime_seconds = time.time() - self.start_time

        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)

        return {
            'seconds': int(uptime_seconds),
            'formatted': f"{days}天 {hours}小时 {minutes}分钟 {seconds}秒",
            'start_time': datetime.fromtimestamp(self.start_time).isoformat()
        }

    def get_system_status(self) -> Dict:
        """获取系统整体状态"""
        cpu_info = self.get_cpu_info()
        memory_info = self.get_memory_info()
        disk_info = self.get_disk_info()

        # 判断系统状态
        status = 'healthy'
        warnings = []

        if cpu_info['percent'] > 80:
            status = 'warning'
            warnings.append('CPU使用率过高')

        if memory_info['percent'] > 85:
            status = 'warning'
            warnings.append('内存使用率过高')

        if disk_info['percent'] > 90:
            status = 'critical'
            warnings.append('磁盘空间不足')

        return {
            'status': status,
            'warnings': warnings,
            'cpu': cpu_info,
            'memory': memory_info,
            'disk': disk_info,
            'network': self.get_network_info(),
            'process': self.get_process_info(),
            'uptime': self.get_uptime(),
            'timestamp': datetime.now().isoformat()
        }

    def get_history(self) -> Dict:
        """获取历史监控数据"""
        return {
            'cpu': list(self.cpu_history),
            'memory': list(self.memory_history),
            'disk': list(self.disk_history)
        }

    def get_alerts(self) -> List[Dict]:
        """获取告警信息"""
        alerts = []

        # CPU告警
        cpu_percent = psutil.cpu_percent(interval=0.1)
        if cpu_percent > 90:
            alerts.append({
                'level': 'critical',
                'type': 'cpu',
                'message': f'CPU使用率过高: {cpu_percent}%',
                'value': cpu_percent,
                'threshold': 90,
                'timestamp': datetime.now().isoformat()
            })
        elif cpu_percent > 80:
            alerts.append({
                'level': 'warning',
                'type': 'cpu',
                'message': f'CPU使用率较高: {cpu_percent}%',
                'value': cpu_percent,
                'threshold': 80,
                'timestamp': datetime.now().isoformat()
            })

        # 内存告警
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            alerts.append({
                'level': 'critical',
                'type': 'memory',
                'message': f'内存使用率过高: {memory.percent}%',
                'value': memory.percent,
                'threshold': 90,
                'timestamp': datetime.now().isoformat()
            })
        elif memory.percent > 85:
            alerts.append({
                'level': 'warning',
                'type': 'memory',
                'message': f'内存使用率较高: {memory.percent}%',
                'value': memory.percent,
                'threshold': 85,
                'timestamp': datetime.now().isoformat()
            })

        # 磁盘告警
        disk = psutil.disk_usage('.')
        if disk.percent > 95:
            alerts.append({
                'level': 'critical',
                'type': 'disk',
                'message': f'磁盘空间严重不足: {disk.percent}%',
                'value': disk.percent,
                'threshold': 95,
                'timestamp': datetime.now().isoformat()
            })
        elif disk.percent > 90:
            alerts.append({
                'level': 'warning',
                'type': 'disk',
                'message': f'磁盘空间不足: {disk.percent}%',
                'value': disk.percent,
                'threshold': 90,
                'timestamp': datetime.now().isoformat()
            })

        return alerts


# 全局监控实例
system_monitor = SystemMonitor()


def get_system_monitor() -> SystemMonitor:
    """获取全局监控实例"""
    return system_monitor
