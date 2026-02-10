"""
初始化数据库表
如果表已存在则跳过，如果不存在则创建
"""
import sys
import os
from pathlib import Path

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(project_root))

# 设置工作目录
os.chdir(str(backend_dir))

from app.db import init_db, check_db_connection
from app.core.config import settings
from app.core.logger import logger

def main():
    print("="*60)
    print("初始化数据库表")
    print("="*60)
    print()
    
    # 检查连接
    print("1. 检查数据库连接...")
    print(f"   数据库URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    
    if not check_db_connection():
        print("   ✗ 数据库连接失败")
        print()
        print("请检查：")
        print("  - MySQL服务是否运行")
        print("  - .env文件中的DATABASE_URL是否正确")
        print("  - 数据库是否已创建")
        return False
    
    print("   ✓ 数据库连接成功")
    print()
    
    # 初始化表
    print("2. 创建数据库表...")
    try:
        init_db()
        print("   ✓ 数据库表创建成功")
        print()
        print("表 'training_tasks' 已创建，包含以下字段：")
        print("  - task_id (主键)")
        print("  - status, progress, message")
        print("  - current_file, total_files, processed_files")
        print("  - result, error")
        print("  - created_at, updated_at, expires_at")
        return True
    except Exception as e:
        print(f"   ✗ 创建表失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print()
            print("="*60)
            print("初始化完成！")
            print("="*60)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

