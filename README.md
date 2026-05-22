# yuanxi

多 Agent 协作的业务分析系统，面向口腔/儿牙诊所运营场景。

Agent1 负责需求澄清与任务规划，Agent2 负责数据取数与分析执行，Agent3 负责事后复盘与知识沉淀。Python 后端 + React 前端。

## 项目结构

```
├── agents/
│   ├── agent1.py              # 需求澄清、图谱边界、任务规划、审核
│   ├── agent2.py              # CrewAI 数据执行：图谱查询、SQL、分析、报告
│   └── agent3.py              # 事后复盘：问题收集、步骤评估、知识沉淀
├── tools/
│   ├── nebula_graph_query.py  # NebulaGraph 图谱查询（Agent1 和 Agent2 共用）
│   ├── data_fetch.py          # 业务数据取数
│   ├── sql_debug.py           # SQL 校验与修复
│   ├── basic_analysis.py      # 基础统计分析
│   ├── advanced_analysis.py   # 进阶分析（回归、趋势）
│   ├── visualization.py       # 图表生成
│   ├── html_report.py         # HTML 报告生成
│   ├── problem_collector.py   # 问题收集读取
│   ├── problem_reporter.py    # 问题上报
│   ├── problem_store.py       # 问题持久化
│   ├── knowledge_store.py     # 知识经验库持久化
│   ├── knowledge_query.py     # 知识经验库查询
│   ├── cache_manager.py       # 中间结果缓存
│   └── graph_api.py           # Graph API 底层封装
├── tests/
│   └── test_agent1_workflow.py
├── app/web/                   # React + Vite + Tailwind + MUI 前端
│   ├── src/main.tsx
│   └── vite.config.ts
├── data/                      # 运行时数据（知识库、问题记录）
├── docs/                      # 需求文档和任务文档
├── integration.py             # 工作流编排入口（Agent1 → Agent2 → Agent1 审核）
├── local_agent1_test.py       # Agent1 本地交互测试（真实 Graph API + LLM）
├── .env.example               # 环境变量模板
└── requirements.txt
```

## 快速开始

### 后端

```bash
# Python 3.12.7（pyenv）
pyenv shell 3.12.7
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 运行测试
.venv/bin/python -m unittest discover -s tests

# 编译检查
.venv/bin/python -m compileall agents integration.py tests tools local_agent1_test.py

# Agent1 本地对话（真实 Graph API + LLM）
printf '查看仙乐斯门店的转化率\n1\n最近一个月\n' | .venv/bin/python local_agent1_test.py

# 集成入口（模拟 Agent2）
.venv/bin/python integration.py "请分析2026年4月上海门店SH001初诊转化率"
```

### 前端

```bash
cd app/web
npm install --fetch-timeout=600000 --fetch-retries=5
npm run dev   # http://localhost:5175/
```

## 环境变量

通过 `.env` 配置（已 git-ignored，参考 `.env.example`）：

| 变量 | 用途 |
|---|---|
| `OPENAI_API_KEY` | LLM API 密钥（DeepSeek/Qwen 兼容） |
| `OPENAI_API_BASE` | LLM Base URL |
| `OPENAI_MODEL_NAME` | 模型名称（默认 `deepseek-chat`） |
| `OPENAI_USER_AGENT` | 可选 User-Agent 头 |
| `OPENAI_RESPONSE_FORMAT_JSON` | Qwen/思考模型设为 `0` |
| `GRAPH_API_KEY` | NebulaGraph HTTP API 密钥 |
| `GRAPH_API_STRICT` | 设为 `1` 禁用 mock/local fallback |
| `GRAPH_API_AUTO_SPACE` | 设为 `1` 自动选择 graph space |
| `GRAPH_API_SPACE` | 固定 graph space（覆盖自动选择） |
| `AGENT1_TODAY` | 测试用日期覆盖 |
| `DB_*` | MySQL 数据库连接配置 |
