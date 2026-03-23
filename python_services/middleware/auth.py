"""
认证中间件
处理JWT认证和权限验证
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional

from core.security import decode_access_token
from core.logger import get_logger

logger = get_logger("middleware:auth")


class AuthMiddleware(BaseHTTPMiddleware):
    """
    认证中间件
    可选认证：部分接口需要认证，部分不需要
    """

    # 不需要认证的路径
    PUBLIC_PATHS = {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/douyin/fetch/user",  # 示例：公开接口
    }

    async def dispatch(self, request: Request, call_next):
        """处理请求并验证认证"""
        path = request.url.path

        # 检查是否是公开路径
        if self._is_public_path(path):
            return await call_next(request)

        # 获取token
        authorization = request.headers.get("Authorization")
        if not authorization:
            return await call_next(request)  # 可选认证，不强制

        # 验证token
        try:
            token = authorization.replace("Bearer ", "")
            payload = decode_access_token(token)

            # 将用户信息存入请求状态
            request.state.user = payload

        except HTTPException:
            # Token无效，但继续处理（由具体接口决定是否需要认证）
            pass
        except Exception as e:
            logger.warning(f"Auth middleware error: {e}")

        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """检查是否是公开路径"""
        return any(path.startswith(p) for p in self.PUBLIC_PATHS)
