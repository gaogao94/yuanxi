# Agent1 / Agent2 问题上报待办

## 文档目的

这份文档用于替代直接修改 `agents/agent1.py`、`agents/agent2.py` 提示词的做法。

当前策略是：

- `tools/problem_reporter.py` 继续负责工具层标准化，保证落库结果可聚合、可审计。
- `Agent1`、`Agent2` 暂时不在代码里写死上报格式约束。
- 未来需要优化 Agent 提示词时，先以待办形式记录在这里，再由对应负责人决定何时改 Agent 本体。

这样做的原因是：

- 第一版还在快速验证 `Agent3` 的复盘质量，不希望频繁改动主链路 Agent。
- `problem_reporter` 已具备“宽进严出”的标准化能力，短期内可以兜住大部分格式漂移。
- 把待办写成文档后，人工评审会更清楚地看到“为什么要改、改什么、验收什么”。

---

## 待办一：Agent1 问题上报提示词补齐

**目标文件：** `agents/agent1.py`

**当前状态：** ⏳ 仅记录待办，暂不改代码

**修改目标：**

在 Agent1 的 `backstory` 和澄清任务描述里补充 `problem_reporter` 的填写约束，减少口径歧义、图谱异常、规划失败时的随意上报。

**建议补充的约束内容：**

```text
agent 固定填 Agent1
stage 只允许 clarification / knowledge / planning / review
problem 建议写成：问题: <歧义或异常>; 上下文: <用户问题/图谱返回/当前判断依据>
solution 建议写成：处理: <澄清动作、降级策略或后续建议>
severity 只允许 high / medium / low
```

**为什么这项待办存在：**

- Agent1 负责需求澄清和任务规划，它上报的问题会直接影响 Agent3 对“前置环节质量”的判断。
- 如果 Agent1 的 `stage`、`problem`、`solution` 写法漂移太大，Agent3 很难稳定区分“澄清歧义”“图谱缺口”“规划失败”。
- 虽然 `problem_reporter` 会兜底标准化，但提示词前置约束仍然能减少无效输入。

**验收标准：**

- Agent1 在遇到图谱查无结果、口径歧义、无法生成合同等情况时，会主动调用 `problem_reporter`。
- 上报内容与工具层标准化规则方向一致，不再大量依赖工具层猜测原意。
- 不引入 Agent3 复盘工具，不扩大 Agent1 的职责边界。

---

## 待办二：Agent2 问题上报提示词补齐

**目标文件：** `agents/agent2.py`

**当前状态：** ⏳ 仅记录待办，暂不改代码

**修改目标：**

在 Agent2 的角色说明和任务说明里补充 `problem_reporter` 的填写约束，统一执行阶段的问题上报格式。

**建议补充的约束内容：**

```text
agent 固定填 Agent2
stage 只允许 knowledge / data_fetch / sql_check / basic_analysis / advanced_analysis / visualization / review
problem 建议写成：问题: <错误或异常>; 上下文: <涉及表/字段/门店/时间条件>
solution 建议写成：处理: <已执行修复、替代字段、降级方案或待补动作>
severity 只允许 high / medium / low
```

**为什么这项待办存在：**

- Agent2 的问题记录是 Agent3 判断“取数质量、SQL 稳定性、分析可靠性”的核心样本来源。
- 如果 Agent2 上报时只写一句“SQL 错了”或“字段有问题”，后续复盘只能看到结果，看不到上下文证据。
- 统一模板后，Agent3 可以更稳定地抽取风险对象、生成整改建议候选项、沉淀知识候选项。

**验收标准：**

- Agent2 在 SQL 报错、字段缺失、样本不足、图表失败等场景下能稳定上报。
- 问题文本保留足够上下文，便于 Agent3 生成 `evidence`。
- 不把知识沉淀职责放回 Agent2，本轮仍然只做“问题上报”。

---

## 待办三：人工评审后再决定是否落地到 Agent 提示词

**当前状态：** ⏳ 待人工确认

**评审关注点：**

- 目前仅靠 `tools/problem_reporter.py` 的标准化，是否已经足够支撑 Agent3 复盘。
- 如果后续发现原始上报内容噪音仍然偏大，再把上述约束正式写回 Agent1/Agent2。
- 正式落地前，优先观察 `data/problem_reports.json` 中的真实记录质量，而不是先追求提示词“看起来更完整”。

**建议操作顺序：**

1. 先继续运行当前主链路，收集真实问题样本。
2. 人工抽查 `problem_reports.json`、`review_candidates.json`、`knowledge_candidates.json`。
3. 如果样本上下文不足，再按本待办修改 Agent1/Agent2 提示词。

---

## 与当前实现的关系

当前仓库中已经落地、且继续保留的能力：

- `tools/problem_reporter.py` 会自动规范化 `agent / stage / severity / problem / solution`
- `Agent3` 会读取标准化后的问题记录做风险抽取和候选项沉淀
- `review_candidates.json`、`knowledge_candidates.json` 仍然只记录，不自动执行

这意味着：

- 现在不改 `Agent1`、`Agent2`，系统仍然能跑
- 这份文档的作用是给后续人工改 Agent 时提供明确 TODO
- 当前阶段先把“规范”放在文档和工具层，而不是放在 Agent 提示词里
