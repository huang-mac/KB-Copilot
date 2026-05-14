# 初学者读懂本项目 Agent 实现

这份文档写给刚开始学习 AI Agent、RAG、FastAPI、Python 后端的同学。你可以把它当成一篇“从代码读懂项目”的学习笔记。

本文尽量少讲空泛概念，多围绕项目里的真实代码解释：

- 这个项目里的 Agent 到底是什么。
- 用户上传文档后，后端做了什么。
- 用户提问后，系统如何识别意图、检索知识库、调用工具或要求补充信息。
- SSE 流式回答、异步索引、监控指标这些 MVP3 能力在代码里如何落地。
- Python 代码和 Java 后端代码有哪些对应关系。
- 初学者应该按什么顺序读代码。

## 1. 先给结论：本项目的 Agent 是什么

当前版本的 KB Copilot 已经不只是一个“单纯 RAG 问答接口”。它更准确的定位是：

```text
一个带意图路由、RAG 检索、业务工具调用和流式输出的知识库 Agent
```

它还不是那种会长期自主规划、循环反思、多 Agent 协作的复杂系统，但已经具备了典型 Agent 的几个基础能力：

- 接收用户问题。
- 识别用户意图。
- 根据意图选择处理路径。
- 知识库问题走 RAG 检索。
- 业务查询走 mock 工具调用。
- 闲聊、信息不足或无法识别时要求用户补充。
- 调用大模型生成回答。
- 保存会话历史、答案和引用来源。
- 支持 SSE token 级流式回答、停止生成和重新生成。

核心链路可以概括成：

```text
用户输入
  -> LangGraph 意图识别
  -> 条件路由
     -> 知识库问答：混合检索 + LLM 回答
     -> 业务工具：提取参数 + mock 工具 + LLM 总结
     -> 需要澄清：返回补充问题提示
  -> 保存会话
  -> 返回普通响应或 SSE 流式响应
```

## 2. 当前项目为什么需要意图识别

早期版本只有一个知识库问答入口，用户进来就是问文档，因此不需要额外判断意图。

MVP3 之后，同一个聊天框开始支持多种行为：

- 查知识库文档。
- 查库存、订单、价格、WMS 任务、采购计划、发票等业务 mock 数据。
- 对问候、闲聊、信息不足的问题做澄清提示。

因此系统必须先回答一个问题：

```text
用户这句话到底应该交给谁处理？
```

这个判断就在 `backend/app/graph/nodes.py` 的 `intent_classifier()` 中完成。它会让 LLM 只返回固定标签之一，例如：

```text
kb_qa
query_inventory
query_order_status
query_material_price
query_wmstask_status
query_purchase_plan
query_invoice_status
clarification_required
```

如果你是初学者，可以把“意图识别”理解成后端里的一个路由前置步骤。它不像 HTTP 路由根据 URL 分发请求，而是根据自然语言内容分发请求。

## 3. 项目整体分层

后端代码主要在 `backend/app` 下。

```text
backend/app/
├── api/v1/endpoints/   HTTP 接口层，接收前端请求
├── core/               配置、依赖装配、异常、日志、指标
├── domain/             领域对象，例如 DocumentChunk、IndexJob
├── graph/              LangGraph Agent 编排
├── schemas/            请求和响应模型
├── services/           核心业务编排，例如 RAGService、DocumentIndexService
├── integrations/       外部系统集成，例如 LLM、Embedding、Qdrant、MinIO
├── repositories/       SQLite 持久化，例如文档、会话、索引任务
├── tools/              业务查询工具抽象和 mock 工具
├── workers/            后台任务，例如异步索引 worker
└── main.py             FastAPI 应用入口
```

如果你是 Java 后端出身，可以先这样类比：

```text
FastAPI router     ≈ Spring MVC Controller
services           ≈ Service 层
repositories       ≈ DAO / Mapper / Repository
integrations       ≈ 外部客户端 / Gateway / Adapter
schemas            ≈ Request DTO / Response DTO
domain             ≈ Domain Model / record
dependencies.py    ≈ 简化版 Spring Bean 配置
LangGraph          ≈ 一个显式状态机 / 工作流编排器
```

## 4. FastAPI 应用如何启动

项目入口是 `backend/app/main.py`。

它主要做几件事：

```python
app = FastAPI(...)
app.add_middleware(CORSMiddleware, ...)
app.include_router(api_router, prefix=settings.api_prefix)
```

这相当于：

1. 创建 Web 应用。
2. 注册中间件。
3. 挂载所有 API 路由。

MVP3 还增加了两个启动/关闭钩子：

```python
@app.on_event("startup")
async def start_background_workers() -> None:
    if settings.async_index_enabled:
        get_index_worker().start()


@app.on_event("shutdown")
async def stop_background_workers() -> None:
    if settings.async_index_enabled:
        await get_index_worker().stop()
```

这表示 FastAPI 启动时会启动后台索引 worker，服务关闭时会停止它。

`main.py` 里还有一个 HTTP middleware 用于记录基础指标：

```python
@app.middleware("http")
async def collect_request_metrics(request: Request, call_next):
    ...
```

它会统计请求次数、请求耗时和错误数量，最后通过 `GET /api/v1/metrics` 暴露。

## 5. API 路由如何汇总

路由汇总在 `backend/app/api/v1/api.py`：

```python
api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(index_jobs.router)
api_router.include_router(search.router)
api_router.include_router(conversations.router)
api_router.include_router(chat.router)
api_router.include_router(tools.router)
api_router.include_router(feedback.router)
api_router.include_router(suggestions.router)
api_router.include_router(metrics.router)
```

可以理解成 Spring Boot 里多个 Controller 都注册到应用里。

当前比较重要的接口有：

```text
POST   /api/v1/kbs/{kb_id}/documents
GET    /api/v1/kbs/{kb_id}/index-jobs/{job_id}
POST   /api/v1/kbs/{kb_id}/search
POST   /api/v1/kbs/{kb_id}/chat
POST   /api/v1/kbs/{kb_id}/chat/stream
POST   /api/v1/kbs/{kb_id}/chat/{conversation_id}/regenerate
GET    /api/v1/metrics
```

## 6. 两条主线：文档入库与用户问答

整个项目最重要的是两条主线。

第一条是“文档入库”。MVP3 默认走异步索引：

```text
上传文件
  -> 创建 DocumentRecord，状态 queued
  -> 创建 IndexJob，保存文件 bytes
  -> HTTP 立即返回 job_id
  -> 后台 worker 领取 queued 任务
  -> 解析文本
  -> 切分 chunk
  -> 调用 Embedding 模型生成向量
  -> 写入 Qdrant
  -> 更新任务状态 completed 或 failed
```

第二条是“用户问答”：

```text
用户提问
  -> 找到或创建会话
  -> 读取历史消息
  -> LangGraph 识别意图
  -> 根据意图路由
     -> kb_qa：RAG 检索 + LLM 回答
     -> 工具意图：mock 工具调用 + LLM 总结
     -> clarification_required：直接返回补充提示
  -> 保存用户问题、模型回答和引用来源
  -> 返回答案、引用、意图和工具结果
```

SSE 流式接口稍有不同：当前流式接口直接走 `RAGService.answer_stream()`，重点服务于知识库问答的 token 级输出、中断和重新生成。

## 7. 文档上传入口：先排队，不阻塞

文档上传接口在 `backend/app/api/v1/endpoints/documents.py`。

MVP3 的关键变化是：默认不再在 HTTP 请求里同步完成全部索引，而是创建后台任务。

简化后的逻辑是：

```python
content = await file.read()
filename = file.filename or "untitled.txt"

if settings.async_index_enabled:
    doc_id = str(uuid.uuid4())
    document = document_repository.create(
        kb_id=kb_id,
        doc_id=doc_id,
        filename=filename,
        status="queued",
    )
    job = index_job_repository.create(
        kb_id=kb_id,
        job_id=str(uuid.uuid4()),
        doc_id=doc_id,
        filename=filename,
        content=content,
        content_type=file.content_type,
    )
    return DocumentUploadResponse(..., job_id=job.job_id, job_status=job.status)
```

对初学者来说，这里有几个关键点：

- `await file.read()`：异步读取上传文件。
- `DocumentRecord`：保存文档列表里能看到的元数据。
- `IndexJob`：保存后台索引任务状态和原始文件内容。
- `ASYNC_INDEX_ENABLED=false` 时仍可回退到同步索引。

Java 后端可以粗略类比成：

```java
@PostMapping("/kbs/{kbId}/documents")
public DocumentUploadResponse uploadDocument(
        @PathVariable String kbId,
        MultipartFile file
) {
    Document doc = documentRepository.createQueued(...);
    IndexJob job = indexJobRepository.create(..., file.getBytes());
    return responseWithJobId(doc, job);
}
```

## 8. 异步索引任务：IndexWorker

后台 worker 在 `backend/app/workers/index_worker.py`。

核心流程是：

```python
while not self._stopping.is_set():
    job = self.index_job_repository.claim_next()
    if job is None:
        await asyncio.sleep(self.poll_interval_seconds)
        continue

    payload = self.index_job_repository.get_payload(kb_id=job.kb_id, job_id=job.job_id)
    ...
    await self.document_index_service.index_existing_document(...)
```

你可以把它理解成一个简单的本地任务队列消费者：

```text
claim_next()
  -> 找一条 queued 任务
  -> 原子更新为 processing
  -> 返回给 worker 处理
```

如果索引成功：

```python
self.index_job_repository.mark_completed(...)
```

如果索引失败：

```python
self.index_job_repository.mark_failed(..., error_message=str(exc))
```

前端可以通过这个接口查询状态：

```text
GET /api/v1/kbs/{kb_id}/index-jobs/{job_id}
```

## 9. 文档入库编排：DocumentIndexService

真正的文档解析、切分、向量化和入库逻辑在 `backend/app/services/document_index_service.py`。

MVP3 里最重要的方法是 `index_existing_document()`，它用于处理已经创建好的文档和索引任务：

```python
self.document_repository.update_status(kb_id=kb_id, doc_id=doc_id, status="processing")
text = self.document_loader.load_text(filename, content)
chunks = self.text_splitter.split(...)
vectors = await self.embedding_client.embed_texts([chunk.content for chunk in chunks])
self.vector_store.delete_document(kb_id=kb_id, doc_id=doc_id)
self.vector_store.upsert_chunks(chunks, vectors, created_at=document.created_at.isoformat())
self.document_repository.mark_completed(...)
```

这段代码就是“知识进入系统”的完整流程：

```text
文件 bytes -> 文本 -> chunks -> embeddings -> Qdrant points
```

它的职责很清楚：不关心 HTTP，也不关心页面，只负责把文档变成可检索知识。

## 10. 文档解析：DocumentLoader

`backend/app/services/document_loader.py` 负责把上传文件变成字符串。

当前支持：

```text
.txt
.md
.markdown
.pdf
.docx
```

简化逻辑：

```python
suffix = Path(filename).suffix.lower()
if suffix == ".pdf":
    text = self._load_pdf(content)
elif suffix == ".docx":
    text = self._load_docx(content)
else:
    text = self._decode_text(content)
```

其中：

- PDF 使用 `pymupdf` 提取文本。
- DOCX 使用 `python-docx` 提取段落文本。
- TXT/Markdown 会尝试 `utf-8`、`utf-8-sig`、`gb18030` 等编码。

这对中文文档比较友好。

## 11. 文本切分：TextSplitter

文本切分在 `backend/app/services/text_splitter.py`。

项目使用 LangChain 的 `RecursiveCharacterTextSplitter`。它会尽量按自然边界切分：

```text
段落 -> 换行 -> 中文句号/问号/感叹号 -> 英文标点 -> 空格 -> 字符
```

为什么要切分？

因为文档太长时，向量检索和大模型上下文都不适合一次塞完整全文。切成小片段后，系统可以只召回最相关的片段。

`chunk_overlap` 是片段重叠长度，用来降低上下文断裂风险。

## 12. 领域对象：DocumentChunk、RetrievedChunk、IndexJob

文档片段对象在 `backend/app/domain/chunks.py`。

```python
@dataclass(frozen=True)
class DocumentChunk:
    id: str
    kb_id: str
    doc_id: str
    filename: str
    chunk_index: int
    content: str
```

`@dataclass` 会自动生成构造函数等常用方法。

`frozen=True` 表示对象创建后不建议再修改，类似 Java 的不可变对象。

Java 可以类比成：

```java
public record DocumentChunk(
    String id,
    String kbId,
    String docId,
    String filename,
    int chunkIndex,
    String content
) {}
```

检索结果对象 `RetrievedChunk` 多了：

```python
score: float
source_type: str = "vector"
```

`source_type` 用来告诉前端这个引用来源来自哪种召回方式。当前混合检索通过 Qdrant fusion 返回时会标记为 `fusion`。

索引任务对象在 `backend/app/domain/index_jobs.py`：

```python
@dataclass(frozen=True)
class IndexJob:
    kb_id: str
    job_id: str
    doc_id: str
    filename: str
    status: IndexJobStatus
    created_at: datetime
    updated_at: datetime
```

它让“上传”和“索引完成”解耦。

## 13. Embedding：把文字变成向量

Embedding 相关代码在 `backend/app/integrations/embedding.py`。

抽象接口：

```python
class EmbeddingClient:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def embed_query(self, query: str) -> list[float]:
        vectors = await self.embed_texts([query])
        return vectors[0]
```

这里体现了面向接口编程。

真实实现是 `OpenAIEmbeddingClient`，通过 OpenAI-compatible Embedding 服务生成向量。

项目也提供 `MockEmbeddingClient`，没有 API Key 时也能做本地冒烟测试。

## 14. Qdrant：向量库如何保存和混合检索

向量库封装在 `backend/app/integrations/qdrant.py`。

写入时不仅存向量，还会把元数据放到 payload 里：

```python
payload={
    "kb_id": chunk.kb_id,
    "doc_id": chunk.doc_id,
    "filename": chunk.filename,
    "chunk_index": chunk.chunk_index,
    "created_at": created_at,
    "content": chunk.content,
}
```

payload 很重要。否则检索出来之后，只知道“某个向量相似”，却不知道它来自哪个文件、哪个片段。

检索时会按 `kb_id` 过滤：

```python
query_filter=models.Filter(
    must=[
        models.FieldCondition(
            key="kb_id",
            match=models.MatchValue(value=kb_id),
        )
    ]
)
```

这保证只在当前知识库内检索。

MVP3 的 `hybrid_search()` 使用 Qdrant 原生 prefetch + fusion：

```python
prefetch=[
    models.Prefetch(query=query_vector, limit=top_k * 2),
    models.Prefetch(query=models.Query(text=models.QueryText(text=query)), limit=top_k * 2),
],
query=models.FusionQuery(fusion=models.Fusion.RRF),
```

可以理解成：

```text
向量召回一批结果
关键词召回一批结果
用 RRF 融合排序
返回 Top-K
```

RRF 的全称是 Reciprocal Rank Fusion，是一种常见的多路检索结果融合算法。

## 15. LangGraph：Agent 的编排核心

Agent 图在 `backend/app/graph/graph.py`。

它注册了四个节点：

```python
graph.add_node("intent_classifier", ...)
graph.add_node("kb_qa", ...)
graph.add_node("tool_executor", ...)
graph.add_node("clarification", ...)
```

入口是意图识别：

```python
graph.set_entry_point("intent_classifier")
```

然后通过条件边路由：

```python
graph.add_conditional_edges(
    "intent_classifier",
    _route_by_intent,
    {
        "kb_qa": "kb_qa",
        "tool_executor": "tool_executor",
        "clarification": "clarification",
    },
)
```

`_route_by_intent()` 的逻辑很直接：

```python
if intent in TOOL_INTENTS:
    return "tool_executor"
if intent == "clarification_required":
    return "clarification"
return "kb_qa"
```

这就是本项目 Agent 的核心状态机。

## 16. AgentState：节点之间传递什么

状态定义在 `backend/app/graph/state.py`：

```python
class AgentState(TypedDict):
    kb_id: str
    question: str
    top_k: int
    history: str
    intent: str
    retrieval_results: list[dict]
    tool_result: dict | None
    answer: str
    sources: list[dict]
    error: str | None
```

你可以把它理解成“图执行过程中的上下文对象”。

每个节点读取一部分字段，再写回一部分字段。例如：

- `intent_classifier` 写入 `intent`。
- `kb_qa_node` 写入 `answer` 和 `sources`。
- `tool_executor_node` 写入 `answer` 和 `tool_result`。
- `clarification_node` 写入澄清提示。

Java 里可以类比成一个工作流上下文 DTO。

## 17. 知识库问答节点：kb_qa_node

代码在 `backend/app/graph/nodes.py`。

简化逻辑：

```python
answer, sources = await rag_service.answer(
    kb_id=state["kb_id"],
    question=state["question"],
    top_k=state.get("top_k", 5),
    history=_parse_history(state.get("history", "")),
)
```

这个节点不自己做检索细节，而是调用 `RAGService`。

返回时会把引用来源转换成 API 可返回的 dict：

```python
{
    "doc_id": s.doc_id,
    "filename": s.filename,
    "chunk_index": s.chunk_index,
    "score": s.score,
    "content": s.content,
    "source_type": s.source_type,
}
```

这就是前端引用弹窗的数据来源。

## 18. 工具调用节点：tool_executor_node

业务工具在 `backend/app/tools/`。

当前实现的是 mock 工具，例如：

```text
query_inventory
query_order_status
query_material_price
query_wmstask_status
query_purchase_plan
query_invoice_status
```

工具执行节点的流程是：

```text
根据 intent 找到工具
  -> 用 LLM 从问题中提取参数
  -> 执行 mock 工具
  -> 用 LLM 把工具结果总结成自然语言回答
```

对应代码在 `tool_executor_node()`：

```python
tool = tool_registry.get(intent)
params = await _extract_params(llm_client, tool, question)
tool_result = await tool.execute(**params)
answer = await llm_client.generate_answer(
    question=question,
    context=_format_tool_result(tool_result),
    history=state.get("history", ""),
)
```

这已经是一个轻量 Tool Calling 流程，只是工具选择由前置意图识别决定，而不是完全交给模型自由调用。

## 19. 澄清节点：clarification_node

当用户输入太短、闲聊或信息不足时，系统不会强行检索或编造答案。

`clarification_node()` 会返回一段引导：

```text
抱歉，我没有完全理解您的问题。您可以尝试：
1. 查询知识库
2. 查询库存
3. 查询订单
...
```

这对企业知识库问答很重要。因为不知道就要求补充，比编造答案更可靠。

## 20. Chat API：普通问答入口如何运行 Agent

普通问答接口在 `backend/app/api/v1/endpoints/chat.py`。

核心流程：

```python
state = await run_graph(
    graph=graph,
    kb_id=kb_id,
    question=request.question,
    top_k=top_k,
    history=history_text,
)

answer = state.get("answer", "")
sources = state.get("sources", [])
intent = state.get("intent")
tool_result = state.get("tool_result")
```

这说明普通 `POST /chat` 走的是 LangGraph Agent 编排。

然后保存两条消息：

```text
user      -> 用户问题
assistant -> 模型回答 + sources 引用来源
```

最后返回：

```python
ChatResponse(
    conversation_id=conversation_id,
    answer=answer,
    sources=[...],
    intent=intent,
    tool_result=tool_result,
)
```

所以前端不仅能看到答案，还能知道这次请求被识别成什么意图，以及工具调用结果是什么。

## 21. SSE 流式回答：chat/stream

流式接口还是在 `chat.py`：

```python
@router.post("/stream")
async def chat_stream(...)
```

它返回的是：

```python
StreamingResponse(
    event_generator(),
    media_type="text/event-stream",
)
```

`event_generator()` 会持续 yield SSE 事件：

```text
event: sources
data: {"sources": [...]}

event: token
data: {"token": "..."}

event: done
data: {"conversation_id": "...", "message_id": "..."}
```

如果用户中断连接，后端会保存部分回答，并在内容后加上：

```text
[已中断]
```

这就是前端“停止生成”的后端基础。

需要注意：当前流式接口直接走 `RAGService.answer_stream()`，没有经过 LangGraph 工具路由；它主要服务知识库问答的实时输出体验。

## 22. RAGService：知识库问答的核心编排器

`backend/app/services/rag_service.py` 是知识库问答的核心。

构造函数接收三个依赖：

```python
class RAGService:
    def __init__(
        self,
        *,
        embedding_client: EmbeddingClient,
        vector_store: QdrantVectorStore,
        llm_client: LLMClient,
    ) -> None:
        ...
```

核心检索方法：

```python
async def search(self, *, kb_id: str, query: str, top_k: int) -> list[RetrievedChunk]:
    with Timer("retrieval.hybrid_search"):
        query_vector = await self.embedding_client.embed_query(query)
        return self.vector_store.hybrid_search(
            kb_id=kb_id,
            query=query,
            query_vector=query_vector,
            top_k=top_k,
        )
```

核心回答方法：

```python
sources = await self.search(kb_id=kb_id, query=query_text, top_k=top_k)
context = self._build_context(sources)
with Timer("llm.generate_answer"):
    answer = await self.llm_client.generate_answer(
        question=question,
        context=context,
        history=history_text,
    )
```

这就是 RAG 的核心：

```text
用户问题 + 历史
  -> embedding
  -> 混合检索
  -> 构造上下文
  -> LLM 生成答案
```

## 23. 上下文拼接：把检索结果喂给大模型

`RAGService._build_context()` 会把检索出来的片段拼成一段字符串：

```python
来源文件：xxx.md
片段序号：3
检索方式：fusion
相关度：0.8123
内容：...
```

为什么要这样做？

因为大模型不会自动知道你的私有知识库内容。你必须把检索到的资料放进 Prompt 里。

这一步就是 RAG 中的 Augmented，也就是“增强”。

没有这一步，大模型只能靠通用知识回答，无法可靠回答企业私有文档里的内容。

## 24. LLMClient：真正调用大模型

大模型调用在 `backend/app/integrations/llm.py`。

抽象接口：

```python
class LLMClient:
    async def generate_answer(self, *, question: str, context: str, history: str = "") -> str:
        raise NotImplementedError
```

真实实现使用 LangChain 的 `ChatOpenAI`，兼容 OpenAI-style API。

Prompt 中最关键的是 system 约束：

```text
你是一个企业知识库问答助手。
请只根据给定资料回答问题；如果资料中没有答案，
请回答“根据当前知识库资料无法确认”。
```

这能降低模型胡编乱造的概率。

项目还提供 `MockLLMClient`，可以在没有真实 API Key 时完成本地冒烟测试。

## 25. 依赖装配：dependencies.py 像一个简化版 Spring 配置类

依赖装配在 `backend/app/core/dependencies.py`。

例如：

```python
@lru_cache
def get_rag_service() -> RAGService:
    settings = get_settings()
    return RAGService(
        embedding_client=create_embedding_client(settings),
        vector_store=get_vector_store(),
        llm_client=create_llm_client(settings),
    )
```

这相当于手写一个 Bean 工厂。

`@lru_cache` 会缓存函数返回值。第一次调用时创建对象，后面复用之前的对象，有点像 Spring 单例 Bean。

MVP3 中这里还装配了：

```text
DocumentRepository
ConversationRepository
IndexJobRepository
DocumentIndexService
RAGService
ToolRegistry
LangGraph graph
IndexWorker
```

## 26. Repository：SQLite 持久化

当前主要 repository：

```text
DocumentRepository
  -> 保存文档元数据、chunk 数量、索引状态、失败原因

ConversationRepository
  -> 保存会话列表
  -> 保存 user / assistant 消息
  -> 保存 assistant 回答对应的引用来源

IndexJobRepository
  -> 保存索引任务、任务状态、错误信息和上传文件 bytes
```

对初学者来说，可以把 Repository 理解成 Java 项目里的 DAO / Mapper 层。

Service 不直接写 SQL，而是通过 Repository 完成数据读写。

## 27. 配置：Settings 统一读取环境变量

配置在 `backend/app/core/config.py`。

常见配置：

```python
qdrant_url: str = "http://localhost:6333"
document_db_path: str = "data/kb_copilot.sqlite3"
chunk_size: int = 700
top_k: int = 5
async_index_enabled: bool = True
metrics_enabled: bool = True
rerank_enabled: bool = False
embedding_provider: Literal["openai", "mock"] = "openai"
llm_provider: Literal["openai", "mock"] = "openai"
```

这类似 Spring Boot 的 `application.yml` + `@ConfigurationProperties`。

`.env` 中配置的值会覆盖默认值。

本地学习时可以使用：

```env
EMBEDDING_PROVIDER=mock
LLM_PROVIDER=mock
```

这样不需要真实模型 API Key，也能先理解工程流程。

## 28. 监控指标：core/metrics.py

MVP3 增加了轻量级内存指标收集器。

代码在 `backend/app/core/metrics.py`。

它记录两类数据：

```text
counters：计数器，例如 http.requests、http.errors
timings：耗时列表，例如 http.request、retrieval.hybrid_search、llm.generate_answer
```

查看接口：

```text
GET /api/v1/metrics
```

这是一个 MVP 级实现，适合单实例、本地和演示环境。生产环境后续可以替换成 Prometheus 等方案。

## 29. 前端如何配合 Agent

前端主要在 `frontend/src/App.tsx`。

几个关键点：

- 上传文档后，如果返回 `job_id`，前端会轮询 `getIndexJob()`。
- 文档列表展示 `queued`、`processing`、`completed`、`failed`。
- 发送问题默认走 SSE 流式接口。
- 停止生成会调用前端的 AbortController，中断当前 stream。
- 引用来源通过 `SourcePopover` 展开。
- 回答可以通过 `CopyButton` 复制。
- 有用/无用反馈通过 `FeedbackButtons` 提交。

前端 API 封装在 `frontend/src/api/client.ts`，类型定义在 `frontend/src/types/api.ts`。

## 30. 当前项目的重点亮点

### 亮点 1：RAG 主链路完整

项目已经跑通了从文档上传到大模型回答的完整闭环：

```text
文档解析 -> 文本切分 -> Embedding -> Qdrant 入库 -> 混合检索 -> Prompt 拼接 -> LLM 回答
```

### 亮点 2：Agent 编排清晰

LangGraph 把意图识别、知识库问答、工具调用、澄清提示拆成清晰节点。

初学者可以很直观看到：

```text
State -> Node -> Conditional Edge -> Node -> END
```

### 亮点 3：异步索引让上传不阻塞

上传接口只创建任务并返回 `job_id`，后台 worker 再慢慢索引。

这比“用户上传后一直等到 embedding 和 Qdrant 全部完成”更接近真实产品。

### 亮点 4：面向接口编程

`EmbeddingClient`、`LLMClient`、`Tool` 都是抽象风格。

真实模型和 mock 模型可以替换，业务工具也可以继续扩展。

### 亮点 5：引用来源可追溯

问答结果不仅返回 `answer`，还返回 `sources`。

知识库问答不能只给答案，还应该告诉用户依据来自哪里。

### 亮点 6：mock 模式降低学习门槛

没有模型 API Key 时，也可以使用 mock Embedding 和 mock LLM 跑通基本流程。

## 31. 当前项目还不是复杂 Agent 的原因

当前项目已经有意图识别和工具调用，但仍不是复杂自主 Agent。

它还没有：

- Agent Loop，也就是多轮“思考 -> 调工具 -> 观察 -> 再思考”。
- 长期记忆总结。
- 多 Agent 协作。
- MCP 远程工具接入。
- 真实外部业务系统调用。
- 复杂工具规划。

这不是缺点，而是当前版本的边界。

可以这样理解：

```text
MVP1：先跑通 RAG 问答
MVP2：增加文档管理和多轮会话
MVP3：加入意图路由、工具调用、SSE、异步索引、混合检索、监控
MVP4：再考虑鉴权、多租户、权限过滤、生产治理
更后面：再加入 Agent Loop、SubAgent、MCP 等复杂能力
```

## 32. 初学者应该按什么顺序读代码

建议按这个顺序看：

```text
1. backend/app/main.py
2. backend/app/api/v1/api.py
3. backend/app/core/config.py
4. backend/app/core/dependencies.py

文档入库链路：
5. backend/app/api/v1/endpoints/documents.py
6. backend/app/repositories/documents.py
7. backend/app/repositories/index_jobs.py
8. backend/app/workers/index_worker.py
9. backend/app/services/document_index_service.py
10. backend/app/services/document_loader.py
11. backend/app/services/text_splitter.py
12. backend/app/integrations/embedding.py
13. backend/app/integrations/qdrant.py

Agent 问答链路：
14. backend/app/api/v1/endpoints/chat.py
15. backend/app/graph/state.py
16. backend/app/graph/graph.py
17. backend/app/graph/nodes.py
18. backend/app/services/rag_service.py
19. backend/app/tools/registry.py
20. backend/app/tools/business_tools.py
21. backend/app/integrations/llm.py

体验和支撑：
22. backend/app/api/v1/endpoints/search.py
23. backend/app/api/v1/endpoints/metrics.py
24. backend/app/core/metrics.py
25. frontend/src/api/client.ts
26. frontend/src/App.tsx
```

不要一开始就纠结所有 Python 语法。先抓住调用链：

```text
Controller -> Service -> Repository / Integration -> 外部系统
Graph State -> Node -> Route -> Node
```

## 33. 最值得背下来的四段代码

第一段：异步上传创建任务。

```python
document = document_repository.create(..., status="queued")
job = index_job_repository.create(..., content=content)
return DocumentUploadResponse(..., job_id=job.job_id, job_status=job.status)
```

第二段：文档入库。

```python
text = self.document_loader.load_text(filename, content)
chunks = self.text_splitter.split(kb_id=kb_id, doc_id=doc_id, filename=filename, text=text)
vectors = await self.embedding_client.embed_texts([chunk.content for chunk in chunks])
self.vector_store.upsert_chunks(chunks, vectors, created_at=document.created_at.isoformat())
```

第三段：Agent 路由。

```python
if intent in TOOL_INTENTS:
    return "tool_executor"
if intent == "clarification_required":
    return "clarification"
return "kb_qa"
```

第四段：RAG 问答。

```python
sources = await self.search(kb_id=kb_id, query=query_text, top_k=top_k)
context = self._build_context(sources)
answer = await self.llm_client.generate_answer(
    question=question,
    context=context,
    history=history_text,
)
```

这四段代码基本就是当前项目 Agent 实现的核心。

## 34. 一句话总结

本项目当前的 Agent 实现，本质是一个工程化的知识库 Agent：

```text
它先把企业文档变成可检索知识，再通过 LangGraph 判断用户意图，
对知识库问题走 RAG，对业务问题走工具，对不清楚的问题要求补充，
最后用大模型生成可追溯的回答。
```

对初学者来说，这是一个合适的学习起点。你能从代码里看到 AI 应用的工程本质：不是“直接问大模型”，而是“组织状态、管理知识、选择路径、调用工具、构造上下文、返回可追溯结果”。
