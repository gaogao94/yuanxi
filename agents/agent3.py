"""
Agent3：洞察优化进阶精灵（复盘精灵）
负责：全流程复盘审计、问题分析、图谱补缺、流程优化、经验沉淀
方式：旁路并行，不阻塞主链路
"""

import sys
import os
from pathlib import Path

# 设置标准输出编码为 UTF-8，解决 Windows GBK 编码问题
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 将项目根目录加入 Python 搜索路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from dotenv import load_dotenv

from tools.problem_collector import ProblemCollectorReader

load_dotenv()


# ============================================================
# 工具 1：问题收集器读取（读取 Agent1/Agent2 上报的问题）
# ============================================================
# 已在 tools/problem_collector.py 中实现，直接导入使用

# ============================================================
# 工具 2：步骤拆解合理性评估
# ============================================================
class StepDecompositionEvaluator(BaseTool):
    name: str = "step_decomposition_evaluator"
    description: str = (
        "Evaluate the reasonableness of the task step decomposition. "
        "Check for redundant steps, missing critical steps, unreasonable ordering, "
        "and suggest improvements. Provide the task_contract or step list as input."
    )

    def _run(self, step_list: str) -> str:
        # 模拟评估逻辑
        findings = []
        suggestions = []

        if "data_fetch" in step_list and "sql_check" not in step_list:
            findings.append("Missing SQL validation step after data fetch")
            suggestions.append("Add a sql_check step after data_fetch to verify query correctness")

        if "advanced_analysis" in step_list and "basic_analysis" not in step_list:
            findings.append("Advanced analysis included without basic analysis prerequisite")
            suggestions.append("Ensure basic analysis runs before advanced analysis")

        if not findings:
            return (
                "Step decomposition evaluation passed.\n"
                "All steps appear logically ordered. No redundant or missing steps detected."
            )

        return (
            f"Found {len(findings)} issue(s):\n"
            + "\n".join(f"- {f}" for f in findings)
            + "\n\nSuggestions:\n"
            + "\n".join(f"- {s}" for s in suggestions)
        )


# ============================================================
# 工具 3：业务知识图谱缺陷诊断 & 关系缺失识别
# ============================================================
class GraphGapDetector(BaseTool):
    name: str = "graph_gap_detector"
    description: str = (
        "Analyze the knowledge graph usage in this task and identify missing entities, "
        "relationships, or incomplete data coverage. Suggest improvements for the graph."
    )

    def _run(self, graph_scope_summary: str) -> str:
        # 模拟图谱诊断逻辑
        suggestions = [
            {
                "missing": "Channel entity -> affects -> ConversionRate metric relationship",
                "reason": "Analysis showed channel source impacts conversion, but graph lacks this relation",
                "example_query": "MATCH (c:Channel)-[r:affects]->(m:Metric) WHERE m.name='conversion_rate'",
            },
            {
                "missing": "Doctor entity -> seniority_level property",
                "reason": "Doctor seniority found to be a key conversion factor, but not stored in graph",
                "example_query": "MATCH (d:Doctor) RETURN d.name, d.seniority_level",
            },
        ]

        report = "## Knowledge Graph Gap Analysis\n\n"
        report += "### Detected Gaps:\n\n"
        for s in suggestions:
            report += f"- **Missing**: {s['missing']}\n"
            report += f"  - **Why needed**: {s['reason']}\n"
            report += f"  - **Example query**: `{s['example_query']}`\n\n"

        report += "### Recommendation:\n"
        report += "1. Add Channel entity and its relationship to metrics\n"
        report += "2. Add seniority_level property to Doctor entity\n"
        report += "3. Consider adding a ClinicPerformance view entity for aggregated KPIs\n"

        return report


# ============================================================
# 工具 4：流程优化建议生成
# ============================================================
class ProcessOptimizer(BaseTool):
    name: str = "process_optimizer"
    description: str = (
        "Analyze the execution process and suggest optimizations. "
        "Identify redundant steps, bottlenecks, and opportunities for templating. "
        "Provide the process log summary as input."
    )

    def _run(self, process_summary: str) -> str:
        # 模拟流程优化逻辑
        return (
            "## Process Optimization Suggestions\n\n"
            "### Bottlenecks Identified:\n"
            "1. **SQL generation step**: Can be templated for recurring query patterns\n"
            "2. **Cache check before fetch**: Can be combined into a single 'fetch-or-cache' step\n\n"
            "### Suggested Improvements:\n"
            "- Create query templates for common patterns (clinic monthly, doctor performance)\n"
            "- Merge cache_manager with data_fetch to reduce tool calls\n"
            "- Add parallel execution for independent chart generation steps\n\n"
            "### Estimated Impact:\n"
            "- Potential 20-30% reduction in total execution time\n"
            "- Fewer tool calls, lower API costs"
        )


# ============================================================
# 工具 5：经验沉淀 & 可复用规则整理
# ============================================================
class InsightRefiner(BaseTool):
    name: str = "insight_refiner"
    description: str = (
        "Summarize reusable lessons learned from this task execution. "
        "Extract standard metrics definitions, common pitfalls, and effective analysis patterns "
        "that can be applied to future tasks."
    )

    def _run(self, task_summary: str) -> str:
        # 模拟经验沉淀逻辑
        return (
            "## Reusable Knowledge Base Entries\n\n"
            "### Standard Metric Definitions:\n"
            "- **First-visit conversion rate** = patients with bill / total first-visit patients\n"
            "  - Time range: monthly\n"
            "  - Data source: dwd_patient_visit table\n\n"
            "### Common Pitfalls:\n"
            "1. Field name differences between clinics (e.g. clinic_name vs store_name)\n"
            "2. Missing filter for is_first_visit=1 when analyzing new patients\n"
            "3. Patient name/phone must be masked before output\n\n"
            "### Effective Analysis Patterns:\n"
            "- Always start with basic statistics before advanced analysis\n"
            "- Dimension drill-down should follow: overall -> clinic -> doctor\n"
            "- Cache intermediate results to enable quick iteration\n\n"
            "### Action Items for Next Sprint:\n"
            "- Add field mapping dictionary to handle naming inconsistencies\n"
            "- Template common SQL patterns to reduce errors\n"
            "- Update knowledge graph with Channel entity"
        )


# ============================================================
# 组装 Agent3
# ============================================================
review_agent = Agent(
    role="全流程复盘审计专家、业务体系优化顾问",
    goal=(
        "独立对需求澄清、知识获取、任务拆解、数据取数、分析输出全流程进行批判性复盘；"
        "发现流程漏洞、口径不合理点、取数逻辑缺陷、业务知识图谱实体关系不完善之处；"
        "给出可落地的流程优化、图谱补充、分析方向拓展建议；"
        "沉淀单次任务经验，反哺业务体系与 Agent 能力持续进化。"
    ),
    backstory=(
        "你具备全局审视思维，不负责直接业务执行，专注于事后复盘、流程审计、体系优化与长期进化；"
        "熟悉儿牙业务全流程逻辑、指标口径规则、知识图谱设计思路、取数分析常见短板与坑点；"
        "善于跳出单次任务视角，发现隐性逻辑问题、冗余步骤、口径歧义盲区、图谱缺失关联关系；"
        "能够给出具体可落地的优化建议、图谱补充方向、分析维度拓展思路，并沉淀为可复用的业务经验。"
    ),
    verbose=True,
    allow_delegation=False,
    tools=[
        ProblemCollectorReader(),     # 读取 Agent1/2 上报的问题
        StepDecompositionEvaluator(), # 评估步骤拆解合理性
        GraphGapDetector(),           # 图谱缺陷诊断
        ProcessOptimizer(),           # 流程优化建议
        InsightRefiner(),             # 经验沉淀 & 维度拓展
    ],
)

# ============================================================
# 复盘任务
# ============================================================
review_task = Task(
    description=(
        "请对本次任务执行结果进行全面复盘分析：\n\n"
        "1. 使用 problem_collector_reader 工具（action='get_all'）读取 Agent1/Agent2 在本轮执行中上报的所有问题记录。\n"
        "2. 使用 step_decomposition_evaluator 工具，评估本轮任务步骤拆解的合理性。\n"
        "3. 使用 graph_gap_detector 工具，分析知识图谱是否存在实体或关系缺失。\n"
        "4. 使用 process_optimizer 工具，总结执行过程中的可优化环节。\n"
        "5. 使用 insight_refiner 工具，沉淀本轮可复用的业务经验和规则。\n\n"
        "最后，将以上分析结果整合为一份完整的复盘报告。"
    ),
    expected_output=(
        "一份结构化的复盘报告，包含以下内容：\n"
        "1. 【问题汇总】本轮遇到的问题、解决方案、严重程度分布\n"
        "2. 【步骤拆解评价】步骤是否合理、有无缺失或冗余\n"
        "3. 【图谱补缺建议】知识图谱需要补充的实体或关系\n"
        "4. 【流程优化建议】可简化的环节、可模板化的步骤\n"
        "5. 【经验沉淀】可复用的标准口径、踩坑记录、分析模式\n"
        "6. 【执行摘要】一句话总结本轮执行质量\n"
        "格式：Markdown"
    ),
    agent=review_agent,
)

# ============================================================
# 独立运行 Agent3 的 Crew
# ============================================================
if __name__ == "__main__":
    # 先初始化问题存储
    from tools.problem_store import ProblemStore
    ProblemStore.init()

    crew = Crew(
        agents=[review_agent],
        tasks=[review_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    print("\n\n" + "=" * 60)
    print("[Agent3] Review Report:")
    print(result)
