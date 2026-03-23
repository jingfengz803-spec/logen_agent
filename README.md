# 短视频创作工具

> 🤖 基于 AI 的短视频内容创作工作流：数据抓取 → 风格分析 → 文案生成 → TTS 语音 → 视频生成

## 📋 项目简介

通过分析抖音爆款视频，使用 AI 生成同款风格的短视频脚本，并支持 TTS 语音合成和数字人视频生成。

### 核心功能

| 模块 | 功能 | 说明 |
|------|------|------|
| 📊 **数据抓取** | 抖音用户视频数据抓取 | 文案、标签、互动数据 |
| 🔍 **风格分析** | AI 分析火爆原因和风格特征 | 支持热门视频深度分析 |
| ✍️ **文案生成** | 多模型支持 | DeepSeek / 智谱 GLM |
| 🎙️ **TTS 合成** | 智谱 GLM-TTS | 内置音色 |
| 🎤 **音色复刻** | 阿里 CosyVoice | 支持自定义音色复刻 |
| 🎬 **视频生成** | 阿里 VideoRetalk | 数字人口播视频 |

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- ffmpeg（可选，用于音频/视频处理）

### 安装依赖

```bash
# 克隆项目
cd D:\pythonProject

# 安装依赖
pip install -r requirements.txt
```

### 配置环境变量

```bash
# 复制配置模板
cp longgraph/.env.example longgraph/.env

# 编辑 longgraph/.env，填入你的 API Keys
# 必需：
#   - DEEPSEEK_API_KEY (文案生成)
#   - ZAI_API_KEY (文案生成 + 智谱 TTS)
#   - DASHSCOPE_API_KEY (CosyVoice + VideoRetalk)
```

### API 获取地址

| API | 用途 | 获取地址 |
|-----|------|----------|
| DeepSeek | 文案生成 | https://platform.deepseek.com/ |
| 智谱 AI | 文案生成 + TTS | https://open.bigmodel.cn/ |
| 阿里云 DashScope | TTS + 视频生成 | https://dashscope.console.aliyun.com/ |

---

## 📁 项目结构

```
D:\pythonProject\
├── douyin_data_tool/          # 抖音数据抓取模块
│   ├── config.py              # 配置文件
│   ├── fetch_user_videos.py   # 用户视频抓取工具
│   ├── runner.py              # 抓取运行器
│   ├── collector/             # API 客户端
│   │   ├── client.py          # 请求客户端
│   │   └── parser.py          # 数据解析
│   ├── analysis/              # 数据分析
│   ├── storage/               # 数据存储
│   └── utils/                 # 工具函数
│
└── longgraph/                 # 主工作目录
    ├── .env                   # 环境变量配置
    ├── .env.example           # 配置模板
    ├── main.py                # 主入口（交互式菜单）
    ├── script_generator.py    # 文案生成模块
    ├── glm_tts.py             # 智谱 TTS 模块
    ├── cosyvoice_tts.py       # 阿里 CosyVoice TTS
    ├── video_generator.py     # VideoRetalk 视频生成
    ├── analyze_and_generate.py# 风格分析 + 脚本生成
    ├── full_workflow.py       # 完整工作流
    ├── upload_audio_helper.py # OSS 上传工具
    └── create_voice_cli.py    # 音色复刻 CLI
```

---

## 💡 使用方式

### 方式 1：交互式菜单（推荐）

```bash
cd longgraph
python main.py
```

### 方式 2：完整工作流

```bash
cd longgraph
python full_workflow.py
```

按提示输入：
1. 抖音用户主页 URL
2. 新主题
3. 音色 ID
4. 参考视频 URL（可选）

### 方式 3：代码调用

#### 文案生成

```python
from longgraph.script_generator import generate_script

result = generate_script(
    topic="律师如何应对奇葩客户",
    reference="杭州老律师月入500待客之道",
    model="deepseek"  # 或 "zhipu"
)

print(result["full_script"])      # TTS/数字人用完整台词
print(result["segments"])         # 分段台词
print(result["short_script"])     # 平台发布文案
```

#### TTS 合成（智谱）

```python
from longgraph.glm_tts import text_to_speech

text_to_speech(
    text="你好，我是黄金律师",
    voice="tongtong",  # 或 "zhiqiang"
    output_path="output.wav"
)
```

#### TTS 合成（CosyVoice 音色复刻）

```python
from longgraph.cosyvoice_tts import CosyVoiceTTSClient

client = CosyVoiceTTSClient()

# 1. 创建音色（仅需一次）
result = client.create_voice(
    audio_url="https://your-url.com/voice.mp3",
    prefix="myvoice",
    wait_ready=True
)
voice_id = result["voice_id"]

# 2. 使用复刻音色合成
client.speech(
    text="你好，这是复刻的声音",
    voice=voice_id,
    output_path="output.mp3"
)
```

#### 视频生成（VideoRetalk）

```python
from longgraph.video_generator import VideoWorkflow

workflow = VideoWorkflow()

result = workflow.generate_from_local_files(
    video_path="ref_video.mp4",  # 参考视频（人物正面镜头）
    audio_path="speech.mp3",      # 合成的音频
    output_dir="output"
)
```

---

## 🎯 输出说明

| 字段 | 用途 | 说明 |
|------|------|------|
| `segments` | TTS/数字人 | 分段台词，每段 8-15 字 |
| `full_script` | TTS/数字人 | 完整台词 |
| `tts_script` | TTS | 带停顿时间标记的台词 |
| `short_script` | 平台发布 | 带标签的发布文案 |
| `suggested_tags` | 平台发布 | 推荐话题标签 |

---

## ⚙️ 配置说明

### 抖音数据抓取

编辑 `douyin_data_tool/config.py`：

```python
HEADERS = {
    "Cookie": "你的抖音Cookie"  # 必需
}

USER_IDS = ["用户sec_user_id"]
COUNT = 10      # 每次请求数量
MAX_PAGE = 5    # 抓取页数
```

### OSS 配置（视频生成需要）

视频生成需要将文件上传到公网，需配置阿里云 OSS：

```bash
# 在 longgraph/.env 中添加
OSS_ACCESS_KEY_ID=your_access_key_id
OSS_ACCESS_KEY_SECRET=your_access_key_secret
OSS_BUCKET_NAME=your_bucket_name
OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com
```

---

## 📊 功能进度

| 模块 | 状态 | 说明 |
|------|------|------|
| 数据抓取 | ✅ | 用户视频、文案、标签 |
| 风格分析 | ✅ | AI 分析火爆原因 + 风格特征 |
| 文案生成 | ✅ | DeepSeek/智谱双模型 |
| 智谱 TTS | ✅ | 内置音色 |
| CosyVoice | ✅ | 音色复刻 + 语音合成 |
| VideoRetalk | ✅ | 数字人视频生成 |

---

## 📚 依赖包

```
python-dotenv    # 环境变量管理
requests         # 网络请求
pandas           # 数据处理
openai           # LLM API (DeepSeek/智谱)
dashscope        # 阿里云服务 (CosyVoice/VideoRetalk)
oss2             # 阿里云 OSS 上传
```

---

## 📝 更新日志

### v1.0.0 (当前)
- ✅ 抖音视频数据抓取
- ✅ AI 风格分析
- ✅ 文案生成（双模型支持）
- ✅ 智谱 TTS
- ✅ 阿里 CosyVoice 音色复刻
- ✅ 阿里 VideoRetalk 视频生成
- ✅ 完整端到端工作流

---

## 📄 许可证

MIT License
