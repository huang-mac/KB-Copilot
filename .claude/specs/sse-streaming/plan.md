# SSE 流式输出 plan.md

> 本文件回答"怎么做"。它根据 `spec.md` 设计技术方案、模块边界、数据模型、接口和验证策略。

## 技术方案

- 前端：新增 `useChatStream` hook 封装 SSE 消费逻辑；引入 `react-markdown` 渲染 Markdown；在聊天消息列表内增加流式消息项。
- 后端：新增 `POST /api/v1/kbs/{kb_id}/chat/stream` SSE endpoint；`LLMClient` 增加 `astream_answer` 异步生成器方法；`RAGService` 增加 `answer_stream` 方法；利用 FastAPI `StreamingResponse` 输出 SSE。
- 存储：复用现有 SQLite conversation/message 存储，流式完成后持久化完整消息。
- 外部集成：LangChain ChatOpenAI 已有 `streaming=True`，改用 `astream` 逐 token yield。
- 配置：复用现有 `.env` 配置，新增 `CHAT_STREAM_ENABLED` 开关（默认 true）。

## 模块设计

```
backend:
  app/
    schemas/chat.py          — 新增 ChatStreamRequest, SSEToken, SSESources, SSEDone, SSEError
    services/rag_service.py  — 新增 answer_stream() 异步生成器
    integrations/llm.py      — LLMClient 新增 astream_answer()，OpenAIChatClient/MockLLMClient 实现
    api/v1/endpoints/chat.py — 新增 chat_stream endpoint, regenerate endpoint

frontend:
  src/
    api/client.ts            — 新增 askQuestionStream() 返回 SSE ReadableStream
    hooks/useChatStream.ts   — 新增 hook：管理 SSE 连接、流式状态、中断
    components/ChatPanel.tsx — 从 App.tsx 拆出聊天面板组件
    App.tsx                  — 集成 ChatPanel
```

## 数据模型

### SSE 事件类型（后端输出）

```
SSE 事件格式（text/event-stream）:
  event: token
  data: {"token": "你"}

  event: token
  data: {"token": "好"}

  event: sources
  data: {"sources": [...]}

  event: done
  data: {"conversation_id": "abc", "message_id": "xyz"}

  event: error
  data: {"error": "LLM_TIMEOUT", "detail": "..."}
```

### 前端流式状态

```typescript
interface StreamState {
  status: "idle" | "streaming" | "done" | "error" | "aborted";
  tokens: string[];           // 已接收的 token 列表
  sources: Source[] | null;   // 引用来源
  conversationId: string | null;
  error: string | null;
}
```

## 状态流

```
[用户输入问题，点击发送]
  -> 前端 POST /chat/stream，建立 fetch + ReadableStream
  -> 后端 RAG: 向量检索 -> 获取召回片段
  -> 后端 LLM: astream 逐 token yield
  -> 后端逐 token 写 SSE event: token
  -> 前端逐 token 更新 UI
  -> [用户点击中断]
       -> 前端 abort fetch
       -> 后端 asyncio task 取消
       -> 已接收内容保留
  -> [生成完成]
       -> 后端发送 event: sources + event: done
       -> 前端渲染最终 Markdown
  -> [用户点击重新生成]
       -> 前端发起新的 SSE 请求（复用上一轮 question）
       -> 新回答替换当前回答
```

## 接口设计

### POST /api/v1/kbs/{kb_id}/chat/stream

```
Request:  ChatStreamRequest { question: str, top_k?: int, conversation_id?: str }
Response: text/event-stream

事件顺序: token* -> sources? -> done
异常时:   token* -> error
```

后端实现要点：
- 使用 `StreamingResponse` + `media_type="text/event-stream"`
- 在生成器内部先做 RAG 检索，再调用 LLM astream
- 检索和 LLM 错误通过 `event: error` 发出
- 流式完成后将完整消息持久化到 conversation_repository

### POST /api/v1/kbs/{kb_id}/chat/{conversation_id}/regenerate

```
Request:  RegenerateRequest { top_k?: int }
Response: text/event-stream（与 chat/stream 相同）
```

后端实现要点：
- 从 conversation 中获取上一轮 user 消息作为 question
- 其他逻辑与 chat/stream 完全相同

## 配置设计

- `CHAT_STREAM_ENABLED`：控制 SSE endpoint 是否启用。默认 `true`。设为 `false` 时 SSE endpoint 拒绝请求，前端降级使用非流式接口。

## 错误处理

- LLM 调用超时/失败：发送 `event: error`，前端展示错误。
- RAG 检索失败：发送 `event: error`，不进入 LLM 阶段。
- SSE 连接意外断开：前端 onerror / reader.cancel 后展示"连接已中断"。
- 用户 abort fetch：前端主动取消，后端生成器检测到客户端断开，触发 `asyncio.CancelledError` 并清理。
- 流式完成后消息持久化失败：发送 `event: error` 并说明持久化失败，但 token 内容仍然返回给前端。

## 测试策略

- 单元测试：MockLLMClient 的 astream 输出正确格式。
- 集成测试：用 `httpx.AsyncClient` 消费 SSE endpoint，验证事件顺序和格式。
- 冒烟测试：前端启动后提问，观察打字机效果、中断和重新生成是否正常。
