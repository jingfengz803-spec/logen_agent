"""
API服务启动脚本
"""
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 加载根目录的 .env 文件（override=True 确保覆盖已存在的环境变量）
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from python_services.core.config import settings
from python_services.core.logger import logger


def main():
    parser = argparse.ArgumentParser(description="短视频创作自动化API服务")
    parser.add_argument(
        "--host",
        default=settings.HOST,
        help=f"监听地址 (默认: {settings.HOST})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.PORT,
        help=f"监听端口 (默认: {settings.PORT})"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.DEBUG,
        help="启用自动重载"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="工作进程数"
    )

    args = parser.parse_args()

    from python_services.main import run_server

    logger.info("🚀 启动API服务...")
    run_server(
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
