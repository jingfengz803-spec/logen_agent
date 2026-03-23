"""
测试 CosyVoice API 调用
"""
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv('.env')

from cosyvoice_tts import CosyVoiceTTSClient

def test_api():
    print("=" * 60)
    print("CosyVoice API 测试")
    print("=" * 60)
    
    # 检查 API Key
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("✗ DASHSCOPE_API_KEY 未设置")
        return
    
    print(f"✓ API Key: {api_key[:10]}...{api_key[-4:]}")
    
    # 列出可用音色
    print("\n[1] 查询可用音色...")
    client = CosyVoiceTTSClient()
    
    try:
        voices = client.get_ready_voices()
        print(f"✓ 可用音色数量: {len(voices)}")
        
        if voices:
            print(f"  示例音色ID: {voices[0]}")
            test_voice = voices[0]
        else:
            print("  没有可用音色，使用预设模型测试")
            test_voice = "cosyvoice-v1"
    except Exception as e:
        print(f"✗ 查询音色失败: {e}")
        print("  使用预设模型测试")
        test_voice = "cosyvoice-v1"
    
    # 测试短文本
    print(f"\n[2] 测试短文本合成...")
    print(f"  音色: {test_voice}")
    print(f"  文本: 你好")
    
    try:
        audio = client.speech(
            text="你好",
            voice=test_voice,
            output_path="data/test_short.mp3"
        )
        print(f"✓ 成功！音频大小: {len(audio)} bytes")
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 测试长文本（你提供的文本）
    long_text = "今天接了一个刑事辩护的案子，客户说：律师，我绝对没犯罪，结果证据一出来，我直接崩溃了。"
    
    print(f"\n[3] 测试较长文本合成...")
    print(f"  音色: {test_voice}")
    print(f"  文本长度: {len(long_text)} 字符")
    print(f"  文本: {long_text[:50]}...")
    
    try:
        audio = client.speech(
            text=long_text,
            voice=test_voice,
            output_path="data/test_long.mp3"
        )
        print(f"✓ 成功！音频大小: {len(audio)} bytes")
        
        if len(audio) == 0:
            print("✗ 警告：音频大小为0！API返回了空数据")
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试超长文本（你提供的完整文本）
    full_text = "今天接了一个刑事辩护的案子，客户说：律师，我绝对没犯罪，结果证据一出来，我直接崩溃了。刑事辩护的崩溃瞬间：当客户说绝对清白，结果监控视频拍得清清楚楚。这种案子，三点一定要记住！第一，千万别轻易相信客户的一面之词，除非你真的核实了所有证据。第二，刑事辩护中，证据链是关键，比如证人证言、物证、书证，缺一环都可能输掉官司。第三，年轻律师别轻易接复杂刑事案，除非你有老律师带，否则压力大到让你怀疑人生。我实习时，一个老律师月入反差巨大，他靠刑事辩护赚得盆满钵满，但崩溃瞬间也特别多，比如客户突然翻供，把律师整不会了。给刑事辩护的建议：别轻易承诺结果，除非你真的有把握，多学法律知识，多积累实战经验。职场生存指南，从崩溃到成长，建议收藏，标签互动起来！"
    
    print(f"\n[4] 测试超长文本合成...")
    print(f"  音色: {test_voice}")
    print(f"  文本长度: {len(full_text)} 字符")
    
    try:
        audio = client.speech(
            text=full_text,
            voice=test_voice,
            output_path="data/test_full.mp3"
        )
        print(f"  返回音频大小: {len(audio)} bytes")
        
        if len(audio) == 0:
            print("✗ 问题找到了！超长文本返回了空音频")
            print("  可能原因：CosyVoice API 对文本长度有限制")
            print("  建议使用分段合成: speech_from_segments()")
        else:
            print(f"✓ 成功！")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_api()
