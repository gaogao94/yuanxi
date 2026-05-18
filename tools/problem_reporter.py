"""
ProblemReporterTool：问题上报工具
供 Agent1（调度精灵）和 Agent2（干活精灵）在遇到问题时调用，
将问题与解决方案写入共享的 JSON 文件存储，供 Agent3 复盘分析。
"""

from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from tools.problem_store import ProblemStore


class ProblemReporterInput(BaseModel):
    agent: str = Field(
        ...,
        description="Who is reporting this problem, e.g. 'Agent1' or 'Agent2'",
    )
    stage: str = Field(
        ...,
        description=(
            "The stage where the problem occurred. Options: "
            "clarification | knowledge | planning | data_fetch | sql_check | "
            "basic_analysis | advanced_analysis | visualization | ppt_generation | review"
        ),
    )
    problem: str = Field(
        ..., description="Description of the problem encountered, be specific and include context"
    )
    solution: str = Field(
        ..., description="How the problem was solved, include specific steps if applicable"
    )
    severity: str = Field(
        default="medium",
        description="Severity level: high | medium | low",
    )


class ProblemReporterTool(BaseTool):
    name: str = "problem_reporter"
    description: str = (
        "Report any problem encountered during task execution, along with the solution. "
        "This helps improve the system for future tasks. Call this whenever you encounter "
        "an error, ambiguity, data issue, or any unexpected situation."
    )
    args_schema: Type[BaseModel] = ProblemReporterInput

    def _run(self, agent: str, stage: str, problem: str, solution: str, severity: str = "medium") -> str:
        # 确保存储已初始化
        ProblemStore.init()

        record = {
            "agent": agent,
            "stage": stage,
            "problem": problem,
            "solution": solution,
            "severity": severity,
        }

        enriched = ProblemStore.add(record)
        return (
            f"Problem reported successfully. "
            f"ID: {enriched['id']}, "
            f"Stage: {stage}, "
            f"Severity: {severity}. "
            f"Total problems recorded: {ProblemStore.count()}"
        )
