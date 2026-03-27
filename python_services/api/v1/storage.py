"""
存储服务API路由
提供文件上传到OSS的接口
"""

from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException, Form
from typing import Optional, List

from models.request import UploadByPathRequest
from models.response import (
    FileUploadResponse,
    FileUploadInfo,
    UploadRecordsResponse,
    UploadRecordInfo,
    OSSConfigResponse,
    TaskResponse,
    TaskStatus
)
from services.storage_service import get_storage_service, StorageService
from core.task_manager import task_manager
from core.task_helper import submit_background_task
from core.logger import get_logger
from api.deps import get_request_id
from datetime import datetime

logger = get_logger("api:storage")
router = APIRouter(prefix="/storage", tags=["存储服务"])


@router.post("/upload/file", response_model=TaskResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_type: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    request_id: str = Depends(get_request_id)
):
    """
    上传文件到 OSS

    - **file**: 要上传的文件（支持 audio, video, image）
    - **file_type**: 文件类型（不指定则自动识别）

    返回任务ID，可通过 /task/{task_id} 查询进度和获取 URL
    """
    try:
        logger.info(f"收到文件上传请求: {file.filename}, size: {file.size}")

        # 创建任务
        task_id = task_manager.create_task("upload_file", {
            "filename": file.filename,
            "content_type": file.content_type
        })

        # 提交后台任务
        async def run_upload():
            try:
                task_manager.update_progress(task_id, 10, "读取文件...")

                # 读取文件内容
                file_bytes = await file.read()

                task_manager.update_progress(task_id, 30, "上传到 OSS...")

                # 上传
                storage = get_storage_service()
                result = await storage.upload_bytes_async(
                    file_bytes=file_bytes,
                    filename=file.filename or "unknown",
                    file_type=file_type,
                    progress_callback=lambda p, msg: task_manager.update_progress(task_id, 30 + int(p * 0.7), msg)
                )

                task_manager.update_progress(task_id, 100, "上传完成")
                return result

            except Exception as e:
                logger.error(f"文件上传失败: {e}")
                raise

        if background_tasks:
            submit_background_task(task_id, run_upload, background_tasks)
        else:
            # 同步执行（用于测试）
            result = await run_upload()

        task = task_manager.get_task(task_id)
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus(task.status.value),
            progress=task.progress,
            created_at=task.created_at,
            request_id=request_id
        )

    except Exception as e:
        logger.error(f"创建上传任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/path", response_model=TaskResponse)
async def upload_by_path(
    request: UploadByPathRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    通过本地路径上传文件到 OSS

    - **file_path**: 本地文件路径
    - **file_type**: 文件类型（不指定则自动识别）
    - **force_reupload**: 是否强制重新上传（忽略缓存）
    - **custom_object_name**: 自定义 OSS 对象名
    """
    try:
        logger.info(f"收到路径上传请求: {request.file_path}")

        task_id = task_manager.create_task("upload_by_path", {
            "file_path": request.file_path,
            "file_type": request.file_type
        })

        async def run_upload():
            try:
                task_manager.update_progress(task_id, 10, "检查文件...")

                storage = get_storage_service()
                result = await storage.upload_file_async(
                    file_path=request.file_path,
                    file_type=request.file_type,
                    force_reupload=request.force_reupload,
                    custom_object_name=request.custom_object_name,
                    progress_callback=lambda p, msg: task_manager.update_progress(task_id, p, msg)
                )

                task_manager.update_progress(task_id, 100, "上传完成")
                return result

            except Exception as e:
                logger.error(f"路径上传失败: {e}")
                raise

        # 使用 asyncio.create_task 而不是 background_tasks.add_task
        submit_background_task(task_id, run_upload, background_tasks)

        task = task_manager.get_task(task_id)
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus(task.status.value),
            progress=task.progress,
            created_at=task.created_at,
            request_id=request_id
        )

    except Exception as e:
        logger.error(f"创建上传任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload/task/{task_id}", response_model=TaskResponse)
async def get_upload_task_status(
    task_id: str,
    request_id: str = Depends(get_request_id)
):
    """查询上传任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskResponse(
        task_id=task.task_id,
        status=TaskStatus(task.status.value),
        progress=task.progress,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        result=task.result,
        error=task.error,
        request_id=request_id
    )


@router.get("/records", response_model=UploadRecordsResponse)
async def list_upload_records(
    file_type: Optional[str] = None,
    request_id: str = Depends(get_request_id)
):
    """
    获取上传记录列表

    - **file_type**: 过滤文件类型（audio, video, image）
    """
    try:
        storage = get_storage_service()
        records = storage.list_records(file_type=file_type)

        record_infos = []
        for r in records:
            record_infos.append(UploadRecordInfo(
                file_path=r["file_path"],
                file_hash=r["file_hash"],
                oss_url=r["oss_url"],
                file_type=r["file_type"],
                size=r["size"],
                uploaded_at=r["uploaded_at"],
                last_accessed_at=r["last_accessed_at"]
            ))

        return UploadRecordsResponse(
            data=record_infos,
            total=len(record_infos),
            request_id=request_id
        )

    except Exception as e:
        logger.error(f"获取上传记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/url/{file_hash}")
async def get_url_by_hash(
    file_hash: str,
    request_id: str = Depends(get_request_id)
):
    """
    根据 hash 获取文件 URL

    - **file_hash**: 文件 MD5 hash
    """
    try:
        storage = get_storage_service()
        url = await storage.get_url_by_hash(file_hash)

        if not url:
            raise HTTPException(status_code=404, detail="文件不存在或未上传")

        return {
            "code": 200,
            "message": "success",
            "data": {
                "oss_url": url,
                "file_hash": file_hash
            },
            "request_id": request_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 URL 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/status", response_model=OSSConfigResponse)
async def get_oss_config_status(
    request_id: str = Depends(get_request_id)
):
    """获取 OSS 配置状态"""
    try:
        storage = get_storage_service()
        status = storage.get_oss_config_status()

        message = None
        if not status["configured"]:
            message = "OSS 未配置，请在 .env 文件中设置以下参数: OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_BUCKET_NAME, OSS_ENDPOINT"

        return OSSConfigResponse(
            configured=status["configured"],
            records_count=status["records_count"],
            temp_dir=status["temp_dir"],
            records_file=status["records_file"],
            message=message,
            request_id=request_id
        )

    except Exception as e:
        logger.error(f"获取配置状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/records/cleanup")
async def cleanup_old_records(
    days: int = 7,
    request_id: str = Depends(get_request_id)
):
    """
    清理过期的上传记录

    - **days**: 保留天数（默认 7 天）
    """
    try:
        storage = get_storage_service()
        count = storage.cleanup_old_records(days=days)

        return {
            "code": 200,
            "message": f"已清理 {count} 条过期记录",
            "data": {
                "cleaned_count": count,
                "days": days
            },
            "request_id": request_id
        }

    except Exception as e:
        logger.error(f"清理记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/batch")
async def batch_upload_files(
    files: List[UploadFile] = File(...),
    file_type: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    request_id: str = Depends(get_request_id)
):
    """
    批量上传文件到 OSS

    - **files**: 要上传的文件列表
    - **file_type**: 文件类型（不指定则自动识别）

    返回任务ID列表
    """
    try:
        task_ids = []

        for file in files:
            task_id = task_manager.create_task("upload_file", {
                "filename": file.filename,
                "content_type": file.content_type
            })

            # 为每个文件创建上传任务
            async def run_upload(f=file, tid=task_id):
                try:
                    task_manager.update_progress(tid, 10, "读取文件...")
                    file_bytes = await f.read()
                    task_manager.update_progress(tid, 30, "上传到 OSS...")

                    storage = get_storage_service()
                    result = await storage.upload_bytes_async(
                        file_bytes=file_bytes,
                        filename=f.filename or "unknown",
                        file_type=file_type,
                        progress_callback=lambda p, msg: task_manager.update_progress(tid, 30 + int(p * 0.7), msg)
                    )

                    task_manager.update_progress(tid, 100, "上传完成")
                    return result

                except Exception as e:
                    logger.error(f"文件上传失败: {e}")
                    raise

            if background_tasks:
                submit_background_task(task_id, run_upload, background_tasks)

            task_ids.append(task_id)

        return {
            "code": 200,
            "message": f"已创建 {len(task_ids)} 个上传任务",
            "data": {
                "task_ids": task_ids
            },
            "request_id": request_id
        }

    except Exception as e:
        logger.error(f"创建批量上传任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
