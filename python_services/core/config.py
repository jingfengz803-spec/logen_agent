"""
配置管理模块 - 统一配置
整合所有模块的配置：API、抖音、AI、TTS、视频等
"""

import os
from pathlib import Path
from typing import Optional, List
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """统一应用配置"""

    # ==================== 应用基础配置 ====================
    APP_NAME: str = "短视频创作自动化API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8088

    # ==================== 路径配置 ====================
    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    OUTPUT_DIR: str = Field(default_factory=lambda: str(Path(__file__).parent.parent.parent / "output"))
    TEMP_DIR: str = Field(default_factory=lambda: str(Path(__file__).parent.parent / "temp"))
    AUDIO_DIR: str = Field(default_factory=lambda: str(Path(__file__).parent.parent.parent / "output" / "audio"))

    @property
    def output_dir_path(self) -> Path:
        """获取 OUTPUT_DIR 的 Path 对象"""
        return Path(self.OUTPUT_DIR)

    @property
    def temp_dir_path(self) -> Path:
        """获取 TEMP_DIR 的 Path 对象"""
        return Path(self.TEMP_DIR)

    @property
    def audio_dir_path(self) -> Path:
        """获取 AUDIO_DIR 的 Path 对象"""
        return Path(self.AUDIO_DIR)

    # 子模块路径
    @property
    def douyin_tool_path(self) -> Path:
        return self.BASE_DIR / "douyin_data_tool"

    @property
    def longgraph_path(self) -> Path:
        return self.BASE_DIR / "longgraph"

    # ==================== MySQL 配置 ====================
    DB_HOST: str = Field("localhost", alias="DB_HOST")
    DB_PORT: int = Field(3306, alias="DB_PORT")
    DB_USER: str = Field("root", alias="DB_USER")
    DB_PASSWORD: str = Field("", alias="DB_PASSWORD")
    DB_NAME: str = Field("logen_agent", alias="DB_NAME")

    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    # ==================== JWT 配置 ====================
    JWT_SECRET_KEY: str = Field(default="", alias="JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天

    @property
    def jwt_secret(self) -> str:
        """获取 JWT 密钥，未配置时自动生成（重启后会话失效）"""
        if self.JWT_SECRET_KEY:
            return self.JWT_SECRET_KEY
        import hashlib
        machine_key = f"auto-{hashlib.sha256(os.urandom(32)).hexdigest()[:32]}"
        return machine_key

    # ==================== CORS 配置 ====================
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8088",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8088",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # ==================== 任务配置 ====================
    MAX_CONCURRENT_TASKS: int = 5
    TASK_TIMEOUT_SECONDS: int = 3600  # 1小时

    # ==================== 文件上传配置 ====================
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_AUDIO_EXTENSIONS: List[str] = [".mp3", ".wav", ".m4a", ".aac"]
    ALLOWED_VIDEO_EXTENSIONS: List[str] = [".mp4", ".mov", ".avi"]
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".webp"]

    # ==================== OSS 配置 ====================
    OSS_ACCESS_KEY_ID: Optional[str] = Field(None, alias="OSS_ACCESS_KEY_ID")
    OSS_ACCESS_KEY_SECRET: Optional[str] = Field(None, alias="OSS_ACCESS_KEY_SECRET")
    OSS_BUCKET_NAME: Optional[str] = Field(None, alias="OSS_BUCKET_NAME")
    OSS_ENDPOINT: Optional[str] = Field(None, alias="OSS_ENDPOINT")
    OSS_ENABLED: bool = True

    # ==================== 阿里云 Dashscope 配置 ====================
    DASHSCOPE_API_KEY: Optional[str] = Field(None, alias="DASHSCOPE_API_KEY")

    # ==================== 抖音配置 ====================
    DOUYIN_COOKIE: Optional[str] = Field(None, alias="DOUYIN_COOKIE")
    DOUYIN_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # ==================== AI 模型配置 ====================
    # DeepSeek
    DEEPSEEK_API_KEY: Optional[str] = Field(None, alias="DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    # 智谱 AI
    ZHIPU_API_KEY: Optional[str] = Field(None, alias="ZHIPU_API_KEY")

    # OpenAI 兼容
    OPENAI_API_KEY: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # ==================== TTS 配置 ====================
    TTS_DEFAULT_MODEL: str = "cosyvoice-v3.5-plus"
    TTS_DEFAULT_FORMAT: str = "mp3"
    TTS_MAX_RETRIES: int = 6

    # ==================== Redis 配置（可选） ====================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # ==================== 日志配置 ====================
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = Field(default_factory=lambda: str(Path(__file__).parent.parent / "logs"))

    # ==================== 兼容方法 ====================
    def get(self, key: str, default=None):
        """获取配置值（兼容旧代码）"""
        return getattr(self, key.upper(), default)

    class Config:
        # 从项目根目录读取 .env 文件
        env_file = Path(__file__).parent.parent.parent / ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略未定义的环境变量


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 全局配置实例
settings = get_settings()
