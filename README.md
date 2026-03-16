# 文案生成与TTS合成工具

> 🤖 基于DeepSeek/智谱AI的短视频内容创作工具

## 📋 项目简介

通过参考爆款视频文案，使用AI生成同款风格的短视频脚本，并支持TTS语音合成。

### 核心功能

1. **📊 数据抓取** - 抓取抖音用户视频数据（文案+标签）
2. **✍️ 文案生成** - 多模型支持（DeepSeek/智谱GLM）
3. **🎙️ TTS合成** - 智谱GLM-TTS语音合成
4. **📱 平台发布** - 生成带标签的发布文案

## 🚀 快速开始

### 环境要求

- Python 3.8+
- DeepSeek 或 智谱AI API Key

### 配置环境变量

在 `longgraph/.env` 文件中设置：

```env
# 智谱AI (文案生成 + TTS)
ZAI_API_KEY=your_zhipuai_api_key

# DeepSeek (文案生成)
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### 安装依赖

```bash
pip install python-dotenv requests zai openai
```

## 📁 项目结构

```
D:\pythonProject\
├── douyin_data_tool/          # 抖音数据抓取
│   ├── config.py              # 配置文件
│   ├── fetch_user_videos.py   # 用户视频抓取工具
│   ├── collector/             # API客户端
│   ├── parser.py              # 数据解析（含标签提取）
│   └── utils/                 # URL解析工具
│
└── longgraph/                 # 主工作目录
    ├── .env                   # 环境变量
    ├── main.py                # 主入口（交互式菜单）
    ├── script_generator.py    # 文案生成模块
    └── glm_tts.py             # TTS合成模块
```

## 💡 使用方式

### 方式1：交互式菜单

```bash
cd longgraph
python main.py
```

### 方式2：代码调用

```python
# 文案生成
from longgraph.script_generator import generate_script

result = generate_script(
    topic="律师如何应对奇葩客户",
    reference="杭州老律师月入500待客之道",
    model="deepseek"  # 或 "zhipu"
)

print(result["full_script"])      # 完整台词
print(result["segments"])         # 分段台词
print(result["short_script"])     # 发布文案
print(result["suggested_tags"])   # 推荐标签
```

```python
# TTS合成
from longgraph.glm_tts import text_to_speech

text_to_speech(
    text="你好，我是黄金律师",
    voice="tongtong",
    output_path="output.wav"
)
```

```python
# 一键生成：文案 + 语音
from longgraph.glm_tts import generate_speech

result = generate_speech(
    topic="律师如何应对奇葩客户",
    reference="杭州老律师月入500待客之道",
    voice="tongtong"
)

print(result["audio_file"])  # 音频文件路径
```

### 方式3：从用户URL生成

```bash
# 1. 抓取用户视频数据
cd douyin_data_tool
python fetch_user_videos.py "用户主页URL" --max 100 --output json

# 2. 使用抓取的数据生成文案
cd ../longgraph
python -c "
from script_generator import generate_script
result = generate_script(
    topic='新主题',
    reference='从抓取数据中复制的文案'
)
print(result['full_script'])
"
```

## 🎯 输出说明

| 字段 | 用途 | 说明 |
|------|------|------|
| `segments` | TTS/数字人 | 分段台词，每段8-15字 |
| `full_script` | TTS/数字人 | 完整台词 |
| `tts_script` | TTS | 带停顿时间标记的台词 |
| `short_script` | 平台发布 | 带标签的发布文案 |
| `suggested_tags` | 平台发布 | 推荐话题标签 |

## 🔧 配置说明

### 抖音数据抓取

编辑 `douyin_data_tool/config.py`：

```python
HEADERS = {
    "Cookie": "你的抖音Cookie"  # 必须设置
}

# 抓取配置
USER_IDS = ["用户sec_user_id"]
COUNT = 10  # 每次请求数量
MAX_PAGE = 5  # 抓取页数
```

### API配置

| API | 用途 | 获取地址 |
|-----|------|----------|
| ZAI_API_KEY | 文案生成 + TTS | https://open.bigmodel.cn/ |
| DEEPSEEK_API_KEY | 文案生成 | https://platform.deepseek.com/ |

## 📊 功能进度

| 模块 | 状态 | 说明 |
|------|------|------|
| 数据抓取 | ✅ | 用户视频、文案、标签 |
| 文案生成 | ✅ | DeepSeek/智谱双模型 |
| TTS合成 | ✅ | 智谱GLM-TTS |
| 数字人生成 | ⏳ | 待接入 |

## 📚 依赖包

```
python-dotenv    # 环境变量
requests        # 网络请求
zai             # 智谱AI SDK
openai          # OpenAI兼容接口
```
