# MVP1 plan.md：RAG 闭环演示版

> 本文件回答“怎么做”。它根据 `spec.md` 设计技术方案、模块边界、数据流和接口实现方式。

## 技术方案

- 前端：React + Vite + TypeScript + Ant Design。
- 后端：FastAPI。
- 文本切分：LangChain `RecursiveCharacterTextSplitter`。
- Embedding：LangChain `OpenAIEmbeddings` 或 mock provider。
- LLM：LangChain `ChatOpenAI` 或 mock provider。
- 向量库：Qdrant。
- 本地部署：Docker Compose。

## 模块设计

```text
frontend/
  -> 上传文档
  -> 输入问题
  -> 展示回答和引用来源

backend/app/api/v1/endpoints/
  -> health
  -> documents
  -> chat

backend/app/services/
  -> document_loader
  -> text_splitter
  -> document_index_service
  -> rag_service

backend/app/integrations/
  -> embedding
  -> llm
  -> qdrant
```

## 数据流

```text
文档上传
  -> 后端读取文件
  -> 文档解析
  -> 文本切分
  -> Embedding
  -> Qdrant upsert

用户提问
  -> Query Embedding
  -> Qdrant 按 kb_id Top-K 检索
  -> 拼接上下文
  -> LLM 生成答案
  -> 返回 answer + sources
```

## 接口设计

```text
GET /api/v1/health
POST /api/v1/kbs/{kb_id}/documents
POST /api/v1/kbs/{kb_id}/chat
```

## 配置设计

- `QDRANT_URL`
- `QDRANT_COLLECTION`
- `EMBEDDING_PROVIDER`
- `EMBEDDING_BASE_URL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSION`
- `LLM_PROVIDER`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`

## 校验策略

- 文档格式和空文档校验放在文档解析层。
- Embedding / LLM / Qdrant 错误向上抛出，由 API 层返回明确错误。
- mock provider 用于本地冒烟测试，避免依赖外部服务。
