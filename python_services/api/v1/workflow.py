"""
完整工作流API路由
提供从抖音抓取到视频生成的完整流程接口
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from models.request import FullWorkflowRequest, WorkflowType
from models.response import WorkflowResponse, TaskStatus
from services.workflow_service import WorkflowService
from core.task_manager import task_manager
from core.logger import get_logger
from api.deps import get_request_id

logger = get_logger("api:workflow")
router = APIRouter(prefix="/workflow", tags=["完整工作流"])

# 服务实例
workflow_service = WorkflowService()


@router.post("/run", response_model=WorkflowResponse)
async def run_workflow(
    request: FullWorkflowRequest,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id)
):
    """
    运行完整工作流

    工作流步骤：
    1. 抓取抖音视频数据
    2. AI分析（火爆原因 + 风格特征）
    3. 生成新主题脚本
    4. TTS语音合成
    5. 视频生成（可选）

    - **douyin_url**: 抖音用户主页URL
    - **topic**: 新主题
    - **voice_id**: 音色ID（可选）
    - **ref_video_url**: 参考视频URL（可选）
    - **workflow_type**: 工作流类型
      - full: 完整流程（含视频）
      - without_video: 不含视频
      - analysis_only: 仅分析
    - **max_videos**: 分析视频数量
    - **output_name**: 输出文件名前缀
    """
    logger.info(f"收到工作流请求: {request.workflow_type.value}")

    task_id = task_manager.create_task("workflow", {
        "type": request.workflow_type.value,
        "topic": request.topic
    })

    async def run_workflow_task():
        return await workflow_service.run_workflow_async(
            douyin_url=request.douyin_url,
            topic=request.topic,
            voice_id=request.voice_id,
            ref_video_url=request.ref_video_url,
            workflow_type=request.workflow_type,
            max_videos=request.max_videos,
            output_name=request.output_name,
            progress_callback=lambda p, msg: task_manager.update_progress(task_id, p, msg)
        )

    import asyncio
    try:
        asyncio.create_task(task_manager.submit_task(task_id, run_workflow_task))
    except RuntimeError:
        def run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(task_manager.submit_task(task_id, run_workflow_task))
            finally:
                new_loop.close()
        background_tasks.add_task(run_in_new_loop)

    task = task_manager.get_task(task_id)
    return WorkflowResponse(
        task_id=task_id,
        status=TaskStatus(task.status.value),
        progress=task.progress,
        current_step="初始化",
        request_id=request_id
    )


@router.get("/task/{task_id}", response_model=WorkflowResponse)
async def get_workflow_status(
    task_id: str,
    request_id: str = Depends(get_request_id)
):
    """
    查询工作流任务状态

    返回任务进度、当前步骤、部分结果等
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    current_step = "待处理"
    if task.status.value == "running":
        progress = task.progress
        if progress < 20:
            current_step = "抓取抖音数据"
        elif progress < 50:
            current_step = "AI分析中"
        elif progress < 70:
            current_step = "生成脚本"
        elif progress < 90:
            current_step = "TTS合成"
        else:
            current_step = "生成视频"

    return WorkflowResponse(
        task_id=task_id,
        status=TaskStatus(task.status.value),
        progress=task.progress,
        current_step=current_step,
        result=task.result,
        request_id=request_id
    )


@router.delete("/task/{task_id}")
async def cancel_workflow(
    task_id: str,
    request_id: str = Depends(get_request_id)
):
    """取消工作流任务"""
    success = task_manager.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="无法取消该任务")

    return {
        "code": 200,
        "message": "任务已取消",
        "request_id": request_id
    }


@router.get("/templates")
async def get_workflow_templates(request_id: str = Depends(get_request_id)):
    """
    获取工作流模板

    返回预设的工作流配置模板
    """
    templates = [
        {
            "id": "quick",
            "name": "快速分析",
            "description": "仅进行AI分析和脚本生成",
            "workflow_type": "analysis_only",
            "max_videos": 50
        },
        {
            "id": "standard",
            "name": "标准流程",
            "description": "分析+脚本+TTS",
            "workflow_type": "without_video",
            "max_videos": 100
        },
        {
            "id": "full",
            "name": "完整流程",
            "description": "分析+脚本+TTS+视频",
            "workflow_type": "full",
            "max_videos": 100,
            "requires_voice": True,
            "requires_ref_video": True
        }
    ]

    return {
        "code": 200,
        "message": "success",
        "data": templates,
        "request_id": request_id
    }
