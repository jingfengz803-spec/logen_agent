"""
URL解析工具 - 从抖音URL中提取用户ID或视频ID
支持的URL格式:
- 用户主页: https://www.douyin.com/user/MS4wLjABAAAA...
- 视频链接: https://www.douyin.com/video/7123456789012345678
- 分享链接: https://v.douyin.com/xxxxxx/
"""

import re
from urllib.parse import urlparse, parse_qs


def parse_douyin_url(url):
    """
    解析抖音URL，返回类型和ID

    Args:
        url: 抖音URL字符串

    Returns:
        dict: {
            'type': 'user' | 'video' | 'share' | 'search' | 'note' | 'unknown',
            'id': 提取的ID,
            'original_url': 原始URL,
            'extra': 额外信息（如modal_id等）
        }
    """
    url = url.strip()
    result = {
        'type': 'unknown',
        'id': None,
        'original_url': url,
        'extra': {}
    }

    # 处理短链接 (v.douyin.com)
    if 'v.douyin.com' in url or 'douyin.v.net' in url:
        result['type'] = 'share'
        # 短链接需要请求后获取真实URL，这里先标记
        return result

    # 解析用户主页链接
    # 格式: https://www.douyin.com/user/MS4wLjABAAAA...
    user_pattern = r'douyin\.com/user/([a-zA-Z0-9_-]+)'
    user_match = re.search(user_pattern, url)
    if user_match:
        result['type'] = 'user'
        result['id'] = user_match.group(1)
        return result

    # 解析视频链接 - 多种格式
    # 格式1: https://www.douyin.com/video/7123456789012345678
    video_pattern = r'douyin\.com/video/(\d+)'
    video_match = re.search(video_pattern, url)
    if video_match:
        result['type'] = 'video'
        result['id'] = video_match.group(1)
        return result

    # 格式2: 从URL参数中提取视频ID (modal_id)
    # 如: ?modal_id=7570371334275992443
    modal_id_pattern = r'modal_id=(\d+)'
    modal_match = re.search(modal_id_pattern, url)
    if modal_match:
        result['type'] = 'video'
        result['id'] = modal_match.group(1)
        result['extra']['modal_id'] = modal_match.group(1)
        return result

    # 格式3: 从URL路径中直接提取数字ID
    # 如: https://www.douyin.com/7570371334275992443
    direct_id_pattern = r'douyin\.com/(\d{19})'
    direct_match = re.search(direct_id_pattern, url)
    if direct_match:
        result['type'] = 'video'
        result['id'] = direct_match.group(1)
        return result

    # 解析笔记链接 (图文)
    # 格式: https://www.douyin.com/note/7123456789012345678
    note_pattern = r'douyin\.com/note/(\d+)'
    note_match = re.search(note_pattern, url)
    if note_match:
        result['type'] = 'note'
        result['id'] = note_match.group(1)
        return result

    # 解析搜索/精选页面
    # 格式: https://www.douyin.com/jingxuan/search/...
    if '/jingxuan/search/' in url or '/search/' in url:
        result['type'] = 'search'
        # 尝试从参数中提取modal_id
        if modal_match:
            result['id'] = modal_match.group(1)
            result['extra']['modal_id'] = modal_match.group(1)
        return result

    # 尝试从路径中提取 (备用)
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')

    if len(path_parts) >= 2:
        if path_parts[0] == 'user':
            result['type'] = 'user'
            result['id'] = path_parts[1]
        elif path_parts[0] == 'video':
            result['type'] = 'video'
            result['id'] = path_parts[1]
        elif path_parts[0] == 'note':
            result['type'] = 'note'
            result['id'] = path_parts[1]

    return result


def resolve_share_url(url, headers=None):
    """
    解析短链接，获取真实URL

    Args:
        url: 短链接
        headers: 请求头（重要：需要正确的Cookie和User-Agent）

    Returns:
        str: 真实URL，失败返回None
    """
    import requests

    # 如果没有提供headers，使用默认的（可能不够）
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    if headers:
        default_headers.update(headers)

    try:
        # 方法1: 使用HEAD请求（更快）
        response = requests.head(
            url,
            headers=default_headers,
            allow_redirects=True,
            timeout=10
        )
        if response.url and 'douyin.com' in response.url:
            return response.url

        # 方法2: HEAD失败则使用GET
        response = requests.get(
            url,
            headers=default_headers,
            allow_redirects=True,
            timeout=10
        )
        return response.url

    except Exception as e:
        print(f"解析短链接失败: {e}")
        return None


def get_user_id_from_url(url, headers=None):
    """
    从任意抖音URL中提取用户ID

    Args:
        url: 抖音URL
        headers: 请求头（用于解析短链接）

    Returns:
        str: 用户ID或None
    """
    parsed = parse_douyin_url(url)

    if parsed['type'] == 'user':
        return parsed['id']

    # 如果是短链接，先解析
    if parsed['type'] == 'share':
        real_url = resolve_share_url(url, headers)
        if real_url:
            return get_user_id_from_url(real_url, headers)

    return None


def get_video_id_from_url(url, headers=None):
    """
    从任意抖音URL中提取视频ID

    Args:
        url: 抖音URL
        headers: 请求头（用于解析短链接）

    Returns:
        str: 视频ID或None
    """
    parsed = parse_douyin_url(url)

    if parsed['type'] == 'video':
        return parsed['id']

    # 如果是短链接，先解析
    if parsed['type'] == 'share':
        real_url = resolve_share_url(url, headers)
        if real_url:
            return get_video_id_from_url(real_url, headers)

    return None


if __name__ == "__main__":
    # 测试用例 - 覆盖各种抖音URL格式
    test_urls = [
        # 1. 标准用户主页
        "https://www.douyin.com/user/MS4wLjABAAAA3q_M7SAG4eQnFrskafFBDLnycg_2s21oi7Q_aI42C2Q",

        # 2. 标准视频链接
        "https://www.douyin.com/video/7570371334275992443",

        # 3. 精选搜索页面（带modal_id）
        "https://www.douyin.com/jingxuan/search/%E4%B8%AD%E5%9B%BD%E8%A1%97%E5%A4%B4%E5%B0%8F%E5%90%83?aid=bcf00a7a-32fd-42f3-bbd2-0087e22527ac&modal_id=7570371334275992443&type=general",

        # 4. 直接ID格式
        "https://www.douyin.com/7570371334275992443",

        # 5. 短链接
        "https://v.douyin.com/xxxxxx/",

        # 6. 测试链接
        "https://www.douyin.com/jingxuan/search/%E4%B8%AD%E5%9B%BD%E8%A1%97%E5%A4%B4%E5%B0%8F%E5%90%83?aid=bcf00a7a-32fd-42f3-bbd2-0087e22527ac&modal_id=7570371334275992443&type=general",

        # 7. 用户主页（无user前缀）
        "https://www.douyin.com/MS4wLjABAAAA3q_M7SAG4eQnFrskafFBDLnycg_2s21oi7Q_aI42C2Q",
    ]

    print("="*80)
    print("抖音URL解析工具 - 测试")
    print("="*80)

    for i, url in enumerate(test_urls, 1):
        print(f"\n【测试 {i}】")
        print(f"URL: {url}")
        result = parse_douyin_url(url)
        print(f"类型: {result['type']}")
        print(f"ID: {result['id']}")
        if result['extra']:
            print(f"额外信息: {result['extra']}")
        print("-" * 80)

    # 测试短链接解析（需要网络）
    print("\n" + "="*80)
    print("测试短链接解析（需要有效的短链接）")
    print("="*80)
    print("\n注意: 短链接解析需要网络请求，如果失败请检查:")
    print("1. 网络连接")
    print("2. 短链接是否有效")
    print("3. 是否需要Cookie")
