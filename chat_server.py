# -*- coding: utf-8 -*-
"""
高管IP助手服务
"""
import logging
import json
import os
import uuid
import re
from typing import Optional, List, Dict, Any, Generator, Tuple
from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_cors import CORS

from llm.llm_service import LlmService
from milvus.miluvs_helper import search_from_collection
from utils.file_loader import extract_content_from_file
from chat.chat_service import ChatService
from minio_utils.minio_client import upload_file
from config.log_config import setup_chat_service_logging
from prompts.idea_gen import idea_gen_prompt
from prompts.scripts_gen import scripts_gen_prompt
try:
    from external_datasource.xiaohongshu_client import XiaoHongShuClient
except Exception:
    XiaoHongShuClient = None

# 配置对话服务日志
setup_chat_service_logging()
logger = logging.getLogger('chat_service')

# 创建 Blueprint
chat_bp = Blueprint('chat', __name__)

# 加载配置文件
with open('./config/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 初始化服务
llm_service = LlmService()
chat_service = ChatService()
ocr_config = config.get('ocr_service', {})
xhs_client = XiaoHongShuClient() if XiaoHongShuClient else None


def generate_suggested_questions(user_question: str, answer: str, llm_service: LlmService) -> List[str]:
    """基于用户问题和回答生成延申问题推荐"""
    try:
        prompt = f"""基于以下用户问题和AI回答，生成3-5个相关的延申问题推荐。要求：
1. 问题应该与用户问题相关，但角度不同或更深入
2. 问题应该简洁明了，每个问题不超过20个字
3. 只返回问题列表，每行一个问题，不要编号，不要其他说明

用户问题：{user_question}

AI回答：{answer[:500]}  # 限制回答长度避免token过多

请生成延申问题："""
        
        response = llm_service.inference(
            prompt=prompt,
            stream=False,
            generate_params={'temperature': 0.7, 'max_tokens': 2000}
        )
        
        if isinstance(response, str):
            # 解析返回的问题列表
            questions = [q.strip() for q in response.split('\n') if q.strip()]
            # 过滤掉空问题和过长的问题
            questions = [q for q in questions if len(q) <= 50 and len(q) > 0]
            return questions[:5]  # 最多返回5个
        else:
            return []
    except Exception as e:
        logger.error(f"生成延申问题失败: {e}，user_question={user_question[:100]}")
        return []


def format_sources(entities: List[Dict]) -> Dict[str, Any]:
    """格式化文档来源信息"""
    if not entities:
        return {
            'count': 0,
            'documents': []
        }
    
    # 提取唯一的文档来源
    source_map = {}
    for entity in entities:
        source_url = entity.get('source', '')
        file_name = entity.get('file_name') or entity.get('question', '未知文档')
        
        if source_url:
            if source_url not in source_map:
                source_map[source_url] = {
                    'name': file_name,
                    'url': source_url
                }
    
    documents = list(source_map.values())
    return {
        'count': len(documents),
        'documents': documents
    }


def extract_keywords_from_question(question: str, max_keywords: int = 3) -> List[str]:
    """从用户问题中简单提取关键词，用于外部资源检索"""
    if not question:
        return []
    
    # 使用中英文标点和空白分割，过滤掉过短的词
    parts = re.split(r'[，,。！？；;、\s]+', question)
    keywords: List[str] = []
    for part in parts:
        part = part.strip()
        if 1 < len(part) <= 12 and part not in keywords:
            keywords.append(part)
        if len(keywords) >= max_keywords:
            break
    
    # 兜底：如果没有有效关键词，使用截断后的原问题
    if not keywords:
        keywords = [truncate_text(question, 20)]
    return keywords


def build_xhs_context(question: str, max_items: int = 3, max_content_len: int = 300) -> Tuple[str, List[Dict[str, str]]]:
    """
    调用小红书接口并构建上下文片段
    
    Returns:
        context_text: 用于提示词的文本
        source_docs: 供前端展示的来源信息
    """
    if not xhs_client:
        return "", []
    
    keywords = extract_keywords_from_question(question)
    if not keywords:
        return "", []
    
    try:
        result = xhs_client.keyword_search(
            keywords=keywords,
            keyword_relationship="AND"
        )
        items = result.get('info_list', []) if isinstance(result, dict) else []
        if not items:
            return "", []
        
        context_blocks = []
        source_docs = []
        for item in items[:max_items]:
            data = item.get('data', {}) if isinstance(item, dict) else {}
            title = data.get('title', '') or '小红书笔记'
            content = data.get('content', '') or ''
            url = data.get('url', '') or ''
            
            snippet = truncate_text(content, max_content_len)
            block = f"标题：{title}\n内容：{snippet}"
            if url:
                block += f"\n链接：{url}"
            context_blocks.append(block)
            
            # 记录来源
            if url:
                source_docs.append({
                    'name': title,
                    'url': url
                })
        
        if not context_blocks:
            return "", []
        
        context_text = "外部资源（小红书）内容：\n" + "\n\n---外部笔记分隔---\n\n".join(context_blocks)
        return context_text, source_docs
    except Exception as e:
        logger.error(f"调用小红书接口失败: {e}，keywords={keywords}")
        return "", []


def truncate_text(text: str, max_length: int) -> str:
    """截断文本到指定长度"""
    if len(text) <= max_length:
        return text
    return text[:max_length]


def simplify_question_title(question: str, max_length: int = 20) -> str:
    """精简用户问题作为标题
    1. 去除标点符号
    2. 去除语气词（如：的、了、呢、吗、啊、呀、吧、哦等）
    3. 保留前N个字符（默认20字）
    """
    if not question:
        return ""
    
    # 去除标点符号（保留中文字符、数字、字母、空格）
    text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', question)
    
    # 去除常见的语气词和助词（只过滤真正的语气词，保留有意义的实词）
    stop_words = ['的', '了', '呢', '吗', '啊', '呀', '吧', '哦', '嗯', '呃', '哈', '啦', 
                  '嘛', '哟', '诶', '唉', '哎', '喂', '嘿', '嗨', '额']
    
    # 按字符分割，过滤语气词
    chars = list(text)
    filtered_chars = [char for char in chars if char not in stop_words]
    text = ''.join(filtered_chars)
    
    # 去除多余空格并合并
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 如果处理后为空，使用原问题（去除标点）作为后备
    if not text:
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', question)
        text = re.sub(r'\s+', ' ', text).strip()
    
    # 截断到指定长度（按字符数，不是字节数）
    if len(text) > max_length:
        text = text[:max_length]
    
    # 如果仍然为空，使用原问题的前max_length个字符（去除标点）
    if not text:
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', question)
        text = re.sub(r'\s+', ' ', text).strip()
        text = text[:max_length] if text else question[:max_length]
    
    return text


def limit_input_length(system_prompt: str, question: str, history: List[Tuple[str, str]], max_chars: int = 8192) -> Tuple[str, str, List[Tuple[str, str]]]:
    """
    限制输入总字符数不超过max_chars
    优先保留question和最近的history，然后保留system_prompt
    
    Returns:
        (system_prompt, question, history) - 截断后的内容
    """
    # 创建history的副本，避免修改原始列表
    history = list(history)
    
    # 计算question和history的字符数
    question_len = len(question)
    history_len = 0
    for q, a in history:
        history_len += len(q) + len(a) + 20  # 加上格式字符的估算
    
    # 计算总字符数
    system_len = len(system_prompt)
    total_len = system_len + question_len + history_len
    
    # 如果超过限制，需要截断
    if total_len > max_chars:
        # 预留空间：question至少保留，history尽量保留，system_prompt可以截断
        reserved_for_question = min(question_len, 1000)  # question最多1000字符
        reserved_for_history = min(history_len, 3000)  # history最多3000字符
        available_for_system = max_chars - reserved_for_question - reserved_for_history - 200  # 预留200字符缓冲
        
        # 截断question
        if question_len > reserved_for_question:
            question = truncate_text(question, reserved_for_question)
        
        # 截断history（保留最近的对话）
        if history_len > reserved_for_history:
            truncated_history = []
            current_len = 0
            for q, a in reversed(history):  # 从最近的开始
                q_len = len(q)
                a_len = len(a)
                if current_len + q_len + a_len + 20 <= reserved_for_history:
                    truncated_history.insert(0, (q, a))
                    current_len += q_len + a_len + 20
                else:
                    break
            history = truncated_history
        
        # 截断system_prompt
        if system_len > available_for_system:
            system_prompt = truncate_text(system_prompt, max(available_for_system, 100))  # 至少保留100字符
    
    return system_prompt, question, history


@chat_bp.route('/chat_service/chat', methods=['POST'])
def chat():
    """问答接口
    
    请求参数：
    - user_id: 用户ID（必填）
    - session_id: 会话ID（可选，不传则创建新会话）
    - question: 用户问题（必填）
    - tenant_code: 租户代码（可选）
    - org_code: 组织代码（可选）
    - use_vector_db: 是否使用素材库（默认true）
    - uploaded_docs: 上传的文档列表（支持多个文档），格式：[{file_name, file_url, content, parse_success}]
      - file_url: 文档URL（用于展示文档来源）
      - content: 文档内容（用于问答）
    - stream: 是否流式输出（默认true）
    - limit: 检索结果数量（默认5）
    - chat_mode: 对话模式（可选），'general'普通对话, 'idea_gen'创意生成, 'scripts_gen'脚本生成
    - use_external_resource: 是否启用外部资源（小红书），布尔值，默认false
    - theme: 主题参数（可选），支持'tech_male'、'overseas_trip'
    """
    data = request.get_json()
    user_id = data.get('user_id', '')
    session_id = data.get('session_id', '')
    question = data.get('question', '')[:100]  # 只记录前100个字符
    logger.info(f'问答请求，user_id={user_id}, session_id={session_id}, question={question}..., use_vector_db={data.get("use_vector_db", True)}, stream={data.get("stream", True)}')
    
    user_id = data.get('user_id', '')
    session_id = data.get('session_id', '')
    question = data.get('question', '')
    tenant_code = data.get('tenant_code', '')
    org_code = data.get('org_code', '')
    use_vector_db = data.get('use_vector_db', True)
    uploaded_docs = data.get('uploaded_docs', [])  # 支持多个文档，格式：[{file_name, file_url, content, parse_success}]
    if not isinstance(uploaded_docs, list):
        uploaded_docs = []
    stream = data.get('stream', True)
    limit = data.get('limit', config.get('search_limit', 3))  # 默认从配置文件读取
    chat_mode = data.get('chat_mode', 'general')  # 兼容旧字段
    use_external_resource = data.get('use_external_resource', False)
    theme = data.get('theme', '')  # 预留主题参数，目前未使用
    
    # 参数验证
    if not user_id:
        return jsonify({'status': 'fail', 'msg': '缺少用户ID', 'code': 400, 'data': ''})
    
    if not question:
        return jsonify({'status': 'fail', 'msg': '缺少问题参数', 'code': 400, 'data': ''})
    
    # 如果没有session_id，创建新会话
    if not session_id:
        session_id = str(uuid.uuid4())
        is_succ, msg = chat_service.create_session(user_id, session_id, title=question[:50], 
                                                   tenant_code=tenant_code, org_code=org_code)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': f'创建会话失败: {msg}', 'code': 400, 'data': ''})
    
    # 检查会话是否存在
    session = chat_service.get_session(session_id)
    if not session:
        return jsonify({'status': 'fail', 'msg': '会话不存在', 'code': 400, 'data': ''})
    
    # 保存用户问题
    is_succ, msg = chat_service.save_message(session_id, user_id, 'user', question)
    if not is_succ:
        logger.warning(f"保存用户消息失败: {msg}，session_id={session_id}, user_id={user_id}")
    
    # 如果session的title为"新对话"，则更新为用户第一条消息的精简版本
    if session and session.get('title') == '新对话':
        simplified_title = simplify_question_title(question, max_length=20)
        if simplified_title:
            is_succ, msg = chat_service.update_session_title(session_id, simplified_title)
            if is_succ:
                logger.info(f"自动更新会话标题: session_id={session_id}, title={simplified_title}")
            else:
                logger.warning(f"更新会话标题失败: {msg}，session_id={session_id}")
    
    # 获取对话历史
    history = chat_service.get_conversation_history(session_id)
    
    # 构建系统提示词和上下文
    context_parts = []
    sources_info = {'count': 0, 'documents': []}
    
    # 优先使用上传的文档（支持多个文档）
    if uploaded_docs and len(uploaded_docs) > 0:
        try:
            doc_contents = []
            doc_names = []
            for doc in uploaded_docs:
                if isinstance(doc, dict):
                    # 过滤出解析成功的文档
                    if doc.get('parse_success') and doc.get('content'):
                        content = doc.get('content', '')
                        file_name = doc.get('file_name', '用户上传文档')
                        file_url = doc.get('file_url', '')
                        
                        if content:
                            doc_contents.append(content)
                            doc_names.append({
                                'name': file_name,
                                'url': file_url if file_url else ''
                            })
            
            if doc_contents:
                # 合并多个文档内容，但需要控制总长度
                combined_content = "\n\n---文档分隔---\n\n".join(doc_contents)
                # 限制总长度，为其他内容预留空间
                max_doc_length = 5000  # 文档内容最多5000字符
                if len(combined_content) > max_doc_length:
                    combined_content = truncate_text(combined_content, max_doc_length)
                context_parts.append(f"参考文档内容：\n{combined_content}")
                sources_info = {
                    'count': len(doc_names),
                    'documents': doc_names
                }
                logger.info(f"使用上传文档内容，文档数量: {len(doc_names)}")
        except Exception as e:
            logger.error(f"处理上传文档失败: {e}，uploaded_docs={uploaded_docs}")
    
    # 如果使用素材库检索（且没有使用上传文档）
    elif use_vector_db and not (uploaded_docs and len(uploaded_docs) > 0):
        try:
            # 构建过滤表达式
            filter_expr = ""
            if tenant_code and org_code:
                filter_expr = f"tenant_code == '{tenant_code}' && org_code == '{org_code}'"
            elif tenant_code:
                filter_expr = f"tenant_code == '{tenant_code}'"
            elif org_code:
                filter_expr = f"org_code == '{org_code}'"
            
            # 从配置文件读取相似度阈值
            similarity_thresholds = config.get('similarity_thresholds', {})
            vector_similarity_threshold = similarity_thresholds.get('vector_similarity_threshold', 0.75)
            rrf_similarity_threshold = similarity_thresholds.get('rrf_similarity_threshold', 0.85)
            
            # 只搜索DOC集合（不传tenant_code和org_code则使用全部向量素材库）
            doc_results = search_from_collection(
                tenant_code=tenant_code if tenant_code else '',
                org_code=org_code if org_code else '',
                collection_type='DOC',
                query_list=[question],
                filter_expr=filter_expr if filter_expr else '',
                limit=limit,
                use_hybrid=True,
                vector_similarity_threshold=vector_similarity_threshold,
                rrf_similarity_threshold=rrf_similarity_threshold
            )
            
            # 只使用DOC结果
            all_entities = []
            if isinstance(doc_results, dict) and doc_results.get('entities'):
                all_entities.extend(doc_results['entities'][0] if doc_results['entities'] else [])
            
            # 格式化来源信息
            sources_info = format_sources(all_entities)
            
            # 构建上下文
            if all_entities:
                context_texts = []
                for entity in all_entities[:limit]:
                    if 'answer' in entity:
                        # QA类型
                        context_texts.append(f"问题：{entity.get('question', '')}\n答案：{entity.get('answer', '')}")
                    elif 'content' in entity:
                        # DOC类型
                        context_texts.append(f"文档内容：{entity.get('content', '')}")
                
                if context_texts:
                    context_parts.append("参考素材库内容：\n" + "\n\n".join(context_texts))
        
        except Exception as e:
            logger.error(f"素材库检索失败: {e}，tenant_code={tenant_code}, org_code={org_code}, query={question[:100]}")
            import traceback
            logger.exception(f"素材库检索异常详情: {traceback.format_exc()}")
    
    # 外部资源（小红书）检索
    external_sources = []
    if use_external_resource:
        xhs_context, xhs_sources = build_xhs_context(question)
        if xhs_context:
            context_parts.append(xhs_context)
        if xhs_sources:
            external_sources.extend(xhs_sources)
    
    # 合并来源信息（向量库/上传文档 + 外部资源）
    if external_sources:
        merged_sources = sources_info.get('documents', []) + external_sources
        # 按url去重
        seen = set()
        deduped_sources = []
        for src in merged_sources:
            url = src.get('url', '')
            if url and url in seen:
                continue
            if url:
                seen.add(url)
            deduped_sources.append(src)
        sources_info = {
            'count': len(deduped_sources),
            'documents': deduped_sources
        }
    
    # 构建系统提示词
    system_prompt = """你是一个专业的AI助手，能够基于提供的素材库内容回答用户问题。
如果素材库中有相关内容，请基于素材库内容回答；如果没有相关内容，可以使用你的通用知识回答。
回答要准确、简洁、有条理。"""
    
    # 根据chat_mode添加相应的prompt
    if chat_mode == 'idea_gen':
        system_prompt += "\n\n" + idea_gen_prompt
    elif chat_mode == 'scripts_gen':
        system_prompt += "\n\n" + scripts_gen_prompt
    
    if context_parts:
        system_prompt += "\n\n" + "\n\n".join(context_parts)
    
    # 限制输入总字符数不超过8192
    system_prompt, question, history = limit_input_length(system_prompt, question, history, max_chars=8192)
    
    # 调用LLM生成回答
    try:
        if stream:
            # 流式输出
            def generate():
                full_answer = ""
                try:
                    response_generator = llm_service.inference(
                        prompt=question,
                        system=system_prompt,
                        history=history,
                        stream=True
                    )
                    
                    for chunk in response_generator:
                        full_answer = chunk
                        yield f"data: {json.dumps({'content': chunk, 'done': False}, ensure_ascii=False)}\n\n"
                    
                    # 生成延申问题
                    suggested_questions = generate_suggested_questions(question, full_answer, llm_service)
                    
                    # 保存完整回答（包含延申问题）
                    is_succ, msg = chat_service.save_message(session_id, user_id, 'assistant', full_answer,
                                                             sources=sources_info.get('documents', []),
                                                             suggested_questions=suggested_questions)
                    if not is_succ:
                        logger.error(f"保存助手消息失败: {msg}，session_id={session_id}, user_id={user_id}")
                    
                    # 返回最终结果
                    final_data = {
                        'content': full_answer,
                        'done': True,
                        'sources': sources_info,
                        'suggested_questions': suggested_questions
                    }
                    yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
                
                except Exception as e:
                    logger.error(f"流式生成回答失败: {e}，session_id={session_id}, user_id={user_id}")
                    import traceback
                    error_msg = traceback.format_exc()
                    logger.exception(f"流式生成回答异常详情: {traceback.format_exc()}")
                    yield f"data: {json.dumps({'error': error_msg, 'done': True}, ensure_ascii=False)}\n\n"
            
            return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
        else:
            # 非流式输出
            response = llm_service.inference(
                prompt=question,
                system=system_prompt,
                history=history,
                stream=False
            )
            
            answer = response if isinstance(response, str) else ""
            
            # 生成延申问题
            suggested_questions = generate_suggested_questions(question, answer, llm_service)
            
            # 保存回答
            is_succ, msg = chat_service.save_message(session_id, user_id, 'assistant', answer,
                                                     sources=sources_info.get('documents', []),
                                                     suggested_questions=suggested_questions)
            if not is_succ:
                logger.error(f"保存助手消息失败: {msg}，session_id={session_id}, user_id={user_id}")
            
            return jsonify({
                'status': 'success',
                'code': 200,
                'msg': '问答成功',
                'data': {
                    'session_id': session_id,
                    'answer': answer,
                    'sources': sources_info,
                    'suggested_questions': suggested_questions
                }
            })
    
    except Exception as e:
        logger.error(f"生成回答失败: {e}，session_id={session_id}, user_id={user_id}")
        import traceback
        logger.exception(f"生成回答异常详情: {traceback.format_exc()}")
        return jsonify({
            'status': 'fail',
            'msg': f'生成回答失败: {traceback.format_exc()}',
            'code': 500,
            'data': ''
        })


@chat_bp.route('/chat_service/sessions', methods=['GET'])
def list_sessions():
    """获取会话列表"""
    user_id = request.args.get('user_id', '')
    tenant_code = request.args.get('tenant_code', '')
    org_code = request.args.get('org_code', '')
    limit = int(request.args.get('limit', 50))
    
    if not user_id:
        return jsonify({'status': 'fail', 'msg': '缺少用户ID', 'code': 400, 'data': ''})
    
    sessions = chat_service.list_sessions(user_id, tenant_code, org_code, limit)
    return jsonify({
        'status': 'success',
        'code': 200,
        'msg': '获取会话列表成功',
        'data': sessions
    })


@chat_bp.route('/chat_service/session', methods=['POST'])
def create_session():
    """创建新会话"""
    data = request.get_json()
    user_id = data.get('user_id', '')
    session_id = data.get('session_id', '')
    title = data.get('title', '')
    tenant_code = data.get('tenant_code', '')
    org_code = data.get('org_code', '')
    
    if not user_id:
        return jsonify({'status': 'fail', 'msg': '缺少用户ID', 'code': 400, 'data': ''})
    
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
    
    is_succ, msg = chat_service.create_session(user_id, session_id, title, tenant_code, org_code)
    if not is_succ:
        return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    
    return jsonify({
        'status': 'success',
        'code': 200,
        'msg': '创建会话成功',
        'data': {'session_id': session_id}
    })


@chat_bp.route('/chat_service/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """获取会话信息"""
    session = chat_service.get_session(session_id)
    if not session:
        return jsonify({'status': 'fail', 'msg': '会话不存在', 'code': 404, 'data': ''})
    
    return jsonify({
        'status': 'success',
        'code': 200,
        'msg': '获取会话成功',
        'data': session
    })


@chat_bp.route('/chat_service/session/<session_id>/messages', methods=['GET'])
def get_messages(session_id):
    """获取会话消息历史"""
    limit = int(request.args.get('limit', 100))
    
    from mysql_utils.mysql_helper import MySQLHelper
    mysql_helper = MySQLHelper()
    messages = mysql_helper.get_messages(session_id, limit)
    mysql_helper.close()
    
    return jsonify({
        'status': 'success',
        'code': 200,
        'msg': '获取消息历史成功',
        'data': messages
    })


@chat_bp.route('/chat_service/session/<session_id>/title', methods=['PUT'])
def update_session_title(session_id):
    """更新会话标题"""
    data = request.get_json()
    title = data.get('title', '')
    
    if not title:
        return jsonify({'status': 'fail', 'msg': '缺少标题参数', 'code': 400, 'data': ''})
    
    is_succ, msg = chat_service.update_session_title(session_id, title)
    if not is_succ:
        return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    
    return jsonify({
        'status': 'success',
        'code': 200,
        'msg': '更新标题成功',
        'data': ''
    })


@chat_bp.route('/chat_service/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """删除会话"""
    is_succ, msg = chat_service.delete_session(session_id)
    if not is_succ:
        return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    
    return jsonify({
        'status': 'success',
        'code': 200,
        'msg': '删除会话成功',
        'data': ''
    })


@chat_bp.route('/chat_service/session/<session_id>/restore', methods=['POST'])
def restore_session(session_id):
    """恢复会话"""
    is_succ, msg = chat_service.restore_session(session_id)
    if not is_succ:
        return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    
    return jsonify({
        'status': 'success',
        'code': 200,
        'msg': '恢复会话成功',
        'data': ''
    })


@chat_bp.route('/chat_service/upload', methods=['POST'])
def upload_document():
    """上传文档到MinIO"""
    if 'file' not in request.files:
        return jsonify({'status': 'fail', 'msg': '缺少文件', 'code': 400, 'data': ''})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'fail', 'msg': '文件名为空', 'code': 400, 'data': ''})
    
    try:
        # 读取文件数据
        file_data = file.read()
        file_name = file.filename
        
        # 获取文件MIME类型
        content_type = file.content_type or 'application/octet-stream'
        
        # 上传到MinIO
        file_url = upload_file(file_data, file_name, content_type)
        
        return jsonify({
            'status': 'success',
            'code': 200,
            'msg': '上传成功',
            'data': {
                'file_url': file_url,
                'file_name': file_name
            }
        })
    except Exception as e:
        logger.error(f"上传文件失败: {e}，file_name={file.filename if file else 'unknown'}")
        import traceback
        logger.exception(f"上传文件异常详情: {traceback.format_exc()}")
        return jsonify({
            'status': 'fail',
            'msg': f'上传失败: {traceback.format_exc()}',
            'code': 500,
            'data': ''
        })


@chat_bp.route('/chat_service/upload_and_parse', methods=['POST'])
def upload_and_parse_document():
    """上传文档到MinIO并解析内容（支持多文件）
    
    返回：
    - file_name: 文件名
    - file_url: 文件URL（用于展示文档来源）
    - content: 解析后的文档内容（用于问答）
    - parse_success: 是否解析成功
    """
    # 支持'file'和'files'两种参数名（Element Plus默认使用'file'）
    files = []
    if 'file' in request.files:
        files = request.files.getlist('file')
    elif 'files' in request.files:
        files = request.files.getlist('files')
    
    if not files or len(files) == 0:
        return jsonify({'status': 'fail', 'msg': '缺少文件', 'code': 400, 'data': ''})
    
    results = []
    
    for file in files:
        if file.filename == '':
            continue
        
        try:
            # 读取文件数据
            file_data = file.read()
            file_name = file.filename
            
            # 获取文件MIME类型
            content_type = file.content_type or 'application/octet-stream'
            
            # 上传到MinIO
            logger.info(f"开始上传文档: {file_name}")
            file_url = upload_file(file_data, file_name, content_type)
            
            # 解析文档内容
            logger.info(f"开始解析文档: {file_name}, URL: {file_url}")
            is_succ, doc_content = extract_content_from_file(file_url, ocr_config=ocr_config)
            
            if is_succ and doc_content:
                results.append({
                    'file_name': file_name,
                    'file_url': file_url,
                    'content': doc_content,
                    'parse_success': True
                })
                logger.info(f"文档解析成功: {file_name}，内容长度: {len(doc_content)}")
            else:
                # 解析失败
                error_msg = doc_content if isinstance(doc_content, str) else '解析失败'
                logger.warning(f"文档解析失败: {file_name}，错误: {error_msg}")
                results.append({
                    'file_name': file_name,
                    'file_url': file_url,
                    'content': '',
                    'parse_success': False,
                    'parse_error': error_msg
                })
        
        except Exception as e:
            logger.error(f"处理文件失败: {e}，file_name={file.filename if file else 'unknown'}")
            import traceback
            logger.exception(f"处理文件异常详情: {traceback.format_exc()}")
            results.append({
                'file_name': file.filename if file else 'unknown',
                'file_url': '',
                'content': '',
                'parse_success': False,
                'parse_error': f'处理失败: {str(e)}'
            })
    
    if len(results) == 0:
        return jsonify({
            'status': 'fail',
            'msg': '没有成功处理的文件',
            'code': 400,
            'data': ''
        })
    
    # 统计成功和失败的数量
    success_count = sum(1 for r in results if r.get('parse_success', False))
    total_count = len(results)
    
    return jsonify({
        'status': 'success',
        'code': 200,
        'msg': f'处理完成，成功{success_count}/{total_count}个文件',
        'data': results
    })

