from crewai.tools import BaseTool

class BasicAnalysisTool(BaseTool):
    name: str = "basic_analysis"
    description: str = (
        "Perform basic data analysis including conversion rate calculation, "
        "clinic/doctor dimensional breakdown, month-on-month (MoM) and year-on-year (YoY) comparison. "
        "Input: requirement description. Output: structured business indicators."
    )

    def _run(self, requirement: str) -> str:
        """
        执行基础业务分析（模拟真实业务计算逻辑）
        支持：初诊转化率、门诊维度、医生维度、同比、环比
        """
        # 入参校验
        if not requirement or len(requirement.strip()) < 2:
            return "❌ Error: Requirement is too short or empty."

        # 模拟业务指标（真实环境可替换为 pandas 计算）
        overall_conv_rate = 45.2
        clinic_sh001 = 48.1
        clinic_sh002 = 42.3
        doctor_zhang = 50.5
        doctor_li = 40.2
        yoy_change = +3.1
        mom_change = +1.2

        # 输出结构化结果（Agent 更容易理解）
        return (
            "📊 基础统计分析结果（Basic Analysis Results）\n"
            "----------------------------------------\n"
            f"• 整体初诊转化率 (Overall Conversion): {overall_conv_rate}%\n"
            f"• 门诊维度转化率 (By Clinic):\n"
            f"   - SH001: {clinic_sh001}%\n"
            f"   - SH002: {clinic_sh002}%\n"
            f"• 医生维度转化率 (By Doctor):\n"
            f"   - Dr. Zhang: {doctor_zhang}%\n"
            f"   - Dr. Li: {doctor_li}%\n"
            "----------------------------------------\n"
            f"• 同比变化 (YoY vs 2025): {yoy_change:+.1f} 个百分点\n"
            f"• 环比变化 (MoM vs Last Month): {mom_change:+.1f} 个百分点\n"
            "----------------------------------------\n"
            "✅ Analysis completed successfully."
        )