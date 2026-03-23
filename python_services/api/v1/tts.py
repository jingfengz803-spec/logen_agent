"""
TTS语音合成API路由
提供音色创建、语音合成等接口
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List, Optional

from models.request import (
    CreateVoiceRequest,
    CreateVoiceWithPreviewRequest,
    SpeechRequest,
    SpeechSegmentsRequest,
    TTSScriptRequest
)
from models.response import (
    CreateVoiceResponse,
    VoiceListResponse,
    VoiceInfo,
    SpeechResponse,
    TTSScriptResponse,
    TaskResponse,
    TaskStatus
)
from services.tts_service import TTSService
from core.task_manager import task_manager
from core.logger import get_logger
from api.deps import get_request_id

logger = get_logger("api:tts")
router = APIRouter(prefix="/tts", tags=["TTS语音"])

# 服务实例
tts_service = TTSService()


@router.post("/voice/create", response_model=TaskResponse)
async def create_voice(
    request: CreateVoiceRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    创建音色复刻

    - **audio_url**: 音色音频公网URL
    - **prefix**: 音色前缀
    - **model**: TTS模型
    - **wait_ready**: 是否等待音色就绪
    """
    logger.info(f"收到音色创建请求: {request.prefix}")

    task_id = task_manager.create_task("create_voice", {
        "prefix": request.prefix,
        "model": request.model
    })

    async def run_create():
        return await tts_service.create_voice_async(
            audio_url=request.audio_url,
            prefix=request.prefix,
            model=request.model,
            language_hints=request.language_hints,
            wait_ready=request.wait_ready
        )

    # 在后台执行异步任务
    import asyncio
    try:
        loop = asyncio.get_running_loop()
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


@router.post("/voice/create-with-preview", response_model=TaskResponse)
async def create_voice_with_preview(
    request: CreateVoiceWithPreviewRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    创建音色并生成试听音频

    流程：
    1. 上传音频文件到OSS获取公网URL
    2. 创建音色复刻（得到voice_id）
    3. 用新音色合成试听文本
    4. 返回试听音频URL供用户试听

    - **audio_url**: 音色音频公网URL
    - **prefix**: 音色前缀
    - **model**: TTS模型
    - **preview_text**: 试听文本（默认："你好，这是我的音色。"）
    - **auto_upload_oss**: 是否自动上传试听音频到OSS（默认True）

    用户试听后：
    - 满意 → 保存voice_id，后续TTS使用
    - 不满意 → 重新调用此接口
    """
    logger.info(f"收到音色创建（含试听）请求: {request.prefix}")

    task_id = task_manager.create_task("create_voice_preview", {
        "prefix": request.prefix,
        "model": request.model
    })

    async def run_create():
        return await tts_service.create_voice_with_preview_async(
            audio_url=request.audio_url,
            prefix=request.prefix,
            model=request.model,
            language_hints=request.language_hints,
            preview_text=request.preview_text,
            auto_upload_oss=request.auto_upload_oss
        )

    # 在后台执行异步任务
    import asyncio
    try:
        loop = asyncio.get_running_loop()
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


@router.get("/voice/list", response_model=VoiceListResponse)
async def list_voices(
    request_id: str = Depends(get_request_id)
):
    """
    获取音色列表

    返回所有已创建的音色及其状态
    """
    try:
        voices = await tts_service.list_voices_async()

        voice_infos = []
        for v in voices:
            voice_id = v.get("voice_id", "")
            # 从 voice_id 中提取 prefix（音色名称部分）
            # voice_id 格式: cosyvoice-v3.5-flash-prefix-xxx
            prefix = ""
            if voice_id:
                parts = voice_id.split('-')
                if len(parts) >= 5:
                    # cosyvoice-v3.5-flash-prefix-xxx -> prefix 是第4部分
                    prefix = parts[3]
                elif len(parts) >= 4:
                    # cosyvoice-v1-prefix-xxx -> prefix 是第3部分
                    prefix = parts[2]
            
            voice_infos.append(VoiceInfo(
                voice_id=voice_id,
                prefix=prefix or v.get("prefix", ""),
                model=v.get("target_model", ""),
                status=v.get("status", "UNKNOWN"),
                created_at=v.get("gmt_create", ""),
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
    """查询单个音色状态"""
    try:
        voice = await tts_service.get_voice_async(voice_id)
        if not voice:
            raise HTTPException(status_code=404, detail="音色不存在")

        vid = voice.get("voice_id", voice_id)
        # 从 voice_id 中提取 prefix
        prefix = ""
        if vid:
            parts = vid.split('-')
            if len(parts) >= 5:
                prefix = parts[3]
            elif len(parts) >= 4:
                prefix = parts[2]

        voice_info = VoiceInfo(
            voice_id=vid,
            prefix=prefix or voice.get("prefix", ""),
            model=voice.get("target_model", ""),
            status=voice.get("status", "UNKNOWN"),
            created_at=voice.get("gmt_create", ""),
            is_available=voice.get("status") == "OK"
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


@router.post("/speech", response_model=TaskResponse)
async def text_to_speech(
    request: SpeechRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    文字转语音

    - **text**: 要合成的文本
    - **voice_id**: 音色ID
    - **model**: TTS模型（可选，默认使用音色对应模型）
    - **output_format**: 输出格式
    """
    logger.info(f"收到语音合成请求，字数: {len(request.text)}")

    task_id = task_manager.create_task("tts_speech", {
        "text_length": len(request.text)
    })

    async def run_speech():
        return await tts_service.speech_async(
            text=request.text,
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
    - **model**: TTS模型
    - **output_format**: 输出格式
    """
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
    - **model**: TTS模型
    """
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
    """查询TTS任务状态"""
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
    """查询TTS语音合成任务状态（兼容前端使用的路径）"""
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


@router.get("/segments/{task_id}", response_model=TaskResponse)
async def get_segments_task_status(
    task_id: str,
    request_id: str = Depends(get_request_id)
):
    """查询TTS分段语音合成任务状态（兼容前端使用的路径）"""
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
