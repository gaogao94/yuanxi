# Agent3 复盘系统接入待办清单

## 背景

Agent3（复盘精灵，`agents/agent3.py`）已开发完成，目前包含 6 个工具：

| 工具 | 用途 | 给谁用 |
|------|------|--------|
| `problem_collector_reader` | 读取 Agent1/Agent2 上报的问题 | Agent3 |
| `step_decomposition_evaluator` | 评估步骤拆解合理性 | Agent3 |
| `graph_gap_detector` | 图谱缺陷诊断 | Agent3 |
| `process_optimizer` | 流程优化建议 | Agent3 |
| `knowledge_base_reader` | 查询知识经验库（多种过滤方式） | Agent3 |
| `insight_refiner` | 经验沉淀 & 自动写入知识库 | Agent3 |

Agent3 的核心数据来源是：
1. **问题上报收集器**（`tools/problem_store.py` + `tools/problem_reporter.py`）— 依赖 Agent1/Agent2 上报
2. **知识经验库**（`tools/knowledge_store.py` + `tools/knowledge_query.py`）— Agent1/Agent2 可以主动查询

---

## 📋 待办一：Agent2 接入工具（2 行代码）

**负责人：** @程芳莹

**改动文件：** `agents/agent2.py`

**改动内容：** 在 tools 列表中增加两个工具

```python
# 文件顶部 imports 区域增加（和其他 import 放一起）
from tools.problem_reporter import ProblemReporterTool
from tools.knowledge_query import KnowledgeBaseQueryTool

# 在 Agent 的 tools 列表中添加（现有 8 个工具之后）
data_agent = Agent(
    ...
    tools=[
        NebulaGraphQueryTool(),
        DataFetchTool(),
        SQLDebugTool(),
        CacheManagerTool(),
        BasicAnalysisTool(),
        AdvancedAnalysisTool(),
        VisualizationTool(),
        PPTGeneratorTool(),
        ProblemReporterTool(),        # ← 新增：遇到问题时自动上报
        KnowledgeBaseQueryTool(),     # ← 新增：主动查询历史经验
    ],
)
```

**改动量：** 4 行（两个 import + 两个工具挂载）

**预期效果：**

| 工具 | 触发场景 | LLM 自动行为 |
|------|---------|-------------|
| `problem_reporter` | SQL 报错、数据异常、口径修复 | 自动上报问题+解决方案 |
| `knowledge_base_query` | 写 SQL 前、指标口径不确定、想参考分析框架 | 自动查知识库参考历史经验 |

---

## 📋 待办二：Agent1 接入工具（2 行代码）

**负责人：** @陈黎斌

**改动文件：** `agents/agent1.py`（开发中）

**改动内容：** 在 tools 列表中增加两个工具

```python
# 文件顶部 imports 区域增加
from tools.problem_reporter import ProblemReporterTool
from tools.knowledge_query import KnowledgeBaseQueryTool

# 在 Agent 的 tools 列表中添加
scheduler_agent = Agent(
    ...
    tools=[
        ...  # 现有工具
        ProblemReporterTool(),        # ← 新增：遇到问题时自动上报
        KnowledgeBaseQueryTool(),     # ← 新增：澄清需求时查标准口径
    ],
)
```

**改动量：** 4 行

**预期效果：**

| 工具 | 触发场景 | LLM 自动行为 |
|------|---------|-------------|
| `problem_reporter` | 口径有歧义、图谱查不到、权限问题 | 自动上报问题+解决方案 |
| `knowledge_base_query` | 用户提到指标时、需要确认口径时 | 自动查知识库的标准口径定义 |

---

## 📋 待办三：确认 .gitignore 已包含 .env

**负责人：** 所有人

**当前状态：** ✅ 已更新

`.gitignore` 中已添加 `.env` 配置，API 密钥不会被提交到仓库。

---

## 📋 待办四：验证全链路跑通

**负责人：** @李宇豪

**前置条件：** 待办一和二完成后

**验证步骤：**

```powershell
# 1. 运行 Agent2（触发问题上报 + 知识库查询）
venv\Scripts\Activate.ps1
python agents/agent2.py

# 2. 查看上报的问题数据
Get-Content data/problem_reports.json

# 3. 查看知识库文件（Agent3 沉淀的经验）
Get-Content data/knowledge_base.json

# 4. 运行 Agent3 复盘
python agents/agent3.py
```

**预期结果：**
- Agent2 执行中自动查知识库 + 上报问题
- Agent3 读取上报的问题，生成复盘报告
- Agent3 沉淀的经验自动写入知识库

---

## 📋 待办五（未来规划）：经验自动注入 Agent1/Agent2

**负责人：** @李宇豪

**当前状态：** ⏳ 待 Workflow 编排器实现后推进

### 现状

目前 Agent1/Agent2 查询知识库是"被动"的——需要 LLM 自己决定去查。LLM 不一定每次都会主动查。

### 方案二：Workflow 自动注入（推荐，全自动）

在 Workflow 编排器中，启动 Agent 前自动查询知识库，把相关内容**直接塞进 Agent 的任务描述里**：

```
Workflow 启动 Agent2 前：
    ↓
自动查询知识库 → 找到和本次任务相关的踩坑记录 + 分析模式
    ↓
注入到 Agent2 的 Task description 中
    ↓
Agent2 启动时已经自带历史经验，无需主动查询
```

关键代码示意：

```python
class Workflow:
    def run_agent2(self, task_contract):
        # 自动查询知识库
        pitfalls = KnowledgeStore.search_by_tag("踩坑")
        patterns = KnowledgeStore.search_by_category("analysis_pattern")
        
        # 注入到任务描述中
        enhanced_task = f"""
        {task_contract}
        
        【历史经验参考】（自动注入）
        常见踩坑：
        {pitfalls}
        
        推荐分析模式：
        {patterns}
        """
        
        return self.crew.kickoff()
```

**优点：**
- 全自动，不依赖 LLM 主动查询
- 不需要改 Agent1/Agent2 代码
- 知识库越丰富，注入的内容越有价值

**依赖条件：** 需要 Workflow 编排器实现

### 方案三：方案一 + 方案二 结合

```
短期（当前）：
    → Agent1/Agent2 挂 KnowledgeBaseQueryTool
    → LLM 主动查询知识库

长期（Workflow 实现后）：
    → Workflow 自动注入历史经验到任务描述
    → Agent 启动前就已带着相关知识
    → KnowledgeBaseQueryTool 作为补充查询手段保留
```

---

## 📋 待办六（未来规划）：增强 Agent3 复盘深度

**负责人：** @李宇豪

**后续可优化方向：**
1. **去掉 Mock 数据**：StepDecompositionEvaluator、GraphGapDetector、ProcessOptimizer 当前返回模拟数据，后续接入真实过程产物
2. **经验去重**：多次运行后知识库可能积累重复条目，需要去重或合并
3. **经验过期机制**：有些经验（如字段映射）可能随系统更新而过期，需要标记或清理
4. **自动生成图谱补缺 PR**：当前图谱建议只是文本，后续可以直接生成 nGQL 语句
5. **异步并行执行**：Agent2 执行时 Agent3 就开始做部分复盘，而非等主链路完全结束

---

## 文件索引

| 文件 | 用途 | 维护人 |
|------|------|--------|
| `agents/agent3.py` | 复盘精灵主体（6 个工具） | @李宇豪 |
| `tools/problem_store.py` | 问题存储器（底层 JSON） | @李宇豪 |
| `tools/problem_reporter.py` | 问题上报工具（给 Agent1/2 用） | @李宇豪 |
| `tools/problem_collector.py` | 问题读取工具（给 Agent3 用） | @李宇豪 |
| `tools/knowledge_store.py` | 知识经验库（底层 JSON） | @李宇豪 |
| `tools/knowledge_query.py` | 知识库查询工具（给 Agent1/2 用） | @李宇豪 |
| `data/problem_reports.json` | 问题数据文件（运行时生成） | 所有 Agent |
| `data/knowledge_base.json` | 知识经验库文件（运行时生成） | 所有 Agent |

---

*文档版本：v1.2 | 更新日期：2026-05-18*
