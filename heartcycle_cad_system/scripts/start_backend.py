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
    """检查端口是否可用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', port))
            return True
    except OSError:
        return False


def find_available_port(start_port=8001, max_attempts=9):
    """查找可用端口（从8009倒序到8001）"""
    for port in range(start_port + max_attempts - 1, start_port - 1, -1):
        if is_port_available(port):
            return port
    return None


def main():
    """启动后端服务"""
    # 查找可用端口（从8009倒序到8001）
    # port = find_available_port(8001)
    port = 8009
    if port is None:
        print("错误: 无法找到可用端口 (尝试了 8009-8001)")
        print("请手动停止占用端口的进程或使用其他端口范围")
        sys.exit(1)

    if port != 8009:
        print(f"警告: 端口 8009 被占用，使用端口 {port} 启动服务")

    print(f"启动后端服务在端口 {port}...")
    print(f"API文档: http://localhost:{port}/docs")
    print(f"健康检查: http://localhost:{port}/health")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # 禁用reload避免子进程环境问题
        log_level="info"
    )



if __name__ == "__main__":
    main()


