import os
from crewai.tools import BaseTool

class HtmlReportGeneratorTool(BaseTool):
    name: str = "html_report_generator"
    description: str = (
        "Integrate all analysis data, indicator conclusions and chart resources into a complete online HTML analysis report. "
        "Input full analysis text content, generate beautiful formatted HTML page, return browser access link, "
        "support online preview, share and simple presentation display instead of PPT."
    )

    def _run(self, content: str) -> str:
        """
        整合所有分析结果生成在线HTML可视化报告
        替代传统PPT，支持浏览器直接打开预览汇报
        """
        if not content or len(content.strip()) < 10:
            return "❌ Error: Analysis content is empty, cannot generate report."

        # 简约商务风HTML模板
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>儿牙业务数据分析汇总报告</title>
    <style>
        *{{margin:0;padding:0;box-sizing:border-box;}}
        body{{font-family:"Microsoft YaHei",sans-serif;background:#f5f7fa;padding:40px 60px;line-height:2;}}
        .report-box{{background:#fff;padding:50px;border-radius:12px;box-shadow:0 2px 15px #e2e8f0;}}
        .report-title{{font-size:28px;color:#234e70;text-align:center;margin-bottom:30px;border-bottom:2px solid #409eff;padding-bottom:15px;}}
        .report-content{{font-size:16px;color:#333;white-space:pre-line;}}
        .report-footer{{margin-top:40px;text-align:right;color:#666;font-size:14px;}}
    </style>
</head>
<body>
    <div class="report-box">
        <h1 class="report-title">儿牙门诊业务数据分析正式报告</h1>
        <div class="report-content">{content}</div>
        <div class="report-footer">自动生成时间：系统实时生成 · 在线可视化汇报文档</div>
    </div>
</body>
</html>
        """

        # 创建目录并写入文件
        report_dir = "./output/report"
        os.makedirs(report_dir, exist_ok=True)
        report_file_path = os.path.join(report_dir, "business_analysis_report.html")

        with open(report_file_path, "w", encoding="utf-8") as f:
            f.write(html_content.strip())

        local_access_link = f"file://{os.path.abspath(report_file_path)}"

        return (
            "📄 在线HTML分析报告生成成功\n"
            "----------------------------------------\n"
            "文档功能：替代PPT在线汇报、浏览器一键打开、支持转发分享\n"
            f"本地浏览器访问链接：{local_access_link}\n"
            "使用说明：可直接用于工作汇报、业务复盘、数据同步展示\n"
            "✅ 全流程数据分析文档整理完毕"
        )