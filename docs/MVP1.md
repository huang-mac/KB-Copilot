# MVP1 当前版本说明

## 版本定位

MVP1 是 KB Copilot 的完整体验版，目标是提供一个可本地启动、可通过 Web 页面演示的知识库 RAG 系统。

当前版本重点不是生产级权限和复杂检索，而是跑通从文档上传、文本切分、向量入库、语义检索到大模型回答的完整闭环。

## 当前能力

- 前端提供知识库 ID 配置、文档上传、智能问答和引用来源展示。
- 后端提供 FastAPI 接口，包括健康检查、文档上传和问答接口。
- 支持 Markdown、TXT 文档解析。
- 使用 LangChain `RecursiveCharacterTextSplitter` 进行文本切分。
- 使用 LangChain `OpenAIEmbeddings` 调用 OpenAI-compatible Embedding 服务。
- 使用 LangChain `ChatOpenAI` 调用 OpenAI-compatible LLM 服务。
- 使用 Qdrant 存储文档片段向量和元数据。
- 问答时按知识库 ID 检索 Top-K 文档片段。
- 支持 mock Embedding 和 mock LLM，方便无 API Key 时做本地冒烟测试。
- 支持 Docker Compose 启动前端、后端和 Qdrant。

## MVP1 实现核对

- 已实现 Web 页面上传文档、配置知识库 ID、发起问答和展示引用来源。
- 已实现后端健康检查、文档上传和问答接口。
- 已实现 Markdown、TXT 文档解析和 LangChain 文本切分。
- 已实现 OpenAI-compatible Embedding / LLM 调用，并提供 mock 模式用于本地冒烟测试。
- 已实现 Qdrant 向量写入、按知识库 ID 过滤检索和 Top-K 召回。
- 已实现 Docker Compose 编排前端、后端和 Qdrant。

## RAG 流程

```text
文档上传
  -> 文本解析
  -> LangChain 文本切分
  -> LangChain Embedding
  -> Qdrant 向量入库
  -> 用户提问
  -> Query Embedding
  -> Qdrant Top-K 检索
  -> 拼接上下文
  -> LangChain ChatOpenAI 生成答案
  -> 返回答案和引用来源
```

## 后端分层

```text
backend/app/
├── api/v1/endpoints/   # HTTP 接口层
├── core/               # 配置、依赖注入、异常、日志
├── domain/             # 领域对象
├── schemas/            # 请求和响应模型
├── services/           # 文档索引、文本切分、RAG 编排
├── integrations/       # LangChain、Qdrant 等外部集成
├── repositories/       # 后续数据访问抽象
└── main.py             # FastAPI 入口
```

## API

```text
GET    /api/v1/health
POST   /api/v1/kbs/{kb_id}/documents
POST   /api/v1/kbs/{kb_id}/chat
```

上传文档：

```bash
curl -X POST "http://localhost:8000/api/v1/kbs/default/documents" \
  -F "file=@./examples/sample.md"
```

发起问答：

```bash
curl -X POST "http://localhost:8000/api/v1/kbs/default/chat" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"这份文档主要讲了什么？\",\"top_k\":5}"
```

## 环境变量

真实模型配置示例：

```env
EMBEDDING_PROVIDER=openai
EMBEDDING_BASE_URL=https://api.hunyuan.cloud.tencent.com/v1
EMBEDDING_API_KEY=your-hunyuan-api-key
EMBEDDING_MODEL=hunyuan-embedding
EMBEDDING_DIMENSION=1024

LLM_PROVIDER=openai
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=your-deepseek-api-key
LLM_MODEL=deepseek-chat
```

本地冒烟测试配置：

```env
EMBEDDING_PROVIDER=mock
LLM_PROVIDER=mock
```

注意：`EMBEDDING_DIMENSION` 必须和实际 embedding 模型输出维度一致，否则 Qdrant collection 创建后会出现向量维度不匹配。

## 当前限制

- 文档格式暂只支持 Markdown、TXT。
- 知识库 ID 由用户手动输入，暂未提供知识库列表管理。
- 文档上传和智能问答目前在同一体验流里，管理动作和使用动作还没有清晰分离。
- 文档上传后暂未提供文档列表、上传状态、删除、重新索引。
- 问答目前是一问一答，暂未保存会话历史，也不支持切换历史会话或继续追问。
- 检索策略为单路向量召回，暂未加入 BM25、RRF 和 rerank。
- 暂未加入 API Key、用户鉴权和权限过滤。

## 下一版本改进

下一版本为 MVP2，重点从“可演示”升级为“轻量可用”：

- 将文档上传/管理页和智能问答页拆分，避免上传流程和问答流程互相干扰。
- 增加文档列表，展示文件名、chunk 数、上传时间、索引状态和失败原因。
- 支持删除文档和重新索引文档。
- 增加上传状态和索引状态，让用户知道文档是否已可用于问答。
- 增加对话历史，支持新建会话、切换历史会话和继续追问。
- 保留引用来源回看，方便从历史回答追溯到命中文档片段。
