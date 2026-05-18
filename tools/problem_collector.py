"""
ProblemCollectorReader：问题收集读取工具
供 Agent3（洞察优化进阶精灵）读取 Agent1/Agent2 上报的问题记录，
作为复盘分析的依据。
"""

from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from tools.problem_store import ProblemStore


class ProblemCollectorInput(BaseModel):
    action: str = Field(
        ...,
        description=(
            "What to do: 'get_all' to retrieve all problems, "
            "'count' to get the total count, "
            "'filter' to filter by specific criteria"
        ),
    )
    filter_agent: Optional[str] = Field(
        default=None,
        description="Filter by agent name, e.g. 'Agent1' or 'Agent2'",
    )
    filter_severity: Optional[str] = Field(
        default=None,
        description="Filter by severity: high | medium | low",
    )
    filter_stage: Optional[str] = Field(
        default=None,
        description="Filter by stage, e.g. 'data_fetch' or 'clarification'",
    )


class ProblemCollectorReader(BaseTool):
    name: str = "problem_collector_reader"
    description: str = (
        "Read and analyze problems reported by Agent1 (Scheduler) and Agent2 (Data Agent) "
        "during task execution. Can retrieve all records, count them, or filter by "
        "agent, severity, or stage. Use this to gather review material."
    )
    args_schema: Type[BaseModel] = ProblemCollectorInput

    def _run(
        self,
        action: str,
        filter_agent: Optional[str] = None,
        filter_severity: Optional[str] = None,
        filter_stage: Optional[str] = None,
    ) -> str:
        ProblemStore.init()

        if action == "count":
            total = ProblemStore.count()
            filtered = total
            if filter_agent or filter_severity or filter_stage:
                filtered = len(self._do_filter(filter_agent, filter_severity, filter_stage))
            return (
                f"Total problems: {total}. "
                f"Matching current filter: {filtered}."
            )

        elif action == "get_all":
            if filter_agent or filter_severity or filter_stage:
                records = self._do_filter(filter_agent, filter_severity, filter_stage)
            else:
                records = ProblemStore.get_all()

            if not records:
                return "No problem records found."

            summary = (
                f"Found {len(records)} problem record(s):\n\n"
                + "\n---\n".join(self._format_record(r) for r in records)
            )
            return summary

        else:
            return f"Unknown action: {action}. Supported: get_all, count, filter."

    # ── 内部辅助 ────────────────────────────────────────────

    def _do_filter(self, agent, severity, stage) -> list:
        kwargs = {}
        if agent:
            kwargs["agent"] = agent
        if severity:
            kwargs["severity"] = severity
        if stage:
            kwargs["stage"] = stage
        return ProblemStore.filter(**kwargs)

    def _format_record(self, r: dict) -> str:
        return (
            f"**ID**: {r.get('id', 'N/A')}\n"
            f"**Agent**: {r.get('agent', 'N/A')}\n"
            f"**Stage**: {r.get('stage', 'N/A')}\n"
            f"**Severity**: {r.get('severity', 'N/A')}\n"
            f"**Problem**: {r.get('problem', 'N/A')}\n"
            f"**Solution**: {r.get('solution', 'N/A')}\n"
            f"**Time**: {r.get('timestamp', 'N/A')}"
        )
