# KB Copilot

面向中小企业的通用智能知识库问答助手，支持企业文档上传、向量化索引、语义检索、RAG 问答生成和答案来源引用。

当前版本：**MVP1**

MVP1 聚焦可演示、可本地运行的 RAG 闭环：通过 Web 页面上传文档、构建向量索引、发起智能问答，并展示答案引用来源。

## 核心特性

### MVP1 当前特性

- **Web 问答界面**：React + Ant Design 实现知识库配置、文档上传和智能问答页面。
- **文档索引构建**：支持 Markdown、TXT 文档上传，后端解析文本并切分 chunk。
- **LangChain RAG 链路**：使用 LangChain 进行文本切分、Embedding 调用和 LLM 调用。
- **Qdrant 向量检索**：按知识库 ID 写入和检索向量片段，返回 Top-K 相关内容。
- **答案引用来源**：回答同时返回文件名、片段序号、相似度分数和片段内容。
- **本地 mock 模式**：无模型 API Key 时可使用 mock Embedding 和 mock LLM 完成冒烟测试。

### 下一版本方向

- MVP1.5 将重点补齐真实使用体验：上传文档和智能问答页面拆分、文档列表、删除/重新索引、上传状态、对话历史和继续追问。
- MVP2 将面向生产增强，规划 API Key/JWT、混合检索、rerank、异步索引、多租户、权限过滤和监控指标。

## 技术栈

- 前端：React + Vite + TypeScript + Ant Design
- 后端：Python 3.11 + FastAPI + LangChain
- 向量库：Qdrant
- 模型接口：OpenAI-compatible LLM / Embedding API
- 部署：Docker Compose

## 目录结构

```text
kb-copliot/
├── backend/            # FastAPI + LangChain RAG 后端
├── frontend/           # React 前端
├── docs/               # 集中项目文档
├── infra/              # 基础设施配置
├── scripts/            # 本地脚本
├── tests/              # 集成或端到端测试
├── docker-compose.yml
├── .env.example
└── README.md
```

## 快速开始

### 方式一：Docker Compose

```bash
cd kb-copliot
cp .env.example .env
docker compose up -d
```

访问：

- 前端页面：`http://localhost:5173`
- 后端接口：`http://localhost:8000/docs`
- Qdrant 控制台：`http://localhost:6333/dashboard`

### 方式二：手动启动

先复制环境变量：

```bash
cd kb-copliot
cp .env.example .env
```

配置 `.env`：

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

启动后端和前端：

```bash
# 后端
cd backend
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 前端
cd ../frontend
npm run dev
```

## API

```text
GET    /api/v1/health
POST   /api/v1/kbs/{kb_id}/documents
POST   /api/v1/kbs/{kb_id}/chat
```

## 文档

- [MVP1 当前版本说明](docs/MVP1.md)
- [MVP1.5 下一版本计划](docs/MVP1_5_PLAN.md)
- [MVP2 生产增强计划](docs/MVP2_PLAN.md)

## License

MIT
