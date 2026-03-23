"""
抖音数据抓取API路由
提供抖音用户视频、话题视频、热榜等数据抓取接口
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List

from models.request import (
    FetchUserVideosRequest,
    FetchTopicVideosRequest,
    FetchHotListRequest
)
from models.response import FetchVideosResponse, TaskResponse, TaskStatus
from services.douyin_service import DouyinService
from core.task_manager import task_manager
from core.logger import get_logger
from api.deps import get_request_id

logger = get_logger("api:douyin")
router = APIRouter(prefix="/douyin", tags=["抖音抓取"])

# 服务实例
douyin_service = DouyinService()


@router.post("/fetch/user", response_model=TaskResponse)
async def fetch_user_videos(
    request: FetchUserVideosRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    抓取用户视频

    - **url**: 抖音用户主页URL
    - **max_count**: 最大抓取数量 (1-200)
    - **enable_filter**: 是否启用过滤
    - **min_likes**: 最小点赞数
    - **min_comments**: 最小评论数
    - **top_n**: 返回Top N热门视频 (0=全部)
    - **sort_by**: 排序字段 (like/comment/share)
    - **wait**: 是否等待完成后直接返回结果（默认false，异步返回task_id）

    返回任务ID，可通过 /task/{task_id} 查询进度
    如果 wait=true，则等待完成后直接返回结果
    """
    try:
        logger.info(f"收到用户视频抓取请求: {request.url}, wait={request.wait}")

        # 如果 wait=true，直接同步执行并返回结果
        if request.wait:
            logger.info("同步模式：等待任务完成...")
            result = await douyin_service.fetch_user_videos_async(
                url=request.url,
                max_count=request.max_count,
                enable_filter=request.enable_filter,
                min_likes=request.min_likes,
                min_comments=request.min_comments,
                top_n=request.top_n,
                sort_by=request.sort_by,
                progress_callback=None
            )
            # 直接返回完整结果
            return TaskResponse(
                code=200,
                message="success",
                task_id="sync",
                status=TaskStatus.SUCCESS,
                progress=100,
                result=result,
                request_id=request_id
            )

        # 异步模式：创建任务
        task_id = task_manager.create_task("fetch_user_videos", {
            "url": request.url,
            "max_count": request.max_count,
            "enable_filter": request.enable_filter,
            "top_n": request.top_n
        })

        # 提交后台任务 - 直接执行异步逻辑
        async def run_fetch():
            try:
                task_manager.update_progress(task_id, 10, "开始抓取...")
                result = await douyin_service.fetch_user_videos_async(
                    url=request.url,
                    max_count=request.max_count,
                    enable_filter=request.enable_filter,
                    min_likes=request.min_likes,
                    min_comments=request.min_comments,
                    top_n=request.top_n,
                    sort_by=request.sort_by,
                    progress_callback=lambda p, msg: task_manager.update_progress(task_id, p, msg)
                )
                task_manager.update_progress(task_id, 100, "抓取完成")
                return result
            except Exception as e:
                logger.error(f"抓取任务失败: {e}")
                task_manager.update_progress(task_id, 0, f"抓取失败: {e}")
                raise

        # 在后台执行异步任务
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # 如果已有运行中的事件循环，使用 create_task
            asyncio.create_task(task_manager.submit_task(task_id, run_fetch))
        except RuntimeError:
            # 没有运行中的事件循环，使用 BackgroundTasks
            def run_in_new_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(task_manager.submit_task(task_id, run_fetch))
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
        logger.error(f"创建抓取任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}", response_model=TaskResponse)
async def get_fetch_task_status(
    task_id: str,
    request_id: str = Depends(get_request_id)
):
    """查询抓取任务状态"""
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


@router.post("/fetch/topic", response_model=TaskResponse)
async def fetch_topic_videos(
    request: FetchTopicVideosRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    抓取话题视频

    - **topic**: 话题名称
    - **max_count**: 最大抓取数量
    """
    logger.info(f"收到话题视频抓取请求: {request.topic}")

    task_id = task_manager.create_task("fetch_topic_videos", {
        "topic": request.topic,
        "max_count": request.max_count
    })

    async def run_fetch():
        return await douyin_service.fetch_topic_videos_async(
            topic=request.topic,
            max_count=request.max_count
        )

    import asyncio
    try:
        asyncio.create_task(task_manager.submit_task(task_id, run_fetch))
    except RuntimeError:
        def run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(task_manager.submit_task(task_id, run_fetch))
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


@router.post("/fetch/hotlist", response_model=TaskResponse)
async def fetch_hot_list(
    request: FetchHotListRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    抓取抖音热榜

    - **cate_id**: 分类ID (可选)
    """
    logger.info("收到热榜抓取请求")

    task_id = task_manager.create_task("fetch_hotlist", {
        "cate_id": request.cate_id
    })

    async def run_fetch():
        return await douyin_service.fetch_hot_list_async(cate_id=request.cate_id)

    background_tasks.add_task(task_manager.submit_task, task_id, run_fetch())

    task = task_manager.get_task(task_id)
    return TaskResponse(
        task_id=task_id,
        status=TaskStatus(task.status.value),
        progress=task.progress,
        created_at=task.created_at,
        request_id=request_id
    )


@router.get("/videos", response_model=FetchVideosResponse)
async def get_cached_videos(
    limit: int = 100,
    offset: int = 0,
    request_id: str = Depends(get_request_id)
):
    """
    获取已缓存的视频数据

    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    try:
        videos = douyin_service.get_cached_videos(limit=limit, offset=offset)
        total = douyin_service.get_cached_count()

        return FetchVideosResponse(
            data=videos,
            total=total,
            filtered_count=len(videos),
            request_id=request_id
        )
    except Exception as e:
        logger.error(f"获取缓存视频失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
