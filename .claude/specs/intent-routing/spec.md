# 意图识别与工具调用 spec.md

> 本文件回答"要做什么"。只描述需求、用户故事和验收标准，不讨论具体技术方案。

## 目标

将当前单一 RAG 问答流程升级为可编排的意图驱动问答。系统在收到用户输入后先识别意图，再根据意图路由到不同处理节点：知识库问答走 RAG 检索，订单查询走工具调用（MVP3 先用 mock），闲聊或无法识别则提示用户补充信息。

这是 MVP3 基础设施升级的第一步，为后续接入真实外部工具和复杂编排打底。

## 用户故事

- 作为普通用户，我希望系统能识别我是在查知识库还是在查订单，以便得到针对性的回答。
- 作为普通用户，当我的问题模糊不清时，我希望系统能引导我补充信息，而不是胡乱编造答案。
- 作为开发者，我希望工具调用有清晰的抽象层，以便后续接入真实订单系统时只需替换 adapter，不动编排逻辑。

## EARS 需求

### 意图识别

- 当用户提交问题时，系统应先对问题做意图分类，再路由到对应处理节点。
- 意图类型至少包含：
  - `kb_qa`：知识库问答（默认意图）。
  - `query_inventory`：库存查询。
  - `query_order_status`：销售订单发货/物流查询。
  - `query_material_price`：物料成本/售价查询。
  - `query_wmstask_status`：WMS 任务进度查询。
  - `query_purchase_plan`：未来到货计划查询。
  - `query_invoice_status`：发票开票/收票状态查询。
  - `clarification_required`：闲聊、无法识别或信息不足。
- 当意图识别为 `clarification_required` 时，系统应返回引导性提示，不进入 RAG 或工具调用。
- 当意图识别置信度不足或分类失败时，系统应降级为 `kb_qa`，不阻塞用户问答。

### 工具调用骨架

- 当意图为工具查询意图时（inventory/order_status/material_price 等），系统应调用对应工具获取结果，并基于工具返回生成回答。
- 使用通用 `tool_executor_node`：根据 intent 从 ToolRegistry 查找工具 → LLM 提取参数 → 执行 → 生成自然语言回答。
- 所有工具均使用 mock 实现，返回固定格式的模拟业务数据。
- 工具调用抽象层应定义清晰的接口（tool name、input schema、output schema、执行逻辑）。
- 系统应预留 HTTP 工具调用的 adapter 实现，代码以注释形式保留，包含 HTTP 请求、超时、错误处理示例。
- 工具注册机制应支持新增工具而不修改编排核心代码（只需新建工具文件 + 注册到 ToolRegistry）。

### 编排流程

- 问答流程应使用 LangGraph 编排，拆分为意图识别、路由、处理、回答生成等独立节点。
- 编排图应支持从状态中传递用户问题、意图、检索结果、工具结果和最终回答。
- 当任一节点发生异常时，系统应返回可理解的错误信息，不静默吞错。

## API 需求

```text
POST /api/v1/kbs/{kb_id}/chat          # 现有端点，行为升级为意图驱动
POST /api/v1/tools/order-query          # 订单查询工具端点（独立可测）
```

- `POST /api/v1/kbs/{kb_id}/chat` 请求体和响应体保持向后兼容，响应中增加可选字段 `intent` 和 `tool_result`。
- `POST /api/v1/tools/order-query` 接收 `{"order_id": "xxx"}`，返回 mock 订单数据。

## 数据需求

- `intent`：意图类型枚举，`kb_qa | order_query | clarification_required`。
- `order_id`：订单号，字符串，订单查询工具的必填参数。
- `tool_result`：工具调用结果，结构化 JSON，在 ChatResponse 中为可选字段。

## 验收标准

- 用户输入"帮我查一下订单 ORD-001"，系统识别为 `query_order_status` 意图，调用 mock 工具，返回结构化订单信息。
- 用户输入"查一下物料 MAT-001 的库存"，系统识别为 `query_inventory` 意图，返回库存 mock 数据。
- 用户输入"hello / 你好 / 今天天气怎么样"，系统识别为 `clarification_required`，返回引导提示而非编造答案。
- 用户输入业务知识问题（如"产品A的返修流程是什么"），系统走 RAG 检索并正常回答。
- 意图识别失败或超时时，系统降级为 `kb_qa`，问答不中断。
- 现有 `POST /api/v1/kbs/{kb_id}/chat` 端点行为向后兼容，已有前端调用无需改动即可正常工作。
- 工具注册机制允许仅通过添加新文件来注册新工具，不修改 LangGraph 图定义。
- HTTP 工具 adapter 代码以注释形式存在于代码库中，包含请求、超时、错误处理示例。

## 不包含

- 真实 MCP 远程工具接入。
- 多工具并行调用或工具链编排。
- 工具调用结果缓存。
- 工具权限控制。
- 订单系统的真实对接（仅 mock）。
- SSE 流式输出（由独立 spec 覆盖）。
- 混合检索和 RRF 融合（由独立 spec 覆盖）。