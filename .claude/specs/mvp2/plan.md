# MVP2 plan.md：对话与文档管理增强

> 本文件回答“怎么做”。它根据 `spec.md` 设计技术方案、模块边界、数据模型和接口实现方式。

## 技术方案

MVP2 保持 MVP1 的 FastAPI + React + Qdrant 架构，新增 SQLite 元数据存储、可选 MinIO 原文件存储，并建立 SDD 项目骨架。

- 元数据存储：SQLite。
- 原文件存储：MinIO，可选启用。
- 文档索引：同步索引。
- 问答历史：SQLite 持久化会话和消息。
- 前端页面：拆分为文档管理页和智能问答页。
- SDD 目录：`.claude/specs/<mvp>/spec.md`、`plan.md`、`tasks.md`。
- Spec Kit 目录：`.specify/memory/constitution.md` 和 `.specify/templates/`。

## 模块设计

```text
backend/app/repositories/
  -> documents.py
  -> conversations.py

backend/app/services/
  -> document_index_service.py
  -> rag_service.py

backend/app/integrations/
  -> qdrant.py
  -> minio_storage.py

frontend/src/
  -> App.tsx
  -> api/client.ts
  -> types/api.ts

.claude/specs/
  -> mvp1/
  -> mvp2/

.specify/
  -> memory/constitution.md
  -> templates/spec-template.md
  -> templates/plan-template.md
  -> templates/tasks-template.md
```

## 数据模型

### Document

- `kb_id`
- `doc_id`
- `filename`
- `chunk_count`
- `status`: `indexing`、`completed`、`failed`
- `created_at`
- `error_message`

### Conversation

- `kb_id`
- `conversation_id`
- `title`
- `created_at`
- `updated_at`

### Conversation Message

- `kb_id`
- `conversation_id`
- `message_id`
- `role`
- `content`
- `sources`
- `created_at`

## 状态流

```text
上传文档
  -> 创建 Document，status=indexing
  -> 如果启用 MinIO，保存原文件
  -> 解析文本
  -> 切分 chunk
  -> 生成 Embedding
  -> 写入 Qdrant
  -> 更新 Document，status=completed，chunk_count=N
```

```text
用户提问
  -> 如果无 conversation_id，创建 Conversation
  -> 如果有 conversation_id，加载历史消息
  -> 使用最近消息和当前问题构造检索查询
  -> RAG 生成回答
  -> 写入 user message
  -> 写入 assistant message 和 sources
  -> 返回 conversation_id、answer、sources
```

## 接口设计

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

## 兼容策略

- 默认 SQLite 保持本地启动简单。
- 默认 MinIO 关闭，因此重新索引在默认环境中返回明确错误。
- `.claude/settings.local.json` 属于本地权限配置，不进入版本控制。
- SDD 模板放入 `.specify/templates/`，实际规格实例放入 `.claude/specs/`。
