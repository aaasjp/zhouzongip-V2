import json
import mysql.connector

import logging

logger = logging.getLogger(__name__)

##加载配置文件
with open('./config/config.json', 'r') as f:
    config = json.load(f)

MYSQL_HOST = config['mysql']['host']
MYSQL_PORT = config['mysql']['port']
MYSQL_USER = config['mysql']['user']
MYSQL_PWD = config['mysql']['password']
MYSQL_BASE = config['mysql']['db_name']


class SQLDatabase:
    def __init__(self):
        self.connection = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PWD,
            database=MYSQL_BASE
        )
        self.cursor = self.connection.cursor()

    def upsert_chat_effect_param(self, tenant_code: str, collection_name: str, params: dict):
        params_str = json.dumps(params)
        try:
            sql_check = "SELECT id FROM t_chat_effect_param WHERE tenant_code = %s AND collection_name = %s"
            self.cursor.execute(sql_check, (tenant_code, collection_name))

            # 获取查询结果
            result = self.cursor.fetchone()

            if result:
                # 如果存在，更新数据
                sql_update = """
                        UPDATE t_chat_effect_param
                        SET params = %s
                        WHERE tenant_code = %s AND collection_name = %s
                    """
                self.cursor.execute(sql_update, (params_str, tenant_code, collection_name))
                print(f"更新问答效果参数成功： params={params}")
            else:
                # 如果不存在，插入数据
                sql_insert = """
                        INSERT INTO t_chat_effect_param (tenant_code, collection_name, params)
                        VALUES (%s, %s, %s)
                    """
                self.cursor.execute(sql_insert, (tenant_code, collection_name, params_str))
                self.connection.commit()
            print(f"插入问答效果参数成功： params={params}")
            return 1
        except Exception:
            import traceback
            self.connection.rollback()
            logging.error(f"插入问答效果参数失败： {traceback.format_exc()}")
            return 0
        finally:
            self.cursor.close()
            self.connection.close()

    def get_chat_effect_param(self, tenant_code: str, collection_name: str):
        squ_query = """
            SELECT params FROM t_chat_effect_param WHERE tenant_code = %s and collection_name = %s
        """
        data = (tenant_code, collection_name)

        try:
            self.cursor.execute(squ_query, data)
            params = self.cursor.fetchone()
            return params
        except Exception:
            import traceback
            logging.error(f"查询问答效果参数失败： {traceback.format_exc()}")
            return None
        finally:
            self.cursor.close()
            self.connection.close()

    def delete_chat_effect_param(self, tenant_code: str, collection_name: str):
        try:
            sql_delete = "DELETE FROM t_chat_effect_param WHERE tenant_code = %s AND collection_name = %s"
            # 执行删除语句
            self.cursor.execute(sql_delete, (tenant_code, collection_name))
            # 提交事务
            self.connection.commit()
            return 1
        except Exception:
            import traceback
            logging.error(f"删除问答效果参数失败： {traceback.format_exc()}")
            return 0
        finally:
            self.cursor.close()
            self.connection.close()

    def save_conversation(self, session_id: str, tenant_code: str, user_id: str, chat_session: str):
        try:
            sql_check = "SELECT id FROM t_conversation WHERE session_id = %s "
            self.cursor.execute(sql_check, (session_id,))
            # 获取查询结果
            exist = self.cursor.fetchone()
            if exist:
                sql_update = """
                        UPDATE t_conversation
                        SET tenant_code = %s, user_id = %s, chat_session = %s 
                        WHERE session_id = %s
                    """
                self.cursor.execute(sql_update, (tenant_code, user_id, chat_session, session_id))
                self.connection.commit()
                print(f"更新会话成功：sesssion_id={session_id}")
            else:
                sql_insert = """
                        INSERT INTO t_conversation (session_id, tenant_code, user_id, chat_session)
                        VALUES (%s, %s, %s, %s)
                    """
                self.cursor.execute(sql_insert, (session_id, tenant_code, user_id, chat_session))
                self.connection.commit()
                print(f"插入会话成功：sesssion_id={session_id}")

        except Exception:
            import traceback
            logging.error(f"保存会话失败： {traceback.format_exc()}")
            raise
        finally:
            self.cursor.close()
            self.connection.close()

    def get_conversation(self, session_id: str):
        try:
            sql_select = "SELECT * FROM t_conversation WHERE session_id = %s "
            self.cursor.execute(sql_select, (session_id,))
            conversation = self.cursor.fetchone()
            #print(f'====>conversation={conversation}',flush=True)
            if conversation:
                return conversation,conversation[4]
            else:
                return None,None
        except Exception:
            import traceback
            logging.error(f"查找对话失败： {traceback.format_exc()}")
            return None,None
        finally:
            self.cursor.close()
            self.connection.close()

    def delete_session(self, session_id: str):
        try:
            sql_delete = "SELECT * FROM t_conversation WHERE session_id = %s "
            self.cursor.execute(sql_delete, (session_id,))
            conversation = self.cursor.fetchone()
            if conversation:
                return conversation,conversation[4]
            else:
                return None,None
        except Exception:
            import traceback
            logging.error(f"查找对话失败： {traceback.format_exc()}")
            return None,None
        finally:
            self.cursor.close()
            self.connection.close()
