"""
任务数据访问层
统一管理所有任务（TTS、视频、抖音抓取等）
"""

from typing import Optional, List, Dict, Any
from database import db
from core.logger import get_logger
import json
from datetime import datetime

logger = get_logger("dao:task")


class TaskDAO:
    """任务数据访问对象"""

    @staticmethod
    def init_table():
        """初始化任务表（如果需要额外的）"""
        # 任务表已在 models/db.py 中定义
        pass

    @staticmethod
    def create_task(task_id: str, user_db_id: Optional[int], task_type: str,
                    input_params: Dict = None) -> int:
        """
        创建任务记录

        Args:
            task_id: 任务唯一标识
            user_db_id: 用户数据库 ID（可为 None）
            task_type: 任务类型
            input_params: 输入参数

        Returns:
            新记录 ID
        """
        sql = """
            INSERT INTO tasks (task_id, user_id, task_type, input_params)
            VALUES (%s, %s, %s, %s)
        """
        return db.insert_return_id(sql, (
            task_id,
            user_db_id,
            task_type,
            json.dumps(input_params) if input_params else None
        ))

    @staticmethod
    def get_task(task_id: str, skip_user_filter: bool = False) -> Optional[Dict]:
        """
        获取任务信息

        Args:
            task_id: 任务 ID
            skip_user_filter: 是否跳过用户过滤（启动迁移等场景）

        Returns:
            任务信息或 None
        """
        sql = "SELECT * FROM tasks WHERE task_id = %s"
        return db.fetch_one(sql, (task_id,), skip_user_filter=skip_user_filter)

    @staticmethod
    def update_task_status(task_id: str, status: str = None, progress: int = None,
                           result: Dict = None, error: str = None):
        """更新任务状态"""
        updates = []
        params = []

        if status:
            updates.append("status = %s")
            params.append(status)
            if status == "running":
                updates.append("started_at = CURRENT_TIMESTAMP")
            elif status in ("success", "failed", "cancelled"):
                updates.append("completed_at = CURRENT_TIMESTAMP")

        if progress is not None:
            updates.append("progress = %s")
            params.append(progress)

        if result:
            updates.append("result = %s")
            params.append(json.dumps(result, ensure_ascii=False))

        if error:
            updates.append("error = %s")
            params.append(error)

        params.append(task_id)

        sql = f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = %s"
        db.execute(sql, tuple(params))

    @staticmethod
    def get_user_tasks(task_type: str = None,
                       status: str = None, limit: int = 100) -> List[Dict]:
        """
        获取当前用户的任务列表（Database 自动按 user_id 过滤）

        Args:
            task_type: 任务类型过滤
            status: 状态过滤
            limit: 返回数量限制

        Returns:
            任务列表
        """
        conditions = []
        params = []

        if task_type:
            conditions.append("task_type = %s")
            params.append(task_type)

        if status:
            conditions.append("status = %s")
            params.append(status)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        sql = f"""
            SELECT * FROM tasks
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s
        """
        params.append(limit)
        return db.fetch_all(sql, tuple(params))

    @staticmethod
    def get_task_stats() -> Dict:
        """
        获取任务统计信息（Database 自动按 user_id 过滤）

        Returns:
            统计信息字典
        """
        sql = """
            SELECT
                task_type,
                status,
                COUNT(*) as count
            FROM tasks
            GROUP BY task_type, status
        """
        return db.fetch_all(sql)

    @staticmethod
    def get_recent_tasks(limit: int = 50) -> List[Dict]:
        """获取最近的任务"""
        sql = """
            SELECT t.*, u.username
            FROM tasks t
            LEFT JOIN users u ON t.user_id = u.id
            ORDER BY t.created_at DESC
            LIMIT %s
        """
        return db.fetch_all(sql, (limit,), skip_user_filter=True)

    @staticmethod
    def cleanup_old_tasks(days: int = 7) -> int:
        """
        清理旧任务

        Args:
            days: 保留天数

        Returns:
            删除的数量
        """
        sql = """
            DELETE FROM tasks
            WHERE completed_at < DATE_SUB(NOW(), INTERVAL %s DAY)
            AND status IN ('success', 'failed', 'cancelled')
        """
        return db.execute(sql, (days,))

    @staticmethod
    def sync_from_json(json_file_path: str, user_map: Dict[str, int] = None):
        """
        从 JSON 文件同步任务到数据库

        Args:
            json_file_path: JSON 文件路径
            user_map: user_id 映射字典 {"user_id": db_id}
        """
        import json
        from pathlib import Path

        json_path = Path(json_file_path)
        if not json_path.exists():
            logger.warning(f"JSON 文件不存在: {json_file_path}")
            return

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for task_id, task_data in data.items():
            if isinstance(task_data, dict):
                user_id = task_data.get("user_id")
                db_user_id = user_map.get(user_id) if user_map and user_id else None

                # 检查是否已存在
                existing = TaskDAO.get_task(task_id, skip_user_filter=True)
                if not existing:
                    TaskDAO.create_task(
                        task_id=task_id,
                        user_db_id=db_user_id,
                        task_type=task_data.get("task_type"),
                        input_params=task_data
                    )
                    count += 1

        logger.info(f"从 JSON 同步了 {count} 个任务到数据库")
