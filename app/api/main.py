"""
yuanxi 后端 API 服务
基于 FastAPI，为前端提供工作流调用接口。

启动方式:
  .venv/bin/uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

或从项目根目录:
  .venv/bin/python -m app.api.main
"""

from __future__ import annotations

import os
import sys
import json
import uuid
import asyncio
import traceback
import queue
import threading
from pathlib import Path
from typing import Any, Callable, Generator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
import uvicorn

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="yuanxi API",
    version="0.1.0",
    description="多 Agent 业务分析系统后端 API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 请求/响应模型 ────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户的自然语言问题")
    conversation_id: str | None = Field(None, description="会话 ID，用于多轮对话")


class ClarificationQuestion(BaseModel):
    id: str
    question: str
    type: str
    options: list[str] = []
    required: bool = True
    source: str = "user_input"


class ChartData(BaseModel):
    type: str
    data: list[dict[str, Any]]


class ThinkingStep(BaseModel):
    text: str
    source: str | None = None
    chart: ChartData | None = None


class Attachment(BaseModel):
    id: str
    type: str
    title: str
    size: str = ""
    preview: list[str] = []
    url: str | None = None


class ChatResponse(BaseModel):
    status: str
    conversation_id: str
    text: str = ""
    clarification_questions: list[ClarificationQuestion] = []
    thinking: list[ThinkingStep] = []
    charts: list[ChartData] = []
    attachments: list[Attachment] = []
    raw: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"


# ── 会话存储（内存，单进程） ────────────────────────────────

_conversations: dict[str, dict[str, Any]] = {}


# ── 澄清上下文更新 ──────────────────────────────────────────

def _apply_clarification_answer(
    original_question: str,
    user_context: dict[str, Any],
    last_result: dict[str, Any],
    answer: str,
) -> bool:
    from agents.agent1 import Agent1LLMClarifier

    questions = last_result.get("clarification_result", {}).get(
        "clarification_questions", []
    )
    if not questions:
        return False

    normalized = answer.strip()
    if not normalized:
        return False

    clarifier = Agent1LLMClarifier()
    pending_item = questions[0] if questions else None

    try:
        reply_parsed = clarifier.interpret_user_reply(
            original_question=original_question,
            context=user_context,
            agent1_result=last_result,
            pending_item=pending_item,
            user_reply=normalized,
        )
    except Exception as exc:
        traceback.print_exc()
        return False

    updates = reply_parsed.get("context_updates")
    if not isinstance(updates, dict):
        updates = {}
        
    replacement = reply_parsed.get("replacement_question")

    if updates:
        user_context.update(updates)
        
    if replacement:
        user_context["business_question"] = replacement

    return bool(updates or replacement or reply_parsed.get("answered_meta_question"))


# ── 工作流适配 ────────────────────────────────────────────────

def _run_workflow_safe(question: str) -> dict[str, Any]:
    from integration import run_workflow
    return run_workflow(user_question=question)


def _run_clarification_turn(
    original_question: str,
    user_context: dict[str, Any],
) -> dict[str, Any]:
    from agents.agent1 import run_agent1_clarification
    return run_agent1_clarification(
        original_question,
        user_context=user_context,
    )


def _extract_graph_data(agent1_output: dict[str, Any]) -> Any:
    return agent1_output.get("_raw_graph_data")


def _map_workflow_result(
    workflow_result: dict[str, Any],
    conversation_id: str,
    original_question: str,
    user_context: dict[str, Any],
) -> ChatResponse:
    if workflow_result.get("status") == "needs_clarification":
        agent1_output = workflow_result.get("agent1_output", {})
        clarification = agent1_output.get("clarification_result", {})
        questions_raw = clarification.get("clarification_questions", [])
        understood = clarification.get("understood_intent", "")

        from agents.agent1 import Agent1LLMClarifier
        clarifier = Agent1LLMClarifier()
        try:
            llm_question = clarifier.build_clarification_message(
                original_question=original_question,
                context=user_context,
                agent1_result=agent1_output,
            )
        except Exception as exc:
            traceback.print_exc()
            llm_question = "请继续补充本次业务分析需求。"

        clarification_questions = [
            ClarificationQuestion(
                id=str(uuid.uuid4()),
                question=llm_question,
                type="free_text",
                options=[],
                required=True,
                source="llm_clarifier",
            )
        ]

        return ChatResponse(
            status="needs_clarification",
            conversation_id=conversation_id,
            text=f"我理解您想了解：{understood}\n\n" if understood else "",
            clarification_questions=clarification_questions,
            raw=workflow_result,
        )

    status = workflow_result.get("status", "completed")
    main_report = workflow_result.get("main_report", "")
    agent2_result = workflow_result.get("agent2_result", {})
    process_log = workflow_result.get("process_log", {})

    charts: list[ChartData] = []
    attachments: list[Attachment] = []

    visualization_result = agent2_result.get("visualization_result", {})
    echarts_options = visualization_result.get("charts", [])
    if not echarts_options:
        echarts_options = agent2_result.get("charts", [])

    for opt in echarts_options:
        chart_type = opt.get("type", "bar")
        series = opt.get("series", [])
        if series:
            chart_type = series[0].get("type", chart_type)
            
        data_points = []
        if chart_type == "pie" and series:
            s_data = series[0].get("data", [])
            for item in s_data:
                if isinstance(item, dict):
                    data_points.append({"name": item.get("name", "未知"), "value": item.get("value", 0)})
        elif series:
            x_data = opt.get("xAxis", {}).get("data", [])
            s_data = series[0].get("data", [])
            if x_data and s_data:
                for label, val in zip(x_data, s_data):
                    if isinstance(val, dict):
                        data_points.append({"name": label, "value": val.get("value", 0)})
                    else:
                        data_points.append({"name": label, "value": val})
            elif s_data:
                for i, val in enumerate(s_data):
                    name = str(val.get("name", f"Item {i}")) if isinstance(val, dict) else f"Item {i}"
                    value = val.get("value", 0) if isinstance(val, dict) else val
                    data_points.append({"name": name, "value": value})

        charts.append(ChartData(type=chart_type, data=data_points))

    html_path = agent2_result.get("html_report_path", "")
    if html_path:
        attachments.append(
            Attachment(
                id=f"report-{uuid.uuid4().hex[:8]}",
                type="html_report",
                title="分析报告",
                size="",
                url=f"/api/reports/{Path(html_path).name}" if html_path else None,
            )
        )

    thinking: list[ThinkingStep] = []
    events = process_log.get("events", [])
    for event in events:
        agent = event.get("agent", "")
        message = event.get("message", "")
        if message:
            thinking.append(
                ThinkingStep(text=f"[{agent}] {message}", source=agent)
            )

    return ChatResponse(
        status=status,
        conversation_id=conversation_id,
        text=main_report or "分析完成。",
        thinking=thinking,
        charts=charts,
        attachments=attachments,
        raw=workflow_result,
    )


def _map_agent1_result(
    agent1_output: dict[str, Any],
    conversation_id: str,
    original_question: str,
    user_context: dict[str, Any],
) -> ChatResponse:
    clarification = agent1_output.get("clarification_result", {})
    status = clarification.get("status", "needs_clarification")

    if status == "needs_clarification":
        questions_raw = clarification.get("clarification_questions", [])
        understood = clarification.get("understood_intent", "")

        from agents.agent1 import Agent1LLMClarifier
        clarifier = Agent1LLMClarifier()
        try:
            llm_question = clarifier.build_clarification_message(
                original_question=original_question,
                context=user_context,
                agent1_result=agent1_output,
            )
        except Exception as exc:
            traceback.print_exc()
            llm_question = "请继续补充本次业务分析需求。"

        clarification_questions = [
            ClarificationQuestion(
                id=str(uuid.uuid4()),
                question=llm_question,
                type="free_text",
                options=[],
                required=True,
                source="llm_clarifier",
            )
        ]

        return ChatResponse(
            status="needs_clarification",
            conversation_id=conversation_id,
            text=f"我理解您想了解：{understood}\n\n" if understood else "",
            clarification_questions=clarification_questions,
        )

    if status == "blocked":
        blocking_reason = clarification.get("blocking_reason", {})
        reason_text = blocking_reason.get("error", "需求澄清被阻塞。")
        return ChatResponse(
            status="error",
            conversation_id=conversation_id,
            text=f"抱歉，当前无法处理您的请求：{reason_text}",
        )

    return ChatResponse(
        status="completed",
        conversation_id=conversation_id,
        text="需求已澄清，正在准备分析...",
    )


# ── API 路由 ──────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    conversation_id = request.conversation_id or str(uuid.uuid4())

    session = _conversations.get(conversation_id)

    if session and session.get("status") == "needs_clarification":
        user_context = dict(session.get("user_context", {}))
        last_result = session.get("last_result", {})
        original_question = session.get("original_question", request.question)

        applied = _apply_clarification_answer(original_question, user_context, last_result, request.question)
        if not applied:
            session["status"] = "new"
            session["original_question"] = request.question
            session["user_context"] = {}
            return await chat(ChatRequest(question=request.question, conversation_id=conversation_id))

        agent1_output = _run_clarification_turn(original_question, user_context)
        clarification_status = agent1_output.get("clarification_result", {}).get("status")

        if clarification_status == "needs_clarification":
            session["user_context"] = user_context
            session["last_result"] = agent1_output

            response = _map_agent1_result(agent1_output, conversation_id, original_question, user_context)
            _conversations[conversation_id] = session
            return response

        if clarification_status == "blocked":
            response = _map_agent1_result(agent1_output, conversation_id, original_question, user_context)
            return response

        try:
            from integration import run_workflow
            workflow_result = run_workflow(
                user_question=original_question,
                user_context=user_context,
            )
        except Exception as exc:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"工作流执行失败: {exc}")

        response = _map_workflow_result(workflow_result, conversation_id, original_question, user_context)
        _conversations[conversation_id] = {
            "status": response.status,
            "last_workflow_result": workflow_result,
        }
        return response

    try:
        workflow_result = _run_workflow_safe(request.question)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"工作流执行失败: {exc}")

    response = _map_workflow_result(workflow_result, conversation_id, request.question, {})

    if response.status == "needs_clarification":
        _conversations[conversation_id] = {
            "status": "needs_clarification",
            "original_question": request.question,
            "user_context": {},
            "last_result": workflow_result.get("agent1_output", {}),
        }
    else:
        _conversations[conversation_id] = {
            "status": response.status,
            "last_workflow_result": workflow_result,
        }

    return response


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    conversation_id = request.conversation_id or str(uuid.uuid4())

    async def _sse_generator() -> Generator[str, None, None]:
        event_queue: queue.Queue[tuple[str, dict[str, Any]]] = ()

        def _emit(event_type: str, data: dict[str, Any]) -> None:
            event_queue.put((event_type, data))

        def _workflow_thread() -> None:
            try:
                session = _conversations.get(conversation_id)

                if session and session.get("status") == "needs_clarification":
                    user_context = dict(session.get("user_context", {}))
                    last_result = session.get("last_result", {})
                    original_question = session.get("original_question", request.question)

                    _emit("thinking", {"text": "正在更新需求上下文...", "source": "Agent1"})
                    applied = _apply_clarification_answer(original_question, user_context, last_result, request.question)
                    if not applied:
                        original_question = request.question
                        user_context = {}

                    _emit("thinking", {"text": "正在查询知识图谱并澄清需求...", "source": "Agent1"})
                    agent1_output = _run_clarification_turn(original_question, user_context)
                    clarification_status = agent1_output.get("clarification_result", {}).get("status")

                    if clarification_status == "needs_clarification":
                        _conversations[conversation_id] = {
                            "status": "needs_clarification",
                            "original_question": original_question,
                            "user_context": user_context,
                            "last_result": agent1_output,
                        }
                        _emit("clarification", _build_clarification_payload(agent1_output, conversation_id, original_question, user_context))
                        return

                    if clarification_status == "blocked":
                        _emit("error", {"text": "需求澄清被阻塞。"})
                        return

                    _emit("thinking", {"text": "需求已澄清，正在执行分析...", "source": "Workflow"})
                    from integration import run_workflow
                    workflow_result = run_workflow(
                        user_question=original_question,
                        user_context=user_context,
                        event_callback=lambda etype, agent, msg: _emit(
                            "thinking", {"text": msg, "source": agent}
                        ),
                    )
                    _emit("result", _build_result_payload(workflow_result, conversation_id, original_question, user_context))
                    _conversations[conversation_id] = {
                        "status": workflow_result.get("status", "completed"),
                        "last_workflow_result": workflow_result,
                    }
                    return

                _emit("thinking", {"text": "正在接收您的问题...", "source": "Workflow"})
                from integration import run_workflow
                workflow_result = run_workflow(
                    user_question=request.question,
                    event_callback=lambda etype, agent, msg: _emit(
                        "thinking", {"text": msg, "source": agent}
                    ),
                )

                if workflow_result.get("status") == "needs_clarification":
                    _conversations[conversation_id] = {
                        "status": "needs_clarification",
                        "original_question": request.question,
                        "user_context": {},
                        "last_result": workflow_result.get("agent1_output", {}),
                    }
                    _emit("clarification", _build_clarification_payload(
                        workflow_result.get("agent1_output", {}), conversation_id, request.question, {}
                    ))
                else:
                    _conversations[conversation_id] = {
                        "status": workflow_result.get("status", "completed"),
                        "last_workflow_result": workflow_result,
                    }
                    _emit("result", _build_result_payload(workflow_result, conversation_id, request.question, {}))

            except Exception as exc:
                traceback.print_exc()
                _emit("error", {"text": f"工作流执行失败: {exc}"})

        event_queue = queue.Queue()
        thread = threading.Thread(target=_workflow_thread, daemon=True)
        thread.start()

        while thread.is_alive() or not event_queue.empty():
            try:
                event_type, data = event_queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue

            payload = json.dumps(data, ensure_ascii=False)
            yield f"event: {event_type}\ndata: {payload}\n\n"

            if event_type in ("result", "error", "clarification"):
                yield "event: done\ndata: {}\n\n"
                break

        thread.join(timeout=5)

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _build_clarification_payload(
    agent1_output: dict[str, Any],
    conversation_id: str,
    original_question: str,
    user_context: dict[str, Any],
) -> dict[str, Any]:
    clarification = agent1_output.get("clarification_result", {})
    understood = clarification.get("understood_intent", "")
    questions_raw = clarification.get("clarification_questions", [])

    from agents.agent1 import Agent1LLMClarifier
    clarifier = Agent1LLMClarifier()
    try:
        llm_question = clarifier.build_clarification_message(
            original_question=original_question,
            context=user_context,
            agent1_result=agent1_output,
        )
    except Exception as exc:
        traceback.print_exc()
        llm_question = "请继续补充本次业务分析需求。"

    questions = [
        {
            "id": str(uuid.uuid4()),
            "question": llm_question,
            "type": "free_text",
            "options": [],
            "required": True,
            "source": "llm_clarifier",
        }
    ]

    return {
        "status": "needs_clarification",
        "conversation_id": conversation_id,
        "text": f"我理解您想了解：{understood}\n\n" if understood else "",
        "clarification_questions": questions,
    }


def _build_result_payload(
    workflow_result: dict[str, Any],
    conversation_id: str,
    original_question: str,
    user_context: dict[str, Any],
) -> dict[str, Any]:
    response = _map_workflow_result(workflow_result, conversation_id, original_question, user_context)
    return response.model_dump(exclude_none=True)


@app.get("/api/reports/{filename}")
async def get_report(filename: str, download: bool = False):
    output_dir = Path(_PROJECT_ROOT) / "output" / "report"
    report_path = output_dir / filename
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="报告不存在")
    
    if download:
        return FileResponse(str(report_path), media_type="text/html", filename=filename)
    return FileResponse(str(report_path), media_type="text/html")


if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
