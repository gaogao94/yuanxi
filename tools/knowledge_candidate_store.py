"""
KnowledgeCandidateStore：经验知识候选池存储

【定位】
这个存储用于接收 Agent3 输出的“经验沉淀候选项”。
第一版只做记录和待审，不直接写入正式知识库。

【为什么不直接入正式知识库】
- 经验条目在第一版里仍然可能有误判或粒度不稳定；
- 人工筛选可以先验证内容质量，再决定是否沉淀为正式规则。
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_KNOWLEDGE_CANDIDATE_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "knowledge_candidates.json"
)


class KnowledgeCandidateStore:
    """
    经验知识候选池。

    每条条目默认都是 pending_review，强调“待人工确认后再入库”。
    """

    _file_path: Path = DEFAULT_KNOWLEDGE_CANDIDATE_FILE
    _lock = threading.RLock()

    @classmethod
    def init(cls, file_path: str | None = None) -> None:
        with cls._lock:
            if file_path:
                cls._file_path = Path(file_path)
            cls._file_path.parent.mkdir(parents=True, exist_ok=True)
            if not cls._file_path.exists():
                cls._save([])

    @classmethod
    def add_many(cls, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        with cls._lock:
            records = cls._load()
            enriched_records: list[dict[str, Any]] = []
            for candidate in candidates:
                enriched = {
                    "candidate_id": f"knowledge-candidate-{len(records) + len(enriched_records) + 1}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "review_status": "pending_review",
                    **candidate,
                }
                enriched_records.append(enriched)
            records.extend(enriched_records)
            cls._save(records)
            return enriched_records

    @classmethod
    def get_all(cls) -> list[dict[str, Any]]:
        with cls._lock:
            return cls._load()

    @classmethod
    def _load(cls) -> list[dict[str, Any]]:
        if not cls._file_path.exists():
            return []
        try:
            with open(cls._file_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            return loaded if isinstance(loaded, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    @classmethod
    def _save(cls, records: list[dict[str, Any]]) -> None:
        cls._file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cls._file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
