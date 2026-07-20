# Dev shortcuts (macOS / Linux). Windows: use scripts\dev.ps1
PY := .venv/bin/python

.PHONY: setup seed test eval check demo run

setup:
	python -m venv .venv && $(PY) -m pip install --upgrade pip && \
	$(PY) -m pip install -r requirements.txt && $(PY) -m app.db.seed

seed:
	$(PY) -m app.db.seed

test:
	$(PY) -m pytest -q

eval:
	$(PY) -m app.eval.run

check: test eval   ## release gate: tests + eval thresholds

demo:
	$(PY) demo.py

run:
	$(PY) -m uvicorn app.main:app --reload
