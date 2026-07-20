"""T11: the LLM validation runner degrades gracefully when Ollama is absent.

Tests force the deterministic fallback (no Ollama), so this asserts the
readiness-check behavior rather than real latency.
"""
from app.eval.llm_check import evaluate_llm


def test_reports_disabled_without_crashing():
    # conftest forces fallback, so the runner reports the LLM as not in use
    report = evaluate_llm(runs=1)
    assert report["reachable"] is False
    assert report["target_met"] is None
    assert report["runs"] == 0
    assert report["message"]
    assert report["model"]  # configured model name is surfaced
