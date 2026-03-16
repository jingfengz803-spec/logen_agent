"""
抖音用户视频文案和标签抓取脚本
功能：从用户主页URL抓取100个以内的视频，提取文案和话题标签

使用方法：
    python fetch_user_videos.py "用户主页URL"

示例：
    python fetch_user_videos.py "https://www.douyin.com/user/MS4wLjABAAAA..."
"""

import os
import sys
import argparse
import json
from typing import List, Dict, Any
from datetime import datetime

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.url_parser import parse_douyin_url
from collector.client import fetch_videos
from collector.parser import (
    parse_aweme_list_with_tags,
    extract_hashtags,
    extract_keywords
)
from config import HEADERS


class DouyinUserFetcher:
    """抖音用户视频抓取器"""
    
    def __init__(self, max_videos: int = 100):
        """
        Args:
            max_videos: 最多抓取视频数
        """
        self.max_videos = max_videos
        self.collected = []
        
    def fetch_from_url(self, user_url: str) -> List[Dict[str, Any]]:
        """
        从用户主页URL抓取视频
        
        Args:
            user_url: 用户主页URL (如: https://www.douyin.com/user/MS4wLjABAAAA...)
            
        Returns:
            List[Dict]: 视频列表，包含文案和标签
        """
        print(f"\n{'='*60}")
        print(f"抖音视频抓取工具")
        print(f"{'='*60}")
        
        # 1. 解析URL
        print(f"\n[步骤 1/4] 解析URL...")
        parsed = parse_douyin_url(user_url)
        
        if parsed['type'] != 'user':
            print(f"❌ 错误: 不支持的URL类型: {parsed['type']}")
            print(f"   请提供用户主页链接，格式如: https://www.douyin.com/user/MS4wLjABAAAA...")
            return []
            
        user_id = parsed['id']
        print(f"✓ 用户ID: {user_id}")
        
        # 2. 抓取视频数据
        print(f"\n[步骤 2/4] 抓取视频数据 (最多 {self.max_videos} 个)...")
        videos = self._fetch_all_videos(user_id)
        print(f"✓ 成功抓取 {len(videos)} 个视频")
        
        if not videos:
            print(f"❌ 未获取到视频数据，请检查:")
            print(f"   1. Cookie是否有效 (config.py)")
            print(f"   2. 用户ID是否正确")
            print(f"   3. 网络连接是否正常")
            return []
        
        # 3. 解析文案和标签
        print(f"\n[步骤 3/4] 解析文案和标签...")
        self._parse_videos(videos)
        print(f"✓ 解析完成")
        
        # 4. 显示统计
        print(f"\n[步骤 4/4] 数据统计")
        self._print_stats()
        
        return self.collected
    
    def _fetch_all_videos(self, user_id: str) -> List[Dict]:
        """抓取用户所有视频"""
        all_videos = []
        max_cursor = 0
        page = 0
        count_per_page = 20  # 每页20个，抖音上限
        
        while len(all_videos) < self.max_videos:
            page += 1
            print(f"   正在抓取第 {page} 页...", end=" ")
            
            data = fetch_videos(user_id, max_cursor=max_cursor, count=count_per_page)
            
            if not data:
                print("❌ 无数据返回")
                break
            
            aweme_list = data.get("aweme_list", [])
            if not aweme_list:
                print("✓ 已到最后一页")
                break
                
            all_videos.extend(aweme_list)
            print(f"✓ 获得 {len(aweme_list)} 个视频，累计 {len(all_videos)} 个")
            
            # 检查是否还有更多
            has_more = data.get("has_more", False)
            if not has_more:
                break
                
            max_cursor = data.get("max_cursor", 0)
        
        return all_videos[:self.max_videos]
    
    def _parse_videos(self, raw_videos: List[Dict]):
        """解析视频数据"""
        for item in raw_videos:
            desc = item.get("desc", "")
            
            # 提取话题标签
            hashtags = extract_hashtags(desc)
            
            # 从 text_extra 中获取额外的标签
            text_extra = item.get("text_extra", [])
            hashtag_names = [t.get("hashtag_name", "") for t in text_extra if t.get("hashtag_name")]
            all_tags = list(set(hashtags + ["#" + h for h in hashtag_names]))
            
            # 统计数据
            statistics = item.get("statistics", {})
            
            video_info = {
                # 基础信息
                "aweme_id": item.get("aweme_id", ""),
                "desc": desc,
                "desc_clean": desc,  # 清理后的文案（可后续处理）
                "create_time": item.get("create_time", 0),
                "create_time_str": datetime.fromtimestamp(item.get("create_time", 0)).strftime("%Y-%m-%d %H:%M:%S") if item.get("create_time") else "",
                
                # 作者信息
                "author": item.get("author", {}).get("nickname", ""),
                "author_id": item.get("author", {}).get("unique_id", ""),
                
                # 统计数据
                "like_count": statistics.get("digg_count", 0),
                "comment_count": statistics.get("comment_count", 0),
                "share_count": statistics.get("share_count", 0),
                "play_count": statistics.get("play_count", 0),
                
                # 话题标签
                "hashtags": all_tags,
                "hashtag_count": len(all_tags),
                
                # 音乐
                "music": item.get("music", {}).get("title", ""),
                
                # 视频时长
                "duration": item.get("duration", 0) / 1000 if item.get("duration") else 0,
                
                # 视频链接
                "video_url": item.get("video", {}).get("play_addr", {}).get("url_list", [""])[0],
            }
            
            self.collected.append(video_info)
    
    def _print_stats(self):
        """打印统计信息"""
        if not self.collected:
            print("   暂无数据")
            return
        
        # 统计标签
        all_tags = []
        for v in self.collected:
            all_tags.extend(v["hashtags"])
        
        tag_counter = {}
        for tag in all_tags:
            tag_counter[tag] = tag_counter.get(tag, 0) + 1
        
        top_tags = sorted(tag_counter.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # 统计互动
        total_likes = sum(v["like_count"] for v in self.collected)
        total_comments = sum(v["comment_count"] for v in self.collected)
        total_shares = sum(v["share_count"] for v in self.collected)
        
        print(f"   📊 视频总数: {len(self.collected)}")
        print(f"   👍 总点赞数: {total_likes:,}")
        print(f"   💬 总评论数: {total_comments:,}")
        print(f"   🔄 总分享数: {total_shares:,}")
        
        print(f"\n   🏷️  最热门标签 TOP 10:")
        for tag, count in top_tags:
            print(f"      {tag} ({count}次)")
    
    def save_to_json(self, filepath: str = "user_videos_data.json"):
        """保存为JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.collected, f, ensure_ascii=False, indent=2)
        print(f"\n✓ 数据已保存到: {filepath}")
    
    def save_to_csv(self, filepath: str = "user_videos_data.csv"):
        """保存为CSV"""
        import pandas as pd
        
        # 展开嵌套字段
        df_data = []
        for v in self.collected:
            df_data.append({
                "视频ID": v["aweme_id"],
                "发布时间": v["create_time_str"],
                "文案": v["desc"],
                "作者": v["author"],
                "点赞数": v["like_count"],
                "评论数": v["comment_count"],
                "分享数": v["share_count"],
                "播放数": v["play_count"],
                "话题标签": ", ".join(v["hashtags"]),
                "标签数量": v["hashtag_count"],
                "音乐": v["music"],
                "时长(秒)": v["duration"],
                "视频链接": v["video_url"],
            })
        
        df = pd.DataFrame(df_data)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"✓ CSV已保存到: {filepath}")
    
    def print_top_videos(self, n: int = 10, by: str = "like"):
        """打印热门视频"""
        if not self.collected:
            return
        
        key = f"{by}_count"
        sorted_videos = sorted(self.collected, key=lambda x: x[key], reverse=True)[:n]
        
        print(f"\n{'='*60}")
        print(f"热门视频 TOP {n} (按{by}排序)")
        print(f"{'='*60}")
        
        for i, v in enumerate(sorted_videos, 1):
            print(f"\n【{i}】{v['author']} - {v['create_time_str']}")
            print(f"文案: {v['desc'][:100]}{'...' if len(v['desc']) > 100 else ''}")
            print(f"标签: {', '.join(v['hashtags'])}")
            print(f"数据: 👍{v['like_count']:,} 💬{v['comment_count']:,} 🔄{v['share_count']:,}")


def main():
    parser = argparse.ArgumentParser(description="抓取抖音用户视频文案和标签")
    parser.add_argument("url", help="用户主页URL")
    parser.add_argument("--max", "-n", type=int, default=100, help="最多抓取视频数 (默认100)")
    parser.add_argument("--output", "-o", choices=["json", "csv", "both", "none"], default="both",
                       help="输出格式 (默认both)")
    parser.add_argument("--top", "-t", type=int, default=10, help="显示热门视频数 (默认10)")
    
    args = parser.parse_args()
    
    # 执行抓取
    fetcher = DouyinUserFetcher(max_videos=args.max)
    fetcher.fetch_from_url(args.url)
    
    # 输出结果
    if args.output in ["json", "both"]:
        fetcher.save_to_json()
    
    if args.output in ["csv", "both"]:
        fetcher.save_to_csv()
    
    # 显示热门视频
    if fetcher.collected:
        fetcher.print_top_videos(n=args.top)
    
    print(f"\n{'='*60}")
    print("✓ 抓取完成!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
