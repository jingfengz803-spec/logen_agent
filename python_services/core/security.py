"""
安全模块 - JWT认证与鉴权
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from fastapi import HTTPException, status

from .config import settings


# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
            settings.JWT_SECRET_KEY,
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
                settings.JWT_SECRET_KEY,
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
        return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any]) -> str:
    """创建访问令牌"""
    return JWTHandler.encode(data)


def decode_access_token(token: str) -> Dict[str, Any]:
    """解码访问令牌"""
    return JWTHandler.decode(token)
