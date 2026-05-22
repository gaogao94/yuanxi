"""Local Agent1 real Graph API smoke test for PyCharm.

Run this file in PyCharm with the project interpreter:
/Users/ameng/temporary/yuanxi/.venv/bin/python
"""

from __future__ import annotations

import json
import os
import re

from dotenv import load_dotenv

from agents.agent1 import Agent1, Agent1LLMClarifier, Agent1LLMError, run_agent1_clarification
from tools.nebula_graph_query import NebulaGraphQueryTool


MAX_CONVERSATION_TURNS = 12


def main() -> None:
    load_dotenv()
    os.environ["GRAPH_API_STRICT"] = "1"
    os.environ.setdefault("GRAPH_API_AUTO_SPACE", "1")
    os.environ.pop("MEDGRAPH_JSON_PATH", None)

    configured_space = os.getenv("GRAPH_API_SPACE", "").strip()
    auto_space = os.getenv("GRAPH_API_AUTO_SPACE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    print("Agent1 local conversation test")
    print("Graph API:", os.getenv("GRAPH_API_BASE_URL", "https://graph.automed.cn"))
    print("Configured space:", configured_space or "未设置")
    print("Space selection:", "auto" if auto_space else "configured")
    print("Strict mode: on")
    print("LLM mode:", "off" if _llm_disabled() else "on")
    if not _llm_disabled():
        print("LLM model:", os.getenv("OPENAI_MODEL_NAME", "deepseek-chat"))
    print()

    question = input("你：").strip()
    if not question:
        question = "帮我看看最近门店转化怎么样"
        print(f"Agent1：使用默认问题：{question}")

    agent1_result = _run_conversation(question)
    _print_final_result(agent1_result)


def _load_graph(question: str) -> dict:
    raw_result = NebulaGraphQueryTool()._run(question, output_format="json")
    return json.loads(raw_result)


def _build_initial_context(question: str) -> dict:
    if not Agent1().should_query_graph(question):
        print("Agent1：当前还不是完整的业务分析问题，我先不查图谱。")
        return {}

    print("Agent1：我先查图谱确认相关实体和关系...")
    graph_result = _load_graph(question)
    _print_graph_summary(graph_result)
    return {"graph_data": graph_result, "strict_graph_match": True}


def _build_llm_clarifier() -> Agent1LLMClarifier | None:
    if _llm_disabled():
        return None
    try:
        return Agent1LLMClarifier.from_env()
    except Agent1LLMError as exc:
        if _allow_deterministic_fallback():
            print(f"Agent1：LLM 不可用，临时使用确定性本地流程。原因：{exc}")
            return None
        raise SystemExit(
            "Agent1：LLM 未配置或不可用，无法进行真实大模型本地测试。"
            "请检查 OPENAI_API_KEY、OPENAI_API_BASE、OPENAI_MODEL_NAME。"
        ) from exc


def _llm_disabled() -> bool:
    return os.getenv("AGENT1_USE_LLM", "1").strip().lower() in {"0", "false", "no", "off"}


def _allow_deterministic_fallback() -> bool:
    return os.getenv("AGENT1_ALLOW_DETERMINISTIC_FALLBACK", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _print_graph_summary(graph: dict) -> None:
    status = graph.get("status", "ok")
    if status == "error":
        print("Agent1：图谱查询失败：", graph.get("error", ""))
        return

    schema = graph.get("schema", {})
    data = graph.get("data", {})
    matched_edges = data.get("edges", [])
    relation_names = [edge.get("edge", "") for edge in matched_edges if isinstance(edge, dict)]
    relation_text = "、".join([name for name in relation_names if name]) or "暂未命中采样边"
    print(
        "Agent1：图谱查询完成，"
        f"space={graph.get('space', '')}，"
        f"tag={len(schema.get('tags', {}))}，"
        f"edge_type={len(schema.get('edges', {}))}，"
        f"命中关系={relation_text}。"
    )


def _print_agent1_result(result: dict) -> None:
    clarification = result["clarification_result"]
    status = clarification["status"]
    print("agent1_status:", status)

    if status == "needs_clarification":
        print("\n需要澄清的问题：")
        for index, item in enumerate(clarification["clarification_questions"], 1):
            print(f"\n{index}. {item['question']}")
            for option in item.get("options", []):
                print(f"   - {option}")
            print("   source:", item.get("source", "rule"))
        return

    if status == "ready":
        print("\n已生成 task_contract：")
        print(json.dumps(result["task_contract"], ensure_ascii=False, indent=2))
        return

    if status == "blocked":
        print("\n阻塞原因：")
        print(json.dumps(clarification.get("blocking_reason", {}), ensure_ascii=False, indent=2))
        return

    print("\n完整输出：")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _run_conversation(question: str) -> dict:
    context: dict = {}
    llm = _build_llm_clarifier()
    for _turn_index in range(MAX_CONVERSATION_TURNS):
        if "graph_data" not in context:
            context.update(_build_initial_context(question))

        result = run_agent1_clarification(question, user_context=context)
        clarification = result["clarification_result"]
        status = clarification["status"]

        if status in {"ready", "blocked"}:
            return result

        if status != "needs_clarification":
            return result

        item = _next_clarification_item(result)
        if not item:
            return result

        answer = _ask_clarification(item, llm, question, context, result)
        if _answer_meta_question(answer, context):
            continue

        if item.get("id") == "business_question" and _answer_looks_valid_for_item(item, answer):
            question = answer.strip()
            context.clear()
            continue

        replacement_question = None
        llm_changed_context = False
        llm_message = ""
        if llm is not None:
            replacement_question, llm_changed_context, llm_message = _interpret_answer_with_llm(
                llm,
                question,
                context,
                result,
                item,
                answer,
            )

        if replacement_question:
            question = replacement_question
            context.clear()
            continue

        if (llm is None or not llm_changed_context) and _answer_looks_valid_for_item(item, answer):
            replacement_question = _apply_answer_to_context(context, item, answer)
        elif llm_message and not llm_changed_context:
            print(f"Agent1：{llm_message}")
        if replacement_question:
            question = replacement_question
            context.clear()

    return {
        "clarification_result": {
            "status": "blocked",
            "blocking_reason": {
                "source": "local_agent1_test",
                "error": f"超过 {MAX_CONVERSATION_TURNS} 轮仍未完成澄清。",
            },
            "confirmed_scope": {
                "metric": "",
                "metric_definition": "",
                "time_range": "",
                "clinic_scope": [],
                "population": "authorized business population",
                "excluded_scope": [],
            },
        },
        "graph_scope": {},
        "task_contract": {},
    }


def _next_clarification_item(result: dict) -> dict | None:
    questions = result.get("clarification_result", {}).get("clarification_questions", [])
    if not questions:
        return None
    return questions[0]


def _answer_meta_question(message: str, context: dict) -> bool:
    if not _is_graph_meta_question(message):
        return False

    graph_data = context.get("graph_data") or {}
    space_selection = graph_data.get("space_selection") or {}
    candidates = space_selection.get("candidates") or []
    spaces = []
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("space"):
            space = str(candidate["space"])
            if space not in spaces:
                spaces.append(space)

    current_space = graph_data.get("space")
    if current_space and current_space not in spaces:
        spaces.append(str(current_space))

    if spaces:
        print(f"Agent1：当前 Graph API 返回了 {len(spaces)} 个候选图谱 space：{', '.join(spaces)}。")
    else:
        print("Agent1：当前还没有可用的图谱候选信息；等你给出业务问题后，我会先查图谱。")
    print("Agent1：这个问题我不会当成业务指标写进任务合同。我们继续刚才的澄清。")
    return True


def _is_graph_meta_question(message: str) -> bool:
    normalized = message.strip()
    if not normalized:
        return False
    graph_terms = ["图谱", "图数据库", "graph", "space"]
    question_terms = ["几个", "多少", "哪些", "列表", "有什么", "有哪些"]
    return any(term in normalized for term in graph_terms) and any(
        term in normalized for term in question_terms
    )


def _ask_clarification(
    item: dict,
    llm: Agent1LLMClarifier | None = None,
    question: str = "",
    context: dict | None = None,
    result: dict | None = None,
) -> str:
    if llm is not None and result is not None:
        if item.get("options"):
            message = str(item["question"])
        else:
            try:
                message = llm.build_clarification_message(
                    original_question=question,
                    context=context or {},
                    agent1_result=result,
                )
            except Agent1LLMError as exc:
                if not _allow_deterministic_fallback():
                    raise SystemExit(f"Agent1：LLM 澄清失败：{exc}") from exc
                message = str(item["question"])
        print(f"Agent1：{message}")
        return _read_clarification_answer(item.get("options", []))

    print(f"Agent1：{item['question']}")
    return _read_clarification_answer(item.get("options", []))


def _read_clarification_answer(options: list) -> str:
    if options:
        print("Agent1：我从图谱里看到这些可能口径，你可以选编号，也可以直接说你的口径：")
    for index, option in enumerate(options, 1):
        print(f"  {index}. {option}")

    answer = input("你：").strip()
    if answer.isdigit():
        selected_index = int(answer) - 1
        if 0 <= selected_index < len(options):
            return str(options[selected_index])
    return answer


def _interpret_answer_with_llm(
    llm: Agent1LLMClarifier,
    question: str,
    context: dict,
    result: dict,
    item: dict,
    answer: str,
) -> tuple[str | None, bool, str]:
    try:
        turn = llm.interpret_user_reply(
            original_question=question,
            context=context,
            agent1_result=result,
            pending_item=item,
            user_reply=answer,
        )
    except Agent1LLMError as exc:
        if not _allow_deterministic_fallback():
            raise SystemExit(f"Agent1：LLM 解析用户回复失败：{exc}") from exc
        return None, False, ""

    changed_context = _llm_turn_has_context_change(turn)
    replacement_question = _apply_llm_turn_to_context(context, turn)
    assistant_message = str(turn.get("assistant_message") or "").strip()
    return replacement_question, changed_context, assistant_message


def _llm_turn_has_context_change(turn: dict) -> bool:
    updates = turn.get("context_updates") or {}
    if str(turn.get("replacement_question") or "").strip():
        return True
    allowed_fields = {
        "business_question",
        "metric",
        "metric_definition_override",
        "time_range",
        "clinic_scope",
        "output_format",
        "population",
    }
    return any(
        key in allowed_fields and value not in ("", None, [], {})
        for key, value in updates.items()
    )


def _apply_llm_turn_to_context(context: dict, turn: dict) -> str | None:
    updates = turn.get("context_updates") or {}
    replacement_question = str(turn.get("replacement_question") or "").strip()
    business_question = str(updates.get("business_question") or "").strip()
    if replacement_question or business_question:
        return replacement_question or business_question

    if "metric" in updates or "metric_definition_override" in updates:
        metric_value = str(updates.get("metric") or "")
        definition_value = str(updates.get("metric_definition_override") or "")
        metric, definition = _normalize_metric_answer(
            f"{metric_value}：{definition_value}" if definition_value else metric_value
        )
        context["metric"] = metric
        if definition:
            context["metric_definition_override"] = definition

    if "time_range" in updates:
        context["time_range"] = _normalize_time_range_answer(str(updates["time_range"]))

    if "clinic_scope" in updates:
        scope_value = updates["clinic_scope"]
        if isinstance(scope_value, list):
            scope_items = [str(item).strip() for item in scope_value if str(item).strip()]
            context["clinic_scope"] = (
                _normalize_clinic_scope_answer("，".join(scope_items))
                if len(scope_items) == 1
                else scope_items
            )
        else:
            context["clinic_scope"] = _normalize_clinic_scope_answer(str(scope_value))

    if "output_format" in updates:
        context["output_format"] = str(updates["output_format"]).strip() or "Markdown"

    if "population" in updates:
        context["population"] = str(updates["population"]).strip()

    return None


def _apply_answer_to_context(context: dict, item: dict, answer: str) -> str | None:
    question_id = item.get("id", "")
    if question_id == "business_question":
        return answer.strip() or None

    if question_id == "metric_definition":
        metric, definition = _normalize_metric_answer(answer)
        context["metric"] = metric
        if definition:
            context["metric_definition_override"] = definition
        return None

    if question_id == "time_range":
        context["time_range"] = _normalize_time_range_answer(answer)
        return None

    if question_id == "clinic_scope":
        context["clinic_scope"] = _normalize_clinic_scope_answer(answer)
        return None

    context[question_id] = answer
    return None


def _answer_looks_valid_for_item(item: dict, answer: str) -> bool:
    question_id = item.get("id", "")
    normalized = answer.strip()
    if not normalized:
        return False

    if question_id == "time_range":
        if _looks_like_followup_question(normalized):
            return False
        time_markers = [
            "最近",
            "近",
            "今天",
            "昨天",
            "本周",
            "上周",
            "本月",
            "上月",
            "本季度",
            "今年",
            "去年",
            "天",
            "周",
            "月",
            "年",
            "到",
            "至",
            "-",
            "/",
        ]
        return bool(any(marker in normalized for marker in time_markers) or re.search(r"\d", normalized))

    if question_id == "metric_definition":
        return not _looks_like_followup_question(normalized)

    if question_id == "clinic_scope":
        return not _looks_like_followup_question(normalized)

    if question_id == "business_question":
        return bool(normalized)

    return not _looks_like_followup_question(normalized)


def _looks_like_followup_question(text: str) -> bool:
    question_markers = ["?", "？", "为什么", "怎么", "不是", "没有", "没查到", "什么意思"]
    return any(marker in text for marker in question_markers)


def _normalize_metric_answer(answer: str) -> tuple[str, str]:
    if "现金流" in answer or "净现金流" in answer or "流水" in answer or "收款" in answer or "回款" in answer:
        return "cash_flow", "现金流入、现金流出和净现金流"
    if "转化率" in answer:
        return "first_visit_conversion_rate", "患者转化为会员的比例"
    if "转化人数" in answer:
        return "conversion_count", "完成转化的患者数量"
    if "转化路径" in answer:
        return "conversion_path", "患者到会员的转化链路"
    if "关联对象" in answer:
        return "conversion_relationships", "患者、会员、初诊医生、责任医生之间的关系"
    if "复诊" in answer:
        return "revisit_rate", ""
    if "营收" in answer or "收入" in answer:
        return "revenue", ""
    if "预约" in answer:
        return "appointment_count", ""
    if "：" in answer:
        metric, definition = answer.split("：", 1)
        return metric.strip() or answer, definition.strip()
    if ":" in answer:
        metric, definition = answer.split(":", 1)
        return metric.strip() or answer, definition.strip()
    return answer or "first_visit_conversion_rate", ""


def _normalize_time_range_answer(answer: str) -> str:
    if "自定义" in answer:
        custom = input("请输入自定义时间范围，例如 2026-04-01 to 2026-04-30：").strip()
        return Agent1().normalize_time_range(custom) or "custom_range"
    if answer.strip() == "7":
        return Agent1().normalize_time_range("last_7_days")
    if answer.strip() == "30":
        return Agent1().normalize_time_range("last_30_days")
    return Agent1().normalize_time_range(answer) or Agent1().normalize_time_range("last_30_days")


def _normalize_clinic_scope_answer(answer: str) -> list[str]:
    if "指定" in answer:
        raw_ids = input("请输入门店 ID，多个用逗号分隔，例如 SH001,SH002：").strip()
        clinic_ids = [item.strip() for item in raw_ids.replace("，", ",").split(",") if item.strip()]
        return clinic_ids or ["specified_clinics"]
    normalized = Agent1()._normalize_clinic_scope(answer)
    return normalized or ["Shanghai clinics"]


def _print_final_result(result: dict) -> None:
    clarification = result["clarification_result"]
    status = clarification["status"]
    print("\nAgent1 final status:", status)

    if status == "ready":
        print("\nAgent1：澄清完成，下面是给 Agent2 的 task_contract：")
        print(json.dumps(result["task_contract"], ensure_ascii=False, indent=2))
        return

    if status == "blocked":
        print("\nAgent1：当前阻塞原因：")
        print(json.dumps(clarification.get("blocking_reason", {}), ensure_ascii=False, indent=2))
        return

    print("\nAgent1：仍未 ready，完整输出：")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
