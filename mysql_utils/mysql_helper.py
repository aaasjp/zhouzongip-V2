# -*- coding: utf-8 -*-
"""
MySQL数据库操作模块
用于对话管理功能
"""
import json
import os
import logging
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from typing import Optional, List, Dict, Any

# 使用chat_service日志记录器，因为MySQL操作属于对话服务
logger = logging.getLogger('chat_service')

# 加载配置文件
def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

CONFIG = load_config()
MYSQL_CONFIG = CONFIG.get('mysql', {})


class MySQLHelper:
    """MySQL数据库操作类"""
    
    def __init__(self):
        """初始化MySQL连接配置"""
        self.host = MYSQL_CONFIG.get('host', 'localhost')
        self.port = MYSQL_CONFIG.get('port', 3306)
        self.user = MYSQL_CONFIG.get('user', 'root')
        self.password = MYSQL_CONFIG.get('password', '')
        self.db_name = MYSQL_CONFIG.get('db_name', 'ai_helper')
        self.connection = None
        
    def _log_sql(self, sql: str, params: tuple = None):
        """记录SQL执行日志"""
        # 格式化SQL语句，将参数值替换到占位符中（用于日志显示）
        formatted_sql = sql
        if params:
            try:
                # 将参数值安全地格式化到SQL中（仅用于日志，不用于实际执行）
                formatted_params = []
                for param in params:
                    if param is None:
                        formatted_params.append('NULL')
                    elif isinstance(param, str):
                        # 转义单引号并截断过长的字符串
                        escaped = param.replace("'", "''")
                        if len(escaped) > 200:
                            escaped = escaped[:200] + '...'
                        formatted_params.append(f"'{escaped}'")
                    elif isinstance(param, (int, float)):
                        formatted_params.append(str(param))
                    else:
                        formatted_params.append(f"'{str(param)}'")
                
                # 简单替换（注意：这不是安全的SQL执行方式，仅用于日志）
                formatted_sql = sql
                for param in formatted_params:
                    formatted_sql = formatted_sql.replace('%s', param, 1)
            except Exception as e:
                formatted_sql = f"{sql} [参数格式化失败: {e}]"
        
        logger.info(f"[MySQL执行] 数据库={self.host}:{self.port}/{self.db_name} | SQL={formatted_sql}")
        if params:
            logger.debug(f"[MySQL参数] params={params}")
        
    def _get_connection(self):
        """获取数据库连接"""
        try:
            if self.connection is None or not self.connection.is_connected():
                logger.info(f"[MySQL连接] 连接到数据库: {self.host}:{self.port}/{self.db_name}, user={self.user}")
                self.connection = mysql.connector.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.db_name,
                    charset='utf8mb4',
                    collation='utf8mb4_unicode_ci'
                )
                logger.info(f"[MySQL连接] 数据库连接成功: {self.host}:{self.port}/{self.db_name}")
            return self.connection
        except Error as e:
            logger.error(f"[MySQL连接] 连接MySQL数据库失败: host={self.host}:{self.port}, db={self.db_name}, error={e}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.connection = None
    
    def create_tables(self):
        """创建对话管理相关的表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 创建对话会话表
            create_session_table = """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(200) NOT NULL COMMENT '用户ID',
                session_id VARCHAR(200) NOT NULL UNIQUE COMMENT '会话ID',
                title VARCHAR(500) DEFAULT NULL COMMENT '会话标题',
                tenant_code VARCHAR(200) DEFAULT NULL COMMENT '租户代码',
                org_code VARCHAR(200) DEFAULT NULL COMMENT '组织代码',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                is_deleted TINYINT(1) DEFAULT 0 COMMENT '是否删除：0-未删除，1-已删除',
                INDEX idx_user_id (user_id),
                INDEX idx_session_id (session_id),
                INDEX idx_tenant_org (tenant_code, org_code),
                INDEX idx_created_at (created_at),
                INDEX idx_is_deleted (is_deleted)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话会话表';
            """
            
            # 创建对话消息表
            create_message_table = """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(200) NOT NULL COMMENT '会话ID',
                user_id VARCHAR(200) NOT NULL COMMENT '用户ID',
                role ENUM('user', 'assistant') NOT NULL COMMENT '角色：user-用户，assistant-助手',
                content TEXT NOT NULL COMMENT '消息内容',
                sources JSON DEFAULT NULL COMMENT '文档来源（JSON格式，包含文档名称、URL等）',
                suggested_questions JSON DEFAULT NULL COMMENT '延申问题推荐（JSON数组）',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                INDEX idx_session_id (session_id),
                INDEX idx_user_id (user_id),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话消息表';
            """
            
            self._log_sql(create_session_table.strip())
            cursor.execute(create_session_table)
            self._log_sql(create_message_table.strip())
            cursor.execute(create_message_table)
            conn.commit()
            cursor.close()
            
            logger.info(f"[MySQL执行] 对话管理表创建成功: {self.host}:{self.port}/{self.db_name}")
            return True, "对话管理表创建成功"
        except Error as e:
            logger.error(f"创建表失败: {e}")
            return False, f"创建表失败: {e}"
    
    def create_session(self, user_id: str, session_id: str, title: Optional[str] = None, 
                      tenant_code: Optional[str] = None, org_code: Optional[str] = None) -> tuple:
        """创建新对话会话"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            insert_sql = """
            INSERT INTO chat_sessions (user_id, session_id, title, tenant_code, org_code)
            VALUES (%s, %s, %s, %s, %s)
            """
            params = (user_id, session_id, title, tenant_code, org_code)
            self._log_sql(insert_sql.strip(), params)
            cursor.execute(insert_sql, params)
            conn.commit()
            cursor.close()
            
            logger.info(f"创建会话成功: session_id={session_id}, user_id={user_id}")
            return True, "创建会话成功"
        except Error as e:
            logger.error(f"创建会话失败: {e}")
            return False, f"创建会话失败: {e}"
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            
            select_sql = """
            SELECT * FROM chat_sessions 
            WHERE session_id = %s AND is_deleted = 0
            """
            params = (session_id,)
            self._log_sql(select_sql.strip(), params)
            cursor.execute(select_sql, params)
            result = cursor.fetchone()
            cursor.close()
            
            return result
        except Error as e:
            logger.error(f"获取会话失败: {e}")
            return None
    
    def list_sessions(self, user_id: str, tenant_code: Optional[str] = None, 
                     org_code: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户的会话列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            
            where_clauses = ["user_id = %s", "is_deleted = 0"]
            params = [user_id]
            
            if tenant_code:
                where_clauses.append("tenant_code = %s")
                params.append(tenant_code)
            if org_code:
                where_clauses.append("org_code = %s")
                params.append(org_code)
            
            select_sql = f"""
            SELECT * FROM chat_sessions 
            WHERE {' AND '.join(where_clauses)}
            ORDER BY updated_at DESC
            LIMIT %s
            """
            params.append(limit)
            
            self._log_sql(select_sql.strip(), tuple(params))
            cursor.execute(select_sql, params)
            results = cursor.fetchall()
            cursor.close()
            
            return results
        except Error as e:
            logger.error(f"获取会话列表失败: {e}")
            return []
    
    def update_session_title(self, session_id: str, title: str) -> tuple:
        """更新会话标题"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            update_sql = """
            UPDATE chat_sessions 
            SET title = %s 
            WHERE session_id = %s AND is_deleted = 0
            """
            params = (title, session_id)
            self._log_sql(update_sql.strip(), params)
            cursor.execute(update_sql, params)
            conn.commit()
            cursor.close()
            
            logger.info(f"更新会话标题成功: session_id={session_id}")
            return True, "更新会话标题成功"
        except Error as e:
            logger.error(f"更新会话标题失败: {e}")
            return False, f"更新会话标题失败: {e}"
    
    def delete_session(self, session_id: str) -> tuple:
        """删除会话（软删除）"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            update_sql = """
            UPDATE chat_sessions 
            SET is_deleted = 1 
            WHERE session_id = %s
            """
            params = (session_id,)
            self._log_sql(update_sql.strip(), params)
            cursor.execute(update_sql, params)
            conn.commit()
            cursor.close()
            
            logger.info(f"删除会话成功: session_id={session_id}")
            return True, "删除会话成功"
        except Error as e:
            logger.error(f"删除会话失败: {e}")
            return False, f"删除会话失败: {e}"
    
    def restore_session(self, session_id: str) -> tuple:
        """恢复会话"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            update_sql = """
            UPDATE chat_sessions 
            SET is_deleted = 0 
            WHERE session_id = %s
            """
            params = (session_id,)
            self._log_sql(update_sql.strip(), params)
            cursor.execute(update_sql, params)
            conn.commit()
            cursor.close()
            
            logger.info(f"恢复会话成功: session_id={session_id}")
            return True, "恢复会话成功"
        except Error as e:
            logger.error(f"恢复会话失败: {e}")
            return False, f"恢复会话失败: {e}"
    
    def add_message(self, session_id: str, user_id: str, role: str, content: str,
                   sources: Optional[List[Dict]] = None, 
                   suggested_questions: Optional[List[str]] = None) -> tuple:
        """添加消息"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 将sources和suggested_questions转换为JSON字符串
            sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
            suggested_questions_json = json.dumps(suggested_questions, ensure_ascii=False) if suggested_questions else None
            
            insert_sql = """
            INSERT INTO chat_messages (session_id, user_id, role, content, sources, suggested_questions)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (session_id, user_id, role, content, sources_json, suggested_questions_json)
            self._log_sql(insert_sql.strip(), params)
            cursor.execute(insert_sql, params)
            conn.commit()
            cursor.close()
            
            logger.info(f"添加消息成功: session_id={session_id}, role={role}")
            return True, "添加消息成功"
        except Error as e:
            logger.error(f"添加消息失败: {e}")
            return False, f"添加消息失败: {e}"
    
    def get_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取会话的消息历史"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            
            select_sql = """
            SELECT * FROM chat_messages 
            WHERE session_id = %s
            ORDER BY created_at ASC
            LIMIT %s
            """
            params = (session_id, limit)
            self._log_sql(select_sql.strip(), params)
            cursor.execute(select_sql, params)
            results = cursor.fetchall()
            cursor.close()
            
            # 解析JSON字段
            for result in results:
                if result.get('sources'):
                    try:
                        result['sources'] = json.loads(result['sources'])
                    except:
                        result['sources'] = []
                if result.get('suggested_questions'):
                    try:
                        result['suggested_questions'] = json.loads(result['suggested_questions'])
                    except:
                        result['suggested_questions'] = []
            
            return results
        except Error as e:
            logger.error(f"获取消息历史失败: {e}")
            return []
    
    def get_conversation_history(self, session_id: str, limit: int = 100) -> List[tuple]:
        """获取对话历史，返回格式为[(question, answer), ...]"""
        messages = self.get_messages(session_id, limit)
        history = []
        current_question = None
        
        for msg in messages:
            if msg['role'] == 'user':
                current_question = msg['content']
            elif msg['role'] == 'assistant' and current_question:
                history.append((current_question, msg['content']))
                current_question = None
        
        return history

