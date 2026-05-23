# yuanxi

多 Agent 协作的业务分析系统，面向口腔/儿牙诊所运营场景。

Agent1 负责需求澄清与任务规划，Agent2 负责数据取数与分析执行，Agent3 负责事后复盘与知识沉淀。Python 后端（FastAPI）+ React 前端。

## 项目结构

```
├── agents/
│   ├── agent1.py              # 需求澄清、图谱边界、任务规划、审核
│   ├── agent2.py              # CrewAI 数据执行：图谱查询、SQL、分析、报告
│   └── agent3.py              # 事后复盘：问题收集、步骤评估、知识沉淀
├── tools/
│   ├── nebula_graph_query.py  # NebulaGraph 图谱查询（Agent1 和 Agent2 共用）
│   ├── graph_api.py           # Graph API 底层封装
│   ├── data_fetch.py          # 业务数据取数
│   ├── sql_debug.py           # SQL 校验与修复
│   ├── basic_analysis.py      # 基础统计分析
│   ├── advanced_analysis.py   # 进阶分析（回归、趋势）
│   ├── visualization.py       # 图表生成
│   ├── html_report.py         # HTML 报告生成
│   ├── problem_collector.py   # 问题收集读取
│   ├── problem_reporter.py    # 问题上报
│   ├── problem_store.py       # 问题持久化
│   ├── knowledge_candidate_store.py  # 知识候选库存储
│   ├── review_candidate_store.py     # 审核候选库存储
│   └── cache_manager.py       # 中间结果缓存
├── app/
│   ├── api/main.py            # FastAPI 后端（/api/chat, /api/health, /api/reports）
│   └── web/                   # React + Vite + Tailwind + MUI 前端
│       ├── src/main.tsx
│       └── vite.config.ts
├── tests/
│   ├── test_agent1_workflow.py
│   └── test_agent3_and_storage.py
├── scripts/
│   └── debug/                 # 临时调试脚本（网络/补丁等）
├── data/                      # 运行时数据（知识库、问题记录，git-ignored）
├── output/                    # 生成的报告（git-ignored）
├── docs/                      # 需求文档和任务文档
├── .agents/                   # Agent 协作日志和变更记录
├── integration.py             # 工作流编排入口（Agent1 → Agent2 → Agent1 审核）
├── local_agent1_test.py       # Agent1 本地交互测试（真实 Graph API + LLM）
├── test_nebula_connection.py  # Graph API 连接诊断工具
├── .env.example               # 环境变量模板
└── requirements.txt
```

## 快速开始

### 后端

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 编译检查（无 linter，这是主要的验证步骤）
.venv/bin/python -m compileall agents integration.py tests tools local_agent1_test.py app/api/main.py

# 运行测试
.venv/bin/python -m unittest discover -s tests

# Graph API 连接诊断
.venv/bin/python test_nebula_connection.py

# Agent1 本地对话（真实 Graph API + LLM，需配置 .env）
printf '查看仙乐斯门店的转化率\n1\n最近一个月\n' | .venv/bin/python local_agent1_test.py

# 集成入口（模拟 Agent2）
.venv/bin/python integration.py "请分析2026年4月上海门店SH001初诊转化率"

# 启动后端 API 服务
.venv/bin/uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd app/web
npm install --fetch-timeout=600000 --fetch-retries=5
npm run dev

# 运行前端测试
npx vitest
```

### 开发 Agent 指南

详见 [AGENTS.md](./AGENTS.md)。

## 环境变量

通过 `.env` 配置（已 git-ignored，参考 `.env.example`）：

| 变量 | 用途 |
|---|---|
| `OPENAI_API_KEY` | LLM API 密钥（DeepSeek/Qwen 兼容） |
| `OPENAI_API_BASE` | LLM Base URL |
| `OPENAI_MODEL_NAME` | 模型名称（默认 `deepseek-chat`） |
| `OPENAI_RESPONSE_FORMAT_JSON` | Qwen/思考模型设为 `0` |
| `OPENAI_TIMEOUT_SECONDS` | LLM 请求超时（默认 60 秒） |
| `OPENAI_MAX_TOKENS` | 最大响应 token 数（默认 2048） |
| `GRAPH_API_KEY` | NebulaGraph HTTP API 密钥 |
| `GRAPH_API_BASE_URL` | Graph API 端点（默认 `https://graph.automed.cn`） |
| `GRAPH_API_STRICT` | 设为 `1` 禁用 mock/local fallback |
| `GRAPH_API_AUTO_SPACE` | 设为 `1` 自动选择 graph space |
| `GRAPH_API_SPACE` | 固定 graph space（覆盖自动选择） |
| `AGENT1_TODAY` | 测试用日期覆盖 |
| `API_PORT` | 后端 API 端口（默认 8000） |
| `DB_*` | MySQL 数据库连接配置 |

> **注意**：`tools/graph_api.py` 读取 `GRAPH_API_URL`（非 `_BASE`），如在代码中直接引入该模块需额外配置。
