# Backend

FastAPI 后端服务目录。

后端采用分层结构组织代码，路由层只负责请求接入和响应返回，核心业务逻辑放在 service 层，外部系统适配放在 integration 层，避免把 RAG 流程直接堆在接口文件里。

计划结构：

```text
backend/
├── app/
│   ├── api/v1/endpoints/     # HTTP 路由
│   ├── core/                 # 配置、日志、异常、依赖注入
│   ├── domain/               # 领域对象和值对象
│   ├── schemas/              # Pydantic 请求/响应模型
│   ├── services/             # 文档处理、索引、检索、问答编排
│   ├── repositories/         # 数据访问与持久化抽象
│   ├── integrations/         # Qdrant、LLM、Embedding 等外部集成
│   ├── workers/              # 后续异步任务
│   └── main.py               # FastAPI 应用入口
├── tests/
├── Dockerfile
└── pyproject.toml
```
