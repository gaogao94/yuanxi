"""
NebulaGraph 知识图谱查询工具（Agent2 使用）

通过 https://graph.automed.cn 只读 HTTP API 查询 medgraph 空间。
文档：https://graph.automed.cn/apidoc
"""

import re
from typing import Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from tools.graph_api import GraphAPIClient, GraphAPIError, format_graph_result

# 自然语言里常见的节点/关系类型关键词 → API 参数
_TAG_ALIASES = {
    "患者": "患者", "patient": "患者",
    "门诊": "门诊", "诊所": "门诊", "门店": "门诊", "clinic": "门诊",
    "卡": "卡", "会员": "卡",
    "家长": "家长",
}
_EDGE_ALIASES = {
    "就诊": "就诊", "预约": "就诊", "appointment": "就诊",
    "持有": "持有", "has": "持有",
    "所属": "所属",
}


class NebulaGraphQueryInput(BaseModel):
    """知识图谱查询参数"""

    question: str = Field(
        ...,
        description=(
            "查询内容：可为 nGQL 只读语句（如 MATCH (p:患者)-[:就诊]->(c:门诊) RETURN p,c LIMIT 10），"
            "或自然语言描述（如「查询门诊与患者的就诊关系」）。"
        ),
    )
    tag: Optional[str] = Field(
        default=None,
        description="节点类型（可选），如：患者、门诊、卡、家长。与 question 二选一或组合使用。",
    )
    edge_type: Optional[str] = Field(
        default=None,
        description="关系类型（可选），如：就诊、持有、所属。",
    )
    limit: int = Field(default=50, description="返回条数上限，最大 500")


class NebulaGraphQueryTool(BaseTool):
    name: str = "nebula_graph_query"
    description: str = (
        "查询 NebulaGraph 医疗知识图谱（medgraph 空间）。"
        "支持：1) 传入 nGQL 只读语句（MATCH/SHOW/GO 等）做自定义查询；"
        "2) 按节点类型（tag）查顶点，如 患者、门诊、卡；"
        "3) 按关系类型查边，如 就诊、持有、所属。"
        "用于确认门店、患者、预约、账单等实体关联。"
    )
    args_schema: Type[BaseModel] = NebulaGraphQueryInput

    def _run(
        self,
        question: str,
        tag: Optional[str] = None,
        edge_type: Optional[str] = None,
        limit: int = 50,
    ) -> str:
        client = GraphAPIClient()
        limit = min(max(limit, 1), 500)

        try:
            stmt = question.strip()
            if _is_ngql_statement(stmt):
                data = client.execute_query(stmt)
                return format_graph_result(data, title=f"nGQL 查询（空间: {client.space}）")

            resolved_tag = tag or _extract_tag(stmt)
            resolved_edge = edge_type or _extract_edge_type(stmt)

            if resolved_edge:
                data = client.query_edges(edge_type=resolved_edge, limit=limit)
                return format_graph_result(
                    data,
                    title=f"关系查询: {resolved_edge}（空间: {client.space}）",
                )

            if resolved_tag:
                data = client.query_vertices(tag=resolved_tag, limit=limit)
                return format_graph_result(
                    data,
                    title=f"节点查询: {resolved_tag}（空间: {client.space}）",
                )

            # 无法解析为结构化查询时，列出 schema 供 Agent 构造 nGQL
            tags = client.list_tags()
            edges = client.list_edge_types()
            tag_names = [r.get("Name", r) for r in tags]
            edge_names = [r.get("Name", r) for r in edges]
            return (
                f"未能从描述中识别具体节点/关系类型，请使用 nGQL 或指定 tag/edge_type。\n\n"
                f"当前空间 `{client.space}` 可用节点类型: {', '.join(map(str, tag_names))}\n"
                f"可用关系类型: {', '.join(map(str, edge_names))}\n\n"
                "示例 nGQL:\n"
                f'  MATCH (p:患者)-[r:就诊]->(c:门诊) RETURN p, r, c LIMIT {limit}'
            )

        except GraphAPIError as e:
            return f"知识图谱查询失败: {e}"
        except Exception as e:
            return f"知识图谱查询异常: {e}"


def _is_ngql_statement(text: str) -> bool:
    upper = text.upper().lstrip()
    return any(
        upper.startswith(p)
        for p in ("MATCH", "SHOW", "DESCRIBE", "FETCH", "GO", "LOOKUP", "RETURN", "GET")
    )


def _extract_tag(text: str) -> Optional[str]:
    if m := re.search(r"(?:tag|节点)[:：]\s*(\S+)", text, re.I):
        return m.group(1)
    lower = text.lower()
    for key, tag in _TAG_ALIASES.items():
        if key in text or key in lower:
            return tag
    return None


def _extract_edge_type(text: str) -> Optional[str]:
    if m := re.search(r"(?:type|关系|边)[:：]\s*(\S+)", text, re.I):
        return m.group(1)
    lower = text.lower()
    for key, edge in _EDGE_ALIASES.items():
        if key in text or key in lower:
            return edge
    return None


if __name__ == "__main__":
    tool = NebulaGraphQueryTool()
    print("--- health / schema ---")
    client = GraphAPIClient()
    try:
        print(client.health())
        print("tags:", client.list_tags())
    except GraphAPIError as e:
        print(f"跳过（未配置或无法连接）: {e}")
    print("\n--- tool: nGQL ---")
    print(
        tool._run(
            question='MATCH (n) RETURN labels(n) AS tag, count(*) AS cnt LIMIT 5',
            limit=5,
        )
    )
