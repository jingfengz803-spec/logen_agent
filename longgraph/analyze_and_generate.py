"""
视频火爆原因分析 + 风格分析 + 脚本生成工具
功能：
1. 抓取主页100个视频
2. 分析火爆原因（内容层面：话题热度、情绪共鸣、实用性、娱乐性）
3. 分析风格（文案+视频模板）
4. 生成可复刻的脚本（含视频描述、镜头、动作、文案、标签）
5. 生成TTS复刻台词（供cosyvoice_tts模块使用）
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# 导入统一配置（当前项目的 config.py）
from config import LLMModel, DouyinConfig, Paths, APIKeys
from openai import OpenAI


class DouyinFetcher:
    """抖音视频数据抓取器 - 通过subprocess调用douyin_data_tool"""
    
    def __init__(self, max_videos: int = 100, enable_filter: bool = False):
        self.max_videos = max_videos
        self.enable_filter = enable_filter
        self.tool_dir = os.path.join(os.path.dirname(__file__), '..', 'douyin_data_tool')
    
    def fetch_from_url(self, url: str) -> List[Dict[str, Any]]:
        """从用户主页URL抓取视频数据"""
        # 先检查是否有已保存的数据
        json_file = os.path.join(self.tool_dir, "user_videos_data.json")

        # 尝试从已保存的数据读取
        videos = self._load_saved_data(json_file)

        if videos:
            print(f"✓ 从已保存的数据中读取到 {len(videos)} 个视频")
            return videos[:self.max_videos]

        # 没有缓存，调用真正的抓取器
        print(f"⚠️ 未找到缓存数据，开始实时抓取: {url}")
        try:
            sys.path.insert(0, self.tool_dir)
            from fetch_user_videos import DouyinUserFetcher

            fetcher = DouyinUserFetcher(
                max_videos=self.max_videos,
                enable_filter=self.enable_filter
            )
            videos = fetcher.fetch_from_url(url)

            if videos:
                # 保存到缓存文件
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(videos, f, ensure_ascii=False, indent=2)
                print(f"✓ 抓取完成，已缓存 {len(videos)} 个视频到 {json_file}")
            else:
                print("⚠️ 抓取完成但未获取到视频数据，请检查 Cookie 是否有效")

            return videos
        except Exception as e:
            print(f"❌ 抓取失败: {e}")
            print("请检查: 1) Cookie 是否有效 (douyin_data_tool/config.py)  2) 网络连接是否正常")
            return []
    
    def _load_saved_data(self, json_file: str) -> List[Dict[str, Any]]:
        """从已保存的文件加载数据"""
        if not os.path.exists(json_file):
            return []

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and 'videos' in data:
                    return data['videos']
        except Exception as e:
            print(f"⚠️ 读取缓存文件失败: {e}")

        return []


class VideoStyleAnalyzer:
    """视频风格分析器 - 分析多个视频，提取风格特征和拍摄模板"""

    def __init__(self, model: str = "deepseek", timeout: float = 120.0):
        """
        Args:
            model: 文案生成模型 ("deepseek" 或 "zhipu")
            timeout: API 请求超时时间（秒），默认 120 秒
        """
        config = LLMModel.get_model_config(model)

        self.client = OpenAI(
            api_key=config["api_key"](),
            base_url=config["base_url"],
            timeout=timeout  # 添加超时设置
        )
        self.model_name = config["model"]

    def analyze_videos(self, videos: List[Dict[str, Any]], top_n: int = 30) -> Dict[str, Any]:
        """
        分析视频列表，提取风格特征和拍摄模板

        Args:
            videos: 视频数据列表（从 fetch_user_videos 获取）
            top_n: 分析热度最高的 N 个视频

        Returns:
            Dict: 风格分析结果
        """
        # 按点赞数排序，取 top_n
        sorted_videos = sorted(videos, key=lambda x: x.get("like_count", 0), reverse=True)[:top_n]

        # 提取文案和标签
        video_data = []
        for v in sorted_videos:
            desc = v.get("desc", "").strip()
            if desc:
                video_data.append({
                    "文案": desc,
                    "点赞": v.get("like_count", 0),
                    "评论": v.get("comment_count", 0),
                    "标签": [t for t in v.get("hashtags", []) if t],
                    "音乐": v.get("music", ""),
                    "时长": f"{v.get('duration', 0):.1f}秒" if v.get('duration') else ""
                })

        if not video_data:
            return {"error": "没有找到有效文案"}

        # 构建分析 prompt
        prompt = f"""你是一位专业的短视频内容分析师。请分析以下 {len(video_data)} 个热门视频，提取风格特征和拍摄模板。

【视频数据】
{json.dumps(video_data, ensure_ascii=False, indent=2)}

【分析要求】
请从以下维度深度分析：

1. **文案风格**
   - 长度特征（平均/最长/最短字数）
   - 语气特点（轻松/严肃/幽默/感性/自嘲等）
   - 表达方式（短句/长句、口语化程度）
   - 标点习惯（是否用感叹号、省略号等）

2. **视频类型推测**
   - 根据文案推测视频内容类型（日常vlog/对口型/剧情/展示类等）
   - 拍摄场景（室内/室外/特定场所）
   - 人物状态（坐/立/走/躺等）

3. **高频词汇与句式**
   - 提取特色高频词
   - 识别常用句式模板

4. **标签策略**
   - 常用话题标签类型
   - 标签数量规律

5. **音乐选择**
   - 根据文案推测音乐风格

6. **复刻模板**
   - 给出3-5个可复刻的视频模板（含场景、动作、文案类型）

【输出格式】
请以JSON格式返回：
{{
    "风格总结": "一句话概括整体风格",
    "文案特征": {{
        "平均字数": 数字,
        "字数范围": "X-Y字",
        "语气": "xxx",
        "表达方式": "xxx",
        "标点习惯": "xxx"
    }},
    "视频类型": "xxx",
    "拍摄特征": {{
        "场景": "xxx",
        "人物状态": "xxx",
        "镜头特点": "xxx"
    }},
    "高频词汇": ["词1", "词2", ...],
    "句式模板": ["模板1", "模板2", ...],
    "常用标签": ["#标签1", "#标签2", ...],
    "音乐风格": "xxx",
    "复刻模板": [
        {{
            "模板名称": "xxx",
            "场景": "xxx",
            "动作": "xxx",
            "镜头": "xxx",
            "文案类型": "xxx",
            "示例": "xxx"
        }}
    ],
    "复刻建议": ["建议1", "建议2", "建议3"]
}}

直接返回JSON："""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是专业的短视频内容分析师，擅长从大量数据中提取风格特征和拍摄模板。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            # 添加基础统计
            result["分析视频数"] = len(video_data)
            result["总点赞数"] = sum(v.get("点赞", 0) for v in video_data)
            result["平均点赞"] = result["总点赞数"] // len(video_data) if video_data else 0

            return result

        except Exception as e:
            return {"error": str(e)}

    def analyze_viral_factors(self, videos: List[Dict[str, Any]], top_n: int = 20) -> Dict[str, Any]:
        """
        分析视频火爆原因 - 内容层面分析

        Args:
            videos: 视频数据列表
            top_n: 分析热度最高的 N 个视频

        Returns:
            Dict: 火爆原因分析结果
        """
        # 按点赞数排序，取 top_n
        sorted_videos = sorted(videos, key=lambda x: x.get("like_count", 0), reverse=True)[:top_n]

        # 提取数据
        video_data = []
        for v in sorted_videos:
            desc = v.get("desc", "").strip()
            if desc:
                video_data.append({
                    "文案": desc,
                    "点赞": v.get("like_count", 0),
                    "评论": v.get("comment_count", 0),
                    "收藏": v.get("collect_count", 0),
                    "转发": v.get("share_count", 0),
                    "标签": [t for t in v.get("hashtags", []) if t],
                })

        if not video_data:
            return {"error": "没有找到有效文案"}

        # 计算互动数据
        total_likes = sum(v["点赞"] for v in video_data)
        avg_likes = total_likes // len(video_data) if video_data else 0
        total_comments = sum(v["评论"] for v in video_data)

        prompt = f"""你是一位专业的短视频内容分析师，擅长分析视频火爆的原因。请从**内容层面**分析以下 {len(video_data)} 个热门视频火爆的原因。

【视频数据】
{json.dumps(video_data, ensure_ascii=False, indent=2)}

【统计数据】
- 分析视频数：{len(video_data)}
- 总点赞数：{total_likes:,}
- 平均点赞：{avg_likes:,}
- 总评论数：{total_comments:,}

【分析要求】
请从以下**内容层面**深度分析火爆原因：

1. **话题热度**
   - 是否踩中当前热门话题/社会热点
   - 话题的普适性（大众关心程度）
   - 话题的新颖程度

2. **情绪共鸣**
   - 触发什么情绪（开心/感动/愤怒/焦虑/共鸣等）
   - 是否有强烈的情绪对比/反转
   - 是否让用户产生"这就是我"的感觉

3. **实用性**
   - 是否提供有价值的信息/技巧/知识
   - 是否解决用户痛点
   - 是否有收藏/转发价值

4. **娱乐性**
   - 是否有趣好笑
   - 是否有创意/新鲜感
   - 是否有悬念/反转

5. **人设魅力**
   - 主角人设特点
   - 人设的辨识度和记忆点
   - 人设与内容的契合度

6. **表达技巧**
   - 文案的钩子（开头吸引人的技巧）
   - 节奏感（短句、押韵、重复等）
   - 互动引导（引导评论/点赞/转发）

【输出格式】
请以JSON格式返回：
{{
    "火爆原因总结": "一句话总结为什么这些视频能火",
    "核心驱动因素": ["因素1", "因素2", "因素3"],
    "维度分析": {{
        "话题热度": {{
            "评估": "高/中/低",
            "说明": "具体说明",
            "相关话题": ["话题1", "话题2"]
        }},
        "情绪共鸣": {{
            "主要情绪": "xxx",
            "评估": "强/中/弱",
            "说明": "具体说明",
            "触发技巧": ["技巧1", "技巧2"]
        }},
        "实用性": {{
            "评估": "高/中/低",
            "说明": "具体说明",
            "价值类型": "知识/技巧/情感/娱乐"
        }},
        "娱乐性": {{
            "评估": "高/中/低",
            "说明": "具体说明",
            "趣味元素": ["元素1", "元素2"]
        }},
        "人设魅力": {{
            "人设特点": "xxx",
            "记忆点": "xxx",
            "说明": "具体说明"
        }},
        "表达技巧": {{
            "钩子类型": "xxx",
            "节奏特点": "xxx",
            "互动引导": "xxx"
        }}
    }},
    "可复刻的成功要素": ["要素1", "要素2", "要素3", "要素4"],
    "避坑指南": ["不要1", "不要2", "不要3"]
}}

直接返回JSON："""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是专业的短视频内容分析师，擅长分析视频火爆的内容层面原因。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            # 添加基础统计
            result["分析视频数"] = len(video_data)
            result["总点赞数"] = total_likes
            result["平均点赞"] = avg_likes
            result["总评论数"] = total_comments

            return result

        except Exception as e:
            return {"error": str(e)}

    def generate_script(
        self,
        style_analysis: Dict[str, Any],
        topic: str,
        count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        根据风格分析结果，生成完整的复刻脚本

        Args:
            style_analysis: 风格分析结果
            topic: 新主题
            count: 生成数量

        Returns:
            List[Dict]: 完整的脚本列表
        """
        # 构建生成 prompt
        prompt = f"""你是一位专业的短视频脚本创作专家。请根据风格分析，创作可复刻的短视频脚本。

【风格分析】
{json.dumps(style_analysis, ensure_ascii=False, indent=2)}

【新主题】
{topic}

【要求】
1. 严格遵循风格特征（字数、语气、表达方式）
2. 使用高频词汇和句式模板
3. 参考复刻模板设计视频内容
4. 生成 {count} 个不同的脚本
5.文案完整版字数必须严格控制在 200~400 字之间，不得少于200字
【输出格式】
请以JSON格式返回，每个脚本包含完整的复刻信息：
{{
    "脚本列表": [
        {{
            "视频描述": {{
                "场景": "具体场景描述",
                "人物动作": "具体动作描述",
                "镜头运动": "推/拉/摇/移/跟/固定等",
                "景别": "全景/中景/近景/特写",
                "时长": "X秒"
            }},
            "文案": {{
                "分段": ["短句1", "短句2", "短句3"],
                "完整版": "完整文案",
                "字数": 数字
            }},
            "标签": ["#标签1", "#标签2", "#标签3"],
            "音乐建议": "音乐风格描述",
            "发布文案": "带标签的完整发布文案"
        }}
    ]
}}

直接返回JSON："""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是专业的短视频脚本创作专家，擅长创作可复刻的完整脚本。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            return result.get("脚本列表", [])

        except Exception as e:
            return [{"error": str(e)}]

    def format_script_for_display(self, script: Dict[str, Any], index: int) -> str:
        """格式化脚本用于显示"""
        output = []
        output.append(f"\n{'='*60}")
        output.append(f"【脚本 {index}】")
        output.append("="*60)

        # 视频描述
        video_desc = script.get("视频描述", {})
        if video_desc:
            output.append(f"\n📹 视频拍摄指南")
            output.append(f"   场景: {video_desc.get('场景', 'N/A')}")
            output.append(f"   动作: {video_desc.get('人物动作', 'N/A')}")
            output.append(f"   镜头: {video_desc.get('景别', 'N/A')} + {video_desc.get('镜头运动', 'N/A')}")
            output.append(f"   时长: {video_desc.get('时长', 'N/A')}")

        # 文案
        content = script.get("文案", {})
        if content:
            output.append(f"\n🎤 文案内容")
            segments = content.get("分段", [])
            if segments:
                for i, seg in enumerate(segments, 1):
                    output.append(f"   {i}. {seg}")
            output.append(f"\n   完整版: {content.get('完整版', '')}")
            output.append(f"   字数: {content.get('字数', 'N/A')}")

        # 其他信息
        tags = script.get("标签", [])
        if tags:
            output.append(f"\n🏷️  标签: {' '.join(tags)}")

        music = script.get("音乐建议", "")
        if music:
            output.append(f"   🎵 音乐: {music}")

        publish = script.get("发布文案", "")
        if publish:
            output.append(f"\n📱 发布文案（可直接复制）")
            output.append(f"   {publish}")

        return "\n".join(output)

    def full_analysis(self, videos: List[Dict[str, Any]], top_n: int = 30) -> Dict[str, Any]:
        """
        完整分析：火爆原因 + 风格特征

        Args:
            videos: 视频数据列表
            top_n: 分析热度最高的 N 个视频

        Returns:
            Dict: 包含火爆分析和风格分析的完整结果
        """
        print("📊 正在进行火爆原因分析...")
        try:
            viral_analysis = self.analyze_viral_factors(videos, top_n=top_n)
            print("✓ 火爆原因分析完成")
        except Exception as e:
            print(f"❌ 火爆分析出错: {e}")
            viral_analysis = {"error": str(e)}

        print("📊 正在进行风格特征分析...")
        try:
            style_analysis = self.analyze_videos(videos, top_n=top_n)
            print("✓ 风格特征分析完成")
        except Exception as e:
            print(f"❌ 风格分析出错: {e}")
            style_analysis = {"error": str(e)}

        return {
            "火爆原因分析": viral_analysis,
            "风格特征分析": style_analysis
        }

    def generate_tts_script(
        self,
        style_analysis: Dict[str, Any],
        viral_analysis: Dict[str, Any],
        topic: str,
        target_duration: float = 20.0
    ) -> Dict[str, Any]:
        """
        生成TTS复刻台词 - 结合风格分析和火爆分析

        Args:
            style_analysis: 风格分析结果
            viral_analysis: 火爆分析结果
            topic: 新主题
            target_duration: 目标时长（秒）

        Returns:
            Dict: TTS台词和发布信息
        """
        # 提取关键信息
        style_summary = style_analysis.get("风格总结", "")
        tone = style_analysis.get("文案特征", {}).get("语气", "轻松幽默")
        high_freq_words = style_analysis.get("高频词汇", [])
        sentence_patterns = style_analysis.get("句式模板", [])
        common_tags = style_analysis.get("常用标签", [])

        viral_factors = viral_analysis.get("核心驱动因素", [])
        viral_dimensions = viral_analysis.get("维度分析", {})
        success_factors = viral_analysis.get("可复刻的成功要素", [])

        # 计算目标字数和段数（按正常语速约3-3.5字/秒）
        target_words = int(target_duration * 3.5)
        target_words_min = int(target_duration * 3)
        # 按每段8-12字计算需要的段数
        min_segments = max(6, target_words_min // 12)  # 至少6段
        max_segments = target_words_min // 8 + 2  # 按最短每段8字计算

        prompt = f"""你是一位专业的短视频文案创作专家。请根据火爆原因分析和风格特征分析，生成两套内容。

【火爆原因分析】
火爆总结: {viral_analysis.get('火爆原因总结', '')}
核心驱动因素: {', '.join(viral_factors)}
可复刻成功要素: {', '.join(success_factors)}

维度分析:
{json.dumps(viral_dimensions, ensure_ascii=False, indent=2)}

【风格特征分析】
风格总结: {style_summary}
语气: {tone}
高频词汇: {', '.join(high_freq_words[:10])}
句式模板: {', '.join(sentence_patterns[:5])}
常用标签: {', '.join(common_tags[:10])}

【新主题】
{topic}

【目标时长】
{target_duration}秒（TTS完整台词需要约{target_words_min}-{target_words}字）

---

## 第一部分：抖音发布信息（简短版）
用于发布在抖音上的标题、描述、标签，保持简洁：
- 视频标题：8-15字，吸睛
- 视频描述：30-50字，概括亮点
- 话题标签：5-8个（必须从"常用标签"中选择，不能编造新标签！）

## 第二部分：TTS完整台词（长篇版）
这是交给TTS生成语音的完整台词，**必须根据目标时长生成足够长的内容**。

⚠️⚠️⚠️ **重要：TTS台词必须严格达到字数要求！** ⚠️⚠️⚠️
- 目标：{target_words_min}-{target_words}字
- 分成{min_segments}-{max_segments}个短句
- 每句8-15字，确保一口气能说完

**TTS台词要求：**
1. **字数硬性要求：完整版必须是{target_words_min}-{target_words}字！少一个字都不行！**
2. 严格遵循风格特征的语气和表达方式
3. 使用高频词汇和句式模板
4. 完整的叙事结构：
   * 开头：钩子吸引注意力（{min(3, min_segments//3)}句）
   * 中间：情节展开，有起伏（{min_segments-6}到{max_segments-6}句）
   * 结尾：记忆点或互动引导（{min(3, min_segments//3)}句）
5. 可以是讲故事、说经历、讲观点等形式
6. 内容要充实，不能空洞重复
7. 使用口语化表达（呢、吧、啊、哦）
8. **禁止编造不相关的话题标签！只能使用分析中提取的常用标签！**

**写作技巧：**
- 多用细节描述，让内容更丰富
- 可以举例子、打比方
- 可以加入场景描述
- 可以加入人物对话
- 可以加入心理活动

【输出格式】
请以JSON格式返回：
{{
    "视频标题": "吸睛标题（8-15字）",
    "视频描述": "内容简介（30-50字）",
    "TTS台词": {{
        "分段": ["短句1", "短句2", ..., "短句{min_segments}"],
        "完整版": "完整TTS台词，必须达到{target_words_min}字以上，用于语音合成",
        "字数": 数字（必须是{target_words_min}-{target_words}之间）,
        "预估时长": 秒数
    }},
    "话题标签": ["#标签1", "#标签2", ...],  // 必须从常用标签中选择！
    "发布文案": "标题\\n\\n描述\\n\\n标签1 标签2...",
    "复刻要点": ["要点1", "要点2", "要点3"]
}}

⚠️⚠️⚠️ **最后强调：**
1. TTS台词"完整版"必须是{target_words_min}-{target_words}字！这是硬性要求！
2. 话题标签必须从"常用标签"中选择，不能编造！
⚠️⚠️⚠️

直接返回JSON："""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是专业的短视频文案创作专家，擅长创作火爆的TTS台词。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            # 添加停顿标记供TTS使用
            segments = result.get("TTS台词", {}).get("分段", [])
            result["TTS台词"]["带停顿标记"] = self._add_pause_markers(segments)

            # 验证字数是否符合要求
            full_script = result.get("TTS台词", {}).get("完整版", "")
            actual_char_count = len(full_script)
            
            # 如果字数不符合要求，尝试重新生成（最多2次）
            if actual_char_count < target_words_min:
                print(f"⚠️ 字数不足：{actual_char_count}字，要求{target_words_min}-{target_words}字，正在重新生成...")
                for retry in range(2):
                    retry_prompt = prompt + f"\n\n⚠️ 上次生成的字数是{actual_char_count}字，不足！请确保完整版TTS台词达到{target_words_min}-{target_words}字！"
                    
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {"role": "system", "content": "你是专业的短视频文案创作专家，擅长创作火爆的TTS台词。"},
                            {"role": "user", "content": retry_prompt}
                        ],
                        temperature=0.8,
                        response_format={"type": "json_object"}
                    )
                    
                    result_text = response.choices[0].message.content
                    result = json.loads(result_text)
                    full_script = result.get("TTS台词", {}).get("完整版", "")
                    actual_char_count = len(full_script)
                    
                    if actual_char_count >= target_words_min:
                        print(f"✓ 重新生成成功：{actual_char_count}字")
                        break
                else:
                    print(f"⚠️ 多次重试后字数仍不足：{actual_char_count}字，使用当前结果")

            # 添加停顿标记
            segments = result.get("TTS台词", {}).get("分段", [])
            result["TTS台词"]["带停顿标记"] = self._add_pause_markers(segments)
            
            # 添加实际字数和预估时长
            result["TTS台词"]["实际字数"] = actual_char_count
            result["TTS台词"]["实际预估时长"] = round(actual_char_count / 3.5, 1)
            result["TTS台词"]["目标字数范围"] = f"{target_words_min}-{target_words}"
            
            # 验证并过滤话题标签（只保留常用标签中的）
            result_tags = result.get("话题标签", [])
            if common_tags and result_tags:
                # 创建允许的标签集合（去掉#号）
                allowed_tags = set(tag.lstrip('#') for tag in common_tags)
                # 过滤标签
                filtered_tags = []
                for tag in result_tags:
                    tag_clean = tag.lstrip('#')
                    if tag_clean in allowed_tags:
                        filtered_tags.append(tag)
                    else:
                        print(f"⚠️ 过滤掉非分析标签: {tag}")
                result["话题标签"] = filtered_tags if filtered_tags else common_tags[:5]
                result["原始标签"] = result_tags  # 保留原始记录用于调试

            return result

        except Exception as e:
            return {"error": str(e)}

    def _add_pause_markers(self, segments: List[str]) -> str:
        """添加停顿标记，便于TTS合成"""
        processed = []
        for seg in segments:
            # 替换标点为停顿标记
            seg = seg.replace("，", "，[0.2]")
            seg = seg.replace("。", "。[0.5]")
            seg = seg.replace("！", "！[0.5]")
            seg = seg.replace("？", "？[0.5]")
            processed.append(seg)
        return " [1.0] ".join(processed)

    def format_viral_analysis_for_display(self, viral_analysis: Dict[str, Any]) -> str:
        """格式化火爆分析结果用于显示"""
        output = []
        output.append("\n" + "=" * 60)
        output.append("🔥 火爆原因分析")
        output.append("=" * 60)

        if "error" in viral_analysis:
            output.append(f"\n❌ 分析失败: {viral_analysis['error']}")
            return "\n".join(output)

        output.append(f"\n📊 数据统计")
        output.append(f"   分析视频数: {viral_analysis.get('分析视频数', 0)}")
        output.append(f"   总点赞数: {viral_analysis.get('总点赞数', 0):,}")
        output.append(f"   平均点赞: {viral_analysis.get('平均点赞', 0):,}")

        output.append(f"\n💡 火爆总结")
        output.append(f"   {viral_analysis.get('火爆原因总结', 'N/A')}")

        core_factors = viral_analysis.get("核心驱动因素", [])
        if core_factors:
            output.append(f"\n🎯 核心驱动因素")
            for i, factor in enumerate(core_factors, 1):
                output.append(f"   {i}. {factor}")

        dimensions = viral_analysis.get("维度分析", {})
        if dimensions:
            output.append(f"\n📋 维度分析")

            for dim_name, dim_data in dimensions.items():
                if isinstance(dim_data, dict):
                    output.append(f"\n   【{dim_name}】")
                    for key, value in dim_data.items():
                        if value and value != "N/A":
                            output.append(f"     {key}: {value}")

        success_factors = viral_analysis.get("可复刻的成功要素", [])
        if success_factors:
            output.append(f"\n✅ 可复刻的成功要素")
            for factor in success_factors:
                output.append(f"   • {factor}")

        pitfalls = viral_analysis.get("避坑指南", [])
        if pitfalls:
            output.append(f"\n⚠️  避坑指南")
            for pitfall in pitfalls:
                output.append(f"   • {pitfall}")

        return "\n".join(output)

    def format_tts_script_for_display(self, tts_result: Dict[str, Any]) -> str:
        """格式化TTS脚本结果用于显示"""
        output = []
        output.append("\n" + "=" * 60)
        output.append("🎤 TTS复刻台词 + 发布信息")
        output.append("=" * 60)

        if "error" in tts_result:
            output.append(f"\n❌ 生成失败: {tts_result['error']}")
            return "\n".join(output)

        # 视频标题
        title = tts_result.get("视频标题", "")
        if title:
            output.append(f"\n📌 视频标题")
            output.append(f"   {title}")

        # 视频描述
        desc = tts_result.get("视频描述", "")
        if desc:
            output.append(f"\n📝 视频描述")
            output.append(f"   {desc}")

        # TTS台词
        tts_data = tts_result.get("TTS台词", {})
        if tts_data:
            output.append(f"\n🎙️  TTS台词（供语音合成）")

            segments = tts_data.get("分段", [])
            if segments:
                output.append(f"   分段台词 ({len(segments)}段):")
                for i, seg in enumerate(segments, 1):
                    output.append(f"     {i}. {seg}")

            full = tts_data.get("完整版", "")
            if full:
                actual_count = tts_data.get("实际字数", len(full))
                target_range = tts_data.get("目标字数范围", "")
                output.append(f"\n   ═══════════════════════════════════")
                output.append(f"   📢 TTS完整台词（不含标题和标签）")
                output.append(f"   ═══════════════════════════════════")
                output.append(f"   {full}")
                output.append(f"   ═══════════════════════════════════")
                output.append(f"   📊 字数统计: {actual_count}字 (目标: {target_range}字)")
                
                estimated = tts_data.get("实际预估时长", tts_data.get("预估时长", "N/A"))
                output.append(f"   ⏱️  预估时长: {estimated}秒")
                
                # 字数是否达标提示
                if target_range:
                    try:
                        min_target = int(target_range.split("-")[0])
                        if actual_count < min_target:
                            output.append(f"   ⚠️  警告: 字数不足 {min_target - actual_count} 字")
                        else:
                            output.append(f"   ✅ 字数达标")
                    except:
                        pass

            # 带停顿标记版本
            with_pause = tts_data.get("带停顿标记", "")
            if with_pause:
                output.append(f"\n   TTS标记版（含停顿）:")
                output.append(f"   {with_pause}")

        # 话题标签
        tags = tts_result.get("话题标签", [])
        if tags:
            output.append(f"\n🏷️  话题标签")
            output.append(f"   {' '.join(tags)}")

        # 发布文案
        publish = tts_result.get("发布文案", "")
        if publish:
            output.append(f"\n📱 发布文案（可直接复制）")
            output.append(f"   {publish}")

        # 复刻要点
        tips = tts_result.get("复刻要点", [])
        if tips:
            output.append(f"\n💡 复刻要点")
            for tip in tips:
                output.append(f"   • {tip}")

        return "\n".join(output)

    def save_scripts(self, scripts: List[Dict], analysis: Dict, filepath: str = "generated_scripts.json"):
        """保存脚本到文件"""
        output = {
            "风格分析": analysis,
            "生成的脚本": scripts
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        # 同时保存可读版本
        readme_path = filepath.replace('.json', '_readme.txt')
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("视频风格分析 + 脚本生成结果\n")
            f.write("="*60 + "\n\n")

            f.write("【风格分析】\n")
            f.write(f"风格总结: {analysis.get('风格总结', 'N/A')}\n")
            f.write(f"分析视频数: {analysis.get('分析视频数', 0)}\n")
            f.write(f"平均点赞: {analysis.get('平均点赞', 0):,}\n\n")

            features = analysis.get('文案特征', {})
            if features:
                f.write("文案特征:\n")
                f.write(f"  平均字数: {features.get('平均字数', 'N/A')}\n")
                f.write(f"  字数范围: {features.get('字数范围', 'N/A')}\n")
                f.write(f"  语气: {features.get('语气', 'N/A')}\n")
                f.write(f"  表达方式: {features.get('表达方式', 'N/A')}\n\n")

            f.write(f"高频词汇: {', '.join(analysis.get('高频词汇', [])[:10])}\n")
            f.write(f"句式模板: {', '.join(analysis.get('句式模板', [])[:5])}\n\n")

            f.write("\n" + "="*60 + "\n")
            f.write("【生成的脚本】\n")
            f.write("="*60 + "\n")

            for i, script in enumerate(scripts, 1):
                f.write(self.format_script_for_display(script, i))
                f.write("\n")

        return filepath, readme_path


def interactive_mode():
    """完整的视频脚本生成工作流
    
    流程：
    1. 输入用户主页链接 → 抓取视频数据
    2. 大模型分析（火爆原因 + 风格特征）
    3. 生成多个标题/描述/标签选项
    4. 用户选择后生成TTS台词
    5. 使用CosyVoice生成语音（需预先配置声源）
    """
    print("=" * 70)
    print("🎬 视频脚本生成工作流")
    print("=" * 70)
    
    # ========================================
    # 步骤1：输入用户主页
    # ========================================
    print("\n【步骤1/6】输入要分析的用户主页")
    print("提示：格式如 https://www.douyin.com/user/MS4wLjABAAAA...")
    url = input("用户主页URL: ").strip()
    
    if not url:
        print("❌ 请输入有效的用户主页URL")
        return
    
    # ========================================
    # 步骤2：抓取视频数据
    # ========================================
    print("\n【步骤2/6】抓取视频数据...")
    fetcher = DouyinFetcher(max_videos=100, enable_filter=False)
    
    videos = fetcher.fetch_from_url(url)
    
    if not videos:
        print("❌ 未获取到视频数据")
        print("   可能原因：")
        print("   1. URL格式不正确")
        print("   2. 用户设置了隐私权限")
        print("   3. Cookie已过期（请在 douyin_data_tool/config.py 中更新）")
        return
    
    print(f"✓ 成功抓取 {len(videos)} 个视频")
    
    # ========================================
    # 步骤3：大模型分析（火爆原因 + 风格特征）
    # ========================================
    print("\n【步骤3/6】AI 分析中（火爆原因 + 风格特征）...")
    analyzer = VideoStyleAnalyzer()
    full_result = analyzer.full_analysis(videos, top_n=30)
    
    viral_analysis = full_result.get("火爆原因分析", {})
    style_analysis = full_result.get("风格特征分析", {})
    
    if "error" in viral_analysis:
        print(f"❌ 火爆分析失败: {viral_analysis.get('error', '')}")
        viral_analysis = {}
    if "error" in style_analysis:
        print(f"❌ 风格分析失败: {style_analysis.get('error', '')}")
        style_analysis = {}
    
    if not viral_analysis and not style_analysis:
        return
    
    # 显示火爆分析
    if viral_analysis:
        print(analyzer.format_viral_analysis_for_display(viral_analysis))
    
    # 显示风格分析
    if style_analysis:
        print("\n" + "=" * 60)
        print("🎨 风格特征分析")
        print("=" * 60)
        print(f"\n📊 数据统计")
        print(f"   分析视频数: {style_analysis.get('分析视频数', 0)}")
        print(f"   平均点赞: {style_analysis.get('平均点赞', 0):,}")
        print(f"\n🎭 风格总结")
        print(f"   {style_analysis.get('风格总结', 'N/A')}")
        
        features = style_analysis.get('文案特征', {})
        if features:
            print(f"\n📝 文案特征")
            print(f"   平均字数: {features.get('平均字数', 'N/A')}")
            print(f"   字数范围: {features.get('字数范围', 'N/A')}")
            print(f"   语气: {features.get('语气', 'N/A')}")
        
        print(f"\n🔤 高频词汇: {', '.join(style_analysis.get('高频词汇', [])[:8])}")
    
    # ========================================
    # 步骤4：输入主题和目标时长，生成多个选项
    # ========================================
    print("\n【步骤4/6】输入新主题")
    topic = input("请输入新主题: ").strip()
    
    if not topic:
        print("已跳过后续步骤")
        return
    
    # 输入目标时长
    print("\n请输入目标视频时长（秒）:")
    print("  常用时长: 15(短视频), 20(中等), 30(较长), 60(长视频)")
    duration_input = input("目标时长（默认20秒）: ").strip()
    try:
        target_duration = float(duration_input) if duration_input else 20.0
    except ValueError:
        print("输入无效，使用默认20秒")
        target_duration = 20.0
    
    print(f"✓ 将生成约 {target_duration} 秒的口播台词（约{int(target_duration * 3)}-{int(target_duration * 3.5)}字）")
    
    count = int(input("生成几个方案供选择（默认3）: ").strip() or "3")
    
    print(f"\n正在生成 {count} 个标题/描述/标签方案...")
    
    # 生成多个方案
    tts_results = []
    for i in range(count):
        result = analyzer.generate_tts_script(
            style_analysis=style_analysis,
            viral_analysis=viral_analysis,
            topic=topic,
            target_duration=target_duration
        )
        if "error" not in result:
            tts_results.append(result)
    
    if not tts_results:
        print("❌ 生成失败")
        return
    
    # ========================================
    # 步骤5：展示方案，让用户选择
    # ========================================
    print("\n【步骤5/6】请选择方案")
    print("\n" + "=" * 60)
    
    for i, result in enumerate(tts_results, 1):
        title = result.get("视频标题", "")
        desc = result.get("视频描述", "")
        tags = result.get("话题标签", [])
        
        print(f"\n【方案 {i}】")
        print(f"📌 标题: {title}")
        print(f"📝 描述: {desc}")
        print(f"🏷️  标签: {' '.join(tags)}")
    
    # 默认选择第一个方案
    selected = tts_results[0]
    
    while True:
        choice = input(f"\n请选择方案（1-{len(tts_results)}），直接回车使用方案1: ").strip()
        if not choice:
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(tts_results):
                selected = tts_results[idx]
                break
        except ValueError:
            pass
        print("无效选择，请重试")
    
    # 用户选择 "0" 会重新进入循环，所以到这里 selected 必然已赋值
    # 显示选中方案的TTS台词
    print("\n" + "=" * 60)
    print("🎤 已选中方案的TTS台词")
    print("=" * 60)
    print(analyzer.format_tts_script_for_display(selected))
    
    # ========================================
    # 步骤6：TTS语音生成（可选）
    # ========================================
    print("\n【步骤6/6】TTS语音生成（可选）")
    do_tts = input("是否使用CosyVoice生成语音？(y/n): ").strip().lower()
    
    if do_tts == "y":
        # 检查是否配置了阿里云API
        try:
            from cosyvoice_tts import CosyVoiceTTSClient
            APIKeys.get_dashscope()  # 检查API Key
        except Exception as e:
            print(f"❌ CosyVoice未配置: {e}")
            print("   请在 .env 文件中设置 DASHSCOPE_API_KEY")
        else:
            # 询问voice_id
            voice_id = input("\n请输入CosyVoice的Voice ID（音色复刻ID）: ").strip()
            
            if not voice_id:
                # 可以提供创建音色的选项
                create_voice = input("是否创建新的音色复刻？(y/n): ").strip().lower()
                if create_voice == "y":
                    audio_url = input("请输入参考音频的公网URL: ").strip()
                    if audio_url:
                        client = CosyVoiceTTSClient()
                        print("\n正在创建音色复刻（可能需要几分钟）...")
                        try:
                            voice_result = client.create_voice(
                                audio_url=audio_url,
                                prefix="myvoice",
                                wait_ready=True
                            )
                            voice_id = voice_result["voice_id"]
                            print(f"✓ 音色创建成功！Voice ID: {voice_id}")
                        except Exception as e:
                            print(f"❌ 音色创建失败: {e}")
                            voice_id = None
                else:
                    print("已跳过TTS生成")
            else:
                # 使用已有voice_id生成语音
                tts_data = selected.get("TTS台词", {})
                full_script = tts_data.get("完整版", "")
                
                if full_script:
                    print("\n正在生成语音...")
                    
                    try:
                        output_path = Paths.get_output_dir() / "final_speech.mp3"
                        
                        client = CosyVoiceTTSClient()
                        client.speech(
                            text=full_script,
                            voice=voice_id,
                            output_path=str(output_path)
                        )
                        
                        print(f"\n✓ 语音生成成功: {output_path}")
                    except Exception as e:
                        print(f"❌ 语音生成失败: {e}")
    
    # ========================================
    # 保存结果
    # ========================================
    save = input("\n是否保存结果？(y/n): ").strip().lower()
    if save == "y":
        timestamp = __import__('time').strftime("%Y%m%d_%H%M%S")
        filename = Paths.get_output_dir() / f"script_{timestamp}.json"
        
        output = {
            "输入信息": {
                "用户主页URL": url,
                "主题": topic,
                "选中方案": int(choice) if choice.isdigit() else 1,
            },
            "火爆原因分析": viral_analysis,
            "风格特征分析": style_analysis,
            "选中方案": selected,
            "所有方案": tts_results,
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ 已保存到: {filename}")
        
        # 同时保存可读文本版本
        txt_file = Paths.get_output_dir() / f"script_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("视频脚本生成结果\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"用户主页: {url}\n")
            f.write(f"主题: {topic}\n\n")
            
            f.write("=" * 60 + "\n")
            f.write("【火爆原因分析】\n")
            f.write("=" * 60 + "\n")
            f.write(f"{viral_analysis.get('火爆原因总结', 'N/A')}\n\n")
            
            f.write("=" * 60 + "\n")
            f.write("【风格特征】\n")
            f.write("=" * 60 + "\n")
            f.write(f"{style_analysis.get('风格总结', 'N/A')}\n\n")
            
            f.write("=" * 60 + "\n")
            f.write("【选中方案】\n")
            f.write("=" * 60 + "\n")
            f.write(f"标题: {selected.get('视频标题', '')}\n")
            f.write(f"描述: {selected.get('视频描述', '')}\n")
            f.write(f"标签: {' '.join(selected.get('话题标签', []))}\n\n")
            
            tts_data = selected.get("TTS台词", {})
            f.write(f"TTS台词: {tts_data.get('完整版', '')}\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("【发布文案（可直接复制）】\n")
            f.write("=" * 60 + "\n")
            f.write(selected.get('发布文案', ''))
        
        print(f"✓ 可读版本: {txt_file}")


def quick_full_workflow(url: str, topic: str, max_videos: int = 50, target_duration: float = 20.0):
    """快速完整流程：火爆分析+风格分析+TTS台词生成"""
    print("=" * 70)
    print(f"分析URL: {url}")
    print(f"新主题: {topic}")
    print("=" * 70)

    # 抓取
    print("\n[1/3] 抓取视频数据...")
    fetcher = DouyinFetcher(max_videos=max_videos, enable_filter=False)
    videos = fetcher.fetch_from_url(url)

    if not videos:
        print("❌ 未获取到视频")
        return None

    print(f"✓ 成功抓取 {len(videos)} 个视频")

    # 分析
    print("\n[2/3] 分析火爆原因和风格特征...")
    analyzer = VideoStyleAnalyzer()
    full_result = analyzer.full_analysis(videos, top_n=30)

    viral_analysis = full_result.get("火爆原因分析", {})
    style_analysis = full_result.get("风格特征分析", {})

    if "error" in viral_analysis:
        print(f"⚠️ 火爆分析失败: {viral_analysis.get('error', '')}")
    if "error" in style_analysis:
        print(f"⚠️ 风格分析失败: {style_analysis.get('error', '')}")

    # 显示分析结果
    if viral_analysis:
        print(analyzer.format_viral_analysis_for_display(viral_analysis))

    if style_analysis:
        print("\n" + "=" * 60)
        print("🎨 风格特征分析")
        print("=" * 60)
        print(f"\n风格总结: {style_analysis.get('风格总结', 'N/A')}")
        features = style_analysis.get('文案特征', {})
        if features:
            print(f"语气: {features.get('语气', 'N/A')}")
            print(f"表达方式: {features.get('表达方式', 'N/A')}")
        print(f"高频词汇: {', '.join(style_analysis.get('高频词汇', [])[:8])}")

    # 生成TTS台词
    print("\n[3/3] 生成TTS复刻台词...")
    if viral_analysis and style_analysis:
        tts_result = analyzer.generate_tts_script(
            style_analysis=style_analysis,
            viral_analysis=viral_analysis,
            topic=topic,
            target_duration=target_duration
        )
        print(analyzer.format_tts_script_for_display(tts_result))
    else:
        tts_result = None
        print("⚠️ 分析失败，跳过TTS台词生成")

    # 保存
    timestamp = __import__('time').strftime("%Y%m%d_%H%M%S")
    filename = f"analysis_result_{timestamp}.json"

    output = {
        "火爆原因分析": viral_analysis,
        "风格特征分析": style_analysis,
    }
    if tts_result:
        output["TTS台词结果"] = tts_result

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 结果已保存到: {filename}")

    return {
        "viral_analysis": viral_analysis,
        "style_analysis": style_analysis,
        "tts_result": tts_result
    }


def quick_generate(url: str, topic: str, max_videos: int = 50, count: int = 3):
    """快速分析+生成（兼容旧接口）"""
    print(f"正在分析: {url}")

    # 抓取
    fetcher = DouyinFetcher(max_videos=max_videos, enable_filter=False)
    videos = fetcher.fetch_from_url(url)

    if not videos:
        print("未获取到视频")
        return None

    # 分析
    analyzer = VideoStyleAnalyzer()
    analysis = analyzer.analyze_videos(videos, top_n=30)

    if "error" in analysis:
        print(f"分析失败: {analysis['error']}")
        return None

    print(f"\n【风格分析】")
    print(f"风格: {analysis.get('风格总结', 'N/A')}")

    # 生成
    print(f"\n【生成脚本: {topic}】")
    scripts = analyzer.generate_script(analysis, topic, count)

    for i, script in enumerate(scripts, 1):
        print(analyzer.format_script_for_display(script, i))

    # 保存
    analyzer.save_scripts(scripts, analysis)

    return {"analysis": analysis, "scripts": scripts}


def full_analysis_workflow(
    url: str,
    topic: str,
    max_videos: int = 100,
    enable_viral: bool = True,
    enable_style: bool = True,
    generate_script: bool = True,
    target_duration: float = 20.0
) -> Dict[str, Any]:
    """
    完整分析流程（供 API 服务调用）
    
    步骤：
    1. 从抖音URL抓取视频数据
    2. 进行火爆原因分析
    3. 进行风格特征分析
    4. 生成新主题脚本（TTS台词）
    
    Args:
        url: 抖音用户主页URL
        topic: 新主题
        max_videos: 最大抓取视频数
        enable_viral: 是否进行火爆分析
        enable_style: 是否进行风格分析
        generate_script: 是否生成脚本
        target_duration: TTS目标时长（秒）
    
    Returns:
        Dict: 包含 viral_analysis, style_analysis, tts_result
    """
    # 抓取
    print("\n[1/4] 抓取视频数据...")
    fetcher = DouyinFetcher(max_videos=max_videos, enable_filter=False)
    videos = fetcher.fetch_from_url(url)
    
    if not videos:
        print("❌ 未获取到视频")
        return {"error": "未获取到视频数据"}
    
    print(f"✓ 成功抓取 {len(videos)} 个视频")
    
    viral_analysis = {}
    style_analysis = {}
    tts_result = None
    
    # 分析
    if enable_viral or enable_style:
        print("\n[2/4] 分析火爆原因和风格特征...")
        analyzer = VideoStyleAnalyzer()
        full_result = analyzer.full_analysis(videos, top_n=30)
        
        if enable_viral:
            viral_analysis = full_result.get("火爆原因分析", {})
        if enable_style:
            style_analysis = full_result.get("风格特征分析", {})
        
        # 显示分析结果
        if viral_analysis and "error" not in viral_analysis:
            print(analyzer.format_viral_analysis_for_display(viral_analysis))
        if style_analysis and "error" not in style_analysis:
            print(f"\n风格总结: {style_analysis.get('风格总结', 'N/A')}")
    
    # 生成TTS台词
    if generate_script and viral_analysis and style_analysis:
        print("\n[3/4] 生成TTS复刻台词...")
        tts_result = analyzer.generate_tts_script(
            style_analysis=style_analysis,
            viral_analysis=viral_analysis,
            topic=topic,
            target_duration=target_duration
        )
        print(analyzer.format_tts_script_for_display(tts_result))
    
    # 保存结果
    print("\n[4/4] 保存结果...")
    timestamp = __import__('time').strftime("%Y%m%d_%H%M%S")
    filename = Paths.get_output_dir() / f"full_analysis_{timestamp}.json"
    
    output = {
        "viral_analysis": viral_analysis,
        "style_analysis": style_analysis,
        "tts_result": tts_result
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 结果已保存到: {filename}")
    
    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="视频火爆原因分析 + 风格分析 + TTS台词生成工具")
    parser.add_argument("--url", help="用户主页URL")
    parser.add_argument("--topic", help="新主题（用于生成TTS台词）")
    parser.add_argument("--max", type=int, default=50, help="抓取视频数（默认50）")
    parser.add_argument("--duration", type=float, default=20.0, help="TTS目标时长（秒，默认20）")
    parser.add_argument("--count", type=int, default=3, help="生成脚本数（默认3，仅旧模式）")
    parser.add_argument("--full", action="store_true", help="使用完整流程（火爆+风格+TTS）")

    args = parser.parse_args()

    if args.url and args.topic:
        if args.full:
            quick_full_workflow(args.url, args.topic, args.max, args.duration)
        else:
            quick_generate(args.url, args.topic, args.max, args.count)
    else:
        interactive_mode()
