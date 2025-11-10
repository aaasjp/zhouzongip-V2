import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(log_file='logs/vector_db_server.log', log_level=logging.INFO):
    """
    配置日志系统，同时输出到文件和控制台
    
    Args:
        log_file: 日志文件路径
        log_level: 日志级别，默认为INFO
    """
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(filename)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除已有的处理器
    root_logger.handlers.clear()
    
    # 文件处理器 - 使用RotatingFileHandler支持日志轮转
    file_handler = RotatingFileHandler(
        log_file, 
        encoding='utf-8', 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
