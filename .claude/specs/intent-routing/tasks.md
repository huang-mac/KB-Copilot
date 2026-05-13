# 意图识别与工具调用 tasks.md

> 本文件将 plan.md 拆分为可执行、可验证的任务。

---

## 基础设施建设

- [x] **T1** 添加 `langgraph` 依赖到 `pyproject.toml`。
  - 验证：`pip list | grep langgraph` 输出版本号 `1.1.10`。

- [x] **T2** 创建 `backend/app/tools/` 模块：`__init__.py`、`base.py`、`registry.py`。
  - 验证：`from app.tools.base import Tool` 和 `from app.tools.registry import ToolRegistry` 无 ImportError。

- [x] **T3** 在 `base.py` 中定义 `Tool` 抽象基类：`name`、`description`、`parameters`（JSON Schema）、`async execute(**kwargs) -> dict`。
  - 验证：`Tool` 类有 `@abstractmethod execute`。

- [x] **T4** 在 `registry.py` 中实现 `ToolRegistry`：`register(tool)`、`get(name) -> Tool`、`list_tools() -> list[Tool]`。
  - 验证：注册 MockTool 后能通过 `get("mock")` 取回同一实例。

## Mock 工具实现

- [x] **T5** 创建 `backend/app/tools/order_query.py`，实现 `MockOrderQueryTool(Tool)`。
  - `parameters` 返回 `{"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}`。
  - `execute(order_id)` 返回固定 mock 数据（订单号、状态、金额、商品项、创建时间、`_source: "mock"`）。
  - 验证：`await tool.execute(order_id="ORD-001")` 返回完整 mock 订单字典。

- [x] **T6** 在同文件中以注释形式预留 HTTP 工具 adapter 代码骨架（HTTP 请求、超时、错误处理、response.json()）。
  - 验证：注释代码包含 `http_client.get()`、`ORDER_SERVICE_BASE_URL`、`timeout`、异常捕获。

## LangGraph 图实现

- [x] **T7** 创建 `backend/app/graph/` 模块：`__init__.py`、`state.py`。
  - 验证：无 ImportError。

- [x] **T8** 在 `state.py` 中定义 `AgentState(TypedDict)`：`kb_id`、`question`、`top_k`、`history`、`intent`、`retrieval_results`、`tool_result`、`answer`、`sources`、`error`。
  - 验证：类型检查通过。

- [x] **T9** 创建 `backend/app/graph/nodes.py`，实现以下节点函数：
  - `intent_classifier(state, llm_client)` → 更新 `intent`。使用 LLM 结构化输出，失败降级 `kb_qa`。
  - `kb_qa_node(state, rag_service)` → 调用 RAGService 检索+生成，更新 `answer`、`sources`。
  - `order_query_node(state, tool_registry)` → 从问题提取 order_id，调用工具，更新 `tool_result`；再调 LLM 生成回答。
  - `clarification_node(state)` → 设置引导性 `answer`。
  - 验证：各节点函数签名匹配 LangGraph 节点要求。

- [x] **T10** 创建 `backend/app/graph/graph.py`，组装 StateGraph：
  - `intent_classifier` → 条件边路由到 `kb_qa` / `order_query` / `clarification`。
  - 三条路径均指向 END。
  - 暴露 `async def run_graph(state) -> AgentState` 入口。
  - 验证：`graph.py` 可 import，`graph.compile()` 输出 5 个节点。

## API 适配

- [x] **T11** 修改 `backend/app/schemas/chat.py`，`ChatResponse` 增加 `intent: str | None = None` 和 `tool_result: dict | None = None`。
  - 验证：现有测试无破坏，新字段序列化正确。

- [x] **T12** 修改 `backend/app/api/v1/endpoints/chat.py`，从调用 `rag_service.answer()` 切换为调用 `run_graph()`，映射 AgentState 到 ChatResponse（包含 intent 和 tool_result）。
  - 验证：现有 `/chat` 请求仍正常返回，且 response JSON 中可看到 `intent` 字段。

- [x] **T13** 创建 `backend/app/api/v1/endpoints/tools.py`，实现 `POST /api/v1/tools/order-query`，注册到 v1 router。
  - 验证：`curl -X POST /api/v1/tools/order-query -d '{"order_id":"ORD-001"}'` 返回 mock 订单数据。

## 依赖注入适配

- [x] **T14** 在 `backend/app/core/dependencies.py` 中添加 `get_tool_registry()` 和 `get_graph()` 工厂函数。
  - 验证：DI 容器可注入 graph 和 tool_registry。

## 前端适配

- [x] **T15** 更新 `frontend/src/types/api.ts`，`ChatResponse` 增加 `intent?: string` 和 `tool_result?: Record<string, unknown>`。
  - 验证：TypeScript 编译无错误。

- [x] **T16** 更新 `frontend/src/App.tsx`，在助手消息卡片中展示意图标签和工具调用结果。
  - 验证：mock 订单查询的回答中能看到订单信息结构。

## 测试

- [x] **T17** 添加 `backend/tests/test_tools.py`：测试 `MockOrderQueryTool.execute()` 和 `ToolRegistry` 注册/查找。
  - 验证：`pytest backend/tests/test_tools.py -v` 通过。

- [x] **T18** 添加 `backend/tests/test_intent_routing.py`：测试订单号提取、历史解析、图编译、Mock LLM 意图分类。
  - 验证：`pytest backend/tests/test_intent_routing.py -v` 通过。

## 文档

- [x] **T19** 更新 `docs/MVP3.md` 中工具调用骨架的状态标注。
- [x] **T20** README 无逐条 API 列表，无需改动。