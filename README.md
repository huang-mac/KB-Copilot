# KB Copilot

面向中小企业的通用智能知识库问答助手，支持企业文档上传、向量化索引、语义检索、RAG 问答生成和答案来源引用。

当前版本：**MVP3 实现中**

MVP3 在 MVP2 的 RAG 闭环、文档管理、对话历史和多轮会话基础上，继续补齐基础设施能力：意图路由、工具调用、SSE 流式输出、异步索引任务、混合检索入口、PDF/DOCX 解析、基础监控指标和前端索引状态展示已落地。MySQL repository 兼容和真实 rerank 仍在 MVP3 剩余范围内；重新索引仍依赖 MinIO 原文件存储，默认配置下 MinIO 未启用。

## 核心特性

### MVP3 当前特性

- **智能问答**：React + Ant Design 实现问答界面，支持历史会话管理和多轮追问。
- **文档管理**：独立管理页支持文档上传、列表查看、删除和重新索引（重新索引需启用 MinIO）。
- **RAG 链路**：使用 LangChain 进行文本切分、Embedding 调用和 LLM 调用。
- **Qdrant 向量检索**：按知识库 ID 写入和检索向量片段，返回 Top-K 相关内容。
- **答案引用来源**：回答同时返回参考文档名，按文档去重展示。
- **对话历史**：SQLite 持久化会话和消息，支持回看历史问答。
- **多轮会话**：支持新建会话、切换历史会话、围绕同一主题继续追问。
- **索引状态**：区分索引中、已完成、失败等状态，失败时展示错误原因。
- **MinIO 文件存储**：可选的原始文档对象存储；启用后可支持重新索引读取原文件。
- **本地 mock 模式**：无模型 API Key 时可使用 mock Embedding 和 mock LLM 完成冒烟测试。
- **意图路由与工具调用**：LangGraph 识别知识库问答、业务查询和澄清意图，业务查询走 mock 工具。
- **SSE 流式问答**：支持 token 级输出、中断和基于上一轮问题重新生成。
- **异步索引任务**：上传文档后创建后台任务，支持查询 queued / processing / completed / failed 状态。
- **混合检索入口**：Qdrant hybrid/RRF 检索已接入，`source_type` 会随引用来源返回。
- **PDF/DOCX 解析**：上传组件和后端解析支持 TXT、Markdown、PDF、DOCX。
- **基础监控指标**：`GET /api/v1/metrics` 返回请求、检索、LLM 耗时和错误计数等 JSON 指标。

### 下一版本方向

MVP3 剩余工作会继续补齐真实 rerank、MySQL repository 双后端、移动端响应式增强和暗色模式。API Key/JWT、多租户、权限过滤和管理员配置后移到 MVP4。

## 技术栈

- 前端：React + Vite + TypeScript + Ant Design
- 后端：Python 3.11 + FastAPI + LangChain
- 向量库：Qdrant
- 对象存储：MinIO（可选）
- 元数据：SQLite
- 模型接口：OpenAI-compatible LLM / Embedding API
- 部署：Docker Compose

## 目录结构

```text
KB-Copilot/
├── backend/            # FastAPI + LangChain RAG 后端
├── frontend/           # React 前端
├── docs/               # 阶段说明、SDD 规格和项目文档
├── .claude/            # Claude 配置、skills 和 SDD 实例规格
│   ├── skills/         # 通用 agent skills
│   └── specs/          # 每个阶段或能力的 spec.md / plan.md / tasks.md
├── .specify/           # Spec Kit 配置目录
│   ├── memory/
│   │   └── constitution.md
│   └── templates/
│       ├── spec-template.md
│       ├── plan-template.md
│       └── tasks-template.md
├── data/               # SQLite 持久化数据
├── scripts/            # 本地脚本
├── docker-compose.yml
├── .env.example
├── .env
└── README.md
```

## SDD 开发流程

KB Copilot 已建立 SDD（Spec-Driven Development）基础骨架。每个阶段或重要能力都应维护三个核心文件：

- `spec.md`：需求文档，回答“要做什么”。只定义用户故事、功能需求和验收标准，不讨论技术实现。
- `plan.md`：技术方案，回答“怎么做”。定义架构、模块、数据模型、API、关键流程和技术取舍。
- `tasks.md`：任务清单，回答“怎么一步步实现”。把方案拆成可执行、可验证、可追踪的开发任务。

推荐流程：

```text
指定：生成 spec.md 来描述需求
计划：根据 spec.md 生成 plan.md，确定技术方案
任务：将 plan.md 拆解为可执行的 tasks.md
实现：依次完成 tasks.md 中的任务，并校验是否符合 spec.md 的要求
```

实际规格实例放在 `.claude/specs/<feature>/`；模板和项目顶层规则放在 `.specify/`。

## 快速开始

### 方式一：Docker Compose

```bash
cd KB-Copilot
cp .env.example .env
# 编辑 .env 填入 API Key
docker compose up -d --build
```

访问：

- 前端页面：`http://localhost:5173`
- 后端接口：`http://localhost:8000/docs`
- Qdrant 控制台：`http://localhost:6333/dashboard`

### 方式二：手动启动

先初始化本地依赖。后端统一使用项目根目录下的 `.venv`，前端依赖安装到 `frontend/node_modules`：

```powershell
cd KB-Copilot
.\scripts\setup.ps1
```

如果只想安装后端虚拟环境依赖，可以执行：

```powershell
.\scripts\setup.ps1 -SkipFrontend
```

如果 PyPI 下载较慢，可以指定镜像源：

```powershell
.\scripts\setup.ps1 -PipIndexUrl https://pypi.tuna.tsinghua.edu.cn/simple
```

再复制环境变量：

```powershell
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

# MinIO 对象存储（可选，默认关闭）
MINIO_ENABLED=false
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=admin123456
MINIO_BUCKET=kb-copilot-documents
```

默认 `MINIO_ENABLED=false`，当前 `docker-compose.yml` 未编排 MinIO 服务。如果需要使用重新索引功能，需要先部署 MinIO 并开启上述配置。

如果只是本地冒烟测试，可以临时改成：

```env
EMBEDDING_PROVIDER=mock
LLM_PROVIDER=mock
```

还需要启动 Qdrant（如果不用 Docker）：

```powershell
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest
```

启动后端和前端：

```powershell
# 后端
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 前端
cd frontend
npm run dev
```

常用检查命令：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests
.\.venv\Scripts\python.exe -m ruff check backend
cd frontend
npm run typecheck
```

## API

```text
GET    /api/v1/health
GET    /api/v1/kbs/{kb_id}/documents
POST   /api/v1/kbs/{kb_id}/documents
DELETE /api/v1/kbs/{kb_id}/documents/{doc_id}
POST   /api/v1/kbs/{kb_id}/documents/{doc_id}/reindex
GET    /api/v1/kbs/{kb_id}/index-jobs/{job_id}
POST   /api/v1/kbs/{kb_id}/search
GET    /api/v1/kbs/{kb_id}/conversations
POST   /api/v1/kbs/{kb_id}/conversations
DELETE /api/v1/kbs/{kb_id}/conversations/{conversation_id}
GET    /api/v1/kbs/{kb_id}/conversations/{conversation_id}/messages
POST   /api/v1/kbs/{kb_id}/chat
POST   /api/v1/kbs/{kb_id}/chat/stream
POST   /api/v1/kbs/{kb_id}/chat/{conversation_id}/regenerate
POST   /api/v1/kbs/{kb_id}/feedback
POST   /api/v1/kbs/{kb_id}/suggestions
GET    /api/v1/metrics
```

## 文档

- [MVP1 当前版本说明](docs/MVP1.md)
- [MVP2 对话与文档管理增强](docs/MVP2.md)
- [MVP3 基础设施与检索编排增强](docs/MVP3.md)
- [MVP4 企业化与生产治理](docs/MVP4.md)
- MVP1 SDD：[spec](.claude/specs/mvp1/spec.md) / [plan](.claude/specs/mvp1/plan.md) / [tasks](.claude/specs/mvp1/tasks.md)
- MVP2 SDD：[spec](.claude/specs/mvp2/spec.md) / [plan](.claude/specs/mvp2/plan.md) / [tasks](.claude/specs/mvp2/tasks.md)
- [项目宪法](.specify/memory/constitution.md)
- SDD 模板：[spec](.specify/templates/spec-template.md) / [plan](.specify/templates/plan-template.md) / [tasks](.specify/templates/tasks-template.md)
- [Claude Agent 指南](CLAUDE.md)
- [初学者读懂 Agent 实现](docs/BEGINNER_AGENT_IMPLEMENTATION.md)

## License

MIT
