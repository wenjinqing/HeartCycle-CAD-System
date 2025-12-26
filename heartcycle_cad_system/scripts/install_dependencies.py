"""
安装依赖包脚本
支持Python 3.8+
"""
import subprocess
import sys
import os


def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("[ERROR] 需要Python 3.8或更高版本")
        print(f"当前版本: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"[OK] Python版本检查通过: {version.major}.{version.minor}.{version.micro}")
    return True


def install_package(package):
    """安装单个包"""
    try:
        print(f"正在安装: {package}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"[OK] {package} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] {package} 安装失败: {e}")
        return False


def install_from_requirements():
    """从requirements.txt安装依赖"""
    requirements_file = os.path.join(
        os.path.dirname(__file__), '..', 'requirements.txt'
    )
    
    if not os.path.exists(requirements_file):
        print(f"[ERROR] 找不到requirements.txt: {requirements_file}")
        return False
    
    print(f"\n从 {requirements_file} 安装依赖...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", requirements_file
        ])
        print("[OK] 所有依赖安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] 依赖安装失败: {e}")
        return False


def install_core_dependencies():
    """安装核心依赖（用于测试）"""
    core_packages = [
        "numpy>=1.19.0",
        "pandas>=1.3.0",
        "scipy>=1.7.0",
        "scikit-learn>=1.0.0",
        "joblib>=1.0.0",
        "pydantic>=1.10.0",
        "pydantic-settings>=2.0.0",
    ]
    
    print("\n安装核心依赖...")
    success_count = 0
    
    for package in core_packages:
        if install_package(package):
            success_count += 1
    
    print(f"\n核心依赖安装完成: {success_count}/{len(core_packages)} 成功")
    return success_count == len(core_packages)


def main():
    """主函数"""
    print("=" * 60)
    print("HeartCycle CAD System - 依赖安装脚本")
    print("=" * 60)
    
    # 检查Python版本
    if not check_python_version():
        sys.exit(1)
    
    # 升级pip
    print("\n升级pip...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--upgrade", "pip"
        ])
        print("[OK] pip升级成功")
    except:
        print("[WARN] pip升级失败，继续安装...")
    
    # 询问安装方式
    print("\n请选择安装方式:")
    print("1. 安装所有依赖（完整安装）")
    print("2. 仅安装核心依赖（用于测试）")
    
    choice = input("\n请输入选择 (1/2，默认为1): ").strip()
    
    if choice == "2":
        success = install_core_dependencies()
    else:
        success = install_from_requirements()
    
    if success:
        print("\n" + "=" * 60)
        print("[OK] 依赖安装完成！")
        print("=" * 60)
        print("\n可以运行以下命令启动后端:")
        print("  python scripts/start_backend.py")
        return 0
    else:
        print("\n" + "=" * 60)
        print("[WARN] 部分依赖安装失败，请检查错误信息")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

