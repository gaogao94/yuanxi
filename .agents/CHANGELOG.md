# Agent Collaboration Changelog

## [2026-05-22 09:21] Agent1 复用 Agent2 图谱工具

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `tools/nebula_graph_query.py`
  - `tools/kg_query.py`
  - `agents/agent1.py`
  - `local_agent1_test.py`
  - `tests/test_agent1_workflow.py`
  - `README.md`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `docs/requirements/agent1-workflow-requirements.md`
  - `docs/tasks/agent3-onboarding-tasks.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：Agent1 不再保留独立 `tools/kg_query.py`，直接复用 Agent2 的 `tools/nebula_graph_query.py`。`NebulaGraphQueryTool` 默认输出文本摘要给 Agent2，Agent1 调用时传 `output_format=json` 获取结构化 graph schema、vertices、edges。`task_contract.required_capabilities` 和 `agent2_planning_policy.must_use_same_graph_tool` 已统一为 `nebula_graph_query`。
- 前端影响：无
- 后端影响：Agent1 与 Agent2 共用同一个图谱工具类；删除独立 Agent1 图谱工具文件。
- 接口影响：Agent2 合同中的图谱能力标识从 `knowledge_graph_query` 统一为 `nebula_graph_query`。
- 数据库影响：无写入，仍只读查询图数据库。
- 配置影响：无。
- 验证：
  - `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.test_nebula_graph_query_reads_medgraph_json_from_env tests.test_agent1_workflow.Agent1WorkflowTest.test_nebula_graph_query_defaults_to_text_for_agent2 tests.test_agent1_workflow.Agent1WorkflowTest.test_build_scheduler_agent_uses_only_graph_and_problem_tools tests.test_agent1_workflow.Agent1WorkflowTest.test_run_agent1_clarification_queries_graph_tool_before_planning`：通过
  - `.venv/bin/python -m unittest discover -s tests`：通过，49 个测试
  - `.venv/bin/python -m compileall agents integration.py tests tools local_agent1_test.py`：通过
  - `printf '转化率很低，为什么\n1\n一个月\n仙乐斯\n' | .venv/bin/python local_agent1_test.py`：通过，真实 DeepSeek + Graph API 输出 `nebula_graph_query` 能力合同
  - `git diff --check`：通过
- 遗留问题：
  - Agent2 真实执行链路仍需按 `required_capabilities` 消费合同并回填执行结果

## [2026-05-20 15:59] Agent1 能力合同替代固定 todos

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `agents/agent1.py`
  - `integration.py`
  - `local_agent1_test.py`
  - `tests/test_agent1_workflow.py`
  - `tools/nebula_graph_query.py`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：Agent1 的 `task_contract` 不再输出固定 `todos`。合同现在只负责说明澄清后的任务、输入范围、图谱边界、Agent2 必须满足的能力、验收标准、安全约束和最终交付要求；具体任务拆分、执行步骤和工具调用顺序由 Agent2 自主决定。后续已在 2026-05-22 将 Agent1 图谱查询统一到 Agent2 的 `tools/nebula_graph_query.py`。
- 前端影响：无
- 后端影响：Agent1 审核从检查 `completed_todos` 改为检查 `completed_capabilities`；Workflow 模拟执行也改为按 `required_capabilities` 回填结果。
- 接口影响：删除 `task_contract.todos`；新增或强化 `clarified_task`、`graph_query_boundary`、`graph_entity_hints`、`graph_relationship_hints`、`required_capabilities`、`acceptance_criteria`、`safety_constraints`、`agent2_planning_policy`、`expected_deliverable`。Agent2 必须使用同一个 `nebula_graph_query` 工具自行查询图数据库。
- 数据库影响：无
- 配置影响：无
- 验证：
  - `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.test_review_agent2_result_does_not_count_cache_as_data_fetch`：通过
  - `.venv/bin/python -m unittest discover -s tests`：通过，48 个测试
  - `.venv/bin/python -m compileall agents integration.py tests tools local_agent1_test.py`：通过
  - `printf '转化率很低，为什么\n1\n一个月\n仙乐斯\n' | .venv/bin/python local_agent1_test.py`：通过，真实 DeepSeek + Graph API 输出能力合同，不含 `todos`，包含 `root_cause_analysis` 和 `agent2_planning_policy.execution_steps=agent2_decides`
  - `git diff --check`：通过
- 遗留问题：
  - Agent2 仍需实现按 `required_capabilities` 自主规划执行的真实工具链路

## [2026-05-20 15:40] Agent1 诊断任务拆分

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `agents/agent1.py`
  - `tests/test_agent1_workflow.py`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：当 `task_contract.input_context.analysis_intent = root_cause_analysis` 时，Agent1 现在会把 Agent2 合同拆成 9 步诊断流程：验证问题是否成立、拆解影响维度、形成原因假设和证据链、准备诊断可视化输出、组装诊断报告。普通指标分析合同仍保持原 7 步结构。
- 前端影响：无
- 后端影响：Agent2 可直接按诊断步骤执行，不再把原因分析压在普通指标分析步骤里。
- 接口影响：诊断类 `task_contract.todos` 步骤更细；诊断类 `final_expected_output.sections` 增加“问题是否成立”“对比基准”“原因假设”“证据链”。
- 数据库影响：无
- 配置影响：无
- 验证：
  - `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.test_prepare_task_captures_low_metric_root_cause_intent_for_agent2`：通过
  - `printf '转化率很低，为什么\n1\n一个月\n仙乐斯\n' | .venv/bin/python local_agent1_test.py`：通过，真实 DeepSeek + Graph API 输出诊断类 9 步合同
  - `.venv/bin/python -m unittest discover -s tests`：通过，47 个测试
  - `.venv/bin/python -m compileall agents integration.py tests tools local_agent1_test.py`：通过
  - `git diff --check`：通过
- 遗留问题：
  - Agent2 实现仍需按新的诊断步骤消费合同并调用真实工具执行

## [2026-05-20 15:26] Agent1 诊断类问题意图捕获

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `agents/agent1.py`
  - `local_agent1_test.py`
  - `tests/test_agent1_workflow.py`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：Agent1 现在会识别“转化率很低，为什么”“下降原因”“异常原因”等诊断类问题，并在 `task_contract.input_context` 中写入 `analysis_intent`、`problem_statement` 和 `problem_signal`。Agent2 需要先验证该问题信号是否成立，再进行原因拆解。同步修复 LLM 未结构化写入有效澄清回答时的空转问题，允许本地流程用确定性解析接住“一个月”“仙乐斯”等有效回答。
- 前端影响：无
- 后端影响：Agent2 可通过新增上下文字段知道这是原因分析任务，而不是普通指标查询。
- 接口影响：`task_contract.input_context` 新增向后兼容字段：`analysis_intent`、`problem_statement`、`problem_signal`。
- 数据库影响：无
- 配置影响：无
- 验证：
  - `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.test_prepare_task_captures_low_metric_root_cause_intent_for_agent2`：通过
  - `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.test_local_agent1_chat_captures_root_cause_intent_and_valid_clinic_reply`：通过
  - `printf '转化率很低，为什么\n1\n一个月\n仙乐斯\n' | .venv/bin/python local_agent1_test.py`：通过，真实 DeepSeek + Graph API 生成包含诊断意图的 ready 合同
  - `.venv/bin/python -m unittest discover -s tests`：通过，47 个测试
  - `.venv/bin/python -m compileall agents integration.py tests tools local_agent1_test.py`：通过
  - `git diff --check`：通过
- 遗留问题：
  - `problem_signal.comparison_baseline` 当前为 `unspecified`，Agent2 需要自行用真实数据查找可用基准并明确说明验证结论

## [2026-05-20 14:50] Agent1 图谱选项稳定展示

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `local_agent1_test.py`
  - `tests/test_agent1_workflow.py`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：修复 LLM 模式下图谱命中关系后选项展示不稳定的问题。现在本地 Agent1 对话入口遇到 `clarification_questions.options` 时，会固定列出全部图谱口径选项，并支持用户输入编号映射到完整口径文本；LLM 不再负责改写或省略这些结构化选项。
- 前端影响：无
- 后端影响：本地真实对话流程更稳定，图谱来源的澄清选项由程序渲染。
- 接口影响：无业务接口变化；正式集成端应以 `clarification_questions.options` 作为选项渲染来源。
- 数据库影响：无
- 配置影响：无
- 验证：
  - `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.test_llm_clarification_stably_lists_graph_options_and_maps_number`：通过
  - `printf '仙乐斯门店的转化率\n1\n最近35天的\n' | .venv/bin/python local_agent1_test.py`：通过，真实 DeepSeek + Graph API 固定列出 4 个转化相关口径选项并生成 ready 合同
  - `.venv/bin/python -m unittest discover -s tests`：通过，45 个测试
  - `.venv/bin/python -m compileall agents integration.py tests tools local_agent1_test.py`：通过
  - `git diff --check`：通过
- 遗留问题：
  - 正式 UI 或其他 agent 集成时也需要渲染结构化 `clarification_questions.options`，不能只使用 LLM 自然语言消息

## [2026-05-20 14:43] Agent1 具名门店澄清去重

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `agents/agent1.py`
  - `tests/test_agent1_workflow.py`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：Agent1 现在会从原始问题中识别具名门店，例如“查看仙乐斯门店的转化率”。用户后续只需要补齐图谱口径和时间范围，生成给 Agent2 的 `task_contract.input_context.clinic_scope` 会直接使用 `["仙乐斯门店"]`，不再重复追问“哪个门店”。
- 前端影响：无
- 后端影响：本地对话式澄清流程减少重复追问，合同范围更贴近用户原始问题。
- 接口影响：无业务接口变化；`task_contract.input_context.clinic_scope` 的来源可能来自原始问题。
- 数据库影响：无
- 配置影响：无
- 验证：
  - `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.test_prepare_task_uses_named_clinic_from_original_question`：通过
  - `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.test_local_agent1_chat_does_not_reask_named_clinic_from_original_question`：通过
  - `printf '查看仙乐斯门店的转化率\n1\n最近35天的\n' | .venv/bin/python local_agent1_test.py`：通过，真实 DeepSeek + Graph API 未再次追问门店，输出 `clinic_scope=["仙乐斯门店"]`、`time_range=2026-04-15 to 2026-05-20`
  - `.venv/bin/python -m unittest discover -s tests`：通过，44 个测试
  - `.venv/bin/python -m compileall agents integration.py tests tools local_agent1_test.py`：通过
  - `git diff --check`：通过
- 遗留问题：
  - 具名门店提取仍是轻量规则；复杂别名或多个门店候选需要后续由图谱实体消歧增强

## [2026-05-20 14:29] Agent1 相对时间规范化

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `agents/agent1.py`
  - `local_agent1_test.py`
  - `tests/test_agent1_workflow.py`
  - `.env.example`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：将 Agent1 澄清中的相对时间规范为具体日期区间后再写入 `task_contract.input_context.time_range`。例如当前日期为 2026-05-20 时，`最近一个月` 输出为 `2026-04-20 to 2026-05-20`，`2026-04` 输出为 `2026-04-01 to 2026-04-30`。
- 前端影响：无
- 后端影响：Agent2 接收的任务合同时间范围更明确，不再收到 `最近一个月` 这类相对时间。
- 接口影响：无业务接口变化；`task_contract.input_context.time_range` 内容更规范。
- 数据库影响：无
- 配置影响：新增可选 `AGENT1_TODAY`，用于测试或本地固定当前日期。
- 验证：
  - `.venv/bin/python -m unittest discover -s tests`：通过，42 个测试
  - `printf '查看仙乐斯门店的转化率\n转化率\n最近一个月\n仙乐斯\n' | .venv/bin/python local_agent1_test.py`：通过，真实 DeepSeek + Graph API 输出 `2026-04-20 to 2026-05-20`
- 遗留问题：
  - `最近一个月` 采用向前推一个自然月的口径；如果业务希望“上一个完整自然月”，需要另行定义为 `上月`

## [2026-05-20 14:08] Agent1 禁止无效澄清兜底和图谱未命中下发

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `agents/agent1.py`
  - `local_agent1_test.py`
  - `tests/test_agent1_workflow.py`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：修复用户追问“你没查到信息，怎么还要时间？”被误写入 `task_contract.input_context.time_range` 的问题。LLM 模式下不再把无法解析的用户追问确定性兜底写入澄清字段；本地真实流程启用 `strict_graph_match`，图谱查询成功但未命中当前指标实体或关系时直接返回 `blocked`，不继续追问时间，也不生成给 Agent2 的任务合同。
- 前端影响：无
- 后端影响：Agent1 本地真实测试入口更严格，避免无图谱证据时下发虚假任务合同。
- 接口影响：无
- 数据库影响：无写入；仍只读调用 Graph API。
- 配置影响：无
- 验证：
  - `.venv/bin/python -m unittest discover -s tests`：通过，40 个测试
  - `printf '你好\n你的知识图谱有几个？\n上海门店的现金流\n你没查到信息，怎么还要时间？\n' | .venv/bin/python local_agent1_test.py`：通过，真实 Qwen LLM + 真实 Graph API 返回 `blocked`，没有生成 Agent2 合同
- 遗留问题：
  - `strict_graph_match` 目前在本地真实测试入口启用；正式 workflow 如果也需要同策略，需要传入相同上下文标志

## [2026-05-20 14:01] Agent1 本地真实 LLM 澄清接入

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `agents/agent1.py`
  - `local_agent1_test.py`
  - `tests/test_agent1_workflow.py`
  - `.env.example`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：新增 `Agent1LLMClarifier`，本地 PyCharm 测试入口默认调用 OpenAI-compatible LLM 生成自然澄清话术和解析用户回复；确定性 Agent1 核心继续负责图谱边界、合同生成和审核。已切到用户提供的 Qwen-compatible 服务，支持 `OPENAI_USER_AGENT` 避免网关拦截，并兼容 Qwen `<think>` 输出后再返回 JSON。
- 前端影响：无
- 后端影响：Agent1 本地测试从纯规则对话升级为真实 LLM + 真实 Graph API；仍不接入 Agent2/Agent3 执行。
- 接口影响：无新增业务接口；LLM 配置读取 `OPENAI_API_KEY`、`OPENAI_API_BASE`、`OPENAI_MODEL_NAME`、`OPENAI_USER_AGENT`、`OPENAI_TIMEOUT_SECONDS`、`OPENAI_MAX_TOKENS`、`OPENAI_RESPONSE_FORMAT_JSON`。
- 数据库影响：无写入；只读调用 Graph API。
- 配置影响：本地 `.env` 使用 Qwen-compatible base URL、`OPENAI_MODEL_NAME=qwen`、`OPENAI_USER_AGENT=ApipostRuntime/1.1.0`、`OPENAI_RESPONSE_FORMAT_JSON=0`；密钥未写入协作文档。
- 验证：
  - `.venv/bin/python -m unittest discover -s tests`：通过，35 个测试
  - `printf '你好\n帮我查看上海门店现金流\n最近30天\n最近30天\n上海门店\n' | .venv/bin/python local_agent1_test.py`：通过，Qwen 生成自然追问，Graph API 自动选择 `medgraph`，最终输出 `cash_flow` 的 `task_contract`
  - `.venv/bin/python -m compileall agents integration.py tests tools local_agent1_test.py`：通过
  - `git diff --check`：通过
- 遗留问题：
  - Qwen 当前会产生 `<think>` 内容，代码已剥离并解析最终 JSON，但单轮响应仍偏慢
  - Workflow 正式 CrewAI kickoff 路径仍待后续接入

## [2026-05-20 13:36] Agent1 现金流识别和图谱元问题处理

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `agents/agent1.py`
  - `local_agent1_test.py`
  - `tests/test_agent1_workflow.py`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：Agent1 可识别 `现金流`、`流水`、`收款`、`回款`、`支出` 等业务问题；本地对话中用户询问“几个图谱/有哪些图谱”时，会作为元问题回答，不会误写入 `task_contract.input_context.metric`。
- 前端影响：无
- 后端影响：Agent1 指标识别和本地对话上下文处理增强。
- 接口影响：无
- 数据库影响：无写入；仍只读调用 Graph API。
- 配置影响：无
- 验证：
  - `.venv/bin/python -m unittest discover -s tests`：通过，35 个测试
  - `.venv/bin/python -m compileall agents integration.py tests tools local_agent1_test.py`：通过
  - `git diff --check`：通过
- 遗留问题：
  - 现金流最终业务口径仍需 Agent2 按账务字段复核

## [2026-05-20 12:06] Agent1 本地对话式澄清入口

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `local_agent1_test.py`
  - `tests/test_agent1_workflow.py`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：将本地 PyCharm 测试入口从批量表单式流程改为对话式澄清；用户直接输入问题，Agent1 每次只追问一个最关键澄清点，用户回答后重新理解上下文，必要时查图谱，直到生成 `task_contract`
- 前端影响：无
- 后端影响：无生产逻辑影响；本地入口更接近直接和 Agent1 对话
- 接口影响：无
- 数据库影响：无写入；仍只读查询图谱
- 配置影响：无
- 验证：
  - `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.test_local_agent1_chat_selects_one_clarification_at_a_time`：通过
  - `.venv/bin/python -m unittest discover -s tests`：通过，24 个测试
  - `.venv/bin/python -m compileall local_agent1_test.py`：通过
  - `printf '你好\n帮我看看最近门店转化怎么样\n1\n最近30天\n上海门店\n' | .venv/bin/python local_agent1_test.py`：通过，脚本表现为单轮对话式澄清
  - `git diff --check`：通过
- 遗留问题：
  - 本地入口仍是确定性 Agent1 的对话包装，不是完整 CrewAI kickoff

## [2026-05-20 11:07] Agent1 图谱驱动动态澄清

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `agents/agent1.py`
  - `local_agent1_test.py`
  - `tests/test_agent1_workflow.py`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：将 Agent1 澄清从固定模板改为图谱和用户问题驱动；图谱命中关系时动态生成口径选项，例如 `续卡` 会生成续卡数量、续卡率、续卡路径、续卡关联对象；用户问题包含地址或区域时，改为自由文本确认对应门店/组织范围；无图谱命中时不再优先展示固定指标列表
- 前端影响：无
- 后端影响：Agent1 的 `clarification_questions` 更动态，`type/options/source` 会随图谱命中结果和用户输入变化
- 接口影响：无新增接口
- 数据库影响：无写入；只读使用图谱查询结果
- 配置影响：无
- 验证：
  - `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.test_prepare_task_uses_graph_relationships_for_dynamic_metric_clarification tests.test_agent1_workflow.Agent1WorkflowTest.test_prepare_task_clarifies_address_without_fixed_clinic_choices`：通过
  - `.venv/bin/python -m unittest discover -s tests`：通过，23 个测试
  - `.venv/bin/python -m compileall agents/agent1.py local_agent1_test.py`：通过
  - `printf '你好\n帮我看看最近门店转化怎么样\n1\n最近30天\n上海门店\n' | .venv/bin/python local_agent1_test.py`：通过
  - `git diff --check`：通过
- 遗留问题：
  - 真实 API 当前账号候选 space 仍只返回 `medgraph`，其他 space 动态口径通过单元测试验证
  - 地址识别是规则式提取，后续可替换为更强的地址解析或 LLM 分类

## [2026-05-20 11:01] Agent1 非业务输入门控

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `agents/agent1.py`
  - `local_agent1_test.py`
  - `tests/test_agent1_workflow.py`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：修复输入“你好”等非业务文本时仍进入固定指标澄清模板的问题；Agent1 现在会先判断是否为业务分析需求，非业务输入不查询图谱、不生成固定指标选项，只要求用户补充业务分析问题；本地测试脚本在用户补充业务问题后会重新查询图谱并继续多轮澄清
- 前端影响：无
- 后端影响：Agent1 澄清入口增加业务意图门控；`run_agent1_clarification` 对非业务输入会跳过 `nebula_graph_query`
- 接口影响：无
- 数据库影响：无写入；非业务输入跳过图谱查询
- 配置影响：无
- 验证：
  - `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.test_prepare_task_does_not_use_fixed_metric_flow_for_non_business_input`：通过
  - `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.test_run_agent1_clarification_skips_graph_query_for_non_business_input`：通过
  - `.venv/bin/python -m unittest discover -s tests`：通过，20 个测试
  - `.venv/bin/python -m compileall agents/agent1.py local_agent1_test.py`：通过
  - `printf '你好\n帮我看看最近门店转化怎么样\n1\n2\n2\n' | .venv/bin/python local_agent1_test.py`：通过，先跳过图谱查询，补充业务问题后重新查询图谱并输出 `ready`
  - `git diff --check`：通过
- 遗留问题：
  - 意图判断目前是关键词规则，后续可以替换为 CrewAI/LLM 分类并保留当前测试作为回归约束

## [2026-05-20 10:48] Agent1 图谱 space 自动选择

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `tools/nebula_graph_query.py`
  - `local_agent1_test.py`
  - `tests/test_agent1_workflow.py`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：修正“由用户输入 graph space”的方向，改为 `nebula_graph_query` 自动调用 `GET /spaces`，再按用户问题与各 space 的 tag / edge / space 名称命中度选择目标 space；本地 PyCharm 脚本默认设置 `GRAPH_API_AUTO_SPACE=1`，不再要求用户输入库名
- 前端影响：无
- 后端影响：Agent1 图谱查询更接近真实自动流程；返回结果增加 `space_selection`，用于解释自动选择依据
- 接口影响：无新增接口；新增使用既有 `GET /spaces`
- 数据库影响：无写入；会只读探测候选 graph space 的 schema
- 配置影响：新增 `GRAPH_API_AUTO_SPACE`；设置为 `1` 时强制自动选择，设置为 `0` 且提供 `GRAPH_API_SPACE` 时固定查询指定 space
- 验证：
  - `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.test_nebula_graph_query_strict_mode_auto_selects_graph_space`：通过
  - `.venv/bin/python -m unittest discover -s tests`：通过，18 个测试
  - `.venv/bin/python -m compileall tools/nebula_graph_query.py local_agent1_test.py`：通过
  - `printf '帮我看看最近门店转化怎么样\n1\n2\n2\n' | .venv/bin/python local_agent1_test.py`：通过，未输入 graph space，真实 API 自动选择 `medgraph`
  - `git diff --check`：通过
- 遗留问题：
  - 当前真实 API 返回的候选中只显示 `medgraph`；如果账号权限开放更多 space，自动选择会纳入候选
  - 还没有实现跨多个 space 聚合查询，只是自动选择一个最匹配的 space

## [2026-05-20 10:36] Agent1 任务合同中文化

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `agents/agent1.py`
  - `tests/test_agent1_workflow.py`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：将 Agent1 输出给 Agent2 的 `task_contract.todos` 人类可读字段改为中文，包括 `name`、`method`、`expected_output`、`self_check`、`risk`、`fallback`；保留 `id`、`type`、`executor`、`depends_on` 等机器字段为稳定标识；新增 `input_context.metric_label` 供业务和工程人员阅读
- 前端影响：无
- 后端影响：Agent1 任务合同更适合人工评审；Agent2 仍可按原机器字段执行
- 接口影响：无新增接口；`task_contract.input_context` 新增向后兼容字段 `metric_label`
- 数据库影响：无
- 配置影响：无
- 验证：
  - `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.test_task_contract_uses_chinese_for_human_readable_todos`：通过
  - `.venv/bin/python -m unittest discover -s tests`：通过，17 个测试
  - `.venv/bin/python -m compileall agents/agent1.py local_agent1_test.py`：通过
  - `printf '帮我看看最近门店转化怎么样\n\n1\n2\n2\n' | .venv/bin/python local_agent1_test.py`：通过，真实 API 流程输出中文 `task_contract.todos`
  - `git diff --check`：通过
- 遗留问题：
  - 未在 PyCharm UI 内点击运行；命令行已验证同一脚本

## [2026-05-20 10:26] Agent1 本地多轮澄清测试脚本

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `agents/agent1.py`
  - `local_agent1_test.py`
  - `tests/test_agent1_workflow.py`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：把 PyCharm 本地测试脚本从单轮输出澄清问题，升级为多轮收集用户回答；用户选择澄清选项后，脚本会把回答转换为 Agent1 `user_context` 并重新运行，直到输出给 Agent2 的 `task_contract`；Agent1 也支持自定义指标口径覆盖
- 前端影响：无
- 后端影响：Agent1 本地测试链路增强；生产 Agent2/Agent3 未改
- 接口影响：无
- 数据库影响：无写入；只读调用真实 Graph API
- 配置影响：读取 `.env` 中的 `GRAPH_API_*`
- 验证：
  - `.venv/bin/python -m unittest discover -s tests`：通过，16 个测试
  - `.venv/bin/python -m compileall local_agent1_test.py agents/agent1.py`：通过
  - `printf '帮我看看最近门店转化怎么样\n\n1\n2\n2\n' | .venv/bin/python local_agent1_test.py`：通过，第二轮输出 `ready` 和 `task_contract`
  - `git diff --check`：通过
- 遗留问题：
  - 未在 PyCharm UI 内点击运行；命令行已验证同一脚本

## [2026-05-20 10:20] Agent1 PyCharm 本地真实流程测试脚本

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `local_agent1_test.py`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：新增 PyCharm 可直接运行的 Agent1 本地真实流程测试脚本；脚本读取 `.env`，强制真实 API 严格模式，支持输入用户问题和可选 graph space，输出真实图谱摘要和 Agent1 澄清问题
- 前端影响：无
- 后端影响：无生产逻辑影响；仅新增本地测试入口
- 接口影响：无
- 数据库影响：无写入；只读调用真实 Graph API
- 配置影响：读取 `.env` 中的 `GRAPH_API_*`
- 验证：
  - `.venv/bin/python -m compileall local_agent1_test.py`：通过
  - `printf '帮我看看最近门店转化怎么样\n\n' | .venv/bin/python local_agent1_test.py`：通过，真实 API 返回转化边并生成澄清问题
  - `git diff --check`：通过
- 遗留问题：
  - 未在 PyCharm UI 内点击运行；命令行已验证同一脚本

## [2026-05-20 09:24] Agent1 真实 Graph API 严格模式

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `agents/agent1.py`
  - `tools/nebula_graph_query.py`
  - `tests/test_agent1_workflow.py`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：新增 `GRAPH_API_STRICT=1` 严格真实 API 模式；启用后 `nebula_graph_query` 不使用 `MEDGRAPH_JSON_PATH` 或 mock fallback；按 Apipost 成功配置修正鉴权为 `Authorization: <API Key>`，请求体字段为 `statement`，并增加 Apipost 风格 `User-Agent`；Agent1 可基于真实 API 返回的 `转化` 边生成澄清问题
- 前端影响：无
- 后端影响：Agent1 严格依赖真实图谱数据的路径已可验证；未修改 Agent2/Agent3 主逻辑
- 接口影响：新增配置 `GRAPH_API_STRICT=1`；错误响应结构为 `status=error`、`source=graph_api`、空 `data.vertices/edges`
- 数据库影响：无写入；只读访问 Graph API
- 配置影响：需要 `GRAPH_API_KEY`；密钥已写入 git 忽略的本地 `.env`，未记录明文
- 验证：
  - `.venv/bin/python -m unittest discover -s tests`：通过，15 个测试
  - `.venv/bin/python -m compileall agents tools integration.py tests`：通过
  - `.venv/bin/python -m compileall tools/nebula_graph_query.py`：通过
  - `git diff --check`：通过
  - 真实 Graph API 严格模式联调：通过，返回 `medgraph` 的 27 个 tag、30 个 edge type，并取到 `patient --转化--> member` 边；Agent1 返回 `needs_clarification`
- 遗留问题：
  - 尚未把真实 API 成功链路接入 CrewAI kickoff

## [2026-05-20 09:21] Agent1 图谱查询和澄清入口实现

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `agents/agent1.py`
  - `tools/nebula_graph_query.py`
  - `integration.py`
  - `tests/test_agent1_workflow.py`
  - `docs/requirements/agent1-system-tooling-requirements.md`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：只推进 Agent1 范围；新增 `run_agent1_clarification` 本地入口，Agent1 可先调用 `nebula_graph_query` 获取图谱数据再生成澄清结果；`nebula_graph_query` 改为正式 Graph API 优先、本地 JSON fallback、mock fallback，并兼容 `raw` 中的 Nebula 错误文本
- 前端影响：无
- 后端影响：Agent1 澄清链路和图谱查询工具行为增强；未修改 Agent2/Agent3 主逻辑
- 接口影响：`nebula_graph_query` 工具名不变；新增可选环境变量 `GRAPH_API_BASE_URL`、`GRAPH_API_KEY`、`GRAPH_API_SPACE`、`GRAPH_API_TIMEOUT_SECONDS`
- 数据库影响：无写入；只读访问 Graph API 或本地 JSON
- 配置影响：正式 Graph API 需要通过环境变量提供 Bearer API Key，不硬编码密钥
- 验证：
  - `.venv/bin/python -m unittest discover -s tests`：通过，12 个测试
  - `.venv/bin/python -m compileall agents tools integration.py tests`：通过
  - `GRAPH_API_KEY= MEDGRAPH_JSON_PATH=/Users/ameng/Downloads/medgraph_backup.json .venv/bin/python - <<'PY' ...`：通过，返回 `needs_clarification`
  - `git diff --check`：通过
- 遗留问题：
  - 未用真实 Graph API Key 联调 `https://graph.automed.cn`
  - Workflow 正式 CrewAI kickoff、CrewAI 输出 JSON 解析和失败降级仍待后续 Agent1 工作

## [2026-05-20 09:05] 图数据库数据源事实同步

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
  - `docs/requirements/agent1-system-tooling-requirements.md`
- 变更摘要：补充 NebulaGraph 3.8 / nGQL 正式数据源事实，明确 Graph API 正式入口、Bearer 鉴权、只读限制，以及 `GET /{space}/edges` 和无效 space 错误码的真实行为
- 前端影响：无
- 后端影响：无
- 接口影响：文档层面明确后续 agent 应优先使用 `POST /{space}/query` 获取 edge type 和只读 nGQL 结果
- 数据库影响：无
- 配置影响：记录了正式环境依赖 API Key，不记录真实 key
- 验证：
  - `sed -n '600,720p' docs/requirements/agent1-system-tooling-requirements.md`：通过
  - `sed -n '936,970p' docs/requirements/agent1-system-tooling-requirements.md`：通过
  - `git status --short`：通过
- 遗留问题：
  - `MEDGRAPH_JSON_PATH` 是否长期保留为离线 fallback 仍待定
  - 指标口径在图谱中的完整度仍待业务确认

## [2026-05-22 09:11] 启动 app/web 前端项目

- Agent：codex-gpt5
- 状态：完成
- 修改文件：
  - `app/web/package-lock.json`
  - `.agents/ACTIVE_WORK.md`
  - `.agents/CHANGELOG.md`
- 变更摘要：为 `app/web` 安装 npm 依赖并启动 Vite 开发服务器，确认项目可在本地访问；安装过程中因 npm 源超时，改用更长超时和重试参数后成功完成安装
- 前端影响：本地开发环境已就绪，可通过 `http://localhost:5175/` 访问页面
- 后端影响：无
- 接口影响：无
- 数据库影响：无
- 配置影响：无
- 验证：
  - `npm install --registry=https://registry.npmjs.org --fetch-timeout=600000 --fetch-retries=5 --fetch-retry-maxtimeout=120000`：通过
  - `npm run dev -- --host 0.0.0.0`：通过
  - `git status --short`：通过
- 遗留问题：
  - 首次安装依赖受网络波动影响明显，后续如再次超时可继续使用延长超时参数
