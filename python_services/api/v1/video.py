"""
视频生成API路由
提供VideoRetalk视频生成接口
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, UploadFile, File, Form
from typing import Optional

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
from database import Database

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


@router.post("/generate-from-files", response_model=TaskResponse)
async def generate_video_from_files(
    video_file: UploadFile = File(..., description="参考视频文件（支持 mp4, mov, avi 等格式）"),
    audio_file: UploadFile = File(..., description="合成音频文件（支持 mp3, wav 等格式）"),
    ref_image_file: Optional[UploadFile] = File(None, description="参考图片文件（可选，支持 jpg, png 等）"),
    video_extension: bool = Form(True, description="是否扩展视频以匹配音频长度"),
    resolution: Optional[str] = Form(None, description="分辨率（如 1280x720）"),
    background_tasks: BackgroundTasks = None,
    request_id: str = Depends(get_request_id)
):
    """
    从上传的文件直接生成口型同步视频（合并API）

    流程：
    1. 接收前端上传的参考视频文件
    2. 接收前端上传的合成音频文件
    3. 自动上传两个文件到OSS获取公网URL
    4. 调用VideoRetalk生成口型同步视频
    5. 返回生成的视频URL

    优势：
    - 前端只需调用一次API
    - 自动处理视频和音频的上传到OSS
    - 支持可选的参考图片上传

    请求参数：
    - video_file: 参考视频文件（必需）
    - audio_file: 合成音频文件（必需）
    - ref_image_file: 参考图片文件（可选）
    - video_extension: 是否扩展视频以匹配音频长度（默认: True）
    - resolution: 分辨率（如 1280x720，可选）

    返回：task_id，轮询 /task/{task_id} 获取结果

    示例（curl）：
    ```bash
    curl -X POST "http://localhost:8000/api/v1/video/generate-from-files" \\
      -H "X-API-Key: your-api-key" \\
      -F "video_file=@ref_video.mp4" \\
      -F "audio_file=@tts_audio.mp3" \\
      -F "video_extension=true"
    ```

    示例（JavaScript）：
    ```javascript
    const formData = new FormData();
    formData.append('video_file', videoFile);
    formData.append('audio_file', audioFile);

    const res = await fetch('/api/v1/video/generate-from-files', {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: formData
    });
    const { task_id } = await res.json();
    // 轮询获取结果
    ```
    """
    try:
        # 获取当前用户 ID（用于后台任务）
        user_db_id = Database.get_current_user_id()

        logger.info(f"收到视频生成（含文件上传）请求: video={video_file.filename}, audio={audio_file.filename}")

        # 创建任务
        task_id = task_manager.create_task("generate_video_from_files", {
            "video_filename": video_file.filename,
            "audio_filename": audio_file.filename,
            "has_ref_image": ref_image_file is not None
        })

        # 提交后台任务
        async def run_generate():
            try:
                from services.storage_service import get_storage_service
                storage = get_storage_service()

                # 步骤1: 上传参考视频到OSS
                task_manager.update_progress(task_id, 5, "读取参考视频...")
                video_bytes = await video_file.read()

                task_manager.update_progress(task_id, 10, "上传参考视频到OSS...")
                video_upload_result = await storage.upload_bytes_async(
                    file_bytes=video_bytes,
                    filename=video_file.filename or f"ref_video.{video_file.content_type.split('/')[-1]}",
                    file_type="video",
                    progress_callback=lambda p, msg: task_manager.update_progress(task_id, 10 + int(p * 0.15), msg)
                )

                video_url = video_upload_result.get("oss_url")
                if not video_url:
                    raise Exception("上传参考视频到OSS失败：未返回URL")

                logger.info(f"参考视频已上传到OSS: {video_url}")

                # 步骤2: 上传音频到OSS
                task_manager.update_progress(task_id, 30, "读取音频文件...")
                audio_bytes = await audio_file.read()

                task_manager.update_progress(task_id, 35, "上传音频到OSS...")
                audio_upload_result = await storage.upload_bytes_async(
                    file_bytes=audio_bytes,
                    filename=audio_file.filename or f"tts_audio.{audio_file.content_type.split('/')[-1]}",
                    file_type="audio",
                    progress_callback=lambda p, msg: task_manager.update_progress(task_id, 35 + int(p * 0.15), msg)
                )

                audio_url = audio_upload_result.get("oss_url")
                if not audio_url:
                    raise Exception("上传音频到OSS失败：未返回URL")

                logger.info(f"音频已上传到OSS: {audio_url}")

                # 步骤3: 上传参考图片（如果提供）
                ref_image_url = None
                if ref_image_file:
                    task_manager.update_progress(task_id, 55, "上传参考图片到OSS...")
                    image_bytes = await ref_image_file.read()

                    image_upload_result = await storage.upload_bytes_async(
                        file_bytes=image_bytes,
                        filename=ref_image_file.filename or f"ref_image.{ref_image_file.content_type.split('/')[-1]}",
                        file_type="image",
                        progress_callback=lambda p, msg: task_manager.update_progress(task_id, 55 + int(p * 0.1), msg)
                    )

                    ref_image_url = image_upload_result.get("oss_url")
                    logger.info(f"参考图片已上传到OSS: {ref_image_url}")

                task_manager.update_progress(task_id, 70, "提交视频生成任务...")

                # 步骤4: 调用VideoRetalk生成视频
                result = await video_service.generate_video_async(
                    video_url=video_url,
                    audio_url=audio_url,
                    ref_image_url=ref_image_url,
                    video_extension=video_extension,
                    resolution=resolution,
                    auto_upload=True,
                    progress_callback=lambda p, msg: task_manager.update_progress(task_id, 70 + int(p * 0.3), msg)
                )

                task_manager.update_progress(task_id, 100, "视频生成完成")

                # 返回完整结果
                return {
                    "task_id": result.get("task_id"),
                    "video_url": result.get("video_url"),
                    "status": result.get("status"),
                    "input_urls": {
                        "video_url": video_url,
                        "audio_url": audio_url,
                        "ref_image_url": ref_image_url
                    }
                }

            except Exception as e:
                logger.error(f"视频生成（含文件上传）失败: {e}")
                raise

        # 在后台执行异步任务
        import asyncio
        try:
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
            code=200,
            message="视频生成任务已创建",
            task_id=task_id,
            status=TaskStatus(task.status.value),
            progress=task.progress,
            created_at=task.created_at,
            request_id=request_id
        )

    except Exception as e:
        logger.error(f"创建视频生成任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
