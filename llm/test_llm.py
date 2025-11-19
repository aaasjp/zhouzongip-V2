from openai import OpenAI
# Set OpenAI's API key and API base to use vLLM's API server.
openai_api_key = "sk-smXfLoe7jIs72ykN7fD157E58e194eEb9aDaCd359c05F5Dc"
openai_api_base = "http://10.249.238.110:8009/v1"

client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)

chat_response = client.chat.completions.create(
    model="qwen3-235b-a22b",
    messages=[
        {"role": "user", "content": "9.9和9.11哪个大？/no_think"},
    ],
    temperature=0.7,
    top_p=0.8,
    presence_penalty=1.5,
    extra_body={
        "top_k": 20,
        "chat_template_kwargs": {"enable_thinking": False}
    },
)
print("Chat response:", chat_response)


import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
completion = client.chat.completions.create(
    model="qwen-plus",  # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    messages=[{'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': '你是谁？'}],
    stream=True,
    stream_options={"include_usage": True}
    )
for chunk in completion:
    print(chunk.model_dump_json())