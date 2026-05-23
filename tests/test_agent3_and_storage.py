import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.agent1 import Agent1, build_clarification_task, build_scheduler_agent
from agents.agent3 import run_agent3_review
from integration import run_workflow
from tools.knowledge_candidate_store import KnowledgeCandidateStore
from tools.problem_reporter import ProblemReporterTool
from tools.problem_store import ProblemStore
from tools.review_candidate_store import ReviewCandidateStore


class Agent3AndStorageTest(unittest.TestCase):
    """
    这组测试承接本轮新增的旁路复盘、存储稳健性和文档策略验证。

    现在统一放回 tests/ 目录，避免 scripts/ 同时承担“调试脚本”和“正式测试”两种职责。
    """

    def test_run_agent3_review_uses_real_workflow_inputs(self):
        agent = Agent1()
        original_problem_path = ProblemStore._file_path
        original_review_candidate_path = ReviewCandidateStore._file_path
        original_knowledge_candidate_path = KnowledgeCandidateStore._file_path
        with tempfile.TemporaryDirectory() as temp_dir:
            ProblemStore.init(os.path.join(temp_dir, "problem_reports.json"))
            ReviewCandidateStore.init(os.path.join(temp_dir, "review_candidates.json"))
            KnowledgeCandidateStore.init(os.path.join(temp_dir, "knowledge_candidates.json"))
            agent1_output = {
            "task_contract": {
                "input_context": {
                    "metric": "first_visit_conversion_rate",
                    "metric_label": "初诊转化率",
                    "time_range": "2026-04-01 to 2026-04-30",
                    "clinic_scope": ["上海徐汇店"],
                    "analysis_intent": "metric_analysis",
                    "problem_statement": "",
                    "problem_signal": {},
                },
                "required_capabilities": [
                        {"name": "nebula_graph_query", "required": True},
                        {"name": "data_fetch", "required": True},
                        {"name": "sql_check", "required": True},
                        {"name": "metric_analysis", "required": True},
                        {"name": "report_generation", "required": True},
                    ],
                    "expected_deliverable": {"format": "Markdown"},
                }
            }
            agent2_result = {
                "completed_capabilities": [
                    capability["name"]
                    for capability in agent1_output["task_contract"]["required_capabilities"]
                    if capability["required"]
                ],
                "knowledge_graph_result": {"status": "success"},
                "data_fetch_result": {
                    "status": "success",
                    "scope": {"clinic_scope": ["SH001", "SH002"]},
                },
                "analysis_result": {
                    "status": "success",
                    "metric_summary": {"metric": "first_visit_conversion_rate"},
                },
                "visualization_result": {"status": "success"},
                "final_report": "主报告已生成。",
            }
            review_result = agent.review_agent2_result(agent1_output, agent2_result)["review_result"]
            process_log = {
                "run_id": "run_test",
                "status": "completed",
                "events": [
                    {
                        "timestamp": "2026-05-22T00:00:00+00:00",
                        "agent": "Workflow",
                        "task": "receive_user_question",
                        "status": "completed",
                        "message": "Workflow received user question.",
                        "artifact_ref": "",
                    }
                ],
                "timeline_summary": [],
                "audit_summary": {
                    "completed_tasks": ["receive_user_question"],
                    "failed_tasks": [],
                    "blocked_reasons": [],
                    "optimization_points": [],
                },
            }
            problem_records = [
                {
                    "id": "prob-1",
                    "timestamp": "2026-05-22T00:00:01+00:00",
                    "agent": "Agent2",
                    "stage": "sql_check",
                    "problem": "缺少过滤条件",
                    "solution": "补充 is_first_visit=1",
                    "severity": "medium",
                }
            ]

            result = run_agent3_review(
                agent1_output=agent1_output,
                agent2_result=agent2_result,
                review_result=review_result,
                process_log=process_log,
                problem_records=problem_records,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["source"], "deterministic")
            self.assertEqual(result["problem_record_count"], 1)
            self.assertIn("初诊转化率", result["report_markdown"])
            self.assertIn("缺少过滤条件", result["report_markdown"])
            self.assertIn("task_", result["sections"]["step_evaluation"])
            self.assertEqual(result["structured_review"]["problem_summary"]["total_count"], 1)
            self.assertEqual(
                result["structured_review"]["overview"]["review_status"],
                review_result["status"],
            )
            self.assertEqual(result["structured_review"]["schema_version"], "1.0")
            self.assertIn("sections", result["structured_review"])
            self.assertGreater(result["structured_review"]["risk_summary"]["total_count"], 0)
            first_risk = result["structured_review"]["risk_objects"][0]
            self.assertIn("category", first_risk)
            self.assertIn("risk_level", first_risk)
            self.assertIn("owner", first_risk)
            self.assertIn("action", first_risk)
            self.assertIn("evidence", first_risk)
            self.assertEqual(
                result["structured_review"]["sections"]["step_evaluation"]["findings"][0]["section"],
                "step_evaluation",
            )
            self.assertGreaterEqual(len(result["recorded_review_candidates"]), 1)
            self.assertGreaterEqual(len(result["recorded_knowledge_candidates"]), 1)
            self.assertEqual(result["recorded_review_candidates"][0]["review_status"], "pending_review")
            self.assertEqual(
                result["recorded_knowledge_candidates"][0]["review_status"],
                "pending_review",
            )
            self.assertTrue(os.path.exists(os.path.join(temp_dir, "review_candidates.json")))
            self.assertTrue(os.path.exists(os.path.join(temp_dir, "knowledge_candidates.json")))
        ProblemStore.init(str(original_problem_path))
        ReviewCandidateStore.init(str(original_review_candidate_path))
        KnowledgeCandidateStore.init(str(original_knowledge_candidate_path))

    def test_run_workflow_keeps_main_flow_when_agent3_sidecar_fails(self):
        def agent2_runner(task_contract):
            return {
                "completed_capabilities": [
                    capability["name"]
                    for capability in task_contract["required_capabilities"]
                    if capability["required"]
                ],
                "data_fetch_result": {"status": "success", "scope": {"clinic_scope": ["上海徐汇店"]}},
                "sql_check_result": {"status": "success"},
                "knowledge_graph_result": {"status": "success"},
                "analysis_result": {
                    "status": "success",
                    "metric_summary": {"metric": "first_visit_conversion_rate"},
                },
                "visualization_result": {"status": "success"},
                "final_report": "主流程正常完成。",
            }

        with patch("integration.run_agent3_review", side_effect=RuntimeError("agent3 boom")):
            result = run_workflow(
                "请分析上海徐汇店初诊转化率，并输出Markdown报告",
                agent2_runner=agent2_runner,
                graph_data={},
                user_context={
                    "metric": "first_visit_conversion_rate",
                    "time_range": "2026-04-01 to 2026-04-30",
                    "clinic_scope": ["上海徐汇店"],
                },
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["review_result"]["status"], "approved")
        self.assertEqual(result["agent3_review"]["status"], "failed")
        self.assertEqual(result["agent3_review"]["error"], "agent3 boom")
        agent3_events = [
            event
            for event in result["process_log"]["events"]
            if event["agent"] == "Agent3" and event["task"] == "sidecar_review"
        ]
        self.assertEqual(len(agent3_events), 1)
        self.assertEqual(agent3_events[0]["status"], "failed")
        self.assertEqual(agent3_events[0]["event_type"], "sidecar")
        self.assertEqual(agent3_events[0]["stage_category"], "retrospective")

    def test_problem_store_recovers_from_corrupted_json_and_keeps_backup_meta(self):
        original_path = ProblemStore._file_path
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = os.path.join(temp_dir, "problem_reports.json")
            with open(store_path, "w", encoding="utf-8") as f:
                f.write("{this is not valid json")

            ProblemStore.init(store_path)
            records = ProblemStore.get_all()
            meta = ProblemStore.get_meta()

            self.assertEqual(records, [])
            self.assertIn(
                meta["storage_status"],
                {"recovered_from_corruption", "corruption_backup_failed", "healthy"},
            )
            self.assertTrue(os.path.exists(store_path))
            self.assertTrue(meta["last_error"])
            if meta["last_backup_path"]:
                self.assertTrue(os.path.exists(meta["last_backup_path"]))

            added = ProblemStore.add(
                {
                    "agent": "Agent2",
                    "stage": "sql_check",
                    "problem": "恢复后补写测试",
                    "solution": "验证存储仍可写",
                    "severity": "low",
                }
            )
            self.assertEqual(added["agent"], "Agent2")
            self.assertEqual(ProblemStore.count(), 1)
        ProblemStore.init(str(original_path))

    def test_run_workflow_populates_process_log_event_taxonomy(self):
        def agent2_runner(task_contract):
            return {
                "completed_capabilities": [
                    capability["name"]
                    for capability in task_contract["required_capabilities"]
                    if capability["required"]
                ],
                "data_fetch_result": {
                    "status": "success",
                    "scope": {"clinic_scope": task_contract["input_context"]["clinic_scope"]},
                },
                "sql_check_result": {"status": "success"},
                "knowledge_graph_result": {"status": "success"},
                "analysis_result": {
                    "status": "success",
                    "metric_summary": {"metric": task_contract["input_context"]["metric"]},
                },
                "visualization_result": {"status": "success"},
                "final_report": "主流程正常完成。",
            }

        result = run_workflow(
            "请分析上海徐汇店和上海新江湾店初诊转化率，并输出Markdown报告",
            agent2_runner=agent2_runner,
            graph_data={},
            user_context={
                "metric": "first_visit_conversion_rate",
                "time_range": "2026-04-01 to 2026-04-30",
                "clinic_scope": ["上海徐汇店", "上海新江湾店"],
            },
        )

        process_log = result["process_log"]
        audit_summary = process_log["audit_summary"]
        self.assertEqual(process_log["events"][0]["event_type"], "lifecycle")
        self.assertEqual(process_log["events"][1]["event_type"], "planning")
        self.assertEqual(process_log["events"][2]["event_type"], "execution")
        self.assertEqual(process_log["events"][3]["event_type"], "review")
        self.assertEqual(process_log["events"][4]["event_type"], "sidecar")
        self.assertEqual(audit_summary["event_type_counts"]["lifecycle"], 1)
        self.assertEqual(audit_summary["event_type_counts"]["planning"], 1)
        self.assertEqual(audit_summary["event_type_counts"]["execution"], 1)
        self.assertEqual(audit_summary["event_type_counts"]["review"], 1)
        self.assertEqual(audit_summary["event_type_counts"]["sidecar"], 1)
        self.assertGreaterEqual(audit_summary["status_counts"]["completed"], 4)

    def test_problem_reporter_normalizes_stage_severity_and_text(self):
        original_path = ProblemStore._file_path
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = os.path.join(temp_dir, "problem_reports.json")
            ProblemStore.init(store_path)

            tool = ProblemReporterTool()
            message = tool._run(
                agent="agent2",
                stage="sql_debug",
                problem="字段 clinic_name 不存在",
                solution="改用 store_name",
                severity="critical",
            )

            records = ProblemStore.get_all()
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record["agent"], "Agent2")
            self.assertEqual(record["stage"], "sql_check")
            self.assertEqual(record["severity"], "high")
            self.assertTrue(record["problem"].startswith("问题: "))
            self.assertTrue(record["solution"].startswith("处理: "))
            self.assertEqual(record["metadata"]["raw_stage"], "sql_debug")
            self.assertEqual(record["metadata"]["raw_severity"], "critical")
            self.assertIn("阶段: sql_check", message)
            self.assertIn("严重程度: high", message)

        ProblemStore.init(str(original_path))

    def test_problem_reporter_todo_is_documented_in_docs_instead_of_agent_prompts(self):
        scheduler = build_scheduler_agent(verbose=False)
        clarification_task = build_clarification_task("帮我看最近门店转化", scheduler)

        self.assertNotIn("problem 统一写成“问题:", scheduler.backstory)
        self.assertNotIn("severity 只允许 high/medium/low", scheduler.backstory)
        self.assertNotIn("problem 写成“问题: ...; 上下文: ...”", clarification_task.description)
        self.assertNotIn("stage 只能填 clarification/knowledge/planning/review", clarification_task.description)

        project_root = Path(__file__).resolve().parents[1]
        doc_path = project_root / "docs" / "tasks" / "agent1-agent2-problem-reporting-todo.md"
        self.assertTrue(doc_path.exists())
        doc_content = doc_path.read_text(encoding="utf-8")
        self.assertIn("Agent1 问题上报提示词补齐", doc_content)
        self.assertIn("Agent2 问题上报提示词补齐", doc_content)
        self.assertIn("当前策略是：", doc_content)
        self.assertIn("暂时不在代码里写死上报格式约束", doc_content)


if __name__ == "__main__":
    unittest.main()
