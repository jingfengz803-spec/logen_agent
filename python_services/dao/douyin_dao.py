"""
抖音数据访问层
存储抓取的抖音视频数据到数据库
"""

from typing import Optional, List, Dict, Any
from database import db
from core.logger import get_logger
import json

logger = get_logger("dao:douyin")


class DouyinDAO:
    """抖音数据访问对象"""

    @staticmethod
    def init_table():
        """初始化抖音相关表"""
        sqls = [
            # 抖音视频表
            """
            CREATE TABLE IF NOT EXISTS douyin_videos (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                aweme_id VARCHAR(64) UNIQUE NOT NULL COMMENT '视频ID',
                user_id BIGINT COMMENT '所属用户ID',
                author_name VARCHAR(200) COMMENT '作者名称',
                author_id VARCHAR(100) COMMENT '作者ID',
                title VARCHAR(500) COMMENT '视频标题',
                description TEXT COMMENT '视频描述',
                video_url VARCHAR(500) COMMENT '视频链接',
                cover_url VARCHAR(500) COMMENT '封面链接',
                music_name VARCHAR(200) COMMENT '音乐名称',
                raw_data JSON COMMENT '原始数据',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                INDEX idx_user_id (user_id),
                INDEX idx_aweme_id (aweme_id),
                INDEX idx_author_id (author_id),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='抖音视频表'
            """,
            # 抓取任务表
            """
            CREATE TABLE IF NOT EXISTS douyin_fetch_tasks (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                task_id VARCHAR(64) UNIQUE NOT NULL COMMENT '任务ID',
                user_id BIGINT COMMENT '用户ID',
                fetch_type VARCHAR(20) NOT NULL COMMENT '抓取类型 user/topic/hotlist',
                target_value VARCHAR(500) COMMENT '抓取目标 URL/话题',
                status VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
                video_count INT DEFAULT 0 COMMENT '抓取到的视频数量',
                error_message TEXT COMMENT '错误信息',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                completed_at DATETIME COMMENT '完成时间',
                INDEX idx_user_id (user_id),
                INDEX idx_task_id (task_id),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='抖音抓取任务表'
            """
        ]

        for sql in sqls:
            try:
                db.execute(sql)
            except Exception as e:
                logger.warning(f"创建表失败（可能已存在）: {e}")

        logger.info("✅ 抖音数据表初始化完成")

    @staticmethod
    def save_video(user_db_id: int, video_data: Dict[str, Any]) -> int:
        """
        保存单个视频数据

        Args:
            user_db_id: 用户数据库 ID
            video_data: 视频数据字典

        Returns:
            新插入记录的 ID
        """
        sql = """
            INSERT INTO douyin_videos
            (aweme_id, user_id, author_name, author_id, title, description,
             video_url, cover_url, music_name, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            description = VALUES(description),
            updated_at = CURRENT_TIMESTAMP
        """
        aweme_id = video_data.get("aweme_id") or video_data.get("aweme_id", "")

        params = (
            aweme_id,
            user_db_id,
            video_data.get("author", {}).get("nickname") if isinstance(video_data.get("author"), dict) else video_data.get("author_name", ""),
            video_data.get("author", {}).get("uid") if isinstance(video_data.get("author"), dict) else video_data.get("author_id", ""),
            video_data.get("title", video_data.get("desc", ""))[:500],
            video_data.get("desc", ""),
            video_data.get("video_url", ""),
            video_data.get("cover", ""),
            video_data.get("music_name", ""),
            json.dumps(video_data, ensure_ascii=False)
        )

        return db.insert_return_id(sql, params)

    @staticmethod
    def save_videos_batch(user_db_id: int, videos: List[Dict[str, Any]]) -> int:
        """
        批量保存视频数据

        Args:
            user_db_id: 用户数据库 ID
            videos: 视频数据列表

        Returns:
            成功保存的数量
        """
        count = 0
        for video in videos:
            try:
                DouyinDAO.save_video(user_db_id, video)
                count += 1
            except Exception as e:
                logger.warning(f"保存视频失败 {video.get('aweme_id')}: {e}")
        return count

    @staticmethod
    def get_video_by_aweme_id(aweme_id: str) -> Optional[Dict]:
        """通过 aweme_id 获取视频"""
        sql = "SELECT * FROM douyin_videos WHERE aweme_id = %s"
        return db.fetch_one(sql, (aweme_id,), skip_user_filter=True)

    @staticmethod
    def get_videos(limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取当前用户的所有视频（Database 自动按 user_id 过滤）"""
        sql = """
            SELECT * FROM douyin_videos
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        return db.fetch_all(sql, (limit, offset))

    @staticmethod
    def search_videos(keyword: str, limit: int = 50) -> List[Dict]:
        """搜索视频"""
        sql = """
            SELECT * FROM douyin_videos
            WHERE title LIKE %s OR description LIKE %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        pattern = f"%{keyword}%"
        return db.fetch_all(sql, (pattern, pattern, limit))

    @staticmethod
    def get_video_stats() -> Dict:
        """获取视频统计信息（Database 自动按 user_id 过滤）"""
        sql = """
            SELECT
                COUNT(*) as total_videos,
                COUNT(DISTINCT author_id) as total_authors
            FROM douyin_videos
        """
        return db.fetch_one(sql) or {}

    @staticmethod
    def create_fetch_task(user_db_id: int, fetch_type: str, target_value: str,
                          task_id: str = None) -> int:
        """
        创建抓取任务记录

        Args:
            user_db_id: 用户数据库 ID
            fetch_type: 抓取类型 (user/topic/hotlist)
            target_value: 目标值 (URL/话题)
            task_id: 任务 ID

        Returns:
            新记录 ID
        """
        import uuid
        if not task_id:
            task_id = str(uuid.uuid4())

        sql = """
            INSERT INTO douyin_fetch_tasks
            (task_id, user_id, fetch_type, target_value, status)
            VALUES (%s, %s, %s, %s, 'pending')
        """
        new_id = db.insert_return_id(sql, (task_id, user_db_id, fetch_type, target_value))

        # 验证：立即查询确认
        verify_sql = "SELECT * FROM douyin_fetch_tasks WHERE id = %s"
        result = db.fetch_one(verify_sql, (new_id,), skip_user_filter=True)
        logger.info(f"✅ 插入后验证: id={new_id}, 查询结果={result is not None}, 内容={result}")

        return new_id

    @staticmethod
    def update_fetch_task(task_id: str, status: str = None,
                           video_count: int = None, error_message: str = None):
        """更新抓取任务状态"""
        updates = []
        params = []

        if status:
            updates.append("status = %s")
            params.append(status)
            if status == "completed":
                updates.append("completed_at = CURRENT_TIMESTAMP")

        if video_count is not None:
            updates.append("video_count = %s")
            params.append(video_count)

        if error_message:
            updates.append("error_message = %s")
            params.append(error_message)

        params.append(task_id)

        sql = f"UPDATE douyin_fetch_tasks SET {', '.join(updates)} WHERE task_id = %s"
        logger.info(f"🔄 更新 douyin_fetch_task: sql={sql}, params={params}")
        db.execute(sql, tuple(params))

    @staticmethod
    def get_fetch_tasks(limit: int = 50) -> List[Dict]:
        """获取抓取任务列表（Database 自动按 user_id 过滤）"""
        sql = """
            SELECT * FROM douyin_fetch_tasks
            ORDER BY created_at DESC
            LIMIT %s
        """
        return db.fetch_all(sql, (limit,))
