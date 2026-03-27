"""
视频生成服务
封装video_generator模块的API
支持本地文件自动上传到OSS
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

logger = get_logger("service:video")


class VideoService:
    """视频生成服务"""

    def __init__(self):
        self.longgraph_dir = settings.longgraph_path
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._client = None
        self._storage = None

    @property
    def client(self):
        """延迟初始化VideoRetalk客户端"""
        if self._client is None:
            sys.path.insert(0, str(self.longgraph_dir))
            from video_generator import VideoRetalkClient, VideoPreprocessor
            self._client = VideoRetalkClient()
            self._preprocessor = VideoPreprocessor
        return self._client

    @property
    def preprocessor(self):
        """获取视频预处理器"""
        if not hasattr(self, '_preprocessor'):
            sys.path.insert(0, str(self.longgraph_dir))
            from video_generator import VideoPreprocessor
            self._preprocessor = VideoPreprocessor
        return self._preprocessor

    @property
    def storage(self):
        """延迟初始化存储服务"""
        if self._storage is None:
            from services.storage_service import get_storage_service
            self._storage = get_storage_service()
        return self._storage

    def _preprocess_video(self, video_path: str) -> str:
        """
        预处理视频：检查分辨率，必要时调整

        Args:
            video_path: 原视频路径

        Returns:
            处理后的视频路径（可能是原路径或调整后的路径）
        """
        from concurrent.futures import ThreadPoolExecutor

        # 检查是否需要调整分辨率
        if not self.preprocessor.needs_resize(video_path):
            logger.info(f"视频分辨率符合要求: {video_path}")
            return video_path

        logger.info(f"视频需要调整分辨率，正在处理: {video_path}")

        # 调整分辨率
        processed_path = self.preprocessor.resize_video(video_path)
        logger.info(f"视频已调整分辨率: {processed_path}")
        return processed_path

    async def _upload_if_needed(
        self,
        file_path: Optional[str],
        existing_url: Optional[str],
        file_type: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Optional[str]:
        """
        如果提供了本地路径但没有 URL，则上传到 OSS

        Args:
            file_path: 本地文件路径
            existing_url: 已有的 URL
            file_type: 文件类型 (video, audio, image)
            progress_callback: 进度回调

        Returns:
            OSS URL 或 None
        """
        # 如果已有 URL，直接返回
        if existing_url:
            return existing_url

        # 如果没有本地路径，返回 None
        if not file_path:
            return None

        # 检查文件是否存在
        if not Path(file_path).exists():
            logger.warning(f"文件不存在: {file_path}")
            return None

        # 视频文件需要预处理（检查分辨率）
        actual_file_path = file_path
        if file_type == "video":
            loop = asyncio.get_event_loop()
            try:
                actual_file_path = await loop.run_in_executor(
                    None, self._preprocess_video, file_path
                )
            except Exception as e:
                logger.warning(f"视频预处理失败: {e}，尝试直接上传原文件")

        try:
            # 上传到 OSS
            if progress_callback:
                progress_callback(20, f"上传{file_type}到OSS...")

            result = await self.storage.upload_file_async(
                file_path=actual_file_path,
                file_type=file_type,
                progress_callback=progress_callback
            )

            logger.info(f"{file_type}已上传到OSS: {result.get('oss_url')}")
            return result.get("oss_url")

        except Exception as e:
            logger.error(f"上传{file_type}到OSS失败: {e}")
            return None

    async def generate_video_async(
        self,
        video_url: Optional[str] = None,
        audio_url: Optional[str] = None,
        ref_image_url: Optional[str] = None,
        video_path: Optional[str] = None,
        audio_path: Optional[str] = None,
        ref_image_path: Optional[str] = None,
        video_extension: bool = True,
        resolution: Optional[str] = None,
        auto_upload: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        异步生成视频（支持本地文件自动上传到OSS）

        Args:
            video_url: 参考视频URL（与video_path二选一）
            audio_url: 合成音频URL（与audio_path二选一）
            ref_image_url: 参考图片URL（与ref_image_path二选一）
            video_path: 本地参考视频路径（会自动上传到OSS）
            audio_path: 本地音频路径（会自动上传到OSS）
            ref_image_path: 本地参考图片路径（会自动上传到OSS）
            video_extension: 是否扩展视频以匹配音频长度
            resolution: 分辨率（如 1280x720）
            auto_upload: 是否自动上传本地文件到OSS
            progress_callback: 进度回调

        Returns:
            生成结果，包含 task_id 和 video_url
        """
        loop = asyncio.get_event_loop()

        def _generate():
            try:
                if progress_callback:
                    progress_callback(5, "准备文件...")

                # 处理参考视频
                final_video_url = None
                if video_url:
                    final_video_url = video_url
                elif video_path and auto_upload:
                    # 同步上传（因为已经在 executor 中）
                    if Path(video_path).exists():
                        if progress_callback:
                            progress_callback(10, "上传参考视频...")

                        # 使用同步方式上传
                        import asyncio
                        try:
                            final_video_url = asyncio.get_event_loop().run_until_complete(
                                self._upload_if_needed(video_path, None, "video", progress_callback)
                            )
                        except RuntimeError:
                            final_video_url = asyncio.run(
                                self._upload_if_needed(video_path, None, "video", progress_callback)
                            )

                if not final_video_url:
                    raise ValueError("需要提供 video_url 或 video_path")

                # 处理音频
                final_audio_url = None
                if audio_url:
                    final_audio_url = audio_url
                elif audio_path and auto_upload:
                    if progress_callback:
                        progress_callback(40, "上传音频...")

                    import asyncio
                    try:
                        final_audio_url = asyncio.get_event_loop().run_until_complete(
                            self._upload_if_needed(audio_path, None, "audio", progress_callback)
                        )
                    except RuntimeError:
                        final_audio_url = asyncio.run(
                            self._upload_if_needed(audio_path, None, "audio", progress_callback)
                        )

                if not final_audio_url:
                    raise ValueError("需要提供 audio_url 或 audio_path")

                # 处理参考图片（可选）
                final_ref_image_url = None
                if ref_image_url:
                    final_ref_image_url = ref_image_url
                elif ref_image_path and auto_upload:
                    if progress_callback:
                        progress_callback(60, "上传参考图片...")

                    import asyncio
                    try:
                        final_ref_image_url = asyncio.get_event_loop().run_until_complete(
                            self._upload_if_needed(ref_image_path, None, "image", progress_callback)
                        )
                    except RuntimeError:
                        final_ref_image_url = asyncio.run(
                            self._upload_if_needed(ref_image_path, None, "image", progress_callback)
                        )

                if progress_callback:
                    progress_callback(70, "提交视频生成任务...")

                logger.info(f"提交视频生成任务 - video_url: {final_video_url}, audio_url: {final_audio_url}")

                # 使用VideoRetalk客户端生成视频
                result = self.client.generate_video(
                    video_url=final_video_url,
                    audio_url=final_audio_url,
                    ref_image_url=final_ref_image_url or "",
                    video_extension=video_extension,
                    output_path=None,  # 不下载，只返回URL
                    wait=True
                )

                if progress_callback:
                    progress_callback(90, "视频生成完成，处理返回结果...")

                # 获取生成的视频URL
                generated_video_url = result.get("video_url")

                # 如果返回的是本地路径，上传到OSS
                if generated_video_url and not generated_video_url.startswith("http"):
                    if progress_callback:
                        progress_callback(95, "上传生成的视频到OSS...")

                    import asyncio
                    try:
                        upload_result = asyncio.get_event_loop().run_until_complete(
                            self.storage.upload_file_async(
                                file_path=generated_video_url,
                                file_type="video"
                            )
                        )
                        generated_video_url = upload_result.get("oss_url")
                        logger.info(f"生成的视频已上传到OSS: {generated_video_url}")
                    except RuntimeError:
                        upload_result = asyncio.run(
                            self.storage.upload_file_async(
                                file_path=generated_video_url,
                                file_type="video"
                            )
                        )
                        generated_video_url = upload_result.get("oss_url")

                if progress_callback:
                    progress_callback(100, "全部完成")

                return {
                    "task_id": result.get("request_id"),
                    "video_url": generated_video_url,  # 确保是公网URL
                    "status": "SUCCESS",
                    "input_urls": {
                        "video_url": final_video_url,
                        "audio_url": final_audio_url,
                        "ref_image_url": final_ref_image_url
                    }
                }

            except Exception as e:
                logger.error(f"视频生成失败: {e}")
                raise

        return await loop.run_in_executor(self.executor, _generate)

    async def query_task_async(self, task_id: str) -> Dict[str, Any]:
        """
        查询视频生成任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态
        """
        loop = asyncio.get_event_loop()

        def _query():
            try:
                result = self.client.query_task(task_id)
                return result
            except Exception as e:
                logger.error(f"查询任务失败: {e}")
                return {
                    "task_id": task_id,
                    "status": "UNKNOWN",
                    "error": str(e)
                }

        return await loop.run_in_executor(self.executor, _query)
