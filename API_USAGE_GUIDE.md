# API 调用指南

本文档介绍如何调用 `python_services` 中封装好的 API 服务。

## 目录

- [环境准备](#环境准备)
- [启动服务](#启动服务)
- [API 接口说明](#api-接口说明)
  - [1. 抖音数据抓取 API](#1-抖音数据抓取-api)
  - [2. AI 分析 API](#2-ai-分析-api)
  - [3. TTS 语音合成 API](#3-tts-语音合成-api)
  - [4. 视频生成 API](#4-视频生成-api)
  - [5. 完整工作流 API](#5-完整工作流-api)
- [完整调用示例](#完整调用示例)

---

## 环境准备

### 1. 安装依赖

```bash
cd python_services
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件或设置环境变量：

```bash
# API服务配置
API_HOST=0.0.0.0
API_PORT=8000
API_PREFIX=/api/v1

# 阿里云配置（用于TTS等功能）
ALIYUN_ACCESS_KEY_ID=your_access_key
ALIYUN_ACCESS_KEY_SECRET=your_secret
```

---

## 启动服务

### 方式一：直接启动

```bash
cd python_services
python main.py
```

### 方式二：使用 uvicorn

```bash
cd python_services
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后，访问 `http://localhost:8000/docs` 查看自动生成的 API 文档。

---

## API 接口说明

### 基础信息

- **基础 URL**: `http://localhost:8000`
- **API 前缀**: `/api/v1`
- **所有请求返回格式**:

```json
{
  "success": true,
  "data": {...},
  "message": "操作成功",
  "request_id": "uuid"
}
```

---

### 1. 抖音数据抓取 API

#### 1.1 抓取用户视频

**接口**: `POST /api/v1/douyin/fetch/user`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | string | 是 | 抖音用户主页URL |
| max_count | int | 否 | 最大抓取数量 (1-200，默认100) |
| enable_filter | bool | 否 | 是否启用过滤 (默认false) |
| min_likes | int | 否 | 最小点赞数 (默认50) |
| min_comments | int | 否 | 最小评论数 (默认0) |

**cURL 示例**:

```bash
curl -X POST "http://localhost:8000/api/v1/douyin/fetch/user" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.douyin.com/user/MS4wLjABAAAA...",
    "max_count": 50,
    "enable_filter": true,
    "min_likes": 100
  }'
```

**Python 示例**:

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/douyin/fetch/user",
    json={
        "url": "https://www.douyin.com/user/MS4wLjABAAAA...",
        "max_count": 50,
        "enable_filter": True,
        "min_likes": 100
    }
)
result = response.json()
task_id = result["data"]["task_id"]
print(f"任务ID: {task_id}")
```

#### 1.2 抓取话题视频

**接口**: `POST /api/v1/douyin/fetch/topic`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| topic | string | 是 | 话题名称 |
| max_count | int | 否 | 最大抓取数量 (默认50) |

**Python 示例**:

```python
response = requests.post(
    "http://localhost:8000/api/v1/douyin/fetch/topic",
    json={
        "topic": "AI科技",
        "max_count": 30
    }
)
```

#### 1.3 查询任务状态

**接口**: `GET /api/v1/douyin/task/{task_id}`

**Python 示例**:

```python
task_id = "abc-123-def"
response = requests.get(f"http://localhost:8000/api/v1/douyin/task/{task_id}")
status = response.json()["data"]["status"]  # pending/running/success/failed
```

#### 1.4 获取视频列表

**接口**: `GET /api/v1/douyin/videos`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | int | 否 | 返回数量 (默认100) |
| offset | int | 否 | 偏移量 (默认0) |

---

### 2. AI 分析 API

#### 2.1 完整分析（火爆原因 + 风格 + 脚本）

**接口**: `POST /api/v1/ai/analyze/full`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| douyin_url | string | 是 | 抖音用户主页URL |
| topic | string | 是 | 新主题 |
| max_videos | int | 否 | 分析视频数量 (默认100) |
| enable_viral_analysis | bool | 否 | 是否火爆分析 (默认true) |
| enable_style_analysis | bool | 否 | 是否风格分析 (默认true) |
| generate_script | bool | 否 | 是否生成脚本 (默认true) |

**Python 示例**:

```python
response = requests.post(
    "http://localhost:8000/api/v1/ai/analyze/full",
    json={
        "douyin_url": "https://www.douyin.com/user/MS4wLjABAAAA...",
        "topic": "人工智能的未来",
        "max_videos": 50,
        "enable_viral_analysis": True,
        "enable_style_analysis": True,
        "generate_script": True
    }
)
task_id = response.json()["data"]["task_id"]
```

#### 2.2 火爆原因分析

**接口**: `POST /api/v1/ai/analyze/viral`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| video_data | list | 是 | 视频数据列表 |
| video_ids | list | 否 | 指定分析的视频ID列表 |

**Python 示例**:

```python
response = requests.post(
    "http://localhost:8000/api/v1/ai/analyze/viral",
    json={
        "video_data": [
            {
                "title": "视频标题",
                "desc": "视频描述",
                "statistics": {
                    "digg_count": 10000,
                    "comment_count": 500
                }
            }
        ],
        "video_ids": ["vid1", "vid2"]
    }
)
```

#### 2.3 风格特征分析

**接口**: `POST /api/v1/ai/analyze/style`

**分析维度**: 话题热度、情绪共鸣、实用性、娱乐性、人设魅力、表达技巧

**Python 示例**:

```python
response = requests.post(
    "http://localhost:8000/api/v1/ai/analyze/style",
    json={
        "video_data": [...],  # 视频数据列表
        "analysis_dimensions": [
            "文案风格", "视频类型", "拍摄特征",
            "高频词汇", "标签策略", "音乐风格"
        ]
    }
)
```

#### 2.4 脚本生成

**接口**: `POST /api/v1/ai/generate/script`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| reference_data | object | 是 | 参考数据（风格分析结果） |
| topic | string | 是 | 新主题 |
| target_duration | int | 否 | 目标时长秒数 (默认30) |
| tone | string | 否 | 语气：专业/幽默/亲切 (默认专业) |
| include_hashtags | bool | 否 | 是否生成话题标签 (默认true) |

**Python 示例**:

```python
response = requests.post(
    "http://localhost:8000/api/v1/ai/generate/script",
    json={
        "reference_data": {
            "style_profile": {...},
            "viral_factors": [...]
        },
        "topic": "量子计算入门",
        "target_duration": 60,
        "tone": "幽默",
        "include_hashtags": True
    }
)
```

---

### 3. TTS 语音合成 API

#### 3.1 创建音色（音色复刻）

**接口**: `POST /api/v1/tts/voice/create`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| audio_url | string | 是 | 音色音频公网URL |
| prefix | string | 否 | 音色前缀 (默认"myvoice") |
| model | string | 否 | TTS模型 (默认cosyvoice-v3.5-flash) |
| language_hints | list | 否 | 语言提示 |
| wait_ready | bool | 否 | 是否等待就绪 (默认true) |

**Python 示例**:

```python
response = requests.post(
    "http://localhost:8000/api/v1/tts/voice/create",
    json={
        "audio_url": "https://example.com/reference_voice.mp3",
        "prefix": "tech_voice",
        "model": "cosyvoice-v3.5-flash",
        "wait_ready": True
    }
)
voice_id = response.json()["data"]["voice_id"]
print(f"音色ID: {voice_id}")
```

#### 3.2 获取音色列表

**接口**: `GET /api/v1/tts/voice/list`

**Python 示例**:

```python
response = requests.get("http://localhost:8000/api/v1/tts/voice/list")
voices = response.json()["data"]["voices"]
```

#### 3.3 查询音色状态

**接口**: `GET /api/v1/tts/voice/{voice_id}`

#### 3.4 单段文本合成

**接口**: `POST /api/v1/tts/speech`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | 是 | 要合成的文本 |
| voice_id | string | 是 | 音色ID |
| model | string | 否 | TTS模型 |
| output_format | string | 否 | 输出格式 (如mp3) |

**Python 示例**:

```python
response = requests.post(
    "http://localhost:8000/api/v1/tts/speech",
    json={
        "text": "大家好，今天我们来聊聊人工智能的发展趋势。",
        "voice_id": "your-voice-id",
        "model": "cosyvoice-v3.5-flash",
        "output_format": "mp3"
    }
)
task_id = response.json()["data"]["task_id"]
```

#### 3.5 分段文本合成

**接口**: `POST /api/v1/tts/speech/segments`

**Python 示例**:

```python
response = requests.post(
    "http://localhost:8000/api/v1/tts/speech/segments",
    json={
        "segments": [
            {"text": "第一段内容"},
            {"text": "第二段内容"},
            {"text": "第三段内容"}
        ],
        "voice_id": "your-voice-id",
        "model": "cosyvoice-v3.5-flash"
    }
)
```

#### 3.6 脚本合成（完整版 + 分段版）

**接口**: `POST /api/v1/tts/script`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| full_text | string | 是 | 完整台词 |
| segments | list | 是 | 分段台词 |
| voice_id | string | 是 | 音色ID |
| model | string | 是 | TTS模型 |

**Python 示例**:

```python
response = requests.post(
    "http://localhost:8000/api/v1/tts/script",
    json={
        "full_text": "大家好，今天我们来聊聊人工智能。人工智能是...",
        "segments": [
            {"text": "大家好，今天我们来聊聊人工智能。"},
            {"text": "人工智能正在改变我们的生活。"},
            {"text": "让我们一起探索这个领域。"}
        ],
        "voice_id": "your-voice-id",
        "model": "cosyvoice-v3.5-flash"
    }
)
```

---

### 4. 视频生成 API

基于 VideoRetalk 生成口型同步视频。

#### 4.1 生成视频

**接口**: `POST /api/v1/video/generate`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| video_url | string | 是 | 参考视频公网URL |
| audio_url | string | 是 | 合成音频公网URL |
| ref_image_url | string | 否 | 参考图片URL |
| video_extension | bool | 否 | 是否扩展视频匹配音频长度 |
| resolution | string | 否 | 分辨率 (如1280x720) |

**Python 示例**:

```python
response = requests.post(
    "http://localhost:8000/api/v1/video/generate",
    json={
        "video_url": "https://example.com/reference.mp4",
        "audio_url": "https://example.com/generated_audio.mp3",
        "resolution": "1280x720"
    }
)
task_id = response.json()["data"]["task_id"]
```

#### 4.2 查询视频生成状态

**接口**: `GET /api/v1/video/task/{task_id}`

**Python 示例**:

```python
import time

task_id = "your-task-id"
while True:
    response = requests.get(f"http://localhost:8000/api/v1/video/task/{task_id}")
    result = response.json()["data"]
    status = result["status"]

    if status == "success":
        video_url = result["video_url"]
        print(f"视频生成成功: {video_url}")
        break
    elif status == "failed":
        print(f"生成失败: {result['error']}")
        break
    else:
        print(f"处理中... 进度: {result.get('progress', 0)}%")
        time.sleep(5)
```

#### 4.3 取消视频生成

**接口**: `DELETE /api/v1/video/task/{task_id}`

---

### 5. 完整工作流 API

一站式服务，从抖音抓取到视频生成的完整流程。

#### 5.1 执行工作流

**接口**: `POST /api/v1/workflow/run`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| douyin_url | string | 是 | 抖音用户主页URL |
| topic | string | 是 | 新主题 |
| workflow_type | string | 是 | 流程类型：full/without_video/analysis_only |
| voice_id | string | 否 | 音色ID |
| ref_video_url | string | 否 | 参考视频URL |
| max_videos | int | 否 | 分析视频数量 (默认100) |
| output_name | string | 否 | 输出文件名前缀 |

**workflow_type 说明**:

| 类型 | 说明 |
|------|------|
| `full` | 完整流程（抓取 + 分析 + 脚本 + TTS + 视频） |
| `without_video` | 不含视频（抓取 + 分析 + 脚本 + TTS） |
| `analysis_only` | 仅分析（抓取 + 分析 + 脚本） |

**Python 示例**:

```python
response = requests.post(
    "http://localhost:8000/api/v1/workflow/run",
    json={
        "douyin_url": "https://www.douyin.com/user/MS4wLjABAAAA...",
        "topic": "AI技术最新进展",
        "workflow_type": "full",
        "voice_id": "your-voice-id",
        "ref_video_url": "https://example.com/reference.mp4",
        "max_videos": 50,
        "output_name": "ai_tech_video"
    }
)
task_id = response.json()["data"]["task_id"]
```

#### 5.2 查询工作流状态

**接口**: `GET /api/v1/workflow/task/{task_id}`

**响应示例**:

```json
{
  "success": true,
  "data": {
    "task_id": "wf-abc-123",
    "status": "running",
    "current_step": "tts_synthesis",
    "steps": [
      {"name": "fetch_videos", "status": "completed"},
      {"name": "ai_analysis", "status": "completed"},
      {"name": "script_generation", "status": "completed"},
      {"name": "tts_synthesis", "status": "running"},
      {"name": "video_generation", "status": "pending"}
    ],
    "progress": 60,
    "result": {
      "script": "生成的脚本内容...",
      "audio_urls": ["..."]
    }
  }
}
```

#### 5.3 获取工作流模板

**接口**: `GET /api/v1/workflow/templates`

**Python 示例**:

```python
response = requests.get("http://localhost:8000/api/v1/workflow/templates")
templates = response.json()["data"]["templates"]
```

---

## 完整调用示例

### 示例一：完整短视频创作流程

```python
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"

# 1. 创建音色
def create_voice(audio_url: str) -> str:
    response = requests.post(
        f"{BASE_URL}/tts/voice/create",
        json={"audio_url": audio_url, "prefix": "creator_voice"}
    )
    return response.json()["data"]["voice_id"]

# 2. 执行完整工作流
def run_workflow(douyin_url: str, topic: str, voice_id: str) -> str:
    response = requests.post(
        f"{BASE_URL}/workflow/run",
        json={
            "douyin_url": douyin_url,
            "topic": topic,
            "workflow_type": "full",
            "voice_id": voice_id,
            "max_videos": 50
        }
    )
    return response.json()["data"]["task_id"]

# 3. 监控工作流进度
def monitor_workflow(task_id: str):
    while True:
        response = requests.get(f"{BASE_URL}/workflow/task/{task_id}")
        result = response.json()["data"]
        status = result["status"]
        progress = result.get("progress", 0)

        print(f"当前步骤: {result.get('current_step', 'N/A')}, 进度: {progress}%")

        if status == "success":
            print("✅ 工作流完成!")
            print(f"脚本: {result['result'].get('script', 'N/A')}")
            print(f"视频URL: {result['result'].get('video_url', 'N/A')}")
            return result["result"]
        elif status == "failed":
            print(f"❌ 工作流失败: {result.get('error', 'Unknown error')}")
            return None

        time.sleep(5)

# 主流程
if __name__ == "__main__":
    # 替换为实际URL
    REFERENCE_AUDIO_URL = "https://your-cdn.com/voice.mp3"
    DOUYIN_URL = "https://www.douyin.com/user/MS4wLjABAAAA..."
    TOPIC = "2024年AI发展趋势预测"

    # 创建音色
    voice_id = create_voice(REFERENCE_AUDIO_URL)
    print(f"音色创建成功: {voice_id}")

    # 执行工作流
    task_id = run_workflow(DOUYIN_URL, TOPIC, voice_id)
    print(f"工作流已启动: {task_id}")

    # 监控进度
    final_result = monitor_workflow(task_id)
```

### 示例二：分步调用

```python
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"

# 1. 抓取抖音视频
def fetch_douyin_videos(url: str) -> str:
    response = requests.post(
        f"{BASE_URL}/douyin/fetch/user",
        json={"url": url, "max_count": 50}
    )
    task_id = response.json()["data"]["task_id"]

    # 等待完成
    while True:
        status_resp = requests.get(f"{BASE_URL}/douyin/task/{task_id}")
        if status_resp.json()["data"]["status"] == "success":
            break
        time.sleep(2)

    return task_id

# 2. 分析视频风格
def analyze_style(douyin_url: str, topic: str) -> str:
    response = requests.post(
        f"{BASE_URL}/ai/analyze/full",
        json={
            "douyin_url": douyin_url,
            "topic": topic,
            "generate_script": True
        }
    )
    return response.json()["data"]["task_id"]

# 3. 合成语音
def synthesize_speech(text: str, voice_id: str) -> str:
    response = requests.post(
        f"{BASE_URL}/tts/speech",
        json={
            "text": text,
            "voice_id": voice_id
        }
    )
    return response.json()["data"]["task_id"]

# 4. 生成视频
def generate_video(video_url: str, audio_url: str) -> str:
    response = requests.post(
        f"{BASE_URL}/video/generate",
        json={
            "video_url": video_url,
            "audio_url": audio_url
        }
    )
    return response.json()["data"]["task_id"]

# 主流程
if __name__ == "__main__":
    # 分步执行
    douyin_url = "https://www.douyin.com/user/MS4wLjABAAAA..."
    voice_id = "your-existing-voice-id"

    # 抓取
    print("1. 抓取抖音视频...")
    fetch_task = fetch_douyin_videos(douyin_url)

    # 分析
    print("2. AI分析...")
    analysis_task = analyze_style(douyin_url, "AI技术")

    # 等待分析完成获取脚本
    time.sleep(30)  # 实际应轮询任务状态
    script = "这是分析生成的脚本内容..."

    # 合成
    print("3. 合成语音...")
    tts_task = synthesize_speech(script, voice_id)

    # 生成视频
    print("4. 生成视频...")
    video_task = generate_video(
        "https://example.com/ref.mp4",
        "https://example.com/audio.mp3"
    )

    print("所有任务已提交，请查询任务状态获取结果")
```

### 示例三：JavaScript/Node.js 调用

```javascript
const BASE_URL = 'http://localhost:8000/api/v1';

// 创建音色
async function createVoice(audioUrl) {
  const response = await fetch(`${BASE_URL}/tts/voice/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      audio_url: audioUrl,
      prefix: 'creator_voice'
    })
  });
  const result = await response.json();
  return result.data.voice_id;
}

// 执行工作流
async function runWorkflow(douyinUrl, topic, voiceId) {
  const response = await fetch(`${BASE_URL}/workflow/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      douyin_url: douyinUrl,
      topic: topic,
      workflow_type: 'full',
      voice_id: voiceId
    })
  });
  const result = await response.json();
  return result.data.task_id;
}

// 监控工作流
async function monitorWorkflow(taskId) {
  while (true) {
    const response = await fetch(`${BASE_URL}/workflow/task/${taskId}`);
    const result = await response.json();
    const { status, progress, current_step } = result.data;

    console.log(`当前步骤: ${current_step}, 进度: ${progress}%`);

    if (status === 'success') {
      console.log('工作流完成!');
      return result.data.result;
    } else if (status === 'failed') {
      throw new Error(result.data.error);
    }

    await new Promise(resolve => setTimeout(resolve, 5000));
  }
}

// 主流程
(async () => {
  const voiceId = await createVoice('https://your-cdn.com/voice.mp3');
  console.log('音色创建成功:', voiceId);

  const taskId = await runWorkflow(
    'https://www.douyin.com/user/MS4wLjABAAAA...',
    'AI技术最新进展',
    voiceId
  );
  console.log('工作流已启动:', taskId);

  const result = await monitorWorkflow(taskId);
  console.log('最终结果:', result);
})();
```

---

## 错误处理

所有API统一错误响应格式：

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "参数验证失败",
    "details": [...]
  },
  "request_id": "uuid"
}
```

**常见错误码**:

| 错误码 | 说明 |
|--------|------|
| VALIDATION_ERROR | 参数验证失败 |
| NOT_FOUND | 资源不存在 |
| TASK_FAILED | 任务执行失败 |
| RATE_LIMIT_EXCEEDED | 请求频率超限 |
| INTERNAL_ERROR | 服务器内部错误 |

---

## 注意事项

1. **URL 要求**: 所有音频、视频 URL 必须是公网可访问的地址
2. **异步处理**: 耗时操作返回任务 ID，需轮询查询结果
3. **超时时间**: 建议轮询间隔 5-10 秒，最长等待 30 分钟
4. **并发限制**: 建议单用户同时任务数不超过 5 个
5. **数据保留**: 生成的文件会定期清理，请及时下载保存

---

## 相关文档

- [项目框架说明](PROJECT_FRAMEWORK.md)
- [SaaS 迁移指南](SAAS_MIGRATION_GUIDE.md)
