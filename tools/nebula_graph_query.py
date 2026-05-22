"""Shared NebulaGraph query tool for Agent1 and Agent2.

Agent2 uses this as its normal CrewAI tool. Agent1 uses the same tool with
``output_format="json"`` so the deterministic clarification core can consume
schema, vertices, and edges without maintaining a separate graph tool module.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.error
import urllib.request
from typing import TYPE_CHECKING, Any, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

if TYPE_CHECKING:
    from nebula3.gclient.net import ConnectionPool


class NebulaGraphQueryInput(BaseModel):
    question: str = Field(default="", description="Natural-language query or read-only nGQL statement.")
    query: str = Field(
        default="",
        description=(
            "Graph query intent or nGQL statement. In local mode this is used as "
            "the business query text while MEDGRAPH_JSON_PATH provides the graph data."
        ),
    )
    keyword: str = Field(default="", description="Business keyword extracted from the user question.")
    user_question: str = Field(default="", description="Original user question for graph lookup context.")
    purpose: str = Field(default="clarification", description="Tool usage purpose, such as clarification.")
    tag: str = Field(default="", description="Optional vertex tag for Agent2 queries.")
    edge_type: str = Field(default="", description="Optional edge type for Agent2 queries.")
    limit: int = Field(default=50, description="Maximum rows to fetch for schema samples.")
    output_format: str = Field(default="text", description="Use json for Agent1 structured graph data.")


class NebulaGraphQueryTool(BaseTool):
    name: str = "nebula_graph_query"
    description: str = (
        "Query the medical/business NebulaGraph knowledge graph. Agent2 can use it "
        "directly for graph lookup; Agent1 passes output_format=json to receive "
        "structured graph data including space, schema, vertices, and edges."
    )
    args_schema: Type[BaseModel] = NebulaGraphQueryInput

    _connection_pool: Optional[Any] = None

    def _get_pool(self) -> "ConnectionPool":
        if self._connection_pool is not None:
            return self._connection_pool

        try:
            from nebula3.Config import Config
            from nebula3.gclient.net import ConnectionPool
        except ImportError:
            raise Exception("nebula3-python 未安装，无法连接图数据库。")

        nebula_address = os.getenv("NEBULA_ADDRESS", "127.0.0.1")
        nebula_port = int(os.getenv("NEBULA_PORT", 9669))

        config = Config()
        config.max_connection_pool_size = 10

        pool = ConnectionPool()
        if not pool.init([(nebula_address, nebula_port)], config):
            raise Exception(f"无法连接到 NebulaGraph {nebula_address}:{nebula_port}")

        self._connection_pool = pool
        return pool

    def _run(
        self,
        question: str = "",
        query: str = "",
        keyword: str = "",
        user_question: str = "",
        purpose: str = "clarification",
        tag: str = "",
        edge_type: str = "",
        limit: int = 50,
        output_format: str = "text",
    ) -> str:
        limit = min(max(int(limit), 1), 500)
        query_text = query or question or keyword or user_question or tag or edge_type
        graph = self._run_structured_graph(
            query_text,
            keyword,
            user_question,
            purpose,
            tag,
            edge_type,
            limit,
        )
        if output_format.strip().lower() in {"json", "structured"}:
            return json.dumps(graph, ensure_ascii=False)
        return self._format_text_result(graph, query_text, limit)

    def _run_structured_graph(
        self,
        query_text: str,
        keyword: str,
        user_question: str,
        purpose: str,
        tag: str = "",
        edge_type: str = "",
        limit: int = 50,
    ) -> dict[str, Any]:
        api_error = ""
        strict_graph_api = self._strict_graph_api_enabled()
        if strict_graph_api and not os.getenv("GRAPH_API_KEY", "").strip():
            return self._error_graph(
                query_text,
                "GRAPH_API_KEY is required when GRAPH_API_STRICT is enabled.",
            )
        try:
            api_graph = self._run_graph_api(
                query_text,
                keyword,
                user_question,
                purpose,
                tag,
                edge_type,
                limit,
            )
            if api_graph is not None:
                return api_graph
        except Exception as exc:
            api_error = str(exc)
            if strict_graph_api:
                return self._error_graph(query_text, api_error)

        if strict_graph_api:
            return self._error_graph(
                query_text,
                api_error or "Graph API did not return graph data.",
            )

        local_json_path = os.getenv("MEDGRAPH_JSON_PATH")
        if local_json_path:
            local_graph = self._load_local_graph(local_json_path)
            if local_graph is not None:
                return local_graph

        try:
            pool = self._get_pool()
            nebula_user = os.getenv("NEBULA_USER", "root")
            nebula_password = os.getenv("NEBULA_PASSWORD", "nebula")
            nebula_space = os.getenv("NEBULA_SPACE", "your_space")

            with pool.session_context(nebula_user, nebula_password) as session:
                session.execute(f"USE {nebula_space}")
                result = session.execute(query_text)
                if result and result.is_succeeded():
                    rows = result.rows()
                    return {
                        "space": nebula_space,
                        "version": "nebula",
                        "schema": {},
                        "data": {
                            "vertices": [],
                            "edges": [],
                            "rows": [str(row) for row in rows],
                        },
                        "query": query_text,
                    }

                error_message = result.error_msg() if result else "未知错误"
                return self._fallback_graph(query_text, error_message)
        except Exception as exc:
            fallback_error = api_error or str(exc)
            return self._fallback_graph(query_text, fallback_error)

    def _format_text_result(
        self,
        graph: dict[str, Any],
        query_text: str,
        limit: int,
    ) -> str:
        if graph.get("status") == "error":
            return f"知识图谱查询失败: {graph.get('error', 'unknown error')}"

        schema = graph.get("schema", {})
        tags = list((schema.get("tags") or {}).keys())
        edges = list((schema.get("edges") or {}).keys())
        data = graph.get("data", {})
        sample_edges = data.get("edges", [])
        rows = data.get("rows", [])

        lines = [
            f"## NebulaGraph 查询结果（空间: {graph.get('space', 'unknown')}）",
            "",
            f"- 查询: {query_text or graph.get('query', '')}",
            f"- 来源: {graph.get('source', graph.get('version', 'unknown'))}",
        ]
        if tags:
            lines.append(f"- 可用节点类型: {', '.join(map(str, tags[:limit]))}")
        if edges:
            lines.append(f"- 可用关系类型: {', '.join(map(str, edges[:limit]))}")
        if sample_edges:
            lines.append("- 命中关系样例:")
            for item in sample_edges[: min(limit, 10)]:
                lines.append(f"  - {item}")
        if rows:
            lines.append("- 查询行样例:")
            for item in rows[: min(limit, 10)]:
                lines.append(f"  - {item}")
        if graph.get("error"):
            lines.append(f"- 降级原因: {graph['error']}")
        return "\n".join(lines)

    def _run_graph_api(
        self,
        query: str,
        keyword: str,
        user_question: str,
        purpose: str,
        tag: str = "",
        edge_type: str = "",
        limit: int = 50,
    ) -> dict[str, Any] | None:
        api_key = os.getenv("GRAPH_API_KEY", "").strip()
        if not api_key:
            return None

        base_url = os.getenv("GRAPH_API_BASE_URL", "https://graph.automed.cn").rstrip("/")
        space, space_selection = self._select_graph_api_space(
            base_url,
            api_key,
            query or keyword or user_question,
        )
        if not space:
            raise ValueError(
                "Unable to auto-select GRAPH_API_SPACE from Graph API spaces."
            )
        if edge_type:
            edge_response = self._get_json(
                f"{base_url}/{space}/edges?type={urllib.parse.quote(edge_type)}&limit={limit}",
                api_key,
            )
            graph = {
                "space": space,
                "version": "graph_api",
                "schema": {"tags": {}, "edges": {edge_type: {}}},
                "data": {
                    "vertices": [],
                    "edges": [],
                    "rows": edge_response.get("rows", []),
                    "columns": edge_response.get("columns", []),
                },
                "query": query or edge_type,
                "source": "graph_api",
                "raw": edge_response.get("raw", ""),
                "space_selection": space_selection,
            }
            for row in edge_response.get("rows", []):
                parsed = self._parse_edge_row(row, edge_type)
                if parsed:
                    graph["data"]["edges"].append(parsed)
            return graph

        if tag:
            vertex_response = self._get_json(
                f"{base_url}/{space}/vertices?tag={urllib.parse.quote(tag)}&limit={limit}",
                api_key,
            )
            return {
                "space": space,
                "version": "graph_api",
                "schema": {"tags": {tag: {}}, "edges": {}},
                "data": {
                    "vertices": vertex_response.get("rows", []),
                    "edges": [],
                    "rows": vertex_response.get("rows", []),
                    "columns": vertex_response.get("columns", []),
                },
                "query": query or tag,
                "source": "graph_api",
                "raw": vertex_response.get("raw", ""),
                "space_selection": space_selection,
            }

        payload = {
            "statement": self._readonly_query(query or keyword or user_question),
            "keyword": keyword,
            "user_question": user_question,
            "purpose": purpose,
        }
        url = f"{base_url}/{space}/query"

        response = self._request_json(url, api_key, payload)
        self._raise_if_nebula_error(response)
        graph = self._normalize_graph_response(response, space, query)
        graph["space_selection"] = space_selection
        self._enrich_graph_schema(base_url, space, api_key, graph)
        self._enrich_relevant_edges(base_url, space, api_key, graph, query or keyword or user_question)
        return graph

    def _request_json(
        self,
        url: str,
        api_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        timeout = float(os.getenv("GRAPH_API_TIMEOUT_SECONDS", "10"))
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": self._authorization_value(api_key),
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": self._user_agent(),
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")

        if not body:
            return {}
        return json.loads(body)

    def _readonly_query(self, query: str) -> str:
        stripped_query = query.strip()
        if not stripped_query:
            return "SHOW EDGES"

        allowed_prefixes = (
            "SHOW ",
            "MATCH ",
            "DESCRIBE ",
            "LOOKUP ",
            "FETCH ",
            "YIELD ",
            "GO ",
        )
        if stripped_query.upper().startswith(allowed_prefixes):
            return stripped_query
        return "SHOW EDGES"

    def _normalize_graph_response(
        self,
        response: dict[str, Any],
        space: str,
        query: str,
    ) -> dict[str, Any]:
        if self._is_graph_shape(response):
            return response

        nested_data = response.get("data")
        if isinstance(nested_data, dict) and self._is_graph_shape(nested_data):
            return nested_data

        graph = {
            "space": space,
            "version": response.get("version", "graph_api"),
            "schema": self._schema_from_rows(response),
            "data": {
                "vertices": response.get("vertices", []),
                "edges": response.get("edges", []),
                "rows": response.get("rows", []),
                "columns": response.get("columns", []),
            },
            "query": query,
            "source": "graph_api",
            "raw": response.get("raw", ""),
        }
        return graph

    def _is_graph_shape(self, graph: dict[str, Any]) -> bool:
        return isinstance(graph.get("schema"), dict) and isinstance(graph.get("data"), dict)

    def _raise_if_nebula_error(self, response: dict[str, Any]) -> None:
        raw = str(response.get("raw", ""))
        if "[ERROR (" in raw or "SpaceNotFound" in raw:
            raise ValueError(raw)

    def _authorization_value(self, api_key: str) -> str:
        scheme = os.getenv("GRAPH_API_AUTH_SCHEME", "raw").strip().lower()
        if scheme == "bearer":
            return f"Bearer {api_key}"
        if scheme == "token":
            return f"Token {api_key}"
        return api_key

    def _user_agent(self) -> str:
        return os.getenv(
            "GRAPH_API_USER_AGENT",
            "Apipost client Runtime/+https://www.apipost.cn/",
        )

    def _schema_from_rows(self, response: dict[str, Any]) -> dict[str, Any]:
        rows = response.get("rows", [])
        columns = response.get("columns", [])
        if columns == ["Name"] and isinstance(rows, list):
            names = [row.get("Name") for row in rows if isinstance(row, dict) and row.get("Name")]
            return {"tags": {}, "edges": {str(name): {} for name in names}}
        return response.get("schema", {})

    def _enrich_graph_schema(
        self,
        base_url: str,
        space: str,
        api_key: str,
        graph: dict[str, Any],
    ) -> None:
        schema = graph.setdefault("schema", {})
        schema.setdefault("tags", {})
        schema.setdefault("edges", {})

        try:
            tags_response = self._get_json(f"{base_url}/{space}/tags", api_key)
        except Exception:
            return

        for row in tags_response.get("rows", []):
            if isinstance(row, dict) and row.get("Name"):
                schema["tags"].setdefault(str(row["Name"]), {})

    def _enrich_relevant_edges(
        self,
        base_url: str,
        space: str,
        api_key: str,
        graph: dict[str, Any],
        query: str,
    ) -> None:
        edge_names = list((graph.get("schema", {}).get("edges") or {}).keys())
        relevant_names = [name for name in edge_names if name and name in query]
        if not relevant_names and "转化" in query and "转化" in edge_names:
            relevant_names = ["转化"]

        data = graph.setdefault("data", {})
        data.setdefault("vertices", [])
        data.setdefault("edges", [])
        for edge_name in relevant_names:
            try:
                sample = self._get_json(
                    f"{base_url}/{space}/edges?type={urllib.parse.quote(edge_name)}&limit=5",
                    api_key,
                )
            except Exception:
                continue
            for row in sample.get("rows", []):
                parsed = self._parse_edge_row(row, edge_name)
                if parsed and parsed not in data["edges"]:
                    data["edges"].append(parsed)

    def _get_json(self, url: str, api_key: str) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": self._authorization_value(api_key),
                "Accept": "application/json",
                "User-Agent": self._user_agent(),
            },
            method="GET",
        )
        timeout = float(os.getenv("GRAPH_API_TIMEOUT_SECONDS", "10"))
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
        return json.loads(body) if body else {}

    def _parse_edge_row(self, row: dict[str, Any], edge_name: str) -> dict[str, str] | None:
        if not isinstance(row, dict):
            return None
        raw_value = next((str(value) for value in row.values() if value), "")
        match = re.search(r'"([^"]+)"->"([^"]+)"', raw_value)
        if not match:
            return None
        src, dst = match.groups()
        return {"src": src, "edge": edge_name, "dst": dst}

    def _strict_graph_api_enabled(self) -> bool:
        return os.getenv("GRAPH_API_STRICT", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def _auto_space_enabled(self) -> bool:
        configured = os.getenv("GRAPH_API_SPACE", "").strip()
        explicit_auto = os.getenv("GRAPH_API_AUTO_SPACE", "").strip().lower()
        if explicit_auto in {"1", "true", "yes", "on"}:
            return True
        if explicit_auto in {"0", "false", "no", "off"}:
            return False
        return not configured

    def _graph_api_space(self) -> str:
        explicit_space = os.getenv("GRAPH_API_SPACE", "").strip()
        if explicit_space:
            return explicit_space
        if self._strict_graph_api_enabled():
            return ""
        return os.getenv("NEBULA_SPACE", "medgraph").strip() or "medgraph"

    def _select_graph_api_space(
        self,
        base_url: str,
        api_key: str,
        query: str,
    ) -> tuple[str, dict[str, Any]]:
        configured_space = os.getenv("GRAPH_API_SPACE", "").strip()
        if configured_space and not self._auto_space_enabled():
            return configured_space, {
                "mode": "configured",
                "selected": configured_space,
                "candidates": [{"space": configured_space, "score": None, "matched_terms": []}],
            }

        spaces = self._available_graph_spaces(base_url, api_key)
        if configured_space and configured_space not in spaces:
            spaces.insert(0, configured_space)

        if not spaces:
            fallback_space = self._graph_api_space()
            return fallback_space, {
                "mode": "fallback",
                "selected": fallback_space,
                "candidates": [],
                "reason": "GET /spaces returned no spaces.",
            }

        scored_candidates = []
        for space in spaces:
            summary = self._graph_space_schema_summary(base_url, space, api_key)
            score, matched_terms = self._score_graph_space(query, space, summary)
            scored_candidates.append(
                {
                    "space": space,
                    "score": score,
                    "matched_terms": matched_terms,
                    "tag_count": len(summary.get("tags", [])),
                    "edge_type_count": len(summary.get("edges", [])),
                }
            )

        selected_index, selected_candidate = max(
            enumerate(scored_candidates),
            key=lambda item: (
                item[1]["score"],
                item[1]["space"] == configured_space,
                -item[0],
            ),
        )
        selected_space = str(selected_candidate["space"])
        return selected_space, {
            "mode": "auto",
            "selected": selected_space,
            "candidates": scored_candidates,
            "selected_index": selected_index,
        }

    def _available_graph_spaces(self, base_url: str, api_key: str) -> list[str]:
        try:
            response = self._get_json(f"{base_url}/spaces", api_key)
        except Exception:
            return []
        return self._extract_space_names(response)

    def _extract_space_names(self, response: dict[str, Any]) -> list[str]:
        names = []

        def add_name(value: Any) -> None:
            if value is None:
                return
            name = str(value).strip()
            if name and name not in names:
                names.append(name)

        for key in ("spaces", "space_names"):
            values = response.get(key)
            if isinstance(values, list):
                for item in values:
                    if isinstance(item, dict):
                        for field in ("Name", "name", "space", "Space", "space_name", "SpaceName"):
                            if field in item:
                                add_name(item[field])
                                break
                    else:
                        add_name(item)

        rows = response.get("rows")
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    for field in ("Name", "name", "space", "Space", "space_name", "SpaceName"):
                        if field in row:
                            add_name(row[field])
                            break
                else:
                    add_name(row)

        data = response.get("data")
        if isinstance(data, dict):
            for name in self._extract_space_names(data):
                add_name(name)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for field in ("Name", "name", "space", "Space", "space_name", "SpaceName"):
                        if field in item:
                            add_name(item[field])
                            break
                else:
                    add_name(item)

        return names

    def _graph_space_schema_summary(
        self,
        base_url: str,
        space: str,
        api_key: str,
    ) -> dict[str, list[str]]:
        tags = []
        edges = []

        try:
            tags_response = self._get_json(f"{base_url}/{space}/tags", api_key)
            tags = self._names_from_rows(tags_response)
        except Exception:
            tags = []

        try:
            edges_response = self._request_json(
                f"{base_url}/{space}/query",
                api_key,
                {"statement": "SHOW EDGES"},
            )
            edge_schema = self._schema_from_rows(edges_response)
            edges = list((edge_schema.get("edges") or {}).keys())
        except Exception:
            edges = []

        return {"tags": tags, "edges": edges}

    def _names_from_rows(self, response: dict[str, Any]) -> list[str]:
        names = []
        rows = response.get("rows", [])
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    for field in ("Name", "name", "tag", "edge"):
                        value = row.get(field)
                        if value:
                            name = str(value)
                            if name not in names:
                                names.append(name)
                            break
        return names

    def _score_graph_space(
        self,
        query: str,
        space: str,
        summary: dict[str, list[str]],
    ) -> tuple[int, list[str]]:
        score = 0
        matched_terms = []
        normalized_query = query.lower()

        weighted_terms = []
        weighted_terms.extend((edge, 10) for edge in summary.get("edges", []))
        weighted_terms.extend((tag, 6) for tag in summary.get("tags", []))
        weighted_terms.append((space, 2))

        for term, weight in weighted_terms:
            normalized_term = str(term).strip().lower()
            if normalized_term and normalized_term in normalized_query:
                score += weight
                matched_terms.append(str(term))

        query_tokens = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]{2,}", normalized_query)
        searchable_space = space.lower()
        for token in query_tokens:
            if token and token in searchable_space and token not in matched_terms:
                score += 1
                matched_terms.append(token)

        return score, matched_terms

    def _error_graph(self, query: str, error: str) -> dict[str, Any]:
        return {
            "status": "error",
            "space": self._graph_api_space(),
            "version": "graph_api",
            "schema": {"tags": {}, "edges": {}},
            "data": {"vertices": [], "edges": []},
            "query": query,
            "source": "graph_api",
            "error": error,
        }

    def _load_local_graph(self, path: str) -> dict[str, Any] | None:
        try:
            with open(path, encoding="utf-8") as file:
                graph = json.load(file)
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(graph, dict):
            return None
        if not isinstance(graph.get("schema"), dict):
            return None
        if not isinstance(graph.get("data"), dict):
            return None
        return graph

    def _fallback_graph(self, query: str, error: str) -> dict[str, Any]:
        return {
            "space": "medgraph",
            "version": "mock",
            "schema": {
                "tags": {
                    "患者": {"描述": "患者实体"},
                    "初诊医生": {"描述": "初诊接诊医生"},
                    "责任医生": {"描述": "后续责任医生"},
                    "会员": {"描述": "已转化会员"},
                },
                "edges": {
                    "首次接诊": {"描述": "患者与初诊医生关系"},
                    "指定": {"描述": "患者与责任医生关系"},
                    "转化": {"描述": "患者转化为会员关系"},
                },
            },
            "data": {
                "vertices": [
                    {"vid": "patient", "tag": "患者"},
                    {"vid": "first_visit_doctor", "tag": "初诊医生"},
                    {"vid": "responsible_doctor", "tag": "责任医生"},
                    {"vid": "member", "tag": "会员"},
                ],
                "edges": [
                    {"src": "patient", "edge": "首次接诊", "dst": "first_visit_doctor"},
                    {"src": "patient", "edge": "指定", "dst": "responsible_doctor"},
                    {"src": "patient", "edge": "转化", "dst": "member"},
                ],
            },
            "query": query,
            "source": "mock_fallback",
            "error": error,
        }
