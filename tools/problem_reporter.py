"""
ProblemReporterTool：问题上报工具

【作用】
这个工具是"公共问题收集器"的写入口，供 Agent1（调度精灵）和 Agent2（干活精灵）
在执行任务过程中遇到问题时调用。Agent 把遇到的问题和解决方案记录下来，
存入 JSON 文件，供 Agent3（复盘精灵）事后分析。

【使用场景举例】
- Agent2 取数时发现字段名不存在 → 自动修复后上报
- Agent1 澄清需求时发现口径有歧义 → 记录歧义和澄清方式
- Agent2 分析时发现数据异常 → 记录异常情况和处理方式

【要求】
- 工具 name 使用英文，符合 OpenAI 函数调用协议
- 参数尽量详细，方便 LLM 理解何时该调用

【本轮升级目标】
这一版不再把 LLM 传进来的 agent/stage/severity/problem/solution 原样落库，
而是通过“宽进严出”的方式统一规范：
1. stage：允许常见别名，但最终统一收敛到固定枚举；
2. severity：允许大小写或近义词，但最终只落 high/medium/low；
3. problem/solution：自动补齐统一前缀，减少自由发挥导致的格式漂移；
4. metadata：附带标准化结果，便于 Agent3 后续更稳定地聚合分析。
"""

from typing import Any, ClassVar, Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from tools.problem_store import ProblemStore


class ProblemReporterInput(BaseModel):
    """
    问题上报工具的输入参数定义。

    这些字段描述了 Agent 在任务执行中遇到的问题及其解决方案。
    LLM 会在遇到异常时自动填充这些字段并调用工具。
    """
    agent: str = Field(
        ...,
        description="上报问题的 Agent 名称，例如 'Agent1' 或 'Agent2'",
    )
    stage: str = Field(
        ...,
        description=(
            "问题出现的执行阶段，可选值："
            "clarification（需求澄清）| knowledge（知识获取）| planning（步骤拆解）| "
            "data_fetch（数据取数）| sql_check（SQL校验）| "
            "basic_analysis（基础分析）| advanced_analysis（进阶分析）| "
            "visualization（可视化）| ppt_generation（PPT生成）| review（审核）"
        ),
    )
    problem: str = Field(
        ...,
        description="遇到的问题描述，描述越具体越好，包括上下文信息、字段名、错误信息等",
    )
    solution: str = Field(
        ...,
        description="问题的解决方案，包括具体的修复步骤、替换的字段名、添加的过滤条件等",
    )
    severity: str = Field(
        default="medium",
        description="问题严重程度：high（严重，影响结果准确性）| medium（中等，需要关注）| low（轻微，不影响核心结果）",
    )


class ProblemReporterTool(BaseTool):
    """
    问题上报工具。

    Agent1 和 Agent2 将此工具挂载到 tools 列表中后，
    LLM 在遇到异常或异常情况时会自动判断是否调用此工具上报问题。

    使用方法：
        在 Agent 的 tools 列表中加入 ProblemReporterTool() 即可，
        不需要额外编写调用逻辑，LLM 会自动决定何时调用。
    """
    name: str = "problem_reporter"
    description: str = (
        "任务执行过程中遇到问题时，调用此工具上报问题和解决方案。"
        "包括但不限于：SQL报错、字段不存在、数据异常、口径歧义、"
        "权限不足、缓存失效等。上报后 Agent3 复盘时会读取分析。"
    )
    args_schema: Type[BaseModel] = ProblemReporterInput

    # 固定 stage 枚举。
    # 这里不把自由文本直接当 stage 存储，是因为后续 Agent3 要按 stage 聚类问题。
    # 如果 stage 名称随模型波动成 knowledge_query / graph / fetch_data / sqldebug，
    # 上层聚合会非常痛苦。
    CANONICAL_STAGES: ClassVar[set[str]] = {
        "clarification",
        "knowledge",
        "planning",
        "data_fetch",
        "sql_check",
        "basic_analysis",
        "advanced_analysis",
        "visualization",
        "ppt_generation",
        "review",
    }

    # stage 别名表。
    # 设计成“别名 -> 标准枚举”的字典，而不是写大量 if/else，后续加别名更容易维护。
    STAGE_ALIASES: ClassVar[dict[str, str]] = {
        "clarify": "clarification",
        "clarify_requirement": "clarification",
        "graph": "knowledge",
        "graph_query": "knowledge",
        "knowledge_query": "knowledge",
        "plan": "planning",
        "task_planning": "planning",
        "fetch": "data_fetch",
        "fetch_data": "data_fetch",
        "data": "data_fetch",
        "sql": "sql_check",
        "sql_debug": "sql_check",
        "basic": "basic_analysis",
        "advanced": "advanced_analysis",
        "viz": "visualization",
        "chart": "visualization",
        "html_report": "review",
        "report_generation": "review",
    }

    # severity 的标准映射。
    # 允许模型写 blocking/critical/minor 等近义词，但最终统一映射到 high/medium/low。
    SEVERITY_ALIASES: ClassVar[dict[str, str]] = {
        "critical": "high",
        "blocking": "high",
        "blocker": "high",
        "high": "high",
        "major": "medium",
        "warning": "medium",
        "medium": "medium",
        "normal": "medium",
        "minor": "low",
        "low": "low",
        "info": "low",
    }

    def _run(self, agent: str, stage: str, problem: str, solution: str, severity: str = "medium") -> str:
        """
        执行问题上报。

        参数由 LLM 根据当前上下文自动填充，不需要手动调用。
        上报成功后，数据会被持久化到 data/problem_reports.json 文件中。

        返回：
            上报结果的提示信息，包含问题 ID、阶段和严重程度
        """
        # 确保存储已初始化（如果文件不存在会自动创建）
        ProblemStore.init()

        # 统一规范化输入。
        # 这里的目标不是“严格拒绝一切非标准输入”，而是让模型在有轻微偏差时也能被自动扶正。
        normalized_agent = self._normalize_agent(agent)
        normalized_stage = self._normalize_stage(stage)
        normalized_severity = self._normalize_severity(severity)
        normalized_problem = self._normalize_text(problem, prefix="问题")
        normalized_solution = self._normalize_text(solution, prefix="处理")

        # 构造问题记录。
        # 新增 metadata 字段，专门存工具层做过的标准化信息。
        # 这样不会污染主字段语义，但后续 Agent3 想知道“原始 stage 是什么、是否被纠正过”
        # 时就有据可查。
        record = {
            "agent": normalized_agent,
            "stage": normalized_stage,
            "problem": normalized_problem,
            "solution": normalized_solution,
            "severity": normalized_severity,
            "metadata": {
                "raw_agent": str(agent or "").strip(),
                "raw_stage": str(stage or "").strip(),
                "raw_severity": str(severity or "").strip(),
                "normalized_by": "ProblemReporterTool",
            },
        }

        # 写入 JSON 文件存储
        enriched = ProblemStore.add(record)

        return (
            f"问题上报成功。"
            f"ID: {enriched['id']}, "
            f"阶段: {normalized_stage}, "
            f"严重程度: {normalized_severity}. "
            f"当前累计上报问题数: {ProblemStore.count()}"
        )

    def _normalize_agent(self, agent: str) -> str:
        """
        统一 agent 名称。

        当前只正式支持 Agent1 / Agent2。
        如果未来有 Agent3 或其他 worker 接入，这里可以继续扩展。
        """
        value = str(agent or "").strip()
        lowered = value.lower()
        if lowered in {"agent1", "a1"}:
            return "Agent1"
        if lowered in {"agent2", "a2"}:
            return "Agent2"
        # 对未知 agent 不直接抛错，而是保留原值，避免工具因为命名偏差完全不可用。
        return value or "UnknownAgent"

    def _normalize_stage(self, stage: str) -> str:
        """
        把 stage 统一映射到固定枚举。

        处理策略：
        1. 先做大小写和空白归一化；
        2. 如果是标准值，直接通过；
        3. 如果命中别名表，映射到标准值；
        4. 最后兜底到 review，确保不会把未知阶段散落成大量脏值。
        """
        value = str(stage or "").strip().lower()
        if value in self.CANONICAL_STAGES:
            return value
        if value in self.STAGE_ALIASES:
            return self.STAGE_ALIASES[value]
        return "review"

    def _normalize_severity(self, severity: str) -> str:
        """
        统一严重程度。

        严重程度最终强制收敛为 high / medium / low，
        这样 Agent3 后续统计和前端筛选才不会出现大量近义词分叉。
        """
        value = str(severity or "").strip().lower()
        return self.SEVERITY_ALIASES.get(value, "medium")

    def _normalize_text(self, text: str, prefix: str) -> str:
        """
        统一 problem / solution 文本格式。

        这里不强制模型输出某种复杂模板，但至少补齐统一前缀，
        让落库后的记录在人工阅读和后续解析时更整齐。
        """
        value = " ".join(str(text or "").strip().split())
        if not value:
            # 即使模型忘了填，也尽量避免空字符串直接落库。
            return f"{prefix}: 未提供详细内容。"
        if value.startswith(f"{prefix}:"):
            return value
        return f"{prefix}: {value}"
