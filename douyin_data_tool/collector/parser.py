import re
from typing import List, Dict, Any


def extract_hashtags(text: str) -> List[str]:
    """
    从文案中提取话题标签

    Args:
        text: 视频文案文本

    Returns:
        List[str]: 话题标签列表，如 ["#普法", "#法律咨询"]
    """
    if not text:
        return []

    # 匹配 #标签 格式
    pattern = r'#([^\s#]+)'
    hashtags = re.findall(pattern, text)
    return list(set(hashtags))  # 去重


def extract_keywords(text: str) -> List[str]:
    """
    从文案中提取关键词

    Args:
        text: 视频文案文本

    Returns:
        List[str]: 关键词列表
    """
    if not text:
        return []

    # 移除话题标签
    clean_text = re.sub(r'#([^\s#]+)', '', text)

    # 简单分词（可替换为 jieba 等专业分词工具）
    words = re.findall(r'[\u4e00-\u9fa5]{2,}', clean_text)
    return words[:10]  # 返回前10个词


def parse_aweme_list(data):
    """解析视频列表数据（基础版本，保留向后兼容）"""
    videos = []
    aweme_list = data.get("aweme_list", [])
    for item in aweme_list:
        video = {
            "aweme_id": item["aweme_id"],
            "desc": item.get("desc", ""),
            "create_time": item["create_time"],
            "author": item.get("author", {}).get("nickname", ""),
            "like": item.get("statistics", {}).get("digg_count", 0),
            "comment": item.get("statistics", {}).get("comment_count", 0),
            "share": item.get("statistics", {}).get("share_count", 0),
        }
        videos.append(video)
    return videos


def parse_aweme_list_with_tags(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    解析视频列表数据（增强版，包含话题标签提取）

    Args:
        data: API返回的原始数据

    Returns:
        List[Dict]: 包含详细信息的视频列表
    """
    videos = []
    aweme_list = data.get("aweme_list", [])

    for item in aweme_list:
        desc = item.get("desc", "")

        # 提取话题标签
        hashtags = extract_hashtags(desc)

        # 从文字话题中获取额外的标签
        text_extra = item.get("text_extra", [])
        hash_tag_names = [t.get("hashtag_name", "") for t in text_extra if t.get("hashtag_name")]

        # 合并所有标签
        all_tags = list(set(hashtags + hash_tag_names))

        video = {
            # 基础信息
            "aweme_id": item.get("aweme_id", ""),
            "desc": desc,
            "desc_clean": desc,  # 清理后的文案（不含标签）
            "create_time": item.get("create_time", 0),

            # 作者信息
            "author": item.get("author", {}).get("nickname", ""),
            "author_id": item.get("author", {}).get("unique_id", ""),
            "sec_user_id": item.get("author", {}).get("sec_user_id", ""),

            # 统计数据
            "statistics": {
                "like": item.get("statistics", {}).get("digg_count", 0),
                "comment": item.get("statistics", {}).get("comment_count", 0),
                "share": item.get("statistics", {}).get("share_count", 0),
                "play": item.get("statistics", {}).get("play_count", 0),
                "collect": item.get("statistics", {}).get("collect_count", 0),
            },

            # 话题标签
            "hashtags": all_tags,
            "hashtag_count": len(all_tags),

            # 音乐信息
            "music": item.get("music", {}).get("title", ""),

            # 视频信息
            "duration": item.get("duration", 0) / 1000 if item.get("duration") else 0,  # 转换为秒
            "video_url": item.get("video", {}).get("play_addr", {}).get("url_list", [""])[0],

            # 关键词
            "keywords": extract_keywords(desc),
        }
        videos.append(video)

    return videos


def get_video_script(video: Dict[str, Any]) -> str:
    """
    提取视频文案（用于复刻）

    Args:
        video: parse_aweme_list_with_tags 返回的视频数据

    Returns:
        str: 清理后的文案内容
    """
    desc = video.get("desc", "")

    # 移除所有话题标签
    clean_desc = re.sub(r'#([^\s#]+)', '', desc).strip()

    return clean_desc


def format_video_for_replication(video: Dict[str, Any]) -> Dict[str, Any]:
    """
    格式化视频数据用于复刻分析

    Args:
        video: 视频数据

    Returns:
        Dict: 格式化的复刻信息
    """
    return {
        "original_desc": video.get("desc", ""),
        "clean_script": get_video_script(video),
        "hashtags": video.get("hashtags", []),
        "keywords": video.get("keywords", []),
        "music": video.get("music", ""),
        "duration": video.get("duration", 0),
        "engagement": {
            "like": video.get("statistics", {}).get("like", 0),
            "comment": video.get("statistics", {}).get("comment", 0),
            "share": video.get("statistics", {}).get("share", 0),
        },
        "viral_score": calculate_simple_viral_score(video)
    }


def calculate_simple_viral_score(video: Dict[str, Any]) -> float:
    """
    计算简单的爆款评分

    Args:
        video: 视频数据

    Returns:
        float: 爆款评分 (0-100)
    """
    stats = video.get("statistics", {})
    like = stats.get("like", 0)
    comment = stats.get("comment", 0)
    share = stats.get("share", 0)

    # 简单加权计算
    score = (like * 1 + comment * 5 + share * 10) / 100
    return min(score, 100)
