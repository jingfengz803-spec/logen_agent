"""
生成的资源数据访问层
管理用户生成的音频、视频等资源
"""

from typing import Optional, List, Dict, Any
from database import db
from core.logger import get_logger
import json
from datetime import datetime

logger = get_logger("dao:resource")


class ResourceDAO:
    """生成的资源数据访问对象"""

    @staticmethod
    def init_table():
        """初始化资源表"""
        sql = """
        CREATE TABLE IF NOT EXISTS generated_resources (
            id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '资源ID',
            user_id BIGINT NOT NULL COMMENT '用户ID',
            resource_type VARCHAR(20) NOT NULL COMMENT '资源类型 audio/video/image',
            resource_url VARCHAR(500) NOT NULL COMMENT 'OSS公网URL',
            file_name VARCHAR(255) COMMENT '文件名',
            file_size BIGINT COMMENT '文件大小(字节)',
            duration INT COMMENT '时长(秒)用于音视频',
            task_id VARCHAR(64) COMMENT '关联的任务ID',
            source_task_type VARCHAR(50) COMMENT '来源任务类型 chain_tts/video_generate等',
            status VARCHAR(20) DEFAULT 'active' COMMENT '状态 active/deleted/blocked',
            metadata JSON COMMENT '额外元数据如分辨率、格式等',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            INDEX idx_user_id (user_id),
            INDEX idx_user_type (user_id, resource_type),
            INDEX idx_user_status (user_id, status),
            INDEX idx_task_id (task_id),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生成的资源表'
        """
        try:
            db.execute(sql)
            logger.info("✅ 资源表初始化完成")
        except Exception as e:
            logger.warning(f"资源表初始化失败（可能已存在）: {e}")

    @staticmethod
    def create_resource(
        user_db_id: int,
        resource_type: str,
        resource_url: str,
        file_name: Optional[str] = None,
        file_size: Optional[int] = None,
        duration: Optional[int] = None,
        task_id: Optional[str] = None,
        source_task_type: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        创建资源记录

        Args:
            user_db_id: 用户数据库ID
            resource_type: 资源类型 audio/video/image
            resource_url: OSS公网URL
            file_name: 文件名
            file_size: 文件大小(字节)
            duration: 时长(秒)
            task_id: 关联的任务ID
            source_task_type: 来源任务类型
            metadata: 额外元数据

        Returns:
            新记录ID
        """
        sql = """
            INSERT INTO generated_resources
            (user_id, resource_type, resource_url, file_name, file_size, duration, task_id, source_task_type, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return db.insert_return_id(sql, (
            user_db_id,
            resource_type,
            resource_url,
            file_name,
            file_size,
            duration,
            task_id,
            source_task_type,
            json.dumps(metadata, ensure_ascii=False) if metadata else None
        ))

    @staticmethod
    def get_resource(resource_id: int) -> Optional[Dict]:
        """获取单个资源"""
        sql = "SELECT * FROM generated_resources WHERE id = %s"
        return db.fetch_one(sql, (resource_id,))

    @staticmethod
    def get_user_resources(
        resource_type: Optional[str] = None,
        status: str = "active",
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        获取当前用户的资源列表（Database 自动按 user_id 过滤）

        Args:
            resource_type: 资源类型过滤 audio/video/image
            status: 状态过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            资源列表
        """
        conditions = ["status = %s"]
        params = [status]

        if resource_type:
            conditions.append("resource_type = %s")
            params.append(resource_type)

        sql = f"""
            SELECT * FROM generated_resources
            WHERE {' AND '.join(conditions)}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        return db.fetch_all(sql, tuple(params))

    @staticmethod
    def get_all_resources(
        resource_type: Optional[str] = None,
        status: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        获取所有资源（管理员审核用）

        Args:
            resource_type: 资源类型过滤
            status: 状态过滤（None表示包括所有状态）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            资源列表
        """
        conditions = []
        params = []

        if resource_type:
            conditions.append("resource_type = %s")
            params.append(resource_type)

        if status:
            conditions.append("status = %s")
            params.append(status)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        sql = f"""
            SELECT r.*, u.username, u.user_id as user_uid
            FROM generated_resources r
            LEFT JOIN users u ON r.user_id = u.id
            {where_clause}
            ORDER BY r.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        return db.fetch_all(sql, tuple(params), skip_user_filter=True)

    @staticmethod
    def update_resource_status(resource_id: int, status: str) -> bool:
        """
        更新资源状态

        Args:
            resource_id: 资源ID
            status: 新状态 active/deleted/blocked

        Returns:
            是否成功
        """
        sql = "UPDATE generated_resources SET status = %s WHERE id = %s"
        affected = db.execute(sql, (status, resource_id))
        return affected > 0

    @staticmethod
    def get_resources_by_task(task_id: str) -> List[Dict]:
        """根据任务ID获取相关资源"""
        sql = """
            SELECT * FROM generated_resources
            WHERE task_id = %s AND status = 'active'
            ORDER BY created_at DESC
        """
        return db.fetch_all(sql, (task_id,), skip_user_filter=True)

    @staticmethod
    def count_user_resources(resource_type: Optional[str] = None) -> Dict[str, int]:
        """
        统计当前用户资源数量（Database 自动按 user_id 过滤）

        Args:
            resource_type: 资源类型过滤

        Returns:
            统计结果 {"total": 100, "audio": 50, "video": 50}
        """
        if resource_type:
            sql = """
                SELECT COUNT(*) as count FROM generated_resources
                WHERE resource_type = %s AND status = 'active'
            """
            result = db.fetch_one(sql, (resource_type,))
            return {resource_type: result.get("count", 0) if result else 0}
        else:
            sql = """
                SELECT resource_type, COUNT(*) as count
                FROM generated_resources
                WHERE status = 'active'
                GROUP BY resource_type
            """
            results = db.fetch_all(sql)
            counts = {r["resource_type"]: r["count"] for r in results}
            counts["total"] = sum(counts.values())
            return counts

    @staticmethod
    def get_resource_stats(days: int = 7) -> Dict[str, Any]:
        """
        获取资源统计信息（管理员用）

        Args:
            days: 统计最近几天

        Returns:
            统计信息
        """
        sql = """
            SELECT
                resource_type,
                status,
                COUNT(*) as count,
                SUM(file_size) as total_size
            FROM generated_resources
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY resource_type, status
        """
        results = db.fetch_all(sql, (days,), skip_user_filter=True)

        # 按类型分组
        stats = {}
        for r in results:
            rtype = r["resource_type"]
            if rtype not in stats:
                stats[rtype] = {
                    "total": 0,
                    "active": 0,
                    "deleted": 0,
                    "blocked": 0,
                    "total_size": 0
                }
            stats[rtype][r["status"]] = r["count"]
            stats[rtype]["total"] += r["count"]
            stats[rtype]["total_size"] += r.get("total_size") or 0

        return stats

    @staticmethod
    def cleanup_old_resources(days: int = 30, status: str = "deleted") -> int:
        """
        清理旧资源记录

        Args:
            days: 保留天数
            status: 只清理指定状态的资源

        Returns:
            删除的数量
        """
        sql = """
            DELETE FROM generated_resources
            WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
            AND status = %s
        """
        return db.execute(sql, (days, status), skip_user_filter=True)

    @staticmethod
    def save_resources_from_task(
        user_db_id: int,
        task_id: str,
        task_type: str,
        result: Dict[str, Any]
    ) -> List[int]:
        """
        从任务结果中自动提取并保存资源

        Args:
            user_db_id: 用户数据库ID
            task_id: 任务ID
            task_type: 任务类型
            result: 任务结果

        Returns:
            保存的资源ID列表
        """
        resource_ids = []

        # 检查预览URL
        preview_urls = result.get("preview_urls") or {}

        # 保存音频
        audio_url = preview_urls.get("audio") or result.get("full_audio_oss_url") or result.get("audio_url")
        if audio_url and audio_url.startswith("http"):
            try:
                rid = ResourceDAO.create_resource(
                    user_db_id=user_db_id,
                    resource_type="audio",
                    resource_url=audio_url,
                    task_id=task_id,
                    source_task_type=task_type,
                    metadata={"format": "mp3"}
                )
                resource_ids.append(rid)
                logger.info(f"保存音频资源: {rid}, url={audio_url}")
            except Exception as e:
                logger.warning(f"保存音频资源失败: {e}")

        # 保存视频
        video_url = preview_urls.get("video") or result.get("video_url")
        if video_url and video_url.startswith("http"):
            try:
                # 提取元数据
                metadata = {}
                if result.get("resolution"):
                    metadata["resolution"] = result["resolution"]

                rid = ResourceDAO.create_resource(
                    user_db_id=user_db_id,
                    resource_type="video",
                    resource_url=video_url,
                    task_id=task_id,
                    source_task_type=task_type,
                    metadata=metadata
                )
                resource_ids.append(rid)
                logger.info(f"保存视频资源: {rid}, url={video_url}")
            except Exception as e:
                logger.warning(f"保存视频资源失败: {e}")

        # 保存分段音频
        segments = preview_urls.get("segments") or result.get("segments_audio_oss", [])
        if isinstance(segments, list):
            for i, seg in enumerate(segments):
                seg_url = seg if isinstance(seg, str) else seg.get("oss_url")
                if seg_url and seg_url.startswith("http"):
                    try:
                        rid = ResourceDAO.create_resource(
                            user_db_id=user_db_id,
                            resource_type="audio",
                            resource_url=seg_url,
                            file_name=f"segment_{i+1}.mp3",
                            task_id=task_id,
                            source_task_type=task_type,
                            metadata={"segment_index": i, "format": "mp3"}
                        )
                        resource_ids.append(rid)
                    except Exception as e:
                        logger.warning(f"保存分段音频失败: {e}")

        return resource_ids
