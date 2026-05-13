import pytest

from app.tools.base import Tool
from app.tools.business_tools import (
    QueryInventoryTool,
    QueryInvoiceStatusTool,
    QueryMaterialPriceTool,
    QueryOrderStatusTool,
    QueryPurchasePlanTool,
    QueryWmsTaskStatusTool,
)
from app.tools.order_query import MockOrderQueryTool
from app.tools.registry import ToolRegistry


class _FakeTool(Tool):
    @property
    def name(self) -> str:
        return "fake"

    @property
    def description(self) -> str:
        return "A fake tool for testing"

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> dict:
        return {"status": "ok", **kwargs}


class TestToolBase:
    def test_cannot_instantiate_abstract_tool(self):
        with pytest.raises(TypeError):
            Tool()  # type: ignore[abstract]

    def test_concrete_tool_has_name(self):
        tool = MockOrderQueryTool()
        assert tool.name == "order_query"


class TestMockOrderQueryTool:
    async def test_execute_returns_structured_result(self):
        tool = MockOrderQueryTool()
        result = await tool.execute(order_id="ORD-001")
        assert result["order_id"] == "ORD-001"
        assert result["status"] == "已发货"
        assert result["amount"] == 299.00
        assert result["currency"] == "CNY"
        assert "_source" in result
        assert result["_source"] == "mock"
        assert len(result["items"]) == 1

    async def test_execute_handles_empty_order_id(self):
        tool = MockOrderQueryTool()
        result = await tool.execute(order_id="")
        assert result["order_id"] == ""

    def test_parameters_schema(self):
        tool = MockOrderQueryTool()
        params = tool.parameters
        assert params["type"] == "object"
        assert "order_id" in params["properties"]
        assert "order_id" in params["required"]


class TestBusinessTools:
    async def test_query_inventory(self):
        tool = QueryInventoryTool()
        result = await tool.execute(material_code="MAT-001")
        assert result["material_code"] == "MAT-001"
        assert "total_stock" in result
        assert result["_source"] == "mock"

    async def test_query_order_status(self):
        tool = QueryOrderStatusTool()
        result = await tool.execute(order_id="SO-20260501-001")
        assert result["order_id"] == "SO-20260501-001"
        assert "logistics" in result
        assert result["_source"] == "mock"

    async def test_query_material_price(self):
        tool = QueryMaterialPriceTool()
        result = await tool.execute(material_code="MAT-001")
        assert result["material_code"] == "MAT-001"
        assert "cost_price" in result
        assert result["_source"] == "mock"

    async def test_query_wmstask_status(self):
        tool = QueryWmsTaskStatusTool()
        result = await tool.execute(task_id="WMS-20260512-001")
        assert result["task_id"] == "WMS-20260512-001"
        assert "steps" in result
        assert result["_source"] == "mock"

    async def test_query_purchase_plan(self):
        tool = QueryPurchasePlanTool()
        result = await tool.execute(material_code="MAT-001")
        assert "planned_arrivals" in result
        assert result["_source"] == "mock"

    async def test_query_invoice_status(self):
        tool = QueryInvoiceStatusTool()
        result = await tool.execute(invoice_id="INV-20260501-001")
        assert result["invoice_id"] == "INV-20260501-001"
        assert "status" in result
        assert result["_source"] == "mock"


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = _FakeTool()
        registry.register(tool)
        assert registry.get("fake") is tool

    def test_get_missing_returns_none(self):
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(MockOrderQueryTool())
        registry.register(_FakeTool())
        names = [t.name for t in registry.list_tools()]
        assert "order_query" in names
        assert "fake" in names
