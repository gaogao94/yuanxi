"""
KnowledgeBaseQueryTool：知识经验库查询工具

【作用】
供 Agent1（调度精灵）和 Agent2（干活精灵）在任务执行过程中主动查询知识经验库。
Agent 在遇到不确定的指标口径、想参考历史踩坑记录、或者想套用标准分析模式时，
可以调用此工具查询已有知识，避免重复踩坑。

【与 KnowledgeBaseReader 的区别】
- KnowledgeBaseReader：给 Agent3 复盘用的（查全量 + 多种过滤方式）
- KnowledgeBaseQueryTool：给 Agent1/Agent2 执行时用的（简洁关键词查询，快速获取答案）

【使用场景举例】
- Agent1 澄清需求时：查"转化率"相关的标准口径定义
- Agent2 写 SQL 前：查"取数"相关的踩坑记录
- Agent2 分析前：查"转化率分析"推荐的分析模式
"""

from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from tools.knowledge_store import KnowledgeStore


class KnowledgeBaseQueryInput(BaseModel):
    """
    知识库查询工具的输入参数定义。
    支持关键词搜索和按分类浏览两种方式。
    """
    keyword: str = Field(
        ...,
        description="搜索关键词，例如：'转化率'、'取数'、'字段名'、'SQL'、'口径'等",
    )
    category: Optional[str] = Field(
        default=None,
        description=(
            "按分类筛选（可选）："
            "metric_definition（标准口径定义）| "
            "pitfall（常见踩坑记录）| "
            "analysis_pattern（有效分析模式）| "
            "action_item（改进行动项）"
        ),
    )


class KnowledgeBaseQueryTool(BaseTool):
    """
    知识经验库查询工具。

    Agent1 和 Agent2 将此工具挂载到 tools 列表中后，
    LLM 在遇到指标口径模糊、需要参考历史经验时，会自动调用此工具查询知识库。

    使用方法：
        在 Agent 的 tools 列表中加入 KnowledgeBaseQueryTool() 即可。
    """
    name: str = "knowledge_base_query"
    description: str = (
        "查询知识经验库中的历史经验。可以按关键词搜索，也可以按分类浏览。"
        "包括：指标标准口径定义（查口径）、常见踩坑记录（查避坑方法）、"
        "有效分析模式（查分析框架）、历史改进行动项。"
        "在遇到指标定义不确定、或者想参考历史经验时调用。"
    )
    args_schema: Type[BaseModel] = KnowledgeBaseQueryInput

    def _run(self, keyword: str, category: Optional[str] = None) -> str:
        """
        执行知识库查询。

        参数：
            keyword: 搜索关键词
            category: 可选的分类筛选

        返回：
            匹配的知识记录（Markdown 格式），如果没有找到则提示无结果
        """
        # 确保知识库已初始化
        KnowledgeStore.init()

        # 先按关键词全文搜索
        results = KnowledgeStore.search_by_keyword(keyword)

        # 如果指定了分类，进一步过滤
        if category and results:
            results = [r for r in results if r.get("category") == category]

        if not results:
            return (
                f"知识库中未找到与「{keyword}」相关的经验记录。\n"
                f"提示：你可以尝试其他关键词，或者等待本次任务结束后由 Agent3 沉淀新的经验。"
            )

        # 格式化返回结果
        category_names = {
            "metric_definition": "📐 标准口径定义",
            "pitfall": "⚠️ 踩坑记录",
            "analysis_pattern": "🔍 分析模式",
            "action_item": "✅ 行动项",
        }

        lines = [
            f"找到 {len(results)} 条与「{keyword}」相关的经验记录：\n"
        ]

        for r in results:
            cat_name = category_names.get(r.get("category", ""), r.get("category", ""))
            lines.append(f"### {cat_name}：{r['title']}")
            lines.append(r.get("content", ""))
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines).strip()
