import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging():
    """设置日志：仅输出到文件，支持轮转，防止重复添加 handler"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 避免重复添加 handler（若 root logger 已有 handler 则不再添加）
    if logger.handlers:
        return logger

    log_file = log_dir / "sci_research_agent.log"

    # 使用 RotatingFileHandler，限制单个文件 10MB，保留 5 个备份
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,   # 10 MB
        backupCount=5,
        encoding="utf-8"            # 显式指定 UTF-8 编码
    )
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    # 如果之前已通过 basicConfig 添加过 StreamHandler，将其移除
    # 或者更彻底地清除所有 handler 后只保留 file_handler
    # 这里选择只保留文件 handler
    for h in logger.handlers[:]:
        if h is not file_handler:
            logger.removeHandler(h)

    return logger