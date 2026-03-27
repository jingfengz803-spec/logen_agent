"""
数据库迁移：添加 role 列到 users 表
执行方式: python migrations/add_role_column.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import db, init_database
from core.logger import get_logger

logger = get_logger("migration")


def migrate():
    """执行迁移"""
    # 先初始化数据库连接
    logger.info("正在连接数据库...")
    init_database()

    if not db.is_connected():
        logger.error("数据库未连接，请检查配置")
        logger.error("请确认：")
        logger.error("  1. MySQL 服务已启动")
        logger.error("  2. .env 文件中数据库配置正确（DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME）")
        return False

    try:
        # 检查 role 列是否已存在
        check_sql = """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'users'
            AND COLUMN_NAME = 'role'
            AND TABLE_SCHEMA = DATABASE()
        """
        result = db.fetch_one(check_sql)

        if result:
            logger.info("role 列已存在，跳过迁移")
            return True

        # 添加 role 列
        alter_sql = """
            ALTER TABLE users
            ADD COLUMN role VARCHAR(20) DEFAULT 'user' COMMENT '角色 user/admin'
            AFTER api_key
        """
        db.execute(alter_sql)
        logger.info("✅ 成功添加 role 列到 users 表")

        # 将现有测试用户设置为 admin（可选）
        update_sql = """
            UPDATE users
            SET role = 'admin'
            WHERE user_id IN ('user_test_001', 'user_test_002')
        """
        db.execute(update_sql)
        logger.info("✅ 已将测试用户设置为 admin 角色")

        return True

    except Exception as e:
        logger.error(f"迁移失败: {e}")
        return False


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
