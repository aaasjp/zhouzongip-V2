from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection, db,SearchResult,Hits,Hit
import json
from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
import torch
from config.log_config_vector_db import setup_logging

import logging
setup_logging()
logger = logging.getLogger(__name__)

DOC_FROM_QA_SOURCE = 'CONVERT_FROM_QA'

##加载配置文件
with open('./config/config.json', 'r') as f:
    config = json.load(f)

# 检测CUDA是否可用
try:
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f"检测到设备: {device}")
except ImportError:
    device = 'cpu'
    logger.warning("未安装torch，使用CPU设备")

embedding_model = HuggingFaceBgeEmbeddings(
    model_name=config['embedding_model_path'],
    model_kwargs={'device': device},
    encode_kwargs={'normalize_embeddings': True}  # set True to compute cosine similarity
)


def qa_collection_schema():
    fields = [
        FieldSchema(name='id', dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name='question', dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name='answer', dtype=DataType.VARCHAR, max_length=20000),
        FieldSchema(name='source', dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name='embedding', dtype=DataType.FLOAT_VECTOR, dim=1024),
        FieldSchema(name='metadata', dtype=DataType.JSON, max_length=2000)
    ]
    return CollectionSchema(fields=fields)


def doc_collection_schema():
    fields = [
        FieldSchema(name='id', dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name='file_name', dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name='block_id', dtype=DataType.INT64, is_primary=False),
        FieldSchema(name='content', dtype=DataType.VARCHAR, max_length=20000),
        FieldSchema(name='source', dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name='embedding', dtype=DataType.FLOAT_VECTOR, dim=1024),
        FieldSchema(name='metadata', dtype=DataType.JSON, max_length=2000)
    ]
    return CollectionSchema(fields=fields)


##此方法需要调用者保持tenant_code是唯一的，否则会覆盖掉其他租户的知识库
def create_collection(tenant_code, collection_name):
    logger.info(f"调用方法:create_collection，参数为:tenant_code={tenant_code}, collection_name={collection_name}")

    config_name_convention_dic = config['name_convention']
    config_milvus_dic = config['milvus']
    index_params = config['index_params']

    db_name = config_name_convention_dic['database_prefix'] + str(tenant_code)
    collection_qa_name = config_name_convention_dic['collection_qa_prefix'] + str(collection_name)
    collection_doc_name = config_name_convention_dic['collection_doc_prefix'] + str(collection_name)

    logger.debug(f"db_name={db_name}, collection_qa_name={collection_qa_name}, collection_doc_name={collection_doc_name}")

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'])
    ##如果db不存在就创建
    if db_name not in db.list_database():
        db.create_database(db_name)

    ##链接到db
    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'], db_name=db_name)
    exist_collection_list = utility.list_collections()

    for cname in [collection_qa_name, collection_doc_name]:
        if cname in exist_collection_list:
            logger.error(f"向量库[{collection_name}:{cname}]已存在,请删除[{collection_name}]再创建")
            return False, f"向量库[{collection_name}:{cname}]已存在,请删除[{collection_name}]再创建"

    ##默认创建qa和doc两个库
    collection = Collection(collection_qa_name, schema=qa_collection_schema())
    collection.create_index(field_name="embedding", index_params=index_params)
    collection.load()
    logger.info(f"向量库[{collection_qa_name}]创建成功")

    collection = Collection(collection_doc_name, schema=doc_collection_schema())
    collection.create_index(field_name="embedding", index_params=index_params)
    collection.load()
    logger.info(f"向量库[{collection_doc_name}]创建成功")

    logger.info(f"向量库[{collection_name}]下的问答库和文档库创建成功")
    return True, f"向量库[{collection_name}]下的问答库和文档库创建成功"


def delete_collection(tenant_code, collection_name):
    logger.info(f"调用方法:delete_collection，参数为:tenant_code={tenant_code}, collection_name={collection_name}")

    config_name_convention_dic = config['name_convention']
    config_milvus_dic = config['milvus']

    db_name = config_name_convention_dic['database_prefix'] + str(tenant_code)
    collection_qa_name = config_name_convention_dic['collection_qa_prefix'] + str(collection_name)
    collection_doc_name = config_name_convention_dic['collection_doc_prefix'] + str(collection_name)

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'])
    if db_name not in db.list_database():
        logger.error(f"不存在tenant_code={tenant_code}的向量库信息")
        return False, f"不存在tenant_code={tenant_code}的向量库信息"

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'], db_name=db_name)
    exist_collection_list = utility.list_collections()

    if collection_qa_name in exist_collection_list:
        utility.drop_collection(collection_qa_name)
        logger.info(f"向量库[{collection_qa_name}]删除成功")

    if collection_doc_name in exist_collection_list:
        utility.drop_collection(collection_doc_name)
        logger.info(f"向量库[{collection_doc_name}]删除成功")

    logger.info(f"向量库[{collection_name}]下的问答库和文档库删除成功")
    return True, f"向量库[{collection_name}]下的问答库和文档库删除成功"


def insert_qa_to_collection(tenant_code, collection_name, question_list, answer_list, source_list, metadata_list):
    logger.info(f"调用方法:insert_qa_to_collection，参数为:tenant_code={tenant_code}, collection_name={collection_name}, 问答对数量={len(question_list)}")
    config_name_convention_dic = config['name_convention']
    config_milvus_dic = config['milvus']

    db_name = config_name_convention_dic['database_prefix'] + str(tenant_code)
    collection_qa_name = config_name_convention_dic['collection_qa_prefix'] + str(collection_name)
    collection_doc_name = config_name_convention_dic['collection_doc_prefix'] + str(collection_name)

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'])
    if db_name not in db.list_database():
        logger.error(f"不存在tenant_code={tenant_code}的向量库信息")
        return False, f"不存在tenant_code={tenant_code}的向量库信息"

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'], db_name=db_name)
    exist_collection_list = utility.list_collections()

    if collection_qa_name not in exist_collection_list:
        logger.error(f"向量库[{collection_name}:{collection_qa_name}]问答库不存在")
        return False, f"向量库[{collection_name}:{collection_qa_name}]问答库不存在"

    if collection_doc_name not in exist_collection_list:
        logger.error(f"向量库[{collection_name}:{collection_doc_name}不存在")
        return False, f"向量库[{collection_name}:{collection_doc_name}不存在"

    collection = Collection(name=collection_qa_name)

    exist_quest_count = 0
    to_delete_indices = []
    for i in range(len(question_list)):
        q = question_list[i]
        res = collection.query(f"question == '{q}'")
        if len(res) > 0:
            exist_quest_count += 1
            to_delete_indices.append(i)
            logger.debug(f'新增问答对：问题=[{q}] 已经存在，不进行插入')

    question_list_to_insert = [x for i, x in enumerate(question_list) if i not in to_delete_indices]
    answer_list_to_insert = [x for i, x in enumerate(answer_list) if i not in to_delete_indices]
    source_list_to_insert = [x for i, x in enumerate(source_list) if i not in to_delete_indices]
    metadata_list_to_insert = [x for i, x in enumerate(metadata_list) if i not in to_delete_indices]

    if len(question_list_to_insert) == 0:
        logger.info(f"新增问答对0条，已经存在而无需新增的问答对{exist_quest_count}条")
        return True, f"新增问答对0条，已经存在而无需新增的问答对{exist_quest_count}条"

    question_embeddings = embedding_model.embed_documents(question_list_to_insert)
    data = [question_list_to_insert, answer_list_to_insert, source_list_to_insert, question_embeddings,
            metadata_list_to_insert]
    collection.insert(data=data)
    collection.flush()
    logger.info(f'插入向量库[{collection_name}]成功，新增问答对{len(question_list_to_insert)}条，已经存在而无需新增的问答对{exist_quest_count}条')

    if config['convert_qa_to_doc'] == 'yes':
        logger.debug('convert_qa_to_doc==yes，开始将问答对转换为文档')
        doc_name_list = []
        doc_content_list = []
        doc_source_list = []
        for i in range(len(question_list)):
            doc_name_list.append(question_list[i])
            doc_content_list.append(f'{question_list[i]}\n{answer_list[i]}')
            doc_source_list.append(DOC_FROM_QA_SOURCE)
        is_success, msg = insert_docs_to_collection(tenant_code, collection_name, doc_name_list, doc_content_list,
                                                    doc_source_list, metadata_list)
        if not is_success:
            logger.error(f'{msg}')
            return False, msg

    return True, f"插入向量库[{collection_name}]成功，新增问答对{len(question_list)}条，已经存在而无需新增的问答对{exist_quest_count}条"


def upsert_qa_to_collection(tenant_code, collection_name, question_list, answer_list, source_list, metadata_list):
    logger.info(f"调用方法:upsert_qa_to_collection，参数为:tenant_code={tenant_code}, collection_name={collection_name}, 问答对数量={len(question_list)}")
    config_name_convention_dic = config['name_convention']
    config_milvus_dic = config['milvus']

    db_name = config_name_convention_dic['database_prefix'] + str(tenant_code)
    collection_qa_name = config_name_convention_dic['collection_qa_prefix'] + str(collection_name)
    collection_doc_name = config_name_convention_dic['collection_doc_prefix'] + str(collection_name)

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'])
    if db_name not in db.list_database():
        logger.error(f"不存在tenant_code={tenant_code}的向量库信息")
        return False, '不存在tenant_code={tenant_code}的向量库信息'

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'], db_name=db_name)
    exist_collection_list = utility.list_collections()

    if collection_qa_name not in exist_collection_list:
        logger.error(f"向量库[{collection_name}:{collection_qa_name}]问答库不存在")
        return False, f"向量库[{collection_name}:{collection_qa_name}]问答库不存在"

    if collection_doc_name not in exist_collection_list:
        logger.error(f"向量库[{collection_name}:{collection_doc_name}不存在")
        return False, f"向量库[{collection_name}:{collection_doc_name}不存在"

    is_succ, msg = delete_qa_from_collection(tenant_code, collection_name, question_list)
    if not is_succ:
        logger.error(f"更新问答对:先删除已存在的问答对出错:{msg}")
        return False, f"更新问答对:先删除已存在的问答对出错:{msg}"

    is_succ, msg = insert_qa_to_collection(tenant_code, collection_name, question_list, answer_list, source_list,
                                           metadata_list)
    if not is_succ:
        logger.error(f"更新问答对：删除之后插入问答对出错:{msg}")
        return False, f"更新问答对：删除之后插入问答对出错:{msg}"

    logger.info(f'更新问答对向量库[{collection_name}]成功')
    return True, f'更新问答对向量库[{collection_name}]成功'


def insert_docs_to_collection(tenant_code, collection_name, doc_name_list, doc_content_list, source_list,
                              metadata_list):
    logger.info(f"调用方法:insert_doc_to_collection，参数为:tenant_code={tenant_code}, collection_name={collection_name}, 文档数量={len(doc_name_list)}")
    config_name_convention_dic = config['name_convention']
    config_milvus_dic = config['milvus']

    db_name = config_name_convention_dic['database_prefix'] + str(tenant_code)
    collection_doc_name = config_name_convention_dic['collection_doc_prefix'] + str(collection_name)

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'])
    if db_name not in db.list_database():
        logger.error(f"不存在tenant_code={tenant_code}的向量库信息")
        return False, '不存在tenant_code={tenant_code}的向量库信息'

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'], db_name=db_name)
    exist_collection_list = utility.list_collections()
    if collection_doc_name not in exist_collection_list:
        logger.error(f"向量库[{collection_name}:{collection_doc_name}不存在")
        return False, f"向量库[{collection_name}:{collection_doc_name}不存在"

    collection = Collection(name=collection_doc_name)
    exist_doc_count = 0
    to_delete_indices = []
    for i in range(len(doc_name_list)):
        dname = doc_name_list[i]
        res = collection.query(f"file_name == '{dname}'")
        if len(res) > 0:
            exist_doc_count += 1
            to_delete_indices.append(i)
            logger.debug(f'新增文档：file_name=[{dname}] 已经存在，不进行插入')

    doc_name_list = [x for i, x in enumerate(doc_name_list) if i not in to_delete_indices]
    doc_content_list = [x for i, x in enumerate(doc_content_list) if i not in to_delete_indices]
    source_list = [x for i, x in enumerate(source_list) if i not in to_delete_indices]
    metadata_list = [x for i, x in enumerate(metadata_list) if i not in to_delete_indices]

    if len(doc_name_list) == 0:
        logger.info(f'新增文档0条，已经存在而无需新增的文档{exist_doc_count}条')
        return True, f'新增文档0条，已经存在而无需新增的文档{exist_doc_count}条'

    new_doc_name_list = []
    new_doc_block_id_list = []
    new_doc_content_block_list = []
    new_source_list = []
    new_metadata_list = []

    CHUNK_LEN = config['split']['chunk_size']
    OVERLAP = config['split']['overlap']

    text_spliter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n"],
        chunk_size=CHUNK_LEN, chunk_overlap=OVERLAP,
        length_function=len, keep_separator=False
    )
    for i in range(len(doc_content_list)):
        cnt = doc_content_list[i]
        dname = doc_name_list[i]
        dsource = source_list[i]
        metadata = metadata_list[i]

        blocks = text_spliter.split_text(cnt)
        for k in range(len(blocks)):
            new_doc_name_list.append(dname)
            new_doc_block_id_list.append(k)
            new_doc_content_block_list.append(blocks[k])
            new_source_list.append(dsource)
            new_metadata_list.append(metadata)

    block_embeddings = embedding_model.embed_documents(new_doc_content_block_list)
    logger.debug(f"文档分块完成，共{len(new_doc_content_block_list)}个块，开始生成向量嵌入")
    data = [new_doc_name_list, new_doc_block_id_list, new_doc_content_block_list, new_source_list, block_embeddings,
            new_metadata_list]
    collection.insert(data=data)
    collection.flush()
    logger.info(f"插入docs到向量库[{collection_doc_name}]成功,新增文档{len(doc_name_list)}条，已经存在而无需新增的文档{exist_doc_count}条，共插入{len(new_doc_content_block_list)}个文档块")
    return True, f"插入docs到向量库[{collection_doc_name}]成功,新增文档{len(doc_name_list)}条，已经存在而无需新增的文档{exist_doc_count}条"


def delete_qa_from_collection(tenant_code, collection_name, question_list):
    logger.info(f"调用方法:delete_qa_from_collection，参数为:tenant_code={tenant_code}, collection_name={collection_name}, 待删除问题数量={len(question_list)}")
    logger.debug(f'待删除的问题列表: {question_list}')

    config_name_convention_dic = config['name_convention']
    config_milvus_dic = config['milvus']

    db_name = config_name_convention_dic['database_prefix'] + str(tenant_code)
    collection_qa_name = config_name_convention_dic['collection_qa_prefix'] + str(collection_name)
    collection_doc_name = config_name_convention_dic['collection_doc_prefix'] + str(collection_name)

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'])
    if db_name not in db.list_database():
        logger.error(f"不存在tenant_code={tenant_code}的向量库信息")
        return False, '不存在tenant_code={tenant_code}的向量库信息'

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'], db_name=db_name)
    exist_collection_list = utility.list_collections()
    if collection_qa_name not in exist_collection_list:
        logger.error(f"向量库[{collection_name}:{collection_qa_name}不存在")
        return False, f"向量库[{collection_name}:{collection_qa_name}不存在"

    if collection_doc_name not in exist_collection_list:
        logger.error(f"向量库[{collection_name}:{collection_doc_name}不存在")
        return False, f"向量库[{collection_name}:{collection_doc_name}不存在"

    collection = Collection(collection_qa_name)
    for question in question_list:
        escaped_question=question.replace("'", "\\'")
        collection.delete(f"question == '{escaped_question}'")
    collection.flush()

    logger.info(f"从向量库[{collection_qa_name}]删除问答对成功，共删除{len(question_list)}条")

    if config['convert_qa_to_doc'] == 'yes':
        logger.debug('convert_qa_to_doc==yes，开始删除对应的文档')
        is_succ, msg = delete_docs_from_collection(tenant_code, collection_name, doc_name_list=question_list)
        if not is_succ:
            logger.error(f"删除问答对对应的文档失败: {msg}")
            return False, msg

    logger.info(f"从向量库[{collection_name}]删除问答对成功")
    return True, f"从向量库[{collection_name}]删除问答对成功"


def delete_docs_from_collection(tenant_code, collection_name, doc_name_list):
    logger.info(f"调用方法:delete_docs_from_collection，参数为:tenant_code={tenant_code}, collection_name={collection_name}, 待删除文档数量={len(doc_name_list)}")
    logger.debug(f'待删除的文档列表: {doc_name_list}')

    config_name_convention_dic = config['name_convention']
    config_milvus_dic = config['milvus']

    db_name = config_name_convention_dic['database_prefix'] + str(tenant_code)
    collection_doc_name = config_name_convention_dic['collection_doc_prefix'] + str(collection_name)

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'])
    if db_name not in db.list_database():
        logger.error(f"不存在tenant_code={tenant_code}的向量库信息")
        return False, '不存在tenant_code={tenant_code}的向量库信息'

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'], db_name=db_name)
    exist_collection_list = utility.list_collections()
    if collection_doc_name not in exist_collection_list:
        logger.error(f"向量库[{collection_name}:{collection_doc_name}不存在")
        return False, f"向量库[{collection_name}:{collection_doc_name}不存在"

    collection = Collection(collection_doc_name)
    for file_name in doc_name_list:
        collection.delete(f"file_name == '{file_name}'")
    collection.flush()

    logger.info(f"从向量库[{collection_doc_name}]删除文档成功，共删除{len(doc_name_list)}个文档")
    return True, f"从向量库[{collection_doc_name}]删除文档成功"


def search_from_collection(tenant_code, collection_name, collection_type, query_list, filter_expr, limit=5):
    logger.info(f"调用方法:search_from_collection，参数为:tenant_code={tenant_code}, collection_name={collection_name}, collection_type={collection_type}, 查询数量={len(query_list)}, limit={limit}")
    logger.debug(f"查询内容: {query_list}, 过滤条件: {filter_expr}")
    config_name_convention_dic = config['name_convention']
    config_milvus_dic = config['milvus']

    assert collection_type in ('QA', 'DOC'), 'collection_type必须是[QA,DOC]之一'

    db_name = config_name_convention_dic['database_prefix'] + str(tenant_code)
    collection_qa_name = config_name_convention_dic['collection_qa_prefix'] + str(collection_name)
    collection_doc_name = config_name_convention_dic['collection_doc_prefix'] + str(collection_name)

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'])
    if db_name not in db.list_database():
        logger.error(f"不存在tenant_code={tenant_code}的向量库信息")
        return False, '不存在tenant_code={tenant_code}的向量库信息'

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'], db_name=db_name)

    if collection_type == 'QA':
        exist_collection_list = utility.list_collections()
        if collection_qa_name not in exist_collection_list:
            logger.error(f"向量库[{collection_name}:{collection_qa_name}不存在")
            return False, f"向量库[{collection_name}:{collection_qa_name}不存在"
        collection = Collection(collection_qa_name)
    else:
        exist_collection_list = utility.list_collections()
        if collection_doc_name not in exist_collection_list:
            logger.error(f"向量库[{collection_name}:{collection_doc_name}不存在")
            return False, f"向量库[{collection_name}:{collection_doc_name}不存在"
        collection = Collection(collection_doc_name)

    fields = [f.name for f in collection.schema.fields if f.name != 'embedding']
    logger.debug(f"开始生成查询向量嵌入，查询数量={len(query_list)}")
    query_embeddings = embedding_model.embed_documents(query_list)
    logger.debug(f"查询向量嵌入生成完成，开始搜索")


    res = collection.search(
        data=query_embeddings,
        anns_field="embedding",
        param=config['search_params'],
        limit=limit,
        expr=filter_expr,
        output_fields=fields
    )

    ids=[]
    distances=[]
    entities=[]

    for hits in res:
        ids.append(hits.ids)
        distances.append(hits.distances)
        ents=[]

        for hit in hits:
            ent={}
            for f in fields:
                ent[f]=hit.get(f)
            ent['score']=hit.score
            ents.append(ent)
        entities.append(ents)

    ret_dic={
        "ids":ids,
        "distances":distances,
        "entities":entities
    }
    logger.debug(f'搜索结果: {json.dumps(ret_dic,ensure_ascii=False,indent=2)}')
    logger.info(f'从向量库[{collection_name}]搜索完成，返回{len(ids)}个查询结果')
    return ret_dic
