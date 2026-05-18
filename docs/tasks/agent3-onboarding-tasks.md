# Agent3 复盘系统接入待办清单

## 背景

Agent3（复盘精灵，`agents/agent3.py`）已开发完成，包含 5 个分析工具，可以对任务执行过程进行复盘审计、图谱补缺、流程优化和经验沉淀。

Agent3 的核心数据来源是**问题上报收集器**（`tools/problem_store.py` + `tools/problem_reporter.py`），它依赖 Agent1 和 Agent2 在任务执行过程中主动上报遇到的问题和解决方案。

当前 Agent3 可以通过手动注入测试数据运行（`data/problem_reports.json`），但要让复盘系统真正跑起来，需要 Agent1 和 Agent2 接入上报工具。

---

## 📋 待办一：Agent2 接入问题上报工具

**负责人：** @程芳莹

**改动文件：** `agents/agent2.py`

**改动内容：** 在 tools 列表中增加一行

```python
# 文件顶部 imports 区域增加（和其他 import 放一起）
from tools.problem_reporter import ProblemReporterTool

# 在 Agent 的 tools 列表中添加（现有 8 个工具之后）
data_agent = Agent(
    ...
    tools=[
        KnowledgeGraphQueryTool(),
        DataFetchTool(),
        SQLDebugTool(),
        CacheManagerTool(),
        BasicAnalysisTool(),
        AdvancedAnalysisTool(),
        VisualizationTool(),
        PPTGeneratorTool(),
        ProblemReporterTool(),    # ← 新增：问题上报工具
    ],
)
```

**改动量：** 2 行（一个 import + 一个工具挂载）

**预期效果：**
Agent2 在执行过程中遇到以下情况时，LLM 会自动调用 `problem_reporter` 工具上报：

| 触发场景 | 上报内容示例 |
|---------|-------------|
| SQL 报错（字段不存在） | 字段 clinic_name 不存在，替换为 store_name |
| 数据异常（门店无数据） | 门店 SH003 无当月数据，已排除该门店 |
| 口径自动修复（缺过滤条件） | 缺少 is_first_visit=1 条件，已自动添加 |
| 缓存命中/未命中 | 缓存未命中，重新取数 |
| 其他异常情况 | 按实际发生的问题描述 |

---

## 📋 待办二：Agent1 接入问题上报工具

**负责人：** @陈黎斌

**改动文件：** `agents/agent1.py`（开发中）

**改动内容：** 在 tools 列表中增加一行

```python
# 文件顶部 imports 区域增加
from tools.problem_reporter import ProblemReporterTool

# 在 Agent 的 tools 列表中添加
scheduler_agent = Agent(
    ...
    tools=[
        ...  # 现有工具
        ProblemReporterTool(),    # ← 新增：问题上报工具
    ],
)
```

**改动量：** 2 行

**预期效果：**
Agent1 在执行过程中遇到以下情况时自动上报：

| 触发场景 | 上报内容示例 |
|---------|-------------|
| 需求口径有歧义 | 用户对"转化率"的定义不清晰，通过追问确认为"首诊转化率" |
| 知识图谱查询不到对象 | 图谱中缺少门店 SH003 的实体信息 |
| 权限校验发现问题 | 用户角色无查看某门店数据的权限 |
| 审核 Agent2 结果发现问题 | Agent2 的转化率计算口径与用户确认的不一致 |

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
# 1. 运行 Agent2（触发问题上报）
venv\Scripts\Activate.ps1
python agents/agent2.py

# 2. 查看上报的问题数据
Get-Content data/problem_reports.json

# 3. 运行 Agent3 复盘
python agents/agent3.py
```

**预期结果：**
- Agent2 执行过程中自动上报遇到的问题
- Agent3 读取到上报的问题，生成复盘报告
- 复盘报告中包含问题分析、优化建议和经验沉淀

---

## 📋 待办五（可选）：增强 Agent3 复盘深度

**负责人：** @李宇豪

**后续可优化方向：**
1. Agent3 的 4 个分析工具（步骤评估、图谱诊断、流程优化、经验沉淀）当前返回的是模拟数据，后续可以接入真实的过程产物作为输入
2. 经验沉淀结果可以持久化到知识库，跨任务复用
3. Agent3 发现的问题可以自动生成改进工单

---

## 文件索引

| 文件 | 用途 | 维护人 |
|------|------|--------|
| `agents/agent3.py` | 复盘精灵主体 | @李宇豪 |
| `tools/problem_store.py` | JSON 文件存储（底层） | @李宇豪 |
| `tools/problem_reporter.py` | 问题上报工具（给 Agent1/2 用） | @李宇豪 |
| `tools/problem_collector.py` | 问题读取工具（给 Agent3 用） | @李宇豪 |
| `data/problem_reports.json` | 问题数据文件（运行时生成） | 所有 Agent |

---

*文档版本：v1.0 | 更新日期：2026-05-18*
