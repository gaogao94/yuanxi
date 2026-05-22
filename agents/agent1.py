"""
Agent1: requirement clarification, graph scoping, task planning, and review.

The LLM layer handles natural clarification turns. The deterministic core keeps
the structured contract stable for Agent2 and validates the final scope.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any


PHONE_PATTERN = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class Agent1LLMError(RuntimeError):
    """Raised when the Agent1 LLM clarification layer cannot run safely."""


class Agent1LLMClarifier:
    """LLM wrapper for natural Agent1 clarification turns.

    The deterministic Agent1 core remains the contract authority. This class
    asks an OpenAI-compatible chat model to phrase one natural clarification at
    a time and to parse user replies into the small context fields that the core
    already validates.
    """

    def __init__(
        self,
        client: Any | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        user_agent: str | None = None,
        timeout: float | None = None,
        temperature: float = 0.2,
    ) -> None:
        self.model = model or os.getenv("OPENAI_MODEL_NAME") or "deepseek-chat"
        self.temperature = temperature
        if client is not None:
            self.client = client
            return

        resolved_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()
        if not resolved_key:
            raise Agent1LLMError("OPENAI_API_KEY is not configured.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise Agent1LLMError("openai package is not installed.") from exc

        resolved_base_url = base_url or os.getenv("OPENAI_API_BASE", "").strip() or None
        resolved_timeout = timeout or float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
        self.client = OpenAI(
            api_key=resolved_key,
            base_url=resolved_base_url,
            default_headers=self._default_headers(user_agent),
            timeout=resolved_timeout,
        )

    @classmethod
    def from_env(cls) -> "Agent1LLMClarifier":
        return cls()

    @staticmethod
    def _default_headers(user_agent: str | None = None) -> dict[str, str] | None:
        resolved_user_agent = user_agent or os.getenv("OPENAI_USER_AGENT", "").strip()
        if not resolved_user_agent:
            return None
        return {"User-Agent": resolved_user_agent}

    def build_clarification_message(
        self,
        original_question: str,
        context: dict[str, Any],
        agent1_result: dict[str, Any],
    ) -> str:
        payload = self._base_payload(
            "ask_next_clarification",
            original_question,
            context,
            agent1_result,
        )
        response = self._chat_json(
            [
                {"role": "system", "content": self._system_prompt()},
                {
                    "role": "user",
                    "content": (
                        "/no_think\n请基于下面 JSON 生成 Agent1 下一句自然澄清问题。"
                        "只问一个最关键问题，不要直接输出任务合同。\n"
                        + json.dumps(payload, ensure_ascii=False)
                    ),
                },
            ]
        )
        message = str(response.get("assistant_message", "")).strip()
        if message:
            return message

        questions = agent1_result.get("clarification_result", {}).get(
            "clarification_questions",
            [],
        )
        if questions:
            return str(questions[0].get("question", "")).strip()
        return "请继续补充本次业务分析需求。"

    def interpret_user_reply(
        self,
        original_question: str,
        context: dict[str, Any],
        agent1_result: dict[str, Any],
        pending_item: dict[str, Any] | None,
        user_reply: str,
    ) -> dict[str, Any]:
        payload = self._base_payload(
            "interpret_user_reply",
            original_question,
            context,
            agent1_result,
        )
        payload["pending_item"] = pending_item or {}
        payload["user_reply"] = user_reply
        response = self._chat_json(
            [
                {"role": "system", "content": self._system_prompt()},
                {
                    "role": "user",
                    "content": (
                        "/no_think\n请把用户最新回复解析成 Agent1 可用的结构化上下文。"
                        "如果用户是在问图谱数量、space 列表等元问题，只回答元问题，"
                        "不要把它写进 metric/time_range/clinic_scope。\n"
                        + json.dumps(payload, ensure_ascii=False)
                    ),
                },
            ]
        )
        return self._normalize_turn(response)

    def _chat_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "2048")),
        }
        first_error: Exception | None = None
        if os.getenv("OPENAI_RESPONSE_FORMAT_JSON", "1").strip().lower() not in {
            "0",
            "false",
            "no",
            "off",
        }:
            try:
                response = self.client.chat.completions.create(
                    **kwargs,
                    response_format={"type": "json_object"},
                )
                return self._response_json(response)
            except Exception as exc:
                first_error = exc

        try:
            response = self.client.chat.completions.create(**kwargs)
            return self._response_json(response)
        except Exception as second_error:
            raise Agent1LLMError(str(second_error)) from first_error

    def _response_json(self, response: Any) -> dict[str, Any]:
        content = response.choices[0].message.content
        parsed = self._parse_json_object(str(content or ""))
        if not isinstance(parsed, dict):
            raise Agent1LLMError("LLM did not return a JSON object.")
        return parsed

    def _parse_json_object(self, content: str) -> dict[str, Any]:
        text = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        if not text:
            raise Agent1LLMError("LLM returned empty content.")
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        decoder = json.JSONDecoder()
        for start in [index for index, char in enumerate(text) if char == "{"][::-1]:
            try:
                parsed, _end = decoder.raw_decode(text[start:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        raise Agent1LLMError("LLM response JSON is invalid.")

    def _normalize_turn(self, response: dict[str, Any]) -> dict[str, Any]:
        updates = response.get("context_updates")
        if not isinstance(updates, dict):
            updates = {}
        allowed_updates = {
            key: value
            for key, value in updates.items()
            if key
            in {
                "business_question",
                "metric",
                "metric_definition_override",
                "time_range",
                "clinic_scope",
                "output_format",
                "population",
            }
            and value not in ("", None, [], {})
        }
        return {
            "assistant_message": str(response.get("assistant_message") or "").strip(),
            "context_updates": allowed_updates,
            "replacement_question": str(response.get("replacement_question") or "").strip(),
            "answered_meta_question": bool(response.get("answered_meta_question", False)),
        }

    def _base_payload(
        self,
        mode: str,
        original_question: str,
        context: dict[str, Any],
        agent1_result: dict[str, Any],
    ) -> dict[str, Any]:
        clarification = agent1_result.get("clarification_result", {})
        return {
            "mode": mode,
            "original_question": original_question,
            "current_context": self._context_for_prompt(context),
            "graph_summary": self._graph_summary(context.get("graph_data")),
            "agent1_status": clarification.get("status", ""),
            "understood_intent": clarification.get("understood_intent", ""),
            "confirmed_scope": clarification.get("confirmed_scope", {}),
            "clarification_questions": clarification.get("clarification_questions", []),
            "known_metric_ids": {
                "first_visit_conversion_rate": "初诊转化率",
                "revisit_rate": "复诊率",
                "revenue": "营收",
                "appointment_count": "预约量",
                "cash_flow": "现金流",
            },
        }

    def _context_for_prompt(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in context.items()
            if key != "graph_data" and value not in ("", None, [], {})
        }

    def _graph_summary(self, graph_data: Any) -> dict[str, Any]:
        graph = Agent1()._coerce_graph_data(graph_data)
        if not graph:
            return {}
        schema = graph.get("schema") or {}
        data = graph.get("data") or {}
        space_selection = graph.get("space_selection") or {}
        candidates = []
        for candidate in space_selection.get("candidates") or []:
            if isinstance(candidate, dict):
                candidates.append(
                    {
                        "space": candidate.get("space", ""),
                        "score": candidate.get("score", 0),
                        "matched_terms": candidate.get("matched_terms", []),
                    }
                )

        return {
            "status": graph.get("status", "ok"),
            "source": graph.get("source", ""),
            "space": graph.get("space", ""),
            "candidate_spaces": candidates[:8],
            "tag_names": list((schema.get("tags") or {}).keys())[:40],
            "edge_names": list((schema.get("edges") or {}).keys())[:40],
            "matched_edges": [
                {
                    "src": edge.get("src", ""),
                    "edge": edge.get("edge", ""),
                    "dst": edge.get("dst", ""),
                }
                for edge in data.get("edges", [])[:20]
                if isinstance(edge, dict)
            ],
        }

    def _system_prompt(self) -> str:
        return (
            "你是 Agent1，负责把用户的自然语言业务问题澄清成 Agent2 可执行的任务。"
            "你可以阅读 current_context、graph_summary 和 deterministic Agent1 的结果，"
            "但不能直接执行 SQL、不能调用 Agent2、不能调用 Agent3、不能编造图谱没有返回的信息。"
            "每次只问一个问题，优先使用图谱实体、关系和用户原话生成自然澄清。"
            "如果用户已经补充了时间、门店、指标等信息，写入 context_updates。"
            "已知指标 ID 只能使用 known_metric_ids 中的英文 ID；现金流必须写为 cash_flow。"
            "如果用户提出新的完整业务问题，把它放入 replacement_question 或 business_question。"
            "如果用户问“有几个图谱/哪些 space”等元问题，只回答元问题，answered_meta_question=true，"
            "context_updates 留空。"
            "不要输出 <think>、推理过程、Markdown 代码块或任何 JSON 之外的文本。"
            "必须只返回 JSON 对象："
            "{\"assistant_message\":\"...\",\"context_updates\":{},"
            "\"replacement_question\":\"\",\"answered_meta_question\":false}。"
        )


@dataclass
class Agent1:
    metric_catalog: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.metric_catalog:
            return
        self.metric_catalog = {
            "first_visit_conversion_rate": {
                "keywords": ["初诊转化", "初诊", "转化率", "到诊率"],
                "label": "初诊转化率",
                "definition": "初诊转化人数 / 初诊线索或预约人数；第一版需由 Agent2 取数后复核口径。",
                "must_include": ["指标口径", "总体结果", "门店维度拆解", "趋势或同比环比", "建议动作"],
            },
            "revisit_rate": {
                "keywords": ["复诊率", "复诊"],
                "label": "复诊率",
                "definition": "复诊人数 / 可复诊人群人数；第一版需由 Agent2 取数后复核口径。",
                "must_include": ["指标口径", "总体结果", "人群维度拆解", "趋势变化", "建议动作"],
            },
            "revenue": {
                "keywords": ["营收", "收入", "销售额", "业绩"],
                "label": "营收",
                "definition": "已入账业务收入；第一版需由 Agent2 校验账单范围和退款处理口径。",
                "must_include": ["指标口径", "收入结果", "门店维度拆解", "趋势变化", "建议动作"],
            },
            "appointment_count": {
                "keywords": ["预约量", "预约数", "预约"],
                "label": "预约量",
                "definition": "符合任务范围的预约记录数；第一版需由 Agent2 校验取消和重复预约口径。",
                "must_include": ["指标口径", "预约总量", "门店维度拆解", "趋势变化", "建议动作"],
            },
            "cash_flow": {
                "keywords": ["现金流", "现金", "流水", "收款", "回款", "支出", "净现金流"],
                "label": "现金流",
                "definition": "现金流入、现金流出和净现金流；第一版需由 Agent2 校验收款、退款、支出和入账时间口径。",
                "must_include": ["指标口径", "现金流入", "现金流出", "净现金流", "门店维度拆解", "风险提示"],
            },
        }

    def prepare_task(
        self,
        original_question: str,
        user_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = user_context or {}
        graph_insights = self._extract_graph_insights(
            original_question,
            context.get("graph_data"),
        )
        if graph_insights.get("error"):
            clarification_result = self._graph_query_blocked_result(
                original_question,
                graph_insights,
            )
            graph_scope = self._build_graph_scope(clarification_result, graph_insights)
            return {
                "clarification_result": clarification_result,
                "graph_scope": graph_scope,
                "task_contract": {},
            }

        clarification_result = self._clarify_requirement(
            original_question,
            context,
            graph_insights,
        )
        if self._strict_graph_match_failed(original_question, context, graph_insights):
            clarification_result = self._graph_match_blocked_result(
                original_question,
                context,
            )
        graph_scope = self._build_graph_scope(clarification_result, graph_insights)

        if clarification_result["status"] != "ready":
            return {
                "clarification_result": clarification_result,
                "graph_scope": graph_scope,
                "task_contract": {},
            }

        task_contract = self._build_task_contract(clarification_result, graph_scope)
        return {
            "clarification_result": clarification_result,
            "graph_scope": graph_scope,
            "task_contract": task_contract,
        }

    def should_query_graph(
        self,
        original_question: str,
        user_context: dict[str, Any] | None = None,
    ) -> bool:
        context = user_context or {}
        effective_question = str(context.get("business_question") or original_question)
        metric = context.get("metric") or self._detect_metric(effective_question)
        time_range = self.normalize_time_range(
            context.get("time_range") or self._detect_time_range(effective_question)
        )
        clinic_scope = context.get("clinic_scope") or self._detect_clinic_scope(effective_question)
        return self._has_business_analysis_intent(
            effective_question,
            metric,
            time_range,
            clinic_scope,
            {},
        )

    def review_agent2_result(
        self,
        agent1_output: dict[str, Any],
        agent2_result: dict[str, Any],
    ) -> dict[str, Any]:
        task_contract = agent1_output.get("task_contract") or {}
        required_capabilities = [
            str(capability.get("name"))
            for capability in task_contract.get("required_capabilities", [])
            if capability.get("required") and capability.get("name")
        ]
        completed_capabilities = self._completed_capabilities(
            agent2_result,
            required_capabilities,
        )
        missing_capabilities = [
            capability
            for capability in required_capabilities
            if capability not in completed_capabilities
        ]

        scope_violations = self._scope_violations(task_contract, agent2_result)
        metric_consistency = self._metric_consistency(task_contract, agent2_result)
        evidence_check = self._evidence_check(agent2_result)
        privacy_check = self._privacy_check(agent2_result)

        revision_requests = self._revision_requests(
            missing_capabilities,
            scope_violations,
            metric_consistency,
            evidence_check,
            privacy_check,
        )

        if privacy_check == "failed" or scope_violations:
            status = "blocked"
        elif revision_requests:
            status = "needs_revision"
        else:
            status = "approved"

        final_report = str(agent2_result.get("final_report", "")).strip()
        final_user_output = (
            final_report
            if status == "approved" and final_report
            else "Agent2 输出未通过 Agent1 审核，需要按 revision_requests 返工。"
        )

        return {
            "review_result": {
                "status": status,
                "completed_capabilities": completed_capabilities,
                "missing_capabilities": missing_capabilities,
                "scope_violations": scope_violations,
                "metric_consistency": metric_consistency,
                "evidence_check": evidence_check,
                "privacy_check": privacy_check,
                "final_user_output": final_user_output,
                "revision_requests": revision_requests,
            }
        }

    def _clarify_requirement(
        self,
        original_question: str,
        context: dict[str, Any],
        graph_insights: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        effective_question = str(context.get("business_question") or original_question)
        metric = context.get("metric") or self._detect_metric(effective_question)
        graph_metric_options = (graph_insights or {}).get("clarification_options", [])
        if graph_metric_options and not context.get("metric"):
            metric = ""
        time_range = self.normalize_time_range(
            context.get("time_range") or self._detect_time_range(effective_question)
        )
        clinic_scope_from_context = "clinic_scope" in context
        clinic_scope = context.get("clinic_scope") or self._detect_clinic_scope(effective_question)
        address_scope = self._detect_address_scope(effective_question)
        output_format = context.get("output_format") or self._detect_output_format(effective_question)
        population = context.get("population") or self._detect_population(effective_question)
        analysis_context = context.get("analysis_context") or self._detect_analysis_context(
            effective_question,
            metric,
        )

        if not self._has_business_analysis_intent(
            effective_question,
            metric,
            time_range,
            clinic_scope,
            graph_insights,
        ):
            return self._non_business_input_result(original_question, output_format, population)

        ambiguities = []
        clarification_questions = []
        if not metric:
            issue = "用户没有明确要分析的核心指标。"
            metric_options = []
            metric_question = "请说明本次要分析的指标或业务口径。"
            metric_type = "free_text"
            metric_source = "user_input"
            ambiguity_options = []
            if graph_metric_options:
                issue = "图谱中匹配到相关业务关系，但用户没有明确要分析的具体口径。"
                metric_options = graph_metric_options
                metric_question = "图谱中匹配到业务关系，本次要按哪个口径继续分析？"
                metric_type = "single_select"
                metric_source = "knowledge_graph_query"
                ambiguity_options = graph_metric_options

            ambiguities.append(
                {
                    "field": "metric",
                    "issue": issue,
                    "options": ambiguity_options,
                    "required": True,
                    "source": metric_source,
                }
            )
            clarification_questions.append(
                {
                    "id": "metric_definition",
                    "question": metric_question,
                    "type": metric_type,
                    "options": metric_options,
                    "required": True,
                    "source": metric_source,
                }
            )
        if not time_range:
            ambiguities.append(
                {
                    "field": "time_range",
                    "issue": "用户没有明确分析时间范围，不能安全取数。",
                    "options": ["2026-04", "last_30_days", "custom_range"],
                    "required": True,
                }
            )
            clarification_questions.append(
                {
                    "id": "time_range",
                    "question": "请补充本次分析的时间范围，例如“最近30天”“2026年4月”或“2026-04-01 到 2026-04-30”。",
                    "type": "free_text",
                    "options": [],
                    "required": True,
                    "source": "user_input",
                }
            )

        needs_clinic_clarification = not clinic_scope or (
            address_scope and not clinic_scope_from_context and self._is_unresolved_location_scope(clinic_scope)
        )
        if needs_clinic_clarification:
            clinic_issue = "用户没有明确门店或组织范围。"
            clinic_question = "请补充本次分析覆盖的门店名称、门店 ID、地址或组织范围。"
            if address_scope:
                clinic_issue = "用户提供了地址或区域，但还需要确认它对应哪些门店或组织范围。"
                clinic_question = (
                    f"你提到的地址或区域是“{address_scope}”，请确认要分析的门店名称、门店 ID 或组织范围。"
                )
            ambiguities.append(
                {
                    "field": "clinic_scope",
                    "issue": clinic_issue,
                    "options": [],
                    "required": True,
                    "source": "user_input",
                }
            )
            clarification_questions.append(
                {
                    "id": "clinic_scope",
                    "question": clinic_question,
                    "type": "free_text",
                    "options": [],
                    "required": True,
                    "source": "user_input",
                }
            )

        metric_info = self.metric_catalog.get(metric or "", {})
        status = "ready" if not clarification_questions else "needs_clarification"
        must_include = metric_info.get(
            "must_include",
            ["问题定义", "分析范围", "核心指标结果", "限制与风险"],
        )
        if analysis_context["analysis_intent"] == "root_cause_analysis":
            must_include = [
                "验证问题是否成立",
                "对比基准",
                "原因拆解",
                *[item for item in must_include if item not in {"原因拆解"}],
            ]

        return {
            "status": status,
            "original_question": original_question,
            "understood_intent": self._understood_intent(
                metric,
                time_range,
                clinic_scope,
                analysis_context,
            ),
            "root_goal": self._root_goal(metric, analysis_context),
            "ambiguities": ambiguities,
            "clarification_questions": clarification_questions,
            "implicit_assumptions": self._implicit_assumptions(status),
            "confirmed_scope": {
                "metric": metric or "",
                "metric_definition": context.get("metric_definition_override")
                or metric_info.get("definition", ""),
                "time_range": time_range or "",
                "clinic_scope": clinic_scope or [],
                "population": population,
                "analysis_intent": analysis_context["analysis_intent"],
                "problem_statement": analysis_context["problem_statement"],
                "problem_signal": analysis_context["problem_signal"],
                "excluded_scope": ["未授权门店", "非脱敏患者明细", "写入型数据库操作"],
            },
            "expected_result": {
                "format": output_format,
                "must_include": must_include,
                "acceptance_criteria": [
                    "Agent2 按任务合同完成全部待办",
                    "所有指标口径、时间范围和门店范围一致",
                    "结论有数据证据或图谱证据支撑",
                    "输出不包含未脱敏患者隐私信息",
                ],
            },
        }

    def _has_business_analysis_intent(
        self,
        question: str,
        metric: str,
        time_range: str,
        clinic_scope: list[str],
        graph_insights: dict[str, Any] | None,
    ) -> bool:
        if metric or time_range or clinic_scope:
            return True
        if (graph_insights or {}).get("relationships") or (graph_insights or {}).get("clarification_options"):
            return True

        domain_terms = [
            "门店",
            "诊所",
            "患者",
            "会员",
            "医生",
            "预约",
            "到诊",
            "就诊",
            "初诊",
            "复诊",
            "转化",
            "营收",
            "收入",
            "业绩",
            "现金流",
            "现金",
            "流水",
            "收款",
            "回款",
            "支出",
            "渠道",
            "续卡",
            "复购",
            "客单",
            "图表",
            "报告",
        ]
        analysis_terms = [
            "分析",
            "看看",
            "看一下",
            "统计",
            "查看",
            "查询",
            "计算",
            "情况",
            "怎么样",
            "趋势",
            "同比",
            "环比",
            "拆解",
            "复盘",
            "输出",
        ]
        return any(term in question for term in domain_terms) and any(
            term in question for term in analysis_terms
        )

    def _non_business_input_result(
        self,
        original_question: str,
        output_format: str,
        population: str,
    ) -> dict[str, Any]:
        return {
            "status": "needs_clarification",
            "original_question": original_question,
            "understood_intent": "当前输入不像业务分析需求，不能进入固定指标澄清流程。",
            "root_goal": "先获取用户真正要分析的业务问题，再查询图谱并生成任务合同。",
            "ambiguities": [
                {
                    "field": "business_question",
                    "issue": "用户输入没有包含可识别的业务对象、指标或分析目标。",
                    "options": [],
                    "required": True,
                    "source": "user_input",
                }
            ],
            "clarification_questions": [
                {
                    "id": "business_question",
                    "question": "请描述你要分析的业务问题，例如“帮我看最近30天上海门店转化率”。",
                    "type": "free_text",
                    "options": [],
                    "required": True,
                    "source": "user_input",
                }
            ],
            "implicit_assumptions": self._implicit_assumptions("needs_clarification"),
            "confirmed_scope": {
                "metric": "",
                "metric_definition": "",
                "time_range": "",
                "clinic_scope": [],
                "population": population,
                "excluded_scope": ["未授权门店", "非脱敏患者明细", "写入型数据库操作"],
            },
            "expected_result": {
                "format": output_format,
                "must_include": ["业务问题", "分析范围", "核心指标结果", "限制与风险"],
                "acceptance_criteria": [
                    "用户补充业务分析问题后才查询图谱并进入指标澄清",
                    "不对寒暄、空输入或无业务目标文本下发固定任务合同",
                ],
            },
        }

    def _build_graph_scope(
        self,
        clarification_result: dict[str, Any],
        graph_insights: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        confirmed_scope = clarification_result["confirmed_scope"]
        metric = confirmed_scope.get("metric", "")
        clinic_scope = confirmed_scope.get("clinic_scope", [])
        target_entities = []

        for clinic_id in clinic_scope:
            target_entities.append(
                {
                    "type": "Clinic",
                    "name": clinic_id,
                    "resolved_ids": [clinic_id],
                    "confidence": "high" if re.fullmatch(r"[A-Z]{2}\d{3}", clinic_id) else "medium",
                }
            )
        if metric:
            target_entities.append(
                {
                    "type": "Metric",
                    "name": metric,
                    "resolved_ids": [metric],
                    "confidence": "high",
                }
            )

        related_entities = ["Clinic", "Patient", "Appointment", "Visit", "Doctor"]
        if metric == "revenue":
            related_entities.append("Bill")
        for entity in (graph_insights or {}).get("related_entities", []):
            if entity not in related_entities:
                related_entities.append(entity)

        knowledge_gaps = []
        if clarification_result["status"] != "ready":
            knowledge_gaps.append(
                {
                    "gap": "需求仍存在必填歧义，暂不能限定完整图谱查询范围。",
                    "impact": "Agent2 无法安全执行取数和分析。",
                    "fallback": "先返回选项式澄清问题，等待补充后再生成任务合同。",
                }
            )
        if (graph_insights or {}).get("error"):
            knowledge_gaps.append(
                {
                    "gap": "真实图数据库查询失败。",
                    "impact": "Agent1 不能基于真实图谱生成澄清问题或任务合同。",
                    "fallback": "不使用本地 mock，等待 Graph API 恢复或修正鉴权后重试。",
                }
            )
        if metric:
            knowledge_gaps.append(
                {
                    "gap": "第一版没有真实业务口径库，指标定义来自静态目录。",
                    "impact": "正式分析前仍需 Agent2 在取数时复核口径。",
                    "fallback": "任务合同中要求输出 SQL、过滤条件和人工复核说明。",
                }
            )

        required_relationships = [
            {
                "from": "Clinic",
                "relation": "has_appointment",
                "to": "Appointment",
                "reason": "按门店限定预约和初诊漏斗范围。",
            },
            {
                "from": "Appointment",
                "relation": "belongs_to_patient",
                "to": "Patient",
                "reason": "确认分析人群并要求患者信息脱敏。",
            },
            {
                "from": "Visit",
                "relation": "served_by",
                "to": "Doctor",
                "reason": "支持医生维度拆解和原因假设。",
            },
        ]
        for relationship in (graph_insights or {}).get("relationships", []):
            if relationship not in required_relationships:
                required_relationships.append(relationship)

        allowed_spaces = ["clinic_operation_kg"]
        graph_space = (graph_insights or {}).get("space")
        if graph_space and graph_space not in allowed_spaces:
            allowed_spaces.insert(0, graph_space)

        return {
            "target_entities": target_entities,
            "related_entities": related_entities,
            "required_relationships": required_relationships,
            "excluded_entities": ["RawPatientIdentity", "PaymentCredential"],
            "graph_query_boundary": {
                "max_hops": 3,
                "allowed_spaces": allowed_spaces,
                "allowed_entity_types": related_entities + ["Metric"],
                "blocked_entity_types": ["RawPatientIdentity", "PaymentCredential"],
                "reason": "仅查询本次分析需要的门店、预约、患者脱敏关系和医生维度。",
            },
            "knowledge_gaps": knowledge_gaps,
        }

    def _extract_graph_insights(
        self,
        original_question: str,
        graph_data: Any,
    ) -> dict[str, Any]:
        graph = self._coerce_graph_data(graph_data)
        if not graph:
            return {}
        if graph.get("status") == "error":
            return {
                "source": "knowledge_graph_query",
                "space": graph.get("space", ""),
                "error": str(graph.get("error", "Graph API query failed.")),
                "relationships": [],
                "related_entities": [],
                "clarification_options": [],
            }

        vertices = graph.get("data", {}).get("vertices", [])
        edges = graph.get("data", {}).get("edges", [])
        schema_edges = graph.get("schema", {}).get("edges", {})
        if not isinstance(schema_edges, dict):
            schema_edges = {}
        vid_to_tag = {
            str(vertex.get("vid")): str(vertex.get("tag") or vertex.get("vid"))
            for vertex in vertices
            if isinstance(vertex, dict) and vertex.get("vid")
        }

        matched_edge_names = [
            str(edge_name)
            for edge_name in schema_edges
            if str(edge_name) and str(edge_name) in original_question
        ]
        relationships = []
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            relation = str(edge.get("edge") or "")
            if not relation:
                continue
            if relation not in original_question and not (
                "转化" in original_question and "转化" in relation
            ):
                continue
            if relation not in matched_edge_names:
                matched_edge_names.append(relation)

            src = str(edge.get("src") or "")
            dst = str(edge.get("dst") or "")
            relationships.append(
                {
                    "from": vid_to_tag.get(src, src),
                    "relation": relation,
                    "to": vid_to_tag.get(dst, dst),
                    "reason": "来自 knowledge_graph_query 的图谱关系。",
                }
            )

        if not relationships and matched_edge_names:
            relationships = [
                {
                    "from": "图谱实体",
                    "relation": edge_name,
                    "to": "图谱实体",
                    "reason": "来自 knowledge_graph_query 的图谱关系类型。",
                }
                for edge_name in matched_edge_names
            ]

        if not relationships:
            return {}

        related_entities = []
        for relationship in relationships:
            for key in ("from", "to"):
                entity = relationship[key]
                if entity and entity not in related_entities:
                    related_entities.append(entity)

        clarification_options = self._graph_clarification_options(relationships)

        return {
            "source": "knowledge_graph_query",
            "space": graph.get("space", ""),
            "relationships": relationships,
            "related_entities": related_entities,
            "clarification_options": clarification_options,
        }

    def _graph_clarification_options(self, relationships: list[dict[str, str]]) -> list[str]:
        options = []
        for relationship in relationships:
            relation = relationship.get("relation", "")
            source = relationship.get("from", "图谱实体")
            target = relationship.get("to", "图谱实体")
            if not relation:
                continue

            if relation == "转化":
                candidates = [
                    "转化率：患者转化为会员的比例",
                    "转化人数：完成转化的患者数量",
                    "转化路径：患者到会员的转化链路",
                    "转化关联对象：患者、会员、初诊医生、责任医生之间的关系",
                ]
            else:
                candidates = [
                    f"{relation}数量：统计{source}到{target}的{relation}记录数",
                    f"{relation}率：统计{relation}成功比例，分母需继续确认",
                    f"{relation}路径：分析{source}到{target}的{relation}链路",
                    f"{relation}关联对象：分析{source}、{target}及相关角色之间的关系",
                ]
            for candidate in candidates:
                if candidate not in options:
                    options.append(candidate)
        return options

    def _graph_query_blocked_result(
        self,
        original_question: str,
        graph_insights: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "status": "blocked",
            "original_question": original_question,
            "understood_intent": "Agent1 需要先查询真实图数据库才能安全澄清需求。",
            "root_goal": "等待 knowledge_graph_query 恢复后再生成澄清问题或任务合同。",
            "ambiguities": [
                {
                    "field": "graph_data",
                    "issue": "真实图数据库查询失败，不能使用本地 mock 或静态规则替代。",
                    "required": True,
                    "source": "knowledge_graph_query",
                }
            ],
            "clarification_questions": [],
            "implicit_assumptions": [
                "Agent1 严格依赖真实图数据库返回结果，不使用本地 mock 生成澄清内容。",
                "Graph API 不可用时不下发 Agent2。",
            ],
            "blocking_reason": {
                "source": "knowledge_graph_query",
                "error": graph_insights["error"],
            },
            "confirmed_scope": {
                "metric": "",
                "metric_definition": "",
                "time_range": "",
                "clinic_scope": [],
                "population": "authorized business population",
                "excluded_scope": ["未授权门店", "非脱敏患者明细", "写入型数据库操作"],
            },
            "expected_result": {
                "format": "Markdown",
                "must_include": ["图数据库查询错误", "阻塞原因", "恢复后重试建议"],
                "acceptance_criteria": [
                    "Graph API 查询成功后才生成澄清问题",
                    "不使用本地 mock 或静态规则替代真实图谱数据",
                ],
            },
        }

    def _strict_graph_match_failed(
        self,
        original_question: str,
        context: dict[str, Any],
        graph_insights: dict[str, Any],
    ) -> bool:
        if not context.get("strict_graph_match"):
            return False
        if graph_insights.get("relationships") or graph_insights.get("clarification_options"):
            return False

        graph = self._coerce_graph_data(context.get("graph_data"))
        if not graph or graph.get("status") == "error":
            return False

        effective_question = str(context.get("business_question") or original_question)
        metric = context.get("metric") or self._detect_metric(effective_question)
        return bool(metric)

    def _graph_match_blocked_result(
        self,
        original_question: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        effective_question = str(context.get("business_question") or original_question)
        metric = context.get("metric") or self._detect_metric(effective_question)
        metric_label = self._metric_label(metric, "")
        return {
            "status": "blocked",
            "original_question": original_question,
            "understood_intent": "Agent1 已识别业务问题，但真实图谱没有命中可支撑该指标的实体或关系。",
            "root_goal": "先明确图谱缺口或换一个图谱可支撑的业务问题，再继续澄清。",
            "ambiguities": [
                {
                    "field": "graph_match",
                    "issue": f"真实图谱未命中与“{metric_label or metric}”相关的实体或关系。",
                    "required": True,
                    "source": "knowledge_graph_query",
                }
            ],
            "clarification_questions": [],
            "implicit_assumptions": [
                "Agent1 不使用静态指标目录替代真实图谱命中结果。",
                "图谱未命中时不生成给 Agent2 的任务合同。",
            ],
            "blocking_reason": {
                "source": "knowledge_graph_query",
                "error": f"图谱查询成功，但未命中与“{metric_label or metric}”相关的实体或关系；当前不生成任务合同。",
            },
            "confirmed_scope": {
                "metric": metric or "",
                "metric_definition": "",
                "time_range": "",
                "clinic_scope": context.get("clinic_scope") or self._detect_clinic_scope(effective_question),
                "population": context.get("population") or "authorized business population",
                "excluded_scope": ["未授权门店", "非脱敏患者明细", "写入型数据库操作"],
            },
            "expected_result": {
                "format": context.get("output_format") or "Markdown",
                "must_include": ["图谱未命中", "阻塞原因", "可继续澄清的信息"],
                "acceptance_criteria": [
                    "图谱命中目标指标实体或关系后才生成任务合同",
                    "不把缺失的图谱证据替换成静态兜底口径",
                ],
            },
        }

    def _coerce_graph_data(self, graph_data: Any) -> dict[str, Any]:
        if isinstance(graph_data, dict):
            return graph_data
        if isinstance(graph_data, str):
            try:
                parsed = json.loads(graph_data)
            except json.JSONDecodeError:
                return {}
            if isinstance(parsed, dict):
                return parsed
        return {}

    def _build_task_contract(
        self,
        clarification_result: dict[str, Any],
        graph_scope: dict[str, Any],
    ) -> dict[str, Any]:
        confirmed_scope = clarification_result["confirmed_scope"]
        task_id = self._task_id(confirmed_scope)
        is_root_cause_analysis = (
            confirmed_scope.get("analysis_intent") == "root_cause_analysis"
        )
        final_sections = [
            "问题定义",
            "分析范围",
            "核心指标结果",
            "维度拆解",
            "主要原因",
            "建议动作",
            "限制与风险",
        ]
        if is_root_cause_analysis:
            final_sections = [
                "问题定义",
                "分析范围",
                "问题是否成立",
                "对比基准",
                "维度拆解",
                "原因假设",
                "证据链",
                "建议动作",
                "限制与风险",
            ]

        expected_deliverable = {
            "format": clarification_result["expected_result"]["format"],
            "sections": final_sections,
            "requirements": [
                "必须回答澄清后的业务目标。",
                "必须说明数据范围、图谱证据、业务数据证据和已知限制。",
                "不得输出未脱敏患者姓名、手机号、邮箱或支付凭证。",
            ],
        }

        return {
            "task_id": task_id,
            "goal": clarification_result["root_goal"],
            "clarified_task": {
                "original_question": clarification_result["original_question"],
                "understood_intent": clarification_result["understood_intent"],
                "analysis_intent": confirmed_scope["analysis_intent"],
                "agent2_execution_owner": True,
                "execution_note": "Agent1 只负责澄清任务和边界；Agent2 自主规划执行步骤和工具调用顺序。",
            },
            "input_context": {
                "metric": confirmed_scope["metric"],
                "metric_label": self._metric_label(
                    confirmed_scope["metric"],
                    confirmed_scope["metric_definition"],
                ),
                "metric_definition": confirmed_scope["metric_definition"],
                "time_range": confirmed_scope["time_range"],
                "clinic_scope": confirmed_scope["clinic_scope"],
                "population": confirmed_scope["population"],
                "analysis_intent": confirmed_scope["analysis_intent"],
                "problem_statement": confirmed_scope["problem_statement"],
                "problem_signal": confirmed_scope["problem_signal"],
            },
            "graph_query_boundary": graph_scope.get("graph_query_boundary", {}),
            "graph_entity_hints": graph_scope.get("target_entities", []),
            "graph_relationship_hints": graph_scope.get("required_relationships", []),
            "required_capabilities": self._required_capabilities(
                confirmed_scope,
                graph_scope,
                is_root_cause_analysis,
            ),
            "acceptance_criteria": self._contract_acceptance_criteria(
                confirmed_scope,
                is_root_cause_analysis,
            ),
            "safety_constraints": [
                "所有数据库操作必须只读。",
                "必须限定 input_context 中的指标、时间范围、门店范围和人群范围。",
                "不得输出未脱敏个人身份信息、联系方式或支付凭证。",
                "真实工具失败时必须返回结构化失败原因，不得生成模拟结论。",
            ],
            "agent2_planning_policy": {
                "execution_steps": "agent2_decides",
                "tool_call_order": "agent2_decides",
                "must_use_same_graph_tool": "knowledge_graph_query",
                "agent1_does_not_prescribe_steps": True,
            },
            "expected_deliverable": expected_deliverable,
            "final_expected_output": expected_deliverable,
        }

    def _required_capabilities(
        self,
        confirmed_scope: dict[str, Any],
        graph_scope: dict[str, Any],
        is_root_cause_analysis: bool,
    ) -> list[dict[str, Any]]:
        metric_label = self._metric_label(
            confirmed_scope["metric"],
            confirmed_scope["metric_definition"],
        )
        capabilities = [
            self._capability(
                "knowledge_graph_query",
                True,
                "Agent2 使用与 Agent1 相同的 knowledge_graph_query 工具，自主查询图数据库并确认实体、关系、字段位置和图谱缺口。",
                [
                    "必须记录查询到的实体、关系和缺口。",
                    "必须遵守 graph_query_boundary。",
                    "不得使用本地 mock 替代真实图谱查询结果。",
                ],
                {
                    "graph_query_boundary": graph_scope.get("graph_query_boundary", {}),
                    "relationship_hints": graph_scope.get("required_relationships", []),
                },
            ),
            self._capability(
                "data_fetch",
                True,
                "Agent2 自主生成只读查询或调用取数工具，获取限定范围内的业务数据。",
                [
                    "必须包含指标、时间范围、门店范围和人群过滤条件。",
                    "必须返回字段、行数、过滤条件和脱敏说明。",
                    "不得扩大取数范围。",
                ],
            ),
            self._capability(
                "sql_check",
                True,
                "Agent2 必须检查 SQL 或数据查询的只读性、边界、性能风险和隐私风险。",
                [
                    "不得出现 DELETE、UPDATE、DROP、TRUNCATE 等写入或破坏性语句。",
                    "不得输出患者原始姓名、手机号、邮箱或支付凭证。",
                ],
            ),
            self._capability(
                "cache_manager",
                False,
                "Agent2 可以根据任务 ID 和输入上下文缓存中间数据，支持断点续跑和减少重复取数。",
                [
                    "如果使用缓存，必须说明 cache_key、过期时间和缓存命中状态。",
                    "如果不使用缓存，必须说明 skipped 原因。",
                ],
            ),
        ]

        if is_root_cause_analysis:
            capabilities.append(
                self._capability(
                    "root_cause_analysis",
                    True,
                    f"验证{metric_label}是否偏低或异常，并拆解主要影响维度和原因假设。",
                    [
                        "必须先验证 problem_signal 是否成立，并说明对比基准。",
                        "没有可用基准时必须标记为 unable_to_validate，不能默认问题成立。",
                        "必须按门店、医生、渠道、时间周期、患者类型、预约到诊链路和图谱关系等维度拆解。",
                        "每条原因必须包含数据证据或图谱证据、反证或限制、置信度和建议验证动作。",
                    ],
                )
            )
        else:
            capabilities.append(
                self._capability(
                    "metric_analysis",
                    True,
                    f"计算{metric_label}并按业务维度拆解表现、趋势和异常。",
                    [
                        "必须输出指标值、样本量、过滤条件和维度拆解。",
                        "有可用基线时必须做同比、环比或目标值对比。",
                        "每条发现必须引用数据证据或图谱证据。",
                    ],
                )
            )

        capabilities.extend(
            [
                self._capability(
                    "visualization",
                    True,
                    "Agent2 自主决定需要的图表类型，生成图表规格或图表文件。",
                    [
                        "每个图表必须只回答一个业务问题。",
                        "每个图表必须包含标题、单位、时间范围、数据来源和明确结论。",
                    ],
                ),
                self._capability(
                    "report_generation",
                    True,
                    "Agent2 根据 expected_deliverable 生成最终报告，供 Agent1 审核。",
                    [
                        "报告必须回答 clarified_task.understood_intent。",
                        "报告不得超出 input_context 和 graph_query_boundary。",
                        "报告必须明确限制、风险和未验证项。",
                    ],
                ),
            ]
        )
        return capabilities

    def _capability(
        self,
        name: str,
        required: bool,
        purpose: str,
        acceptance_criteria: list[str],
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        capability = {
            "name": name,
            "required": required,
            "owner": "Agent2",
            "purpose": purpose,
            "acceptance_criteria": acceptance_criteria,
        }
        if constraints:
            capability["constraints"] = constraints
        return capability

    def _contract_acceptance_criteria(
        self,
        confirmed_scope: dict[str, Any],
        is_root_cause_analysis: bool,
    ) -> list[str]:
        criteria = [
            "Agent2 必须自主规划执行步骤，不依赖 Agent1 固定步骤。",
            "Agent2 必须使用 task_contract.input_context 作为唯一业务范围来源。",
            "Agent2 必须自行调用 knowledge_graph_query 确认图谱实体和关系。",
            "Agent2 必须输出可被 Agent1 审核的结构化结果和最终报告。",
        ]
        if is_root_cause_analysis:
            criteria.extend(
                [
                    "必须先验证用户声称的问题是否成立，再解释原因。",
                    "必须说明对比基准；没有基准时不得默认问题成立。",
                    "原因结论必须有数据证据或图谱证据支撑。",
                ]
            )
        else:
            criteria.append("必须计算目标指标并完成维度拆解、趋势说明和建议动作。")
        return criteria

    def _detect_metric(self, question: str) -> str:
        for metric, info in self.metric_catalog.items():
            if any(keyword in question for keyword in info["keywords"]):
                return metric
        return ""

    def _detect_time_range(self, question: str) -> str:
        if any(term in question for term in ["最近一个月", "近一个月", "最近一月", "近一月"]):
            return "recent_1_month"
        if any(term in question for term in ["最近30天", "近30天", "30天"]):
            return "last_30_days"
        if any(term in question for term in ["最近7天", "近7天", "7天"]):
            return "last_7_days"
        if "本月" in question:
            return "this_month"
        if "上月" in question or "上个月" in question:
            return "previous_month"

        full_match = re.search(r"(20\d{2})\s*年\s*(1[0-2]|0?[1-9])\s*月", question)
        if full_match:
            year, month = full_match.groups()
            return f"{year}-{int(month):02d}"

        iso_match = re.search(r"(20\d{2})[-/](1[0-2]|0?[1-9])", question)
        if iso_match:
            year, month = iso_match.groups()
            return f"{year}-{int(month):02d}"

        range_match = re.search(
            r"(20\d{2}[-/]\d{1,2}[-/]\d{1,2})\s*(?:至|到|-)\s*(20\d{2}[-/]\d{1,2}[-/]\d{1,2})",
            question,
        )
        if range_match:
            return " to ".join(date.replace("/", "-") for date in range_match.groups())

        return ""

    def normalize_time_range(self, time_range: str) -> str:
        text = str(time_range or "").strip()
        if not text:
            return ""

        today = self._today()
        recent_days_match = re.search(r"(?:最近|近)\s*(\d{1,3})\s*天", text)
        if recent_days_match:
            days = int(recent_days_match.group(1))
            return self._format_date_range(today - timedelta(days=days), today)

        if text == "last_30_days" or any(
            term in text
            for term in [
                "最近30天",
                "近30天",
                "30天",
                "最近一个月",
                "近一个月",
                "最近一月",
                "近一月",
                "一个月",
                "一月",
                "1个月",
            ]
        ):
            if any(term in text for term in ["最近一个月", "近一个月", "最近一月", "近一月", "一个月", "一月", "1个月"]):
                start = self._subtract_months(today, 1)
            else:
                start = today - timedelta(days=30)
            return self._format_date_range(start, today)

        if text == "last_7_days" or any(term in text for term in ["最近7天", "近7天", "7天"]):
            return self._format_date_range(today - timedelta(days=7), today)

        if text == "this_month" or "本月" in text:
            return self._format_date_range(today.replace(day=1), today)

        if text == "previous_month" or "上月" in text or "上个月" in text:
            first_this_month = today.replace(day=1)
            last_previous_month = first_this_month - timedelta(days=1)
            first_previous_month = last_previous_month.replace(day=1)
            return self._format_date_range(first_previous_month, last_previous_month)

        month_match = re.fullmatch(r"(20\d{2})-(1[0-2]|0[1-9])", text)
        if month_match:
            year, month = [int(part) for part in month_match.groups()]
            start = date(year, month, 1)
            end = date(year, month, calendar.monthrange(year, month)[1])
            return self._format_date_range(start, end)

        range_match = re.fullmatch(
            r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\s*(?:至|到|-|to)\s*(20\d{2})[-/](\d{1,2})[-/](\d{1,2})",
            text,
        )
        if range_match:
            start_year, start_month, start_day, end_year, end_month, end_day = [
                int(part) for part in range_match.groups()
            ]
            return self._format_date_range(
                date(start_year, start_month, start_day),
                date(end_year, end_month, end_day),
            )

        return text

    def _today(self) -> date:
        configured_today = os.getenv("AGENT1_TODAY", "").strip()
        if configured_today:
            return date.fromisoformat(configured_today)
        return date.today()

    def _subtract_months(self, value: date, months: int) -> date:
        month_index = value.year * 12 + value.month - 1 - months
        year = month_index // 12
        month = month_index % 12 + 1
        day = min(value.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    def _format_date_range(self, start: date, end: date) -> str:
        return f"{start.isoformat()} to {end.isoformat()}"

    def _detect_clinic_scope(self, question: str) -> list[str]:
        clinic_ids = sorted(
            set(re.findall(r"(?<![A-Z0-9])([A-Z]{2}\d{3})(?![A-Z0-9])", question))
        )
        if clinic_ids:
            return clinic_ids
        if "上海门店" in question or "上海" in question:
            return ["Shanghai clinics"]
        named_clinic = self._detect_named_clinic_scope(question)
        if named_clinic:
            return [named_clinic]
        address_scope = self._detect_address_scope(question)
        if address_scope:
            return [address_scope]
        return []

    def _detect_named_clinic_scope(self, question: str) -> str:
        for marker in ("门店", "诊所", "院区", "店"):
            marker_index = question.find(marker)
            if marker_index < 0:
                continue
            start = max(0, marker_index - 12)
            name = question[start : marker_index + len(marker)]
            name = re.sub(
                r"^(帮我|帮忙|请|查看|查询|分析|看一下|看看|看|统计|计算|本次|这个|那个|最近|近)+",
                "",
                name,
            )
            name = name.strip("，,。；;：: 的")
            if not name or name in {"门店", "诊所", "院区", "店", "最近门店", "近门店"}:
                continue
            if name in {"上海门店", "上海"}:
                return ""
            if len(name) >= 3:
                return name
        return ""

    def _detect_address_scope(self, question: str) -> str:
        match = re.search(
            r"([\u4e00-\u9fffA-Za-z0-9]{2,}(?:省|市|区|县|镇|乡|街道|路|街|门店|诊所|院区)"
            r"(?:[\u4e00-\u9fffA-Za-z0-9]*(?:省|市|区|县|镇|乡|街道|路|街|门店|诊所|院区))*)",
            question,
        )
        if not match:
            return ""

        address = match.group(1)
        for suffix in ("最近", "近", "本月", "上月", "今年", "去年"):
            if suffix in address:
                address = address.split(suffix, 1)[0]
        address = address.strip("，,。；;：: 的")
        location_markers = ("省", "市", "区", "县", "镇", "乡", "街道", "路", "街", "诊所", "院区")
        if "门店" in address and not any(marker in address for marker in location_markers):
            return ""
        if address in {"帮我看看", "看一下", "看看", "查询", "分析"}:
            return ""
        return address

    def _is_unresolved_location_scope(self, clinic_scope: list[str]) -> bool:
        if not clinic_scope:
            return False
        for item in clinic_scope:
            scope = str(item)
            if re.fullmatch(r"[A-Z]{2}\d{3}", scope):
                continue
            if scope in {"Shanghai clinics", "all_authorized_clinics"}:
                continue
            return True
        return False

    def _detect_output_format(self, question: str) -> str:
        upper_question = question.upper()
        if "PPT" in upper_question or "PPTX" in upper_question:
            return "PPT"
        if "HTML" in upper_question:
            return "HTML"
        if "图表" in question or "chart" in question.lower():
            return "chart_pack"
        return "Markdown"

    def _detect_population(self, question: str) -> str:
        if "儿童" in question or "儿牙" in question:
            return "pediatric dental patients"
        if "初诊" in question:
            return "first-visit patients"
        if "复诊" in question:
            return "revisit patients"
        return "authorized business population"

    def _detect_analysis_context(self, question: str, metric: str) -> dict[str, Any]:
        metric_label = self._metric_label(metric) or "目标指标"
        cause_terms = ["为什么", "原因", "怎么回事", "因为什么", "分析原因", "归因"]
        low_terms = ["很低", "偏低", "过低", "低", "不好", "差"]
        change_terms = ["下降", "降低", "下滑", "变差", "异常", "波动"]

        asks_cause = any(term in question for term in cause_terms)
        has_low_signal = any(term in question for term in low_terms)
        has_change_signal = any(term in question for term in change_terms)
        if not (asks_cause or has_low_signal or has_change_signal):
            return {
                "analysis_intent": "metric_analysis",
                "problem_statement": "",
                "problem_signal": {},
            }

        signal_type = "low_metric" if has_low_signal else "metric_anomaly"
        if has_change_signal and not has_low_signal:
            signal_type = "metric_change_or_anomaly"

        return {
            "analysis_intent": "root_cause_analysis",
            "problem_statement": question.strip(),
            "problem_signal": {
                "type": signal_type,
                "metric": metric or "",
                "metric_label": metric_label,
                "description": f"用户认为{metric_label}偏低或异常，需要解释原因。",
                "comparison_baseline": "unspecified",
                "requires_baseline_validation": True,
                "validation_rule": "Agent2 必须先用历史同期、环比、同类门店均值或目标值等可用基准验证问题是否成立；没有可用基准时必须明确说明无法验证，不得默认认为偏低。",
            },
        }

    def _understood_intent(
        self,
        metric: str,
        time_range: str,
        clinic_scope: list[str],
        analysis_context: dict[str, Any] | None = None,
    ) -> str:
        if not metric:
            return "用户希望分析门店经营情况，但核心指标尚未明确。"
        metric_label = self._metric_label(metric)
        if (analysis_context or {}).get("analysis_intent") == "root_cause_analysis":
            if time_range and clinic_scope:
                return (
                    f"验证 {time_range}、{', '.join(clinic_scope)} 的{metric_label}是否偏低，"
                    "并定位原因和改善动作。"
                )
            return f"用户希望解释{metric_label}偏低或异常的原因，但时间范围或门店范围仍需确认。"
        if time_range and clinic_scope:
            return f"分析 {time_range}、{', '.join(clinic_scope)} 的{metric_label}表现并形成可交付报告。"
        return f"用户希望分析{metric_label}，但时间范围或门店范围仍需确认。"

    def _metric_label(self, metric: str, metric_definition: str = "") -> str:
        if not metric:
            return ""
        catalog_label = self.metric_catalog.get(metric, {}).get("label")
        if catalog_label:
            return str(catalog_label)
        if metric_definition:
            return metric_definition
        return metric

    def _root_goal(self, metric: str, analysis_context: dict[str, Any] | None = None) -> str:
        metric_label = self._metric_label(metric)
        if (analysis_context or {}).get("analysis_intent") == "root_cause_analysis":
            return f"验证{metric_label or '目标指标'}是否偏低或异常，并定位主要原因、影响维度和可执行改善动作。"
        if metric == "first_visit_conversion_rate":
            return "定位初诊转化表现、主要影响维度和可执行改善动作。"
        if metric == "revisit_rate":
            return "定位复诊表现、流失风险和可执行改善动作。"
        if metric == "revenue":
            return "定位营收变化、关键贡献维度和可执行改善动作。"
        if metric == "appointment_count":
            return "定位预约量变化、渠道或门店差异和可执行改善动作。"
        if metric == "cash_flow":
            return "定位现金流入、现金流出、净现金流变化和门店经营风险。"
        return "明确业务问题、分析范围和最终交付预期。"

    def _implicit_assumptions(self, status: str) -> list[str]:
        assumptions = [
            "Agent2 只能依据 task_contract 执行，不重新解释用户原始模糊需求。",
            "所有患者姓名、手机号等个人信息必须脱敏。",
            "第一版不连接真实权限系统，按任务合同范围模拟权限边界。",
        ]
        if status != "ready":
            assumptions.append("缺失必填信息时不下发 Agent2，先返回澄清问题。")
        return assumptions

    def _task_id(self, confirmed_scope: dict[str, Any]) -> str:
        raw = json.dumps(confirmed_scope, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
        return f"task_{digest}"

    def _completed_capabilities(
        self,
        agent2_result: dict[str, Any],
        required_capabilities: list[str],
    ) -> list[str]:
        explicit = agent2_result.get("completed_capabilities")
        if isinstance(explicit, list):
            return [str(capability) for capability in explicit]

        completed = []
        result_keys_by_capability = {
            "knowledge_graph_query": ["knowledge_graph_result", "graph_result"],
            "data_fetch": ["data_fetch_result"],
            "sql_check": ["sql_check_result"],
            "cache_manager": ["cache_result"],
            "metric_analysis": ["analysis_result"],
            "root_cause_analysis": ["analysis_result"],
            "visualization": ["visualization_result"],
            "report_generation": ["final_report", "report_artifact"],
        }
        for capability in required_capabilities:
            keys = result_keys_by_capability.get(capability, [])
            if any(key in agent2_result for key in keys):
                completed.append(capability)
        return completed

    def _scope_violations(
        self,
        task_contract: dict[str, Any],
        agent2_result: dict[str, Any],
    ) -> list[str]:
        expected_scope = set(task_contract.get("input_context", {}).get("clinic_scope", []))
        data_scope = (
            agent2_result.get("data_fetch_result", {})
            .get("scope", {})
            .get("clinic_scope", [])
        )
        if not expected_scope or not data_scope:
            return []
        unexpected = sorted(set(data_scope) - expected_scope)
        if unexpected:
            return [f"Agent2 returned clinics outside task scope: {', '.join(unexpected)}"]
        return []

    def _metric_consistency(
        self,
        task_contract: dict[str, Any],
        agent2_result: dict[str, Any],
    ) -> str:
        expected_metric = task_contract.get("input_context", {}).get("metric", "")
        reported_metric = (
            agent2_result.get("analysis_result", {})
            .get("metric_summary", {})
            .get("metric", "")
        )
        if reported_metric and expected_metric and reported_metric != expected_metric:
            return "failed"
        return "passed"

    def _evidence_check(self, agent2_result: dict[str, Any]) -> str:
        analysis = agent2_result.get("analysis_result")
        final_report = str(agent2_result.get("final_report", "")).strip()
        if not analysis or analysis.get("status") == "failed" or not final_report:
            return "failed"
        return "passed"

    def _privacy_check(self, agent2_result: dict[str, Any]) -> str:
        serialized = json.dumps(agent2_result, ensure_ascii=False, sort_keys=True)
        if PHONE_PATTERN.search(serialized) or EMAIL_PATTERN.search(serialized):
            return "failed"
        return "passed"

    def _revision_requests(
        self,
        missing_capabilities: list[str],
        scope_violations: list[str],
        metric_consistency: str,
        evidence_check: str,
        privacy_check: str,
    ) -> list[dict[str, str]]:
        requests = []
        if missing_capabilities:
            requests.append(
                {
                    "target_capability": ",".join(missing_capabilities),
                    "issue": "Agent2 未满足任务合同要求的能力或输出。",
                    "required_fix": "由 Agent2 自主补齐缺失能力对应的工具调用、分析结果或报告内容。",
                }
            )
        for violation in scope_violations:
            requests.append(
                {
                    "target_capability": "data_fetch",
                    "issue": violation,
                    "required_fix": "重新按 task_contract.input_context.clinic_scope 取数。",
                }
            )
        if metric_consistency == "failed":
            requests.append(
                {
                    "target_capability": "metric_analysis",
                    "issue": "Agent2 输出指标与任务合同指标不一致。",
                    "required_fix": "按 task_contract.input_context.metric 重新计算并说明口径。",
                }
            )
        if evidence_check == "failed":
            requests.append(
                {
                    "target_capability": "report_generation",
                    "issue": "分析结果缺少证据或最终报告。",
                    "required_fix": "补充 analysis_result、证据说明和 final_report。",
                }
            )
        if privacy_check == "failed":
            requests.append(
                {
                    "target_capability": "data_fetch",
                    "issue": "输出中疑似包含未脱敏个人信息。",
                    "required_fix": "移除或脱敏患者手机号、邮箱等敏感字段后重新提交。",
                }
            )
        return requests


def build_scheduler_agent(verbose: bool = True) -> Any:
    from crewai import Agent

    from tools.kg_query import KnowledgeGraphQueryTool
    from tools.problem_reporter import ProblemReporterTool

    return Agent(
        role="Agent1 需求澄清与任务规划专家",
        goal=(
            "基于用户问题和 knowledge_graph_query 返回的图谱数据完成需求澄清、"
            "范围限定、任务合同生成，并在遇到问题时通过 problem_reporter 上报。"
        ),
        backstory=(
            "你负责把模糊业务问题变成 Agent2 可以执行的清晰任务。"
            "你只使用图谱查询和问题上报工具，不直接取业务数据，也不调用 Agent3。"
        ),
        verbose=verbose,
        allow_delegation=False,
        tools=[KnowledgeGraphQueryTool(), ProblemReporterTool()],
    )


def build_clarification_task(original_question: str, scheduler_agent: Any | None = None) -> Any:
    from crewai import Task

    agent = scheduler_agent or build_scheduler_agent()
    return Task(
        description=(
            "澄清用户问题并输出结构化 Agent1 结果。\n"
            f"用户问题：{original_question}\n"
            "如果用户输入是业务分析需求，必须先调用 knowledge_graph_query 获取图谱数据，"
            "再根据图谱中的实体和关系生成澄清问题；如果只是寒暄或缺少业务目标，先要求用户补充业务问题。"
            "如果发现口径歧义或工具异常，使用 problem_reporter 上报。"
        ),
        expected_output=(
            "输出 JSON 对象，包含 clarification_result、graph_scope 和 task_contract。"
            "如果仍需要澄清，task_contract 必须为空对象。"
        ),
        agent=agent,
    )


def run_agent1_clarification(
    original_question: str,
    user_context: dict[str, Any] | None = None,
    graph_tool: Any | None = None,
    agent1: Agent1 | None = None,
) -> dict[str, Any]:
    from tools.kg_query import KnowledgeGraphQueryTool

    context = dict(user_context or {})
    coordinator = agent1 or Agent1()
    effective_question = str(context.get("business_question") or original_question)
    if "graph_data" not in context and coordinator.should_query_graph(original_question, context):
        tool = graph_tool or KnowledgeGraphQueryTool()
        context["graph_data"] = tool._run(effective_question)

    return coordinator.prepare_task(original_question, context)
