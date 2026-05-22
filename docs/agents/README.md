# Agents 文档总览

这个目录用于集中说明 `Agent1`、`Agent2`、`Agent3` 的职责边界、输入输出、当前实现状态和后续协作方式。

当前约定是：

- `docs/requirements/` 保留偏需求设计、流程设计、系统边界类文档。
- `docs/tasks/` 保留需要人工跟进的待办类文档。
- `docs/agents/` 专门放三个 Agent 的功能介绍，方便新人快速理解系统分工。

---

## 目录说明

- [Agent1 功能介绍](/D:/app/work/wishSpace/workspace/yuanxi/docs/agents/agent1.md)
- [Agent2 功能介绍](/D:/app/work/wishSpace/workspace/yuanxi/docs/agents/agent2.md)
- [Agent3 功能介绍](/D:/app/work/wishSpace/workspace/yuanxi/docs/agents/agent3.md)

---

## 三个 Agent 的整体分工

```text
用户问题
  ↓
Workflow / Coordinator
  ↓
Agent1：需求澄清、图谱辅助理解、任务合同生成、结果审核
  ↓
Agent2：图谱查询、取数、SQL 校验、分析、可视化、报告生成
  ↓
Agent1：审核 Agent2 结果并整理主报告

旁路非阻塞：
Agent3：全流程复盘、问题诊断、图谱/流程优化建议、经验候选沉淀
```

---

## 当前文档策略

为了避免把所有信息混在一个大文档里，这里做了两层拆分：

- 如果想了解“系统为什么这样设计”，优先看 `docs/requirements/`
- 如果想了解“某个 Agent 现在到底负责什么”，优先看 `docs/agents/`
- 如果想了解“后面还要人工补什么”，优先看 `docs/tasks/`

---

## 相关待办

- [Agent1 / Agent2 问题上报待办](/D:/app/work/wishSpace/workspace/yuanxi/docs/tasks/agent1-agent2-problem-reporting-todo.md)
