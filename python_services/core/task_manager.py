"""
异步任务管理器
管理长时间运行的任务（如视频生成、数据抓取等）
使用MySQL数据库进行任务持久化
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

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
    user_id: Optional[str] = None  # 用户ID，用于数据隔离

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
            "user_id": self.user_id,
        }


class TaskManager:
    """任务管理器（使用MySQL持久化）"""

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, Task] = {}
        self.tasks_by_type: Dict[str, Dict[str, Task]] = defaultdict(dict)
        self.running_tasks: set = set()
        self._lock = asyncio.Lock()

        # 启动时从数据库加载任务（如果数据库已连接）
        self._load_tasks_from_db()

    def load_from_db(self) -> int:
        """
        手动从数据库加载任务（数据库初始化后调用）

        Returns:
            加载的任务数量
        """
        return self._load_tasks_from_db(silent=False)

    def create_task(self, task_type: str, params: Optional[Dict[str, Any]] = None) -> str:
        """创建新任务（自动关联当前用户）"""
        from database import Database

        task_id = str(uuid.uuid4())
        user_db_id = Database.get_current_user_id()

        task = Task(
            task_id=task_id,
            task_type=task_type,
            user_id=str(user_db_id) if user_db_id else None
        )

        self.tasks[task_id] = task
        self.tasks_by_type[task_type][task_id] = task
        self._save_task_to_db(task, params)

        logger.info(f"创建任务: {task_type} - {task_id} (用户: {user_db_id})")
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

            # 更新数据库状态
            self._update_task_status_in_db(task_id, "running")

        try:
            # 执行任务 - coro 是一个可调用对象，需要先调用获取协程
            result = await coro()
            task.result = result
            task.status = TaskStatus.SUCCESS
            task.progress = 100
            logger.info(f"任务完成: {task_id}")

            # 更新数据库
            self._update_task_complete_in_db(task_id, result=result)

            # 自动保存生成的资源到资源表
            if result and task.task_type in ["chain_tts", "chain_tts_from_analysis", "chain_video", "tts_speech", "video_generate"]:
                self._save_resources_from_task(task_id, task.task_type, result)
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.error(f"任务失败: {task_id} - {e}")
            # 更新数据库
            self._update_task_complete_in_db(task_id, error=str(e))
        finally:
            async with self._lock:
                self.running_tasks.discard(task_id)
                task.completed_at = datetime.utcnow()

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务（Database 层自动过滤）"""
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
            # 更新数据库进度
            self._update_task_progress_in_db(task_id, progress)

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.CANCELLED
            self.running_tasks.discard(task_id)
            task.completed_at = datetime.utcnow()
            logger.info(f"任务已取消: {task_id}")
            # 更新数据库
            self._update_task_complete_in_db(task_id, status="cancelled")
            return True
        return False

    def _load_tasks_from_db(self, silent: bool = True) -> int:
        """
        从数据库加载任务

        Args:
            silent: 是否静默模式（不显示警告）

        Returns:
            加载的任务数量
        """
        count = 0
        try:
            from database import db
            if not db.is_connected():
                if not silent:
                    logger.warning("数据库未连接，跳过任务加载")
                return 0

            # 只加载最近的任务（避免内存占用过大）
            sql = """
                SELECT task_id, task_type, status, progress, result, error,
                       created_at, started_at, completed_at
                FROM tasks
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                ORDER BY created_at DESC
            """
            import json
            rows = db.fetch_all(sql)

            for row in rows:
                task = Task(
                    task_id=row["task_id"],
                    task_type=row["task_type"]
                )
                task.status = TaskStatus(row["status"])
                task.progress = row.get("progress", 0)

                # 解析JSON字段
                if row.get("result"):
                    if isinstance(row["result"], str):
                        task.result = json.loads(row["result"])
                    else:
                        task.result = row["result"]

                task.error = row.get("error")
                task.created_at = row["created_at"]
                task.started_at = row.get("started_at")
                task.completed_at = row.get("completed_at")

                self.tasks[task.task_id] = task
                self.tasks_by_type[task.task_type][task.task_id] = task

                # 如果任务是运行中状态，恢复为待处理（服务重启后需要重新执行）
                if task.status == TaskStatus.RUNNING:
                    task.status = TaskStatus.PENDING
                    task.started_at = None

                count += 1

            logger.info(f"从数据库加载了 {count} 个任务")
        except Exception as e:
            if not silent:
                logger.warning(f"从数据库加载任务失败: {e}")

        return count

    def _save_task_to_db(self, task: Task, params: Optional[Dict[str, Any]] = None) -> None:
        """保存任务到数据库"""
        try:
            from database import db, Database
            if not db.is_connected():
                return

            import json
            user_db_id = Database.get_current_user_id()

            sql = """
                INSERT INTO tasks (task_id, user_id, task_type, status, progress, input_params)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE status = VALUES(status)
            """
            db.execute(sql, (
                task.task_id,
                user_db_id,
                task.task_type,
                task.status.value,
                task.progress,
                json.dumps(params, ensure_ascii=False) if params else None
            ))
        except Exception as e:
            logger.warning(f"保存任务到数据库失败: {e}")

    def _update_task_status_in_db(self, task_id: str, status: str) -> None:
        """更新任务状态到数据库"""
        try:
            from database import db
            if not db.is_connected():
                return

            updates = ["status = %s"]
            params = [status]

            if status == "running":
                updates.append("started_at = CURRENT_TIMESTAMP")
            elif status in ("success", "failed", "cancelled"):
                updates.append("completed_at = CURRENT_TIMESTAMP")

            params.append(task_id)
            sql = f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = %s"
            db.execute(sql, tuple(params), skip_user_filter=True)
        except Exception as e:
            logger.warning(f"更新任务状态失败: {e}")

    def _update_task_progress_in_db(self, task_id: str, progress: int) -> None:
        """更新任务进度到数据库"""
        try:
            from database import db
            if not db.is_connected():
                return

            sql = "UPDATE tasks SET progress = %s WHERE task_id = %s"
            db.execute(sql, (progress, task_id), skip_user_filter=True)
        except Exception as e:
            logger.warning(f"更新任务进度失败: {e}")

    def _update_task_complete_in_db(
        self,
        task_id: str,
        status: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """更新任务完成状态到数据库"""
        try:
            from database import db
            if not db.is_connected():
                return

            import json
            updates = []
            params = []

            if status:
                updates.append("status = %s")
                params.append(status)
                if status in ("success", "failed", "cancelled"):
                    updates.append("completed_at = CURRENT_TIMESTAMP")

            if result:
                updates.append("result = %s")
                params.append(json.dumps(result, ensure_ascii=False))

            if error:
                updates.append("error = %s")
                params.append(error)

            params.append(task_id)
            sql = f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = %s"
            db.execute(sql, tuple(params), skip_user_filter=True)
        except Exception as e:
            logger.warning(f"更新任务完成状态失败: {e}")

    def _save_resources_from_task(self, task_id: str, task_type: str, result: Dict[str, Any]) -> None:
        """
        从任务结果中自动保存生成的资源

        Args:
            task_id: 任务ID
            task_type: 任务类型
            result: 任务结果
        """
        try:
            from database import db
            if not db.is_connected():
                return

            # 获取用户数据库ID
            sql = "SELECT user_id FROM tasks WHERE task_id = %s"
            task_row = db.fetch_one(sql, (task_id,))
            if not task_row:
                return

            user_db_id = task_row.get("user_id")
            if not user_db_id:
                return

            # 使用 ResourceDAO 保存资源
            from dao.resource_dao import ResourceDAO
            resource_ids = ResourceDAO.save_resources_from_task(
                user_db_id=user_db_id,
                task_id=task_id,
                task_type=task_type,
                result=result
            )

            if resource_ids:
                logger.info(f"任务 {task_id} 自动保存了 {len(resource_ids)} 个资源")
        except Exception as e:
            logger.warning(f"自动保存资源失败: {e}")

    def cleanup_old_tasks(self, days: int = 7) -> int:
        """清理旧任务（内存和数据库）"""
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

        # 清理数据库中的旧任务
        try:
            from database import db
            if db.is_connected():
                from dao.task_dao import TaskDAO
                db_count = TaskDAO.cleanup_old_tasks(days)
                logger.info(f"数据库清理了 {db_count} 个旧任务")
        except Exception as e:
            logger.warning(f"数据库清理失败: {e}")

        return len(to_remove)


# 全局任务管理器实例
task_manager = TaskManager(max_concurrent=5)
