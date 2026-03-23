"""
日志工具模块
提供统一的日志输出功能
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


class Logger:
    """简单日志工具"""

    def __init__(self, name: str = "douyin", log_dir: str = None, level: int = logging.INFO):
        """
        初始化日志器

        Args:
            name: 日志器名称
            log_dir: 日志文件目录（不指定则不输出到文件）
            level: 日志级别
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # 避免重复添加 handler
        if self.logger.handlers:
            return

        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # 文件输出（可选）
        if log_dir:
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            log_file = log_path / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

    def debug(self, msg: str):
        """输出调试信息"""
        self.logger.debug(msg)

    def info(self, msg: str):
        """输出一般信息"""
        self.logger.info(msg)

    def warning(self, msg: str):
        """输出警告信息"""
        self.logger.warning(msg)

    def error(self, msg: str):
        """输出错误信息"""
        self.logger.error(msg)

    def critical(self, msg: str):
        """输出严重错误信息"""
        self.logger.critical(msg)


# 默认日志实例
_default_logger = None


def get_logger(name: str = "douyin", log_dir: str = None) -> Logger:
    """
    获取日志器实例

    Args:
        name: 日志器名称
        log_dir: 日志文件目录

    Returns:
        Logger: 日志器实例
    """
    return Logger(name=name, log_dir=log_dir)


def info(msg: str):
    """快捷输出 info 日志"""
    global _default_logger
    if _default_logger is None:
        _default_logger = get_logger()
    _default_logger.info(msg)


def error(msg: str):
    """快捷输出 error 日志"""
    global _default_logger
    if _default_logger is None:
        _default_logger = get_logger()
    _default_logger.error(msg)


def warning(msg: str):
    """快捷输出 warning 日志"""
    global _default_logger
    if _default_logger is None:
        _default_logger = get_logger()
    _default_logger.warning(msg)


if __name__ == "__main__":
    # 测试日志功能
    logger = get_logger()
    logger.info("这是一条测试日志")
    logger.warning("这是一条警告")
    logger.error("这是一条错误")
