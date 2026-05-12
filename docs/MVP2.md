# MVP2 对话与文档管理增强

> **状态：已完成，存在配置依赖** ✅
>
> 经代码核对，MVP2 的文档管理、会话历史、多轮问答、索引状态展示、统一错误展示和 SDD 基础骨架已落地。需要注意：重新索引依赖已启用的 MinIO 原文件存储；默认 `.env.example` 关闭 MinIO，当前 `docker-compose.yml` 也未编排 MinIO 服务，因此默认启动方式下重新索引会返回“Document storage is not enabled.”。

## 版本定位

MVP2 的目标是把 MVP1 的演示型 RAG 系统升级为对话与文档管理体验增强版，让系统更接近真实知识库问答产品。

重点不是先做复杂检索或权限体系，而是补齐用户每天会用到的基础体验：文档能管理、索引状态能看见、问答能形成历史会话，并且可以围绕同一个主题继续追问。同时，MVP2 补齐 SDD 基础目录，为 MVP3 之后的规范驱动开发打底。

## 规格文档

MVP2 的 SDD 基线文档放在 `.claude/specs/mvp2/`：

- [spec.md](../.claude/specs/mvp2/spec.md)：描述需求和验收标准。
- [plan.md](../.claude/specs/mvp2/plan.md)：描述技术方案和模块设计。
- [tasks.md](../.claude/specs/mvp2/tasks.md)：描述可执行任务和验证清单。

## 新增能力

- ✅ **页面拆分**：将文档上传/管理页与智能问答页分离，上传偏管理，问答偏使用。
- ✅ **文档列表**：展示已上传文档、所属知识库、片段数量、上传时间、索引状态和失败原因。
- ✅ **文档删除**：删除文档时同步删除 Qdrant 中对应 chunk。
- ⚠️ **重新索引**：接口和前端入口已实现；实际重建依赖 MinIO 保存原文件，默认配置未启用 MinIO。
- ✅ **上传/索引状态**：前端展示上传中状态，后端持久化索引中、已完成、失败等状态。
- ✅ **对话历史**：保存用户问题、模型回答、引用来源和时间，便于回看。
- ✅ **多轮会话**：支持新建会话、切换历史会话、围绕历史上下文继续追问。
- ✅ **问答页优化**：展示当前知识库、历史会话列表、当前会话消息流和引用来源。
- ✅ **统一错误响应**：前后端统一展示外部模型、Qdrant、文档解析等错误。
- ✅ **SDD 基础骨架**：增加 `.claude/specs/` 三件套、`.specify/` 宪法与模板，以及通用 spec/code-review skills。

## 后端改进

- ✅ 增加文档元数据和会话历史存储，先使用 SQLite。
- ✅ 在 `repositories` 层补充文档、会话和消息的持久化实现。
- ✅ 文档索引服务写入索引状态，失败时保存错误原因。
- ✅ Qdrant payload 中保留 `kb_id`、`doc_id`、`filename`、`chunk_index`、`created_at` 等字段。
- ✅ 问答服务写入会话消息，保存问题、回答、引用来源和创建时间。
- ✅ 支持基于 `conversation_id` 继续问答，保留当前会话的上下文摘要或最近消息。
- ⚠️ 原文件存储接入了 MinIO 客户端，但默认未启用，且当前 Docker Compose 未包含 MinIO 服务。
- ✅ SDD 实例规格放在 `.claude/specs/`，模板和项目宪法放在 `.specify/`。

## 前端改进

- ✅ 增加文档管理页，包含上传区域、文档列表、索引状态和文档操作。
- ✅ 智能问答页只保留问答相关功能，避免和上传管理混在一起。
- ✅ 问答页左侧展示历史会话，右侧展示当前会话消息流。
- ✅ 支持新建会话、切换会话、继续追问。
- ✅ 回答下方展示引用来源，按文档名去重显示参考文档标签。
- ✅ 文档上传、索引失败、模型调用失败时展示明确错误提示。

## SDD 结构

```text
.claude/specs/
├── mvp1/
│   ├── spec.md
│   ├── plan.md
│   └── tasks.md
└── mvp2/
    ├── spec.md
    ├── plan.md
    └── tasks.md

.specify/
├── memory/
│   └── constitution.md
└── templates/
    ├── spec-template.md
    ├── plan-template.md
    └── tasks-template.md
```

## API

```text
GET    /api/v1/kbs/{kb_id}/documents                     ✅
POST   /api/v1/kbs/{kb_id}/documents                     ✅
DELETE /api/v1/kbs/{kb_id}/documents/{doc_id}            ✅
POST   /api/v1/kbs/{kb_id}/documents/{doc_id}/reindex    ⚠️ 依赖 MinIO 原文件存储
GET    /api/v1/kbs/{kb_id}/conversations                 ✅
POST   /api/v1/kbs/{kb_id}/conversations                 ✅
GET    /api/v1/kbs/{kb_id}/conversations/{conversation_id}/messages  ✅
POST   /api/v1/kbs/{kb_id}/chat                          ✅
```

## 验收标准

- ✅ 上传文档和智能问答在两个清晰页面中完成。
- ✅ 用户可以查看文档列表、索引状态、失败原因。
- ⚠️ 用户可以删除文档；重新索引能力已接入，但默认环境需先启用并部署 MinIO。
- ✅ 上传和索引失败时能看到明确错误信息。
- ✅ 问答历史可以回看，历史回答仍能查看引用来源。
- ✅ 用户可以新建会话、切换会话，并围绕同一会话继续追问。
- ✅ README 仍保持总览，MVP2 的细节放在本文件。

## 已知差异

- 引用来源当前按文档名去重显示，不再展开 chunk 内容（用户认为全量片段在对话框内过于冗余）。
- SQLite 通过 `backend_data` Docker volume 持久化。
- MinIO 原文件存储为可选能力：代码和环境变量已接入，但默认关闭，且 `docker-compose.yml` 暂未提供 MinIO 服务。
- 当前后端文档状态为 `indexing`、`completed`、`failed`；“上传中”由前端本地 loading 状态表达，未作为后端持久状态保存。

## MVP3 前状态核对

- MVP1：已完成。
- MVP2：已完成，包括文档管理页、问答页、SQLite 元数据、会话历史、多轮问答、删除文档、错误展示和 SDD 基础骨架。
- MVP2 遗留：重新索引默认不可开箱使用，需要补齐 MinIO 部署和默认配置，或改为本地文件/数据库保存原文件。

## 下一版本

MVP3 将重点转向基础设施与检索编排增强，详见 [MVP3.md](MVP3.md)。
