"""测试 LLM API 连接"""
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 从项目根目录加载 .env 文件
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / '.env', override=True)

def test_deepseek():
    print("测试 DeepSeek API...")
    try:
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
            timeout=30.0
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "你好，回复'OK'"}],
            max_tokens=10
        )
        print(f"✓ DeepSeek API 正常: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ DeepSeek API 失败: {e}")
        return False

def test_zhipu():
    print("\n测试智谱 API...")
    try:
        client = OpenAI(
            api_key=os.getenv("ZAI_API_KEY"),
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            timeout=30.0
        )
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": "你好，回复'OK'"}],
            max_tokens=10
        )
        print(f"✓ 智谱 API 正常: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ 智谱 API 失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("LLM API 连接测试")
    print("=" * 50)

    deepseek_ok = test_deepseek()
    zhipu_ok = test_zhipu()

    print("\n" + "=" * 50)
    print("测试结果:")
    print(f"  DeepSeek: {'✓ 可用' if deepseek_ok else '✗ 不可用'}")
    print(f"  智谱 AI:  {'✓ 可用' if zhipu_ok else '✗ 不可用'}")
    print("=" * 50)
