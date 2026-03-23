"""
前端交互模拟器
模拟用户在前端页面的操作流程，发送 API 请求
"""
import requests
import time


BASE_URL = "http://localhost:8088"


def print_header(title):
    print("\n" + "=" * 50)
    print(f"  {title}")
    print("=" * 50)


def print_request(method, endpoint, data=None):
    print(f"\n>>> 前端发送请求:")
    print(f"    {method} {endpoint}")
    if data:
        import json
        print(f"    参数: {json.dumps(data, ensure_ascii=False)}")


def print_response(response):
    print(f"\n<<< 服务端响应:")
    print(f"    状态码: {response.status_code}")
    import json
    try:
        print(f"    数据: {json.dumps(response.json(), ensure_ascii=False, indent=6)}")
    except:
        print(f"    数据: {response.text[:200]}")


def show_result_summary(module_name, result_data):
    """
    展示环节完成后的结果摘要（用户视角）
    """
    print("\n" + "─" * 50)
    print(f"  📋 {module_name} - 处理完成")
    print("─" * 50)

    if module_name == "完整分析":
        # 处理完整分析结果（viral_analysis + style_analysis + tts_result）
        viral = result_data.get("viral_analysis", {})
        style = result_data.get("style_analysis", {})
        tts = result_data.get("tts_result", {})

        # 火爆原因分析摘要
        if viral and "error" not in viral:
            print(f"\n  🔥 火爆原因分析:")
            summary = viral.get("火爆原因总结", "N/A")
            print(f"     • 总结: {summary[:80]}...")

            factors = viral.get("核心驱动因素", [])
            if factors:
                print(f"     • 核心驱动因素:")
                for f in factors[:5]:
                    print(f"       - {f}")

            stats = viral.get("维度分析", {})
            if stats:
                emo = stats.get("情绪共鸣", {})
                if emo:
                    print(f"     • 情绪共鸣: {emo.get('主要情绪', 'N/A')} ({emo.get('评估', 'N/A')})")

        # 风格特征分析摘要
        if style and "error" not in style:
            print(f"\n  🎨 风格特征分析:")
            summary = style.get("风格总结", "N/A")
            print(f"     • 风格总结: {summary[:80]}...")

            copy_templates = style.get("复刻模板", [])
            if copy_templates:
                print(f"     • 复刻模板数: {len(copy_templates)} 个")

        # TTS脚本结果
        if tts and "error" not in tts:
            print(f"\n  📜 TTS脚本生成:")

            # TTS台词在嵌套的"TTS台词"字段下
            tts_data = tts.get("TTS台词", {})
            
            # 完整版台词
            full_script = tts_data.get("完整版", "")
            if full_script:
                actual_count = tts_data.get("实际字数", len(full_script))
                target_range = tts_data.get("目标字数范围", "")
                print(f"     • 完整台词 ({actual_count}字, 目标: {target_range}):")
                print(f"       {full_script[:100]}...")

            # 分段台词
            segments = tts_data.get("分段", [])
            if segments:
                print(f"     • 分段台词 ({len(segments)}段):")
                for i, seg in enumerate(segments[:3], 1):
                    print(f"       {i}. {seg[:40]}...")

            # 其他信息（视频发布信息，不含TTS）
            if tts.get("视频标题"):
                print(f"     • 视频标题: {tts['视频标题']}")
            if tts.get("话题标签"):
                tags = " ".join([f"#{t}" for t in tts.get("话题标签", [])])
                print(f"     • 话题标签: {tags}")
            if tts.get("发布文案"):
                desc = tts["发布文案"][:60]
                print(f"     • 发布文案: {desc}...")

        print(f"\n  🎉 完整分析流程已完成！")

    elif module_name == "抖音视频抓取":
        videos = result_data.get("videos", [])
        total = result_data.get("total", len(videos))
        stats = result_data.get("stats", {})
        top_n = result_data.get("top_n", 0)
        sort_by = result_data.get("sort_by", "like")

        print(f"\n  ✅ 抓取成功！")
        print(f"  📊 数据统计:")
        print(f"     • 抓取视频数: {total} 条")
        if top_n > 0:
            print(f"     • 返回Top {top_n} (按{sort_by}排序)")

        # 使用后端计算的统计信息
        if stats:
            print(f"\n  📈 互动统计:")
            print(f"     • 总点赞: {stats.get('total_likes', 0):,}")
            print(f"     • 总评论: {stats.get('total_comments', 0):,}")
            print(f"     • 总分享: {stats.get('total_shares', 0):,}")
            print(f"     • 总播放: {stats.get('total_plays', 0):,}")
            print(f"     • 平均点赞: {stats.get('avg_likes', 0):,}")
            print(f"     • 平均评论: {stats.get('avg_comments', 0):,}")

            top_tags = stats.get("top_tags", [])
            if top_tags:
                print(f"\n  🏷️  高频标签 (TOP10):")
                for item in top_tags[:10]:
                    print(f"     • #{item.get('tag', '')} ({item.get('count', 0)}次)")

            top_liked = stats.get("top_liked_video", {})
            if top_liked and top_liked.get("aweme_id"):
                print(f"\n  🔥 最受欢迎视频:")
                print(f"     • {top_liked.get('desc', '')[:40]}...")
                print(f"     • 点赞: {top_liked.get('like_count', 0):,}")

        if videos:
            print(f"\n  📝 视频列表 (前3条):")
            for i, v in enumerate(videos[:3], 1):
                desc = v.get("desc_clean", v.get("desc", ""))[:40]
                tags = ", ".join(v.get("hashtags", [])[:3])
                print(f"     {i}. {desc}...")
                print(f"        标签: #{tags}  |  👍{v.get('like_count', 0)}")

        print(f"\n  🔄 下一步: 这些数据将交给AI分析，提取爆款特征")

    elif module_name == "音色克隆":
        print(f"\n  ✅ 音色创建成功！")
        print(f"  🎙️  音色信息:")
        print(f"     • 音色ID: {result_data.get('voice_id', 'N/A')}")
        print(f"     • 前缀: {result_data.get('prefix', 'N/A')}")
        print(f"     • 模型: {result_data.get('model', 'N/A')}")
        print(f"     • 状态: {result_data.get('status', 'N/A')}")
        print(f"\n  🔄 下一步: 使用此音色进行语音合成")

    elif module_name == "AI脚本生成":
        script = result_data.get("script", {})
        if script:
            print(f"\n  ✅ 脚本生成成功！")
            print(f"  📜 脚本信息:")
            print(f"     • 标题: {script.get('title', 'N/A')}")
            print(f"     • 字数: {script.get('word_count', 0)} 字")
            print(f"     • 预估时长: {script.get('estimated_duration', 0)} 秒")
            print(f"     • 分段数: {len(script.get('segments', []))} 段")

            hashtags = script.get('hashtags', [])
            if hashtags:
                print(f"\n  🏷️  推荐标签:")
                print(f"     {' '.join(['#' + tag for tag in hashtags[:5]])}")

            publish_text = script.get('publish_text', '')[:80]
            if publish_text:
                print(f"\n  📱 发布文案预览:")
                print(f"     {publish_text}...")

            print(f"\n  🔄 下一步: 使用此脚本进行TTS语音合成")

    elif module_name == "语音合成":
        print(f"\n  ✅ 语音合成成功！")
        print(f"  🔊 音频信息:")
        print(f"     • 文件路径: {result_data.get('audio_path', 'N/A')}")
        print(f"     • 时长: {result_data.get('duration', 0):.1f} 秒")
        print(f"     • 文件大小: {result_data.get('size', 0) / 1024:.1f} KB")
        print(f"\n  🔄 下一步: 音频可用于视频生成")

    elif module_name == "数字人视频生成":
        print(f"\n  ✅ 视频生成成功！")
        print(f"  🎬 视频信息:")
        print(f"     • 输出路径: {result_data.get('video_path', 'N/A')}")
        print(f"     • 视频时长: {result_data.get('duration', 0):.1f} 秒")
        print(f"\n  🎉 完成！数字人视频已生成")

    elif module_name == "完整工作流":
        print(f"\n  ✅ 工作流执行完成！")
        print(f"  📦 输出结果:")

        if result_data.get("videos"):
            print(f"     • 抓取视频: {len(result_data['videos'])} 条")

        if result_data.get("script"):
            script = result_data["script"]
            print(f"     • 生成脚本: {script.get('title', 'N/A')}")

        if result_data.get("audio_urls"):
            print(f"     • TTS音频: 已生成")

        if result_data.get("video_url"):
            print(f"     • 最终视频: {result_data['video_url']}")

        output_files = result_data.get("output_files", {})
        if output_files:
            print(f"\n  📁 输出文件:")
            for name, path in output_files.items():
                print(f"     • {name}: {path}")

    print("\n" + "─" * 50 + "\n")


def poll_task_with_result(task_id, endpoint, module_name):
    """
    轮询任务状态，完成后展示结果摘要
    """
    print(f"\n[前端] 正在等待任务完成...")

    while True:
        response = requests.get(f"{BASE_URL}{endpoint}/{task_id}")
        data = response.json()

        status = data.get("status", "")
        progress = data.get("progress", 0)

        print(f"  进度: {progress}% | 状态: {status}", end="\r")

        if status == "success":
            print(f"\n")
            result = data.get("result", {})
            if result:
                show_result_summary(module_name, result)
            return result
        elif status == "failed":
            error = data.get("error", "未知错误")
            print(f"\n  ❌ 任务失败: {error}")
            return None

        time.sleep(2)


# ==================== 模块1: 抓取+分析+生成（整合） ====================
def module_douyin_fetch():
    """
    前端页面: 抖音视频抓取 + AI分析 + 脚本生成（完整流程）
    用户操作: 输入抖音链接 + 新主题 → 一键完成全部流程
    """
    print_header("模块1: 抖音视频抓取 + AI分析 + 脚本生成")

    # 用户输入
    url = input("\n[用户输入] 请输入抖音用户主页链接: ").strip()
    if not url:
        print("已取消")
        return

    topic = input("[用户输入] 请输入新视频主题: ").strip()
    if not topic:
        print("已取消")
        return

    max_count = input("[用户输入] 抓取数量/分析数量 (默认50): ").strip()
    max_count = int(max_count) if max_count else 50

    duration = input("[用户输入] 目标时长/秒 (默认20): ").strip()
    target_duration = float(duration) if duration else 20.0

    # 前端发送请求 - 使用完整分析接口
    data = {
        "douyin_url": url,
        "topic": topic,
        "max_videos": max_count,
        "enable_viral_analysis": True,
        "enable_style_analysis": True,
        "generate_script": True
    }
    print_request("POST", f"{BASE_URL}/api/v1/ai/analyze/full", data)

    response = requests.post(f"{BASE_URL}/api/v1/ai/analyze/full", json=data)
    print_response(response)

    if response.status_code == 200:
        task_id = response.json().get("task_id")
        print(f"\n[前端] 完整分析任务ID: {task_id}")

        # 自动轮询并展示结果
        result = poll_task_with_result(task_id, "/api/v1/ai/task", "完整分析")

        # 如果有TTS结果，额外显示完整内容
        if result and result.get("tts_result"):
            tts_result = result["tts_result"]
            print("\n" + "=" * 50)
            print("  📜 生成的TTS台词（完整）")
            print("=" * 50)
            
            # TTS台词在嵌套的"TTS台词"字段下
            tts_data = tts_result.get("TTS台词", {})
            full_script = tts_data.get("完整版", "")
            
            if full_script:
                actual_count = tts_data.get("实际字数", len(full_script))
                target_range = tts_data.get("目标字数范围", "")
                estimated = tts_data.get("实际预估时长", tts_data.get("预估时长", "N/A"))
                
                print(f"\n  ═══════════════════════════════════")
                print(f"  📢 TTS完整台词（不含标题和标签）")
                print(f"  ═══════════════════════════════════")
                print(f"  {full_script}")
                print(f"  ═══════════════════════════════════")
                print(f"  📊 字数统计: {actual_count}字 (目标: {target_range}字)")
                print(f"  ⏱️  预估时长: {estimated}秒")
                
                # 字数是否达标提示
                if target_range:
                    try:
                        min_target = int(target_range.split("-")[0])
                        if actual_count < min_target:
                            print(f"  ⚠️  警告: 字数不足 {min_target - actual_count} 字")
                        else:
                            print(f"  ✅ 字数达标")
                    except:
                        pass

            segments = tts_data.get("分段", [])
            if segments:
                print(f"\n  分段台词 ({len(segments)}段):")
                for i, seg in enumerate(segments, 1):
                    print(f"    {i}. {seg}")

            # 视频发布信息（分开显示）
            print(f"\n  ──────────────────────────────────────────")
            print(f"  📌 视频发布信息（不含TTS）")
            print(f"  ──────────────────────────────────────────")
            print(f"  视频标题: {tts_result.get('视频标题', '')}")
            print(f"  话题标签: {' '.join(tts_result.get('话题标签', []))}")
            print(f"  发布文案: {tts_result.get('发布文案', '')}")


# ==================== 模块3: 音色克隆 ====================
def module_voice_clone():
    """
    前端页面: 音色克隆（独立步骤）
    用户操作: 上传音频文件 → 上传到OSS → 创建音色 → 返回voice_id供后续使用
    """
    print_header("模块3: 音色克隆")

    # 步骤1: 用户上传文件
    print("\n[步骤1/3] 上传音频文件")
    print("[提示] 请上传10-60秒的清晰人声录音（mp3/wav格式）")
    file_path = input("[用户输入] 请输入本地音频文件路径: ").strip()
    if not file_path:
        print("已取消")
        return

    # 前端上传文件到 OSS
    print("\n[前端] 正在上传文件到 OSS...")
    print_request("POST", f"{BASE_URL}/api/v1/storage/upload/path",
                  {"file_path": file_path, "file_type": "audio"})

    response = requests.post(
        f"{BASE_URL}/api/v1/storage/upload/path",
        json={"file_path": file_path, "file_type": "audio"}
    )
    print_response(response)

    audio_url = None
    if response.status_code == 200:
        task_id = response.json().get("task_id")
        print(f"\n[前端] 上传任务ID: {task_id}")

        # 获取上传结果
        print_request("GET", f"{BASE_URL}/api/v1/storage/upload/task/{task_id}")
        response = requests.get(f"{BASE_URL}/api/v1/storage/upload/task/{task_id}")
        print_response(response)

        if response.json().get("result"):
            audio_url = response.json()["result"].get("oss_url")
            print(f"\n[前端] 音频文件已上传，公网URL: {audio_url}")

    # 步骤2: 创建音色
    if audio_url:
        print("\n[步骤2/3] 创建音色")
        prefix = input("[用户输入] 音色名称/前缀 (如: xiaoming, 默认 my_voice): ").strip() or "my_voice"
        model = input("[用户输入] TTS模型 (默认 cosyvoice-v3.5-flash): ").strip() or "cosyvoice-v3.5-flash"

        print_request("POST", f"{BASE_URL}/api/v1/tts/voice/create", {
            "audio_url": audio_url,
            "prefix": prefix,
            "model": model
        })

        response = requests.post(
            f"{BASE_URL}/api/v1/tts/voice/create",
            json={"audio_url": audio_url, "prefix": prefix, "model": model}
        )
        print_response(response)

        if response.status_code == 200:
            task_id = response.json().get("task_id")
            print(f"\n[前端] 音色创建任务ID: {task_id}")

            # 步骤3: 查询创建状态并展示结果
            print("\n[步骤3/3] 查询音色创建状态")
            result = poll_task_with_result(task_id, "/api/v1/tts/task", "音色克隆")
            
            if result:
                voice_id = result.get("voice_id")
                print(f"\n" + "="*50)
                print(f"  ✅ 音色创建完成！")
                print(f"  📝 请记录此 voice_id，后续语音合成需要使用：")
                print(f"     {voice_id}")
                print(f"  🔄 下一步: 进入'语音合成'模块使用此音色")
                print("="*50)


# ==================== 模块3: AI脚本生成 ====================
def module_ai_script():
    """
    前端页面: AI 脚本生成
    用户操作: 输入抖音链接 + 新主题 → 完整分析并生成脚本
    """
    print_header("模块3: AI 脚本生成")

    print("\n[提示] 此功能需要先提供抖音用户主页链接进行风格分析")
    print("       如无链接，请使用'完整工作流向导'功能")

    # 用户输入
    douyin_url = input("\n[用户输入] 请输入抖音用户主页链接 (可选): ").strip()
    topic = input("[用户输入] 请输入视频主题: ").strip()
    if not topic:
        print("已取消")
        return

    duration = input("[用户输入] 目标时长/秒 (默认60): ").strip()
    max_videos = int(duration) if duration else 100

    # 前端发送请求 - 使用完整分析接口
    data = {
        "douyin_url": douyin_url or "https://www.douyin.com/user/placeholder",
        "topic": topic,
        "max_videos": max_videos,
        "enable_viral_analysis": True,
        "enable_style_analysis": True,
        "generate_script": True
    }
    print_request("POST", f"{BASE_URL}/api/v1/ai/analyze/full", data)

    response = requests.post(f"{BASE_URL}/api/v1/ai/analyze/full", json=data)
    print_response(response)

    if response.status_code == 200:
        task_id = response.json().get("task_id")
        print(f"\n[前端] 分析任务ID: {task_id}")

        # 自动轮询并展示结果
        poll_task_with_result(task_id, "/api/v1/ai/task", "AI脚本生成")


# ==================== 模块4: 语音合成 ====================
def module_tts_speech():
    """
    前端页面: 语音合成
    用户操作: 选择音色 → 输入文本 → 合成语音
    """
    print_header("模块4: 语音合成")

    # 先获取可用音色列表
    print("\n[前端] 获取可用音色列表...")
    print_request("GET", f"{BASE_URL}/api/v1/tts/voice/list")
    response = requests.get(f"{BASE_URL}/api/v1/tts/voice/list")
    print_response(response)

    voices = response.json().get("voices", [])
    available_voices = [v for v in voices if v.get("is_available")]

    if available_voices:
        print(f"\n[前端展示] 可用音色:")
        for i, v in enumerate(available_voices[:5], 1):
            prefix = v.get('prefix') or '无前缀'
            voice_id_short = v.get('voice_id', '')[:40] + '...' if len(v.get('voice_id', '')) > 40 else v.get('voice_id', '')
            print(f"    {i}. {prefix} ({voice_id_short})")

    # 用户输入 - 支持序号或完整voice_id
    user_input = input("\n[用户输入] 请输入音色序号或完整voice_id: ").strip()
    if not user_input:
        print("已取消")
        return

    # 判断是序号还是完整voice_id
    if user_input.isdigit() and available_voices:
        idx = int(user_input) - 1
        if 0 <= idx < len(available_voices):
            voice_id = available_voices[idx].get('voice_id')
            print(f"[前端] 已选择: {available_voices[idx].get('prefix', '无前缀')}")
        else:
            print(f"错误: 序号超出范围 (1-{len(available_voices)})")
            return
    else:
        voice_id = user_input

    text = input("[用户输入] 请输入要合成的文本: ").strip()
    if not text:
        print("已取消")
        return

    # 前端发送请求
    data = {
        "text": text,
        "voice_id": voice_id,
        "output_format": "mp3"
    }
    print_request("POST", f"{BASE_URL}/api/v1/tts/speech", data)

    response = requests.post(f"{BASE_URL}/api/v1/tts/speech", json=data)
    print_response(response)

    if response.status_code == 200:
        task_id = response.json().get("task_id")
        print(f"\n[前端] 语音合成任务ID: {task_id}")

        # 自动轮询并展示结果
        poll_task_with_result(task_id, "/api/v1/tts/task", "语音合成")


# ==================== 模块5: 视频生成 (VideoRetalk) ====================
def module_video_generate():
    """
    前端页面: 数字人视频生成
    用户操作: 上传视频文件 + 上传音频文件 → 生成口型同步视频
    """
    print_header("模块5: 数字人视频生成")

    # 步骤1: 上传参考视频
    print("\n[步骤1/4] 上传参考视频文件")
    video_path = input("[用户输入] 请输入本地视频文件路径: ").strip()
    if not video_path:
        print("已取消")
        return

    print("\n[前端] 正在上传视频到 OSS...")
    print_request("POST", f"{BASE_URL}/api/v1/storage/upload/path",
                  {"file_path": video_path, "file_type": "video"})

    response = requests.post(
        f"{BASE_URL}/api/v1/storage/upload/path",
        json={"file_path": video_path, "file_type": "video"}
    )
    print_response(response)

    video_url = None
    if response.status_code == 200:
        task_id = response.json().get("task_id")
        print(f"\n[前端] 视频上传任务ID: {task_id}")

        # 使用轮询等待上传完成
        result = poll_task_with_result(task_id, "/api/v1/storage/upload/task", "视频上传")
        if result:
            video_url = result.get("oss_url")
            print(f"\n[前端] 视频已上传，公网URL: {video_url}")

    if not video_url:
        print("\n[错误] 视频上传失败")
        return

    # 步骤2: 上传音频文件
    print("\n[步骤2/4] 上传音频文件")
    print("[提示] 请选择音频来源:")
    print("    1. 本地音频文件路径")
    print("    2. 使用已有的TTS音频文件路径")

    audio_choice = input("[用户输入] 请选择 (1/2, 默认1): ").strip() or "1"

    audio_path = None
    if audio_choice == "1":
        audio_path = input("[用户输入] 请输入本地音频文件路径: ").strip()
    else:
        audio_path = input("[用户输入] 请输入TTS生成的音频文件路径: ").strip()

    if not audio_path:
        print("已取消")
        return

    print("\n[前端] 正在上传音频到 OSS...")
    print_request("POST", f"{BASE_URL}/api/v1/storage/upload/path",
                  {"file_path": audio_path, "file_type": "audio"})

    response = requests.post(
        f"{BASE_URL}/api/v1/storage/upload/path",
        json={"file_path": audio_path, "file_type": "audio"}
    )
    print_response(response)

    audio_url = None
    if response.status_code == 200:
        task_id = response.json().get("task_id")
        print(f"\n[前端] 音频上传任务ID: {task_id}")

        print_request("GET", f"{BASE_URL}/api/v1/storage/upload/task/{task_id}")
        # 使用轮询等待上传完成
        result = poll_task_with_result(task_id, "/api/v1/storage/upload/task", "音频上传")
        if result:
            audio_url = result.get("oss_url")
            print(f"\n[前端] 音频已上传，公网URL: {audio_url}")

    if not audio_url:
        print("\n[错误] 音频上传失败")
        return

    # 步骤3: 配置视频生成参数
    print("\n[步骤3/4] 配置视频生成参数")

    video_extension = input("[用户输入] 是否扩展视频以匹配音频长度? (y/n, 默认y): ").strip().lower() != 'n'

    resolution_input = input("[用户输入] 分辨率 (留空自动调整，如 1280x720): ").strip()
    resolution = resolution_input if resolution_input else None

    # 步骤4: 生成视频
    print("\n[步骤4/4] 生成数字人视频")

    data = {
        "video_url": video_url,
        "audio_url": audio_url,
        "video_extension": video_extension
    }
    if resolution:
        data["resolution"] = resolution

    print_request("POST", f"{BASE_URL}/api/v1/video/generate", data)

    response = requests.post(f"{BASE_URL}/api/v1/video/generate", json=data)
    print_response(response)

    if response.status_code == 200:
        task_id = response.json().get("task_id")
        print(f"\n[前端] 视频生成任务ID: {task_id}")

        # 自动轮询并展示结果
        poll_task_with_result(task_id, "/api/v1/video/task", "数字人视频生成")


# ==================== 模块6: 完整工作流 ====================
def module_workflow():
    """
    前端页面: 完整工作流
    用户操作: 输入抖音链接 + 新主题 → 一键生成
    """
    print_header("模块6: 完整工作流")

    # 获取工作流模板
    print("\n[前端] 获取工作流模板...")
    response = requests.get(f"{BASE_URL}/api/v1/workflow/templates")
    templates = response.json().get("data", [])

    print("\n[前端展示] 可用工作流:")
    for i, t in enumerate(templates, 1):
        print(f"    {i}. {t.get('name')} - {t.get('description')}")

    # 用户输入
    douyin_url = input("\n[用户输入] 请输入抖音用户主页链接: ").strip()
    if not douyin_url:
        print("已取消")
        return

    topic = input("[用户输入] 请输入新视频主题: ").strip()
    if not topic:
        print("已取消")
        return

    print("\n[用户选择] 工作流类型:")
    print("    1. 快速分析 (仅AI分析)")
    print("    2. 标准流程 (分析+脚本+TTS)")
    print("    3. 完整流程 (分析+脚本+TTS+视频)")

    choice = input("[用户输入] 请选择 (1-3, 默认2): ").strip() or "2"

    workflow_map = {"1": "analysis_only", "2": "without_video", "3": "full"}
    workflow_type = workflow_map.get(choice, "without_video")

    # 前端发送请求
    data = {
        "douyin_url": douyin_url,
        "topic": topic,
        "workflow_type": workflow_type,
        "max_videos": 50
    }
    print_request("POST", f"{BASE_URL}/api/v1/workflow/run", data)

    response = requests.post(f"{BASE_URL}/api/v1/workflow/run", json=data)
    print_response(response)

    if response.status_code == 200:
        task_id = response.json().get("task_id")
        print(f"\n[前端] 工作流已启动，任务ID: {task_id}")
        print("[前端提示] 工作流正在后台执行，可以稍后查询结果")


# ==================== 主菜单 ====================

# 存储最近的任务ID
recent_task_ids = []


def module_task_manager():
    """任务管理：查看所有任务状态"""
    print_header("任务管理")

    if not recent_task_ids:
        print("\n  暂无任务记录")
        return

    print(f"\n  最近任务 ({len(recent_task_ids)}个):")

    for i, task_id in enumerate(recent_task_ids, 1):
        response = requests.get(f"{BASE_URL}/api/v1/douyin/task/{task_id}")
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown")
            progress = data.get("progress", 0)
            status_emoji = {
                "pending": "⏳",
                "running": "🔄",
                "success": "✅",
                "failed": "❌",
                "cancelled": "⏹️"
            }.get(status, "❓")

            print(f"    {i}. {task_id[:8]}... {status_emoji} {status} ({progress}%)")
        else:
            print(f"    {i}. {task_id[:8]}... ❌ 查询失败")


def module_resource_list():
    """资源管理：查看音色、上传文件等"""
    print_header("资源管理")

    print("\n  1. 查看音色列表")
    print("  2. 查看上传记录")
    print("  3. 查看 OSS 配置状态")

    choice = input("\n  请选择: ").strip()

    if choice == "1":
        print_request("GET", f"{BASE_URL}/api/v1/tts/voice/list")
        response = requests.get(f"{BASE_URL}/api/v1/tts/voice/list")
        print_response(response)

        if response.status_code == 200:
            voices = response.json().get("voices", [])
            if voices:
                print(f"\n  🎙️  可用音色 ({len(voices)}个):")
                for i, v in enumerate(voices, 1):
                    status_emoji = "✅" if v.get("is_available") else "⏳"
                    print(f"    {i}. {status_emoji} {v.get('prefix')} ({v.get('voice_id', '')[:12]}...)")
            else:
                print("\n  暂无音色，请先创建音色")

    elif choice == "2":
        print_request("GET", f"{BASE_URL}/api/v1/storage/records")
        response = requests.get(f"{BASE_URL}/api/v1/storage/records")
        print_response(response)

    elif choice == "3":
        print_request("GET", f"{BASE_URL}/api/v1/storage/config/status")
        response = requests.get(f"{BASE_URL}/api/v1/storage/config/status")
        print_response(response)


def module_workflow_guided():
    """
    工作流向导：引导用户分步骤完成完整流程
    步骤1: 准备音色（可选）
    步骤2: 准备参考视频（可选）
    步骤3: 启动工作流
    """
    print_header("完整工作流向导")

    print("\n" + "=" * 50)
    print("  工作流向导将引导你完成以下步骤:")
    print("  1. 音色准备（可选，已有音色可跳过）")
    print("  2. 参考视频准备（可选，仅完整流程需要）")
    print("  3. 启动工作流")
    print("=" * 50)

    voice_id = None
    ref_video_url = None

    # 步骤1: 音色准备
    print("\n[步骤1/3] 音色准备")
    print("  1. 查看已有音色")
    print("  2. 创建新音色")
    print("  3. 跳过（使用默认音色）")

    voice_choice = input("\n  请选择: ").strip()

    if voice_choice == "1":
        # 查看已有音色
        response = requests.get(f"{BASE_URL}/api/v1/tts/voice/list")
        if response.status_code == 200:
            voices = response.json().get("voices", [])
            available = [v for v in voices if v.get("is_available")]

            if available:
                print(f"\n  可用音色:")
                for i, v in enumerate(available, 1):
                    print(f"    {i}. {v.get('prefix')}")

                idx = input(f"\n  选择音色 (1-{len(available)}): ").strip()
                try:
                    idx = int(idx) - 1
                    if 0 <= idx < len(available):
                        voice_id = available[idx].get("voice_id")
                        print(f"  ✓ 已选择音色: {available[idx].get('prefix')}")
                except:
                    pass

        if not voice_id:
            print("  未选择音色，将使用默认音色")

    elif voice_choice == "2":
        # 创建新音色 - 调用音色克隆模块
        print("\n  进入音色创建流程...")
        module_voice_clone()
        return

    # 步骤2: 参考视频准备
    print("\n[步骤2/3] 参考视频准备")
    need_video = input("\n  是否需要生成数字人视频? (y/n): ").strip().lower() == 'y'

    if need_video:
        print("  1. 上传新视频")
        print("  2. 输入已有视频URL")
        print("  3. 跳过")

        video_choice = input("\n  请选择: ").strip()

        if video_choice == "1":
            video_path = input("\n  请输入本地视频文件路径: ").strip()
            if video_path:
                print(f"\n  [前端] 正在上传视频...")
                response = requests.post(
                    f"{BASE_URL}/api/v1/storage/upload/path",
                    json={"file_path": video_path, "file_type": "video"}
                )

                if response.status_code == 200:
                    task_id = response.json().get("task_id")
                    result = poll_task_with_result(task_id, "/api/v1/storage/upload/task", "视频上传")
                    if result:
                        ref_video_url = result.get("oss_url")
                        print(f"  ✓ 视频已上传")

        elif video_choice == "2":
            ref_video_url = input("\n  请输入视频URL: ").strip()

    # 步骤3: 启动工作流
    print("\n[步骤3/3] 启动工作流")

    douyin_url = input("\n  请输入抖音用户主页链接: ").strip()
    if not douyin_url:
        print("  已取消")
        return

    topic = input("  请输入新视频主题: ").strip()
    if not topic:
        print("  已取消")
        return

    # 选择工作流类型
    if ref_video_url and voice_id:
        workflow_type = "full"
        print(f"\n  将执行: 完整流程（含视频生成）")
    elif voice_id:
        workflow_type = "without_video"
        print(f"\n  将执行: 标准流程（分析+脚本+TTS）")
    else:
        workflow_type = "analysis_only"
        print(f"\n  将执行: 快速分析（仅AI分析）")

    confirm = input("\n  确认启动? (y/n): ").strip().lower() == 'y'
    if not confirm:
        print("  已取消")
        return

    # 发送请求
    data = {
        "douyin_url": douyin_url,
        "topic": topic,
        "workflow_type": workflow_type,
        "max_videos": 50
    }
    if voice_id:
        data["voice_id"] = voice_id
    if ref_video_url:
        data["ref_video_url"] = ref_video_url

    print_request("POST", f"{BASE_URL}/api/v1/workflow/run", data)
    response = requests.post(f"{BASE_URL}/api/v1/workflow/run", json=data)
    print_response(response)

    if response.status_code == 200:
        task_id = response.json().get("task_id")
        recent_task_ids.append(task_id)

        # 自动轮询并展示结果
        poll_task_with_result(task_id, "/api/v1/workflow/task", "完整工作流")


def main():
    import sys

    modules = {
        "1": ("抖音抓取+分析+生成（完整流程）", module_douyin_fetch),
        "2": ("AI脚本生成", module_ai_script),
        "3": ("音色克隆", module_voice_clone),
        "4": ("语音合成", module_tts_speech),
        "5": ("数字人视频生成", module_video_generate),
        "6": ("完整工作流向导", module_workflow_guided),
        "7": ("任务管理", module_task_manager),
        "8": ("资源管理", module_resource_list),
    }

    while True:
        print("\n" + "#" * 50)
        print("#  前端交互模拟器")
        print("#" * 50)
        print("\n选择要模拟的前端页面:")
        for num, (name, _) in modules.items():
            print(f"  {num}. {name}")
        print("  0. 退出")

        if len(sys.argv) > 1:
            choice = sys.argv[1]
            # 命令行模式只运行一次
            if choice in modules:
                modules[choice][1]()
            break
        else:
            choice = input("\n请选择页面: ").strip()

            if choice == "0":
                print("退出")
                break
            elif choice in modules:
                modules[choice][1]()
            else:
                print("无效选项")


if __name__ == "__main__":
    # 检查服务
    try:
        requests.get(BASE_URL, timeout=2)
    except:
        print(f"错误: 无法连接到 {BASE_URL}")
        print("请先启动服务: cd python_services && python main.py")
        exit(1)

    main()
