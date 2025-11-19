from prompt.prompt_util import *
from llm.llm_service import *
import logging

logger = logging.getLogger(__name__)

def stream_string(string, ind=0):
    for i in range(ind, len(string)):
        yield string[ind:i + 1]

def parse_text(text):
    """copy from https://github.com/GaiZhenbiao/ChuanhuChatGPT/"""
    lines = text.split("\n")
    lines = [line for line in lines if line != ""]
    count = 0
    for i, line in enumerate(lines):
        if "```" in line:
            count += 1
            items = line.split('`')
            if count % 2 == 1:
                lines[i] = f'<pre><code class="language-{items[-1]}">'
            else:
                lines[i] = f'<br><br></code></pre>'
        elif r"\begin{code}" in line:
            count += 1
            lines[i] = '<pre><code>'
        elif r"\end{code}" in line:
            count += 1
            lines[i] = '<br><br></code></pre>'
        else:
            if i > 0:
                if count % 2 == 1:
                    line = line.replace("`", r"\`")
                    line = line.replace("<", "&lt;")
                    line = line.replace(">", "&gt;")
                    line = line.replace(" ", "&ensp;")
                    line = line.replace("*", "&ast;")
                    line = line.replace("_", "&lowbar;")
                    line = line.replace("-", "&#45;")
                    line = line.replace(".", "&#46;")
                    line = line.replace("!", "&#33;")
                    line = line.replace("(", "&#40;")
                    line = line.replace(")", "&#41;")
                    line = line.replace("$", "&#36;")
                lines[i] = "<br>" + line
    text = "".join(lines)
    return text


def parse_context_intent(context_intent):
    last_intent = context_intent.replace(f"{summary_context_intent_prefix_words}", "") \
        .replace("他们的", "").replace("他的", "").replace("他们", "").replace("他", "") \
        .replace("她们的", "").replace("她的", "").replace("她", "") \
        .replace("用户的", "").replace("用户", "") \
        .replace("了解","").replace("询问", "") \
        .rstrip("。").rstrip(".").lstrip(':').lstrip('：')
    return last_intent


def summary_context_intent(query:str, history:list,llm:LlmService,llm_generate_params:dict):
    if len(history)<=1:
        return query
    prompt=summary_context_intent_prompt(query=query, history=history)
    response=llm.inference(prompt=prompt,stream=False,generate_params=llm_generate_params)
    context_intent=parse_context_intent(response)
    return context_intent


def polish_answer(answer:str,llm:LlmService,llm_generate_params:dict,stream=False):
    prompt=polish_answer_prompt(answer=answer)
    response=llm.inference(prompt=prompt,stream=stream,generate_params=llm_generate_params)
    return response


def extend_questions(origin_question:str,llm:LlmService)->list[str]:
    try:
        prompt=extend_questions_prompt(origin_question)
        response=llm.inference(prompt,stream=False)
        if response:
            return response.strip().split('\n')
    except Exception as e:
        import traceback
        logger.error(f'生成扩展问题错误: {traceback.format_exc()}')
        return []

