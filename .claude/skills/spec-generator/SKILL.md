---
name: spec-generator
description: 为 KB Copilot 创建或更新 SDD 三件套。当用户要求生成 MVP、功能规格、spec、plan、tasks 或推进 SDD 流程时使用。
---

# Spec Generator

这个 skill 用于在 `.claude/specs/<feature>/` 下生成或更新 SDD 三件套：

- `spec.md`：需求文档，回答“要做什么”。
- `plan.md`：技术方案，回答“怎么做”。
- `tasks.md`：任务清单，回答“怎么一步步实现”。

模板来源：

- `.specify/templates/spec-template.md`
- `.specify/templates/plan-template.md`
- `.specify/templates/tasks-template.md`

顶层约束：

- `.specify/memory/constitution.md`

## 使用流程

### 1. 确认目标

先确认以下信息，不要直接写代码：

- feature 或 MVP 的英文目录名，例如 `mvp3`、`hybrid-search`、`intent-routing`。
- 业务目标：这个能力要解决什么问题。
- 范围边界：明确包含什么、不包含什么。
- 当前阶段：属于 MVP1、MVP2、MVP3、MVP4 还是独立能力。

如果信息不足，先向用户提问。

### 2. 生成或更新 `spec.md`

`spec.md` 只写需求，不写技术实现。

必须包含：

- 目标
- 用户故事
- EARS 需求
- API 需求（如果有）
- 数据需求（如果有）
- 验收标准
- 不包含

完成后提醒用户确认需求是否准确，再继续 `plan.md`。

### 3. 生成或更新 `plan.md`

`plan.md` 基于 `spec.md` 描述实现方案。

必须包含：

- 技术方案
- 模块设计
- 数据模型
- 状态流
- 接口设计
- 配置设计
- 错误处理
- 测试策略

涉及流程编排时，优先使用文本流程图；如果用户要求架构图，再补 Mermaid。

### 4. 生成或更新 `tasks.md`

`tasks.md` 将 `plan.md` 拆成可执行任务。

要求：

- 使用 checkbox。
- 每个任务必须可验证。
- 任务应能回溯到 `spec.md` 的需求或验收标准。
- 不把后续 MVP 的能力混入当前任务。

### 5. 完成后检查

生成完成后检查：

- 三件套路径是否为 `.claude/specs/<feature>/spec.md`、`plan.md`、`tasks.md`。
- 是否遵守 `.specify/memory/constitution.md`。
- README 或阶段文档是否需要补链接。

## 输出要求

- 全程使用简体中文。
- 不要一次性扩大范围。
- 如果用户只要求生成 spec，就只生成 `spec.md`。
- 如果用户要求完整 SDD，可以按 `spec.md -> plan.md -> tasks.md` 顺序生成。
