"""
音色数据访问层
"""

from typing import Optional, List
from database import db
from models.db import Voice
from core.logger import get_logger

logger = get_logger("dao:voice")


class VoiceDAO:
    """音色数据访问对象"""

    @staticmethod
    def create_voice(user_db_id: int, voice_id: str, prefix: str, model: str,
                      status: str = "DEPLOYING", target_model: str = None,
                      gmt_create: str = None, gmt_modified: str = None) -> Voice:
        """
        创建音色记录

        Args:
            user_db_id: 用户数据库 ID
            voice_id: Dashscope 音色 ID
            prefix: 音色前缀
            model: 模型名称
            status: 状态
            target_model: 目标模型
            gmt_create: Dashscope 创建时间
            gmt_modified: Dashscope 修改时间

        Returns:
            创建的音色对象
        """
        sql = """
            INSERT INTO voices (user_id, voice_id, prefix, model, status, target_model, gmt_create, gmt_modified)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        db.execute(sql, (user_db_id, voice_id, prefix, model, status, target_model, gmt_create, gmt_modified))

        logger.info(f"创建音色记录: {voice_id} (用户ID: {user_db_id})")
        return Voice(
            voice_id=voice_id,
            user_id=user_db_id,
            prefix=prefix,
            model=model,
            status=status,
            target_model=target_model
        )

    @staticmethod
    def _resolve_id(raw_id: str):
        """根据输入判断使用 id（数字）还是 voice_id（字符串）"""
        if raw_id.isdigit():
            return "id", int(raw_id)
        return "voice_id", raw_id

    @staticmethod
    def get_by_voice_id(voice_id: str) -> Optional[Voice]:
        """通过 id 或 voice_id 获取音色"""
        col, val = VoiceDAO._resolve_id(voice_id)
        sql = f"SELECT * FROM voices WHERE {col} = %s"
        row = db.fetch_one(sql, (val,))
        if row:
            return Voice(**row)
        return None

    @staticmethod
    def list_voices(status: str = None) -> list:
        """获取当前用户的音色列表（自动按 user_id 过滤）"""
        if status:
            sql = "SELECT * FROM voices WHERE status = %s"
            rows = db.fetch_all(sql, (status,))
        else:
            sql = "SELECT * FROM voices WHERE 1=1"
            rows = list(db.fetch_all(sql))
        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return rows

    @staticmethod
    def list_all(status: str = None, limit: int = 100) -> List[dict]:
        """获取所有音色（管理员用，跳过用户过滤）"""
        if status:
            sql = """
                SELECT v.*, u.username
                FROM voices v
                LEFT JOIN users u ON v.user_id = u.id
                WHERE v.status = %s
                ORDER BY v.created_at DESC
                LIMIT %s
            """
            rows = db.fetch_all(sql, (status, limit), skip_user_filter=True)
        else:
            sql = """
                SELECT v.*, u.username
                FROM voices v
                LEFT JOIN users u ON v.user_id = u.id
                ORDER BY v.created_at DESC
                LIMIT %s
            """
            rows = db.fetch_all(sql, (limit,), skip_user_filter=True)
        return rows

    @staticmethod
    def update_status(voice_id: str, status: str, gmt_modified: str = None) -> bool:
        """更新音色状态，支持 id 或 voice_id"""
        col, val = VoiceDAO._resolve_id(voice_id)
        sql = f"UPDATE voices SET status = %s, gmt_modified = %s WHERE {col} = %s"
        affected = db.execute(sql, (status, gmt_modified, val))
        return affected > 0

    @staticmethod
    def delete_voice(voice_id: str) -> bool:
        """删除音色，支持 id 或 voice_id"""
        col, val = VoiceDAO._resolve_id(voice_id)
        sql = f"DELETE FROM voices WHERE {col} = %s"
        affected = db.execute(sql, (val,))
        return affected > 0

    @staticmethod
    def sync_from_dashscope(voices_data: list, user_db_id: int):
        """
        从 Dashscope 同步音色数据

        Args:
            voices_data: Dashscope 返回的音色列表
            user_db_id: 用户数据库 ID
        """
        for voice_info in voices_data:
            voice_id = voice_info.get("voice_id")
            existing = VoiceDAO.get_by_voice_id(voice_id)

            if not existing:
                # 新建音色
                parts = voice_id.split("-")
                prefix = parts[3] if len(parts) > 3 else ""

                VoiceDAO.create_voice(
                    user_db_id=user_db_id,
                    voice_id=voice_id,
                    prefix=prefix,
                    model=voice_info.get("target_model", ""),
                    status=voice_info.get("status", "DEPLOYING"),
                    target_model=voice_info.get("target_model"),
                    gmt_create=voice_info.get("gmt_create"),
                    gmt_modified=voice_info.get("gmt_modified")
                )
            else:
                # 更新状态
                VoiceDAO.update_status(
                    voice_id=voice_id,
                    status=voice_info.get("status", existing.status),
                    gmt_modified=voice_info.get("gmt_modified")
                )

        logger.info(f"同步音色数据完成，共 {len(voices_data)} 个")
