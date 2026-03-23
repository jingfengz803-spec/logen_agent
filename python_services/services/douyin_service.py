"""
抖音数据抓取服务
封装douyin_data_tool模块的API
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config import settings
from core.logger import get_logger

logger = get_logger("service:douyin")


class DouyinService:
    """抖音数据抓取服务"""

    def __init__(self):
        self.tool_dir = settings.douyin_tool_path
        self.data_file = self.tool_dir / "user_videos_data.json"
        self.executor = ThreadPoolExecutor(max_workers=2)

    async def fetch_user_videos_async(
        self,
        url: str,
        max_count: int = 100,
        enable_filter: bool = False,
        min_likes: int = 50,
        min_comments: int = 0,
        top_n: int = 0,
        sort_by: str = "like",
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        异步抓取用户视频

        Args:
            url: 抖音用户主页URL
            max_count: 最大抓取数量
            enable_filter: 是否启用过滤
            min_likes: 最小点赞数
            min_comments: 最小评论数
            progress_callback: 进度回调

        Returns:
            抓取结果
        """
        loop = asyncio.get_event_loop()

        def _fetch():
            try:
                # 导入抓取模块
                sys.path.insert(0, str(self.tool_dir))
                from fetch_user_videos import DouyinUserFetcher
                import config as douyin_config

                if progress_callback:
                    progress_callback(20, "初始化抓取器...")

                # 设置过滤条件（config.py 中是全局变量）
                douyin_config.FILTER_MIN_LIKE = min_likes
                douyin_config.FILTER_MIN_COMMENT = min_comments

                # 创建抓取器
                fetcher = DouyinUserFetcher(
                    max_videos=max_count,
                    enable_filter=enable_filter
                )

                if progress_callback:
                    progress_callback(40, "开始抓取...")

                # 直接使用 URL 抓取（内部会解析 sec_user_id）
                videos = fetcher.fetch_from_url(url)

                if progress_callback:
                    progress_callback(80, "处理数据...")

                # Top N 筛选
                top_videos = []
                if top_n > 0 and videos:
                    key = f"{sort_by}_count"
                    top_videos = sorted(videos, key=lambda x: x.get(key, 0), reverse=True)[:top_n]

                # 统计信息
                stats = self._calculate_stats(videos) if videos else {}

                if progress_callback:
                    progress_callback(100, "抓取完成")

                # 保存结果
                result = {
                    "total": len(videos),
                    "videos": top_videos if top_n > 0 else videos,
                    "top_n": top_n,
                    "sort_by": sort_by,
                    "stats": stats,
                    "url": url
                }

                if progress_callback:
                    progress_callback(100, "抓取完成")

                return result

            except Exception as e:
                logger.error(f"抓取视频失败: {e}")
                raise

        return await loop.run_in_executor(self.executor, _fetch)

    async def fetch_topic_videos_async(
        self,
        topic: str,
        max_count: int = 50
    ) -> Dict[str, Any]:
        """异步抓取话题视频"""
        loop = asyncio.get_event_loop()

        def _fetch():
            # TODO: 实现话题抓取
            return {
                "total": 0,
                "videos": [],
                "topic": topic
            }

        return await loop.run_in_executor(self.executor, _fetch)

    async def fetch_hot_list_async(
        self,
        cate_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """异步抓取热榜"""
        loop = asyncio.get_event_loop()

        def _fetch():
            # TODO: 实现热榜抓取
            return {
                "total": 0,
                "items": []
            }

        return await loop.run_in_executor(self.executor, _fetch)

    def get_cached_videos(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取已缓存的视频数据"""
        try:
            if not self.data_file.exists():
                return []

            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                videos = data
            elif isinstance(data, dict) and "videos" in data:
                videos = data["videos"]
            else:
                videos = []

            return videos[offset:offset + limit]

        except Exception as e:
            logger.error(f"读取缓存数据失败: {e}")
            return []

    def get_cached_count(self) -> int:
        """获取缓存视频总数"""
        videos = self.get_cached_videos(limit=999999)
        return len(videos)

    def parse_video_info(self, raw_video: Dict[str, Any]) -> Dict[str, Any]:
        """解析视频信息为统一格式"""
        return {
            "aweme_id": raw_video.get("aweme_id", ""),
            "desc": raw_video.get("desc", ""),
            "desc_clean": raw_video.get("desc_clean", ""),
            "author": raw_video.get("author", ""),
            "author_id": raw_video.get("author_id", ""),
            "like_count": raw_video.get("like_count", 0),
            "comment_count": raw_video.get("comment_count", 0),
            "share_count": raw_video.get("share_count", 0),
            "play_count": raw_video.get("play_count", 0),
            "duration": raw_video.get("duration", 0),
            "create_time": raw_video.get("create_time", 0),
            "create_time_str": raw_video.get("create_time_str", ""),
            "hashtags": raw_video.get("hashtags", []),
            "music": raw_video.get("music", ""),
            "video_url": raw_video.get("video_url", ""),
            "hot_score": raw_video.get("hot_score")
        }

    def _calculate_stats(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算视频数据统计信息"""
        if not videos:
            return {}

        # 统计标签
        all_tags = []
        for v in videos:
            all_tags.extend(v.get("hashtags", []))

        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        # 统计互动数据
        total_likes = sum(v.get("like_count", 0) for v in videos)
        total_comments = sum(v.get("comment_count", 0) for v in videos)
        total_shares = sum(v.get("share_count", 0) for v in videos)
        total_plays = sum(v.get("play_count", 0) for v in videos)

        avg_likes = total_likes // len(videos) if videos else 0
        avg_comments = total_comments // len(videos) if videos else 0

        # 找出最佳视频
        top_liked = max(videos, key=lambda x: x.get("like_count", 0))
        most_commented = max(videos, key=lambda x: x.get("comment_count", 0))

        return {
            "total_videos": len(videos),
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "total_plays": total_plays,
            "avg_likes": avg_likes,
            "avg_comments": avg_comments,
            "top_tags": [{"tag": tag, "count": count} for tag, count in top_tags],
            "top_liked_video": {
                "aweme_id": top_liked.get("aweme_id"),
                "desc": top_liked.get("desc", "")[:50],
                "like_count": top_liked.get("like_count", 0)
            },
            "most_commented_video": {
                "aweme_id": most_commented.get("aweme_id"),
                "desc": most_commented.get("desc", "")[:50],
                "comment_count": most_commented.get("comment_count", 0)
            }
        }
