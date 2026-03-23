"""
配置管理模块
统一管理所有API服务的配置
"""

import os
from pathlib import Path
from typing import Optional, List
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "短视频创作自动化API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8088

    # CORS配置
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # JWT配置
    JWT_SECRET_KEY: str = Field(default="your-secret-key-change-in-production", alias="JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天

    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # 路径配置
    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    OUTPUT_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "longgraph" / "data")
    TEMP_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "temp")

    # 任务配置
    MAX_CONCURRENT_TASKS: int = 5
    TASK_TIMEOUT_SECONDS: int = 3600  # 1小时

    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_AUDIO_EXTENSIONS: List[str] = [".mp3", ".wav", ".m4a", ".aac"]
    ALLOWED_VIDEO_EXTENSIONS: List[str] = [".mp4", ".mov", ".avi"]
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".webp"]

    # OSS 配置（用于文件上传）
    OSS_ACCESS_KEY_ID: Optional[str] = Field(None, alias="OSS_ACCESS_KEY_ID")
    OSS_ACCESS_KEY_SECRET: Optional[str] = Field(None, alias="OSS_ACCESS_KEY_SECRET")
    OSS_BUCKET_NAME: Optional[str] = Field(None, alias="OSS_BUCKET_NAME")
    OSS_ENDPOINT: Optional[str] = Field(None, alias="OSS_ENDPOINT")
    OSS_ENABLED: bool = True  # 是否启用 OSS 上传

    class Config:
        # 从项目根目录读取 .env 文件
        env_file = Path(__file__).parent.parent.parent / ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def douyin_tool_path(self) -> Path:
        """抖音工具路径"""
        return self.BASE_DIR / "douyin_data_tool"

    @property
    def longgraph_path(self) -> Path:
        """Longgraph工具路径"""
        return self.BASE_DIR / "longgraph"


class APISettings(Settings):
    """API服务特定配置"""

    # 服务类型: douyin, ai, tts, video, all
    SERVICE_TYPE: str = "all"

    # 服务端口映射
    DOUYIN_SERVICE_PORT: int = 8087
    AI_SERVICE_PORT: int = 8088
    TTS_SERVICE_PORT: int = 8089
    VIDEO_SERVICE_PORT: int = 8090


@lru_cache()
def get_settings() -> APISettings:
    """获取配置单例"""
    return APISettings()


# 全局配置实例
settings = get_settings()
