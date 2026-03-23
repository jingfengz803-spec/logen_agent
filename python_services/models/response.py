"""
响应模型 - 定义API响应的数据结构
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== 通用响应模型 ====================

class ResponseCode(int, Enum):
    """响应状态码"""
    SUCCESS = 200
    CREATED = 201
    ACCEPTED = 202
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    TIMEOUT = 408
    CONFLICT = 409
    SERVER_ERROR = 500


class BaseResponse(BaseModel):
    """基础响应模型"""
    code: int = Field(ResponseCode.SUCCESS, description="状态码")
    message: str = Field("success", description="响应消息")
    request_id: Optional[str] = Field(None, description="请求ID")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "success",
                "request_id": "req_123456"
            }
        }


class DataResponse(BaseResponse):
    """带数据的响应模型"""
    data: Optional[Any] = Field(None, description="响应数据")


# ==================== 任务相关响应 ====================

class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskResponse(BaseResponse):
    """任务响应"""
    task_id: Optional[str] = Field(None, description="任务ID")
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    progress: Optional[int] = Field(0, description="进度0-100", ge=0, le=100)
    created_at: Optional[datetime] = Field(None, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    result: Optional[Dict[str, Any]] = Field(None, description="结果")
    error: Optional[str] = Field(None, description="错误信息")
    current_step: Optional[str] = Field(None, description="当前步骤（仅工作流）")


class TaskListResponse(DataResponse):
    """任务列表响应"""
    pass


# ==================== 抖音抓取响应 ====================

class VideoInfo(BaseModel):
    """视频信息"""
    aweme_id: str = Field(..., description="视频ID")
    desc: str = Field(..., description="视频文案")
    desc_clean: Optional[str] = Field(None, description="清理后文案")
    author: str = Field(..., description="作者昵称")
    author_id: str = Field(..., description="作者ID")
    like_count: int = Field(0, description="点赞数")
    comment_count: int = Field(0, description="评论数")
    share_count: int = Field(0, description="分享数")
    play_count: int = Field(0, description="播放数")
    duration: float = Field(0, description="时长(秒)")
    create_time: int = Field(0, description="发布时间戳")
    create_time_str: Optional[str] = Field(None, description="发布时间字符串")
    hashtags: List[str] = Field(default_factory=list, description="话题标签")
    music: Optional[str] = Field(None, description="背景音乐")
    video_url: Optional[str] = Field(None, description="视频链接")
    hot_score: Optional[float] = Field(None, description="热度评分")


class FetchVideosResponse(DataResponse):
    """抓取视频响应"""
    data: List[VideoInfo] = Field(default_factory=list, description="视频列表")
    total: int = Field(0, description="总数")
    filtered_count: int = Field(0, description="过滤后数量")


# ==================== AI分析响应 ====================

class ViralFactor(BaseModel):
    """火爆因素"""
    factor: str = Field(..., description="因素名称")
    score: float = Field(..., description="评分", ge=0, le=100)
    description: str = Field(..., description="描述")


class ViralAnalysisResult(BaseModel):
    """火爆原因分析结果"""
    summary: str = Field(..., description="总体摘要")
    factors: List[ViralFactor] = Field(default_factory=list, description="各维度评分")
    topic_heat: Optional[Dict[str, Any]] = Field(None, description="话题热度分析")
    emotional_resonance: Optional[Dict[str, Any]] = Field(None, description="情绪共鸣分析")
    practicality: Optional[Dict[str, Any]] = Field(None, description="实用性分析")
    entertainment: Optional[Dict[str, Any]] = Field(None, description="娱乐性分析")
    personality_appeal: Optional[Dict[str, Any]] = Field(None, description="人设魅力分析")
    expression_technique: Optional[Dict[str, Any]] = Field(None, description="表达技巧分析")


class StyleAnalysisResult(BaseModel):
    """风格分析结果"""
    summary: str = Field(..., description="总体摘要")
    copywriting_style: Optional[Dict[str, Any]] = Field(None, description="文案风格")
    video_type: Optional[str] = Field(None, description="视频类型")
    shooting_features: Optional[Dict[str, Any]] = Field(None, description="拍摄特征")
    high_frequency_words: Optional[List[str]] = Field(None, description="高频词汇")
    sentence_patterns: Optional[List[str]] = Field(None, description="句式模板")
    hashtag_strategy: Optional[Dict[str, Any]] = Field(None, description="标签策略")
    music_style: Optional[Dict[str, Any]] = Field(None, description="音乐风格")


class GeneratedScript(BaseModel):
    """生成的脚本"""
    title: str = Field(..., description="视频标题")
    description: str = Field(..., description="视频描述")
    hashtags: List[str] = Field(default_factory=list, description="话题标签")
    publish_text: str = Field(..., description="发布文案")
    full_script: str = Field(..., description="完整台词")
    segments: List[str] = Field(default_factory=list, description="分段台词")
    word_count: int = Field(0, description="字数")
    estimated_duration: int = Field(0, description="预估时长(秒)")


class AnalysisResponse(DataResponse):
    """分析响应"""
    viral_analysis: Optional[ViralAnalysisResult] = Field(None, description="火爆原因分析")
    style_analysis: Optional[StyleAnalysisResult] = Field(None, description="风格分析")
    script: Optional[GeneratedScript] = Field(None, description="生成的脚本")


# ==================== TTS响应 ====================

class VoiceInfo(BaseModel):
    """音色信息"""
    voice_id: str = Field(..., description="音色ID")
    prefix: str = Field(..., description="前缀")
    model: str = Field(..., description="模型")
    status: str = Field(..., description="状态: DEPLOYING/OK/UNDEPLOYED")
    created_at: str = Field(..., description="创建时间")
    is_available: bool = Field(..., description="是否可用")


class CreateVoiceResponse(DataResponse):
    """创建音色响应"""
    voice_id: str = Field(..., description="音色ID")
    prefix: str = Field(..., description="前缀")
    model: str = Field(..., description="模型")
    status: str = Field(..., description="状态")


class VoiceListResponse(BaseResponse):
    """音色列表响应"""
    voices: List[VoiceInfo] = Field(default_factory=list, description="音色列表")


class SpeechResponse(DataResponse):
    """语音合成响应"""
    audio_url: str = Field(..., description="音频URL")
    duration: float = Field(0, description="时长(秒)")
    format: str = Field(..., description="音频格式")
    text: str = Field(..., description="合成的文本")


class TTSScriptResponse(DataResponse):
    """TTS脚本响应"""
    full_audio_url: str = Field(..., description="完整音频URL")
    segment_audio_urls: List[str] = Field(default_factory=list, description="分段音频URL")
    total_duration: float = Field(0, description="总时长")


# ==================== 视频生成响应 ====================

class VideoGenerateResponse(DataResponse):
    """视频生成响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="状态")
    video_url: Optional[str] = Field(None, description="视频URL")
    estimated_time: Optional[int] = Field(None, description="预估耗时(秒)")


class VideoStatusResponse(DataResponse):
    """视频任务状态响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="状态")
    progress: int = Field(0, description="进度")
    video_url: Optional[str] = Field(None, description="视频URL")
    error: Optional[str] = Field(None, description="错误信息")


# ==================== 完整工作流响应 ====================

class WorkflowResult(BaseModel):
    """工作流结果"""
    videos: List[VideoInfo] = Field(default_factory=list, description="抓取的视频")
    viral_analysis: Optional[ViralAnalysisResult] = Field(None, description="火爆原因分析")
    style_analysis: Optional[StyleAnalysisResult] = Field(None, description="风格分析")
    script: Optional[GeneratedScript] = Field(None, description="生成的脚本")
    voice_id: Optional[str] = Field(None, description="使用的音色ID")
    audio_urls: Optional[Dict[str, Any]] = Field(None, description="音频URLs")
    video_url: Optional[str] = Field(None, description="视频URL")
    output_files: Optional[Dict[str, str]] = Field(None, description="输出文件路径")


class WorkflowResponse(DataResponse):
    """工作流响应"""
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(..., description="任务状态")
    progress: int = Field(0, description="进度")
    current_step: Optional[str] = Field(None, description="当前步骤")
    result: Optional[WorkflowResult] = Field(None, description="结果")


# ==================== 存储响应 ====================

class FileUploadInfo(BaseModel):
    """文件上传信息"""
    oss_url: str = Field(..., description="OSS 公网 URL")
    oss_object_name: str = Field(..., description="OSS 对象名")
    file_hash: str = Field(..., description="文件 MD5 hash")
    file_type: str = Field(..., description="文件类型")
    size: int = Field(..., description="文件大小（字节）")
    cached: bool = Field(..., description="是否使用缓存")


class FileUploadResponse(DataResponse):
    """文件上传响应"""
    data: FileUploadInfo


class UploadRecordInfo(BaseModel):
    """上传记录信息"""
    file_path: str = Field(..., description="本地文件路径")
    file_hash: str = Field(..., description="文件 hash")
    oss_url: str = Field(..., description="OSS URL")
    file_type: str = Field(..., description="文件类型")
    size: int = Field(..., description="文件大小")
    uploaded_at: str = Field(..., description="上传时间")
    last_accessed_at: str = Field(..., description="最后访问时间")


class UploadRecordsResponse(DataResponse):
    """上传记录列表响应"""
    data: List[UploadRecordInfo]
    total: int = Field(..., description="记录总数")


class OSSConfigResponse(BaseModel):
    """OSS 配置状态响应"""
    configured: bool = Field(..., description="是否已配置")
    records_count: int = Field(..., description="记录数量")
    temp_dir: str = Field(..., description="临时目录")
    records_file: str = Field(..., description="记录文件路径")
    message: Optional[str] = Field(None, description="提示信息")
