# KB Copilot Constitution

> 本文件是项目 SDD 的顶层规则。任何 spec、plan、tasks 和实现都不得违背本文件。

## 1. Spec First

- 没有 `spec.md`，不得开始业务代码实现。
- 没有 `plan.md`，不得确定技术实现路径。
- 没有 `tasks.md`，不得宣称进入可执行开发阶段。
- 需求变化必须先更新 `spec.md`，再同步 `plan.md` 和 `tasks.md`。

## 2. Scope Discipline

- 每个 MVP 只实现该阶段明确列入范围的能力。
- 不把后续 MVP 的能力以“顺手实现”的方式混入当前阶段。
- 对外部系统、鉴权、多租户、权限过滤等高复杂度能力，必须先进入对应 MVP 的 spec。

## 3. Verifiable Tasks

- `tasks.md` 中的每个任务必须能被代码、文档、测试或运行结果验证。
- 任务完成后才能勾选 `[x]`。
- 禁止任务未实现就提前标记完成。

## 4. Local First

- 本项目优先保证本地可启动、可演示、可冒烟测试。
- 默认配置应尽量降低依赖门槛。
- 外部模型、MinIO、MySQL、rerank 等能力必须提供明确配置说明。

## 5. Clear Failure

- 失败不能静默吞掉。
- 文档解析、Embedding、LLM、Qdrant、MinIO、数据库和工具调用错误都应返回可理解的错误信息。
- 前端必须展示关键失败原因。

## 6. Conservative Engineering

- 优先复用现有模块和模式。
- 不为未进入 spec 的未来能力提前设计复杂抽象。
- 新增依赖必须能解释必要性，并同步更新文档。

## 7. Testable Delivery

- 高风险逻辑必须有测试或可复现验证方式。
- 文档变更至少要保证链接、路径、阶段状态一致。
- 实现完成后要回查 `spec.md` 的验收标准。
