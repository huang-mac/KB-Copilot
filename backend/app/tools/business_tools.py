"""业务查询 Mock 工具集（库存/订单/物料/发票/WMS/采购）。"""

from app.tools.base import Tool


class QueryInventoryTool(Tool):
    """库存查询工具 — 返回物料库存 mock 数据。"""

    @property
    def name(self) -> str:
        return "query_inventory"

    @property
    def description(self) -> str:
        return "查询物料库存信息，输入物料编码或名称返回当前库存量、可用量、仓库分布等。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "material_code": {"type": "string", "description": "物料编码，如 MAT-001"},
                "warehouse": {"type": "string", "description": "仓库名称（可选）"},
            },
            "required": ["material_code"],
        }

    async def execute(self, material_code: str = "", warehouse: str = "", **kwargs) -> dict:
        return {
            "material_code": material_code or "MAT-001",
            "material_name": "高强度钢板 Q345",
            "total_stock": 12500,
            "available_stock": 8300,
            "reserved_stock": 4200,
            "unit": "kg",
            "warehouses": [
                {"name": warehouse or "A1-主仓", "stock": 8000},
                {"name": "B3-备件仓", "stock": 4500},
            ],
            "last_updated": "2026-05-12T08:00:00",
            "_source": "mock",
        }


class QueryOrderStatusTool(Tool):
    """销售订单状态查询工具 — 返回订单发货/物流 mock 数据。"""

    @property
    def name(self) -> str:
        return "query_order_status"

    @property
    def description(self) -> str:
        return "查询销售订单的发货状态和物流信息，输入订单号返回当前状态、物流单号、签收情况等。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "销售订单号，如 SO-20260501-001"},
            },
            "required": ["order_id"],
        }

    async def execute(self, order_id: str = "", **kwargs) -> dict:
        return {
            "order_id": order_id or "SO-20260501-001",
            "order_type": "销售订单",
            "status": "已发货",
            "logistics": {
                "carrier": "顺丰速运",
                "tracking_no": "SF1234567890",
                "status": "运输中",
                "estimated_delivery": "2026-05-15",
                "current_location": "上海分拣中心",
            },
            "items": [
                {"name": "高强度钢板 Q345", "quantity": 200, "unit": "kg"},
            ],
            "created_at": "2026-05-01T09:00:00",
            "_source": "mock",
        }


class QueryMaterialPriceTool(Tool):
    """物料价格查询工具 — 返回成本/售价 mock 数据。"""

    @property
    def name(self) -> str:
        return "query_material_price"

    @property
    def description(self) -> str:
        return "查询物料成本价或销售价，输入物料编码返回最新采购成本、建议售价等。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "material_code": {"type": "string", "description": "物料编码，如 MAT-001"},
            },
            "required": ["material_code"],
        }

    async def execute(self, material_code: str = "", **kwargs) -> dict:
        return {
            "material_code": material_code or "MAT-001",
            "material_name": "高强度钢板 Q345",
            "cost_price": 18.50,
            "suggested_sale_price": 25.00,
            "currency": "CNY",
            "unit": "kg",
            "supplier": "宝钢股份",
            "price_effective_from": "2026-05-01",
            "_source": "mock",
        }


class QueryWmsTaskStatusTool(Tool):
    """WMS 任务状态查询工具 — 返回仓储任务进度 mock 数据。"""

    @property
    def name(self) -> str:
        return "query_wmstask_status"

    @property
    def description(self) -> str:
        return "查询 WMS 仓库任务进度，输入任务号或关联订单号返回任务当前状态、进度、操作人等。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "WMS 任务号，如 WMS-20260512-001"},
                "order_id": {"type": "string", "description": "关联订单号（可选）"},
            },
            "required": ["task_id"],
        }

    async def execute(self, task_id: str = "", order_id: str = "", **kwargs) -> dict:
        return {
            "task_id": task_id or "WMS-20260512-001",
            "task_type": "拣货出库",
            "status": "进行中",
            "progress": "65%",
            "related_order_id": order_id or "SO-20260501-001",
            "assigned_operator": "张三",
            "started_at": "2026-05-12T08:30:00",
            "estimated_completion": "2026-05-12T16:00:00",
            "steps": [
                {"name": "生成拣货单", "status": "completed"},
                {"name": "拣货", "status": "in_progress"},
                {"name": "复核", "status": "pending"},
                {"name": "装车", "status": "pending"},
            ],
            "_source": "mock",
        }


class QueryPurchasePlanTool(Tool):
    """采购到货计划查询工具 — 返回未来到货 mock 数据。"""

    @property
    def name(self) -> str:
        return "query_purchase_plan"

    @property
    def description(self) -> str:
        return "查询未来到货计划，输入物料编码或日期范围返回预计到货时间、数量、供应商等。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "material_code": {"type": "string", "description": "物料编码（可选）"},
                "date_from": {"type": "string", "description": "查询起始日期（可选）"},
                "date_to": {"type": "string", "description": "查询截止日期（可选）"},
            },
            "required": [],
        }

    async def execute(self, material_code: str = "", date_from: str = "", date_to: str = "", **kwargs) -> dict:
        return {
            "material_code": material_code or "MAT-001",
            "material_name": "高强度钢板 Q345",
            "planned_arrivals": [
                {
                    "po_id": "PO-20260510-001",
                    "supplier": "宝钢股份",
                    "quantity": 5000,
                    "unit": "kg",
                    "estimated_arrival": "2026-05-20",
                    "status": "在途",
                },
                {
                    "po_id": "PO-20260512-002",
                    "supplier": "鞍钢集团",
                    "quantity": 3000,
                    "unit": "kg",
                    "estimated_arrival": "2026-05-25",
                    "status": "已发货",
                },
            ],
            "query_period": f"{date_from or '不限'} ~ {date_to or '不限'}",
            "_source": "mock",
        }


class QueryInvoiceStatusTool(Tool):
    """发票状态查询工具 — 返回发票开票/收票 mock 数据。"""

    @property
    def name(self) -> str:
        return "query_invoice_status"

    @property
    def description(self) -> str:
        return "查询发票开票或收票状态，输入发票号或关联订单号返回发票当前状态、金额、税务信息等。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string", "description": "发票号，如 INV-20260501-001"},
                "order_id": {"type": "string", "description": "关联订单号（可选）"},
            },
            "required": ["invoice_id"],
        }

    async def execute(self, invoice_id: str = "", order_id: str = "", **kwargs) -> dict:
        return {
            "invoice_id": invoice_id or "INV-20260501-001",
            "invoice_type": "增值税专用发票",
            "status": "已开票",
            "amount": 5000.00,
            "tax_amount": 650.00,
            "currency": "CNY",
            "related_order_id": order_id or "SO-20260501-001",
            "issued_at": "2026-05-02T10:00:00",
            "recipient": "XX制造有限公司",
            "_source": "mock",
        }


# ============================================================
# 预留：HTTP 工具调用 adapter（以 query_order_status 为例）
# 后续接入真实系统时取消注释，替换对应 Mock 工具。
# ============================================================
#
# import httpx
# from app.core.exceptions import ExternalProviderError
#
# BUSINESS_SERVICE_BASE_URL = "http://business-service:8080"
# BUSINESS_SERVICE_TIMEOUT = 10.0
#
#
# class HttpOrderStatusTool(Tool):
#     """HTTP 销售订单状态查询工具。"""
#
#     def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
#         self._http_client = http_client
#
#     @property
#     def name(self) -> str:
#         return "query_order_status"
#
#     @property
#     def description(self) -> str:
#         return "查询销售订单的发货状态和物流信息。"
#
#     @property
#     def parameters(self) -> dict:
#         return {
#             "type": "object",
#             "properties": {
#                 "order_id": {"type": "string", "description": "销售订单号"},
#             },
#             "required": ["order_id"],
#         }
#
#     async def execute(self, order_id: str = "", **kwargs) -> dict:
#         client = self._http_client or httpx.AsyncClient()
#         try:
#             response = await client.get(
#                 f"{BUSINESS_SERVICE_BASE_URL}/sales-orders/{order_id}",
#                 timeout=BUSINESS_SERVICE_TIMEOUT,
#             )
#             response.raise_for_status()
#             return response.json()
#         except httpx.TimeoutException as exc:
#             raise ExternalProviderError(f"订单服务超时: order_id={order_id}") from exc
#         finally:
#             if self._http_client is None:
#                 await client.aclose()
