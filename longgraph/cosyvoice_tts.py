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

# 修复 Windows 控制台编码（只执行一次）
if sys.platform == "win32" and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 加载 .env 文件（从项目根目录）
from dotenv import load_dotenv
# 尝试从多个位置加载 .env
env_paths = [
    Path(__file__).parent.parent / '.env',  # 项目根目录
    Path(__file__).parent / '.env',          # 当前目录
]
loaded = False
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        loaded = True
        break
if not loaded:
    load_dotenv()  # 尝试从环境变量或默认位置加载

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

    def list_voices(self, prefix=None, page_index: int = 0, page_size: int = 10) -> list:
        """
        查询已创建的所有音色（使用官方 API）

        Args:
            prefix: 音色自定义前缀，仅允许数字和小写字母，长度小于10个字符
            page_index: 查询的页索引
            page_size: 查询页大小

        Returns:
            list: 音色信息列表，格式为：
                  [{'gmt_create': '2025-10-09 14:51:01',
                    'gmt_modified': '2025-10-09 14:51:07',
                    'status': 'OK',
                    'voice_id': 'cosyvoice-v3-myvoice-xxx'}]

            音色状态有三种：
                DEPLOYING： 审核中
                OK：审核通过，可调用
                UNDEPLOYED：审核不通过，不可调用
        """
        service = VoiceEnrollmentService()
        return service.list_voices(prefix=prefix, page_index=page_index, page_size=page_size)

    def get_ready_voices(self) -> list:
        """
        获取所有状态为 OK 的音色 ID

        Returns:
            list: 可用的音色 ID 列表
        """
        voices = self.list_voices()
        return [v["voice_id"] for v in voices if v["status"] == "OK"]

    def print_voices_status(self, prefix=None, page_index: int = 0, page_size: int = 10):
        """打印所有音色的状态"""
        voices = self.list_voices(prefix=prefix, page_index=page_index, page_size=page_size)

        if not voices:
            print("  暂无音色，请先创建音色")
            return

        print("\n  音色列表:")
        print("  " + "-" * 80)
        for v in voices:
            status_icon = "✓" if v["status"] == "OK" else "⏳" if v["status"] == "DEPLOYING" else "❌"
            voice_id = v.get('voice_id', 'N/A')
            status = v.get('status', 'UNKNOWN')
            gmt_create = v.get('gmt_create', 'N/A')
            gmt_modified = v.get('gmt_modified', 'N/A')
            print(f"  {status_icon} {voice_id}")
            print(f"     状态: {status}, 创建时间: {gmt_create}, 修改时间: {gmt_modified}")
        print("  " + "-" * 80)

    def speech(
        self,
        text: str,
        voice: str,
        model: Optional[str] = None,
        output_path: Optional[str] = None,
        max_retries: int = 6  # 增加重试次数以应对 WebSocket 连接超时
    ) -> bytes:
        """
        使用复刻音色进行语音合成

        Args:
            text: 要转换的文本
            voice: 音色 ID（通过 create_voice 创建）
            model: 模型名称，默认从 voice_id 自动推断
            output_path: 保存路径，如不指定则只返回音频数据
            max_retries: 最大重试次数（应对网络超时）

        Returns:
            bytes: 音频数据（如果指定了output_path，则返回文件路径字符串）
        """
        # 如果没有指定 model，尝试从 voice_id 中推断
        if model is None:
            # voice_id 格式分析:
            # - cosyvoice-v1-xxx
            # - cosyvoice-v2-xxx
            # - cosyvoice-v3-flash-xxx
            # - cosyvoice-v3-plus-xxx
            # - cosyvoice-v3.5-flash-xxx
            # - cosyvoice-v3.5-plus-xxx
            if voice.startswith('cosyvoice-v1'):
                model = 'cosyvoice-v1'
            elif voice.startswith('cosyvoice-v2'):
                model = 'cosyvoice-v2'
            elif voice.startswith('cosyvoice-v3-flash'):
                model = 'cosyvoice-v3-flash'
            elif voice.startswith('cosyvoice-v3-plus'):
                model = 'cosyvoice-v3-plus'
            elif voice.startswith('cosyvoice-v3.5-flash'):
                model = 'cosyvoice-v3.5-flash'
            elif voice.startswith('cosyvoice-v3.5-plus'):
                model = 'cosyvoice-v3.5-plus'
            else:
                model = self.DEFAULT_MODEL

        # 确保模型名始终是小写（Dashscope API 要求）
        model = model.lower() if model else self.DEFAULT_MODEL

        # 调试：打印推断的模型名（输出到 stderr 以便被日志捕获）
        # import sys
        # print(f"[DEBUG] speech() 推断的 model: '{model}', type: {type(model)}", file=sys.stderr, flush=True)

        # 清理文本
        clean_text = self._clean_text(text)

        # 重试机制处理 WebSocket 连接超时
        last_error = None
        for attempt in range(max_retries):
            try:
                # 调试：打印 model 值（输出到 stderr 以便被日志捕获）
                # import sys
                # print(f"[DEBUG] speech() 调用参数: model={model}, voice={voice[:30]}... (尝试 {attempt + 1}/{max_retries})", file=sys.stderr, flush=True)

                # 创建 SpeechSynthesizer 实例
                synthesizer = SpeechSynthesizer(model=model, voice=voice)

                # 修复 SDK 可能存在的模型名转换问题
                # Dashscope SDK 可能会将模型名转换为首字母大写，需要强制使用小写
                import json

                original_getStartRequest = synthesizer.request.getStartRequest

                def patched_getStartRequest(additional_params=None):
                    # 调用原始方法
                    request_json = original_getStartRequest(additional_params)
                    # 修改 JSON 中的模型名为小写
                    request_data = json.loads(request_json)
                    request_data['payload']['model'] = model
                    return json.dumps(request_data)

                synthesizer.request.getStartRequest = patched_getStartRequest

                # 同样修复 getContinueRequest
                original_getContinueRequest = synthesizer.request.getContinueRequest

                def patched_getContinueRequest(text):
                    request_json = original_getContinueRequest(text)
                    request_data = json.loads(request_json)
                    request_data['payload']['model'] = model
                    return json.dumps(request_data)

                synthesizer.request.getContinueRequest = patched_getContinueRequest

                # 修复 getFinishRequest（如果存在）
                if hasattr(synthesizer.request, 'getFinishRequest'):
                    original_getFinishRequest = synthesizer.request.getFinishRequest

                    def patched_getFinishRequest():
                        request_json = original_getFinishRequest()
                        request_data = json.loads(request_json)
                        request_data['payload']['model'] = model
                        return json.dumps(request_data)

                    synthesizer.request.getFinishRequest = patched_getFinishRequest

                # print(f"[DEBUG] 已应用 monkey-patch 修复模型名", file=sys.stderr, flush=True)
                # print(f"[DEBUG] SpeechSynthesizer.model={synthesizer.model}", file=sys.stderr, flush=True)
                audio_data = synthesizer.call(clean_text)

                # 验证返回的音频数据
                if audio_data is None:
                    raise Exception(f"API返回了空数据。可能原因：1) 音色ID '{voice}' 无效 2) 文本不符合要求")

                if len(audio_data) == 0:
                    raise Exception(f"API返回了空音频（0字节）。可能原因：1) 音色ID '{voice}' 无效或不可用 2) 文本问题")

                print(f"✓ 语音合成成功，Request ID: {synthesizer.get_last_request_id()}, 音频大小: {len(audio_data)} bytes")

                # 保存到文件
                if output_path:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(audio_data)
                    print(f"✓ 音频已保存到: {output_path}")
                    return output_path  # 返回文件路径

                return audio_data

            except Exception as e:
                last_error = e
                error_msg = str(e)
                # 如果是 WebSocket 超时错误，且不是最后一次尝试，则立即重试
                if ("websocket" in error_msg.lower() and "timeout" in error_msg.lower()) or "could not established" in error_msg.lower():
                    if attempt < max_retries - 1:
                        print(f"⚠ WebSocket 连接超时，立即重试 ({attempt + 1}/{max_retries})...")
                        continue
                # 其他错误或最后一次尝试，直接抛出
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
