import logging
logger=logging.getLogger(__name__)

summary_context_intent_prefix_words='用户最后的意图是'

def construct_conversation_by_history(history):
    conversation = ""
    for (inpt, oupt) in history:
        if inpt:
            conversation += "用户:" + inpt + "\n"
        if oupt:
            conversation += "智能助手:" + oupt + "\n"
    return conversation

def summary_context_intent_prompt(query:str, history:list):
    citizen_conversation = construct_conversation_by_history(history=history)
    prompt = "你是一名智能助手，根据用户和智能助手的对话，判断用户当前的意图。下面是对话：\n'''\n"
    prompt += citizen_conversation
    prompt += "\n'''\n"
    prompt += f"判断用户的意图，要求：\n" \
              f"1.如果'{query}'与上面对话没有关系，就直接输出'{query}'。\n" \
              f"2.如果'{query}'与上面对话有关系，就结合上面对话，判断用户关于'{query}'的完整意思，以'{summary_context_intent_prefix_words}'开头。"
    return prompt


def polish_answer_prompt(answer:str):
    prompt = '"""\n'+answer+'"""\n'
    prompt+="整理上面的句子，使其更具条理性"
    return prompt


##延伸问题推荐
def extend_questions_prompt(origin_question:str)->str:
    prompt=f"基于问题'{origin_question}'延伸3个问题,问题之间以'\n'分割"
    return prompt
