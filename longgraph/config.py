"""
统一配置管理
所有环境变量和配置项集中管理
"""

import os
from pathlib import Path
from typing import Literal, Dict, Any

from dotenv import load_dotenv

# 加载 .env 文件（从项目根目录，override=True 确保覆盖已存在的环境变量）
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / '.env', override=True)

# 项目根目录
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
OUTPUT_DIR = DATA_DIR / "output"

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


# ================================================================
# API Keys
# ================================================================

class APIKeys:
    """API 密钥配置"""

    @staticmethod
    def get_deepseek() -> str:
        """DeepSeek API Key - 用于文案生成"""
        key = os.getenv("DEEPSEEK_API_KEY", "")
        if not key:
            raise ValueError("未设置 DEEPSEEK_API_KEY 环境变量")
        return key

    @staticmethod
    def get_zhipu() -> str:
        """智谱 AI API Key - 用于文案生成和智谱 TTS"""
        key = os.getenv("ZAI_API_KEY", "")
        if not key:
            raise ValueError("未设置 ZAI_API_KEY 环境变量")
        return key

    @staticmethod
    def get_dashscope() -> str:
        """阿里云 DashScope API Key - 用于 CosyVoice TTS"""
        key = os.getenv("DASHSCOPE_API_KEY", "")
        if not key:
            raise ValueError("未设置 DASHSCOPE_API_KEY 环境变量")
        return key

    @staticmethod
    def check_all() -> dict:
        """检查所有 API Key 是否配置"""
        return {
            "deepseek": bool(os.getenv("DEEPSEEK_API_KEY")),
            "zhipu": bool(os.getenv("ZAI_API_KEY")),
            "dashscope": bool(os.getenv("DASHSCOPE_API_KEY")),
        }


# ================================================================
# 文案生成模型配置
# ================================================================

class LLMModel:
    """大语言模型配置"""

    # DeepSeek
    DEEPSEEK_ID = "deepseek"
    DEEPSEEK_NAME = "DeepSeek"
    DEEPSEEK_MODEL = "deepseek-chat"
    DEEPSEEK_BASE_URL = "https://api.deepseek.com"

    # 智谱 GLM
    ZHIPU_ID = "zhipu"
    ZHIPU_NAME = "智谱 GLM"
    ZHIPU_MODEL = "glm-4-flash"
    ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

    @staticmethod
    def get_model_config(model_id: Literal["deepseek", "zhipu"]) -> dict:
        """获取模型配置"""
        configs = {
            "deepseek": {
                "id": LLMModel.DEEPSEEK_ID,
                "name": LLMModel.DEEPSEEK_NAME,
                "model": LLMModel.DEEPSEEK_MODEL,
                "base_url": LLMModel.DEEPSEEK_BASE_URL,
                "api_key": APIKeys.get_deepseek,
            },
            "zhipu": {
                "id": LLMModel.ZHIPU_ID,
                "name": LLMModel.ZHIPU_NAME,
                "model": LLMModel.ZHIPU_MODEL,
                "base_url": LLMModel.ZHIPU_BASE_URL,
                "api_key": APIKeys.get_zhipu,
            },
        }
        return configs.get(model_id, configs["deepseek"])


# ================================================================
# TTS 配置
# ================================================================

class TTSConfig:
    """TTS 语音合成配置"""

    # 智谱 TTS
    ZHIPU_ID = "zhipu"
    ZHIPU_NAME = "智谱 TTS"
    ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/audio/speech"
    ZHIPU_VOICES = {
        "tongtong": "通通 (女声，亲切)",
        "zhiqiang": "志强 (男声，稳重)",
    }
    ZHIPU_DEFAULT_VOICE = "tongtong"
    ZHIPU_FORMAT = "wav"

    # 阿里 CosyVoice
    COSYVOICE_ID = "cosyvoice"
    COSYVOICE_NAME = "阿里 CosyVoice"
    COSYVOICE_DEFAULT_MODEL = "cosyvoice-v3.5-flash"
    COSYVOICE_MODELS = {
        "cosyvoice-v3.5-flash": "CosyVoice v3.5 Flash (快速，推荐)",
        "cosyvoice-v3.5-plus": "CosyVoice v3.5 Plus (高质量)",
        "cosyvoice-v3-flash": "CosyVoice v3 Flash",
        "cosyvoice-v3-plus": "CosyVoice v3 Plus",
        "cosyvoice-v1": "CosyVoice v1",
        "cosyvoice-v1-zh": "CosyVoice v1 中文",
    }
    COSYVOICE_FORMAT = "mp3"
    COSYVOICE_WS_URL = 'wss://dashscope.aliyuncs.com/api-ws/v1/inference'
    COSYVOICE_HTTP_URL = 'https://dashscope.aliyuncs.com/api/v1'

    @staticmethod
    def get_tts_config(tts_id: Literal["zhipu", "cosyvoice"]) -> dict:
        """获取 TTS 配置"""
        configs = {
            "zhipu": {
                "id": TTSConfig.ZHIPU_ID,
                "name": TTSConfig.ZHIPU_NAME,
                "api_url": TTSConfig.ZHIPU_API_URL,
                "voices": TTSConfig.ZHIPU_VOICES,
                "default_voice": TTSConfig.ZHIPU_DEFAULT_VOICE,
                "format": TTSConfig.ZHIPU_FORMAT,
                "api_key": APIKeys.get_zhipu,
            },
            "cosyvoice": {
                "id": TTSConfig.COSYVOICE_ID,
                "name": TTSConfig.COSYVOICE_NAME,
                "models": TTSConfig.COSYVOICE_MODELS,
                "default_model": TTSConfig.COSYVOICE_DEFAULT_MODEL,
                "format": TTSConfig.COSYVOICE_FORMAT,
                "ws_url": TTSConfig.COSYVOICE_WS_URL,
                "http_url": TTSConfig.COSYVOICE_HTTP_URL,
                "api_key": APIKeys.get_dashscope,
            },
        }
        return configs.get(tts_id, configs["zhipu"])


# ================================================================
# 抖音数据抓取配置
# ================================================================

class DouyinConfig:
    """抖音数据抓取配置"""

    @staticmethod
    def get_cookie() -> str:
        """获取抖音 Cookie"""
        return os.getenv("DOUYYIN_COOKIE", "")

    # 默认抓取配置
    DEFAULT_MAX_VIDEOS = 100
    DEFAULT_TOP_N = 30  # 分析时取热度最高的 N 个


# ================================================================
# 视频生成配置
# ================================================================

class VideoConfig:
    """视频生成配置"""

    # 阿里 VideoRetalk
    VIDEORETALK_ID = "videoretalk"
    VIDEORETALK_NAME = "阿里 VideoRetalk"
    VIDEORETALK_MODEL = "videoretalk"
    VIDEORETALK_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image2video/video-synthesis/"
    VIDEORETALK_ASYNC_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image2video/video-synthesis/"

    @staticmethod
    def get_video_config(video_id: Literal["videoretalk"]) -> dict:
        """获取视频生成配置"""
        configs = {
            "videoretalk": {
                "id": VideoConfig.VIDEORETALK_ID,
                "name": VideoConfig.VIDEORETALK_NAME,
                "model": VideoConfig.VIDEORETALK_MODEL,
                "api_url": VideoConfig.VIDEORETALK_API_URL,
                "async_url": VideoConfig.VIDEORETALK_ASYNC_URL,
                "api_key": APIKeys.get_dashscope,
            },
        }
        return configs.get(video_id, configs["videoretalk"])


# ================================================================
# 路径配置
# ================================================================

class Paths:
    """文件路径配置"""

    @staticmethod
    def get_data_dir() -> Path:
        return DATA_DIR

    @staticmethod
    def get_audio_dir() -> Path:
        return AUDIO_DIR

    @staticmethod
    def get_output_dir() -> Path:
        return OUTPUT_DIR


# ================================================================
# 便捷函数
# ================================================================

def print_api_status():
    """打印 API 配置状态"""
    status = APIKeys.check_all()
    print("\n" + "=" * 50)
    print("API 配置状态")
    print("=" * 50)
    print(f"  DeepSeek (文案生成):  {'✓ 已配置' if status['deepseek'] else '✗ 未配置'}")
    print(f"  智谱 AI (文案+TTS):   {'✓ 已配置' if status['zhipu'] else '✗ 未配置'}")
    print(f"  阿里 CosyVoice:      {'✓ 已配置' if status['dashscope'] else '✗ 未配置'}")
    print("=" * 50)


if __name__ == "__main__":
    print_api_status()
    print(f"\n数据目录: {DATA_DIR}")
    print(f"音频目录: {AUDIO_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
