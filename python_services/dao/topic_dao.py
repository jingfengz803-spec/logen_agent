"""
选题数据访问层
"""
from typing import Optional, List, Dict
from database import db
from core.logger import get_logger

logger = get_logger("dao:topic")


class TopicDAO:
    """选题数据访问对象"""

    @staticmethod
    def init_table():
        """初始化选题表"""
        sql = """
        CREATE TABLE IF NOT EXISTS topics (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            user_id BIGINT NOT NULL,
            profile_id VARCHAR(64) NOT NULL,
            title VARCHAR(200) NOT NULL COMMENT '选题标题',
            source VARCHAR(20) NOT NULL DEFAULT 'custom' COMMENT '来源: ai/custom',
            status VARCHAR(20) DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user_id (user_id),
            INDEX idx_profile_id (profile_id),
            INDEX idx_user_status (user_id, status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='选题表'
        """
        try:
            db.execute(sql)
            logger.info("✅ 选题表初始化完成")
        except Exception as e:
            logger.warning(f"选题表初始化失败（可能已存在）: {e}")

    @staticmethod
    def create_topic(user_db_id: int, profile_id: str, title: str, source: str = "custom") -> int:
        """创建选题"""
        sql = """
            INSERT INTO topics (user_id, profile_id, title, source)
            VALUES (%s, %s, %s, %s)
        """
        return db.insert_return_id(sql, (user_db_id, profile_id, title, source))

    @staticmethod
    def upsert_ai_topic(user_db_id: int, profile_id: str, title: str) -> int:
        """创建或覆盖 AI 选题（同一 profile_id 只保留一条）"""
        check_sql = "SELECT id FROM topics WHERE profile_id = %s AND source = 'ai' AND status = 'active'"
        existing = db.fetch_one(check_sql, (profile_id,))
        if existing:
            update_sql = "UPDATE topics SET title = %s WHERE id = %s"
            db.execute(update_sql, (title, existing["id"]))
            return existing["id"]
        else:
            return TopicDAO.create_topic(user_db_id, profile_id, title, source="ai")

    @staticmethod
    def list_topics(profile_id: str = None, limit: int = 50, offset: int = 0) -> List[Dict]:
        """获取选题列表"""
        if profile_id:
            sql = """
                SELECT * FROM topics
                WHERE profile_id = %s AND status = 'active'
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            return db.fetch_all(sql, (profile_id, limit, offset))
        else:
            sql = """
                SELECT * FROM topics
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            return db.fetch_all(sql, (limit, offset))

    @staticmethod
    def update_topic(topic_id: int, title: str) -> bool:
        """更新选题标题"""
        sql = "UPDATE topics SET title = %s WHERE id = %s AND status = 'active'"
        affected = db.execute(sql, (title, topic_id))
        return affected > 0

    @staticmethod
    def delete_topic(topic_id: int) -> bool:
        """软删除选题"""
        sql = "UPDATE topics SET status = 'deleted' WHERE id = %s"
        affected = db.execute(sql, (topic_id,))
        return affected > 0
