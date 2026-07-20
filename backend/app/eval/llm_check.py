"""Real-LLM validation (T11).

Checks that a local Ollama model is wired in and measures whether option-set
generation meets the plan's latency target (p95 < 30s on an 8B-class model).
Also shows an LLM-named theme next to the deterministic fallback so you can eye
the quality difference.

Run (after `ollama serve` + `ollama pull <model>`):

    python -m app.eval.llm_check --runs 5

Degrades gracefully: if Ollama isn't reachable it prints install guidance and
exits non-zero, so it doubles as a readiness check.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from typing import Dict, List, Optional

import httpx

from app.config import settings

P95_TARGET_SECONDS = 30.0

_SAMPLE_REQS = {
    "event_type": "wedding reception", "guest_count": 120, "budget": 300000,
    "dietary_restrictions": ["vegetarian"], "cuisine_pref": "Indian",
}


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, int(round((pct / 100) * (len(ordered) - 1)))))
    return ordered[k]


def _models_available() -> Optional[List[str]]:
    try:
        resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3.0)
        resp.raise_for_status()
        return [m.get("name", "") for m in resp.json().get("models", [])]
    except Exception:  # noqa: BLE001
        return None


def _theme_samples() -> Dict[str, str]:
    """LLM-named vs fallback theme for the same dishes (illustrative)."""
    from app.agents.tiers import _theme_name
    from app.llm.client import llm
    from app.mcp import tools

    dishes = tools.get_dishes()[:4]
    llm_theme = _theme_name("standard", _SAMPLE_REQS, dishes) if llm.is_available() else ""
    saved = llm._available
    llm._available = False
    try:
        fallback_theme = _theme_name("standard", _SAMPLE_REQS, dishes)
    finally:
        llm._available = saved
    return {"llm": llm_theme, "fallback": fallback_theme}


def evaluate_llm(runs: int = 5) -> Dict:
    from app.llm.client import llm

    if settings.force_fallback_llm:
        return {
            "reachable": False, "model": settings.ollama_model, "model_available": False,
            "runs": 0, "p50": None, "p95": None, "target_seconds": P95_TARGET_SECONDS,
            "target_met": None, "themes": None,
            "message": ("LLM disabled via CATERER_FORCE_FALLBACK_LLM — the "
                        "deterministic planner is in use; Ollama not consulted."),
        }

    models = _models_available()
    reachable = models is not None
    model_ok = reachable and any(settings.ollama_model in m for m in models)

    report: Dict = {
        "reachable": reachable,
        "model": settings.ollama_model,
        "model_available": bool(model_ok),
        "runs": 0,
        "p50": None,
        "p95": None,
        "target_seconds": P95_TARGET_SECONDS,
        "target_met": None,
        "themes": None,
    }
    if not reachable:
        report["message"] = (
            "Ollama not reachable at " + settings.ollama_base_url +
            ". Install from https://ollama.com, run `ollama serve`, then "
            f"`ollama pull {settings.ollama_model}`."
        )
        return report
    if not model_ok:
        report["message"] = (
            f"Ollama is up but model '{settings.ollama_model}' is not pulled. "
            f"Run `ollama pull {settings.ollama_model}` (or set CATERER_OLLAMA_MODEL)."
        )
        return report

    # reset cached availability so the LLM path is actually exercised
    llm._available = None
    from app.agents.graph import plan

    plan(_SAMPLE_REQS)  # warmup (loads the model)
    durations: List[float] = []
    for _ in range(max(1, runs)):
        start = time.perf_counter()
        plan(_SAMPLE_REQS)
        durations.append(time.perf_counter() - start)

    report["runs"] = len(durations)
    report["p50"] = round(statistics.median(durations), 2)
    report["p95"] = round(_percentile(durations, 95), 2)
    report["target_met"] = report["p95"] < P95_TARGET_SECONDS
    report["themes"] = _theme_samples()
    report["message"] = "OK"
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate the local Ollama LLM.")
    ap.add_argument("--runs", type=int, default=5, help="timed generation runs")
    args = ap.parse_args()

    r = evaluate_llm(args.runs)
    print("=" * 60)
    print("Caterer Part 1 — LLM validation")
    print("=" * 60)
    print(f"ollama:          {settings.ollama_base_url}  reachable={r['reachable']}")
    print(f"model:           {r['model']}  available={r['model_available']}")
    if r.get("message") and r["message"] != "OK":
        print("\n" + r["message"])
        return 1
    print(f"runs:            {r['runs']}")
    print(f"latency p50/p95: {r['p50']}s / {r['p95']}s  "
          f"(target p95 < {int(P95_TARGET_SECONDS)}s)  -> "
          f"{'PASS' if r['target_met'] else 'FAIL'}")
    if r["themes"]:
        print(f"theme (LLM):     {r['themes']['llm']}")
        print(f"theme (fallback):{r['themes']['fallback']}")
    ok = bool(r["target_met"])
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
