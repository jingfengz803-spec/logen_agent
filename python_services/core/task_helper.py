"""后台任务提交工具，统一封装 asyncio.create_task / BackgroundTasks 双重调度"""
import asyncio
from typing import Callable, Awaitable, Dict, Any, Optional
from starlette.background import BackgroundTasks
from core.task_manager import task_manager
from core.logger import get_logger

logger = get_logger("task_helper")


def submit_background_task(
    task_id: str,
    coro_factory: Callable[[], Awaitable[Dict[str, Any]]],
    background_tasks: Optional[BackgroundTasks] = None,
) -> None:
    """
    统一提交后台异步任务。

    优先使用 asyncio.create_task；如果没有运行中的事件循环，
    则回退到 BackgroundTasks + 新建事件循环执行。
    """
    try:
        asyncio.create_task(task_manager.submit_task(task_id, coro_factory))
    except RuntimeError:
        if background_tasks is not None:
            def _run():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(task_manager.submit_task(task_id, coro_factory))
                finally:
                    loop.close()
            background_tasks.add_task(_run)
        else:
            logger.warning(f"任务 {task_id} 无事件循环且无 background_tasks，跳过执行")
