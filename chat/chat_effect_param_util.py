import json
from mysql_utils.mysql_helper import *

import logging
logger=logging.getLogger(__name__)

##加载配置文件
with open('./config/config.json', 'r') as f:
    config = json.load(f)

def get_chat_effect_param(tenant_code, collection_name):
    chat_effect_params_str = SQLDatabase().get_chat_effect_param(tenant_code=tenant_code,
                                                                 collection_name=collection_name)

    print(f'====>chat_effect_params_str={chat_effect_params_str}',flush=True)
    if chat_effect_params_str:
        chat_effect_params_str=chat_effect_params_str[0]
        chat_effect_param=json.loads(chat_effect_params_str)
    else:
        chat_effect_param=config['chat_effect_param']

    print(f'====>get_chat_effect_param(),chat_effect_param={json.dumps(chat_effect_param, ensure_ascii=False, indent=2)}',flush=True)
    return chat_effect_param

