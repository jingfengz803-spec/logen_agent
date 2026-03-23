# 短视频创作自动化 API 文档

> 版本：v1.0.0
> 基础URL：`http://192.168.111.22:8088`

## 目录

- [通用说明](#通用说明)
- [系统接口](#系统接口)
- [抖音数据抓取](#抖音数据抓取)
- [AI分析与脚本生成](#ai分析与脚本生成)
- [TTS语音合成](#tts语音合成)
- [视频生成](#视频生成)
- [完整工作流](#完整工作流)
- [存储服务](#存储服务)

---

## 通用说明

### 统一响应格式

所有接口返回的 JSON 响应都包含以下字段：

```json
{
  "code": 200,
  "message": "success",
  "request_id": "req_xxxxx"
}
```

### 任务状态

异步任务接口会返回 `task_id`，状态值如下：

| 状态 | 说明 |
|------|------|
| `pending` | 等待执行 |
| `running` | 执行中 |
| `success` | 执行成功 |
| `failed` | 执行失败 |
| `cancelled` | 已取消 |

### 查询任务状态

```bash
GET /api/v1/{module}/task/{task_id}
```

---

## 系统接口

### 健康检查

```bash
GET /
```

**响应示例：**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

## 抖音数据抓取

### 1. 抓取用户视频

```bash
POST /api/v1/douyin/fetch/user
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| url | string | 是 | - | 抖音用户主页URL |
| max_count | int | 否 | 100 | 最大抓取数量 (1-200) |
| enable_filter | bool | 否 | false | 是否启用过滤 |
| min_likes | int | 否 | 50 | 最小点赞数 |
| min_comments | int | 否 | 0 | 最小评论数 |
| top_n | int | 否 | 0 | 返回Top N热门视频 (0=全部) |
| sort_by | string | 否 | like | 排序字段 (like/comment/share) |
| wait | bool | 否 | false | 是否等待完成同步返回结果 |

**请求示例：**
```json
{
  "url": "https://www.douyin.com/user/MS4wLjABAAAA...",
  "max_count": 50,
  "enable_filter": true,
  "min_likes": 100,
  "wait": false
}
```

**响应示例：**
```json
{
  "code": 200,
  "message": "success",
  "task_id": "task_abc123",
  "status": "running",
  "progress": 0,
  "request_id": "req_xyz"
}
```

---

### 2. 查询抓取任务状态

```bash
GET /api/v1/douyin/task/{task_id}
```

**响应示例：**
```json
{
  "code": 200,
  "task_id": "task_abc123",
  "status": "success",
  "progress": 100,
  "result": {
    "count": 50,
    "videos": [...]
  }
}
```

---

### 3. 抓取话题视频

```bash
POST /api/v1/douyin/fetch/topic
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| topic | string | 是 | - | 话题名称 |
| max_count | int | 否 | 50 | 最大抓取数量 |

**请求示例：**
```json
{
  "topic": "AI绘画",
  "max_count": 30
}
```

---

### 4. 抓取抖音热榜

```bash
POST /api/v1/douyin/fetch/hotlist
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| cate_id | string | 否 | - | 分类ID |

---

### 5. 获取缓存视频数据

```bash
GET /api/v1/douyin/videos?limit=100&offset=0
```

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| limit | int | 否 | 100 | 返回数量限制 |
| offset | int | 否 | 0 | 偏移量 |

**响应示例：**
```json
{
  "code": 200,
  "data": [...],
  "total": 150,
  "filtered_count": 100
}
```

---

## AI分析与脚本生成

### 1. 火爆原因分析

```bash
POST /api/v1/ai/analyze/viral
```

**分析维度：**
- 话题热度
- 情绪共鸣
- 实用性
- 娱乐性
- 人设魅力
- 表达技巧

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| video_data | array | 是 | 视频数据列表 |
| video_ids | array | 否 | 视频ID列表 |

**请求示例：**
```json
{
  "video_data": [
    {
      "title": "视频标题",
      "desc": "视频描述",
      "likes": 1000,
      "comments": 50
    }
  ]
}
```

---

### 2. 风格特征分析

```bash
POST /api/v1/ai/analyze/style
```

**分析维度：**
- 文案风格
- 视频类型
- 拍摄特征
- 高频词汇
- 标签策略
- 音乐风格

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| video_data | array | 是 | 视频数据列表 |
| analysis_dimensions | array | 否 | 分析维度列表 |

---

### 3. 生成TTS脚本

```bash
POST /api/v1/ai/generate/script
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| topic | string | 是 | - | 新主题 |
| style_analysis | object | 否 | - | 风格分析结果 |
| viral_analysis | object | 否 | - | 火爆分析结果 |
| target_duration | int | 否 | 60 | 目标时长（秒） |

**响应示例：**
```json
{
  "result": {
    "title": "视频标题",
    "description": "视频描述",
    "hashtags": ["#标签1", "#标签2"],
    "publish_text": "发布文案",
    "full_script": "完整台词...",
    "segments": ["分段1", "分段2"]
  }
}
```

---

### 4. 完整分析流程

```bash
POST /api/v1/ai/analyze/full
```

**一键完成：**
1. 从抖音URL抓取视频数据
2. 进行火爆原因分析
3. 进行风格特征分析
4. 生成新主题脚本

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| douyin_url | string | 是 | - | 抖音用户主页URL |
| topic | string | 是 | - | 新主题 |
| max_videos | int | 否 | 50 | 分析视频数量 |
| enable_viral_analysis | bool | 否 | true | 是否进行火爆分析 |
| enable_style_analysis | bool | 否 | true | 是否进行风格分析 |
| generate_script | bool | 否 | true | 是否生成脚本 |
| target_duration | int | 否 | 60 | 目标时长（秒） |

**请求示例：**
```json
{
  "douyin_url": "https://www.douyin.com/user/MS4wLjABAAAA...",
  "topic": "AI写作助手使用技巧",
  "max_videos": 50
}
```

---

### 5. 查询AI任务状态

```bash
GET /api/v1/ai/task/{task_id}
```

---

## TTS语音合成

### 1. 获取音色列表

```bash
GET /api/v1/tts/voice/list
```

**说明：** 从阿里云API获取所有已创建的音色及其状态

**响应示例：**
```json
{
  "code": 200,
  "message": "success",
  "request_id": "req_xyz",
  "voices": [
    {
      "voice_id": "cosyvoice-v3.5-flash-niro-8cc614e161c44abe8621eadddb2e4a11",
      "prefix": "niro",
      "model": "cosyvoice-v3.5-flash",
      "status": "OK",
      "created_at": "2025-03-20 10:30:00",
      "is_available": true
    },
    {
      "voice_id": "cosyvoice-v3.5-flash-otto-4ff2a472101d4b0cb71734837a0d0f86",
      "prefix": "otto",
      "model": "cosyvoice-v3.5-flash",
      "status": "OK",
      "created_at": "2025-03-19 15:20:00",
      "is_available": true
    }
  ]
}
```

**音色状态：**
- `OK` - 审核通过，可调用
- `DEPLOYING` - 审核中
- `UNDEPLOYED` - 审核不通过，不可调用

---

### 2. 查询单个音色状态

```bash
GET /api/v1/tts/voice/{voice_id}
```

**路径参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| voice_id | string | 是 | 音色ID |

---

### 3. 创建音色复刻

```bash
POST /api/v1/tts/voice/create
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| audio_url | string | 是 | - | 音色音频公网URL |
| prefix | string | 否 | myvoice | 音色前缀（仅数字和小写字母，小于10个字符） |
| model | string | 否 | cosyvoice-v3.5-flash | TTS模型 |
| language_hints | array | 否 | ["zh"] | 语言提示 |
| wait_ready | bool | 否 | true | 是否等待音色就绪 |

**请求示例：**
```json
{
  "audio_url": "https://your-oss-bucket.oss-cn-hangzhou.aliyuncs.com/audio/voice_sample.wav",
  "prefix": "niro",
  "model": "cosyvoice-v3.5-flash",
  "wait_ready": true
}
```

---

### 4. 文字转语音

```bash
POST /api/v1/tts/speech
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| text | string | 是 | - | 要合成的文本 |
| voice_id | string | 是 | - | 音色ID |
| model | string | 否 | - | TTS模型（可选） |
| output_format | string | 否 | mp3 | 输出格式 |

**请求示例：**
```json
{
  "text": "大家好，欢迎收听今天的节目。",
  "voice_id": "cosyvoice-v3.5-flash-niro-8cc614e161c44abe8621eadddb2e4a11",
  "output_format": "mp3"
}
```

**响应示例：**
```json
{
  "code": 200,
  "task_id": "task_tts_001",
  "status": "success",
  "result": {
    "audio_url": "https://your-oss-bucket.oss-cn-hangzhou.aliyuncs.com/audio/output.mp3",
    "duration": 3.5,
    "size": 56000
  }
}
```

---

### 5. 分段文字转语音

```bash
POST /api/v1/tts/speech/segments
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| segments | array | 是 | 分段文本列表 |
| voice_id | string | 是 | 音色ID |
| model | string | 否 | TTS模型 |
| output_format | string | 否 | 输出格式 |

**请求示例：**
```json
{
  "segments": [
    "大家好，欢迎收听今天的节目。",
    "今天我们要聊的话题是AI写作助手。",
    "希望能给大家带来一些有用的信息。"
  ],
  "voice_id": "cosyvoice-v3.5-flash-niro-8cc614e161c44abe8621eadddb2e4a11"
}
```

---

### 6. TTS脚本转语音

```bash
POST /api/v1/tts/script
```

**同时生成完整版和分段音频**

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| full_text | string | 是 | 完整台词 |
| segments | array | 是 | 分段台词 |
| voice_id | string | 是 | 音色ID |
| model | string | 否 | TTS模型 |

**请求示例：**
```json
{
  "full_text": "大家好，欢迎收听今天的节目。今天我们要聊的话题是AI写作助手。希望能给大家带来一些有用的信息。",
  "segments": [
    "大家好，欢迎收听今天的节目。",
    "今天我们要聊的话题是AI写作助手。",
    "希望能给大家带来一些有用的信息。"
  ],
  "voice_id": "cosyvoice-v3.5-flash-niro-8cc614e161c44abe8621eadddb2e4a11"
}
```

**响应示例：**
```json
{
  "result": {
    "full_audio_url": "https://.../full.mp3",
    "segment_urls": [
      "https://.../segment_001.mp3",
      "https://.../segment_002.mp3",
      "https://.../segment_003.mp3"
    ]
  }
}
```

---

### 7. 查询TTS任务状态

```bash
GET /api/v1/tts/task/{task_id}
```

---

## 视频生成

### 1. 生成口型同步视频

```bash
POST /api/v1/video/generate
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| video_url | string | 是 | - | 参考视频公网URL |
| audio_url | string | 是 | - | 合成音频公网URL |
| ref_image_url | string | 否 | - | 参考图片URL |
| video_extension | bool | 否 | true | 是否扩展视频以匹配音频长度 |
| resolution | string | 否 | - | 分辨率（如1280x720） |

**请求示例：**
```json
{
  "video_url": "https://your-oss-bucket.oss-cn-hangzhou.aliyuncs.com/videos/ref.mp4",
  "audio_url": "https://your-oss-bucket.oss-cn-hangzhou.aliyuncs.com/audio/output.mp3",
  "resolution": "1280x720"
}
```

---

### 2. 查询视频生成任务状态

```bash
GET /api/v1/video/task/{task_id}
```

**响应示例：**
```json
{
  "task_id": "task_video_001",
  "status": "success",
  "progress": 100,
  "video_url": "https://your-oss-bucket.oss-cn-hangzhou.aliyuncs.com/videos/output.mp4"
}
```

---

### 3. 取消视频生成任务

```bash
DELETE /api/v1/video/task/{task_id}
```

---

## 完整工作流

### 1. 运行完整工作流

```bash
POST /api/v1/workflow/run
```

**工作流步骤：**
1. 抓取抖音视频数据
2. AI分析（火爆原因 + 风格特征）
3. 生成新主题脚本
4. TTS语音合成
5. 视频生成（可选）

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| douyin_url | string | 是 | - | 抖音用户主页URL |
| topic | string | 是 | - | 新主题 |
| voice_id | string | 否 | - | 音色ID（可选） |
| ref_video_url | string | 否 | - | 参考视频URL（可选） |
| workflow_type | string | 否 | without_video | 工作流类型 |
| max_videos | int | 否 | 50 | 分析视频数量 |
| output_name | string | 否 | - | 输出文件名前缀 |

**workflow_type 可选值：**
- `analysis_only` - 仅分析
- `without_video` - 不含视频
- `full` - 完整流程（含视频）

**请求示例：**
```json
{
  "douyin_url": "https://www.douyin.com/user/MS4wLjABAAAA...",
  "topic": "AI写作助手使用技巧",
  "workflow_type": "without_video",
  "voice_id": "cosyvoice-v3.5-flash-niro-8cc614e161c44abe8621eadddb2e4a11",
  "max_videos": 50
}
```

---

### 2. 查询工作流任务状态

```bash
GET /api/v1/workflow/task/{task_id}
```

**响应示例：**
```json
{
  "task_id": "task_workflow_001",
  "status": "running",
  "progress": 45,
  "current_step": "AI分析中",
  "result": {
    "videos_fetched": 50,
    "analysis_complete": true
  }
}
```

**current_step 可能值：**
- 待处理
- 抓取抖音数据
- AI分析中
- 生成脚本
- TTS合成
- 生成视频

---

### 3. 取消工作流任务

```bash
DELETE /api/v1/workflow/task/{task_id}
```

---

### 4. 获取工作流模板

```bash
GET /api/v1/workflow/templates
```

**响应示例：**
```json
{
  "code": 200,
  "data": [
    {
      "id": "quick",
      "name": "快速分析",
      "description": "仅进行AI分析和脚本生成",
      "workflow_type": "analysis_only",
      "max_videos": 50
    },
    {
      "id": "standard",
      "name": "标准流程",
      "description": "分析+脚本+TTS",
      "workflow_type": "without_video",
      "max_videos": 100
    },
    {
      "id": "full",
      "name": "完整流程",
      "description": "分析+脚本+TTS+视频",
      "workflow_type": "full",
      "max_videos": 100,
      "requires_voice": true,
      "requires_ref_video": true
    }
  ]
}
```

---

## 存储服务

### 1. 上传文件到OSS

```bash
POST /api/v1/storage/upload/file
```

**Content-Type:** `multipart/form-data`

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 要上传的文件 |
| file_type | string | 否 | 文件类型（audio/video/image） |

**请求示例（curl）：**
```bash
curl -X POST http://192.168.111.22:8088/api/v1/storage/upload/file \
  -F "file=@/path/to/audio.wav" \
  -F "file_type=audio"
```

---

### 2. 通过路径上传文件到OSS

```bash
POST /api/v1/storage/upload/path
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| file_path | string | 是 | - | 本地文件路径 |
| file_type | string | 否 | - | 文件类型 |
| force_reupload | bool | 否 | false | 是否强制重新上传 |
| custom_object_name | string | 否 | - | 自定义OSS对象名 |

**请求示例：**
```json
{
  "file_path": "/data/audio/voice_sample.wav",
  "file_type": "audio"
}
```

---

### 3. 批量上传文件

```bash
POST /api/v1/storage/upload/batch
```

**Content-Type:** `multipart/form-data`

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| files | file[] | 是 | 要上传的文件列表 |
| file_type | string | 否 | 文件类型 |

---

### 4. 查询上传任务状态

```bash
GET /api/v1/storage/upload/task/{task_id}
```

---

### 5. 获取上传记录

```bash
GET /api/v1/storage/records?file_type=audio
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file_type | string | 否 | 过滤文件类型（audio/video/image） |

**响应示例：**
```json
{
  "code": 200,
  "data": [
    {
      "file_path": "/data/audio/sample.wav",
      "file_hash": "abc123...",
      "oss_url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/audio/sample.wav",
      "file_type": "audio",
      "size": 56000,
      "uploaded_at": "2025-03-20T10:30:00",
      "last_accessed_at": "2025-03-20T15:20:00"
    }
  ],
  "total": 25
}
```

---

### 6. 根据hash获取文件URL

```bash
GET /api/v1/storage/url/{file_hash}
```

**路径参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file_hash | string | 是 | 文件MD5 hash |

**响应示例：**
```json
{
  "code": 200,
  "data": {
    "oss_url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/audio/sample.wav",
    "file_hash": "abc123..."
  }
}
```

---

### 7. 获取OSS配置状态

```bash
GET /api/v1/storage/config/status
```

**响应示例：**
```json
{
  "code": 200,
  "configured": true,
  "records_count": 25,
  "temp_dir": "/path/to/temp",
  "records_file": "/path/to/records.json"
}
```

---

### 8. 清理过期记录

```bash
POST /api/v1/storage/records/cleanup?days=7
```

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| days | int | 否 | 7 | 保留天数 |

**响应示例：**
```json
{
  "code": 200,
  "message": "已清理 5 条过期记录",
  "data": {
    "cleaned_count": 5,
    "days": 7
  }
}
```

---

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

**错误响应示例：**
```json
{
  "code": 400,
  "message": "参数错误：url不能为空",
  "request_id": "req_xyz"
}
```

---

## 前端集成示例

### 使用 Fetch API

```javascript
// 抓取抖音用户视频
async function fetchDouyinVideos(url) {
  const response = await fetch('http://192.168.111.22:8088/api/v1/douyin/fetch/user', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      url: url,
      max_count: 50,
      wait: false
    })
  });
  
  const data = await response.json();
  return data;
}

// 查询任务状态
async function getTaskStatus(taskId) {
  const response = await fetch(`http://192.168.111.22:8088/api/v1/douyin/task/${taskId}`);
  const data = await response.json();
  return data;
}

// 轮询任务直到完成
async function pollTask(taskId) {
  while (true) {
    const result = await getTaskStatus(taskId);
    
    if (result.status === 'success') {
      return result.result;
    } else if (result.status === 'failed') {
      throw new Error(result.error);
    }
    
    // 等待2秒后重试
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}
```

### 使用 Axios

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://192.168.111.22:8088',
  headers: {
    'Content-Type': 'application/json'
  }
});

// 获取音色列表
async function getVoices() {
  const { data } = await api.get('/api/v1/tts/voice/list');
  return data.voices;
}

// 文字转语音
async function textToSpeech(text, voiceId) {
  const { data } = await api.post('/api/v1/tts/speech', {
    text: text,
    voice_id: voiceId,
    output_format: 'mp3'
  });
  return data;
}

// 上传文件
async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('file_type', 'audio');
  
  const { data } = await api.post('/api/v1/storage/upload/file', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
  return data;
}
```

---

## 联系方式

如有问题，请联系后端开发团队。
