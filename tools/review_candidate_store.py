"""
ReviewCandidateStore：整改建议候选池存储

【定位】
这不是“自动执行整改”的队列，而是 Agent3 复盘后沉淀出的“待人工审核建议池”。
第一版只负责记录，不做自动修改图谱、流程或代码。

【为什么单独建一个存储】
- 风险对象是本轮复盘结果的一部分，偏运行时产物；
- 候选池是跨轮次积累的人工审核入口，偏治理台账。
把两者拆开后，后续更容易做：
1. 人工审核状态流转
2. 去重和合并
3. 审核通过后再转正式落地动作
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REVIEW_CANDIDATE_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "review_candidates.json"
)


class ReviewCandidateStore:
    """
    整改建议候选池。

    每条记录默认都是 pending_review，明确表达“这只是候选项，不是已批准动作”。
    """

    _file_path: Path = DEFAULT_REVIEW_CANDIDATE_FILE
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
                    "candidate_id": f"review-candidate-{len(records) + len(enriched_records) + 1}",
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
