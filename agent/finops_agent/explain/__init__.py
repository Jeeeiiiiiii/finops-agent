"""The explainer seam.

Given deterministic Evidence, produce an Explanation. Two adapters:

- RuleExplainer   — no model. Deterministic sentences from the numbers and
                    the change list. Always available; the floor.
- ClaudeExplainer — Claude with three read-only tools for follow-up
                    questions. Falls back to RuleExplainer on any failure,
                    so a model outage never silences an alert.
"""

from __future__ import annotations

from typing import Protocol

from ..models import Evidence, Explanation


class Explainer(Protocol):
    def explain(self, evidence: Evidence) -> Explanation: ...


from .rules import RuleExplainer  # noqa: E402

__all__ = ["Explainer", "RuleExplainer"]
