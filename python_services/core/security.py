"""
安全模块 - JWT认证与鉴权
V1: 简单 API Key 验证（临时方案）
V2: 完整 JWT + Spring Cloud 集成
"""

import jwt
import secrets
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from fastapi import HTTPException, status, Header

from .config import settings


# ==================== V1: 简单 API Key 验证 ====================

class SimpleAuth:
    """V1 简单认证 - API Key 方式
    支持 MySQL（优先）和 JSON（降级）两种存储方式
    """

    # 用户存储文件路径（降级使用）
    USERS_FILE = Path(__file__).parent.parent / "temp" / "users.json"

    # MySQL DAO
    _user_dao = None

    @classmethod
    def _get_user_dao(cls):
        """获取用户 DAO（延迟加载）"""
        if cls._user_dao is None:
            try:
                from dao.user_dao import UserDAO
                from database import db
                if db.is_connected():
                    cls._user_dao = UserDAO
                    from core.logger import get_logger
                    logger = get_logger("security")
                    logger.info("使用 MySQL 存储用户数据")
            except ImportError:
                pass
        return cls._user_dao

    @classmethod
    def _use_database(cls) -> bool:
        """检查是否使用数据库"""
        dao = cls._get_user_dao()
        return dao is not None

    @classmethod
    def _load_users_json(cls) -> Dict[str, Any]:
        """从 JSON 加载用户数据（降级方案）"""
        if not cls.USERS_FILE.exists():
            cls.USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
            # 创建默认测试用户
            default_users = {
                "users": [
                    {
                        "user_id": "user_test_001",
                        "api_key": "test-key-123456",
                        "name": "测试用户1",
                        "created_at": "2026-03-23T00:00:00"
                    },
                    {
                        "user_id": "user_test_002",
                        "api_key": "test-key-789012",
                        "name": "测试用户2",
                        "created_at": "2026-03-23T00:00:00"
                    }
                ]
            }
            with open(cls.USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(default_users, f, ensure_ascii=False, indent=2)
            return default_users

        with open(cls.USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def _save_users_json(cls, data: Dict[str, Any]):
        """保存用户数据到 JSON（降级方案）"""
        with open(cls.USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def verify_api_key(cls, api_key: str) -> Dict[str, Any]:
        """
        验证 API Key

        Args:
            api_key: API Key

        Returns:
            用户信息字典

        Raises:
            HTTPException: API Key 无效
        """
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 API Key，请在请求头中添加 X-API-Key"
            )

        # 优先使用 MySQL
        if cls._use_database():
            user = cls._user_dao.get_by_api_key(api_key)
            if user:
                return {
                    "user_id": user.user_id,
                    "api_key": user.api_key,
                    "name": user.username,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }

        # 降级使用 JSON
        data = cls._load_users_json()
        for user in data.get("users", []):
            if user.get("api_key") == api_key:
                return user

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key"
        )

    @classmethod
    def create_user(cls, name: str, role: str = "user") -> Dict[str, Any]:
        """
        创建新用户并生成 API Key

        Args:
            name: 用户名称
            role: 角色（默认为 user）

        Returns:
            包含 user_id 和 api_key 的字典
        """
        # 优先使用 MySQL
        if cls._use_database():
            user = cls._user_dao.create_user(name, role=role)
            return {
                "user_id": user.user_id,
                "api_key": user.api_key,
                "name": user.username,
                "role": user.role
            }

        # 降级使用 JSON
        data = cls._load_users_json()

        # 生成唯一 ID 和 API Key
        user_id = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
        api_key = f"key-{secrets.token_urlsafe(16)}"

        new_user = {
            "user_id": user_id,
            "api_key": api_key,
            "name": name,
            "created_at": datetime.now().isoformat()
        }

        data["users"].append(new_user)
        cls._save_users_json(data)

        return {
            "user_id": user_id,
            "api_key": api_key,
            "name": name
        }

    @classmethod
    def list_users(cls) -> list:
        """列出所有用户（不暴露 API Key）"""
        # 优先使用 MySQL
        if cls._use_database():
            return cls._user_dao.list_users()

        # 降级使用 JSON
        data = cls._load_users_json()
        return [
            {
                "user_id": u.get("user_id"),
                "name": u.get("name"),
                "created_at": u.get("created_at"),
                "api_key_preview": u.get("api_key", "")[:8] + "..."
            }
            for u in data.get("users", [])
        ]

    @classmethod
    def get_user_stats(cls, user_id: str) -> dict:
        """获取用户统计信息（仅 MySQL）"""
        if cls._use_database():
            return cls._user_dao.get_user_stats(user_id)
        return {}


# ==================== V2: JWT 认证（后续使用） ====================


# 密码加密上下文（降低 rounds 提升速度，12->8，约快 16 倍）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=8)


class JWTHandler:
    """JWT处理器"""

    @staticmethod
    def encode(payload: Dict[str, Any], expire_minutes: Optional[int] = None) -> str:
        """
        生成JWT token

        Args:
            payload: 要编码的数据
            expire_minutes: 过期时间(分钟)，默认使用配置

        Returns:
            JWT token字符串
        """
        expire = expire_minutes or settings.JWT_EXPIRE_MINUTES
        expire_delta = timedelta(minutes=expire)

        # 添加过期时间
        payload = payload.copy()
        payload.update({
            "exp": datetime.utcnow() + expire_delta,
            "iat": datetime.utcnow()
        })

        return jwt.encode(
            payload,
            settings.jwt_secret,
            algorithm=settings.JWT_ALGORITHM
        )

    @staticmethod
    def decode(token: str) -> Dict[str, Any]:
        """
        解码JWT token

        Args:
            token: JWT token字符串

        Returns:
            解码后的数据

        Raises:
            HTTPException: token无效或过期
        """
        try:
            return jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token已过期"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的Token"
            )


class PasswordHandler:
    """密码处理器"""

    @staticmethod
    def hash(password: str) -> str:
        """加密密码"""
        return pwd_context.hash(password)

    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        # 处理空哈希的情况（通过 /users/create 创建的用户没有密码）
        if not hashed_password:
            return False
        try:
            result = pwd_context.verify(plain_password, hashed_password)
            from core.logger import get_logger
            logger = get_logger("security")
            logger.info(f"密码验证: 输入长度={len(plain_password)}, 哈希前20={hashed_password[:20]}, 结果={result}")
            return result
        except Exception as e:
            # 哈希格式无效时返回 False
            from core.logger import get_logger
            logger = get_logger("security")
            logger.error(f"密码验证异常: {e}")
            return False


def create_access_token(data: Dict[str, Any]) -> str:
    """创建访问令牌"""
    return JWTHandler.encode(data)


def decode_access_token(token: str) -> Dict[str, Any]:
    """解码访问令牌"""
    return JWTHandler.decode(token)
