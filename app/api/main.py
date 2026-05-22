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
import traceback
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# 将项目根目录加入 Python 搜索路径
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
    allow_credentials=True,
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
    type: str  # "single_select" | "free_text"
    options: list[str] = []
    required: bool = True
    source: str = "user_input"


class ChartData(BaseModel):
    type: str  # "bar" | "line" | "pie"
    data: list[dict[str, Any]]


class ThinkingStep(BaseModel):
    text: str
    source: str | None = None
    chart: ChartData | None = None


class Attachment(BaseModel):
    id: str
    type: str  # "ppt" | "todo" | "html_report"
    title: str
    size: str = ""
    preview: list[str] = []
    url: str | None = None


class ChatResponse(BaseModel):
    status: str  # "needs_clarification" | "completed" | "error"
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


# ── 工作流适配 ────────────────────────────────────────────────

def _run_workflow_safe(question: str) -> dict[str, Any]:
    """调用 integration.run_workflow，捕获所有异常。"""
    from integration import run_workflow

    return run_workflow(user_question=question)


def _map_workflow_result(workflow_result: dict[str, Any], conversation_id: str) -> ChatResponse:
    """将 integration.run_workflow 的输出映射为前端友好的 ChatResponse。"""

    if workflow_result.get("status") == "needs_clarification":
        clarification = workflow_result.get("agent1_output", {}).get(
            "clarification_result", {}
        )
        questions_raw = clarification.get("clarification_questions", [])
        understood = clarification.get("understood_intent", "")

        clarification_questions = []
        for q in questions_raw:
            clarification_questions.append(
                ClarificationQuestion(
                    id=q.get("id", str(uuid.uuid4())),
                    question=q.get("question", ""),
                    type=q.get("type", "free_text"),
                    options=q.get("options", []),
                    required=q.get("required", True),
                    source=q.get("source", "user_input"),
                )
            )

        return ChatResponse(
            status="needs_clarification",
            conversation_id=conversation_id,
            text=f"我理解您想了解：{understood}\n\n为了给您更准确的分析，还需要确认以下信息："
            if understood
            else "为了给您更准确的分析，还需要确认以下信息：",
            clarification_questions=clarification_questions,
            raw=workflow_result,
        )

    # completed / approved / other terminal status
    status = workflow_result.get("status", "completed")
    main_report = workflow_result.get("main_report", "")
    agent2_result = workflow_result.get("agent2_result", {})
    process_log = workflow_result.get("process_log", {})

    # 从 agent2_result 中提取图表和附件
    charts: list[ChartData] = []
    attachments: list[Attachment] = []

    # 提取 ECharts option 图表
    echarts_options = agent2_result.get("charts", [])
    for i, opt in enumerate(echarts_options):
        chart_type = "bar"
        series = opt.get("series", [])
        if series:
            s = series[0]
            chart_type = s.get("type", "bar")
        data_points = []
        if series:
            x_data = opt.get("xAxis", {}).get("data", [])
            s_data = series[0].get("data", [])
            for label, val in zip(x_data, s_data):
                if isinstance(val, dict):
                    data_points.append({"name": label, "value": val.get("value", 0)})
                else:
                    data_points.append({"name": label, "value": val})
        charts.append(ChartData(type=chart_type, data=data_points))

    # 提取 HTML 报告
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

    # 构建思考步骤（从 process_log 提取关键事件）
    thinking: list[ThinkingStep] = []
    events = process_log.get("events", [])
    for event in events:
        agent = event.get("agent", "")
        task = event.get("task", "")
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


# ── API 路由 ──────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    conversation_id = request.conversation_id or str(uuid.uuid4())

    try:
        workflow_result = _run_workflow_safe(request.question)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"工作流执行失败: {exc}",
        )

    response = _map_workflow_result(workflow_result, conversation_id)

    # 保存会话上下文
    _conversations[conversation_id] = {
        "last_workflow_result": workflow_result,
    }

    return response


@app.get("/api/reports/{filename}")
async def get_report(filename: str):
    """提供生成的 HTML 报告文件。"""
    from fastapi.responses import FileResponse

    output_dir = Path(_PROJECT_ROOT) / "output"
    report_path = output_dir / filename
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="报告不存在")
    return FileResponse(str(report_path), media_type="text/html")


# ── 入口 ──────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
