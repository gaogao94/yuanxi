# Agent1 与 Agent2 图谱驱动需求澄清需求文档

## 文档状态

- 状态：Draft
- 日期：2026-05-19
- 当前实现范围：Agent1、Agent2、Workflow 主链路
- 当前不纳入范围：Agent3 执行、Agent3 复盘、知识沉淀实现、长期知识库治理
- 核心结论：Agent1 必须 CrewAI 化；Agent1 的澄清知识来源是图数据库；Agent1/Agent2 只把问题和缺口上报给未来 Agent3，不处理知识沉淀。

## 背景和目标

当前系统要先完成 Agent1/Agent2 主链路。

Agent1 负责把用户自然语言问题转成结构化分析任务合同。澄清过程中，Agent1 需要查询图数据库 API，拿到图数据库返回的 schema、点和边，再基于这些图谱信息生成澄清问题或任务合同。

Agent2 负责接收 Agent1 的任务合同，并根据合同自主规划图谱查询、取数、SQL 校验、分析和报告生成的执行步骤。

Agent3 当前不参与主链路，也不需要现在实现。Agent1/Agent2 只需要把执行中发现的问题、图谱缺口、口径歧义、数据异常上报出去，作为未来 Agent3 复盘输入。

目标流程：

```text
用户问题
  ↓
Workflow / Coordinator
  ↓
Agent1：识别业务词 → 查询图数据库 → 需求澄清 → 生成 task_contract
  ↓
Agent2：按 task_contract 自主规划并执行取数、分析、可视化、报告
  ↓
Agent1：审核 Agent2 输出
  ↓
主报告

旁路数据：
Agent1 / Agent2 → problem_reporter → 问题记录 → 未来 Agent3 使用
```

## 当前范围

### 本期必须做

- Agent1 查询图数据库辅助澄清。
- Agent1 必须以 CrewAI Agent 形式运行，能够主动调用 `knowledge_graph_query` 和 `problem_reporter`。
- Agent1 根据图谱上下文生成选项式澄清问题。
- Agent1 在信息完整时生成 Agent2 可执行的 `task_contract`。
- Agent2 只接收 `task_contract`，不直接解释用户原始问题。
- Agent1 审核 Agent2 输出。
- Agent1/Agent2 发现问题时上报给未来 Agent3。

### 本期不做

- 不实现 Agent3 调用链路。
- 不读取 Agent3 的沉淀结果。
- 不维护 `data/knowledge_base.json` 作为 Agent1 的知识来源。
- 不让 Agent1/Agent2 做知识沉淀。
- 不让 Agent1/Agent2 直接写入图数据库沉淀知识。
- 不做真实用户权限系统。
- 不做真实数据库写入。
- 不做蜂群式 Agent handoff。

## 系统角色边界

### Workflow / Coordinator

Workflow 是代码层编排器。

职责：

- 接收用户问题。
- 调用 Agent1 前置澄清和规划。
- 如果 Agent1 返回 `needs_clarification`，把澄清问题返回给用户。
- 如果 Agent1 返回 `ready`，把 `task_contract` 交给 Agent2。
- 将 Agent2 输出交回 Agent1 审核。
- 输出主报告、返工要求或阻断原因。
- 记录过程日志。

不做：

- 不解释业务问题。
- 不判断指标口径。
- 不查询业务数据。
- 不替 Agent 决策。
- 当前不触发 Agent3。

### Agent1

Agent1 是主链路入口和出口审核者。

Agent1 必须 CrewAI 化：需要定义 CrewAI `Agent`、`Task` 和可调用 tools，让 LLM 能基于用户问题主动调用图数据库工具，再输出结构化澄清结果。当前确定性 `Agent1` 类保留为结构校验、合同规范化和审核核心，不替代 CrewAI Agent。

前置职责：

- 从用户问题中识别业务词，例如“转化率”“复诊率”“门店”“医生”“渠道”。
- 调用图数据库 API 获取业务词相关上下文。
- 基于图谱上下文识别指标口径、候选对象、关联实体、字段、常见歧义。
- 判断用户问题是否缺少必填信息。
- 生成选项式澄清问题。
- 在需求完整时生成 `clarification_result`、`graph_scope`、`task_contract`。
- 发现图谱缺口、口径缺失、权限不明时，上报问题。

后置职责：

- 审核 Agent2 是否满足 `task_contract.required_capabilities` 和验收标准。
- 审核 Agent2 输出是否符合指标口径。
- 审核数据范围是否越过合同范围。
- 审核结论是否有证据。
- 审核输出是否有隐私泄漏。
- 输出 `review_result` 和最终主报告。

不做：

- 不直接执行 SQL。
- 不读取业务宽表。
- 不做统计计算。
- 不生成图表或 PPT。
- 不做知识沉淀。
- 不读取 Agent3 的沉淀。
- 不调用 Agent3 复盘工具。

### Agent1 CrewAI 化要求

CrewAI 化不是把现有 Python 类删掉，而是在确定性核心外增加一层 CrewAI Agent 包装。

推荐分层：

```text
CrewAI scheduler_agent
  ↓ 调用 tools
knowledge_graph_query / problem_reporter
  ↓ 输出草稿 JSON
Agent1 deterministic core
  ↓ 校验、规范化、补齐默认字段
clarification_result / graph_scope / task_contract
```

CrewAI Agent1 职责：

- 理解用户自然语言问题。
- 判断需要查询哪些图谱关键词。
- 主动调用 `knowledge_graph_query`。
- 阅读图数据库返回的 `schema`、`vertices`、`edges`。
- 生成结构化澄清草稿。
- 在发现图谱缺口或无法规划时调用 `problem_reporter`。

确定性核心职责：

- 校验 CrewAI 输出是否包含必填字段。
- 规范化输出结构。
- 生成稳定 `task_id`。
- 生成稳定 `task_contract`，包含澄清后的任务、边界、能力要求、验收标准和交付要求。
- 审核 Agent2 输出。
- 在没有 LLM Key 时提供本地测试和降级能力。

Agent1 CrewAI Agent 需要挂载的 tools：

```python
tools=[
    KnowledgeGraphQueryTool(),
    ProblemReporterTool(),
]
```

Agent1 CrewAI Agent 不允许挂载：

```python
KnowledgeBaseQueryTool()
DataFetchTool()
BasicAnalysisTool()
AdvancedAnalysisTool()
VisualizationTool()
PPTGeneratorTool()
Agent3 复盘工具
```

Agent1 CrewAI Task 的输出必须是 JSON 字符串，Workflow 必须解析并交给确定性核心校验。

### Agent2

Agent2 是执行者。

职责：

- 只接收 Agent1 输出的 `task_contract`。
- 根据合同自主规划执行步骤和工具调用顺序，完成图谱查询、业务取数、SQL 检查、缓存、基础分析、进阶分析、可视化和报告生成。
- 输出结构化 `agent2_result`。
- 遇到问题时上报，例如 SQL 报错、字段缺失、数据异常、图谱缺口。

不做：

- 不向用户澄清需求。
- 不重新解释原始问题。
- 不自行扩大分析范围。
- 不做最终审核。
- 不做知识沉淀。
- 不调用 Agent3 复盘工具。

### Agent3

Agent3 是未来的旁路复盘者，本期不实现、不调用、不纳入主链路。

本期只需要给 Agent3 预留输入：

```text
Agent1 / Agent2 → problem_reporter → problem_reports
```

也就是说，Agent1/Agent2 只负责“上报问题”，不负责“沉淀知识”。

## Agent1 澄清流程

### 1. 识别业务词

Agent1 从用户原始问题中提取业务词。

示例：

```text
用户输入：帮我看看最近门店转化怎么样
识别业务词：转化、门店、最近
```

候选业务词类型：

- 指标：转化率、初诊转化率、复诊率、营收、预约量。
- 实体：患者、门店、医生、会员、预约、账单、渠道。
- 维度：时间、门店、医生、渠道、人群。
- 输出：Markdown、PPT、图表、报告。

### 2. 查询图数据库数据

Agent1 必须优先查询图数据库 API，而不是查询 Agent3 的知识库。

核心工具：

```text
knowledge_graph_query
```

工具输入：

```json
{
  "keyword": "转化率",
  "user_question": "帮我看看最近门店转化怎么样",
  "purpose": "clarification"
}
```

接口返回的数据结构大致如下，所有澄清需要的信息都从这个结构中读取：

```json
{
  "space": "medgraph",
  "version": "3.8.0",
  "schema": {
    "tags": {
      "患者": {
        "note": "string",
        "描述": "string",
        "数据库位置": "string",
        "其他备注": "string"
      },
      "初诊医生": {
        "note": "string",
        "描述": "string",
        "数据库位置": "string",
        "其他备注": "string"
      },
      "责任医生": {
        "note": "string",
        "描述": "string",
        "数据库位置": "string",
        "其他备注": "string"
      },
      "会员": {
        "note": "string",
        "描述": "string",
        "数据库位置": "string",
        "其他备注": "string"
      }
    },
    "edges": {
      "首次接诊": {
        "note": "string",
        "描述": "string",
        "数据库位置": "string",
        "其他备注": "string"
      },
      "指定": {
        "note": "string",
        "描述": "string",
        "数据库位置": "string",
        "其他备注": "string"
      },
      "转化": {
        "note": "string",
        "描述": "string",
        "数据库位置": "string",
        "其他备注": "string"
      }
    }
  },
  "data": {
    "vertices": [
      {
        "vid": "patient",
        "tag": "患者"
      },
      {
        "vid": "first_visit_doctor",
        "tag": "初诊医生"
      },
      {
        "vid": "member",
        "tag": "会员"
      }
    ],
    "edges": [
      {
        "src": "patient",
        "edge": "首次接诊",
        "dst": "first_visit_doctor"
      },
      {
        "src": "patient",
        "edge": "转化",
        "dst": "member"
      }
    ]
  }
}
```

Agent1 不要求图数据库接口提前整理出 `candidate_metrics`。当前设计是：图数据库 API 返回完整图谱结构，Agent1 自己从 `schema` 和 `data` 中提取澄清线索。

Agent1 需要从返回结果中提取：

| 来源 | 字段 | 用途 |
|---|---|---|
| `schema.tags` | 实体类型，例如患者、初诊医生、责任医生、会员 | 判断问题涉及哪些对象 |
| `schema.tags.*.描述` | 实体说明 | 生成更可读的澄清选项 |
| `schema.tags.*.数据库位置` | 实体对应数据位置 | 后续写入 `task_contract.input_context`，供 Agent2 取数 |
| `schema.edges` | 关系类型，例如首次接诊、指定、转化 | 判断用户问题涉及哪些业务关系 |
| `schema.edges.*.描述` | 关系说明 | 解释口径或生成澄清问题 |
| `schema.edges.*.数据库位置` | 关系对应数据位置 | 供 Agent2 后续定位字段或表 |
| `data.vertices` | 实际命中的点 | 生成 `graph_scope.target_entities` |
| `data.edges` | 实际命中的边 | 生成 `graph_scope.required_relationships` |

基于示例 JSON，用户输入“转化率”时，Agent1 应识别：

```json
{
  "matched_terms": [
    {
      "name": "转化",
      "type": "Relation",
      "confidence": "high"
    }
  ],
  "related_entities": ["患者", "会员"],
  "relationships": [
    {
      "from": "patient",
      "relation": "转化",
      "to": "member"
    }
  ],
  "ambiguities": [
    {
      "field": "metric_definition",
      "issue": "图谱存在转化关系，但用户没有说明要分析转化率、转化人数、转化路径还是转化后的会员结果",
      "options": ["转化率", "转化人数", "转化路径", "会员转化结果"]
    }
  ],
  "knowledge_gaps": []
}
```

### 3. 基于图谱结果判断缺什么

Agent1 需要检查以下字段。

必填：

- `metric`
- `metric_definition`
- `time_range`
- `clinic_scope`
- `population`
- `expected_result.format`

条件必填：

- `comparison_baseline`：用户要求同比、环比、异常变化、原因分析时需要。
- `doctor_scope`：用户要求医生维度时需要。
- `channel_scope`：用户提到渠道或来源时需要。
- `advanced_method`：用户要求预测、聚类、归因、因果或优化时需要。

### 4. 生成澄清问题

Agent1 的澄清问题必须来自图数据库返回的 `schema` 和 `data`，而不是凭空生成。

例如，图数据库返回：

```text
patient --转化--> member
patient --首次接诊--> first_visit_doctor
patient --指定--> responsible_doctor
```

Agent1 应生成：

```json
{
  "id": "metric_definition",
  "question": "你说的转化具体想看哪个结果？",
  "type": "single_select",
  "options": [
    "转化率：患者转化为会员的比例",
    "转化人数：完成转化的患者数量",
    "转化路径：患者到会员的转化链路",
    "转化关联对象：患者、会员、初诊医生、责任医生之间的关系"
  ],
  "required": true,
  "source": "knowledge_graph_query"
}
```

常见澄清字段：

| 字段 | 触发条件 | 示例问题 |
|---|---|---|
| `metric_definition` | 图谱命中关系但无法唯一确定指标口径 | 你说的转化具体想看哪个结果？ |
| `time_range` | 用户只说“最近”“近期”或没说时间 | 本次分析使用哪个时间范围？ |
| `clinic_scope` | 用户只说“门店”或没说组织范围 | 本次分析覆盖哪些门店？ |
| `population` | 图谱显示指标依赖患者类型，但用户未说明 | 本次分析面向哪类人群？ |
| `comparison_baseline` | 用户要求看变化或异常 | 需要和什么基准比较？ |
| `output_format` | 用户未说明交付格式 | 你希望输出什么形式？ |

### 5. 判断状态

如果缺少必填字段：

```json
{
  "status": "needs_clarification",
  "clarification_questions": [],
  "task_contract": {}
}
```

如果字段完整：

```json
{
  "status": "ready",
  "clarification_questions": [],
  "task_contract": {}
}
```

### 6. 生成任务合同

当 `status = ready` 时，Agent1 输出 `task_contract`。

`task_contract` 是 Agent2 的唯一任务输入。Agent1 只负责澄清任务、限定边界和声明 Agent2 必须具备的能力，不为 Agent2 固定执行步骤；Agent2 根据合同自主决定具体怎么执行、什么时候调用工具、如何拆分子任务。

结构：

```json
{
  "task_contract": {
    "task_id": "task_xxx",
    "goal": "本次分析目标",
    "clarified_task": {
      "original_question": "转化率很低，为什么",
      "understood_intent": "验证初诊转化率是否偏低，并定位原因和建议动作",
      "analysis_intent": "root_cause_analysis",
      "agent2_execution_owner": true,
      "execution_note": "Agent1 只负责澄清任务和边界；Agent2 自主规划执行步骤和工具调用顺序。"
    },
    "input_context": {
      "metric": "first_visit_conversion_rate",
      "metric_label": "初诊转化率",
      "metric_definition": "基于图谱关系 patient --转化--> member，统计患者转化为会员的比例；具体分母需用户或数据口径确认",
      "time_range": "2026-04-20 to 2026-05-20",
      "clinic_scope": ["仙乐斯门店"],
      "population": "患者",
      "analysis_intent": "root_cause_analysis",
      "problem_statement": "转化率很低，为什么",
      "problem_signal": {
        "type": "low_metric",
        "metric": "first_visit_conversion_rate",
        "metric_label": "初诊转化率",
        "comparison_baseline": "unspecified",
        "requires_baseline_validation": true
      }
    },
    "graph_query_boundary": {
      "allowed_entity_types": ["患者", "会员", "门店", "医生"],
      "allowed_relationships": ["转化", "初诊医生", "责任医生"],
      "constraints": ["只读查询", "不扩大门店和时间范围"]
    },
    "graph_entity_hints": ["患者", "会员"],
    "graph_relationship_hints": ["转化"],
    "required_capabilities": [
      {
        "name": "knowledge_graph_query",
        "required": true,
        "owner": "Agent2",
        "purpose": "Agent2 使用与 Agent1 相同的 knowledge_graph_query 工具，自主查询图数据库并确认实体、关系、字段位置和图谱缺口。",
        "acceptance_criteria": [
          "必须记录查询到的实体、关系和缺口。",
          "必须遵守 graph_query_boundary。",
          "不得使用本地 mock 替代真实图谱查询结果。"
        ]
      },
      {
        "name": "data_fetch",
        "required": true,
        "owner": "Agent2",
        "purpose": "Agent2 自主生成只读查询或调用取数工具，获取限定范围内的业务数据。",
        "acceptance_criteria": [
          "必须包含指标、时间范围、门店范围和人群过滤条件。",
          "必须返回字段、行数、过滤条件和脱敏说明。",
          "不得扩大取数范围。"
        ]
      },
      {
        "name": "root_cause_analysis",
        "required": true,
        "owner": "Agent2",
        "purpose": "验证初诊转化率是否偏低或异常，并拆解主要影响维度和原因假设。",
        "acceptance_criteria": [
          "必须先验证 problem_signal 是否成立，并说明对比基准。",
          "没有可用基准时必须标记为 unable_to_validate，不能默认问题成立。",
          "每条原因必须包含数据证据或图谱证据、反证或限制、置信度和建议验证动作。"
        ]
      }
    ],
    "acceptance_criteria": [
      "Agent2 必须自主规划执行步骤，不依赖 Agent1 固定步骤。",
      "Agent2 必须使用 task_contract.input_context 作为唯一业务范围来源。",
      "Agent2 必须自行调用 knowledge_graph_query 确认图谱实体和关系。",
      "Agent2 必须输出可被 Agent1 审核的结构化结果和最终报告。"
    ],
    "safety_constraints": [
      "所有数据库操作必须只读。",
      "必须限定 input_context 中的指标、时间范围、门店范围和人群范围。",
      "不得输出未脱敏个人身份信息、联系方式或支付凭证。",
      "真实工具失败时必须返回结构化失败原因，不得生成模拟结论。"
    ],
    "agent2_planning_policy": {
      "execution_steps": "agent2_decides",
      "tool_call_order": "agent2_decides",
      "must_use_same_graph_tool": "knowledge_graph_query",
      "agent1_does_not_prescribe_steps": true
    },
    "expected_deliverable": {
      "format": "Markdown",
      "sections": ["问题定义", "分析范围", "核心指标结果", "维度拆解", "主要原因", "建议动作", "限制与风险"]
    },
    "final_expected_output": {
      "format": "Markdown",
      "sections": ["问题定义", "分析范围", "核心指标结果", "维度拆解", "主要原因", "建议动作", "限制与风险"]
    }
  }
}
```

约定：

- `input_context.metric` 保留指标标识，`input_context.metric_label` 提供中文指标名。
- `input_context.analysis_intent` 标记任务类型；当用户输入“很低/为什么/异常/下降”等原因分析诉求时，值为 `root_cause_analysis`。
- `input_context.problem_signal` 保存用户声称的问题信号，例如低转化率；Agent2 必须先用历史同期、环比、同类门店均值或目标值等可用基准验证该信号是否成立，不能默认“确实很低”。
- `task_contract` 不包含固定 `todos`。Agent1 不声明 step_1、step_2 这类执行顺序。
- `required_capabilities` 只表达 Agent2 必须具备和证明完成的能力，不表达执行步骤。
- `agent2_planning_policy.execution_steps = agent2_decides`，表示 Agent2 自主拆分任务。
- `agent2_planning_policy.tool_call_order = agent2_decides`，表示 Agent2 自主决定工具调用顺序。
- `agent2_planning_policy.must_use_same_graph_tool = knowledge_graph_query`，表示 Agent1/Agent2 使用同一个图数据库查询工具，Agent2 需要自己调用该工具复核图谱范围。
- `graph_query_boundary` 是边界，不是查询结果替代品；Agent2 不能只消费 Agent1 的图谱摘要，必须按需自己查图数据库。

标准指标分析 `required_capabilities`：

| Capability | Required | 目的 |
|---|---|---|
| `knowledge_graph_query` | 是 | Agent2 用同一个图谱工具确认实体、关系、字段位置和图谱缺口 |
| `data_fetch` | 是 | Agent2 自主生成只读查询或调用取数工具，获取限定范围内的业务数据 |
| `sql_check` | 是 | 检查 SQL 或数据查询的只读性、边界、性能风险和隐私风险 |
| `cache_manager` | 否 | 缓存中间数据，支持断点续跑和减少重复取数 |
| `metric_analysis` | 是 | 计算目标指标，并完成趋势、维度拆解和建议动作 |
| `visualization` | 是 | 生成必要的图表规格或图表文件 |
| `report_generation` | 是 | 根据 `expected_deliverable` 生成最终报告 |

诊断类原因分析 `required_capabilities`：

当 `input_context.analysis_intent = root_cause_analysis` 时，Agent1 不再把任务拆成固定步骤，而是把 `metric_analysis` 替换为 `root_cause_analysis`：

| Capability | Required | 目的 |
|---|---|---|
| `knowledge_graph_query` | 是 | Agent2 用同一个图谱工具确认实体、关系、字段位置和图谱缺口 |
| `data_fetch` | 是 | Agent2 自主获取限定范围内的业务数据 |
| `sql_check` | 是 | 检查 SQL 或数据查询安全 |
| `cache_manager` | 否 | 如使用缓存，说明缓存 key、过期时间和命中状态 |
| `root_cause_analysis` | 是 | 先验证问题是否成立，再拆解维度、形成原因假设和证据链 |
| `visualization` | 是 | 生成诊断必要的图表规格或图表文件 |
| `report_generation` | 是 | 生成诊断报告，明确证据、限制和未验证项 |

诊断类 `final_expected_output.sections`：

```json
[
  "问题定义",
  "分析范围",
  "问题是否成立",
  "对比基准",
  "维度拆解",
  "原因假设",
  "证据链",
  "建议动作",
  "限制与风险"
]
```

## Agent1 需要的工具

### 必须工具

| 工具名 | 文件 | Agent1 是否调用 | 说明 |
|---|---|---|---|
| `knowledge_graph_query` | `tools/kg_query.py` | 是 | 根据业务词查询图数据库，返回 schema、vertices、edges，并由 Agent1 基于结果生成澄清内容 |
| `problem_reporter` | `tools/problem_reporter.py` | 是 | 发现口径歧义、图谱缺口、权限不明、合同不完整时上报给未来 Agent3 |

### Agent1 内部能力，不建议做成 CrewAI Tool

| 能力 | 位置 | 说明 |
|---|---|---|
| `requirement_clarifier` | `agents/agent1.py` | 基于图谱上下文和用户问题生成澄清结构 |
| `task_contract_builder` | `agents/agent1.py` | 生成 Agent2 可执行合同 |
| `agent2_result_reviewer` | `agents/agent1.py` | 审核 Agent2 输出 |
| `privacy_checker` | `agents/agent1.py` | 检测手机号、邮箱、未脱敏身份字段 |

### Agent1 当前不需要的工具

| 工具名 | 原因 |
|---|---|
| `knowledge_base_query` | 当前知识来源改为图数据库，不读 Agent3/JSON 知识沉淀 |
| `knowledge_base_reader` | Agent3 复盘工具，本期不调用 |
| `insight_refiner` | Agent3 知识沉淀工具，本期不调用 |
| `problem_collector_reader` | Agent3 读取工具，本期不调用 |
| `step_decomposition_evaluator` | Agent3 复盘工具，本期不调用 |
| `graph_gap_detector` | Agent3 复盘工具，本期不调用 |
| `process_optimizer` | Agent3 复盘工具，本期不调用 |

## Agent2 需要的工具

Agent2 需要执行任务合同，因此需要以下工具。

| 工具名 | 当前位置 | 状态 | 说明 |
|---|---|---|---|
| `knowledge_graph_query` | `agents/agent2.py` 和 `tools/kg_query.py` 均有相关实现 | 需统一 | 按合同查询图谱实体和关系 |
| `data_fetch` | `agents/agent2.py` | 已有 mock | 业务取数 |
| `sql_debug` | `agents/agent2.py` | 已有 mock | SQL 自动修复 |
| `cache_manager` | `agents/agent2.py` | 已有 mock | 数据缓存 |
| `basic_analysis` | `agents/agent2.py` | 已有 mock | 基础分析 |
| `advanced_analysis` | `agents/agent2.py` | 已有 mock | 进阶分析 |
| `visualization` | `agents/agent2.py` | 已有 mock | 图表生成 |
| `ppt_generator` | `agents/agent2.py` | 已有 mock | PPT 生成 |
| `problem_reporter` | `tools/problem_reporter.py` | 已有 | 执行问题上报给未来 Agent3 |

Agent2 当前不需要：

```text
knowledge_base_query
Agent3 复盘工具
Agent3 知识沉淀工具
```

## 问题上报要求

Agent1/Agent2 不做知识沉淀，只做问题上报。

上报工具：

```text
problem_reporter
```

上报场景：

| Agent | Stage | 触发场景 |
|---|---|---|
| Agent1 | `clarification` | 用户问题缺少必填字段 |
| Agent1 | `knowledge` | 图数据库查不到业务词 |
| Agent1 | `knowledge` | 图数据库命中关系但无法唯一确定分析目标 |
| Agent1 | `planning` | 无法生成可执行任务合同 |
| Agent2 | `data_fetch` | 字段不存在、表不存在、数据库不可用 |
| Agent2 | `sql_check` | SQL 不安全或无法修复 |
| Agent2 | `basic_analysis` | 样本不足、数据异常 |
| Agent2 | `visualization` | 图表无法生成 |

上报结构：

```json
{
  "agent": "Agent1",
  "stage": "clarification",
  "problem": "图谱命中 patient --转化--> member 关系，但用户未确认要看转化率、转化人数还是转化路径",
  "solution": "返回 metric_definition 澄清问题，要求用户选择转化率、转化人数、转化路径或转化关联对象",
  "severity": "medium"
}
```

## 图数据库工具要求

### 工具命名

所有 CrewAI / function calling 工具名必须使用英文。

当前需要改造：

```python
name: str = "知识图谱查询"
```

改为：

```python
name: str = "knowledge_graph_query"
```

### 数据源优先级

已确认的正式图谱数据源按以下顺序获取数据：

```text
1. 正式只读 Graph API：https://graph.automed.cn
2. 本地图谱 JSON：MEDGRAPH_JSON_PATH
3. 模拟降级结果
```

本地图谱 JSON 可先使用：

```text
/Users/ameng/Downloads/medgraph_backup.json
```

注意：

- Graph API 路径中的 `{space}` 是查询边界，不是全局默认库。
- Agent1 默认不要求用户选择 space；`knowledge_graph_query` 会先调用 `GET /spaces`，再按用户问题和各 space 的 tag / edge 命中度自动选择。
- `GRAPH_API_AUTO_SPACE=1` 时，即使本地配置了 `GRAPH_API_SPACE`，也会执行自动选择；`GRAPH_API_AUTO_SPACE=0` 且设置了 `GRAPH_API_SPACE` 时，才固定查询指定 space。
- PyCharm 本地测试脚本默认开启自动选库，避免因为本地默认库导致其他 space 的数据拿不到。

已知结构：

```json
{
  "space": "medgraph",
  "version": "3.8.0",
  "schema": {
    "tags": {},
    "edges": {}
  },
  "data": {
    "vertices": [],
    "edges": []
  }
}
```

### 已验证的正式接口事实

以下事实已在 2026-05-19 基于真实接口联调验证，可作为后续 Agent 协作的共同前提：

- 底层图数据库是 `NebulaGraph 3.8`。
- 查询语言是 `nGQL`。
- 正式对外入口是只读 HTTP API，不建议 Agent 直接连 NebulaGraph。
- 正式 base URL：`https://graph.automed.cn`
- 鉴权方式：Header `Authorization: <API Key>`
- 本地联调确认，Cloudflare 会拦截默认 Python/urllib 指纹；请求需要带 Apipost 或浏览器风格 `User-Agent`。
- 所有写入类 nGQL 会被拒绝；验证过 `CREATE TAG ...` 返回 `HTTP 403`
- 可确认可用的只读路径：
  - `GET /health`
  - `GET /spaces`
  - `GET /{space}/tags`
  - `GET /{space}/vertices?tag={tag}&limit={limit}`
  - `GET /{space}/edges?type={type}&limit={limit}`
  - `POST /{space}/query`
- `POST /{space}/query` 已验证支持只读 nGQL，如 `MATCH`、`SHOW EDGES` 等；请求体字段是 `statement`。
- 已确认空间：
  - `medgraph`：`27` 个 tag，`30` 个 edge type，`56` 个 vertex
  - `card_renew_knowledge`：`4` 个 tag，`3` 个 edge type

### 已验证的接口行为差异

文档与真实返回存在以下重要差异，后续 Agent 和实现代码都必须按真实行为处理：

- Apipost 成功请求使用的是 `Authorization: <API Key>`，不是 `Authorization: Bearer <API Key>`。
- `POST /{space}/query` 请求体字段是 `statement`，不是 `query` 或 `ngql`。
- `GET /{space}/edges` 在文档中写的是“查看关系类型”，但实际返回的是边数据样本，不是真正的 edge type 列表。
- 需要获取真实 edge type 时，应优先走 `POST /{space}/query` 并执行 `SHOW EDGES`。
- 无效空间如 `not_a_space` 并不会返回文档描述的 `HTTP 400`；实际会返回 `HTTP 200`，并把 Nebula 错误写在响应体 `raw` 中。

已验证的错误体特征：

```json
{
  "raw": "(root@nebula) [(none)]> USE not_a_space; SHOW TAGS;\n[ERROR (-1005)]: SpaceNotFound: SpaceName `not_a_space`",
  "rows": [],
  "columns": []
}
```

写入拒绝特征：

```json
{
  "detail": "只允许只读操作（MATCH/SHOW/DESCRIBE/LOOKUP 等）"
}
```

### 图谱返回结构

接口返回可以是图数据库导出的原始结构，不要求后端提前整理为指标口径数组。

必须包含：

- `space`
- `version`
- `schema.tags`
- `schema.edges`
- `data.vertices`
- `data.edges`

Agent1 负责在读取后整理出：

- 命中的业务词。
- 命中的实体类型。
- 命中的关系类型。
- 本次相关点。
- 本次相关边。
- 可用于澄清的候选含义。
- 必须追问的缺失字段。
- 图谱缺口。

### 工具职责边界

`knowledge_graph_query` 直接返回 API 数据，不做澄清推理。

允许做：

- 调用图数据库 API。
- 读取 `MEDGRAPH_JSON_PATH` 本地 fallback。
- 校验返回中是否包含 `schema` 和 `data`。
- 对 `POST /{space}/query` 结果解析 `raw`，识别 Nebula 错误文本，例如 `[ERROR (`。
- 在失败时返回结构化错误或模拟降级结果。

不允许做：

- 不生成 `clarification_questions`。
- 不生成 `task_contract`。
- 不判断用户意图。
- 不把原始图谱加工成业务结论。

这些推理都属于 CrewAI Agent1 和确定性核心。

## 数据流

### 需求澄清数据流

```text
original_question
  ↓
Agent1 提取业务词
  ↓
knowledge_graph_query
  ↓
graph_data(schema + vertices + edges)
  ↓
Agent1 生成 clarification_result
  ↓
needs_clarification 或 ready
```

### 主执行数据流

```text
clarification_result + graph_scope
  ↓
Agent1 生成 task_contract
  ↓
Agent2 执行 task_contract
  ↓
agent2_result
  ↓
Agent1 审核
  ↓
main_report / revision_requests / blocked
```

### 问题上报数据流

```text
Agent1 / Agent2
  ↓
problem_reporter
  ↓
problem_reports
  ↓
未来 Agent3 复盘使用
```

## 使用示例

### 模糊问题

输入：

```text
帮我看看最近门店转化怎么样
```

Agent1 操作：

```text
1. 识别业务词：转化、门店、最近
2. 查询图数据库：转化相关 schema、点和边
3. 图谱返回 patient --转化--> member 等关系
4. 生成澄清问题
```

输出：

```json
{
  "clarification_result": {
    "status": "needs_clarification",
    "clarification_questions": [
      {
        "id": "metric_definition",
        "question": "你说的转化具体想看哪个结果？",
        "type": "single_select",
        "options": [
          "转化率：患者转化为会员的比例",
          "转化人数：完成转化的患者数量",
          "转化路径：患者到会员的转化链路",
          "转化关联对象：患者、会员、初诊医生、责任医生之间的关系"
        ],
        "required": true,
        "source": "knowledge_graph_query"
      },
      {
        "id": "time_range",
        "question": "本次分析使用哪个时间范围？",
        "type": "single_select",
        "options": ["最近7天", "最近30天", "2026年4月", "自定义"],
        "required": true
      },
      {
        "id": "clinic_scope",
        "question": "本次分析覆盖哪些门店？",
        "type": "multi_select",
        "options": ["指定门店", "上海门店", "当前权限内全部门店"],
        "required": true
      }
    ]
  },
  "task_contract": {}
}
```

### 明确问题

输入：

```text
请分析2026年4月上海门店SH001和SH002初诊转化率，并输出Markdown报告
```

Agent1 操作：

```text
1. 识别业务词：初诊、转化、上海门店、SH001、SH002、2026年4月
2. 查询图数据库：初诊医生、患者、会员、转化、首次接诊、指定等 schema 和关系
3. 字段完整，生成任务合同
```

输出：

```json
{
  "clarification_result": {
    "status": "ready"
  },
  "graph_scope": {},
  "task_contract": {}
}
```

## 实现阶段

### Phase 1：图数据库查询工具

任务：

- 改造 `tools/kg_query.py`：
  - 工具名改成 `knowledge_graph_query`。
  - 支持 `MEDGRAPH_JSON_PATH`。
  - 返回接口原始结构或等价结构：`space`、`version`、`schema`、`data.vertices`、`data.edges`。
  - 保留 NebulaGraph 和模拟降级。
- 增加测试：
  - 本地 JSON 可读取 schema。
  - 输入“转化率”可返回包含 `转化` 关系的 edges。
  - 数据源不可用时返回模拟降级。

验收：

```bash
.venv/bin/python -m unittest discover -s tests
```

### Phase 2：Agent1 CrewAI 化和图谱驱动澄清

任务：

- 定义 CrewAI `scheduler_agent`。
- 定义 Agent1 澄清 Task，要求输出 JSON。
- CrewAI Agent1 从用户问题提取业务词。
- CrewAI Agent1 主动调用 `knowledge_graph_query`。
- CrewAI Agent1 用图谱 `schema`、`vertices`、`edges` 生成 `clarification_questions` 草稿。
- CrewAI Agent1 在缺口或歧义时调用 `problem_reporter` 上报。
- 确定性 Agent1 核心校验 CrewAI 输出。
- 确定性 Agent1 核心在字段完整时生成或规范化 `task_contract`。

验收：

- 输入“转化率”会先查图谱，再基于 `转化` 关系生成澄清问题。
- 澄清问题中的选项来自图谱 schema 和关系。
- Agent1 不调用 `knowledge_base_query`。
- Agent1 不调用 Agent3 工具。
- Agent1 以 CrewAI Agent 形式运行。
- CrewAI 输出不可解析时，Workflow 返回结构化错误或降级结果，不直接把脏文本交给 Agent2。

### Phase 3：Agent2 接收真实任务合同

任务：

- Agent2 从固定 `test_task` 改为接收 `task_contract`。
- Agent2 根据合同中的能力要求和边界自主规划执行步骤。
- Agent2 遇到执行异常时调用 `problem_reporter`。
- Agent2 不调用 `knowledge_base_query`。
- Agent2 不调用 Agent3 工具。

验收：

- Agent2 不读取用户原始问题。
- Agent2 输出可被 Agent1 审核的结构化结果。

## 测试策略

必须覆盖：

- Agent1 CrewAI Task 能调用 `knowledge_graph_query`。
- 模糊问题触发图数据库查询。
- 图数据库返回命中关系但无法唯一确定分析目标时，Agent1 输出 `needs_clarification`。
- 图数据库唯一命中且必填字段完整时，Agent1 输出 `ready`。
- 澄清问题的选项来自图数据库 `schema` 和 `data.edges`。
- 图数据库查不到业务词时，Agent1 调用 `problem_reporter`。
- Agent1 不调用 Agent3 任何工具。
- Agent1 不调用 `knowledge_base_query`。
- Agent2 只接收 `task_contract`。
- Agent2 执行异常时调用 `problem_reporter`。
- Agent1 审核发现缺失能力、范围越界、口径不一致、隐私泄漏。

建议命令：

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall agents integration.py tests tools
```

## 当前实现状态

当前已落地：

- `agents/agent1.py`：确定性 Agent1 核心逻辑。
- `agents/agent1.py`：新增 `Agent1LLMClarifier`，使用 OpenAI-compatible LLM 生成自然澄清话术、解析用户回复中的上下文字段，并由确定性核心继续生成稳定 `task_contract`。
- `agents/agent1.py`：LLM 客户端读取 `OPENAI_API_KEY`、`OPENAI_API_BASE`、`OPENAI_MODEL_NAME`，支持 `OPENAI_USER_AGENT`、`OPENAI_TIMEOUT_SECONDS`、`OPENAI_MAX_TOKENS` 和 `OPENAI_RESPONSE_FORMAT_JSON`；兼容 Qwen 输出 `<think>...</think>` 后再返回 JSON 的情况。
- `agents/agent1.py`：CrewAI `scheduler_agent` 和澄清 `Task` 工厂。
- `agents/agent1.py`：`run_agent1_clarification` 本地入口，会先判断是否需要查询图谱；业务问题会调用 `knowledge_graph_query` 获取图谱数据，再交给确定性核心生成澄清结果。
- `agents/agent1.py`：基于 `knowledge_graph_query` 返回图谱数据提取 `转化` 关系，并生成图谱来源的澄清选项。
- `agents/agent1.py`：当严格真实 API 模式返回错误时，Agent1 返回 `blocked`，不使用静态规则或 mock 继续澄清。
- `agents/agent1.py`：本地真实流程启用 `strict_graph_match` 后，如果图谱查询成功但没有命中当前指标相关实体或关系，Agent1 返回 `blocked`，不继续追问时间范围，也不生成 `task_contract`。
- `agents/agent1.py`：`task_contract.input_context.time_range` 会将相对时间规范为具体日期区间，例如 `最近一个月` 在 2026-05-20 会规范为 `2026-04-20 to 2026-05-20`，`2026-04` 会规范为 `2026-04-01 to 2026-04-30`。
- `agents/agent1.py`：识别“转化率很低，为什么”“下降原因”“异常原因”等诊断类问题，并在 `task_contract.input_context` 写入 `analysis_intent`、`problem_statement` 和 `problem_signal`，供 Agent2 先验证问题是否成立再做原因拆解。
- `agents/agent1.py`：`task_contract` 不再包含固定 `todos`，改为 `required_capabilities`、`acceptance_criteria`、`safety_constraints`、`expected_deliverable` 和 `agent2_planning_policy`。
- `agents/agent1.py`：当 `analysis_intent = root_cause_analysis` 时，Agent1 不再替 Agent2 拆固定步骤，而是要求 Agent2 具备 `root_cause_analysis` 能力：先验证问题是否成立，再拆解影响维度、形成原因假设和证据链。
- `agents/agent1.py`：Agent1 在 `task_contract.graph_query_boundary`、`graph_entity_hints`、`graph_relationship_hints` 中提供图谱边界和提示；Agent2 必须使用同一个 `knowledge_graph_query` 工具自己查询图数据库。
- `agents/agent1.py`：`required_capabilities` 中给人读的能力说明使用中文；`name` 等机器字段保持稳定英文标识；`input_context` 增加 `metric_label` 中文指标名。
- `agents/agent1.py`：先判断输入是否为业务分析需求；寒暄、空泛文本或没有业务对象的输入不查询图谱，也不进入固定指标澄清模板。
- `agents/agent1.py`：内置业务指标识别已覆盖 `现金流`，可识别现金流入、现金流出、净现金流相关问题。
- `agents/agent1.py`：图谱命中关系后，按图谱关系动态生成口径选项，例如 `续卡` 会生成续卡数量、续卡率、续卡路径、续卡关联对象；无图谱命中时改为自由文本澄清，不再优先展示固定指标列表。
- `agents/agent1.py`：识别用户问题中的地址或区域，使用自由文本确认其对应的门店/组织范围，不再固定展示“指定门店ID / 上海门店 / 当前权限内全部门店”。
- `agents/agent1.py`：识别原始问题中的具名门店，例如“查看仙乐斯门店的转化率”；用户补齐指标口径和时间范围后，`task_contract.input_context.clinic_scope` 会直接使用 `["仙乐斯门店"]`，不会重复追问门店。
- `local_agent1_test.py`：本地 PyCharm 入口改为真实 LLM 对话式澄清；默认 `AGENT1_USE_LLM=1`，Qwen/其他 OpenAI-compatible 模型负责自由文本澄清话术和回答解析，确定性核心负责边界校验和任务合同生成；当图谱命中关系并返回 `clarification_questions.options` 时，本地入口固定列出全部图谱口径选项并支持编号选择，不由 LLM 改写或省略选项；对话中用户询问“几个图谱/有哪些图谱”会作为元问题回答，不会写入业务指标；LLM 模式下不再把无法解析的用户追问确定性兜底写入 `time_range`、`metric` 或 `clinic_scope`。
- `integration.py`：模拟 workflow，支持把 `graph_data` 传入 Agent1 澄清路径。
- `agents/agent2.py`：Agent2 和 mock 工具。
- `tools/kg_query.py`：Agent1 使用的 `knowledge_graph_query` 工具，优先支持正式 Graph API + `Authorization: <API Key>` + Apipost 风格 `User-Agent`，兼容 `raw` Nebula 错误文本；默认可通过 `GET /spaces` 自动选择 graph space；仍保留 `MEDGRAPH_JSON_PATH` 本地 JSON fallback、NebulaGraph 查询和同结构模拟降级；设置 `GRAPH_API_STRICT=1` 时禁用本地 JSON/mock fallback，真实 API 失败会返回结构化错误。
- `tools/nebula_graph_query.py`：Agent2 当前使用的 NebulaGraph 查询工具；与 Agent1 的 `knowledge_graph_query` 并存，后续 Agent2 接入能力合同时需要确认是否直接复用 `knowledge_graph_query` 或在 Agent2 内部做等价适配。
- `tools/problem_reporter.py`：问题上报工具。
- `tests/test_agent1_workflow.py`：覆盖 Agent1 合同生成、Graph API 优先、Graph API 错误 fallback、严格真实 API 模式、图谱驱动澄清、图谱未命中阻塞、相对时间规范化、LLM JSON 解析、Qwen `<think>` 兼容、CrewAI 工具挂载、Workflow 传图谱数据、Agent1 审核。

仍需补齐：

- Workflow 正式 CrewAI kickoff 路径，当前已提供 Agent/Task 工厂和 deterministic 本地验证路径。
- CrewAI kickoff 输出 JSON 的解析、校验和失败降级。
- 图数据库查不到业务词时，由 Agent1 调用 `problem_reporter` 的运行时路径。
- Agent2 执行异常时调用 `problem_reporter`。
- Agent2 需要从固定测试任务改为消费 `task_contract`，并根据 `required_capabilities` 自主规划执行步骤。

当前不处理：

- Agent3 接入。
- Agent3 复盘工具。
- `data/knowledge_base.json` 知识沉淀。
- 从 Agent3 读取历史经验。

## 决策

- Agent1 必须 CrewAI 化。
- 当前确定性 `Agent1` 类继续保留，用于校验、规范化、测试和审核。
- Agent1 澄清必须以图数据库上下文为主。
- Agent1/Agent2 不负责知识沉淀。
- Agent1/Agent2 只负责问题上报，供未来 Agent3 使用。
- 当前实现只考虑 Agent1/Agent2。
- Agent3 不进入主链路，也不作为 Agent1 的知识来源。
- `task_contract` 是 Agent2 的唯一任务依据。
- Agent1 不直接取数、不分析、不生成图表或 PPT。

## 未决问题

- `MEDGRAPH_JSON_PATH` 只应作为本地开发 fallback，还是还要支持离线验收场景的长期保留。
- “转化率”等指标在图数据库中的节点和关系是否已有完整口径信息。
- 问题上报最终写入 JSON 文件，还是直接发给未来 Agent3 服务。
