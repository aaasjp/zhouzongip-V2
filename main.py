# -*- coding: utf-8 -*-
"""
AI助手主服务
合并向量数据库服务和高管IP助手服务到一个服务
"""
import logging
import json
from flask import Flask
from flask_cors import CORS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 加载配置文件
with open('./config/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)


def main():
    """主函数：创建Flask应用并注册Blueprint"""
    logger.info("=" * 60)
    logger.info("AI助手主服务启动")
    logger.info("=" * 60)
    
    # 创建主Flask应用
    app = Flask(__name__)
    CORS(app)
    
    # 配置 JSON 编码器，确保中文字符不被转义
    app.json.ensure_ascii = False
    
    # 初始化素材库（如果需要）
    try:
        logger.info("初始化素材库...")
        from milvus.miluvs_helper import create_collection
        is_succ, msg = create_collection()
        if is_succ:
            logger.info(f"素材库初始化成功: {msg}")
        else:
            logger.warning(f"素材库初始化失败: {msg}")
    except Exception as e:
        logger.warning(f"素材库初始化异常（可能已存在）: {e}")
    
    # 初始化MySQL表（如果需要）
    try:
        logger.info("初始化MySQL表...")
        from mysql_utils.mysql_helper import MySQLHelper
        mysql_helper = MySQLHelper()
        is_succ, msg = mysql_helper.create_tables()
        if is_succ:
            logger.info(f"MySQL表初始化成功: {msg}")
        else:
            logger.warning(f"MySQL表初始化失败: {msg}")
        mysql_helper.close()
    except Exception as e:
        logger.warning(f"MySQL表初始化异常: {e}")
    
    # 注册素材库服务 Blueprint
    try:
        from vector_db_server import vector_db_bp
        app.register_blueprint(vector_db_bp)
        logger.info("素材库服务路由已注册")
    except Exception as e:
        logger.error(f"注册素材库服务路由失败: {e}")
        import traceback
        logger.exception(traceback.format_exc())
        return
    
    # 注册对话服务 Blueprint
    try:
        from chat_server import chat_bp
        app.register_blueprint(chat_bp)
        logger.info("对话服务路由已注册")
    except Exception as e:
        logger.error(f"注册对话服务路由失败: {e}")
        import traceback
        logger.exception(traceback.format_exc())
        return
    
    # 启动服务配置
    server_config = config.get('api_server', {})
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 8003)
    
    # 启动服务
    
    logger.info("=" * 60)
    logger.info(f"所有服务已启动，监听地址: {host}:{port}")
    logger.info("素材库服务接口: /vector_db_service/*")
    logger.info("对话服务接口: /chat_service/*")
    logger.info("=" * 60)
    
    try:
        app.run(host=host, port=port, debug=False)
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭服务...")
    except Exception as e:
        logger.error(f"服务运行异常: {e}")
        import traceback
        logger.exception(traceback.format_exc())


if __name__ == '__main__':
    main()
