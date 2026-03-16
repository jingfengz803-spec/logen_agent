"""
智谱 GLM-TTS 文字转语音模块
文档: https://open.bigmodel.cn/dev/api#audio
"""

import os
import sys
import io
import subprocess
import requests
from pathlib import Path
from typing import Literal, Optional
import json

# 修复 Windows 控制台编码
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv('.env')


class GLMTTSClient:
    """智谱 TTS 客户端"""

    # API 地址
    API_URL = "https://open.bigmodel.cn/api/paas/v4/audio/speech"

    # 可用音色
    VOICES = {
        "tongtong": "通通 (女声，亲切)",
        "zhiqiang": "志强 (男声，稳重)",
    }

    # 支持的格式 - 根据智谱文档
    FORMATS = ["mp3", "wav", "pcm"]  # 注意：实际支持的格式可能有所不同

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: ZAI_API_KEY，如不指定则从环境变量读取
        """
        self.api_key = api_key or os.getenv("ZAI_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 ZAI_API_KEY 环境变量")

    def speech(
        self,
        text: str,
        voice: Literal["tongtong", "zhiqiang"] = "tongtong",
        response_format: Literal["wav", "mp3", "pcm"] = "wav",
        speed: float = 1.0,
        output_path: Optional[str] = None
    ) -> bytes:
        """
        文字转语音

        Args:
            text: 要转换的文本
            voice: 音色选择
            response_format: 返回格式 (wav/mp3/pcm)
            speed: 语速 (0.5-2.0)
            output_path: 保存路径，如不指定则只返回音频数据

        Returns:
            bytes: 音频数据
        """
        # 清理文本 - 移除停顿标记（如果有）
        clean_text = self._clean_text(text)

        payload = {
            "model": "glm-tts",
            "input": clean_text,
            "voice": voice,
            "response_format": response_format
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                self.API_URL,
                json=payload,
                headers=headers,
                timeout=60
            )

            if response.status_code != 200:
                error_msg = response.text
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error", {}).get("message", error_msg)
                except:
                    pass
                raise Exception(f"TTS请求失败: {error_msg}")

            audio_data = response.content

            # 保存到文件
            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                print(f"✓ 音频已保存到: {output_path}")

            return audio_data

        except Exception as e:
            raise Exception(f"TTS合成失败: {str(e)}")

    def _clean_text(self, text: str) -> str:
        """清理文本，移除停顿标记等特殊符号"""
        import re

        # 移除停顿时间标记 [0.3] [1.0] 等
        text = re.sub(r'\[\d+\.?\d*\]', '', text)

        # 移除SSML标签
        text = re.sub(r'<[^>]+>', '', text)

        # 移除多余空格
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def speech_from_segments(
        self,
        segments: list,
        voice: str = "tongtong",
        output_dir: str = "data/audio",
        merge: bool = True
    ) -> str:
        """
        从分段台词合成语音

        Args:
            segments: 分段台词列表
            voice: 音色
            output_dir: 输出目录
            merge: 是否合并为单个音频文件（需要额外工具）

        Returns:
            str: 音频文件路径
        """
        import tempfile
        import subprocess

        audio_files = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 为每段生成音频
        for i, segment in enumerate(segments):
            filename = output_path / f"segment_{i:03d}.wav"
            self.speech(segment, voice=voice, output_path=str(filename))
            audio_files.append(str(filename))

        if merge and len(audio_files) > 1:
            # 合并音频（需要ffmpeg）
            merged_path = output_path / "merged.wav"
            self._merge_audio(audio_files, str(merged_path))
            return str(merged_path)

        return str(audio_files[0]) if audio_files else ""

    def _merge_audio(self, audio_files: list, output_path: str):
        """合并多个音频文件（需要ffmpeg）"""
        try:
            # 构建ffmpeg命令
            inputs = []
            for f in audio_files:
                inputs.extend(["-i", f])

            filter_complex = "".join([f"[{i}:0]" for i in range(len(audio_files))])
            filter_complex += f"concat=n={len(audio_files)}:v=0:a=1[out]"

            cmd = [
                "ffmpeg",
                *inputs,
                "-filter_complex", filter_complex,
                "-map", "[out]",
                "-y",  # 覆盖已存在的文件
                output_path
            ]

            subprocess.run(cmd, check=True, capture_output=True)
            print(f"✓ 音频已合并: {output_path}")

        except FileNotFoundError:
            print("⚠ ffmpeg未安装，无法合并音频文件")
            print("  请安装ffmpeg: https://ffmpeg.org/download.html")
            print("  或单独使用各段音频文件")
        except Exception as e:
            print(f"⚠ 合并音频失败: {e}")


class TTSWorkflow:
    """TTS 工作流 - 从文案生成到音频"""

    def __init__(self, model: str = "deepseek", use_cosyvoice: bool = False):
        """
        Args:
            model: 文案生成模型 (deepseek/zhipu)
            use_cosyvoice: 是否使用 CosyVoice（否则使用智谱 TTS）
        """
        from script_generator import ScriptGenerator

        self.model = model
        self.generator = ScriptGenerator(model=model)

        if use_cosyvoice:
            from cosyvoice_tts import CosyVoiceTTSClient
            self.tts_client = CosyVoiceTTSClient()
        else:
            self.tts_client = GLMTTSClient()

    def generate_and_synthesize(
        self,
        topic: str,
        reference: str = "",
        voice: str = "tongtong",
        output_dir: str = "data/output",
        target_duration: float = 15.0
    ) -> dict:
        """
        一键生成文案并合成语音

        Args:
            topic: 主题
            reference: 参考文案
            voice: 音色
            output_dir: 输出目录
            target_duration: 目标时长

        Returns:
            dict: 包含文案和音频文件路径
        """
        print("=" * 60)
        print("TTS 工作流")
        print("=" * 60)

        # 1. 生成文案
        print("\n[1/3] 生成文案...")
        if not reference:
            reference = "杭州老律师月入500待客之道"

        result = self.generator.generate_tts_with_pacing(
            reference, topic, target_duration
        )

        if "error" in result:
            print(f"✗ 文案生成失败: {result['error']}")
            return result

        print(f"✓ 文案生成完成 ({result['character_count']}字, {result['estimated_duration']}秒)")

        # 2. 合成完整音频
        print(f"\n[2/3] 合成语音 (音色: {voice})...")
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        audio_file = output_path / f"speech_{voice}.wav"
        self.tts_client.speech(
            result["full_script"],
            voice=voice,
            output_path=str(audio_file)
        )

        # 3. 生成分段音频（可选，用于更精细控制）
        print(f"\n[3/3] 生成分段音频...")
        segments_dir = output_path / "segments"
        segment_audio = self.tts_client.speech_from_segments(
            result["segments"],
            voice=voice,
            output_dir=str(segments_dir),
            merge=False
        )

        # 保存元数据
        metadata = {
            "topic": topic,
            "model": self.model,
            "voice": voice,
            "target_duration": target_duration,
            "estimated_duration": result.get("estimated_duration", 0),
            "segments": result["segments"],
            "full_script": result["full_script"],
            "audio_file": str(audio_file),
            "segment_files": [f"{segments_dir}/segment_{i:03d}.mp3" for i in range(len(result["segments"]))]
        }

        metadata_file = output_path / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"\n✓ 全部完成!")
        print(f"  - 完整音频: {audio_file}")
        print(f"  - 分段音频: {segments_dir}/")
        print(f"  - 元数据: {metadata_file}")

        return {
            **result,
            "audio_file": str(audio_file),
            "segment_files": metadata["segment_files"],
            "metadata_file": str(metadata_file)
        }


# 便捷函数
def text_to_speech(
    text: str,
    voice: str = "tongtong",
    output_path: str = "output.wav"
) -> str:
    """
    快速文字转语音

    示例:
        audio_path = text_to_speech(
            text="你好，今天天气不错",
            voice="tongtong",
            output_path="hello.mp3"
        )
    """
    client = GLMTTSClient()
    client.speech(text, voice=voice, output_path=output_path)
    return output_path


def generate_speech(
    topic: str,
    reference: str = "",
    voice: str = "tongtong",
    model: str = "deepseek"
) -> dict:
    """
    生成文案并合成语音（一键）

    示例:
        result = generate_speech(
            topic="律师如何应对奇葩客户",
            voice="zhiqiang",  # 男声
            model="deepseek"
        )
        print(result["audio_file"])
    """
    workflow = TTSWorkflow(model=model)
    return workflow.generate_and_synthesize(topic, reference, voice)


if __name__ == "__main__":
    print("=" * 60)
    print("智谱 TTS 测试")
    print("=" * 60)

    # 检查 API Key
    api_key = os.getenv("ZAI_API_KEY")
    if not api_key:
        print("✗ 请设置 ZAI_API_KEY 环境变量")
        exit(1)

    print(f"✓ API Key 已设置")

    # 显示可用音色
    print("\n可用音色:")
    for key, desc in GLMTTSClient.VOICES.items():
        print(f"  - {key}: {desc}")

    # 测试1：简单文字转语音
    print("\n" + "=" * 60)
    print("测试1: 简单文字转语音")
    print("=" * 60)

    text_to_speech(
        text="你好，我是黄金律师。月入五百，依然快乐！",
        voice="tongtong",
        output_path="data/audio/test_tts.wav"
    )

    # 测试2：生成文案并合成
    print("\n" + "=" * 60)
    print("测试2: 生成文案并合成语音")
    print("=" * 60)

    result = generate_speech(
        topic="律师如何应对奇葩客户",
        reference="杭州老律师月入500待客之道",
        voice="tongtong",
        model="deepseek"
    )

    print(f"\n生成的文案:")
    print(result["full_script"])

    print(f"\n音频文件: {result.get('audio_file', 'N/A')}")
