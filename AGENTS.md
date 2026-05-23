# yuanxi — Agent Instructions

Multi-agent business analytics system: Agent1 (clarify/plan), Agent2 (execute), Agent3 (retrospective). Python backend + React frontend. Targets oral/children's dental clinic operations.

## Quick Start

```bash
# Backend — venv at .venv/ (.gitignore covers .venv/, venv/, env/)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run all tests
.venv/bin/python -m unittest discover -s tests

# Compile-check all source (no linter configured; this is the primary verification step)
.venv/bin/python -m compileall agents integration.py tests tools local_agent1_test.py app/api/main.py

# Agent1 local conversation (real Graph API + LLM, requires .env with keys)
printf '查看仙乐斯门店的转化率\n1\n最近一个月\n' | .venv/bin/python local_agent1_test.py

# Integration entrypoint (mock Agent2)
.venv/bin/python integration.py "请分析2026年4月上海门店SH001初诊转化率"

# Backend API server (FastAPI, port 8000)
.venv/bin/uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend dev server (Vite, proxies /api → localhost:8000)
cd app/web && npm install --fetch-timeout=600000 --fetch-retries=5 && npm run dev

# Frontend tests (vitest — no "test" script in package.json; must use npx)
cd app/web && npx vitest
```

## Architecture

- `agents/agent1.py` — Requirement clarification, graph scoping, task planning, and review. Contains deterministic core (`Agent1`) and LLM wrapper (`Agent1LLMClarifier`). No `task_contract.todos`; outputs `required_capabilities` for Agent2 to self-plan.
- `agents/agent2.py` — Data execution via CrewAI: graph query, SQL fetch/debug, analysis, visualization, HTML report. Uses DeepSeek via OpenAI-compatible API.
- `agents/agent3.py` — Post-hoc review: problem collection, step evaluation, graph gap detection, knowledge store. Runs as sidecar, does not block main workflow.
- `integration.py` — Deterministic workflow orchestrator: Agent1 → Agent2 → Agent1 review. `__main__` block runs with a simulated Agent2.
- `local_agent1_test.py` — Interactive CLI test: real Graph API + real LLM multi-turn clarification until `task_contract` is generated.
- `tools/` — Shared tool modules. `nebula_graph_query.py` is the single graph tool used by both Agent1 and Agent2. `graph_api.py` is the low-level HTTP client.
- `app/api/main.py` — FastAPI backend. Endpoints: `POST /api/chat`, `POST /api/chat/stream` (SSE), `GET /api/health`, `GET /api/reports/{filename}`.
- `app/web/` — React + Vite + Tailwind + MUI frontend. Entry: `src/main.tsx`. Vite proxies `/api` to backend.
- `data/` — Runtime knowledge base and problem records (git-ignored).
- `output/` — Generated reports (git-ignored, served by `GET /api/reports/{filename}`).
- `scripts/debug/` — Temporary debug scripts only (network connectivity patches, one-off fix scripts). Structure documented in `scripts/README.md`. Formal tests go in `tests/`.
- `test_nebula_connection.py` — Standalone Graph API connection diagnostic at repo root. Reads both `GRAPH_API_BASE_URL` and `GRAPH_API_URL`; useful first step when graph queries fail.

## Key Conventions

- **No fixed execution steps**: `task_contract` has no `todos` field. Agent1 outputs `required_capabilities`; Agent2 decides execution order via `agent2_planning_policy.execution_steps = "agent2_decides"`.
- **Single graph tool**: Both agents use `tools/nebula_graph_query.py` (`NebulaGraphQueryTool`). Agent1 calls with `output_format="json"` for structured data; Agent2 gets text summaries by default.
- **Strict graph mode**: Set `GRAPH_API_STRICT=1` to disable local JSON/mock fallback on API failure. Agent1 returns `blocked` instead.
- **Time ranges normalized**: Relative phrases ("最近一个月") are converted to concrete date intervals before entering `task_contract`.
- **Chinese human-readable fields**: Task contract human text is in Chinese; machine identifiers (`id`, `type`, `executor`) stay English.
- **Clinic scope extraction**: Agent1 extracts named clinics from the original question (e.g. "仙乐斯门店" → `["仙乐斯门店"]`) and strips possessive particles ("仙乐斯的" → `["仙乐斯"]`). Does not re-ask for clinics already named.
- **Privacy hardening**: Phone/email regex scrubbing, excluded entities (`RawPatientIdentity`, `PaymentCredential`), read-only DB constraint in safety_constraints.

## Environment Variables

Configure via `.env` (git-ignored, see `.env.example`).

**Env var naming split** (a real gotcha): `tools/nebula_graph_query.py` reads `GRAPH_API_BASE_URL`; `tools/graph_api.py` reads `GRAPH_API_URL`. `.env.example` only lists `GRAPH_API_BASE_URL`. If anything imports `graph_api.py` directly, also set `GRAPH_API_URL`. Default for both: `https://graph.automed.cn`.

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | LLM API key (DeepSeek/Qwen compatible) |
| `OPENAI_API_BASE` | LLM base URL |
| `OPENAI_MODEL_NAME` | Model name (default `deepseek-chat`) |
| `OPENAI_USER_AGENT` | Optional User-Agent header |
| `OPENAI_RESPONSE_FORMAT_JSON` | Set `0` for Qwen/thinking models |
| `OPENAI_TIMEOUT_SECONDS` | LLM request timeout (default `60`) |
| `OPENAI_MAX_TOKENS` | Max response tokens (default `2048`) |
| `GRAPH_API_KEY` | NebulaGraph HTTP API key |
| `GRAPH_API_STRICT` | Set `1` to disable mock/local fallback (not in `.env.example`) |
| `GRAPH_API_AUTO_SPACE` | Set `1` to auto-select graph space |
| `GRAPH_API_SPACE` | Fixed graph space (overrides auto) |
| `GRAPH_API_BASE_URL` | Graph API endpoint (default `https://graph.automed.cn`) |
| `AGENT1_TODAY` | Override "today" date for testing |
| `API_PORT` | Backend API port (default `8000`) |
| `DB_*` | MySQL connection for data fetch |

## Testing

- Framework: `unittest` — no pytest, no third-party test runner
- Test files: `tests/test_agent1_workflow.py`, `tests/test_agent3_and_storage.py`
- Run single test: `.venv/bin/python -m unittest tests.test_agent1_workflow.Agent1WorkflowTest.<test_method>`
- Run all: `.venv/bin/python -m unittest discover -s tests`
- After changes, always verify with: `.venv/bin/python -m compileall agents integration.py tests tools local_agent1_test.py app/api/main.py`
- `local_agent1_test.py` helper functions are imported directly by tests — changes to its function signatures will break test imports

## Multi-Agent Collaboration Protocol

Before modifying code, read `.agents/ACTIVE_WORK.md` and `.agents/CHANGELOG.md`. After changes, update both files with:
- Status, task, files modified
- Frontend/backend/interface/database/config impact
- Verification commands and results

When changing interfaces between agents, record the contract change explicitly. See existing CHANGELOG entries for format.

**Known issue**: `.agents/ACTIVE_WORK.md` has unresolved merge conflict markers (lines 658-705). Resolve before editing that file.

## Frontend Gotchas

- Frontend bootstrapped from Figma Make (`"name": "@figma/my-make-file"` in package.json) — this is why the `figma:asset/` resolver exists and why it cannot be removed
- `@` alias maps to `src/`
- Both React and Tailwind plugins must remain in vite config
- `assetsInclude`: `.svg`, `.csv` only — never add `.css`, `.tsx`, `.ts`
- npm install may timeout; use `--fetch-timeout=600000 --fetch-retries=5`
- Frontend tests use vitest + jsdom; test setup at `src/test/setup.ts`; run with `npx vitest` inside `app/web/` (no `npm test` script in `package.json`)
- Data viz charts use `echarts-for-react` via `src/app/components/charts/EChart.tsx`; `recharts` is used separately in `src/app/components/ui/chart.tsx` as a UI primitive — both are active
- API client at `src/api/chat.ts` — `API_BASE` is `/api` (proxied by Vite dev server)
