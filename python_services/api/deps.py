"""
依赖注入模块
提供API路由使用的依赖函数
"""

from typing import Optional
from fastapi import Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.security import decode_access_token
from core.logger import get_logger

logger = get_logger("deps")
security = HTTPBearer(auto_error=False)


async def get_request_id(
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID")
) -> Optional[str]:
    """获取请求ID"""
    return x_request_id or "req_unknown"


async def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Header(None)
) -> Optional[dict]:
    """
    验证JWT Token

    可选鉴权：如果传了token则验证，没传则返回None
    """
    if credentials is None:
        return None

    try:
        payload = decode_access_token(credentials.credentials)
        return payload
    except Exception as e:
        logger.warning(f"Token验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据"
        )


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Header(None)
) -> dict:
    """
    强制要求认证

    必须提供有效的Token
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证凭据"
        )

    try:
        payload = decode_access_token(credentials.credentials)
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Token验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据"
        )
