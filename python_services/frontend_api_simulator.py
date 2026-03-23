"""
前端 API 调用模拟器
模拟前端发送请求到后端 API，验证接口和数据格式
用于前后端对接前的测试
"""
import requests
import json


BASE_URL = "http://localhost:8088"


def print_response(title, response):
    """打印响应结果"""
    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")
    print(f"请求: {response.request.method} {response.request.url}")
    if response.request.body:
        body = response.request.body
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        print(f"参数: {body}")
    print(f"\n状态码: {response.status_code}")
    print(f"响应数据:")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


# ==================== 前端场景模拟 ====================

def scenario_1_fetch_and_analyze():
    """场景1: 抓取抖音视频 -> AI分析"""
    print("\n" + "#" * 50)
    print("# 场景1: 抓取抖音视频并分析")
    print("#" * 50)

    # 步骤1: 前端发起抓取请求
    response = requests.post(
        f"{BASE_URL}/api/v1/douyin/fetch/user",
        json={
            "url": "https://www.douyin.com/user/MS4wLjABAAAA...",
            "max_count": 20,
            "enable_filter": True,
            "min_likes": 100
        }
    )
    print_response("步骤1: 抓取抖音用户视频", response)

    # 获取 task_id
    task_id = response.json().get("task_id")
    if not task_id:
        print("错误: 未获取到 task_id")
        return

    # 步骤2: 前端轮询任务状态
    print(f"\n>>> 前端开始轮询任务状态...")
    response = requests.get(f"{BASE_URL}/api/v1/douyin/task/{task_id}")
    print_response("步骤2: 查询任务状态", response)


def scenario_2_generate_content():
    """场景2: AI 生成新内容"""
    print("\n" + "#" * 50)
    print("# 场景2: AI 生成新内容")
    print("#" * 50)

    # 前端发送生成脚本请求
    response = requests.post(
        f"{BASE_URL}/api/v1/ai/generate/script",
        json={
            "reference_data": {
                "style": "专业干货",
                "video_type": "知识分享",
                "examples": ["高效工作法", "职场生存指南"]
            },
            "topic": "如何应对职场压力",
            "target_duration": 60,
            "tone": "亲切",
            "include_hashtags": True
        }
    )
    print_response("AI 生成脚本", response)

    # 检查返回数据格式是否符合前端预期
    data = response.json()
    print(f"\n>>> 前端预期字段检查:")
    print(f"  - task_id: {('✓' if 'task_id' in data else '✗')} {data.get('task_id', 'N/A')}")
    print(f"  - status: {('✓' if 'status' in data else '✗')} {data.get('status', 'N/A')}")


def scenario_3_full_workflow():
    """场景3: 完整工作流（前端一键生成）"""
    print("\n" + "#" * 50)
    print("# 场景3: 完整工作流")
    print("#" * 50)

    # 前端一键启动工作流
    response = requests.post(
        f"{BASE_URL}/api/v1/workflow/run",
        json={
            "douyin_url": "https://www.douyin.com/user/MS4wLjABAAAA...",
            "topic": "如何提高工作效率",
            "workflow_type": "without_video",  # 不含视频生成
            "max_videos": 50,
            "output_name": "efficiency_tips"
        }
    )
    print_response("启动完整工作流", response)


def scenario_4_tts_workflow():
    """场景4: TTS 语音合成"""
    print("\n" + "#" * 50)
    print("# 场景4: TTS 语音合成")
    print("#" * 50)

    # 步骤1: 获取可用音色列表（前端展示给用户选择）
    response = requests.get(f"{BASE_URL}/api/v1/tts/voice/list")
    print_response("获取音色列表", response)

    # 步骤2: 用户选择音色后，前端发起语音合成请求
    print(f"\n>>> 假设用户选择音色: cosyvoice-v3.5-flash-xxx")
    response = requests.post(
        f"{BASE_URL}/api/v1/tts/speech",
        json={
            "text": "大家好，今天我们来聊聊如何提高工作效率。",
            "voice_id": "cosyvoice-v3.5-flash-xxx",
            "output_format": "mp3"
        }
    )
    print_response("文字转语音", response)


def scenario_5_error_handling():
    """场景5: 错误处理测试"""
    print("\n" + "#" * 50)
    print("# 场景5: 错误处理测试")
    print("#" * 50)

    # 测试1: 无效的 URL
    print("\n>>> 测试: 无效的抖音 URL")
    response = requests.post(
        f"{BASE_URL}/api/v1/douyin/fetch/user",
        json={
            "url": "https://invalid.com/user/test",
            "max_count": 10
        }
    )
    print_response("无效 URL 请求", response)
    print(f">>> 前端应处理错误: {response.status_code >= 400 or 'error' in response.json()}")

    # 测试2: 缺少必填参数
    print("\n>>> 测试: 缺少必填参数")
    response = requests.post(
        f"{BASE_URL}/api/v1/ai/generate/script",
        json={
            "topic": "测试主题"
            # 缺少 reference_data
        }
    )
    print_response("缺少参数请求", response)
    print(f">>> 前端应处理错误: {response.status_code >= 400}")


def scenario_6_get_resources():
    """场景6: 前端获取资源数据"""
    print("\n" + "#" * 50)
    print("# 场景6: 前端获取资源")
    print("#" * 50)

    # 前端获取已缓存的视频列表（展示给用户）
    response = requests.get(
        f"{BASE_URL}/api/v1/douyin/videos",
        params={"limit": 10, "offset": 0}
    )
    print_response("获取缓存视频列表", response)

    # 前端获取工作流模板（展示选项给用户）
    response = requests.get(f"{BASE_URL}/api/v1/workflow/templates")
    print_response("获取工作流模板", response)


# ==================== 单接口测试 ====================

def test_single_api(endpoint, method="GET", params=None, body=None):
    """测试单个接口"""
    url = f"{BASE_URL}{endpoint}"

    print(f"\n{'='*50}")
    print(f"测试接口: {method} {endpoint}")
    print(f"{'='*50}")

    if method == "GET":
        response = requests.get(url, params=params)
    elif method == "POST":
        response = requests.post(url, json=body)

    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

    return response


# ==================== 主菜单 ====================

def main():
    import sys

    scenarios = {
        "1": ("抓取并分析", scenario_1_fetch_and_analyze),
        "2": ("AI 生成内容", scenario_2_generate_content),
        "3": ("完整工作流", scenario_3_full_workflow),
        "4": ("TTS 语音合成", scenario_4_tts_workflow),
        "5": ("错误处理测试", scenario_5_error_handling),
        "6": ("获取资源数据", scenario_6_get_resources),
    }

    print("=" * 50)
    print("前端 API 调用模拟器")
    print("=" * 50)
    print("\n选择测试场景:")
    for num, (name, _) in scenarios.items():
        print(f"{num}. {name}")
    print("\n0. 退出")
    print("s. 单接口测试")

    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\n请选择: ").strip()

    if choice == "0":
        return
    elif choice == "s":
        # 单接口测试
        endpoint = input("接口路径 (如 /api/v1/ai/generate/script): ")
        method = input("方法 (GET/POST, 默认GET): ") or "GET"
        body = None
        if method == "POST":
            body_str = input("请求体 (JSON): ")
            body = json.loads(body_str) if body_str else None
        test_single_api(endpoint, method, body=body)
    elif choice in scenarios:
        name, func = scenarios[choice]
        try:
            func()
        except Exception as e:
            print(f"\n>>> 错误: {e}")
    else:
        print("无效选项")


if __name__ == "__main__":
    # 确保服务已启动！
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except:
        print(f"错误: 无法连接到 {BASE_URL}")
        print("请先启动服务: python python_services/run_server.py")
        exit(1)

    main()
