"""
请求模型 - 定义API请求的数据结构
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum


# ==================== 通用请求模型 ====================

class CommonRequest(BaseModel):
    """通用请求基类"""
    request_id: Optional[str] = Field(None, description="请求ID，用于追踪")


# ==================== 抖音抓取请求模型 ====================

class FetchUserVideosRequest(CommonRequest):
    """抓取用户视频请求"""
    url: str = Field(..., description="抖音用户主页URL", min_length=10)
    max_count: int = Field(100, description="最大抓取数量", ge=1, le=200)
    enable_filter: bool = Field(False, description="是否启用过滤")
    min_likes: int = Field(50, description="最小点赞数", ge=0)
    min_comments: int = Field(0, description="最小评论数", ge=0)
    top_n: int = Field(0, description="返回Top N热门视频，0表示全部", ge=0, le=50)
    sort_by: str = Field("like", description="排序字段: like/comment/share")
    wait: bool = Field(False, description="是否等待完成后直接返回结果")

    @validator("url")
    def validate_url(cls, v):
        if "douyin.com" not in v:
            raise ValueError("URL必须是抖音链接")
        return v


class FetchTopicVideosRequest(CommonRequest):
    """抓取话题视频请求"""
    topic: str = Field(..., description="话题名称", min_length=1)
    max_count: int = Field(50, description="最大抓取数量", ge=1, le=100)


class FetchHotListRequest(CommonRequest):
    """抓取热榜请求"""
    cate_id: Optional[int] = Field(None, description="分类ID")


# ==================== AI分析请求模型 ====================

class AnalyzeViralRequest(CommonRequest):
    """火爆原因分析请求"""
    video_data: List[dict] = Field(..., description="视频数据列表")
    video_ids: Optional[List[str]] = Field(None, description="指定分析的视频ID列表")


class AnalyzeStyleRequest(CommonRequest):
    """风格特征分析请求"""
    video_data: List[dict] = Field(..., description="视频数据列表")
    analysis_dimensions: List[str] = Field(
        default=["文案风格", "视频类型", "拍摄特征", "高频词汇", "标签策略", "音乐风格"],
        description="分析维度"
    )


class GenerateScriptRequest(CommonRequest):
    """生成脚本请求"""
    style_analysis: dict = Field(..., description="风格分析结果")
    viral_analysis: dict = Field(..., description="火爆原因分析结果")
    topic: str = Field(..., description="新主题", min_length=1)
    target_duration: float = Field(20.0, description="目标时长(秒)", ge=10.0, le=180.0)


class FullAnalysisRequest(CommonRequest):
    """完整分析请求（抓取+分析+生成脚本）"""
    douyin_url: str = Field(..., description="抖音用户主页URL")
    topic: str = Field(..., description="新主题")
    max_videos: int = Field(100, description="分析视频数量", ge=10, le=200)
    enable_viral_analysis: bool = Field(True, description="启用火爆原因分析")
    enable_style_analysis: bool = Field(True, description="启用风格分析")
    generate_script: bool = Field(True, description="是否生成脚本")
    target_duration: float = Field(60.0, description="TTS目标时长（秒）", ge=5.0, le=300.0)


# ==================== TTS请求模型 ====================

class TTSType(str, Enum):
    """TTS类型"""
    COSYVOICE = "cosyvoice"
    GLM = "glm"


class CreateVoiceRequest(CommonRequest):
    """创建音色请求"""
    audio_url: str = Field(..., description="音色音频公网URL")
    prefix: str = Field("myvoice", description="音色前缀", max_length=10, pattern="^[a-zA-Z0-9_]+$")
    model: str = Field("cosyvoice-v3.5-flash", description="TTS模型")
    language_hints: Optional[List[str]] = Field(None, description="语言提示")
    wait_ready: bool = Field(True, description="是否等待就绪")


class CreateVoiceWithPreviewRequest(CommonRequest):
    """创建音色并生成试听音频请求"""
    audio_url: str = Field(..., description="音色音频公网URL")
    prefix: str = Field("myvoice", description="音色前缀", max_length=10, pattern="^[a-zA-Z0-9_]+$")
    model: str = Field("cosyvoice-v3.5-flash", description="TTS模型")
    language_hints: Optional[List[str]] = Field(None, description="语言提示")
    preview_text: str = Field("你好，这是我的音色。", description="试听文本")
    auto_upload_oss: bool = Field(True, description="是否自动上传试听音频到OSS")


class SpeechRequest(CommonRequest):
    """语音合成请求"""
    text: str = Field(..., description="要合成的文本", min_length=1)
    voice_id: str = Field(..., description="音色ID")
    model: Optional[str] = Field(None, description="TTS模型（默认使用音色对应模型）")
    output_format: str = Field("mp3", description="输出格式", pattern="^(mp3|wav|pcm)$")


class SpeechSegmentsRequest(CommonRequest):
    """分段语音合成请求"""
    segments: List[str] = Field(..., description="分段文本列表")
    voice_id: str = Field(..., description="音色ID")
    model: Optional[str] = Field(None, description="TTS模型")
    output_format: str = Field("mp3", description="输出格式")


class TTSScriptRequest(CommonRequest):
    """完整TTS脚本请求"""
    full_text: str = Field(..., description="完整台词")
    segments: List[str] = Field(..., description="分段台词")
    voice_id: str = Field(..., description="音色ID")
    model: Optional[str] = Field(None, description="TTS模型")


# ==================== 视频生成请求模型 ====================

class VideoGenerateRequest(CommonRequest):
    """视频生成请求"""
    video_url: str = Field(..., description="参考视频公网URL")
    audio_url: str = Field(..., description="合成音频公网URL")
    ref_image_url: Optional[str] = Field(None, description="参考图片URL（可选）")
    video_extension: bool = Field(True, description="是否扩展视频以匹配音频长度")
    resolution: Optional[str] = Field(None, description="分辨率（如 1280x720）")


# ==================== 完整工作流请求模型 ====================

class WorkflowType(str, Enum):
    """工作流类型"""
    FULL = "full"                    # 完整流程（含视频）
    WITHOUT_VIDEO = "without_video"  # 不含视频
    ANALYSIS_ONLY = "analysis_only"  # 仅分析


class FullWorkflowRequest(CommonRequest):
    """完整工作流请求"""
    douyin_url: str = Field(..., description="抖音用户主页URL")
    topic: str = Field(..., description="新主题")
    voice_id: Optional[str] = Field(None, description="音色ID")
    ref_video_url: Optional[str] = Field(None, description="参考视频URL")
    workflow_type: WorkflowType = Field(WorkflowType.WITHOUT_VIDEO, description="工作流类型")
    max_videos: int = Field(100, description="分析视频数量")
    output_name: Optional[str] = Field(None, description="输出文件名前缀")


# ==================== 存储请求模型 ====================

class UploadByPathRequest(CommonRequest):
    """通过路径上传文件请求"""
    file_path: str = Field(..., description="本地文件路径")
    file_type: Optional[str] = Field(None, description="文件类型（不指定则自动识别）")
    force_reupload: bool = Field(False, description="是否强制重新上传")
    custom_object_name: Optional[str] = Field(None, description="自定义 OSS 对象名")
