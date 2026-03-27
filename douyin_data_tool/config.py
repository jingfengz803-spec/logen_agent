# config.py
# 抖音数据抓取工具配置文件
# 请根据你的需求修改以下配置项

import os

# ------------------- 基础请求配置 -------------------
# 通用请求头，必须包含有效的Cookie（从浏览器Network复制完整的Cookie字符串）
HEADERS = {
    "Referer": "https://www.douyin.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    # 将下面字符串替换为你从浏览器复制的完整Cookie（重要：Cookie有时效性，过期需更新）
    "Cookie": "douyin.com; enter_pc_once=1; UIFID_TEMP=ed3eadd74fe8fd7fe8cc39b2f8425a87324d41d3f6a0cfdc014da4c26c6540512ca8f2959b3beb30d7971d3e5debe831f2b151722262538c09ca723ad910017f9acf637925ad569b54c5b8382936213a; hevc_supported=true; dy_swidth=1536; dy_sheight=864; fpk1=U2FsdGVkX18zI8T5aV/n5REUovRZaORNoxyQeviAWJKbyi3gaRmy5IMq/+OR9KGtqj7Lr3NX/plkC2J1SaRaow==; fpk2=91e1a2a41c0741f7f47615ab9de2fb8a; s_v_web_id=verify_mmlfdjay_7wNSdtMq_FHgu_4gzW_ATlS_Ioya567WTgln; my_rd=2; passport_csrf_token=a13b038df1d7dd734784be8f9e12daba; passport_csrf_token_default=a13b038df1d7dd734784be8f9e12daba; passport_mfa_token=CjfaGt%2FapjITCGL6lggTogimHDSaEkgDxVYy0rmc2byWZPFU534Y2rnepIleTIe7XEB3v0Dfa0mcGkoKPAAAAAAAAAAAAABQKlwg15NUlLv8jNQBBmgQ7vqYWDFvkvOG07HJ%2FRpycfwgRB%2F%2B5wU4MyCJN5xWzL1mcBDa4osOGPax0WwgAiIBA%2FAHrVM%3D; d_ticket=d30256b2c97dc2278f0b1348b8120dd5866e4; passport_assist_user=CkDLisOG1tc-PgCfWDYnRod1uFQJ2YKIqgOF0yPwvYn-SV4ktzIzwcV1Z_NMHXbmH0ksaf94wKiqEdskMVexO8_KGkoKPAAAAAAAAAAAAABQK-3Ar6dArJXmf4YsAIIYpvziFQZyqJ7QtdM00Y26YHFFivTgZc4O3kCvzbHAA5D7WRCv5IsOGImv1lQgASIBAxD1Tfc%3D; n_mh=cSYv1u7hE2PoGPPrCO3XXyTUTWWuSMg9Zjx73Ln3C50; sid_guard=1e1034a1defd4fee762a4b349df99c37%7C1773196537%7C5184000%7CSun%2C+10-May-2026+02%3A35%3A37+GMT; uid_tt=168bf01093f7d53f264dd4e647ed5577; uid_tt_ss=168bf01093f7d53f264dd4e647ed5577; sid_tt=1e1034a1defd4fee762a4b349df99c37; sessionid=1e1034a1defd4fee762a4b349df99c37; sessionid_ss=1e1034a1defd4fee762a4b349df99c37; session_tlb_tag=sttt%7C19%7CHhA0od79T-52Kks0nfmcN_________-6vP2tm7Ee1LbTBk_7ttRaIDXJ11qurHRbGrj3nJsm2dc%3D; is_staff_user=false; sid_ucp_v1=1.0.0-KGE5NWQ3ZGI1NGE0YWY3MjBkMjU1YTQ4ZTljYWNlM2I2OTljNDU1YjAKHwjr4tDgiM3JARD5qcPNBhjvMSAMMIGDo7QGOAdA9AcaAmhsIiAxZTEwMzRhMWRlZmQ0ZmVlNzYyYTRiMzQ5ZGY5OWMzNw; ssid_ucp_v1=1.0.0-KGE5NWQ3ZGI1NGE0YWY3MjBkMjU1YTQ4ZTljYWNlM2I2OTljNDU1YjAKHwjr4tDgiM3JARD5qcPNBhjvMSAMMIGDo7QGOAdA9AcaAmhsIiAxZTEwMzRhMWRlZmQ0ZmVlNzYyYTRiMzQ5ZGY5OWMzNw; login_time=1773196537857; UIFID=ed3eadd74fe8fd7fe8cc39b2f8425a87324d41d3f6a0cfdc014da4c26c6540512ca8f2959b3beb30d7971d3e5debe831a7ac0ee24dc87afe1b33f648fe0f1451a7b6adf523c87cdea12dcd6878c392ee957ee22736875d2cc67b1d3170d2670ae575cc3177800822c6aa283edc49b92c9399ef42b4a5e31b3db5e348a9aa708aaa14d1f3570964e9edfe446a77ee00ddfab7dac9e557007ca02d4f948cd46535; bd_ticket_guard_client_web_domain=2; SelfTabRedDotControl=%5B%5D; is_dash_user=1; SEARCH_RESULT_LIST_TYPE=%22single%22; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Atrue%2C%22volume%22%3A0.5%7D; __security_mc_1_s_sdk_crypt_sdk=d44704a0-41a4-ae95; playRecommendGuideTagCount=1; totalRecommendGuideTagCount=16; douyin.com; device_web_cpu_core=16; device_web_memory_size=8; architecture=amd64; strategyABtestKey=%221774489825.6%22; ttwid=1%7C5CJmdCPoK_-jhkD3A0s2bE7HSMn-iXdGOfQle3ouaHU%7C1774489828%7Ce44aaad30eb830e00cb7ad7143b5862faf1f239e00510b8766cb2e3d95bfd958; FOLLOW_LIVE_POINT_INFO=%22MS4wLjABAAAAWqE2lDLLDljNPaLRyAPzL8ujk_k_bhQ6YcI7uWjrb-M%2F1774540800000%2F0%2F1774498225755%2F0%22; __ac_nonce=069c4b1b500e0b57afdaa; __ac_signature=_02B4Z6wo00f01VvD6CwAAIDDCMiR8a.mRTVb4-yAAD84ec; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1536%2C%5C%22screen_height%5C%22%3A864%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A16%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A200%7D%22; FOLLOW_NUMBER_YELLOW_POINT_INFO=%22MS4wLjABAAAAWqE2lDLLDljNPaLRyAPzL8ujk_k_bhQ6YcI7uWjrb-M%2F1774540800000%2F0%2F0%2F1774499429240%22; home_can_add_dy_2_desktop=%221%22; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCQWF4Ti9iVTJxd2kwV21CZEdHK2NQRjVDdDZiVUcwUlA5UXc1OHI1ck5hc0xLOVExY3RPdlg3ZndYRnRUYldiTEpSOUphWHdLblh4MTEzODI5ZERnV1k9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; publish_badge_show_info=%220%2C0%2C0%2C1774498234025%22; odin_tt=476439fecb3c79873504eb866b1d96ea2561e7ed7a416b5fd12981864bf8aa606abed10e4cbc0a5a2a9c9ad7b7c1df514b9e2747da671a54a011b5556a44ef82; biz_trace_id=f0c9f36d; sdk_source_info=7e276470716a68645a606960273f276364697660272927676c715a6d6069756077273f276364697660272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e58272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e582729277672715a646971273f2763646976602729277f6b5a666475273f2763646976602729276d6a6e5a6b6a716c273f2763646976602729276c6b6f5a7f6367273f27636469766027292771273f27333c343036373d3c3131323234272927676c715a75776a716a666a69273f2763646976602778; bit_env=o5W1XZ2E4H3D0COT--bRemmzaXY4bWsmqQ3kw1DPKjK3VPK5gIh0CXtH4P0lCIxix6EznZNpWO0nIMnDjnQANptzydUSkmLdNVBsAhRvgcIum9T03d-LJ4k7fYjAoNXDINKGMiX5xc28SSo2AZDRA6wyVfcpTg_JYcTCdEPcDSGnCh1hF1158Mx9J9F4CGmWrhZvtbegva8qg4TAna_YM8U14uf7opdNQXhsvklC1rISs_jz_qdaZkPM4TqtSMQudQDEMxIu6pWvmL7VVTlJM_Six6FiG2r-RcRJJooZajqfJ1SBosqeKtw7iDhR4UNykQ4XHqr5gzzrgnw7sY9TFzAkmtEDSby33pYOaRfPdeYkmBpe0eb_dDv_OPgKZ71POYZqRdgydxg_1dSkpw31XpeXoxfKKaDZg4X8Hq6iBeZHjHv--oOPb_ACzYmDYOX4LyelML-Rb_bAxMZHt0SLG1ARBdlYmM6IumJxsMKd1m433wMTc-MfCdfdX0r76rML; gulu_source_res=eyJwX2luIjoiNTBhMWExZmI2NDg1MjU5ZjFiNjJiNGMyZTJhMzU1MjFiMTUyYWI4ZTYwYzk3YmFjNWQ5YzgwMTBmZDg1ZTg1ZSJ9; passport_auth_mix_state=9ep4a5ffrnne3dwbbnt8gy3rmtz0ztdk; bd_ticket_guard_client_data_v2=eyJyZWVfcHVibGljX2tleSI6IkJBYXhOL2JVMnF3aTBXbUJkR0crY1BGNUN0NmJVRzBSUDlRdzU4cjVyTmFzTEs5UTFjdE92WDdmd1hGdFRiV2JMSlI5SmFYd0tuWHgxMTM4MjlkRGdXWT0iLCJyZXFfY29udGVudCI6InNlY190cyIsInJlcV9zaWduIjoiVE5HL1RMQUd1bDV3alUxQk16WUljMzFVdnNuL3E4b0phWkJWVTNMZ3pDWT0iLCJzZWNfdHMiOiIjTkJYOHJtS0dDTnd4YkZSa1hKb3Qvenk4bCtkdktCcnkyWXR4Wit5Zm5Fd3VkNDJqRUZtRU5lRUZVT3Z0In0%3D; download_guide=%221%2F20260326%2F0%22; IsDouyinActive=false",
    "Origin": "https://www.douyin.com",
}

# ------------------- 抓取模式设置 -------------------
# MODE: "user" 表示抓取指定用户的视频列表， "topic" 表示抓取指定话题下的视频
MODE = "user"   # 可选 "user" 或 "topic"

# ------------------- 用户模式配置 -------------------
# 用户作品的API接口（通常不需要修改）
USER_BASE_URL = "https://www.douyin.com/aweme/v1/web/aweme/post/"

# 通用API接口（兼容旧代码）
BASE_URL = USER_BASE_URL

# 目标用户的sec_user_id列表（可从用户主页URL获取，例如 https://www.douyin.com/user/XXXXXXXX 最后的XXXXXXXX即为sec_user_id）
USER_IDS = [
    "MS4wLjABAAAAY34PkUuYwnOseWTb7bsc1p_tuOxsu5kCDGr8xjjy1KbNSd7CBpVHzuhfEK2ix2OP",  # 示例用户，请替换为实际ID
    # 可添加更多用户ID，用逗号分隔
]

# 每次请求获取的视频数量（抖音通常限制最大20）
COUNT = 10

# 最大抓取页数（每页COUNT条）
MAX_PAGE = 3

# ------------------- 话题模式配置 -------------------
# 话题搜索API（用于根据关键词获取话题ID）
TOPIC_SEARCH_URL = "https://www.douyin.com/aweme/v1/web/challenge/search/"

# 话题视频列表API
TOPIC_AWEME_URL = "https://www.douyin.com/aweme/v1/web/challenge/aweme/"

# 话题名称（当MODE="topic"时使用，替换为你要抓取的话题，例如 "挑战名"）
TOPIC_NAME = "路边摊美味"

# 如果已知话题ID，可以直接指定，避免搜索（如果为None则自动搜索）
TOPIC_ID = None

# 是否自动搜索话题（当TOPIC_ID为None时生效）
SEARCH_TOPIC = True

# 话题视频排序方式（可能依赖接口，0=综合，1=最新，2=最热）
SORT_TYPE = 2   # 2 表示热门排序

# 话题最大抓取页数
MAX_TOPIC_PAGES = 5

# ------------------- 热榜模式配置 -------------------
# 抖音热榜API（热门视频列表）
HOT_RANK_URL = "https://www.douyin.com/aweme/v1/web/hot/search/"

# 热榜类型（例如 "hot_video" 或其他）
HOT_RANK_TYPE = "hot_video"

# 热榜最大抓取页数
MAX_HOT_PAGES = 5

# ------------------- 数据过滤条件 -------------------
# 以下条件用于筛选视频，同时满足才会保存

# 最大允许的天数（发布至今的天数，超过则过滤）
FILTER_MAX_DAYS = 10000   # 30天内的视频

# 最小点赞数
FILTER_MIN_LIKE = 50

# 最小评论数
FILTER_MIN_COMMENT = 1

# 目标采集数量（达到此数量后停止抓取）
FILTER_TARGET_COUNT = 100

# ------------------- 输出文件设置 -------------------
# 保存结果的文件名（CSV格式）
OUTPUT_FILE = "douyin_data.csv"

# 如果希望不同模式使用不同输出文件，可以分别定义，例如：
# OUTPUT_FILE_USER = "user_data.csv"
# OUTPUT_FILE_TOPIC = "topic_data.csv"
# 然后在主程序中根据MODE选择