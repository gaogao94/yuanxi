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

    workflow_status = (
        "completed" if review_result["status"] == "approved" else review_result["status"]
    )
    process_log["status"] = workflow_status
    return {
        "status": workflow_status,
        "agent1_output": agent1_output,
        "agent2_result": agent2_result,
        "review_result": review_result,
        "main_report": review_result["final_user_output"],
        "process_log": process_log,
    }


def _simulate_agent2_result(task_contract: dict[str, Any]) -> dict[str, Any]:
    input_context = task_contract["input_context"]
    completed_todos = [todo["id"] for todo in task_contract["todos"]]
    metric = input_context["metric"]
    time_range = input_context["time_range"]
    clinic_scope = input_context["clinic_scope"]

    return {
        "completed_todos": completed_todos,
        "knowledge_graph_result": {
            "status": "success",
            "scope": task_contract["input_context"]["graph_scope_ref"],
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
        },
    }


def _log_event(
    process_log: dict[str, Any],
    agent: str,
    task: str,
    status: str,
    message: str,
    artifact_ref: str = "",
) -> None:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "task": task,
        "status": status,
        "message": message,
        "artifact_ref": artifact_ref,
    }
    process_log["events"].append(event)
    if status in {"completed", "approved"}:
        process_log["audit_summary"]["completed_tasks"].append(task)
    elif status in {"failed", "blocked", "needs_revision"}:
        process_log["audit_summary"]["failed_tasks"].append(task)
        process_log["audit_summary"]["blocked_reasons"].append(message)


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = "请分析2026年4月上海门店SH001和SH002初诊转化率，并输出Markdown报告"
    print(json.dumps(run_workflow(question), ensure_ascii=False, indent=2))
