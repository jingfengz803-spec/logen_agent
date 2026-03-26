"""
TTS语音合成API路由
提供音色创建、语音合成等接口
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, UploadFile, File, Form
from typing import List, Optional

from models.request import (
    SpeechRequest,
    SpeechSegmentsRequest,
    TTSScriptRequest,
    CreateVoiceRequest
)
from models.response import (
    VoiceListResponse,
    VoiceInfo,
    TaskResponse,
    TaskStatus
)
from services.tts_service import TTSService
from core.task_manager import task_manager
from core.logger import get_logger
from api.deps import get_request_id, require_admin
from database import Database
from dao.voice_dao import VoiceDAO

logger = get_logger("api:tts")
router = APIRouter(prefix="/tts", tags=["TTS语音"])

# 服务实例
tts_service = TTSService()


@router.post("/voice/create-from-file", response_model=TaskResponse)
async def create_voice_from_file(
    file: UploadFile = File(..., description="音色音频文件（支持 mp3, wav, m4a 等格式）"),
    prefix: str = Form("myvoice", description="音色前缀", max_length=20),
    model: str = Form("cosyvoice-v3.5-flash", description="TTS模型"),
    preview_text: str = Form("你好，这是我的音色。", description="试听文本"),
    auto_upload_oss: bool = Form(True, description="是否自动上传试听音频到OSS"),
    background_tasks: BackgroundTasks = None,
    request_id: str = Depends(get_request_id)
):
    """
    从上传的音频文件直接创建音色并生成试听

    流程：
    1. 接收前端上传的音频文件
    2. 自动上传到OSS获取公网URL
    3. 创建音色复刻（得到voice_id）
    4. 用新音色合成试听文本
    5. 返回voice_id和试听音频URL

    优势：
    - 前端只需调用一次API
    - 无需手动处理上传和音色创建的两个步骤
    - 自动处理文件上传到OSS

    请求参数：
    - file: 音频文件（multipart/form-data）
    - prefix: 音色前缀（默认: myvoice）
    - model: TTS模型（默认: cosyvoice-v3.5-flash）
    - preview_text: 试听文本（默认: "你好，这是我的音色。"）
    - auto_upload_oss: 是否上传试听音频到OSS（默认: True）

    返回：task_id，轮询 /task/{task_id} 获取结果
    """
    try:
        user_db_id = Database.get_current_user_id()

        logger.info(f"收到音色创建（含文件上传）请求: {file.filename}, prefix={prefix}")

        # 创建任务
        task_id = task_manager.create_task("create_voice_from_file", {
            "filename": file.filename,
            "prefix": prefix,
            "model": model
        })

        # 提交后台任务
        async def run_create():
            try:
                # 步骤1: 上传文件到OSS
                task_manager.update_progress(task_id, 10, "读取音频文件...")
                file_bytes = await file.read()

                task_manager.update_progress(task_id, 30, "上传音频到OSS...")
                from services.storage_service import get_storage_service
                storage = get_storage_service()

                upload_result = await storage.upload_bytes_async(
                    file_bytes=file_bytes,
                    filename=file.filename or f"voice_{prefix}.{file.content_type.split('/')[-1]}",
                    file_type="audio",
                    progress_callback=lambda p, msg: task_manager.update_progress(task_id, 30 + int(p * 0.3), msg)
                )

                audio_url = upload_result.get("oss_url")
                if not audio_url:
                    raise Exception("上传到OSS失败：未返回URL")

                logger.info(f"音频已上传到OSS: {audio_url}")
                task_manager.update_progress(task_id, 60, "创建音色复刻...")

                # 步骤2: 创建音色并生成试听
                result = await tts_service.create_voice_with_preview_async(
                    audio_url=audio_url,
                    prefix=prefix,
                    model=model,
                    preview_text=preview_text,
                    auto_upload_oss=auto_upload_oss
                )

                # 保存音色到数据库
                voice_id = result.get("voice_id")
                if voice_id:
                    user_db_id = Database.get_current_user_id()
                    VoiceDAO.create_voice(
                        user_db_id=user_db_id,
                        voice_id=voice_id,
                        prefix=prefix,
                        model=model,
                        status=result.get("status", "DEPLOYING"),
                        target_model=result.get("model"),
                    )

                task_manager.update_progress(task_id, 100, "完成")

                # 返回完整结果
                return {
                    "voice_id": result.get("voice_id"),
                    "prefix": result.get("prefix"),
                    "model": result.get("model"),
                    "status": result.get("status"),
                    "preview_text": result.get("preview_text"),
                    "preview_audio_url": result.get("preview_audio_url"),
                    "is_available": result.get("is_available"),
                    "audio_url": audio_url  # 原始音频URL，供调试用
                }

            except Exception as e:
                logger.error(f"创建音色（含文件上传）失败: {e}")
                raise

        # 在后台执行异步任务
        import asyncio
        try:
            asyncio.create_task(task_manager.submit_task(task_id, run_create))
        except RuntimeError:
            def run_in_new_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(task_manager.submit_task(task_id, run_create))
                finally:
                    new_loop.close()
            background_tasks.add_task(run_in_new_loop)

        task = task_manager.get_task(task_id)
        return TaskResponse(
            code=200,
            message="音色创建任务已创建",
            task_id=task_id,
            status=TaskStatus(task.status.value),
            progress=task.progress,
            created_at=task.created_at,
            request_id=request_id
        )

    except Exception as e:
        logger.error(f"创建音色任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice/list", response_model=VoiceListResponse)
async def list_voices(
    request_id: str = Depends(get_request_id)
):
    """
    获取当前用户的音色列表（自动按用户隔离）
    """
    try:
        voices = VoiceDAO.list_voices()

        voice_infos = []
        for v in voices:
            created_at = ""
            if v.get("gmt_create"):
                created_at = str(v["gmt_create"])
            elif v.get("created_at"):
                created_at = str(v["created_at"])

            voice_infos.append(VoiceInfo(
                voice_id=v.get("voice_id", ""),
                prefix=v.get("prefix", ""),
                model=v.get("target_model") or v.get("model", ""),
                status=v.get("status", "UNKNOWN"),
                created_at=created_at,
                is_available=v.get("status") == "OK"
            ))

        return VoiceListResponse(
            voices=voice_infos,
            request_id=request_id
        )
    except Exception as e:
        logger.error(f"获取音色列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice/{voice_id}", response_model=VoiceListResponse)
async def get_voice(
    voice_id: str,
    request_id: str = Depends(get_request_id)
):
    """
    查询单个音色（自动按用户隔离，只能查看自己的音色）
    """
    try:
        voice = VoiceDAO.get_by_voice_id(voice_id)
        if not voice:
            raise HTTPException(status_code=404, detail="音色不存在")

        created_at = ""
        if voice.gmt_create:
            created_at = str(voice.gmt_create)
        elif voice.created_at:
            created_at = str(voice.created_at)

        voice_info = VoiceInfo(
            voice_id=voice.voice_id,
            prefix=voice.prefix,
            model=voice.target_model or voice.model,
            status=voice.status,
            created_at=created_at,
            is_available=voice.status == "OK"
        )

        return VoiceListResponse(
            voices=[voice_info],
            request_id=request_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询音色失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/voices", response_model=VoiceListResponse)
async def list_all_voices(
    status: Optional[str] = None,
    limit: int = 100,
    _admin: dict = Depends(require_admin),
    request_id: str = Depends(get_request_id)
):
    """
    管理员接口：获取所有用户的音色列表
    """
    try:
        voices = VoiceDAO.list_all(status=status, limit=limit)

        voice_infos = []
        for v in voices:
            created_at = ""
            if v.get("gmt_create"):
                created_at = str(v["gmt_create"])
            elif v.get("created_at"):
                created_at = str(v["created_at"])

            voice_infos.append(VoiceInfo(
                voice_id=v.get("voice_id", ""),
                prefix=v.get("prefix", ""),
                model=v.get("target_model") or v.get("model", ""),
                status=v.get("status", "UNKNOWN"),
                created_at=created_at,
                is_available=v.get("status") == "OK"
            ))

        return VoiceListResponse(
            voices=voice_infos,
            request_id=request_id
        )
    except Exception as e:
        logger.error(f"管理员获取音色列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice/create-from-url", response_model=TaskResponse)
async def create_voice_from_url(
    request: CreateVoiceRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    使用已有的音频URL创建音色

    - **audio_url**: 音色音频的公网URL（OSS URL）
    - **prefix**: 音色前缀/名称
    - **model**: TTS模型（默认: cosyvoice-v3.5-flash）
    - **wait_ready**: 是否等待音色就绪（默认: True）

    返回：task_id，轮询 /task/{task_id} 获取结果
    """
    try:
        user_db_id = Database.get_current_user_id()

        logger.info(f"收到音色创建请求（URL）: audio_url={request.audio_url}, prefix={request.prefix}")

        task_id = task_manager.create_task("create_voice_from_url", {
            "audio_url": request.audio_url,
            "prefix": request.prefix,
            "model": request.model
        })

        async def run_create():
            result = await tts_service.create_voice_async(
                audio_url=request.audio_url,
                prefix=request.prefix,
                model=request.model,
                wait_ready=request.wait_ready
            )
            # 保存音色到数据库
            voice_id = result.get("voice_id")
            if voice_id:
                user_db_id = Database.get_current_user_id()
                VoiceDAO.create_voice(
                    user_db_id=user_db_id,
                    voice_id=voice_id,
                    prefix=request.prefix,
                    model=request.model,
                    status=result.get("status", "DEPLOYING"),
                    target_model=result.get("model"),
                )
            return result

        import asyncio
        try:
            asyncio.create_task(task_manager.submit_task(task_id, run_create))
        except RuntimeError:
            def run_in_new_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(task_manager.submit_task(task_id, run_create))
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

    except Exception as e:
        logger.error(f"创建音色任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speech", response_model=TaskResponse)
async def text_to_speech(
    request: SpeechRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    文字转语音（自动上传到OSS，返回公网URL）

    - **text**: 要合成的文本
    - **voice_id**: 音色ID
    - **model**: TTS模型（可选，默认使用音色对应模型）
    - **output_format**: 输出格式（mp3/wav/pcm）

    返回结果中包含 audio_url（OSS公网URL），可直接用于视频生成
    """
    user_db_id = Database.get_current_user_id()

    logger.info(f"收到语音合成请求，字数: {len(request.text)}")

    task_id = task_manager.create_task("tts_speech", {
        "text_length": len(request.text)
    })

    async def run_speech():
        return await tts_service.speech_async(
            text=request.text,
            voice_id=request.voice_id,
            model=request.model,
            output_format=request.output_format,
            auto_upload_oss=True  # 自动上传到OSS
        )

    import asyncio
    try:
        asyncio.create_task(task_manager.submit_task(task_id, run_speech))
    except RuntimeError:
        def run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(task_manager.submit_task(task_id, run_speech))
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


@router.post("/speech/segments", response_model=TaskResponse)
async def text_segments_to_speech(
    request: SpeechSegmentsRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    分段文字转语音

    - **segments**: 分段文本列表
    - **voice_id**: 音色ID
    - **model**: TTS模型（可选）
    - **output_format**: 输出格式
    """
    user_db_id = Database.get_current_user_id()

    logger.info(f"收到分段语音合成请求，段数: {len(request.segments)}")

    task_id = task_manager.create_task("tts_segments", {
        "segment_count": len(request.segments)
    })

    async def run_speech():
        return await tts_service.speech_segments_async(
            segments=request.segments,
            voice_id=request.voice_id,
            model=request.model,
            output_format=request.output_format
        )

    import asyncio
    try:
        asyncio.create_task(task_manager.submit_task(task_id, run_speech))
    except RuntimeError:
        def run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(task_manager.submit_task(task_id, run_speech))
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


@router.post("/script", response_model=TaskResponse)
async def script_to_speech(
    request: TTSScriptRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    TTS脚本转语音

    同时生成完整版和分段音频

    - **full_text**: 完整台词
    - **segments**: 分段台词
    - **voice_id**: 音色ID
    - **model**: TTS模型（可选）
    """
    user_db_id = Database.get_current_user_id()

    logger.info(f"收到TTS脚本请求，段数: {len(request.segments)}")

    task_id = task_manager.create_task("tts_script", {
        "segment_count": len(request.segments)
    })

    async def run_speech():
        return await tts_service.script_to_speech_async(
            full_text=request.full_text,
            segments=request.segments,
            voice_id=request.voice_id,
            model=request.model
        )

    import asyncio
    try:
        asyncio.create_task(task_manager.submit_task(task_id, run_speech))
    except RuntimeError:
        def run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(task_manager.submit_task(task_id, run_speech))
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


@router.get("/task/{task_id}", response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    request_id: str = Depends(get_request_id)
):
    """
    查询TTS任务状态（通用）

    支持查询所有类型的TTS任务：
    - create_voice_from_file
    - tts_speech
    - tts_segments
    - tts_script
    """
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


@router.get("/speech/{task_id}", response_model=TaskResponse)
async def get_speech_task_status(
    task_id: str,
    request_id: str = Depends(get_request_id)
):
    """
    查询TTS语音合成任务状态（兼容前端）

    前端兼容接口，内部调用通用任务查询
    """
    logger.info(f"查询TTS任务: task_id={task_id}")

    task = task_manager.get_task(task_id)

    if not task:
        logger.warning(f"任务未找到: task_id={task_id}")
        raise HTTPException(status_code=404, detail="任务不存在或无权访问")

    logger.info(f"任务状态: task_id={task.task_id}, status={task.status}, progress={task.progress}, result={bool(task.result)}")
    
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


@router.get("/segments/{task_id}", response_model=TaskResponse)
async def get_segments_task_status(
    task_id: str,
    request_id: str = Depends(get_request_id)
):
    """
    查询TTS分段语音合成任务状态（兼容前端）
    
    前端兼容接口，内部调用通用任务查询
    """
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
