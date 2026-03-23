"""
异步任务管理器
管理长时间运行的任务（如视频生成、数据抓取等）
支持任务持久化到文件
"""

import asyncio
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

from .logger import get_logger

logger = get_logger("task_manager")


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"       # 待处理
    RUNNING = "running"       # 运行中
    SUCCESS = "success"       # 成功
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消


@dataclass
class Task:
    """任务数据类"""
    task_id: str
    task_type: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class TaskManager:
    """任务管理器（支持持久化）"""

    def __init__(self, max_concurrent: int = 5, persist_file: Optional[str] = None):
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, Task] = {}
        self.tasks_by_type: Dict[str, Dict[str, Task]] = defaultdict(dict)
        self.running_tasks: set = set()
        self._lock = asyncio.Lock()
        self._persist_file = Path(persist_file) if persist_file else None

        # 启动时加载已保存的任务
        if self._persist_file:
            self._load_tasks()

    def create_task(self, task_type: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        创建新任务

        Args:
            task_type: 任务类型
            params: 任务参数

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            task_type=task_type
        )

        self.tasks[task_id] = task
        self.tasks_by_type[task_type][task_id] = task

        logger.info(f"创建任务: {task_type} - {task_id}")
        return task_id

    async def submit_task(
        self,
        task_id: str,
        coro: Callable[[], Awaitable[Dict[str, Any]]]
    ) -> None:
        """
        提交任务执行

        Args:
            task_id: 任务ID
            coro: 异步协程函数
        """
        async with self._lock:
            if len(self.running_tasks) >= self.max_concurrent:
                logger.warning(f"达到最大并发任务数: {self.max_concurrent}")
                return

            task = self.tasks.get(task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return

            self.running_tasks.add(task_id)
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()

        try:
            # 执行任务 - coro 是一个可调用对象，需要先调用获取协程
            result = await coro()
            task.result = result
            task.status = TaskStatus.SUCCESS
            task.progress = 100
            logger.info(f"任务完成: {task_id}")
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.error(f"任务失败: {task_id} - {e}")
        finally:
            async with self._lock:
                self.running_tasks.discard(task_id)
                task.completed_at = datetime.utcnow()
            # 任务状态变更后保存
            self._save_tasks()

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)

    def get_tasks_by_type(self, task_type: str) -> list[Task]:
        """按类型获取任务"""
        return list(self.tasks_by_type.get(task_type, {}).values())

    def update_progress(self, task_id: str, progress: int, message: str = "") -> None:
        """更新任务进度"""
        task = self.tasks.get(task_id)
        if task:
            task.progress = min(100, max(0, progress))
            if message:
                logger.info(f"任务进度: {task_id} - {progress}% - {message}")

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.CANCELLED
            self.running_tasks.discard(task_id)
            task.completed_at = datetime.utcnow()
            logger.info(f"任务已取消: {task_id}")
            self._save_tasks()
            return True
        return False

    def _save_tasks(self) -> None:
        """保存任务到文件"""
        if not self._persist_file:
            return

        try:
            self._persist_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                task_id: task.to_dict()
                for task_id, task in self.tasks.items()
            }
            with open(self._persist_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存任务失败: {e}")

    def _load_tasks(self) -> None:
        """从文件加载任务"""
        if not self._persist_file or not self._persist_file.exists():
            return

        try:
            with open(self._persist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for task_id, task_data in data.items():
                task = Task(
                    task_id=task_data["task_id"],
                    task_type=task_data["task_type"]
                )
                task.status = TaskStatus(task_data["status"])
                task.progress = task_data.get("progress", 0)
                task.result = task_data.get("result")
                task.error = task_data.get("error")
                task.created_at = datetime.fromisoformat(task_data["created_at"])
                task.started_at = datetime.fromisoformat(task_data["started_at"]) if task_data.get("started_at") else None
                task.completed_at = datetime.fromisoformat(task_data["completed_at"]) if task_data.get("completed_at") else None

                self.tasks[task_id] = task
                self.tasks_by_type[task.task_type][task_id] = task

                # 如果任务是运行中状态，恢复为待处理（服务重启后需要重新执行）
                if task.status == TaskStatus.RUNNING:
                    task.status = TaskStatus.PENDING
                    task.started_at = None

            logger.info(f"从文件加载了 {len(self.tasks)} 个任务")
        except Exception as e:
            logger.warning(f"加载任务失败: {e}")

    def cleanup_old_tasks(self, days: int = 7) -> int:
        """清理旧任务"""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        to_remove = [
            tid for tid, task in self.tasks.items()
            if task.completed_at and task.completed_at < cutoff
        ]

        for tid in to_remove:
            task = self.tasks[tid]
            self.tasks_by_type[task.task_type].pop(tid, None)
            self.tasks.pop(tid)

        logger.info(f"清理了 {len(to_remove)} 个旧任务")
        # 清理后保存
        self._save_tasks()
        return len(to_remove)


# 全局任务管理器实例
# 使用持久化文件，服务重启后任务不会丢失
import os
TEMP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/temp"
task_manager = TaskManager(
    max_concurrent=5,
    persist_file=f"{TEMP_DIR}/tasks.json"
)
