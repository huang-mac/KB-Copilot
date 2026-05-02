# Frontend

React + Vite + TypeScript + Ant Design 前端目录。

前端按业务功能组织页面和组件，公共 API 客户端、类型、布局和通用组件独立维护，避免页面文件直接堆满请求逻辑和展示逻辑。

计划结构：

```text
frontend/
├── src/
│   ├── api/                  # axios 实例和后端接口封装
│   ├── assets/               # 静态资源
│   ├── components/           # 通用组件
│   ├── features/             # 知识库、文档、问答等业务模块
│   ├── layouts/              # 页面布局
│   ├── pages/                # 路由页面
│   ├── router/               # 路由配置
│   ├── styles/               # 全局样式
│   ├── types/                # TypeScript 类型
│   ├── utils/                # 工具函数
│   └── main.tsx              # 前端入口
├── Dockerfile
├── package.json
└── vite.config.ts
```
