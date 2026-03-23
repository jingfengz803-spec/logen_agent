"""
完整工作流服务
整合所有模块提供端到端的工作流
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config import settings
from core.logger import get_logger
from services.douyin_service import DouyinService
from services.ai_service import AIService
from services.tts_service import TTSService
from services.video_service import VideoService

logger = get_logger("service:workflow")


class WorkflowService:
    """完整工作流服务"""

    def __init__(self):
        self.douyin_service = DouyinService()
        self.ai_service = AIService()
        self.tts_service = TTSService()
        self.video_service = VideoService()
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def run_workflow_async(
        self,
        douyin_url: str,
        topic: str,
        voice_id: Optional[str] = None,
        ref_video_url: Optional[str] = None,
        workflow_type: str = "without_video",
        max_videos: int = 100,
        output_name: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        运行完整工作流

        Args:
            douyin_url: 抖音URL
            topic: 新主题
            voice_id: 音色ID
            ref_video_url: 参考视频URL
            workflow_type: 工作流类型
            max_videos: 最大视频数
            output_name: 输出文件名
            progress_callback: 进度回调

        Returns:
            工作流结果
        """
        result = {
            "workflow_type": workflow_type,
            "topic": topic,
            "steps": {}
        }

        # 步骤1: 抓取抖音数据
        if progress_callback:
            progress_callback(5, "开始抓取抖音数据...")

        fetch_result = await self.douyin_service.fetch_user_videos_async(
            url=douyin_url,
            max_count=max_videos,
            progress_callback=lambda p, msg: progress_callback(
                5 + int(p * 0.15), f"抓取数据: {msg}"
            )
        )

        videos = fetch_result.get("videos", [])
        result["steps"]["fetch"] = {
            "status": "success",
            "count": len(videos)
        }

        if progress_callback:
            progress_callback(20, "抖音数据抓取完成")

        # 步骤2: AI分析
        if progress_callback:
            progress_callback(25, "开始AI分析...")

        # 火爆原因分析
        viral_result = await self.ai_service.analyze_viral_async(videos)
        result["steps"]["viral_analysis"] = viral_result.get("viral_analysis", {})

        # 风格分析
        style_result = await self.ai_service.analyze_style_async(videos)
        result["steps"]["style_analysis"] = style_result.get("style_analysis", {})

        if progress_callback:
            progress_callback(50, "AI分析完成")

        # 步骤3: 生成脚本
        if progress_callback:
            progress_callback(55, "生成脚本...")

        script_result = await self.ai_service.generate_script_async(
            reference_data=style_result.get("style_analysis", {}),
            topic=topic
        )
        result["steps"]["script"] = script_result.get("script", {})

        if progress_callback:
            progress_callback(65, "脚本生成完成")

        # 如果只是分析，直接返回
        if workflow_type == "analysis_only":
            if progress_callback:
                progress_callback(100, "分析完成")
            return result

        # 步骤4: TTS合成
        if voice_id and progress_callback:
            progress_callback(70, "开始TTS合成...")

        if voice_id:
            script = script_result.get("script", {})
            tts_result = await self.tts_service.script_to_speech_async(
                full_text=script.get("full_script", ""),
                segments=script.get("segments", []),
                voice_id=voice_id
            )
            result["steps"]["tts"] = tts_result

            if progress_callback:
                progress_callback(85, "TTS合成完成")

        # 步骤5: 视频生成
        if workflow_type == "full" and voice_id and ref_video_url:
            if progress_callback:
                progress_callback(90, "开始生成视频...")

            audio_url = tts_result.get("full_audio_path")
            if audio_url:
                # 需要先上传到OSS
                # TODO: 添加OSS上传逻辑
                pass

            # video_result = await self.video_service.generate_video_async(
            #     video_url=ref_video_url,
            #     audio_url=audio_url,
            #     progress_callback=lambda p, msg: progress_callback(
            #         90 + int(p * 0.1), f"生成视频: {msg}"
            #     )
            # )
            # result["steps"]["video"] = video_result

        if progress_callback:
            progress_callback(100, "工作流完成")

        return result

    async def get_workflow_templates(self) -> list[Dict[str, Any]]:
        """获取工作流模板"""
        return [
            {
                "id": "quick",
                "name": "快速分析",
                "description": "仅进行AI分析和脚本生成",
                "workflow_type": "analysis_only",
                "estimated_time": "2-5分钟"
            },
            {
                "id": "standard",
                "name": "标准流程",
                "description": "分析+脚本+TTS",
                "workflow_type": "without_video",
                "requires_voice": True,
                "estimated_time": "5-10分钟"
            },
            {
                "id": "full",
                "name": "完整流程",
                "description": "分析+脚本+TTS+视频",
                "workflow_type": "full",
                "requires_voice": True,
                "requires_ref_video": True,
                "estimated_time": "10-20分钟"
            }
        ]
