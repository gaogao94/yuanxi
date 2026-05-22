# Agent1 功能介绍

## 角色定位

`Agent1` 是主链路入口和主链路出口审核者。

它的核心职责不是直接干数据分析，而是把用户的模糊业务问题整理成 `Agent2` 可执行、可验证、可审计的任务合同，并在 `Agent2` 完成后做结果审核。

---

## 核心职责

### 1. 需求澄清

`Agent1` 负责识别用户问题里的业务目标、指标口径、时间范围、门店范围、人群范围和交付预期。

当信息不完整时，它会返回澄清问题，而不是直接让 `Agent2` 开工。

### 2. 图谱辅助理解

`Agent1` 会使用 `nebula_graph_query` 查询图谱，辅助理解：

- 用户提到的业务对象是什么
- 对象之间有哪些关系
- 本轮分析应该把图谱边界限定在哪里

### 3. 任务合同生成

当信息足够完整时，`Agent1` 会生成结构化 `task_contract`，作为 `Agent2` 的唯一业务执行依据。

这里强调的是“定义能力要求和边界”，而不是替 `Agent2` 写死每一步怎么做。

### 4. 结果审核

`Agent2` 执行完成后，`Agent1` 会审核：

- 是否完成了要求的能力项
- 是否越界取数
- 指标口径是否一致
- 是否有足够证据支撑结论
- 是否存在隐私或安全问题

---

## 当前会用到的工具

- `nebula_graph_query`
- `problem_reporter`

当前策略下，`Agent1` 不直接使用 `Agent3` 的复盘工具，也不负责知识沉淀。

---

## 输入与输出

### 主要输入

- 用户原始问题
- Workflow 传入的上下文
- 图谱查询结果
- `Agent2` 的结构化执行结果

### 主要输出

- `clarification_result`
- `graph_scope`
- `task_contract`
- `review_result`

---

## 与问题上报的关系

`Agent1` 在以下场景应该考虑调用 `problem_reporter`：

- 图谱查不到目标业务词
- 口径歧义无法自动消解
- 无法生成稳定的任务合同
- 审核阶段发现主结果存在关键缺口

但当前仓库策略是：

- 先由 `tools/problem_reporter.py` 做工具层标准化
- 暂时不把更强的格式约束直接写死进 `Agent1` 提示词
- 如果后续人工评审认为问题样本质量不够，再按待办文档推进

相关待办见：

- [Agent1 / Agent2 问题上报待办](/D:/app/work/wishSpace/workspace/yuanxi/docs/tasks/agent1-agent2-problem-reporting-todo.md)

---

## 不负责的事情

`Agent1` 不负责：

- 直接取业务数据
- 直接执行 SQL
- 做基础统计或进阶分析
- 生成图表或 PPT
- 执行旁路复盘
- 自动沉淀经验到知识库

---

## 当前协作关系

```text
Workflow -> Agent1
Agent1 -> 生成 task_contract
Workflow -> Agent2
Agent2 -> 输出执行结果
Workflow -> Agent1
Agent1 -> 输出 review_result / final_user_output
```

`Agent3` 会读取这条链路的产物做旁路复盘，但不会改变 `Agent1` 的主链路职责。
