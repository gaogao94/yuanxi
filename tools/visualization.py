import os
import json
from crewai.tools import BaseTool
from typing import Optional, Dict, Any

class VisualizationTool(BaseTool):
    name: str = "visualization"
    description: str = (
        "Automatically generate ECharts configuration for business data visualization. "
        "Supports bar, line, pie, and comparison charts. "
        "Input: chart_type (required), data (optional JSON string). "
        "Output: ECharts option JSON and usage description."
    )

    def _run(self, chart_type: str, data: Optional[str] = None) -> str:
        """
        自动生成业务数据可视化图表配置（适配 ECharts）
        支持：柱状图 (bar)、折线图 (line)、饼图 (pie)、对比分析图 (compare)
        """
        if not chart_type or len(chart_type.strip()) < 2:
            return "❌ Error: Please enter the specific chart type you need to generate."

        chart_name = chart_type.strip().lower()
        
        # 解析输入数据，如果为空则使用模拟数据
        try:
            input_data = json.loads(data) if data else {}
        except Exception:
            input_data = {}

        echarts_option: Dict[str, Any] = {}
        desc = ""

        if "bar" in chart_name:
            desc = "门诊&医生转化率对比柱状图，直观展示各维度数据差距"
            echarts_option = {
                "title": {"text": "转化率对比分析"},
                "tooltip": {},
                "xAxis": {"data": input_data.get("categories", ["SH001", "SH002", "Dr. Zhang", "Dr. Li"])},
                "yAxis": {},
                "series": [{
                    "name": "转化率",
                    "type": "bar",
                    "data": input_data.get("values", [48.1, 42.3, 50.5, 40.2])
                }]
            }
        elif "line" in chart_name:
            desc = "月度业务数据趋势折线图，清晰查看涨跌走势"
            echarts_option = {
                "title": {"text": "月度趋势分析"},
                "tooltip": {"trigger": "axis"},
                "xAxis": {"type": "category", "data": input_data.get("months", ["1月", "2月", "3月", "4月", "5月"])},
                "yAxis": {"type": "value"},
                "series": [{
                    "data": input_data.get("values", [35, 38, 42, 45, 48]),
                    "type": "line",
                    "smooth": True
                }]
            }
        elif "pie" in chart_name:
            desc = "客户人群结构占比饼图，快速划分用户群体分布"
            echarts_option = {
                "title": {"text": "人群结构分布", "left": "center"},
                "tooltip": {"trigger": "item"},
                "legend": {"orient": "vertical", "left": "left"},
                "series": [{
                    "name": "人群占比",
                    "type": "pie",
                    "radius": "50%",
                    "data": input_data.get("items", [
                        {"value": 22, "name": "高意向"},
                        {"value": 55, "name": "犹豫中"},
                        {"value": 23, "name": "低意向"}
                    ])
                }]
            }
        elif "compare" in chart_name:
            desc = "同期同比数据对比图，横向研判业务增长水平"
            echarts_option = {
                "title": {"text": "同比/环比分析"},
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                "legend": {"data": ["2025", "2026"]},
                "xAxis": [{"type": "category", "axisTick": {"show": False}, "data": ["转化率", "到店量", "成交额"]}],
                "yAxis": [{"type": "value"}],
                "series": [
                    {"name": "2025", "type": "bar", "barGap": 0, "data": input_data.get("v2025", [42, 100, 500])},
                    {"name": "2026", "type": "bar", "data": input_data.get("v2026", [45, 120, 550])}
                ]
            }
        else:
            desc = f"{chart_type} 业务专项数据分析图表"
            echarts_option = {"title": {"text": desc}, "series": []}

        # 构造返回结果
        result = {
            "status": "success",
            "chart_type": chart_type,
            "description": desc,
            "echarts_option": echarts_option
        }

        return (
            "📊 ECharts 可视化配置生成完成\n"
            "----------------------------------------\n"
            f"图表类型：{chart_type}\n"
            f"图表用途：{desc}\n"
            "✅ 配置已生成，可直接用于前端 ECharts 渲染：\n"
            f"```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```"
        )

# 手动测试入口
if __name__ == "__main__":
    vis_tool = VisualizationTool()
    # 测试生成柱状图
    print(vis_tool._run("bar"))
    # 测试传入数据生成折线图
    test_data = json.dumps({"months": ["周一", "周二", "周三"], "values": [10, 20, 15]})
    print(vis_tool._run("line", data=test_data))