from abc import ABC, abstractmethod


class Tool(ABC):
    """工具抽象基类，所有工具需继承并实现 execute 方法。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称，用于注册和路由。"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述，用于 LLM 选择工具时参考。"""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """工具参数 JSON Schema，描述输入参数格式。"""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> dict:
        """执行工具，返回结构化结果字典。"""
        ...
