"""
档案管理API路由
提供档案CRUD和行业管理功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from models.request import CommonRequest
from models.response import BaseResponse, DataResponse
from dao.profile_dao import ProfileDAO, SYSTEM_INDUSTRIES
from database import Database
from core.logger import get_logger
from api.deps import get_request_id

logger = get_logger("api:profiles")
router = APIRouter(prefix="/profiles", tags=["档案管理"])


# ── 请求模型 ──────────────────────────────────────

class CreateProfileRequest(CommonRequest):
    """创建档案请求"""
    name: str
    industry: str
    video_url: Optional[str] = None
    homepage_url: Optional[str] = None
    target_audience: str
    customer_pain_points: str
    solution: str
    persona_background: str


class UpdateProfileRequest(CommonRequest):
    """更新档案请求"""
    name: Optional[str] = None
    industry: Optional[str] = None
    video_url: Optional[str] = None
    homepage_url: Optional[str] = None
    target_audience: Optional[str] = None
    customer_pain_points: Optional[str] = None
    solution: Optional[str] = None
    persona_background: Optional[str] = None


class AddIndustryRequest(CommonRequest):
    """添加自定义行业请求"""
    name: str


# ── 档案 CRUD ──────────────────────────────────────

@router.post("", response_model=DataResponse)
async def create_profile(
    request: CreateProfileRequest,
    request_id: str = Depends(get_request_id)
):
    """创建档案"""
    try:
        user_db_id = Database.get_current_user_id()
        if not user_db_id:
            raise HTTPException(status_code=401, detail="用户未登录")

        import uuid
        profile_id = f"profile_{uuid.uuid4().hex[:12]}"

        pid = ProfileDAO.create_profile(
            user_db_id=user_db_id,
            profile_id=profile_id,
            name=request.name,
            industry=request.industry,
            video_url=request.video_url,
            homepage_url=request.homepage_url,
            target_audience=request.target_audience,
            customer_pain_points=request.customer_pain_points,
            solution=request.solution,
            persona_background=request.persona_background,
        )

        return DataResponse(
            code=201,
            message="档案创建成功",
            data={"profile_id": profile_id, "id": pid},
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建档案失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=DataResponse)
async def list_profiles(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    request_id: str = Depends(get_request_id)
):
    """获取当前用户的档案列表"""
    try:
        profiles = ProfileDAO.list_profiles(limit=limit, offset=offset)

        return DataResponse(
            code=200,
            message="success",
            data={"profiles": profiles, "total": len(profiles)},
            request_id=request_id
        )

    except Exception as e:
        logger.error(f"获取档案列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{profile_id}", response_model=DataResponse)
async def get_profile(
    profile_id: str,
    request_id: str = Depends(get_request_id)
):
    """获取档案详情"""
    try:
        profile = ProfileDAO.get_profile(profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="档案不存在")

        return DataResponse(
            code=200,
            message="success",
            data=profile,
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取档案详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{profile_id}", response_model=BaseResponse)
async def update_profile(
    profile_id: str,
    request: UpdateProfileRequest,
    request_id: str = Depends(get_request_id)
):
    """更新档案"""
    try:
        success = ProfileDAO.update_profile(
            profile_id=profile_id,
            name=request.name,
            industry=request.industry,
            video_url=request.video_url,
            homepage_url=request.homepage_url,
            target_audience=request.target_audience,
            customer_pain_points=request.customer_pain_points,
            solution=request.solution,
            persona_background=request.persona_background,
        )
        if not success:
            raise HTTPException(status_code=404, detail="档案不存在或未修改")

        return BaseResponse(
            code=200,
            message="档案更新成功",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新档案失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{profile_id}", response_model=BaseResponse)
async def delete_profile(
    profile_id: str,
    request_id: str = Depends(get_request_id)
):
    """删除档案（软删除）"""
    try:
        success = ProfileDAO.delete_profile(profile_id)
        if not success:
            raise HTTPException(status_code=404, detail="档案不存在")

        return BaseResponse(
            code=200,
            message="档案已删除",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除档案失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── 行业管理 ──────────────────────────────────────

@router.get("/industries", response_model=DataResponse)
async def get_industries(
    request_id: str = Depends(get_request_id)
):
    """
    获取行业列表（系统预设 + 用户自定义）

    返回合并后的列表，包含系统预设行业和当前用户的自定义行业
    """
    try:
        custom = ProfileDAO.get_custom_industries()
        custom_names = [item["name"] for item in custom]

        # 合并去重
        all_industries = list(SYSTEM_INDUSTRIES)
        for name in custom_names:
            if name not in all_industries:
                all_industries.append(name)

        return DataResponse(
            code=200,
            message="success",
            data={
                "system": SYSTEM_INDUSTRIES,
                "custom": [{"id": item["id"], "name": item["name"]} for item in custom],
                "all": all_industries
            },
            request_id=request_id
        )

    except Exception as e:
        logger.error(f"获取行业列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/industries", response_model=DataResponse)
async def add_custom_industry(
    request: AddIndustryRequest,
    request_id: str = Depends(get_request_id)
):
    """添加自定义行业"""
    try:
        user_db_id = Database.get_current_user_id()
        if not user_db_id:
            raise HTTPException(status_code=401, detail="用户未登录")

        # 检查是否已存在（系统预设或自定义）
        if request.name in SYSTEM_INDUSTRIES:
            raise HTTPException(status_code=409, detail="该行业已存在于系统预设中")

        custom = ProfileDAO.get_custom_industries()
        if any(item["name"] == request.name for item in custom):
            raise HTTPException(status_code=409, detail="该行业已存在")

        industry_id = ProfileDAO.add_custom_industry(user_db_id, request.name)

        return DataResponse(
            code=201,
            message="自定义行业添加成功",
            data={"id": industry_id, "name": request.name},
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加自定义行业失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/industries/{industry_id}", response_model=BaseResponse)
async def delete_custom_industry(
    industry_id: int,
    request_id: str = Depends(get_request_id)
):
    """删除自定义行业"""
    try:
        success = ProfileDAO.delete_custom_industry(industry_id)
        if not success:
            raise HTTPException(status_code=404, detail="自定义行业不存在")

        return BaseResponse(
            code=200,
            message="自定义行业已删除",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除自定义行业失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
