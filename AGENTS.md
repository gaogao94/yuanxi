# yuanxi — Agent Instructions

Multi-agent business analytics system: Agent1 (clarify/plan), Agent2 (execute), Agent3 (retrospective). Python backend + React frontend. Targets oral/children's dental clinic operations.

## Quick Start

```bash
source venv/bin/activate          # Python 3.12.7 via pyenv
pip install -r requirements.txt

# Run tests
.venv/bin/python -m unittest discover -s tests

# Compile-check everything
.venv/bin/python -m compileall agents integration.py tests tools local_agent1_test.py

# Agent1 local conversation (real Graph API + LLM)
printf '查看仙乐斯门店的转化率\n1\n最近一个月\n' | .venv/bin/python local_agent1_test.py

# Integration entrypoint (mock Agent2)
.venv/bin/python integration.py "请分析2026年4月上海门店SH001初诊转化率"

# Frontend dev server
cd app/web && npm install && npm run dev   # http://localhost:5175/
```

## Architecture

- `agents/agent1.py` — Requirement clarification, graph scoping, task planning, and review. Contains both deterministic core (`Agent1`) and LLM wrapper (`Agent1LLMClarifier`). No `task_contract.todos`; outputs `required_capabilities` for Agent2 to self-plan.
- `agents/agent2.py` — Data execution via CrewAI: graph query, SQL fetch/debug, analysis, visualization, HTML report. Uses DeepSeek via OpenAI-compatible API.
- `agents/agent3.py` — Post-hoc review: problem collection, step evaluation, graph gap detection, knowledge store. Runs as sidecar, does not block main workflow.
- `integration.py` — Deterministic workflow orchestrator: Agent1 -> Agent2 -> Agent1 review. The `__main__` block runs with a simulated Agent2.
- `local_agent1_test.py` — Interactive PyCharm/CLI test: real Graph API + real LLM multi-turn clarification until `task_contract` is generated.
- `tools/` — Shared tool modules. `nebula_graph_query.py` is the single graph tool used by both Agent1 and Agent2.
- `app/web/` — React + Vite + Tailwind + MUI frontend. Entry: `src/main.tsx`.

## Key Conventions

- **No fixed execution steps**: `task_contract` has no `todos` field. Agent1 outputs `required_capabilities`; Agent2 decides execution order via `agent2_planning_policy.execution_steps = "agent2_decides"`.
- **Single graph tool**: Both agents use `tools/nebula_graph_query.py` (`NebulaGraphQueryTool`). Agent1 calls with `output_format="json"` for structured data; Agent2 gets text summaries by default.
- **Strict graph mode**: Production uses `GRAPH_API_STRICT=1` — no local JSON/mock fallback on API failure. Agent1 returns `blocked` instead.
- **Time ranges normalized**: Relative phrases ("最近一个月") are converted to concrete date intervals (`2026-04-20 to 2026-05-20`) before entering `task_contract`.
- **Chinese human-readable fields**: Task contract human text is in Chinese; machine identifiers (`id`, `type`, `executor`) stay English.
- **Clinic scope extraction**: Agent1 extracts named clinics from the original question (e.g. "仙乐斯门店" → `["仙乐斯门店"]`) and strips possessive particles ("仙乐斯的" → `["仙乐斯"]`). Does not re-ask for clinics already named.
- **Privacy hardening**: Phone/email regex scrubbing, excluded entities (`RawPatientIdentity`, `PaymentCredential`), read-only DB constraint in safety_constraints.

## Environment Variables

Configure via `.env` (git-ignored, see `.env.example`).

**Important**: `.env.example` uses `GRAPH_API_URL` but the code reads `GRAPH_API_BASE_URL`. Keep both in sync; the code default is `https://graph.automed.cn`.

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | LLM API key (DeepSeek/Qwen compatible) |
| `OPENAI_API_BASE` | LLM base URL |
| `OPENAI_MODEL_NAME` | Model name (default `deepseek-chat`) |
| `OPENAI_USER_AGENT` | Optional User-Agent header |
| `OPENAI_RESPONSE_FORMAT_JSON` | Set `0` for Qwen/thinking models |
| `GRAPH_API_KEY` | NebulaGraph HTTP API key |
| `GRAPH_API_STRICT` | Set `1` to disable mock/local fallback |
| `GRAPH_API_AUTO_SPACE` | Set `1` to auto-select graph space |
| `GRAPH_API_SPACE` | Fixed graph space (overrides auto) |
| `GRAPH_API_BASE_URL` | Graph API endpoint (default `https://graph.automed.cn`) |
| `AGENT1_TODAY` | Override "today" date for testing |
| `DB_*` | MySQL connection for data fetch |

## Testing

- Framework: `unittest`
- All tests in `tests/test_agent1_workflow.py`
- Run single test: `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.<test_method>`
- Run all: `.venv/bin/python -m unittest discover -s tests`
- Always verify with: `.venv/bin/python -m compileall agents integration.py tests tools local_agent1_test.py`

## Multi-Agent Collaboration Protocol

Before modifying code, read `.agents/ACTIVE_WORK.md` and `.agents/CHANGELOG.md`. After changes, update both files with:
- Status, task, files modified
- Frontend/backend/interface/database/config impact
- Verification commands and results

When changing interfaces between agents, record the contract change explicitly. See existing CHANGELOG entries for format.

## Frontend Notes

- `app/web/` uses Vite with a custom `figma:asset/` resolver
- `@` alias maps to `src/`
- Both React and Tailwind plugins must remain in vite config
- `assetsInclude`: `.svg`, `.csv` only — never add `.css`, `.tsx`, `.ts`
- npm install may timeout; use `--fetch-timeout=600000 --fetch-retries=5`
