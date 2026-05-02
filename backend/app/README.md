# Backend App

后端应用代码放在这里。

目录职责：

- `api/v1/endpoints`: HTTP 接口层，只处理请求参数、依赖注入和响应模型。
- `core`: 配置、日志、异常、鉴权依赖等基础能力。
- `domain`: 知识库、文档、chunk、检索结果等领域对象。
- `schemas`: Pydantic 请求和响应模型。
- `services`: 文档解析、索引构建、RAG 问答等业务编排。
- `repositories`: 数据访问抽象，后续可接 SQLite、PostgreSQL 或对象存储。
- `integrations`: Qdrant、LLM、Embedding 等外部服务适配器。
- `workers`: 后续异步索引任务。
