"""
依赖注入模块
提供API路由使用的依赖函数
"""

from typing import Optional
from fastapi import Header, HTTPException
from core.logger import get_logger

logger = get_logger("deps")


async def get_request_id(
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID")
) -> Optional[str]:
    """获取请求ID"""
    return x_request_id or "req_unknown"


async def get_current_user() -> Optional[dict]:
    """
    获取当前用户（从 Database 上下文）
    认证中间件已验证，这里只读取上下文
    """
    from database import Database
    from dao.user_dao import UserDAO

    user_db_id = Database.get_current_user_id()
    if not user_db_id:
        return None

    user = UserDAO.get_by_id(user_db_id, skip_user_filter=True)
    if not user:
        return None

    return {
        "user_id": user.user_id,
        "api_key": user.api_key,
        "name": user.username,
        "role": user.role,
    }


async def require_admin() -> dict:
    """要求管理员权限"""
    user = await get_current_user()
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user