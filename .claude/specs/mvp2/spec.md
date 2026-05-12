# MVP2 spec.md：对话与文档管理增强

> 本文件回答“要做什么”。只描述需求、用户故事和验收标准，不讨论具体技术方案。

## 目标

MVP2 应在 MVP1 的 RAG 闭环基础上补齐轻量可用体验：文档可以管理，索引状态可以查看，问答可以形成历史会话，并支持围绕同一会话继续追问。同时，项目应完成 SDD 基础骨架，让后续 MVP 可以按 `spec.md / plan.md / tasks.md` 推进。

## 用户故事

- 作为知识库维护者，我希望在文档管理页上传文档，以便把资料加入知识库。
- 作为知识库维护者，我希望查看文档列表、索引状态和失败原因，以便判断文档是否可用于问答。
- 作为知识库维护者，我希望删除文档，以便同步移除不再需要的知识内容。
- 作为知识库维护者，我希望重新索引文档，以便在原文件保留时重建向量索引。
- 作为问答用户，我希望新建和切换会话，以便按主题管理问答。
- 作为问答用户，我希望继续追问，以便围绕同一主题进行多轮对话。
- 作为开发者，我希望项目具备 SDD 三件套和模板，以便后续开发有统一流程。

## EARS 需求

- 当用户进入文档管理页时，系统应展示当前知识库的文档列表。
- 当用户上传文档时，系统应创建文档记录并展示索引状态。
- 当文档索引成功时，系统应展示 `completed` 状态和 chunk 数量。
- 当文档索引失败时，系统应展示 `failed` 状态和失败原因。
- 当用户删除文档时，系统应删除文档元数据并同步删除 Qdrant 中对应 chunk。
- 当用户重新索引文档且原文件存储可用时，系统应重新解析、切分、向量化并写入 Qdrant。
- 当用户重新索引文档但原文件存储不可用时，系统应返回明确错误。
- 当用户进入问答页时，系统应展示历史会话列表。
- 当用户在已有会话中提问时，系统应携带最近历史消息参与问答。
- 当系统生成回答后，系统应保存用户问题、助手回答、引用来源和时间。
- 当项目进入 MVP3 或新增重要能力时，系统应先生成 `.claude/specs/<feature>/spec.md`、`plan.md`、`tasks.md`。

## API 需求

```text
GET    /api/v1/kbs/{kb_id}/documents
POST   /api/v1/kbs/{kb_id}/documents
DELETE /api/v1/kbs/{kb_id}/documents/{doc_id}
POST   /api/v1/kbs/{kb_id}/documents/{doc_id}/reindex
GET    /api/v1/kbs/{kb_id}/conversations
POST   /api/v1/kbs/{kb_id}/conversations
GET    /api/v1/kbs/{kb_id}/conversations/{conversation_id}/messages
POST   /api/v1/kbs/{kb_id}/chat
```

## 验收标准

- 上传文档和智能问答在两个清晰页面中完成。
- 用户可以查看文档列表、索引状态和失败原因。
- 用户可以删除文档，且 Qdrant 中对应 chunk 被删除。
- 启用 MinIO 原文件存储后，用户可以重新索引文档。
- 默认未启用 MinIO 时，重新索引返回明确错误。
- 用户可以新建会话、切换会话并继续追问。
- 历史回答可以回看引用来源。
- 项目包含 `.claude/specs/mvp1` 和 `.claude/specs/mvp2` 的三件套。
- 项目包含 `.specify/memory/constitution.md` 和 `.specify/templates/` 模板。

## 不包含

- 混合检索、RRF、rerank。
- LangGraph 意图识别和工具路由。
- 异步索引任务队列。
- MySQL 元数据存储。
- SSE token 级流式输出。
- 鉴权、多租户、权限过滤和审计日志。
