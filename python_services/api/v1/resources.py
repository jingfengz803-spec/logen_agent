"""
生成的资源管理API路由
提供用户资源查询、管理员审核等功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List

from models.response import BaseResponse, DataResponse
from models.request import CommonRequest
from dao.resource_dao import ResourceDAO
from database import Database
from core.logger import get_logger
from api.deps import get_request_id, require_admin

logger = get_logger("api:resources")
router = APIRouter(prefix="/resources", tags=["资源管理"])


@router.get("/list", response_model=DataResponse)
async def get_user_resources(
    resource_type: Optional[str] = Query(None, description="资源类型: audio/video/image"),
    status: str = Query("active", description="资源状态"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    request_id: str = Depends(get_request_id)
):
    """
    获取当前用户的资源列表

    返回用户生成的所有音频、视频等资源
    """
    try:
        user_db_id = Database.get_current_user_id()
        if not user_db_id:
            raise HTTPException(status_code=401, detail="用户未登录")

        resources = ResourceDAO.get_user_resources(
            user_db_id,
            resource_type=resource_type,
            status=status,
            limit=limit,
            offset=offset
        )

        # 获取统计
        stats = ResourceDAO.count_user_resources(user_db_id, resource_type)

        return DataResponse(
            code=200,
            message="success",
            data={
                "resources": resources,
                "stats": stats
            },
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取资源列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/all", response_model=DataResponse)
async def get_all_resources(
    resource_type: Optional[str] = Query(None, description="资源类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    request_id: str = Depends(get_request_id),
    current_user: dict = Depends(require_admin)
):
    """
    获取所有资源（管理员审核用）

    需要管理员权限
    """
    try:
        resources = ResourceDAO.get_all_resources(
            resource_type=resource_type,
            status=status,
            limit=limit,
            offset=offset
        )

        return DataResponse(
            code=200,
            message="success",
            data={
                "resources": resources
            },
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取所有资源失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=DataResponse)
async def get_resource_stats(
    days: int = Query(7, ge=1, le=90, description="统计最近几天"),
    request_id: str = Depends(get_request_id),
    current_user: dict = Depends(require_admin)
):
    """
    获取资源统计信息（管理员用）
    """
    try:
        stats = ResourceDAO.get_resource_stats(days=days)

        return DataResponse(
            code=200,
            message="success",
            data=stats,
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{resource_id}/status", response_model=BaseResponse)
async def update_resource_status(
    resource_id: int,
    status: str = Query(..., description="新状态: active/deleted/blocked"),
    request_id: str = Depends(get_request_id),
    current_user: dict = Depends(require_admin)
):
    """
    更新资源状态

    管理员可以删除或封禁资源
    """
    try:
        if status not in ["active", "deleted", "blocked"]:
            raise HTTPException(status_code=400, detail="无效的状态值")

        success = ResourceDAO.update_resource_status(resource_id, status)
        if not success:
            raise HTTPException(status_code=404, detail="资源不存在")

        return BaseResponse(
            code=200,
            message=f"资源状态已更新为: {status}",
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新资源状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}", response_model=DataResponse)
async def get_task_resources(
    task_id: str,
    request_id: str = Depends(get_request_id)
):
    """
    根据任务ID获取相关资源
    """
    try:
        resources = ResourceDAO.get_resources_by_task(task_id)

        return DataResponse(
            code=200,
            message="success",
            data={
                "task_id": task_id,
                "resources": resources
            },
            request_id=request_id
        )

    except Exception as e:
        logger.error(f"获取任务资源失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
