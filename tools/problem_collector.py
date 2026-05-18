"""
ProblemCollectorReader：问题收集读取工具

【作用】
这个工具是"公共问题收集器"的读入口，供 Agent3（洞察优化进阶精灵）使用。
Agent3 通过这个工具读取 Agent1 和 Agent2 在任务执行过程中上报的
所有问题记录，作为复盘分析的原始素材。

【与 ProblemReporterTool 的关系】
- ProblemReporterTool：写工具（给 Agent1/Agent2 用）→ 写入问题
- ProblemCollectorReader：读工具（给 Agent3 用）→ 读取问题
- 底层共用同一个 ProblemStore（JSON 文件存储）

【使用方式】
Agent3 在复盘任务中调用此工具，可以：
1. get_all：获取全部问题记录
2. count：统计问题数量
3. filter：按 Agent、严重程度、阶段等条件过滤
"""

from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from tools.problem_store import ProblemStore


class ProblemCollectorInput(BaseModel):
    """
    问题读取工具的输入参数定义。

    action 指定操作类型，filter_* 参数用于筛选需要查看的问题。
    """
    action: str = Field(
        ...,
        description=(
            "操作类型："
            "'get_all' 获取全部问题记录，"
            "'count' 统计问题总数，"
            "'filter' 按条件过滤查询"
        ),
    )
    filter_agent: Optional[str] = Field(
        default=None,
        description="按 Agent 名称过滤，例如 'Agent1' 或 'Agent2'",
    )
    filter_severity: Optional[str] = Field(
        default=None,
        description="按严重程度过滤：high（严重）| medium（中等）| low（轻微）",
    )
    filter_stage: Optional[str] = Field(
        default=None,
        description="按执行阶段过滤，例如 'data_fetch'（数据取数）或 'clarification'（需求澄清）",
    )


class ProblemCollectorReader(BaseTool):
    """
    问题收集读取工具。

    Agent3 使用此工具读取 Agent1/Agent2 上报的问题记录。
    支持获取全部记录、按条件过滤、统计数量等操作。
    返回的结果是格式化后的 Markdown 文本，方便 Agent3 直接阅读和分析。
    """
    name: str = "problem_collector_reader"
    description: str = (
        "读取 Agent1（调度精灵）和 Agent2（干活精灵）在任务执行中上报的问题记录。"
        "可以获取全部记录、统计数量、或按上报Agent、严重程度、执行阶段进行过滤。"
        "用于复盘分析时获取原始素材。"
    )
    args_schema: Type[BaseModel] = ProblemCollectorInput

    def _run(
        self,
        action: str,
        filter_agent: Optional[str] = None,
        filter_severity: Optional[str] = None,
        filter_stage: Optional[str] = None,
    ) -> str:
        """
        执行问题读取操作。

        根据 action 参数执行不同的操作：
        - get_all：返回所有（或过滤后的）问题记录
        - count：返回问题总数和过滤后的数量
        - filter：同 get_all，按条件过滤

        参数：
            action: 操作类型
            filter_agent: 按 Agent 名称过滤
            filter_severity: 按严重程度过滤
            filter_stage: 按执行阶段过滤

        返回：
            格式化的结果文本（Markdown 格式）
        """
        # 确保存储已初始化
        ProblemStore.init()

        if action == "count":
            # 统计问题数量（总数量和过滤后的数量）
            total = ProblemStore.count()
            filtered = total
            if filter_agent or filter_severity or filter_stage:
                filtered = len(self._do_filter(filter_agent, filter_severity, filter_stage))
            return (
                f"问题总数: {total}. "
                f"当前筛选条件匹配: {filtered} 条."
            )

        elif action in ("get_all", "filter"):
            # 获取问题记录（可选过滤）
            if filter_agent or filter_severity or filter_stage:
                records = self._do_filter(filter_agent, filter_severity, filter_stage)
            else:
                records = ProblemStore.get_all()

            if not records:
                return "暂无问题记录。"

            # 格式化为可读的 Markdown 文本
            summary = (
                f"共找到 {len(records)} 条问题记录:\n\n"
                + "\n---\n".join(self._format_record(r) for r in records)
            )
            return summary

        else:
            return f"未知操作: {action}。支持的操作: get_all, count, filter。"

    # ── 内部辅助方法 ──────────────────────────────────────────

    def _do_filter(self, agent, severity, stage) -> list:
        """
        根据条件过滤问题记录（内部方法）。

        只过滤非空的筛选条件，忽略 None 值。
        """
        kwargs = {}
        if agent:
            kwargs["agent"] = agent
        if severity:
            kwargs["severity"] = severity
        if stage:
            kwargs["stage"] = stage
        return ProblemStore.filter(**kwargs)

    def _format_record(self, r: dict) -> str:
        """
        将单条问题记录格式化为可读文本（内部方法）。

        每条记录包含：ID、上报Agent、阶段、严重程度、问题描述、解决方案、时间戳。
        使用 Markdown 格式以便 Agent3 直接阅读。
        """
        return (
            f"**ID**: {r.get('id', '未知')}\n"
            f"**上报Agent**: {r.get('agent', '未知')}\n"
            f"**执行阶段**: {r.get('stage', '未知')}\n"
            f"**严重程度**: {r.get('severity', '未知')}\n"
            f"**问题描述**: {r.get('problem', '未知')}\n"
            f"**解决方案**: {r.get('solution', '未知')}\n"
            f"**上报时间**: {r.get('timestamp', '未知')}"
        )
