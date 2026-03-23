"""
阿里云 OSS 上传工具 - 用于上传音频文件并获取公网 URL

安装依赖：
    pip install oss2

使用方法：
    python upload_audio_helper.py
"""

import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# 从项目根目录加载 .env 文件（override=True 确保覆盖已存在的环境变量）
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / '.env', override=True)


class OSSUploader:
    """阿里云 OSS 文件上传器"""

    def __init__(
        self,
        access_key_id: str = None,
        access_key_secret: str = None,
        bucket_name: str = None,
        endpoint: str = None
    ):
        """
        Args:
            access_key_id: AccessKey ID
            access_key_secret: AccessKey Secret
            bucket_name: 存储桶名称
            endpoint: 访问域名（如 oss-cn-hangzhou.aliyuncs.com）
        """
        self.access_key_id = access_key_id or os.getenv("OSS_ACCESS_KEY_ID")
        self.access_key_secret = access_key_secret or os.getenv("OSS_ACCESS_KEY_SECRET")
        self.bucket_name = bucket_name or os.getenv("OSS_BUCKET_NAME")
        self.endpoint = endpoint or os.getenv("OSS_ENDPOINT")

        if not all([self.access_key_id, self.access_key_secret, self.bucket_name, self.endpoint]):
            raise ValueError(
                "请在 .env 文件中配置 OSS 参数:\n"
                "  OSS_ACCESS_KEY_ID=your_access_key_id\n"
                "  OSS_ACCESS_KEY_SECRET=your_access_key_secret\n"
                "  OSS_BUCKET_NAME=your_bucket_name\n"
                "  OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com"
            )

    def upload_file(
        self,
        file_path: str,
        object_name: str = None,
        public: bool = True
    ) -> str:
        """
        上传文件到 OSS

        Args:
            file_path: 本地文件路径
            object_name: OSS 中的对象名（不指定则使用文件名）
            public: 是否设置为公共读

        Returns:
            str: 公网访问 URL
        """
        import oss2
        import uuid

        # 创建 Auth 实例
        auth = oss2.Auth(self.access_key_id, self.access_key_secret)

        # 创建 Bucket 实例
        bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)

        # 确定对象名
        if object_name is None:
            # 使用 UUID 避免文件名冲突
            ext = Path(file_path).suffix
            object_name = f"voices/{uuid.uuid4().hex}{ext}"

        # 检查文件大小
        file_size = Path(file_path).stat().st_size
        print(f"正在上传: {file_path}")
        print(f"  -> Bucket: {self.bucket_name}")
        print(f"  -> Object: {object_name}")
        print(f"  -> 文件大小: {file_size / 1024 / 1024:.1f} MB")

        # 上传文件（大文件会自动分块上传）
        result = bucket.put_object_from_file(object_name, file_path)

        if result.status == 200:
            print(f"✓ 上传成功")

            # 设置公共读权限
            if public:
                bucket.put_object_acl(object_name, oss2.OBJECT_ACL_PUBLIC_READ)
                print(f"✓ 已设置公共读权限")

            # 构建公网 URL
            # 如果 bucket 配置了自定义域名，替换 endpoint
            url = f"https://{self.bucket_name}.{self.endpoint.replace('aliyuncs.com', 'aliyuncs.com')}/{object_name}"

            # 使用标准路径格式
            if self.endpoint.startswith("http"):
                url = f"{self.endpoint}/{object_name}"
            else:
                url = f"https://{self.bucket_name}.{self.endpoint}/{object_name}"

            return url
        else:
            raise Exception(f"上传失败: {result.status}")


def print_oss_setup_guide():
    """打印 OSS 配置指南"""
    print("\n" + "=" * 70)
    print("阿里云 OSS 配置指南")
    print("=" * 70)

    print("\n【步骤 1】开通 OSS 服务")
    print("  访问: https://oss.console.aliyun.com/")
    print("  如果未开通，点击「立即开通」")

    print("\n【步骤 2】创建 Bucket")
    print("  1. 点击「创建 Bucket」")
    print("  2. 设置 Bucket 名称（如: my-voice-bucket）")
    print("  3. 选择地域（建议: 华东2-上海，离 CosyVoice 服务近）")
    print("  4. 读写权限选择: 「公共读」")
    print("  5. 其他按默认设置，点击确定")

    print("\n【步骤 3】获取 AccessKey")
    print("  1. 访问: https://ram.console.aliyun.com/manage/ak")
    print("  2. 创建 AccessKey（或使用已有的）")
    print("  3. 保存 AccessKey ID 和 Secret")

    print("\n【步骤 4】配置 .env 文件")
    print("  在 .env 文件中添加以下内容:")
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │ OSS_ACCESS_KEY_ID=your_access_key_id                   │")
    print("  │ OSS_ACCESS_KEY_SECRET=your_access_key_secret           │")
    print("  │ OSS_BUCKET_NAME=your_bucket_name                       │")
    print("  │ OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com              │")
    print("  └─────────────────────────────────────────────────────────┘")

    print("\n【步骤 5】安装依赖")
    print("  pip install oss2")

    print("\n" + "=" * 70)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="上传音频文件到阿里云 OSS")
    parser.add_argument("file", help="要上传的音频文件路径")
    parser.add_argument("--name", help="OSS 中的对象名（可选）")

    args = parser.parse_args()

    # 检查文件
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"✗ 文件不存在: {args.file}")
        print_oss_setup_guide()
        return

    # 尝试上传
    try:
        uploader = OSSUploader()
        url = uploader.upload_file(str(file_path), object_name=args.name)

        print("\n" + "=" * 70)
        print("✓ 上传完成!")
        print("=" * 70)
        print(f"\n公网 URL:")
        print(f"  {url}")
        print(f"\n现在可以使用此 URL 创建音色了:")
        print(f"  python create_voice_cli.py")
        print(f"  然后输入上述 URL")

        # 复制到剪贴板（Windows）
        if sys.platform == "win32":
            try:
                import subprocess
                subprocess.run(["clip"], input=url.strip().encode("utf-16"), check=True)
                print(f"\n✓ URL 已复制到剪贴板")
            except:
                pass

    except ValueError as e:
        print(f"✗ 配置错误: {e}")
        print_oss_setup_guide()

    except ImportError:
        print("✗ 未安装 oss2 库")
        print("  请运行: pip install oss2")

    except Exception as e:
        print(f"✗ 上传失败: {e}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # 没有参数，显示帮助
        print_oss_setup_guide()
        print("\n使用方法:")
        print("  python upload_audio_helper.py <音频文件路径>")
        print("\n示例:")
        print("  python upload_audio_helper.py my_voice.wav")
    else:
        main()
