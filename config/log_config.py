# -*- coding: utf-8 -*-
"""
日志配置模块
支持为不同服务配置独立的日志记录器
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def setup_logging(service_name='vector_db', log_file='logs/vector_db_server.log', 
                  log_level=logging.INFO, enable_console=True):
    """
    配置日志系统，为指定服务创建独立的日志记录器
    
    Args:
        service_name: 服务名称，用于创建独立的日志记录器
        log_file: 日志文件路径
        log_level: 日志级别，默认为INFO
        enable_console: 是否启用控制台输出，默认为True
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # 创建服务专用的日志记录器
    logger = logging.getLogger(service_name)
    logger.setLevel(log_level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 规范化日志格式：时间戳 | 级别 | 模块名 | 函数名:行号 | 消息
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件处理器 - 使用RotatingFileHandler支持日志轮转
    file_handler = RotatingFileHandler(
        log_file, 
        encoding='utf-8', 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 控制台处理器（可选）
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 防止日志向上传播到根日志记录器（避免重复输出）
    logger.propagate = False
    
    return logger


def setup_vector_db_logging():
    """配置素材库服务的日志"""
    return setup_logging(
        service_name='vector_db',
        log_file='logs/vector_db_server.log',
        log_level=logging.INFO
    )


def setup_chat_service_logging():
    """配置对话服务的日志"""
    return setup_logging(
        service_name='chat_service',
        log_file='logs/chat_service.log',
        log_level=logging.INFO
    )
