# 接口文档说明

本文档总结 `chat_server.py` 与 `vector_db_server.py` 暴露的 HTTP 接口，基于当前代码实现整理，方便联调与排查。默认请求/响应体为 `application/json`，除非特别说明。

## chat_server.py

- **基础信息**
  - Blueprint: `chat_bp`
  - 配置来源: `./config/config.json`
  - 依赖服务: LlmService、ChatService、Milvus、MinIO、OCR

### 1) 问答接口
- 路径: `/chat_service/chat`
- 方法: `POST`
- 描述: 进行问答，可选流式返回，支持上传文档或向量库检索。
- 请求体示例:
  ```json
  {
    "user_id": "必填",
    "session_id": "可选，留空则创建",
    "question": "必填",
    "tenant_code": "可选",
    "org_code": "可选",
    "use_vector_db": true,
    "uploaded_docs": [
      {
        "file_name": "doc.pdf",
        "file_url": "可选，仅用于来源展示",
        "content": "解析后的文本",
        "parse_success": true
      }
    ],
    "stream": true,
    "limit": 5,
    "prompt_type": ""        // "", "idea_gen", "scripts_gen"
  }
  ```
- 返回:
  - `stream=true`: SSE，字段 `content`（分片）、`done`。最后一条含 `sources`、`suggested_questions`。
  - `stream=false`: 普通 JSON，字段 `answer`、`sources`、`suggested_questions`。
- 备注:
  - 若无 session 自动创建并保存消息。
  - `uploaded_docs` 优先于向量检索；检索使用 Milvus DOC 集合，支持 tenant/org 过滤与阈值配置。

### 2) 获取会话列表
- 路径: `/chat_service/sessions`
- 方法: `GET`
- 参数: `user_id`(必填), `tenant_code`, `org_code`, `limit`(默认50)

### 3) 创建会话
- 路径: `/chat_service/session`
- 方法: `POST`
- 参数: `user_id`(必填), `session_id`(可选), `title`(可选), `tenant_code`, `org_code`

### 4) 获取会话详情
- 路径: `/chat_service/session/<session_id>`
- 方法: `GET`

### 5) 获取会话消息
- 路径: `/chat_service/session/<session_id>/messages`
- 方法: `GET`
- 参数: `limit`(默认100)

### 6) 更新会话标题
- 路径: `/chat_service/session/<session_id>/title`
- 方法: `PUT`
- 参数: JSON `title` 必填

### 7) 删除会话
- 路径: `/chat_service/session/<session_id>`
- 方法: `DELETE`

### 8) 恢复会话
- 路径: `/chat_service/session/<session_id>/restore`
- 方法: `POST`

### 9) 上传文件到 MinIO
- 路径: `/chat_service/upload`
- 方法: `POST`
- Form: `file` 单文件，返回 `file_url`, `file_name`

### 10) 上传并解析文件（多文件）
- 路径: `/chat_service/upload_and_parse`
- 方法: `POST`
- Form: `file` 或 `files`，支持多文件
- 返回: 每个文件 `file_name`, `file_url`, `content`, `parse_success`, `parse_error`（失败时）

---

## vector_db_server.py

- **基础信息**
  - Blueprint: `vector_db_bp`
  - 配置来源: `./config/config.json`
  - 依赖服务: Milvus、OCR

### 1) 创建全局素材库集合
- 路径: `/vector_db_service/new_collection`
- 方法: `POST`
- 描述: 初始化创建集合。

### 2) 删除集合数据
- 路径: `/vector_db_service/del_collection`
- 方法: `POST`
- 参数: `tenant_code`(可选), `org_code`(可选) — 用于过滤删除范围。

### 文档类
#### 3) 添加单个文档
- 路径: `/vector_db_service/add_document`
- 方法: `POST`
- 参数: `tenant_code`, `org_code`, `doc_url`(必填), `doc_name`(必填)
- 行为: 通过 URL 下载并解析，成功后入库 DOC 集合。

#### 4) 批量添加文档
- 路径: `/vector_db_service/add_multi_document`
- 方法: `POST`
- 参数: `tenant_code`, `org_code`, `multi_doc_urls`(list, 必填), `doc_names`(list, 必填，长度一致)
- 行为: 逐个解析并入库，返回成功/失败计数。

#### 5) 删除文档
- 路径: `/vector_db_service/del_document`
- 方法: `POST`
- 参数: `tenant_code`, `org_code`, `doc_name`(list, 必填)

### QA 类
#### 6) 添加 QA
- 路径: `/vector_db_service/add_qa`
- 方法: `POST`
- 参数:
  - `tenant_code`, `org_code`
  - `question`: 字符串或列表，必填
  - `answer`: 字符串或列表，必填
  - `source`: 字符串或列表，可选；列表需与问题长度一致
- 说明: question/answer 列表长度需一致。

#### 7) 从模板文件添加 QA
- 路径: `/vector_db_service/add_qa_from_template`
- 方法: `POST`
- Form: `file`(xlsx 模板), `tenant_code`, `org_code`
- 行为: 解析模板并批量入库。

#### 8) 删除 QA
- 路径: `/vector_db_service/del_qa`
- 方法: `POST`
- 参数: `tenant_code`, `org_code`, `question`(list, 必填)

### 检索类
#### 9) 从素材库检索
- 路径: `/vector_db_service/search_from_vector_db`
- 方法: `POST`
- 参数:
  - `tenant_code`, `org_code`
  - `query`(必填)
  - `collection_type`(必填，`DOC` 或 `QA`)
  - `filter_expr`(可选)
  - `limit`(默认5)
  - `use_hybrid`(默认 false)
  - `vector_similarity_threshold`, `rrf_similarity_threshold`(可选)

### 其他
#### 10) 下载 QA 模板
- 路径: `/vector_db_service/download_qa_template`
- 方法: `GET`
- 返回: `问答库模板.xlsx`

#### 11) 健康检查
- 路径: `/`
- 方法: `GET`
- 返回: `"Hello, World!"`

---

## 状态码与通用返回格式
- 成功: `{"status": "success", "code": 200, "msg": "...", "data": ...}`
- 失败: `{"status": "fail", "code": <4xx/5xx>, "msg": "...", "data": ""}`

## 注意事项
- 上传/解析依赖 MinIO 与 OCR 配置，需保证 `config.json` 中相关配置可用。
- 素材库检索使用 Milvus，阈值可通过配置或请求参数控制。
- `chat` 接口流式返回为 SSE，需要前端按事件流处理；非流式为标准 JSON。

