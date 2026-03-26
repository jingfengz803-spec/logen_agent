"""
用户管理 API (V1)
提供用户注册、登录和 API Key 管理
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from models.response import TaskResponse
from core.security import SimpleAuth
from core.logger import get_logger
from api.deps import get_request_id, get_current_user, require_admin

logger = get_logger("api:users")
router = APIRouter(prefix="/users", tags=["用户管理"])


# ==================== 请求模型 ====================

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    password: str


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class CreateUserRequest(BaseModel):
    """创建用户请求（管理员用，无密码）"""
    name: str
    role: str = "user"  # 默认为普通用户


class UserResponse(BaseModel):
    """用户响应"""
    user_id: str
    username: str
    api_key: str
    created_at: str


class LoginResponse(BaseModel):
    """登录响应"""
    user_id: str
    username: str
    api_key: str
    message: str


class UserListResponse(BaseModel):
    """用户列表响应"""
    users: List[dict]
    request_id: str


# ==================== 认证接口 ====================

@router.post("/register", response_model=UserResponse)
async def register(
    request: RegisterRequest,
    request_id: str = Depends(get_request_id)
):
    """
    用户注册（用户名 + 密码）

    - **username**: 用户名（唯一）
    - **password**: 密码

    返回 API Key，前端保存后用于后续请求
    """
    try:
        from dao.user_dao import UserDAO

        user = UserDAO.register(request.username, request.password)
        logger.info(f"用户注册成功: {user.username} ({user.user_id})")

        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            api_key=user.api_key,
            created_at=user.created_at.isoformat() if user.created_at else ""
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"注册失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    request_id: str = Depends(get_request_id)
):
    """
    用户登录（用户名 + 密码）

    - **username**: 用户名
    - **password**: 密码

    验证成功后返回 API Key
    """
    try:
        from dao.user_dao import UserDAO

        user = UserDAO.login(request.username, request.password)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="用户名或密码错误"
            )

        return LoginResponse(
            user_id=user.user_id,
            username=user.username,
            api_key=user.api_key,
            message="登录成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 管理员接口 ====================

@router.post("/create", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    request_id: str = Depends(get_request_id),
    current_user: dict = Depends(require_admin)
):
    """
    创建新用户并生成 API Key（管理员用，无密码）

    - **name**: 用户名称

    需要管理员权限
    """
    try:
        user = SimpleAuth.create_user(request.name, role=request.role)
        logger.info(f"管理员创建新用户: {user['user_id']} - {user['name']}, 角色: {user.get('role')}, 操作者: {current_user.get('user_id')}")
        return UserResponse(
            user_id=user['user_id'],
            username=user['name'],
            api_key=user['api_key'],
            created_at=user.get("created_at", "")
        )
    except Exception as e:
        logger.error(f"创建用户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=UserListResponse)
async def list_users(
    request_id: str = Depends(get_request_id),
    current_user: dict = Depends(require_admin)
):
    """
    获取用户列表（管理员）

    注意：API Key 只显示前8位
    """
    try:
        users = SimpleAuth.list_users()
        return UserListResponse(users=users, request_id=request_id)
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
async def get_current_user(
    request_id: str = Depends(get_request_id)
):
    """
    获取当前用户信息（需要 API Key）
    """
    from api.deps import get_current_user as _get_current_user
    user = await _get_current_user()
    if not user:
        raise HTTPException(status_code=401, detail="未认证，请在请求头中添加 X-API-Key")
    return {
        "code": 200,
        "message": "success",
        "data": user,
        "request_id": request_id
    }
