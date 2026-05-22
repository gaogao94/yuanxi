import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from io import StringIO
from contextlib import redirect_stdout
from unittest.mock import patch

from agents.agent1 import (
    Agent1,
    Agent1LLMClarifier,
    build_scheduler_agent,
    run_agent1_clarification,
)
from integration import run_workflow
from local_agent1_test import (
    _answer_meta_question,
    _apply_llm_turn_to_context,
    _answer_looks_valid_for_item,
    _ask_clarification,
    _next_clarification_item,
    _normalize_time_range_answer,
    _run_conversation,
)
from tools.nebula_graph_query import NebulaGraphQueryTool


def sample_medgraph() -> dict:
    return {
        "space": "medgraph",
        "version": "3.8.0",
        "schema": {
            "tags": {
                "患者": {"描述": "患者实体"},
                "初诊医生": {"描述": "初诊接诊医生"},
                "责任医生": {"描述": "后续责任医生"},
                "会员": {"描述": "已转化会员"},
            },
            "edges": {
                "首次接诊": {"描述": "患者与初诊医生关系"},
                "指定": {"描述": "患者与责任医生关系"},
                "转化": {"描述": "患者转化为会员关系"},
            },
        },
        "data": {
            "vertices": [
                {"vid": "patient", "tag": "患者"},
                {"vid": "first_visit_doctor", "tag": "初诊医生"},
                {"vid": "responsible_doctor", "tag": "责任医生"},
                {"vid": "member", "tag": "会员"},
            ],
            "edges": [
                {"src": "patient", "edge": "首次接诊", "dst": "first_visit_doctor"},
                {"src": "patient", "edge": "指定", "dst": "responsible_doctor"},
                {"src": "patient", "edge": "转化", "dst": "member"},
            ],
        },
    }


def sample_renewal_graph() -> dict:
    return {
        "space": "card_renew_knowledge",
        "version": "graph_api",
        "schema": {
            "tags": {
                "会员": {},
                "续卡记录": {},
                "门店": {},
            },
            "edges": {
                "续卡": {},
                "到店": {},
            },
        },
        "data": {
            "vertices": [
                {"vid": "member", "tag": "会员"},
                {"vid": "renewal", "tag": "续卡记录"},
                {"vid": "clinic", "tag": "门店"},
            ],
            "edges": [
                {"src": "member", "edge": "续卡", "dst": "renewal"},
                {"src": "member", "edge": "到店", "dst": "clinic"},
            ],
        },
    }


def sample_cashflow_graph() -> dict:
    return {
        "space": "finance_knowledge",
        "version": "graph_api",
        "schema": {
            "tags": {
                "门店": {},
                "现金流": {},
            },
            "edges": {
                "现金流": {},
            },
        },
        "data": {
            "vertices": [
                {"vid": "clinic", "tag": "门店"},
                {"vid": "cash_flow", "tag": "现金流"},
            ],
            "edges": [
                {"src": "clinic", "edge": "现金流", "dst": "cash_flow"},
            ],
        },
    }


class FakeLLMClient:
    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create),
        )

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        content = self.responses.pop(0)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                )
            ]
        )


class FakeConversationLLM:
    def build_clarification_message(self, original_question, context, agent1_result):
        return agent1_result["clarification_result"]["clarification_questions"][0]["question"]

    def interpret_user_reply(self, original_question, context, agent1_result, pending_item, user_reply):
        if pending_item.get("id") == "metric_definition":
            return {
                "assistant_message": "",
                "context_updates": {
                    "metric": "cash_flow",
                    "metric_definition_override": "现金流入、现金流出和净现金流",
                },
                "replacement_question": "",
                "answered_meta_question": False,
            }
        if "怎么还要时间" in user_reply:
            return {
                "assistant_message": "现金流必须有统计周期。请继续补充时间范围。",
                "context_updates": {},
                "replacement_question": "",
                "answered_meta_question": False,
            }
        return {
            "assistant_message": "",
            "context_updates": {"time_range": user_reply},
            "replacement_question": "",
            "answered_meta_question": False,
        }


class FakeBusinessQuestionLLM:
    def build_clarification_message(self, original_question, context, agent1_result):
        return agent1_result["clarification_result"]["clarification_questions"][0]["question"]

    def interpret_user_reply(self, original_question, context, agent1_result, pending_item, user_reply):
        return {
            "assistant_message": "收到，您想查看上海门店的现金流。",
            "context_updates": {
                "metric": "cash_flow",
                "clinic_scope": ["上海门店"],
            },
            "replacement_question": "",
            "answered_meta_question": False,
        }


class FakeNamedClinicLLM:
    def build_clarification_message(self, original_question, context, agent1_result):
        return agent1_result["clarification_result"]["clarification_questions"][0]["question"]

    def interpret_user_reply(self, original_question, context, agent1_result, pending_item, user_reply):
        if pending_item.get("id") == "metric_definition":
            return {
                "assistant_message": "",
                "context_updates": {
                    "metric": "first_visit_conversion_rate",
                    "metric_definition_override": "患者转化为会员的比例",
                },
                "replacement_question": "",
                "answered_meta_question": False,
            }
        if pending_item.get("id") == "time_range":
            return {
                "assistant_message": "",
                "context_updates": {"time_range": user_reply},
                "replacement_question": "",
                "answered_meta_question": False,
            }
        return {
            "assistant_message": "",
            "context_updates": {},
            "replacement_question": "",
            "answered_meta_question": False,
        }


class Agent1WorkflowTest(unittest.TestCase):
    def test_prepare_task_returns_ready_contract_for_scoped_question(self):
        agent = Agent1()
        question = "请分析2026年4月上海门店SH001和SH002初诊转化率，并输出Markdown报告"

        result = agent.prepare_task(question)
        repeated = agent.prepare_task(question)

        self.assertEqual(result["clarification_result"]["status"], "ready")
        self.assertEqual(result["clarification_result"]["confirmed_scope"]["metric"], "first_visit_conversion_rate")
        self.assertEqual(result["clarification_result"]["confirmed_scope"]["time_range"], "2026-04-01 to 2026-04-30")
        self.assertEqual(result["clarification_result"]["expected_result"]["format"], "Markdown")
        self.assertEqual(result["task_contract"]["task_id"], repeated["task_contract"]["task_id"])
        self.assertEqual(result["task_contract"]["input_context"]["clinic_scope"], ["SH001", "SH002"])
        self.assertNotIn("todos", result["task_contract"])
        self.assertTrue(result["graph_scope"]["target_entities"])
        self.assertTrue(result["graph_scope"]["required_relationships"])

        capability_names = {
            capability["name"]
            for capability in result["task_contract"]["required_capabilities"]
            if capability["required"]
        }
        self.assertIn("nebula_graph_query", capability_names)
        self.assertIn("data_fetch", capability_names)
        self.assertIn("sql_check", capability_names)
        self.assertIn("metric_analysis", capability_names)
        self.assertIn("visualization", capability_names)
        self.assertIn("report_generation", capability_names)
        self.assertEqual(
            result["task_contract"]["agent2_planning_policy"]["execution_steps"],
            "agent2_decides",
        )
        self.assertEqual(
            result["task_contract"]["agent2_planning_policy"]["must_use_same_graph_tool"],
            "nebula_graph_query",
        )

    def test_task_contract_uses_capabilities_instead_of_fixed_todos(self):
        agent = Agent1()

        result = agent.prepare_task("请分析2026年4月上海门店SH001初诊转化率，并输出Markdown报告")

        task_contract = result["task_contract"]
        input_context = result["task_contract"]["input_context"]
        self.assertEqual(input_context["metric"], "first_visit_conversion_rate")
        self.assertEqual(input_context["metric_label"], "初诊转化率")
        self.assertNotIn("todos", task_contract)

        capabilities = task_contract["required_capabilities"]
        graph_capability = next(
            capability for capability in capabilities if capability["name"] == "nebula_graph_query"
        )
        data_capability = next(
            capability for capability in capabilities if capability["name"] == "data_fetch"
        )
        self.assertIn("图数据库", graph_capability["purpose"])
        self.assertIn("只读", data_capability["purpose"])
        self.assertTrue(task_contract["agent2_planning_policy"]["agent1_does_not_prescribe_steps"])

        human_text = json.dumps(
            [
                {
                    "purpose": capability["purpose"],
                    "acceptance_criteria": capability["acceptance_criteria"],
                }
                for capability in capabilities
            ],
            ensure_ascii=False,
        )
        for english_phrase in [
            "Resolve graph",
            "Fetch scoped",
            "Generate read-only",
            "Cache intermediate",
            "Analyze metric",
            "Prepare visualization",
            "Assemble Markdown",
        ]:
            self.assertNotIn(english_phrase, human_text)

    def test_prepare_task_marks_vague_question_as_needing_clarification(self):
        agent = Agent1()

        result = agent.prepare_task("帮我看看最近门店情况")

        self.assertEqual(result["clarification_result"]["status"], "needs_clarification")
        self.assertEqual(result["task_contract"], {})
        question_ids = {
            question["id"]
            for question in result["clarification_result"]["clarification_questions"]
        }
        self.assertIn("metric_definition", question_ids)
        self.assertIn("time_range", question_ids)

    def test_prepare_task_does_not_use_fixed_metric_flow_for_non_business_input(self):
        agent = Agent1()

        result = agent.prepare_task(
            "你好",
            user_context={
                "graph_data": {
                    **sample_medgraph(),
                    "space_selection": {
                        "mode": "auto",
                        "selected": "medgraph",
                        "candidates": [{"space": "medgraph", "score": 0, "matched_terms": []}],
                    },
                }
            },
        )

        clarification = result["clarification_result"]
        self.assertEqual(clarification["status"], "needs_clarification")
        self.assertEqual(result["task_contract"], {})
        self.assertEqual(clarification["ambiguities"][0]["field"], "business_question")
        self.assertEqual(
            clarification["clarification_questions"],
            [
                {
                    "id": "business_question",
                    "question": "请描述你要分析的业务问题，例如“帮我看最近30天上海门店转化率”。",
                    "type": "free_text",
                    "options": [],
                    "required": True,
                    "source": "user_input",
                }
            ],
        )

    def test_prepare_task_uses_graph_relationships_for_dynamic_metric_clarification(self):
        agent = Agent1()

        result = agent.prepare_task(
            "帮我看看北京朝阳区望京门店最近续卡情况",
            user_context={"graph_data": sample_renewal_graph()},
        )

        metric_question = next(
            question
            for question in result["clarification_result"]["clarification_questions"]
            if question["id"] == "metric_definition"
        )
        self.assertEqual(metric_question["source"], "nebula_graph_query")
        self.assertIn("续卡数量：统计会员到续卡记录的续卡记录数", metric_question["options"])
        self.assertIn("续卡路径：分析会员到续卡记录的续卡链路", metric_question["options"])
        self.assertNotIn("初诊转化率", metric_question["options"])

    def test_prepare_task_clarifies_address_without_fixed_clinic_choices(self):
        agent = Agent1()

        result = agent.prepare_task(
            "帮我看看北京朝阳区望京门店最近续卡情况",
            user_context={"graph_data": sample_renewal_graph()},
        )

        clinic_question = next(
            question
            for question in result["clarification_result"]["clarification_questions"]
            if question["id"] == "clinic_scope"
        )
        self.assertEqual(clinic_question["type"], "free_text")
        self.assertEqual(clinic_question["source"], "user_input")
        self.assertEqual(clinic_question["options"], [])
        self.assertIn("北京朝阳区望京门店", clinic_question["question"])
        self.assertNotIn("上海门店", clinic_question["question"])

    def test_prepare_task_does_not_treat_generic_recent_clinic_text_as_address(self):
        agent = Agent1()

        result = agent.prepare_task(
            "帮我看看最近门店转化怎么样",
            user_context={"graph_data": sample_medgraph()},
        )

        clinic_question = next(
            question
            for question in result["clarification_result"]["clarification_questions"]
            if question["id"] == "clinic_scope"
        )
        self.assertEqual(clinic_question["type"], "free_text")
        self.assertNotIn("帮我看看", clinic_question["question"])
        self.assertIn("请补充本次分析覆盖的门店", clinic_question["question"])

    def test_prepare_task_uses_named_clinic_from_original_question(self):
        agent = Agent1()

        with patch.dict(os.environ, {"AGENT1_TODAY": "2026-05-20"}):
            result = agent.prepare_task(
                "查看仙乐斯门店的转化率",
                user_context={
                    "graph_data": sample_medgraph(),
                    "metric": "first_visit_conversion_rate",
                    "time_range": "最近35天",
                },
            )

        self.assertEqual(result["clarification_result"]["status"], "ready")
        self.assertEqual(result["task_contract"]["input_context"]["clinic_scope"], ["仙乐斯门店"])
        question_ids = {
            question["id"]
            for question in result["clarification_result"]["clarification_questions"]
        }
        self.assertNotIn("clinic_scope", question_ids)

    def test_prepare_task_uses_possessive_named_clinic_from_original_question(self):
        agent = Agent1()

        with patch.dict(os.environ, {"AGENT1_TODAY": "2026-05-20"}):
            result = agent.prepare_task(
                "查看仙乐斯的转化率",
                user_context={
                    "graph_data": sample_medgraph(),
                    "metric": "first_visit_conversion_rate",
                    "time_range": "最近一个月",
                },
            )

        self.assertEqual(result["clarification_result"]["status"], "ready")
        self.assertEqual(result["task_contract"]["input_context"]["clinic_scope"], ["仙乐斯"])
        self.assertNotIn(
            "clinic_scope",
            {
                question["id"]
                for question in result["clarification_result"]["clarification_questions"]
            },
        )

    def test_prepare_task_cleans_possessive_clinic_scope_from_context(self):
        agent = Agent1()

        with patch.dict(os.environ, {"AGENT1_TODAY": "2026-05-20"}):
            result = agent.prepare_task(
                "查看仙乐斯的转化率",
                user_context={
                    "graph_data": sample_medgraph(),
                    "metric": "first_visit_conversion_rate",
                    "time_range": "最近一个月",
                    "clinic_scope": ["仙乐斯的"],
                },
            )

        self.assertEqual(result["clarification_result"]["status"], "ready")
        self.assertEqual(result["task_contract"]["input_context"]["clinic_scope"], ["仙乐斯"])
        self.assertEqual(
            result["task_contract"]["clarified_task"]["understood_intent"],
            "分析 2026-04-20 to 2026-05-20、仙乐斯的初诊转化率表现并形成可交付报告。",
        )

    def test_prepare_task_captures_low_metric_root_cause_intent_for_agent2(self):
        agent = Agent1()

        with patch.dict(os.environ, {"AGENT1_TODAY": "2026-05-20"}):
            result = agent.prepare_task(
                "转化率很低，为什么",
                user_context={
                    "graph_data": sample_medgraph(),
                    "metric": "first_visit_conversion_rate",
                    "time_range": "最近一个月",
                    "clinic_scope": ["仙乐斯门店"],
                },
            )

        input_context = result["task_contract"]["input_context"]
        self.assertEqual(result["clarification_result"]["status"], "ready")
        self.assertEqual(input_context["analysis_intent"], "root_cause_analysis")
        self.assertEqual(input_context["problem_statement"], "转化率很低，为什么")
        self.assertEqual(input_context["problem_signal"]["type"], "low_metric")
        self.assertTrue(input_context["problem_signal"]["requires_baseline_validation"])
        self.assertIn("验证初诊转化率是否偏低", result["task_contract"]["goal"])
        self.assertNotIn("todos", result["task_contract"])
        capability_names = {
            capability["name"]
            for capability in result["task_contract"]["required_capabilities"]
            if capability["required"]
        }
        self.assertIn("root_cause_analysis", capability_names)
        self.assertNotIn("metric_analysis", capability_names)
        root_cause_capability = next(
            capability
            for capability in result["task_contract"]["required_capabilities"]
            if capability["name"] == "root_cause_analysis"
        )
        root_cause_text = json.dumps(root_cause_capability, ensure_ascii=False)
        self.assertIn("必须先验证 problem_signal 是否成立", root_cause_text)
        self.assertIn("门店、医生、渠道", root_cause_text)
        self.assertIn("每条原因必须包含数据证据或图谱证据", root_cause_text)
        self.assertIn("问题是否成立", result["task_contract"]["final_expected_output"]["sections"])
        self.assertIn("证据链", result["task_contract"]["final_expected_output"]["sections"])

    def test_prepare_task_detects_cash_flow_as_business_metric(self):
        agent = Agent1()

        result = agent.prepare_task(
            "帮我查看上海门店的现金流",
            user_context={"graph_data": sample_medgraph()},
        )

        clarification = result["clarification_result"]
        self.assertEqual(clarification["confirmed_scope"]["metric"], "cash_flow")
        self.assertEqual(clarification["status"], "needs_clarification")
        question_ids = {
            question["id"]
            for question in clarification["clarification_questions"]
        }
        self.assertEqual(question_ids, {"time_range"})

    def test_prepare_task_normalizes_recent_month_for_agent2_contract(self):
        agent = Agent1()

        with patch.dict(os.environ, {"AGENT1_TODAY": "2026-05-20"}):
            result = agent.prepare_task(
                "查看仙乐斯门店的转化率",
                user_context={
                    "graph_data": sample_medgraph(),
                    "metric": "first_visit_conversion_rate",
                    "time_range": "最近一个月",
                    "clinic_scope": ["仙乐斯"],
                },
            )

        self.assertEqual(result["clarification_result"]["status"], "ready")
        self.assertEqual(
            result["task_contract"]["input_context"]["time_range"],
            "2026-04-20 to 2026-05-20",
        )

    def test_local_time_range_answer_normalizes_recent_month(self):
        with patch.dict(os.environ, {"AGENT1_TODAY": "2026-05-20"}):
            normalized = _normalize_time_range_answer("最近一个月")

        self.assertEqual(normalized, "2026-04-20 to 2026-05-20")

    def test_prepare_task_blocks_when_strict_graph_match_has_no_metric_relationship(self):
        agent = Agent1()

        result = agent.prepare_task(
            "帮我查看上海门店的现金流",
            user_context={"graph_data": sample_medgraph(), "strict_graph_match": True},
        )

        self.assertEqual(result["clarification_result"]["status"], "blocked")
        self.assertEqual(result["task_contract"], {})
        self.assertIn(
            "未命中",
            result["clarification_result"]["blocking_reason"]["error"],
        )

    def test_should_query_graph_treats_cash_flow_as_business_question(self):
        agent = Agent1()

        self.assertTrue(agent.should_query_graph("查看门店的现金流"))

    def test_local_agent1_chat_selects_one_clarification_at_a_time(self):
        agent = Agent1()

        result = agent.prepare_task(
            "帮我看看最近门店转化怎么样",
            user_context={"graph_data": sample_medgraph()},
        )

        self.assertGreater(
            len(result["clarification_result"]["clarification_questions"]),
            1,
        )
        next_item = _next_clarification_item(result)

        self.assertEqual(next_item["id"], "metric_definition")
        self.assertNotIn("time_range", next_item["id"])

    def test_local_agent1_chat_answers_graph_count_meta_question(self):
        context = {
            "graph_data": {
                "space_selection": {
                    "candidates": [
                        {"space": "medgraph"},
                        {"space": "card_renew_knowledge"},
                    ]
                }
            }
        }

        output = StringIO()
        with redirect_stdout(output):
            handled = _answer_meta_question("现在有几个图谱？", context)

        self.assertTrue(handled)
        self.assertIn("2 个", output.getvalue())
        self.assertNotIn("metric", context)

    def test_agent1_llm_clarifier_builds_question_from_model_json(self):
        client = FakeLLMClient(
            [
                json.dumps(
                    {
                        "assistant_message": "我先按现金流来理解。请补充分析时间范围，比如最近30天或2026年4月。",
                        "context_updates": {},
                        "replacement_question": "",
                        "answered_meta_question": False,
                    },
                    ensure_ascii=False,
                )
            ]
        )
        clarifier = Agent1LLMClarifier(client=client, model="fake-model")
        agent = Agent1()
        result = agent.prepare_task(
            "帮我查看上海门店的现金流",
            user_context={"graph_data": sample_medgraph()},
        )

        message = clarifier.build_clarification_message(
            original_question="帮我查看上海门店的现金流",
            context={"graph_data": sample_medgraph()},
            agent1_result=result,
        )

        self.assertIn("现金流", message)
        self.assertIn("最近30天", message)
        self.assertEqual(client.calls[0]["model"], "fake-model")

    def test_agent1_llm_clarifier_interprets_reply_as_json_updates(self):
        client = FakeLLMClient(
            [
                json.dumps(
                    {
                        "assistant_message": "",
                        "context_updates": {
                            "time_range": "最近30天",
                            "clinic_scope": ["上海门店"],
                        },
                        "replacement_question": "",
                        "answered_meta_question": False,
                    },
                    ensure_ascii=False,
                )
            ]
        )
        clarifier = Agent1LLMClarifier(client=client, model="fake-model")
        agent = Agent1()
        result = agent.prepare_task(
            "帮我查看上海门店的现金流",
            user_context={"graph_data": sample_medgraph()},
        )
        pending_item = _next_clarification_item(result)

        turn = clarifier.interpret_user_reply(
            original_question="帮我查看上海门店的现金流",
            context={"graph_data": sample_medgraph()},
            agent1_result=result,
            pending_item=pending_item,
            user_reply="最近30天，上海门店",
        )

        self.assertEqual(turn["context_updates"]["time_range"], "最近30天")
        self.assertEqual(turn["context_updates"]["clinic_scope"], ["上海门店"])

    def test_agent1_llm_clarifier_supports_configurable_user_agent_header(self):
        with patch.dict(os.environ, {"OPENAI_USER_AGENT": "ApipostRuntime/1.1.0"}):
            headers = Agent1LLMClarifier._default_headers()

        self.assertEqual(headers, {"User-Agent": "ApipostRuntime/1.1.0"})

    def test_agent1_llm_clarifier_parses_json_after_qwen_thinking_block(self):
        clarifier = Agent1LLMClarifier(client=FakeLLMClient([]), model="fake-model")

        parsed = clarifier._parse_json_object(
            '<think>{"assistant_message":"wrong"}</think>'
            '{"assistant_message":"你好","context_updates":{},'
            '"replacement_question":"","answered_meta_question":false}'
        )

        self.assertEqual(parsed["assistant_message"], "你好")

    def test_agent1_llm_clarifier_retries_without_response_format_on_empty_content(self):
        client = FakeLLMClient(
            [
                "",
                json.dumps(
                    {
                        "assistant_message": "请补充时间范围。",
                        "context_updates": {},
                        "replacement_question": "",
                        "answered_meta_question": False,
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        clarifier = Agent1LLMClarifier(client=client, model="fake-model")

        with patch.dict(os.environ, {"OPENAI_RESPONSE_FORMAT_JSON": "1"}):
            response = clarifier._chat_json([{"role": "user", "content": "test"}])

        self.assertEqual(response["assistant_message"], "请补充时间范围。")
        self.assertEqual(len(client.calls), 2)
        self.assertIn("response_format", client.calls[0])
        self.assertNotIn("response_format", client.calls[1])

    def test_local_agent1_chat_applies_llm_business_question_without_metric_pollution(self):
        context = {}

        replacement_question = _apply_llm_turn_to_context(
            context,
            {
                "assistant_message": "",
                "context_updates": {
                    "business_question": "帮我查看上海门店的现金流",
                },
                "replacement_question": "帮我查看上海门店的现金流",
                "answered_meta_question": False,
            },
        )

        self.assertEqual(replacement_question, "帮我查看上海门店的现金流")
        self.assertEqual(context, {})

    def test_local_agent1_chat_applies_llm_scope_updates(self):
        context = {}

        with patch.dict(os.environ, {"AGENT1_TODAY": "2026-05-20"}):
            replacement_question = _apply_llm_turn_to_context(
                context,
                {
                    "assistant_message": "",
                    "context_updates": {
                        "metric": "现金流",
                        "time_range": "最近30天",
                        "clinic_scope": "上海门店",
                    },
                    "replacement_question": "",
                    "answered_meta_question": False,
                },
            )

        self.assertIsNone(replacement_question)
        self.assertEqual(context["metric"], "cash_flow")
        self.assertEqual(context["time_range"], "2026-04-20 to 2026-05-20")
        self.assertEqual(context["clinic_scope"], ["Shanghai clinics"])

    def test_local_agent1_chat_does_not_treat_followup_question_as_time_range(self):
        item = {"id": "time_range"}

        self.assertFalse(_answer_looks_valid_for_item(item, "你没查到信息，怎么还要时间？"))
        self.assertTrue(_answer_looks_valid_for_item(item, "最近30天"))

    def test_local_agent1_chat_keeps_clarifying_when_reply_is_a_followup_question(self):
        with patch.dict(os.environ, {"AGENT1_TODAY": "2026-05-20"}), patch(
            "local_agent1_test._build_llm_clarifier",
            return_value=FakeConversationLLM(),
        ), patch(
            "local_agent1_test._load_graph",
            return_value=sample_cashflow_graph(),
        ), patch("builtins.input", side_effect=["现金流", "你没查到信息，怎么还要时间？", "最近30天"]):
            result = _run_conversation("上海门店的现金流")

        input_context = result["task_contract"]["input_context"]
        self.assertEqual(result["clarification_result"]["status"], "ready")
        self.assertEqual(input_context["time_range"], "2026-04-20 to 2026-05-20")
        self.assertNotEqual(input_context["time_range"], "你没查到信息，怎么还要时间？")

    def test_local_agent1_chat_blocks_when_real_graph_has_no_metric_match(self):
        with patch("local_agent1_test._build_llm_clarifier", return_value=FakeConversationLLM()), patch(
            "local_agent1_test._load_graph",
            return_value=sample_medgraph(),
        ):
            result = _run_conversation("上海门店的现金流")

        self.assertEqual(result["clarification_result"]["status"], "blocked")
        self.assertEqual(result["task_contract"], {})

    def test_local_agent1_chat_uses_business_question_reply_for_graph_query(self):
        with patch("local_agent1_test._build_llm_clarifier", return_value=FakeBusinessQuestionLLM()), patch(
            "local_agent1_test._load_graph",
            return_value=sample_medgraph(),
        ) as load_graph, patch("builtins.input", side_effect=["上海门店的现金流"]):
            result = _run_conversation("你好")

        load_graph.assert_called_once_with("上海门店的现金流")
        self.assertEqual(result["clarification_result"]["status"], "blocked")
        self.assertEqual(result["task_contract"], {})

    def test_local_agent1_chat_does_not_reask_named_clinic_from_original_question(self):
        with patch.dict(os.environ, {"AGENT1_TODAY": "2026-05-20"}), patch(
            "local_agent1_test._build_llm_clarifier",
            return_value=FakeNamedClinicLLM(),
        ), patch(
            "local_agent1_test._load_graph",
            return_value=sample_medgraph(),
        ), patch("builtins.input", side_effect=["转化率", "最近35天的"]):
            result = _run_conversation("查看仙乐斯门店的转化率")

        input_context = result["task_contract"]["input_context"]
        self.assertEqual(result["clarification_result"]["status"], "ready")
        self.assertEqual(input_context["time_range"], "2026-04-15 to 2026-05-20")
        self.assertEqual(input_context["clinic_scope"], ["仙乐斯门店"])

    def test_local_agent1_chat_does_not_reask_possessive_named_clinic(self):
        with patch.dict(os.environ, {"AGENT1_TODAY": "2026-05-20"}), patch(
            "local_agent1_test._build_llm_clarifier",
            return_value=FakeNamedClinicLLM(),
        ), patch(
            "local_agent1_test._load_graph",
            return_value=sample_medgraph(),
        ), patch("builtins.input", side_effect=["转化率", "最近一个月"]):
            result = _run_conversation("查看仙乐斯的转化率")

        input_context = result["task_contract"]["input_context"]
        self.assertEqual(result["clarification_result"]["status"], "ready")
        self.assertEqual(input_context["time_range"], "2026-04-20 to 2026-05-20")
        self.assertEqual(input_context["clinic_scope"], ["仙乐斯"])

    def test_local_agent1_chat_suppresses_stale_llm_prompt_after_context_update(self):
        class StalePromptLLM(FakeNamedClinicLLM):
            def interpret_user_reply(self, original_question, context, agent1_result, pending_item, user_reply):
                turn = super().interpret_user_reply(
                    original_question,
                    context,
                    agent1_result,
                    pending_item,
                    user_reply,
                )
                if pending_item.get("id") == "time_range":
                    turn["assistant_message"] = "请问还要分析哪个门店？"
                return turn

        with patch.dict(os.environ, {"AGENT1_TODAY": "2026-05-20"}), patch(
            "local_agent1_test._build_llm_clarifier",
            return_value=StalePromptLLM(),
        ), patch(
            "local_agent1_test._load_graph",
            return_value=sample_medgraph(),
        ), patch("builtins.input", side_effect=["转化率", "最近一个月"]):
            output = StringIO()
            with redirect_stdout(output):
                result = _run_conversation("查看仙乐斯的转化率")

        self.assertEqual(result["clarification_result"]["status"], "ready")
        self.assertNotIn("请问还要分析哪个门店", output.getvalue())

    def test_local_agent1_chat_captures_root_cause_intent_and_valid_clinic_reply(self):
        with patch.dict(os.environ, {"AGENT1_TODAY": "2026-05-20"}), patch(
            "local_agent1_test._build_llm_clarifier",
            return_value=FakeNamedClinicLLM(),
        ), patch(
            "local_agent1_test._load_graph",
            return_value=sample_medgraph(),
        ), patch("builtins.input", side_effect=["转化率", "一个月", "仙乐斯"]):
            result = _run_conversation("转化率很低，为什么")

        input_context = result["task_contract"]["input_context"]
        self.assertEqual(result["clarification_result"]["status"], "ready")
        self.assertEqual(input_context["analysis_intent"], "root_cause_analysis")
        self.assertEqual(input_context["problem_signal"]["type"], "low_metric")
        self.assertEqual(input_context["time_range"], "2026-04-20 to 2026-05-20")
        self.assertEqual(input_context["clinic_scope"], ["仙乐斯"])

    def test_llm_clarification_stably_lists_graph_options_and_maps_number(self):
        class FailingOptionLLM:
            def build_clarification_message(self, *_args, **_kwargs):
                raise AssertionError("option turns should use structured graph options, not LLM wording")

        item = {
            "id": "metric_definition",
            "question": "图谱中匹配到业务关系，本次要按哪个口径继续分析？",
            "type": "single_select",
            "options": [
                "转化率：患者转化为会员的比例",
                "转化人数：完成转化的患者数量",
                "转化路径：患者到会员的转化链路",
                "转化关联对象：患者、会员、初诊医生、责任医生之间的关系",
            ],
            "source": "nebula_graph_query",
        }

        output = StringIO()
        with redirect_stdout(output), patch("builtins.input", return_value="1"):
            answer = _ask_clarification(
                item,
                FailingOptionLLM(),
                question="仙乐斯门店的转化率",
                context={},
                result={"clarification_result": {"clarification_questions": [item]}},
            )

        self.assertEqual(answer, "转化率：患者转化为会员的比例")
        printed = output.getvalue()
        self.assertIn("图谱中匹配到业务关系，本次要按哪个口径继续分析？", printed)
        self.assertIn("我从图谱里看到这些可能口径", printed)
        self.assertIn("1. 转化率：患者转化为会员的比例", printed)
        self.assertIn("2. 转化人数：完成转化的患者数量", printed)
        self.assertIn("3. 转化路径：患者到会员的转化链路", printed)
        self.assertIn("4. 转化关联对象：患者、会员、初诊医生、责任医生之间的关系", printed)

    def test_run_agent1_clarification_skips_graph_query_for_non_business_input(self):
        class FailingGraphTool:
            def _run(self, _query):
                raise AssertionError("graph query should be skipped for non-business input")

        result = run_agent1_clarification("你好", graph_tool=FailingGraphTool())

        self.assertEqual(result["clarification_result"]["status"], "needs_clarification")
        self.assertEqual(result["task_contract"], {})
        self.assertEqual(
            result["clarification_result"]["clarification_questions"][0]["id"],
            "business_question",
        )

    def test_nebula_graph_query_reads_medgraph_json_from_env(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as file:
            json.dump(sample_medgraph(), file, ensure_ascii=False)
            medgraph_path = file.name

        try:
            with patch.dict(
                os.environ,
                {
                    "MEDGRAPH_JSON_PATH": medgraph_path,
                    "GRAPH_API_KEY": "",
                    "GRAPH_API_STRICT": "",
                },
            ):
                tool = NebulaGraphQueryTool()

                result = json.loads(tool._run("转化率", output_format="json"))

            self.assertEqual(tool.name, "nebula_graph_query")
            self.assertEqual(result["space"], "medgraph")
            self.assertIn(
                {"src": "patient", "edge": "转化", "dst": "member"},
                result["data"]["edges"],
            )
        finally:
            os.unlink(medgraph_path)

    def test_nebula_graph_query_defaults_to_text_for_agent2(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as file:
            json.dump(sample_medgraph(), file, ensure_ascii=False)
            medgraph_path = file.name

        try:
            with patch.dict(
                os.environ,
                {
                    "MEDGRAPH_JSON_PATH": medgraph_path,
                    "GRAPH_API_KEY": "",
                    "GRAPH_API_STRICT": "",
                },
            ):
                result = NebulaGraphQueryTool()._run("转化率")

            self.assertIn("NebulaGraph 查询结果", result)
            self.assertIn("转化", result)
        finally:
            os.unlink(medgraph_path)

    def test_nebula_graph_query_uses_graph_api_before_local_json(self):
        captured_requests = []

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _traceback):
                return False

            def read(self):
                return json.dumps(sample_medgraph(), ensure_ascii=False).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured_requests.append((request, timeout))
            return FakeResponse()

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as file:
            json.dump({"space": "local_should_not_win", "schema": {}, "data": {}}, file)
            medgraph_path = file.name

        try:
            with patch.dict(
                os.environ,
                {
                    "GRAPH_API_BASE_URL": "https://graph.example.test",
                    "GRAPH_API_KEY": "secret-token",
                    "GRAPH_API_SPACE": "medgraph",
                    "GRAPH_API_STRICT": "",
                    "MEDGRAPH_JSON_PATH": medgraph_path,
                },
            ), patch("urllib.request.urlopen", fake_urlopen):
                result = json.loads(NebulaGraphQueryTool()._run("转化率", output_format="json"))

            request, timeout = captured_requests[0]
            self.assertEqual(result["space"], "medgraph")
            self.assertEqual(request.full_url, "https://graph.example.test/medgraph/query")
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(request.headers["Authorization"], "secret-token")
            self.assertEqual(
                json.loads(request.data.decode("utf-8"))["statement"],
                "SHOW EDGES",
            )
            self.assertGreater(timeout, 0)
        finally:
            os.unlink(medgraph_path)

    def test_nebula_graph_query_falls_back_to_local_json_when_api_raw_error(self):
        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _traceback):
                return False

            def read(self):
                return json.dumps(
                    {
                        "raw": "(root@nebula) [(none)]> USE not_a_space; SHOW TAGS;\n[ERROR (-1005)]: SpaceNotFound",
                        "rows": [],
                        "columns": [],
                    },
                    ensure_ascii=False,
                ).encode("utf-8")

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as file:
            json.dump(sample_medgraph(), file, ensure_ascii=False)
            medgraph_path = file.name

        try:
            with patch.dict(
                os.environ,
                {
                    "GRAPH_API_BASE_URL": "https://graph.example.test",
                    "GRAPH_API_KEY": "secret-token",
                    "GRAPH_API_SPACE": "not_a_space",
                    "GRAPH_API_STRICT": "",
                    "MEDGRAPH_JSON_PATH": medgraph_path,
                },
            ), patch("urllib.request.urlopen", return_value=FakeResponse()):
                result = json.loads(NebulaGraphQueryTool()._run("SHOW TAGS", output_format="json"))

            self.assertEqual(result["space"], "medgraph")
            self.assertIn(
                {"src": "patient", "edge": "转化", "dst": "member"},
                result["data"]["edges"],
            )
        finally:
            os.unlink(medgraph_path)

    def test_nebula_graph_query_strict_mode_returns_api_error_without_fallback(self):
        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _traceback):
                return False

            def read(self):
                return json.dumps(
                    {
                        "raw": "(root@nebula) [(none)]> USE not_a_space; SHOW TAGS;\n[ERROR (-1005)]: SpaceNotFound",
                        "rows": [],
                        "columns": [],
                    },
                    ensure_ascii=False,
                ).encode("utf-8")

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as file:
            json.dump(sample_medgraph(), file, ensure_ascii=False)
            medgraph_path = file.name

        try:
            with patch.dict(
                os.environ,
                {
                    "GRAPH_API_BASE_URL": "https://graph.example.test",
                    "GRAPH_API_KEY": "secret-token",
                    "GRAPH_API_SPACE": "not_a_space",
                    "GRAPH_API_STRICT": "1",
                    "MEDGRAPH_JSON_PATH": medgraph_path,
                },
            ), patch("urllib.request.urlopen", return_value=FakeResponse()):
                result = json.loads(NebulaGraphQueryTool()._run("SHOW TAGS", output_format="json"))

            self.assertEqual(result["status"], "error")
            self.assertEqual(result["source"], "graph_api")
            self.assertEqual(result["data"]["edges"], [])
            self.assertIn("SpaceNotFound", result["error"])
        finally:
            os.unlink(medgraph_path)

    def test_nebula_graph_query_strict_mode_requires_api_key(self):
        with patch.dict(os.environ, {"GRAPH_API_KEY": "", "GRAPH_API_STRICT": "1"}):
            result = json.loads(NebulaGraphQueryTool()._run("转化率", output_format="json"))

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["source"], "graph_api")
        self.assertIn("GRAPH_API_KEY", result["error"])

    def test_nebula_graph_query_strict_mode_auto_selects_graph_space(self):
        captured_urls = []

        class FakeResponse:
            status = 200

            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _traceback):
                return False

            def read(self):
                return json.dumps(self.body, ensure_ascii=False).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured_urls.append(request.full_url)
            if request.full_url == "https://graph.example.test/spaces":
                return FakeResponse(
                    {
                        "rows": [
                            {"Name": "card_renew_knowledge"},
                            {"Name": "medgraph"},
                        ]
                    }
                )
            if request.full_url == "https://graph.example.test/card_renew_knowledge/tags":
                return FakeResponse({"rows": [{"Name": "会员"}, {"Name": "续卡"}]})
            if request.full_url == "https://graph.example.test/medgraph/tags":
                return FakeResponse({"rows": [{"Name": "患者"}, {"Name": "会员"}]})
            if request.full_url == "https://graph.example.test/card_renew_knowledge/query":
                return FakeResponse({"rows": [{"Name": "续卡"}], "columns": ["Name"]})
            if request.full_url == "https://graph.example.test/medgraph/query":
                return FakeResponse({"rows": [{"Name": "转化"}], "columns": ["Name"]})
            if request.full_url.startswith("https://graph.example.test/card_renew_knowledge/edges?"):
                return FakeResponse({"rows": []})
            raise AssertionError(f"Unexpected URL: {request.full_url}")

        with patch.dict(
            os.environ,
            {
                "GRAPH_API_KEY": "secret-token",
                "GRAPH_API_STRICT": "1",
                "GRAPH_API_BASE_URL": "https://graph.example.test",
                "GRAPH_API_SPACE": "",
                "NEBULA_SPACE": "",
            },
        ), patch("urllib.request.urlopen", fake_urlopen):
            result = json.loads(NebulaGraphQueryTool()._run("帮我看续卡情况", output_format="json"))

        self.assertEqual(result["space"], "card_renew_knowledge")
        self.assertEqual(result["source"], "graph_api")
        self.assertEqual(result["space_selection"]["mode"], "auto")
        self.assertIn("https://graph.example.test/spaces", captured_urls)
        self.assertIn("https://graph.example.test/card_renew_knowledge/query", captured_urls)

    def test_prepare_task_uses_graph_data_for_conversion_clarification(self):
        agent = Agent1()

        result = agent.prepare_task(
            "帮我看看最近门店转化怎么样",
            user_context={"graph_data": sample_medgraph()},
        )

        self.assertEqual(result["clarification_result"]["status"], "needs_clarification")
        metric_question = next(
            question
            for question in result["clarification_result"]["clarification_questions"]
            if question["id"] == "metric_definition"
        )
        self.assertEqual(metric_question["source"], "nebula_graph_query")
        self.assertIn("转化路径：患者到会员的转化链路", metric_question["options"])
        self.assertIn(
            {"from": "患者", "relation": "转化", "to": "会员", "reason": "来自 nebula_graph_query 的图谱关系。"},
            result["graph_scope"]["required_relationships"],
        )

    def test_prepare_task_accepts_clarified_custom_metric_context(self):
        agent = Agent1()

        result = agent.prepare_task(
            "帮我看看最近门店转化怎么样",
            user_context={
                "graph_data": sample_medgraph(),
                "metric": "conversion_count",
                "metric_definition_override": "完成转化的患者数量",
                "time_range": "last_30_days",
                "clinic_scope": ["Shanghai clinics"],
            },
        )

        self.assertEqual(result["clarification_result"]["status"], "ready")
        self.assertEqual(
            result["task_contract"]["input_context"]["metric"],
            "conversion_count",
        )
        self.assertEqual(
            result["task_contract"]["input_context"]["metric_definition"],
            "完成转化的患者数量",
        )

    def test_build_scheduler_agent_uses_only_graph_and_problem_tools(self):
        scheduler = build_scheduler_agent(verbose=False)

        tool_names = {tool.name for tool in scheduler.tools}

        self.assertEqual(tool_names, {"nebula_graph_query", "problem_reporter"})
        self.assertNotIn("knowledge_base_query", tool_names)

    def test_run_agent1_clarification_queries_graph_tool_before_planning(self):
        class FakeGraphTool:
            def __init__(self):
                self.queries = []

            def _run(self, query, **_kwargs):
                self.queries.append(query)
                return json.dumps(sample_medgraph(), ensure_ascii=False)

        graph_tool = FakeGraphTool()

        result = run_agent1_clarification(
            "帮我看看最近门店转化怎么样",
            graph_tool=graph_tool,
        )

        self.assertEqual(graph_tool.queries, ["帮我看看最近门店转化怎么样"])
        self.assertEqual(result["clarification_result"]["status"], "needs_clarification")
        self.assertEqual(
            result["clarification_result"]["clarification_questions"][0]["source"],
            "nebula_graph_query",
        )

    def test_run_agent1_clarification_queries_effective_business_question_from_context(self):
        class FakeGraphTool:
            def __init__(self):
                self.queries = []

            def _run(self, query, **_kwargs):
                self.queries.append(query)
                return json.dumps(sample_medgraph(), ensure_ascii=False)

        graph_tool = FakeGraphTool()

        result = run_agent1_clarification(
            "你好",
            user_context={"business_question": "帮我查看上海门店的现金流"},
            graph_tool=graph_tool,
        )

        self.assertEqual(graph_tool.queries, ["帮我查看上海门店的现金流"])
        self.assertEqual(
            result["clarification_result"]["confirmed_scope"]["metric"],
            "cash_flow",
        )

    def test_run_agent1_clarification_blocks_on_strict_graph_api_error(self):
        class FakeGraphTool:
            def _run(self, _query, **_kwargs):
                return json.dumps(
                    {
                        "status": "error",
                        "source": "graph_api",
                        "error": "HTTP Error 403: Forbidden",
                        "schema": {"tags": {}, "edges": {}},
                        "data": {"vertices": [], "edges": []},
                    },
                    ensure_ascii=False,
                )

        result = run_agent1_clarification(
            "帮我看看最近门店转化怎么样",
            graph_tool=FakeGraphTool(),
        )

        self.assertEqual(result["clarification_result"]["status"], "blocked")
        self.assertEqual(result["task_contract"], {})
        self.assertEqual(
            result["clarification_result"]["blocking_reason"]["source"],
            "nebula_graph_query",
        )
        self.assertIn("403", result["clarification_result"]["blocking_reason"]["error"])

    def test_review_agent2_result_detects_missing_capabilities_and_privacy_leak(self):
        agent = Agent1()
        agent1_output = agent.prepare_task(
            "请分析2026年4月上海门店SH001初诊转化率，并输出Markdown报告"
        )

        review = agent.review_agent2_result(
            agent1_output,
            {
                "completed_capabilities": ["nebula_graph_query"],
                "final_report": "患者手机号 13812345678 出现在报告中。",
                "analysis_result": {"status": "success"},
            },
        )

        review_result = review["review_result"]
        self.assertEqual(review_result["status"], "blocked")
        self.assertTrue(review_result["missing_capabilities"])
        self.assertEqual(review_result["privacy_check"], "failed")
        self.assertTrue(review_result["revision_requests"])

    def test_review_agent2_result_does_not_count_cache_as_data_fetch(self):
        agent = Agent1()
        agent1_output = agent.prepare_task(
            "请分析2026年4月上海门店SH001初诊转化率，并输出Markdown报告"
        )

        review = agent.review_agent2_result(
            agent1_output,
            {
                "knowledge_graph_result": {"status": "success"},
                "cache_result": {"status": "hit"},
                "sql_check_result": {"status": "success"},
                "analysis_result": {"status": "success"},
                "visualization_result": {"status": "success"},
                "final_report": "本次初诊转化率分析已完成，包含图谱和数据证据。",
            },
        )

        review_result = review["review_result"]
        self.assertEqual(review_result["status"], "needs_revision")
        self.assertIn("data_fetch", review_result["missing_capabilities"])

    def test_run_workflow_passes_only_task_contract_to_agent2(self):
        captured_inputs = []

        def agent2_runner(task_contract):
            captured_inputs.append(task_contract)
            return {
                "completed_capabilities": [
                    capability["name"]
                    for capability in task_contract["required_capabilities"]
                    if capability["required"]
                ],
                "data_fetch_result": {"status": "success"},
                "sql_check_result": {"status": "success"},
                "knowledge_graph_result": {"status": "success"},
                "analysis_result": {"status": "success"},
                "visualization_result": {"status": "success"},
                "final_report": "本次初诊转化率分析已完成，未包含患者敏感信息。",
            }

        result = run_workflow(
            "请分析2026年4月上海门店SH001和SH002初诊转化率，并输出Markdown报告",
            agent2_runner=agent2_runner,
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["review_result"]["status"], "approved")
        self.assertEqual(len(captured_inputs), 1)
        self.assertIn("task_id", captured_inputs[0])
        self.assertNotIn("original_question", captured_inputs[0])

    def test_run_workflow_does_not_call_agent2_when_clarification_is_needed(self):
        def agent2_runner(_task_contract):
            raise AssertionError("agent2_runner should not be called")

        result = run_workflow("帮我看看最近门店情况", agent2_runner=agent2_runner)

        self.assertEqual(result["status"], "needs_clarification")
        self.assertNotIn("agent2_result", result)

    def test_run_workflow_can_pass_graph_data_to_agent1_clarification(self):
        def agent2_runner(_task_contract):
            raise AssertionError("agent2_runner should not be called")

        result = run_workflow(
            "帮我看看最近门店转化怎么样",
            agent2_runner=agent2_runner,
            graph_data=sample_medgraph(),
        )

        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(
            result["clarification_questions"][0]["source"],
            "nebula_graph_query",
        )

if __name__ == "__main__":
    unittest.main()
