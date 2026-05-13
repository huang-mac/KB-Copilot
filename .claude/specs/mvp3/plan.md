a# MVP3 plan.md

> 本文件回答"怎么做"。它根据 `spec.md` 设计技术方案、模块边界、数据模型、接口和验证策略。
>
> 已有子 plan 直接引用，不重复：
> - SSE 流式输出：见 `.claude/specs/sse-streaming/plan.md`
> - 意图识别与工具调用：见 `.claude/specs/intent-routing/plan.md`

## 技术方案

### 总览

| 层 | 关键变更 |
|---|---|
| 前端 | 聊天面板重构（ChatPanel 组件）、主题切换、响应式布局、auto-scroll hook、追问建议、反馈/复制按钮、引用展开、拖拽上传 |
| 后端 | 混合检索服务、异步索引 worker、MySQL repository、metrics 中间件、会话删除 API、反馈 API、追问建议 API、PDF/DOCX 解析 |
| 存储 | Qdrant（不变）、SQLite/MySQL 双 repository、索引任务表、反馈表 |
| 外部集成 | PDF 解析（PyMuPDF）、DOCX 解析（python-docx）、Rerank API（可选） |
| 配置 | 新增 `METADATA_DB_PROVIDER`、`MYSQL_DSN`、`RERANK_ENABLED`、`METRICS_ENABLED` |

### 已有模块复用

- `graph/` — LangGraph 编排已实现，MVP3 增强 `kb_qa_node` 使其调用混合检索
- `tools/` — 工具抽象层已实现，继续作为 order_query 的 mock 实现
- `useChatStream` hook — 已实现，MVP3 扩展为包含追问建议和反馈状态
- 现有 endpoints（chat、documents、conversations）— 在已有基础上增量修改

## 模块设计

```
backend/app/
├── services/
│   ├── rag_service.py              # 修改：kb_qa_node 调用混合检索
│   ├── hybrid_search_service.py    # 新增：混合检索 + RRF + 可选 rerank
│   ├── keyword_search_service.py   # 新增：基于 jieba + SQLite FTS 的关键词检索
│   └── document_loader.py          # 修改：新增 PDF/DOCX 解析
├── repositories/
│   ├── base.py                     # 新增：Repository 抽象基类
│   ├── conversations.py            # 修改：实现 MySQL 版本
│   ├── documents.py                # 修改：实现 MySQL 版本
│   └── index_jobs.py               # 新增：索引任务 CRUD
├── workers/
│   ├── index_worker.py             # 新增：后台异步索引 worker
│   └── __init__.py
├── core/
│   ├── config.py                   # 修改：新增配置项
│   ├── metrics.py                  # 新增：指标收集 + GET /metrics
│   └── database.py                 # 修改：SQLite/MySQL 双驱动
├── domain/
│   ├── index_jobs.py               # 新增：IndexJob 模型
│   └── feedback.py                 # 新增：Feedback 模型
├── schemas/
│   ├── search.py                   # 新增：SearchRequest/Response
│   ├── index_jobs.py               # 新增：IndexJobResponse
│   ├── feedback.py                 # 新增：FeedbackRequest
│   └── suggestions.py              # 新增：SuggestionsRequest/Response
├── api/v1/endpoints/
│   ├── chat.py                     # 修改：集成混合检索、追问建议
│   ├── conversations.py            # 修改：新增 DELETE 端点
│   ├── search.py                   # 新增：POST /search
│   ├── index_jobs.py               # 新增：GET /index-jobs/{id}
│   ├── feedback.py                 # 新增：POST /feedback
│   └── suggestions.py              # 新增：POST /suggestions
├── graph/
│   └── nodes.py                    # 修改：kb_qa_node 使用混合检索
└── integrations/
    └── llm.py                      # 修改：新增 generate_suggestions()

frontend/src/
├── api/
│   └── client.ts                   # 修改：新增 API 调用
├── components/
│   ├── ChatPanel.tsx               # 新增：从 App.tsx 拆出聊天面板
│   ├── SourcePopover.tsx           # 新增：引用展开组件
│   ├── FollowupSuggestions.tsx     # 新增：追问建议按钮组
│   ├── FeedbackButtons.tsx         # 新增：有用/无用反馈按钮
│   ├── CopyButton.tsx              # 新增：复制到剪贴板
│   ├── StructuredAnswer.tsx        # 新增：结构化答案组件
│   └── ThemeToggle.tsx             # 新增：亮/暗主题切换
├── hooks/
│   ├── useChatStream.ts            # 修改：增加 suggestions、feedback 状态
│   ├── useAutoScroll.ts            # 新增：自动滚底 hook
│   └── useTheme.ts                 # 新增：主题管理 hook
├── styles/
│   ├── global.css                  # 修改：暗色模式变量、响应式增强
│   └── dark.css                    # 新增：暗色主题覆盖
├── types/
│   └── api.ts                      # 修改：新增类型定义
└── App.tsx                         # 修改：集成 ChatPanel、主题切换、响应式布局
```

## 数据模型

### IndexJob

```sql
CREATE TABLE index_jobs (
    job_id      TEXT PRIMARY KEY,
    kb_id       TEXT NOT NULL,
    doc_id      TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'queued',  -- queued|processing|completed|failed
    error_message TEXT,
    chunk_count INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
```

### Feedback

```sql
CREATE TABLE feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,  -- MySQL: AUTO_INCREMENT
    message_id  TEXT NOT NULL,
    rating      TEXT NOT NULL,  -- helpful | not_helpful
    created_at  TEXT NOT NULL
);
```

### SearchResult（Schema）

```python
class SearchResult(BaseModel):
    doc_id: str
    filename: str
    chunk_index: int
    content: str
    score: float           # RRF 融合后的分数
    source_type: str       # "vector" | "keyword"
    rerank_score: float | None  # 仅启用 rerank 时有值
```

### FollowupSuggestion（Schema）

```python
class SuggestionRequest(BaseModel):
    question: str
    answer: str
    conversation_id: str | None

class SuggestionResponse(BaseModel):
    suggestions: list[str]  # 2-3 个追问
```

## 状态流

### 自动滚底

```
[消息列表渲染]
  -> useAutoScroll 监听容器 scroll 事件
  -> 计算 isNearBottom (距离底部 < 100px)
  -> [新消息到达]
       -> isNearBottom=true  → 自动 scrollTo(bottom)
       -> isNearBottom=false → 不滚动（用户在看历史）
  -> [用户手动滚回底部] → 恢复自动滚底
```

### 异步索引

```
[POST /documents] 
  -> 200ms 内创建 DocumentRecord + IndexJob(status=queued)
  -> 返回 { doc_id, job_id, status: "queued" }
  
[IndexWorker (后台 asyncio task)]
  -> 轮询 index_jobs WHERE status='queued'
  -> 更新 status='processing'
  -> document_loader.parse(file) → chunks
  -> embedding.embed(chunks) → vectors
  -> qdrant.upsert(vectors)
  -> 更新 status='completed', chunk_count=N
  -> [失败]
       -> 更新 status='failed', error_message=...
```

### 会话删除

```
[DELETE /conversations/{id}]
  -> 删除该 conversation 的所有 messages
  -> 删除该 conversation 记录
  -> 返回 204
  -> 前端：
       -> 从 conversation list 移除
       -> 如果当前正在查看：
            -> 切换到列表第一个（如果有）
            -> 否则显示空状态
```

## 接口设计

### 新增端点

```text
# 混合检索（独立可测）
POST /api/v1/kbs/{kb_id}/search
  Request:  { "query": "...", "top_k": 5 }
  Response: { "results": SearchResult[], "total": N }

# 索引任务状态
GET /api/v1/kbs/{kb_id}/index-jobs/{job_id}
  Response: { "job_id": "...", "doc_id": "...", "status": "...", 
              "chunk_count": 0, "error_message": null }

# 删除会话
DELETE /api/v1/kbs/{kb_id}/conversations/{conv_id}
  Response: 204 No Content

# 反馈
POST /api/v1/kbs/{kb_id}/feedback
  Request:  { "message_id": "...", "rating": "helpful" }
  Response: 201 { "message": "反馈已提交" }

# 追问建议
POST /api/v1/kbs/{kb_id}/suggestions
  Request:  { "question": "...", "answer": "...", "conversation_id": "..." }
  Response: { "suggestions": ["追问1", "追问2", "追问3"] }

# 监控指标
GET /api/v1/metrics
  Response: { "requests_total": N, "request_duration_ms": M, 
              "retrieval_duration_ms": M, "llm_duration_ms": M,
              "tokens_total": N, "errors_total": N }
```

### 修改端点

```text
# 文档上传 — 行为改为异步
POST /api/v1/kbs/{kb_id}/documents
  Response 改为: { "doc_id": "...", "job_id": "...", "status": "queued", 
                   "filename": "..." }

# kb_qa 节点内部调用混合检索
POST /api/v1/kbs/{kb_id}/chat  # 行为不变，内部走 hybrid_search
```

## 配置设计

```bash
# 元数据存储
METADATA_DB_PROVIDER=sqlite     # sqlite | mysql
MYSQL_DSN=mysql+aiomysql://user:pass@localhost:3306/kb_copilot

# 检索增强
RERANK_ENABLED=false            # 是否启用 rerank
RERANK_BASE_URL=                # rerank API 地址
RERANK_API_KEY=                 # rerank API key
RERANK_MODEL=                   # rerank 模型名

# 异步索引
INDEX_WORKER_CONCURRENCY=2      # worker 并发数
INDEX_WORKER_POLL_INTERVAL=2    # 轮询间隔（秒）

# 监控
METRICS_ENABLED=true

# 流式（已有）
CHAT_STREAM_ENABLED=true
```

## 错误处理

| 场景 | 处理 |
|---|---|
| PDF 解析失败 | 索引任务标记 failed，记录具体原因（文件损坏/格式不支持/空文件） |
| DOCX 解析失败 | 同上 |
| 关键词检索分词失败 | 降级为纯向量检索，日志 warning |
| rerank API 超时 | 跳过 rerank，使用 RRF 结果，日志 warning |
| MySQL 连接失败 | 启动时报错退出，给出明确 DSN 提示 |
| 会话删除时已不存在 | 返回 404 |
| 反馈提交到不存在的 message | 返回 404 |
| 追问建议 LLM 超时 | 返回空列表 `{"suggestions": []}`，前端不展示追问区域 |
| 监控指标内存溢出 | 限制最大保留条数（轮转），MVP3 不持久化 |
| 异步 worker 崩溃 | asyncio task 层面 catch，记录日志并更新任务为 failed |

## 测试策略

- **单元测试**：
  - `hybrid_search_service.py` 的 RRF 融合算法。
  - `keyword_search_service.py` 的分词和 FTS 查询。
  - `index_worker.py` 的状态流转逻辑。
  - `useAutoScroll` hook 的滚动行为（jsdom）。
- **集成测试**：
  - `POST /search` 端点返回正确融合结果。
  - `GET /index-jobs/{job_id}` 返回真实状态变化。
  - `DELETE /conversations/{id}` 级联删除验证。
  - MySQL 模式下完整 CRUD 流程。
- **冒烟测试**：
  - 前端上传 PDF 后查看索引状态，验证异步不阻塞。
  - 提问后观察自动滚底、追问建议、复制和反馈按钮。
  - 切换暗色模式后所有页面正常。
  - 移动端视口下布局可用。