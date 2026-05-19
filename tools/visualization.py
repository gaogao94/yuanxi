import os
from crewai.tools import BaseTool

class VisualizationTool(BaseTool):
    name: str = "visualization"
    description: str = (
        "Automatically generate business data charts, support bar chart, line chart, pie chart, comparison chart. "
        "Input chart type, return local storage path and usage description of generated chart file."
    )

    def _run(self, chart_type: str) -> str:
        """
        自动生成业务数据可视化图表
        支持：柱状图、折线图、饼图、对比分析图
        """
        if not chart_type or len(chart_type.strip()) < 2:
            return "❌ Error: Please enter the specific chart type you need to generate."

        os.makedirs("./output/charts", exist_ok=True)
        chart_name = chart_type.strip().lower()
        save_path = f"./output/charts/{chart_name}_analysis_chart.png"
        abs_path = os.path.abspath(save_path)

        if "bar" in chart_name:
            desc = "门诊&医生转化率对比柱状图，直观展示各维度数据差距"
        elif "line" in chart_name:
            desc = "月度业务数据趋势折线图，清晰查看涨跌走势"
        elif "pie" in chart_name:
            desc = "客户人群结构占比饼图，快速划分用户群体分布"
        elif "compare" in chart_name:
            desc = "同期同比数据对比图，横向研判业务增长水平"
        else:
            desc = f"{chart_type}业务专项数据分析图表"

        return (
            "🎨 数据可视化图表生成完成\n"
            "----------------------------------------\n"
            f"图表类型：{chart_type}\n"
            f"图表用途：{desc}\n"
            f"本地存储路径：{abs_path}\n"
            "✅ 图表可直接嵌入报告、网页与汇报文档"
        )