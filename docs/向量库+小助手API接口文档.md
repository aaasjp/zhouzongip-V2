# API接口文档

## 1. 服务概述

本系统提供AI助手服务，包含对话问答服务和向量数据库管理服务。

**服务地址**: `http://0.0.0.0:8005`（默认配置，可通过config.json修改）

**服务路径**:
- 对话服务: `/chat_service/*`
- 向量库服务: `/vector_db_service/*`

## 2. 统一响应格式

所有接口统一使用以下响应格式：

### 成功响应
```json
{
  "status": "success",
  "code": 200,
  "msg": "操作成功",
  "data": {}
}
```

### 失败响应
```json
{
  "status": "fail",
  "code": 400,
  "msg": "错误信息",
  "data": ""
}
```

**状态码说明**:
- `200`: 成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

---

## 3. 对话服务接口 (chat_service)

### 3.1 问答接口

**接口地址**: `POST /chat_service/chat`

**接口说明**: 用户问答接口，支持流式和非流式输出，支持向量库检索和文档上传。

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_id | string | 是 | 用户ID |
| question | string | 是 | 用户问题 |
| session_id | string | 否 | 会话ID，不传则创建新会话 |
| tenant_code | string | 否 | 租户代码 |
| org_code | string | 否 | 组织代码 |
| use_vector_db | boolean | 否 | 是否使用向量库，默认true |
| uploaded_docs | array | 否 | 上传的文档列表，格式：`[{file_name, file_url, content, parse_success}]` |
| stream | boolean | 否 | 是否流式输出，默认true |
| limit | number | 否 | 检索结果数量，默认3 |

**请求示例**:
```json
{
  "user_id": "user123",
  "question": "什么是人工智能？",
  "session_id": "session-uuid",
  "tenant_code": "tenant001",
  "org_code": "org001",
  "use_vector_db": true,
  "stream": true,
  "limit": 5
}
```

**流式响应** (stream=true):
```
data: {"content": "人工智能是...", "done": false}

data: {"content": "完整回答", "done": true, "sources": {...}, "suggested_questions": [...]}
```

**非流式响应** (stream=false):
```json
{
  "status": "success",
  "code": 200,
  "msg": "问答成功",
  "data": {
    "session_id": "session-uuid",
    "answer": "完整回答内容",
    "sources": {
      "count": 2,
      "documents": [
        {
          "name": "文档名称",
          "url": "文档URL"
        }
      ]
    },
    "suggested_questions": [
      "延申问题1",
      "延申问题2"
    ]
  }
}
```

---

### 3.2 获取会话列表

**接口地址**: `GET /chat_service/sessions`

**接口说明**: 获取用户的会话列表。

**请求参数** (Query):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_id | string | 是 | 用户ID |
| tenant_code | string | 否 | 租户代码 |
| org_code | string | 否 | 组织代码 |
| limit | number | 否 | 返回数量限制，默认50 |

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "获取会话列表成功",
  "data": [
    {
      "session_id": "session-uuid",
      "user_id": "user123",
      "title": "会话标题",
      "created_at": "2024-01-01 12:00:00",
      "updated_at": "2024-01-01 12:30:00",
      "is_deleted": 0
    }
  ]
}
```

---

### 3.3 创建会话

**接口地址**: `POST /chat_service/session`

**接口说明**: 创建新的对话会话。

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_id | string | 是 | 用户ID |
| session_id | string | 否 | 会话ID，不传则自动生成 |
| title | string | 否 | 会话标题 |
| tenant_code | string | 否 | 租户代码 |
| org_code | string | 否 | 组织代码 |

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "创建会话成功",
  "data": {
    "session_id": "session-uuid"
  }
}
```

---

### 3.4 获取会话信息

**接口地址**: `GET /chat_service/session/<session_id>`

**接口说明**: 获取指定会话的详细信息。

**路径参数**:
- `session_id`: 会话ID

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "获取会话成功",
  "data": {
    "session_id": "session-uuid",
    "user_id": "user123",
    "title": "会话标题",
    "created_at": "2024-01-01 12:00:00",
    "updated_at": "2024-01-01 12:30:00"
  }
}
```

---

### 3.5 获取会话消息历史

**接口地址**: `GET /chat_service/session/<session_id>/messages`

**接口说明**: 获取指定会话的消息历史记录。

**路径参数**:
- `session_id`: 会话ID

**请求参数** (Query):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| limit | number | 否 | 返回数量限制，默认100 |

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "获取消息历史成功",
  "data": [
    {
      "message_id": 1,
      "session_id": "session-uuid",
      "user_id": "user123",
      "role": "user",
      "content": "用户问题",
      "created_at": "2024-01-01 12:00:00"
    },
    {
      "message_id": 2,
      "session_id": "session-uuid",
      "user_id": "user123",
      "role": "assistant",
      "content": "AI回答",
      "sources": [...],
      "suggested_questions": [...],
      "created_at": "2024-01-01 12:00:05"
    }
  ]
}
```

---

### 3.6 更新会话标题

**接口地址**: `PUT /chat_service/session/<session_id>/title`

**接口说明**: 更新指定会话的标题。

**路径参数**:
- `session_id`: 会话ID

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| title | string | 是 | 新标题 |

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "更新标题成功",
  "data": ""
}
```

---

### 3.7 删除会话

**接口地址**: `DELETE /chat_service/session/<session_id>`

**接口说明**: 删除指定会话（软删除）。

**路径参数**:
- `session_id`: 会话ID

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "删除会话成功",
  "data": ""
}
```

---

### 3.8 恢复会话

**接口地址**: `POST /chat_service/session/<session_id>/restore`

**接口说明**: 恢复已删除的会话。

**路径参数**:
- `session_id`: 会话ID

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "恢复会话成功",
  "data": ""
}
```

---

### 3.9 上传文档

**接口地址**: `POST /chat_service/upload`

**接口说明**: 上传文档到MinIO存储。

**请求参数** (FormData):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file | file | 是 | 要上传的文件 |

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "上传成功",
  "data": {
    "file_url": "http://minio-server/bucket/file.pdf",
    "file_name": "file.pdf"
  }
}
```

---

### 3.10 上传并解析文档

**接口地址**: `POST /chat_service/upload_and_parse`

**接口说明**: 上传文档到MinIO并解析文档内容（支持多文件上传）。

**请求参数** (FormData):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file | file | 是 | 要上传的文件（支持多文件，使用files[]或file[]） |

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "处理完成，成功2/2个文件",
  "data": [
    {
      "file_name": "文档1.pdf",
      "file_url": "http://minio-server/bucket/文档1.pdf",
      "content": "解析后的文档内容...",
      "parse_success": true
    },
    {
      "file_name": "文档2.pdf",
      "file_url": "http://minio-server/bucket/文档2.pdf",
      "content": "解析后的文档内容...",
      "parse_success": true
    }
  ]
}
```

**失败响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "处理完成，成功1/2个文件",
  "data": [
    {
      "file_name": "文档1.pdf",
      "file_url": "http://minio-server/bucket/文档1.pdf",
      "content": "解析后的文档内容...",
      "parse_success": true
    },
    {
      "file_name": "文档2.pdf",
      "file_url": "http://minio-server/bucket/文档2.pdf",
      "content": "",
      "parse_success": false,
      "parse_error": "解析失败原因"
    }
  ]
}
```

---

## 4. 向量库服务接口 (vector_db_service)

### 4.1 创建全局向量库

**接口地址**: `POST /vector_db_service/new_collection`

**接口说明**: 创建全局向量库集合（DOC和QA）。

**请求参数**: 无

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "成功创建全局向量库",
  "data": ""
}
```

---

### 4.2 删除向量库数据

**接口地址**: `POST /vector_db_service/del_collection`

**接口说明**: 删除向量库中的数据（可按租户和组织过滤）。

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| tenant_code | string | 否 | 租户代码，用于过滤 |
| org_code | string | 否 | 组织代码，用于过滤 |

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "成功删除向量库数据",
  "data": ""
}
```

---

### 4.3 添加文档

**接口地址**: `POST /vector_db_service/add_document`

**接口说明**: 添加单个文档到向量库。

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| tenant_code | string | 否 | 租户代码 |
| org_code | string | 否 | 组织代码 |
| doc_url | string | 是 | 文档URL（完整URL，支持http/https） |
| doc_name | string | 是 | 文档名称 |

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "成功插入文档到向量库",
  "data": ""
}
```

---

### 4.4 批量添加文档

**接口地址**: `POST /vector_db_service/add_multi_document`

**接口说明**: 批量添加多个文档到向量库。

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| tenant_code | string | 否 | 租户代码 |
| org_code | string | 否 | 组织代码 |
| multi_doc_urls | array | 是 | 文档URL列表 |
| doc_names | array | 是 | 文档名称列表（长度需与multi_doc_urls一致） |

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "插入文档到向量库成功",
  "data": ""
}
```

**部分失败响应**:
```json
{
  "status": "fail",
  "code": 400,
  "msg": "插入文档到向量库：成功[2]个,失败[1]个",
  "data": ""
}
```

---

### 4.5 删除文档

**接口地址**: `POST /vector_db_service/del_document`

**接口说明**: 从向量库删除文档。

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| tenant_code | string | 否 | 租户代码 |
| org_code | string | 否 | 组织代码 |
| doc_name | array | 是 | 文档名称列表 |

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "从全局向量库删除文档成功",
  "data": ""
}
```

---

### 4.6 向量库搜索

**接口地址**: `POST /vector_db_service/search_from_vector_db`

**接口说明**: 从向量库中搜索相关内容。

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| tenant_code | string | 否 | 租户代码 |
| org_code | string | 否 | 组织代码 |
| query | string | 是 | 搜索查询文本 |
| collection_type | string | 是 | 集合类型：'DOC' 或 'QA' |
| filter_expr | string | 否 | 过滤表达式（Milvus表达式） |
| limit | number | 否 | 返回数量，默认5 |
| use_hybrid | boolean | 否 | 是否使用混合检索，默认false |
| vector_similarity_threshold | number | 否 | 向量相似度阈值（0-1），不传则不过滤 |
| rrf_similarity_threshold | number | 否 | RRF相似度阈值（0-1），不传则不过滤 |

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "从向量库查询成功",
  "data": {
    "entities": [
      [
        {
          "id": 1,
          "content": "文档内容片段...",
          "source": "http://example.com/doc.pdf",
          "file_name": "文档名称",
          "distance": 0.85,
          "score": 0.85
        }
      ]
    ],
    "distances": [[0.85]],
    "ids": [[1]]
  }
}
```

---

### 4.7 下载问答库模板

**接口地址**: `GET /vector_db_service/download_qa_template`

**接口说明**: 下载问答库导入模板文件（Excel格式）。

**响应**: 返回Excel文件下载

---

### 4.8 添加问答对

**接口地址**: `POST /vector_db_service/add_qa`

**接口说明**: 添加问答对到向量库（支持单个或批量）。

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| tenant_code | string | 否 | 租户代码 |
| org_code | string | 否 | 组织代码 |
| question | string/array | 是 | 问题（字符串或列表） |
| answer | string/array | 是 | 答案（字符串或列表，长度需与question一致） |
| source | string/array | 否 | 来源（字符串或列表，列表长度需与question一致） |

**请求示例（单个）**:
```json
{
  "tenant_code": "tenant001",
  "org_code": "org001",
  "question": "什么是人工智能？",
  "answer": "人工智能是...",
  "source": "知识库"
}
```

**请求示例（批量）**:
```json
{
  "tenant_code": "tenant001",
  "org_code": "org001",
  "question": ["问题1", "问题2"],
  "answer": ["答案1", "答案2"],
  "source": ["来源1", "来源2"]
}
```

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "成功插入2条问答对到向量库",
  "data": ""
}
```

---

### 4.9 从模板文件添加问答对

**接口地址**: `POST /vector_db_service/add_qa_from_template`

**接口说明**: 从上传的Excel模板文件批量导入问答对。

**请求参数** (FormData):

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file | file | 是 | Excel模板文件 |
| tenant_code | string | 否 | 租户代码 |
| org_code | string | 否 | 组织代码 |

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "成功插入50条问答对到向量库",
  "data": ""
}
```

---

### 4.10 删除问答对

**接口地址**: `POST /vector_db_service/del_qa`

**接口说明**: 从向量库删除问答对。

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| tenant_code | string | 否 | 租户代码 |
| org_code | string | 否 | 组织代码 |
| question | array | 是 | 问题列表 |

**响应示例**:
```json
{
  "status": "success",
  "code": 200,
  "msg": "从全局向量库删除问答对成功",
  "data": ""
}
```

---

## 5. 错误码说明

| 错误码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误或业务逻辑错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 6. 注意事项

1. **流式响应**: 问答接口支持流式输出（Server-Sent Events），客户端需要按照SSE格式解析响应。

2. **文档解析**: 系统支持PDF、Word、Excel等格式的文档解析，通过OCR服务进行内容提取。

3. **向量库检索**: 
   - 支持纯向量检索和混合检索（向量+关键词）
   - 可通过相似度阈值过滤结果
   - 支持按租户和组织代码过滤

4. **会话管理**: 
   - 会话支持软删除，可通过恢复接口恢复
   - 会话消息会自动保存到数据库

5. **多租户支持**: 所有接口支持`tenant_code`和`org_code`参数，用于多租户数据隔离。

6. **文件上传**: 
   - 支持单文件和多文件上传
   - 文件会存储到MinIO对象存储
   - 上传后自动解析文档内容

---

## 7. 更新日志

- 2024-01-01: 初始版本接口文档

