"""
Agent2：数据处理干活精灵
负责：知识图谱查询、数据取数、自动 Debug、缓存、基础/进阶分析、可视化、PPT 生成
要求：所有工具 name 必须为英文，符合 OpenAI 函数调用协议
"""

import os
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from dotenv import load_dotenv

from tools.kg_query import NebulaGraphQueryTool


# 加载环境变量（DeepSeek 密钥已配置为 OpenAI 兼容模式）
load_dotenv()

# ============================================================
# 工具 1：知识图谱查询
# ============================================================
class KnowledgeGraphQueryTool(BaseTool):
    name: str = "knowledge_graph_query"
    description: str = "Query NebulaGraph for entity relationships (clinics, patients, appointments, bills) and return relevant associations."

    def _run(self, question: str) -> str:
        # 模拟：实际可接入 nebula3-python 执行 nGQL
        return (
            "Knowledge graph result: "
            "Clinic[SH001] -> treats -> Patient[PT12345]; "
            "Patient[PT12345] -> has -> Appointment[AP20260401]; "
            "Appointment[AP20260401] -> generates -> Bill[BL789]. "
            "Scope limited to Shanghai clinics."
        )

# ============================================================
# 工具 2：业务数据取数
# ============================================================
class DataFetchTool(BaseTool):
    name: str = "data_fetch"
    description: str = "Fetch data from business wide tables safely. Input a query/SQL, return row count and fields."

    def _run(self, query: str) -> str:
        # 模拟：实际可连接数据库执行 SQL
        return (
            "Data fetched successfully. 1280 rows, fields: [clinic_id, patient_id, doctor_id, "
            "first_visit_date, is_arrived, amount]. Patient names and phones have been masked."
        )

# ============================================================
# 工具 3：SQL 自动修复
# ============================================================
class SQLDebugTool(BaseTool):
    name: str = "sql_debug"
    description: str = "Auto-detect and fix SQL syntax errors, return corrected SQL with comments."

    def _run(self, sql: str) -> str:
        # 模拟修复逻辑
        if "form" in sql.lower() and "from" not in sql.lower():
            fixed = sql.replace("form", "from")
            return f"SQL error fixed: {fixed}"
        return f"SQL is valid: {sql}"

# ============================================================
# 工具 4：数据缓存管理
# ============================================================
class CacheManagerTool(BaseTool):
    name: str = "cache_manager"
    description: str = "Cache intermediate data with a TTL. Provide data_id and return cache status."

    def _run(self, data_id: str) -> str:
        # 模拟：实际可用 Redis 或文件缓存
        return f"Data '{data_id}' cached successfully. TTL: 1 hour. Subsequent identical requests will use cache."

# ============================================================
# 工具 5：基础统计分析
# ============================================================
class BasicAnalysisTool(BaseTool):
    name: str = "basic_analysis"
    description: str = "Perform descriptive statistics, dimensional breakdown, and YoY/MoM comparisons."

    def _run(self, requirement: str) -> str:
        return (
            "Basic analysis results:\n"
            "- Overall first-visit conversion rate: 45.2%\n"
            "- By clinic: SH001=48.1%, SH002=42.3%\n"
            "- By doctor: Dr.Zhang=50.5%, Dr.Li=40.2%\n"
            "- YoY (April 2026 vs April 2025): increased by 3.1 percentage points."
        )

# ============================================================
# 工具 6：进阶分析
# ============================================================
class AdvancedAnalysisTool(BaseTool):
    name: str = "advanced_analysis"
    description: str = "Execute advanced analytics: clustering, regression, causal inference, time series, etc."

    def _run(self, method: str) -> str:
        if "clustering" in method.lower():
            return "Clustering result: 3 patient segments identified; high-conversion-potential group accounts for 22%."
        elif "regression" in method.lower():
            return "Regression result: Key factors affecting conversion rate are consultation duration and doctor seniority (p<0.05)."
        else:
            return f"Advanced analysis '{method}' completed."

# ============================================================
# 工具 7：可视化图表生成
# ============================================================
class VisualizationTool(BaseTool):
    name: str = "visualization"
    description: str = "Generate charts (bar, line, pie) and return file paths."

    def _run(self, chart_type: str) -> str:
        return f"Chart generated: ./output/chart_{chart_type}.png"

# ============================================================
# 工具 8：PPT 自动生成
# ============================================================
class PPTGeneratorTool(BaseTool):
    name: str = "ppt_generator"
    description: str = "Compile analysis conclusions and charts into a standard PPT, return file path."

    def _run(self, content: str) -> str:
        return "PPT generated: ./output/analysis_report.pptx"

# ============================================================
# 组装 Agent2
# ============================================================
data_agent = Agent(
    role="业务数据取数与分析专家",
    goal=(
        "在安全边界内完成知识图谱查询、业务数据取数、自动 debug、缓存复用，"
        "并执行基础与进阶分析，最终输出可视化图表及标准化 PPT。"
    ),
    backstory=(
        "你是口腔儿牙业务数据执行分析师，精通领健数据源、业务宽表、NebulaGraph 知识图谱。"
        "你能自动生成并修复 SQL，善于描述性统计、多维度拆解、趋势归因、机器学习建模。"
        "你做事严谨，所有 SQL 都留注释，中间数据会自动缓存，图表和 PPT 输出专业规范。"
    ),
    verbose=True,
    allow_delegation=False,
    tools=[
        KnowledgeGraphQueryTool(),
        DataFetchTool(),
        SQLDebugTool(),
        CacheManagerTool(),
        BasicAnalysisTool(),
        AdvancedAnalysisTool(),
        VisualizationTool(),
        PPTGeneratorTool(),
    ],
)

# ============================================================
# 模拟调度精灵下达的任务（用于独立测试 Agent2）
# ============================================================
test_task = Task(
    description=(
        "调度精灵已为你澄清需求并划定安全边界，请严格按以下步骤执行：\n"
        "1. 使用 knowledge_graph_query 工具，确认上海门店（SH001, SH002）与患者、预约、账单的实体关系。\n"
        "2. 使用 data_fetch 工具，获取 2026年4月这些门店的初诊患者数据，要求自动脱敏。\n"
        "3. 检查取数 SQL 是否正确，若有错误请使用 sql_debug 工具自动修复。\n"
        "4. 使用 cache_manager 工具，将取到的数据缓存，避免重复查询。\n"
        "5. 使用 basic_analysis 工具，执行基础统计分析：计算总体转化率、按门店和医生维度下钻，并进行同比分析。\n"
        "6. 使用 advanced_analysis 工具，对影响转化率的因素进行回归分析。\n"
        "7. 使用 visualization 工具，生成转化率柱状图和趋势折线图。\n"
        "8. 使用 ppt_generator 工具，将所有分析结论和图表整合为一份 PPT，输出文件路径。\n"
        "最后，用 Markdown 格式汇总所有关键发现和输出文件路径。"
    ),
    expected_output=(
        "一份包含数据概况、分析结论、图表路径、PPT 路径的完整 Markdown 报告。"
    ),
    agent=data_agent,
)

# ============================================================
# 独立运行 Agent2 的 Crew
# ============================================================
if __name__ == "__main__":
    crew = Crew(
        agents=[data_agent],
        tasks=[test_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    print("\n\n" + "=" * 60)
    print("🎯 Agent2 最终输出：")
    print(result)