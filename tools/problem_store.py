"""
ProblemStore：共享问题收集器（JSON 文件持久化）

【作用】
这个模块是"公共问题收集器"的底层存储层，负责把问题数据持久化到 JSON 文件中。
它是整个复盘体系的数据底座，Agent1 和 Agent2 上报的问题最终都存在这里，
Agent3 复盘时从这里读取。

【本轮升级点】
相比第一版“直接读整个 JSON、直接整文件覆盖写回”的实现，这一版重点补了三类能力：
1. 并发安全：至少保证同一 Python 进程内多个调用方不会同时写坏文件。
2. 原子落盘：先写临时文件，再 replace 到正式文件，降低半写入状态的风险。
3. 损坏自愈：如果 JSON 文件已经损坏，不再静默返回空列表，而是备份坏文件并重建空存储。

【为什么还保留 JSON 而不是直接上数据库】
- 当前项目依然处于快速演进阶段，JSON 便于直接观察和调试。
- 这次优化的目标是先补“可靠性底线”，而不是引入新的运行依赖。
- 等问题记录量和并发量继续上来，再切到 SQLite 会更顺滑，因为接口形态已经更稳定。
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


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

    # 存储文件的路径，可通过 init() 方法自定义。
    # 之所以保留为类变量，是为了让整个进程内所有 Agent 共用同一份问题池，
    # 避免不同调用方各自 new 实例后写到不同地方。
    _file_path: Path = DEFAULT_STORAGE_FILE

    # 进程内写锁：
    # 这把锁不能跨进程，但可以解决“同一个 Python 进程里多个 Agent/线程同时写 JSON”
    # 时出现的 interleaving 问题。考虑到当前 workflow 主要跑在单进程内，这个改造
    # 已经能显著降低数据竞争风险。
    _lock = threading.RLock()

    # 最近一次读取/写入时观察到的元信息，供上层调试或复盘使用。
    # 我们把这些状态留在内存里，而不是混到业务 records 中，
    # 这样既不污染问题记录格式，也方便后续暴露到监控接口。
    _last_meta: dict[str, Any] = {
        "storage_status": "uninitialized",
        "last_error": "",
        "last_recovered_at": "",
        "last_backup_path": "",
    }

    # ── 初始化 ──────────────────────────────────────────────

    @classmethod
    def init(cls, file_path: Optional[str] = None) -> None:
        """
        初始化存储，指定存储路径并确保文件存在。

        参数：
            file_path: 可选的 JSON 文件路径，不传则使用默认路径
        """
        with cls._lock:
            if file_path:
                cls._file_path = Path(file_path)
            # 初始化阶段就把目录建好，避免后续第一次写入时各处重复处理目录不存在的问题。
            cls._file_path.parent.mkdir(parents=True, exist_ok=True)
            # 如果文件不存在，就创建一个空数组文件，并把状态记成 healthy。
            if not cls._file_path.exists():
                cls._save([])
            else:
                cls._last_meta["storage_status"] = "healthy"

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
        with cls._lock:
            # 先读取现有的所有记录；如果底层文件损坏，_load() 会负责恢复并记录元信息。
            records = cls._load()

            # 自动补充 ID 和上报时间戳。
            # 这里仍然延续“递增序号 + UTC 时间”的组合形式，原因是：
            # 1. 人眼可读，排查时比纯随机 UUID 更直观；
            # 2. 在单进程串行写前提下足够稳定；
            # 3. 后续若迁移到数据库，也能平滑保留这套展示 ID。
            enriched = {
                "id": f"prob-{len(records) + 1}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **record,
            }
            records.append(enriched)
            cls._save(records)
            return enriched

    @classmethod
    def clear(cls) -> None:
        """清空所有记录，相当于重置存储"""
        with cls._lock:
            cls._save([])

    # ── 读操作 ──────────────────────────────────────────────

    @classmethod
    def get_all(cls) -> list:
        """
        获取全部问题记录。

        返回：
            所有记录的列表，如果没有记录则返回空列表
        """
        with cls._lock:
            return cls._load()

    @classmethod
    def count(cls) -> int:
        """
        获取记录总数。

        返回：
            当前存储的问题记录数量
        """
        with cls._lock:
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
        with cls._lock:
            records = cls._load()
            results = records
            for key, value in kwargs.items():
                results = [r for r in results if r.get(key) == value]
            return results

    @classmethod
    def get_meta(cls) -> dict[str, Any]:
        """
        获取 ProblemStore 最近一次运行状态的元信息。

        这个接口主要给 Agent3 或调试脚本用：
        - 如果文件损坏后发生过自动恢复，可以从这里看到 backup 路径；
        - 如果上一次读写有异常，也能知道不是“真的没有问题记录”，
          而是存储层出过问题。
        """
        with cls._lock:
            return dict(cls._last_meta)

    # ── 内部方法 ────────────────────────────────────────────

    @classmethod
    def _load(cls) -> list:
        """
        从 JSON 文件加载全部记录（内部方法）。

        如果文件不存在或损坏，返回空列表而不是报错，
        保证系统在异常情况下也能正常运行。
        """
        if not cls._file_path.exists():
            cls._last_meta["storage_status"] = "missing"
            cls._last_meta["last_error"] = ""
            return []
        try:
            with open(cls._file_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except json.JSONDecodeError as exc:
            # 和第一版最大的区别在这里：
            # 以前文件一坏就直接返回空列表，上层根本分不清“确实没有记录”还是“文件已经炸了”。
            # 现在我们会先备份坏文件，再重建空存储，并把恢复动作写进 meta。
            cls._recover_from_corruption(exc)
            return []
        except OSError as exc:
            cls._last_meta["storage_status"] = "io_error"
            cls._last_meta["last_error"] = str(exc)
            return []

        if not isinstance(loaded, list):
            # 文件即使能被 json 解析，也可能被手改成 dict/str 等错误结构。
            # 这里按“结构损坏”处理，和 JSON 语法损坏一样走恢复逻辑。
            cls._recover_from_corruption(
                ValueError("problem_reports.json 顶层结构不是 list")
            )
            return []

        cls._last_meta["storage_status"] = "healthy"
        cls._last_meta["last_error"] = ""
        return loaded

    @classmethod
    def _save(cls, records: list) -> None:
        """
        将记录列表写入 JSON 文件（内部方法）。

        ensure_ascii=False 保证中文能正常显示，不会转义成 \\uXXXX。
        indent=2 让 JSON 文件可读性更好，方便人工查看。
        """
        cls._file_path.parent.mkdir(parents=True, exist_ok=True)

        # 原子写入的关键思路：
        # 1. 先把完整内容写到同目录下的临时文件；
        # 2. flush + fsync，尽量确保数据已经真正落到磁盘；
        # 3. 使用 replace 原子替换正式文件。
        # 这样即使程序在写入中途崩掉，也更可能留下“旧文件 or 新文件”二选一，
        # 而不是半截 JSON。
        temp_path = cls._file_path.with_suffix(cls._file_path.suffix + ".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
            f.flush()
            # 某些平台上 fsync 可能不可用或没有必要，所以这里容错处理；
            # 但在大多数本地文件系统中，它能进一步降低断电时的数据丢失概率。
            try:
                import os

                os.fsync(f.fileno())
            except OSError:
                pass

        temp_path.replace(cls._file_path)
        cls._last_meta["storage_status"] = "healthy"
        cls._last_meta["last_error"] = ""

    @classmethod
    def _recover_from_corruption(cls, exc: Exception) -> None:
        """
        处理存储文件损坏的恢复逻辑。

        恢复策略故意做得很保守：
        1. 绝不直接覆盖坏文件，先备份；
        2. 备份文件名带 UTC 时间戳，方便人工回溯；
        3. 恢复后重建一个空数组文件，保证主流程还能继续写入新的问题记录。
        """
        backup_path = cls._build_backup_path()
        cls._last_meta["storage_status"] = "recovered_from_corruption"
        cls._last_meta["last_error"] = str(exc)
        cls._last_meta["last_recovered_at"] = datetime.now(timezone.utc).isoformat()
        cls._last_meta["last_backup_path"] = str(backup_path)

        try:
            if cls._file_path.exists():
                cls._file_path.replace(backup_path)
        except OSError:
            # 如果连备份都失败，我们至少把状态写出来，避免上层误判。
            cls._last_meta["storage_status"] = "corruption_backup_failed"
        finally:
            # 无论备份成功与否，都尝试重建一份空存储，保证系统还能继续接收新记录。
            cls._file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cls._file_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    @classmethod
    def _build_backup_path(cls) -> Path:
        """
        生成损坏文件备份路径。

        备份文件仍然放在原目录，原因是：
        - 更容易和当前正式文件一起排查；
        - 不依赖额外的备份目录配置；
        - Git 忽略策略也更容易统一处理。
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return cls._file_path.with_suffix(cls._file_path.suffix + f".corrupt.{timestamp}.bak")
