import logging
#logging.basicConfig(filename='logs/vector_db_server.log', encoding='utf-8', level=logging.INFO,
#                   format='%(asctime)s - %(filename)s - %(funcName)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

import os
from flask import Flask, request, jsonify
from milvus.miluvs_helper import *
from utils.auth_check import *
from utils.file_loader import *
from mysql_utils.mysql_helper import *



app = Flask(__name__)

##加载配置文件
with open('./config/config.json', 'r') as f:
    config = json.load(f)


@app.route('/')
def index():
    return 'Hello, World!'


@app.route('/vector_db_service/new_collection', methods=['POST'])
def new_collection():
    data = request.get_json()
    print(f'====>new_collection(),data={data}',flush=True)
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    try:
        is_succ, msg = create_collection(tenant_code, collection_name)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})

        SQLDatabase().upsert_chat_effect_param(tenant_code, collection_name, params=config['chat_effect_param'])
    except Exception as e:
        import traceback
        logger.exception(f"创建向量库[{collection_name}]异常:：%s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '成功创建向量库', 'data': ''})


@app.route('/vector_db_service/del_collection', methods=['POST'])
def del_collection():
    data = request.get_json()
    print(f'====>del_collection(),data={data}',flush=True)
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    try:
        is_succ, msg = delete_collection(tenant_code, collection_name)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})

        SQLDatabase().delete_chat_effect_param(tenant_code, collection_name)
    except Exception:
        import traceback
        logger.exception(f"删除向量库[{collection_name}]异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '成功删除向量库', 'data': ''})


@app.route('/vector_db_service/add_qa', methods=['POST'])
def add_qa():
    data = request.get_json()
    print(f'====>add_qa(),data={data}',flush=True)
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    question = data.get('question', '')
    answer = data.get('answer', '')
    source = data.get('source', '')

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not question:
        return jsonify({'status': 'fail', 'msg': '缺少问题参数', 'code': 400, 'data': ''})

    if not answer:
        return jsonify({'status': 'fail', 'msg': '缺少答案参数', 'code': 400, 'data': ''})

    try:
        is_succ, msg = insert_qa_to_collection(tenant_code, collection_name, question_list=[question.strip()],
                                               answer_list=[answer], source_list=[source], metadata_list=[{}])
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"插入向量库[{collection_name}]异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '成功插入问答对到向量库', 'data': ''})


@app.route('/vector_db_service/add_qa_from_template', methods=['POST'])
def add_qa_from_template():
    data = request.get_json()
    print(f'====>add_qa_from_template(),data={data}',flush=True)
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    template_file_path = data.get('template_path', '')

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not template_file_path:
        return jsonify({'status': 'fail', 'msg': '缺少模版文件路径参数', 'code': 400, 'data': ''})

    if not os.path.exists(template_file_path):
        logger.error(f"{template_file_path}模版文件不存在")
        return jsonify({'status': 'fail', 'msg': f"{template_file_path}模版文件不存在", 'code': 400, 'data': ''})

    question_list, answers_list, source_list = load_qa_template(template_file_path)
    metadata_list = [{} for q in question_list]
    try:
        is_succ, msg = insert_qa_to_collection(tenant_code, collection_name, question_list=question_list,
                                               answer_list=answers_list, source_list=source_list,
                                               metadata_list=metadata_list)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"插入问答对到向量库[{collection_name}]异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '成功插入问答对到向量库', 'data': ''})


@app.route('/vector_db_service/add_document', methods=['POST'])
def add_document():
    data = request.get_json()
    print(f'====>add_document(),data={data}',flush=True)
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    doc_path = data.get('doc_path', '')

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not os.path.isfile(doc_path):
        logger.error(f"{doc_path}文件不存在或者是一个目录")
        return jsonify({'status': 'fail', 'msg': f"{doc_path}文件不存在或者不是一个文件", 'code': 400, 'data': ''})

    is_succ, content = extract_content_from_file(doc_path)
    if not is_succ:
        logger.error(f'f"解析文件失败:{content}"')
        return jsonify({'status': 'fail', 'msg': f"解析文件失败:{content}", 'code': 400, 'data': ''})

    try:
        doc_name = doc_path.split('/')[-1]
        is_succ, msg = insert_docs_to_collection(tenant_code, collection_name, doc_name_list=[doc_name.strip()],
                                                 doc_content_list=[content], source_list=[doc_path], metadata_list=[{}])
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"插入文档到向量库[{collection_name}]异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '成功插入文档到向量库', 'data': ''})


@app.route('/vector_db_service/add_multi_document', methods=['POST'])
def add_multi_document():
    data = request.get_json()
    print(f'====>add_multi_document(),data={data}')
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    multi_doc_path = data.get('multi_doc_path', '')

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not os.path.exists(multi_doc_path):
        logger.error(f"{multi_doc_path}目录不存在")
        return jsonify({'status': 'fail', 'msg': f"{multi_doc_path}目录不存在", 'code': 400, 'data': ''})

    files_and_dirs = os.listdir(multi_doc_path)
    files = [os.path.join(multi_doc_path, f) for f in files_and_dirs if os.path.isfile(os.path.join(multi_doc_path, f))]

    success_count = 0
    failed_count = 0
    for doc in files:
        try:
            is_succ, content = extract_content_from_file(doc)
            if not is_succ:
                logger.error(f'f"解析文件[{doc}]失败:{content}"')
                failed_count += 1
                continue
            doc_name = doc.split('/')[-1]
            is_succ, msg = insert_docs_to_collection(tenant_code, collection_name, doc_name_list=[doc_name],
                                                     doc_content_list=[content], source_list=[doc_path],
                                                     metadata_list=[{}])
            if not is_succ:
                logger.error(f'f"插入文档[{doc}]到向量库[{collection_name}]失败:{msg}"')
                failed_count += 1
                continue
            success_count += 1
        except Exception:
            import traceback
            logger.exception(f"插入文档[{doc}]到向量库[{collection_name}]异常: %s", traceback.format_exc())
            return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    if failed_count > 0:
        return jsonify({'status': 'fail', 'code': 400,
                        'msg': f'插入文档到向量库[{collection_name}]：成功[{success_count}]个,失败[{failed_count}]个', 'data': ''})
    return jsonify({'status': 'success', 'code': 200, 'msg': '插入文档到向量库[{collection_name}]成功', 'data': ''})


@app.route('/vector_db_service/update_qa', methods=['POST'])
def update_qa():
    data = request.get_json()
    print(f'====>update_qa(),data={data}')
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    question = data.get('question', '')
    answer = data.get('answer', '')
    source = data.get('source', '')

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not question:
        return jsonify({'status': 'fail', 'msg': '缺少问题参数', 'code': 400, 'data': ''})

    if not answer:
        return jsonify({'status': 'fail', 'msg': '缺少答案参数', 'code': 400, 'data': ''})

    try:
        is_succ, msg = upsert_qa_to_collection(tenant_code, collection_name, question_list=[question],
                                               answer_list=[answer], source_list=[source], metadata_list=[{}])
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"更新向量库[{collection_name}]异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '成功更新问答对到向量库', 'data': ''})


@app.route('/vector_db_service/del_qa', methods=['POST'])
def del_qa():
    data = request.get_json()
    print(f'====>del_qa(),data={data}')
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    question = data.get('question', [])

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not question:
        return jsonify({'status': 'fail', 'msg': '缺少问题参数', 'code': 400, 'data': ''})

    question_list=[q.strip() for q in question]

    try:
        is_succ, msg = delete_qa_from_collection(tenant_code, collection_name, question_list=question_list)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"从向量库[{collection_name}]删除问答对异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '从向量库删除问答对成功', 'data': ''})



@app.route('/vector_db_service/del_document', methods=['POST'])
def del_document():
    data = request.get_json()
    print(f'====>del_document(),data={data}')
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    doc_name = data.get('doc_name', [])

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not doc_name:
        return jsonify({'status': 'fail', 'msg': '缺少问题参数', 'code': 400, 'data': ''})

    doc_name_list=[dname.strip() for dname in doc_name]

    try:
        is_succ, msg = delete_docs_from_collection(tenant_code, collection_name, doc_name_list=doc_name_list)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"从向量库[{collection_name}]删除文档异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '从向量库删除文档成功', 'data': ''})


@app.route('/vector_db_service/search_from_vector_db', methods=['POST'])
def search_from_vector_db():
    data = request.get_json()
    print(f'====>search_from_vector_db(),data={data}')
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    query = data.get('query', '')
    collection_type = data.get('collection_type', '')
    filter_expr = data.get('filter_expr', '')
    limit=data.get('limit',5)

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not query:
        return jsonify({'status': 'fail', 'msg': '搜索数据不能为空', 'code': 400, 'data': ''})

    if not collection_type:
        return jsonify({'status': 'fail', 'msg': 'collect_type不能为空', 'code': 400, 'data': ''})

    try:
        res = search_from_collection(tenant_code=tenant_code, collection_name=collection_name,
                                     collection_type=collection_type, query_list=[query], filter_expr=filter_expr, limit=limit)

        print(f"从向量库[{collection_name}]查询成功")
    except Exception:
        import traceback
        logger.exception(f"从向量库[{collection_name}]查询异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '从向量库查询成功', 'data': res})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8801)
