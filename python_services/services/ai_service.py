"""
AI分析与脚本生成服务
封装analyze_and_generate模块的API
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config import settings
from core.logger import get_logger

logger = get_logger("service:ai")


class AIService:
    """AI分析与脚本生成服务"""

    def __init__(self):
        self.longgraph_dir = settings.longgraph_path
        self.executor = ThreadPoolExecutor(max_workers=3)

    async def _run_in_executor(self, func, label="操作"):
        """在线程池中执行同步函数，统一日志和异常处理"""
        def _wrapper():
            try:
                return func()
            except Exception as e:
                logger.error(f"{label}失败: {e}")
                raise
        return await asyncio.get_running_loop().run_in_executor(self.executor, _wrapper)

    async def analyze_viral_async(
        self,
        video_data: List[Dict[str, Any]],
        video_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        异步火爆原因分析

        Args:
            video_data: 视频数据列表
            video_ids: 指定分析的视频ID

        Returns:
            分析结果
        """
        def _analyze():
            sys.path.insert(0, str(self.longgraph_dir))
            from analyze_and_generate import VideoStyleAnalyzer

            analyzer = VideoStyleAnalyzer()
            return analyzer.analyze_viral_factors(videos=video_data, top_n=20)

        return await self._run_in_executor(_analyze, "火爆原因分析")

    async def analyze_style_async(
        self,
        video_data: List[Dict[str, Any]],
        dimensions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        异步风格特征分析

        Args:
            video_data: 视频数据列表
            dimensions: 分析维度

        Returns:
            分析结果
        """
        def _analyze():
            sys.path.insert(0, str(self.longgraph_dir))
            from analyze_and_generate import VideoStyleAnalyzer

            analyzer = VideoStyleAnalyzer()
            return analyzer.analyze_videos(videos=video_data, top_n=30)

        return await self._run_in_executor(_analyze, "风格分析")

    async def generate_script_async(
        self,
        style_analysis: Dict[str, Any],
        viral_analysis: Dict[str, Any],
        topic: str,
        target_duration: float = 20.0,
        profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        异步生成脚本

        两种模式：
        1. 有视频分析结果 → 走 analyze_and_generate.generate_tts_script
        2. 仅有档案 → 直接根据档案+选题生成，按 target_duration 控制字数

        Args:
            style_analysis: 风格分析结果
            viral_analysis: 火爆分析结果
            topic: 新主题
            target_duration: 目标时长（秒）
            profile: 档案数据（可选）

        Returns:
            生成的脚本
        """
        has_video_analysis = bool(style_analysis) or bool(viral_analysis)

        if has_video_analysis:
            return await self._generate_from_video_analysis(
                style_analysis, viral_analysis, topic, target_duration, profile
            )
        elif profile:
            return await self._generate_from_profile(profile, topic, target_duration)
        else:
            raise ValueError("请提供 style_analysis/viral_analysis 或 profile_id")

    async def _generate_from_video_analysis(
        self,
        style_analysis: Dict[str, Any],
        viral_analysis: Dict[str, Any],
        topic: str,
        target_duration: float,
        profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """有视频分析结果时，走 analyze_and_generate 模块"""
        def _generate():
            sys.path.insert(0, str(self.longgraph_dir))
            from analyze_and_generate import VideoStyleAnalyzer

            analyzer = VideoStyleAnalyzer()

            local_style = dict(style_analysis or {})
            local_viral = dict(viral_analysis or {})

            if profile:
                local_style["_profile_context"] = (
                    f"创作者档案 - 行业: {profile.get('industry', '')}, "
                    f"目标用户: {profile.get('target_audience', '')}, "
                    f"客户痛点: {profile.get('customer_pain_points', '')}, "
                    f"解决方案: {profile.get('solution', '')}, "
                    f"人设背景: {profile.get('persona_background', '')}"
                )
                local_viral["_profile_context"] = local_style["_profile_context"]

            result = analyzer.generate_tts_script(
                style_analysis=local_style,
                viral_analysis=local_viral,
                topic=topic,
                target_duration=target_duration
            )

            tts_data = result.get("TTS台词", {})
            normalized = {
                "title": result.get("视频标题", ""),
                "description": result.get("视频描述", ""),
                "hashtags": result.get("话题标签", []),
                "publish_text": result.get("发布文案", ""),
                "full_script": tts_data.get("完整版", ""),
                "segments": tts_data.get("分段", []),
                "word_count": tts_data.get("实际字数", len(tts_data.get("完整版", ""))),
                "estimated_duration": tts_data.get("实际预估时长", 0),
                "copy_points": result.get("复刻要点", []),
            }
            if "error" in result:
                normalized["error"] = result["error"]
            return normalized

        return await self._run_in_executor(_generate, "脚本生成")

    async def _generate_from_profile(
        self,
        profile: Dict[str, Any],
        topic: str,
        target_duration: float
    ) -> Dict[str, Any]:
        """仅有档案时，直接根据档案+选题生成 TTS 脚本"""
        def _generate():
            sys.path.insert(0, str(self.longgraph_dir))
            from config import LLMModel
            from openai import OpenAI

            config = LLMModel.get_model_config("deepseek")
            client = OpenAI(api_key=config["api_key"](), base_url=config["base_url"])

            # 按正常语速 3-3.5 字/秒计算目标字数
            target_words_min = int(target_duration * 3)
            target_words_max = int(target_duration * 3.5)

            reference_section = ""
            if profile.get("video_url"):
                reference_section += f"\n- 参考视频链接：{profile['video_url']}"
            if profile.get("homepage_url"):
                reference_section += f"\n- 参考主页链接：{profile['homepage_url']}"

            prompt = f"""你是一位专业的短视频文案策划师和口播脚本撰写专家。请根据以下创作者档案和选题，生成一份用于 TTS 语音合成的完整口播脚本。

【创作者档案】
- 档案名称：{profile.get('name', '')}
- 所属行业：{profile.get('industry', '')}
- 目标用户群体：{profile.get('target_audience', '')}
- 客户痛点：{profile.get('customer_pain_points', '')}
- 解决方案：{profile.get('solution', '')}
- 人设背景：{profile.get('persona_background', '')}
{reference_section}

【选题主题】
{topic}

【目标时长】{target_duration}秒（约{target_words_min}-{target_words_max}字）

---

请生成两部分内容：

## 第一部分：发布信息
- 视频标题：8-15字，吸睛
- 视频描述：30-50字
- 话题标签：5-8个
- 发布文案：适合直接复制发布

## 第二部分：TTS口播脚本
这是交给 TTS 语音合成的完整台词，需要满足以下要求：

⚠️ **字数硬性要求：完整版必须达到{target_words_min}-{target_words_max}字！**

**脚本结构：**
1. 开头钩子（{max(2, int(target_duration * 0.1))}秒）- 用提问、数据、反常识等方式抓住注意力
2. 痛点共鸣（约{target_duration * 0.2:.0f}秒）- 描述{profile.get('target_audience', '')}的真实困境
3. 核心内容展开（约{target_duration * 0.5:.0f}秒）- 针对{profile.get('customer_pain_points', '')}提供{profile.get('solution', '')}的方案
   - 可穿插案例、数据、比喻
   - 多用具体细节，少用空泛描述
   - 适当加入口语化表达（呢、吧、啊、哦）
4. 结尾引导（{max(3, int(target_duration * 0.2))}秒）- 总结升华或引导互动（点赞、关注、评论）

**写作要求：**
- 以{profile.get('persona_background', '')}的人设口吻撰写
- 口语化表达，像和朋友聊天一样自然
- 短句为主，每句8-15字，确保一口气能说完
- 多用细节描述、场景还原、人物对话让内容更生动
- 紧扣{profile.get('industry', '')}行业背景，体现专业性

【输出格式】
请以JSON格式返回：
{{{{
    "title": "视频标题（8-15字）",
    "description": "视频描述（30-50字）",
    "hashtags": ["#标签1", "#标签2", "#标签3"],
    "publish_text": "发布文案（含标签，100字以内）",
    "full_script": "完整TTS口播台词（必须{target_words_min}-{target_words_max}字，自然口语化）",
    "segments": ["开头钩子句", "痛点共鸣句1", "痛点共鸣句2", "核心内容句1", "核心内容句2", "...", "结尾引导句"]
}}}}

直接返回JSON，不要输出其他内容："""

            response = client.chat.completions.create(
                model=config["model"],
                messages=[
                    {"role": "system", "content": "你是专业的短视频口播脚本撰写专家。只输出JSON格式的内容，不要输出任何其他文字或markdown标记。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )

            content = response.choices[0].message.content.strip()

            # 清理 markdown 代码块标记
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            try:
                script = json.loads(content)
            except json.JSONDecodeError:
                logger.warning("文案 JSON 解析失败，返回原始文本")
                script = {
                    "title": topic,
                    "description": "",
                    "hashtags": [],
                    "publish_text": content,
                    "full_script": content,
                    "segments": [content]
                }

            # 计算实际字数和时长
            full_text = script.get("full_script", "")
            script["word_count"] = len(full_text)
            script["estimated_duration"] = max(10, round(len(full_text) / 3.5, 1))

            logger.info(f"档案脚本生成完成: {len(full_text)}字, 预估{script['estimated_duration']}秒")

            return script

        return await self._run_in_executor(_generate, "档案脚本生成")

    async def full_analysis_async(
        self,
        douyin_url: str,
        topic: str,
        max_videos: int = 100,
        enable_viral: bool = True,
        enable_style: bool = True,
        generate_script: bool = True,
        target_duration: float = 60.0
    ) -> Dict[str, Any]:
        """
        完整分析流程

        Args:
            douyin_url: 抖音URL
            topic: 新主题
            max_videos: 最大视频数
            enable_viral: 是否进行火爆分析
            enable_style: 是否进行风格分析
            generate_script: 是否生成脚本
            target_duration: TTS目标时长（秒），默认60秒

        Returns:
            完整分析结果
        """
        def _analyze():
            sys.path.insert(0, str(self.longgraph_dir))
            from analyze_and_generate import full_analysis_workflow

            return full_analysis_workflow(
                url=douyin_url,
                topic=topic,
                max_videos=max_videos,
                enable_viral=enable_viral,
                enable_style=enable_style,
                generate_script=generate_script,
                target_duration=target_duration
            )

        return await self._run_in_executor(_analyze, "完整分析")
