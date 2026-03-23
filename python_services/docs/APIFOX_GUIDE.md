# 短视频创作自动化 API - Apifox 使用手册

> 适用于前端开发人员、测试人员
> 版本：v1.0.0
> 更新时间：2025-03-20

---

## 目录

1. [快速开始](#1-快速开始)
2. [导入接口文档](#2-导入接口文档)
3. [核心业务流程](#3-核心业务流程)
4. [接口详解](#4-接口详解)
5. [常见问题](#5-常见问题)

---

## 1. 快速开始

### 1.1 环境信息

```
服务器地址：http://192.168.111.22:8088
认证方式：无需认证（当前版本）
数据格式：application/json
```

### 1.2 测试连接

```bash
GET http://192.168.111.22:8088/
```

**预期响应：**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

## 2. 导入接口文档

### 2.1 导入步骤

1. 打开 Apifox
2. 点击项目设置 → 导入数据 → OpenAPI
3. 选择 `python_services/openapi.json` 文件
4. 选择「覆盖并更新」
5. 点击「确定」完成导入

### 2.2 可空字段说明

以下字段在任务未完成时为 `null`，这是正常情况：

| 字段 | 为 null 的情况 |
|------|----------------|
| `started_at` | 任务还未开始 |
| `completed_at` | 任务未完成 |
| `result` | 任务未完成或无结果 |
| `error` | 没有错误时 |

---

## 3. 核心业务流程

### 3.1 完整交互式流程

这是前端的主要使用场景，用户在每个步骤都可以进行确认或修改：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          步骤1：抖音数据抓取                             │
├─────────────────────────────────────────────────────────────────────────┤
│  用户操作：输入抖音主页URL                                               │
│  调用接口：POST /api/v1/douyin/fetch/user (wait=true)                   │
│  返回数据：视频列表（展示前10个火爆视频）                                  │
│  用户操作：查看并确认                                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                          步骤2：AI分析                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  调用接口：POST /api/v1/ai/analyze/viral (火爆原因分析)                  │
│  调用接口：POST /api/v1/ai/analyze/style (风格特征分析)                  │
│  返回数据：分析结果（展示给用户）                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                          步骤3：生成脚本                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  用户操作：输入复刻主题                                                  │
│  调用接口：POST /api/v1/ai/generate/script                              │
│  返回数据：标题、描述、标签、口播台词                                     │
│  用户操作：确认/编辑脚本                                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      步骤4：音色复刻（可提前操作）                         │
├─────────────────────────────────────────────────────────────────────────┤
│  用户操作：上传本地音频文件                                              │
│  调用接口：POST /api/v1/storage/upload/file                            │
│  返回数据：audio_url (公网URL)                                          │
│  调用接口：POST /api/v1/tts/voice/create (audio_url, wait_ready=true)   │
│  返回数据：试听音频URL + voice_id                                       │
│  用户操作：试听并确认音色效果                                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                          步骤5：TTS语音合成                             │
├─────────────────────────────────────────────────────────────────────────┤
│  用户操作：选择已创建的音色                                              │
│  调用接口：GET /api/v1/tts/voice/list (获取可用音色)                    │
│  调用接口：POST /api/v1/tts/speech (口播台词, voice_id)                 │
│  返回数据：audio_url (公网URL)                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                          步骤6：视频生成                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  用户操作：上传参考视频文件                                              │
│  调用接口：POST /api/v1/storage/upload/file                            │
│  返回数据：video_url (公网URL)                                          │
│  调用接口：POST /api/v1/video/generate (video_url, audio_url)           │
│  返回数据：最终视频文件URL                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 流程说明

| 特点 | 说明 |
|------|------|
| 🔀 分步执行 | 每个步骤独立调用，用户可控制进度 |
| ✅ 用户确认 | 关键步骤需要用户确认后继续 |
| 🔄 可回退 | 用户可以返回上一步修改内容 |
| 💾 状态保持 | 前端需要保存每步的结果，供后续使用 |

### 3.3 前端状态管理建议

```javascript
// 前端需要维护的状态
const workflowState = {
  // 步骤1：抖音数据
  douyinVideos: [],
  viralAnalysis: null,
  styleAnalysis: null,
  
  // 步骤3：生成的脚本
  script: {
    title: "",
    description: "",
    hashtags: [],
    publish_text: "",
    full_script: "",
    segments: []
  },
  
  // 步骤4：音色信息
  selectedVoice: {
    voice_id: "",
    prefix: "",
    preview_url: ""
  },
  
  // 步骤5：TTS音频
  ttsAudioUrl: "",
  
  // 步骤6：最终视频
  finalVideoUrl: ""
};
```

---

## 4. 接口详解

### 4.1 步骤1：抖音数据抓取

#### 4.1.1 抓取用户视频

```
POST /api/v1/douyin/fetch/user
```

**推荐使用同步模式（wait=true），直接返回结果：**

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| url | string | ✅ | - | 抖音用户主页URL |
| max_count | int | ❌ | 100 | 最大抓取数量 |
| enable_filter | bool | ❌ | true | 启用过滤 |
| min_likes | int | ❌ | 50 | 最小点赞数 |
| top_n | int | ❌ | 10 | 返回Top N |
| sort_by | string | ❌ | like | 排序字段 |
| **wait** | **bool** | **❌** | **false** | **true=同步等待结果（推荐）** |

**Apifox 配置：**

```json
{
  "url": "https://www.douyin.com/user/MS4wLjABAAAA...",
  "max_count": 50,
  "enable_filter": true,
  "min_likes": 100,
  "top_n": 10,
  "sort_by": "like",
  "wait": true
}
```

**同步响应（wait=true 时直接返回结果）：**

```json
{
  "code": 200,
  "message": "success",
  "task_id": "sync",
  "status": "success",
  "progress": 100,
  "result": {
    "count": 50,
    "filtered_count": 10,
    "videos": [
      {
        "video_id": "7123456789012345678",
        "title": "视频标题",
        "desc": "视频描述",
        "likes": 1500,
        "comments": 80,
        "shares": 20,
        "video_url": "https://..."
      }
    ]
  }
}
```

---

### 4.2 步骤2：AI分析

#### 4.2.1 火爆原因分析

```
POST /api/v1/ai/analyze/viral
```

**分析维度：** 话题热度、情绪共鸣、实用性、娱乐性、人设魅力、表达技巧

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| video_data | array | ✅ | 视频数据列表（从步骤1获取） |

**Apifox 配置：**

```json
{
  "video_data": [
    {
      "title": "视频标题",
      "desc": "视频描述",
      "likes": 1500,
      "comments": 80
    }
  ]
}
```

**响应示例：**

```json
{
  "code": 200,
  "task_id": "task_viral_001",
  "status": "success",
  "result": {
    "overall_score": 85,
    "dimensions": {
      "话题热度": 90,
      "情绪共鸣": 85,
      "实用性": 80,
      "娱乐性": 75,
      "人设魅力": 88,
      "表达技巧": 82
    },
    "summary": "分析总结..."
  }
}
```

---

#### 4.2.2 风格特征分析

```
POST /api/v1/ai/analyze/style
```

**分析维度：** 文案风格、视频类型、拍摄特征、高频词汇、标签策略、音乐风格

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| video_data | array | ✅ | 视频数据列表 |
| analysis_dimensions | array | ❌ | 指定分析维度 |

**响应示例：**

```json
{
  "code": 200,
  "task_id": "task_style_001",
  "status": "success",
  "result": {
    "writing_style": "轻松幽默",
    "video_type": "知识分享",
    "high_frequency_words": ["大家", "注意", "非常重要"],
    "tag_strategy": "使用3-5个相关标签",
    "music_style": "轻快背景音乐"
  }
}
```

---

### 4.3 步骤3：生成脚本

#### 4.3.1 生成TTS脚本

```
POST /api/v1/ai/generate/script
```

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| topic | string | ✅ | 用户输入的复刻主题 |
| style_analysis | object | ❌ | 风格分析结果（步骤2获取） |
| viral_analysis | object | ❌ | 火爆分析结果（步骤2获取） |
| target_duration | int | ❌ | 60 | 目标时长（秒） |

**Apifox 配置：**

```json
{
  "topic": "AI写作助手使用技巧",
  "style_analysis": {
    "writing_style": "轻松幽默",
    "video_type": "知识分享"
  },
  "viral_analysis": {
    "overall_score": 85
  },
  "target_duration": 60
}
```

**响应示例：**

```json
{
  "code": 200,
  "task_id": "task_script_001",
  "status": "success",
  "result": {
    "title": "AI写作助手使用技巧，让你效率翻倍！",
    "description": "分享3个实用的AI写作技巧",
    "hashtags": ["#AI写作", "#效率工具", "#干货分享"],
    "publish_text": "今天分享几个超实用的AI写作技巧！",
    "full_script": "大家好，今天分享几个AI写作技巧...",
    "segments": [
      "大家好，今天分享几个AI写作技巧。",
      "第一个技巧是...",
      "第二个技巧是...",
      "赶紧试试吧！"
    ]
  }
}
```

---

### 4.4 步骤4：音色复刻（含试听）

#### 4.4.1 上传音频文件

```
POST /api/v1/storage/upload/file
```

**Content-Type：** `multipart/form-data`

**Apifox 配置：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file | file | ✅ | 选择本地音频文件 |
| file_type | text | ❌ | audio |

**响应示例：**

```json
{
  "code": 200,
  "task_id": "task_upload_001",
  "status": "success",
  "result": {
    "oss_url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/audio/voice_sample.wav",
    "file_hash": "abc123...",
    "size": 56000
  }
}
```

---

#### 4.4.2 创建音色并生成试听音频（推荐）

```
POST /api/v1/tts/voice/create-with-preview
```

**流程说明：**

```
┌─────────────────────────────────────────────────────────────────┐
│  用户上传音频 → 创建音色 → 合成试听音频 → 返回试听URL         │
│                                                                  │
│  用户试听                                                        │
│     ├─ 满意 → 保存 voice_id，后续使用                            │
│     └─ 不满意 → 重新上传音频，重新调用此接口                      │
└─────────────────────────────────────────────────────────────────┘
```

**请求参数：**

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| audio_url | string | ✅ | - | 上传后得到的公网URL |
| prefix | string | ❌ | myvoice | 音色前缀 |
| model | string | ❌ | cosyvoice-v3.5-flash | TTS模型 |
| language_hints | array | ❌ | - | 语言提示 |
| preview_text | string | ❌ | "你好，这是我的音色。" | 试听文本 |
| auto_upload_oss | bool | ❌ | true | 是否自动上传试听音频到OSS |

**Apifox 配置：**

```json
{
  "audio_url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/audio/voice_sample.wav",
  "prefix": "tom",
  "model": "cosyvoice-v3.5-flash",
  "preview_text": "你好，这是我的音色。",
  "auto_upload_oss": true
}
```

**响应示例：**

```json
{
  "code": 200,
  "task_id": "task_voice_preview_001",
  "status": "success",
  "result": {
    "voice_id": "cosyvoice-v3.5-flash-tom-xxxxxxxxxx",
    "prefix": "tom",
    "model": "cosyvoice-v3.5-flash",
    "status": "OK",
    "preview_text": "你好，这是我的音色。",
    "preview_audio_url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/audio/preview_tom_123456.mp3",
    "is_available": true
  }
}
```

**字段说明：**

| 字段 | 说明 |
|------|------|
| voice_id | 音色ID，后续TTS需要用到 |
| status | 音色状态：OK=可用, DEPLOYING=审核中, UNDEPLOYED=不可用 |
| preview_audio_url | 试听音频公网URL，用户试听用 |
| is_available | 音色是否可用（status=OK时为true） |

---

#### 4.4.3 获取音色列表

```
GET /api/v1/tts/voice/list
```

**用途：** 查看所有已创建的音色，供用户选择

**响应示例：**

```json
{
  "code": 200,
  "voices": [
    {
      "voice_id": "cosyvoice-v3.5-flash-tom-xxxxxxxxxx",
      "prefix": "tom",
      "model": "cosyvoice-v3.5-flash",
      "status": "OK",
      "created_at": "2025-03-20 10:30:00",
      "is_available": true
    }
  ]
}
```

**音色状态：**

| 状态 | 是否可用 | 说明 |
|------|----------|------|
| OK | ✅ | 审核通过，可使用 |
| DEPLOYING | ❌ | 审核中 |
| UNDEPLOYED | ❌ | 审核未通过 |

---

#### 4.4.4 用户交互流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     前端页面：音色创建                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 用户点击"上传音频"按钮                                       │
│     → 调用 POST /api/v1/storage/upload/file                     │
│     → 获得 audio_url                                            │
│                                                                  │
│  2. 调用创建音色接口                                            │
│     → 调用 POST /api/v1/tts/voice/create-with-preview             │
│     → 获得 voice_id + preview_audio_url                           │
│                                                                  │
│  3. 显示试听音频播放器                                           │
│     → 用户点击试听按钮                                            │
│     → 播放 preview_audio_url                                      │
│                                                                  │
│  4. 用户选择：                                                   │
│     ┌─ 满意 → 保存 voice_id，继续下一步                           │
│     └─ 不满意 → 返回步骤1，重新上传                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

#### 4.4.5 前端集成示例

```javascript
// 音色创建组件
class VoiceCreator {
  async createVoiceWithPreview(audioFile) {
    // 步骤1：上传音频文件
    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('file_type', 'audio');
    
    const uploadResponse = await fetch('http://192.168.111.22:8088/api/v1/storage/upload/file', {
      method: 'POST',
      body: formData
    });
    const uploadData = await uploadResponse.json();
    const audioUrl = uploadData.result.oss_url;
    
    // 步骤2：创建音色并生成试听音频
    const voiceResponse = await fetch('http://192.168.111.22:8088/api/v1/tts/voice/create-with-preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        audio_url: audioUrl,
        prefix: 'myvoice',
        model: 'cosyvoice-v3.5-flash',
        preview_text: '你好，这是我的音色。',
        auto_upload_oss: true
      })
    });
    const voiceData = await voiceResponse.json();
    
    // 步骤3：返回结果
    return {
      voiceId: voiceData.result.voice_id,
      previewUrl: voiceData.result.preview_audio_url,
      isAvailable: voiceData.result.is_available,
      status: voiceData.result.status
    };
  }
  
  // 用户试听后的处理
  onUserPreview(result) {
    if (result.isAvailable) {
      // 播放试听音频
      this.audioPlayer.src = result.previewUrl;
      this.audioPlayer.play();
      
      // 显示选择按钮
      this.showSatisfactionButtons = true;
    } else {
      this.showError('音色创建失败或审核中');
    }
  }
  
  onUserSatisfied(isSatisfied, voiceId) {
    if (isSatisfied) {
      // 保存voice_id，供后续使用
      this.selectedVoiceId = voiceId;
      this.showSuccess('音色已保存，可以继续下一步');
    } else {
      // 重新上传
      this.showUploadDialog = true;
    }
  }
}
```
      "created_at": "2025-03-20 10:30:00",
      "is_available": true
    }
  ]
}
```

**音色状态：**

| 状态 | 是否可用 | 说明 |
|------|----------|------|
| OK | ✅ | 审核通过，可使用 |
| DEPLOYING | ❌ | 审核中 |
| UNDEPLOYED | ❌ | 审核未通过 |

---

### 4.5 步骤5：TTS语音合成

#### 4.5.1 文字转语音

```
POST /api/v1/tts/speech
```

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| text | string | ✅ | 完整口播台词 |
| voice_id | string | ✅ | 用户选择的音色ID |
| output_format | string | ❌ | mp3 | 输出格式 |

**Apifox 配置：**

```json
{
  "text": "大家好，今天分享几个AI写作技巧。第一个技巧是使用AI辅助生成大纲。第二个技巧是利用AI进行内容润色。第三个技巧是使用AI检查语法错误。赶紧试试吧！",
  "voice_id": "cosyvoice-v3.5-flash-tom-xxxxxxxxxx",
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
    "audio_url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/audio/output_20250320.mp3",
    "duration": 18.5,
    "size": 296000
  }
}
```

---

#### 4.5.2 分段文字转语音（可选）

```
POST /api/v1/tts/speech/segments
```

**用途：** 将分段台词分别生成多个音频文件

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| segments | array | ✅ | 分段台词数组 |
| voice_id | string | ✅ | 音色ID |

**Apifox 配置：**

```json
{
  "segments": [
    "大家好，今天分享几个AI写作技巧。",
    "第一个技巧是使用AI辅助生成大纲。",
    "第二个技巧是利用AI进行内容润色。",
    "第三个技巧是使用AI检查语法错误。",
    "赶紧试试吧！"
  ],
  "voice_id": "cosyvoice-v3.5-flash-tom-xxxxxxxxxx"
}
```

**响应示例：**

```json
{
  "code": 200,
  "task_id": "task_tts_segments_001",
  "status": "success",
  "result": {
    "segment_urls": [
      "https://.../segment_001.mp3",
      "https://.../segment_002.mp3",
      "https://.../segment_003.mp3",
      "https://.../segment_004.mp3",
      "https://.../segment_005.mp3"
    ],
    "count": 5
  }
}
```

---

### 4.6 步骤6：视频生成

#### 4.6.1 上传参考视频

```
POST /api/v1/storage/upload/file
```

**同步骤4的音频上传，将 file_type 设为 video**

---

#### 4.6.2 生成口型同步视频

```
POST /api/v1/video/generate
```

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| video_url | string | ✅ | 参考视频公网URL |
| audio_url | string | ✅ | TTS生成的音频公网URL |
| ref_image_url | string | ❌ | 参考图片URL（可选） |
| resolution | string | ❌ | 分辨率，如 1280x720 |

**Apifox 配置：**

```json
{
  "video_url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/videos/ref.mp4",
  "audio_url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/audio/output_20250320.mp3",
  "resolution": "1280x720"
}
```

**响应示例：**

```json
{
  "code": 200,
  "task_id": "task_video_001",
  "status": "running",
  "progress": 0
}
```

---

#### 4.6.3 查询视频生成进度

```
GET /api/v1/video/task/{task_id}
```

**进行中的响应：**

```json
{
  "task_id": "task_video_001",
  "status": "running",
  "progress": 45,
  "message": "正在处理..."
}
```

**完成的响应：**

```json
{
  "task_id": "task_video_001",
  "status": "success",
  "progress": 100,
  "video_url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/videos/output_20250320.mp4"
}
```

---

### 4.7 其他辅助接口

#### 4.7.1 获取上传记录

```
GET /api/v1/storage/records?file_type=audio
```

**用途：** 查看已上传的文件记录

---

#### 4.7.2 根据Hash获取URL

```
GET /api/v1/storage/url/{file_hash}
```

**用途：** 如果已知文件hash，可直接获取公网URL

---

#### 4.7.3 获取OSS配置状态

```
GET /api/v1/storage/config/status
```

**用途：** 检查OSS是否正确配置

---

## 5. 常见问题

### Q1: 同步模式 vs 异步模式？

**A:** 
- **同步模式（wait=true）**: 请求会等待任务完成，直接返回结果。适合耗时较短的操作。
- **异步模式（wait=false）**: 立即返回 task_id，需要轮询查询结果。适合耗时较长的操作。

**推荐：**
- 抖音抓取：使用 `wait=true`（通常1-3分钟）
- 音色创建：使用 `wait_ready=true`（通常1-3分钟）
- TTS合成：使用异步模式（几秒到几十秒）
- 视频生成：使用异步模式（5-15分钟）

---

### Q2: 音色创建失败怎么办？

**A:** 常见原因：
1. 音频文件不符合要求（需要10-20秒，清晰无杂音）
2. 网络问题导致音频URL无法访问
3. 音频格式不支持（推荐WAV格式）

**解决方案：**
- 确保音频是10-20秒的清晰人声
- 使用WAV格式而非MP3
- 确保上传后得到的URL可公网访问

---

### Q3: 视频生成失败怎么办？

**A:** 常见原因：
1. 参考视频和音频时长差异过大
2. 视频或音频URL无法访问
3. 参考视频格式不支持

**解决方案：**
- 确保参考视频时长 > 音频时长
- 使用MP4格式的参考视频
- 检查URL是否可公网访问

---

### Q4: 如何取消正在进行的任务？

**A:** 使用 DELETE 方法：

```
DELETE /api/v1/video/task/{task_id}
DELETE /api/v1/workflow/task/{task_id}
```

---

### Q5: 音色状态一直是 DEPLOYING？

**A:** 音色审核通常需要1-3分钟：
1. 等待几分钟后重新查询
2. 如果超过10分钟仍是 DEPLOYING，可能是审核失败
3. 尝试重新创建音色

---

### Q6: 前端需要保存哪些数据？

**A:** 建议保存以下数据供后续使用：

| 步骤 | 需要保存的数据 | 用途 |
|------|---------------|------|
| 步骤1 | video_data | AI分析输入 |
| 步骤2 | viral_analysis, style_analysis | 脚本生成输入 |
| 步骤3 | script (完整脚本) | TTS输入 |
| 步骤4 | voice_id | TTS输入 |
| 步骤5 | audio_url | 视频生成输入 |

---

### Q7: 响应中的 request_id 有什么用？

**A:** request_id 用于日志追踪：
- 遇到问题时记录下 request_id
- 提供给后端开发人员
- 后端可通过 request_id 查找详细日志

---

## 附录

### A. 接口清单

| 分类 | 接口 | 用途 |
|------|------|------|
| 抖音 | POST /api/v1/douyin/fetch/user | 抓取用户视频 |
| 抖音 | GET /api/v1/douyin/task/{task_id} | 查询抓取任务 |
| AI | POST /api/v1/ai/analyze/viral | 火爆原因分析 |
| AI | POST /api/v1/ai/analyze/style | 风格特征分析 |
| AI | POST /api/v1/ai/generate/script | 生成脚本 |
| TTS | GET /api/v1/tts/voice/list | 获取音色列表 |
| TTS | POST /api/v1/tts/voice/create | 创建音色复刻 |
| TTS | POST /api/v1/tts/speech | 文字转语音 |
| TTS | POST /api/v1/tts/speech/segments | 分段转语音 |
| TTS | GET /api/v1/tts/task/{task_id} | 查询TTS任务 |
| 视频 | POST /api/v1/storage/upload/file | 上传文件 |
| 视频 | POST /api/v1/video/generate | 生成视频 |
| 视频 | GET /api/v1/video/task/{task_id} | 查询视频任务 |

---

### B. 错误码

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

### C. 前端集成示例

```javascript
// 完整流程示例
class VideoCreationWorkflow {
  constructor() {
    this.state = {
      douyinVideos: [],
      analysis: null,
      script: null,
      voiceId: null,
      audioUrl: null,
      videoUrl: null
    };
  }
  
  // 步骤1：抓取抖音数据
  async fetchDouyinVideos(url) {
    const response = await fetch('http://192.168.111.22:8088/api/v1/douyin/fetch/user', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: url,
        max_count: 50,
        enable_filter: true,
        min_likes: 100,
        top_n: 10,
        wait: true  // 同步等待
      })
    });
    const data = await response.json();
    this.state.douyinVideos = data.result.videos;
    return data.result;
  }
  
  // 步骤2：AI分析
  async analyzeVideos(videos) {
    const viralResponse = await fetch('http://192.168.111.22:8088/api/v1/ai/analyze/viral', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_data: videos })
    });
    const viralData = await viralResponse.json();
    
    const styleResponse = await fetch('http://192.168.111.22:8088/api/v1/ai/analyze/style', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_data: videos })
    });
    const styleData = await styleResponse.json();
    
    this.state.analysis = {
      viral: viralData.result,
      style: styleData.result
    };
    return this.state.analysis;
  }
  
  // 步骤3：生成脚本
  async generateScript(topic) {
    const response = await fetch('http://192.168.111.22:8088/api/v1/ai/generate/script', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic: topic,
        style_analysis: this.state.analysis?.style,
        viral_analysis: this.state.analysis?.viral,
        target_duration: 60
      })
    });
    const data = await response.json();
    this.state.script = data.result;
    return data.result;
  }
  
  // 步骤4：创建音色
  async createVoice(file) {
    // 先上传文件
    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type', 'audio');
    
    const uploadResponse = await fetch('http://192.168.111.22:8088/api/v1/storage/upload/file', {
      method: 'POST',
      body: formData
    });
    const uploadData = await uploadResponse.json();
    const audioUrl = uploadData.result.oss_url;
    
    // 创建音色
    const voiceResponse = await fetch('http://192.168.111.22:8088/api/v1/tts/voice/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        audio_url: audioUrl,
        prefix: 'myvoice',
        wait_ready: true
      })
    });
    const voiceData = await voiceResponse.json();
    this.state.voiceId = voiceData.result.voice_id;
    return voiceData.result;
  }
  
  // 步骤5：TTS合成
  async synthesizeSpeech(text) {
    const response = await fetch('http://192.168.111.22:8088/api/v1/tts/speech', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: text,
        voice_id: this.state.voiceId,
        output_format: 'mp3'
      })
    });
    const data = await response.json();
    this.state.audioUrl = data.result.audio_url;
    return data.result;
  }
  
  // 步骤6：生成视频
  async generateVideo(refVideoFile) {
    // 上传参考视频
    const formData = new FormData();
    formData.append('file', refVideoFile);
    formData.append('file_type', 'video');
    
    const uploadResponse = await fetch('http://192.168.111.22:8088/api/v1/storage/upload/file', {
      method: 'POST',
      body: formData
    });
    const uploadData = await uploadResponse.json();
    const videoUrl = uploadData.result.oss_url;
    
    // 生成视频
    const response = await fetch('http://192.168.111.22:8088/api/v1/video/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_url: videoUrl,
        audio_url: this.state.audioUrl
      })
    });
    const data = await response.json();
    
    // 轮询等待完成
    while (data.status === 'running') {
      await new Promise(resolve => setTimeout(resolve, 5000));
      const statusResponse = await fetch(`http://192.168.111.22:8088/api/v1/video/task/${data.task_id}`);
      const statusData = await statusResponse.json();
      if (statusData.status === 'success') {
        this.state.videoUrl = statusData.video_url;
        return statusData;
      }
    }
  }
}

// 使用示例
const workflow = new VideoCreationWorkflow();

// 按步骤执行
await workflow.fetchDouyinVideos('https://www.douyin.com/user/...');
await workflow.analyzeVideos(workflow.state.douyinVideos);
await workflow.generateScript('AI写作技巧');
// 用户上传音频文件后
await workflow.createVoice(audioFile);
await workflow.synthesizeSpeech(workflow.state.script.full_script);
// 用户上传参考视频后
await workflow.generateVideo(refVideoFile);
```

---

**文档版本：v1.0.0**  
**更新时间：2025-03-20**  
**技术支持：后端开发团队**
