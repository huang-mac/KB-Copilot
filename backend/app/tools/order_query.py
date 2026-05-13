from app.tools.base import Tool


class MockOrderQueryTool(Tool):
    """Mock 订单查询工具，返回固定格式的模拟订单数据。"""

    @property
    def name(self) -> str:
        return "order_query"

    @property
    def description(self) -> str:
        return "查询订单信息，输入订单号返回订单详情、状态、金额、商品明细等。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "订单号，格式如 ORD-001",
                }
            },
            "required": ["order_id"],
        }

    async def execute(self, order_id: str = "", **kwargs) -> dict:
        return {
            "order_id": order_id,
            "status": "已发货",
            "amount": 299.00,
            "currency": "CNY",
            "created_at": "2026-05-10T10:30:00",
            "items": [
                {"name": "商品A", "quantity": 2, "unit_price": 149.50},
            ],
            "_source": "mock",
        }


# ============================================================
# 预留：HTTP 工具调用 adapter
# 后续接入真实订单系统时，取消下方注释并替换 MockOrderQueryTool。
# ============================================================
#
# import httpx
# from app.core.exceptions import ExternalProviderError
#
# ORDER_SERVICE_BASE_URL = "http://order-service:8080"
# ORDER_SERVICE_TIMEOUT = 10.0
#
#
# class HttpOrderQueryTool(Tool):
#     """HTTP 订单查询工具，通过 HTTP 调用真实订单服务。"""
#
#     def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
#         self._http_client = http_client
#
#     @property
#     def name(self) -> str:
#         return "order_query"
#
#     @property
#     def description(self) -> str:
#         return "查询订单信息，输入订单号返回订单详情。"
#
#     @property
#     def parameters(self) -> dict:
#         return {
#             "type": "object",
#             "properties": {
#                 "order_id": {"type": "string", "description": "订单号"},
#             },
#             "required": ["order_id"],
#         }
#
#     async def execute(self, order_id: str = "", **kwargs) -> dict:
#         client = self._http_client or httpx.AsyncClient()
#         try:
#             response = await client.get(
#                 f"{ORDER_SERVICE_BASE_URL}/orders/{order_id}",
#                 timeout=ORDER_SERVICE_TIMEOUT,
#             )
#             response.raise_for_status()
#             return response.json()
#         except httpx.TimeoutException as exc:
#             raise ExternalProviderError(
#                 f"订单服务超时: order_id={order_id}"
#             ) from exc
#         except httpx.HTTPStatusError as exc:
#             raise ExternalProviderError(
#                 f"订单服务返回错误: {exc.response.status_code}"
#             ) from exc
#         except Exception as exc:
#             raise ExternalProviderError(
#                 f"订单服务调用失败: {exc}"
#             ) from exc
#         finally:
#             if self._http_client is None:
#                 await client.aclose()
