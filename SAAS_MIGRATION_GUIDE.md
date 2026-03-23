# 短视频创作SaaS系统 - 架构设计方案

## 一、系统架构概览

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              客户端层                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Web管理端  │  │  移动端H5    │  │   开放API    │  │   小程序     │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
└─────────┼──────────────────┼──────────────────┼──────────────────┼───────┘
          │                  │                  │                  │
          └──────────────────┼──────────────────┼──────────────────┘
                            │
         ┌──────────────────┴──────────────────┐
         │         Spring Cloud Gateway         │
         │            (API网关)                  │
         └──────────────────┬───────────────────┘
                            │
┌───────────────────────────┴───────────────────────────────────────────┐
│                           Nacos 注册中心                              │
└───────────────────────────────────────────────────────────────────────┘
         │
    ┌────┴────┬────────┬────────┬────────┬────────┬────────┬────────┐
    │         │        │        │        │        │        │        │
┌───▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐
│用户服务│ │任务服务│ │素材服务│ │作品服务│ │AI服务 │ │TTS服务│ │视频服务│ │OSS服务│
│User    │ │Task   │ │Material│ │Work   │ │AI     │ │TTS    │ │Video  │ │OSS    │
│Service │ │Service │ │Service │ │Service│ │Service│ │Service│ │Service│ │Service│
└───┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
    │        │        │        │        │        │        │        │        │
┌───┴────────┴────────┴────────┴────────┴────────┴────────┴────────┴───┐
│                          MySQL 数据库集群                             │
├───────────────────────────────────────────────────────────────────────┤
│                          Redis 缓存集群                               │
├───────────────────────────────────────────────────────────────────────┤
│                         RocketMQ 消息队列                             │
└───────────────────────────────────────────────────────────────────────┘
         │
    ┌────┴────┬────────┬────────┐
    │         │        │        │
┌───▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐
│Python │ │Python │ │Python │ │Python │
│抖音抓取│ │AI分析 │ │TTS服务│ │视频生成│
│服务   │ │服务   │ │服务   │ │服务   │
└───────┘ └───────┘ └───────┘ └───────┘
```

### 1.2 服务拆分方案

| 服务名称 | 技术栈 | 端口 | 职责 |
|---------|--------|------|------|
| gateway-service | Spring Cloud Gateway | 8080 | API网关、路由、鉴权 |
| auth-service | Spring Boot | 8081 | 用户认证、JWT签发 |
| user-service | Spring Boot | 8082 | 用户管理、权限管理 |
| project-service | Spring Boot | 8083 | 项目管理、任务管理 |
| material-service | Spring Boot | 8084 | 素材管理（对标账号、音色、视频） |
| work-service | Spring Boot | 8085 | 作品管理、发布记录 |
| payment-service | Spring Boot | 8086 | 订单、支付、套餐管理（可选） |
| douyin-service | Python FastAPI | 8087 | 抖音数据抓取服务 |
| ai-service | Python FastAPI | 8088 | AI分析服务 |
| tts-service | Python FastAPI | 8089 | TTS音色克隆服务 |
| video-service | Python FastAPI | 8090 | 视频生成服务 |
| oss-service | Spring Boot | 8091 | OSS文件管理 |

---

## 二、数据库设计

### 2.1 ER图概览

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   t_user    │──────<│ t_project   │──────<│  t_task     │
│   用户表    │       │   项目表    │       │   任务表    │
└─────────────┘       └─────────────┘       └─────────────┘
       │                     │                     │
       │                     │                     │
       │                ┌────▼────┐          ┌────▼────┐
       │                │t_target │          │ t_work  │
       │                │对标账号表│          │ 作品表  │
       │                └─────────┘          └─────────┘
       │
┌──────▼──────┐    ┌─────────────┐    ┌─────────────┐
│ t_user_role │    │ t_voice     │    │ t_material  │
│  用户角色表 │    │  音色表      │    │  素材表     │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
┌─────────────┐    ┌─────▼─────┐    ┌─────────────┐
│ t_package   │    │ t_analysis │    │ t_publish   │
│  套餐表     │    │  分析结果表 │    │  发布记录表 │
└─────────────┘    └───────────┘    └─────────────┘
```

### 2.2 核心表结构

#### 2.2.1 用户相关表

```sql
-- 用户表
CREATE TABLE t_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '密码(BCrypt)',
    phone VARCHAR(20) UNIQUE COMMENT '手机号',
    email VARCHAR(100) UNIQUE COMMENT '邮箱',
    avatar VARCHAR(500) COMMENT '头像URL',
    nickname VARCHAR(50) COMMENT '昵称',
    status TINYINT DEFAULT 1 COMMENT '状态 0-禁用 1-正常',
    package_id BIGINT COMMENT '当前套餐ID',
    package_expire_time DATETIME COMMENT '套餐过期时间',
    tenant_id BIGINT COMMENT '租户ID(SaaS多租户)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_phone(phone),
    INDEX idx_tenant(tenant_id)
) COMMENT='用户表';

-- 用户角色表
CREATE TABLE t_user_role (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL COMMENT '用户ID',
    role_code VARCHAR(50) COMMENT '角色编码',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_role(user_id, role_code)
) COMMENT='用户角色表';

-- 套餐表
CREATE TABLE t_package (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '套餐名称',
    code VARCHAR(50) UNIQUE COMMENT '套餐编码',
    price DECIMAL(10,2) COMMENT '价格',
    duration_days INT COMMENT '有效天数',
    ai_analysis_limit INT COMMENT 'AI分析次数限制',
    tts_limit INT COMMENT 'TTS生成次数限制',
    video_limit INT COMMENT '视频生成次数限制',
    storage_limit_mb INT COMMENT '存储空间限制(MB)',
    status TINYINT DEFAULT 1 COMMENT '状态',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
) COMMENT='套餐表';
```

#### 2.2.2 项目与任务表

```sql
-- 项目表
CREATE TABLE t_project (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL COMMENT '所属用户',
    name VARCHAR(200) NOT NULL COMMENT '项目名称',
    description TEXT COMMENT '项目描述',
    target_url VARCHAR(500) COMMENT '对标账号URL',
    target_account_id BIGINT COMMENT '对标账号ID',
    status VARCHAR(20) DEFAULT 'DRAFT' COMMENT '状态 DRAFT-草稿 RUNNING-运行中 COMPLETED-完成',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user(user_id),
    INDEX idx_status(status)
) COMMENT='项目表';

-- 任务表
CREATE TABLE t_task (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    project_id BIGINT COMMENT '项目ID',
    user_id BIGINT NOT NULL COMMENT '所属用户',
    task_type VARCHAR(50) NOT NULL COMMENT '任务类型 FETCH-抓取 ANALYZE-分析 TTS-语音 VIDEO-视频',
    task_name VARCHAR(200) COMMENT '任务名称',
    input_params JSON COMMENT '输入参数',
    output_result JSON COMMENT '输出结果',
    status VARCHAR(20) DEFAULT 'PENDING' COMMENT 'PENDING-待处理 RUNNING-处理中 SUCCESS-成功 FAILED-失败',
    progress INT DEFAULT 0 COMMENT '进度0-100',
    error_msg TEXT COMMENT '错误信息',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_project(project_id),
    INDEX idx_user(user_id),
    INDEX idx_status(status),
    INDEX idx_type(task_type)
) COMMENT='任务表';
```

#### 2.2.3 素材表

```sql
-- 对标账号表
CREATE TABLE t_target_account (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL COMMENT '所属用户',
    platform VARCHAR(20) DEFAULT 'douyin' COMMENT '平台',
    account_url VARCHAR(500) COMMENT '账号主页URL',
    sec_user_id VARCHAR(100) COMMENT '账号ID',
    nickname VARCHAR(100) COMMENT '昵称',
    avatar VARCHAR(500) COMMENT '头像',
    follower_count INT COMMENT '粉丝数',
    description TEXT COMMENT '简介',
    fetch_status VARCHAR(20) COMMENT '抓取状态',
    last_fetch_time DATETIME COMMENT '最后抓取时间',
    video_count INT DEFAULT 0 COMMENT '抓取视频数',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user(user_id),
    INDEX idx_platform(platform)
) COMMENT='对标账号表';

-- 抓取的视频数据表
CREATE TABLE t_fetched_video (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    account_id BIGINT COMMENT '账号ID',
    aweme_id VARCHAR(100) UNIQUE COMMENT '视频ID',
    desc TEXT COMMENT '文案',
    hashtags JSON COMMENT '话题标签',
    like_count INT DEFAULT 0 COMMENT '点赞数',
    comment_count INT DEFAULT 0 COMMENT '评论数',
    share_count INT DEFAULT 0 COMMENT '分享数',
    play_count INT DEFAULT 0 COMMENT '播放数',
    duration DECIMAL(10,2) COMMENT '时长(秒)',
    music VARCHAR(200) COMMENT '音乐',
    video_url VARCHAR(500) COMMENT '视频链接',
    cover_url VARCHAR(500) COMMENT '封面',
    create_time_ts BIGINT COMMENT '发布时间戳',
    fetch_time DATETIME COMMENT '抓取时间',
    INDEX idx_account(account_id),
    INDEX idx_aweme(aweme_id)
) COMMENT='抓取视频表';

-- 音色表
CREATE TABLE t_voice (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL COMMENT '所属用户',
    voice_id VARCHAR(200) NOT NULL COMMENT 'CosyVoice Voice ID',
    voice_name VARCHAR(100) COMMENT '音色名称',
    prefix VARCHAR(50) COMMENT '前缀',
    model VARCHAR(50) COMMENT '模型',
    audio_url VARCHAR(500) COMMENT '参考音频URL',
    status VARCHAR(20) DEFAULT 'DEPLOYING' COMMENT 'DEPLOYING-审核中 OK-可用 UNDEPLOYED-失败',
    is_default TINYINT DEFAULT 0 COMMENT '是否默认音色',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user(user_id),
    INDEX idx_voice_id(voice_id)
) COMMENT='音色表';

-- 素材表（视频/音频文件）
CREATE TABLE t_material (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL COMMENT '所属用户',
    material_type VARCHAR(20) NOT NULL COMMENT '类型 VOICE-音色视频 REF-参考视频 AUDIO-生成音频 VIDEO-生成视频',
    material_name VARCHAR(200) COMMENT '素材名称',
    file_url VARCHAR(500) COMMENT '文件URL',
    file_size BIGINT COMMENT '文件大小(字节)',
    duration DECIMAL(10,2) COMMENT '时长(秒)',
    oss_key VARCHAR(500) COMMENT 'OSS对象key',
    status VARCHAR(20) DEFAULT 'ACTIVE' COMMENT '状态',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user(user_id),
    INDEX idx_type(material_type)
) COMMENT='素材表';
```

#### 2.2.4 分析与作品表

```sql
-- 分析结果表
CREATE TABLE t_analysis (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT COMMENT '任务ID',
    account_id BIGINT COMMENT '对标账号ID',
    analysis_type VARCHAR(50) COMMENT '分析类型 VIRAL-火爆原因 STYLE-风格特征',
    result JSON COMMENT '分析结果(JSON)',
    summary TEXT COMMENT '摘要',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task(task_id),
    INDEX idx_account(account_id)
) COMMENT='分析结果表';

-- 生成的脚本表
CREATE TABLE t_script (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT COMMENT '任务ID',
    analysis_id BIGINT COMMENT '分析ID',
    topic VARCHAR(200) COMMENT '主题',
    title VARCHAR(200) COMMENT '视频标题',
    description TEXT COMMENT '视频描述',
    full_script TEXT COMMENT '完整脚本',
    segments JSON COMMENT '分段脚本',
    hashtags JSON COMMENT '话题标签',
    publish_text TEXT COMMENT '发布文案',
    word_count INT COMMENT '字数',
    estimated_duration DECIMAL(10,2) COMMENT '预估时长',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task(task_id)
) COMMENT='生成的脚本表';

-- 作品表
CREATE TABLE t_work (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL COMMENT '所属用户',
    project_id BIGINT COMMENT '项目ID',
    task_id BIGINT COMMENT '任务ID',
    script_id BIGINT COMMENT '脚本ID',
    voice_id BIGINT COMMENT '使用的音色ID',
    ref_video_id BIGINT COMMENT '参考视频ID',
    work_name VARCHAR(200) COMMENT '作品名称',
    video_url VARCHAR(500) COMMENT '成品视频URL',
    audio_url VARCHAR(500) COMMENT '合成音频URL',
    cover_url VARCHAR(500) COMMENT '封面URL',
    duration DECIMAL(10,2) COMMENT '时长',
    status VARCHAR(20) DEFAULT 'DRAFT' COMMENT 'DRAFT-草稿 COMPLETED-完成 PUBLISHED-已发布',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user(user_id),
    INDEX idx_project(project_id)
) COMMENT='作品表';

-- 发布记录表
CREATE TABLE t_publish (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    work_id BIGINT NOT NULL COMMENT '作品ID',
    platform VARCHAR(20) COMMENT '发布平台',
    publish_url VARCHAR(500) COMMENT '发布后URL',
    status VARCHAR(20) DEFAULT 'PENDING' COMMENT 'PENDING-待发布 SUCCESS-成功 FAILED-失败',
    publish_time DATETIME COMMENT '发布时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_work(work_id)
) COMMENT='发布记录表';
```

#### 2.2.5 系统配置表

```sql
-- 系统配置表
CREATE TABLE t_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(100) UNIQUE COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    description VARCHAR(500) COMMENT '描述',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT='系统配置表';

-- 操作日志表
CREATE TABLE t_operation_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT COMMENT '操作用户',
    module VARCHAR(50) COMMENT '模块',
    operation VARCHAR(50) COMMENT '操作',
    method VARCHAR(200) COMMENT '方法',
    params TEXT COMMENT '参数',
    ip VARCHAR(50) COMMENT 'IP',
    status TINYINT COMMENT '状态 0-失败 1-成功',
    error_msg TEXT COMMENT '错误信息',
    execute_time INT COMMENT '执行时长(ms)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user(user_id),
    INDEX idx_create_time(create_time)
) COMMENT='操作日志表';
```

---

## 三、Python服务化改造

### 3.1 改造方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| FastAPI独立服务 | 性能好、异步支持 | 需要维护多服务 | ⭐⭐⭐⭐⭐ |
| Flask简单封装 | 轻量、易上手 | 性能一般 | ⭐⭐⭐ |
| Java直接调用Python脚本 | 简单 | 性能差、难维护 | ⭐⭐ |
| gRPC微服务 | 高性能 | 复杂度高 | ⭐⭐⭐⭐ |

### 3.2 FastAPI服务改造

#### 创建API服务目录结构

```
python_services/
├── douyin_service/          # 抖音抓取服务
│   ├── main.py              # FastAPI入口
│   ├── api/                 # API路由
│   │   └── v1/
│   │       └── douyin.py    # 抖音相关接口
│   ├── services/            # 业务逻辑
│   │   └── fetcher.py       # 调用douyin_data_tool
│   ├── models/              # 数据模型
│   │   └── schemas.py       # Pydantic模型
│   └── config.py            # 配置
│
├── ai_service/              # AI分析服务
│   ├── main.py
│   ├── api/v1/ai.py
│   ├── services/analyzer.py # 调用analyze_and_generate
│   └── models/schemas.py
│
├── tts_service/             # TTS服务
│   ├── main.py
│   ├── api/v1/tts.py
│   ├── services/tts.py      # 调用cosyvoice_tts
│   └── models/schemas.py
│
├── video_service/           # 视频生成服务
│   ├── main.py
│   ├── api/v1/video.py
│   ├── services/generator.py # 调用video_generator
│   └── models/schemas.py
│
├── shared/                  # 共享模块
│   ├── __init__.py
│   ├── config.py            # 共享配置
│   ├── utils.py             # 工具函数
│   └── middleware.py        # 中间件
│
├── requirements.txt         # 依赖
├── docker-compose.yml       # 容器编排
└── start_all.sh             # 启动脚本
```

#### 3.2.1 douyin_service/main.py

```python
"""
抖音抓取服务 - FastAPI
端口: 8087
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import sys
from pathlib import Path

# 添加原模块路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "douyin_data_tool"))

from api.v1 import douyin
from shared.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """生命周期管理"""
    print("抖音抓取服务启动中...")
    yield
    print("抖音抓取服务关闭中...")


app = FastAPI(
    title="抖音抓取服务",
    description="提供抖音账号数据抓取API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(douyin.router, prefix="/api/v1", tags=["douyin"])


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"service": "douyin-service", "status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8087,
        reload=True,
        log_level="info"
    )
```

#### 3.2.2 douyin_service/api/v1/douyin.py

```python
"""
抖音抓取API路由
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

router = APIRouter()


class FetchRequest(BaseModel):
    """抓取请求"""
    user_url: str = Field(..., description="抖音用户主页URL")
    max_videos: int = Field(100, description="最大抓取数量")
    enable_filter: bool = Field(True, description="是否启用过滤")
    task_id: Optional[str] = Field(None, description="任务ID")


class VideoData(BaseModel):
    """视频数据"""
    aweme_id: str
    desc: str
    hashtags: List[str]
    like_count: int
    comment_count: int
    share_count: int
    duration: float
    create_time_str: str


class FetchResponse(BaseModel):
    """抓取响应"""
    task_id: str
    status: str
    total: int = 0
    videos: List[VideoData] = []


@router.post("/fetch", response_model=FetchResponse)
async def fetch_user_videos(request: FetchRequest, background_tasks: BackgroundTasks):
    """
    抓取用户视频

    - 同步模式: 直接返回结果
    - 异步模式: 返回task_id，通过task_id查询结果
    """
    from fetch_user_videos import DouyinUserFetcher

    task_id = request.task_id or str(uuid.uuid4())

    try:
        fetcher = DouyinUserFetcher(
            max_videos=request.max_videos,
            enable_filter=request.enable_filter
        )

        # 执行抓取
        videos = fetcher.fetch_from_url(request.user_url)

        # 转换为响应格式
        video_list = [
            VideoData(
                aweme_id=v.get("aweme_id"),
                desc=v.get("desc"),
                hashtags=v.get("hashtags", []),
                like_count=v.get("like_count", 0),
                comment_count=v.get("comment_count", 0),
                share_count=v.get("share_count", 0),
                duration=v.get("duration", 0),
                create_time_str=v.get("create_time_str", "")
            )
            for v in videos
        ]

        return FetchResponse(
            task_id=task_id,
            status="success",
            total=len(video_list),
            videos=video_list
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态（异步模式）"""
    # 实际应该从Redis/数据库查询
    return {"task_id": task_id, "status": "running", "progress": 50}
```

#### 3.2.3 ai_service/main.py

```python
"""
AI分析服务 - FastAPI
端口: 8088
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uvicorn
import sys
from pathlib import Path

# 添加原模块路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "longgraph"))

from analyze_and_generate import VideoStyleAnalyzer


app = FastAPI(
    title="AI分析服务",
    description="提供视频风格分析和脚本生成API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    """分析请求"""
    videos: List[Dict[str, Any]] = Field(..., description="视频数据列表")
    analysis_type: str = Field("full", description="分析类型: viral, style, full, script")
    top_n: int = Field(30, description="分析热门视频数量")
    topic: Optional[str] = Field(None, description="生成脚本的主题(仅script类型需要)")


@app.post("/api/v1/analyze")
async def analyze(request: AnalyzeRequest):
    """
    分析视频数据

    - viral: 火爆原因分析
    - style: 风格特征分析
    - full: 完整分析(火爆+风格)
    - script: 生成脚本
    """
    try:
        analyzer = VideoStyleAnalyzer(timeout=120.0)

        if request.analysis_type == "viral":
            result = analyzer.analyze_viral_factors(request.videos, top_n=request.top_n)

        elif request.analysis_type == "style":
            result = analyzer.analyze_videos(request.videos, top_n=request.top_n)

        elif request.analysis_type == "full":
            result = analyzer.full_analysis(request.videos, top_n=request.top_n)

        elif request.analysis_type == "script":
            if not request.topic:
                raise HTTPException(status_code=400, detail="script类型需要提供topic参数")
            # 先做完整分析
            full_result = analyzer.full_analysis(request.videos, top_n=request.top_n)
            # 生成脚本
            result = analyzer.generate_script(
                style_analysis=full_result.get("风格特征分析", {}),
                topic=request.topic,
                count=3
            )

        else:
            raise HTTPException(status_code=400, detail="无效的analysis_type")

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/generate-script")
async def generate_script(
    videos: List[Dict[str, Any]],
    topic: str,
    style_analysis: Optional[Dict[str, Any]] = None,
    viral_analysis: Optional[Dict[str, Any]] = None
):
    """生成TTS脚本"""
    try:
        analyzer = VideoStyleAnalyzer(timeout=120.0)

        result = analyzer.generate_tts_script(
            style_analysis=style_analysis or {},
            viral_analysis=viral_analysis or {},
            topic=topic,
            target_duration=20.0
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"service": "ai-service", "status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8088, reload=True)
```

#### 3.2.4 tts_service/main.py

```python
"""
TTS服务 - FastAPI
端口: 8089
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import uvicorn
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "longgraph"))

from cosyvoice_tts import CosyVoiceTTSClient


app = FastAPI(title="TTS服务", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"])


class CreateVoiceRequest(BaseModel):
    """创建音色请求"""
    audio_url: str
    prefix: str = "myvoice"
    model: str = "cosyvoice-v3.5-flash"
    language: str = "zh"
    enable_preprocess: bool = True


class SpeechRequest(BaseModel):
    """语音合成请求"""
    text: str
    voice_id: str
    model: Optional[str] = None


@app.post("/api/v1/voice/create")
async def create_voice(request: CreateVoiceRequest, background_tasks: BackgroundTasks):
    """创建音色复刻"""
    try:
        client = CosyVoiceTTSClient()

        result = client.create_voice(
            audio_url=request.audio_url,
            prefix=request.prefix,
            model=request.model,
            language_hints=[request.language],
            enable_preprocess=request.enable_preprocess,
            wait_ready=False  # 异步，通过接口查询状态
        )

        return {
            "success": True,
            "data": {
                "voice_id": result["voice_id"],
                "status": result["status"]
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/voice/{voice_id}")
async def get_voice_status(voice_id: str):
    """查询音色状态"""
    try:
        client = CosyVoiceTTSClient()
        result = client.query_voice(voice_id)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/voice/list")
async def list_voices(prefix: Optional[str] = None):
    """列出所有音色"""
    try:
        client = CosyVoiceTTSClient()
        result = client.list_voices(prefix=prefix, page_size=100)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/speech")
async def speech(request: SpeechRequest):
    """语音合成"""
    try:
        client = CosyVoiceTTSClient()

        # 生成临时文件路径
        output_path = f"/tmp/speech_{request.voice_id[:8]}_{uuid.uuid4().hex[:8]}.mp3"

        audio_data = client.speech(
            text=request.text,
            voice=request.voice_id,
            model=request.model,
            output_path=output_path
        )

        # 上传到OSS并返回URL
        from upload_audio_helper import OSSUploader
        uploader = OSSUploader()
        url = uploader.upload_file(output_path)

        return {
            "success": True,
            "data": {
                "audio_url": url,
                "duration": len(audio_data) / 44100  # 粗略估算
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"service": "tts-service", "status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8089, reload=True)
```

#### 3.2.5 video_service/main.py

```python
"""
视频生成服务 - FastAPI
端口: 8090
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "longgraph"))

from video_generator import VideoRetalkClient, VideoWorkflow


app = FastAPI(title="视频生成服务", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"])


class GenerateVideoRequest(BaseModel):
    """视频生成请求"""
    video_url: str = Field(..., description="参考视频URL")
    audio_url: str = Field(..., description="音频URL")
    ref_image_url: Optional[str] = Field(None, description="参考图片URL")
    video_extension: bool = Field(False, description="是否扩展视频")
    wait: bool = Field(True, description="是否等待完成")


@app.post("/api/v1/video/generate")
async def generate_video(request: GenerateVideoRequest, background_tasks: BackgroundTasks):
    """生成视频"""
    try:
        client = VideoRetalkClient()

        if request.wait:
            # 同步等待
            result = client.generate_video(
                video_url=request.video_url,
                audio_url=request.audio_url,
                ref_image_url=request.ref_image_url or "",
                video_extension=request.video_extension,
                wait=True
            )

            return {
                "success": True,
                "data": result
            }
        else:
            # 异步提交
            task_id = client.submit_video_generation_task(
                video_url=request.video_url,
                audio_url=request.audio_url,
                ref_image_url=request.ref_image_url or "",
                video_extension=request.video_extension
            )

            return {
                "success": True,
                "data": {
                    "task_id": task_id,
                    "status": "pending"
                }
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/video/task/{task_id}")
async def get_task_status(task_id: str):
    """查询视频生成任务状态"""
    try:
        client = VideoRetalkClient()
        result = client.query_task_status(task_id)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/video/workflow")
async def workflow_generate(
    video_path: str,
    audio_path: str,
    output_dir: str = "/tmp/output"
):
    """完整工作流（自动上传OSS）"""
    try:
        workflow = VideoWorkflow()
        result = workflow.generate_from_local_files(
            video_path=video_path,
            audio_path=audio_path,
            output_dir=output_dir,
            auto_upload=True,
            video_extension=True
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"service": "video-service", "status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8090, reload=True)
```

#### 3.2.6 docker-compose.yml

```yaml
version: '3.8'

services:
  douyin-service:
    build:
      context: .
      dockerfile: docker/Dockerfile.douyin
    container_name: douyin-service
    ports:
      - "8087:8087"
    environment:
      - DOUYYIN_COOKIE=${DOUYYIN_COOKIE}
      - PYTHONUNBUFFERED=1
    volumes:
      - ./longgraph:/app/longgraph
      - ./douyin_data_tool:/app/douyin_data_tool
    networks:
      - saas-network
    restart: unless-stopped

  ai-service:
    build:
      context: .
      dockerfile: docker/Dockerfile.ai
    container_name: ai-service
    ports:
      - "8088:8088"
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - ZAI_API_KEY=${ZAI_API_KEY}
      - PYTHONUNBUFFERED=1
    volumes:
      - ./longgraph:/app/longgraph
    networks:
      - saas-network
    restart: unless-stopped

  tts-service:
    build:
      context: .
      dockerfile: docker/Dockerfile.tts
    container_name: tts-service
    ports:
      - "8089:8089"
    environment:
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - OSS_ACCESS_KEY_ID=${OSS_ACCESS_KEY_ID}
      - OSS_ACCESS_KEY_SECRET=${OSS_ACCESS_KEY_SECRET}
      - OSS_BUCKET_NAME=${OSS_BUCKET_NAME}
      - OSS_ENDPOINT=${OSS_ENDPOINT}
      - PYTHONUNBUFFERED=1
    volumes:
      - ./longgraph:/app/longgraph
      - ./data:/app/data
    networks:
      - saas-network
    restart: unless-stopped

  video-service:
    build:
      context: .
      dockerfile: docker/Dockerfile.video
    container_name: video-service
    ports:
      - "8090:8090"
    environment:
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - OSS_ACCESS_KEY_ID=${OSS_ACCESS_KEY_ID}
      - OSS_ACCESS_KEY_SECRET=${OSS_ACCESS_KEY_SECRET}
      - OSS_BUCKET_NAME=${OSS_BUCKET_NAME}
      - OSS_ENDPOINT=${OSS_ENDPOINT}
      - PYTHONUNBUFFERED=1
    volumes:
      - ./longgraph:/app/longgraph
      - ./data/output:/app/data/output
    networks:
      - saas-network
    restart: unless-stopped

networks:
  saas-network:
    driver: bridge
```

---

## 四、Java后端服务设计

### 4.1 项目结构

```
saas-backend/
├── gateway-service/         # 网关服务
├── auth-service/            # 认证服务
├── user-service/            # 用户服务
├── project-service/         # 项目服务
├── material-service/        # 素材服务
├── work-service/            # 作品服务
├── payment-service/         # 支付服务(可选)
├── oss-service/             # OSS服务
├── common/                  # 公共模块
│   ├── common-core/         # 核心工具类
│   ├── common-web/          # Web相关
│   ├── common-security/     # 安全相关
│   ├── common-redis/        # Redis相关
│   ├── common-mysql/        # MySQL相关
│   └── common-feign/        # Feign相关
└── pom.xml                  # 父POM
```

### 4.2 核心依赖 (pom.xml)

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>2.6.13</version>
</parent>

<properties>
    <java.version>17</java.version>
    <spring-cloud.version>2021.0.5</spring-cloud.version>
    <spring-cloud-alibaba.version>2021.0.5.0</spring-cloud-alibaba.version>
    <mybatis-plus.version>3.5.3</mybatis-plus.version>
    <hutool.version>5.8.16</hutool.version>
</properties>

<dependencies>
    <!-- Spring Cloud -->
    <dependency>
        <groupId>com.alibaba.cloud</groupId>
        <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
    </dependency>
    <dependency>
        <groupId>com.alibaba.cloud</groupId>
        <artifactId>spring-cloud-starter-alibaba-nacos-config</artifactId>
    </dependency>

    <!-- MySQL -->
    <dependency>
        <groupId>com.baomidou</groupId>
        <artifactId>mybatis-plus-boot-starter</artifactId>
    </dependency>
    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
    </dependency>

    <!-- Redis -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-redis</artifactId>
    </dependency>

    <!-- RocketMQ -->
    <dependency>
        <groupId>org.apache.rocketmq</groupId>
        <artifactId>rocketmq-spring-boot-starter</artifactId>
    </dependency>

    <!-- 工具类 -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>

    <!-- HTTP客户端 -->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-openfeign</artifactId>
    </dependency>
</dependencies>
```

### 4.3 Feign客户端 (调用Python服务)

```java
// common/common-feign/src/main/java/com/saas/feign/DouyinServiceClient.java
package com.saas.feign;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@FeignClient(
    name = "douyin-service",
    url = "${python.services.douyin:http://localhost:8087}",
    path = "/api/v1"
)
public interface DouyinServiceClient {

    @PostMapping("/fetch")
    Map<String, Object> fetchUserVideos(@RequestBody Map<String, Object> request);

    @GetMapping("/task/{taskId}")
    Map<String, Object> getTaskStatus(@PathVariable("taskId") String taskId);
}

// common/common-feign/src/main/java/com/saas/feign/AIServiceClient.java
@FeignClient(
    name = "ai-service",
    url = "${python.services.ai:http://localhost:8088}",
    path = "/api/v1"
)
public interface AIServiceClient {

    @PostMapping("/analyze")
    Map<String, Object> analyze(@RequestBody Map<String, Object> request);

    @PostMapping("/generate-script")
    Map<String, Object> generateScript(@RequestBody Map<String, Object> request);
}

// common/common-feign/src/main/java/com/saas/feign/TTSServiceClient.java
@FeignClient(
    name = "tts-service",
    url = "${python.services.tts:http://localhost:8089}",
    path = "/api/v1"
)
public interface TTSServiceClient {

    @PostMapping("/voice/create")
    Map<String, Object> createVoice(@RequestBody Map<String, Object> request);

    @GetMapping("/voice/{voiceId}")
    Map<String, Object> getVoiceStatus(@PathVariable("voiceId") String voiceId);

    @PostMapping("/speech")
    Map<String, Object> speech(@RequestBody Map<String, Object> request);
}

// common/common-feign/src/main/java/com/saas/feign/VideoServiceClient.java
@FeignClient(
    name = "video-service",
    url = "${python.services.video:http://localhost:8090}",
    path = "/api/v1"
)
public interface VideoServiceClient {

    @PostMapping("/video/generate")
    Map<String, Object> generateVideo(@RequestBody Map<String, Object> request);

    @GetMapping("/video/task/{taskId}")
    Map<String, Object> getTaskStatus(@PathVariable("taskId") String taskId);
}
```

### 4.4 核心业务代码示例

```java
// project-service/src/main/java/com/saas/project/service/ProjectWorkflowService.java
package com.saas.project.service;

import com.saas.feign.*;
import com.saas.project.entity.*;
import com.saas.project.mapper.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class ProjectWorkflowService {

    private final DouyinServiceClient douyinClient;
    private final AIServiceClient aiClient;
    private final TTSServiceClient ttsClient;
    private final VideoServiceClient videoClient;

    private final ProjectMapper projectMapper;
    private final TaskMapper taskMapper;
    private final AnalysisMapper analysisMapper;
    private final ScriptMapper scriptMapper;
    private final WorkMapper workMapper;

    /**
     * 完整工作流
     * 1. 抓取视频
     * 2. AI分析
     * 3. 生成脚本
     * 4. TTS合成
     * 5. 视频生成
     */
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> executeFullWorkflow(Long projectId, String topic, Long voiceId, Long refVideoId) {

        // 1. 获取项目信息
        Project project = projectMapper.selectById(projectId);
        if (project == null) {
            throw new RuntimeException("项目不存在");
        }

        // 2. 创建主任务
        Task mainTask = Task.builder()
                .projectId(projectId)
                .userId(project.getUserId())
                .taskType("FULL_WORKFLOW")
                .taskName("完整视频生成工作流")
                .status("RUNNING")
                .build();
        taskMapper.insert(mainTask);

        Map<String, Object> result = new HashMap<>();
        result.put("taskId", mainTask.getId());

        try {
            // 步骤1: 抓取抖音数据
            updateTaskProgress(mainTask.getId(), 10, "正在抓取抖音数据...");
            Map<String, Object> fetchRequest = Map.of(
                    "userUrl", project.getTargetUrl(),
                    "maxVideos", 100,
                    "enableFilter", true
            );
            Map<String, Object> fetchResult = douyinClient.fetchUserVideos(fetchRequest);

            if (!"success".equals(fetchResult.get("status"))) {
                throw new RuntimeException("抖音数据抓取失败");
            }

            // 步骤2: AI分析
            updateTaskProgress(mainTask.getId(), 30, "正在进行AI分析...");
            Map<String, Object> analyzeRequest = Map.of(
                    "videos", fetchResult.get("videos"),
                    "analysisType", "full",
                    "topN", 30
            );
            Map<String, Object> analyzeResult = aiClient.analyze(analyzeRequest);

            // 保存分析结果
            Analysis analysis = Analysis.builder()
                    .taskId(mainTask.getId())
                    .analysisType("FULL")
                    .result(JSON.toJSONString(analyzeResult))
                    .build();
            analysisMapper.insert(analysis);

            // 步骤3: 生成脚本
            updateTaskProgress(mainTask.getId(), 50, "正在生成脚本...");
            Map<String, Object> scriptRequest = new HashMap<>();
            scriptRequest.put("videos", fetchResult.get("videos"));
            scriptRequest.put("topic", topic);
            scriptRequest.put("styleAnalysis", analyzeResult.get("风格特征分析"));
            scriptRequest.put("viralAnalysis", analyzeResult.get("火爆原因分析"));

            Map<String, Object> scriptResult = aiClient.generateScript(scriptRequest);

            // 保存脚本
            Script script = Script.builder()
                    .taskId(mainTask.getId())
                    .analysisId(analysis.getId())
                    .topic(topic)
                    .title((String) scriptResult.get("视频标题"))
                    .description((String) scriptResult.get("视频描述"))
                    .fullScript((String) scriptResult.get("完整脚本"))
                    .segments(JSON.toJSONString(scriptResult.get("分段")))
                    .hashtags(JSON.toJSONString(scriptResult.get("话题标签")))
                    .publishText((String) scriptResult.get("发布文案"))
                    .build();
            scriptMapper.insert(script);

            // 步骤4: TTS语音合成
            updateTaskProgress(mainTask.getId(), 70, "正在合成语音...");
            Voice voice = null;
            if (voiceId != null) {
                // 查询音色
                voice = voiceMapper.selectById(voiceId);
            }

            Map<String, Object> ttsRequest = Map.of(
                    "text", scriptResult.get("完整脚本"),
                    "voiceId", voice != null ? voice.getVoiceId() : "default"
            );
            Map<String, Object> ttsResult = ttsClient.speech(ttsRequest);

            // 步骤5: 视频生成
            updateTaskProgress(mainTask.getId(), 85, "正在生成视频...");
            Map<String, Object> videoRequest = Map.of(
                    "videoUrl", getMaterialUrl(refVideoId),
                    "audioUrl", ttsResult.get("audioUrl"),
                    "videoExtension", true,
                    "wait", true
            );
            Map<String, Object> videoResult = videoClient.generateVideo(videoRequest);

            // 保存作品
            Work work = Work.builder()
                    .userId(project.getUserId())
                    .projectId(projectId)
                    .taskId(mainTask.getId())
                    .scriptId(script.getId())
                    .voiceId(voiceId)
                    .refVideoId(refVideoId)
                    .workName(project.getName() + "-" + topic)
                    .videoUrl((String) videoResult.get("videoUrl"))
                    .audioUrl((String) ttsResult.get("audioUrl"))
                    .status("COMPLETED")
                    .build();
            workMapper.insert(work);

            // 更新任务状态
            updateTaskProgress(mainTask.getId(), 100, "完成");
            mainTask.setStatus("SUCCESS");
            mainTask.setOutputResult(JSON.toJSONString(videoResult));
            mainTask.setEndTime(LocalDateTime.now());
            taskMapper.updateById(mainTask);

            result.put("workId", work.getId());
            result.put("videoUrl", work.getVideoUrl());
            result.put("success", true);

        } catch (Exception e) {
            log.error("工作流执行失败", e);
            mainTask.setStatus("FAILED");
            mainTask.setErrorMsg(e.getMessage());
            mainTask.setEndTime(LocalDateTime.now());
            taskMapper.updateById(mainTask);
            result.put("success", false);
            result.put("error", e.getMessage());
        }

        return result;
    }

    private void updateTaskProgress(Long taskId, int progress, String message) {
        Task task = taskMapper.selectById(taskId);
        task.setProgress(progress);
        task.setOutputResult(JSON.toJSONString(Map.of("message", message)));
        taskMapper.updateById(task);
    }
}
```

---

## 五、API接口规范

### 5.1 统一响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "timestamp": 1234567890
}
```

### 5.2 核心API列表

| 模块 | 接口 | 方法 | 说明 |
|------|------|------|------|
| 用户 | /api/v1/user/register | POST | 用户注册 |
| 用户 | /api/v1/user/login | POST | 用户登录 |
| 用户 | /api/v1/user/info | GET | 获取用户信息 |
| 项目 | /api/v1/project/create | POST | 创建项目 |
| 项目 | /api/v1/project/list | GET | 项目列表 |
| 项目 | /api/v1/project/{id} | GET | 项目详情 |
| 项目 | /api/v1/project/workflow/start | POST | 启动工作流 |
| 任务 | /api/v1/task/list | GET | 任务列表 |
| 任务 | /api/v1/task/{id} | GET | 任务详情 |
| 任务 | /api/v1/task/{id}/cancel | POST | 取消任务 |
| 音色 | /api/v1/voice/create | POST | 创建音色 |
| 音色 | /api/v1/voice/list | GET | 音色列表 |
| 音色 | /api/v1/voice/{id} | GET | 音色详情 |
| 作品 | /api/v1/work/list | GET | 作品列表 |
| 作品 | /api/v1/work/{id} | GET | 作品详情 |
| 作品 | /api/v1/work/{id}/publish | POST | 发布作品 |

---

## 六、迁移步骤

### 6.1 第一阶段：服务化改造（1-2周）

1. 创建FastAPI服务框架
2. 改造douyin_data_tool为douyin_service
3. 改造analyze_and_generate为ai_service
4. 改造cosyvoice_tts为tts_service
5. 改造video_generator为video_service
6. 编写API文档

### 6.2 第二阶段：Java后端开发（2-3周）

1. 搭建Spring Cloud + Nacos基础架构
2. 开发用户服务、认证服务
3. 开发项目服务、任务服务
4. 开发素材服务、作品服务
5. 集成Python服务(Feign调用)
6. 开发OSS服务

### 6.3 第三阶段：前端开发（2-3周）

1. 搭建Vue/React管理后台
2. 用户管理界面
3. 项目管理界面
4. 工作流执行界面
5. 作品展示界面

### 6.4 第四阶段：测试上线（1周）

1. 功能测试
2. 性能测试
3. 部署上线
4. 监控告警配置

---

## 七、部署架构

### 7.1 生产环境部署

```
┌─────────────────────────────────────────────────────────────┐
│                        负载均衡 (SLB)                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼─────────┐  ┌──────▼─────────┐
│ Gateway Node 1 │  │ Gateway Node 2 │  │ Gateway Node 3 │
└───────┬────────┘  └──────┬─────────┘  └──────┬─────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
    ┌───────────────────────┼───────────────────────────────┐
    │                       │                               │
┌───▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐
│ Java微服务集群│   │ Python服务集群   │   │ MySQL主从集群   │
│ (用户/项目等) │   │ (AI/TTS/视频)   │   │ Redis集群      │
└─────────────┘    └─────────────────┘    └─────────────────┘
```

### 7.2 Docker部署脚本

```bash
#!/bin/bash
# deploy.sh

echo "部署短视频创作SaaS系统..."

# 启动Python服务
docker-compose -f docker-compose.yml up -d

# 启动Java服务
cd java-services
./gradlew bootJar

# 启动各微服务
java -jar gateway-service/target/gateway-service.jar &
java -jar user-service/target/user-service.jar &
java -jar project-service/target/project-service.jar &

echo "部署完成!"
```

---

## 八、总结

本方案将现有Python工程改造成SaaS系统，主要工作包括：

1. **Python服务化**：将脚本改造为FastAPI RESTful服务
2. **Java微服务**：Spring Cloud + Nacos搭建业务系统
3. **数据库设计**：MySQL存储业务数据
4. **服务通信**：Feign调用Python服务
5. **容器化部署**：Docker Compose编排

**预计工作量：6-8周**
**推荐团队配置：**
- 后端Java开发 x2
- Python服务改造 x1
- 前端开发 x1
- 测试工程师 x1
