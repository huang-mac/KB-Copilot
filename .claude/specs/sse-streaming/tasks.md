# SSE 流式输出 tasks.md

> 本文件回答"怎么一步步实现"。任务应能独立执行、验证，并回溯到 `spec.md`。

## 任务清单

- [x] 1. 后端：LLMClient 增加流式方法  
  _需求：spec.md — 逐 token 推送回答内容_
- [x] 1.1 在 `LLMClient` 基类中定义 `astream_answer()` 异步生成器方法签名。  
- [x] 1.2 在 `OpenAIChatClient` 中实现 `astream_answer()`，使用 `chat_model.astream()` 逐 token yield。  
- [x] 1.3 在 `MockLLMClient` 中实现 `astream_answer()`，模拟逐 token 输出。

- [x] 2. 后端：RAGService 增加流式方法  
  _需求：spec.md — 检索后流式生成回答_
- [x] 2.1 新增 `answer_stream()` 异步生成器，先检索再调用 LLM 流式生成。  
- [x] 2.2 yield 结构化数据：`{"type": "token", "data": "..."}`, `{"type": "sources", "data": [...]}`, `{"type": "done", "data": ...}`。

- [x] 3. 后端：新增 SSE chat 和 regenerate endpoint  
  _需求：spec.md — API 需求_
- [x] 3.1 新增 `POST /api/v1/kbs/{kb_id}/chat/stream` endpoint，使用 `StreamingResponse` 包装 SSE 事件流。  
- [x] 3.2 新增 `POST /api/v1/kbs/{kb_id}/chat/{conversation_id}/regenerate` endpoint。  
- [x] 3.3 新增 Pydantic schema：`ChatStreamRequest`, `RegenerateRequest`。  
- [x] 3.4 处理客户端断开连接（`asyncio.CancelledError`），优雅清理。  
- [x] 3.5 流式完成后持久化消息到 conversation_repository。

- [x] 4. 前端：SSE 客户端  
  _需求：spec.md — 逐 token 打字机效果_
- [x] 4.1 在 `api/client.ts` 中新增 `askQuestionStream()` 函数，基于 fetch + ReadableStream 消费 SSE。  
- [x] 4.2 新增 `useChatStream` hook，管理流式状态、token 累积、abort 控制、错误处理。

- [x] 5. 前端：Markdown 实时渲染  
  _需求：spec.md — Markdown/代码块实时渲染_
- [x] 5.1 安装 `react-markdown` 依赖。  
- [x] 5.2 在聊天消息中集成 Markdown 渲染，流式过程中实时更新。

- [x] 6. 前端：中断与重新生成  
  _需求：spec.md — 中断和重新生成_
- [x] 6.1 流式过程中显示"停止生成"按钮，点击调用 abort。  
- [x] 6.2 对已完成的助手消息显示"重新生成"按钮，点击发起 regenerate 请求。

- [ ] 7. 前端：拆分 ChatPanel 组件  
  _需求：代码可维护性 — 当前 App.tsx 过大_
- [ ] 7.1 将聊天相关逻辑从 App.tsx 抽到 `components/ChatPanel.tsx`。（延后：不阻塞 SSE 核心功能）
- [ ] 7.2 把消息渲染拆为独立组件。（延后：不阻塞 SSE 核心功能）

## 验证清单

- [ ] 流式问题提交后能逐 token 展示打字机效果。
- [ ] Markdown 内容在流式过程中实时渲染。
- [ ] 代码块实时渲染（基础样式）。
- [ ] 点击"停止生成"后生成中断，已输出内容保留。
- [ ] 点击"重新生成"后发起新的流式回答，替换旧回答。
- [ ] SSE 连接异常断开时展示提示。
- [ ] 原有非流式接口 `POST /chat` 仍可正常工作。
- [ ] 流式完成后消息出现在会话历史中。
- [ ] Mock LLM 模式下流式输出正常。

## 文档更新

- [ ] README 确认 MVP3 进度更新。

## 完成定义

- 所有必要任务已标记为 `[x]`。
- 验收标准全部通过。
- 测试或冒烟验证已执行并记录结果。
- 实现与 `spec.md` 范围一致，没有混入后续 MVP 能力。
