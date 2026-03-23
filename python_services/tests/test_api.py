"""
API 测试 - 统一入口
用于测试所有 API 接口，支持全部测试或单个模块测试
"""
import requests


BASE_URL = "http://localhost:8088"


# ==================== 模块测试函数 ====================

def test_health():
    """健康检查"""
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
    print("[OK] Health check")


def test_douyin():
    """抖音抓取模块"""
    # 抓取用户视频
    r = requests.post(f"{BASE_URL}/api/v1/douyin/fetch/user",
                      json={"url": "https://www.douyin.com/user/test", "max_count": 10})
    assert r.status_code == 200
    task_id = r.json()["task_id"]
    print(f"[OK] Douyin fetch (task_id: {task_id})")

    # 获取缓存视频
    r = requests.get(f"{BASE_URL}/api/v1/douyin/videos", params={"limit": 5})
    assert r.status_code == 200
    print(f"[OK] Douyin cached videos")


def test_ai():
    """AI 分析模块"""
    # 火爆分析
    r = requests.post(f"{BASE_URL}/api/v1/ai/analyze/viral",
                      json={"video_data": [{"desc": "test"}]})
    assert r.status_code == 200
    print(f"[OK] AI viral analysis")

    # 生成脚本
    r = requests.post(f"{BASE_URL}/api/v1/ai/generate/script",
                      json={"reference_data": {}, "topic": "test"})
    assert r.status_code == 200
    print(f"[OK] AI script generation")


def test_tts():
    """TTS 语音模块"""
    r = requests.get(f"{BASE_URL}/api/v1/tts/voice/list")
    assert r.status_code == 200
    print(f"[OK] TTS voice list")


def test_workflow():
    """工作流模块"""
    r = requests.get(f"{BASE_URL}/api/v1/workflow/templates")
    assert r.status_code == 200
    print(f"[OK] Workflow templates")

    r = requests.post(f"{BASE_URL}/api/v1/workflow/run",
                      json={"douyin_url": "https://www.douyin.com/user/test",
                            "topic": "test", "workflow_type": "analysis_only"})
    assert r.status_code == 200
    print(f"[OK] Workflow run")


# ==================== 测试套件 ====================

TESTS = {
    "health": ("健康检查", test_health),
    "douyin": ("抖音抓取", test_douyin),
    "ai": ("AI分析", test_ai),
    "tts": ("TTS语音", test_tts),
    "workflow": ("工作流", test_workflow),
}


def run_all():
    """运行所有测试"""
    print("\n" + "=" * 40)
    print("Running All API Tests")
    print("=" * 40)

    passed = 0
    for name, (desc, func) in TESTS.items():
        try:
            func()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {desc}: {e}")
        except Exception as e:
            print(f"[ERROR] {desc}: {e}")

    print(f"\n{'=' * 40}")
    print(f"Results: {passed}/{len(TESTS)} passed")
    print("=" * 40)


def run_single(name):
    """运行单个测试"""
    if name not in TESTS:
        print(f"Unknown test: {name}")
        print(f"Available: {', '.join(TESTS.keys())}")
        return

    desc, func = TESTS[name]
    print(f"\n[{desc.upper()}]")
    try:
        func()
        print(f"\n>>> Test passed!")
    except Exception as e:
        print(f"\n>>> Test failed: {e}")


# ==================== 主入口 ====================

if __name__ == "__main__":
    import sys

    # 检查服务
    try:
        requests.get(BASE_URL, timeout=2)
    except:
        print(f"Error: Cannot connect to {BASE_URL}")
        print("Please start server first: python run_server.py")
        sys.exit(1)

    if len(sys.argv) > 1:
        # 命令行指定: python test_api.py douyin
        run_single(sys.argv[1])
    else:
        # 无参数运行全部
        run_all()

    print("\nUsage: python test_api.py [module_name]")
    print("Modules: " + ", ".join(TESTS.keys()))
