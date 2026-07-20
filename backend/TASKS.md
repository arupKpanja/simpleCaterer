# Part 1 Backend — Task Tracker

Tracks the **Part 1 (Planning & Quoting)** backend. See
[`../caterer-multi-agent-langgraph-plan.md`](../caterer-multi-agent-langgraph-plan.md).

**Status: T1–T10 ✅, T11 ✅, T12 ✅ — Part 1 backend complete.** The pipeline runs
requirements → three costed tiers (menu + decor + venue, allergen-safe,
budget-checked) → approved-order freeze → vendor draft + human approval gate →
stock deduction, over FastAPI (+ SSE), through a typed MCP tool layer, on a
durable checkpointer, gated by an eval harness, validated against a real local
Ollama model, and packaged as a one-command Docker stack.

Remaining beyond this tracker: the **Logistics & Prep agent** (optional Part 1
extra) and all of **Part 2** (event-day ops).

Status legend: ⬜ not started · 🟡 in progress · ✅ done

---

## T1 — Persist option sets to the database ✅
Generated options are now stored. Added `Event` / `Option` / `OptionMenuItem`
tables, a persistence service, and endpoints; the API returns an `event_id` and
options are fetchable by it.
- **Delivered:** `app/db/models.py` (Event/Option/OptionMenuItem),
  `app/services/persistence.py`, `POST /api/plan` returns `event_id`,
  `GET /api/options/{event_id}`; `tests/test_persistence.py` (roundtrip, 404,
  allergen snapshot). `save_event` already takes a list of options (T2-ready).
- **Blocks:** T2, T4.

## T2 — Tiered multi-option generation (essential / standard / premium) ✅
Supervisor now fans out via LangGraph `Send` to one parallel `plan_tier` worker
per tier; each builds + prices + allergen-checks its own menu and emits an option.
- **Delivered:** `app/agents/tiers.py` (per-tier worker; deterministic
  cheapest/median/priciest-per-course selection guarantees premium ≥ standard ≥
  essential; LLM names the theme only), fan-out in `graph.py`, reducer channels
  in `state.py`, API/persistence handle the option list. Tests assert three
  tiers, cost monotonicity, diet safety, and the streamed `tier:*` stages.
- **This is what the 3-card mockup needs.**

## T3 — Decor & Venue agent ✅
Each tier now includes a decor package + a capacity-fitting venue, priced from
catalog tables and folded into the option total (with the budget check against
the grand total).
- **Delivered:** `DecorPackage` / `Venue` models + seed (3 packages, 4 venues),
  `app/agents/decor.py` (per-tier cheapest/median/priciest package; venues
  filtered by capacity then ranked by price), integration in `tiers.py`
  (`food_cost` + `decor_cost` + `venue_cost` = `total_cost`), extended `Option`
  columns + persistence, `tests/test_decor.py`. Venue capacity respected;
  totals stay monotonic across tiers.

## T4 — Approved-order freeze ✅
Selecting an option freezes it into an immutable `ApprovedOrder` with a full JSON
snapshot (menu, decor, venue, shopping list, costs) — the Part 1 → Part 2 hinge.
- **Delivered:** `ApprovedOrder` model (one per event, frozen `snapshot`),
  `app/services/orders.py`, `POST /api/orders/approve` (201; 404 unknown option,
  409 already-approved) and `GET /api/orders/{id}`. `save_event` backfills option
  ids so the plan response is directly approvable. `tests/test_orders.py` covers
  freeze, conflict, ownership, and snapshot immutability.
- **Depends on:** T1.

## T5 — Vendor agent + human approval gate ✅
A LangGraph flow drafts a supplier order from the approved order, pauses at a
human approval gate (`interrupt_before`), and on the owner's decision places it
(with an exportable shopping list) or rejects it.
- **Delivered:** `VendorOrder` / `OrderLine` models, `app/services/vendor.py`
  (draft → gate → place/reject graph on the T6 checkpointer; idempotent draft &
  decision), endpoints `POST /api/orders/{id}/vendor-draft` (201, pauses),
  `POST /api/orders/{id}/vendor-decision` (approve/reject; 422 bad value, 409 no
  draft), `GET /api/orders/{id}/vendor`. `tests/test_vendor.py` covers the pause,
  place, reject, ordering guards, and idempotency.
- **Depends on:** T4, T6.

## T6 — LangGraph checkpointer + session state ✅
The graph is compiled with a durable checkpointer and every run is keyed by a
`session_id`; state survives a process restart and is retrievable/resumable.
- **Delivered:** `app/agents/checkpointer.py` (file-backed `SqliteSaver`,
  `MemorySaver` fallback), `session_id` threaded through `run_plan`/`plan`
  (generated if omitted, echoed on the result), `get_session_state`, and
  `GET /api/sessions/{session_id}/state`. `tests/test_sessions.py` proves
  retrieval, durability across a checkpointer reload, and 404 on unknown session.
- **Enables:** T5 (the approval-gate `interrupt` resumes on this checkpointer).

## T7 — MCP tool layer over the local DB ✅
Agents now reach data only through the typed tool layer; behavior unchanged.
- **Delivered:** `app/mcp/schemas.py` (Pydantic DTOs), `app/mcp/tools.py`
  (recipe / decor / venue / price / stock tools returning DTOs), `diet.py` +
  `pricing.py` refactored to DTOs, `tiers.py` + `decor.py` refactored to call
  tools (no `SessionLocal`/`select` left in `app/agents/`), `tests/test_tools.py`.
  `app/mcp/server.py` exposes the same tools over MCP (FastMCP), import-guarded so
  the app still runs where `mcp` is unavailable.
- **Note:** dev env upgraded to **Python 3.12** (from 3.9), which also enables the
  real MCP server and removes the Anaconda SQLite DLL workaround.

## T8 — Stock deduction on order recording ✅
Placing a vendor order now consumes on-hand stock and records the per-item impact.
- **Delivered:** `VendorOrder.stock_impact` column; `_deduct_stock` in
  `app/services/vendor.py` runs once inside the draft→placed transition (each item
  drops by min(required, on-hand); the remainder is the flagged shortfall).
  `stock_impact` is surfaced on the vendor result. `tests/test_stock.py` covers
  deduction, reject-no-op, idempotency, and shortfall flagging.
- **Done when:** recording an order updates stock; shortfalls are flagged. ✔

## T9 — Eval harness (allergen + budget accuracy) ✅
A labeled dataset + scored runner gate releases on the plan's success metrics.
- **Delivered:** `app/eval/dataset.py` (10 labeled scenarios covering each
  allergen/diet plus an over-budget case), `app/eval/run.py` (scores diet
  compliance and budget respect-or-flag per option; `python -m app.eval.run`
  prints a report and exits non-zero on a miss), `tests/test_eval.py` gating on
  the thresholds. Current run: 30 options scored, 100% diet, 100% budget-or-flag.
- **Metrics:** diet compliance ≥ 95%, budget respect-or-flag = 100%.

## T10 — Config & DX polish ✅
- **Delivered:** `.env.example` (all `CATERER_*` settings), `app/logging_config.py`
  (human or `CATERER_LOG_JSON` structured logs, wired into `main.py`),
  `scripts/dev.ps1` + `scripts/dev.sh` + `Makefile` with
  `setup/seed/test/eval/check/demo/run`, and `pytest.ini`. The Anaconda SQLite
  DLL note is documented in the README (now legacy after the 3.12 upgrade).
- **Done when:** `dev.ps1 check` (tests + eval) and `dev.ps1 run` work in one
  command. ✔

## T11 — Ollama install + model pull + real-LLM validation ✅
Ollama installed (0.32.1) and `llama3.1:8b` pulled; the real-model path is
validated on this machine.
- **Delivered:** `app/eval/llm_check.py` — checks reachability + model presence,
  measures p50/p95 option-set generation vs the < 30s target, and shows an
  LLM-named theme next to the fallback; exits non-zero as a readiness check.
  Hooked into `dev.ps1 llm-check` / `dev.sh llm-check`; README documents install,
  model choice, and the command. `tests/test_llm_check.py` covers the disabled path.
- **Validated on real hardware:** `/health` → `{"llm":"ollama"}`; latency
  **p50 11.3s / p95 11.76s** (target < 30s) → PASS; tiers get distinct LLM themes
  (e.g. essential "Taste of Indian Bliss" → premium "Taste of Royal India").
  Tests stay deterministic (conftest forces the fallback).

## T12 — Dockerize the backend + full local stack ✅
`docker compose up --build` brings up **Ollama + Postgres + API** with one command.
- **Delivered:** `backend/Dockerfile` (python:3.12-slim), `backend/.dockerignore`,
  root `docker-compose.yml` (Postgres with a data volume + healthcheck; Ollama
  with a model volume + healthcheck; API depends on both, seeds on startup,
  configurable host port via `CATERER_API_PORT`), `psycopg[binary]` added, and a
  configurable checkpoint path (`CATERER_CHECKPOINT_DB_PATH`) so session state can
  live on a volume. README documents the flow.
- **Verified:** image builds; all three containers report **healthy**;
  `/health` → `{"llm":"ollama"}`; `/api/plan` returns 3 persisted tiers against
  **Postgres** in-container (deterministic themes until a model is pulled).
- **Environmental caveat:** running the 8B model *inside* the container needs a
  Docker VM with enough RAM/disk (this box's VM is ~2 GB RAM and its disk filled
  on the 5 GB model pull, crashing Postgres). The real-model path is validated on
  the host in T11 (p95 11.76s); in-container it serves the deterministic fallback,
  which is fully functional. Give the Docker VM ~6 GB+ RAM to run the model in it.
- **Relates to:** T6, T11.

---

### Suggested order
T1 → T2 → T4 (unlocks the 3-card UI and the Part 1→Part 2 handoff), then T6 → T5
(approval gate), then T3, T7, T8, T9 as parallelizable follow-ups. **T11 (Ollama)
can be done anytime** to move off the fallback; **T12 (dockerize)** best comes
after T6/T11 so the compose stack wires the real Postgres + Ollama.

> Part 2 (event-day ops) is a separate backend and is intentionally out of scope here.
