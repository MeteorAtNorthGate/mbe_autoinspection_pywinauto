# helpers.py

import logging
import logging.handlers
from pathlib import Path

def setup_logger(log_level: int = logging.INFO) -> None:
    """
    为控制台程序设置一个简单的日志记录器
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "debug_console.log"

    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    # 文件处理器
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=2, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    logging.info("="*20 + " Logger Initialized " + "="*20)

class LoggerMixin:
    """
    为其他类提供日志功能的混入类
    """
    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger(self.__class__.__name__)