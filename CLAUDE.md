# KB Copilot Agent Guide

## 项目定位

KB Copilot 是面向中小企业的智能知识库问答助手，当前核心能力包括文档上传、向量化索引、语义检索、RAG 问答、引用来源、文档管理、会话历史和多轮追问。

当前阶段：**MVP2 已完成**。MVP3 将推进基础设施与检索编排增强。

## SDD 开发规则

本项目采用 Spec-Driven Development。

### 核心纪律

- **No Spec, No Code**：没有对应 `spec.md`，不得开始业务实现。
- **No Plan, No Architecture**：没有 `plan.md`，不得擅自确定技术方案。
- **No Tasks, No Claim Done**：没有 `tasks.md`，不得宣称任务可执行或已完成。
- 需求变更必须先更新 `spec.md`，再同步 `plan.md` 和 `tasks.md`。
- 实现完成后必须回查 `spec.md` 的验收标准。

### 三件套位置

实际规格实例放在：

```text
.claude/specs/<feature>/
├── spec.md
├── plan.md
└── tasks.md
```

模板和项目宪法放在：

```text
.specify/
├── memory/
│   └── constitution.md
└── templates/
    ├── spec-template.md
    ├── plan-template.md
    └── tasks-template.md
```

### 标准流程

1. 指定：生成 `spec.md` 来描述需求。
2. 计划：根据 `spec.md` 生成 `plan.md`，确定技术方案。
3. 任务：将 `plan.md` 拆解为可执行的 `tasks.md`。
4. 实现：依次完成 `tasks.md` 中的任务，并校验是否符合 `spec.md`。

## 当前 Specs

- MVP1：`.claude/specs/mvp1/`
- MVP2：`.claude/specs/mvp2/`

MVP3 新能力应优先拆成独立 spec，例如：

- `.claude/specs/mvp3/`
- `.claude/specs/intent-routing/`
- `.claude/specs/hybrid-search/`
- `.claude/specs/async-indexing/`
- `.claude/specs/sse-streaming/`

## 技术栈

- 前端：React + Vite + TypeScript + Ant Design。
- 后端：Python 3.11 + FastAPI + LangChain。
- 向量库：Qdrant。
- 元数据：SQLite，MVP3 计划兼容 MySQL。
- 对象存储：MinIO，可选启用。
- 部署：Docker Compose。

## 后端规则

- 后端依赖统一使用项目根目录 `.venv`。
- 不要向全局 Python 环境安装依赖。
- 新增依赖前先说明用途和替代方案。
- 优先保持 `api -> service -> repository/integration` 分层。
- 外部系统调用必须有明确错误处理和超时策略。

## 前端规则

- TypeScript 类型必须明确。
- API 调用集中在 `frontend/src/api/client.ts`。
- 共享响应类型放在 `frontend/src/types/api.ts`。
- loading、error、empty 状态必须可见。
- SSE、定时器、订阅等资源必须清理。

## Skills

### spec-generator

当用户说“生成 spec”“创建 MVP”“按 SDD 拆任务”等，使用 `.claude/skills/spec-generator/SKILL.md`：

- 收集 feature 名称和目标。
- 生成或更新 `spec.md`。
- 基于 `spec.md` 生成 `plan.md`。
- 基于 `plan.md` 生成 `tasks.md`。

### code-review

当用户说“review 代码”“检查完成情况”“看看有没有问题”等，使用 `.claude/skills/code-review/SKILL.md`：

- 基于 git diff 做增量 review。
- 对照 `.claude/specs/<feature>/` 检查需求覆盖。
- 核查 `tasks.md` 是否存在虚假完成。
- 输出代码质量、测试缺口和优先修复建议。

## 本地文件规则

- `.claude/settings.local.json` 是本地权限配置，不应提交。
- `.env`、`.env.*` 不应提交，只有 `.env.example` 可以提交。
- `data/`、本地上传文件、运行时存储不应提交。

## 文档同步规则

修改阶段范围、API、配置或 SDD 结构时，必须同步检查：

- `README.md`
- `docs/MVP*.md`
- `.claude/specs/<feature>/`
- `.specify/templates/`
- `.env.example`
