#!/usr/bin/env bash
# Dev helper (macOS / Linux / Git Bash).
# Usage: ./scripts/dev.sh <setup|seed|test|eval|check|demo|run>
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe"   # Windows venv
elif [ -x ".venv/bin/python" ];      then PY=".venv/bin/python"            # POSIX venv
else PY="python"; fi

need_venv() { [ "$PY" != "python" ] || { echo "No venv found. Run: ./scripts/dev.sh setup"; exit 1; }; }

case "${1:-help}" in
  setup)
    python -m venv .venv
    if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; else PY=".venv/Scripts/python.exe"; fi
    "$PY" -m pip install --upgrade pip
    "$PY" -m pip install -r requirements.txt
    "$PY" -m app.db.seed ;;
  seed)  need_venv; "$PY" -m app.db.seed ;;
  test)  need_venv; "$PY" -m pytest -q ;;
  eval)  need_venv; "$PY" -m app.eval.run ;;
  llm-check) need_venv; "$PY" -m app.eval.llm_check ;;
  check) need_venv; "$PY" -m pytest -q && "$PY" -m app.eval.run ;;
  demo)  need_venv; "$PY" demo.py ;;
  run)   need_venv; "$PY" -m uvicorn app.main:app --reload ;;
  *) echo "Usage: ./scripts/dev.sh <setup|seed|test|eval|check|demo|run>" ;;
esac
