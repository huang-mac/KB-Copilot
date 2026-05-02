# KB Copilot

面向中小企业的通用智能知识库问答助手，支持企业文档上传、向量化索引、语义检索、RAG 问答生成和答案来源引用。

项目当前定位为可运行、可部署的通用知识库系统。后续可以扩展到 ERP、WMS、客服知识库、产品文档、企业制度、内部培训资料等场景。

## 项目目标

- 让中小企业可以把 PDF、Markdown、TXT、Word 等内部资料沉淀为可问答的知识库。
- 通过 Qdrant 向量检索找到与问题最相关的文档片段。
- 通过大模型基于检索结果生成答案，减少人工翻文档成本。
- 返回引用来源，让用户知道答案来自哪些资料片段。
- 使用 Docker Compose 降低本地部署和验证成本。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 前端 | React + Vite + TypeScript + Ant Design |
| 后端 | FastAPI |
| 向量数据库 | Qdrant |
| 大模型接口 | OpenAI-compatible API |
| Embedding | OpenAI-compatible / BGE 可扩展 |
| 文档解析 | pypdf / python-docx / markdown |
| 部署 | Docker Compose |

## 核心功能

- 知识库管理：创建和查看知识库。
- 文档上传：上传企业内部文档并构建索引。
- 文档解析：抽取文本并进行 chunk 切分。
- 向量入库：调用 Embedding 模型生成向量并写入 Qdrant。
- 智能问答：基于用户问题检索相关片段，并调用 LLM 生成答案。
- 引用溯源：展示答案依据的文件名、片段内容和相似度分数。
- 一键部署：通过 Docker Compose 启动前端、后端和 Qdrant。

## 系统架构

```text
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│ React + AntD │ ───▶  │   FastAPI    │ ───▶  │    Qdrant    │
│   Web UI     │       │  RAG Backend │       │ Vector Store │
└──────────────┘       └──────┬───────┘       └──────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ LLM/Embedding│
                       │   Provider   │
                       └──────────────┘
```

## RAG 流程

1. 用户上传文档。
2. 后端解析文档内容。
3. 文本按固定长度和 overlap 切分为多个片段。
4. Embedding 服务将片段转换为向量。
5. 向量和文档元数据写入 Qdrant。
6. 用户在前端提出问题。
7. 后端将问题转换为 query vector。
8. Qdrant 检索 Top-K 相关片段。
9. 后端把片段拼接为上下文并调用 LLM。
10. 前端展示答案和引用来源。

## 目录结构

```text
kb-copliot/
├── backend/                         # FastAPI 后端服务
│   ├── app/
│   │   ├── api/v1/endpoints/        # HTTP 路由，按版本和资源拆分
│   │   ├── core/                    # 配置、日志、异常、依赖注入
│   │   ├── domain/                  # 领域对象和值对象
│   │   ├── schemas/                 # Pydantic 请求/响应模型
│   │   ├── services/                # 文档处理、索引、检索、问答编排
│   │   ├── repositories/            # 数据访问与持久化抽象
│   │   ├── integrations/            # Qdrant、LLM、Embedding 外部集成
│   │   ├── workers/                 # 后续异步任务
│   │   └── main.py                  # FastAPI 应用入口
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/                        # React + Vite 前端
│   ├── src/
│   │   ├── api/                     # 后端接口封装
│   │   ├── assets/                  # 静态资源
│   │   ├── components/              # 通用组件
│   │   ├── features/                # 业务模块
│   │   ├── layouts/                 # 页面布局
│   │   ├── pages/                   # 路由页面
│   │   ├── router/                  # 路由配置
│   │   ├── styles/                  # 全局样式
│   │   ├── types/                   # TypeScript 类型
│   │   └── utils/                   # 工具函数
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.ts
├── docs/                            # 项目文档
├── infra/                           # Qdrant、Nginx 等基础设施配置
├── scripts/                         # 本地开发和运维脚本
├── tests/                           # 端到端或集成测试
├── docker-compose.yml               # 本地一键启动
├── .env.example                     # 环境变量示例
└── README.md
```

## 快速开始

当前已进入 MVP1：在 MVP0 后端 RAG 闭环基础上，新增 React + Vite + TypeScript + Ant Design 前端，支持通过 Web 页面上传文档、发起问答并查看引用来源。

### 1. 进入项目目录

```bash
cd kb-copliot
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

需要配置：

```env
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=kb_copilot

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

如果只是本地冒烟测试，可以临时改成：

```env
EMBEDDING_PROVIDER=mock
LLM_PROVIDER=mock
```

### 3. 启动服务

开发模式建议先分别启动后端和前端：

```bash
# 后端
cd backend
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 前端
cd frontend
npm run dev
```

如果本机 Docker 和网络代理配置正常，也可以使用 Docker Compose：

```bash
docker compose up -d
```

### 4. 访问系统

- 前端页面：`http://localhost:5173`
- 后端接口：`http://localhost:8000/docs`
- Qdrant 控制台：`http://localhost:6333/dashboard`

### 5. 上传文档

推荐直接在前端页面上传，也可以通过命令行调用：

```bash
curl -X POST "http://localhost:8000/api/v1/kbs/default/documents" \
  -F "file=@./examples/sample.md"
```

### 6. 发起问答

推荐直接在前端页面提问，也可以通过命令行调用：

```bash
curl -X POST "http://localhost:8000/api/v1/kbs/default/chat" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"这份文档主要讲了什么？\",\"top_k\":5}"
```

## MVP 版本规划

### MVP 0：最小可跑版

- FastAPI 后端。
- Qdrant 接入。
- 支持上传 `txt` 或 `md`。
- 文档切分、Embedding、向量入库。
- Top-K 向量检索。
- LLM 生成回答。
- 返回答案和引用片段。

### MVP 1：完整体验版

- React + Vite + TypeScript + Ant Design 前端。
- 知识库 ID 配置、文档上传、智能问答页面。
- 当前支持 Markdown、TXT，PDF 和 Word 放到后续增强。
- 回答展示引用来源。
- Docker Compose 启动前端、后端和 Qdrant。
- README、架构说明、接口说明、界面截图。

### MVP 1.5：中小公司可用增强版

- 多知识库管理。
- API Key 简单鉴权。
- 文档列表、删除、重新索引。
- 对话历史。
- 上传状态管理。
- BM25 + 向量检索的混合召回。
- RRF 融合排序。
- 可选 rerank。

### MVP 2：生产增强 Roadmap

- 多租户隔离。
- JWT 对接业务系统。
- Redis 会话管理。
- 异步队列处理大文档索引。
- 模型路由。
- 权限过滤。
- Prometheus 监控指标。
- Spring Boot 集成。

## API 设计草案

```text
GET    /api/v1/health
POST   /api/v1/kbs/{kb_id}/documents
POST   /api/v1/kbs/{kb_id}/chat
```

问答请求：

```json
{
  "question": "如何创建销售订单？",
  "top_k": 5
}
```

问答响应：

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

## 适用场景

- 企业制度问答。
- 产品手册问答。
- 客服 FAQ 问答。
- ERP/WMS 操作手册问答。
- 内部培训资料问答。
- 项目文档和技术文档问答。

## 文档

- [迭代文档](docs/ITERATION_PLAN.md)
- [代码学习文档](docs/CODE_LEARNING_GUIDE.md)

## 项目描述参考

> 基于 FastAPI、Qdrant、React 和大模型 API 设计并实现面向中小企业的智能知识库问答系统，支持文档上传、向量化索引、语义检索、RAG 问答生成与答案来源引用，并通过 Docker Compose 提供一键部署能力。

增强版描述：

> 引入多知识库管理、文档元数据过滤、API Key 鉴权和混合检索策略，提升企业内部制度、产品文档、FAQ、错误码等知识检索场景下的可用性和准确率。

## License

MIT
