"""
抖音API诊断工具
帮助找出为什么抓取失败
"""

import os
import sys
import json
import requests

# 修复编码
if sys.platform == "win32":
    import io
    if not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(__file__))
from config import HEADERS, USER_IDS

def diagnose():
    """诊断抖音API连接"""
    
    print("=" * 60)
    print("抖音API诊断工具")
    print("=" * 60)
    
    # 1. 检查Cookie
    print("\n【1】检查Cookie配置")
    cookie = HEADERS.get("Cookie", "")
    if not cookie or "enter_pc_once=1" in cookie:
        print("❌ Cookie未配置或使用默认值")
        print("   请在 config.py 中更新 Cookie")
        return False
    else:
        print("✓ Cookie已配置")
        
    # 检查关键参数
    required_params = ["ttwid", "s_v_web_id", "passport_csrf_token"]
    missing = []
    for param in required_params:
        if param not in cookie:
            missing.append(param)
    if missing:
        print(f"⚠️ Cookie可能缺少以下参数: {', '.join(missing)}")
        print("   这可能导致请求失败，请尝试从浏览器重新复制完整Cookie")
    
    # 2. 检查用户ID
    print("\n【2】检查用户ID配置")
    if not USER_IDS:
        print("❌ USER_IDS为空")
        return False
    
    user_id = USER_IDS[0]
    print(f"用户ID: {user_id[:50]}...")
    
    # 清理用户ID（去掉多余的查询参数）
    if "?" in user_id:
        user_id = user_id.split("?")[0]
        print(f"清理后的用户ID: {user_id}")
    
    # 3. 测试API请求
    print("\n【3】测试API请求")
    
    api_url = "https://www.douyin.com/aweme/v1/web/aweme/post/"
    
    params = {
        "device_platform": "webapp",
        "aid": "6383",
        "sec_user_id": user_id,
        "count": 10,
        "max_cursor": 0
    }
    
    print(f"API URL: {api_url}")
    print(f"参数: {json.dumps(params, ensure_ascii=False)}")
    
    try:
        resp = requests.get(api_url, headers=HEADERS, params=params, timeout=10)
        print(f"\n状态码: {resp.status_code}")
        
        data = resp.json()
        print(f"\n响应数据结构:")
        print(f"  status_code: {data.get('status_code')}")
        print(f"  has_more: {data.get('has_more')}")
        print(f"  aweme_list 存在: {'aweme_list' in data}")
        print(f"  aweme_list 长度: {len(data.get('aweme_list', []))}")
        
        if data.get('status_code') == 0 and data.get('aweme_list'):
            print("\n✓ 请求成功！获取到视频数据")
            print(f"\n第一个视频示例:")
            video = data['aweme_list'][0]
            desc = video.get('desc', '无描述')
            likes = video.get('statistics', {}).get('digg_count', 0)
            print(f"  描述: {desc[:50]}...")
            print(f"  点赞: {likes}")
            return True
        else:
            print("\n❌ 未获取到视频数据")
            print(f"\n完整响应:")
            print(json.dumps(data, ensure_ascii=False, indent=2))
            
            # 检查是否是用户ID问题
            if data.get('status_code') != 0:
                error_msg = data.get('status_msg', '')
                print(f"\n可能的问题:")
                print(f"  1. 用户ID不正确")
                print(f"  2. 用户设置了隐私权限")
                print(f"  3. Cookie已过期或无效")
            
            return False
            
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        return False


if __name__ == "__main__":
    diagnose()
