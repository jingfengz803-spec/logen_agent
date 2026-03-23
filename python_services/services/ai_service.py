"""
AI分析与脚本生成服务
封装analyze_and_generate模块的API
"""

import sys
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config import settings
from core.logger import get_logger

logger = get_logger("service:ai")


class AIService:
    """AI分析与脚本生成服务"""

    def __init__(self):
        self.longgraph_dir = settings.longgraph_path
        self.executor = ThreadPoolExecutor(max_workers=3)

    async def analyze_viral_async(
        self,
        video_data: List[Dict[str, Any]],
        video_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        异步火爆原因分析

        Args:
            video_data: 视频数据列表
            video_ids: 指定分析的视频ID

        Returns:
            分析结果
        """
        loop = asyncio.get_event_loop()

        def _analyze():
            try:
                sys.path.insert(0, str(self.longgraph_dir))
                from analyze_and_generate import VideoStyleAnalyzer

                analyzer = VideoStyleAnalyzer()

                # 执行火爆原因分析
                result = analyzer.analyze_viral_factors(
                    videos=video_data,
                    top_n=20
                )

                return {
                    "viral_analysis": result
                }

            except Exception as e:
                logger.error(f"火爆原因分析失败: {e}")
                raise

        return await loop.run_in_executor(self.executor, _analyze)

    async def analyze_style_async(
        self,
        video_data: List[Dict[str, Any]],
        dimensions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        异步风格特征分析

        Args:
            video_data: 视频数据列表
            dimensions: 分析维度

        Returns:
            分析结果
        """
        loop = asyncio.get_event_loop()

        def _analyze():
            try:
                sys.path.insert(0, str(self.longgraph_dir))
                from analyze_and_generate import VideoStyleAnalyzer

                analyzer = VideoStyleAnalyzer()

                # 执行风格分析
                result = analyzer.analyze_videos(
                    videos=video_data,
                    top_n=30
                )

                return {
                    "style_analysis": result
                }

            except Exception as e:
                logger.error(f"风格分析失败: {e}")
                raise

        return await loop.run_in_executor(self.executor, _analyze)

    async def generate_script_async(
        self,
        style_analysis: Dict[str, Any],
        viral_analysis: Dict[str, Any],
        topic: str,
        target_duration: float = 20.0
    ) -> Dict[str, Any]:
        """
        异步生成脚本

        Args:
            style_analysis: 风格分析结果
            viral_analysis: 火爆分析结果
            topic: 新主题
            target_duration: 目标时长（秒）

        Returns:
            生成的脚本
        """
        loop = asyncio.get_event_loop()

        def _generate():
            try:
                sys.path.insert(0, str(self.longgraph_dir))
                from analyze_and_generate import VideoStyleAnalyzer

                analyzer = VideoStyleAnalyzer()

                # 生成TTS脚本
                result = analyzer.generate_tts_script(
                    style_analysis=style_analysis,
                    viral_analysis=viral_analysis,
                    topic=topic,
                    target_duration=target_duration
                )

                return {
                    "script": result
                }

            except Exception as e:
                logger.error(f"脚本生成失败: {e}")
                raise

        return await loop.run_in_executor(self.executor, _generate)

    async def full_analysis_async(
        self,
        douyin_url: str,
        topic: str,
        max_videos: int = 100,
        enable_viral: bool = True,
        enable_style: bool = True,
        generate_script: bool = True,
        target_duration: float = 60.0
    ) -> Dict[str, Any]:
        """
        完整分析流程

        Args:
            douyin_url: 抖音URL
            topic: 新主题
            max_videos: 最大视频数
            enable_viral: 是否进行火爆分析
            enable_style: 是否进行风格分析
            generate_script: 是否生成脚本
            target_duration: TTS目标时长（秒），默认60秒

        Returns:
            完整分析结果
        """
        loop = asyncio.get_event_loop()

        def _analyze():
            try:
                sys.path.insert(0, str(self.longgraph_dir))
                from analyze_and_generate import full_analysis_workflow

                result = full_analysis_workflow(
                    url=douyin_url,
                    topic=topic,
                    max_videos=max_videos,
                    enable_viral=enable_viral,
                    enable_style=enable_style,
                    generate_script=generate_script,
                    target_duration=target_duration
                )

                return result

            except Exception as e:
                logger.error(f"完整分析失败: {e}")
                raise

        return await loop.run_in_executor(self.executor, _analyze)
