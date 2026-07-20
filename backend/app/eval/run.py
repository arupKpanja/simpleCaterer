"""Scored eval runner (T9).

Runs the planner over the labeled dataset and scores two metrics per generated
option:

- **diet compliance** — every course meets the scenario's required diet tags and
  carries none of its excluded allergens, and the option's ``allergen_safe`` flag
  agrees. Target: >= 95%.
- **budget respect-or-flag** — the option is within budget with the flag set
  correctly, or over budget and explicitly flagged (``within_budget`` false with a
  positive ``overage``). Target: 100%.

``evaluate()`` returns the report; running the module prints it and exits
non-zero if a threshold is missed (so it can gate a release).
"""
from __future__ import annotations

import sys
from typing import Dict, List

from app.agents.graph import plan
from app.eval.dataset import SCENARIOS

DIET_THRESHOLD = 0.95
BUDGET_THRESHOLD = 1.0


def _option_diet_ok(option: Dict, required_tags: List[str], excluded: List[str]) -> bool:
    req, exc = set(required_tags), set(excluded)
    for course in option["courses"]:
        if not req.issubset(set(course.get("diet_tags", []))):
            return False
        if exc & set(course.get("allergens", [])):
            return False
    # the reported safety flag must agree with reality
    return bool(option.get("allergen_safe", True)) is True


def _option_budget_ok(option: Dict) -> bool:
    budget = option.get("budget", 0) or 0
    total = option.get("total_cost", 0) or 0
    within = option.get("within_budget", True)
    overage = option.get("overage", 0) or 0
    if budget <= 0:
        return within is True  # no cap → always "within"
    if total <= budget:
        return within is True and overage == 0
    return within is False and overage > 0  # over budget must be flagged


def evaluate() -> Dict:
    total = 0
    diet_pass = 0
    budget_pass = 0
    failures: List[str] = []

    for sc in SCENARIOS:
        options = plan(sc["requirements"]).get("options", [])
        if not options:
            failures.append(f"{sc['name']}: produced no options")
            continue
        for opt in options:
            total += 1
            if _option_diet_ok(opt, sc["required_diet_tags"], sc["excluded_allergens"]):
                diet_pass += 1
            else:
                failures.append(f"{sc['name']} [{opt['tier']}]: diet violation")
            if _option_budget_ok(opt):
                budget_pass += 1
            else:
                failures.append(f"{sc['name']} [{opt['tier']}]: budget flag wrong "
                                f"(total={opt.get('total_cost')} budget={opt.get('budget')} "
                                f"within={opt.get('within_budget')})")

    diet_rate = diet_pass / total if total else 0.0
    budget_rate = budget_pass / total if total else 0.0
    return {
        "scenarios": len(SCENARIOS),
        "options_scored": total,
        "diet_compliance_rate": round(diet_rate, 4),
        "budget_ok_rate": round(budget_rate, 4),
        "diet_pass": diet_rate >= DIET_THRESHOLD,
        "budget_pass": budget_rate >= BUDGET_THRESHOLD,
        "failures": failures,
    }


def main() -> int:
    r = evaluate()
    print("=" * 60)
    print("Caterer Part 1 — evaluation report")
    print("=" * 60)
    print(f"scenarios:       {r['scenarios']}")
    print(f"options scored:  {r['options_scored']}")
    print(f"diet compliance: {r['diet_compliance_rate']:.1%}  "
          f"(target >= {DIET_THRESHOLD:.0%})  -> {'PASS' if r['diet_pass'] else 'FAIL'}")
    print(f"budget or-flag:  {r['budget_ok_rate']:.1%}  "
          f"(target = {BUDGET_THRESHOLD:.0%})  -> {'PASS' if r['budget_pass'] else 'FAIL'}")
    if r["failures"]:
        print("\nfailures:")
        for f in r["failures"]:
            print(f"  - {f}")
    ok = r["diet_pass"] and r["budget_pass"]
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
