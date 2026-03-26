# 短视频创作自动化 API 文档

## 基础信息

- **Base URL**: `http://localhost:8088/api/v1`
- **Content-Type**: `application/json` (除文件上传接口外)
- **认证方式**: `X-API-Key` 请求头

---

## 认证说明

### API Key 认证

大部分接口需要在请求头中携带 API Key：

```http
X-API-Key: your-api-key-here
```

### 获取 API Key

用户注册或登录成功后会返回 `api_key`，前端需保存该 key 用于后续请求。

### 用户角色

系统有两种用户角色：

| 角色 | 说明 | 权限 |
|------|------|------|
| `user` | 普通用户 | 基础业务接口（注册、登录、抓取、TTS、视频生成等） |
| `admin` | 管理员 | 全部接口（含用户管理、资源审核、统计等） |

**注意**：管理员专属接口需要使用 `role=admin` 的用户 API Key，否则返回 `403 Forbidden`。

---

## 通用响应结构

### 成功响应

```json
{
  "code": 200,
  "message": "success",
  "request_id": "req_123456"
}
```

### 带数据的响应

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "request_id": "req_123456"
}
```

### 错误响应

```json
{
  "detail": "错误信息描述"
}
```

---

## 状态码说明

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证（缺少或无效的 API Key） |
| 403 | 禁止访问（权限不足） |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 任务查询说明

所有异步任务接口都会返回 `task_id`，使用以下方式查询任务状态：

```http
GET /api/v1/{模块}/task/{task_id}
```

任务状态枚举：
- `pending` - 等待中
- `running` - 执行中
- `success` - 成功
- `failed` - 失败
- `cancelled` - 已取消

---

## 模块索引

1. [用户管理](#用户管理-users)
2. [抖音数据抓取](#抖音数据抓取-douyin)
3. [AI 分析](#ai-分析-ai)
4. [TTS 语音合成](#tts-语音合成-tts)
5. [视频生成](#视频生成-video)
6. [任务串联](#任务串联-chain)
7. [档案管理](#档案管理-profiles)
8. [资源管理](#资源管理-resources)
9. [存储服务](#存储服务-storage)

---

## 用户管理 (/users)

### 1. 用户注册

```http
POST /api/v1/users/register
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名（唯一） |
| password | string | 是 | 密码 |

**请求示例：**

```json
{
  "username": "testuser",
  "password": "password123"
}
```

**响应示例：**

```json
{
  "user_id": "user_xxx",
  "username": "testuser",
  "api_key": "sk-xxx",
  "created_at": "2024-01-01T00:00:00"
}
```

---

### 2. 用户登录

```http
POST /api/v1/users/login
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**请求示例：**

```json
{
  "username": "testuser",
  "password": "password123"
}
```

**响应示例：**

```json
{
  "user_id": "user_xxx",
  "username": "testuser",
  "api_key": "sk-xxx",
  "message": "登录成功"
}
```

---

### 3. 创建用户（管理员专用）

```http
POST /api/v1/users/create
```

**请求头：** `X-API-Key: admin-api-key` ⚠️ 需要管理员权限

**请求体：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| name | string | 是 | - | 用户名称 |
| role | string | 否 | user | 用户角色（user/admin） |

**请求示例：**

```json
{
  "name": "newuser",
  "role": "user"
}
```

创建管理员用户：

```json
{
  "name": "adminuser",
  "role": "admin"
}
```

**响应示例：**

```json
{
  "user_id": "user_xxx",
  "username": "newuser",
  "api_key": "sk-xxx",
  "created_at": "2024-01-01T00:00:00"
}
```

**错误示例：**

```json
{
  "detail": "需要管理员权限"
}
```

---

### 4. 获取用户列表（管理员专用）

```http
GET /api/v1/users/list
```

**请求头：** `X-API-Key: admin-api-key` ⚠️ 需要管理员权限

**响应示例：**

```json
{
  "users": [
    {
      "user_id": "user_xxx",
      "username": "testuser",
      "api_key": "sk-xxxxxxx...",
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "request_id": "req_123"
}
```

---

### 5. 获取当前用户信息

```http
GET /api/v1/users/me
```

**请求头：** `X-API-Key: your-api-key`

**响应示例：**

```json
{
  "message": "请在请求头中添加 X-API-Key 进行认证",
  "example": "X-API-Key: test-key-123456"
}
```

---

## 抖音数据抓取 (/douyin)

### 1. 抓取用户视频

```http
POST /api/v1/douyin/fetch/user
```

**请求头：** `X-API-Key: your-api-key`

**请求体：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| url | string | 是 | - | 抖音用户主页 URL |
| max_count | int | 否 | 100 | 最大抓取数量 (1-200) |
| enable_filter | bool | 否 | false | 是否启用过滤 |
| min_likes | int | 否 | 50 | 最小点赞数 |
| min_comments | int | 否 | 0 | 最小评论数 |
| top_n | int | 否 | 0 | 返回 Top N 热门视频 (0=全部) |
| sort_by | string | 否 | like | 排序字段 (like/comment/share) |
| wait | bool | 否 | false | 是否等待完成后直接返回结果 |

**请求示例：**

```json
{
  "url": "https://www.douyin.com/user/xxx",
  "max_count": 50,
  "enable_filter": true,
  "min_likes": 100,
  "wait": false
}
```

**响应示例（异步模式）：**

```json
{
  "code": 200,
  "task_id": "task_xxx",
  "status": "pending",
  "progress": 0,
  "created_at": "2024-01-01T00:00:00",
  "request_id": "req_123"
}
```

**响应示例（同步模式，wait=true）：**

```json
{
  "code": 200,
  "message": "success",
  "task_id": "sync",
  "status": "success",
  "progress": 100,
  "result": {
    "videos": [...],
    "total": 50,
    "filtered_count": 20
  },
  "request_id": "req_123"
}
```

---

### 2. 查询抓取任务状态

```http
GET /api/v1/douyin/task/{task_id}
```

**响应示例：**

```json
{
  "task_id": "task_xxx",
  "status": "success",
  "progress": 100,
  "created_at": "2024-01-01T00:00:00",
  "started_at": "2024-01-01T00:00:01",
  "completed_at": "2024-01-01T00:00:30",
  "result": {
    "videos": [
      {
        "aweme_id": "xxx",
        "desc": "视频文案",
        "desc_clean": "清理后文案",
        "author": "作者昵称",
        "author_id": "author_xxx",
        "like_count": 1000,
        "comment_count": 50,
        "share_count": 20,
        "play_count": 5000,
        "duration": 15.5,
        "create_time": 1609459200000,
        "create_time_str": "2021-01-01",
        "hashtags": ["#标签1", "#标签2"],
        "music": "背景音乐",
        "video_url": "https://...",
        "hot_score": 85.5
      }
    ],
    "total": 50,
    "filtered_count": 20
  },
  "request_id": "req_123"
}
```

---

### 3. 抓取话题视频

```http
POST /api/v1/douyin/fetch/topic
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| topic | string | 是 | 话题名称 |
| max_count | int | 否 | 最大抓取数量 (默认 50) |

**请求示例：**

```json
{
  "topic": "搞笑",
  "max_count": 30
}
```

---

### 4. 抓取抖音热榜

```http
POST /api/v1/douyin/fetch/hotlist
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| cate_id | int | 否 | 分类 ID |

**请求示例：**

```json
{
  "cate_id": 1
}
```

---

### 5. 获取缓存视频

```http
GET /api/v1/douyin/videos?limit=100&offset=0
```

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| limit | int | 否 | 100 | 返回数量限制 |
| offset | int | 否 | 0 | 偏移量 |

---

## AI 分析 (/ai)

### 1. 火爆原因分析

```http
POST /api/v1/ai/analyze/viral
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| video_data | array | 是 | 视频数据列表 |
| video_ids | array | 否 | 指定分析的视频 ID 列表 |

**请求示例：**

```json
{
  "video_data": [
    {
      "aweme_id": "xxx",
      "desc": "视频文案",
      "author": {"nickname": "作者", "uid": "xxx"},
      "statistics": {
        "digg_count": 1000,
        "comment_count": 50,
        "share_count": 20
      }
    }
  ],
  "video_ids": ["xxx", "yyy"]
}
```

**响应示例（任务状态）：**

```json
{
  "task_id": "task_xxx",
  "status": "pending",
  "progress": 0,
  "created_at": "2024-01-01T00:00:00"
}
```

**结果示例（任务完成后）：**

```json
{
  "summary": "该视频火爆的主要原因是...",
  "factors": [
    {
      "factor": "话题热度",
      "score": 85,
      "description": "结合了当下热门话题"
    },
    {
      "factor": "情绪共鸣",
      "score": 78,
      "description": "内容能引起观众情感共鸣"
    }
  ],
  "topic_heat": {...},
  "emotional_resonance": {...},
  "practicality": {...},
  "entertainment": {...},
  "personality_appeal": {...},
  "expression_technique": {...}
}
```

---

### 2. 风格特征分析

```http
POST /api/v1/ai/analyze/style
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| video_data | array | 是 | 视频数据列表 |
| analysis_dimensions | array | 否 | 分析维度（默认全维度） |

**分析维度：**
- 文案风格
- 视频类型
- 拍摄特征
- 高频词汇
- 标签策略
- 音乐风格

**请求示例：**

```json
{
  "video_data": [...],
  "analysis_dimensions": ["文案风格", "视频类型", "拍摄特征"]
}
```

**结果示例：**

```json
{
  "summary": "该创作者的视频风格以...",
  "copywriting_style": {...},
  "video_type": "知识分享",
  "shooting_features": {...},
  "high_frequency_words": ["关键词1", "关键词2"],
  "sentence_patterns": ["句式1", "句式2"],
  "hashtag_strategy": {...},
  "music_style": {...}
}
```

---

### 3. 生成 TTS 脚本

```http
POST /api/v1/ai/generate/script
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| style_analysis | object | 是 | 风格分析结果 |
| viral_analysis | object | 是 | 火爆原因分析结果 |
| topic | string | 是 | 新主题 |
| target_duration | float | 否 | 目标时长(秒)，默认 20 |

**请求示例：**

```json
{
  "style_analysis": {...},
  "viral_analysis": {...},
  "topic": "如何高效学习",
  "target_duration": 60
}
```

**结果示例：**

```json
{
  "title": "视频标题",
  "description": "视频描述",
  "hashtags": ["#标签1", "#标签2"],
  "publish_text": "发布文案",
  "full_script": "完整台词内容",
  "segments": ["分段1", "分段2", "分段3"],
  "word_count": 150,
  "estimated_duration": 60
}
```

---

### 4. 完整分析流程

```http
POST /api/v1/ai/analyze/full
```

**请求体：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| douyin_url | string | 是 | - | 抖音用户主页 URL |
| topic | string | 是 | - | 新主题 |
| max_videos | int | 否 | 100 | 分析视频数量 |
| enable_viral_analysis | bool | 否 | true | 启用火爆原因分析 |
| enable_style_analysis | bool | 否 | true | 启用风格分析 |
| generate_script | bool | 否 | true | 是否生成脚本 |
| target_duration | float | 否 | 60 | TTS 目标时长(秒) |

---

### 5. 查询 AI 分析任务状态

```http
GET /api/v1/ai/task/{task_id}
```

---

## TTS 语音合成 (/tts)

### 1. 从文件创建音色（推荐）

```http
POST /api/v1/tts/voice/create-from-file
```

**请求头：** `X-API-Key: your-api-key`  
**Content-Type:** `multipart/form-data`

**表单参数：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| file | file | 是 | - | 音色音频文件（mp3/wav/m4a 等） |
| prefix | string | 否 | myvoice | 音色前缀 |
| model | string | 否 | cosyvoice-v3.5-flash | TTS 模型 |
| preview_text | string | 否 | 你好，这是我的音色。 | 试听文本 |
| auto_upload_oss | bool | 否 | true | 是否自动上传试听音频到 OSS |

**JavaScript 示例：**

```javascript
const formData = new FormData();
formData.append('file', audioFile);
formData.append('prefix', 'myvoice');
formData.append('preview_text', '你好，这是我的音色。');

const res = await fetch('/api/v1/tts/voice/create-from-file', {
  method: 'POST',
  headers: { 'X-API-Key': apiKey },
  body: formData
});
const { task_id } = await res.json();
```

**响应示例：**

```json
{
  "code": 200,
  "message": "音色创建任务已创建",
  "task_id": "task_xxx",
  "status": "pending",
  "progress": 0,
  "created_at": "2024-01-01T00:00:00"
}
```

**任务完成后结果：**

```json
{
  "voice_id": "cosyvoice-v3.5-flash-myvoice-xxx",
  "prefix": "myvoice",
  "model": "cosyvoice-v3.5-flash",
  "status": "OK",
  "preview_text": "你好，这是我的音色。",
  "preview_audio_url": "https://oss.xxx/preview.mp3",
  "is_available": true,
  "audio_url": "https://oss.xxx/original.mp3"
}
```

---

### 2. 从 URL 创建音色

```http
POST /api/v1/tts/voice/create-from-url
```

**请求头：** `X-API-Key: your-api-key`

**请求体：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| audio_url | string | 是 | - | 音色音频的公网 URL |
| prefix | string | 否 | myvoice | 音色前缀 |
| model | string | 否 | cosyvoice-v3.5-flash | TTS 模型 |
| wait_ready | bool | 否 | true | 是否等待音色就绪 |

**请求示例：**

```json
{
  "audio_url": "https://oss.xxx/audio.mp3",
  "prefix": "myvoice",
  "model": "cosyvoice-v3.5-flash"
}
```

---

### 3. 获取音色列表

```http
GET /api/v1/tts/voice/list
```

**请求头：** `X-API-Key: your-api-key`

**说明：** 返回当前用户自己创建的音色列表（自动按用户隔离）。

**响应示例：**

```json
{
  "voices": [
    {
      "voice_id": "cosyvoice-v3.5-flash-myvoice-xxx",
      "prefix": "myvoice",
      "model": "cosyvoice-v3.5-flash",
      "status": "OK",
      "created_at": "2024-01-01T00:00:00",
      "is_available": true
    }
  ],
  "request_id": "req_123"
}
```

---

### 4. 查询单个音色

```http
GET /api/v1/tts/voice/{voice_id}
```

**请求头：** `X-API-Key: your-api-key`

**说明：** 只能查询当前用户自己创建的音色，其他用户的音色返回 404。

---

### 5. 获取所有音色（管理员专用）

```http
GET /api/v1/tts/admin/voices?status=OK&limit=100
```

**请求头：** `X-API-Key: admin-api-key` ⚠️ 需要管理员权限

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| status | string | 否 | - | 按状态过滤 (DEPLOYING/OK/UNDEPLOYED) |
| limit | int | 否 | 100 | 返回数量限制 |

**响应示例：**

```json
{
  "voices": [
    {
      "voice_id": "cosyvoice-v3.5-flash-myvoice-xxx",
      "prefix": "myvoice",
      "model": "cosyvoice-v3.5-flash",
      "status": "OK",
      "created_at": "2024-01-01T00:00:00",
      "is_available": true
    }
  ],
  "request_id": "req_123"
}
```

---

### 6. 文字转语音

```http
POST /api/v1/tts/speech
```

**请求头：** `X-API-Key: your-api-key`

**请求体：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| text | string | 是 | - | 要合成的文本 |
| voice_id | string | 是 | - | 音色 ID |
| model | string | 否 | 音色对应模型 | TTS 模型 |
| output_format | string | 否 | mp3 | 输出格式 (mp3/wav/pcm) |

**请求示例：**

```json
{
  "text": "你好，这是一段测试文本。",
  "voice_id": "cosyvoice-v3.5-flash-myvoice-xxx",
  "output_format": "mp3"
}
```

**任务完成后结果：**

```json
{
  "audio_url": "https://oss.xxx/tts_xxx.mp3",
  "duration": 5.2,
  "format": "mp3",
  "text": "你好，这是一段测试文本。"
}
```

---

### 7. 分段文字转语音

```http
POST /api/v1/tts/speech/segments
```

**请求头：** `X-API-Key: your-api-key`

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| segments | array | 是 | 分段文本列表 |
| voice_id | string | 是 | 音色 ID |
| model | string | 否 | TTS 模型 |
| output_format | string | 否 | 输出格式 |

**请求示例：**

```json
{
  "segments": ["第一段内容", "第二段内容", "第三段内容"],
  "voice_id": "cosyvoice-v3.5-flash-myvoice-xxx"
}
```

---

### 8. TTS 脚本转语音

```http
POST /api/v1/tts/script
```

**请求头：** `X-API-Key: your-api-key`

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| full_text | string | 是 | 完整台词 |
| segments | array | 是 | 分段台词 |
| voice_id | string | 是 | 音色 ID |
| model | string | 否 | TTS 模型 |

**请求示例：**

```json
{
  "full_text": "完整台词内容",
  "segments": ["分段1", "分段2"],
  "voice_id": "cosyvoice-v3.5-flash-myvoice-xxx"
}
```

**结果示例：**

```json
{
  "full_audio_url": "https://oss.xxx/full.mp3",
  "full_audio_oss_url": "https://oss.xxx/full.mp3",
  "segment_audio_urls": ["https://oss.xxx/seg1.mp3", "https://oss.xxx/seg2.mp3"],
  "segments_audio_oss": ["https://oss.xxx/seg1.mp3", "https://oss.xxx/seg2.mp3"],
  "total_duration": 30.5
}
```

---

## 视频生成 (/video)

### 1. 生成口型同步视频

```http
POST /api/v1/video/generate
```

**请求体：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| video_url | string | 是 | - | 参考视频公网 URL |
| audio_url | string | 是 | - | 合成音频公网 URL |
| ref_image_url | string | 否 | - | 参考图片 URL（可选） |
| video_extension | bool | 否 | true | 是否扩展视频以匹配音频长度 |
| resolution | string | 否 | - | 分辨率（如 1280x720） |

**请求示例：**

```json
{
  "video_url": "https://oss.xxx/ref_video.mp4",
  "audio_url": "https://oss.xxx/tts_audio.mp3",
  "video_extension": true
}
```

**响应示例：**

```json
{
  "task_id": "task_xxx",
  "status": "pending",
  "progress": 0,
  "created_at": "2024-01-01T00:00:00"
}
```

---

### 2. 从文件生成视频（推荐）

```http
POST /api/v1/video/generate-from-files
```

**请求头：** `X-API-Key: your-api-key`  
**Content-Type:** `multipart/form-data`

**表单参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| video_file | file | 是 | 参考视频文件（mp4/mov/avi 等） |
| audio_file | file | 是 | 合成音频文件（mp3/wav 等） |
| ref_image_file | file | 否 | 参考图片文件（可选） |
| video_extension | bool | 否 | 是否扩展视频以匹配音频长度（默认 true） |
| resolution | string | 否 | 分辨率（如 1280x720） |

**JavaScript 示例：**

```javascript
const formData = new FormData();
formData.append('video_file', videoFile);
formData.append('audio_file', audioFile);
formData.append('video_extension', 'true');

const res = await fetch('/api/v1/video/generate-from-files', {
  method: 'POST',
  headers: { 'X-API-Key': apiKey },
  body: formData
});
const { task_id } = await res.json();
```

**任务完成后结果：**

```json
{
  "task_id": "task_xxx",
  "video_url": "https://oss.xxx/output.mp4",
  "status": "success",
  "input_urls": {
    "video_url": "https://oss.xxx/ref_video.mp4",
    "audio_url": "https://oss.xxx/tts_audio.mp3",
    "ref_image_url": null
  }
}
```

---

### 3. 查询视频任务状态

```http
GET /api/v1/video/task/{task_id}
```

**响应示例：**

```json
{
  "task_id": "task_xxx",
  "status": "success",
  "progress": 100,
  "video_url": "https://oss.xxx/output.mp4",
  "error": null,
  "request_id": "req_123"
}
```

---

### 4. 取消视频任务

```http
DELETE /api/v1/video/task/{task_id}
```

**响应示例：**

```json
{
  "code": 200,
  "message": "任务已取消",
  "request_id": "req_123"
}
```

---

## 任务串联 (/chain)

任务串联接口允许基于前一步的 `task_id` 自动执行后续步骤，无需手动传递数据。

### 1. 根据抓取任务进行 AI 分析

```http
POST /api/v1/chain/analyze/from-fetch
```

**请求头：** `X-API-Key: your-api-key`

**请求体：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| fetch_task_id | string | 是 | - | 抓取任务返回的 task_id |
| enable_viral | bool | 否 | true | 是否进行火爆原因分析 |
| enable_style | bool | 否 | true | 是否进行风格分析 |

**请求示例：**

```json
{
  "fetch_task_id": "task_xxx",
  "enable_viral": true,
  "enable_style": true
}
```

**响应示例：**

```json
{
  "code": 200,
  "message": "分析任务已创建",
  "task_id": "new_task_xxx",
  "status": "pending",
  "progress": 0,
  "created_at": "2024-01-01T00:00:00"
}
```

---

### 2. 根据分析任务生成脚本

```http
POST /api/v1/chain/generate/from-analysis
```

**请求头：** `X-API-Key: your-api-key`

**请求体：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| analysis_task_id | string | 是 | - | 分析任务返回的 task_id |
| topic | string | 是 | - | 新主题 |
| target_duration | float | 否 | 60 | 目标时长（秒） |

**请求示例：**

```json
{
  "analysis_task_id": "task_xxx",
  "topic": "如何高效学习",
  "target_duration": 60
}
```

---

### 3. 根据脚本任务进行 TTS

```http
POST /api/v1/chain/tts/from-script
```

**请求头：** `X-API-Key: your-api-key`

**请求体：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| script_task_id | string | 是 | - | 脚本任务返回的 task_id |
| voice_id | string | 是 | - | 音色 ID |
| model | string | 否 | 音色对应模型 | TTS 模型 |
| auto_upload_oss | bool | 否 | true | 是否自动上传到 OSS |

**请求示例：**

```json
{
  "script_task_id": "task_xxx",
  "voice_id": "cosyvoice-v3.5-flash-myvoice-xxx"
}
```

**结果示例：**

```json
{
  "full_audio_url": "https://oss.xxx/full.mp3",
  "full_audio_oss_url": "https://oss.xxx/full.mp3",
  "segment_audio_urls": ["https://oss.xxx/seg1.mp3"],
  "segments_audio_oss": ["https://oss.xxx/seg1.mp3"],
  "total_duration": 30.5,
  "preview_urls": {
    "audio": "https://oss.xxx/full.mp3",
    "segments": ["https://oss.xxx/seg1.mp3"]
  }
}
```

---

### 4. 从分析任务直接生成 TTS（合并步骤）

```http
POST /api/v1/chain/tts/from-analysis
```

**请求头：** `X-API-Key: your-api-key`

**请求体：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| analysis_task_id | string | 是 | - | 分析任务返回的 task_id |
| topic | string | 是 | - | 新主题 |
| voice_id | string | 是 | - | 音色 ID |
| target_duration | float | 否 | 60 | 目标时长（秒） |
| model | string | 否 | 音色对应模型 | TTS 模型 |
| auto_upload_oss | bool | 否 | true | 是否自动上传到 OSS |

---

### 5. 根据 TTS 任务生成视频

```http
POST /api/v1/chain/video/from-tts
```

**请求头：** `X-API-Key: your-api-key`

**请求体：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| tts_task_id | string | 是 | - | TTS 任务返回的 task_id |
| ref_video_url | string | 否 | - | 参考视频 URL（与 ref_video_path 二选一） |
| ref_video_path | string | 否 | - | 本地参考视频路径 |
| video_extension | bool | 否 | true | 是否扩展视频以匹配音频长度 |
| resolution | string | 否 | - | 分辨率（如 1280x720） |

---

## 档案管理 (/profiles)

档案管理模块允许用户创建和维护客户档案，包含行业、目标人群、痛点等信息，然后基于档案通过大模型生成多版本文案。

### 1. 创建档案

```http
POST /api/v1/profiles
```

**请求头：** `X-API-Key: your-api-key`

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 档案名称 |
| industry | string | 是 | 所需行业 |
| video_url | string | 否 | 参考视频链接 |
| homepage_url | string | 否 | 参考主页链接 |
| target_audience | string | 是 | 目标用户群体 |
| customer_pain_points | string | 是 | 客户痛点 |
| solution | string | 是 | 解决方案 |
| persona_background | string | 是 | 人设背景 |

**请求示例：**

```json
{
  "name": "美食探店号",
  "industry": "美食",
  "video_url": "https://www.douyin.com/user/xxx",
  "target_audience": "25-35岁城市白领，喜欢尝试新餐厅",
  "customer_pain_points": "不知道附近有什么好吃的，选择困难",
  "solution": "提供真实探店体验，帮用户做美食决策",
  "persona_background": "资深美食博主，有5年餐饮行业经验"
}
```

**响应示例：**

```json
{
  "code": 201,
  "message": "档案创建成功",
  "data": {
    "profile_id": "profile_a1b2c3d4e5f6",
    "id": 1
  },
  "request_id": "req_123"
}
```

---

### 2. 获取档案列表

```http
GET /api/v1/profiles?limit=50&offset=0
```

**请求头：** `X-API-Key: your-api-key`

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| limit | int | 否 | 50 | 返回数量限制 (1-200) |
| offset | int | 否 | 0 | 偏移量 |

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "profiles": [
      {
        "id": 1,
        "profile_id": "profile_a1b2c3d4e5f6",
        "user_id": 1,
        "name": "美食探店号",
        "industry": "美食",
        "video_url": "https://www.douyin.com/user/xxx",
        "homepage_url": null,
        "target_audience": "25-35岁城市白领...",
        "customer_pain_points": "不知道附近有什么好吃的...",
        "solution": "提供真实探店体验...",
        "persona_background": "资深美食博主...",
        "status": "active",
        "created_at": "2026-03-25T10:00:00",
        "updated_at": "2026-03-25T10:00:00"
      }
    ],
    "total": 1
  },
  "request_id": "req_123"
}
```

---

### 3. 获取档案详情

```http
GET /api/v1/profiles/{profile_id}
```

**请求头：** `X-API-Key: your-api-key`

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| profile_id | string | 档案 ID（创建时返回的 profile_id） |

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "profile_id": "profile_a1b2c3d4e5f6",
    "name": "美食探店号",
    "industry": "美食",
    "video_url": "https://www.douyin.com/user/xxx",
    "homepage_url": null,
    "target_audience": "25-35岁城市白领，喜欢尝试新餐厅",
    "customer_pain_points": "不知道附近有什么好吃的，选择困难",
    "solution": "提供真实探店体验，帮用户做美食决策",
    "persona_background": "资深美食博主，有5年餐饮行业经验",
    "status": "active",
    "created_at": "2026-03-25T10:00:00",
    "updated_at": "2026-03-25T10:00:00"
  },
  "request_id": "req_123"
}
```

---

### 4. 更新档案

```http
PUT /api/v1/profiles/{profile_id}
```

**请求头：** `X-API-Key: your-api-key`

**请求体：**（仅传需要更新的字段，所有字段可选）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 否 | 档案名称 |
| industry | string | 否 | 所需行业 |
| video_url | string | 否 | 参考视频链接 |
| homepage_url | string | 否 | 参考主页链接 |
| target_audience | string | 否 | 目标用户群体 |
| customer_pain_points | string | 否 | 客户痛点 |
| solution | string | 否 | 解决方案 |
| persona_background | string | 否 | 人设背景 |

**请求示例（部分更新）：**

```json
{
  "name": "美食探店号V2",
  "target_audience": "20-30岁年轻上班族，热爱美食探店"
}
```

**响应示例：**

```json
{
  "code": 200,
  "message": "档案更新成功",
  "request_id": "req_123"
}
```

---

### 5. 删除档案

```http
DELETE /api/v1/profiles/{profile_id}
```

**请求头：** `X-API-Key: your-api-key`

**说明：** 软删除，数据不会真正从数据库移除。

**响应示例：**

```json
{
  "code": 200,
  "message": "档案已删除",
  "request_id": "req_123"
}
```

---

### 6. 获取行业列表

```http
GET /api/v1/profiles/industries
```

**请求头：** `X-API-Key: your-api-key`

**说明：** 返回系统预设行业和当前用户的自定义行业合并后的列表。

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "system": ["美食", "科技", "美妆", "穿搭", "母婴", "教育", "健身", "旅行", "汽车", "房产", "家居", "宠物", "医疗", "金融", "法律", "娱乐", "电商", "其他"],
    "custom": [
      {"id": 1, "name": "宠物摄影"}
    ],
    "all": ["美食", "科技", "美妆", "穿搭", "母婴", "教育", "健身", "旅行", "汽车", "房产", "家居", "宠物", "医疗", "金融", "法律", "娱乐", "电商", "其他", "宠物摄影"]
  },
  "request_id": "req_123"
}
```

---

### 7. 添加自定义行业

```http
POST /api/v1/profiles/industries
```

**请求头：** `X-API-Key: your-api-key`

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 行业名称 |

**请求示例：**

```json
{
  "name": "宠物摄影"
}
```

**响应示例：**

```json
{
  "code": 201,
  "message": "自定义行业添加成功",
  "data": {
    "id": 1,
    "name": "宠物摄影"
  },
  "request_id": "req_123"
}
```

**错误示例：**

```json
{
  "detail": "该行业已存在于系统预设中"
}
```

```json
{
  "detail": "该行业已存在"
}
```

---

### 8. 删除自定义行业

```http
DELETE /api/v1/profiles/industries/{industry_id}
```

**请求头：** `X-API-Key: your-api-key`

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| industry_id | int | 自定义行业 ID（从行业列表接口获取） |

**响应示例：**

```json
{
  "code": 200,
  "message": "自定义行业已删除",
  "request_id": "req_123"
}
```

---

### 9. 从档案生成文案

```http
POST /api/v1/chain/generate-from-profile
```

**请求头：** `X-API-Key: your-api-key`

**说明：** 根据档案信息，调用大模型生成多版本文案（短视频脚本或纯文字文案），用户可从中选择。这是一个异步任务，返回 `task_id`，通过轮询获取结果。

**请求体：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| profile_id | string | 是 | - | 档案 ID |
| generate_type | string | 否 | video_script | 文案类型：`video_script`（短视频脚本）或 `text_copy`（纯文字文案） |
| topic | string | 否 | - | 可选的主题补充 |
| count | int | 否 | 3 | 生成版本数量 (1-5) |

**请求示例：**

```json
{
  "profile_id": "profile_a1b2c3d4e5f6",
  "generate_type": "video_script",
  "topic": "周末探店推荐",
  "count": 3
}
```

**响应示例（任务创建）：**

```json
{
  "code": 200,
  "message": "文案生成任务已创建",
  "task_id": "task_xxx",
  "status": "pending",
  "progress": 0,
  "created_at": "2026-03-25T10:00:00",
  "request_id": "req_123"
}
```

**任务完成后结果（通过 GET /api/v1/chain/task/{task_id} 获取）：**

```json
{
  "task_id": "task_xxx",
  "status": "success",
  "progress": 100,
  "result": {
    "versions": [
      {
        "index": 1,
        "content": "【版本1】\n标题：周末3家宝藏餐厅推荐\n正文：这个周末别再纠结吃什么了..."
      },
      {
        "index": 2,
        "content": "【版本2】\n标题：打工人周末美食攻略\n正文：加班了一整周，周末必须犒劳一下自己..."
      },
      {
        "index": 3,
        "content": "【版本3】\n标题：跟着本地人吃就对了\n正文：作为一名在美食圈摸爬滚打5年的老饕..."
      }
    ],
    "profile_id": "profile_a1b2c3d4e5f6",
    "generate_type": "video_script"
  }
}
```

**完整工作流示例：**

```javascript
// 1. 创建档案
const profileRes = await fetch('/api/v1/profiles', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': apiKey
  },
  body: JSON.stringify({
    name: '美食探店号',
    industry: '美食',
    target_audience: '25-35岁城市白领',
    customer_pain_points: '不知道吃什么',
    solution: '真实探店体验',
    persona_background: '资深美食博主'
  })
});
const { data: { profile_id } } = await profileRes.json();

// 2. 从档案生成文案
const genRes = await fetch('/api/v1/chain/generate-from-profile', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': apiKey
  },
  body: JSON.stringify({
    profile_id,
    generate_type: 'video_script',
    topic: '周末探店',
    count: 3
  })
});
const { task_id } = await genRes.json();

// 3. 轮询等待结果
const pollResult = async (taskId) => {
  while (true) {
    const res = await fetch(`/api/v1/chain/task/${taskId}`, {
      headers: { 'X-API-Key': apiKey }
    });
    const task = await res.json();
    if (task.status === 'success') {
      return task.result.versions; // 返回多个版本供用户选择
    }
    if (task.status === 'failed') {
      throw new Error(task.error || '生成失败');
    }
    await new Promise(resolve => setTimeout(resolve, 3000));
  }
};

const versions = await pollResult(task_id);
// versions 是一个数组，每个元素包含 index 和 content
// 前端展示给用户选择
```

---

## 资源管理 (/resources)

### 1. 获取用户资源列表

```http
GET /api/v1/resources/list?resource_type=audio&status=active&limit=50&offset=0
```

**请求头：** `X-API-Key: your-api-key`

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| resource_type | string | 否 | - | 资源类型 (audio/video/image) |
| status | string | 否 | active | 资源状态 |
| limit | int | 否 | 50 | 返回数量限制 (1-200) |
| offset | int | 否 | 0 | 偏移量 |

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "resources": [
      {
        "id": 1,
        "resource_type": "audio",
        "oss_url": "https://oss.xxx/audio.mp3",
        "file_hash": "xxx",
        "status": "active",
        "created_at": "2024-01-01T00:00:00"
      }
    ],
    "stats": {
      "total": 100,
      "audio": 50,
      "video": 30,
      "image": 20
    }
  },
  "request_id": "req_123"
}
```

---

### 2. 根据任务 ID 获取资源

```http
GET /api/v1/resources/task/{task_id}
```

**请求头：** `X-API-Key: your-api-key`

---

### 3. 获取所有资源（管理员专用）

```http
GET /api/v1/resources/admin/all
```

**请求头：** `X-API-Key: admin-api-key` ⚠️ 需要管理员权限

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| resource_type | string | 否 | 资源类型过滤 |
| status | string | 否 | 状态过滤 |
| limit | int | 否 | 返回数量限制 (1-500) |
| offset | int | 否 | 偏移量 |

---

### 4. 获取资源统计（管理员专用）

```http
GET /api/v1/resources/stats?days=7
```

**请求头：** `X-API-Key: admin-api-key` ⚠️ 需要管理员权限

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| days | int | 否 | 7 | 统计最近几天 (1-90) |

---

### 5. 更新资源状态（管理员专用）

```http
PUT /api/v1/resources/{resource_id}/status?status=deleted
```

**请求头：** `X-API-Key: admin-api-key` ⚠️ 需要管理员权限

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 是 | 新状态 (active/deleted/blocked) |

---

## 存储服务 (/storage)

### 1. 上传文件到 OSS

```http
POST /api/v1/storage/upload/file
```

**Content-Type:** `multipart/form-data`

**表单参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 要上传的文件 |
| file_type | string | 否 | 文件类型（不指定则自动识别） |

**JavaScript 示例：**

```javascript
const formData = new FormData();
formData.append('file', fileToUpload);

const res = await fetch('/api/v1/storage/upload/file', {
  method: 'POST',
  body: formData
});
const { task_id } = await res.json();
```

**响应示例：**

```json
{
  "task_id": "task_xxx",
  "status": "pending",
  "progress": 0,
  "created_at": "2024-01-01T00:00:00"
}
```

**任务完成后结果：**

```json
{
  "oss_url": "https://oss.xxx/file.mp3",
  "oss_object_name": "audio/file_xxx.mp3",
  "file_hash": "abc123...",
  "file_type": "audio",
  "size": 1024000,
  "cached": false
}
```

---

### 2. 通过本地路径上传

```http
POST /api/v1/storage/upload/path
```

**请求体：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| file_path | string | 是 | - | 本地文件路径 |
| file_type | string | 否 | - | 文件类型（不指定则自动识别） |
| force_reupload | bool | 否 | false | 是否强制重新上传 |
| custom_object_name | string | 否 | - | 自定义 OSS 对象名 |

---

### 3. 批量上传文件

```http
POST /api/v1/storage/upload/batch
```

**Content-Type:** `multipart/form-data`

**表单参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| files | file[] | 是 | 要上传的文件列表 |
| file_type | string | 否 | 文件类型 |

---

### 4. 查询上传任务状态

```http
GET /api/v1/storage/upload/task/{task_id}
```

---

### 5. 获取上传记录

```http
GET /api/v1/storage/records?file_type=audio
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file_type | string | 否 | 过滤文件类型 (audio/video/image) |

**响应示例：**

```json
{
  "data": [
    {
      "file_path": "/path/to/file.mp3",
      "file_hash": "abc123...",
      "oss_url": "https://oss.xxx/file.mp3",
      "file_type": "audio",
      "size": 1024000,
      "uploaded_at": "2024-01-01T00:00:00",
      "last_accessed_at": "2024-01-01T01:00:00"
    }
  ],
  "total": 10,
  "request_id": "req_123"
}
```

---

### 6. 根据 hash 获取 URL

```http
GET /api/v1/storage/url/{file_hash}
```

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "oss_url": "https://oss.xxx/file.mp3",
    "file_hash": "abc123..."
  },
  "request_id": "req_123"
}
```

---

### 7. 获取 OSS 配置状态

```http
GET /api/v1/storage/config/status
```

**响应示例：**

```json
{
  "configured": true,
  "records_count": 10,
  "temp_dir": "/path/to/temp",
  "records_file": "/path/to/records.json",
  "message": null,
  "request_id": "req_123"
}
```

---

### 8. 清理过期记录

```http
POST /api/v1/storage/records/cleanup?days=7
```

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| days | int | 否 | 7 | 保留天数 |

---

## 完整工作流示例

以下是一个完整的工作流程示例，展示如何从抓取视频到生成最终视频：

```javascript
// 1. 用户登录获取 API Key
const loginRes = await fetch('/api/v1/users/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'testuser',
    password: 'password123'
  })
});
const { api_key } = await loginRes.json();

// 2. 抓取用户视频
const fetchRes = await fetch('/api/v1/douyin/fetch/user', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': api_key
  },
  body: JSON.stringify({
    url: 'https://www.douyin.com/user/xxx',
    max_count: 50
  })
});
const { task_id: fetchTaskId } = await fetchRes.json();

// 3. 等待抓取完成，然后进行 AI 分析
const analyzeRes = await fetch('/api/v1/chain/analyze/from-fetch', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': api_key
  },
  body: JSON.stringify({
    fetch_task_id: fetchTaskId,
    enable_viral: true,
    enable_style: true
  })
});
const { task_id: analyzeTaskId } = await analyzeRes.json();

// 4. 根据分析生成脚本
const scriptRes = await fetch('/api/v1/chain/generate/from-analysis', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': api_key
  },
  body: JSON.stringify({
    analysis_task_id: analyzeTaskId,
    topic: '如何高效学习',
    target_duration: 60
  })
});
const { task_id: scriptTaskId } = await scriptRes.json();

// 5. 根据脚本进行 TTS
const ttsRes = await fetch('/api/v1/chain/tts/from-script', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': api_key
  },
  body: JSON.stringify({
    script_task_id: scriptTaskId,
    voice_id: 'cosyvoice-v3.5-flash-myvoice-xxx'
  })
});
const { task_id: ttsTaskId } = await ttsRes.json();

// 6. 根据 TTS 生成视频
const videoFormData = new FormData();
videoFormData.append('video_file', refVideoFile);
// 使用 tts_task_id 获取音频 URL，或直接上传
// ...

const videoRes = await fetch('/api/v1/video/generate-from-files', {
  method: 'POST',
  headers: { 'X-API-Key': api_key },
  body: videoFormData
});
const { task_id: videoTaskId } = await videoRes.json();

// 7. 轮询查询视频任务状态
const pollVideoStatus = async (taskId) => {
  while (true) {
    const statusRes = await fetch(`/api/v1/video/task/${taskId}`);
    const { status, video_url } = await statusRes.json();
    if (status === 'success') {
      return video_url;
    }
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
};

const finalVideoUrl = await pollVideoStatus(videoTaskId);
console.log('最终视频 URL:', finalVideoUrl);
```

---

## 常见问题

### 1. 如何轮询任务状态？

```javascript
const pollTask = async (taskId, url) => {
  while (true) {
    const res = await fetch(`${url}/${taskId}`);
    const { status, progress, result } = await res.json();
    
    console.log(`进度: ${progress}%`);
    
    if (status === 'success') {
      return result;
    }
    if (status === 'failed') {
      throw new Error('任务失败');
    }
    
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
};
```

### 2. 文件上传大小限制

- 默认最大上传大小：100MB
- 支持的音频格式：mp3, wav, m4a, aac
- 支持的视频格式：mp4, mov, avi
- 支持的图片格式：jpg, jpeg, png, webp

### 3. 错误处理

```javascript
try {
  const res = await fetch('/api/v1/xxx', {
    headers: { 'X-API-Key': apiKey }
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || '请求失败');
  }
  
  const data = await res.json();
  // 处理数据
} catch (error) {
  console.error('请求错误:', error.message);
}
```

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.2.0 | 2026-03-26 | 音色列表/查询接口改为用户隔离；新增管理员音色列表接口 |
| 1.1.0 | 2026-03-25 | 新增档案管理模块（档案CRUD、行业管理、从档案生成文案） |
| 1.0.0 | 2024-01-01 | 初始版本 |

---

## 联系方式

如有问题，请联系开发团队。
