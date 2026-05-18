"""
ProblemStore：共享问题收集器（JSON 文件持久化）
Agent1 和 Agent2 可以通过 ProblemReporterTool 写入问题，
Agent3 可以通过 ProblemCollectorReader 读取分析。
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


# 默认存储路径：项目根目录下的 data 文件夹
DEFAULT_STORAGE_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_STORAGE_FILE = DEFAULT_STORAGE_DIR / "problem_reports.json"


class ProblemStore:
    """线程安全的类级别问题存储，后端采用 JSON 文件持久化"""

    _file_path: Path = DEFAULT_STORAGE_FILE

    # ── 初始化 ──────────────────────────────────────────────

    @classmethod
    def init(cls, file_path: Optional[str] = None) -> None:
        """指定存储路径，并确保文件存在"""
        if file_path:
            cls._file_path = Path(file_path)
        cls._file_path.parent.mkdir(parents=True, exist_ok=True)
        if not cls._file_path.exists():
            cls._save([])

    # ── 写操作 ──────────────────────────────────────────────

    @classmethod
    def add(cls, record: dict) -> dict:
        """添加一条问题记录，返回带 id 和时间戳的完整记录"""
        records = cls._load()

        # 补充元信息
        enriched = {
            "id": f"prob-{len(records) + 1}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **record,  # 应包含 agent, stage, problem, solution, severity
        }
        records.append(enriched)
        cls._save(records)
        return enriched

    @classmethod
    def clear(cls) -> None:
        """清空所有记录"""
        cls._save([])

    # ── 读操作 ──────────────────────────────────────────────

    @classmethod
    def get_all(cls) -> list:
        """获取全部问题记录"""
        return cls._load()

    @classmethod
    def count(cls) -> int:
        """获取记录总数"""
        return len(cls._load())

    @classmethod
    def filter(cls, **kwargs) -> list:
        """按字段过滤，例如 filter(agent='Agent2', severity='high')"""
        records = cls._load()
        results = records
        for key, value in kwargs.items():
            results = [r for r in results if r.get(key) == value]
        return results

    # ── 内部方法 ────────────────────────────────────────────

    @classmethod
    def _load(cls) -> list:
        """从 JSON 文件加载全部记录"""
        if not cls._file_path.exists():
            return []
        try:
            with open(cls._file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    @classmethod
    def _save(cls, records: list) -> None:
        """将记录列表写入 JSON 文件"""
        cls._file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cls._file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
