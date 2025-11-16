"""
日志配置
"""
import logging
import sys
from pathlib import Path

def setup_logger(verbose: bool = False, log_file: str = "vol_quant.log"):
    """
    设置日志
    
    Args:
        verbose: 是否启用详细日志
        log_file: 日志文件路径
    """
    
    # 日志级别
    level = logging.DEBUG if verbose else logging.INFO
    
    # 日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 配置根日志
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清空已有的处理器
    root_logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(log_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(log_format, datefmt=date_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    return root_logger
