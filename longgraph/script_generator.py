"""
文案生成工具 - 支持多模型选择，优化电子音合成
功能：
1. 可选择智谱/DeepSeek模型
2. 生成适合电子音朗读的台词（分段、停顿标记、口语化）
3. 输出可直接用于TTS和数字人生成的格式
"""

import os
import sys
from pathlib import Path
from typing import Literal, List, Dict, Any

from openai import OpenAI

# 导入统一配置
from config import LLMModel, Paths


class ScriptGenerator:
    """文案生成器 - 支持多模型，优化电子音朗读"""

    def __init__(self, model: Literal["zhipu", "deepseek"] = "deepseek"):
        """
        Args:
            model: 选择模型 ("zhipu" 或 "deepseek")
        """
        self.model = model
        self._init_client()

    def _init_client(self):
        """初始化客户端"""
        config = LLMModel.get_model_config(self.model)

        self.client = OpenAI(
            api_key=config["api_key"](),
            base_url=config["base_url"]
        )
        self.model_name = config["model"]

    def generate_for_tts(
        self,
        reference_script: str,
        hashtags: List[str],
        topic: str,
        style: str = "自嘲幽默",
        target_duration: float = 20.0
    ) -> Dict[str, Any]:
        """
        生成文案：TTS朗读用 + 平台发布用

        Args:
            reference_script: 参考文案
            hashtags: 话题标签
            topic: 新主题
            style: 文案风格
            target_duration: 目标时长（秒），默认20秒

        Returns:
            Dict: {
                # TTS/数字人用
                "full_script": "完整文案",
                "segments": ["分段1", "分段2", ...],
                "tts_script": "带停顿标记的台词",
                "estimated_duration": 预估时长(秒),
                "target_duration": 目标时长(秒),

                # 平台发布用
                "short_script": "带标签的短文案，用于作品描述",
                "publish_text": "完整的发布文案（标题+描述+标签）",

                # 通用
                "suggested_tags": ["标签1", "标签2"]
            }
        """
        # 根据目标时长计算字数要求（正常语速约3-3.5字/秒）
        target_words = int(target_duration * 3.5)
        target_words_min = int(target_duration * 3)
        # 按每段8-12字计算需要的段数
        min_segments = max(4, target_words_min // 12)  # 至少4段
        max_segments = target_words_min // 8 + 2  # 按最短每段8字计算
        tags_str = " ".join(hashtags) if hashtags else ""

        prompt = f"""你是短视频文案创作专家，需要同时生成两种文案。

【参考文案】
{reference_script}

【话题标签】
{tags_str}

【新主题】
{topic}

【文案风格】
{style}

【参考风格特征】
- 人设: 自嘲式"黄金律师"，喜欢用"月入XXX"自嘲
- 语气: 轻松幽默接地气，有网络梗
- 表达: 短句为主，善用反问和感叹
- 口语化: 用"呢、吧、啊、哦"等语气词

【目标时长】
{target_duration}秒（TTS完整台词需要约{target_words_min}-{target_words}字）

【要求 - 生成两种文案】

**文案1：TTS朗读用（电子音/数字人）- 重点关注节奏和连贯性**
1. 口语化表达，避免生僻字
2. 每句话8-15个字，确保一口气能说完
3. 段落间必须有明显停顿（用...或换行表示）
4. **完整版字数必须达到{target_words_min}-{target_words}字**（硬性要求！用于生成{target_duration}秒的语音）
5. **分成{min_segments}-{max_segments}个短句**
6. 必须是完整的叙事结构：
   * 开头：钩子吸引注意力（1-2句）
   * 中间：情节展开，有起伏（{min_segments-4}到{max_segments-4}句）
   * 结尾：记忆点或互动引导（1-2句）
7. 保持自嘲幽默风格
8. 重要：句子之间用标点符号明确分隔，确保TTS正确断句
9. 内容要充实，不能空洞重复

**文案2：平台发布用（作品描述+引流）**
1. 短小精悍，200字
2. 吸引眼球的标题/开头
3. 文末附5-8个话题标签（#格式）
4. 包含引导互动（关注、点赞等）
5. 可使用emoji增加吸引力

【输出格式】
按以下JSON格式返回：
{{
    "segments": ["第一段", "第二段", "第三段"],
    "full_script": "完整文案（必须达到{target_words_min}字以上）",
    "short_script": "短文案用于发布 #标签1 #标签2",
    "suggested_tags": ["#标签1", "#标签2", "#标签3"]
}}

⚠️ **再次强调："full_script"必须是{target_words_min}-{target_words}字的长篇内容，用于生成{target_duration}秒的语音！**

直接返回JSON，不要其他内容："""

        try:
            if self.model == "zhipu":
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "你是专业的短视频文案创作专家。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,
                )
                result_text = response.choices[0].message.content
            else:  # deepseek
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "你是专业的短视频文案创作专家。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,
                    response_format={"type": "json_object"},
                )
                result_text = response.choices[0].message.content

            # 解析JSON
            import json
            result = json.loads(result_text)

            # 处理TTS优化版本
            segments = result.get("segments", [])
            full_script = result.get("full_script", "".join(segments))
            short_script = result.get("short_script", "")
            suggested_tags = result.get("suggested_tags", [])

            # 生成带停顿标记的台词（用于TTS）
            tts_script = self._add_pause_markers(segments)

            # 生成完整的发布文案
            if not short_script:
                # 如果模型没返回short_script，用full_script+tags生成
                short_script = f"{full_script} {' '.join(suggested_tags[:5])}"
            
            publish_text = f"{short_script}"

            # 预估时长（平均每秒3个字）
            estimated_duration = len(full_script) / 3

            return {
                "model_used": self.model,
                # TTS/数字人用
                "full_script": full_script,
                "segments": segments,
                "tts_script": tts_script,
                "estimated_duration": round(estimated_duration, 1),
                "target_duration": target_duration,
                # 平台发布用
                "short_script": short_script,
                "publish_text": publish_text,
                # 通用
                "suggested_tags": suggested_tags,
                "character_count": len(full_script)
            }

        except Exception as e:
            print(f"生成失败: {e}")
            return {
                "model_used": self.model,
                "error": str(e)
            }

    def _add_pause_markers(self, segments: List[str]) -> str:
        """
        添加停顿标记，便于TTS合成
        
        停顿规则：
        - 句号/感叹号/问号：0.5秒停顿
        - 逗号：0.2秒停顿
        - 段落之间：1.0秒停顿
        - 强调/转折：0.8秒停顿
        """
        pause_long = " [1.0] "     # 段落间停顿
        pause_medium = " [0.5] "   # 句末停顿
        pause_short = " [0.2] "    # 逗号停顿
        pause_emphasis = " [0.8] " # 强调停顿

        processed_segments = []
        for seg in segments:
            # 替换标点为停顿标记
            seg = seg.replace("，", "，[0.2]")
            seg = seg.replace("。", "。[0.5]")
            seg = seg.replace("！", "！[0.5]")
            seg = seg.replace("？", "？[0.5]")
            # 处理省略号（较长停顿）
            seg = seg.replace("...", "...[0.8]")
            seg = seg.replace("…", "…[0.8]")
            
            processed_segments.append(seg)

        return pause_long.join(processed_segments)

    def generate_tts_with_pacing(
        self,
        reference_script: str,
        topic: str,
        target_duration: float = 15.0
    ) -> Dict[str, Any]:
        """
        生成带节奏控制的TTS文案
        
        Args:
            reference_script: 参考文案
            topic: 新主题
            target_duration: 目标时长（秒），默认15秒
            
        Returns:
            Dict: 包含带节奏标记的台词
        """
        prompt = f"""你是短视频文案创作专家，专门为TTS合成创作台词。

【参考文案】
{reference_script}

【新主题】
{topic}

【重要 - 解决TTS不连贯问题】
1. 每句话严格控制在8-12个字
2. 句子之间用标点明确分隔
3. 总字数控制在{int(target_duration * 3)}-{int(target_duration * 3.5)}字
4. 分成4-6个短句，每句是一个完整的意思
5. 使用口语化表达（呢、吧、啊、哦）
6. 保持自嘲幽默风格

【输出格式】
JSON格式：
{{
    "segments": ["短句1", "短句2", "短句3", "短句4"],
    "full_script": "完整文案"
}}

直接返回JSON："""

        try:
            if self.model == "zhipu":
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "你是专业的短视频文案创作专家。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,
                )
                result_text = response.choices[0].message.content
            else:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "你是专业的短视频文案创作专家。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,
                    response_format={"type": "json_object"},
                )
                result_text = response.choices[0].message.content

            import json
            result = json.loads(result_text)

            segments = result.get("segments", [])
            full_script = result.get("full_script", "".join(segments))

            # 生成TTS专用版本（带详细停顿）
            tts_script = self._add_pause_markers(segments)

            # 生成带SSML标签的版本（如果TTS支持）
            ssml_script = self._generate_ssml(segments)

            # 计算实际字数和预估时长
            char_count = len(full_script)
            estimated_duration = char_count / 3.5  # 稍保守的估计

            return {
                "model_used": self.model,
                "segments": segments,
                "full_script": full_script,
                "tts_script": tts_script,
                "ssml_script": ssml_script,  # SSML格式（部分TTS支持）
                "target_duration": target_duration,
                "estimated_duration": round(estimated_duration, 1),
                "character_count": char_count,
                "words_per_segment": [len(s) for s in segments],
                "pacing_guide": self._generate_pacing_guide(segments)
            }

        except Exception as e:
            return {"error": str(e), "model_used": self.model}

    def _generate_ssml(self, segments: List[str]) -> str:
        """
        生成SSML格式（支持SSML的TTS可用）
        SSML可以更精确控制停顿、语速、语调
        """
        ssml_parts = []
        for i, seg in enumerate(segments):
            # 第一个句子不需要额外停顿
            if i == 0:
                ssml_parts.append(f'<speak><prosody rate="0.9">{seg}</prosody>')
            else:
                # 中间的句子加停顿
                ssml_parts.append(f'<break time="800ms"/><prosody rate="0.9">{seg}</prosody>')
        
        ssml_parts.append('</speak>')
        return "".join(ssml_parts)

    def _generate_pacing_guide(self, segments: List[str]) -> str:
        """生成节奏指南，帮助TTS合成时掌握节奏"""
        guide = []
        for i, seg in enumerate(segments):
            char_count = len(seg)
            # 估算每句的时长（假设每秒3.5字）
            duration = char_count / 3.5
            guide.append(f"句{i+1}: [{char_count}字] 约{duration:.1f}秒 - {seg}")
        
        return "\n".join(guide)

    def batch_generate(
        self,
        reference_scripts: List[str],
        topics: List[str],
        style: str = "自嘲幽默"
    ) -> List[Dict[str, Any]]:
        """批量生成文案"""
        results = []
        for topic in topics:
            # 使用第一个参考文案
            result = self.generate_for_tts(
                reference_scripts[0] if reference_scripts else "",
                [],
                topic,
                style
            )
            result["topic"] = topic
            results.append(result)
        return results


def interactive_mode():
    """交互式选择模式"""
    print("=" * 70)
    print("文案生成工具 - 选择模型")
    print("=" * 70)
    print("\n请选择模型:")
    print("  1. DeepSeek (推荐，频率限制宽松)")
    print("  2. 智谱 GLM-4.7-Flash")

    choice = input("\n请输入选项 (1/2，默认1): ").strip() or "1"

    model = "deepseek" if choice == "1" else "zhipu"

    print(f"\n已选择: {model.upper()}")

    # 输入参考信息
    print("\n请输入参考文案（直接回车使用默认示例）:")
    reference = input("参考文案: ").strip()
    if not reference:
        reference = "杭州老律师月入500待客之道 #律师的真实日常#vlog日常"

    print("\n请输入话题标签（用空格分隔，直接回车跳过）:")
    tags_input = input("标签: ").strip()
    hashtags = tags_input.split() if tags_input else []

    print("\n请输入新主题:")
    topic = input("新主题: ").strip()
    if not topic:
        topic = "青年律师如何应对职场压力"

    # 生成
    generator = ScriptGenerator(model=model)
    result = generator.generate_for_tts(reference, hashtags, topic)

    # 显示结果
    print("\n" + "=" * 70)
    print("生成结果")
    print("=" * 70)
    print(f"\n使用模型: {result.get('model_used', model).upper()}")
    print(f"预估时长: {result.get('estimated_duration', 0)} 秒")
    print(f"字数: {result.get('character_count', 0)} 字")

    if "error" in result:
        print(f"\n错误: {result['error']}")
        return

    # ========== TTS/数字人用 ==========
    print("\n" + "🎤 " * 20)
    print("【TTS/数字人用】分段台词")
    print("🎤 " * 20)
    for i, seg in enumerate(result["segments"], 1):
        print(f"  {i}. {seg}")

    print(f"\n【完整台词】(无停顿)")
    print(result["full_script"])

    print(f"\n【TTS标记版】(带停顿时间)")
    print(result["tts_script"])

    # ========== 平台发布用 ==========
    print("\n" + "📱 " * 20)
    print("【平台发布用】作品描述+引流")
    print("📱 " * 20)
    print(result.get("short_script", result["full_script"] + " " + " ".join(result.get("suggested_tags", []))))

    # 保存选项
    save = input("\n是否保存到文件? (y/n): ").strip().lower()
    if save == "y":
        filename = input("文件名 (默认: generated_script.txt): ").strip()
        if not filename:
            filename = "generated_script.txt"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"模型: {result.get('model_used', model)}\n")
            f.write(f"主题: {topic}\n")
            f.write(f"预估时长: {result.get('estimated_duration', 0)}秒\n\n")

            f.write("=" * 50 + "\n")
            f.write("【TTS/数字人用】\n")
            f.write("=" * 50 + "\n")
            f.write("【分段台词】\n")
            for i, seg in enumerate(result["segments"], 1):
                f.write(f"{i}. {seg}\n")
            f.write("\n【完整台词】\n")
            f.write(result["full_script"] + "\n\n")
            f.write("【TTS标记版】\n")
            f.write(result["tts_script"] + "\n\n")

            f.write("=" * 50 + "\n")
            f.write("【平台发布用】\n")
            f.write("=" * 50 + "\n")
            f.write("【发布文案】(可直接复制到抖音/小红书)\n")
            f.write(result.get("short_script", result["full_script"] + " " + " ".join(result.get("suggested_tags", []))))

        print(f"\n✓ 已保存到: {filename}")


# ============================================================================
# 便捷函数
# ============================================================================

def generate_script(
    topic: str,
    reference: str = "",
    model: str = "deepseek",
    target_duration: float = 20.0
) -> Dict[str, Any]:
    """
    快速生成文案

    示例:
        result = generate_script(
            topic="律师如何应对奇葩客户",
            reference="杭州老律师月入500待客之道",
            model="deepseek",  # 或 "zhipu"
            target_duration=30.0  # 30秒视频
        )
        # TTS/数字人用
        print(result["full_script"])
        print(result["segments"])  # 分段台词
        print(result["tts_script"])  # TTS标记版
        # 平台发布用
        print(result["short_script"])  # 带标签的短文案
    """
    if not reference:
        reference = "杭州老律师月入500待客之道 #律师的真实日常#vlog日常"

    generator = ScriptGenerator(model=model)
    return generator.generate_for_tts(reference, [], topic, target_duration=target_duration)


def generate_tts_script(
    topic: str,
    reference: str = "",
    target_duration: float = 15.0,
    model: str = "deepseek"
) -> Dict[str, Any]:
    """
    生成TTS优化版文案（解决不连贯问题）

    示例:
        result = generate_tts_script(
            topic="律师如何应对奇葩客户",
            reference="杭州老律师月入500待客之道",
            target_duration=15.0,  # 15秒视频
            model="deepseek"
        )
        print(result["tts_script"])      # 带停顿标记
        print(result["ssml_script"])     # SSML格式
        print(result["pacing_guide"])    # 节奏指南
    """
    if not reference:
        reference = "杭州老律师月入500待客之道 #律师的真实日常#vlog日常"

    generator = ScriptGenerator(model=model)
    return generator.generate_tts_with_pacing(reference, topic, target_duration)


if __name__ == "__main__":
    # 检查API Key
    has_zhipu = bool(os.getenv("ZAI_API_KEY"))
    has_deepseek = bool(os.getenv("DEEPSEEK_API_KEY"))

    if not has_zhipu and not has_deepseek:
        print("错误: 请在 .env 文件中设置 API Key")
        sys.exit(1)

    print(f"API Key 状态:")
    print(f"  ZAI_API_KEY: {'✓' if has_zhipu else '✗'}")
    print(f"  DEEPSEEK_API_KEY: {'✓' if has_deepseek else '✗'}")

    # 快速测试
    print("\n" + "=" * 70)
    print("快速测试 - DeepSeek")
    print("=" * 70)

    try:
        result = generate_script(
            topic="青年律师如何应对职场压力",
            reference="杭州老律师月入500待客之道",
            model="deepseek"
        )

        print(f"\n【完整文案】({result['character_count']}字, {result['estimated_duration']}秒)")
        print(result["full_script"])

        print(f"\n【分段台词】")
        for i, seg in enumerate(result["segments"], 1):
            print(f"  {i}. {seg}")

        print(f"\n【平台发布文案】")
        print(result.get("short_script", result["full_script"]))

        print(f"\n✓ 测试成功！")
        print(f"\n运行交互模式: python {Path(__file__).name} --interactive")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
