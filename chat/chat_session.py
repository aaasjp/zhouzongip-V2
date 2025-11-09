import sys

sys.path.append('./')
import json
import uuid
import time
from mysql_utils.mysql_helper import *
import logging

logger = logging.getLogger(__name__)


class ChatState:
    def __init__(self):
        self.round = 0
        self.user_question = ''
        self.context_question = ''
        self.reply = ''
        self.reply_type = ''
        self.recommend_questions = []
        self.reply_reference = []

    def serialize(self):
        attr_dic = vars(self)
        res_str = json.dumps(attr_dic, ensure_ascii=False, indent=2)
        return res_str

    def deserialize(self, state_str):
        dic = json.loads(state_str)
        for k, v in dic.items():
            setattr(self, k, v)

    def __str__(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False, indent=2)


class ChatSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.chat_state_history: list[ChatState] = []

    def serialize(self):

        def default_serializer(obj):
            if isinstance(obj, ChatState):
                return obj.__dict__
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

        attr_dic = vars(self)
        res_str = json.dumps(attr_dic, ensure_ascii=False, indent=2, default=default_serializer)
        return res_str

    def deserialize(self, state_str):
        dic = json.loads(state_str)
        for k, v in dic.items():
            if k == 'chat_state_history':
                for jb in v:
                    cs = ChatState()
                    cs.deserialize(json.dumps(jb))
                    self.chat_state_history.append(cs)
            else:
                setattr(self, k, v)


class ChatSessionManager:
    def __init__(self):
        self.session_dic = {}

    def generate_session_id(self):
        timestamp = str(int(time.time() * 1000))  # 毫秒时间戳
        unique_id = str(uuid.uuid4())  # 生成UUID
        session_id = f"{timestamp}-{unique_id}"
        return session_id

    ##主要在session_dic中增加一个槽位方session，如果已经有槽位了，直接返回。如果没有，就看数据库有没有，有的话放到槽位；数据库也没有就初始化一个
    def add_session(self, session_id):
        if session_id in self.session_dic:
            print(f"session already exists: {session_id}",flush=True)
        else:
            conversation, chat_session_str = SQLDatabase().get_conversation(session_id=session_id)
            if conversation:
                chat_session = ChatSession(session_id)
                chat_session.deserialize(chat_session_str)
                self.session_dic[session_id] = chat_session
                print(f"add session from mysql: {session_id}",flush=True)
            else:
                self.session_dic[session_id] = ChatSession(session_id)
                print(f"add new session: {session_id}",flush=True)

    def get_session(self, session_id) -> ChatSession:
        return self.session_dic.get(session_id, None)

    def session_exist(self, session_id):
        if session_id in self.session_dic:
            return True
        else:
            return False

    def get_last_round(self, session_id):
        last_round = 0
        cur_session = self.get_session(session_id)
        if cur_session and cur_session.chat_state_history:
            last_round = cur_session.chat_state_history[-1].round
        return last_round

    def get_history(self, session_id):
        history = []
        cur_session = self.get_session(session_id)
        if cur_session and cur_session.chat_state_history:
            for chatstat in cur_session.chat_state_history:
                #print(f'=====>chatstat={chatstat},{type(chatstat)}')
                history.append((chatstat.user_question, chatstat.reply))
        print(f'=====>get history={history}',flush=True)
        return history

    def update_last_reply_to_chat_state(self, session_id, final_answer):
        if self.get_session(session_id).chat_state_history:
            self.get_session(session_id).chat_state_history[-1].reply = final_answer

    def save_session_to_db(self, session_id: str, tenant_code: str, user_id: str):
        chat_session = self.session_dic.get(session_id, None)
        if chat_session:
            chat_session_str = chat_session.serialize()
            SQLDatabase().save_conversation(session_id=session_id, tenant_code=tenant_code, user_id=user_id,
                                            chat_session=chat_session_str)
            print(f'save chat session to mysql completed。{session_id}',flush=True)

    def remove_session(self, session_id):
        if session_id in self.session_dic:
            self.session_dic.pop(session_id, None)


if __name__ == '__main__':
    '''

    s_id = '12323123'

    cstat1 = ChatState()
    cstat1.round = 1
    cstat1.recommend_questions = ['那你还', '滚动']

    cstat2 = ChatState()
    cstat2.round = 2
    cstat2.recommend_questions = ['我还好', 'ok']

    csm = ChatSessionManager()
    csm.add_session(s_id)

    current_se=csm.get_session(session_id=s_id)

    current_se.chat_state_history.extend([cstat1, cstat2])

    ss = csm.get_serialized_session(s_id)

    print('序列化：')
    print(ss)
    print('*' * 100)

    print('把序列化的session保存入库')

    print('*' * 10)

    print('反序列化：')
    restored_session=csm.save_deserialized_session(s_id, ss)

    print(restored_session.chat_state_history[0])

    resored_str=restored_session.serialize()


    print('前后对比')
    if ss==resored_str:
        print("true")
    '''


    # 下面是测试对话数据的数据库操作
    csm = ChatSessionManager()
    # s_id = '12212312312'
    s_id = csm.generate_session_id()
    tenant_code = 'xiaomi'
    user_id = 'fdsfdsfafsafaf'

    csm.add_session(session_id=s_id)

    current_session = csm.get_session(session_id=s_id)

    cstat1 = ChatState()
    cstat1.round = 1
    cstat1.user_question = '你是谁'
    cstat1.context_question = '用户想咨询是谁？'
    cstat1.reply_type = 'LLM'
    cstat1.reply = '我是下凹爱'
    cstat1.recommend_questions = ['你的真名', '你的名字叫啥']

    cstat2 = ChatState()
    cstat2.round = 2
    cstat2.user_question = '我是XX'
    cstat2.context_question = '用户自我介绍？'
    cstat2.reply_type = 'LLM'
    cstat2.reply = '你好哈，XX'
    cstat2.recommend_questions = ['我叫什么', '我是谁']

    current_session.chat_state_history.extend([cstat1, cstat2])

    csm.save_session_to_db(session_id=s_id, tenant_code=tenant_code, user_id=user_id)
