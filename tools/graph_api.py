"""
NebulaGraph HTTP API 客户端
文档：https://graph.automed.cn/apidoc
"""

import os
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

READONLY_STATEMENT_PREFIXES = (
    "MATCH", "SHOW", "DESCRIBE", "FETCH", "GO", "LOOKUP", "RETURN", "GET",
)


class GraphAPIError(Exception):
    """图数据库 API 调用失败"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class GraphAPIClient:
    """只读图数据库 HTTP 客户端"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        space: Optional[str] = None,
    ):
        self.base_url = (
            base_url or os.getenv("GRAPH_API_URL", "https://graph.automed.cn")
        ).rstrip("/")
        self.api_key = api_key or os.getenv("GRAPH_API_KEY") or os.getenv("NEBULA_API_KEY")
        self.space = space or os.getenv("GRAPH_SPACE") or os.getenv("NEBULA_SPACE", "medgraph")

    def _headers(self, json_body: bool = False) -> Dict[str, str]:
        if not self.api_key:
            raise GraphAPIError(
                "未配置 GRAPH_API_KEY，请在 .env 中设置（由管理员提供的 Bearer Token）"
            )
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = requests.request(
                method,
                url,
                headers=self._headers(json_body=json is not None),
                params=params,
                json=json,
                timeout=35,
            )
        except requests.RequestException as e:
            raise GraphAPIError(f"网络请求失败: {e}") from e

        if resp.status_code == 401:
            raise GraphAPIError("缺少或无效的 API Key（HTTP 401）", 401)
        if resp.status_code == 403:
            raise GraphAPIError("API Key 无效或查询被拒绝（HTTP 403）", 403)
        if resp.status_code == 400:
            detail = resp.text[:500] if resp.text else "请求参数或 nGQL 语法错误"
            raise GraphAPIError(f"请求错误（HTTP 400）: {detail}", 400)
        if resp.status_code == 504:
            raise GraphAPIError("查询超时，超过 30 秒（HTTP 504）", 504)
        if resp.status_code == 503:
            raise GraphAPIError("图数据库连接异常（HTTP 503）", 503)
        if not resp.ok:
            raise GraphAPIError(
                f"API 返回异常（HTTP {resp.status_code}）: {resp.text[:500]}",
                resp.status_code,
            )

        if not resp.content:
            return {}
        return resp.json()

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health")

    def list_spaces(self) -> List[str]:
        data = self._request("GET", "/spaces")
        return data.get("spaces", [])

    def list_tags(self, space: Optional[str] = None) -> List[Dict[str, Any]]:
        sp = space or self.space
        data = self._request("GET", f"/{sp}/tags")
        return data.get("rows", [])

    def list_edge_types(self, space: Optional[str] = None) -> List[Dict[str, Any]]:
        sp = space or self.space
        data = self._request("GET", f"/{sp}/edges")
        return data.get("rows", [])

    def query_vertices(
        self,
        tag: Optional[str] = None,
        limit: int = 50,
        space: Optional[str] = None,
    ) -> Dict[str, Any]:
        sp = space or self.space
        params: Dict[str, Any] = {"limit": min(max(limit, 1), 500)}
        if tag:
            params["tag"] = tag
        return self._request("GET", f"/{sp}/vertices", params=params)

    def query_edges(
        self,
        edge_type: Optional[str] = None,
        limit: int = 50,
        space: Optional[str] = None,
    ) -> Dict[str, Any]:
        sp = space or self.space
        params: Dict[str, Any] = {"limit": min(max(limit, 1), 500)}
        if edge_type:
            params["type"] = edge_type
        return self._request("GET", f"/{sp}/edges", params=params)

    def execute_query(self, statement: str, space: Optional[str] = None) -> Dict[str, Any]:
        sp = space or self.space
        stmt = statement.strip()
        if not stmt:
            raise GraphAPIError("nGQL 语句不能为空")
        upper = stmt.upper()
        if not any(upper.startswith(p) for p in READONLY_STATEMENT_PREFIXES):
            raise GraphAPIError(
                "仅支持只读 nGQL（MATCH / SHOW / DESCRIBE / FETCH / GO / LOOKUP / RETURN 等）"
            )
        return self._request(
            "POST",
            f"/{sp}/query",
            json={"statement": stmt},
        )


def format_graph_result(data: Dict[str, Any], title: str = "查询结果") -> str:
    """将 API JSON 格式化为 Agent 易读的文本"""
    lines = [f"## {title}", ""]
    count = data.get("count")
    if count is not None:
        lines.append(f"- 返回条数: {count}")

    rows = data.get("rows")
    if rows is None and "spaces" in data:
        lines.append(f"- 可用空间: {', '.join(data['spaces'])}")
        return "\n".join(lines)

    if rows is None:
        for key, value in data.items():
            if key != "count":
                lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    if not rows:
        lines.append("- 无匹配数据")
        return "\n".join(lines)

    lines.append(f"- 共 {len(rows)} 条记录:")
    for i, row in enumerate(rows[:20], 1):
        lines.append(f"  {i}. {row}")
    if len(rows) > 20:
        lines.append(f"  ... 另有 {len(rows) - 20} 条未展示")
    return "\n".join(lines)
