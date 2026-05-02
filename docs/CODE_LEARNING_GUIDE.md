# 代码学习文档

## 学习目标

这份文档用于指导你从零理解并实现一个通用智能知识库问答系统。学习重点不是堆技术名词，而是掌握一个 RAG 项目从前端交互、后端接口、文档处理、向量检索到大模型生成的完整链路。

完成 MVP 1 后，你应该能够清楚讲出：

- 用户上传文档后，系统如何解析、切分、向量化并写入 Qdrant。
- 用户提问后，系统如何检索相关片段并组织 prompt。
- LLM 返回答案后，系统如何展示答案和引用来源。
- 前端如何调用后端接口完成知识库管理、上传和问答。
- Docker Compose 如何把前端、后端和 Qdrant 组合成一个可运行系统。

## 推荐目录结构

项目采用前后端分离的工程结构。后端按 API、配置、领域、服务、仓储和外部集成分层；前端按 API、页面、业务模块、布局和通用组件分层。这样后续增加混合检索、异步索引、权限过滤时，不需要重写整体结构。

```text
kb-copliot/
├── backend/                         # FastAPI 后端服务
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── api.py           # v1 路由聚合
│   │   │       └── endpoints/
│   │   │           ├── health.py
│   │   │           ├── knowledge_bases.py
│   │   │           ├── documents.py
│   │   │           └── chat.py
│   │   ├── core/                    # 配置、日志、异常、依赖注入
│   │   ├── domain/                  # 领域对象和值对象
│   │   ├── schemas/                 # Pydantic 请求/响应模型
│   │   ├── services/                # 业务流程编排
│   │   ├── repositories/            # 数据访问抽象
│   │   ├── integrations/            # Qdrant、LLM、Embedding 适配器
│   │   ├── workers/                 # 后续异步索引任务
│   │   └── main.py                  # FastAPI 应用入口
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/                        # React + Vite 前端
│   ├── src/
│   │   ├── api/                     # axios 实例和后端接口封装
│   │   ├── assets/
│   │   ├── components/              # 通用组件
│   │   ├── features/                # 知识库、文档、问答等业务模块
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── router/
│   │   ├── styles/
│   │   ├── types/
│   │   ├── utils/
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docs/
├── infra/
│   └── qdrant/
├── scripts/
├── tests/
├── docker-compose.yml
├── .env.example
└── README.md
```

## 后端学习路线

### 1. FastAPI 启动流程

优先理解：

- `app/main.py` 如何创建 FastAPI 实例。
- 路由如何通过 `include_router` 注册。
- 配置如何从 `.env` 读取。
- `/health` 如何用于健康检查。

建议先实现一个最小接口：

```python
from fastapi import FastAPI

app = FastAPI(title="KB Copilot API")

@app.get("/health")
def health_check():
    return {"status": "ok"}
```

### 2. 配置管理

重点理解为什么不要把 API Key 写死在代码里。

建议配置项：

- `APP_NAME`
- `API_PREFIX`
- `QDRANT_URL`
- `QDRANT_COLLECTION`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `EMBEDDING_MODEL`

后续可以用 `pydantic-settings` 管理配置。

### 3. 文档上传与解析

需要理解的链路：

1. 前端上传文件。
2. FastAPI 接收 `UploadFile`。
3. 根据后缀选择解析器。
4. 抽取纯文本。
5. 保存原始文档信息和文本片段元数据。

MVP 0 可以先支持 `txt` 和 `md`，MVP 1 再增加 `pdf` 和 `docx`。

### 4. 文本切分

文本切分决定检索质量。

建议先用简单规则：

- `chunk_size`: 500-800 中文字符。
- `chunk_overlap`: 80-150 中文字符。
- 保留 `filename`、`chunk_index`、`kb_id`、`doc_id`。

切分后的数据结构可以理解为：

```json
{
  "id": "chunk-id",
  "text": "切分后的文档片段",
  "metadata": {
    "kb_id": "default",
    "doc_id": "doc-001",
    "filename": "产品手册.pdf",
    "chunk_index": 0
  }
}
```

### 5. Embedding 服务

Embedding 的作用是把文本转换成向量，便于语义检索。

学习重点：

- 为什么 query 和 document 要使用同一个 embedding 模型。
- 向量维度必须和 Qdrant collection 配置一致。
- Embedding 服务应该封装成独立模块，避免业务代码直接依赖某个厂商。

建议接口设计：

```python
class EmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, query: str) -> list[float]:
        ...
```

### 6. Qdrant 向量存储

Qdrant 中最重要的概念：

- Collection：类似一组向量数据表。
- Point：一条向量记录。
- Vector：Embedding 生成的向量。
- Payload：业务元数据，例如 `kb_id`、`filename`、`chunk_index`。

你需要重点掌握：

- 创建 collection。
- 写入 points。
- 根据 query vector 搜索 Top-K。
- 使用 payload filter 限定某个知识库。

### 7. RAG 问答流程

RAG 的核心流程：

1. 接收用户问题。
2. 将问题转成 query embedding。
3. 从 Qdrant 检索相关片段。
4. 把片段拼成 context。
5. 构造 prompt。
6. 调用 LLM。
7. 返回答案和引用来源。

推荐 prompt 约束：

```text
你是一个企业知识库问答助手。
请只根据给定资料回答问题。
如果资料中没有答案，请回答“根据当前知识库资料无法确认”。
回答后列出引用来源。

资料：
{context}

问题：
{question}
```

## 前端学习路线

### 1. React + Vite 项目结构

建议页面拆分：

- `KnowledgeBasePage`: 知识库列表。
- `UploadPage`: 文档上传。
- `ChatPage`: 知识库问答。

建议公共模块：

- `api/client.ts`: axios 实例。
- `api/kb.ts`: 知识库接口。
- `api/documents.ts`: 文档接口。
- `api/chat.ts`: 问答接口。
- `types/index.ts`: 前后端共享类型声明。

### 2. Ant Design 组件

优先掌握这些组件：

- `Layout`: 页面整体布局。
- `Menu`: 左侧导航。
- `Table`: 知识库和文档列表。
- `Upload`: 文档上传。
- `Input.TextArea`: 问题输入框。
- `Button`: 操作按钮。
- `Card`: 答案和引用来源展示。
- `Spin`: 加载状态。
- `message`: 成功和错误提示。

### 3. 前后端接口约定

建议接口：

```text
GET    /api/health
GET    /api/kbs
POST   /api/kbs
POST   /api/kbs/{kb_id}/documents
GET    /api/kbs/{kb_id}/documents
DELETE /api/kbs/{kb_id}/documents/{doc_id}
POST   /api/kbs/{kb_id}/chat
```

问答请求示例：

```json
{
  "question": "如何创建销售订单？",
  "top_k": 5
}
```

问答响应示例：

```json
{
  "answer": "可以在销售管理模块中创建销售订单...",
  "sources": [
    {
      "filename": "销售操作手册.pdf",
      "chunk_index": 3,
      "score": 0.82,
      "content": "销售订单创建步骤..."
    }
  ]
}
```

## 重点代码模块说明

可以按下面方式理解项目主链路：

### 文档索引链路

用户上传文档后，后端根据文件类型解析文本，再按固定窗口和 overlap 切分为多个 chunk。系统调用 Embedding 服务将 chunk 转为向量，并把向量和文档元数据一起写入 Qdrant。元数据用于后续按知识库过滤和展示引用来源。

### 问答检索链路

用户提问时，系统先将问题转换为 query vector，然后在 Qdrant 中检索相似片段。检索结果会被拼接成上下文，再和用户问题一起传给 LLM。系统要求模型只基于上下文回答，并在响应中返回引用来源，降低幻觉风险。

### 工程化设计

项目把文档解析、文本切分、Embedding、向量库、LLM 调用、RAG 编排拆成独立 service，避免所有逻辑堆在路由层。这样后续替换 embedding 模型、切换向量数据库或增加混合检索时，改动范围更小。

## 常见问题

### 为什么选择 Qdrant？

Qdrant 是独立向量数据库，部署简单，支持 payload 过滤，适合做中小企业知识库的向量检索底座。相比纯本地嵌入式向量库，Qdrant 更容易体现生产化部署思路。

### 为什么要返回引用来源？

知识库问答不能只返回一个自然语言答案。引用来源可以让用户确认答案依据，也能降低大模型编造内容带来的风险。

### 为什么先不做多租户？

当前目标是完成一个可运行、可部署、结构清晰的通用项目。多租户、权限和 JWT 属于生产增强能力，可以放到 Roadmap，不影响 MVP 1 的核心目标。

### 为什么前端选择 Ant Design？

Ant Design 的组件风格接近企业后台，适合知识库管理、文档列表、上传和问答页面，能快速做出中小企业系统的观感。

## 学习检查清单

- 能解释 RAG 和普通 LLM 聊天的区别。
- 能解释文档为什么要切分。
- 能解释 Embedding 和向量检索的作用。
- 能解释 Qdrant collection、point、payload 的关系。
- 能解释为什么需要引用来源。
- 能独立跑通一次上传、索引、问答流程。
- 能通过 Docker Compose 启动项目依赖。
- 能看懂前端页面如何调用后端 API。
