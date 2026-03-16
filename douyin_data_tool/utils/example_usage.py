"""
URL解析工具使用示例
展示如何从各种抖音URL中提取ID
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from url_parser import parse_douyin_url, get_user_id_from_url, get_video_id_from_url


def print_result(url, result):
    """打印解析结果"""
    print(f"URL: {url}")
    print(f"  类型: {result['type']}")
    print(f"  ID: {result['id']}")
    if result.get('extra'):
        print(f"  额外信息: {result['extra']}")
    print()


def main():
    print("="*80)
    print("抖音URL解析工具 - 使用示例")
    print("="*80)
    print()

    # 示例1: 解析用户主页
    print("【示例1: 解析用户主页】")
    user_url = "https://www.douyin.com/user/MS4wLjABAAAA3q_M7SAG4eQnFrskafFBDLnycg_2s21oi7Q_aI42C2Q"
    result = parse_douyin_url(user_url)
    print_result(user_url, result)

    # 示例2: 解析视频链接
    print("【示例2: 解析视频链接】")
    video_url = "https://www.douyin.com/video/7570371334275992443"
    result = parse_douyin_url(video_url)
    print_result(video_url, result)

    # 示例3: 解析搜索页面（你的场景）
    print("【示例3: 解析搜索页面（带modal_id）】")
    search_url = "https://www.douyin.com/jingxuan/search/%E4%B8%AD%E5%9B%BD%E8%A1%97%E5%A4%B4%E5%B0%8F%E5%90%83?aid=bcf00a7a-32fd-42f3-bbd2-0087e22527ac&modal_id=7570371334275992443&type=general"
    result = parse_douyin_url(search_url)
    print_result(search_url, result)

    # 示例4: 快速获取视频ID
    print("【示例4: 快速获取视频ID】")
    video_id = get_video_id_from_url(search_url)
    print(f"从搜索URL提取的视频ID: {video_id}")
    print()

    # 示例5: 批量解析
    print("【示例5: 批量解析URL列表】")
    urls = [
        "https://www.douyin.com/video/7570371334275992443",
        "https://www.douyin.com/7570371334275992443",
        "https://www.douyin.com/jingxuan/search/xxx?modal_id=7570371334275992443",
    ]

    for url in urls:
        video_id = get_video_id_from_url(url)
        print(f"  {url[:60]}... -> {video_id}")
    print()

    # 示例6: 集成到数据抓取流程
    print("【示例6: 集成到数据抓取流程】")
    print("""
    # 在你的代码中使用
    from utils.url_parser import get_video_id_from_url

    # 从分享的URL中提取视频ID
    url = input("请输入抖音视频URL: ")
    video_id = get_video_id_from_url(url)

    if video_id:
        print(f"提取成功！视频ID: {video_id}")
        # 然后可以用这个ID调用API获取视频详情
        # video_data = fetch_video_detail(video_id)
    else:
        print("无法提取视频ID，请检查URL格式")
    """)


if __name__ == "__main__":
    main()