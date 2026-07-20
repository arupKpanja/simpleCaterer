# Caterer System — Part 1 (Planning & Quoting) — MVP

A supervisor-orchestrated multi-agent assistant (LangGraph) that turns a
client's live requirements — event type, guest count, budget, dietary
restrictions, cuisine — into **three costed, constraint-respecting menu options**
(essential / standard / premium) for side-by-side comparison.

Part 1 of [`../caterer-multi-agent-langgraph-plan.md`](../caterer-multi-agent-langgraph-plan.md):

- **Supervisor** validates requirements, normalizes diet constraints, and fans
  out one worker per tier.
- **Per-tier worker** ([`tiers.py`](app/agents/tiers.py)) builds a themed,
  diet-compliant menu (deterministic cheapest/median/priciest-per-course
  selection → premium ≥ standard ≥ essential), prices it against local inventory,
  emits a shopping list, and runs a final allergen post-check. The LLM only names
  the theme; selection and all arithmetic are deterministic (tools decide).
- **Decor & Venue agent** ([`decor.py`](app/agents/decor.py)) adds a decor
  package + a capacity-fitting venue per tier; `total_cost = food + decor + venue`
  and the budget check is against that total.
- Options are persisted (`Event` / `Option` / `OptionMenuItem`) and returned with
  an `event_id` for later retrieval.

Logistics, approved-order freeze, and the vendor approval gate come in later
phases (see [`TASKS.md`](TASKS.md)).

Everything runs **locally**. SQLite by default; Ollama used when available,
otherwise a deterministic rule-based planner keeps the system fully runnable.

## Architecture

```
                    ┌─► [plan_tier: essential] ─┐
requirements ─► [supervisor] ─► [plan_tier: standard] ─┼─► [assemble] ─► 3 options
                    │           └─► [plan_tier: premium]  ┘
                    │ (invalid reqs short-circuit to END)
                    ▼
                 EventState (typed; options/log/errors are reducer channels)
```

| Layer | Where |
|---|---|
| Graph / agents | [`app/agents/`](app/agents/) — `graph.py`, `supervisor.py`, `tiers.py` |
| MCP tool layer | [`app/mcp/`](app/mcp/) — typed data-access tools (the agents' only DB path) + optional MCP server |
| Safety-critical logic | [`app/agents/diet.py`](app/agents/diet.py) (allergen filter), [`app/agents/pricing.py`](app/agents/pricing.py) (all cost math) |
| LLM abstraction | [`app/llm/client.py`](app/llm/client.py) — Ollama + deterministic fallback |
| DB + catalog | [`app/db/`](app/db/) — SQLAlchemy models + seed |
| API | [`app/main.py`](app/main.py) — FastAPI + SSE |

## Setup

Requires **Python 3.10+** (developed/tested on 3.12).

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux

python -m app.db.seed        # create + seed the SQLite catalog
```

Or use the dev helper (one command each):

```powershell
.\scripts\dev.ps1 setup   # venv + install + seed        (Windows)
.\scripts\dev.ps1 check   # run tests + eval gate
.\scripts\dev.ps1 run     # start the API
```

```bash
./scripts/dev.sh setup    # macOS / Linux / Git Bash  (or: make setup / make check)
```

Copy [`.env.example`](.env.example) to `.env` to override any setting
(`CATERER_*`); all are optional.

> **Legacy note (Anaconda Python only):** an Anaconda-derived venv can fail to
> load its SQLite DLL (`import sqlite3` segfaults). Use a python.org 3.12 build,
> or prepend `…\anaconda3\Library\bin` to `PATH`. A standard python.org install
> needs neither.

## Run

```bash
python demo.py                                   # end-to-end console demo
uvicorn app.main:app --reload                    # API on http://localhost:8000
```

Then:

```bash
curl -s localhost:8000/health
# returns { "event_id": ..., "options": [essential, standard, premium], ... }
curl -s -X POST localhost:8000/api/plan -H "content-type: application/json" -d '{
  "event_type": "wedding reception", "guest_count": 120, "budget": 60000,
  "dietary_restrictions": ["vegetarian", "no nuts"], "cuisine_pref": "Indian"}'
curl -s localhost:8000/api/options/<event_id>   # retrieve a persisted option set
```

`POST /api/plan/stream` returns the same result as Server-Sent Events, one event
per agent stage (`supervisor` → `tier:essential` / `tier:standard` /
`tier:premium` → `assemble` → `result`).

Other endpoints:

- `POST /api/orders/approve` `{event_id, option_id}` — freeze the chosen tier
  into an immutable approved order (201; 409 if already approved).
- `GET  /api/orders/{order_id}` — retrieve a frozen order.
- `POST /api/orders/{order_id}/vendor-draft` — draft a supplier order and pause
  at the human approval gate (nothing is placed yet).
- `POST /api/orders/{order_id}/vendor-decision` `{decision: approve|reject}` —
  place (with exportable shopping list; deducts consumed stock and flags
  shortfalls in `stock_impact`) or reject the drafted order.
- `GET  /api/orders/{order_id}/vendor` — the vendor order (draft/placed/rejected).
- `GET  /api/sessions/{session_id}/state` — the checkpointed state for a planning
  session. Runs are keyed by `session_id` (pass one in the plan request to
  resume/inspect, or use the generated one echoed back); state is durable across
  restarts via a local SQLite checkpointer.

## Enabling the real LLM (optional)

1. Install [Ollama](https://ollama.com) and start it (`ollama serve`).
2. Pull a model: `ollama pull llama3.1:8b` (a 7–8B model is the sweet spot on a
   local box; use a smaller/quantized tag if RAM is tight).
3. The client auto-detects Ollama at `http://localhost:11434`. Override via env:
   `CATERER_OLLAMA_MODEL`, `CATERER_OLLAMA_BASE_URL`, or force the deterministic
   planner with `CATERER_FORCE_FALLBACK_LLM=true`.

Validate the wiring and latency (targets p95 < 30s per the plan):

```bash
python -m app.eval.llm_check --runs 5      # or: .\scripts\dev.ps1 llm-check
```

It checks reachability + that the model is pulled, measures p50/p95 option-set
generation time, and prints an LLM-named theme next to the deterministic
fallback. It exits non-zero (with guidance) if Ollama or the model is missing, so
it doubles as a readiness check. The LLM is used only to *name* menu themes;
selection and all costing stay deterministic either way, so the system produces
identical, constraint-safe options with or without it.

## MCP tool layer

The agents read data only through the typed tools in
[`app/mcp/tools.py`](app/mcp/tools.py) (recipe / decor / venue / price / stock),
which return validated Pydantic DTOs — no agent touches SQLAlchemy directly. The
same tools are exposed over the Model Context Protocol for external clients:

```bash
python -m app.mcp.server   # runs the MCP server over stdio (needs the `mcp` package)
```

## Test

```bash
python -m pytest -q
```

Covers the diet filter, budget/allergen math, and full graph runs (vegetarian,
nut-allergy, and invalid-requirements paths).

### Eval harness

```bash
python -m app.eval.run     # scores a labeled set; exits non-zero if a metric misses
```

Gates on the plan's success metrics — ≥95% dietary-constraint compliance and
100% budget respect-or-flag — over [`app/eval/dataset.py`](app/eval/dataset.py).

## Switching to Postgres

Set `CATERER_DATABASE_URL=postgresql+psycopg://user:pass@localhost/caterer` —
no code changes (SQLAlchemy models are engine-agnostic). `psycopg[binary]` is
already in requirements.

## Docker

### Default: Postgres + API in containers, Ollama on the host (recommended)

The LLM stays native on the host (keeps its RAM/GPU; containers stay light); only
Postgres + API are containerized ([`../docker-compose.yml`](../docker-compose.yml)):

```bash
docker compose up --build                        # from the repo root
# host port 8000 busy?  CATERER_API_PORT=8080 docker compose up --build
```

The API is on http://localhost:8000, targets the Postgres service, and reaches
the host Ollama at `host.docker.internal:11434`. For the container to reach it,
make Ollama listen on all interfaces (not just loopback):

```bash
# set OLLAMA_HOST=0.0.0.0 for the host Ollama, restart it, then:
ollama pull llama3.1:8b
```

Until a model is reachable the API serves the deterministic planner, so the stack
works immediately regardless.

### Optional: bundle Ollama as a container

Only on a Docker VM with enough RAM (~6 GB+) and free disk for the model:

```bash
docker compose -f docker-compose.yml -f docker-compose.bundled-llm.yml up --build
docker compose -f docker-compose.yml -f docker-compose.bundled-llm.yml \
    exec ollama ollama pull llama3.1:8b
```

Data persists in named volumes (`caterer_db`, `caterer_data`, and — bundled mode
only — `ollama_models`).

## Not yet built (later phases)

Logistics & Prep agent, the option-comparison UI, and all of **Part 2**
(event-day ops). See [`TASKS.md`](TASKS.md) for the tracked backlog.
