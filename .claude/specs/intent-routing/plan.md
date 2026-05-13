# 意图识别与工具调用 plan.md

> 本文件回答"怎么做"。基于 spec.md 描述技术方案、模块设计、数据模型和接口设计。

## 技术方案

引入 LangGraph 编排问答流程，将现有单一 RAG 管线拆分为意图识别 → 路由 → 处理 → 回答生成的图结构。新增工具抽象层管理可复用工具，MVP3 先实现 mock 订单查询。

核心依赖：
- `langgraph`：图编排框架。
- 现有 `langchain-openai`：LLM 调用（含结构化输出）。

## 模块设计

```
backend/app/
├── graph/                          # 新增：LangGraph 编排
│   ├── __init__.py
│   ├── state.py                    # AgentState 定义
│   ├── nodes.py                    # 节点函数
│   └── graph.py                    # 图组装 + 运行入口
├── tools/                          # 新增：工具抽象层
│   ├── __init__.py
│   ├── base.py                     # Tool 抽象基类
│   ├── registry.py                 # ToolRegistry
│   └── order_query.py              # MockOrderQueryTool
├── api/v1/endpoints/
│   ├── chat.py                     # 修改：从 rag_service 切换到 graph
│   └── tools.py                    # 新增：POST /api/v1/tools/order-query
├── schemas/
│   └── chat.py                     # 修改：ChatResponse 增加 intent、tool_result
└── services/
    └── rag_service.py              # 保留，作为 kb_qa 节点的内部实现
```

### 分层职责

| 层 | 文件 | 职责 |
|---|---|---|
| API | `endpoints/chat.py` | 接收请求，调用 graph，返回响应 |
| API | `endpoints/tools.py` | 独立工具端点（调试/直接调用） |
| Graph | `state.py` | 定义图状态结构 |
| Graph | `nodes.py` | 各节点实现（意图识别、检索、工具执行、回答生成） |
| Graph | `graph.py` | 组装节点和边，暴露 `run()` 入口 |
| Tools | `base.py` | Tool 抽象接口 |
| Tools | `registry.py` | 工具注册与查找 |
| Tools | `order_query.py` | Mock 订单查询实现 |
| Service | `rag_service.py` | 保持现有检索+生成能力，被 kb_qa 节点调用 |

## 数据模型

### LangGraph 状态

```python
# graph/state.py
from typing import TypedDict

class AgentState(TypedDict):
    kb_id: str
    question: str
    history: str                       # 格式化的历史文本
    intent: str                        # kb_qa | order_query | clarification_required
    retrieval_results: list[dict]      # 向量检索结果
    tool_result: dict | None           # 工具执行结果
    answer: str
    sources: list[dict]                # 引用来源
    error: str | None
```

### 工具接口

```python
# tools/base.py
from abc import ABC, abstractmethod

class Tool(ABC):
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def parameters(self) -> dict: ...   # JSON Schema 格式

    @abstractmethod
    async def execute(self, **kwargs) -> dict: ...
```

### 请求/响应 Schema 变更

```python
# schemas/chat.py — ChatResponse 新增字段
class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[Source]
    intent: str | None = None           # 新增
    tool_result: dict | None = None     # 新增
```

## 图流程

```
                  ┌──────────────────┐
                  │  intent_classifier│
                  │  (LLM 结构化输出) │
                  └────────┬─────────┘
                           │
                    ┌──────▼──────┐
                    │   router    │  ← 条件边
                    └──┬──┬───┬──┘
                       │  │   │
            ┌──────────┘  │   └──────────┐
            ▼             ▼              ▼
    ┌───────────┐  ┌──────────┐  ┌──────────────────┐
    │  kb_qa    │  │order_query│  │clarification_rsp │
    │ (检索+生成)│  │(工具+生成)│  │  (固定引导文本)   │
    └─────┬─────┘  └────┬─────┘  └────────┬─────────┘
          │             │                 │
          └─────────────┴─────────────────┘
                        │
                        ▼
                  (END)
```

## 接口设计

### POST /api/v1/kbs/{kb_id}/chat（修改）

请求不变，响应增加可选字段：

```json
{
  "conversation_id": "conv-xxx",
  "answer": "...",
  "sources": [...],
  "intent": "order_query",
  "tool_result": {"order_id": "ORD-001", "status": "已发货", ...}
}
```

### POST /api/v1/tools/order-query（新增）

```json
// Request
{"order_id": "ORD-001"}

// Response
{
  "order_id": "ORD-001",
  "status": "已发货",
  "amount": 299.00,
  "currency": "CNY",
  "created_at": "2026-05-10T10:30:00",
  "items": [
    {"name": "商品A", "quantity": 2, "unit_price": 149.50}
  ],
  "_source": "mock"
}
```

## 配置设计

无新增配置项。工具注册通过代码完成，HTTP 工具 adapter 以注释保留。

## 错误处理

| 场景 | 处理 |
|---|---|
| 意图识别 LLM 调用失败 | 降级为 `kb_qa`，日志记录 |
| 意图识别返回非法值 | 降级为 `kb_qa` |
| 工具执行异常 | 返回 `{"error": "工具调用失败：<原因>"}`，写入 state.error |
| 检索失败 | 返回"检索暂时不可用"提示，不阻塞回答 |
| LLM 生成失败 | 返回明确错误信息给前端 |
| 图节点间状态传递异常 | LangGraph 框架级异常，由 chat endpoint 捕获并返回 500 |

## 测试策略

- 单元测试：Tool 基类和 MockOrderQueryTool 的 execute 方法。
- 单元测试：ToolRegistry 的注册和查找。
- 集成测试：LangGraph 图的三条路由路径各至少一个 case。
- 冒烟测试：`POST /api/v1/tools/order-query` 独立端点可访问。
- 回归测试：现有 `POST /api/v1/kbs/{kb_id}/chat` 无 conversation_id 场景仍正常返回。