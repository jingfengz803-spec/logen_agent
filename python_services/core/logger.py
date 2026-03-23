"""
日志模块
统一API服务的日志配置
"""

import sys
import logging
from pathlib import Path
from typing import Optional
from loguru import logger as loguru_logger

from .config import settings


class APILogger:
    """API日志器"""

    def __init__(self):
        self._setup_loguru()
        self._intercept_standard_logging()

    def _setup_loguru(self):
        """配置Loguru"""

        # 确保日志目录存在
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)

        # 移除默认handler
        loguru_logger.remove()

        # 控制台输出
        loguru_logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO" if not settings.DEBUG else "DEBUG",
            colorize=True
        )

        # 文件输出 - 所有日志
        loguru_logger.add(
            log_dir / "api_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="7 days",
            compression="zip",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG"
        )

        # 文件输出 - 错误日志
        loguru_logger.add(
            log_dir / "api_error_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="30 days",
            compression="zip",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="ERROR"
        )

    def _intercept_standard_logging(self):
        """拦截标准logging输出"""

        class InterceptHandler(logging.Handler):
            def emit(self, record):
                try:
                    level = loguru_logger.level(record.levelname).name
                except ValueError:
                    level = record.levelno

                frame, depth = logging.currentframe(), 2
                while frame.f_code.co_filename == logging.__file__:
                    frame = frame.f_back
                    depth += 1

                loguru_logger.opt(depth=depth, exception=record.exc_info).log(
                    level, record.getMessage()
                )

        # 设置所有logging使用我们的handler
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


# 初始化日志器
api_logger = APILogger()
logger = loguru_logger


def get_logger(name: Optional[str] = None):
    """获取logger实例"""
    if name:
        return logger.bind(name=name)
    return logger
