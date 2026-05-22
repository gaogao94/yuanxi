# Agent3 功能介绍

## 角色定位

`Agent3` 是旁路非阻塞的洞察与复盘 Agent。

它不负责主报告交付，不改变主链路执行顺序，也不替 `Agent1`、`Agent2` 做它们本该做的工作。它的职责是读取主链路产物，做全流程复盘、问题诊断、优化建议沉淀和经验候选沉淀。

---

## 当前核心能力

### 1. 全流程复盘

`Agent3` 现在会基于真实输入做 deterministic 复盘，输入来源包括：

- `agent1_output`
- `agent2_result`
- `review_result`
- `process_log`
- `problem_records`

它不再依赖早期那种“写死文案”的 mock 逻辑。

### 2. 风险对象生成

`Agent3` 会把 findings 结构化成显式风险对象，包含：

- `category`
- `title`
- `risk_level`
- `owner`
- `action`
- `evidence`
- `section`

这样后续不只是“看报告”，还可以按风险等级、责任归属和证据链继续做人工筛选。

### 3. 结构化复盘输出

除了 Markdown 文本，`Agent3` 还会输出 `structured_review`，当前 schema 重点包括：

- `schema_version`
- `overview`
- `problem_summary`
- `process_insights`
- `risk_summary`
- `risk_objects`
- `sections`
- `snapshots`

### 4. 候选项沉淀

当前第一版不会自动执行整改，也不会自动正式入库，而是只记录待人工审核的候选项：

- 图谱/流程优化建议 → `review_candidates.json`
- 经验沉淀内容 → `knowledge_candidates.json`

默认状态都是 `pending_review`。

---

## 当前会用到的数据与工具

### 主要输入来源

- `tools/problem_store.py`
- `tools/problem_collector.py`
- Workflow 传入的 `process_log`
- Agent1 / Agent2 的真实执行结果

### 相关存储

- `data/problem_reports.json`
- `data/review_candidates.json`
- `data/knowledge_candidates.json`

### 当前实现特点

- 主流程失败隔离，`Agent3` 异常不阻断主报告
- 支持结构化风险对象
- 支持候选整改项与候选知识项沉淀
- 详细中文注释已经补入代码，便于后续迭代

---

## 解决的问题

`Agent3` 主要解决这些系统级问题：

- 主链路做完了，但不知道哪里还容易踩坑
- 问题样本有了，但没有统一复盘视角
- 图谱/流程优化建议散落在文本里，不好人工筛选
- 经验能总结出来，但还没有稳定候选池

---

## 当前不做的事情

`Agent3` 当前明确不做：

- 不自动执行整改
- 不自动修改图谱
- 不自动修改 Workflow
- 不自动把候选经验写入正式知识库
- 不阻塞主报告返回

这不是能力缺失，而是当前产品策略有意收敛：

- 第一版先记录
- 先人工筛选
- 先验证内容质量
- 等人工确认机制稳定后，再考虑是否自动推进下一步

---

## 当前协作关系

```text
Agent1 / Agent2 / Workflow
  ↓
主链路产物 + process_log + problem_records
  ↓
Agent3
  ↓
structured_review + report_markdown
  ↓
review_candidates.json / knowledge_candidates.json
```

---

## 与旧文档的关系

旧的 `agent3-onboarding-tasks` 更偏“接入待办”，里面包含不少已经过时的接入假设，比如：

- 让 Agent1 / Agent2 主动接知识库查询职责
- 早期对 Agent3 工具形态和知识写回方式的假设

当前已经改成：

- `docs/agents/agent3.md` 负责说明 Agent3 现在到底是什么
- `docs/tasks/` 只保留仍需人工推进的待办
