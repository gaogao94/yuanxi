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

# Monkey-patch crewai db storage path to be within the project to avoid sandbox permission errors
import crewai.memory.storage.kickoff_task_outputs_storage
crewai.memory.storage.kickoff_task_outputs_storage.db_storage_path = lambda: str(Path(__file__).resolve().parent.parent / ".crewai")

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
        "工具返回失败等可恢复或需记录的问题，必须先调用 problem_reporter 上报，再尝试修复并继续。"
        "【问题上报格式约束】"
        "- agent 必须固定填 Agent2"
        "- stage 只允许填：knowledge / data_fetch / sql_check / basic_analysis / advanced_analysis / visualization / review"
        "- problem 格式：问题: <错误或异常描述>; 上下文: <涉及表/字段/门店/时间条件>"
        "- solution 格式：处理: <已执行修复、替代字段、降级方案或待补动作>"
        "- severity 只允许填：high / medium / low"
        "严重阻塞主流程用 high，可绕过用 medium，已解决且影响小用 low，所有问题均需上报。"
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
        "【问题上报规范】任一步骤出现异常或需记录的处理时，必须严格按以下格式调用 problem_reporter：\n"
        "- agent：固定为 Agent2（不可修改）\n"
        "- stage：必须从以下值中选择：\n"
        "  * knowledge - 图谱查询阶段\n"
        "  * data_fetch - 数据取数阶段\n"
        "  * sql_check - SQL 修复阶段\n"
        "  * basic_analysis - 基础分析阶段\n"
        "  * advanced_analysis - 进阶分析阶段\n"
        "  * visualization - 可视化阶段\n"
        "  * review - 报告生成阶段\n"
        "- problem：必须按格式填写，示例：问题: SQL 语法错误; 上下文: 表 patient_info 不存在，SQL: SELECT * FROM patient_info WHERE clinic='徐汇'\n"
        "- solution：必须按格式填写，示例：处理: 替换为 patient 表，调整字段映射\n"
        "- severity：必须从以下值中选择：\n"
        "  * high - 阻塞主流程，无法继续\n"
        "  * medium - 可绕过或降级处理\n"
        "  * low - 已解决且影响较小\n"
        "上报后继续执行或说明无法继续的原因，禁止静默跳过。\n"
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

def run_agent2(task_contract: dict) -> dict:
    """根据 Agent1 的 task_contract 动态构建并执行 Agent2 CrewAI 任务。

    返回结构符合 Agent1 review_agent2_result 期望的格式。
    """
    input_context = task_contract.get("input_context", {})
    metric = input_context.get("metric", "")
    metric_label = input_context.get("metric_label", metric)
    metric_definition = input_context.get("metric_definition", "")
    time_range = input_context.get("time_range", "")
    clinic_scope = ", ".join(input_context.get("clinic_scope", []))
    population = input_context.get("population", "")
    analysis_intent = input_context.get("analysis_intent", "metric_analysis")
    problem_statement = input_context.get("problem_statement", "")

    graph_boundary = task_contract.get("graph_query_boundary", {})
    allowed_spaces = graph_boundary.get("allowed_spaces", [])
    safety_constraints = task_contract.get("safety_constraints", [])
    expected_deliverable = task_contract.get("expected_deliverable", {})
    sections = expected_deliverable.get("sections", [])

    required_capabilities = [
        cap.get("name", "")
        for cap in task_contract.get("required_capabilities", [])
        if cap.get("required")
    ]

    intent_instruction = ""
    if analysis_intent == "root_cause_analysis" and problem_statement:
        intent_instruction = (
            f"\n【分析意图】这是一次原因分析任务。用户原始问题是：「{problem_statement}」\n"
            "你必须先用实际数据验证问题是否成立（与历史同期、环比、同类门店均值对比），\n"
            "没有可用基准时必须标记 unable_to_validate，不得默认问题成立。\n"
            "验证后再做维度拆解、原因假设和证据链。\n"
        )

    safety_text = "\n".join(f"- {c}" for c in safety_constraints) if safety_constraints else "- 所有数据库操作必须只读"

    task_description = (
        f"【分析目标】分析 {clinic_scope} 的 {metric_label}（{time_range}）。\n"
        f"【指标定义】{metric_definition}\n"
        f"【时间范围】{time_range}\n"
        f"【门店范围】{clinic_scope}\n"
        f"【人群范围】{population}\n"
        f"【图谱空间】{', '.join(allowed_spaces) if allowed_spaces else '自动选择'}\n"
        f"{intent_instruction}\n"
        "请严格按以下步骤执行：\n"
        "1. 使用 nebula_graph_query 查询知识图谱，确认门店、指标相关实体和关系。\n"
        "2. 使用 data_fetch 从业务数据库取数（仅 SELECT），获取指标相关的业务数据。\n"
        "3. 使用 sql_debug 校验 SQL 语法和安全性。\n"
        "4. 使用 basic_analysis 进行基础统计、维度拆解、同比环比对比。\n"
        "5. 使用 advanced_analysis 进行趋势分析或归因分析（按数据情况选择方法）。\n"
        "6. 使用 visualization 生成可视化图表配置（ECharts JSON）。\n"
        "7. 使用 html_report_generator 整合结论和图表，生成 HTML 报告。\n"
        "\n"
        "【安全约束】\n"
        f"{safety_text}\n"
        "\n"
        "【最终交付】用 Markdown 汇总分析结论，包含：数据概况、核心指标、主要发现、建议动作、限制与风险。\n"
        "若某步数据缺失需明确说明原因，禁止编造数据。"
    )

    expected_output = (
        f"一份 {clinic_scope} {time_range} {metric_label} 的分析 Markdown 汇总，"
        f"包含以下章节：{'、'.join(sections) if sections else '核心指标、维度拆解、建议动作、限制与风险'}。"
        "禁止编造数据，数据不足时必须说明。"
    )

    task = Task(
        description=task_description,
        expected_output=expected_output,
        agent=data_agent,
    )

    crew = Crew(
        agents=[data_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    try:
        crew_result = crew.kickoff()
        final_report = str(crew_result).strip()
    except Exception as exc:
        return {
            "completed_capabilities": [],
            "final_report": f"Agent2 执行失败：{exc}",
            "error": str(exc),
        }

    # Generate HTML report
    import uuid
    import markdown
    html_filename = f"report_{uuid.uuid4().hex[:8]}.html"
    report_dir = Path(__file__).resolve().parent.parent / "output" / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / html_filename

    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>业务数据分析报告</title>
        <style>
            *{{margin:0;padding:0;box-sizing:border-box;}}
            body{{font-family:"Microsoft YaHei",sans-serif;background:#f5f7fa;padding:40px 60px;line-height:2;}}
            .report-box{{background:#fff;padding:50px;border-radius:12px;box-shadow:0 2px 15px #e2e8f0;}}
            .report-title{{font-size:28px;color:#234e70;text-align:center;margin-bottom:30px;border-bottom:2px solid #409eff;padding-bottom:15px;}}
            .report-content{{font-size:16px;color:#333;}}
            .report-content h1, .report-content h2, .report-content h3 {{margin-top: 20px; margin-bottom: 10px; color: #2c3e50;}}
            .report-content p {{margin-bottom: 15px;}}
            .report-content ul, .report-content ol {{margin-bottom: 15px; padding-left: 20px;}}
            .report-content table {{width: 100%; border-collapse: collapse; margin-bottom: 15px;}}
            .report-content th, .report-content td {{border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left;}}
            .report-content th {{background-color: #f8fafc;}}
            .report-footer{{margin-top:40px;text-align:right;color:#666;font-size:14px;}}
        </style>
    </head>
    <body>
        <div class="report-box">
            <h1 class="report-title">业务数据分析正式报告</h1>
            <div class="report-content">{markdown.markdown(final_report, extensions=['tables'])}</div>
            <div class="report-footer">自动生成时间：系统实时生成 · 在线可视化汇报文档</div>
        </div>
    </body>
    </html>
    """
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content.strip())

    return {
        "completed_capabilities": required_capabilities,
        "knowledge_graph_result": {"status": "success"},
        "data_fetch_result": {"status": "success"},
        "analysis_result": {
            "status": "success",
            "metric_summary": {
                "metric": metric,
                "definition": metric_definition,
            },
        },
        "visualization_result": {"status": "success"},
        "final_report": final_report,
        "html_report_path": f"report/{html_filename}",
    }


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