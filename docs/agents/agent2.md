# Agent2 功能介绍

## 角色定位

`Agent2` 是主链路执行者。

它不直接解释用户的模糊原始问题，而是严格依据 `Agent1` 生成的 `task_contract` 来完成图谱查询、取数、分析、可视化和报告生成。

---

## 核心职责

### 1. 按任务合同自主规划执行

`Agent2` 的特点不是被动照着固定步骤走，而是根据 `task_contract.required_capabilities` 和边界要求，自主决定：

- 工具调用顺序
- 步骤拆分方式
- 是否先查图谱还是先校验数据范围
- 遇到异常后的降级路径

### 2. 图谱查询与边界确认

虽然 `Agent1` 已经做过图谱辅助理解，但 `Agent2` 仍然需要基于合同再次使用 `nebula_graph_query` 进行执行侧确认，避免误解对象关系或字段来源。

### 3. 数据获取与 SQL 校验

`Agent2` 负责：

- 安全取数
- SQL 修复和调试
- 数据范围确认
- 合理性检查

### 4. 分析与可视化

`Agent2` 负责：

- 基础分析
- 进阶分析
- 图表生成
- 报告或 PPT 生成

最终它要输出一个可被 `Agent1` 审核的结构化结果，而不是只给一句自然语言结论。

---

## 当前会用到的工具

- `nebula_graph_query`
- `data_fetch`
- `sql_debug`
- `cache_manager`
- `basic_analysis`
- `advanced_analysis`
- `visualization`
- `ppt_generator`
- `problem_reporter`

当前策略下，`Agent2` 不直接调用 `Agent3` 的复盘工具，也不直接负责经验沉淀。

---

## 输入与输出

### 主要输入

- `Agent1` 产出的 `task_contract`

### 主要输出

- `knowledge_graph_result`
- `data_fetch_result`
- `sql_check_result`
- `analysis_result`
- `visualization_result`
- `final_report`
- 其他结构化执行结果

---

## 与问题上报的关系

`Agent2` 的问题样本是 `Agent3` 后续复盘的重要证据来源。

典型上报场景包括：

- SQL 报错
- 字段不存在
- 图谱查无结果
- 数据异常
- 样本不足
- 图表生成失败

当前仓库策略是：

- 先依赖 `tools/problem_reporter.py` 做标准化
- 暂时不把更强的格式约束直接写死进 `Agent2` 提示词
- 后续是否补 Agent 提示词，由人工评审真实记录质量后再决定

相关待办见：

- [Agent1 / Agent2 问题上报待办](/D:/app/work/wishSpace/workspace/yuanxi/docs/tasks/agent1-agent2-problem-reporting-todo.md)

---

## 不负责的事情

`Agent2` 不负责：

- 直接向用户澄清模糊需求
- 自行扩大业务范围
- 替代 `Agent1` 做最终审核
- 执行 `Agent3` 的复盘逻辑
- 自动把经验写进正式知识库

---

## 当前协作关系

```text
Agent1 -> task_contract
Agent2 -> 执行能力项
Agent2 -> 输出结构化结果
Agent1 -> 审核结果
Agent3 -> 读取 Agent2 执行结果做旁路复盘
```

`Agent2` 的目标是把“能执行的分析工作”做扎实，而不是承担系统治理职责。
