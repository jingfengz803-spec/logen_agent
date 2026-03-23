"""
TTS语音合成服务
封装cosyvoice_tts和glm_tts模块的API
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

logger = get_logger("service:tts")


class TTSService:
    """TTS语音合成服务"""

    def __init__(self):
        self.longgraph_dir = settings.longgraph_path
        self.executor = ThreadPoolExecutor(max_workers=3)
        self._cosyvoice_client = None

    @property
    def cosyvoice_client(self):
        """延迟初始化CosyVoice客户端 - 每次都创建新实例以避免 monkey-patch 缓存问题"""
        sys.path.insert(0, str(self.longgraph_dir))
        # 强制重新加载模块以获取最新代码
        if 'cosyvoice_tts' in sys.modules:
            del sys.modules['cosyvoice_tts']
        from cosyvoice_tts import CosyVoiceTTSClient
        return CosyVoiceTTSClient()

    async def create_voice_async(
        self,
        audio_url: str,
        prefix: str = "myvoice",
        model: str = "cosyvoice-v3.5-flash",
        language_hints: Optional[List[str]] = None,
        wait_ready: bool = True
    ) -> Dict[str, Any]:
        """
        异步创建音色

        Args:
            audio_url: 音色音频URL
            prefix: 音色前缀
            model: TTS模型
            language_hints: 语言提示
            wait_ready: 是否等待就绪

        Returns:
            创建结果
        """
        loop = asyncio.get_event_loop()

        def _create():
            try:
                result = self.cosyvoice_client.create_voice(
                    audio_url=audio_url,
                    prefix=prefix,
                    model=model,
                    language_hints=language_hints,
                    wait_ready=wait_ready
                )

                voice_id = result.get("voice_id")

                # 保存到本地 voices.txt 文件
                if voice_id:
                    try:
                        from pathlib import Path
                        voices_file = Path(self.longgraph_dir) / "data" / "voices.txt"
                        voices_file.parent.mkdir(parents=True, exist_ok=True)

                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y-%m-%d")

                        with open(voices_file, "a", encoding="utf-8") as f:
                            f.write(f"{voice_id} | {prefix} | {timestamp}\n")

                        logger.info(f"音色ID已保存到 voices.txt: {voice_id}")
                    except Exception as e:
                        logger.warning(f"保存音色ID失败: {e}")

                return {
                    "voice_id": voice_id,
                    "prefix": result.get("prefix", prefix),
                    "model": result.get("model", model),
                    "status": result.get("status", "DEPLOYING")
                }

            except Exception as e:
                logger.error(f"创建音色失败: {e}")
                raise

        return await loop.run_in_executor(self.executor, _create)

    async def list_voices_async(self) -> List[Dict[str, Any]]:
        """异步获取音色列表"""
        loop = asyncio.get_event_loop()

        def _list():
            try:
                voices = self.cosyvoice_client.list_voices()
                return voices
            except Exception as e:
                logger.error(f"获取音色列表失败: {e}")
                return []

        return await loop.run_in_executor(self.executor, _list)

    async def get_voice_async(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """异步查询单个音色"""
        loop = asyncio.get_event_loop()

        def _get():
            try:
                return self.cosyvoice_client.query_voice(voice_id)
            except Exception as e:
                logger.error(f"查询音色失败: {e}")
                return None

        return await loop.run_in_executor(self.executor, _get)

    async def speech_async(
        self,
        text: str,
        voice_id: str,
        model: Optional[str] = None,
        output_format: str = "mp3"
    ) -> Dict[str, Any]:
        """
        异步语音合成

        Args:
            text: 要合成的文本
            voice_id: 音色ID
            model: TTS模型
            output_format: 输出格式

        Returns:
            合成结果
        """
        loop = asyncio.get_event_loop()

        def _speech():
            try:
                # 生成输出路径
                from pathlib import Path
                output_dir = settings.OUTPUT_DIR / "audio"
                output_dir.mkdir(parents=True, exist_ok=True)
                import time
                timestamp = int(time.time() * 1000)
                output_path = output_dir / f"tts_{timestamp}.{output_format}"

                # 调试：记录传递的参数
                # logger.info(f"[TTS] 调用参数: text='{text}', voice_id='{voice_id[:30]}...', model='{model}'")

                output_path = self.cosyvoice_client.speech(
                    text=text,
                    voice=voice_id,
                    model=model,
                    output_path=str(output_path)
                )

                # 计算文件大小和时长
                file_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0
                # 估算时长（假设平均 16kbps）
                estimated_duration = file_size / 16000 if file_size > 0 else 0

                return {
                    "audio_path": str(output_path),
                    "text": text,
                    "format": output_format,
                    "size": file_size,
                    "duration": estimated_duration
                }

            except Exception as e:
                logger.error(f"语音合成失败: {e}")
                raise

        return await loop.run_in_executor(self.executor, _speech)

    async def speech_segments_async(
        self,
        segments: List[str],
        voice_id: str,
        model: Optional[str] = None,
        output_format: str = "mp3"
    ) -> Dict[str, Any]:
        """
        异步分段语音合成

        Args:
            segments: 分段文本列表
            voice_id: 音色ID
            model: TTS模型
            output_format: 输出格式

        Returns:
            合成结果
        """
        loop = asyncio.get_event_loop()

        def _speech():
            try:
                result = self.cosyvoice_client.speech_from_segments(
                    segments=segments,
                    voice_id=voice_id,
                    model=model,
                    output_format=output_format
                )

                return {
                    "full_audio": result.get("full_audio"),
                    "segments": result.get("segments", []),
                    "count": len(segments)
                }

            except Exception as e:
                logger.error(f"分段语音合成失败: {e}")
                raise

        return await loop.run_in_executor(self.executor, _speech)

    async def create_voice_with_preview_async(
        self,
        audio_url: str,
        prefix: str = "myvoice",
        model: str = "cosyvoice-v3.5-flash",
        language_hints: Optional[List[str]] = None,
        preview_text: str = "你好，这是我的音色。",
        auto_upload_oss: bool = True
    ) -> Dict[str, Any]:
        """
        创建音色并生成试听音频

        Args:
            audio_url: 音色音频URL
            prefix: 音色前缀
            model: TTS模型
            language_hints: 语言提示
            preview_text: 试听文本
            auto_upload_oss: 是否自动上传试听音频到OSS

        Returns:
            创建结果，包含voice_id和试听音频URL
        """
        loop = asyncio.get_event_loop()

        def _create_with_preview():
            try:
                # 步骤1: 创建音色
                logger.info(f"开始创建音色: prefix={prefix}, model={model}")
                voice_result = self.cosyvoice_client.create_voice(
                    audio_url=audio_url,
                    prefix=prefix,
                    model=model,
                    language_hints=language_hints,
                    wait_ready=True
                )

                voice_id = voice_result.get("voice_id")
                status = voice_result.get("status", "DEPLOYING")

                if not voice_id:
                    raise Exception("创建音色失败：未返回voice_id")

                # 保存到本地 voices.txt 文件
                try:
                    from pathlib import Path
                    voices_file = Path(self.longgraph_dir) / "data" / "voices.txt"
                    voices_file.parent.mkdir(parents=True, exist_ok=True)

                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y-%m-%d")

                    with open(voices_file, "a", encoding="utf-8") as f:
                        f.write(f"{voice_id} | {prefix} | {timestamp}\n")

                    logger.info(f"音色ID已保存到 voices.txt: {voice_id}")
                except Exception as e:
                    logger.warning(f"保存音色ID失败: {e}")

                # 步骤2: 如果音色就绪，生成试听音频
                preview_audio_url = None
                if status == "OK":
                    logger.info(f"音色已就绪，生成试听音频...")
                    try:
                        # 生成试听音频
                        from pathlib import Path
                        output_dir = settings.OUTPUT_DIR / "audio" / "preview"
                        output_dir.mkdir(parents=True, exist_ok=True)
                        import time
                        timestamp = int(time.time() * 1000)
                        preview_path = output_dir / f"preview_{prefix}_{timestamp}.mp3"

                        self.cosyvoice_client.speech(
                            text=preview_text,
                            voice=voice_id,
                            model=model,
                            output_path=str(preview_path)
                        )

                        # 上传到OSS
                        if auto_upload_oss:
                            from services.storage_service import get_storage_service
                            storage = get_storage_service()

                            # 同步上传
                            import asyncio
                            try:
                                upload_result = asyncio.get_event_loop().run_until_complete(
                                    storage.upload_file_async(
                                        file_path=str(preview_path),
                                        file_type="audio"
                                    )
                                )
                            except RuntimeError:
                                upload_result = asyncio.run(
                                    storage.upload_file_async(
                                        file_path=str(preview_path),
                                        file_type="audio"
                                    )
                                )

                            preview_audio_url = upload_result.get("oss_url")
                            logger.info(f"试听音频已上传到OSS: {preview_audio_url}")
                        else:
                            # 返回本地路径
                            preview_audio_url = str(preview_path)

                    except Exception as e:
                        logger.error(f"生成试听音频失败: {e}")
                        # 试听音频生成失败不影响音色创建

                return {
                    "voice_id": voice_id,
                    "prefix": prefix,
                    "model": model,
                    "status": status,
                    "preview_text": preview_text,
                    "preview_audio_url": preview_audio_url,
                    "is_available": status == "OK"
                }

            except Exception as e:
                logger.error(f"创建音色（含试听）失败: {e}")
                raise

        return await loop.run_in_executor(self.executor, _create_with_preview)

    async def script_to_speech_async(
        self,
        full_text: str,
        segments: List[str],
        voice_id: str,
        model: Optional[str] = None,
        auto_upload_oss: bool = False,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        异步TTS脚本转语音

        Args:
            full_text: 完整台词
            segments: 分段台词
            voice_id: 音色ID
            model: TTS模型
            auto_upload_oss: 是否自动上传到 OSS
            progress_callback: 进度回调

        Returns:
            合成结果，包含 OSS URL（如果 auto_upload_oss=True）
        """
        loop = asyncio.get_event_loop()

        def _speech():
            try:
                # 生成输出路径
                from pathlib import Path
                output_dir = settings.OUTPUT_DIR / "audio"
                output_dir.mkdir(parents=True, exist_ok=True)
                import time
                timestamp = int(time.time() * 1000)
                
                if progress_callback:
                    progress_callback(20, "合成完整音频...")

                # 合成完整版
                full_audio_path = output_dir / f"full_{timestamp}.{output_format}"
                full_result = self.cosyvoice_client.speech(
                    text=full_text,
                    voice_id=voice_id,
                    model=model,
                    output_path=str(full_audio_path)
                )

                if progress_callback:
                    progress_callback(60, "合成分段音频...")

                # 合成分段
                segments_dir = output_dir / "segments"
                segments_result = self.cosyvoice_client.speech_from_segments(
                    segments=segments,
                    voice_id=voice_id,
                    model=model,
                    output_dir=str(segments_dir)
                )

                result = {
                    "full_audio": str(full_audio_path),
                    "segments_audio": segments_result.get("segments", []),
                    "full_audio_path": str(full_audio_path)
                }

                # 自动上传到 OSS
                if auto_upload_oss:
                    if progress_callback:
                        progress_callback(80, "上传音频到 OSS...")

                    # 延迟导入避免循环依赖
                    from services.storage_service import get_storage_service
                    storage = get_storage_service()

                    # 上传完整音频
                    try:
                        upload_result = storage.upload_file_async(
                            file_path=str(full_result),
                            file_type="audio"
                        )
                        # 这里需要在事件循环中运行
                        import asyncio
                        try:
                            upload_result = asyncio.get_event_loop().run_until_complete(upload_result)
                        except RuntimeError:
                            # 如果没有运行中的事件循环，创建一个新的
                            upload_result = asyncio.run(upload_result)

                        result["full_audio_oss_url"] = upload_result.get("oss_url")
                        result["full_audio_hash"] = upload_result.get("file_hash")

                        logger.info(f"完整音频已上传到 OSS: {upload_result.get('oss_url')}")
                    except Exception as e:
                        logger.warning(f"上传完整音频到 OSS 失败: {e}")

                    # 上传分段音频
                    segment_urls = []
                    for i, seg_path in enumerate(segments_result.get("segments", [])):
                        try:
                            upload_result = storage.upload_file_async(
                                file_path=str(seg_path),
                                file_type="audio"
                            )
                            try:
                                upload_result = asyncio.get_event_loop().run_until_complete(upload_result)
                            except RuntimeError:
                                upload_result = asyncio.run(upload_result)

                            segment_urls.append({
                                "index": i,
                                "local_path": str(seg_path),
                                "oss_url": upload_result.get("oss_url"),
                                "file_hash": upload_result.get("file_hash")
                            })
                        except Exception as e:
                            logger.warning(f"上传分段音频 {i} 到 OSS 失败: {e}")

                    result["segments_audio_oss"] = segment_urls

                return result

            except Exception as e:
                logger.error(f"TTS脚本合成失败: {e}")
                raise

        return await loop.run_in_executor(self.executor, _speech)
