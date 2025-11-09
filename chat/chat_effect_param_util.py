import json

import logging
logger=logging.getLogger(__name__)

##加载配置文件
with open('./config/config.json', 'r') as f:
    config = json.load(f)

def get_chat_effect_param(tenant_code, collection_name):
    # 直接从配置文件读取，不再从数据库读取
    chat_effect_param = config['chat_effect_param']

    print(f'====>get_chat_effect_param(),chat_effect_param={json.dumps(chat_effect_param, ensure_ascii=False, indent=2)}',flush=True)
    return chat_effect_param

