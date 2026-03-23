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
│   │   └── workflow.py      # 完整工作流接口
│   └── deps.py              # 依赖注入
│
├── services/                 # 业务逻辑层
│   ├── douyin_service.py
│   ├── ai_service.py
│   ├── tts_service.py
│   ├── video_service.py
│   └── workflow_service.py
│
├── models/                   # 数据模型
│   ├── request.py           # 请求模型
│   └── response.py          # 响应模型
│
├── core/                     # 核心模块
│   ├── config.py            # 配置管理
│   ├── security.py          # JWT鉴权
│   ├── task_manager.py      # 异步任务管理
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

### 视频生成 (`/api/v1/video`)

| 接口 | 方法 | 描述 |
|------|------|------|
| `/generate` | POST | 生成口型同步视频 |
| `/task/{task_id}` | GET | 查询视频生成状态 |

### 完整工作流 (`/api/v1/workflow`)

| 接口 | 方法 | 描述 |
|------|------|------|
| `/run` | POST | 运行完整工作流 |
| `/task/{task_id}` | GET | 查询工作流状态 |
| `/templates` | GET | 获取工作流模板 |

## 请求示例

### 抓取用户视频

```bash
curl -X POST "http://localhost:8088/api/v1/douyin/fetch/user" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.douyin.com/user/MS4wLjABAAAA...",
    "max_count": 100,
    "enable_filter": true,
    "min_likes": 50
  }'
```

### 运行完整工作流

```bash
curl -X POST "http://localhost:8088/api/v1/workflow/run" \
  -H "Content-Type: application/json" \
  -d '{
    "douyin_url": "https://www.douyin.com/user/MS4wLjABAAAA...",
    "topic": "如何应对职场PUA",
    "voice_id": "cosyvoice-v3.5-flash-xxx",
    "workflow_type": "without_video"
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
