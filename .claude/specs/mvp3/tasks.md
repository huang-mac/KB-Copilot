# MVP3 tasks.md

> 本文件回答"怎么一步步实现"。任务应能独立执行、验证，并回溯到 `spec.md`。
>
> 已完成的子 spec 任务不在此重复，直接引用：
> - SSE 流式输出：见 `.claude/specs/sse-streaming/tasks.md`
> - 意图识别与工具调用：见 `.claude/specs/intent-routing/tasks.md`

## 任务清单

### A. 混合检索与 RRF 融合

- [x] A1. 实现关键词检索能力  
  _需求：spec > EARS > 混合检索 — 系统应执行关键词检索_
  - [ ] A1.1 集成 jieba 分词，对 query 做分词和去停用词
  - [x] A1.2 基于 Qdrant `MatchText` + payload contains fallback 做关键词匹配
  - [x] A1.3 返回统一 `RetrievedChunk` 列表，`source_type="keyword"`
  - [x] A1.4 实现位置：`QdrantVectorStore.keyword_search()`

- [x] A2. 实现混合检索与 RRF 融合能力  
  _需求：spec > EARS > 混合检索 — 同时执行向量+关键词，RRF 融合_
  - [x] A2.1 实现 RRF 融合算法（k=60），输入两路 RetrievedChunk 列表，输出融合排序后的列表
  - [x] A2.2 融合结果保留 `source_type` 标识
  - [ ] A2.3 可选 rerank：当 `RERANK_ENABLED=true` 时，调用 rerank API 对 Top-N 候选排序，写入 `rerank_score`
  - [x] A2.4 融合后结果数 ≤ top_k
  - [x] A2.5 实现位置：`QdrantVectorStore.hybrid_search()` / `_rrf_fuse()`

- [x] A3. 修改 `kb_qa_node` 使用混合检索  
  _需求：spec > 验收标准 > 检索增强 — RRF 融合结果可追溯来源_
  - [x] A3.1 `kb_qa_node` 调用 `rag_service.answer()`，内部通过 `RAGService.search()` 走混合检索
  - [x] A3.2 结果中的 `source_type` 传递到最终 `sources` 中

- [x] A4. 新增独立检索端点 `POST /api/v1/kbs/{kb_id}/search`  
  _需求：spec > API > search — 混合检索独立可测_
  - [x] A4.1 创建 `schemas/search.py`（SearchRequest / SearchResponse）
  - [x] A4.2 创建 `api/v1/endpoints/search.py`
  - [x] A4.3 注册路由

### B. 异步索引

- [x] B1. 新增 IndexJob 数据模型和数据库表  
  _需求：spec > EARS > 异步索引 — 索引任务状态可查询_
  - [x] B1.1 创建 `domain/index_jobs.py`（IndexJob dataclass）
  - [x] B1.2 创建 `schemas/index_jobs.py`（IndexJobResponse）
  - [x] B1.3 创建 `repositories/index_jobs.py`（SQLite 实现，建表 + CRUD）

- [x] B2. 实现后台 index worker  
  _需求：spec > EARS > 异步索引 — 后台 worker 异步执行索引流程_
  - [x] B2.1 创建 `workers/index_worker.py`：asyncio task，轮询 queued 任务
  - [x] B2.2 worker 流程：更新 status=processing → 解析文档 → 切分 → Embedding → Qdrant 入库 → 更新 status=completed
  - [x] B2.3 异常时更新 status=failed，记录 error_message
  - [x] B2.4 在 FastAPI startup 事件中启动 worker

- [x] B3. 修改文档上传端点行为  
  _需求：spec > EARS > 异步索引 — 上传后 200ms 内返回_
  - [x] B3.1 `POST /api/v1/kbs/{kb_id}/documents` 改为创建 DocumentRecord + IndexJob，立即返回
  - [x] B3.2 响应中包含 `job_id` 和 `status: "queued"`
  - [x] B3.3 保持非异步模式作为兼容（配置开关 `ASYNC_INDEX_ENABLED=true`）

- [x] B4. 新增索引任务查询端点 `GET /api/v1/kbs/{kb_id}/index-jobs/{job_id}`  
  _需求：spec > API > index-jobs_
  - [x] B4.1 创建 `api/v1/endpoints/index_jobs.py`
  - [x] B4.2 注册路由

### C. PDF / DOCX 解析

- [x] C1. 后端支持 PDF 解析  
  _需求：spec > EARS > 文件上传 — 后端应能解析 PDF_
  - [x] C1.1 添加 `pymupdf` 依赖
  - [x] C1.2 `document_loader.py` 增加 PDF 解析分支，提取纯文本

- [x] C2. 后端支持 DOCX 解析  
  _需求：spec > EARS > 文件上传 — 后端应能解析 DOCX_
  - [x] C2.1 添加 `python-docx` 依赖
  - [x] C2.2 `document_loader.py` 增加 DOCX 解析分支，提取纯文本

- [x] C3. 前端上传组件支持 PDF/DOCX 拖拽  
  _需求：spec > EARS > 文件上传 — 上传组件应支持拖拽 PDF/DOCX_
  - [x] C3.1 扩展 Upload 组件的 accept 为 `.txt,.md,.markdown,.pdf,.docx`
  - [x] C3.2 上传区域提示文案更新

### D. MySQL 兼容

- [ ] D1. 实现数据库驱动抽象层  
  _需求：spec > EARS > MySQL 兼容 — 两种存储行为一致_
  - [ ] D1.1 `core/database.py` 根据 `METADATA_DB_PROVIDER` 创建 SQLite 或 MySQL 连接池
  - [ ] D1.2 添加 `aiomysql` 和 `sqlalchemy[asyncio]` 依赖（或直接用 aiosqlite/aiomysql 最小化方案）

- [ ] D2. 改造 repository 支持双后端  
  _需求：spec > EARS > MySQL 兼容_
  - [ ] D2.1 `repositories/conversations.py` 在 MySQL 模式下建表和 CRUD 正常
  - [ ] D2.2 `repositories/documents.py` 同上
  - [ ] D2.3 `repositories/index_jobs.py` 同上
  - [ ] D2.4 默认 SQLite 模式零依赖体验不变

### E. 会话删除

- [x] E1. 后端实现 DELETE 端点  
  _需求：spec > EARS > 对话体验 — 删除会话及其关联消息_
  - [x] E1.1 `api/v1/endpoints/conversations.py` 新增 `DELETE /{conv_id}`
  - [x] E1.2 repository 增加 `delete_conversation()` 方法（级联删除 messages）
  - [x] E1.3 会话不存在时返回 404

- [x] E2. 前端实现删除对话按钮  
  _需求：spec > 验收标准 > 对话体验 — 删除后从列表消失，自动切换_
  - [x] E2.1 会话列表项增加删除按钮（Popconfirm 确认）
  - [x] E2.2 `api/client.ts` 增加 `deleteConversation()`
  - [x] E2.3 删除当前查看的会话后，自动切换到下一个（或空状态）

### F. 对话自动滚底

- [x] F1. 实现 `useAutoScroll` hook  
  _需求：spec > EARS > 对话体验 — 新消息自动滚底，向上滚动时暂停_
  - [x] F1.1 监听消息列表容器的 scroll 事件
  - [x] F1.2 计算 `isNearBottom`（距离底部 < 100px 视为在底部）
  - [x] F1.3 新消息/token 更新时：若 isNearBottom，自动 scrollTo(bottom)
  - [x] F1.4 用户向上滚动时暂停，滚回底部后恢复

- [x] F2. 集成到聊天面板  
  _需求：spec > 验收标准 > 对话体验 — 新消息时自动滚底_
  - [x] F2.1 在 App 聊天消息列表容器上挂载 useAutoScroll
  - [x] F2.2 流式 token 更新也触发自动滚底

### G. 引用可视化与体验增强

- [x] G1. 实现引用来源展开组件 `SourcePopover`  
  _需求：spec > EARS > 对话体验 — 点击引用标签展开原文片段_
  - [x] G1.1 引用标签点击后 Popover 展示 `content` 原文
  - [x] G1.2 证据区域用浅色背景（#f0f7ff）或左边框（3px solid #60a5fa）高亮

- [x] G2. 实现一键复制按钮 `CopyButton`  
  _需求：spec > EARS > 对话体验 — 提供复制按钮_
  - [x] G2.1 使用 `navigator.clipboard.writeText()` 复制完整 Markdown 原文
  - [x] G2.2 复制后显示"已复制"确认（短暂 tooltip 或图标变化）

- [x] G3. 实现反馈按钮 `FeedbackButtons`  
  _需求：spec > EARS > 对话体验 — 有用/无用反馈_
  - [x] G3.1 两个按钮：有用 / 无用（图标）
  - [x] G3.2 点击后调用 `POST /feedback`，按钮变为已选状态（disabled）
  - [x] G3.3 `api/client.ts` 增加 `submitFeedback()`

- [ ] G4. 优雅降级提示  
  _需求：spec > EARS > 对话体验 — 无结果时明确提示_
  - [ ] G4.1 后端检索结果为空（分数低于阈值或无结果）时，answer 返回降级文案
  - [ ] G4.2 前端渲染降级提示（Alert type="info"）

### H. 追问建议

- [x] H1. 后端实现追问建议生成  
  _需求：spec > EARS > 追问建议 — 基于回答生成 2-3 个追问_
  - [x] H1.1 `integrations/llm.py` 增加 `generate_suggestions()` 方法
  - [x] H1.2 创建 `POST /api/v1/kbs/{kb_id}/suggestions` 端点
  - [x] H1.3 LLM 超时/失败时返回空列表，不阻塞

- [ ] H2. 前端实现追问建议组件 `FollowupSuggestions`  
  _需求：spec > 验收标准 > 追问建议 — 回答完成后出现按钮_
  - [x] H2.1 已创建 `FollowupSuggestions` 组件并封装 `POST /suggestions` 请求
  - [ ] H2.2 流式完成后在回答下方展示 2-3 个按钮
  - [ ] H2.3 点击后自动填入输入框并发送

### I. 响应式布局与暗色模式

- [ ] I1. 响应式布局增强  
  _需求：spec > EARS > 响应式布局 — 移动端输入框固定底部_
  - [ ] I1.1 移动端（<768px）历史会话改为 Drawer 弹出
  - [ ] I1.2 输入框固定在底部（position: sticky / fixed）
  - [ ] I1.3 键盘弹起时 viewport 调整（visualViewport API）

- [ ] I2. 暗色模式  
  _需求：spec > EARS > 暗色模式 — 支持亮色/暗色切换_
  - [ ] I2.1 实现 `useTheme` hook（localStorage 持久化 + Ant Design ConfigProvider `theme`）
  - [ ] I2.2 创建 `ThemeToggle` 组件（Header 中的切换按钮）
  - [ ] I2.3 新建 `styles/dark.css` 覆盖自定义组件样式
  - [ ] I2.4 暗色模式下：卡片、输入框、代码块、表格、消息气泡均适配

### J. 监控指标

- [x] J1. 实现指标收集器  
  _需求：spec > EARS > 监控指标 — 记录请求耗时、检索耗时等_
  - [x] J1.1 创建 `core/metrics.py`：内存字典存储计数器 + 耗时列表
  - [x] J1.2 在 FastAPI middleware 中收集请求数和耗时
  - [x] J1.3 在 hybrid_search 和 LLM 调用处埋点记录耗时；token 用量待真实用量统计补齐

- [x] J2. 暴露 metrics 端点  
  _需求：spec > API > metrics_
  - [x] J2.1 创建 `GET /api/v1/metrics` 端点，返回 JSON 指标
  - [x] J2.2 通过 `METRICS_ENABLED` 控制是否启用

### K. 聊天面板组件化重构

- [ ] K1. 从 App.tsx 拆分 ChatPanel 组件  
  _需求：spec > 体验基础 — 为后续组件化打底_
  - [ ] K1.1 创建 `components/ChatPanel.tsx`，迁移聊天相关 JSX 和状态
  - [ ] K1.2 App.tsx 通过 props 向 ChatPanel 传递 kbId
  - [ ] K1.3 集成 SourcePopover、CopyButton、FeedbackButtons、FollowupSuggestions

### L. 输入与消息气泡体验

- [x] L1. 输入框默认聚焦  
  _需求：产品体验优化 — 进入问答页后可直接输入_
  - [x] L1.1 问题输入框挂载 ref
  - [x] L1.2 页面加载后自动 focus

- [x] L2. 输入框快捷键  
  _需求：产品体验优化 — Enter 快速发送，Shift+Enter 换行_
  - [x] L2.1 Enter 触发发送
  - [x] L2.2 Shift+Enter 保留换行
  - [x] L2.3 IME 组合输入期间不误发送

- [x] L3. 消息气泡布局优化  
  _需求：产品体验优化 — 减少冗余标签，提升对话可读性_
  - [x] L3.1 去掉“用户/助手”显式角色标签
  - [x] L3.2 用户消息靠右，助手消息靠左
  - [x] L3.3 收紧消息区和输入框之间的垂直间距

- [x] L4. 单次回答耗时展示
  _需求：产品体验优化 — 用户可感知本次回答耗时_
  - [x] L4.1 前端记录发送到流式完成的耗时
  - [x] L4.2 在助手消息底部以小号文字展示耗时

### M. 监控指标前端页

- [x] M1. 新增监控指标 Tab
  _需求：spec > 监控指标 — 常用指标可在前端查看_
  - [x] M1.1 `api/client.ts` 增加 `getMetrics()`
  - [x] M1.2 展示请求数、错误数、平均请求耗时和平均流式耗时
  - [x] M1.3 展示 timing 指标表格
  - [x] M1.4 支持手动刷新指标

## 验证清单

### 检索增强
- [ ] 精确关键词搜索比纯向量检索更准确（抽查 5 个 case）。
- [x] RRF 融合结果中每个片段有 `source_type` 标识。
- [ ] `RERANK_ENABLED=false` 时走 RRF，`=true` 时有 rerank_score。（RRF 已完成，rerank 待补）

### 异步索引
- [ ] 上传文档后接口 200ms 内返回，前端不卡顿。
- [x] `GET /index-jobs/{id}` 能追踪 queued → processing → completed/failed。
- [x] 索引失败时 error_message 有具体原因。

### 对话体验
- [x] 新消息时自动滚到底部。
- [x] 向上滚动查看历史时停止自动滚底，滚回底部恢复。
- [x] 输入框默认聚焦，Enter 发送，Shift+Enter 换行。
- [x] 用户消息靠右，助手消息靠左，消息区和输入框间距更紧凑。
- [x] 助手消息显示单次回答耗时。
- [x] 引用标签可点击展开原文，证据有视觉高亮。
- [x] 复制按钮正常复制原文到剪贴板。
- [x] 有用/无用反馈可提交，提交后按钮 disabled。
- [ ] 无检索结果时显示降级提示。

### 会话删除
- [x] 删除会话后从列表消失。
- [x] 删除当前会话后自动切换到下一个。

### 追问建议
- [ ] 回答完成后出现 2-3 个追问按钮。
- [ ] 点击追问自动填入并发送。

### 文件上传
- [x] 支持拖拽 PDF 和 DOCX。
- [ ] 上传后能正常解析、索引、在问答中检索到内容。

### 响应式与暗色模式
- [ ] 移动端布局可用，输入框固定底部。
- [ ] 暗色模式切换正常，所有组件样式适配。

### MySQL 与监控
- [ ] `METADATA_DB_PROVIDER=mysql` 时 CRUD 正常。
- [x] `GET /api/v1/metrics` 返回有效指标，并可在前端监控指标 Tab 查看。

## 文档更新

- [x] `docs/MVP3.md` 状态更新为"实现中"。
- [x] `.env.example` 增加新增配置项。
- [x] `backend/pyproject.toml` 增加新依赖（pymupdf、python-docx）。
- [x] `CLAUDE.md` 的"当前 Specs"列表更新 mvp3 状态。

## 完成定义

- 所有 A-K 组必要任务标记为 `[x]`。
- 验证清单全部通过。
- 冒烟测试：从上传 PDF → 异步索引 → 提问 → 流式回答 → 自动滚底 → 引用展开 → 复制 → 反馈 → 追问建议 → 删除会话 → 切换主题，全流程可用。
- 实现与 `spec.md` 范围一致，没有混入 MVP4 能力（鉴权、多租户、导出、分享等）。
