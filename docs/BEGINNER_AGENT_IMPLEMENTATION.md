# 初学者读懂本项目 Agent 实现

这份文档写给刚开始学习 AI Agent、RAG、FastAPI、Python 后端的同学。你可以把它当成一篇“从代码读懂项目”的学习笔记。

本文会尽量少讲空泛概念，多围绕项目里的真实代码解释：

- 这个项目里的 Agent 到底是什么。
- 用户上传文档后，后端做了什么。
- 用户提问后，系统如何检索知识库并调用大模型。
- Python 代码和 Java 后端代码有哪些对应关系。
- 当前项目的重点、亮点和后续可以升级的方向。

## 1. 先给结论：本项目的 Agent 是什么

严格来说，当前版本的 KB Copilot 不是那种“会自己规划任务、自己调用多个工具、循环反思”的复杂 Agent。

它更准确的定位是：

```text
一个基于 RAG 的知识库问答助手
```

如果从宽泛的 Agent 角度理解，它的 Agent 能力主要体现在：

- 接收用户问题。
- 从私有知识库中检索相关资料。
- 把检索结果组织成上下文。
- 调用大模型生成回答。
- 返回答案和引用来源。

所以当前项目的核心不是复杂 Tool Calling，也不是多 Agent 协作，而是把最重要的一条链路跑通：

```text
文档进入系统 -> 变成可检索的知识 -> 用户提问 -> 检索资料 -> 大模型基于资料回答
```

这条链路就是 RAG，也就是 Retrieval-Augmented Generation，中文一般叫“检索增强生成”。

## 2. 为什么当前项目不需要意图识别

很多 Agent 文章里都会讲“意图识别”，比如先判断用户是在闲聊、查知识库、调用工具，还是要创建子任务。

但当前项目暂时不需要这一层。

原因很简单：你的接口已经表达了用户意图。

问答接口是：

```text
POST /api/v1/kbs/{kb_id}/chat
GET  /api/v1/kbs/{kb_id}/conversations
GET  /api/v1/kbs/{kb_id}/conversations/{conversation_id}/messages
```

这个接口的语义非常明确：用户就是在某个知识库 `kb_id` 下面提问。

既然入口已经告诉系统“这是知识库问答”，就不需要再额外调用一次 LLM 判断“这是不是知识库问题”。

什么时候才需要意图识别？

- 同一个聊天框既支持普通闲聊，又支持知识库问答。
- 同一个聊天框既支持查文档，又支持调用天气、股票、数据库等工具。
- 系统有多个 Agent，需要先判断该交给哪个 Agent。
- RAG 检索成本很高，你希望只有必要时才检索。
- 用户输入很开放，系统必须先做路由。

当前项目的设计反而是一个优点：链路简单，适合初学者先把 RAG 主流程学透。

## 3. 项目整体分层

后端代码主要在 `backend/app` 下。

```text
backend/app/
├── api/v1/endpoints/   HTTP 接口层，接收前端请求
├── core/               配置、依赖装配、异常、日志
├── domain/             领域对象，例如 DocumentChunk
├── schemas/            请求和响应模型
├── services/           核心业务编排，例如 RAGService
├── integrations/       外部系统集成，例如 LLM、Embedding、Qdrant
└── main.py             FastAPI 应用入口
```

如果你是 Java 后端出身，可以先这样类比：

```text
FastAPI router     ≈ Spring MVC Controller
services           ≈ Service 层
integrations       ≈ 外部客户端 / Gateway / Adapter
schemas            ≈ Request DTO / Response DTO
domain             ≈ Domain Model / record
dependencies.py    ≈ 简化版 Spring Bean 配置
```

## 4. HTTP 入口：FastAPI 应用如何启动

项目入口是 `backend/app/main.py`。

重点代码：

```python
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="A lightweight RAG knowledge base assistant powered by FastAPI and Qdrant.",
)

app.include_router(api_router, prefix=settings.api_prefix)
```

这段代码做了两件事：

1. 创建一个 FastAPI 应用，相当于 Spring Boot 创建 Web 应用上下文。
2. 把所有 API 路由挂载到应用上。

`settings.api_prefix` 默认是 `/api/v1`，所以最终接口会带上这个前缀。

路由汇总在 `backend/app/api/v1/api.py`：

```python
api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(conversations.router)
api_router.include_router(chat.router)
```

可以理解成 Spring 里把多个 Controller 都交给应用管理。

## 5. 两条主线：文档入库与用户问答

整个项目最重要的是两条主线。

第一条是“文档入库”：

```text
上传文件
  -> 读取 bytes
  -> 保存原始文件到 MinIO
  -> 解析文本
  -> 切分 chunk
  -> 调用 Embedding 模型生成向量
  -> 写入 Qdrant 向量库
```

第二条是“用户问答”：

```text
用户提问
  -> 找到或创建会话
  -> 读取历史消息
  -> 问题转向量
  -> 在 Qdrant 中检索相似 chunk
  -> 拼接成上下文
  -> 调用 LLM
  -> 保存用户问题、模型回答和引用来源
  -> 返回答案和引用来源
```

MVP2 以后，系统还多了一条“会话管理”链路：

```text
新建会话
  -> 保存 conversation 元数据
  -> 每次问答追加 user / assistant 消息
  -> 前端切换会话时重新加载消息流
```

这几条链路合起来就是本项目的核心 Agent 实现。

## 6. 文档上传入口

文档上传接口在 `backend/app/api/v1/endpoints/documents.py`。

核心代码：

```python
@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    kb_id: str,
    file: Annotated[UploadFile, File(...)],
    document_index_service: Annotated[
        DocumentIndexService,
        Depends(get_document_index_service),
    ],
) -> DocumentUploadResponse:
    content = await file.read()
    document, _chunks = await document_index_service.index_document(
        kb_id=kb_id,
        filename=file.filename or "untitled.txt",
        content=content,
        content_type=file.content_type,
    )
```

对初学者来说，这里有几个关键点。

`async def` 表示这是一个异步接口函数。它可以在等待文件读取、模型请求、外部服务响应时释放执行权，提高并发能力。

`await file.read()` 表示等待文件内容读取完成。

`Depends(get_document_index_service)` 是 FastAPI 的依赖注入机制。它会帮你拿到一个 `DocumentIndexService` 实例。

如果类比 Java，大致像这样：

```java
@PostMapping("/kbs/{kbId}/documents")
public DocumentUploadResponse uploadDocument(
        @PathVariable String kbId,
        MultipartFile file,
        DocumentIndexService documentIndexService
) {
    byte[] content = file.getBytes();
    return documentIndexService.indexDocument(kbId, file.getOriginalFilename(), content);
}
```

## 7. 文档入库编排：DocumentIndexService

真正的文档入库逻辑在 `backend/app/services/document_index_service.py`。

核心代码：

```python
async def index_document(
    self,
    *,
    kb_id: str,
    filename: str,
    content: bytes,
) -> tuple[str, list[DocumentChunk]]:
    doc_id = str(uuid.uuid4())
    text = self.document_loader.load_text(filename, content)
    chunks = self.text_splitter.split(kb_id=kb_id, doc_id=doc_id, filename=filename, text=text)
    vectors = await self.embedding_client.embed_texts([chunk.content for chunk in chunks])
    self.vector_store.upsert_chunks(chunks, vectors)
    return doc_id, chunks
```

这段代码非常重要，它就是“知识进入系统”的完整流程。

逐行解释：

```python
doc_id = str(uuid.uuid4())
```

给上传的文档生成一个唯一 ID。类似 Java 里的：

```java
String docId = UUID.randomUUID().toString();
```

```python
text = self.document_loader.load_text(filename, content)
```

把文件 bytes 解析成文本。当前支持 `.txt`、`.md`、`.markdown`。

```python
chunks = self.text_splitter.split(...)
```

把一篇长文档切成多个小片段。因为大模型和向量检索都不适合一次处理超长文档。

```python
vectors = await self.embedding_client.embed_texts([chunk.content for chunk in chunks])
```

把每个文本片段转换成向量。

其中：

```python
[chunk.content for chunk in chunks]
```

是 Python 的列表推导式，相当于 Java Stream：

```java
List<String> contents = chunks.stream()
    .map(DocumentChunk::content)
    .toList();
```

```python
self.vector_store.upsert_chunks(chunks, vectors)
```

把文本片段和对应向量写入 Qdrant。

这个 Service 的亮点是职责非常清晰：它不关心 HTTP，也不关心页面，只负责“文档如何变成可检索知识”。

## 8. 文档解析：DocumentLoader

`backend/app/services/document_loader.py` 负责把上传文件变成字符串。

核心代码：

```python
class DocumentLoader:
    supported_suffixes = {".txt", ".md", ".markdown"}

    def load_text(self, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix not in self.supported_suffixes:
            raise UnsupportedDocumentError(
                f"Unsupported document type '{suffix}'. MVP1 supports txt and md."
            )

        text = self._decode_text(content)
        if not text.strip():
            raise UnsupportedDocumentError("Uploaded document is empty.")
        return text
```

这里的亮点是先做边界检查：

- 文件后缀必须是支持的类型。
- 文件内容不能为空。
- 编码解析单独封装在 `_decode_text()`。

`_decode_text()` 会依次尝试 `utf-8`、`utf-8-sig`、`gb18030`，这对中文文档比较友好。

## 9. 文本切分：TextSplitter

文本切分在 `backend/app/services/text_splitter.py`。

核心代码：

```python
class TextSplitter:
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
        )
```

这里使用的是 LangChain 的 `RecursiveCharacterTextSplitter`。

它的思想是：尽量按照更自然的语义边界切分文本。

切分优先级大致是：

```text
段落 -> 换行 -> 中文句号/问号/感叹号 -> 英文句号/问号/感叹号 -> 空格 -> 字符
```

这比简单地每 700 个字符硬切一次更好，因为它更可能保留完整句子和段落。

`chunk_overlap` 是重叠长度。假设一个 chunk 结尾处的信息和下一个 chunk 开头有关，重叠可以避免上下文断裂。

举个简单例子：

```text
chunk 1: A B C D E
chunk 2: D E F G H
```

`D E` 就是重叠部分。

这也是当前项目的一个重点亮点：虽然是 MVP，但没有用最粗糙的固定切分，而是使用了递归语义切分。

## 10. 领域对象：DocumentChunk 和 RetrievedChunk

领域对象在 `backend/app/domain/chunks.py`。

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

`@dataclass` 会自动帮你生成构造函数等常用方法。

`frozen=True` 表示对象创建后不建议再修改，类似不可变对象。

Java 里可以类比成：

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

为什么要有 `DocumentChunk`？

因为系统不能只存文本内容，还要知道这段文本来自哪里：

- 属于哪个知识库：`kb_id`
- 属于哪个文档：`doc_id`
- 来自哪个文件：`filename`
- 是第几个片段：`chunk_index`
- 片段内容是什么：`content`

这些元数据后面会用于返回引用来源。

## 11. Embedding：把文字变成向量

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

Java 中你可能会写：

```java
public interface EmbeddingClient {
    List<List<Float>> embedTexts(List<String> texts);
    List<Float> embedQuery(String query);
}
```

`OpenAIEmbeddingClient` 是真实实现，内部通过 LangChain 的 `OpenAIEmbeddings` 调用 OpenAI-compatible Embedding 服务。

```python
class OpenAIEmbeddingClient(EmbeddingClient):
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.embedding_api_key
        self.client = OpenAIEmbeddings(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url.rstrip("/"),
            model=settings.embedding_model,
            check_embedding_ctx_length=False,
        )
```

项目还提供了 `MockEmbeddingClient`。

```python
class MockEmbeddingClient(EmbeddingClient):
    """Deterministic local embedding for smoke tests without external API keys."""
```

这个 mock 实现很适合本地冒烟测试。没有 API Key 时，也可以跑通基本链路。

这也是项目的一个亮点：初学者不需要一开始就卡在模型 API 配置上。

## 12. Qdrant：向量库如何保存和检索

向量库封装在 `backend/app/integrations/qdrant.py`。

初始化：

```python
class QdrantVectorStore:
    def __init__(self, settings: Settings) -> None:
        if settings.qdrant_url == ":memory:":
            self.client = QdrantClient(":memory:")
        else:
            self.client = QdrantClient(url=settings.qdrant_url)
        self.collection_name = settings.qdrant_collection
        self.vector_size = settings.embedding_dimension
```

这里做了两件事：

- 根据配置连接 Qdrant。
- 记录 collection 名称和向量维度。

写入向量：

```python
def upsert_chunks(self, chunks: list[DocumentChunk], vectors: list[list[float]]) -> None:
    self.ensure_collection()
    points = [
        models.PointStruct(
            id=chunk.id,
            vector=vector,
            payload={
                "kb_id": chunk.kb_id,
                "doc_id": chunk.doc_id,
                "filename": chunk.filename,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
            },
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    self.client.upsert(collection_name=self.collection_name, points=points)
```

这里的 `payload` 很关键。

向量库里不只是存向量，还要存元数据。否则检索出来之后，只知道“有个向量很相似”，却不知道它来自哪个文件、哪个片段、具体内容是什么。

检索向量：

```python
def search(self, *, kb_id: str, query_vector: list[float], top_k: int) -> list[RetrievedChunk]:
    self.ensure_collection()
    response = self.client.query_points(
        collection_name=self.collection_name,
        query=query_vector,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="kb_id",
                    match=models.MatchValue(value=kb_id),
                )
            ]
        ),
        limit=top_k,
        with_payload=True,
    )
```

这里最重要的是 `query_filter`。

它保证只在当前 `kb_id` 对应的知识库里检索，不会把其他知识库的内容混进来。

这就是最基础的知识库隔离。

## 13. 问答入口：Chat API

问答接口在 `backend/app/api/v1/endpoints/chat.py`。

核心代码：

```python
@router.post("", response_model=ChatResponse)
async def chat(
    kb_id: str,
    request: ChatRequest,
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
) -> ChatResponse:
    settings = get_settings()
    top_k = request.top_k or settings.top_k

    answer, sources = await rag_service.answer(
        kb_id=kb_id,
        question=request.question,
        top_k=top_k,
    )
```

这里的逻辑很薄：

- 从路径里拿到 `kb_id`。
- 从请求体里拿到 `question` 和 `top_k`。
- 调用 `RAGService.answer()`。
- 把答案和引用来源包装成响应。

Controller 层保持很薄，这是一个好习惯。

业务逻辑不要堆在接口函数里，而是放到 Service 层。

### MVP2 增强：Chat API 会写入会话历史

MVP2 的 `ChatRequest` 多了 `conversation_id`：

```python
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    top_k: int | None = Field(default=None, ge=1, le=20)
    conversation_id: str | None = None
```

如果前端没有传 `conversation_id`，后端会自动创建一个新会话；如果传了，就把本次问答追加到已有会话。

保存消息时会写两条记录：

```text
user      -> 用户问题
assistant -> 模型回答 + sources 引用来源
```

这样前端刷新后，可以通过会话接口把历史消息重新展示出来。

## 14. 请求响应模型：Pydantic Schema

请求和响应模型在 `backend/app/schemas/chat.py`。

```python
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    top_k: int | None = Field(default=None, ge=1, le=20)
    conversation_id: str | None = None
```

这里有几个 Python 新手容易困惑的点。

`BaseModel` 来自 Pydantic，作用类似 Java 里的 DTO，但它还能自动校验字段。

`question: str` 表示 `question` 必须是字符串。

`Field(..., min_length=1)` 表示必填，并且长度至少为 1。

`top_k: int | None` 表示 `top_k` 可以是整数，也可以是空值。类似 Java 里的：

```java
Integer topK;
```

响应模型：

```python
class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[Source]
```

这保证 API 返回的数据结构稳定，前端可以放心按固定结构解析。

## 15. RAGService：本项目 Agent 的核心编排器

最重要的类是 `backend/app/services/rag_service.py`。

```python
class RAGService:
    def __init__(
        self,
        *,
        embedding_client: EmbeddingClient,
        vector_store: QdrantVectorStore,
        llm_client: LLMClient,
    ) -> None:
        self.embedding_client = embedding_client
        self.vector_store = vector_store
        self.llm_client = llm_client
```

构造函数接收三个依赖：

- `EmbeddingClient`：负责把问题变成向量。
- `QdrantVectorStore`：负责检索相似文档片段。
- `LLMClient`：负责调用大模型生成回答。

这就是典型的组合式设计。`RAGService` 不自己实现所有细节，而是编排多个组件完成任务。

核心方法：

```python
async def answer(
    self,
    *,
    kb_id: str,
    question: str,
    top_k: int,
) -> tuple[str, list[RetrievedChunk]]:
    query_vector = await self.embedding_client.embed_query(question)
    sources = self.vector_store.search(kb_id=kb_id, query_vector=query_vector, top_k=top_k)
    context = self._build_context(sources)
    answer = await self.llm_client.generate_answer(question=question, context=context)
    return answer, sources
```

这是全文最值得反复看的代码。

它浓缩了 RAG 问答的全部核心思想：

```text
用户问题
  -> embedding
  -> 向量检索
  -> 构造上下文
  -> LLM 生成答案
```

如果你只记一段代码，就记这段。

## 16. 上下文拼接：把检索结果喂给大模型

`RAGService._build_context()` 负责把检索出来的文档片段拼成一段字符串。

```python
def _build_context(self, sources: list[RetrievedChunk]) -> str:
    blocks = []
    for source in sources:
        blocks.append(
            "\n".join(
                [
                    f"来源文件：{source.filename}",
                    f"片段序号：{source.chunk_index}",
                    f"内容：{source.content}",
                ]
            )
        )
    return "\n\n".join(blocks)
```

为什么要这样做？

因为大模型不会自动知道你的知识库内容。你必须把检索到的资料放进 Prompt 里。

这一步就是 RAG 中的 Augmented，也就是“增强”。

没有这一步，大模型只能靠自己训练时学到的通用知识回答，无法可靠回答企业私有文档里的内容。

### MVP2 增强：把历史消息也放进 Prompt

MVP1 只有“当前问题 + 检索上下文”。MVP2 增加了会话历史后，问答链路变成：

```text
当前问题 + 最近历史消息 + 检索上下文 -> LLM
```

这样用户可以围绕同一个会话继续追问，例如先问“这份文档讲了什么”，再问“那第二点展开说说”。系统会把最近几轮 user / assistant 消息传给 `RAGService`，再由 `LLMClient` 放进 Prompt。

这里要注意：当前实现是轻量级多轮会话，不是完整 Agent Memory。它不会做长期记忆总结，只是保存消息并取最近几轮作为上下文，足够支撑 MVP2 的产品体验。

## 17. LLMClient：真正调用大模型

大模型调用在 `backend/app/integrations/llm.py`。

抽象接口：

```python
class LLMClient:
    async def generate_answer(self, *, question: str, context: str, history: str = "") -> str:
        raise NotImplementedError
```

真实实现：

```python
messages = [
    {
        "role": "system",
        "content": (
            "你是一个企业知识库问答助手。"
            "请只根据给定资料回答问题；如果资料中没有答案，"
            "请回答“根据当前知识库资料无法确认”。"
        ),
    },
    {
        "role": "user",
        "content": f"历史对话：\n{history or '无'}\n\n资料：\n{context}\n\n问题：\n{question}",
    },
]
```

这里的 system prompt 非常关键。

它给模型设定了边界：

```text
只能根据给定资料回答
资料中没有答案就说无法确认
```

这能降低模型胡编乱造的概率。

然后通过 LangChain 的 `ChatOpenAI` 调用 OpenAI-compatible LLM 服务。

```python
return (await self.client.ainvoke(messages)).content.strip()
```

`ainvoke` 里的 `a` 通常表示 async，也就是异步版本。

## 18. 依赖装配：dependencies.py 像一个简化版 Spring 配置类

依赖装配在 `backend/app/core/dependencies.py`。

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

这段代码相当于手写一个 Bean 工厂。

Java Spring 里可能是：

```java
@Bean
public RAGService ragService(
        EmbeddingClient embeddingClient,
        VectorStore vectorStore,
        LLMClient llmClient
) {
    return new RAGService(embeddingClient, vectorStore, llmClient);
}
```

`@lru_cache` 的作用是缓存函数返回值。

也就是说，第一次调用 `get_rag_service()` 会创建对象，后面再次调用会复用之前的对象。

这有点像单例 Bean。

### MVP2 增强：Repository 负责持久化

MVP2 开始引入 SQLite 持久化，主要有两个 Repository：

```text
DocumentRepository
  -> 保存文档元数据、chunk 数量、索引状态、失败原因

ConversationRepository
  -> 保存会话列表
  -> 保存 user / assistant 消息
  -> 保存 assistant 回答对应的引用来源
```

这样前端刷新页面后，仍然可以重新加载文档列表和历史会话。

对初学者来说，可以把 Repository 理解成 Java 项目里的 DAO / Mapper 层。Service 不直接写 SQL，而是通过 Repository 完成数据读写。

## 19. 配置：Settings 统一读取环境变量

配置在 `backend/app/core/config.py`。

```python
class Settings(BaseSettings):
    app_name: str = "KB Copilot API"
    api_prefix: str = "/api/v1"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "kb_copilot"
    document_db_path: str = "data/kb_copilot.sqlite3"

    minio_enabled: bool = False
    minio_endpoint: str = "localhost:9000"
    minio_bucket: str = "kb-copilot-documents"

    chunk_size: int = 700
    chunk_overlap: int = 120
    top_k: int = 5

    embedding_provider: Literal["openai", "mock"] = "openai"
    llm_provider: Literal["openai", "mock"] = "openai"
```

这类似 Spring Boot 的 `application.yml` + `@ConfigurationProperties`。

`.env` 中配置的值会覆盖默认值。

比如：

```env
EMBEDDING_PROVIDER=mock
LLM_PROVIDER=mock
```

就可以切换到 mock 模式，方便本地测试。

## 20. 当前项目的重点亮点

### 亮点 1：RAG 主链路完整

项目已经跑通了从文档上传到大模型回答的完整闭环：

```text
MinIO 原文保存 -> 文档解析 -> 文本切分 -> Embedding -> Qdrant 入库 -> 向量检索 -> Prompt 拼接 -> LLM 回答
```

这比只写一个“调用大模型接口”的 Demo 更有学习价值。

### 亮点 2：代码分层清晰

接口层、业务层、外部集成层分得比较清楚。

例如 `chat.py` 只负责接收请求，真正的 RAG 逻辑放在 `RAGService`。

这种分层非常适合后续扩展。

### 亮点 3：面向接口编程

`EmbeddingClient` 和 `LLMClient` 都是抽象基类风格。

真实模型和 mock 模型可以替换：

```text
EmbeddingClient
  -> OpenAIEmbeddingClient
  -> MockEmbeddingClient

LLMClient
  -> OpenAIChatClient
  -> MockLLMClient
```

这对测试和本地开发很友好。

### 亮点 4：知识库隔离做得早

Qdrant 检索时使用了 `kb_id` 过滤：

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

这避免不同知识库的数据互相污染。

### 亮点 5：返回引用来源

问答结果不仅返回 `answer`，还返回 `sources`。

```python
class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[Source]
```

这点非常重要。

知识库问答不能只给一个答案，还应该告诉用户答案依据来自哪里。否则用户很难信任模型输出。

### 亮点 6：MVP2 支持文档管理和会话历史

MVP2 不再只是一次性问答，而是开始接近真实产品：

```text
文档列表 / 删除 / 重新索引 / 索引状态
历史会话 / 消息流 / 引用来源回看 / 多轮追问
```

这一步的重点不是让模型更复杂，而是让知识库“可管理、可回看、可继续使用”。

### 亮点 7：mock 模式降低学习门槛

`MockEmbeddingClient` 和 `MockLLMClient` 让项目不依赖真实模型 API Key 也能跑起来。

这对初学者非常友好，因为你可以先理解工程流程，再配置真实模型。

## 21. 当前项目还不是复杂 Agent 的原因

当前项目没有以下能力：

- Function Calling / Tool Calling
- Agent Loop
- 长期记忆总结
- SubAgent
- MCP
- 意图识别
- 多路召回
- RRF
- Rerank

这不是缺点，而是当前版本的边界。

学习项目最怕一开始把所有概念都塞进去。当前版本先把 RAG 主链路讲清楚，是更适合初学者的设计。

可以这样理解：

```text
MVP1：先做一个可靠的 RAG 知识库问答助手
MVP2：增加文档管理和多轮会话
MVP3：再考虑混合检索、rerank、权限、监控等生产能力
更后面：再加入 Tool Calling、Agent Loop、SubAgent、MCP
```

## 22. 如果后续要进化成更像 Agent 的系统

后续可以按这个顺序升级，而不是一次性加完。

第一步：把多轮会话记忆升级成可总结的长期记忆。

```text
最近历史消息 -> 会话摘要 -> 用户问题 + 会话摘要 + 检索上下文 -> LLM
```

第二步：增加意图识别。

```text
用户输入 -> 判断是普通聊天还是知识库问答
```

第三步：把知识库检索封装成 Tool。

```text
LLM 决定是否调用 knowledge_search
```

第四步：增加更多工具。

```text
查文档、查数据库、查接口、生成报告
```

第五步：实现 Agent Loop。

```text
LLM 思考 -> 调工具 -> 观察结果 -> 继续思考 -> 最终回答
```

但对当前项目来说，不建议马上加这些复杂能力。先把 RAG 这条主线写稳、讲透、测好，更重要。

## 23. 初学者应该按什么顺序读代码

建议按这个顺序看：

```text
1. backend/app/main.py
2. backend/app/api/v1/api.py
3. backend/app/api/v1/endpoints/documents.py
4. backend/app/repositories/documents.py
5. backend/app/services/document_index_service.py
6. backend/app/services/document_loader.py
7. backend/app/services/text_splitter.py
8. backend/app/integrations/minio_storage.py
9. backend/app/integrations/embedding.py
10. backend/app/integrations/qdrant.py
11. backend/app/api/v1/endpoints/conversations.py
12. backend/app/repositories/conversations.py
13. backend/app/api/v1/endpoints/chat.py
14. backend/app/services/rag_service.py
15. backend/app/integrations/llm.py
16. backend/app/core/dependencies.py
17. backend/app/core/config.py
```

不要一开始就纠结所有 Python 语法。先抓住调用链：

```text
Controller -> Service -> Integration -> 外部系统
```

这和 Java 后端项目的基本思路是一样的。

## 24. 最值得背下来的三段代码

第一段：文档入库。

```python
text = self.document_loader.load_text(filename, content)
chunks = self.text_splitter.split(kb_id=kb_id, doc_id=doc_id, filename=filename, text=text)
vectors = await self.embedding_client.embed_texts([chunk.content for chunk in chunks])
self.vector_store.upsert_chunks(chunks, vectors)
```

第二段：RAG 问答。

```python
query_vector = await self.embedding_client.embed_query(question)
sources = self.vector_store.search(kb_id=kb_id, query_vector=query_vector, top_k=top_k)
context = self._build_context(sources)
answer = await self.llm_client.generate_answer(question=question, context=context)
```

第三段：Prompt 约束。

```python
messages = [
    {
        "role": "system",
        "content": (
            "你是一个企业知识库问答助手。"
            "请只根据给定资料回答问题；如果资料中没有答案，"
            "请回答“根据当前知识库资料无法确认”。"
        ),
    },
    {
        "role": "user",
        "content": f"资料：\n{context}\n\n问题：\n{question}",
    },
]
```

这三段代码基本就是本项目 Agent 实现的核心。

## 25. 一句话总结

本项目当前的 Agent 实现，本质是一个结构清晰的 RAG 编排器：

```text
它不追求复杂的自动规划，而是专注完成一件事：
把企业文档变成可检索知识，再让大模型基于检索到的资料回答问题。
```

对初学者来说，这是非常好的起点。因为你能从代码里清楚看到 AI 应用的工程本质：不是“直接问大模型”，而是“组织上下文、管理知识、调用模型、返回可追溯结果”。
