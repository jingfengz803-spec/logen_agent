# 短视频创作自动化API服务

将Python功能封装为RESTful API，供前端调用。

## 目录结构

```
python_services/
├── api/                      # API路由
│   ├── v1/
│   │   ├── douyin.py        # 抖音抓取接口
│   │   ├── ai.py            # AI分析接口
│   │   ├── tts.py           # 语音合成接口
│   │   ├── video.py         # 视频生成接口
│   │   ├── chain.py         # 任务串联接口（基于task_id）
│   │   ├── storage.py       # 文件存储接口
│   │   └── users.py         # 用户管理接口
│   └── deps.py              # 依赖注入
│
├── services/                 # 业务逻辑层
│   ├── douyin_service.py
│   ├── ai_service.py
│   ├── tts_service.py
│   └── video_service.py
│
├── dao/                      # 数据访问层
│   ├── user_dao.py          # 用户数据访问
│   ├── douyin_dao.py        # 抖音数据访问
│   ├── task_dao.py          # 任务数据访问
│   └── voice_dao.py         # 音色数据访问
│
├── models/                   # 数据模型
│   ├── request.py           # 请求模型
│   ├── response.py          # 响应模型
│   └── db.py                # 数据库表模型
│
├── core/                     # 核心模块
│   ├── config.py            # 配置管理
│   ├── security.py          # JWT鉴权
│   ├── task_manager.py      # 异步任务管理（MySQL持久化）
│   └── logger.py            # 日志
│
├── middleware/               # 中间件
│   ├── cors.py              # CORS配置
│   ├── auth.py              # 认证中间件
│   └── error_handler.py     # 异常处理
│
├── main.py                   # FastAPI入口
├── run_server.py            # 启动脚本
├── requirements.txt         # 依赖
└── .env.example             # 配置示例
```

## 快速开始

### 1. 安装依赖

```bash
cd python_services
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填写API密钥等配置
```

### 3. 启动服务

```bash
python main.py
# 或使用启动脚本
python run_server.py --host 0.0.0.0 --port 8088
```

### 4. 访问API文档

服务启动后，访问 http://localhost:8088/docs 查看Swagger API文档

## API接口列表

### 抖音抓取 (`/api/v1/douyin`)

| 接口 | 方法 | 描述 |
|------|------|------|
| `/fetch/user` | POST | 抓取用户视频 |
| `/fetch/topic` | POST | 抓取话题视频 |
| `/fetch/hotlist` | POST | 抓取抖音热榜 |
| `/task/{task_id}` | GET | 查询任务状态 |
| `/videos` | GET | 获取缓存视频 |

### AI分析 (`/api/v1/ai`)

| 接口 | 方法 | 描述 |
|------|------|------|
| `/analyze/viral` | POST | 火爆原因分析 |
| `/analyze/style` | POST | 风格特征分析 |
| `/generate/script` | POST | 生成TTS脚本 |
| `/analyze/full` | POST | 完整分析流程 |

### TTS语音 (`/api/v1/tts`)

| 接口 | 方法 | 描述 |
|------|------|------|
| `/voice/create` | POST | 创建音色复刻 |
| `/voice/list` | GET | 获取音色列表 |
| `/voice/{voice_id}` | GET | 查询音色状态 |
| `/speech` | POST | 文字转语音 |
| `/speech/segments` | POST | 分段语音合成 |
| `/script` | POST | TTS脚本转语音 |

### 任务串联 (`/api/v1/chain`) ⭐ 新增

基于 `task_id` 自动串联各个步骤，避免前端手动传递数据。

| 接口 | 方法 | 描述 |
|------|------|------|
| `/analyze/from-fetch` | POST | 根据抓取任务ID自动进行AI分析 |
| `/generate/from-analysis` | POST | 根据分析任务ID自动生成脚本 |
| `/tts/from-script` | POST | 根据脚本任务ID自动进行TTS |
| `/tts/from-analysis` | POST | 直接从分析任务生成TTS（合并步骤） |
| `/task/{task_id}` | GET | 查询串联任务状态 |

### 视频生成 (`/api/v1/video`)

| 接口 | 方法 | 描述 |
|------|------|------|
| `/generate` | POST | 生成口型同步视频 |
| `/task/{task_id}` | GET | 查询视频生成状态 |

### 文件存储 (`/api/v1/storage`)

| 接口 | 方法 | 描述 |
|------|------|------|
| `/upload/path` | POST | 通过路径上传文件到OSS |
| `/records` | GET | 获取上传记录 |

### 用户管理 (`/api/v1/users`)

| 接口 | 方法 | 描述 |
|------|------|------|
| `/create` | POST | 创建用户并获取API Key |
| `/list` | GET | 获取用户列表 |

## 请求示例

### 抓取用户视频

```bash
curl -X POST "http://localhost:8088/api/v1/douyin/fetch/user" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "url": "https://www.douyin.com/user/MS4wLjABAAAA...",
    "max_count": 100,
    "enable_filter": true,
    "min_likes": 50
  }'
```

### 任务串联流程（推荐）⭐

```bash
# 1. 抓取视频，返回 fetch_task_id
curl -X POST "http://localhost:8088/api/v1/douyin/fetch/user" \
  -H "X-API-Key: your-api-key" \
  -d '{"url": "抖音主页链接"}'

# 2. 根据 fetch_task_id 自动分析
curl -X POST "http://localhost:8088/api/v1/chain/analyze/from-fetch" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "fetch_task_id": "xxx",
    "enable_viral": true,
    "enable_style": true
  }'

# 3. 根据 analysis_task_id 生成脚本
curl -X POST "http://localhost:8088/api/v1/chain/generate/from-analysis" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "analysis_task_id": "xxx",
    "topic": "新主题",
    "target_duration": 60
  }'

# 4. 根据 script_task_id 进行TTS
curl -X POST "http://localhost:8088/api/v1/chain/tts/from-script" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "script_task_id": "xxx",
    "voice_id": "your-voice-id"
  }'

# 或者一步到位：从分析直接生成TTS
curl -X POST "http://localhost:8088/api/v1/chain/tts/from-analysis" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "analysis_task_id": "xxx",
    "topic": "新主题",
    "voice_id": "your-voice-id"
  }'
```

## 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `DEBUG` | 调试模式 | `true` |
| `HOST` | 监听地址 | `0.0.0.0` |
| `PORT` | 监听端口 | `8088` |
| `JWT_SECRET_KEY` | JWT密钥 | - |
| `MAX_CONCURRENT_TASKS` | 最大并发任务数 | `5` |

## 数据库说明

项目使用 MySQL 数据库进行数据持久化：

| 表名 | 说明 |
|------|------|
| `users` | 用户表 |
| `voices` | 音色表 |
| `tasks` | 任务表 |
| `operation_logs` | 操作日志表 |
| `douyin_videos` | 抖音视频表 |
| `douyin_fetch_tasks` | 抖音抓取任务表 |
