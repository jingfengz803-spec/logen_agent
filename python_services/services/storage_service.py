"""
存储服务 - OSS 文件上传与管理
支持本地文件上传、URL 复用、临时文件管理
"""

import sys
import os
import hashlib
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config import settings
from core.logger import get_logger

logger = get_logger("service:storage")


class FileRecord:
    """文件上传记录"""

    def __init__(
        self,
        file_path: str,
        file_hash: str,
        oss_url: str,
        oss_object_name: str,
        file_type: str = "unknown",
        size: int = 0
    ):
        self.file_path = file_path
        self.file_hash = file_hash
        self.oss_url = oss_url
        self.oss_object_name = oss_object_name
        self.file_type = file_type
        self.size = size
        self.uploaded_at = datetime.now()
        self.last_accessed_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "file_hash": self.file_hash,
            "oss_url": self.oss_url,
            "oss_object_name": self.oss_object_name,
            "file_type": self.file_type,
            "size": self.size,
            "uploaded_at": self.uploaded_at.isoformat(),
            "last_accessed_at": self.last_accessed_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileRecord":
        record = cls(
            file_path=data["file_path"],
            file_hash=data["file_hash"],
            oss_url=data["oss_url"],
            oss_object_name=data["oss_object_name"],
            file_type=data.get("file_type", "unknown"),
            size=data.get("size", 0)
        )
        if "uploaded_at" in data:
            record.uploaded_at = datetime.fromisoformat(data["uploaded_at"])
        if "last_accessed_at" in data:
            record.last_accessed_at = datetime.fromisoformat(data["last_accessed_at"])
        return record


class StorageService:
    """
    存储服务 - 统一管理文件上传到 OSS

    功能：
    1. 自动上传本地文件到 OSS
    2. 文件 hash 去重（相同文件不重复上传）
    3. 上传记录持久化
    4. URL 复用
    5. 临时文件管理
    """

    # 文件类型映射
    FILE_TYPE_MAPPING = {
        ".mp3": "audio",
        ".wav": "audio",
        ".m4a": "audio",
        ".aac": "audio",
        ".mp4": "video",
        ".mov": "video",
        ".avi": "video",
        ".mkv": "video",
        ".jpg": "image",
        ".jpeg": "image",
        ".png": "image",
        ".webp": "image",
    }

    # OSS 目录映射
    OSS_DIR_MAPPING = {
        "audio": "audio",
        "video": "videos",
        "image": "images",
        "unknown": "files"
    }

    def __init__(self):
        self.longgraph_dir = settings.longgraph_path
        self.executor = ThreadPoolExecutor(max_workers=3)
        self._uploader = None
        self._preprocessor = None  # 视频预处理器
        self._records: Dict[str, FileRecord] = {}  # file_hash -> FileRecord
        self._records_file = settings.TEMP_DIR / "upload_records.json"

        # 加载上传记录
        self._load_records()

    @property
    def uploader(self):
        """延迟初始化 OSS 上传器"""
        if self._uploader is None:
            sys.path.insert(0, str(self.longgraph_dir))
            from upload_audio_helper import OSSUploader
            try:
                self._uploader = OSSUploader()
                logger.info("OSS 上传器初始化成功")
            except ValueError as e:
                logger.warning(f"OSS 配置不完整: {e}")
                self._uploader = None
        return self._uploader

    @property
    def preprocessor(self):
        """延迟初始化视频预处理器"""
        if self._preprocessor is None:
            sys.path.insert(0, str(self.longgraph_dir))
            try:
                from video_generator import VideoPreprocessor
                self._preprocessor = VideoPreprocessor
                logger.info("视频预处理器初始化成功")
            except ImportError as e:
                logger.warning(f"视频预处理器不可用: {e}")
                self._preprocessor = False  # 标记为不可用
        return self._preprocessor

    def _preprocess_video_if_needed(self, file_path: str, file_type: str) -> str:
        """
        如果是视频文件，检查并调整分辨率

        Args:
            file_path: 视频文件路径
            file_type: 文件类型

        Returns:
            处理后的文件路径（原路径或调整后的路径）
        """
        if file_type != "video":
            return file_path

        preprocessor = self.preprocessor
        if preprocessor is False:
            logger.warning("视频预处理器不可用，跳过预处理")
            return file_path

        try:
            # 检查是否需要调整分辨率
            if not preprocessor.needs_resize(file_path):
                logger.info(f"视频分辨率符合要求: {file_path}")
                return file_path

            logger.info(f"视频分辨率不符合API要求，正在调整: {file_path}")

            # 调整分辨率
            processed_path = preprocessor.resize_video(file_path)
            logger.info(f"视频已调整分辨率: {processed_path}")
            return processed_path

        except Exception as e:
            logger.warning(f"视频预处理失败: {e}，尝试直接上传原文件")
            return file_path

    def _get_file_hash(self, file_path: str) -> Optional[str]:
        """
        计算文件 MD5 hash

        Args:
            file_path: 文件路径

        Returns:
            MD5 hash，失败返回 None
        """
        try:
            md5_hash = hashlib.md5()
            with open(file_path, "rb") as f:
                # 分块读取大文件
                for chunk in iter(lambda: f.read(8192), b""):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception as e:
            logger.error(f"计算文件 hash 失败: {e}")
            return None

    def _get_file_type(self, file_path: str) -> str:
        """
        根据扩展名获取文件类型

        Args:
            file_path: 文件路径

        Returns:
            文件类型: audio, video, image, unknown
        """
        ext = Path(file_path).suffix.lower()
        return self.FILE_TYPE_MAPPING.get(ext, "unknown")

    def _get_oss_dir(self, file_type: str) -> str:
        """获取 OSS 目录"""
        return self.OSS_DIR_MAPPING.get(file_type, "files")

    def _load_records(self):
        """从文件加载上传记录"""
        if self._records_file.exists():
            try:
                with open(self._records_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for hash_key, record_data in data.items():
                        self._records[hash_key] = FileRecord.from_dict(record_data)
                logger.info(f"加载了 {len(self._records)} 条上传记录")
            except Exception as e:
                logger.warning(f"加载上传记录失败: {e}")

    def _save_records(self):
        """保存上传记录到文件"""
        try:
            self._records_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                hash_key: record.to_dict()
                for hash_key, record in self._records.items()
            }
            with open(self._records_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存上传记录失败: {e}")

    def _update_last_accessed(self, hash_key: str):
        """更新最后访问时间"""
        if hash_key in self._records:
            self._records[hash_key].last_accessed_at = datetime.now()
            self._save_records()

    async def upload_file_async(
        self,
        file_path: str,
        file_type: Optional[str] = None,
        force_reupload: bool = False,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        custom_object_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        异步上传文件到 OSS

        Args:
            file_path: 本地文件路径
            file_type: 文件类型（不指定则自动识别）
            force_reupload: 是否强制重新上传（忽略缓存）
            progress_callback: 进度回调 (progress, message)
            custom_object_name: 自定义 OSS 对象名

        Returns:
            {
                "oss_url": "https://...",
                "oss_object_name": "...",
                "file_hash": "...",
                "file_type": "...",
                "size": 12345,
                "cached": False
            }
        """
        loop = asyncio.get_event_loop()

        def _upload():
            try:
                # 检查文件是否存在
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"文件不存在: {file_path}")

                file_size = file_path_obj.stat().st_size

                if progress_callback:
                    progress_callback(10, "检查文件...")

                # 确定文件类型（提前确定，用于预处理判断）
                _file_type = file_type
                if _file_type is None:
                    _file_type = self._get_file_type(file_path)

                # 视频文件预处理：检查并调整分辨率
                actual_file_path = file_path
                if _file_type == "video":
                    actual_file_path = self._preprocess_video_if_needed(file_path, _file_type)
                    # 如果文件被调整过，更新路径对象
                    if actual_file_path != file_path:
                        file_path_obj = Path(actual_file_path)
                        file_size = file_path_obj.stat().st_size

                # 计算文件 hash（使用处理后的文件）
                file_hash = self._get_file_hash(actual_file_path)
                if not file_hash:
                    raise RuntimeError("无法计算文件 hash")

                if progress_callback:
                    progress_callback(30, "检查缓存...")

                # 检查是否已上传过（复用 URL）
                if not force_reupload and file_hash in self._records:
                    record = self._records[file_hash]
                    # 检查文件是否还存在
                    if Path(record.file_path).exists():
                        logger.info(f"复用已上传的文件 URL: {record.oss_url}")
                        self._update_last_accessed(file_hash)

                        return {
                            "oss_url": record.oss_url,
                            "oss_object_name": record.oss_object_name,
                            "file_hash": file_hash,
                            "file_type": record.file_type or "unknown",
                            "size": record.size,
                            "cached": True
                        }

                if progress_callback:
                    progress_callback(50, "上传到 OSS...")

                # 上传到 OSS
                uploader = self.uploader
                if uploader is None:
                    raise RuntimeError("OSS 上传器未初始化，请检查 OSS 配置")

                # 生成 OSS 对象名
                if custom_object_name:
                    object_name = custom_object_name
                else:
                    oss_dir = self._get_oss_dir(_file_type)
                    # 使用 hash 作为文件名的一部分，避免重复
                    ext = file_path_obj.suffix
                    timestamp = datetime.now().strftime("%Y%m%d")
                    object_name = f"{oss_dir}/{timestamp}/{file_hash[:8]}{ext}"

                # 上传（使用处理后的文件路径）
                oss_url = uploader.upload_file(
                    file_path=actual_file_path,
                    object_name=object_name,
                    public=True
                )

                if progress_callback:
                    progress_callback(90, "保存记录...")

                # 保存记录
                record = FileRecord(
                    file_path=str(file_path_obj.absolute()),
                    file_hash=file_hash,
                    oss_url=oss_url,
                    oss_object_name=object_name,
                    file_type=_file_type,
                    size=file_size
                )
                self._records[file_hash] = record
                self._save_records()

                if progress_callback:
                    progress_callback(100, "上传完成")

                return {
                    "oss_url": oss_url,
                    "oss_object_name": object_name,
                    "file_hash": file_hash,
                    "file_type": _file_type,
                    "size": file_size,
                    "cached": False
                }

            except Exception as e:
                logger.error(f"上传文件失败: {e}")
                raise

        return await loop.run_in_executor(self.executor, _upload)

    async def upload_bytes_async(
        self,
        file_bytes: bytes,
        filename: str,
        file_type: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        异步上传字节数据到 OSS

        Args:
            file_bytes: 文件字节数据
            filename: 文件名（用于确定扩展名和类型）
            file_type: 文件类型（不指定则自动识别）
            progress_callback: 进度回调

        Returns:
            上传结果
        """
        # 保存到临时文件
        temp_dir = settings.TEMP_DIR / "uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)

        import time
        timestamp = int(time.time() * 1000)
        temp_path = temp_dir / f"{timestamp}_{filename}"

        try:
            # 写入临时文件
            with open(temp_path, "wb") as f:
                f.write(file_bytes)

            # 上传
            result = await self.upload_file_async(
                file_path=str(temp_path),
                file_type=file_type,
                progress_callback=progress_callback
            )

            return result

        except Exception as e:
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
            raise

    async def get_url_by_hash(self, file_hash: str) -> Optional[str]:
        """
        根据 hash 获取已上传文件的 URL

        Args:
            file_hash: 文件 MD5 hash

        Returns:
            OSS URL，不存在返回 None
        """
        if file_hash in self._records:
            record = self._records[file_hash]
            self._update_last_accessed(file_hash)
            return record.oss_url
        return None

    async def get_or_upload(
        self,
        file_path: str,
        file_type: Optional[str] = None
    ) -> str:
        """
        获取文件 URL，如果未上传则自动上传

        Args:
            file_path: 文件路径
            file_type: 文件类型

        Returns:
            OSS URL
        """
        result = await self.upload_file_async(file_path, file_type)
        return result["oss_url"]

    def list_records(self, file_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出上传记录

        Args:
            file_type: 过滤文件类型

        Returns:
            记录列表
        """
        records = list(self._records.values())

        if file_type:
            records = [r for r in records if r.file_type == file_type]

        return [
            {
                "file_path": r.file_path,
                "file_hash": r.file_hash,
                "oss_url": r.oss_url,
                "file_type": r.file_type,
                "size": r.size,
                "uploaded_at": r.uploaded_at.isoformat(),
                "last_accessed_at": r.last_accessed_at.isoformat()
            }
            for r in records
        ]

    def cleanup_old_records(self, days: int = 7) -> int:
        """
        清理超过指定天数的记录

        Args:
            days: 天数

        Returns:
            清理的记录数
        """
        cutoff = datetime.now() - timedelta(days=days)
        to_remove = [
            hash_key
            for hash_key, record in self._records.items()
            if record.uploaded_at < cutoff
        ]

        for hash_key in to_remove:
            del self._records[hash_key]

        if to_remove:
            self._save_records()

        logger.info(f"清理了 {len(to_remove)} 条过期记录")
        return len(to_remove)

    def is_oss_configured(self) -> bool:
        """检查 OSS 是否已配置"""
        try:
            return self.uploader is not None
        except Exception:
            return False

    def get_oss_config_status(self) -> Dict[str, Any]:
        """获取 OSS 配置状态"""
        return {
            "configured": self.is_oss_configured(),
            "records_count": len(self._records),
            "temp_dir": str(settings.TEMP_DIR),
            "records_file": str(self._records_file)
        }


# 全局单例
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """获取存储服务单例"""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
