"""
KnowledgeStore：知识经验库（JSON 文件持久化）

【作用】
这个模块是"经验知识库"的底层存储层，负责把 Agent3 复盘沉淀的经验持久化到 JSON 文件中。
每次任务复盘沉淀的新经验会写入这里，后续任务可以查阅已有的经验，
避免重复沉淀，也支持 Agent1/Agent2 直接调用查询。

【数据流转】
Agent3 复盘 → 沉淀新经验（口径定义、踩坑记录、分析模式、行动项）
    ↓
KnowledgeStore.add() → 写入 data/knowledge_base.json
    ↓
后续 Agent3/Agent1/Agent2 查询 → KnowledgeStore.search() 检索已有知识

【数据结构（每条记录）】
{
    "id": "kb-metric_definition-20260518-001",   # 自动生成的唯一 ID
    "category": "metric_definition",             # 分类
    "title": "初诊转化率标准口径",                 # 标题
    "content": "初诊转化率 = 有消费记录的首诊患者数 / 总首诊患者数 × 100%",  # 正文
    "tags": ["转化率", "首诊", "口径"],            # 标签，用于检索
    "source_task": "2026年4月上海门店转化率分析",   # 来源任务
    "source_agent": "Agent3",                     # 来源 Agent
    "created_at": "2026-05-18T14:56:00Z",         # 创建时间
    "updated_at": "2026-05-18T14:56:00Z"          # 更新时间
}

【分类说明】
- metric_definition: 标准指标口径定义
- pitfall: 常见踩坑记录与规避方法
- analysis_pattern: 有效的分析模式/框架
- action_item: 下轮改进行动清单
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


# 默认存储路径：项目根目录下的 data 文件夹
DEFAULT_STORAGE_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_STORAGE_FILE = DEFAULT_STORAGE_DIR / "knowledge_base.json"


# 允许的经验分类，超出时会自动归类为 other
VALID_CATEGORIES = {"metric_definition", "pitfall", "analysis_pattern", "action_item", "other"}


class KnowledgeStore:
    """
    知识经验库（类级别，全局唯一）

    使用类方法和类变量实现，所有 Agent 共享同一个知识库实例。
    后端使用 JSON 文件持久化，程序重启后数据不丢失。

    支持按分类、标签、关键词搜索，方便后续 Agent1/Agent2 直接查询。
    """

    # 存储文件的路径，可通过 init() 方法自定义
    _file_path: Path = DEFAULT_STORAGE_FILE

    # ── 初始化 ──────────────────────────────────────────────

    @classmethod
    def init(cls, file_path: Optional[str] = None) -> None:
        """
        初始化知识库，指定存储路径并确保文件存在。

        参数：
            file_path: 可选的 JSON 文件路径，不传则使用默认路径
        """
        if file_path:
            cls._file_path = Path(file_path)
        cls._file_path.parent.mkdir(parents=True, exist_ok=True)
        if not cls._file_path.exists():
            cls._save({"records": [], "version": 1})

    # ── 写操作 ──────────────────────────────────────────────

    @classmethod
    def add(cls, record: dict) -> dict:
        """
        添加一条知识记录。

        record 中应包含：
            - category: 分类（metric_definition | pitfall | analysis_pattern | action_item）
            - title: 标题
            - content: 正文内容
            - tags: 标签列表
            - source_task: 来源任务描述
            - source_agent: 来源 Agent 名称

        返回：
            补充了 id 和时间戳的完整记录
        """
        data = cls._load()
        records = data["records"]

        # 校验并修正分类
        category = record.get("category", "other")
        if category not in VALID_CATEGORIES:
            category = "other"

        # 自动生成 ID：分类 + 日期 + 序号
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        seq = len([r for r in records if r["category"] == category]) + 1
        record_id = f"kb-{category}-{date_str}-{seq:03d}"

        # 补充元信息
        enriched = {
            "id": record_id,
            "category": category,
            "title": record.get("title", "未命名"),
            "content": record.get("content", ""),
            "tags": record.get("tags", []),
            "source_task": record.get("source_task", ""),
            "source_agent": record.get("source_agent", "Agent3"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        records.append(enriched)
        data["records"] = records
        cls._save(data)
        return enriched

    @classmethod
    def clear(cls) -> None:
        """清空所有知识记录"""
        cls._save({"records": [], "version": 1})

    # ── 读操作 ──────────────────────────────────────────────

    @classmethod
    def get_all(cls) -> list:
        """
        获取全部知识记录。

        返回：
            所有记录的列表，如果没有记录则返回空列表
        """
        data = cls._load()
        return data["records"]

    @classmethod
    def count(cls) -> int:
        """
        获取记录总数。

        返回：
            当前知识库的记录数量
        """
        data = cls._load()
        return len(data["records"])

    @classmethod
    def filter(cls, **kwargs) -> list:
        """
        按字段精确匹配过滤。

        用法：
            KnowledgeStore.filter(category='metric_definition')  # 只看口径定义
            KnowledgeStore.filter(source_agent='Agent3')         # 只看 Agent3 沉淀的

        参数：
            **kwargs: 键值对，键是字段名，值是期望的匹配值

        返回：
            过滤后的记录列表
        """
        data = cls._load()
        results = data["records"]
        for key, value in kwargs.items():
            results = [r for r in results if r.get(key) == value]
        return results

    @classmethod
    def search_by_tag(cls, tag: str) -> list:
        """
        按标签搜索知识记录。

        用法：
            KnowledgeStore.search_by_tag('转化率')  # 查找所有含"转化率"标签的记录

        参数：
            tag: 标签名称（大小写敏感）

        返回：
            匹配的记录列表
        """
        data = cls._load()
        return [r for r in data["records"] if tag in r.get("tags", [])]

    @classmethod
    def search_by_keyword(cls, keyword: str) -> list:
        """
        按关键词全文搜索（在标题和正文中搜索）。

        用法：
            KnowledgeStore.search_by_keyword('字段名')  # 查找标题或正文中含"字段名"的记录

        参数：
            keyword: 搜索关键词

        返回：
            匹配的记录列表，按相关度排序（标题匹配优先于正文匹配）
        """
        data = cls._load()
        keyword_lower = keyword.lower()

        def _relevance(record: dict) -> int:
            """计算相关度分数：标题匹配 2 分，正文匹配 1 分"""
            score = 0
            if keyword_lower in record.get("title", "").lower():
                score += 2
            if keyword_lower in record.get("content", "").lower():
                score += 1
            return score

        results = [r for r in data["records"] if _relevance(r) > 0]
        # 按相关度降序排列
        results.sort(key=_relevance, reverse=True)
        return results

    @classmethod
    def count_by_category(cls) -> dict:
        """
        按分类统计记录数量。

        返回：
            字典，如 {"metric_definition": 3, "pitfall": 5, ...}
        """
        data = cls._load()
        stats = {cat: 0 for cat in VALID_CATEGORIES}
        for r in data["records"]:
            cat = r.get("category", "other")
            if cat in stats:
                stats[cat] += 1
            else:
                stats["other"] += 1
        return stats

    # ── 格式化输出 ──────────────────────────────────────────

    @classmethod
    def format_summary(cls) -> str:
        """
        生成知识库概览文本（Markdown 格式）。

        返回：
            知识库概要，包含各类记录数量和总条数
        """
        stats = cls.count_by_category()
        total = cls.count()

        category_names = {
            "metric_definition": "标准指标口径定义",
            "pitfall": "常见踩坑记录",
            "analysis_pattern": "有效分析模式",
            "action_item": "改进行动项",
            "other": "其他",
        }

        lines = [f"知识库概览（共 {total} 条记录）：\n"]
        for cat, name in category_names.items():
            count = stats.get(cat, 0)
            if count > 0:
                lines.append(f"- {name}：{count} 条")

        if total == 0:
            lines.append("（暂无记录）")

        return "\n".join(lines)

    # ── 内部方法 ────────────────────────────────────────────

    @classmethod
    def _load(cls) -> dict:
        """
        从 JSON 文件加载全部数据（内部方法）。

        如果文件不存在或损坏，返回空结构而不是报错。
        """
        if not cls._file_path.exists():
            return {"records": [], "version": 1}
        try:
            with open(cls._file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"records": [], "version": 1}

    @classmethod
    def _save(cls, data: dict) -> None:
        """
        将数据写入 JSON 文件（内部方法）。

        ensure_ascii=False 保证中文能正常显示。
        indent=2 让 JSON 文件可读性更好。
        """
        cls._file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cls._file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
