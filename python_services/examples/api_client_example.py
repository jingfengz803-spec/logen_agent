"""
API服务调用示例
展示如何使用Python调用短视频创作自动化API
"""

import requests
import json
import time
from typing import Dict, Any, Optional


class APIClient:
    """API客户端"""

    def __init__(self, base_url: str = "http://localhost:8088", api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "X-Request-ID": "test_request_001"
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def _request(self, method: str, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """发送请求"""
        url = f"{self.base_url}{path}"
        response = requests.request(method, url, json=data, headers=self.headers)
        return response.json()

    # ==================== 健康检查 ====================

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return self._request("GET", "/health")

    # ==================== 抖音抓取 ====================

    def fetch_user_videos(self, url: str, max_count: int = 100) -> str:
        """
        抓取用户视频

        Returns:
            task_id: 任务ID
        """
        data = {
            "url": url,
            "max_count": max_count,
            "enable_filter": True,
            "min_likes": 50,
            "min_comments": 0
        }
        result = self._request("POST", "/api/v1/douyin/fetch/user", data)
        return result.get("task_id")

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """查询任务状态"""
        return self._request("GET", f"/api/v1/douyin/task/{task_id}")

    def wait_task(self, task_id: str, timeout: int = 300) -> Dict[str, Any]:
        """
        等待任务完成

        Args:
            task_id: 任务ID
            timeout: 超时时间(秒)

        Returns:
            任务结果
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.get_task_status(task_id)
            status = result.get("status")

            print(f"任务状态: {status}, 进度: {result.get('progress', 0)}%")

            if status in ["success", "failed", "cancelled"]:
                return result

            time.sleep(3)

        raise TimeoutError(f"任务超时: {task_id}")

    # ==================== AI分析 ====================

    def analyze_viral(self, video_data: list) -> str:
        """
        火爆原因分析

        Args:
            video_data: 视频数据列表

        Returns:
            task_id: 任务ID
        """
        data = {"video_data": video_data}
        result = self._request("POST", "/api/v1/ai/analyze/viral", data)
        return result.get("task_id")

    def analyze_style(self, video_data: list) -> str:
        """风格特征分析"""
        data = {
            "video_data": video_data,
            "analysis_dimensions": [
                "文案风格", "视频类型", "拍摄特征",
                "高频词汇", "标签策略", "音乐风格"
            ]
        }
        result = self._request("POST", "/api/v1/ai/analyze/style", data)
        return result.get("task_id")

    def generate_script(self, reference_data: dict, topic: str) -> str:
        """
        生成脚本

        Args:
            reference_data: 参考风格数据
            topic: 新主题

        Returns:
            task_id: 任务ID
        """
        data = {
            "reference_data": reference_data,
            "topic": topic,
            "target_duration": 30,
            "tone": "专业"
        }
        result = self._request("POST", "/api/v1/ai/generate/script", data)
        return result.get("task_id")

    # ==================== TTS语音 ====================

    def create_voice(self, audio_url: str, prefix: str = "myvoice") -> str:
        """
        创建音色

        Args:
            audio_url: 音色音频URL
            prefix: 音色前缀

        Returns:
            task_id: 任务ID
        """
        data = {
            "audio_url": audio_url,
            "prefix": prefix,
            "model": "cosyvoice-v3.5-flash",
            "wait_ready": True
        }
        result = self._request("POST", "/api/v1/tts/voice/create", data)
        return result.get("task_id")

    def list_voices(self) -> list:
        """获取音色列表"""
        result = self._request("GET", "/api/v1/tts/voice/list")
        return result.get("voices", [])

    def text_to_speech(self, text: str, voice_id: str) -> str:
        """
        文字转语音

        Args:
            text: 要合成的文本
            voice_id: 音色ID

        Returns:
            task_id: 任务ID
        """
        data = {
            "text": text,
            "voice_id": voice_id,
            "output_format": "mp3"
        }
        result = self._request("POST", "/api/v1/tts/speech", data)
        return result.get("task_id")

    # ==================== 视频生成 ====================

    def generate_video(self, video_url: str, audio_url: str) -> str:
        """
        生成视频

        Args:
            video_url: 参考视频URL
            audio_url: 合成音频URL

        Returns:
            task_id: 任务ID
        """
        data = {
            "video_url": video_url,
            "audio_url": audio_url,
            "video_extension": True
        }
        result = self._request("POST", "/api/v1/video/generate", data)
        return result.get("task_id")

    # ==================== 完整工作流 ====================

    def run_workflow(
        self,
        douyin_url: str,
        topic: str,
        voice_id: Optional[str] = None,
        workflow_type: str = "without_video"
    ) -> str:
        """
        运行完整工作流

        Args:
            douyin_url: 抖音URL
            topic: 新主题
            voice_id: 音色ID
            workflow_type: 工作流类型

        Returns:
            task_id: 任务ID
        """
        data = {
            "douyin_url": douyin_url,
            "topic": topic,
            "voice_id": voice_id,
            "workflow_type": workflow_type,
            "max_videos": 100
        }
        result = self._request("POST", "/api/v1/workflow/run", data)
        return result.get("task_id")


# ==================== 使用示例 ====================

def example_basic_usage():
    """基础使用示例"""
    # 初始化客户端
    client = APIClient(base_url="http://localhost:8088")

    # 1. 健康检查
    print("=== 健康检查 ===")
    health = client.health_check()
    print(f"服务状态: {health}")

    # 2. 抓取用户视频
    print("\n=== 抓取用户视频 ===")
    douyin_url = "https://www.douyin.com/user/MS4wLjABAAAA..."
    task_id = client.fetch_user_videos(douyin_url, max_count=50)
    print(f"任务ID: {task_id}")

    # 3. 等待任务完成
    print("\n=== 等待任务完成 ===")
    result = client.wait_task(task_id, timeout=120)
    print(f"任务结果: {result}")


def example_full_workflow():
    """完整工作流示例"""
    client = APIClient(base_url="http://localhost:8088")

    print("=== 运行完整工作流 ===")

    # 运行工作流（不含视频生成）
    task_id = client.run_workflow(
        douyin_url="https://www.douyin.com/user/MS4wLjABAAAA...",
        topic="如何应对职场PUA",
        voice_id="cosyvoice-v3.5-flash-xxx",
        workflow_type="without_video"
    )

    print(f"工作流任务ID: {task_id}")

    # 轮询任务状态
    while True:
        result = client.get_task_status(task_id)
        status = result.get("status")
        progress = result.get("progress", 0)

        print(f"进度: {progress}% - 状态: {status}")

        if status == "success":
            print("工作流完成!")
            print(f"结果: {result.get('result')}")
            break
        elif status == "failed":
            print(f"工作流失败: {result.get('error')}")
            break

        time.sleep(5)


def example_step_by_step():
    """分步骤使用示例"""
    client = APIClient(base_url="http://localhost:8088")

    # 步骤1: 抓取视频
    print("步骤1: 抓取视频...")
    task_id = client.fetch_user_videos("https://www.douyin.com/user/MS4wLjABAAAA...")
    result = client.wait_task(task_id)
    videos = result.get("result", {}).get("videos", [])

    # 步骤2: 风格分析
    print("\n步骤2: 风格分析...")
    task_id = client.analyze_style(videos[:20])
    result = client.wait_task(task_id)
    style_analysis = result.get("result", {}).get("style_analysis", {})

    # 步骤3: 生成脚本
    print("\n步骤3: 生成脚本...")
    task_id = client.generate_script(style_analysis, "如何应对职场PUA")
    result = client.wait_task(task_id)
    script = result.get("result", {}).get("script", {})

    print(f"\n生成的脚本标题: {script.get('title')}")
    print(f"生成的文案: {script.get('publish_text')}")


if __name__ == "__main__":
    # 运行示例
    example_basic_usage()
    # example_full_workflow()
    # example_step_by_step()
