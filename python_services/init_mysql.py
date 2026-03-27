"""
MySQL 数据库初始化脚本
运行此脚本创建数据库和表结构
"""

import pymysql
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def init_mysql(
    host: str = "localhost",
    port: int = 3306,
    user: str = "root",
    password: str = "",
    database: str = "logen_agent"
):
    """
    初始化 MySQL 数据库

    Args:
        host: 数据库地址
        port: 端口
        user: 用户名
        password: 密码
        database: 数据库名
    """
    print(f"🔧 正在连接 MySQL: {host}:{port}")

    try:
        # 先连接 MySQL 服务器（不指定数据库）
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4'
        )
        cursor = conn.cursor()

        # 创建数据库（如果不存在）
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✅ 数据库 `{database}` 已就绪")

        # 切换到目标数据库
        conn.select_db(database)

        # 创建表
        from models.db import CREATE_TABLES_SQL

        statements = [s.strip() for s in CREATE_TABLES_SQL.split(';') if s.strip()]

        for statement in statements:
            cursor.execute(statement)

        print(f"✅ 数据表创建完成")

        # 创建默认测试用户
        print("\n📝 创建默认测试用户...")
        cursor.execute("""
            INSERT IGNORE INTO users (user_id, username, api_key)
            VALUES ('user_test_001', '测试用户1', 'test-key-123456')
        """)
        cursor.execute("""
            INSERT IGNORE INTO users (user_id, username, api_key)
            VALUES ('user_test_002', '测试用户2', 'test-key-789012')
        """)
        print("✅ 默认用户创建完成")
        print("   - 测试用户1: test-key-123456")
        print("   - 测试用户2: test-key-789012")

        conn.commit()
        cursor.close()
        conn.close()

        print("\n" + "="*50)
        print("🎉 MySQL 初始化完成！")
        print("="*50)
        print(f"\n请在 .env 文件中添加以下配置：")
        print(f"DB_HOST={host}")
        print(f"DB_PORT={port}")
        print(f"DB_USER={user}")
        print(f"DB_PASSWORD={password}")
        print(f"DB_NAME={database}")
        print("\n然后重启服务即可使用 MySQL 存储数据。")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        print("\n请检查：")
        print("1. MySQL 是否已安装并运行")
        print("2. 用户名和密码是否正确")
        print("3. 用户是否有创建数据库的权限")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="初始化 MySQL 数据库")
    parser.add_argument("--host", default="localhost", help="数据库地址")
    parser.add_argument("--port", type=int, default=3306, help="端口")
    parser.add_argument("--user", default="root", help="用户名")
    parser.add_argument("--password", default="", help="密码")
    parser.add_argument("--database", default="logen_agent", help="数据库名")

    args = parser.parse_args()

    # 如果没有提供密码，提示输入
    password = args.password
    if not password:
        password = input("请输入 MySQL 密码: ")

    init_mysql(
        host=args.host,
        port=args.port,
        user=args.user,
        password=password,
        database=args.database
    )
