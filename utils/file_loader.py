import pandas as pd
from docx import Document
import subprocess
from langchain_community.document_loaders import PyPDFLoader
import requests
import json
import logging

logger = logging.getLogger(__name__)


def load_qa_template(template_file_path):
    sheet_name = '问答对数据'
    col_ques_name = '问题'
    col_ans_name = '答案'
    col_source_name = '关联文档名称'

    df = pd.read_excel(template_file_path, sheet_name=sheet_name)
    df = df.fillna('')

    question_list = df[col_ques_name].values
    answers_list = df[col_ans_name].values
    source_list = df[col_source_name].values

    assert len(question_list) == len(answers_list) == len(source_list)
    assert '' not in question_list
    assert '' not in answers_list

    return question_list, answers_list, source_list


def extract_content_from_file(file_url, ocr_config=None):
    """
    通过OCR接口解析文档内容（支持URL链接）
    :param file_url: 文档URL链接
    :param ocr_config: OCR服务配置，包含base_url、parse_mode、timeout等
    :return: (is_success, content_or_error_message)
    """
    if ocr_config is None:
        # 如果没有传入配置，尝试从配置文件读取
        try:
            with open('./config/config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                ocr_config = config.get('ocr_service', {})
        except Exception as e:
            logger.error(f"读取OCR配置失败: {e}")
            return False, f"OCR配置读取失败: {repr(e)}"
    
    base_url = ocr_config.get('base_url', 'http://localhost:8000')
    parse_mode = ocr_config.get('parse_mode', 'balanced')
    timeout = ocr_config.get('timeout', 300)
    
    # 构建OCR接口URL
    parse_url = f"{base_url.rstrip('/')}/parse"
    
    try:
        # 调用OCR接口解析文档
        payload = {
            "document": file_url,
            "parse_mode": parse_mode,
            "include_raw_result": False
        }
        
        logger.info(f"调用OCR接口解析文档: {parse_url}, 文档URL: {file_url}")
        response = requests.post(parse_url, json=payload, timeout=timeout)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get('success', False):
            text_content = result.get('text_content', '')
            if text_content:
                logger.info(f"OCR解析成功，文档URL: {file_url}")
                return True, text_content
            else:
                logger.warning(f"OCR解析返回内容为空，文档URL: {file_url}")
                return False, "OCR解析返回内容为空"
        else:
            error_msg = result.get('error', '未知错误')
            logger.error(f"OCR解析失败，文档URL: {file_url}, 错误: {error_msg}")
            return False, f"OCR解析失败: {error_msg}"
            
    except requests.exceptions.Timeout:
        error_msg = f"OCR接口请求超时（超过{timeout}秒）"
        logger.error(f"{error_msg}, 文档URL: {file_url}")
        return False, error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"OCR接口请求异常: {repr(e)}"
        logger.error(f"{error_msg}, 文档URL: {file_url}")
        return False, error_msg
    except Exception as e:
        error_msg = f"解析文档异常: {repr(e)}"
        logger.error(f"{error_msg}, 文档URL: {file_url}")
        return False, error_msg


def save_doc_to_docx(doc_file_path, docx_file_path):
    """
    doc转docx
    :param dir_path:
    :param dir_name:
    :return:
    """
    # 注意：这里要用subprocess的run方法，这是Python3.4之后的用法，如果还用之前的方法会报错。
    try:
        output = subprocess.run(
            f"soffice --headless --invisible --convert-to docx '{doc_file_path}' --outdir {docx_file_path}",
            shell=True, capture_output=True, encoding='utf-8'
        )
    except Exception as e:
        return None, e
    return output, 'success'


def load_pdf(file_path: str):
    try:
        loader = PyPDFLoader(file_path)
        #loader = PyPDFLoader(file_path, extract_images=True)
        pages = loader.load_and_split()
        contents = []
        for page in pages:
            page_text = page.page_content
            raw_text = [text.strip() for text in page_text.splitlines() if text.strip()]
            new_text = ''
            for text in raw_text:
                new_text += text
                if text[-1] in ['.', '!', '?', '。', '！', '？', '…', ';', '；', ':', '：', '”', '’', '）', '】', '》', '」',
                                '』', '〕', '〉', '》', '〗', '〞', '〟', '»', '"', "'", ')', ']', '}']:
                    contents.append(new_text)
                    new_text = ''
            if new_text:
                contents.append(new_text)
    except Exception as e:
        import traceback
        print(traceback.format_exc(), flush=True)
    return '\n'.join(contents)


def load_docx(file_path):
    doc = Document(file_path)
    tables = doc.tables
    table_count = 0
    cont = ''
    for element in doc.element.body:
        if element.tag.endswith('p'):
            cont = cont + "\n" + element.text.strip()
        elif element.tag.endswith('tbl'):
            data = []
            for row in tables[table_count].rows:
                row_data = []
                for cell in row.cells:
                    row_data.append(cell.text)
                data.append(row_data)
            df = pd.DataFrame(data[1:], columns=data[0])
            markdown_content = df.to_markdown(index=False)
            cont = cont + "\n" + markdown_content
            table_count += 1
    return cont


def load_table(file_path):
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
    cont = ''
    for index, row in df.iterrows():
        cont += f'index: {index}\n'
        curr_cont = str(row)
        cont += curr_cont[:curr_cont.rfind('\n')]
    return cont
