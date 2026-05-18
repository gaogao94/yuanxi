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
"""

from typing import Type
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

        # 构造问题记录
        record = {
            "agent": agent,
            "stage": stage,
            "problem": problem,
            "solution": solution,
            "severity": severity,
        }

        # 写入 JSON 文件存储
        enriched = ProblemStore.add(record)

        return (
            f"问题上报成功。"
            f"ID: {enriched['id']}, "
            f"阶段: {stage}, "
            f"严重程度: {severity}. "
            f"当前累计上报问题数: {ProblemStore.count()}"
        )
