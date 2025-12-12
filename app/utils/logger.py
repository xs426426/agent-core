"""
日志配置模块
"""
import logging
import sys
from pythonjsonlogger import jsonlogger
from app.config import settings


def setup_logger(name: str = "agent-core") -> logging.Logger:
    """
    配置并返回logger实例

    Args:
        name: logger名称

    Returns:
        配置好的logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # 格式化器
    if settings.log_level.upper() == "DEBUG":
        # 开发环境: 人类可读格式
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        # 生产环境: JSON格式
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# 全局logger实例
logger = setup_logger()
