# Caterer System — Part 1 (Planning & Quoting)

A multi-agent planning & quoting assistant: enter event requirements → get three
costed, allergen-safe menu options (essential / standard / premium) → freeze one
→ draft & approve the supplier order. LangGraph + Ollama backend, React frontend.

- **Backend:** [`backend/`](backend/) — FastAPI + LangGraph, SQLite or Postgres.
- **Frontend:** [`frontend/`](frontend/) — Vite + React + TypeScript + Tailwind.
- **LLM:** local **Ollama** (used to name menu themes; all costing/allergen logic
  is deterministic, so the app also runs fully without it).

There are **three pieces**: the LLM (Ollama), the backend API, and the frontend.
Below is the recommended local setup and how to **start and stop** each.

---

## Prerequisites

- **Docker Desktop** (for the recommended backend setup)
- **Node.js 18+** (frontend)
- **Ollama** (optional, for real LLM theming) — https://ollama.com
- Python 3.10+ only if you run the backend *without* Docker

Ports: **frontend 5173**, **backend API 8000** (local) or **8080** (Docker),
**Ollama 11434**.

---

## Recommended setup: Ollama on host, backend in Docker, frontend via Vite

### 1) LLM — Ollama (host)

**Start** (once installed). The container reaches the host Ollama, so it must
listen on all interfaces:

```powershell
# Windows (PowerShell) — set once, then it persists
[Environment]::SetEnvironmentVariable("OLLAMA_HOST","0.0.0.0","User")
# (re)start Ollama, then pull a model once:
ollama serve            # or just launch the Ollama app
ollama pull llama3.1:8b
```

```bash
# macOS / Linux
OLLAMA_HOST=0.0.0.0 ollama serve &
ollama pull llama3.1:8b
```

**Stop:**

```powershell
Get-Process ollama, "ollama app" -ErrorAction SilentlyContinue | Stop-Process -Force   # Windows
```
```bash
pkill ollama    # macOS / Linux
```

> Skip this entirely to run on the deterministic planner — the app still produces
> identical, constraint-safe options (theme names are just templated).

### 2) Backend — Postgres + API (Docker)

**Start** (from the repo root):

```bash
docker compose up --build -d          # add CATERER_API_PORT=8080 if 8000 is busy
```

The API seeds its catalog on first boot. Check it:

```bash
curl http://localhost:8000/health     # -> {"status":"ok","llm":"ollama"|"fallback"}
```

**Stop:**

```bash
docker compose stop                   # stop containers, keep data
docker compose down                   # stop + remove containers (keeps volumes)
docker compose down -v                # also delete data volumes (fresh start)
```

> To bundle Ollama as a container instead of using the host (needs a Docker VM
> with ~6 GB+ RAM), see [`backend/README.md`](backend/README.md#docker).

### 3) Frontend — Vite dev server

**Start:**

```bash
cd frontend
npm install                                   # first time only
echo "VITE_API_BASE=http://localhost:8000" > .env   # use :8080 if you set CATERER_API_PORT
npm run dev                                   # http://localhost:5173
```

**Stop:** press **Ctrl+C** in that terminal.

---

## Alternative: backend without Docker (local uvicorn + SQLite)

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
python -m app.db.seed
uvicorn app.main:app --reload                 # http://localhost:8000  (Ctrl+C to stop)
# or: .\scripts\dev.ps1 run   (Windows)   /   ./scripts/dev.sh run   (macOS/Linux)
```

Then point the frontend at `http://localhost:8000` (default).

---

## Stop everything

```bash
# frontend: Ctrl+C in its terminal
docker compose down          # backend (from repo root)
# Ollama: Stop-Process (Windows) / pkill ollama (macOS/Linux), or quit the app
```

---

## Tests

```bash
cd backend  && python -m pytest -q && python -m app.eval.run   # 50 tests + eval gate
cd frontend && npm test                                        # 9 unit/component tests
cd frontend && API_BASE=http://localhost:8080 npm run e2e      # e2e vs a running backend
```

## More docs

- Backend details, endpoints, Docker modes, Ollama validation: [`backend/README.md`](backend/README.md)
- Frontend flow, scripts, structure: [`frontend/README.md`](frontend/README.md)
- Task trackers: [`backend/TASKS.md`](backend/TASKS.md), [`UI_Task.md`](UI_Task.md)
- Original plan: [`caterer-multi-agent-langgraph-plan.md`](caterer-multi-agent-langgraph-plan.md)
