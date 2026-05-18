"""
ProblemStore：共享问题收集器（JSON 文件持久化）

【作用】
这个模块是"公共问题收集器"的底层存储层，负责把问题数据持久化到 JSON 文件中。
它是整个复盘体系的数据底座，Agent1 和 Agent2 上报的问题最终都存在这里，
Agent3 复盘时从这里读取。

【数据流转】
Agent1/Agent2 调用 ProblemReporterTool
    ↓
ProblemStore.add() → 写入 data/problem_reports.json
    ↓
Agent3 调用 ProblemCollectorReader
    ↓
ProblemStore.get_all() / filter() → 从 JSON 文件读取

【为什么用 JSON 文件而不是数据库】
- 第一版不需要真实数据库，零依赖、零配置
- JSON 文件人类可直接阅读和修改，方便调试
- 后续可以无缝升级为 SQLite 或真实数据库
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


# 默认存储路径：项目根目录下的 data 文件夹
# 例如：D:/app/work/wishSpace/workspace/yuanxi/data/problem_reports.json
DEFAULT_STORAGE_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_STORAGE_FILE = DEFAULT_STORAGE_DIR / "problem_reports.json"


class ProblemStore:
    """
    共享问题存储器（类级别，全局唯一）

    使用类方法和类变量实现，所有 Agent 共享同一个存储实例。
    后端使用 JSON 文件持久化，程序重启后数据不丢失。

    数据结构（每条记录）：
    {
        "id": "prob-1-20260518145600",       # 自动生成的唯一 ID
        "timestamp": "2026-05-18T14:56:00",  # 自动记录的上报时间
        "agent": "Agent2",                   # 上报问题的 Agent 名称
        "stage": "data_fetch",               # 出现问题的阶段
        "problem": "字段名不存在",            # 问题描述
        "solution": "将 A 替换为 B",          # 解决方案
        "severity": "medium"                 # 严重程度：high / medium / low
    }
    """

    # 存储文件的路径，可通过 init() 方法自定义
    _file_path: Path = DEFAULT_STORAGE_FILE

    # ── 初始化 ──────────────────────────────────────────────

    @classmethod
    def init(cls, file_path: Optional[str] = None) -> None:
        """
        初始化存储，指定存储路径并确保文件存在。

        参数：
            file_path: 可选的 JSON 文件路径，不传则使用默认路径
        """
        if file_path:
            cls._file_path = Path(file_path)
        # 确保 data 目录存在
        cls._file_path.parent.mkdir(parents=True, exist_ok=True)
        # 如果文件不存在，创建一个空的 JSON 数组文件
        if not cls._file_path.exists():
            cls._save([])

    # ── 写操作 ──────────────────────────────────────────────

    @classmethod
    def add(cls, record: dict) -> dict:
        """
        添加一条问题记录。

        record 中应包含：
            - agent: 上报者名称（如 "Agent1" 或 "Agent2"）
            - stage: 问题出现阶段
            - problem: 问题描述
            - solution: 解决方案
            - severity: 严重程度

        返回：
            补充了 id 和时间戳的完整记录
        """
        # 先读取现有的所有记录
        records = cls._load()

        # 自动补充 ID 和上报时间戳
        enriched = {
            "id": f"prob-{len(records) + 1}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **record,  # 将传入的字段合并进来（注意：放在后面可以覆盖前面）
        }
        records.append(enriched)
        cls._save(records)
        return enriched

    @classmethod
    def clear(cls) -> None:
        """清空所有记录，相当于重置存储"""
        cls._save([])

    # ── 读操作 ──────────────────────────────────────────────

    @classmethod
    def get_all(cls) -> list:
        """
        获取全部问题记录。

        返回：
            所有记录的列表，如果没有记录则返回空列表
        """
        return cls._load()

    @classmethod
    def count(cls) -> int:
        """
        获取记录总数。

        返回：
            当前存储的问题记录数量
        """
        return len(cls._load())

    @classmethod
    def filter(cls, **kwargs) -> list:
        """
        按字段过滤记录，支持任意字段组合。

        用法：
            ProblemStore.filter(agent='Agent2')           # 只看 Agent2 的问题
            ProblemStore.filter(severity='high')          # 只看高严重度问题
            ProblemStore.filter(agent='Agent2', stage='data_fetch')  # 组合过滤

        参数：
            **kwargs: 键值对，键是字段名，值是期望的匹配值

        返回：
            过滤后的记录列表
        """
        records = cls._load()
        results = records
        for key, value in kwargs.items():
            results = [r for r in results if r.get(key) == value]
        return results

    # ── 内部方法 ────────────────────────────────────────────

    @classmethod
    def _load(cls) -> list:
        """
        从 JSON 文件加载全部记录（内部方法）。

        如果文件不存在或损坏，返回空列表而不是报错，
        保证系统在异常情况下也能正常运行。
        """
        if not cls._file_path.exists():
            return []
        try:
            with open(cls._file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            # JSON 文件损坏时静默处理，返回空列表
            return []

    @classmethod
    def _save(cls, records: list) -> None:
        """
        将记录列表写入 JSON 文件（内部方法）。

        ensure_ascii=False 保证中文能正常显示，不会转义成 \\uXXXX。
        indent=2 让 JSON 文件可读性更好，方便人工查看。
        """
        cls._file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cls._file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
