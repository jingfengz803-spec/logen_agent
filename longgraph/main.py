"""
文案生成与TTS合成 - 主入口
整合：文案生成 + TTS合成
"""

import os
import sys
import io

# 修复编码
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from dotenv import load_dotenv
from pathlib import Path

# 加载环境变量
load_dotenv('.env')

from script_generator import ScriptGenerator, generate_script, generate_tts_script
from glm_tts import GLMTTSClient, TTSWorkflow, text_to_speech, generate_speech
from cosyvoice_tts import CosyVoiceTTSClient


def show_menu():
    """显示菜单"""
    print("\n" + "=" * 60)
    print("文案生成与TTS合成工具")
    print("=" * 60)
    print("\n请选择功能:")
    print("  1. 生成文案 (DeepSeek)")
    print("  2. 生成文案 (智谱 GLM)")
    print("  3. 文字转语音 (智谱 TTS)")
    print("  4. 一键生成：文案 + 语音 (智谱)")
    print("  5. 创建 CosyVoice 音色复刻")
    print("  6. 文字转语音 (CosyVoice)")
    print("  7. 一键生成：文案 + 语音 (CosyVoice)")
    print("  0. 退出")


def mode_generate_script(model: str):
    """模式1-2: 生成文案"""
    print(f"\n【文案生成 - {model.upper()}】")

    # 输入参考文案
    print("\n请输入参考文案 (直接回车使用默认示例):")
    reference = input("参考文案: ").strip()
    if not reference:
        reference = "杭州老律师月入500待客之道 #律师的真实日常#vlog日常"
        print(f"使用默认: {reference}")

    # 输入新主题
    print("\n请输入新主题:")
    topic = input("新主题: ").strip()
    if not topic:
        topic = "青年律师如何应对职场压力"
        print(f"使用默认: {topic}")

    # 生成
    generator = ScriptGenerator(model=model)
    result = generator.generate_for_tts(reference, [], topic)

    if "error" in result:
        print(f"\n错误: {result['error']}")
        return

    # 显示结果
    print("\n" + "-" * 60)
    print("【TTS/数字人用】分段台词")
    print("-" * 60)
    for i, seg in enumerate(result["segments"], 1):
        print(f"  {i}. {seg}")

    print(f"\n【平台发布用】作品描述")
    print("-" * 60)
    print(result.get("short_script", result["full_script"]))

    print(f"\n预估时长: {result['estimated_duration']}秒")

    # 保存选项
    save = input("\n是否保存到文件? (y/n): ").strip().lower()
    if save == "y":
        from script_generator import ScriptGenerator as SG
        filename = input("文件名 (默认: script.txt): ").strip()
        if not filename:
            filename = "data/script.txt"

        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"模型: {model}\n")
            f.write(f"主题: {topic}\n\n")
            f.write(f"完整文案:\n{result['full_script']}\n\n")
            f.write(f"分段台词:\n")
            for i, seg in enumerate(result["segments"], 1):
                f.write(f"{i}. {seg}\n")
            f.write(f"\n发布文案:\n{result.get('short_script', '')}")
        print(f"\n已保存到: {filename}")


def mode_tts():
    """模式3: 文字转语音"""
    print("\n【文字转语音 - GLM-TTS】")

    # 显示可用音色
    print("\n可用音色:")
    for key, desc in GLMTTSClient.VOICES.items():
        print(f"  - {key}: {desc}")

    # 选择音色
    voice = input("\n选择音色 (默认tongtong): ").strip() or "tongtong"

    # 输入文字
    print("\n请输入要转换的文字:")
    text = input("文字: ").strip()
    if not text:
        text = "你好，我是黄金律师。月入五百，依然快乐！"
        print(f"使用默认: {text}")

    # 输出路径
    output_path = input("输出文件 (默认: output.wav): ").strip()
    if not output_path:
        output_path = "data/output.wav"

    # 合成
    client = GLMTTSClient()
    client.speech(text, voice=voice, output_path=output_path)

    print(f"\n已保存到: {output_path}")


def mode_full_workflow():
    """模式4: 一键生成：文案 + 语音"""
    print("\n【一键生成：文案 + 语音 (智谱 TTS)】")

    # 显示可用音色
    print("\n可用音色:")
    for key, desc in GLMTTSClient.VOICES.items():
        print(f"  - {key}: {desc}")

    # 选择模型
    print("\n选择文案模型:")
    print("  1. DeepSeek (推荐)")
    print("  2. 智谱 GLM")
    model_choice = input("选择 (默认1): ").strip() or "1"
    model = "deepseek" if model_choice == "1" else "zhipu"

    # 选择音色
    voice = input("\n选择音色 (默认tongtong): ").strip() or "tongtong"

    # 输入参考文案
    print("\n请输入参考文案 (直接回车使用默认示例):")
    reference = input("参考文案: ").strip()
    if not reference:
        reference = "杭州老律师月入500待客之道 #律师的真实日常#vlog日常"

    # 输入新主题
    print("\n请输入新主题:")
    topic = input("新主题: ").strip()
    if not topic:
        topic = "律师如何应对奇葩客户"

    # 执行工作流
    workflow = TTSWorkflow(model=model, use_cosyvoice=False)
    result = workflow.generate_and_synthesize(
        topic=topic,
        reference=reference,
        voice=voice,
        output_dir="data/output"
    )

    if "error" in result:
        print(f"\n错误: {result['error']}")
        return

    # 显示结果
    print("\n" + "-" * 60)
    print("【生成结果】")
    print("-" * 60)
    print(f"\n完整文案:")
    print(result["full_script"])

    print(f"\n音频文件: {result.get('audio_file', 'N/A')}")


def mode_cosyvoice_create():
    """模式5: 创建 CosyVoice 音色复刻"""
    print("\n【创建 CosyVoice 音色复刻】")

    # 显示可用模型
    print("\n可用模型:")
    for key, desc in CosyVoiceTTSClient.MODELS.items():
        print(f"  - {key}: {desc}")

    model = input("\n选择模型 (默认 cosyvoice-v3.5-plus): ").strip() or "cosyvoice-v3.5-plus"

    # 输入音频 URL
    print("\n请输入音频文件的公网 URL:")
    print("提示: 音频文件需要在公网可访问，可以是 OSS、CDN 等地址")
    audio_url = input("音频 URL: ").strip()
    if not audio_url:
        audio_url = "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/cosyvoice/cosyvoice-zeroshot-sample.wav"
        print(f"使用默认示例 URL")

    # 输入音色前缀
    prefix = input("\n音色前缀 (仅数字和小写字母，默认 myvoice): ").strip() or "myvoice"

    # 创建音色
    client = CosyVoiceTTSClient()
    try:
        result = client.create_voice(
            audio_url=audio_url,
            prefix=prefix,
            model=model,
            wait_ready=True
        )
        voice_id = result["voice_id"]

        print(f"\n✓ 音色创建成功!")
        print(f"  Voice ID: {voice_id}")
        print(f"  请保存此 ID，用于后续语音合成")

        # 询问是否立即测试
        test = input("\n是否立即测试语音合成? (y/n): ").strip().lower()
        if test == "y":
            text = input("请输入测试文字 (默认: 你好，这是复刻的声音): ").strip()
            if not text:
                text = "你好，这是复刻的声音"

            output_path = f"data/output/{prefix}_test.mp3"
            client.speech(text, voice=voice_id, output_path=output_path)
            print(f"✓ 测试音频已保存: {output_path}")

        return voice_id

    except Exception as e:
        print(f"\n✗ 创建失败: {e}")
        return None


def mode_cosyvoice_tts():
    """模式6: CosyVoice 文字转语音"""
    print("\n【CosyVoice 文字转语音】")

    # 输入 voice_id
    voice_id = input("\n请输入 Voice ID (通过音色复刻功能创建): ").strip()
    if not voice_id:
        print("✗ Voice ID 不能为空")
        return

    # 输入文字
    print("\n请输入要转换的文字:")
    text = input("文字: ").strip()
    if not text:
        text = "你好，这是用 CosyVoice 复刻的声音合成的语音！"
        print(f"使用默认: {text}")

    # 输出路径
    output_path = input("输出文件 (默认: data/output/cosyvoice.mp3): ").strip()
    if not output_path:
        output_path = "data/output/cosyvoice.mp3"

    # 合成
    client = CosyVoiceTTSClient()
    try:
        client.speech(text, voice=voice_id, output_path=output_path)
        print(f"\n已保存到: {output_path}")
    except Exception as e:
        print(f"\n✗ 合成失败: {e}")


def mode_cosyvoice_full_workflow():
    """模式7: 一键生成：文案 + 语音 (CosyVoice)"""
    print("\n【一键生成：文案 + 语音 (CosyVoice)】")

    # 输入 voice_id
    voice_id = input("\n请输入 Voice ID (通过音色复刻功能创建): ").strip()
    if not voice_id:
        print("✗ Voice ID 不能为空")
        return

    # 选择文案模型
    print("\n选择文案模型:")
    print("  1. DeepSeek (推荐)")
    print("  2. 智谱 GLM")
    model_choice = input("选择 (默认1): ").strip() or "1"
    model = "deepseek" if model_choice == "1" else "zhipu"

    # 输入参考文案
    print("\n请输入参考文案 (直接回车使用默认示例):")
    reference = input("参考文案: ").strip()
    if not reference:
        reference = "杭州老律师月入500待客之道 #律师的真实日常#vlog日常"

    # 输入新主题
    print("\n请输入新主题:")
    topic = input("新主题: ").strip()
    if not topic:
        topic = "律师如何应对奇葩客户"

    # 执行工作流
    workflow = TTSWorkflow(model=model, use_cosyvoice=True)
    result = workflow.generate_and_synthesize(
        topic=topic,
        reference=reference,
        voice=voice_id,
        output_dir="data/output"
    )

    if "error" in result:
        print(f"\n错误: {result['error']}")
        return

    # 显示结果
    print("\n" + "-" * 60)
    print("【生成结果】")
    print("-" * 60)
    print(f"\n完整文案:")
    print(result["full_script"])

    print(f"\n音频文件: {result.get('audio_file', 'N/A')}")


def main():
    """主函数"""
    # 检查API Key
    has_zhipu = bool(os.getenv("ZAI_API_KEY"))
    has_deepseek = bool(os.getenv("DEEPSEEK_API_KEY"))
    has_dashscope = bool(os.getenv("DASHSCOPE_API_KEY"))

    print("=" * 60)
    print("文案生成与TTS合成工具")
    print("=" * 60)
    print(f"\nAPI Key 状态:")
    print(f"  ZAI_API_KEY (智谱): {'✓' if has_zhipu else '✗'}")
    print(f"  DEEPSEEK_API_KEY: {'✓' if has_deepseek else '✗'}")
    print(f"  DASHSCOPE_API_KEY (CosyVoice): {'✓' if has_dashscope else '✗'}")

    if not has_zhipu and not has_deepseek:
        print("\n错误: 请在 .env 文件中设置至少一个文案生成 API Key")
        return

    # 主循环
    while True:
        show_menu()
        choice = input("\n请选择 (0-7): ").strip()

        if choice == "0":
            print("\n再见!")
            break
        elif choice == "1":
            mode_generate_script("deepseek")
        elif choice == "2":
            mode_generate_script("zhipu")
        elif choice == "3":
            mode_tts()
        elif choice == "4":
            mode_full_workflow()
        elif choice == "5":
            mode_cosyvoice_create()
        elif choice == "6":
            mode_cosyvoice_tts()
        elif choice == "7":
            mode_cosyvoice_full_workflow()
        else:
            print("\n无效选择，请重试")


if __name__ == "__main__":
    main()
