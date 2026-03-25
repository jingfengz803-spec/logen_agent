"""
全局认证中间件
基于 X-API-Key 请求头进行 API Key 验证
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.security import SimpleAuth
from core.logger import get_logger

logger = get_logger("middleware:auth")

# 白名单路径（跳过认证）
WHITELIST_PATHS = {
    "/health",
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/users/register",
    "/api/v1/users/login",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """全局 API Key 认证中间件"""

    async def dispatch(self, request: Request, call_next):
        """处理请求，验证 API Key"""

        # OPTIONS 请求（CORS 预检）跳过认证
        if request.method == "OPTIONS":
            return await call_next(request)

        # 白名单路径跳过认证
        if request.url.path in WHITELIST_PATHS:
            return await call_next(request)

        # 检查 X-API-Key 请求头
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "缺少 API Key，请在请求头中添加 X-API-Key"},
            )

        # 验证 API Key
        try:
            user = SimpleAuth.verify_api_key(api_key)
        except Exception as e:
            # 捕获 SimpleAuth 抛出的 HTTPException 或其他异常
            detail = getattr(e, "detail", None) or "无效的 API Key"
            return JSONResponse(
                status_code=401,
                content={"detail": detail},
            )

        # 设置用户上下文
        try:
            from dao.user_dao import UserDAO
            from database import Database

            user_id_str = user.get("user_id")
            if user_id_str:
                db_user = UserDAO.get_by_user_id(user_id_str)
                if db_user:
                    Database.set_current_user(db_user.id, user.get("role", "user"))
                    logger.debug(f"用户上下文已设置: {user_id_str} (db_id={db_user.id})")
        except Exception as e:
            logger.warning(f"设置用户上下文失败: {e}")

        try:
            response = await call_next(request)
        finally:
            # 请求完成后清除用户上下文
            try:
                from database import Database
                Database.clear_current_user()
            except Exception:
                pass

        return response