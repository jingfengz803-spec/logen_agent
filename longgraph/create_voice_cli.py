"""
音色复刻 CLI 工具
使用方法：
    python create_voice_cli.py
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# 从项目根目录加载 .env 文件
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / '.env', override=True)

from cosyvoice_tts import CosyVoiceTTSClient
from config import APIKeys, TTSConfig


def print_banner():
    print("=" * 70)
    print(" CosyVoice 音色复刻工具")
    print("=" * 70)


def check_api_key():
    """检查 API Key"""
    try:
        APIKeys.get_dashscope()
        print("✓ DASHSCOPE_API_KEY 已配置\n")
        return True
    except ValueError:
        print("✗ 未配置 DASHSCOPE_API_KEY")
        print("  请在 .env 文件中设置: DASHSCOPE_API_KEY=your_key\n")
        return False


def create_voice_flow():
    """创建音色流程"""
    print_banner()

    if not check_api_key():
        return

    # 显示可用模型
    print("可用模型:")
    models = TTSConfig.get_tts_config("cosyvoice")["models"]
    for i, (model_id, desc) in enumerate(models.items(), 1):
        default = " (默认)" if model_id == TTSConfig.COSYVOICE_DEFAULT_MODEL else ""
        print(f"  {i}. {model_id} - {desc}{default}")

    # 输入音频 URL
    print("\n" + "-" * 70)
    print("【步骤 1/5】输入参考音频 URL")
    print("-" * 70)
    print("要求:")
    print("  - 公网可访问的 HTTP/HTTPS URL")
    print("  - 建议时长: 10-30 秒")
    print("  - 清晰的人声，少背景音")
    print("  - 支持格式: mp3, wav, m4a 等")
    print("\n示例: https://example.com/voice.mp3")

    audio_url = input("\n音频 URL: ").strip()
    if not audio_url:
        print("✗ 已取消")
        return

    # 输入前缀
    print("\n" + "-" * 70)
    print("【步骤 2/5】设置音色前缀")
    print("-" * 70)
    print("前缀用于识别音色（仅数字、字母、下划线，不超过10个字符）")
    print("生成的音色名格式: 模型名-前缀-唯一标识")
    print("例如: cosyvoice-v3.5-flash-myzhangsan-xxxxxxxx")

    prefix = input("\n音色前缀 (默认: myvoice): ").strip() or "myvoice"

    # 选择模型
    print("\n" + "-" * 70)
    print("【步骤 3/5】选择模型")
    print("-" * 70)
    model_choice = input(f"模型 (直接回车使用默认 {TTSConfig.COSYVOICE_DEFAULT_MODEL}): ").strip()
    model = model_choice if model_choice else TTSConfig.COSYVOICE_DEFAULT_MODEL

    # 语言提示
    print("\n" + "-" * 70)
    print("【步骤 4/5】语言设置")
    print("-" * 70)
    print("可选语言: zh(中文), en(英文), ja(日文), ko(韩文), fr(法语), de(德语), ru(俄语), pt(葡萄牙语), th(泰语), id(印尼语), vi(越南语)")

    language = input("语言代码 (默认: zh): ").strip() or "zh"

    # 是否预处理
    print("\n" + "-" * 70)
    print("【步骤 5/5】音频预处理")
    print("-" * 70)
    print("开启预处理会对音频进行降噪、增强、音量规整")

    preprocess = input("是否开启预处理? (Y/n): ").strip().lower()
    enable_preprocess = preprocess != 'n'

    # 确认
    print("\n" + "=" * 70)
    print("确认创建音色")
    print("=" * 70)
    print(f"  音频 URL:   {audio_url}")
    print(f"  前缀:       {prefix}")
    print(f"  模型:       {model}")
    print(f"  语言:       {language}")
    print(f"  预处理:     {'是' if enable_preprocess else '否'}")

    confirm = input("\n确认创建? (Y/n): ").strip().lower()
    if confirm == 'n':
        print("✗ 已取消")
        return

    # 创建音色
    print("\n" + "=" * 70)
    print("开始创建音色...")
    print("=" * 70)

    client = CosyVoiceTTSClient()

    try:
        result = client.create_voice(
            audio_url=audio_url,
            prefix=prefix,
            model=model,
            language_hints=[language],
            enable_preprocess=enable_preprocess,
            wait_ready=False  # 先不等待，手动查询状态
        )

        voice_id = result["voice_id"]
        print(f"\n✓ 音色已提交创建!")
        print(f"✓ Voice ID: {voice_id}")
        print(f"\n提示: 音色需要审核通过后才能使用，通常需要 1-5 分钟")

        # 询问是否等待
        wait = input("\n是否等待审核完成? (Y/n): ").strip().lower()
        if wait != 'n':
            wait_for_voice_ready(client, voice_id)

        # 显示当前所有音色
        print("\n" + "=" * 70)
        print("当前所有音色状态:")
        print("=" * 70)
        client.print_voices_status()

        # 保存 voice_id
        save_voice_id(voice_id, prefix, audio_url)

    except Exception as e:
        print(f"\n✗ 创建失败: {e}")


def wait_for_voice_ready(client, voice_id, max_attempts=30, poll_interval=10):
    """等待音色就绪"""
    print("\n" + "-" * 70)
    print("等待音色审核完成...")
    print("-" * 70)

    for attempt in range(max_attempts):
        try:
            voice_info = client.query_voice(voice_id)
            status = voice_info.get("status")

            if status == "OK":
                print(f"\n✓ 音色已就绪! (耗时 {attempt * poll_interval} 秒)")
                print(f"✓ Voice ID: {voice_id}")
                print(f"\n现在可以使用此音色进行语音合成了!")
                return True

            elif status == "UNDEPLOYED":
                print(f"\n✗ 音色审核未通过，状态: {status}")
                return False

            else:
                print(f"  [{attempt + 1}/{max_attempts}] 状态: {status}...")

        except Exception as e:
            print(f"  查询出错: {e}")

        time.sleep(poll_interval)

    print(f"\n⚠ 等待超时 (已等待 {max_attempts * poll_interval} 秒)")
    print(f"  音色可能仍在处理中，Voice ID: {voice_id}")
    print(f"  稍后可使用 list_voices() 查询状态")
    return False


def save_voice_id(voice_id, prefix, audio_url):
    """保存 voice_id 到文件"""
    voices_file = "data/voices.txt"
    os.makedirs(os.path.dirname(voices_file), exist_ok=True)

    with open(voices_file, "a", encoding="utf-8") as f:
        f.write(f"{voice_id} | {prefix} | {audio_url}\n")

    print(f"\n✓ Voice ID 已保存到: {voices_file}")


def list_voices_flow():
    """列出所有音色"""
    print_banner()

    client = CosyVoiceTTSClient()
    client.print_voices_status()

    # 显示可用音色
    ready_voices = client.get_ready_voices()
    if ready_voices:
        print(f"\n可直接使用的 Voice ID:")
        for vid in ready_voices:
            print(f"  {vid}")


def test_tts_flow():
    """测试语音合成"""
    print_banner()

    if not check_api_key():
        return

    # 先列出可用音色
    client = CosyVoiceTTSClient()
    ready_voices = client.get_ready_voices()

    if not ready_voices:
        print("✗ 没有可用的音色，请先创建音色")
        return

    print("\n可用音色:")
    for i, vid in enumerate(ready_voices, 1):
        print(f"  {i}. {vid}")

    print("\n" + "-" * 70)
    voice_choice = input("\n选择音色序号或直接输入 Voice ID: ").strip()

    if voice_choice.isdigit():
        idx = int(voice_choice) - 1
        if 0 <= idx < len(ready_voices):
            voice_id = ready_voices[idx]
        else:
            print("✗ 无效选择")
            return
    else:
        voice_id = voice_choice

    # 输入测试文本
    text = input("\n输入要合成的文本 (默认: 你好，这是测试语音): ").strip()
    if not text:
        text = "你好，这是测试语音"

    output_path = input("\n输出路径 (默认: data/output/test.mp3): ").strip()
    if not output_path:
        output_path = "data/output/test.mp3"

    print("\n开始合成...")
    try:
        client.speech(text, voice=voice_id, output_path=output_path)
        print(f"\n✓ 合成完成: {output_path}")
    except Exception as e:
        print(f"\n✗ 合成失败: {e}")


def main_menu():
    """主菜单"""
    while True:
        print_banner()
        print("\n请选择操作:")
        print("  1. 创建新音色")
        print("  2. 查看所有音色状态")
        print("  3. 测试语音合成")
        print("  0. 退出")

        choice = input("\n请输入选项 (0-3): ").strip()

        if choice == "1":
            create_voice_flow()
        elif choice == "2":
            list_voices_flow()
        elif choice == "3":
            test_tts_flow()
        elif choice == "0":
            print("\n再见!")
            break
        else:
            print("\n✗ 无效选项")

        input("\n按回车继续...")


if __name__ == "__main__":
    main_menu()
