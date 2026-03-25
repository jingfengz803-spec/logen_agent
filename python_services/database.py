"""
数据库连接模块
支持 MySQL 连接池管理
"""

import re
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from typing import Optional, Dict, Any
from core.config import settings
from core.logger import get_logger

logger = get_logger("database")


class Database:
    """数据库连接管理类"""

    _pool = None
    _current_user_id = None
    _current_user_role = None

    # 需要进行用户数据隔离的表
    _ISOLATED_TABLES = {
        "tasks",
        "generated_resources",
        "douyin_fetch_tasks",
        "douyin_videos",
        "operation_logs",
    }

    @classmethod
    def init_pool(cls, config: Dict[str, Any]):
        """
        初始化数据库连接池

        Args:
            config: 数据库配置
                - host: 数据库地址
                - port: 端口
                - user: 用户名
                - password: 密码
                - database: 数据库名
                - pool_size: 连接池大小
        """
        if cls._pool is not None:
            logger.warning("数据库连接池已存在，跳过初始化")
            return

        try:
            # 测试连接
            conn = pymysql.connect(
                host=config.get("host", "localhost"),
                port=config.get("port", 3306),
                user=config.get("user"),
                password=config.get("password"),
                database=config.get("database"),
                cursorclass=DictCursor,
                charset='utf8mb4'
            )
            conn.close()

            logger.info(f"✅ 数据库连接成功: {config.get('host')}:{config.get('port')}/{config.get('database')}")

            # 保存配置供后续使用
            cls._config = config
            cls._pool = True  # 标记已初始化

        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            # 不抛出异常，允许系统降级运行
            cls._pool = None

    # ── 用户上下文管理 ──────────────────────────────────────────

    @classmethod
    def set_current_user(cls, user_db_id: int, role: str = "user"):
        """设置当前请求的用户上下文"""
        cls._current_user_id = user_db_id
        cls._current_user_role = role

    @classmethod
    def clear_current_user(cls):
        """清除当前请求的用户上下文"""
        cls._current_user_id = None
        cls._current_user_role = None

    @classmethod
    def is_admin(cls) -> bool:
        """判断当前用户是否为管理员"""
        return cls._current_user_role == "admin"

    @classmethod
    def get_current_user_id(cls) -> Optional[int]:
        """获取当前用户 ID，未设置时返回 None"""
        return cls._current_user_id

    # ── SQL 用户过滤 ──────────────────────────────────────────

    @classmethod
    def _extract_table_name(cls, sql: str) -> Optional[str]:
        """
        从 SQL 语句中提取主表名。

        支持的写法:
            SELECT ... FROM table
            SELECT ... FROM table AS alias / table alias
            INSERT INTO table
            UPDATE table
            DELETE FROM table
        """
        sql_upper = sql.strip().upper()
        # 尝试匹配 SELECT ... FROM / DELETE FROM / INSERT INTO / UPDATE
        m = re.search(
            r"""(?:FROM|INTO|UPDATE)\s+([`"]?(\w+)[`"]?)""",
            sql_upper,
        )
        if m:
            return m.group(2).lower()
        return None

    @classmethod
    def _apply_user_filter(cls, sql: str, params: Optional[tuple]) -> tuple:
        """
        根据当前用户上下文，在查询中自动追加 user_id 过滤条件。

        Returns:
            (modified_sql, modified_params)
        """
        # 管理员或未设置用户 → 不过滤
        if cls.is_admin() or cls._current_user_id is None:
            return sql, params

        table = cls._extract_table_name(sql)
        if table is None or table not in cls._ISOLATED_TABLES:
            return sql, params

        user_params = params or ()

        sql_upper = sql.rstrip().upper()
        if "WHERE" in sql_upper:
            modified_sql = sql.rstrip() + " AND user_id = %s"
        else:
            modified_sql = sql.rstrip() + " WHERE user_id = %s"

        return modified_sql, user_params + (cls._current_user_id,)

    @classmethod
    def is_connected(cls) -> bool:
        """检查数据库是否已连接"""
        return cls._pool is not None

    @classmethod
    @contextmanager
    def get_connection(cls):
        """
        获取数据库连接（上下文管理器）

        用法:
            with Database.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM users")
        """
        if not cls.is_connected():
            raise RuntimeError("数据库未初始化，请先调用 init_pool()")

        conn = pymysql.connect(
            host=cls._config.get("host", "localhost"),
            port=cls._config.get("port", 3306),
            user=cls._config.get("user"),
            password=cls._config.get("password"),
            database=cls._config.get("database"),
            cursorclass=DictCursor,
            charset='utf8mb4'
        )

        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @classmethod
    def execute(cls, sql: str, params: Optional[tuple] = None) -> int:
        """
        执行 SQL 语句（INSERT/UPDATE/DELETE）

        Args:
            sql: SQL 语句
            params: 参数

        Returns:
            影响的行数
        """
        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.rowcount

    @classmethod
    def fetch_one(cls, sql: str, params: Optional[tuple] = None,
                  *, skip_user_filter: bool = False) -> Optional[Dict]:
        """
        查询单行

        Args:
            sql: SQL 语句
            params: 参数
            skip_user_filter: 是否跳过自动用户过滤（默认 False）

        Returns:
            单行数据或 None
        """
        if not skip_user_filter:
            sql, params = cls._apply_user_filter(sql, params)
        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchone()

    @classmethod
    def fetch_all(cls, sql: str, params: Optional[tuple] = None,
                  *, skip_user_filter: bool = False) -> list:
        """
        查询多行

        Args:
            sql: SQL 语句
            params: 参数
            skip_user_filter: 是否跳过自动用户过滤（默认 False）

        Returns:
            行数据列表
        """
        if not skip_user_filter:
            sql, params = cls._apply_user_filter(sql, params)
        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchall()

    @classmethod
    def insert_return_id(cls, sql: str, params: Optional[tuple] = None) -> int:
        """
        插入并返回自增 ID

        Args:
            sql: SQL 语句
            params: 参数

        Returns:
            新插入行的 ID
        """
        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.lastrowid


# 全局数据库实例
db = Database()


def init_database():
    """初始化数据库连接（从配置读取）"""
    config = {
        "host": settings.get("DB_HOST", "localhost"),
        "port": settings.get("DB_PORT", 3306),
        "user": settings.get("DB_USER", "root"),
        "password": settings.get("DB_PASSWORD", ""),
        "database": settings.get("DB_NAME", "logen_agent"),
    }

    try:
        Database.init_pool(config)
        return True
    except Exception as e:
        logger.warning(f"数据库初始化失败，将使用降级模式: {e}")
        return False
