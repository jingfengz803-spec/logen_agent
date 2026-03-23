"""
视频生成API路由
提供VideoRetalk视频生成接口
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from models.request import VideoGenerateRequest
from models.response import (
    VideoGenerateResponse,
    VideoStatusResponse,
    TaskResponse,
    TaskStatus
)
from services.video_service import VideoService
from core.task_manager import task_manager
from core.logger import get_logger
from api.deps import get_request_id

logger = get_logger("api:video")
router = APIRouter(prefix="/video", tags=["视频生成"])

# 服务实例
video_service = VideoService()


@router.post("/generate", response_model=TaskResponse)
async def generate_video(
    request: VideoGenerateRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    生成口型同步视频

    - **video_url**: 参考视频公网URL
    - **audio_url**: 合成音频公网URL
    - **ref_image_url**: 参考图片URL（可选）
    - **video_extension**: 是否扩展视频以匹配音频长度
    - **resolution**: 分辨率（如1280x720）
    """
    logger.info(f"收到视频生成请求")

    task_id = task_manager.create_task("generate_video", {
        "has_ref_image": request.ref_image_url is not None
    })

    async def run_generate():
        return await video_service.generate_video_async(
            video_url=request.video_url,
            audio_url=request.audio_url,
            ref_image_url=request.ref_image_url,
            video_extension=request.video_extension,
            resolution=request.resolution
        )

    # 在后台执行异步任务
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        asyncio.create_task(task_manager.submit_task(task_id, run_generate))
    except RuntimeError:
        def run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(task_manager.submit_task(task_id, run_generate))
            finally:
                new_loop.close()
        background_tasks.add_task(run_in_new_loop)

    task = task_manager.get_task(task_id)
    return TaskResponse(
        task_id=task_id,
        status=TaskStatus(task.status.value),
        progress=task.progress,
        created_at=task.created_at,
        request_id=request_id
    )


@router.get("/task/{task_id}", response_model=VideoStatusResponse)
async def get_video_task_status(
    task_id: str,
    request_id: str = Depends(get_request_id)
):
    """
    查询视频生成任务状态

    可查询任务进度、结果URL等
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return VideoStatusResponse(
        task_id=task_id,
        status=task.status.value,
        progress=task.progress,
        video_url=task.result.get("video_url") if task.result else None,
        error=task.error,
        request_id=request_id
    )


@router.delete("/task/{task_id}")
async def cancel_video_task(
    task_id: str,
    request_id: str = Depends(get_request_id)
):
    """取消视频生成任务"""
    success = task_manager.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="无法取消该任务")

    return {
        "code": 200,
        "message": "任务已取消",
        "request_id": request_id
    }
