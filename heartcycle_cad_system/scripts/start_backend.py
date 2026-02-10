"""
启动后端服务脚本
自动查找可用端口
"""
import sys
import socket
from pathlib import Path

import uvicorn

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_dir))


def is_port_available(port):
    """检查端口是否可用（同时检查0.0.0.0和127.0.0.1）"""
    # 检查 0.0.0.0（所有接口）
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', port))
    except OSError:
        return False

    # 检查 127.0.0.1（本地回环）
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
    except OSError:
        return False

    return True


def find_available_port(start_port=8000, max_attempts=10):
    """查找可用端口"""
    for port in range(start_port, start_port + max_attempts):
        if is_port_available(port):
            return port
    return None


def main():
    """启动后端服务"""
    # 查找可用端口
    port = find_available_port(8000)

    if port is None:
        print("错误: 无法找到可用端口 (尝试了 8000-8009)")
        print("请手动停止占用端口的进程或使用其他端口范围")
        sys.exit(1)

    if port != 8000:
        print(f"警告: 端口 8000 被占用，使用端口 {port} 启动服务")

    print(f"启动后端服务在端口 {port}...")
    print(f"API文档: http://localhost:{port}/docs")
    print(f"健康检查: http://localhost:{port}/health")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )



if __name__ == "__main__":
    main()


