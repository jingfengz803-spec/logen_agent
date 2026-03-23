"""
完整视频创作工作流
分析 → 文案生成 → TTS 语音合成 → 视频生成

使用方法：
    python full_workflow.py
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('.env')

from analyze_and_generate import (
    DouyinFetcher,
    VideoStyleAnalyzer
)
from cosyvoice_tts import CosyVoiceTTSClient
from video_generator import VideoRetalkClient, VideoWorkflow
from upload_audio_helper import OSSUploader
from config import Paths, APIKeys


def print_banner():
    print("=" * 70)
    print(" 短视频创作完整工作流")
    print(" 分析 → 文案 → TTS 语音")
    print("=" * 70)


def get_voice_id():
    """获取用户可用的音色 ID"""
    default_voice = "cosyvoice-v3.5-flash-niro-8cc614e161c44abe8621eadddb2e4a11"

    # 检查是否有保存的音色
    voices_file = Path("data/voices.txt")
    saved_voices = []
    if voices_file.exists():
        with open(voices_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(" | ")
                if len(parts) >= 1:
                    saved_voices.append(parts[0])

    print("\n可用音色:")
    print(f"  [默认] {default_voice}")
    for i, vid in enumerate(saved_voices, 1):
        if vid != default_voice:
            print(f"  [{i}] {vid}")

    choice = input(f"\n选择音色（直接回车使用默认）: ").strip()

    if choice.isdigit() and 0 < int(choice) <= len(saved_voices):
        return saved_voices[int(choice) - 1]
    elif choice:
        return choice
    else:
        return default_voice


def get_reference_video_url() -> str:
    """获取用户可用的参考视频 URL"""
    print("\n请提供参考视频 URL（用于 VideoRetalk 视频生成）")
    print("参考视频应包含一个人物的正面镜头，说话状态最佳")
    print("可以使用阿里云 OSS 或其他公网可访问的 URL")

    video_url = input("\n参考视频 URL (留空跳过视频生成): ").strip()
    return video_url


def full_workflow_with_video(
    url: str,
    topic: str,
    voice_id: str = None,
    ref_video_url: str = "",
    output_name: str = None,
    skip_video: bool = False,
    target_duration: float = 20.0
):
    """
    完整工作流（包含视频生成）

    Args:
        url: 抖音用户主页 URL
        topic: 新主题
        voice_id: 音色 ID（不指定则询问）
        ref_video_url: 参考视频 URL（用于 VideoRetalk）
        output_name: 输出文件名前缀（不指定则自动生成）
        skip_video: 是否跳过视频生成
        target_duration: 目标视频时长（秒），默认20秒
    """
    print_banner()
    print(" 分析 → 文案 → TTS 语音 → 视频生成")

    # ========================================
    # 步骤1: 抓取视频数据
    # ========================================
    print(f"\n【步骤1/6】抓取视频数据...")
    print(f"URL: {url}")

    fetcher = DouyinFetcher(max_videos=100, enable_filter=False)
    videos = fetcher.fetch_from_url(url)

    if not videos:
        print("❌ 未获取到视频数据")
        return None

    print(f"✓ 成功抓取 {len(videos)} 个视频")

    # ========================================
    # 步骤2: AI 分析
    # ========================================
    print(f"\n【步骤2/6】AI 分析中（火爆原因 + 风格特征）...")

    analyzer = VideoStyleAnalyzer(timeout=120.0)
    full_result = analyzer.full_analysis(videos, top_n=30)

    viral_analysis = full_result.get("火爆原因分析", {})
    style_analysis = full_result.get("风格特征分析", {})

    if "error" in viral_analysis:
        print(f"⚠️ 火爆分析失败: {viral_analysis.get('error', '')}")
    if "error" in style_analysis:
        print(f"⚠️ 风格分析失败: {style_analysis.get('error', '')}")

    # 显示分析结果摘要
    if viral_analysis:
        print(f"\n🔥 {viral_analysis.get('火爆原因总结', 'N/A')}")

    if style_analysis:
        print(f"🎨 {style_analysis.get('风格总结', 'N/A')}")

    # ========================================
    # 步骤3: 生成 TTS 台词
    # ========================================
    print(f"\n【步骤3/6】生成 TTS 台词...")
    print(f"主题: {topic}")

    if not voice_id:
        voice_id = get_voice_id()

    tts_result = analyzer.generate_tts_script(
        style_analysis=style_analysis,
        viral_analysis=viral_analysis,
        topic=topic,
        target_duration=target_duration
    )

    if "error" in tts_result:
        print(f"❌ TTS 台词生成失败: {tts_result['error']}")
        return None

    # 显示生成的台词
    print(f"\n📌 视频标题: {tts_result.get('视频标题', '')}")
    print(f"📝 视频描述: {tts_result.get('视频描述', '')}")

    tts_data = tts_result.get("TTS台词", {})
    full_script = tts_data.get("完整版", "")
    segments = tts_data.get("分段", [])

    print(f"\n🎤 TTS 台词 ({tts_data.get('字数', 0)}字, 预估{tts_data.get('预估时长', 0)}秒):")
    print(f"   {full_script}")

    # ========================================
    # 步骤4: 语音合成
    # ========================================
    print(f"\n【步骤4/6】TTS 语音合成...")
    print(f"音色: {voice_id}")

    client = CosyVoiceTTSClient()

    # 准备输出目录
    if not output_name:
        import time
        output_name = f"output_{time.strftime('%Y%m%d_%H%M%S')}"

    output_dir = Paths.get_output_dir() / output_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # 合成完整音频
    full_audio_path = output_dir / "full.mp3"
    client.speech(full_script, voice=voice_id, output_path=str(full_audio_path))
    print(f"✓ 完整音频: {full_audio_path}")

    # 合成分段音频
    if segments:
        segments_dir = output_dir / "segments"
        segments_dir.mkdir(exist_ok=True)
        segment_files = []

        for i, seg in enumerate(segments):
            seg_file = segments_dir / f"segment_{i:02d}.mp3"
            client.speech(seg, voice=voice_id, output_path=str(seg_file))
            segment_files.append(str(seg_file))

        print(f"✓ 分段音频: {segments_dir}/ ({len(segment_files)} 个)")

    # ========================================
    # 步骤5: 视频生成（可选）
    # ========================================
    video_result = None
    generated_video_path = None

    if not skip_video:
        print(f"\n【步骤5/6】视频生成...")

        # 如果没有提供参考视频 URL，询问用户
        if not ref_video_url:
            print("\n⚠️ 视频生成需要参考视频 URL")
            print("参考视频应包含一个人物的正面镜头，说话状态最佳")
            print("支持公网 URL 或本地文件路径（会自动上传到 OSS）")
            ref_video_url = input("\n请输入参考视频 URL 或本地路径 (留空跳过): ").strip()

            # 如果输入的是本地文件路径，检查文件是否存在
            if ref_video_url and not ref_video_url.startswith("http"):
                if Path(ref_video_url).exists():
                    print(f"✓ 检测到本地文件: {ref_video_url}")
                else:
                    print(f"✗ 文件不存在: {ref_video_url}")
                    ref_video_url = ""

        if ref_video_url:
            # 使用 VideoWorkflow 自动处理音频上传和视频生成
            try:
                video_workflow = VideoWorkflow()
                video_output_name = f"{output_name}_video"

                print("\n--- 开始自动视频生成流程 ---")
                print("  1. 音频将自动上传到 OSS")
                print("  2. 视频将自动匹配音频长度（video_extension=True）")
                print("  3. 生成过程可能需要几分钟，请耐心等待")

                video_result = video_workflow.generate_from_local_files(
                    video_path="" if ref_video_url.startswith("http") else ref_video_url,
                    video_url=ref_video_url if ref_video_url.startswith("http") else "",
                    audio_path=str(full_audio_path),
                    output_dir=str(output_dir),
                    output_name=video_output_name,
                    auto_upload=True,
                    video_extension=True  # 自动扩展视频以匹配音频长度
                )

                if "error" in video_result:
                    print(f"⚠️ 视频生成失败: {video_result.get('error')}")
                else:
                    generated_video_path = video_result.get("video_path")
                    print(f"\n✓ 视频生成完成: {generated_video_path}")

            except ValueError as e:
                print(f"⚠️ OSS 配置错误: {e}")
                print("视频生成需要 OSS 配置，请检查 .env 文件")
                video_result = {"error": f"OSS 配置错误: {e}"}
            except Exception as e:
                print(f"⚠️ 视频生成失败: {e}")
                video_result = {"error": str(e)}
        else:
            print("跳过视频生成")
    else:
        print(f"\n【步骤5/6】跳过视频生成")

    # ========================================
    # 步骤6: 保存结果
    # ========================================
    print(f"\n【步骤6/6】保存结果...")

    result = {
        "输入": {
            "用户主页URL": url,
            "主题": topic,
            "音色ID": voice_id,
            "参考视频URL": ref_video_url,
        },
        "火爆原因分析": viral_analysis,
        "风格特征分析": style_analysis,
        "TTS台词结果": tts_result,
        "文件": {
            "完整音频": str(full_audio_path),
            "分段音频目录": str(output_dir / "segments"),
            "生成视频": str(generated_video_path) if generated_video_path else None,
        },
        "视频生成结果": video_result,
    }

    # 保存 JSON
    json_file = output_dir / "result.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 保存可读文本
    txt_file = output_dir / "result.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("短视频创作工作流 - 输出结果\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"用户主页: {url}\n")
        f.write(f"主题: {topic}\n")
        f.write(f"音色ID: {voice_id}\n\n")

        f.write("=" * 60 + "\n")
        f.write("【火爆原因分析】\n")
        f.write("=" * 60 + "\n")
        f.write(f"{viral_analysis.get('火爆原因总结', 'N/A')}\n\n")

        f.write("=" * 60 + "\n")
        f.write("【风格特征】\n")
        f.write("=" * 60 + "\n")
        f.write(f"{style_analysis.get('风格总结', 'N/A')}\n\n")

        f.write("=" * 60 + "\n")
        f.write("【视频信息】\n")
        f.write("=" * 60 + "\n")
        f.write(f"标题: {tts_result.get('视频标题', '')}\n")
        f.write(f"描述: {tts_result.get('视频描述', '')}\n")
        tags = tts_result.get('话题标签', [])
        f.write(f"标签: {' '.join(tags)}\n\n")

        f.write("=" * 60 + "\n")
        f.write("【TTS 台词】\n")
        f.write("=" * 60 + "\n")
        f.write(f"{full_script}\n\n")

        f.write("=" * 60 + "\n")
        f.write("【发布文案（可直接复制）】\n")
        f.write("=" * 60 + "\n")
        f.write(tts_result.get('发布文案', ''))

    print(f"✓ 结果已保存到: {output_dir}")
    print(f"  - {json_file.name}")
    print(f"  - {txt_file.name}")

    print("\n" + "=" * 70)
    print("✓ 全部完成!")
    print("=" * 70)
    print(f"\n📁 输出目录: {output_dir}")
    print(f"🎵 完整音频: {full_audio_path}")
    if generated_video_path:
        print(f"🎬 生成视频: {generated_video_path}")

    return result


def full_workflow(url: str, topic: str, voice_id: str = None, output_name: str = None, target_duration: float = 20.0):
    """
    完整工作流

    Args:
        url: 抖音用户主页 URL
        topic: 新主题
        voice_id: 音色 ID（不指定则询问）
        output_name: 输出文件名前缀（不指定则自动生成）
        target_duration: 目标视频时长（秒），默认20秒
    """
    print_banner()

    # ========================================
    # 步骤1: 抓取视频数据
    # ========================================
    print(f"\n【步骤1/5】抓取视频数据...")
    print(f"URL: {url}")

    fetcher = DouyinFetcher(max_videos=100, enable_filter=False)
    videos = fetcher.fetch_from_url(url)

    if not videos:
        print("❌ 未获取到视频数据")
        return None

    print(f"✓ 成功抓取 {len(videos)} 个视频")

    # ========================================
    # 步骤2: AI 分析
    # ========================================
    print(f"\n【步骤2/5】AI 分析中（火爆原因 + 风格特征）...")

    analyzer = VideoStyleAnalyzer(timeout=120.0)
    full_result = analyzer.full_analysis(videos, top_n=30)

    viral_analysis = full_result.get("火爆原因分析", {})
    style_analysis = full_result.get("风格特征分析", {})

    if "error" in viral_analysis:
        print(f"⚠️ 火爆分析失败: {viral_analysis.get('error', '')}")
    if "error" in style_analysis:
        print(f"⚠️ 风格分析失败: {style_analysis.get('error', '')}")

    # 显示分析结果摘要
    if viral_analysis:
        print(f"\n🔥 {viral_analysis.get('火爆原因总结', 'N/A')}")

    if style_analysis:
        print(f"🎨 {style_analysis.get('风格总结', 'N/A')}")

    # ========================================
    # 步骤3: 生成 TTS 台词
    # ========================================
    print(f"\n【步骤3/5】生成 TTS 台词...")
    print(f"主题: {topic}")

    if not voice_id:
        voice_id = get_voice_id()

    tts_result = analyzer.generate_tts_script(
        style_analysis=style_analysis,
        viral_analysis=viral_analysis,
        topic=topic,
        target_duration=target_duration
    )

    if "error" in tts_result:
        print(f"❌ TTS 台词生成失败: {tts_result['error']}")
        return None

    # 显示生成的台词
    print(f"\n📌 视频标题: {tts_result.get('视频标题', '')}")
    print(f"📝 视频描述: {tts_result.get('视频描述', '')}")

    tts_data = tts_result.get("TTS台词", {})
    full_script = tts_data.get("完整版", "")
    segments = tts_data.get("分段", [])

    print(f"\n🎤 TTS 台词 ({tts_data.get('字数', 0)}字, 预估{tts_data.get('预估时长', 0)}秒):")
    print(f"   {full_script}")

    # ========================================
    # 步骤4: 语音合成
    # ========================================
    print(f"\n【步骤4/5】TTS 语音合成...")
    print(f"音色: {voice_id}")

    client = CosyVoiceTTSClient()

    # 准备输出目录
    if not output_name:
        import time
        output_name = f"output_{time.strftime('%Y%m%d_%H%M%S')}"

    output_dir = Paths.get_output_dir() / output_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # 合成完整音频
    full_audio_path = output_dir / "full.mp3"
    client.speech(full_script, voice=voice_id, output_path=str(full_audio_path))
    print(f"✓ 完整音频: {full_audio_path}")

    # 合成分段音频
    if segments:
        segments_dir = output_dir / "segments"
        segments_dir.mkdir(exist_ok=True)
        segment_files = []

        for i, seg in enumerate(segments):
            seg_file = segments_dir / f"segment_{i:02d}.mp3"
            client.speech(seg, voice=voice_id, output_path=str(seg_file))
            segment_files.append(str(seg_file))

        print(f"✓ 分段音频: {segments_dir}/ ({len(segment_files)} 个)")

    # ========================================
    # 步骤5: 保存结果
    # ========================================
    print(f"\n【步骤5/5】保存结果...")

    result = {
        "输入": {
            "用户主页URL": url,
            "主题": topic,
            "音色ID": voice_id,
        },
        "火爆原因分析": viral_analysis,
        "风格特征分析": style_analysis,
        "TTS台词结果": tts_result,
        "文件": {
            "完整音频": str(full_audio_path),
            "分段音频目录": str(output_dir / "segments"),
        }
    }

    # 保存 JSON
    json_file = output_dir / "result.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 保存可读文本
    txt_file = output_dir / "result.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("短视频创作工作流 - 输出结果\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"用户主页: {url}\n")
        f.write(f"主题: {topic}\n")
        f.write(f"音色ID: {voice_id}\n\n")

        f.write("=" * 60 + "\n")
        f.write("【火爆原因分析】\n")
        f.write("=" * 60 + "\n")
        f.write(f"{viral_analysis.get('火爆原因总结', 'N/A')}\n\n")

        f.write("=" * 60 + "\n")
        f.write("【风格特征】\n")
        f.write("=" * 60 + "\n")
        f.write(f"{style_analysis.get('风格总结', 'N/A')}\n\n")

        f.write("=" * 60 + "\n")
        f.write("【视频信息】\n")
        f.write("=" * 60 + "\n")
        f.write(f"标题: {tts_result.get('视频标题', '')}\n")
        f.write(f"描述: {tts_result.get('视频描述', '')}\n")
        tags = tts_result.get('话题标签', [])
        f.write(f"标签: {' '.join(tags)}\n\n")

        f.write("=" * 60 + "\n")
        f.write("【TTS 台词】\n")
        f.write("=" * 60 + "\n")
        f.write(f"{full_script}\n\n")

        f.write("=" * 60 + "\n")
        f.write("【发布文案（可直接复制）】\n")
        f.write("=" * 60 + "\n")
        f.write(tts_result.get('发布文案', ''))

    print(f"✓ 结果已保存到: {output_dir}")
    print(f"  - {json_file.name}")
    print(f"  - {txt_file.name}")

    print("\n" + "=" * 70)
    print("✓ 全部完成!")
    print("=" * 70)
    print(f"\n📁 输出目录: {output_dir}")
    print(f"🎵 完整音频: {full_audio_path}")

    return result


def interactive_mode():
    """交互式模式"""
    print_banner()

    print("\n请选择模式:")
    print("  1. 完整工作流（分析 + 生成 + TTS + 视频生成）")
    print("  2. 标准工作流（分析 + 生成 + TTS）")
    print("  3. 仅分析已有视频")
    print("  4. 使用已有文案生成 TTS")
    print("  5. VideoRetalk 视频生成（需要已有音频 URL）")
    print("  6. 查询视频生成任务状态")

    mode = input("\n请选择 (1-6): ").strip()

    if mode == "1":
        # 完整工作流（包含视频生成）
        print("\n" + "-" * 70)
        url = input("抖音用户主页 URL: ").strip()
        topic = input("新主题: ").strip()
        voice = input("音色ID（留空使用默认）: ").strip() or None
        ref_video = input("参考视频 URL（用于 VideoRetalk，留空跳过）: ").strip()

        if url and topic:
            full_workflow_with_video(url, topic, voice, ref_video)

    elif mode == "2":
        # 标准工作流
        print("\n" + "-" * 70)
        url = input("抖音用户主页 URL: ").strip()
        topic = input("新主题: ").strip()
        voice = input("音色ID（留空使用默认）: ").strip() or None

        if url and topic:
            full_workflow(url, topic, voice)

    elif mode == "3":
        # 仅分析
        print("\n" + "-" * 70)
        url = input("抖音用户主页 URL: ").strip()

        if url:
            from analyze_and_generate import quick_full_workflow
            topic = input("主题（用于生成测试）: ").strip() or "测试"
            quick_full_workflow(url, topic)

    elif mode == "4":
        # TTS 生成
        print("\n" + "-" * 70)
        text = input("要合成的文本: ").strip()
        voice = input("音色ID（留空使用默认）: ").strip() or None

        if text:
            if not voice:
                voice = get_voice_id()

            client = CosyVoiceTTSClient()
            output = Paths.get_output_dir() / "quick_tts.mp3"
            client.speech(text, voice=voice, output_path=str(output))
            print(f"\n✓ 音频已保存: {output}")

    elif mode == "5":
        # 视频生成
        print("\n" + "-" * 70)
        print("【VideoRetalk 视频生成】")
        print("\n需要提供以下资源的公网 URL:")
        print("  1. 参考视频 URL（包含人物正面镜头，说话状态最佳）")
        print("  2. 音频 URL（要合成的语音）")

        video_url = input("\n参考视频 URL: ").strip()
        audio_url = input("音频 URL: ").strip()
        ref_image = input("参考图片 URL（可选，留空跳过）: ").strip()

        if video_url and audio_url:
            import time
            output_name = f"video_{time.strftime('%Y%m%d_%H%M%S')}"
            output_path = str(Paths.get_output_dir() / f"{output_name}.mp4")

            print("\n开始视频生成（可能需要几分钟）...")

            client = VideoRetalkClient()
            try:
                result = client.generate_video(
                    video_url=video_url,
                    audio_url=audio_url,
                    ref_image_url=ref_image,
                    output_path=output_path
                )
                print(f"\n✓ 视频生成完成!")
                print(f"  - 视频文件: {result.get('video_path', output_path)}")
                print(f"  - Request ID: {result.get('request_id')}")
            except Exception as e:
                print(f"\n✗ 视频生成失败: {e}")

    elif mode == "6":
        # 查询任务状态
        print("\n" + "-" * 70)
        print("【查询视频生成任务状态】")

        request_id = input("请输入任务ID: ").strip()

        if request_id:
            client = VideoRetalkClient()
            try:
                result = client.query_task_status(request_id)
                print(f"\n任务状态:")
                print(json.dumps(result, ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"\n✗ 查询失败: {e}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="短视频创作完整工作流")
    parser.add_argument("--url", help="抖音用户主页 URL")
    parser.add_argument("--topic", help="新主题")
    parser.add_argument("--voice", help="音色ID（可选）")
    parser.add_argument("--output", help="输出文件名前缀（可选）")
    parser.add_argument("--video", help="参考视频 URL（用于完整工作流，支持本地路径或公网URL）")
    parser.add_argument("--full", action="store_true", help="启用完整工作流（包含视频生成）")
    parser.add_argument("--skip-video", action="store_true", help="跳过视频生成")

    args = parser.parse_args()

    if args.url and args.topic:
        # 命令行模式
        if args.full or args.video:
            # 完整工作流（包含视频生成）
            ref_video = args.video or ""
            full_workflow_with_video(
                url=args.url,
                topic=args.topic,
                voice_id=args.voice,
                ref_video_url=ref_video,
                skip_video=args.skip_video
            )
        else:
            # 标准工作流
            full_workflow(args.url, args.topic, args.voice, args.output)
    else:
        # 交互模式
        interactive_mode()


if __name__ == "__main__":
    main()
