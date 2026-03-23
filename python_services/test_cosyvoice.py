"""
测试 CosyVoice 音色创建和列表
"""
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv('.env')

def test_cosyvoice():
    print("=" * 60)
    print("CosyVoice 测试")
    print("=" * 60)

    # 检查 API Key
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ 未配置 DASHSCOPE_API_KEY")
        print("请在 .env 文件中添加: DASHSCOPE_API_KEY=sk-xxxxx")
        return False

    print(f"✓ API Key 已配置: {api_key[:10]}...")

    try:
        from longgraph.cosyvoice_tts import CosyVoiceTTSClient

        client = CosyVoiceTTSClient()

        # 测试1: 获取音色列表
        print("\n[测试1] 获取音色列表...")
        voices = client.list_voices(page_size=10)

        if voices:
            print(f"✓ 获取到 {len(voices)} 个音色:")
            for i, v in enumerate(voices, 1):
                print(f"  {i}. {v.get('voice_id', 'N/A')} - {v.get('status', 'UNKNOWN')}")
        else:
            print("✓ 暂无音色（这是正常的，如果还没创建过）")

        # 测试2: 打印音色状态
        print("\n[测试2] 打印音色状态...")
        client.print_voices_status()

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_cosyvoice()
