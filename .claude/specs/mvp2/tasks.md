# MVP2 tasks.md：对话与文档管理增强

> 本文件回答“怎么一步步实现”。任务应能独立执行、验证，并回溯到 `spec.md`。

## 任务清单

- [x] 新增 SQLite 文档元数据 repository。
- [x] 新增 SQLite 会话和消息 repository。
- [x] 文档上传时创建文档记录并写入 `indexing` 状态。
- [x] 文档索引成功后写入 `completed` 状态和 chunk 数量。
- [x] 文档索引失败后写入 `failed` 状态和失败原因。
- [x] Qdrant payload 补充 `kb_id`、`doc_id`、`filename`、`chunk_index`、`created_at`。
- [x] 实现文档列表接口。
- [x] 实现文档删除接口，并同步删除 Qdrant chunk。
- [x] 接入可选 MinIO 原文件存储。
- [x] 实现重新索引接口。
- [x] MinIO 未启用时重新索引返回明确错误。
- [x] 实现会话列表接口。
- [x] 实现新建会话接口。
- [x] 实现会话消息查询接口。
- [x] 问答接口支持 `conversation_id`。
- [x] 问答时加载最近会话消息作为上下文。
- [x] 问答完成后写入用户消息、助手消息和引用来源。
- [x] 前端拆分智能问答页和文档管理页。
- [x] 前端文档管理页展示上传区、文档列表、索引状态、失败原因和文档操作。
- [x] 前端问答页展示历史会话、当前消息流、问题输入和引用来源。
- [x] 前端支持新建会话、切换会话和继续追问。
- [x] 前端统一展示上传、索引、模型调用等错误。
- [x] 建立 `.claude/specs/mvp1` 与 `.claude/specs/mvp2` 三件套。
- [x] 建立 `.specify/memory/constitution.md` 与 `.specify/templates/`。
- [x] 新增通用 `spec-generator` skill。
- [x] 新增通用 `code-review` skill。
- [x] README 更新为 MVP2 当前版本并说明 SDD 流程。
- [x] MVP2 文档标注实现状态和已知差异。

## 验证清单

- [x] 上传成功后文档列表展示 `completed` 和 chunk 数。
- [x] 上传失败后文档列表展示 `failed` 和失败原因。
- [x] 删除文档后文档列表不再展示该文档。
- [x] 删除文档后 Qdrant 中对应 chunk 被删除。
- [x] 默认未启用 MinIO 时，重新索引返回明确错误。
- [x] 新建会话后可以在历史会话列表中看到。
- [x] 切换会话后可以加载对应消息。
- [x] 在同一会话继续提问时，后端会带入最近历史消息。
- [x] 历史助手消息保留引用来源。
- [x] `.claude/specs/mvp1` 和 `.claude/specs/mvp2` 均包含 `spec.md`、`plan.md`、`tasks.md`。
- [x] `.specify/templates/` 包含 `spec-template.md`、`plan-template.md`、`tasks-template.md`。

## 后续遗留

- 异步索引进入 MVP3。
- MySQL 兼容进入 MVP3。
- 混合检索、RRF、rerank 进入 MVP3。
- LangGraph 意图识别和工具路由进入 MVP3。
- SSE token 级流式输出进入 MVP3。
- 鉴权、多租户、权限过滤和审计日志进入 MVP4。
