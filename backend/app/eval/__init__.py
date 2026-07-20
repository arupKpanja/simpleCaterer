"""Evaluation harness (T9).

Scores generated option sets against the plan's success metrics on a labeled
dataset: dietary-constraint compliance (>= 95%) and budget respect-or-flag
(100%). Run ``python -m app.eval.run`` for a report; ``tests/test_eval.py``
gates releases on the thresholds.
"""
