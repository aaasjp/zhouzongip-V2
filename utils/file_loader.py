import pandas as pd
from docx import Document
import subprocess
from langchain_community.document_loaders import PyPDFLoader


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


def extract_content_from_file(file_path):
    file_name = file_path.split('/')[-1]
    file_type = file_name.split('.')[-1]
    cont = ""
    if file_type not in ['txt', 'docx', 'md', 'pdf']:
        return False, '现在只支持txt，docx，md, pdf类型的文档'
    try:
        '''
        if file_name.endswith('.docx'):
            doc = Document(file_path)
            for value in doc.paragraphs:
                cont = cont + "\n" + value.text
        '''
        if file_name.endswith('.docx'):
            cont = load_docx(file_path)
        elif file_name.endswith('.pdf'):
            cont = load_pdf(file_path)
        elif file_name.endswith('.txt') or file_name.endswith('.md'):
            with open(file_path, "r", encoding='utf-8') as fb:
                cont = fb.read()
        return True, cont
    except Exception as e:
        return False, repr(e)


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
