"""
文案生成与TTS合成 - 主入口
整合：文案生成 + TTS合成
"""

import os
import sys
import io
import json
from pathlib import Path

# 修复 Windows 控制台编码 - 必须在任何导入之前执行
if sys.platform == "win32" and hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 导入统一配置
from config import APIKeys, TTSConfig, Paths, print_api_status

from script_generator import ScriptGenerator
from cosyvoice_tts import CosyVoiceTTSClient, TTSWorkflow
from analyze_and_generate import interactive_mode as video_workflow_mode
from video_generator import VideoRetalkClient, VideoWorkflow


def mode_complete_workflow():
    """完整端到端工作流：抖音抓取 → 分析 → 文案 → TTS → 视频"""
    print("\n" + "=" * 60)
    print("【完整端到端工作流】")
    print(" 抖音抓取 → 分析 → 文案 → TTS → 视频")
    print("=" * 60)

    # 输入参数
    print("\n请输入参数:")
    douyin_url = input("抖音用户主页 URL: ").strip()
    if not douyin_url:
        print("✗ URL 不能为空")
        return

    topic = input("新主题: ").strip()
    if not topic:
        print("✗ 主题不能为空")
        return

    voice = input("音色ID（留空使用默认）: ").strip() or None
    ref_video_url = input("参考视频 URL（用于VideoRetalk，留空跳过视频生成）: ").strip()
    output_name = input("输出文件名前缀（留空自动生成）: ").strip() or None

    # 调用完整工作流
    from full_workflow import full_workflow_with_video
    full_workflow_with_video(
        url=douyin_url,
        topic=topic,
        voice_id=voice,
        ref_video_url=ref_video_url,
        output_name=output_name,
        skip_video=(not ref_video_url)
    )


def show_menu():
    """显示菜单"""
    print("\n" + "=" * 60)
    print("视频脚本生成工具")
    print("=" * 60)
    print("\n请选择功能:")
    print("  【完整工作流 - 推荐】")
    print("  1. 完整端到端（抖音抓取→分析→文案→TTS→视频）")
    print("  2. 视频脚本生成（抓取+分析+生成TTS+语音）")
    print("  3. 标准工作流（抓取+分析+生成TTS+语音）")
    print("\n  【文案生成】")
    print("  4. 生成文案 (DeepSeek)")
    print("  5. 生成文案 (智谱 GLM)")
    print("\n  【阿里 CosyVoice - 支持音色复刻】")
    print("  6. 创建 CosyVoice 音色复刻")
    print("  7. 文字转语音 (CosyVoice)")
    print("  8. 一键生成：文案 + 语音 (CosyVoice)")
    print("\n  【阿里 VideoRetalk - 视频生成】")
    print("  9. 视频生成（需要参考视频 URL 和音频 URL）")
    print("  10. 查询视频生成任务状态")
    print("\n  0. 退出")


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


def mode_cosyvoice_create():
    """模式5: 创建 CosyVoice 音色复刻"""
    print("\n【创建 CosyVoice 音色复刻】")

    # 显示可用模型
    cosyvoice_config = TTSConfig.get_tts_config("cosyvoice")
    print("\n可用模型:")
    for key, desc in cosyvoice_config["models"].items():
        print(f"  - {key}: {desc}")

    model = input("\n选择模型 (默认 cosyvoice-v3.5-plus): ").strip() or cosyvoice_config["default_model"]

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
    workflow = TTSWorkflow(model=model, tts_engine="cosyvoice")
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


def mode_video_generate():
    """模式10: VideoRetalk 视频生成"""
    print("\n【VideoRetalk 视频生成】")

    print("\n请选择输入方式:")
    print("  1. 本地文件（自动上传到 OSS）")
    print("  2. 已有的 URL")

    input_mode = input("\n请选择 (1/2，默认1): ").strip() or "1"

    video_path = ""
    audio_path = ""
    video_url = ""
    audio_url = ""
    ref_image_path = ""
    ref_image_url = ""

    if input_mode == "1":
        # 本地文件模式
        print("\n--- 本地文件模式 ---")
        print("提示: 需要在 .env 中配置 OSS 参数以自动上传文件")

        video_path = input("\n参考视频路径: ").strip()
        audio_path = input("音频路径: ").strip()
        ref_image_path = input("参考图片路径（可选，留空跳过）: ").strip()

        if not video_path or not audio_path:
            print("\n✗ 参考视频和音频路径不能为空")
            return

        # 检查文件是否存在
        if not Path(video_path).exists():
            print(f"\n✗ 视频文件不存在: {video_path}")
            return
        if not Path(audio_path).exists():
            print(f"\n✗ 音频文件不存在: {audio_path}")
            return
        if ref_image_path and not Path(ref_image_path).exists():
            print(f"\n✗ 图片文件不存在: {ref_image_path}")
            return

    else:
        # URL 模式
        print("\n--- URL 模式 ---")
        print("需要提供公网可访问的 URL（如阿里云 OSS）")

        video_url = input("\n参考视频 URL: ").strip()
        audio_url = input("音频 URL: ").strip()
        ref_image_url = input("参考图片 URL（可选，留空跳过）: ").strip()

        if not video_url or not audio_url:
            print("\n✗ 参考视频和音频 URL 不能为空")
            return

    # 输出路径
    output_path = input("输出文件路径 (默认: data/output/video.mp4): ").strip()
    if not output_path:
        output_path = "data/output/video.mp4"

    # 生成视频
    try:
        from video_generator import VideoWorkflow

        workflow = VideoWorkflow()

        print("\n开始视频生成（可能需要几分钟）...")

        result = workflow.generate_from_local_files(
            video_path=video_path,
            audio_path=audio_path,
            video_url=video_url,
            audio_url=audio_url,
            ref_image_path=ref_image_path,
            ref_image_url=ref_image_url,
            output_dir=str(Path(output_path).parent),
            output_name=Path(output_path).stem
        )

        if "error" in result:
            print(f"\n✗ {result['error']}")
            hint = result.get("hint")
            if hint:
                print(f"提示: {hint}")
            return

        print("\n" + "-" * 60)
        print("【生成结果】")
        print("-" * 60)
        print(f"\n视频文件: {result.get('video_path', 'N/A')}")
        print(f"Request ID: {result.get('request_id', 'N/A')}")

        if "video_url" in result:
            print(f"视频 URL: {result['video_url']}")

    except Exception as e:
        print(f"\n✗ 视频生成失败: {e}")
        import traceback
        traceback.print_exc()


def mode_query_video_task():
    """模式11: 查询视频生成任务状态"""
    print("\n【查询视频生成任务状态】")

    request_id = input("请输入任务ID: ").strip()

    if not request_id:
        print("✗ 任务ID不能为空")
        return

    client = VideoRetalkClient()
    try:
        result = client.query_task_status(request_id)

        print("\n" + "-" * 60)
        print("【任务状态】")
        print("-" * 60)

        # 格式化输出
        output = result.get("output", {})
        status = output.get("task_status") or output.get("status", "UNKNOWN")

        print(f"\n状态: {status}")

        if status == "SUCCEEDED" or status == "completed":
            results = output.get("results", [])
            if results and "url" in results[0]:
                print(f"视频 URL: {results[0]['url']}")
        elif status == "FAILED":
            print(f"错误信息: {output.get('message', '未知错误')}")

        print(f"\n完整响应:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"\n✗ 查询失败: {e}")


def main():
    """主函数"""
    # 检查 API Key 状态
    status = APIKeys.check_all()

    print("=" * 60)
    print("文案生成与TTS合成工具")
    print("=" * 60)

    # 使用统一配置打印状态
    print_api_status()

    if not status["deepseek"] and not status["zhipu"]:
        print("\n错误: 请在 .env 文件中设置至少一个文案生成 API Key")
        return

    # 主循环
    while True:
        show_menu()
        choice = input("\n请选择 (0-10): ").strip()

        if choice == "0":
            print("\n再见!")
            break
        elif choice == "1":
            mode_complete_workflow()
        elif choice == "2":
            video_workflow_mode()
        elif choice == "3":
            from full_workflow import interactive_mode as full_workflow_interactive
            full_workflow_interactive()
        elif choice == "4":
            mode_generate_script("deepseek")
        elif choice == "5":
            mode_generate_script("zhipu")
        elif choice == "6":
            mode_cosyvoice_create()
        elif choice == "7":
            mode_cosyvoice_tts()
        elif choice == "8":
            mode_cosyvoice_full_workflow()
        elif choice == "9":
            mode_video_generate()
        elif choice == "10":
            mode_query_video_task()
        else:
            print("\n无效选择，请重试")


if __name__ == "__main__":
    main()
