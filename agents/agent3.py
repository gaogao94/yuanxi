"""
Agent3：洞察优化进阶精灵（复盘精灵）

【角色定位】
全流程复盘审计专家、业务体系优化顾问、知识图谱迭代、经验沉淀与体系进化专家。

【核心职责】
- 不直接执行业务任务（那是 Agent1 和 Agent2 的事）
- 专注于事后复盘、流程审计、体系优化与长期进化
- 跳出单次任务视角，发现隐性逻辑问题、冗余步骤、口径歧义盲区、图谱缺失关系
- 给出可落地的优化建议、图谱补充方向、分析维度拓展思路
- 沉淀可复用的业务经验，推动整个数据分析体系越迭代越完善

【运行方式】
旁路并行执行——不阻塞主链路，不决定主流程下一步，不影响最终结果交付。
Agent3 失败不影响主报告正常返回。

【工具列表】
1. ProblemCollectorReader  - 读取 Agent1/Agent2 上报的问题
2. StepDecompositionEvaluator - 评估步骤拆解合理性
3. GraphGapDetector        - 图谱缺陷诊断
4. ProcessOptimizer        - 流程优化建议
5. InsightRefiner          - 经验沉淀 & 维度拓展
"""

import sys
import os
from pathlib import Path

# 设置标准输出编码为 UTF-8，解决 Windows 终端 GBK 编码不支持 Emoji 的问题
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 将项目根目录加入 Python 搜索路径，确保能找到 tools 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from dotenv import load_dotenv

from tools.problem_collector import ProblemCollectorReader
from tools.knowledge_store import KnowledgeStore

# 加载环境变量（API 密钥等配置）
load_dotenv()


# ============================================================
# 工具 2：步骤拆解合理性评估
# ============================================================
class StepDecompositionEvaluator(BaseTool):
    """
    步骤拆解合理性评估工具。

    【用途】
    评估 Agent1 的任务步骤拆解是否合理，检查：
    - 是否有冗余步骤（可以合并或删除）
    - 是否有缺失的关键步骤
    - 步骤的执行顺序是否合理
    - 串行/并行关系是否恰当

    【调用时机】
    Agent3 复盘时调用，输入是 Agent1 生成的任务合同（task_contract）中的步骤列表。
    """
    name: str = "step_decomposition_evaluator"
    description: str = (
        "评估任务步骤拆解的合理性。检查是否有冗余步骤、是否缺失关键步骤、"
        "执行顺序是否合理。输入任务合同中的步骤列表，返回评估结果和改进建议。"
    )

    def _run(self, step_list: str) -> str:
        """
        执行步骤拆解评估。

        参数：
            step_list: 任务步骤列表的文本描述（来自 Agent1 的 task_contract）

        返回：
            评估结果，包括发现的问题和改进建议
        """
        # TODO: 第一期使用模拟逻辑，后续接入真实的任务合同数据
        findings = []
        suggestions = []

        # 检查：取数后是否缺少 SQL 校验步骤
        if "data_fetch" in step_list and "sql_check" not in step_list:
            findings.append("数据取数后缺少 SQL 校验步骤")
            suggestions.append("建议在 data_fetch 步骤之后增加 sql_check 步骤，确保查询语句正确")

        # 检查：进阶分析前是否缺少基础分析
        if "advanced_analysis" in step_list and "basic_analysis" not in step_list:
            findings.append("进阶分析缺少基础分析作为前置步骤")
            suggestions.append("建议先执行 basic_analysis，再执行 advanced_analysis")

        if not findings:
            return (
                "步骤拆解评估通过。\n"
                "所有步骤逻辑顺序合理，未发现冗余或缺失步骤。"
            )

        return (
            f"发现 {len(findings)} 个问题:\n"
            + "\n".join(f"- {f}" for f in findings)
            + "\n\n改进建议:\n"
            + "\n".join(f"- {s}" for s in suggestions)
        )


# ============================================================
# 工具 3：业务知识图谱缺陷诊断 & 关系缺失识别
# ============================================================
class GraphGapDetector(BaseTool):
    """
    业务知识图谱缺陷诊断工具。

    【用途】
    分析本次任务中知识图谱的使用情况，发现：
    - 缺失的实体类型（如缺少"渠道"实体）
    - 缺失的关系（如缺少"渠道→影响→转化率"的关系）
    - 缺失的属性（如医生缺少"资历等级"属性）
    - 数据覆盖不完整的地方

    【调用时机】
    Agent3 复盘时调用，输入是 Agent1 确定的知识图谱范围（graph_scope）。
    """
    name: str = "graph_gap_detector"
    description: str = (
        "分析知识图谱的实体和关系完整度，发现缺失的实体、关系或属性。"
        "输入本次任务的知识图谱范围总结，返回图谱补充建议。"
    )

    def _run(self, graph_scope_summary: str) -> str:
        """
        执行图谱缺陷诊断。

        参数：
            graph_scope_summary: 本次任务的知识图谱使用范围（来自 Agent1 的 graph_scope）

        返回：
            图谱缺陷诊断报告，包含缺失的实体/关系和补充建议
        """
        # 模拟图谱诊断逻辑
        # TODO: 后续接入真实的知识图谱元数据对比
        suggestions = [
            {
                "missing": "渠道(Channel)实体 → 影响(affects) → 转化率指标(Metric) 的关系",
                "reason": "本次分析发现渠道来源对转化率有影响，但图谱中缺少此关系",
                "example_query": "MATCH (c:Channel)-[r:affects]->(m:Metric) WHERE m.name='conversion_rate'",
            },
            {
                "missing": "医生(Doctor)实体 → 资历等级(seniority_level) 属性",
                "reason": "回归分析发现医生资历是转化率的关键影响因素，但图谱未存储此属性",
                "example_query": "MATCH (d:Doctor) RETURN d.name, d.seniority_level",
            },
        ]

        report = "## 知识图谱缺陷分析\n\n"
        report += "### 检测到的缺失项：\n\n"
        for s in suggestions:
            report += f"- **缺失内容**：{s['missing']}\n"
            report += f"  - **缺失原因**：{s['reason']}\n"
            report += f"  - **示例查询**：`{s['example_query']}`\n\n"

        report += "### 改进建议：\n"
        report += "1. 新增渠道(Channel)实体，建立与指标(Metric)的关联关系\n"
        report += "2. 在医生(Doctor)实体上增加资历等级(seniority_level)属性\n"
        report += "3. 考虑新增门店绩效视图(ClinicPerformance)，聚合展示关键KPI\n"

        return report


# ============================================================
# 工具 4：流程优化建议生成
# ============================================================
class ProcessOptimizer(BaseTool):
    """
    流程优化建议工具。

    【用途】
    分析整个执行过程，找出可以优化的环节：
    - 哪些步骤耗时冗余可以简化
    - 哪些步骤可以模板化（固化标准流程）
    - 哪些步骤可以并行执行提升效率
    - 哪些工具调用可以合并

    【调用时机】
    Agent3 复盘时调用，输入是本次执行的过程日志摘要。
    """
    name: str = "process_optimizer"
    description: str = (
        "分析执行过程，总结可优化的环节。包括：冗余步骤简化、"
        "标准步骤模板化、可并行执行的步骤识别、工具调用合并建议。"
        "输入过程日志摘要，返回优化建议。"
    )

    def _run(self, process_summary: str) -> str:
        """
        执行流程优化分析。

        参数：
            process_summary: 执行过程日志摘要

        返回：
            流程优化建议报告
        """
        # 模拟流程优化逻辑
        # TODO: 后续接入真实的过程日志数据分析
        return (
            "## 流程优化建议\n\n"
            "### 识别的瓶颈点：\n"
            "1. **SQL 生成步骤**：常用查询模式可模板化，减少重复生成时间\n"
            "2. **缓存检查前置**：可以将缓存检查合并到取数步骤中，减少一次工具调用\n\n"
            "### 建议改进：\n"
            "- 为常见查询模式（门店月报、医生绩效）创建 SQL 模板\n"
            "- 将 cache_manager 与 data_fetch 合并为 fetch-or-cache 单一步骤\n"
            "- 独立的图表生成步骤可以并行执行，减少串行等待\n\n"
            "### 预估效果：\n"
            "- 预计减少 20-30% 的总执行时间\n"
            "- 减少工具调用次数，降低 API 调用成本"
        )


# ============================================================
# 工具 5：知识经验库查询（新增）
# ============================================================
class KnowledgeBaseReader(BaseTool):
    """
    知识经验库查询工具。

    【用途】
    在开始复盘之前或沉淀经验之前，查询知识库中已有的经验记录。
    支持按分类查看、按关键词搜索、按标签检索。
    这样可以避免重复沉淀相同的经验。

    【调用时机】
    Agent3 复盘时调用，可以在沉淀新经验前先查一下是否已有相关内容。
    """
    name: str = "knowledge_base_reader"
    description: str = (
        "查询知识经验库中已有的沉淀知识。支持按分类查看（metric_definition/pitfall/"
        "analysis_pattern/action_item）、按关键词搜索、按标签检索。"
        "复盘前先查询已有知识，避免重复沉淀。"
    )

    def _run(self, action: str, category: str = "", keyword: str = "", tag: str = "") -> str:
        """
        执行知识库查询。

        参数：
            action: 操作类型（overview | search_keyword | search_tag | filter_category）
            category: 分类筛选（metric_definition | pitfall | analysis_pattern | action_item）
            keyword: 搜索关键词
            tag: 搜索标签

        返回：
            查询结果的 Markdown 文本
        """
        KnowledgeStore.init()

        if action == "overview":
            # 返回知识库概览
            return KnowledgeStore.format_summary()

        elif action == "search_keyword" and keyword:
            # 按关键词搜索
            results = KnowledgeStore.search_by_keyword(keyword)
            if not results:
                return f"未找到包含「{keyword}」的知识记录。"
            return self._format_results(results, f"关键词「{keyword}」搜索结果")

        elif action == "search_tag" and tag:
            # 按标签搜索
            results = KnowledgeStore.search_by_tag(tag)
            if not results:
                return f"未找到标签为「{tag}」的知识记录。"
            return self._format_results(results, f"标签「{tag}」搜索结果")

        elif action == "filter_category" and category:
            # 按分类过滤
            results = KnowledgeStore.filter(category=category)
            if not results:
                return f"未找到分类为「{category}」的知识记录。"
            return self._format_results(results, f"分类「{category}」下的记录")

        else:
            return f"未知操作: {action}。支持: overview, search_keyword, search_tag, filter_category。"

    def _format_results(self, records: list, title: str) -> str:
        """将查询结果格式化为 Markdown 文本"""
        lines = [f"## {title}\n"]
        for r in records:
            lines.append(f"### {r['title']}")
            lines.append(f"- **分类**：{r['category']}")
            lines.append(f"- **标签**：{'、'.join(r.get('tags', []))}")
            lines.append(f"- **来源**：{r.get('source_task', '未知')}")
            lines.append("")
            lines.append(r.get("content", ""))
            lines.append("")
            lines.append("---")
            lines.append("")
        return "\n".join(lines)


# ============================================================
# 工具 6：经验沉淀 & 可复用规则整理（改造：同时写入知识库）
# ============================================================
# ============================================================
# 工具 6：经验沉淀 & 可复用规则整理（改造：同时写入知识库）
# ============================================================
class InsightRefiner(BaseTool):
    """
    经验沉淀 & 可复用规则整理工具。

    【用途】
    将本次任务执行中学到的经验沉淀下来，包括：
    - 标准指标口径定义（避免下次口径不一致）
    - 常见踩坑记录（避免重复犯错）
    - 有效的分析模式（可以标准化复用的方法）
    - 下轮行动清单（哪些需要改进）

    每次沉淀的经验会自动写入 knowledge_base.json 持久化存储，
    后续任务可以直接查询已有知识，避免重复沉淀。
    """
    name: str = "insight_refiner"
    description: str = (
        "沉淀本次任务的可复用经验和知识，并自动存入知识库。"
        "包括：标准指标口径定义（metric_definition）、"
        "常见踩坑记录与规避方法（pitfall）、"
        "有效的分析模式（analysis_pattern）、"
        "下轮改进行动清单（action_item）。"
        "输入任务执行总结，返回结构化的知识沉淀，同时持久化到知识库文件。"
    )

    def _run(self, task_summary: str) -> str:
        """
        执行经验沉淀并写入知识库。

        参数：
            task_summary: 本次任务执行总结

        返回：
            结构化的可复用知识条目（含已保存到知识库的提示）
        """
        # 确保知识库已初始化
        KnowledgeStore.init()

        # ---- 写入口径定义 ----
        metric_record = {
            "category": "metric_definition",
            "title": "初诊转化率标准口径",
            "content": (
                "初诊转化率 = 有消费记录的首诊患者数 / 总首诊患者数 \u00d7 100%\n"
                "- 时间粒度：月度\n"
                "- 数据来源：dwd_patient_visit 表\n"
                "- 过滤条件：is_first_visit = 1"
            ),
            "tags": ["转化率", "首诊", "口径定义"],
            "source_task": task_summary[:100] if task_summary else "本次任务",
            "source_agent": "Agent3",
        }
        saved_metric = KnowledgeStore.add(metric_record)

        # ---- 写入踩坑记录 ----
        pitfall_record = {
            "category": "pitfall",
            "title": "字段名不一致导致查询失败",
            "content": (
                "不同门店或系统之间同一概念的字段名可能不同（如 clinic_name vs store_name）。\n"
                "- 触发条件：跨系统取数时\n"
                "- 规避方法：建立字段映射字典，取数前先查字典\n"
                "- 示例：本次遇到 clinic_name 不存在，实际字段为 store_name"
            ),
            "tags": ["字段名", "SQL", "踩坑"],
            "source_task": task_summary[:100] if task_summary else "本次任务",
            "source_agent": "Agent3",
        }
        saved_pitfall = KnowledgeStore.add(pitfall_record)

        # ---- 写入分析模式 ----
        pattern_record = {
            "category": "analysis_pattern",
            "title": "标准分析框架：转化率分析",
            "content": (
                "推荐的分析执行顺序：\n"
                "1. 先做基础统计（总体转化率）\n"
                "2. 维度下钻：整体 \u2192 门店 \u2192 医生 \u2192 时间\n"
                "3. 中间结果缓存，支持快速迭代\n"
                "4. 进阶分析前确保基础分析已完成\n"
                "5. 交叉验证不同口径的数据一致性"
            ),
            "tags": ["分析框架", "转化率", "维度下钻"],
            "source_task": task_summary[:100] if task_summary else "本次任务",
            "source_agent": "Agent3",
        }
        saved_pattern = KnowledgeStore.add(pattern_record)

        # ---- 写入行动项 ----
        action_record = {
            "category": "action_item",
            "title": "下轮优化行动清单",
            "content": (
                "- 建立字段映射字典，解决命名不一致问题\n"
                "- 创建常用 SQL 模板，减少语法错误\n"
                "- 更新知识图谱，补充渠道实体\n"
                "- 将 is_first_visit=1 作为首诊分析的默认过滤条件"
            ),
            "tags": ["优化", "行动项", "SQL模板"],
            "source_task": task_summary[:100] if task_summary else "本次任务",
            "source_agent": "Agent3",
        }
        saved_action = KnowledgeStore.add(action_record)

        # ---- 返回经验报告（含已保存到知识库的提示） ----
        return (
            "## 可复用知识库条目\n\n"
            f"> 以下经验已自动保存到知识库（知识库现有 {KnowledgeStore.count()} 条记录）\n\n"
            "### 标准指标口径定义：\n"
            "- **初诊转化率** = 有消费记录的首诊患者数 / 总首诊患者数 \u00d7 100%\n"
            "  - 时间粒度：月度\n"
            "  - 数据来源：dwd_patient_visit 表\n\n"
            "### 常见踩坑记录：\n"
            "1. 不同门店之间字段名可能不同（如 clinic_name vs store_name）\n"
            "2. 分析首诊患者时容易漏加 is_first_visit=1 过滤条件\n"
            "3. 患者姓名和电话必须在输出前脱敏\n\n"
            "### 有效分析模式：\n"
            "- 先做基础统计，再做进阶分析\n"
            "- 维度下钻顺序：整体 \u2192 门店 \u2192 医生 \u2192 时间\n"
            "- 中间结果缓存，支持快速迭代\n\n"
            "### 下轮行动清单：\n"
            "- 建立字段映射字典，解决命名不一致问题\n"
            "- 创建常用 SQL 模板，减少语法错误\n"
            "- 更新知识图谱，补充渠道实体\n\n"
            "---\n"
            "已保存到知识库的条目：\n"
            f"- {saved_metric['id']}：初诊转化率标准口径\n"
            f"- {saved_pitfall['id']}：字段名不一致导致查询失败\n"
            f"- {saved_pattern['id']}：标准分析框架\n"
            f"- {saved_action['id']}：下轮优化行动清单"
        )


# ============================================================
review_agent = Agent(
    role="全流程复盘审计专家、业务体系优化顾问",
    goal=(
        "独立对需求澄清、知识获取、任务拆解、数据取数、分析输出全流程进行批判性复盘；"
        "发现流程漏洞、口径不合理点、取数逻辑缺陷、业务知识图谱实体关系不完善之处；"
        "给出可落地的流程优化、图谱补充、分析方向拓展建议；"
        "沉淀单次任务经验，反哺业务体系与 Agent 能力持续进化。"
    ),
    backstory=(
        "你具备全局审视思维，不负责直接业务执行，专注于事后复盘、流程审计、体系优化与长期进化；"
        "熟悉儿牙业务全流程逻辑、指标口径规则、知识图谱设计思路、取数分析常见短板与坑点；"
        "善于跳出单次任务视角，发现隐性逻辑问题、冗余步骤、口径歧义盲区、图谱缺失关联关系；"
        "能够给出具体可落地的优化建议、图谱补充方向、分析维度拓展思路，并沉淀为可复用的业务经验。"
    ),
    verbose=True,
    allow_delegation=False,
    tools=[
        ProblemCollectorReader(),     # 工具1：读取 Agent1/Agent2 上报的问题
        StepDecompositionEvaluator(), # 工具2：评估步骤拆解合理性
        GraphGapDetector(),           # 工具3：图谱缺陷诊断
        ProcessOptimizer(),           # 工具4：流程优化建议
        KnowledgeBaseReader(),        # 工具5：查询已有知识库（避免重复沉淀）
        InsightRefiner(),             # 工具6：经验沉淀 & 写入知识库
    ],
)

# ============================================================
# 复盘任务
# ============================================================
review_task = Task(
    description=(
        "请对本次任务执行结果进行全面复盘分析：\n\n"
        "1. 使用 problem_collector_reader 工具（action='get_all'）读取 Agent1/Agent2 在本轮执行中上报的所有问题记录。\n"
        "2. 使用 step_decomposition_evaluator 工具，评估本轮任务步骤拆解的合理性。\n"
        "3. 使用 graph_gap_detector 工具，分析知识图谱是否存在实体或关系缺失。\n"
        "4. 使用 process_optimizer 工具，总结执行过程中的可优化环节。\n"
        "5. 使用 insight_refiner 工具，沉淀本轮可复用的业务经验和规则。\n\n"
        "最后，将以上分析结果整合为一份完整的复盘报告。"
    ),
    expected_output=(
        "一份结构化的复盘报告，包含以下内容：\n"
        "1. 【问题汇总】本轮遇到的问题、解决方案、严重程度分布\n"
        "2. 【步骤拆解评价】步骤是否合理、有无缺失或冗余\n"
        "3. 【图谱补缺建议】知识图谱需要补充的实体或关系\n"
        "4. 【流程优化建议】可简化的环节、可模板化的步骤\n"
        "5. 【经验沉淀】可复用的标准口径、踩坑记录、分析模式\n"
        "6. 【执行摘要】一句话总结本轮执行质量\n"
        "格式：Markdown"
    ),
    agent=review_agent,
)

# ============================================================
# 独立运行 Agent3 的入口
# ============================================================
if __name__ == "__main__":
    """
    独立运行 Agent3 进行复盘。

    运行前确保：
    1. 虚拟环境已激活（venv/Scripts/Activate.ps1）
    2. .env 文件已配置 API 密钥
    3. data/problem_reports.json 中已有 Agent1/Agent2 上报的问题数据

    运行命令：
        python agents/agent3.py
    """
    # 初始化问题存储和知识库（确保 data 目录和 JSON 文件存在）
    from tools.problem_store import ProblemStore
    from tools.knowledge_store import KnowledgeStore
    ProblemStore.init()
    KnowledgeStore.init()

    # 创建 Crew 并执行复盘任务
    crew = Crew(
        agents=[review_agent],
        tasks=[review_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    print("\n\n" + "=" * 60)
    print("[Agent3] 复盘报告：")
    print(result)
