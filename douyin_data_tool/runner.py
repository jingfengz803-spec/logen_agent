from datetime import datetime, timedelta
import config
from config import (
    USER_IDS, COUNT, MAX_PAGE, OUTPUT_FILE,
    # TOPIC_NAME, TOPIC_ID, SEARCH_TOPIC, SORT_TYPE, MAX_TOPIC_PAGES,  # use via config
    HOT_RANK_TYPE, MAX_HOT_PAGES,
    FILTER_MAX_DAYS, FILTER_MIN_LIKE, FILTER_MIN_COMMENT, FILTER_TARGET_COUNT
)  # MODE accessed via config.MODE
from collector.client import fetch_videos, fetch_topic_videos, fetch_hot_rank_videos
from collector.parser import parse_aweme_list
from analysis.hot_score import hot_score
from storage.save_csv import save_csv
import requests
from config import TOPIC_SEARCH_URL, HEADERS


def meets_conditions(video):
    """筛选条件"""
    create_time = video.get("create_time", 0)
    if not create_time:
        return False
    try:
        video_time = datetime.fromtimestamp(create_time)
    except Exception as e:
        print(f"时间转换错误: {e}")
        return False
    now = datetime.now()
    if video_time > now + timedelta(days=1):
        return False
    days_ago = (now - video_time).days
    if days_ago > FILTER_MAX_DAYS:
        return False
    # 修复：API返回的是 digg_count 而非 like
    statistics = video.get("statistics", {})
    like_count = statistics.get("digg_count", 0)
    comment_count = statistics.get("comment_count", 0)
    if like_count < FILTER_MIN_LIKE or comment_count < FILTER_MIN_COMMENT:
        return False
    return True


def search_topic_id(topic_name):
    """搜索话题ID"""
    params = {
        "device_platform": "webapp",
        "aid": "6383",
        "keyword": topic_name
    }
    try:
        resp = requests.get(TOPIC_SEARCH_URL, headers=HEADERS, params=params, timeout=10)
        data = resp.json()
        print("话题搜索返回:", data)
        if data and "challenge_list" in data and data["challenge_list"]:
            return data["challenge_list"][0]["cid"]
    except Exception as e:
        print(f"搜索话题失败: {e}")
    return None


def run_user_mode():
    """用户模式抓取"""
    all_data = []
    for user in USER_IDS:
        cursor = 0
        for page in range(MAX_PAGE):
            data = fetch_videos(user, cursor, COUNT)
            if not data:
                break
            videos = parse_aweme_list(data)
            for v in videos:
                if meets_conditions(v):
                    v["score"] = hot_score(v)
                    all_data.append(v)
                    if len(all_data) >= FILTER_TARGET_COUNT:
                        break
            if len(all_data) >= FILTER_TARGET_COUNT:
                break
            cursor = data.get("max_cursor", 0)
    return all_data


def run_topic_mode():
    """话题模式抓取"""
    all_data = []
    challenge_id = config.TOPIC_ID if config.TOPIC_ID else search_topic_id(config.TOPIC_NAME)
    print(f"使用话题名称 '{config.TOPIC_NAME}' 解析到ID: {challenge_id}")
    if not challenge_id:
        print("未找到话题ID")
        return []
    cursor = 0
    for page in range(config.MAX_TOPIC_PAGES):
        data = fetch_topic_videos(challenge_id, cursor, COUNT, config.SORT_TYPE)
        if not data:
            break
        videos = parse_aweme_list(data)
        for v in videos:
            if meets_conditions(v):
                v["score"] = hot_score(v)
                all_data.append(v)
                if len(all_data) >= FILTER_TARGET_COUNT:
                    break
        if len(all_data) >= FILTER_TARGET_COUNT:
            break
        cursor = data.get("cursor", 0)
    return all_data


def run_hot_mode():
    """热榜模式抓取"""
    all_data = []
    cursor = 0
    for page in range(MAX_HOT_PAGES):
        data = fetch_hot_rank_videos(cursor, COUNT)
        if not data:
            break
        videos = parse_aweme_list(data)
        for v in videos:
            if meets_conditions(v):
                v["score"] = hot_score(v)
                all_data.append(v)
                if len(all_data) >= FILTER_TARGET_COUNT:
                    break
        if len(all_data) >= FILTER_TARGET_COUNT:
            break
        cursor = data.get("cursor", 0)
    return all_data


def run():
    if config.MODE == "user":
        all_data = run_user_mode()
    elif config.MODE == "topic":
        all_data = run_topic_mode()
    elif config.MODE == "hot":
        all_data = run_hot_mode()
    else:
        print("无效模式")
        return

    all_data.sort(key=lambda x: x["score"], reverse=True)
    save_csv(all_data, OUTPUT_FILE)
    print(f"共保存 {len(all_data)} 条数据到 {OUTPUT_FILE}")


import argparse

# ... 其他代码 ...

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', default=config.MODE, choices=['user', 'topic', 'hot'])
    parser.add_argument('--target', default='')
    args = parser.parse_args()
    
    # 临时覆盖配置
    config.MODE = args.mode
    if args.target:
        if args.mode == 'user':
            config.USER_IDS = [args.target]
        elif args.mode == 'topic':
            config.TOPIC_NAME = args.target
    
    run()