"""
阿里云 CosyVoice 语音复刻 TTS 模块
文档: https://help.aliyun.com/zh/model-studio/
"""

import os
import sys
import io
import time
from pathlib import Path
from typing import Optional, Literal
import json

# 修复 Windows 控制台编码
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv('.env')

import dashscope
from dashscope.audio.tts_v2 import VoiceEnrollmentService, SpeechSynthesizer


class CosyVoiceTTSClient:
    """阿里云 CosyVoice TTS 客户端"""

    # 模型选择
    MODELS = {
        "cosyvoice-v3.5-plus": "CosyVoice v3.5 Plus (最新，推荐)",
        "cosyvoice-v1": "CosyVoice v1",
        "cosyvoice-v1-zh": "CosyVoice v1 中文",
    }

    # 默认模型
    DEFAULT_MODEL = "cosyvoice-v3.5-plus"

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: DASHSCOPE_API_KEY，如不指定则从环境变量读取
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 DASHSCOPE_API_KEY 环境变量")

        dashscope.api_key = self.api_key

        # 设置 API 地址（北京地域，如需新加坡地域请修改）
        dashscope.base_websocket_api_url = 'wss://dashscope.aliyuncs.com/api-ws/v1/inference'
        dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

        # 音色缓存（voice_id -> voice_info）
        self._voice_cache = {}

    def create_voice(
        self,
        audio_url: str,
        prefix: str = "myvoice",
        model: Optional[str] = None,
        wait_ready: bool = True,
        max_attempts: int = 30,
        poll_interval: int = 10
    ) -> dict:
        """
        创建复刻音色

        Args:
            audio_url: 公网可访问的音频 URL
            prefix: 音色前缀（仅数字和小写字母，小于10个字符）
            model: 模型名称，默认使用 DEFAULT_MODEL
            wait_ready: 是否等待音色准备就绪
            max_attempts: 最大轮询次数
            poll_interval: 轮询间隔（秒）

        Returns:
            dict: 包含 voice_id 和状态信息
        """
        model = model or self.DEFAULT_MODEL

        print(f"--- 开始创建音色复刻 ---")
        print(f"模型: {model}")
        print(f"音频 URL: {audio_url}")

        service = VoiceEnrollmentService()

        try:
            voice_id = service.create_voice(
                target_model=model,
                prefix=prefix,
                url=audio_url
            )
            print(f"✓ 音色复刻已提交，Request ID: {service.get_last_request_id()}")
            print(f"✓ 生成的 Voice ID: {voice_id}")

        except Exception as e:
            raise Exception(f"音色创建失败: {e}")

        if not wait_ready:
            return {"voice_id": voice_id, "status": "pending"}

        # 轮询等待音色就绪
        print(f"\n--- 轮询等待音色就绪 ---")
        for attempt in range(max_attempts):
            try:
                voice_info = service.query_voice(voice_id=voice_id)
                status = voice_info.get("status")
                print(f"尝试 {attempt + 1}/{max_attempts}: 状态 '{status}'")

                if status == "OK":
                    print("✓ 音色已就绪，可以用于合成")
                    self._voice_cache[voice_id] = voice_info
                    return {"voice_id": voice_id, "status": "ready", "info": voice_info}

                elif status == "UNDEPLOYED":
                    raise RuntimeError(f"音色处理失败，状态: {status}")

                # 继续等待
                time.sleep(poll_interval)

            except Exception as e:
                print(f"轮询出错: {e}")
                time.sleep(poll_interval)

        raise RuntimeError("音色准备超时")

    def query_voice(self, voice_id: str) -> dict:
        """
        查询音色状态

        Args:
            voice_id: 音色 ID

        Returns:
            dict: 音色信息
        """
        service = VoiceEnrollmentService()
        return service.query_voice(voice_id=voice_id)

    def speech(
        self,
        text: str,
        voice: str,
        model: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> bytes:
        """
        使用复刻音色进行语音合成

        Args:
            text: 要转换的文本
            voice: 音色 ID（通过 create_voice 创建）
            model: 模型名称，默认使用 DEFAULT_MODEL
            output_path: 保存路径，如不指定则只返回音频数据

        Returns:
            bytes: 音频数据
        """
        model = model or self.DEFAULT_MODEL

        # 清理文本
        clean_text = self._clean_text(text)

        try:
            synthesizer = SpeechSynthesizer(model=model, voice=voice)
            audio_data = synthesizer.call(clean_text)

            print(f"✓ 语音合成成功，Request ID: {synthesizer.get_last_request_id()}")

            # 保存到文件
            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                print(f"✓ 音频已保存到: {output_path}")

            return audio_data

        except Exception as e:
            raise Exception(f"语音合成失败: {e}")

    def speech_from_segments(
        self,
        segments: list,
        voice: str,
        model: Optional[str] = None,
        output_dir: str = "data/audio",
        merge: bool = True
    ) -> str:
        """
        从分段台词合成语音

        Args:
            segments: 分段台词列表
            voice: 音色 ID
            model: 模型名称
            output_dir: 输出目录
            merge: 是否合并为单个音频文件

        Returns:
            str: 音频文件路径
        """
        model = model or self.DEFAULT_MODEL

        audio_files = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 为每段生成音频
        for i, segment in enumerate(segments):
            filename = output_path / f"segment_{i:03d}.mp3"
            self.speech(segment, voice=voice, model=model, output_path=str(filename))
            audio_files.append(str(filename))

        if merge and len(audio_files) > 1:
            merged_path = output_path / "merged.mp3"
            self._merge_audio(audio_files, str(merged_path))
            return str(merged_path)

        return str(audio_files[0]) if audio_files else ""

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

    def _merge_audio(self, audio_files: list, output_path: str):
        """合并多个音频文件（需要ffmpeg）"""
        try:
            import subprocess

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
                "-y",
                output_path
            ]

            subprocess.run(cmd, check=True, capture_output=True)
            print(f"✓ 音频已合并: {output_path}")

        except FileNotFoundError:
            print("⚠ ffmpeg未安装，无法合并音频文件")
        except Exception as e:
            print(f"⚠ 合并音频失败: {e}")


class TTSWorkflow:
    """TTS 工作流 - 从文案生成到音频"""

    def __init__(self, model: str = "deepseek", use_cosyvoice: bool = True):
        """
        Args:
            model: 文案生成模型 (deepseek/zhipu)
            use_cosyvoice: 是否使用 CosyVoice（否则使用智谱 TTS）
        """
        from script_generator import ScriptGenerator

        self.model = model
        self.generator = ScriptGenerator(model=model)
        self.use_cosyvoice = use_cosyvoice

        if use_cosyvoice:
            self.tts_client = CosyVoiceTTSClient()
        else:
            from glm_tts import GLMTTSClient
            self.tts_client = GLMTTSClient()

    def generate_and_synthesize(
        self,
        topic: str,
        reference: str = "",
        voice: str = None,
        output_dir: str = "data/output",
        target_duration: float = 15.0
    ) -> dict:
        """
        一键生成文案并合成语音

        Args:
            topic: 主题
            reference: 参考文案
            voice: 音色 ID（CosyVoice）或音色名（智谱）
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
        print(f"\n[2/3] 合成语音...")
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if self.use_cosyvoice:
            if not voice:
                raise ValueError("使用 CosyVoice 时必须指定 voice_id（请先通过 create_voice 创建）")

            audio_file = output_path / "speech.mp3"
            self.tts_client.speech(
                result["full_script"],
                voice=voice,
                output_path=str(audio_file)
            )
        else:
            if not voice:
                voice = "tongtong"

            audio_file = output_path / f"speech_{voice}.wav"
            self.tts_client.speech(
                result["full_script"],
                voice=voice,
                output_path=str(audio_file)
            )

        # 3. 生成分段音频
        print(f"\n[3/3] 生成分段音频...")
        segments_dir = output_path / "segments"
        self.tts_client.speech_from_segments(
            result["segments"],
            voice=voice,
            output_dir=str(segments_dir),
            merge=False
        )

        # 保存元数据
        metadata = {
            "topic": topic,
            "model": self.model,
            "tts_engine": "cosyvoice" if self.use_cosyvoice else "zhipu",
            "voice": voice,
            "target_duration": target_duration,
            "estimated_duration": result.get("estimated_duration", 0),
            "segments": result["segments"],
            "full_script": result["full_script"],
            "audio_file": str(audio_file),
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
            "metadata_file": str(metadata_file)
        }


# 便捷函数
def text_to_speech(
    text: str,
    voice: str,
    output_path: str = "output.mp3"
) -> str:
    """
    快速文字转语音（使用 CosyVoice）

    Args:
        text: 要转换的文本
        voice: 音色 ID（通过 create_voice 创建）
        output_path: 输出文件路径

    示例:
        # 先创建音色
        client = CosyVoiceTTSClient()
        result = client.create_voice(audio_url="https://example.com/voice.wav")
        voice_id = result["voice_id"]

        # 再合成语音
        audio_path = text_to_speech("你好，世界！", voice=voice_id)
    """
    client = CosyVoiceTTSClient()
    client.speech(text, voice=voice, output_path=output_path)
    return output_path


def create_voice_from_url(
    audio_url: str,
    prefix: str = "myvoice"
) -> str:
    """
    从音频 URL 创建音色复刻

    Args:
        audio_url: 公网可访问的音频 URL
        prefix: 音色前缀

    Returns:
        str: 音色 ID
    """
    client = CosyVoiceTTSClient()
    result = client.create_voice(audio_url=audio_url, prefix=prefix)
    return result["voice_id"]


if __name__ == "__main__":
    print("=" * 60)
    print("CosyVoice TTS 测试")
    print("=" * 60)

    # 检查 API Key
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("✗ 请设置 DASHSCOPE_API_KEY 环境变量")
        exit(1)

    print(f"✓ API Key 已设置")

    # 可用模型
    print("\n可用模型:")
    for key, desc in CosyVoiceTTSClient.MODELS.items():
        print(f"  - {key}: {desc}")

    # 示例：创建音色并合成语音
    print("\n" + "=" * 60)
    print("示例：创建音色并合成语音")
    print("=" * 60)

    # 使用示例音频 URL（请替换为你自己的）
    EXAMPLE_AUDIO_URL = "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/cosyvoice/cosyvoice-zeroshot-sample.wav"

    client = CosyVoiceTTSClient()

    try:
        # 创建音色
        voice_result = client.create_voice(
            audio_url=EXAMPLE_AUDIO_URL,
            prefix="test"
        )
        voice_id = voice_result["voice_id"]

        # 合成语音
        audio_path = text_to_speech(
            text="你好，这是用 CosyVoice 复刻的声音合成的语音！",
            voice=voice_id,
            output_path="data/audio/cosyvoice_test.mp3"
        )

        print(f"\n✓ 测试完成，音频文件: {audio_path}")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
