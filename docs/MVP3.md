# MVP3 基础设施与检索编排增强

> **状态：实现中** 🔧
>
> MVP3 的目标不是继续堆叠企业权限能力，而是先把系统底座补强：用 SDD 规范驱动开发，完善索引、检索、路由、存储、流式响应和可观测性。当前已完成意图路由、工具调用、SSE、异步索引、混合检索入口、PDF/DOCX 解析、基础 metrics 与前端索引状态展示；MySQL repository 兼容和真实 rerank 仍在 MVP3 剩余范围内。鉴权、多租户、权限过滤、管理员配置等能力后移到 [MVP4](MVP4.md)。

## 版本定位

MVP3 面向基础设施升级，目标是在 MVP2 的轻量可用基础上，把 KB Copilot 从“可用的 RAG 应用”升级为“可编排、可扩展、可观测、可异步处理”的知识库问答底座。

该版本仍不追求完整企业权限体系，而是优先解决后续扩展会反复依赖的基础能力。

## 范围边界

MVP3 包含：

- **SDD 驱动开发**：先补齐规格文档，再按规格拆分接口、状态流、数据模型和验收标准。
- **LangGraph 意图识别与路由**：识别知识库问答、订单查询、闲聊/无法识别等意图，并路由到对应节点。✅ 已完成，spec 见 [intent-routing](../.claude/specs/intent-routing/)。
- **工具调用骨架**：订单查询先使用 mock 工具；预留 HTTP 工具调用实现，示例代码可注释保留。✅ 已完成。
- **混合检索**：在 Qdrant 向量检索之外增加关键词检索。✅ 已通过 Qdrant hybrid/RRF 接入。
- **RRF 融合排序**：融合向量召回和关键词召回结果。✅ 已通过 Qdrant 原生 fusion 接入。
- **可选 rerank**：对融合后的候选片段进行二次排序，可通过配置开关控制。⏳ 配置已预留，真实 rerank 调用待补。
- **MySQL 兼容**：在保留 SQLite 本地默认体验的同时，增加 MySQL 元数据存储能力。⏳ 配置已预留，repository 双后端待补。
- **异步索引**：上传文档后创建索引任务，由后台 worker 执行解析、切分、Embedding 和入库。✅ 已完成 SQLite 任务队列与后台 worker。
- **监控指标**：记录请求、索引、检索、rerank、LLM、token 和错误等基础指标。✅ 已完成 JSON metrics 基础版本。
- **SSE 流式输出**：支持 token 级打字机效果、Markdown/代码块实时渲染、中断和重新生成。✅ 已完成。

MVP3 不包含：

- API Key / JWT 鉴权。
- 多租户隔离。
- 文档级权限过滤。
- 管理员配置页。
- 模型配置中心。
- 真实 MCP 远程工具接入。
- 审计日志。

## 后端改进

- 新增 `specs` 目录，规格先行定义需求、接口、状态流、数据模型、验收标准和测试点。
- 引入 LangGraph 编排问答流程，将意图识别、检索、工具调用和回答生成拆成独立节点。
- 新增意图类型：
  - `kb_qa`：知识库问答，走 RAG 检索与回答。
  - `order_query`：订单查询，调用订单工具，MVP3 先使用 mock 数据。
  - `clarification_required`：闲聊、无法识别或信息不足时，不直接编造答案，提示用户补充问题或选择查询方向。
- 新增工具调用抽象，先实现 mock 订单查询工具，并预留 HTTP 调用 adapter。
- 增加混合检索服务，统一封装向量召回、关键词召回、RRF 融合排序和可选 rerank。
- 预留 MySQL 元数据存储配置；当前 repository 仍以 SQLite 为默认实现，MySQL 双后端待补齐。
- 引入异步索引任务模型，上传接口返回任务状态，worker 负责后台索引。
- 增加结构化日志和基础指标采集，暴露 JSON 监控查询接口。
- 新增 SSE 流式问答接口，支持 token 流、完成事件、错误事件和中断事件。

## 前端改进

- 文档上传后展示异步索引任务状态，包括排队中、索引中、已完成、失败和失败原因。
- 上传组件支持 TXT、Markdown、PDF、DOCX；后端提取纯文本后索引。
- 问答页支持 SSE token 级打字机效果。
- Markdown 和代码块支持实时渲染，流式过程中保持可读。
- 支持中断当前生成。
- 支持基于上一轮问题和上下文重新生成回答。
- 展示基础检索详情，例如召回来源、融合后排名、rerank 分数和命中文档。
- 对订单查询意图展示工具调用结果；mock 阶段展示固定格式的订单信息。
- 对闲聊、无法识别或信息不足的输入，展示补充问题提示，而不是直接进入 RAG 或工具调用。

## API 计划

```text
POST   /api/v1/kbs/{kb_id}/documents
GET    /api/v1/kbs/{kb_id}/index-jobs/{job_id}
POST   /api/v1/kbs/{kb_id}/search
POST   /api/v1/kbs/{kb_id}/chat
POST   /api/v1/kbs/{kb_id}/chat/stream
POST   /api/v1/kbs/{kb_id}/chat/{conversation_id}/regenerate
POST   /api/v1/tools/order-query
GET    /api/v1/metrics
```

`POST /api/v1/kbs/{kb_id}/documents` 在 MVP3 中调整为创建索引任务并返回任务信息，后台 worker 异步完成索引。

## 数据与配置

- `METADATA_DB_PROVIDER=sqlite|mysql`：控制元数据存储实现。
- `MYSQL_DSN`：MySQL 连接配置。
- `ASYNC_INDEX_ENABLED=true|false`：控制上传接口是否创建后台索引任务；关闭时回退同步索引。
- `RERANK_ENABLED=true|false`：控制是否启用 rerank。
- `INDEX_WORKER_POLL_INTERVAL_SECONDS`：控制索引 worker 轮询间隔。
- `INDEX_WORKER_CONCURRENCY`：控制索引 worker 并发数。
- `CHAT_STREAM_ENABLED=true|false`：控制是否启用 SSE 流式输出。
- `METRICS_ENABLED=true|false`：控制是否采集监控指标。

## LangGraph 流程

```text
用户输入
  -> 意图识别节点
    -> kb_qa
       -> 混合检索
       -> RRF 融合
       -> 可选 rerank
       -> LLM 生成答案
       -> SSE / 普通响应
    -> order_query
       -> mock 订单工具
       -> 订单结果回答
    -> clarification_required
       -> 请求用户补充问题或选择查询方向
```

HTTP 工具调用预留：

```python
# 后续接真实订单系统时启用：
# response = http_client.get(
#     f"{ORDER_SERVICE_BASE_URL}/orders/{order_id}",
#     timeout=ORDER_SERVICE_TIMEOUT,
# )
# return response.json()
```

## 验收标准

- MVP3 的主要能力都有对应 spec，且实现前先通过规格评审。
- 用户提问业务编号、错误码、产品型号等精确信息时，混合检索结果比单路向量检索更稳定。
- RRF 能融合向量召回和关键词召回，并保留召回来源信息。
- rerank 可通过配置开关启用或关闭。
- 订单查询意图能被路由到 mock 工具，并返回结构化订单结果。
- 闲聊、无法识别或信息不足的问题会要求用户补充，而不是编造答案。
- 文档上传不会阻塞 HTTP 请求，索引状态可查询。✅ SQLite 模式已完成。
- SQLite 默认体验保持可用，MySQL 模式能完成文档、会话、消息和索引任务读写。⏳ SQLite 已完成，MySQL 待补。
- 问答支持 SSE token 级输出，前端能实时渲染 Markdown 和代码块。
- 用户可以中断生成，并对上一轮回答重新生成。
- 系统能查看基础监控指标，包括请求耗时、检索耗时、LLM 耗时和错误数。✅ 已完成基础版本；rerank 耗时和 token 用量待随真实 rerank/LLM 用量统计补齐。

## 交付文档

- MVP1 SDD：[spec](../.claude/specs/mvp1/spec.md) / [plan](../.claude/specs/mvp1/plan.md) / [tasks](../.claude/specs/mvp1/tasks.md)
- MVP2 SDD：[spec](../.claude/specs/mvp2/spec.md) / [plan](../.claude/specs/mvp2/plan.md) / [tasks](../.claude/specs/mvp2/tasks.md)
- MVP3 规格将按能力拆分补充到 `.claude/specs/`，每个能力都应包含 `spec.md`、`plan.md`、`tasks.md`。

## 下一版本

MVP4 将承接企业化和生产治理能力，详见 [MVP4.md](MVP4.md)。
