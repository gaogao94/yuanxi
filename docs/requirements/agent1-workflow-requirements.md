# Agent1 与工作流需求梳理

## 文档来源

本需求文档基于以下输入整理：

- 用户在当前对话中明确给出的系统流程判断。
- 用户在当前对话中明确给出的 Agent1 三项核心任务：需求澄清、知识获取、步骤拆解。
- 用户在当前对话中补充的全量 Task 清单。
- 当前仓库已有文件：`README.md`、`agents/agent2.py`、`tools/kg_query.py`。

前序参考文件链接：

- <https://alidocs.dingtalk.com/i/nodes/14lgGw3P8vv6LjADFp2zYNKY85daZ90D>
- <https://alidocs.dingtalk.com/i/nodes/m9bN7RYPWdlKXrk0hb1zDEpMWZd1wyK0>
- <https://alidocs.dingtalk.com/i/nodes/G1DKw2zgV2RwyngDhBaxG2L0VB5r9YAn>

访问状态：

- 上述钉钉文档链接当前会跳转到钉钉登录页，本次没有读取到原文内容。
- 因此本文不把钉钉文档内容当作已验证依据，只把链接作为后续人工补充来源。
- 当前需求以用户在本对话中粘贴的任务描述为准。

## 结论

当前系统应采用代码层工作流编排，而不是蜂群模式，也不是再抽一个只做调度的 LLM Agent。

整体流程是：

```text
用户输入
  ↓
Workflow / Coordinator
  ↓
Agent1：需求澄清、知识获取、步骤拆解
  ↓
Agent2：数据获取、图谱查询、分析、可视化、PPT/报告生成
  ↓
Agent1：结果审核、口径核对、最终输出整理

旁路并行：
Agent3：洞察复盘、流程审计、图谱补缺、经验沉淀
```

Agent3 可以和任何 Agent 并行，但不阻塞主链路，不决定主流程下一步，不覆盖 Agent1 或 Agent2 的职责。

## 全量 Task 归属总览

| Task | 主负责 Agent | 所属链路 | 是否阻塞主报告 | 说明 |
|---|---|---|---|---|
| 需求澄清 | Agent1 | 主链路 | 是 | 将模糊问题变成明确需求和结果预期 |
| 知识获取 | Agent1 主导，图谱工具辅助 | 主链路 | 是 | 在澄清过程中确认对象和关系范围 |
| 步骤拆解 | Agent1 | 主链路 | 是 | 生成 Agent2 可执行、可验证的任务合同 |
| 安全围栏 | Workflow + Agent1 + Agent2 | 全流程 | 是 | 贯穿权限、脱敏、SQL 风控和数据边界 |
| 过程记录和可视化 | Workflow 主导，各 Agent 上报 | 全流程 | 否 | 状态播报、日志、审计可视化 |
| 数据获取 | Agent2 | 主链路 | 是 | 安全取数、SQL 修复、结果合理性检查 |
| 数据缓存 | Agent2 | 主链路 | 是 | 缓存中间数据，支持断点续跑和快速复用 |
| 数据分析 | Agent2 | 主链路 | 是 | 描述性统计、维度拆解、趋势和原因推断 |
| 数据分析（进阶） | Agent2 | 主链路 | 视任务而定 | 分类、回归、聚类、因果、时序、队列、运筹 |
| 数据可视化 | Agent2 | 主链路 | 是 | 生成可理解、清晰、美观的图表或汇报材料 |
| 审核输出 | Agent1 | 主链路 | 是 | 验证待办完成度和结果是否符合任务预期 |
| 批判性思考 | Agent3 | 旁路链路 | 否 | 并行复盘、图谱补缺、流程优化、经验沉淀 |

## 核心判断

使用工作流是必要的，因为当前系统同时存在两类关系：

- 主业务链路有明确顺序：先澄清，再执行，再审核。
- 洞察链路是旁路并行：可以读取任何阶段的过程信息，但不影响当前主结果交付。

因此，工作流负责确定性编排：

- 谁先执行。
- 谁后执行。
- 谁可以并行。
- 谁阻塞最终输出。
- 谁只产出旁路复盘。
- 如何汇总主结果和洞察结果。

Agent 负责专业判断和内容产出。

## 不采用蜂群

本系统第一版不采用蜂群。

不做：

- Agent 之间自由 handoff。
- 自动创建 Agent。
- 让 Agent 自己决定下一步找谁。
- 让多个 Agent 共享自治状态。
- 项目级 `.swarm` 状态系统。
- SessionStore 型长期蜂群记忆。

原因：

- 当前业务链路已经明确，不需要动态路由。
- 调度关系应该稳定、可测、可复现。
- 蜂群会增加不确定性，容易模糊 Agent1、Agent2、Agent3 的职责边界。

## 不新增上层调度 Agent

不建议新增一个“只做分配任务和最终输出”的 LLM Agent。

上层调度应该是代码层 `Workflow / Coordinator`，不是 Agent。

原因：

- 调度职责是确定性的流程控制，不需要 LLM 推理。
- LLM 调度 Agent 容易越界参与业务判断。
- 当前流程固定，代码调度更便宜、更稳定、更容易测试。
- 如果未来任务路径变复杂，再考虑升级为 CrewAI hierarchical manager。

## 推荐系统边界

### Workflow / Coordinator

Workflow 是代码层编排器。

职责：

- 接收用户输入。
- 创建主链路任务。
- 创建旁路洞察任务。
- 控制主链路顺序。
- 控制 Agent3 并行执行。
- 汇总主链路结果。
- 附加 Agent3 洞察结果。
- 处理失败降级。
- 记录每个阶段的过程信息。

不做：

- 不澄清业务问题。
- 不判断指标口径。
- 不分析数据。
- 不生成业务结论。
- 不替 Agent 决策。

### Agent1：需求澄清与任务规划 Agent

Agent1 是主链路入口，也是主链路出口审核者。

职责：

- 需求澄清。
- 业务用词消歧。
- 用户根本目的识别。
- 隐含信息识别。
- 知识图谱目标对象确认。
- 图谱调用范围限定。
- 分析步骤拆解。
- 生成给 Agent2 的任务合同。
- 审核 Agent2 结果。
- 整理最终可交付输出。

不做：

- 不直接执行 SQL。
- 不直接查询业务宽表。
- 不做统计计算。
- 不生成图表或 PPT 文件。
- 不负责旁路复盘。
- 不决定工作流并行关系。

### Agent2：数据处理干活 Agent

Agent2 是执行者。

职责：

- 接收 Agent1 输出的任务合同。
- 查询知识图谱。
- 读取或模拟业务宽表。
- 生成并检查 SQL。
- 做基础统计分析。
- 做多维度拆解。
- 做趋势和归因分析。
- 生成图表路径。
- 生成 PPT 或报告路径。
- 输出可被 Agent1 审核的分析报告。

不做：

- 不直接解释用户原始模糊需求。
- 不自行扩大分析范围。
- 不绕过 Agent1 的任务合同。
- 不做最终合规审核。

### Agent3：洞察优化进阶 Agent

Agent3 是旁路并行审计者。

职责：

- 读取 Agent1 需求澄清结果。
- 读取 Agent2 执行结果。
- 读取 Agent1 审核结果。
- 复盘流程漏洞。
- 发现口径歧义残留。
- 发现图谱实体或关系缺失。
- 发现取数和分析逻辑风险。
- 输出流程优化建议。
- 输出图谱补充建议。
- 沉淀可复用经验。

不做：

- 不阻塞主链路返回。
- 不决定主流程下一步。
- 不替 Agent1 重新澄清需求。
- 不替 Agent2 执行数据分析。
- 不覆盖最终用户主报告。

## 主链路流程

```text
1. Workflow 接收用户自然语言问题。
2. Workflow 将问题交给 Agent1。
3. Agent1 进行需求澄清、知识获取、步骤拆解。
4. Agent1 输出结构化任务合同。
5. Workflow 将任务合同交给 Agent2。
6. Agent2 按任务合同执行数据和图谱分析。
7. Agent2 输出分析结果、证据、图表/PPT路径。
8. Workflow 将 Agent2 输出交回 Agent1。
9. Agent1 审核结果是否满足需求、口径、安全和交付预期。
10. Workflow 输出主报告。
```

## Agent3 旁路并行流程

Agent3 可以读取任意阶段产物：

```text
Agent1 需求澄清结果
Agent1 任务合同
Agent2 执行过程摘要
Agent2 分析结果
Agent1 最终审核结果
```

Agent3 的运行方式：

- 可以在 Agent1 完成后启动第一轮复盘。
- 可以在 Agent2 执行后补充复盘。
- 可以在 Agent1 最终审核后生成完整复盘。
- 如果技术上第一版不方便真并行，可以先串行执行，但语义上必须保持“旁路非阻塞”。

第一版建议：

```text
主链路先保证稳定可跑。
Agent3 可以在主链路完成后立即执行，输出作为附加洞察区块。
后续再升级为真正异步并行。
```

## Agent1 详细需求

Agent1 的核心目标：

```text
将用户模糊业务问题转化为结构化、可执行、可验证的分析任务合同。
```

Agent1 包含三个核心能力：

- 需求澄清。
- 知识获取。
- 步骤拆解。

### 需求澄清

描述：

通过多轮选项式问答，澄清用户的目的和用词歧义，避免同名不同意、同意不同名。同时引导用户思考，限缩问题范围，理解并确认用户未表达出的隐含信息，明确用户根本目的，达成对工作结果的一致预期。

输出验证：

- 输出明确的工作结果预期。
- 明确是否还需要继续追问。
- 如果无需追问，必须输出可执行的需求确认结果。

结构化输出要求：

```json
{
  "status": "needs_clarification | ready",
  "original_question": "用户原始问题",
  "understood_intent": "系统理解到的业务目的",
  "root_goal": "用户根本目的",
  "ambiguities": [
    {
      "field": "metric | time_range | clinic_scope | channel | population | object",
      "issue": "歧义说明",
      "options": ["选项1", "选项2", "选项3"],
      "required": true
    }
  ],
  "clarification_questions": [
    {
      "id": "metric_definition",
      "question": "需要向用户确认的问题",
      "type": "single_select | multi_select | text",
      "options": ["选项1", "选项2"],
      "required": true
    }
  ],
  "implicit_assumptions": [
    "用户没有明说但会影响分析方向的信息"
  ],
  "confirmed_scope": {
    "metric": "已确认指标",
    "time_range": "已确认时间范围",
    "clinic_scope": ["已确认门店或组织范围"],
    "population": "已确认分析人群",
    "excluded_scope": ["明确排除的范围"]
  },
  "expected_result": {
    "format": "Markdown | PPT | HTML | chart_pack",
    "must_include": ["必须包含的结果模块"],
    "acceptance_criteria": ["用户认为任务完成的判断标准"]
  }
}
```

### 知识获取

描述：

知识获取在需求澄清过程中就应该参与。Agent1 需要从知识图谱中确认目标对象，理解目标对象与其他对象的关系，并限定本次分析允许调用的图谱范围。

输出验证：

- 输出本次分析相关对象。
- 输出相关对象之间的关系。
- 输出限定后的图谱调用范围。
- 输出已发现的知识缺口。

结构化输出要求：

```json
{
  "graph_scope": {
    "target_entities": [
      {
        "type": "Clinic | Patient | Appointment | Visit | Doctor | Channel | Bill | MembershipCard | Metric",
        "name": "对象名称",
        "resolved_ids": ["对象ID"],
        "confidence": "high | medium | low"
      }
    ],
    "related_entities": [
      "与本次分析相关的实体类型"
    ],
    "required_relationships": [
      {
        "from": "起点实体",
        "relation": "关系",
        "to": "终点实体",
        "reason": "为什么本次分析需要这条关系"
      }
    ],
    "excluded_entities": [
      "本次不应该查询或不相关的实体"
    ],
    "graph_query_boundary": {
      "max_hops": 3,
      "allowed_spaces": ["允许查询的图谱空间"],
      "allowed_entity_types": ["允许查询的实体类型"],
      "blocked_entity_types": ["禁止查询的实体类型"],
      "reason": "边界限定原因"
    },
    "knowledge_gaps": [
      {
        "gap": "缺失的实体、关系或口径",
        "impact": "对分析准确性的影响",
        "fallback": "第一版如何处理"
      }
    ]
  }
}
```

### 步骤拆解

描述：

基于获取的知识和澄清后的需求，构建需求分析框架，拆解具体的可被代理执行的步骤，定义步骤的串行并行关系，以及每个步骤的工作方法和预期结果，供代理自我验证。

输出验证：

- 输出可被执行和验证的待办列表。
- 每个步骤必须有执行者、依赖关系、工作方法、预期结果、自检标准。
- Agent2 可以直接按照待办列表执行。

结构化输出要求：

```json
{
  "task_contract": {
    "task_id": "稳定的任务ID",
    "goal": "本次分析目标",
    "input_context": {
      "metric": "指标",
      "metric_definition": "指标口径",
      "time_range": "时间范围",
      "clinic_scope": ["门店或组织范围"],
      "population": "分析人群",
      "graph_scope_ref": "关联的 graph_scope"
    },
    "todos": [
      {
        "id": "step_1",
        "name": "步骤名称",
        "executor": "Agent2",
        "type": "knowledge_graph_query | data_fetch | sql_check | basic_analysis | advanced_analysis | visualization | ppt_generation | reasoning",
        "depends_on": [],
        "can_parallel": false,
        "method": "具体工作方法",
        "expected_output": "该步骤应该产出什么",
        "self_check": "执行者如何验证该步骤完成",
        "risk": "该步骤可能的风险",
        "fallback": "失败时如何降级"
      }
    ],
    "final_expected_output": {
      "format": "Markdown",
      "sections": [
        "问题定义",
        "分析范围",
        "核心指标结果",
        "维度拆解",
        "主要原因",
        "建议动作",
        "限制与风险"
      ]
    }
  }
}
```

## Agent1 最终输出

Agent1 前置阶段最终输出一个完整对象：

```json
{
  "clarification_result": {},
  "graph_scope": {},
  "task_contract": {}
}
```

该对象是 Agent2 的唯一输入依据。

Agent2 不应该绕过该对象直接解释用户原始问题。

## Agent1 后置审核需求

Agent1 在 Agent2 执行完成后再次参与。

职责：

- 检查 Agent2 是否完成全部待办。
- 检查指标口径是否一致。
- 检查分析范围是否越界。
- 检查结论是否有证据。
- 检查输出格式是否满足用户预期。
- 检查是否存在隐私或权限风险。
- 整理用户可读的最终主报告。

结构化输出要求：

```json
{
  "review_result": {
    "status": "approved | needs_revision | blocked",
    "completed_todos": ["step_1", "step_2"],
    "missing_todos": [],
    "scope_violations": [],
    "metric_consistency": "passed | failed",
    "evidence_check": "passed | failed",
    "privacy_check": "passed | failed",
    "final_user_output": "面向用户的最终报告",
    "revision_requests": [
      {
        "target_step": "step_2",
        "issue": "需要返工的问题",
        "required_fix": "返工要求"
      }
    ]
  }
}
```

## Agent2 详细需求

Agent2 的核心目标：

```text
基于 Agent1 输出的任务合同，在安全边界内完成取数、缓存、分析、进阶分析和可视化，并输出可被 Agent1 审核的证据化分析结果。
```

Agent2 不直接读取用户原始模糊需求作为执行依据。Agent2 的唯一任务依据是 Agent1 输出的 `task_contract`。

### 数据获取

描述：

基于知识库中的提示，从数据库中安全且有边界地获取实际数据，供后续分析使用。取数过程中自行解决数据库抛出的提示并修复 bug。留存和解释相关 SQL，确保人类可以校验取数逻辑并 debug。自行确认结果的合理性。

输出验证：

- 数据范围必须符合 `task_contract.input_context`。
- SQL 只允许读取，不允许污染数据库。
- SQL 必须带解释说明。
- 查询结果必须包含行数、字段、时间范围和过滤条件。
- Agent2 必须说明数据结果是否合理。
- 查询失败时必须给出错误、修复动作和最终状态。

结构化输出要求：

```json
{
  "data_fetch_result": {
    "status": "success | partial_success | failed",
    "source": "business_wide_table | database | mock_data",
    "scope": {
      "time_range": "取数时间范围",
      "clinic_scope": ["门店或组织范围"],
      "population": "人群范围",
      "filters": ["过滤条件"]
    },
    "sql_records": [
      {
        "sql": "实际执行或模拟执行的 SQL",
        "purpose": "SQL 用途",
        "safety_check": {
          "read_only": true,
          "has_limit": true,
          "estimated_pressure": "low | medium | high",
          "blocked_reason": ""
        },
        "debug_history": [
          {
            "error": "数据库或语法错误",
            "fix": "修复动作",
            "result": "修复结果"
          }
        ]
      }
    ],
    "data_profile": {
      "row_count": 0,
      "fields": ["字段名"],
      "missing_values": ["缺失字段或缺失情况"],
      "outliers": ["异常数据说明"],
      "reasonableness_check": "合理性判断"
    },
    "human_check_notes": [
      "人类可以如何复核该取数逻辑"
    ]
  }
}
```

### 数据缓存

描述：

在取数过程中，暂时存放取出的数据，释放宝贵的内存资源。避免任务突发中断时可继续任务，避免重复取数影响进度。同时明确持久化存储时间，确保数据时效性。同时为相同需求提供快速查询结果。

输出验证：

- 缓存必须有稳定 `cache_key`。
- 缓存必须记录数据来源和任务上下文。
- 缓存必须有过期时间。
- 缓存必须说明是否可复用。
- 相同需求可命中缓存。
- 过期缓存不可作为正式结论依据。

结构化输出要求：

```json
{
  "cache_result": {
    "status": "hit | created | refreshed | skipped | failed",
    "cache_key": "稳定缓存键",
    "data_ref": "缓存数据引用或路径",
    "created_at": "ISO-8601 时间",
    "expires_at": "ISO-8601 时间",
    "ttl_seconds": 3600,
    "reuse_policy": {
      "can_reuse_for_same_contract": true,
      "requires_refresh_if": [
        "任务口径变化",
        "时间范围变化",
        "门店范围变化",
        "缓存过期"
      ]
    },
    "resume_support": {
      "can_resume": true,
      "resume_from_step": "step_id"
    }
  }
}
```

### 数据分析

描述：

在不同维度，使用描述性统计指标，对数据进行汇总和分析，明确问题现状和随时间变化的趋势。推断问题成因，并基于分析数据和知识库信息，给出可能的解决方案。

输出验证：

- 必须回答当前问题现状。
- 必须包含核心指标结果。
- 必须包含至少一个时间趋势分析。
- 必须包含关键维度拆解。
- 每个原因判断必须绑定数据证据或知识图谱证据。
- 每条建议必须能追溯到一个或多个发现。

结构化输出要求：

```json
{
  "analysis_result": {
    "status": "success | partial_success | failed",
    "metric_summary": {
      "metric": "指标名称",
      "definition": "指标口径",
      "value": "指标值",
      "comparison": {
        "mom": "环比变化",
        "yoy": "同比变化",
        "baseline": "对比基准"
      }
    },
    "dimension_breakdowns": [
      {
        "dimension": "clinic | doctor | channel | age_group | time_period",
        "findings": [
          {
            "segment": "维度项",
            "value": "指标值",
            "sample_size": 0,
            "change": "变化说明",
            "is_anomaly": false
          }
        ]
      }
    ],
    "trend_findings": [
      {
        "period": "时间周期",
        "trend": "趋势描述",
        "evidence": "证据"
      }
    ],
    "cause_hypotheses": [
      {
        "cause": "可能原因",
        "confidence": "high | medium | low",
        "evidence": ["数据证据或图谱证据"],
        "counter_evidence": ["反证或限制"],
        "recommended_action": "建议动作"
      }
    ]
  }
}
```

### 数据分析（进阶）

描述：

调用代码能力，对数据进行分类、回归、聚类，进行因果分析、相关性分析、时间序列分析、队列分析等，或基于限制性条件进行运筹学建模和求解，给出最优决策。

输出验证：

- 必须说明采用的进阶方法。
- 必须说明为什么该方法适合当前问题。
- 必须输出输入特征、目标变量和限制条件。
- 必须输出结果解释，而不是只输出模型指标。
- 如果数据量或质量不满足要求，必须降级为基础分析并说明原因。

结构化输出要求：

```json
{
  "advanced_analysis_result": {
    "status": "success | skipped | failed",
    "method": "classification | regression | clustering | causal_inference | correlation | time_series | cohort_analysis | optimization",
    "reason_to_use": "为什么使用该方法",
    "input_features": ["输入特征"],
    "target": "目标变量",
    "constraints": ["限制条件"],
    "data_quality_check": {
      "sample_size": 0,
      "sufficient": true,
      "issues": ["数据质量问题"]
    },
    "model_or_algorithm": "模型或算法名称",
    "result_summary": "结果摘要",
    "business_interpretation": "业务解释",
    "recommended_decision": "建议决策",
    "fallback": "不适用时的降级方案"
  }
}
```

### 数据可视化

描述：

基于澄清后的需求，使用代码能力或 Hppt 能力，对结论和分析过程进行可视化，确保结果可被理解、结论明确、逻辑清晰、视觉美观。

输出验证：

- 每张图必须服务于一个明确结论。
- 图表标题必须表达业务含义。
- 图表必须标注维度、指标、单位和时间范围。
- 可视化结果必须能被 Agent1 审核。
- 如果生成 PPT，必须包含结构清晰的章节。

结构化输出要求：

```json
{
  "visualization_result": {
    "status": "success | partial_success | failed",
    "charts": [
      {
        "chart_id": "chart_1",
        "type": "bar | line | pie | scatter | heatmap | table",
        "title": "图表标题",
        "business_question": "该图回答的问题",
        "data_source": "数据来源",
        "file_path": "图表文件路径",
        "key_message": "图表表达的核心结论"
      }
    ],
    "report_artifact": {
      "type": "markdown | pptx | html",
      "file_path": "报告或 PPT 路径",
      "sections": ["章节"]
    },
    "readability_check": {
      "has_titles": true,
      "has_units": true,
      "has_time_range": true,
      "conclusion_clear": true
    }
  }
}
```

## 安全围栏需求

安全围栏贯穿 Workflow、Agent1 和 Agent2。

描述：

确保用户在自己权限范围内获取和分析相关数据；确保没有非脱敏的患者信息被输出；确保执行的 SQL 不污染数据库，不影响数据安全和完整，不带来过大的查询压力。

输出验证：

- 用户权限范围明确。
- 分析范围不越权。
- 患者信息必须脱敏。
- SQL 必须只读。
- 禁止危险 SQL。
- 大查询必须被拦截或降级。
- 安全检查失败时主链路必须阻断。

结构化输出要求：

```json
{
  "safety_guardrail_result": {
    "status": "passed | blocked | needs_approval",
    "permission_check": {
      "user_role": "用户角色",
      "allowed_scope": ["允许范围"],
      "requested_scope": ["请求范围"],
      "is_allowed": true,
      "blocked_reason": ""
    },
    "privacy_check": {
      "patient_data_present": false,
      "masked_fields": ["name", "phone"],
      "leak_detected": false
    },
    "sql_risk_check": {
      "read_only": true,
      "blocked_keywords": ["DELETE", "UPDATE", "DROP", "TRUNCATE"],
      "estimated_rows": 0,
      "estimated_pressure": "low | medium | high",
      "allowed_to_execute": true
    },
    "decision": "continue | block | require_human_approval"
  }
}
```

## Agent3 详细需求

Agent3 的核心目标：

```text
对主链路过程进行旁路并行复盘，发现流程、口径、图谱和分析方向的改进空间。
```

### 批判性思考

描述：

对需求澄清过程、取数和分析过程遇到的问题和学习到的经验进行思考，给出优化建议。同时发现业务图谱中不完善的地方，对业务关联和分析方向给出建议。

输出验证：

- 至少覆盖需求澄清、知识获取、步骤拆解、取数、分析、输出审核中的一个或多个环节。
- 每条问题必须说明影响。
- 每条建议必须可执行。
- 图谱补缺建议必须说明实体或关系。
- 不影响当前主报告返回。

结构化输出要求：

```json
{
  "critical_thinking_result": {
    "status": "success | partial_success | failed",
    "reviewed_artifacts": [
      "clarification_result",
      "graph_scope",
      "task_contract",
      "data_fetch_result",
      "analysis_result",
      "review_result"
    ],
    "process_findings": [
      {
        "stage": "clarification | knowledge | planning | data_fetch | analysis | review",
        "issue": "发现的问题",
        "impact": "影响",
        "severity": "high | medium | low",
        "recommendation": "优化建议"
      }
    ],
    "graph_improvement_suggestions": [
      {
        "missing_entity_or_relation": "缺失实体或关系",
        "why_needed": "为什么需要",
        "example_query_or_use_case": "示例查询或业务场景"
      }
    ],
    "reusable_lessons": [
      {
        "lesson": "可复用经验",
        "applies_to": "适用场景"
      }
    ]
  }
}
```

## 过程记录和可视化需求

过程记录和可视化由 Workflow 负责收集，各 Agent 主动上报状态。

描述：

在处理过程中，积极输出各个代理的当前任务和状态，减少用户的等待焦虑，并对过程进行记录。在处理完成后，整理 log，分析优化点，可视化过程方便人类进行审计。

输出验证：

- 每个阶段必须有状态记录。
- 每个 Agent 当前任务可见。
- 主链路失败时可定位失败阶段。
- Agent3 旁路结果不影响主链路状态。
- 完成后能输出审计日志摘要。

结构化输出要求：

```json
{
  "process_log": {
    "run_id": "单次运行ID",
    "status": "running | completed | failed | partial_completed",
    "events": [
      {
        "timestamp": "ISO-8601 时间",
        "agent": "Workflow | Agent1 | Agent2 | Agent3",
        "task": "任务名称",
        "status": "pending | running | completed | failed | skipped",
        "message": "面向用户或审计者的状态说明",
        "artifact_ref": "相关产物引用"
      }
    ],
    "timeline_summary": [
      {
        "stage": "阶段名称",
        "duration_seconds": 0,
        "result": "阶段结果"
      }
    ],
    "audit_summary": {
      "completed_tasks": ["已完成任务"],
      "failed_tasks": ["失败任务"],
      "blocked_reasons": ["阻断原因"],
      "optimization_points": ["流程优化点"]
    }
  }
}
```

## 输出分层

最终对用户的输出应分两层：

### 主报告

来自主链路：

```text
Agent1 前置澄清
Agent2 执行分析
Agent1 后置审核
```

这是用户当前任务的正式交付物。

### 洞察报告

来自 Agent3：

```text
流程问题
口径风险
图谱缺口
取数风险
下一轮优化建议
可沉淀经验
```

这是附加复盘，不应该覆盖主报告。

## 第一版成功标准

第一版完成后，应满足：

- Workflow 能接收一个用户问题。
- Workflow 能调用 Agent1 生成结构化任务合同。
- Workflow 能将任务合同传给 Agent2。
- Workflow 能将 Agent2 输出传回 Agent1 审核。
- Agent3 可以读取过程产物并输出旁路洞察。
- 主报告可以在没有 Agent3 的情况下正常返回。
- Agent3 失败不影响主报告。
- 所有工具名使用英文，避免函数调用协议问题。
- 没有真实数据库或 NebulaGraph 时可以返回模拟结果。

## 暂不做范围

第一版不做：

- Web UI。
- 用户登录。
- 真实权限系统。
- 真实 SQL 数据库连接。
- 真实 PPT 文件生成。
- 真实图表渲染。
- 复杂多轮前端交互。
- 长期记忆。
- 蜂群式 Agent handoff。
- LLM manager agent。

## 待确认问题

以下问题不阻塞第一版需求文档，但会影响后续实现：

- Agent1 的多轮选项式问答第一版是否先用单轮结构化输出模拟。
- Agent3 第一版是否真实异步并行，还是主链路完成后立即串行执行但语义上保持旁路。
- Agent1 的业务口径库第一版是否先用静态字典模拟。
- 任务合同是否需要持久化到文件，还是仅在单次运行内传递。
- 最终输出第一版是纯 Markdown，还是同时保留 JSON 结构化结果。
