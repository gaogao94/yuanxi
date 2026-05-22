"""
Deterministic workflow entrypoint.

The coordinator controls order only:
1. Agent1 clarifies and creates a task contract.
2. Agent2 receives only the task contract.
3. Agent1 reviews Agent2 output before the main report is returned.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, Callable

from agents.agent1 import Agent1
from agents.agent3 import run_agent3_review


Agent2Runner = Callable[[dict[str, Any]], dict[str, Any]]


def run_workflow(
    user_question: str,
    agent2_runner: Agent2Runner | None = None,
    agent1: Agent1 | None = None,
    graph_data: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    coordinator_agent1 = agent1 or Agent1()
    process_log = _new_process_log()

    _log_event(
        process_log,
        agent="Workflow",
        task="receive_user_question",
        status="completed",
        message="Workflow received user question.",
    )

    user_context = {"graph_data": graph_data} if graph_data is not None else None
    agent1_output = coordinator_agent1.prepare_task(user_question, user_context)
    _log_event(
        process_log,
        agent="Agent1",
        task="clarify_and_plan",
        status="completed",
        message=f"Agent1 status: {agent1_output['clarification_result']['status']}.",
        artifact_ref="agent1_output",
    )

    if agent1_output["clarification_result"]["status"] != "ready":
        process_log["status"] = "partial_completed"
        return {
            "status": "needs_clarification",
            "agent1_output": agent1_output,
            "clarification_questions": agent1_output["clarification_result"][
                "clarification_questions"
            ],
            "process_log": process_log,
        }

    task_contract = agent1_output["task_contract"]
    runner = agent2_runner or _simulate_agent2_result
    agent2_result = runner(task_contract)
    _log_event(
        process_log,
        agent="Agent2",
        task="execute_task_contract",
        status="completed",
        message="Agent2 returned structured execution result.",
        artifact_ref="agent2_result",
    )

    review = coordinator_agent1.review_agent2_result(agent1_output, agent2_result)
    review_result = review["review_result"]
    _log_event(
        process_log,
        agent="Agent1",
        task="review_agent2_result",
        status=review_result["status"],
        message=f"Agent1 review status: {review_result['status']}.",
        artifact_ref="review_result",
    )

    agent3_review = _run_agent3_sidecar(
        agent1_output=agent1_output,
        agent2_result=agent2_result,
        review_result=review_result,
        process_log=process_log,
    )

    workflow_status = (
        "completed" if review_result["status"] == "approved" else review_result["status"]
    )
    process_log["status"] = workflow_status
    return {
        "status": workflow_status,
        "agent1_output": agent1_output,
        "agent2_result": agent2_result,
        "review_result": review_result,
        "agent3_review": agent3_review,
        "main_report": review_result["final_user_output"],
        "process_log": process_log,
    }


def _simulate_agent2_result(task_contract: dict[str, Any]) -> dict[str, Any]:
    input_context = task_contract["input_context"]
    completed_capabilities = [
        capability["name"]
        for capability in task_contract.get("required_capabilities", [])
        if capability.get("required")
    ]
    metric = input_context["metric"]
    time_range = input_context["time_range"]
    clinic_scope = input_context["clinic_scope"]

    return {
        "completed_capabilities": completed_capabilities,
        "knowledge_graph_result": {
            "status": "success",
            "scope": task_contract.get("graph_query_boundary", {}),
        },
        "data_fetch_result": {
            "status": "success",
            "source": "mock_data",
            "scope": {
                "time_range": time_range,
                "clinic_scope": clinic_scope,
                "population": input_context["population"],
                "filters": [metric, time_range, ",".join(clinic_scope)],
            },
            "data_profile": {
                "row_count": 1280,
                "fields": ["clinic_id", "patient_id_masked", "doctor_id", "is_arrived"],
                "missing_values": [],
                "outliers": [],
                "reasonableness_check": "Mock data is structurally valid for first-version workflow verification.",
            },
        },
        "analysis_result": {
            "status": "success",
            "metric_summary": {
                "metric": metric,
                "definition": input_context["metric_definition"],
                "value": "45.2%",
                "comparison": {"mom": "N/A", "yoy": "+3.1pp", "baseline": "mock baseline"},
            },
            "dimension_breakdowns": [
                {
                    "dimension": "clinic",
                    "findings": [
                        {
                            "segment": clinic,
                            "value": "45.2%",
                            "sample_size": 640,
                            "change": "mock stable",
                            "is_anomaly": False,
                        }
                        for clinic in clinic_scope
                    ],
                }
            ],
            "trend_findings": [
                {
                    "period": time_range,
                    "trend": "mock upward trend",
                    "evidence": "Mock baseline comparison.",
                }
            ],
            "cause_hypotheses": [
                {
                    "cause": "Doctor follow-up timeliness may affect conversion.",
                    "confidence": "low",
                    "evidence": ["Mock clinic and doctor breakdowns"],
                    "counter_evidence": ["No real database connected in first version."],
                    "recommended_action": "Validate with real appointment and visit data before business action.",
                }
            ],
        },
        "visualization_result": {
            "status": "success",
            "charts": [
                {
                    "chart_id": "chart_1",
                    "type": "bar",
                    "title": f"{time_range} {metric} by clinic",
                    "business_question": "Which clinics differ on the target metric?",
                    "data_source": "mock_data",
                    "file_path": "",
                    "key_message": "Mock chart spec generated; no real chart file in first version.",
                }
            ],
        },
        "final_report": (
            f"## 问题定义\n\n"
            f"本次分析目标是评估 {time_range}、{', '.join(clinic_scope)} 的 {metric}。\n\n"
            f"## 核心指标结果\n\n"
            f"- 模拟结果：45.2%。\n"
            f"- 同比：+3.1pp。\n\n"
            f"## 限制与风险\n\n"
            f"- 当前为第一版模拟数据输出，正式结论需要接入真实数据库后复核。\n"
        ),
    }


def _new_process_log() -> dict[str, Any]:
    # process_log 在这个项目里承担两层职责：
    # 1. 给人看：让我们知道这轮 workflow 大致经历了什么；
    # 2. 给程序算：后续 Agent3、前端或统计任务要据此计算返工率、阻塞率、失败分布。
    #
    # 因此这里不再只保存“松散的自然语言事件”，而是预留出更稳定的聚合槽位：
    # - event_type_counts：统计生命周期/执行/审核/旁路等事件类别；
    # - status_counts：统计 completed/failed/blocked 等状态分布；
    # - optimization_points：后续可以由 Agent3 或其他审计器反向写入。
    return {
        "run_id": datetime.now(timezone.utc).strftime("run_%Y%m%d%H%M%S%f"),
        "status": "running",
        "events": [],
        "timeline_summary": [],
        "audit_summary": {
            "completed_tasks": [],
            "failed_tasks": [],
            "blocked_reasons": [],
            "optimization_points": [],
            "event_type_counts": {},
            "status_counts": {},
        },
    }


def _run_agent3_sidecar(
    *,
    agent1_output: dict[str, Any],
    agent2_result: dict[str, Any],
    review_result: dict[str, Any],
    process_log: dict[str, Any],
) -> dict[str, Any]:
    try:
        agent3_review = run_agent3_review(
            agent1_output=agent1_output,
            agent2_result=agent2_result,
            review_result=review_result,
            process_log=process_log,
        )
        _log_event(
            process_log,
            agent="Agent3",
            task="sidecar_review",
            status="completed" if agent3_review.get("status") == "completed" else "failed",
            message=(
                "Agent3 sidecar review completed."
                if agent3_review.get("status") == "completed"
                else f"Agent3 sidecar review returned status: {agent3_review.get('status', 'unknown')}."
            ),
            artifact_ref="agent3_review",
        )
        return agent3_review
    except Exception as exc:
        _log_event(
            process_log,
            agent="Agent3",
            task="sidecar_review",
            status="failed",
            message=f"Agent3 sidecar review failed: {exc}",
            artifact_ref="agent3_review",
        )
        return {
            "status": "failed",
            "source": "sidecar",
            "error": str(exc),
        }


def _log_event(
    process_log: dict[str, Any],
    agent: str,
    task: str,
    status: str,
    message: str,
    artifact_ref: str = "",
) -> None:
    # 事件分类是这一轮改造的重点之一。
    # 以前只有 task 名称，后续如果想统计“主流程里到底多少是审核失败、多少是 sidecar 失败”
    # 就只能做字符串匹配，既脆弱又难维护。
    #
    # 现在我们在写事件时同步补两个稳定维度：
    # - event_type：从生命周期角度看，这是什么事件（lifecycle/execution/review/sidecar）
    # - stage_category：从业务阶段角度看，这一步更接近 planning/execution/review/retrospective
    #
    # 这两个字段都用规则映射生成，避免调用方每次手写不一致。
    event_type = _event_type(task)
    stage_category = _stage_category(agent, task)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "task": task,
        "status": status,
        "event_type": event_type,
        "stage_category": stage_category,
        "message": message,
        "artifact_ref": artifact_ref,
    }
    process_log["events"].append(event)
    _increment_counter(process_log["audit_summary"]["event_type_counts"], event_type)
    _increment_counter(process_log["audit_summary"]["status_counts"], status)
    if status in {"completed", "approved"}:
        process_log["audit_summary"]["completed_tasks"].append(task)
    elif status in {"failed", "blocked", "needs_revision"}:
        process_log["audit_summary"]["failed_tasks"].append(task)
        process_log["audit_summary"]["blocked_reasons"].append(message)


def _increment_counter(bucket: dict[str, int], key: str) -> None:
    """
    递增 process_log 里的计数字段。

    单独抽成函数有两个好处：
    1. 避免每个地方都写 if/else 初始化逻辑；
    2. 后续如果要统一做 key 归一化或埋点扩展，只改这一处即可。
    """
    bucket[key] = int(bucket.get(key, 0)) + 1


def _event_type(task: str) -> str:
    """
    根据 task 名称推断事件类型。

    这里故意用“小而稳定”的 taxonomy，而不是把 task 原样当分类：
    - lifecycle：工作流生命周期事件，如接收请求
    - planning：需求澄清与任务规划
    - execution：Agent2 执行任务
    - review：Agent1 审核 Agent2 结果
    - sidecar：Agent3 旁路复盘
    - unknown：兜底，保证未来新增 task 时不会因为漏分类而报错
    """
    mapping = {
        "receive_user_question": "lifecycle",
        "clarify_and_plan": "planning",
        "execute_task_contract": "execution",
        "review_agent2_result": "review",
        "sidecar_review": "sidecar",
    }
    return mapping.get(task, "unknown")


def _stage_category(agent: str, task: str) -> str:
    """
    输出更贴近业务阶段的分类。

    和 event_type 的区别是：
    - event_type 偏“系统行为分类”；
    - stage_category 偏“业务过程阶段”。
    两者保留并行是为了给后续分析留出足够空间。
    """
    if agent == "Workflow":
        return "intake"
    if task == "clarify_and_plan":
        return "planning"
    if task == "execute_task_contract":
        return "execution"
    if task == "review_agent2_result":
        return "review"
    if task == "sidecar_review":
        return "retrospective"
    return "unknown"


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = "请分析2026年4月上海门店SH001和SH002初诊转化率，并输出Markdown报告"
    print(json.dumps(run_workflow(question), ensure_ascii=False, indent=2))
