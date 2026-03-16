import requests
import json
from config import BASE_URL, HEADERS

headers = HEADERS


def fetch_videos(sec_user_id, max_cursor=0, count=10):
    params = {
        "device_platform": "webapp",
        "aid": "6383",
        "sec_user_id": sec_user_id,
        "count": count,
        "max_cursor": max_cursor
    }
    try:
        resp = requests.get(BASE_URL, headers=headers, params=params, timeout=10)
        print("状态码:", resp.status_code)
        if resp.status_code != 200:
            print("请求失败，状态码:", resp.status_code)
            return None
        data = resp.json()
        # 安全打印第一条视频用于调试
        if data and "aweme_list" in data and data["aweme_list"]:
            print("返回内容样例:", json.dumps(data["aweme_list"][0], indent=2, ensure_ascii=False)[:500])
        else:
            print("返回内容中 aweme_list 为空或不存在，完整数据预览:", str(data)[:200])
        return data
    except Exception as e:
        print("请求异常:", e)
        return None


def fetch_topic_videos(challenge_id, cursor=0, count=10, sort_type=2):
    """根据话题ID抓取视频"""
    from config import TOPIC_AWEME_URL, HEADERS
    params = {
        "device_platform": "webapp",
        "aid": "6383",
        "ch_id": challenge_id,
        "count": count,
        "cursor": cursor,
        "sort_type": sort_type  # 0=综合, 1=最新, 2=最热
    }
    try:
        resp = requests.get(TOPIC_AWEME_URL, headers=HEADERS, params=params, timeout=10)
        print("话题视频请求状态码:", resp.status_code)
        if resp.status_code != 200:
            print("请求失败，状态码:", resp.status_code)
            return None
        data = resp.json()
        if data and "aweme_list" in data and data["aweme_list"]:
            print("返回内容样例:", json.dumps(data["aweme_list"][0], indent=2, ensure_ascii=False)[:500])
        else:
            print("返回内容中 aweme_list 为空或不存在")
        return data
    except Exception as e:
        print("请求异常:", e)
        return None


def fetch_hot_rank_videos(cursor=0, count=10):
    """抓取热榜视频"""
    from config import HOT_RANK_URL, HEADERS
    params = {
        "device_platform": "webapp",
        "aid": "6383",
        "count": count,
        "cursor": cursor
    }
    try:
        resp = requests.get(HOT_RANK_URL, headers=HEADERS, params=params, timeout=10)
        print("热榜视频请求状态码:", resp.status_code)
        if resp.status_code != 200:
            print("请求失败，状态码:", resp.status_code)
            return None
        data = resp.json()
        if data and "data" in data and data["data"]:
            print("返回内容样例:", json.dumps(data["data"][0], indent=2, ensure_ascii=False)[:500])
        else:
            print("返回内容中 data 为空或不存在")
        return data
    except Exception as e:
        print("请求异常:", e)
        return None
