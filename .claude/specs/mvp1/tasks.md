# MVP1 tasks.md：RAG 闭环演示版

> 本文件回答“怎么一步步实现”。任务应能独立执行、验证，并回溯到 `spec.md`。

## 任务清单

- [x] 初始化 FastAPI 后端项目结构。
- [x] 初始化 React + Vite 前端项目结构。
- [x] 实现健康检查接口 `GET /api/v1/health`。
- [x] 实现 Markdown/TXT 文档解析。
- [x] 实现文本切分服务。
- [x] 实现 OpenAI-compatible Embedding 集成。
- [x] 实现 mock Embedding。
- [x] 实现 Qdrant collection 创建和 chunk upsert。
- [x] 实现文档上传接口 `POST /api/v1/kbs/{kb_id}/documents`。
- [x] 实现 Qdrant 按 `kb_id` 过滤的 Top-K 检索。
- [x] 实现 OpenAI-compatible LLM 集成。
- [x] 实现 mock LLM。
- [x] 实现问答接口 `POST /api/v1/kbs/{kb_id}/chat`。
- [x] 前端实现知识库 ID 配置、文档上传、问题输入和 Top-K 配置。
- [x] 前端展示回答和引用来源。
- [x] 编写 Dockerfile 和 Docker Compose，启动前端、后端、Qdrant。
- [x] 补充 `.env.example`。
- [x] 补充文本切分测试。
- [x] 补充 README 和 MVP1 文档。

## 验证清单

- [x] 上传 `.md` 文件可以完成索引。
- [x] 上传 `.txt` 文件可以完成索引。
- [x] 不支持的文档格式会返回错误。
- [x] 空文档会返回错误。
- [x] mock 模式下可以完成本地冒烟问答。
- [x] 问答返回 answer 和 sources。
- [x] Docker Compose 可以启动基础服务。

## 后续遗留

- 文档列表、删除、重新索引进入 MVP2。
- 会话历史和多轮追问进入 MVP2。
- 混合检索、RRF、rerank 进入 MVP3。
- 鉴权、多租户、权限过滤进入 MVP4。
