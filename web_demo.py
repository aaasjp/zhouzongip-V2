import json
import torch
import streamlit as st
from llm.llm_service import *
from chat.chat_uitls import ChatUitls
from chat.chat_session import *
from chat.chat_effect_param_util import *

import logging
logger=logging.getLogger(__name__)

# 初始化
st.set_page_config(page_title="智能小助手", page_icon=":handshake:")
st.title("智能小助手")

with open('./config/config.json', 'r') as f:
    config = json.load(f)


session_id='iloD1jUc6dfdDc-0zAADX'
tenant_code='jzbo'
collection_name='gggrfa'
user_id=59
stream=True

@st.cache_resource
def init():
    print(f'====>init()',flush=True)
    chat_session_manager = ChatSessionManager()
    llm_serv=LlmService()
    chat_obj=ChatUitls(llm_srv=llm_serv, chat_session_manager=chat_session_manager)
    chat_effect_params=get_chat_effect_param(tenant_code,collection_name)
    return chat_session_manager,chat_obj,chat_effect_params


def restore_chat_history_to_page(history):
    print('====>restore_chat_history_to_page()',flush=True)
    if not history :
        with st.chat_message("assistant", avatar='🤖'):
            st.markdown("您好，我是**智能客服**，很高兴为您服务🥰")
        return
    for his in history:
        query,reply=his[0],his[1]
        with st.chat_message('user', avatar='🧑‍💻'):
            st.markdown(query)
        with st.chat_message('assistant', avatar='🤖'):
            st.markdown(reply)

def main():
    chat_session_manager,chat_obj,chat_effect_params=init()
    chat_session_manager.add_session(session_id=session_id)
    history=chat_session_manager.get_history(session_id=session_id)
    restore_chat_history_to_page(history)

    if prompt := st.chat_input("Shift + Enter 换行, Enter 发送"):

        with st.chat_message("user", avatar='🧑‍💻'):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar='🤖'):
            placeholder = st.empty()
            params_dic={
                'prompt':prompt,
                'history':history,
                'session_id':session_id,
                'tenant_code':tenant_code,
                'collection_name':collection_name,
                'stream':stream,
                'chat_effect_params':chat_effect_params
            }
            result = chat_obj.chat(params_dic=params_dic)
            print(f'====>result={result}',flush=True)
            finally_resp=''
            if stream:

                for r in result['response']:
                    placeholder.markdown(r)
                finally_resp = r

                #response = st.write_stream(result['response'])
                #print(response)
            chat_session_manager.update_last_reply_to_chat_state(session_id,finally_resp)
            chat_session_manager.save_session_to_db(session_id=session_id,tenant_code=tenant_code,user_id=user_id)


        if torch.backends.mps.is_available():
            torch.mps.empty_cache()




if __name__ == "__main__":
    main()
