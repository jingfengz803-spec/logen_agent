# 短视频创作自动化系统 - 架构文档

## 项目概述

本项目是一个完整的短视频创作自动化系统，实现从**对标账号分析**到**AI生成视频**的全流程自动化。

### 核心工作流

```
用户输入抖音主页链接
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  阶段1: 数据抓取 (douyin_data_tool)                          │
│  - 视频列表抓取                                              │
│  - 文案/标签提取                                             │
│  - 互动数据统计                                              │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  阶段2: AI分析与脚本生成 (longgraph/analyze_and_generate)   │
│  - 火爆原因分析（话题热度、情绪共鸣、实用性等）               │
│  - 风格特征分析（文案风格、拍摄特征、高频词汇）               │
│  - TTS台词生成（含分段、时长估算）                           │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  阶段3: 音色克隆与语音合成 (longgraph/cosyvoice_tts)        │
│  - 音色上传到OSS获取公网URL                                  │
│  - CosyVoice音色复刻                                        │
│  - 语音合成（完整版+分段）                                   │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  阶段4: 视频生成 (longgraph/video_generator)                 │
│  - 参考视频上传到OSS                                         │
│  - 合成音频上传到OSS                                        │
│  - VideoRetalk口型对接                                      │
│  - 视频下载与保存                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 模块架构

### 1. douyin_data_tool - 抖音数据抓取模块

#### 目录结构
```
douyin_data_tool/
├── __init__.py
├── config.py              # 配置文件（Cookie、过滤条件等）
├── runner.py              # 运行入口（用户/话题/热榜模式）
├── fetch_user_videos.py   # 用户主页抓取
├── diagnose.py            # 诊断工具
├── analysis/
│   ├── __init__.py
│   └── hot_score.py       # 热度评分算法
├── collector/
│   ├── __init__.py
│   ├── client.py          # API请求客户端
│   └── parser.py          # 数据解析器
├── storage/
│   ├── __init__.py
│   ├── save_csv.py        # CSV导出
│   └── save_json.py       # JSON导出
└── utils/
    ├── __init__.py
    ├── url_parser.py      # URL解析工具
    └── logger.py          # 日志工具
```

#### 核心类

| 类名 | 文件 | 功能 |
|------|------|------|
| `DouyinUserFetcher` | fetch_user_videos.py | 用户视频抓取器 |
| `fetch_videos()` | collector/client.py | 调用抖音API获取视频列表 |
| `parse_aweme_list()` | collector/parser.py | 解析API返回数据 |
| `hot_score()` | analysis/hot_score.py | 计算视频热度分 |

#### 数据过滤配置 (config.py)
```python
FILTER_MAX_DAYS = 10000      # 最大天数
FILTER_MIN_LIKE = 50         # 最小点赞数
FILTER_MIN_COMMENT = 1       # 最小评论数
FILTER_TARGET_COUNT = 100    # 目标采集数量
```

#### 输出数据格式
```json
{
  "aweme_id": "视频ID",
  "desc": "视频文案",
  "desc_clean": "清理后文案",
  "create_time": 1699999999,
  "create_time_str": "2023-11-15 10:00:00",
  "author": "作者昵称",
  "author_id": "作者ID",
  "like_count": 10000,
  "comment_count": 500,
  "share_count": 200,
  "play_count": 50000,
  "hashtags": ["#标签1", "#标签2"],
  "hashtag_count": 2,
  "music": "背景音乐",
  "duration": 18.5,
  "video_url": "视频链接"
}
```

---

### 2. longgraph/analyze_and_generate - AI分析与脚本生成模块

#### 目录结构
```
longgraph/
├── analyze_and_generate.py  # 主模块
├── script_generator.py       # 脚本生成器
└── config.py                 # LLM配置
```

#### 核心类

| 类名 | 功能 |
|------|------|
| `DouyinFetcher` | 通过subprocess调用douyin_data_tool抓取数据 |
| `VideoStyleAnalyzer` | 视频风格分析器（火爆原因+风格特征） |

#### 分析维度

**火爆原因分析 (analyze_viral_factors)**
- 话题热度（是否踩中热点、话题普适性、新颖度）
- 情绪共鸣（触发情绪、对比反转、代入感）
- 实用性（信息价值、痛点解决、收藏转发价值）
- 娱乐性（趣味性、创意、悬念反转）
- 人设魅力（人设特点、辨识度、契合度）
- 表达技巧（钩子类型、节奏特点、互动引导）

**风格特征分析 (analyze_videos)**
- 文案风格（字数、语气、表达方式、标点习惯）
- 视频类型（日常vlog/对口型/剧情/展示类）
- 拍摄特征（场景、人物状态、镜头特点）
- 高频词汇与句式模板
- 标签策略
- 音乐风格

**TTS台词生成 (generate_tts_script)**
- 完整版台词（带节奏标记）
- 分段台词（便于分段合成）
- 视频标题/描述
- 话题标签
- 发布文案

#### 输出格式
```json
{
  "视频标题": "标题",
  "视频描述": "描述",
  "话题标签": ["#标签1", "#标签2"],
  "发布文案": "可直接复制发布的文案",
  "TTS台词": {
    "完整版": "完整台词内容",
    "分段": ["分段1", "分段2", "分段3"],
    "字数": 120,
    "预估时长": 25
  }
}
```

---

### 3. longgraph/cosyvoice_tts - 音色克隆与语音合成模块

#### 目录结构
```
longgraph/
├── cosyvoice_tts.py       # CosyVoice TTS客户端
├── glm_tts.py             # 智谱TTS备用方案
├── create_voice_cli.py    # 音色复刻CLI工具
└── data/
    └── voices.txt         # 已保存的音色ID
```

#### 核心类

| 类名 | 功能 |
|------|------|
| `CosyVoiceTTSClient` | 阿里云CosyVoice客户端 |
| `create_voice()` | 创建音色复刻 |
| `query_voice()` | 查询音色状态 |
| `list_voices()` | 列出所有音色 |
| `speech()` | 语音合成 |
| `speech_from_segments()` | 分段语音合成 |

#### CosyVoice 模型
| 模型 | 说明 |
|------|------|
| cosyvoice-v3.5-flash | 快速（推荐） |
| cosyvoice-v3.5-plus | 高质量 |
| cosyvoice-v3-flash | 标准版 |
| cosyvoice-v1 | 第一代 |

#### 音色状态
- `DEPLOYING`: 审核中
- `OK`: 可用
- `UNDEPLOYED`: 审核未通过

---

### 4. longgraph/upload_audio_helper - OSS文件上传模块

#### 核心类

| 类名 | 功能 |
|------|------|
| `OSSUploader` | 阿里云OSS文件上传器 |

#### OSS配置 (.env)
```bash
OSS_ACCESS_KEY_ID=your_access_key_id
OSS_ACCESS_KEY_SECRET=your_access_key_secret
OSS_BUCKET_NAME=your_bucket_name
OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com
```

#### 上传流程
1. 读取本地文件
2. 上传到OSS Bucket
3. 设置公共读权限
4. 返回公网URL

---

### 5. longgraph/video_generator - 视频生成模块

#### 目录结构
```
longgraph/
└── video_generator.py     # VideoRetalk客户端
```

#### 核心类

| 类名 | 功能 |
|------|------|
| `VideoPreprocessor` | 视频预处理（分辨率调整） |
| `VideoRetalkClient` | 阿里云VideoRetalk客户端 |
| `VideoWorkflow` | 完整视频生成工作流 |

#### 视频预处理
- 分辨率范围: 640-2048
- 默认分辨率: 1280x720
- 自动保持宽高比
- 使用ffmpeg处理

#### VideoRetalk 参数
| 参数 | 说明 |
|------|------|
| video_url | 参考视频公网URL |
| audio_url | 待合成音频公网URL |
| ref_image_url | 参考图片公网URL（可选） |
| video_extension | 是否扩展视频以匹配音频长度 |

---

### 6. longgraph/full_workflow - 完整工作流整合

#### 核心函数

| 函数 | 功能 |
|------|------|
| `full_workflow()` | 抓取→分析→TTS（不含视频生成） |
| `full_workflow_with_video()` | 抓取→分析→TTS→视频生成 |

#### 工作流步骤
```
【步骤1/6】抓取视频数据
【步骤2/6】AI分析（火爆原因+风格特征）
【步骤3/6】生成TTS台词
【步骤4/6】TTS语音合成
【步骤5/6】视频生成（可选）
【步骤6/6】保存结果
```

---

## 配置文件说明

### 环境变量 (.env)
```bash
# ========== LLM API Keys ==========
DEEPSEEK_API_KEY=sk-xxx                    # DeepSeek API（文案生成）
ZAI_API_KEY=xxx                            # 智谱AI API（文案生成+TTS备用）
DASHSCOPE_API_KEY=sk-xxx                   # 阿里DashScope（CosyVoice+VideoRetalk）

# ========== OSS 配置 ==========
OSS_ACCESS_KEY_ID=xxx                      # 阿里云OSS AccessKey
OSS_ACCESS_KEY_SECRET=xxx                  # 阿里云OSS Secret
OSS_BUCKET_NAME=xxx                        # OSS Bucket名称
OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com  # OSS访问域名

# ========== 抖音配置 ==========
DOUYYIN_COOKIE=xxx                         # 抖音Cookie（用于数据抓取）
```

### longgraph/config.py 配置类

| 配置类 | 说明 |
|--------|------|
| `APIKeys` | 统一API密钥管理 |
| `LLMModel` | 大语言模型配置（DeepSeek/智谱） |
| `TTSConfig` | TTS配置（CosyVoice/智谱TTS） |
| `VideoConfig` | 视频生成配置（VideoRetalk） |
| `Paths` | 文件路径配置 |
| `DouyinConfig` | 抖音数据抓取配置 |

---

## 数据流图

```
┌──────────────────────────────────────────────────────────────────────┐
│                          用户输入                                     │
│  抖音主页URL | 新主题 | 音色文件 | 参考视频                          │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    douyin_data_tool                                  │
│  输出: user_videos_data.json                                         │
│  - aweme_id, desc, hashtags, like_count, comment_count, etc.        │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  analyze_and_generate                                │
│  输出: 火爆原因分析 + 风格分析 + TTS台词                              │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    OSS上传 + CosyVoice                               │
│  音色文件 → OSS URL → create_voice() → voice_id                      │
│  TTS台词 + voice_id → speech() → full.mp3 + segments/               │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    OSS上传 + VideoRetalk                             │
│  参考视频 → OSS URL                                                  │
│  full.mp3 → OSS URL                                                  │
│  video_url + audio_url → VideoRetalk → 最终视频.mp4                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 使用场景

### 场景1: 完整流程（含视频生成）
```bash
cd longgraph
python full_workflow.py
# 按提示输入: 抖音URL、主题、音色ID、参考视频URL
```

### 场景2: 仅分析与TTS
```bash
cd longgraph
python -c "
from full_workflow import full_workflow
full_workflow(
    url='https://www.douyin.com/user/MS4wLjABAAAA...',
    topic='如何应对职场PUA',
    voice_id='cosyvoice-v3.5-flash-niro-xxx'
)
"
```

### 场景3: 音色复刻
```bash
cd longgraph
python create_voice_cli.py
# 选择: 1. 创建新音色
# 输入音频URL（需先通过 upload_audio_helper.py 上传）
```

### 场景4: 上传本地音色/视频到OSS
```bash
cd longgraph
python upload_audio_helper.py /path/to/voice.mp3
python upload_audio_helper.py /path/to/ref_video.mp4
```

---

## 功能完善度评估

### ✅ 已实现功能

| 功能模块 | 完成度 | 说明 |
|---------|--------|------|
| 抖音数据抓取 | ✅ 100% | 支持用户/话题/热榜三种模式 |
| URL解析 | ✅ 100% | 自动解析用户主页URL |
| 数据过滤 | ✅ 100% | 按天数/点赞/评论过滤 |
| 火爆原因分析 | ✅ 100% | 6维度内容层面分析 |
| 风格特征分析 | ✅ 100% | 文案+视频风格提取 |
| TTS台词生成 | ✅ 100% | 含分段、时长估算 |
| CosyVoice音色克隆 | ✅ 100% | 支持多模型、状态查询 |
| 语音合成 | ✅ 100% | 完整版+分段合成 |
| OSS文件上传 | ✅ 100% | 音频/视频上传 |
| 视频预处理 | ✅ 100% | 分辨率自动调整 |
| VideoRetalk对接 | ✅ 100% | 异步任务+状态轮询 |
| 完整工作流 | ✅ 100% | 一键端到端生成 |

### ⚠️ 可改进功能

| 模块 | 改进点 | 优先级 |
|------|--------|--------|
| 错误处理 | API失败重试机制 | 中 |
| 用户体验 | 进度条可视化 | 低 |
| 批量处理 | 多用户/多主题并行 | 中 |
| 音质优化 | 音频预处理（降噪） | 低 |
| 质量评估 | 生成结果自动评分 | 低 |
| 缓存机制 | 分析结果缓存 | 中 |

### 🔧 建议补充细节

1. **Cookie自动更新机制**
   - 当前Cookie需手动更新
   - 建议: 添加Cookie失效检测和自动刷新提示

2. **生成结果预览**
   - 当前直接保存到文件
   - 建议: 添加终端内结果预览

3. **视频质量检查**
   - 当前VideoRetalk结果直接下载
   - 建议: 添加生成质量检查和重试机制

4. **成本统计**
   - 当前无API调用统计
   - 建议: 添加Token/费用统计

---

## 依赖项

### 核心依赖
```
# 数据抓取
requests

# AI分析
openai
dashscope

# OSS上传
oss2
python-dotenv

# 音视频处理
ffmpeg (系统依赖)
```

### 安装命令
```bash
pip install -r requirements.txt
```

---

## 常见问题

### Q1: 抖音Cookie如何获取？
A: 
1. 打开浏览器，访问 douyin.com
2. 按F12打开开发者工具
3. 切换到Network标签
4. 刷新页面，找到任意请求
5. 复制请求头中的Cookie字段

### Q2: CosyVoice音色审核需要多久？
A: 通常1-5分钟，审核通过后状态变为"OK"

### Q3: VideoRetalk视频生成需要多久？
A: 取决于视频长度，通常1-3分钟

### Q4: 支持哪些视频格式？
A: 
- 音频: mp3, wav, m4a
- 视频: mp4（其他格式需ffmpeg转换）

---

## 文件清单

### 核心模块
```
douyin_data_tool/
├── config.py
├── runner.py
├── fetch_user_videos.py
├── collector/client.py
├── collector/parser.py
└── utils/url_parser.py

longgraph/
├── config.py
├── analyze_and_generate.py
├── script_generator.py
├── cosyvoice_tts.py
├── glm_tts.py
├── create_voice_cli.py
├── upload_audio_helper.py
├── video_generator.py
└── full_workflow.py
```

### 数据目录
```
longgraph/data/
├── audio/           # 音频文件
├── output/          # 输出文件
└── voices.txt       # 音色ID记录
```

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2024-11 | 初始版本，实现基础工作流 |
| 1.1 | 2024-12 | 添加VideoRetalk视频生成 |
| 1.2 | 2025-01 | 添加完整工作流整合 |
