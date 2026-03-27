"""
阿里云 VideoRetalk 视频生成模块
文档: https://help.aliyun.com/zh/model-studio/
"""

import os
import time
import json
import requests
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Literal, Dict, Any, Callable, Tuple
from urllib.parse import urlparse

# 导入 OSS 上传器（复用现有模块，已包含 load_dotenv）
from upload_audio_helper import OSSUploader

# 导入统一配置
from config import VideoConfig, Paths


# ================================================================
# 视频预处理工具
# ================================================================

class VideoPreprocessor:
    """视频预处理 - 使用 ffmpeg 调整分辨率"""

    # API 要求的分辨率范围
    MIN_RESOLUTION = 640
    MAX_RESOLUTION = 2048

    # 默认目标分辨率
    DEFAULT_WIDTH = 1280   # 720p
    DEFAULT_HEIGHT = 720

    @staticmethod
    def check_ffmpeg() -> bool:
        """检查 ffmpeg 是否已安装"""
        return shutil.which("ffmpeg") is not None

    @staticmethod
    def get_video_resolution(video_path: str) -> Optional[Tuple[int, int]]:
        """
        获取视频分辨率

        Returns:
            (width, height) 或 None
        """
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "json",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                streams = data.get("streams", [])
                if streams:
                    width = streams[0].get("width")
                    height = streams[0].get("height")
                    if width and height:
                        return (width, height)
        except Exception as e:
            print(f"获取视频分辨率失败: {e}")
        return None

    @staticmethod
    def needs_resize(video_path: str) -> bool:
        """
        检查视频是否需要调整分辨率

        Returns:
            True 如果需要调整
        """
        resolution = VideoPreprocessor.get_video_resolution(video_path)
        if not resolution:
            return False

        width, height = resolution
        # 检查宽或高是否超出范围
        if width < VideoPreprocessor.MIN_RESOLUTION or width > VideoPreprocessor.MAX_RESOLUTION:
            return True
        if height < VideoPreprocessor.MIN_RESOLUTION or height > VideoPreprocessor.MAX_RESOLUTION:
            return True
        return False

    @staticmethod
    def calculate_target_size(width: int, height: int) -> Tuple[int, int]:
        """
        计算目标分辨率（保持宽高比）

        规则：
        - 如果太小，放大到默认尺寸
        - 如果太大，缩小到最大尺寸内
        - 保持原始宽高比
        """
        min_size = VideoPreprocessor.MIN_RESOLUTION
        max_size = VideoPreprocessor.MAX_RESOLUTION

        # 如果两边都在范围内，不需要调整
        if min_size <= width <= max_size and min_size <= height <= max_size:
            return (width, height)

        # 计算宽高比
        aspect_ratio = width / height

        # 如果太小，按比例放大
        if width < min_size or height < min_size:
            # 以较小的边为准
            if width < height:
                new_width = min_size
                new_height = int(min_size / aspect_ratio)
            else:
                new_height = min_size
                new_width = int(min_size * aspect_ratio)
            # 确保都是偶数（ffmpeg 要求）
            new_width = new_width if new_width % 2 == 0 else new_width + 1
            new_height = new_height if new_height % 2 == 0 else new_height + 1
            return (new_width, new_height)

        # 如果太大，按比例缩小
        if width > max_size or height > max_size:
            # 以较大的边为准
            if width > height:
                new_width = max_size
                new_height = int(max_size / aspect_ratio)
            else:
                new_height = max_size
                new_width = int(max_size * aspect_ratio)
            # 确保都是偶数
            new_width = new_width if new_width % 2 == 0 else new_width - 1
            new_height = new_height if new_height % 2 == 0 else new_height - 1
            return (new_width, new_height)

        return (width, height)

    @staticmethod
    def resize_video(
        video_path: str,
        output_path: Optional[str] = None,
        target_width: Optional[int] = None,
        target_height: Optional[int] = None
    ) -> str:
        """
        调整视频分辨率

        Args:
            video_path: 原视频路径
            output_path: 输出路径（如不指定则自动生成）
            target_width: 目标宽度（如不指定则自动计算）
            target_height: 目标高度（如不指定则自动计算）

        Returns:
            输出文件路径
        """
        if not VideoPreprocessor.check_ffmpeg():
            raise RuntimeError(
                "ffmpeg 未安装。请先安装 ffmpeg:\n"
                "  - Windows: 下载 https://ffmpeg.org/download.html\n"
                "  - Mac: brew install ffmpeg\n"
                "  - Linux: sudo apt install ffmpeg"
            )

        # 获取当前分辨率
        current = VideoPreprocessor.get_video_resolution(video_path)
        if not current:
            raise RuntimeError(f"无法读取视频: {video_path}")

        current_width, current_height = current

        # 计算目标分辨率
        if target_width is None or target_height is None:
            target_width, target_height = VideoPreprocessor.calculate_target_size(
                current_width, current_height
            )

        # 如果不需要调整，返回原文件
        if target_width == current_width and target_height == current_height:
            print(f"  分辨率已符合要求: {current_width}x{current_height}")
            return video_path

        # 生成输出路径
        if output_path is None:
            video_path_obj = Path(video_path)
            output_path = str(
                video_path_obj.parent / f"{video_path_obj.stem}_rescaled{video_path_obj.suffix}"
            )

        print(f"\n--- 调整视频分辨率 ---")
        print(f"  原始: {current_width}x{current_height}")
        print(f"  目标: {target_width}x{target_height}")

        # 使用 ffmpeg 缩放视频
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"scale={target_width}:{target_height}",
            "-c:a", "copy",  # 音频直接复制
            "-y",  # 覆盖输出文件
            output_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode != 0:
                print(f"ffmpeg stderr: {result.stderr}")
                raise RuntimeError(f"ffmpeg 处理失败")

            print(f"  ✓ 已保存: {output_path}")
            return output_path

        except subprocess.TimeoutExpired:
            raise RuntimeError("ffmpeg 处理超时")
        except FileNotFoundError:
            raise RuntimeError("ffmpeg 未找到，请确保已安装并添加到 PATH")


class VideoRetalkClient:
    """阿里 VideoRetalk 视频生成客户端"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: 阿里 DashScope API Key，如不指定则从配置读取
        """
        config = VideoConfig.get_video_config("videoretalk")

        self.api_key = api_key or config["api_key"]()
        self.api_url = config["async_url"]
        self.model = config["model"]

    def submit_video_generation_task(
        self,
        video_url: str,
        audio_url: str,
        ref_image_url: str = "",
        video_extension: bool = False
    ) -> str:
        """
        提交视频生成任务（异步）

        Args:
            video_url: 参考视频的公网 URL（必需）
            audio_url: 待合成音频的公网 URL（必需）
            ref_image_url: 参考图片的公网 URL（可选）
            video_extension: 是否扩展视频

        Returns:
            str: 任务 ID (request_id)

        注意：video_url 和 audio_url 必须是公网可访问的 URL
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"
        }

        payload = {
            "model": self.model,
            "input": {
                "video_url": video_url,
                "audio_url": audio_url,
                "ref_image_url": ref_image_url
            },
            "parameters": {
                "video_extension": video_extension
            }
        }

        print(f"--- 提交视频生成任务 ---")
        print(f"参考视频: {video_url}")
        print(f"音频: {audio_url}")
        print(f"参考图片: {ref_image_url or '(无)'}")
        print(f"扩展视频: {video_extension}")

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code not in [200, 201]:
                error_msg = response.text
                try:
                    error_json = response.json()
                    error_msg = error_json.get("message", error_msg)
                except:
                    pass
                raise Exception(f"任务提交失败: {error_msg}")

            result = response.json()

            # 保存完整响应用于调试
            print(f"提交响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

            # 提取 task_id（用于查询状态）
            output = result.get("output", {})
            task_id = output.get("task_id")

            if not task_id:
                raise Exception(f"未获取到任务ID: {result}")

            print(f"✓ 任务已提交，Task ID: {task_id}")
            return task_id

        except Exception as e:
            raise Exception(f"视频生成任务提交失败: {str(e)}")

    def query_task_status(self, request_id: str) -> Dict[str, Any]:
        """
        查询任务状态

        Args:
            request_id: 任务 ID (实际上是 task_id)

        Returns:
            Dict: 任务状态信息
        """
        # 使用通用任务查询 API
        url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{request_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=30
            )

            if response.status_code == 404:
                return {
                    "output": {
                        "task_id": request_id,
                        "task_status": "NOT_FOUND",
                        "message": "任务不存在或已过期（通常保留24小时）"
                    }
                }

            if response.status_code != 200:
                print(f"查询响应: {response.text}")

            response.raise_for_status()
            return response.json()

        except Exception as e:
            raise Exception(f"查询任务状态失败: {str(e)}")

    def wait_for_completion(
        self,
        request_id: str,
        max_attempts: int = 360,  # 360 * 5秒 = 30分钟
        poll_interval: int = 5,
        callback=None
    ) -> Dict[str, Any]:
        """
        等待任务完成

        Args:
            request_id: 任务 ID
            max_attempts: 最大轮询次数
            poll_interval: 轮询间隔（秒）
            callback: 状态回调函数

        Returns:
            Dict: 完成后的任务结果
        """
        print(f"\n--- 等待视频生成完成 ---")

        for attempt in range(max_attempts):
            try:
                result = self.query_task_status(request_id)

                # 获取状态
                output = result.get("output", {})
                status = output.get("task_status") or result.get("output", {}).get("status")
                message = output.get("message", "")

                if callback:
                    callback(attempt + 1, status, result)

                elapsed = (attempt + 1) * poll_interval

                # 不同平台的状态字段可能不同
                if status in ["SUCCEEDED", "completed", "success", "finished"]:
                    print(f"✓ 视频生成完成! 耗时: {elapsed}秒")
                    return result

                elif status in ["FAILED", "failed", "error"]:
                    error_msg = output.get("message", "未知错误")
                    raise RuntimeError(f"视频生成失败: {error_msg}")

                elif status in ["PENDING", "RUNNING", "processing", "pending", "UNKNOWN"]:
                    # UNKNOWN 表示任务还在排队
                    msg_part = f" - {message}" if message else ""
                    print(f"进度: {attempt + 1}/{max_attempts} ({elapsed}秒) - 状态: {status}{msg_part}")
                else:
                    print(f"进度: {attempt + 1}/{max_attempts} ({elapsed}秒) - 状态: {status}")

                # 超过 10 分钟仍在 RUNNING，打印完整响应用于排查
                if elapsed >= 600 and attempt % 12 == 0:
                    print(f"⚠️ 已运行 {elapsed}秒，dashscope 响应: {json.dumps(result, ensure_ascii=False)[:500]}")

                time.sleep(poll_interval)

            except RuntimeError as e:
                # 任务明确失败（FAILED 状态），不再重试
                print(f"任务失败，停止轮询: {e}")
                raise
            except Exception as e:
                # 网络等临时错误，允许继续轮询
                print(f"轮询出错: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(poll_interval)
                else:
                    raise

        raise RuntimeError("视频生成超时")

    def generate_video(
        self,
        video_url: str,
        audio_url: str,
        ref_image_url: str = "",
        video_extension: bool = False,
        output_path: Optional[str] = None,
        wait: bool = True,
        max_attempts: int = 360  # 增加到360次 = 30分钟
    ) -> Dict[str, Any]:
        """
        一键生成视频（提交 + 等待 + 下载）

        Args:
            video_url: 参考视频的公网 URL
            audio_url: 待合成音频的公网 URL
            ref_image_url: 参考图片的公网 URL（可选）
            video_extension: 是否扩展视频
            output_path: 保存路径（可选）
            wait: 是否等待完成
            max_attempts: 最大等待次数

        Returns:
            Dict: 包含视频路径和任务信息
        """
        # 提交任务
        request_id = self.submit_video_generation_task(
            video_url=video_url,
            audio_url=audio_url,
            ref_image_url=ref_image_url,
            video_extension=video_extension
        )

        if not wait:
            return {"request_id": request_id, "status": "pending"}

        # 等待完成
        result = self.wait_for_completion(
            request_id=request_id,
            max_attempts=max_attempts
        )

        # 获取视频 URL
        output = result.get("output", {})
        video_result = output.get("results", [{}])[0] if output.get("results") else {}
        video_url_result = video_result.get("url") or output.get("video_url")

        if not video_url_result:
            print(f"⚠ 任务完成但未找到视频URL")
            print(f"返回结果: {result}")
            return {"request_id": request_id, "result": result}

        print(f"✓ 视频URL: {video_url_result}")

        # 下载视频
        if output_path:
            downloaded_path = self._download_video(video_url_result, output_path)
            return {
                "request_id": request_id,
                "video_url": video_url_result,
                "video_path": downloaded_path,
                "result": result
            }

        return {
            "request_id": request_id,
            "video_url": video_url_result,
            "result": result
        }

    def _download_video(self, url: str, output_path: str) -> str:
        """
        下载视频到本地

        Args:
            url: 视频 URL
            output_path: 输出路径

        Returns:
            str: 实际保存的文件路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"\n--- 下载视频 ---")
        print(f"从: {url}")
        print(f"到: {output_path}")

        try:
            response = requests.get(url, stream=True, timeout=120)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = downloaded / total_size * 100
                            print(f"\r下载进度: {progress:.1f}%", end="")

            print(f"\n✓ 视频已保存: {output_path}")
            return str(output_path)

        except Exception as e:
            raise Exception(f"视频下载失败: {str(e)}")

    def generate_video_from_local_files(
        self,
        video_path: str,
        audio_path: str,
        ref_image_path: Optional[str] = None,
        video_extension: bool = False,
        output_path: Optional[str] = None,
        upload_callback=None
    ) -> Dict[str, Any]:
        """
        从本地文件生成视频

        注意：需要先将文件上传到公网可访问的位置（如 OSS）
        这里提供接口，实际上传需要用户实现

        Args:
            video_path: 本地参考视频路径
            audio_path: 本地音频路径
            ref_image_path: 本地参考图片路径（可选）
            video_extension: 是否扩展视频
            output_path: 输出路径
            upload_callback: 上传回调函数，接收 (file_path, file_type) 返回 URL

        Returns:
            Dict: 生成结果
        """
        # 如果没有提供上传回调，返回提示
        if upload_callback is None:
            return {
                "error": "需要提供 upload_callback 将本地文件上传到公网可访问的位置",
                "note": "可以使用阿里云 OSS 或其他对象存储服务"
            }

        # 上传文件
        video_url = upload_callback(video_path, "video")
        audio_url = upload_callback(audio_path, "audio")
        ref_image_url = upload_callback(ref_image_path, "image") if ref_image_path else ""

        # 生成视频
        return self.generate_video(
            video_url=video_url,
            audio_url=audio_url,
            ref_image_url=ref_image_url,
            video_extension=video_extension,
            output_path=output_path
        )


class VideoWorkflow:
    """视频生成工作流 - 从本地音频/视频文件到最终视频"""

    def __init__(self, default_video_url: str = "", oss_uploader: OSSUploader = None):
        """
        Args:
            default_video_url: 默认的参考视频 URL
            oss_uploader: OSS 上传器实例（如果不提供则自动创建）
        """
        self.client = VideoRetalkClient()
        self.default_video_url = default_video_url
        self.oss_uploader = oss_uploader

    def _get_oss_uploader(self) -> Optional[OSSUploader]:
        """获取 OSS 上传器"""
        if self.oss_uploader:
            return self.oss_uploader

        try:
            # 直接尝试创建，如果配置缺失会抛出 ValueError
            uploader = OSSUploader()
            return uploader
        except ValueError:
            # OSS 配置不完整
            return None
        except Exception:
            return None

    def _upload_file_if_needed(
        self,
        local_path: str,
        existing_url: str = "",
        file_type: str = "file",
        auto_resize_video: bool = True
    ) -> str:
        """
        如果提供了本地路径但没有 URL，则上传到 OSS

        Args:
            local_path: 本地文件路径
            existing_url: 已有的 URL（如果有）
            file_type: 文件类型（用于日志）
            auto_resize_video: 是否自动调整视频分辨率（仅当 file_type="参考视频" 时）

        Returns:
            str: 公网 URL
        """
        if existing_url:
            return existing_url

        if not local_path or not Path(local_path).exists():
            return ""

        # 如果是视频，检查并自动调整分辨率
        video_to_upload = local_path
        if file_type == "参考视频" and auto_resize_video:
            if VideoPreprocessor.needs_resize(local_path):
                print(f"\n--- 检测到视频分辨率不符合要求 ---")
                try:
                    video_to_upload = VideoPreprocessor.resize_video(local_path)
                except RuntimeError as e:
                    print(f"⚠️ 视频分辨率调整失败: {e}")
                    print(f"将尝试使用原视频上传...")
            else:
                # 显示当前分辨率
                res = VideoPreprocessor.get_video_resolution(local_path)
                if res:
                    print(f"  视频分辨率: {res[0]}x{res[1]} ✓")

        # 尝试上传到 OSS
        uploader = self._get_oss_uploader()
        if uploader:
            try:
                print(f"\n--- 上传{file_type}到 OSS ---")
                url = uploader.upload_file(video_to_upload)
                print(f"✓ {file_type} URL: {url}")
                return url
            except ImportError as e:
                print(f"⚠️ OSS 上传失败: {e}")
                print(f"请先安装依赖: pip install oss2")
                print(f"或者使用 URL 模式直接提供公网 URL")
            except ValueError as e:
                print(f"⚠️ OSS 配置错误: {e}")
            except Exception as e:
                print(f"⚠️ OSS 上传失败: {e}")

        return ""

    def generate_from_local_files(
        self,
        video_path: str = "",
        audio_path: str = "",
        video_url: str = "",
        audio_url: str = "",
        ref_image_path: str = "",
        ref_image_url: str = "",
        video_extension: bool = True,
        output_dir: str = "data/output/video",
        output_name: str = None,
        auto_upload: bool = True
    ) -> Dict[str, Any]:
        """
        从本地文件生成视频（自动上传到 OSS）

        Args:
            video_path: 本地参考视频路径
            audio_path: 本地音频路径
            video_url: 参考视频 URL（优先于本地文件）
            audio_url: 音频 URL（优先于本地文件）
            ref_image_path: 本地参考图片路径（可选）
            ref_image_url: 参考图片 URL（可选）
            video_extension: 是否扩展视频以匹配音频长度（默认 True）
            output_dir: 输出目录
            output_name: 输出文件名（不含扩展名）
            auto_upload: 是否自动上传本地文件到 OSS

        Returns:
            Dict: 包含视频路径和任务信息

        注意:
            - video_extension=True 时，视频会循环扩展以匹配音频长度
            - 例如: 12s 视频 + 72s 音频 → 生成 72s 视频
        """
        print("=" * 60)
        print("VideoRetalk 视频生成工作流")
        print("=" * 60)

        # 准备输出目录
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if output_name:
            output_path = output_dir / f"{output_name}.mp4"
        else:
            import time
            output_path = output_dir / f"video_{time.strftime('%Y%m%d_%H%M%S')}.mp4"

        # ========================================
        # 处理参考视频
        # ========================================
        print(f"\n【步骤1/4】准备参考视频...")

        if not video_url and video_path and Path(video_path).exists():
            print(f"本地参考视频: {video_path}")
            if auto_upload:
                video_url = self._upload_file_if_needed(video_path, "", "参考视频")
            else:
                print("⚠️ 需要提供 video_url 或启用 auto_upload")
                return {"error": "需要提供参考视频 URL"}

        if not video_url:
            return {
                "error": "需要提供参考视频（video_url 或 video_path）",
                "hint": "请确保 video_path 文件存在，或直接提供 video_url"
            }

        print(f"✓ 参考视频 URL: {video_url}")

        # ========================================
        # 处理音频
        # ========================================
        print(f"\n【步骤2/4】准备音频...")

        if not audio_url and audio_path and Path(audio_path).exists():
            print(f"本地音频: {audio_path}")
            if auto_upload:
                audio_url = self._upload_file_if_needed(audio_path, "", "音频")
            else:
                print("⚠️ 需要提供 audio_url 或启用 auto_upload")
                return {"error": "需要提供音频 URL"}

        if not audio_url:
            return {
                "error": "需要提供音频（audio_url 或 audio_path）",
                "hint": "请确保 audio_path 文件存在，或直接提供 audio_url"
            }

        print(f"✓ 音频 URL: {audio_url}")

        # ========================================
        # 处理参考图片（可选）
        # ========================================
        if ref_image_path or ref_image_url:
            print(f"\n【步骤3/4】准备参考图片...")

            if not ref_image_url and ref_image_path and Path(ref_image_path).exists():
                if auto_upload:
                    ref_image_url = self._upload_file_if_needed(ref_image_path, "", "参考图片")

            if ref_image_url:
                print(f"✓ 参考图片 URL: {ref_image_url}")

        # ========================================
        # 生成视频
        # ========================================
        print(f"\n【步骤4/4】生成视频...")
        print("这可能需要几分钟，请耐心等待...")

        try:
            result = self.client.generate_video(
                video_url=video_url,
                audio_url=audio_url,
                ref_image_url=ref_image_url,
                video_extension=video_extension,
                output_path=str(output_path)
            )

            # 保存元数据
            metadata = {
                "input": {
                    "video_path": str(video_path) if video_path else None,
                    "video_url": video_url,
                    "audio_path": str(audio_path) if audio_path else None,
                    "audio_url": audio_url,
                    "ref_image_path": str(ref_image_path) if ref_image_path else None,
                    "ref_image_url": ref_image_url,
                },
                "output": {
                    "video_path": str(output_path),
                    "request_id": result.get("request_id"),
                    "generated_video_url": result.get("video_url"),
                }
            }

            metadata_file = output_dir / f"{output_path.stem}_metadata.json"
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            result["metadata_file"] = str(metadata_file)

            print(f"\n✓ 视频生成完成!")
            print(f"  - 视频: {output_path}")
            print(f"  - 元数据: {metadata_file}")

            return result

        except Exception as e:
            return {
                "error": f"视频生成失败: {str(e)}",
                "video_url": video_url,
                "audio_url": audio_url
            }


# 便捷函数
def generate_video(
    video_url: str,
    audio_url: str,
    output_path: str = "output.mp4",
    ref_image_url: str = ""
) -> Dict[str, Any]:
    """
    快速生成视频

    示例:
        result = generate_video(
            video_url="https://example.com/ref_video.mp4",
            audio_url="https://example.com/speech.mp3",
            output_path="data/output/video.mp4"
        )
    """
    client = VideoRetalkClient()
    return client.generate_video(
        video_url=video_url,
        audio_url=audio_url,
        ref_image_url=ref_image_url,
        output_path=output_path
    )


if __name__ == "__main__":
    print("=" * 60)
    print("VideoRetalk 视频生成测试")
    print("=" * 60)

    # 检查 API Key
    import os
    from dotenv import load_dotenv
    load_dotenv('.env')

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("✗ 请设置 DASHSCOPE_API_KEY 环境变量")
        exit(1)

    print(f"✓ API Key 已设置")

    # 示例：查询任务状态
    print("\n" + "=" * 60)
    print("查询任务状态示例")
    print("=" * 60)

    # 如果有任务ID，可以查询状态
    request_id = input("请输入任务ID (留空跳过): ").strip()

    if request_id:
        client = VideoRetalkClient()
        result = client.query_task_status(request_id)
        print(f"\n任务状态:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n跳过查询")

    print("\n提示: 使用 generate_video() 函数生成新视频")
    print("  - video_url: 参考视频的公网 URL")
    print("  - audio_url: 音频的公网 URL")
    print("  - ref_image_url: 参考图片的公网 URL (可选)")
