"""
Agent2：数据处理干活精灵
负责：知识图谱查询、数据取数、自动 Debug、基础/进阶分析、可视化、HTML 报告生成
"""

import os
import sys
from pathlib import Path

# 设置标准输出编码为 UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 将项目根目录加入 Python 搜索路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Task, Crew, Process, LLM
from dotenv import load_dotenv

from tools.nebula_graph_query import NebulaGraphQueryTool
from tools.data_fetch import DataFetchTool
from tools.sql_debug import SQLDebugTool
from tools.basic_analysis import BasicAnalysisTool
from tools.advanced_analysis import AdvancedAnalysisTool
from tools.visualization import VisualizationTool
from tools.html_report import HtmlReportGeneratorTool
from tools.problem_reporter import ProblemReporterTool

load_dotenv()

# DeepSeek 需走 OpenAI 兼容 function calling；使用 deepseek/ 前缀启用 CrewAI 原生适配
llm = LLM(
    model=os.getenv("OPENAI_MODEL_NAME", "deepseek-chat"),
    base_url=os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.1,
)

# ============================================================
# 组装 Agent2
# ============================================================
data_agent = Agent(
    role="业务数据取数与分析专家",
    goal=(
        "在安全边界内完成知识图谱查询、业务数据取数、自动 debug、"
        "基础与进阶分析，最终输出可视化图表及标准化 HTML 报告。"
    ),
    backstory=(
        "你是口腔儿牙业务数据执行分析师，精通领健数据源、业务宽表、NebulaGraph 知识图谱。"
        "你能自动生成并修复 SQL，善于描述性统计、多维度拆解、趋势归因、机器学习建模。"
        "你做事严谨，所有 SQL 都留注释，图表和 HTML 报告输出专业规范。"
        "必须通过平台提供的工具接口调用工具，禁止在回复正文中输出 DSML/XML 形式的伪工具调用。"
        "执行任一步骤时若遇到 SQL 报错、字段不存在、图谱查无结果、数据异常、口径歧义、"
        "工具返回失败等可恢复或需记录的问题，必须先调用 problem_reporter 上报"
        "（agent 固定填 Agent2，stage 填当前阶段，problem 写清上下文，solution 写已采取或建议的修复），"
        "再尝试修复并继续；严重阻塞（high）与已自行解决（low/medium）均需上报。"
    ),
    llm=llm,
    verbose=True,
    allow_delegation=False,
    max_iter=30,
    tools=[
        NebulaGraphQueryTool(),
        DataFetchTool(),
        SQLDebugTool(),
        BasicAnalysisTool(),
        AdvancedAnalysisTool(),
        VisualizationTool(),
        HtmlReportGeneratorTool(),
        ProblemReporterTool(),
    ],
)

# ============================================================
# 测试任务
# ============================================================
test_task = Task(
    description=(
        "【分析目标】查询本月徐汇门店的患者就诊情况，形成可汇报的分析结论。\n"
        "【时间范围】当前自然月（2026年5月1日至今）。\n"
        "【门店范围】徐汇门店（图谱或宽表中名称/编码含「徐汇」的门诊）。\n"
        "\n"
        "请严格按以下步骤执行，最终输出 HTML 报告：\n"
        "1. 使用 nebula_graph_query：在知识图谱中定位徐汇门店，并查询其与患者、就诊、预约等关系"
        "（可用 tag=门诊、edge_type=就诊，或 nGQL 按门店名称筛选）。\n"
        "2. 使用 data_fetch：从业务宽表取数，获取徐汇门店本月就诊记录"
        "（含就诊日期、患者标识、医生、就诊类型等；仅 SELECT，敏感字段自动脱敏）。\n"
        "3. 使用 sql_debug：检查并修复上一步的取数 SQL，确保语法正确、时间/门店条件准确。\n"
        "4. 使用 basic_analysis：统计本月就诊人次、初复诊占比、按医生/就诊类型维度拆解，"
        "并与上月或去年同期做简要对比（若数据不足则说明）。\n"
        "5. 使用 advanced_analysis：对就诊量波动或复诊率等因素做回归/趋势类分析（按数据情况选择方法）。\n"
        "6. 使用 visualization：生成「按日就诊量」折线图与「按医生/类型」对比柱状图。\n"
        "7. 使用 html_report_generator：整合上述结论与图表路径，生成徐汇门店本月就诊分析 HTML 报告。\n"
        "\n"
        "【问题上报】任一步骤出现异常或需记录的处理时，立即调用 problem_reporter：\n"
        "- agent 固定为 Agent2；stage 与步骤对应：图谱查询→knowledge，取数→data_fetch，"
        "SQL 修复→sql_check，基础分析→basic_analysis，进阶分析→advanced_analysis，"
        "可视化→visualization，报告生成→review；\n"
        "- problem：错误信息、涉及表/字段/门店/时间条件等上下文；\n"
        "- solution：已执行的修复（如改 SQL、换字段、缩小范围）或降级方案；\n"
        "- severity：阻塞主流程用 high，可绕过用 medium，已解决且影响小用 low。\n"
        "上报后继续执行或说明无法继续的原因，勿静默跳过。\n"
        "\n"
        "【约束】必须通过工具接口逐步调用，禁止在正文中输出 DSML/XML 伪工具调用。\n"
        "【最终交付】用 Markdown 汇总：数据概况、核心指标、主要发现、图表路径、HTML 报告路径。"
    ),
    expected_output=(
        "一份徐汇门店本月患者就诊分析的 Markdown 汇总，包含："
        "就诊人次与结构概况、按医生/类型拆解结论、趋势或对比要点、"
        "图表文件路径、HTML 报告本地访问路径；"
        "执行过程中通过 problem_reporter 上报过的问题及 ID 列表；"
        "若某步数据缺失需明确说明原因。"
    ),
    agent=data_agent,
)

# ============================================================
# 独立运行
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
    print("[Agent2] Final output:")
    print(result)
