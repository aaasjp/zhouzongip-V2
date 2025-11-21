import logging
from config.log_config import setup_vector_db_logging

# 配置向量库服务日志
setup_vector_db_logging()
logger = logging.getLogger('vector_db')

import os
import json
import tempfile
import requests
from urllib.parse import urlparse
from flask import Blueprint, request, jsonify, send_file
from milvus.miluvs_helper import *
from utils.file_loader import *

# 创建 Blueprint
vector_db_bp = Blueprint('vector_db', __name__)

##加载配置文件
with open('./config/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)


@vector_db_bp.route('/')
def index():
    return 'Hello, World!'


@vector_db_bp.route('/vector_db_service/new_collection', methods=['POST'])
def new_collection():
    data = request.get_json()
    logger.info(f'创建全局collection，请求参数: {data}')

    try:
        is_succ, msg = create_collection()
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception as e:
        import traceback
        logger.exception(f"创建全局向量库异常: {traceback.format_exc()}")
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '成功创建全局向量库', 'data': ''})


@vector_db_bp.route('/vector_db_service/del_collection', methods=['POST'])
def del_collection():
    data = request.get_json()
    logger.info(f'删除collection数据，请求参数: {data}')
    tenant_code = data.get('tenant_code', '')
    org_code = data.get('org_code', '')

    # tenant_code和org_code用于过滤要删除的数据，都是可选的
    try:
        is_succ, msg = delete_collection(tenant_code if tenant_code else None, org_code if org_code else None)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"删除向量库数据异常: {traceback.format_exc()}")
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '成功删除向量库数据', 'data': ''})


# ==================== 文档相关接口 ====================

@vector_db_bp.route('/vector_db_service/add_document', methods=['POST'])
def add_document():
    data = request.get_json()
    logger.info(f'添加文档，请求参数: tenant_code={data.get("tenant_code", "")}, org_code={data.get("org_code", "")}, doc_name={data.get("doc_name", "")}, doc_url={data.get("doc_url", "")}')
    tenant_code = data.get('tenant_code', '')
    org_code = data.get('org_code', '')
    doc_url = data.get('doc_url', '')
    doc_name = data.get('doc_name', '')

    if not doc_url:
        return jsonify({'status': 'fail', 'msg': '缺少文档URL参数', 'code': 400, 'data': ''})

    if not doc_name:
        return jsonify({'status': 'fail', 'msg': '缺少文档名称参数', 'code': 400, 'data': ''})

    # 验证URL格式
    try:
        parsed_url = urlparse(doc_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return jsonify({'status': 'fail', 'msg': '文档URL格式不正确', 'code': 400, 'data': ''})
    except Exception as e:
        return jsonify({'status': 'fail', 'msg': f'文档URL格式验证失败: {repr(e)}', 'code': 400, 'data': ''})

    # 从配置读取OCR配置
    ocr_config = config.get('ocr_service', {})
    is_succ, content = extract_content_from_file(doc_url, ocr_config=ocr_config)
    if not is_succ:
        logger.error(f"解析文档失败: {content}")
        return jsonify({'status': 'fail', 'msg': f"解析文档失败:{content}", 'code': 400, 'data': ''})

    try:
        is_succ, msg = insert_docs_to_collection(tenant_code, org_code, doc_name_list=[doc_name.strip()],
                                                 doc_content_list=[content], source_list=[doc_url], metadata_list=[{}])
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"插入文档到向量库异常: {traceback.format_exc()}")
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '成功插入文档到向量库', 'data': ''})


@vector_db_bp.route('/vector_db_service/add_multi_document', methods=['POST'])
def add_multi_document():
    data = request.get_json()
    logger.info(f'批量添加文档，请求参数: tenant_code={data.get("tenant_code", "")}, org_code={data.get("org_code", "")}, doc_count={len(data.get("multi_doc_urls", []))}')
    tenant_code = data.get('tenant_code', '')
    org_code = data.get('org_code', '')
    multi_doc_urls = data.get('multi_doc_urls', [])
    doc_names = data.get('doc_names', [])

    if not multi_doc_urls or not isinstance(multi_doc_urls, list):
        return jsonify({'status': 'fail', 'msg': '缺少文档URL列表参数或格式不正确', 'code': 400, 'data': ''})

    if len(multi_doc_urls) == 0:
        return jsonify({'status': 'fail', 'msg': '文档URL列表为空', 'code': 400, 'data': ''})

    if not doc_names or not isinstance(doc_names, list):
        return jsonify({'status': 'fail', 'msg': '缺少文档名称列表参数或格式不正确', 'code': 400, 'data': ''})

    if len(doc_names) != len(multi_doc_urls):
        return jsonify({'status': 'fail', 'msg': f'文档名称列表长度({len(doc_names)})与文档URL列表长度({len(multi_doc_urls)})不一致', 'code': 400, 'data': ''})

    # 从配置读取OCR配置
    ocr_config = config.get('ocr_service', {})
    
    success_count = 0
    failed_count = 0
    for idx, doc_url in enumerate(multi_doc_urls):
        try:
            # 验证URL格式
            try:
                parsed_url = urlparse(doc_url)
                if not parsed_url.scheme or not parsed_url.netloc:
                    logger.error(f"文档URL格式不正确: {doc_url}")
                    failed_count += 1
                    continue
            except Exception as e:
                logger.error(f"文档URL格式验证失败: {doc_url}, 错误: {repr(e)}")
                failed_count += 1
                continue
            
            is_succ, content = extract_content_from_file(doc_url, ocr_config=ocr_config)
            if not is_succ:
                logger.error(f"解析文档[{doc_url}]失败:{content}")
                failed_count += 1
                continue
            
            # 从请求参数中获取文档名称
            doc_name = doc_names[idx].strip() if idx < len(doc_names) else ''
            if not doc_name:
                logger.error(f"文档名称为空，索引: {idx}")
                failed_count += 1
                continue
            
            is_succ, msg = insert_docs_to_collection(tenant_code, org_code, doc_name_list=[doc_name],
                                                     doc_content_list=[content], source_list=[doc_url],
                                                     metadata_list=[{}])
            if not is_succ:
                logger.error(f"插入文档[{doc_url}]到向量库失败:{msg}")
                failed_count += 1
                continue
            success_count += 1
        except Exception:
            import traceback
            logger.exception(f"插入文档[{doc_url}]到向量库异常: {traceback.format_exc()}")
            failed_count += 1
            continue
    
    if failed_count > 0:
        return jsonify({'status': 'fail', 'code': 400,
                        'msg': f'插入文档到向量库：成功[{success_count}]个,失败[{failed_count}]个', 'data': ''})
    return jsonify({'status': 'success', 'code': 200, 'msg': f'插入文档到向量库成功', 'data': ''})


@vector_db_bp.route('/vector_db_service/del_document', methods=['POST'])
def del_document():
    data = request.get_json()
    logger.info(f'删除文档，请求参数: tenant_code={data.get("tenant_code", "")}, org_code={data.get("org_code", "")}, doc_count={len(data.get("doc_name", []))}')
    tenant_code = data.get('tenant_code', '')
    org_code = data.get('org_code', '')
    doc_name = data.get('doc_name', [])

    if not doc_name:
        return jsonify({'status': 'fail', 'msg': '缺少文档名称参数', 'code': 400, 'data': ''})

    doc_name_list=[dname.strip() for dname in doc_name]

    try:
        is_succ, msg = delete_docs_from_collection(tenant_code, org_code, doc_name_list=doc_name_list)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"从全局向量库删除文档异常: {traceback.format_exc()}")
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '从全局向量库删除文档成功', 'data': ''})


@vector_db_bp.route('/vector_db_service/search_from_vector_db', methods=['POST'])
def search_from_vector_db():
    data = request.get_json()
    logger.info(f'从向量库搜索，请求参数: tenant_code={data.get("tenant_code", "")}, org_code={data.get("org_code", "")}, query={data.get("query", "")[:100]}..., collection_type={data.get("collection_type", "")}, limit={data.get("limit", 5)}, use_hybrid={data.get("use_hybrid", False)}')
    tenant_code = data.get('tenant_code', '')
    org_code = data.get('org_code', '')
    query = data.get('query', '')
    collection_type = data.get('collection_type', '')
    filter_expr = data.get('filter_expr', '')
    limit = data.get('limit', 5)  # 接口默认limit为5，不使用配置中的search_limit
    use_hybrid = data.get('use_hybrid', False)  # 是否使用混合检索，默认False
    # 向量库服务接口可以传递阈值，如果不传则使用None（不进行阈值过滤）
    vector_similarity_threshold = data.get('vector_similarity_threshold', None)
    rrf_similarity_threshold = data.get('rrf_similarity_threshold', None)

    if not query:
        return jsonify({'status': 'fail', 'msg': '搜索数据不能为空', 'code': 400, 'data': ''})

    if not collection_type:
        return jsonify({'status': 'fail', 'msg': 'collect_type不能为空', 'code': 400, 'data': ''})

    # 根据 collection_type 获取对应的向量库名称
    name_convention = config.get('name_convention', {})
    if collection_type == 'DOC':
        collection_name = name_convention.get('global_collection_doc', '全局文档向量库')
    else:  # QA
        collection_name = name_convention.get('global_collection_qa', '全局QA向量库')

    try:
        res = search_from_collection(tenant_code=tenant_code, org_code=org_code,
                                     collection_type=collection_type, query_list=[query], 
                                     filter_expr=filter_expr, limit=limit, use_hybrid=use_hybrid,
                                     vector_similarity_threshold=vector_similarity_threshold,
                                     rrf_similarity_threshold=rrf_similarity_threshold)

        logger.info(f"从向量库[{collection_name}]查询成功，使用混合检索: {use_hybrid}")
    except Exception:
        import traceback
        logger.exception(f"从向量库[{collection_name}]查询异常: {traceback.format_exc()}")
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '从向量库查询成功', 'data': res})


# ==================== 问答对相关接口 ====================

@vector_db_bp.route('/vector_db_service/download_qa_template', methods=['GET'])
def download_qa_template():
    """下载问答库模板文件"""
    template_path = './data/问答库模板.xlsx'
    if not os.path.exists(template_path):
        return jsonify({'status': 'fail', 'msg': '模板文件不存在', 'code': 404, 'data': ''})
    
    return send_file(template_path, as_attachment=True, download_name='问答库模板.xlsx')


@vector_db_bp.route('/vector_db_service/add_qa', methods=['POST'])
def add_qa():
    data = request.get_json()
    logger.info(f'添加QA，请求参数: tenant_code={data.get("tenant_code", "")}, org_code={data.get("org_code", "")}, question_count={len(data.get("question", [])) if isinstance(data.get("question"), list) else 1}')
    tenant_code = data.get('tenant_code', '')
    org_code = data.get('org_code', '')
    question = data.get('question', '')
    answer = data.get('answer', '')
    source = data.get('source', '')

    # 支持question和answer可以是字符串或列表
    # 如果是字符串，转换为列表（保持向后兼容）
    if isinstance(question, str):
        if not question.strip():
            return jsonify({'status': 'fail', 'msg': '缺少问题参数', 'code': 400, 'data': ''})
        question_list = [question.strip()]
    elif isinstance(question, list):
        if len(question) == 0:
            return jsonify({'status': 'fail', 'msg': '问题列表不能为空', 'code': 400, 'data': ''})
        question_list = [q.strip() if isinstance(q, str) else str(q).strip() for q in question]
        # 检查转换后是否有空问题
        if any(not q for q in question_list):
            return jsonify({'status': 'fail', 'msg': '问题列表中包含空问题', 'code': 400, 'data': ''})
    else:
        return jsonify({'status': 'fail', 'msg': '问题参数格式不正确，应为字符串或列表', 'code': 400, 'data': ''})

    if isinstance(answer, str):
        if not answer:
            return jsonify({'status': 'fail', 'msg': '缺少答案参数', 'code': 400, 'data': ''})
        answer_list = [answer]
    elif isinstance(answer, list):
        if len(answer) == 0:
            return jsonify({'status': 'fail', 'msg': '答案列表不能为空', 'code': 400, 'data': ''})
        answer_list = [a if isinstance(a, str) else str(a) for a in answer]
        # 检查转换后是否有空答案
        if any(not a for a in answer_list):
            return jsonify({'status': 'fail', 'msg': '答案列表中包含空答案', 'code': 400, 'data': ''})
    else:
        return jsonify({'status': 'fail', 'msg': '答案参数格式不正确，应为字符串或列表', 'code': 400, 'data': ''})

    # 验证question和answer列表长度是否一致
    if len(question_list) != len(answer_list):
        return jsonify({'status': 'fail', 'msg': f'问题列表长度({len(question_list)})与答案列表长度({len(answer_list)})不一致', 'code': 400, 'data': ''})

    # 处理source参数：如果是列表，长度需匹配；如果是字符串，重复使用
    if isinstance(source, list):
        if len(source) != len(question_list):
            return jsonify({'status': 'fail', 'msg': f'来源列表长度({len(source)})与问题列表长度({len(question_list)})不一致', 'code': 400, 'data': ''})
        source_list = source
    else:
        # 字符串或空值，重复使用
        source_list = [source] * len(question_list)

    # 生成metadata_list
    metadata_list = [{}] * len(question_list)

    try:
        is_succ, msg = insert_qa_to_collection(tenant_code, org_code, question_list=question_list,
                                               answer_list=answer_list, source_list=source_list, metadata_list=metadata_list)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"插入向量库异常: {traceback.format_exc()}")
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': f'成功插入{len(question_list)}条问答对到向量库', 'data': ''})


@vector_db_bp.route('/vector_db_service/add_qa_from_template', methods=['POST'])
def add_qa_from_template():
    """从上传的模板文件添加QA对"""
    # 检查是否有文件上传
    if 'file' not in request.files:
        return jsonify({'status': 'fail', 'msg': '请上传文件', 'code': 400, 'data': ''})
    
    file = request.files['file']
    tenant_code = request.form.get('tenant_code', '')
    org_code = request.form.get('org_code', '')
    
    logger.info(f'从上传文件添加QA，请求参数: tenant_code={tenant_code}, org_code={org_code}, filename={file.filename}')
    
    if not file or file.filename == '':
        return jsonify({'status': 'fail', 'msg': '请选择文件', 'code': 400, 'data': ''})
    
    # 保存上传的文件到临时目录
    temp_file_path = None
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        temp_file_path = temp_file.name
        file.save(temp_file_path)
        temp_file.close()
        
        logger.info(f"文件保存成功，保存到: {temp_file_path}")
        
        # 加载问答对模板
        question_list, answers_list, source_list = load_qa_template(temp_file_path)
        metadata_list = [{} for q in question_list]
        
        # 插入到向量库
        is_succ, msg = insert_qa_to_collection(tenant_code, org_code, question_list=question_list,
                                               answer_list=answers_list, source_list=source_list,
                                               metadata_list=metadata_list)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
        
        logger.info(f"成功从上传文件添加{len(question_list)}条问答对到向量库")
        return jsonify({'status': 'success', 'code': 200, 'msg': f'成功插入{len(question_list)}条问答对到向量库', 'data': ''})
        
    except Exception as e:
        import traceback
        logger.exception(f"从上传文件添加问答对到向量库异常: {traceback.format_exc()}")
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.info(f"已删除临时文件: {temp_file_path}")
            except Exception as e:
                logger.warning(f"删除临时文件失败: {e}")


@vector_db_bp.route('/vector_db_service/del_qa', methods=['POST'])
def del_qa():
    data = request.get_json()
    logger.info(f'删除QA，请求参数: tenant_code={data.get("tenant_code", "")}, org_code={data.get("org_code", "")}, question_count={len(data.get("question", []))}')
    tenant_code = data.get('tenant_code', '')
    org_code = data.get('org_code', '')
    question = data.get('question', [])

    if not question:
        return jsonify({'status': 'fail', 'msg': '缺少问题参数', 'code': 400, 'data': ''})

    question_list=[q.strip() for q in question]

    try:
        is_succ, msg = delete_qa_from_collection(tenant_code, org_code, question_list=question_list)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"从全局向量库删除问答对异常: {traceback.format_exc()}")
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '从全局向量库删除问答对成功', 'data': ''})
