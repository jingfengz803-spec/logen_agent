"""
用户数据访问层
"""

import secrets
from datetime import datetime
from typing import Optional, List
from database import db
from models.db import User, OperationLog
from core.logger import get_logger
from core.security import PasswordHandler

logger = get_logger("dao:user")


class UserDAO:
    """用户数据访问对象"""

    @staticmethod
    def create_user(username: str, role: str = "user") -> User:
        """
        创建新用户（无密码，仅 API Key）

        Args:
            username: 用户名

        Returns:
            创建的用户对象
        """
        import uuid
        user_id = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
        api_key = f"key-{secrets.token_urlsafe(32)}"

        sql = """
            INSERT INTO users (user_id, username, api_key, role)
            VALUES (%s, %s, %s, %s)
        """
        db.execute(sql, (user_id, username, api_key, role))

        # 记录操作日志
        UserDAO._log_operation(user_id, "create_user", "user", user_id,
                              {"username": username, "role": role})

        logger.info(f"创建用户: {username} ({user_id}), 角色: {role}")
        return User(
            user_id=user_id,
            username=username,
            api_key=api_key,
            role=role
        )

    @staticmethod
    def register(username: str, password: str, role: str = "user") -> User:
        """
        注册新用户（用户名 + 密码）

        Args:
            username: 用户名
            password: 明文密码
            role: 角色（默认为 user）

        Returns:
            创建的用户对象（包含 API Key）

        Raises:
            ValueError: 用户名已存在
        """
        # 检查用户名是否已存在
        existing = UserDAO.get_by_username(username)
        if existing:
            raise ValueError(f"用户名 '{username}' 已存在")

        import uuid
        user_id = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
        password_hash = PasswordHandler.hash(password)
        api_key = f"key-{secrets.token_urlsafe(32)}"

        sql = """
            INSERT INTO users (user_id, username, password_hash, api_key, role)
            VALUES (%s, %s, %s, %s, %s)
        """
        db.execute(sql, (user_id, username, password_hash, api_key, role))

        # 记录操作日志
        UserDAO._log_operation(user_id, "register", "user", user_id,
                              {"username": username, "role": role})

        logger.info(f"用户注册: {username} ({user_id}), 角色: {role}")
        return User(
            user_id=user_id,
            username=username,
            password_hash=password_hash,
            api_key=api_key,
            role=role
        )

    @staticmethod
    def login(username: str, password: str) -> Optional[User]:
        """
        用户登录验证

        Args:
            username: 用户名
            password: 明文密码

        Returns:
            用户对象（包含 API Key），验证失败返回 None
        """
        user = UserDAO.get_by_username(username)
        if not user:
            logger.warning(f"登录失败: 用户不存在 - {username}")
            return None

        if not user.password_hash:
            logger.warning(f"登录失败: 用户未设置密码 - {username}")
            return None

        if user.status != 1:
            logger.warning(f"登录失败: 用户已被禁用 - {username}")
            return None

        if not PasswordHandler.verify(password, user.password_hash):
            logger.warning(f"登录失败: 密码错误 - {username}, 输入密码长度: {len(password)}, 存储哈希: {user.password_hash[:20]}...")
            return None

        # 记录登录日志
        UserDAO._log_operation(user.user_id, "login", "user", user.user_id)

        logger.info(f"用户登录成功: {username} ({user.user_id})")
        return user

    @staticmethod
    def get_by_api_key(api_key: str) -> Optional[User]:
        """通过 API Key 获取用户"""
        sql = """
            SELECT id, user_id, username, password_hash, api_key, role, status, created_at, updated_at
            FROM users
            WHERE api_key = %s AND status = 1
        """
        row = db.fetch_one(sql, (api_key,), skip_user_filter=True)
        if row:
            return User(**row)
        return None

    @staticmethod
    def get_by_username(username: str) -> Optional[User]:
        """通过用户名获取用户"""
        sql = """
            SELECT id, user_id, username, password_hash, api_key, role, status, created_at, updated_at
            FROM users
            WHERE username = %s
        """
        row = db.fetch_one(sql, (username,), skip_user_filter=True)
        if row:
            return User(**row)
        return None

    @staticmethod
    def get_by_user_id(user_id: str) -> Optional[User]:
        """通过 user_id 获取用户"""
        sql = """
            SELECT id, user_id, username, password_hash, api_key, role, status, created_at, updated_at
            FROM users
            WHERE user_id = %s
        """
        row = db.fetch_one(sql, (user_id,), skip_user_filter=True)
        if row:
            return User(**row)
        return None

    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        """通过数据库 ID 获取用户"""
        sql = """
            SELECT id, user_id, username, password_hash, api_key, role, status, created_at, updated_at
            FROM users
            WHERE id = %s
        """
        row = db.fetch_one(sql, (user_id,), skip_user_filter=True)
        if row:
            return User(**row)
        return None

    @staticmethod
    def list_users(limit: int = 100, offset: int = 0) -> List[dict]:
        """获取用户列表"""
        sql = """
            SELECT id, user_id, username,
                   CONCAT(LEFT(api_key, 8), '...') as api_key_preview,
                   status, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        rows = db.fetch_all(sql, (limit, offset), skip_user_filter=True)
        return rows

    @staticmethod
    def update_status(user_id: str, status: int) -> bool:
        """更新用户状态"""
        sql = "UPDATE users SET status = %s WHERE user_id = %s"
        affected = db.execute(sql, (status, user_id))
        if affected > 0:
            UserDAO._log_operation(user_id, "update_status", "user", user_id,
                                  {"status": status})
        return affected > 0

    @staticmethod
    def regenerate_api_key(user_id: str) -> Optional[str]:
        """重新生成 API Key"""
        new_api_key = f"key-{secrets.token_urlsafe(32)}"
        sql = "UPDATE users SET api_key = %s WHERE user_id = %s"
        affected = db.execute(sql, (new_api_key, user_id))
        if affected > 0:
            UserDAO._log_operation(user_id, "regenerate_key", "user", user_id)
            return new_api_key
        return None

    @staticmethod
    def _log_operation(user_id: str, operation: str, resource_type: str,
                       resource_id: str, details: dict = None):
        """记录操作日志"""
        sql = """
            INSERT INTO operation_logs (user_id, operation, resource_type, resource_id, details)
            VALUES (%s, %s, %s, %s, %s)
        """
        try:
            import json
            # 获取数据库 ID
            db_user_id = None
            if user_id:
                user = UserDAO.get_by_user_id(user_id)
                if user:
                    db_user_id = user.id
            db.execute(sql, (db_user_id, operation, resource_type, resource_id,
                           json.dumps(details) if details else None))
        except Exception as e:
            logger.warning(f"记录操作日志失败: {e}")

    @staticmethod
    def get_operation_logs(user_id: str = None, limit: int = 100) -> List[dict]:
        """获取操作日志"""
        if user_id:
            sql = """
                SELECT * FROM operation_logs
                WHERE user_id = (SELECT id FROM users WHERE user_id = %s)
                ORDER BY created_at DESC
                LIMIT %s
            """
            # 先获取数据库 ID
            user = UserDAO.get_by_user_id(user_id)
            if user:
                sql = """
                    SELECT l.*, u.username
                    FROM operation_logs l
                    LEFT JOIN users u ON l.user_id = u.id
                    WHERE l.user_id = %s
                    ORDER BY l.created_at DESC
                    LIMIT %s
                """
                rows = db.fetch_all(sql, (user.id, limit), skip_user_filter=True)
                return rows
        else:
            sql = """
                SELECT l.*, u.username
                FROM operation_logs l
                LEFT JOIN users u ON l.user_id = u.id
                ORDER BY l.created_at DESC
                LIMIT %s
            """
            rows = db.fetch_all(sql, (limit,), skip_user_filter=True)
        return []

    @staticmethod
    def get_user_stats(user_id: str) -> dict:
        """获取用户统计信息"""
        # 先获取数据库 ID
        user = UserDAO.get_by_user_id(user_id)
        if not user:
            return {}

        sql = """
            SELECT
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_tasks,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_tasks
            FROM tasks
            WHERE user_id = %s
        """
        row = db.fetch_one(sql, (user.id,), skip_user_filter=True)
        return row or {}

    @staticmethod
    def ensure_default_users():
        """确保默认测试用户存在"""
        default_users = [
            {"user_id": "user_test_001", "username": "测试用户1", "api_key": "test-key-123456"},
            {"user_id": "user_test_002", "username": "测试用户2", "api_key": "test-key-789012"},
        ]

        for user_data in default_users:
            existing = UserDAO.get_by_user_id(user_data["user_id"])
            if not existing:
                sql = """
                    INSERT INTO users (user_id, username, api_key)
                    VALUES (%s, %s, %s)
                """
                try:
                    db.execute(sql, (user_data["user_id"], user_data["username"], user_data["api_key"]))
                    logger.info(f"创建默认用户: {user_data['username']}")
                except Exception as e:
                    logger.warning(f"创建默认用户失败: {e}")
