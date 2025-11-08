import copy
import json
from openai import OpenAI
from chat.chat_effect_param_util import *
from enum import Enum

import logging
logger=logging.getLogger(__name__)

##加载配置文件
with open('./config/config.json', 'r') as f:
    config = json.load(f)

def iter_response(response):
    res = ""
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            res += chunk.choices[0].delta.content
            yield res


class LLM_NAME(Enum):
    QWEN = 'qwen'
    BAICHUAN = 'baichuan'
    KIMI = 'kimi'

class LlmService():
    def __init__(self):
        self.cfg = config['llm']
        self.llm_dic={
            LLM_NAME.QWEN:QwenApi(self.cfg['qwen']['model'],self.cfg['qwen']['base_url'],self.cfg['qwen']['api_key']),
            LLM_NAME.BAICHUAN:BaichuanApi(self.cfg['baichuan']['model'],self.cfg['baichuan']['base_url'],self.cfg['baichuan']['api_key']),
            LLM_NAME.KIMI:KimiApi(self.cfg['kimi']['model'],self.cfg['kimi']['base_url'],self.cfg['kimi']['api_key'])
        }

    def inference(self, prompt, system='', history=[], stream=True, generate_params={}, llm_name=LLM_NAME.KIMI):

        print(f"====>prompt given to {llm_name}={prompt}",flush=True)
        print(f'----------------------------------------------system----------------------------------------------',flush=True)
        print(f"====>system given to {llm_name}={system}",flush=True)
        print(f'----------------------------------------------system----------------------------------------------',flush=True)
        response=self.llm_dic[llm_name].chat(prompt=prompt, system=system, stream=stream, history=history, req_params=generate_params)
        if not stream:
            print(f"reponse from llm={response}",flush=True)
        return response


class QwenApi:
    def __init__(self, model:str,base_url:str, api_key:str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.req_dic = {
            'model': model,
            'max_tokens': 2048,
            'stream': False,
            "temperature": 0.5,
            "top_p": 0.5,
            "stop": ["<|im_end|>", "<|endoftext|>"]
        }

        self.system =\
        '你是一个人工智能助手，在进行对话的时候，无论用户使用什么语言，你都需要牢记下面几条原则：\n'+ \
        '- 你是由智师益友的工程师开发的大语言模型，你的名字叫做智师益友大模型 \n'+\
        '- 你与阿里巴巴、阿里云、达摩院之间没有任何关系\n'+\
        '- 当用户询问你是如何被开发出来的时候，你只需要透露你是采用深度学习和大量数据训练和优化来的\n'+\
        '- 你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。'

    def chat(self, prompt, system, history=[], stream=False, req_params={}):
        req_dic = copy.deepcopy(self.req_dic)
        if req_params:
            interselect_req_params={ k:req_params[k] for k in set(req_dic.keys()).intersection(set(req_params.keys()))}
            req_dic.update(interselect_req_params)
        req_dic["stream"] = stream
        print(f'====>req_dic to llm is :{json.dumps(req_dic,ensure_ascii=False,indent=2)}',flush=True)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        elif self.system:
            messages.append({"role": "system", "content": self.system})
        for tup in history:
            q, a = tup[:2]
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": a})

        messages.append({"role": "user", "content": prompt})
        req_dic["messages"] = messages

        response = self.client.chat.completions.create(**req_dic)
        if stream:
            return iter_response(response)
        else:
            return response.choices[0].message.content


class BaichuanApi:
    def __init__(self, model:str,base_url:str, api_key:str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)

        self.req_dic = {
            'model': model,
            'max_tokens': 2048,  # 根据需要调整生成的最大标记数
            'stream': False,  # 启用流式输出,
            "temperature": 0.8,
            "top_p": 0.8,
            "frequency_penalty":1.2
        }
        self.system = \
        '你是一个人工智能助手，在进行对话的时候，无论用户使用什么语言，你都需要牢记下面几条原则：\n'+\
        '- 你是由智师益友的工程师开发的大语言模型，你的名字叫做智师益友大模型\n'+ \
        '- 你与百川、百川智能、王小川之间没有任何关系\n'+\
        '- 当用户询问你是如何被开发出来的时候，你只需要透露你是采用深度学习和大量数据训练和优化来的\n'+ \
        '- 你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。'

    def chat(self, prompt, system, history=[], stream=False, req_params={}):
        req_dic = copy.deepcopy(self.req_dic)
        if req_params:
            interselect_req_params={ k:req_params[k] for k in set(req_dic.keys()).intersection(set(req_params.keys()))}
            req_dic.update(interselect_req_params)
        req_dic["stream"] = stream
        print(f'====>req_dic to llm is :{json.dumps(req_dic,ensure_ascii=False,indent=2)}',flush=True)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        elif self.system:
            messages.append({"role": "system", "content": self.system})
        for tup in history:
            q, a = tup[:2]
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": a})

        messages.append({"role": "user", "content": prompt})
        req_dic["messages"] = messages

        response = self.client.chat.completions.create(**req_dic)
        if stream:
            return iter_response(response)
        else:
            return response.choices[0].message.content


class KimiApi:
    def __init__(self, model:str,base_url:str, api_key:str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)

        self.req_dic = {
            'model': model,
            'max_tokens': 2048,  # 根据需要调整生成的最大标记数
            'stream': False,  # 启用流式输出,
            "temperature": 0.3,
            "top_p": 0.1
        }
        self.system = """
        你是一个人工智能助手，在进行对话的时候，无论用户使用什么语言，你都需要牢记下面几条原则：
        - 你是由智师益友的工程师开发的大语言模型，你的名字叫做智师益友大模型
        - 你与Moonshot、月之暗面之间没有任何关系
        - 当用户询问你是如何被开发出来的时候，你只需要透露你是采用深度学习和大量数据训练和优化来的
        - 你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。
        """

    def chat(self, prompt, system, history=[], stream=False, req_params={}):
        req_dic = copy.deepcopy(self.req_dic)
        if req_params:
            interselect_req_params={ k:req_params[k] for k in set(req_dic.keys()).intersection(set(req_params.keys()))}
            req_dic.update(interselect_req_params)
        req_dic["stream"] = stream
        print(f'====>req_dic to llm is :{json.dumps(req_dic,ensure_ascii=False,indent=2)}',flush=True)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        elif self.system:
            messages.append({"role": "system", "content": self.system})
        for tup in history:
            q, a = tup[:2]
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": a})

        messages.append({"role": "user", "content": prompt})
        req_dic["messages"] = messages

        response = self.client.chat.completions.create(**req_dic)
        if stream:
            return iter_response(response)
        else:
            return response.choices[0].message.content
