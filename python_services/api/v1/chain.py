"""
任务串联API路由
基于 task_id 自动串联各个步骤，避免前端手动传递数据
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from pydantic import Field
from typing import Optional, List

from models.request import CommonRequest
from models.response import TaskResponse, TaskStatus
from services.ai_service import AIService
from services.tts_service import TTSService
from services.video_service import VideoService
from core.task_manager import task_manager
from core.task_helper import submit_background_task
from core.logger import get_logger
from api.deps import get_request_id

logger = get_logger("api:chain")
router = APIRouter(prefix="/chain", tags=["任务串联"])

# 服务实例
ai_service = AIService()
tts_service = TTSService()
video_service = VideoService()


# ==================== 请求模型 ====================

class AnalyzeFromFetchTaskRequest(CommonRequest):
    """根据抓取任务进行AI分析请求"""
    fetch_task_id: str  # 抓取任务的 task_id
    enable_viral: bool = True  # 是否进行火爆原因分析
    enable_style: bool = True  # 是否进行风格分析


class GenerateScriptFromAnalysisRequest(CommonRequest):
    """根据分析任务生成脚本请求"""
    analysis_task_id: str  # 分析任务的 task_id
    topic: str  # 新主题
    target_duration: float = 60.0  # 目标时长(秒)


class TTSFromScriptRequest(CommonRequest):
    """根据脚本任务进行TTS请求"""
    script_task_id: str  # 脚本生成任务的 task_id
    voice_id: str  # 音色ID
    model: Optional[str] = None  # TTS模型（可选）
    auto_upload_oss: bool = True  # 是否自动上传到OSS（默认True，用于视频生成）


class TTSFromAnalysisRequest(CommonRequest):
    """直接从分析任务生成TTS（跳过脚本生成步骤）"""
    analysis_task_id: str  # 分析任务的 task_id
    topic: str  # 新主题
    voice_id: str  # 音色ID
    target_duration: float = 60.0  # 目标时长(秒)
    model: Optional[str] = None  # TTS模型（可选）
    auto_upload_oss: bool = True  # 是否自动上传到OSS（默认True，用于视频生成）


class VideoFromTTSRequest(CommonRequest):
    """根据TTS任务生成视频请求"""
    tts_task_id: str  # TTS任务的 task_id
    ref_video_url: Optional[str] = None  # 参考视频URL（与ref_video_path二选一）
    ref_video_path: Optional[str] = None  # 本地参考视频路径
    video_extension: bool = True  # 是否扩展视频以匹配音频长度
    resolution: Optional[str] = None  # 分辨率（如 1280x720）


class GenerateFromProfileRequest(CommonRequest):
    """根据档案生成文案请求"""
    profile_id: str  # 档案ID
    generate_type: str = "video_script"  # video_script 或 text_copy
    topic: Optional[str] = None  # 可选的主题补充
    count: int = Field(3, ge=1, le=5, description="生成版本数量")


# ==================== 串联接口 ====================

@router.post("/analyze/from-fetch", response_model=TaskResponse)
async def analyze_from_fetch_task(
    request: AnalyzeFromFetchTaskRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    根据抓取任务ID自动进行AI分析

    流程：
    1. 从 douyin_fetch_tasks 表获取抓取任务信息
    2. 从 douyin_videos 表获取该任务抓取的视频数据
    3. 自动调用AI分析接口

    请求参数：
    - fetch_task_id: 抓取任务返回的 task_id
    - enable_viral: 是否进行火爆原因分析（默认True）
    - enable_style: 是否进行风格分析（默认True）

    返回：新的分析任务 task_id
    """
    try:
        # 1. 从数据库获取抓取任务信息
        from dao.douyin_dao import DouyinDAO
        from database import db

        fetch_task_sql = "SELECT * FROM douyin_fetch_tasks WHERE task_id = %s"
        fetch_task = db.fetch_one(fetch_task_sql, (request.fetch_task_id,))

        if not fetch_task:
            raise HTTPException(status_code=404, detail=f"抓取任务不存在: {request.fetch_task_id}")

        if fetch_task.get("status") != "completed":
            raise HTTPException(status_code=400, detail=f"抓取任务未完成，当前状态: {fetch_task.get('status')}")

        logger.info(f"找到抓取任务: {request.fetch_task_id}, 视频数量: {fetch_task.get('video_count', 0)}")

        # 2. 获取该任务抓取的视频数据
        # 通过 user_id 和时间范围获取视频（因为视频表没有直接关联 fetch_task_id）
        # 使用抓取任务的创建时间和用户ID来匹配
        videos_sql = """
            SELECT * FROM douyin_videos
            WHERE user_id = %s
            AND created_at >= %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        videos = db.fetch_all(videos_sql, (fetch_task["user_id"], fetch_task["created_at"], fetch_task.get("video_count", 100)))

        if not videos:
            raise HTTPException(status_code=404, detail="未找到该任务抓取的视频数据")

        logger.info(f"获取到 {len(videos)} 条视频数据")

        # 3. 转换为AI服务需要的格式
        video_data = []
        for video in videos:
            # 从 raw_data 解析，如果没有则使用字段值
            raw_data = video.get("raw_data")
            if isinstance(raw_data, dict):
                video_data.append(raw_data)
            else:
                # 构造基本格式
                video_data.append({
                    "aweme_id": video.get("aweme_id"),
                    "desc": video.get("description") or video.get("title", ""),
                    "author": {"nickname": video.get("author_name"), "uid": video.get("author_id")},
                    "statistics": {
                        "digg_count": 0,
                        "comment_count": 0,
                        "share_count": 0
                    },
                    "create_time": int(video.get("created_at").timestamp() * 1000) if video.get("created_at") else 0
                })

        # 4. 创建分析任务
        task_id = task_manager.create_task("chain_analyze", {
            "fetch_task_id": request.fetch_task_id,
            "enable_viral": request.enable_viral,
            "enable_style": request.enable_style,
            "video_count": len(video_data)
        })

        # 5. 执行分析
        async def run_analysis():
            result = {}
            video_ids = [v.get("aweme_id") for v in video_data]

            if request.enable_viral:
                logger.info("开始火爆原因分析...")
                viral_result = await ai_service.analyze_viral_async(
                    video_data=video_data,
                    video_ids=video_ids
                )
                result["viral_analysis"] = viral_result
                task_manager.update_progress(task_id, 50, "火爆原因分析完成")

            if request.enable_style:
                logger.info("开始风格分析...")
                style_result = await ai_service.analyze_style_async(
                    video_data=video_data,
                    dimensions=["文案风格", "视频类型", "拍摄特征", "高频词汇", "标签策略", "音乐风格"]
                )
                result["style_analysis"] = style_result
                task_manager.update_progress(task_id, 100, "风格分析完成")

            return result

        submit_background_task(task_id, run_analysis, background_tasks)

        task = task_manager.get_task(task_id)
        return TaskResponse(
            code=200,
            message="分析任务已创建",
            task_id=task_id,
            status=TaskStatus(task.status.value),
            progress=task.progress,
            created_at=task.created_at,
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建分析任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/from-analysis", response_model=TaskResponse)
async def generate_script_from_analysis(
    request: GenerateScriptFromAnalysisRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    根据分析任务ID自动生成脚本

    流程：
    1. 从 tasks 表获取分析任务结果
    2. 提取 style_analysis 和 viral_analysis
    3. 调用脚本生成接口

    请求参数：
    - analysis_task_id: 分析任务返回的 task_id
    - topic: 新主题
    - target_duration: 目标时长（秒）

    返回：新的脚本生成任务 task_id
    """
    try:
        # 1. 从数据库获取分析任务
        from dao.task_dao import TaskDAO
        from database import db

        analysis_task = TaskDAO.get_task(request.analysis_task_id)
        if not analysis_task:
            raise HTTPException(status_code=404, detail=f"分析任务不存在: {request.analysis_task_id}")

        if analysis_task.get("status") != "success":
            raise HTTPException(status_code=400, detail=f"分析任务未完成，当前状态: {analysis_task.get('status')}")

        # 2. 解析分析结果
        import json
        result_data = analysis_task.get("result")
        if isinstance(result_data, str):
            result_data = json.loads(result_data)

        if not result_data:
            raise HTTPException(status_code=404, detail="分析任务结果为空")

        style_analysis = result_data.get("style_analysis")
        viral_analysis = result_data.get("viral_analysis")

        if not style_analysis and not viral_analysis:
            raise HTTPException(status_code=400, detail="分析结果中缺少 style_analysis 或 viral_analysis")

        logger.info(f"获取到分析结果: style={bool(style_analysis)}, viral={bool(viral_analysis)}")

        # 3. 创建脚本生成任务
        task_id = task_manager.create_task("chain_generate_script", {
            "analysis_task_id": request.analysis_task_id,
            "topic": request.topic,
            "target_duration": request.target_duration
        })

        # 4. 执行脚本生成
        async def run_generation():
            return await ai_service.generate_script_async(
                style_analysis=style_analysis or {},
                viral_analysis=viral_analysis or {},
                topic=request.topic,
                target_duration=request.target_duration
            )

        submit_background_task(task_id, run_generation, background_tasks)

        task = task_manager.get_task(task_id)
        return TaskResponse(
            code=200,
            message="脚本生成任务已创建",
            task_id=task_id,
            status=TaskStatus(task.status.value),
            progress=task.progress,
            created_at=task.created_at,
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建脚本生成任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts/from-script", response_model=TaskResponse)
async def tts_from_script(
    request: TTSFromScriptRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    根据脚本任务ID自动进行TTS合成

    流程：
    1. 从 tasks 表获取脚本生成任务结果
    2. 提取 full_script 和 segments
    3. 调用TTS接口

    请求参数：
    - script_task_id: 脚本生成任务返回的 task_id
    - voice_id: 音色ID
    - model: TTS模型（可选）

    返回：新的TTS任务 task_id
    """
    try:
        # 1. 从数据库获取脚本任务
        from dao.task_dao import TaskDAO

        script_task = TaskDAO.get_task(request.script_task_id)
        if not script_task:
            raise HTTPException(status_code=404, detail=f"脚本任务不存在: {request.script_task_id}")

        if script_task.get("status") != "success":
            raise HTTPException(status_code=400, detail=f"脚本任务未完成，当前状态: {script_task.get('status')}")

        # 2. 解析脚本结果
        import json
        result_data = script_task.get("result")
        if isinstance(result_data, str):
            result_data = json.loads(result_data)

        if not result_data:
            raise HTTPException(status_code=404, detail="脚本任务结果为空")

        full_text = result_data.get("full_script") or result_data.get("full_text")
        segments = result_data.get("segments", [])

        if not full_text:
            raise HTTPException(status_code=400, detail="脚本结果中缺少 full_script 或 full_text")

        if not segments:
            # 如果没有分段，使用完整文本作为单段
            segments = [full_text]

        logger.info(f"获取到脚本: 字数={len(full_text)}, 分段数={len(segments)}")

        # 3. 创建TTS任务
        task_id = task_manager.create_task("chain_tts", {
            "script_task_id": request.script_task_id,
            "voice_id": request.voice_id,
            "segment_count": len(segments)
        })

        # 4. 执行TTS合成
        async def run_tts():
            result = await tts_service.script_to_speech_async(
                full_text=full_text,
                segments=segments,
                voice_id=request.voice_id,
                model=request.model,
                auto_upload_oss=request.auto_upload_oss  # 自动上传到OSS
            )
            # 确保返回包含预览URL
            result["preview_urls"] = {
                "audio": result.get("full_audio_oss_url") or result.get("full_audio"),
                "segments": result.get("segments_audio_oss", [])
            }
            return result

        submit_background_task(task_id, run_tts, background_tasks)

        task = task_manager.get_task(task_id)
        return TaskResponse(
            code=200,
            message="TTS任务已创建",
            task_id=task_id,
            status=TaskStatus(task.status.value),
            progress=task.progress,
            created_at=task.created_at,
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建TTS任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts/from-analysis", response_model=TaskResponse)
async def tts_from_analysis(
    request: TTSFromAnalysisRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    直接从分析任务生成TTS（合并步骤：先生成脚本再TTS）

    流程：
    1. 从 tasks 表获取分析任务结果
    2. 自动生成脚本
    3. 自动进行TTS合成

    请求参数：
    - analysis_task_id: 分析任务返回的 task_id
    - topic: 新主题
    - voice_id: 音色ID
    - target_duration: 目标时长（秒）
    - model: TTS模型（可选）

    返回：新的TTS任务 task_id
    """
    try:
        # 1. 从数据库获取分析任务
        from dao.task_dao import TaskDAO

        analysis_task = TaskDAO.get_task(request.analysis_task_id)
        if not analysis_task:
            raise HTTPException(status_code=404, detail=f"分析任务不存在: {request.analysis_task_id}")

        if analysis_task.get("status") != "success":
            raise HTTPException(status_code=400, detail=f"分析任务未完成，当前状态: {analysis_task.get('status')}")

        # 2. 解析分析结果
        import json
        result_data = analysis_task.get("result")
        if isinstance(result_data, str):
            result_data = json.loads(result_data)

        if not result_data:
            raise HTTPException(status_code=404, detail="分析任务结果为空")

        style_analysis = result_data.get("style_analysis")
        viral_analysis = result_data.get("viral_analysis")

        if not style_analysis and not viral_analysis:
            raise HTTPException(status_code=400, detail="分析结果中缺少 style_analysis 或 viral_analysis")

        # 3. 创建TTS任务（内部先生成脚本）
        task_id = task_manager.create_task("chain_tts_from_analysis", {
            "analysis_task_id": request.analysis_task_id,
            "topic": request.topic,
            "voice_id": request.voice_id,
            "target_duration": request.target_duration
        })

        # 4. 执行：生成脚本 + TTS
        async def run_tts_with_script():
            # 先生成脚本
            task_manager.update_progress(task_id, 10, "正在生成脚本...")
            script_result = await ai_service.generate_script_async(
                style_analysis=style_analysis or {},
                viral_analysis=viral_analysis or {},
                topic=request.topic,
                target_duration=request.target_duration
            )

            task_manager.update_progress(task_id, 50, "脚本生成完成，开始TTS合成...")

            # 再进行TTS
            full_text = script_result.get("full_script") or script_result.get("full_text")
            segments = script_result.get("segments", [])

            if not full_text:
                raise ValueError("脚本生成结果缺少 full_script")

            if not segments:
                segments = [full_text]

            tts_result = await tts_service.script_to_speech_async(
                full_text=full_text,
                segments=segments,
                voice_id=request.voice_id,
                model=request.model,
                auto_upload_oss=request.auto_upload_oss  # 自动上传到OSS
            )

            task_manager.update_progress(task_id, 100, "TTS合成完成")

            # 合并返回结果，包含预览URL
            return {
                "script": script_result,
                "tts": tts_result,
                "preview_urls": {
                    "audio": tts_result.get("full_audio_oss_url") or tts_result.get("full_audio"),
                    "segments": tts_result.get("segments_audio_oss", [])
                }
            }

        submit_background_task(task_id, run_tts_with_script, background_tasks)

        task = task_manager.get_task(task_id)
        return TaskResponse(
            code=200,
            message="TTS任务已创建（包含脚本生成）",
            task_id=task_id,
            status=TaskStatus(task.status.value),
            progress=task.progress,
            created_at=task.created_at,
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建TTS任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/from-tts", response_model=TaskResponse)
async def video_from_tts(
    request: VideoFromTTSRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    根据TTS任务ID自动生成视频

    流程：
    1. 从 tasks 表获取TTS任务结果
    2. 提取音频的 OSS URL（如果TTS时已上传）
    3. 如果没有 OSS URL，自动上传本地音频
    4. 调用视频生成接口

    请求参数：
    - tts_task_id: TTS任务返回的 task_id
    - ref_video_url: 参考视频URL（与ref_video_path二选一）
    - ref_video_path: 本地参考视频路径（会自动上传到OSS）
    - video_extension: 是否扩展视频以匹配音频长度
    - resolution: 分辨率（如 1280x720）

    返回：新的视频生成任务 task_id
    """
    try:
        # 1. 从数据库获取TTS任务
        from dao.task_dao import TaskDAO

        tts_task = TaskDAO.get_task(request.tts_task_id)
        if not tts_task:
            raise HTTPException(status_code=404, detail=f"TTS任务不存在: {request.tts_task_id}")

        if tts_task.get("status") != "success":
            raise HTTPException(status_code=400, detail=f"TTS任务未完成，当前状态: {tts_task.get('status')}")

        # 2. 解析TTS结果
        import json
        result_data = tts_task.get("result")
        if isinstance(result_data, str):
            result_data = json.loads(result_data)

        if not result_data:
            raise HTTPException(status_code=404, detail="TTS任务结果为空")

        # 获取音频URL（优先使用OSS URL）
        audio_url = result_data.get("full_audio_oss_url")
        audio_path = result_data.get("full_audio") or result_data.get("full_audio_path")

        if not audio_url and not audio_path:
            raise HTTPException(status_code=400, detail="TTS结果中缺少音频路径")

        if not audio_url and audio_path:
            logger.info(f"TTS结果为本地路径，将自动上传到OSS: {audio_path}")

        logger.info(f"准备生成视频: audio_url={bool(audio_url)}, audio_path={bool(audio_path)}")

        # 3. 创建视频生成任务
        task_id = task_manager.create_task("chain_video", {
            "tts_task_id": request.tts_task_id,
            "ref_video_url": request.ref_video_url,
            "video_extension": request.video_extension
        })

        # 4. 执行视频生成
        async def run_video():
            result = await video_service.generate_video_async(
                audio_url=audio_url,
                audio_path=audio_path if not audio_url else None,
                video_url=request.ref_video_url,
                video_path=request.ref_video_path,
                video_extension=request.video_extension,
                resolution=request.resolution,
                auto_upload=True,
                progress_callback=lambda p, msg: task_manager.update_progress(task_id, p, msg)
            )
            # 确保返回包含所有预览URL
            result["preview_urls"] = {
                "video": result.get("video_url"),
                "audio": result.get("input_urls", {}).get("audio_url") or audio_url
            }
            return result

        submit_background_task(task_id, run_video, background_tasks)

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建视频生成任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}", response_model=TaskResponse)
async def get_chain_task_status(
    task_id: str,
    request_id: str = Depends(get_request_id)
):
    """查询串联任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或无权访问")

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


@router.post("/generate-from-profile", response_model=TaskResponse)
async def generate_from_profile(
    request: GenerateFromProfileRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    根据档案生成文案（支持短视频脚本和纯文字文案）

    流程：
    1. 从 profiles 表获取档案信息
    2. 组装 prompt 发送给大模型
    3. 返回 3 个版本的文案供用户选择

    请求参数：
    - profile_id: 档案ID
    - generate_type: video_script（短视频脚本）或 text_copy（纯文字文案）
    - topic: 可选的主题补充
    - count: 生成版本数量（默认3）

    返回：任务 task_id，任务完成后 result 中包含多个版本的文案
    """
    try:
        from dao.profile_dao import ProfileDAO

        # 0. 参数校验
        if request.generate_type not in ("video_script", "text_copy"):
            raise HTTPException(status_code=400, detail="generate_type 必须是 video_script 或 text_copy")

        # 1. 获取档案
        profile = ProfileDAO.get_profile(request.profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"档案不存在: {request.profile_id}")

        logger.info(f"从档案生成文案: profile={request.profile_id}, type={request.generate_type}")

        # 2. 组装 prompt
        type_desc = "短视频脚本（含分镜、台词、时长建议）" if request.generate_type == "video_script" else "纯文字文案（适合社交媒体发布）"

        topic_section = f"\n补充主题：{request.topic}" if request.topic else ""

        reference_section = ""
        if profile.get("video_url"):
            reference_section += f"\n- 参考视频：{profile['video_url']}"
        if profile.get("homepage_url"):
            reference_section += f"\n- 参考主页：{profile['homepage_url']}"

        prompt = f"""你是一个专业的内容策划师，请根据以下档案信息生成{type_desc}：

行业：{profile['industry']}
目标用户群体：{profile['target_audience']}
客户痛点：{profile['customer_pain_points']}
解决方案：{profile['solution']}
人设背景：{profile['persona_background']}
{reference_section}{topic_section}

请生成 {request.count} 个不同风格的版本，每个版本之间用 "---VERSION---" 分隔。
每个版本应包含：标题、正文内容。"""

        # 3. 创建任务
        task_id = task_manager.create_task("chain_generate_from_profile", {
            "profile_id": request.profile_id,
            "generate_type": request.generate_type,
            "count": request.count
        })

        # 4. 调用大模型
        async def run_generation():
            from core.config import settings
            import httpx

            # 获取 LLM 配置
            api_key = settings.get("DASHSCOPE_API_KEY", "")
            base_url = settings.get("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            model = settings.get("LLM_MODEL", "qwen-plus")

            if not api_key:
                raise ValueError("未配置 LLM API Key")

            task_manager.update_progress(task_id, 20, "正在调用大模型...")

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "你是一个专业的内容策划师，擅长根据用户档案信息生成高质量的短视频脚本和文案。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.8,
                    }
                )
                response.raise_for_status()
                result = response.json()

            content = result["choices"][0]["message"]["content"]
            task_manager.update_progress(task_id, 80, "文案生成完成，正在解析...")

            # 解析多个版本
            versions = [v.strip() for v in content.split("---VERSION---") if v.strip()]

            # 如果分隔符没生效，按整体返回一个版本
            if len(versions) <= 1:
                versions = [content.strip()]

            result_data = {
                "versions": [
                    {"index": i + 1, "content": v}
                    for i, v in enumerate(versions[:request.count])
                ],
                "profile_id": request.profile_id,
                "generate_type": request.generate_type,
            }

            task_manager.update_progress(task_id, 100, "完成")
            return result_data

        submit_background_task(task_id, run_generation, background_tasks)

        task = task_manager.get_task(task_id)
        return TaskResponse(
            code=200,
            message="文案生成任务已创建",
            task_id=task_id,
            status=TaskStatus(task.status.value),
            progress=task.progress,
            created_at=task.created_at,
            request_id=request_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从档案生成文案失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
