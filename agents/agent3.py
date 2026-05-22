"""
Agent3: sidecar retrospective review for the workflow.

这个版本继续往前推进了两件关键能力：
1. 复盘结果不再只有 Markdown，还会额外产出结构化对象，便于接口和前端直接消费。
2. 复盘会感知 ProblemStore 的健康状态，避免把“底层文件损坏后刚恢复”误判成“真的没有问题”。

设计原则保持不变：
- 主流程优先：Agent3 永远是旁路，不阻塞 Agent1/Agent2 的主交付。
- 真实输入优先：尽量依据 task_contract、review_result、process_log 和问题记录本身做判断。
- 可读 + 可编排并重：既给人看的 Markdown，也给程序消费的 structured_review。
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure direct execution can still import the repo packages.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from tools.knowledge_candidate_store import KnowledgeCandidateStore
from tools.problem_collector import ProblemCollectorReader
from tools.problem_store import ProblemStore
from tools.review_candidate_store import ReviewCandidateStore

load_dotenv()


def _parse_payload(raw_value: Any, default: Any) -> Any:
    if raw_value in (None, "", {}):
        return default
    if isinstance(raw_value, (dict, list)):
        return raw_value
    if isinstance(raw_value, str):
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            return default
    return default


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _bullet_lines(text: str) -> list[str]:
    """
    从多行文本里提取以 "- " 开头的 bullet。

    这不是为了做复杂的自然语言解析，而是为了把 deterministic 文本里的关键结论
    抽成结构化列表，便于上层页面做卡片化展示。
    """
    lines: list[str] = []
    for raw_line in str(text).splitlines():
        line = raw_line.strip()
        if line.startswith("- "):
            lines.append(line[2:].strip())
    return lines


def _risk_object(
    *,
    category: str,
    title: str,
    risk_level: str,
    owner: str,
    action: str,
    evidence: list[str],
    section: str,
) -> dict[str, Any]:
    """
    构造 Agent3 的标准风险对象。

    这是本轮改造的核心抽象。之前 structured_review 里的 findings 只是字符串数组，
    调用方只能“展示这句话”，却很难继续做这些事情：
    - 按风险等级排序
    - 按 owner 分配待办
    - 按 category 做聚合统计
    - 展示证据链而不是只展示一句结论

    现在统一通过这个工厂函数生成风险对象，至少保证每条 finding 都具备：
    - category：问题类别，例如 planning/process/privacy
    - title：简洁标题，适合列表展示
    - risk_level：critical/high/medium/low
    - owner：默认建议由谁负责
    - action：下一步建议动作
    - evidence：支撑这条风险判断的证据列表
    - section：它来自哪个复盘章节，方便回跳和过滤
    """
    return {
        "category": category,
        "title": title,
        "risk_level": risk_level,
        "owner": owner,
        "action": action,
        "evidence": evidence,
        "section": section,
    }


def _top_counter_items(counter: Counter, limit: int = 5) -> list[dict[str, Any]]:
    """
    将 Counter 转成稳定的结构化列表。

    不直接暴露 Counter 对象有两个原因：
    1. Counter 不是标准 JSON schema 语义，前端直接消费不够友好；
    2. list[{name,count}] 的形式更利于后续排序、图表和接口演进。
    """
    return [
        {"name": name, "count": count}
        for name, count in counter.most_common(limit)
    ]


def _review_priority(review_result: dict[str, Any]) -> str:
    """
    给本轮复盘结果打一个统一优先级。

    这是为了让后续页面可以直接按 priority 排序，不必在前端重复写判断逻辑。
    当前规则故意保持简单透明：
    - 隐私失败最高；
    - 范围越界或 blocked 次高；
    - needs_revision 为 medium；
    - approved 为 low。
    """
    if review_result.get("privacy_check") == "failed":
        return "critical"
    if review_result.get("scope_violations") or review_result.get("status") == "blocked":
        return "high"
    if review_result.get("status") == "needs_revision":
        return "medium"
    return "low"


def _section_risk_objects(
    *,
    task_contract: dict[str, Any],
    graph_scope: dict[str, Any],
    process_log: dict[str, Any],
    review_result: dict[str, Any],
    problem_records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """
    为每个复盘章节生成显式风险对象。

    这里刻意不做“把文本再解析回结构”的反向工程，而是直接依据真实输入构造风险对象。
    这样做有三个明显好处：
    1. 稳定：不依赖中文措辞变化，后续即使我们改文案，风险结构也不受影响；
    2. 可追溯：每条风险都能明确指向它引用的输入证据；
    3. 可演进：未来如果要输出 owner SLA、截止时间、工单编号，可以在这层继续扩展。
    """
    section_risks = {
        "step_evaluation": _step_evaluation_risks(task_contract),
        "graph_gap_analysis": _graph_gap_risks(graph_scope),
        "process_optimization": _process_optimization_risks(process_log),
        "insight_refinement": _insight_refinement_risks(review_result, problem_records),
        "execution_summary": _execution_summary_risks(review_result, process_log, problem_records),
    }
    return section_risks


def _step_evaluation_risks(task_contract: dict[str, Any]) -> list[dict[str, Any]]:
    """
    基于 task_contract 生成“步骤拆解评价”章节的风险对象。

    这里聚焦的不是执行结果，而是规划阶段是否把关键边界定义清楚。
    """
    if not task_contract:
        return [
            _risk_object(
                category="planning_missing_context",
                title="缺少任务合同",
                risk_level="high",
                owner="Agent1",
                action="在进入 Agent2 前确保 Agent1 产出完整 task_contract。",
                evidence=["task_contract 为空，无法评估步骤规划完整性。"],
                section="step_evaluation",
            )
        ]

    required_capabilities = [
        capability
        for capability in _as_list(task_contract.get("required_capabilities"))
        if isinstance(capability, dict) and capability.get("required")
    ]
    capability_names = [str(item.get("name", "")).strip() for item in required_capabilities]
    risks: list[dict[str, Any]] = []

    if "data_fetch" in capability_names and "sql_check" not in capability_names:
        risks.append(
            _risk_object(
                category="planning_capability_gap",
                title="取数任务缺少 SQL 校验能力",
                risk_level="high",
                owner="Agent1",
                action="将 sql_check 明确加入 required_capabilities。",
                evidence=[
                    f"required_capabilities={capability_names}",
                    "task_contract 包含 data_fetch，但不包含 sql_check。",
                ],
                section="step_evaluation",
            )
        )

    if "root_cause_analysis" in capability_names and not task_contract.get("input_context", {}).get("problem_signal"):
        risks.append(
            _risk_object(
                category="planning_signal_gap",
                title="根因分析任务缺少问题信号定义",
                risk_level="medium",
                owner="Agent1",
                action="补充 problem_signal、基准校验规则和异常定义。",
                evidence=[
                    f"required_capabilities={capability_names}",
                    "input_context.problem_signal 为空。",
                ],
                section="step_evaluation",
            )
        )

    if "report_generation" in capability_names and not task_contract.get("output_requirements", {}):
        risks.append(
            _risk_object(
                category="planning_output_gap",
                title="报告任务缺少结构化交付约束",
                risk_level="medium",
                owner="Agent1",
                action="补充 output_requirements，明确必含章节与验收标准。",
                evidence=["required_capabilities 包含 report_generation。", "output_requirements 为空。"],
                section="step_evaluation",
            )
        )

    if not task_contract.get("agent2_planning_policy", {}):
        risks.append(
            _risk_object(
                category="planning_policy_gap",
                title="缺少 Agent2 规划策略边界",
                risk_level="medium",
                owner="Agent1",
                action="补充 agent2_planning_policy，约束 Agent2 的执行自由度。",
                evidence=["agent2_planning_policy 为空。"],
                section="step_evaluation",
            )
        )

    return risks


def _graph_gap_risks(graph_scope: dict[str, Any]) -> list[dict[str, Any]]:
    """
    生成“图谱补缺建议”对应的风险对象。

    这里关注的不是图谱查询是否成功，而是本轮 task scope 是否足够定义清楚，
    能不能支持 Agent2 安全且稳定地使用图谱。
    """
    if not graph_scope:
        return [
            _risk_object(
                category="graph_scope_missing",
                title="缺少图谱范围定义",
                risk_level="high",
                owner="Agent1",
                action="在任务澄清完成后同步产出 graph_scope。",
                evidence=["graph_scope 为空。"],
                section="graph_gap_analysis",
            )
        ]

    risks: list[dict[str, Any]] = []
    target_entities = _as_list(graph_scope.get("target_entities"))
    relationships = _as_list(graph_scope.get("required_relationships"))
    constraints = graph_scope.get("data_source_constraints", {})

    if not target_entities:
        risks.append(
            _risk_object(
                category="graph_target_gap",
                title="图谱范围未声明目标实体",
                risk_level="medium",
                owner="Agent1",
                action="补充 target_entities，明确 Agent2 要围绕哪些实体查询。",
                evidence=["graph_scope.target_entities 为空。"],
                section="graph_gap_analysis",
            )
        )

    if not relationships:
        risks.append(
            _risk_object(
                category="graph_relationship_gap",
                title="图谱范围未声明关键关系链",
                risk_level="medium",
                owner="Agent1",
                action="补充 required_relationships，避免 Agent2 查询路径发散。",
                evidence=["graph_scope.required_relationships 为空。"],
                section="graph_gap_analysis",
            )
        )

    if constraints and not constraints.get("authorized_spaces"):
        risks.append(
            _risk_object(
                category="graph_authorization_gap",
                title="图谱数据源缺少授权空间白名单",
                risk_level="medium",
                owner="Agent1",
                action="补充 authorized_spaces，限制 Agent2 误查非目标图谱。",
                evidence=["graph_scope.data_source_constraints 存在，但 authorized_spaces 为空。"],
                section="graph_gap_analysis",
            )
        )

    return risks


def _process_optimization_risks(process_log: dict[str, Any]) -> list[dict[str, Any]]:
    """
    基于 process_log 生成流程优化风险对象。

    这里的“风险”偏流程效率和可治理性，而不是业务口径错误。
    """
    events = [
        event for event in _as_list(process_log.get("events"))
        if isinstance(event, dict)
    ]
    if not events:
        return [
            _risk_object(
                category="process_log_missing",
                title="缺少执行事件日志",
                risk_level="high",
                owner="Workflow",
                action="确保 workflow 在关键节点持续写入 process_log.events。",
                evidence=["process_log.events 为空。"],
                section="process_optimization",
            )
        ]

    risks: list[dict[str, Any]] = []
    status_counter = Counter(str(event.get("status", "unknown")) for event in events)
    task_counter = Counter(str(event.get("task", "unknown")) for event in events)
    blocked_reasons = _as_list(process_log.get("audit_summary", {}).get("blocked_reasons"))

    if status_counter.get("failed", 0):
        risks.append(
            _risk_object(
                category="process_failure_density",
                title="流程中存在失败事件",
                risk_level="high",
                owner="Workflow",
                action="为失败事件增加重试、降级或明确的错误分类。",
                evidence=[f"status_distribution={dict(status_counter)}"],
                section="process_optimization",
            )
        )

    repeated_tasks = [task for task, count in task_counter.items() if count > 1]
    if repeated_tasks:
        risks.append(
            _risk_object(
                category="process_rework_signal",
                title="任务节点存在重复记录",
                risk_level="medium",
                owner="Workflow",
                action="区分正常步骤与重试步骤，便于统计真实返工率。",
                evidence=[f"repeated_tasks={repeated_tasks}"],
                section="process_optimization",
            )
        )

    if blocked_reasons:
        risks.append(
            _risk_object(
                category="process_blocked_reason_unstructured",
                title="阻塞原因仍是非结构化文本",
                risk_level="medium",
                owner="Workflow",
                action="将 blocked_reasons 进一步归类为固定 taxonomy。",
                evidence=[f"blocked_reasons={blocked_reasons}"],
                section="process_optimization",
            )
        )

    return risks


def _insight_refinement_risks(
    review_result: dict[str, Any],
    problem_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    生成“经验沉淀”章节的风险对象。

    这里的风险更偏“知识沉淀是否可持续”，而不是某一步马上报错。
    """
    risks: list[dict[str, Any]] = []
    stages = sorted({record.get("stage", "unknown") for record in problem_records if isinstance(record, dict)})

    if not problem_records:
        risks.append(
            _risk_object(
                category="insight_missing_samples",
                title="本轮缺少问题样本，经验沉淀基础偏弱",
                risk_level="low",
                owner="Agent1/Agent2",
                action="检查是否存在问题漏报，保证后续复盘有足够样本。",
                evidence=["problem_records 为空。"],
                section="insight_refinement",
            )
        )

    if review_result.get("privacy_check") != "passed":
        risks.append(
            _risk_object(
                category="insight_privacy_rule",
                title="隐私检查规则需要固化为标准知识",
                risk_level="critical",
                owner="Agent2",
                action="将手机号、邮箱、患者标识脱敏规则固化为执行前置检查。",
                evidence=[f"privacy_check={review_result.get('privacy_check', 'unknown')}"],
                section="insight_refinement",
            )
        )

    if review_result.get("scope_violations"):
        risks.append(
            _risk_object(
                category="insight_scope_rule",
                title="范围边界校验需要沉淀为固定规则",
                risk_level="high",
                owner="Agent2",
                action="把 clinic_scope 回查纳入 Agent2 交付前的固定校验清单。",
                evidence=[f"scope_violations={review_result.get('scope_violations')}"],
                section="insight_refinement",
            )
        )

    if stages:
        risks.append(
            _risk_object(
                category="insight_hot_stage",
                title="高发阶段值得沉淀专项经验",
                risk_level="low",
                owner="Agent3",
                action="围绕高发 stage 形成 FAQ、模板或标准口径文档。",
                evidence=[f"problem_stages={stages}"],
                section="insight_refinement",
            )
        )

    return risks


def _execution_summary_risks(
    review_result: dict[str, Any],
    process_log: dict[str, Any],
    problem_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    生成“执行摘要”章节的风险对象。

    这是总览层的风险，优先级通常更高，因为它直接决定本轮结果能否交付。
    """
    risks: list[dict[str, Any]] = []
    review_status = review_result.get("status", "unknown")
    revision_requests = _as_list(review_result.get("revision_requests"))
    blocked_reasons = _as_list(process_log.get("audit_summary", {}).get("blocked_reasons"))

    if review_result.get("privacy_check") == "failed":
        risks.append(
            _risk_object(
                category="delivery_privacy_blocker",
                title="存在隐私泄露风险，当前结果不可直接交付",
                risk_level="critical",
                owner="Agent2",
                action="移除或脱敏敏感信息后重新提交审核。",
                evidence=[f"privacy_check={review_result.get('privacy_check')}"],
                section="execution_summary",
            )
        )

    if review_result.get("scope_violations"):
        risks.append(
            _risk_object(
                category="delivery_scope_blocker",
                title="存在数据范围越界风险",
                risk_level="high",
                owner="Agent2",
                action="重新按 task_contract 的 scope 取数并复核输出。",
                evidence=[f"scope_violations={review_result.get('scope_violations')}"],
                section="execution_summary",
            )
        )

    if review_status == "needs_revision":
        risks.append(
            _risk_object(
                category="delivery_revision_required",
                title="主流程结果需要返工后才能稳定交付",
                risk_level="medium",
                owner="Agent2",
                action="根据 revision_requests 补齐缺失能力和证据链。",
                evidence=[f"revision_request_count={len(revision_requests)}"],
                section="execution_summary",
            )
        )

    if blocked_reasons:
        risks.append(
            _risk_object(
                category="delivery_blocked_reasons_present",
                title="流程中已出现阻塞信息，需纳入交付判断",
                risk_level="medium" if review_status == "approved" else "high",
                owner="Workflow",
                action="复核 blocked_reasons 是否属于已解决历史事件，避免误判已交付结果。",
                evidence=[f"blocked_reasons={blocked_reasons}", f"problem_record_count={len(problem_records)}"],
                section="execution_summary",
            )
        )

    return risks


def _flatten_risk_objects(section_risks: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """
    把分章节风险对象扁平化成单列表。

    扁平列表主要服务两个场景：
    - 前端做全局风险面板
    - 后续把风险对象直接转成待办项 / 工单
    """
    flattened: list[dict[str, Any]] = []
    for risks in section_risks.values():
        flattened.extend(risks)
    return flattened


def _review_candidates_from_risks(
    *,
    run_id: str,
    task_id: str,
    risk_objects: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    将风险对象转成“整改建议候选项”。

    这里明确只收集和优化图谱/流程相关的建议，不把所有风险都写进整改池。
    这样第一版人工审核列表更聚焦，也更符合“先看哪些建议值得落地”的目标。
    """
    candidates: list[dict[str, Any]] = []
    for risk in risk_objects:
        section = str(risk.get("section", ""))
        if section not in {"graph_gap_analysis", "process_optimization", "step_evaluation"}:
            continue
        candidate_type = "graph_optimization" if section == "graph_gap_analysis" else "process_optimization"
        candidates.append(
            {
                "run_id": run_id,
                "task_id": task_id,
                "candidate_type": candidate_type,
                "title": risk.get("title", ""),
                "priority": risk.get("risk_level", "medium"),
                "owner": risk.get("owner", ""),
                "suggested_action": risk.get("action", ""),
                "evidence": risk.get("evidence", []),
                "source_section": section,
            }
        )
    return candidates


def _knowledge_candidates_from_review(
    *,
    run_id: str,
    task_id: str,
    structured_review: dict[str, Any],
    metric_label: str,
) -> list[dict[str, Any]]:
    """
    将经验沉淀章节转换成“知识候选项”。

    第一版不做复杂 NLP 拆句，而是优先把已经结构化好的风险/洞察装配成可审核条目。
    这样虽然保守，但更稳定，也更利于人工筛选。
    """
    section = structured_review.get("sections", {}).get("insight_refinement", {})
    findings = _as_list(section.get("findings"))
    candidates: list[dict[str, Any]] = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        candidates.append(
            {
                "run_id": run_id,
                "task_id": task_id,
                "candidate_type": "experience_rule",
                "category": item.get("category", "insight"),
                "title": item.get("title", "") or f"{metric_label} 经验沉淀候选",
                "content": item.get("action", ""),
                "evidence": item.get("evidence", []),
                "source_section": "insight_refinement",
            }
        )
    return candidates


def _review_overview(
    *,
    task_contract: dict[str, Any],
    review_result: dict[str, Any],
    process_log: dict[str, Any],
    problem_records: list[dict[str, Any]],
    storage_meta: dict[str, Any],
) -> dict[str, Any]:
    """
    生成结构化复盘的总览头信息。

    这层信息专门给“列表页 / 摘要卡片 / 接口首页”用，
    目标是让调用方不用深入 sections 也能快速判断：
    - 这轮任务是谁、状态如何、风险高不高；
    - 一共有多少问题、多少返工请求；
    - 底层存储是否健康。
    """
    events = _as_list(process_log.get("events"))
    return {
        "schema_version": "1.0",
        "task_id": task_contract.get("task_id", ""),
        "review_status": review_result.get("status", "unknown"),
        "priority": _review_priority(review_result),
        "problem_record_count": len(problem_records),
        "revision_request_count": len(_as_list(review_result.get("revision_requests"))),
        "scope_violation_count": len(_as_list(review_result.get("scope_violations"))),
        "event_count": len(events),
        "storage_status": storage_meta.get("storage_status", "unknown"),
    }


def _build_process_insights(process_log: dict[str, Any]) -> dict[str, Any]:
    """
    从 process_log 中抽取更稳定的过程洞察。

    这里不再只返回“event_count + 原始文本”，而是把常用统计显式展开：
    - 各 event_type 数量
    - 各 status 数量
    - 高频 task
    - 最近事件样本
    """
    events = [
        event for event in _as_list(process_log.get("events"))
        if isinstance(event, dict)
    ]
    event_type_counter = Counter(str(event.get("event_type", "unknown")) for event in events)
    status_counter = Counter(str(event.get("status", "unknown")) for event in events)
    task_counter = Counter(str(event.get("task", "unknown")) for event in events)
    return {
        "event_type_distribution": dict(event_type_counter),
        "status_distribution": dict(status_counter),
        "top_tasks": _top_counter_items(task_counter),
        "recent_events": events[-5:],
    }


class StepDecompositionEvaluator:
    name = "step_decomposition_evaluator"
    description = (
        "Evaluate whether the real Agent1 task contract covers key execution "
        "capabilities and whether the capability mix is coherent."
    )

    def _run(self, task_contract: str) -> str:
        contract = _parse_payload(task_contract, {})
        if not isinstance(contract, dict) or not contract:
            return "步骤拆解评估：缺少 task_contract，无法判断本轮规划是否完整。"

        required_capabilities = [
            capability
            for capability in _as_list(contract.get("required_capabilities"))
            if isinstance(capability, dict) and capability.get("required")
        ]
        capability_names = [str(item.get("name", "")).strip() for item in required_capabilities]
        findings: list[str] = []
        suggestions: list[str] = []

        if "data_fetch" in capability_names and "sql_check" not in capability_names:
            findings.append("任务包含数据取数，但未显式要求 SQL 校验能力。")
            suggestions.append("将 sql_check 设为必需能力，避免取数 SQL 漏条件或字段错误。")

        if "root_cause_analysis" in capability_names:
            problem_signal = contract.get("input_context", {}).get("problem_signal", {})
            if not problem_signal:
                findings.append("任务要求根因分析，但缺少 problem_signal 等问题信号定义。")
                suggestions.append("在 input_context 中补充异常信号、基准校验规则和分析目标。")

        if "report_generation" in capability_names:
            report_constraints = contract.get("output_requirements", {})
            if not report_constraints:
                findings.append("任务要求生成报告，但输出要求没有结构化约束。")
                suggestions.append("补充 report_generation 的交付格式、必含章节和验收标准。")

        policy = contract.get("agent2_planning_policy", {})
        if not policy:
            findings.append("缺少 Agent2 规划策略，执行自由度边界不清晰。")
            suggestions.append("补充 agent2_planning_policy，明确能否自拟步骤和必须遵守的边界。")

        if not findings:
            return (
                "步骤拆解评估：通过。\n"
                f"- task_id: {contract.get('task_id', 'unknown')}\n"
                f"- 必需能力: {', '.join(capability_names) or '无'}\n"
                "- 当前任务合同已覆盖主要执行能力，未发现明显的步骤缺口。"
            )

        return (
            "步骤拆解评估：发现以下需要优化的点。\n"
            f"- task_id: {contract.get('task_id', 'unknown')}\n"
            f"- 必需能力: {', '.join(capability_names) or '无'}\n"
            + "\n".join(f"- {item}" for item in findings)
            + "\n\n改进建议：\n"
            + "\n".join(f"- {item}" for item in suggestions)
        )


class GraphGapDetector:
    name = "graph_gap_detector"
    description = "Inspect the real graph scope used by Agent1 and identify missing graph coverage."

    def _run(self, graph_scope_summary: str) -> str:
        graph_scope = _parse_payload(graph_scope_summary, {})
        if not isinstance(graph_scope, dict) or not graph_scope:
            return "知识图谱缺陷分析：缺少 graph_scope，无法判断图谱边界是否完整。"

        target_entities = _as_list(graph_scope.get("target_entities"))
        relationships = _as_list(graph_scope.get("required_relationships"))
        constraints = graph_scope.get("data_source_constraints", {})
        findings: list[str] = []
        suggestions: list[str] = []

        if not target_entities:
            findings.append("本轮图谱范围没有明确目标实体。")
            suggestions.append("在 Agent1 澄清阶段补充 target_entities，避免 Agent2 图谱查询过散。")

        if not relationships:
            findings.append("本轮图谱范围没有明确要求的关系链。")
            suggestions.append("补充 required_relationships，让 Agent2 明确验证哪些实体连接。")

        if constraints and not constraints.get("authorized_spaces"):
            findings.append("图谱数据源约束缺少 authorized_spaces。")
            suggestions.append("补充可访问 space 白名单，减少误查错图谱的风险。")

        entity_text = "、".join(
            str(entity.get("name", entity))
            for entity in target_entities
            if entity
        ) or "未声明"
        relationship_text = "；".join(
            f"{item.get('from', '?')} -[{item.get('relation', '?')}]-> {item.get('to', '?')}"
            for item in relationships
            if isinstance(item, dict)
        ) or "未声明"

        if not findings:
            return (
                "知识图谱缺陷分析：当前图谱边界定义基本完整。\n"
                f"- 目标实体: {entity_text}\n"
                f"- 关键关系: {relationship_text}\n"
                "- 当前更适合继续积累真实缺口样本，而不是先新增图谱结构。"
            )

        return (
            "知识图谱缺陷分析：发现以下边界缺口。\n"
            + "\n".join(f"- {item}" for item in findings)
            + "\n\n当前任务图谱范围：\n"
            + f"- 目标实体: {entity_text}\n"
            + f"- 关键关系: {relationship_text}\n"
            + "\n\n补充建议：\n"
            + "\n".join(f"- {item}" for item in suggestions)
        )


class ProcessOptimizer:
    name = "process_optimizer"
    description = "Summarize bottlenecks from the real workflow process log."

    def _run(self, process_summary: str) -> str:
        process_log = _parse_payload(process_summary, {})
        events = _as_list(process_log.get("events")) if isinstance(process_log, dict) else []
        if not events:
            return "流程优化建议：缺少 process_log.events，无法从执行轨迹中识别瓶颈。"

        status_counter = Counter(str(event.get("status", "unknown")) for event in events if isinstance(event, dict))
        task_counter = Counter(str(event.get("task", "unknown")) for event in events if isinstance(event, dict))
        blocked_reasons = _as_list(process_log.get("audit_summary", {}).get("blocked_reasons"))

        findings: list[str] = []
        suggestions: list[str] = []

        if status_counter.get("failed", 0):
            findings.append(f"流程中出现 {status_counter['failed']} 个失败事件。")
            suggestions.append("为失败事件增加分类码和重试/降级策略，避免只留下自然语言日志。")

        repeated_tasks = [task for task, count in task_counter.items() if count > 1]
        if repeated_tasks:
            findings.append(f"存在重复记录的任务节点：{', '.join(repeated_tasks)}。")
            suggestions.append("区分重试事件与正常步骤，便于后续统计真正的返工率。")

        if blocked_reasons:
            findings.append("审计摘要中已记录阻塞原因，但尚未看到结构化优化点沉淀。")
            suggestions.append("将 blocked_reasons 归类为固定 taxonomy，支持按类别统计和治理。")

        if not findings:
            return (
                "流程优化建议：当前日志链路较简洁。\n"
                f"- 总事件数: {len(events)}\n"
                f"- 状态分布: {dict(status_counter)}\n"
                "- 下一步建议补充耗时、重试次数和工具调用明细，提升复盘精度。"
            )

        return (
            "流程优化建议：从真实执行日志中识别到以下优化点。\n"
            + "\n".join(f"- {item}" for item in findings)
            + "\n\n建议动作：\n"
            + "\n".join(f"- {item}" for item in suggestions)
        )


class InsightRefiner:
    name = "insight_refiner"
    description = "Convert the real review context into reusable operating knowledge."

    def _run(self, task_summary: str) -> str:
        summary = _parse_payload(task_summary, {})
        if not isinstance(summary, dict) or not summary:
            return "经验沉淀：缺少复盘上下文，无法输出可复用知识。"

        input_context = summary.get("task_contract", {}).get("input_context", {})
        review_result = summary.get("review_result", {})
        problem_records = _as_list(summary.get("problem_records"))
        metric_label = input_context.get("metric_label") or input_context.get("metric") or "目标指标"
        stages = sorted({record.get("stage", "unknown") for record in problem_records if isinstance(record, dict)})
        privacy_check = review_result.get("privacy_check", "unknown")
        scope_violations = _as_list(review_result.get("scope_violations"))

        lines = [
            "## 可复用经验沉淀",
            "",
            "### 本轮固定结论",
            f"- 核心指标: {metric_label}",
            f"- 输出格式: {input_context.get('output_format', 'unknown')}",
            f"- 审核状态: {review_result.get('status', 'unknown')}",
            "",
            "### 本轮暴露出的操作规则",
        ]

        if stages:
            lines.append(f"- 问题高发阶段: {', '.join(stages)}")
        else:
            lines.append("- 本轮未记录问题上报，后续可检查是否存在漏报。")

        if privacy_check != "passed":
            lines.append("- 对外输出前必须执行敏感信息检查，尤其是手机号、邮箱和患者标识。")

        if scope_violations:
            lines.append("- Agent2 取数后必须回查 clinic_scope，避免超范围输出。")

        lines.extend(
            [
                "",
                "### 建议沉淀到系统配置的知识",
                f"- 为 {metric_label} 建立标准口径模板和验收清单。",
                "- 将常见问题上报按 stage、severity 归档，形成可检索的复盘样本库。",
                "- 为 workflow 级复盘保留结构化输入快照，减少只靠自然语言回忆的偏差。",
            ]
        )
        return "\n".join(lines)


def _safe_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError):
        return None


def _records_for_run(problem_records: list[dict[str, Any]], process_log: dict[str, Any]) -> list[dict[str, Any]]:
    events = _as_list(process_log.get("events")) if isinstance(process_log, dict) else []
    if not events:
        return problem_records
    run_start = _safe_datetime(events[0].get("timestamp"))
    if run_start is None:
        return problem_records

    filtered: list[dict[str, Any]] = []
    for record in problem_records:
        if not isinstance(record, dict):
            continue
        record_ts = _safe_datetime(record.get("timestamp"))
        if record_ts is None or record_ts >= run_start:
            filtered.append(record)
    return filtered


def _build_problem_summary(problem_records: list[dict[str, Any]]) -> str:
    if not problem_records:
        return "## 问题汇总\n\n本轮未读取到问题上报记录。需要确认是流程顺畅，还是 Agent1/Agent2 存在漏报。"

    severity_counter = Counter(record.get("severity", "unknown") for record in problem_records)
    stage_counter = Counter(record.get("stage", "unknown") for record in problem_records)
    top_stages = ", ".join(f"{stage}:{count}" for stage, count in stage_counter.most_common(5))
    lines = [
        "## 问题汇总",
        "",
        f"- 问题总数: {len(problem_records)}",
        f"- 严重度分布: {dict(severity_counter)}",
        f"- 阶段分布: {top_stages or '无'}",
        "",
        "### 样例记录",
    ]
    for record in problem_records[:3]:
        lines.append(
            f"- [{record.get('severity', 'unknown')}] {record.get('stage', 'unknown')}: "
            f"{record.get('problem', 'unknown')} -> {record.get('solution', 'unknown')}"
        )
    return "\n".join(lines)


def _build_problem_summary_structured(problem_records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    生成问题汇总的结构化对象。

    这里和 Markdown 版本并行存在，原因是两类消费场景完全不同：
    - Markdown 更适合直接给人看；
    - dict/list 更适合前端表格、筛选器、接口聚合。
    """
    severity_counter = Counter(record.get("severity", "unknown") for record in problem_records)
    stage_counter = Counter(record.get("stage", "unknown") for record in problem_records)
    return {
        "total_count": len(problem_records),
        "severity_distribution": dict(severity_counter),
        "stage_distribution": dict(stage_counter),
        "top_severities": _top_counter_items(severity_counter, limit=3),
        "top_stages": _top_counter_items(stage_counter, limit=5),
        "sample_records": problem_records[:3],
    }


def _build_execution_summary(review_result: dict[str, Any], problem_records: list[dict[str, Any]]) -> str:
    revision_requests = _as_list(review_result.get("revision_requests"))
    summary = (
        f"本轮主流程审核状态为 {review_result.get('status', 'unknown')}，"
        f"累计读取到 {len(problem_records)} 条问题记录，"
        f"返工请求 {len(revision_requests)} 条。"
    )
    if review_result.get("privacy_check") == "failed":
        summary += " 其中包含隐私风险，优先级最高。"
    elif review_result.get("scope_violations"):
        summary += " 当前存在范围越界风险，需要优先收敛数据边界。"
    elif review_result.get("status") == "approved":
        summary += " 主链路结果可交付，后续优化重点应放在复盘沉淀质量。"
    return summary


def _build_structured_review(
    *,
    task_contract: dict[str, Any],
    graph_scope: dict[str, Any],
    process_log: dict[str, Any],
    review_result: dict[str, Any],
    problem_records: list[dict[str, Any]],
    step_report: str,
    graph_report: str,
    process_report: str,
    insight_report: str,
    execution_summary: str,
    storage_meta: dict[str, Any],
) -> dict[str, Any]:
    """
    组装 Agent3 的结构化复盘结果。

    我们把结构化结果设计成“轻 schema”，而不是很重的嵌套模型，目的是：
    - 先稳定字段语义，方便主流程和前端快速接入；
    - 避免当前阶段为了过度建模引入太多迁移成本；
    - 未来即使接 Pydantic/接口协议，也能从这层平滑演进。
    """
    section_risks = _section_risk_objects(
        task_contract=task_contract,
        graph_scope=graph_scope,
        process_log=process_log,
        review_result=review_result,
        problem_records=problem_records,
    )
    all_risks = _flatten_risk_objects(section_risks)

    # schema_version 是这一步改造的核心。
    # 有了版本号，后续即使我们继续演进字段结构，前端或调用方也能按版本做兼容，
    # 不至于出现“同名字段含义悄悄变化”的问题。
    return {
        "schema_version": "1.0",
        "overview": _review_overview(
            task_contract=task_contract,
            review_result=review_result,
            process_log=process_log,
            problem_records=problem_records,
            storage_meta=storage_meta,
        ),
        "storage_meta": storage_meta,
        "risk_summary": {
            "total_count": len(all_risks),
            "by_level": dict(Counter(risk["risk_level"] for risk in all_risks)),
            "by_owner": dict(Counter(risk["owner"] for risk in all_risks)),
            "top_risks": all_risks[:5],
        },
        "risk_objects": all_risks,
        "problem_summary": _build_problem_summary_structured(problem_records),
        "process_insights": _build_process_insights(process_log),
        "sections": {
            "step_evaluation": {
                "summary_text": step_report,
                "findings": section_risks["step_evaluation"],
            },
            "graph_gap_analysis": {
                "summary_text": graph_report,
                "findings": section_risks["graph_gap_analysis"],
            },
            "process_optimization": {
                "summary_text": process_report,
                "findings": section_risks["process_optimization"],
            },
            "insight_refinement": {
                "summary_text": insight_report,
                "findings": section_risks["insight_refinement"],
            },
            "execution_summary": {
                "summary_text": execution_summary,
                "revision_request_count": len(_as_list(review_result.get("revision_requests"))),
                "scope_violation_count": len(_as_list(review_result.get("scope_violations"))),
                "findings": section_risks["execution_summary"],
            },
        },
        "snapshots": {
            "graph_scope": graph_scope,
            "task_contract": task_contract,
        },
    }


def build_deterministic_review(
    *,
    agent1_output: dict[str, Any],
    agent2_result: dict[str, Any],
    review_result: dict[str, Any],
    process_log: dict[str, Any],
    problem_records: list[dict[str, Any]],
    storage_meta: dict[str, Any],
) -> dict[str, Any]:
    task_contract = agent1_output.get("task_contract", {})
    graph_scope = agent1_output.get("graph_scope", {})

    step_report = StepDecompositionEvaluator()._run(_json_text(task_contract))
    graph_report = GraphGapDetector()._run(_json_text(graph_scope))
    process_report = ProcessOptimizer()._run(_json_text(process_log))
    insight_report = InsightRefiner()._run(
        _json_text(
            {
                "task_contract": task_contract,
                "agent2_result": agent2_result,
                "review_result": review_result,
                "problem_records": problem_records,
            }
        )
    )
    problem_report = _build_problem_summary(problem_records)
    execution_summary = _build_execution_summary(review_result, problem_records)

    sections = {
        "problem_summary": problem_report,
        "step_evaluation": step_report,
        "graph_gap_analysis": graph_report,
        "process_optimization": process_report,
        "insight_refinement": insight_report,
        "execution_summary": execution_summary,
    }
    markdown = "\n\n".join(
        [
            problem_report,
            "## 步骤拆解评价\n\n" + step_report,
            graph_report,
            process_report,
            insight_report,
            "## 执行摘要\n\n" + execution_summary,
        ]
    )
    structured_review = _build_structured_review(
        task_contract=task_contract,
        graph_scope=graph_scope,
        process_log=process_log,
        review_result=review_result,
        problem_records=problem_records,
        step_report=step_report,
        graph_report=graph_report,
        process_report=process_report,
        insight_report=insight_report,
        execution_summary=execution_summary,
        storage_meta=storage_meta,
    )
    return {
        "sections": sections,
        "report_markdown": markdown,
        "structured_review": structured_review,
    }


def _verify_ssl() -> bool:
    value = os.getenv("OPENAI_VERIFY_SSL", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _build_openai_client() -> Any:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    try:
        import httpx
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("OpenAI client dependencies are not installed.") from exc

    timeout_seconds = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
    base_url = os.getenv("OPENAI_API_BASE", "").strip() or None
    user_agent = os.getenv("OPENAI_USER_AGENT", "").strip() or None
    http_client = httpx.Client(verify=_verify_ssl(), timeout=timeout_seconds)
    default_headers = {"User-Agent": user_agent} if user_agent else None
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout_seconds,
        default_headers=default_headers,
        http_client=http_client,
    )


def _enhance_review_with_llm(review_payload: dict[str, Any], deterministic_report: str) -> str:
    client = _build_openai_client()
    model = os.getenv("OPENAI_MODEL_NAME", "deepseek-chat").strip()
    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是 Agent3 复盘精灵。请根据给定的 workflow 上下文和已有草稿，"
                    "输出一份更凝练的 Markdown 复盘报告。不要编造不存在的数据，"
                    "必须保留问题汇总、步骤拆解评价、图谱补缺建议、流程优化建议、经验沉淀、执行摘要六部分。"
                ),
            },
            {
                "role": "user",
                "content": (
                    "以下是本轮真实上下文：\n"
                    + _json_text(review_payload)
                    + "\n\n以下是 deterministic 草稿：\n"
                    + deterministic_report
                ),
            },
        ],
    )
    return str(response.choices[0].message.content or "").strip()


def run_agent3_review(
    *,
    agent1_output: dict[str, Any],
    agent2_result: dict[str, Any],
    review_result: dict[str, Any],
    process_log: dict[str, Any],
    problem_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ProblemStore.init()
    ReviewCandidateStore.init()
    KnowledgeCandidateStore.init()
    # 先取 meta，再取 records，目的是把“本轮读取时存储层是否经历过恢复”一并带给复盘结果。
    # 如果只拿 records，不拿 meta，上层会很难判断空列表背后的真实原因。
    storage_meta = ProblemStore.get_meta()
    records = problem_records if problem_records is not None else ProblemStore.get_all()
    if problem_records is None:
        storage_meta = ProblemStore.get_meta()
    scoped_records = _records_for_run(records, process_log)
    deterministic = build_deterministic_review(
        agent1_output=agent1_output,
        agent2_result=agent2_result,
        review_result=review_result,
        process_log=process_log,
        problem_records=scoped_records,
        storage_meta=storage_meta,
    )
    review_payload = {
        "agent1_output": agent1_output,
        "agent2_result": agent2_result,
        "review_result": review_result,
        "process_log": process_log,
        "problem_records": scoped_records,
    }

    result = {
        "status": "completed",
        "source": "deterministic",
        "problem_record_count": len(scoped_records),
        "storage_meta": storage_meta,
        "sections": deterministic["sections"],
        "structured_review": deterministic["structured_review"],
        "report_markdown": deterministic["report_markdown"],
    }

    # 第一版闭环策略：只记录候选项，不执行候选项。
    # 也就是说，Agent3 到这里为止只做两件事：
    # 1. 把图谱/流程优化建议记录进 review_candidates.json
    # 2. 把经验沉淀记录进 knowledge_candidates.json
    #
    # 所有记录默认都是 pending_review，后续由人工筛选是否值得正式落地。
    overview = deterministic["structured_review"].get("overview", {})
    task_id = str(overview.get("task_id", ""))
    run_id = str(process_log.get("run_id", ""))
    metric_label = (
        agent1_output.get("task_contract", {})
        .get("input_context", {})
        .get("metric_label", "")
    )
    risk_objects = _as_list(deterministic["structured_review"].get("risk_objects"))
    review_candidates = _review_candidates_from_risks(
        run_id=run_id,
        task_id=task_id,
        risk_objects=risk_objects,
    )
    knowledge_candidates = _knowledge_candidates_from_review(
        run_id=run_id,
        task_id=task_id,
        structured_review=deterministic["structured_review"],
        metric_label=str(metric_label or "业务经验"),
    )
    result["recorded_review_candidates"] = ReviewCandidateStore.add_many(review_candidates)
    result["recorded_knowledge_candidates"] = KnowledgeCandidateStore.add_many(knowledge_candidates)

    if os.getenv("AGENT3_ENABLE_LLM", "0").strip().lower() in {"1", "true", "yes", "on"}:
        try:
            llm_report = _enhance_review_with_llm(review_payload, deterministic["report_markdown"])
            if llm_report:
                result["source"] = "deterministic+llm"
                result["report_markdown"] = llm_report
        except Exception as exc:
            result["llm_error"] = str(exc)

    return result


def preview_problem_records() -> str:
    return ProblemCollectorReader()._run("get_all")


if __name__ == "__main__":
    print(
        "Agent3 现在作为 sidecar review 运行，请从 integration.run_workflow() 中调用 "
        "run_agent3_review(...) 获取复盘结果。"
    )
