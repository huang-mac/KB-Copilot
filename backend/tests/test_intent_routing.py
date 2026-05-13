from app.graph.graph import build_graph
from app.graph.nodes import _parse_history
from app.integrations.llm import MockLLMClient
from app.tools.business_tools import QueryOrderStatusTool
from app.tools.registry import ToolRegistry


class TestHistoryParsing:
    def test_empty_history(self):
        assert _parse_history("") == []

    def test_parse_user_and_assistant(self):
        history = "用户：什么是KB Copilot\n助手：KB Copilot是..."
        result = _parse_history(history)
        assert len(result) == 2
        assert result[0] == ("user", "什么是KB Copilot")
        assert result[1] == ("assistant", "KB Copilot是...")


class TestGraphAssembly:
    def test_build_graph_compiles(self):
        registry = ToolRegistry()
        registry.register(QueryOrderStatusTool())
        llm = MockLLMClient()

        graph = build_graph(
            rag_service=None,
            llm_client=llm,
            tool_registry=registry,
        )
        compiled = graph.compile()
        node_names = list(compiled.nodes.keys())
        assert "intent_classifier" in node_names
        assert "kb_qa" in node_names
        assert "tool_executor" in node_names
        assert "clarification" in node_names


class TestMockLLMIntentClassification:
    def test_inventory_intent(self):
        result = _classify("查一下 MAT-001 的库存")
        assert result == "query_inventory"

    def test_invoice_intent(self):
        result = _classify("INV-20260501-001 这张发票开了没")
        assert result == "query_invoice_status"

    def test_wms_task_intent(self):
        result = _classify("WMS-20260512-001 的拣货任务完成了没")
        assert result == "query_wmstask_status"

    def test_order_status_intent(self):
        result = _classify("SO-20260501-001 发货了没")
        assert result == "query_order_status"

    def test_material_price_intent(self):
        result = _classify("MAT-001 现在什么价格")
        assert result == "query_material_price"

    def test_purchase_plan_intent(self):
        result = _classify("PO-20260510-001 什么时候到货")
        assert result == "query_purchase_plan"

    def test_clarification_for_short_greeting(self):
        result = _classify("你好")
        assert result == "clarification_required"

    def test_default_to_kb_qa(self):
        result = _classify("产品A的规格是什么")
        assert result == "kb_qa"


def _classify(question: str) -> str:
    import asyncio
    llm = MockLLMClient()
    return asyncio.run(
        llm.generate_text(system_prompt="classify", user_message=question)
    )
