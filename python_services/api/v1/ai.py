"""
AI分析与脚本生成API路由
提供视频火爆原因分析、风格特征分析、脚本生成等接口
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List

from models.request import (
    AnalyzeViralRequest,
    AnalyzeStyleRequest,
    GenerateScriptRequest,
    FullAnalysisRequest
)
from models.response import (
    AnalysisResponse,
    ViralAnalysisResult,
    StyleAnalysisResult,
    GeneratedScript,
    TaskResponse,
    TaskStatus
)
from services.ai_service import AIService
from core.task_manager import task_manager
from core.logger import get_logger
from api.deps import get_request_id

logger = get_logger("api:ai")
router = APIRouter(prefix="/ai", tags=["AI分析"])

# 服务实例
ai_service = AIService()


@router.post("/analyze/viral", response_model=TaskResponse)
async def analyze_viral_factors(
    request: AnalyzeViralRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    火爆原因分析

    分析视频火爆的6个维度：
    - 话题热度
    - 情绪共鸣
    - 实用性
    - 娱乐性
    - 人设魅力
    - 表达技巧
    """
    logger.info(f"收到火爆原因分析请求，视频数: {len(request.video_data)}")

    task_id = task_manager.create_task("analyze_viral", {
        "video_count": len(request.video_data)
    })

    async def run_analysis():
        return await ai_service.analyze_viral_async(
            video_data=request.video_data,
            video_ids=request.video_ids
        )

    import asyncio
    try:
        asyncio.create_task(task_manager.submit_task(task_id, run_analysis))
    except RuntimeError:
        def run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(task_manager.submit_task(task_id, run_analysis))
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


@router.post("/analyze/style", response_model=TaskResponse)
async def analyze_style(
    request: AnalyzeStyleRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    风格特征分析

    分析维度：
    - 文案风格
    - 视频类型
    - 拍摄特征
    - 高频词汇
    - 标签策略
    - 音乐风格
    """
    logger.info(f"收到风格分析请求，维度: {request.analysis_dimensions}")

    task_id = task_manager.create_task("analyze_style", {
        "video_count": len(request.video_data)
    })

    async def run_analysis():
        return await ai_service.analyze_style_async(
            video_data=request.video_data,
            dimensions=request.analysis_dimensions
        )

    import asyncio
    try:
        asyncio.create_task(task_manager.submit_task(task_id, run_analysis))
    except RuntimeError:
        def run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(task_manager.submit_task(task_id, run_analysis))
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


@router.post("/generate/script", response_model=TaskResponse)
async def generate_script(
    request: GenerateScriptRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    生成TTS脚本

    根据参考风格数据和新主题生成视频脚本，包括：
    - 视频标题
    - 视频描述
    - 话题标签
    - 发布文案
    - 完整台词（含分段）
    """
    logger.info(f"收到脚本生成请求: {request.topic}")

    task_id = task_manager.create_task("generate_script", {
        "topic": request.topic
    })

    async def run_generation():
        return await ai_service.generate_script_async(
            style_analysis=request.style_analysis,
            viral_analysis=request.viral_analysis,
            topic=request.topic,
            target_duration=request.target_duration
        )

    import asyncio
    try:
        asyncio.create_task(task_manager.submit_task(task_id, run_generation))
    except RuntimeError:
        def run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(task_manager.submit_task(task_id, run_generation))
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


@router.post("/analyze/full", response_model=TaskResponse)
async def full_analysis(
    request: FullAnalysisRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    完整分析流程

    1. 从抖音URL抓取视频数据
    2. 进行火爆原因分析
    3. 进行风格特征分析
    4. 生成新主题脚本
    """
    logger.info(f"收到完整分析请求: {request.douyin_url} - {request.topic}")

    task_id = task_manager.create_task("full_analysis", {
        "url": request.douyin_url,
        "topic": request.topic
    })

    async def run_analysis():
        return await ai_service.full_analysis_async(
            douyin_url=request.douyin_url,
            topic=request.topic,
            max_videos=request.max_videos,
            enable_viral=request.enable_viral_analysis,
            enable_style=request.enable_style_analysis,
            generate_script=request.generate_script,
            target_duration=request.target_duration
        )

    import asyncio
    try:
        asyncio.create_task(task_manager.submit_task(task_id, run_analysis))
    except RuntimeError:
        def run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(task_manager.submit_task(task_id, run_analysis))
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
    """查询AI分析任务状态"""
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
