"""Deterministic explanation. What the alert says when there is no model.

It is honest about what it does not know: with no changes in the window it
says so and points at usage growth; with changes it names the most recent
one and the actor, and calls that a correlation, not a cause.
"""

from __future__ import annotations

from datetime import date

from ..models import Change, Evidence, Explanation


def _fmt_usd(v: float) -> str:
    return f"${v:,.2f}"


def _when(change: Change, day: date) -> str:
    return "today" if change.at.startswith(day.isoformat()) else f"on {change.at[:10]}"


class RuleExplainer:
    def explain(self, evidence: Evidence) -> Explanation:
        a = evidence.anomaly
        changes = evidence.changes
        share = (a.today_usd / evidence.account_total_today_usd * 100) if evidence.account_total_today_usd else 0.0

        if a.kind == "new":
            head = f"{a.service} cost {_fmt_usd(a.today_usd)} today and had no cost at all in the baseline window"
        else:
            head = (
                f"{a.service} cost {_fmt_usd(a.today_usd)} today against a {_fmt_usd(a.baseline_usd)} baseline "
                f"({a.ratio:.1f}x, +{_fmt_usd(a.delta_usd)})"
            )
        head += f"; that is {share:.0f}% of today's spend."

        if not changes:
            return Explanation(
                cause=f"{head} No write calls to this service were found in the audit trail for the window, "
                "so the increase is most likely usage-driven (more traffic, more data, a job that ran longer) rather than a configuration change.",
                confidence="low",
                recommendation=f"Check the service's own usage metrics for the same period and confirm the workload that drives {a.service} did more work than usual.",
                explained_by="rules",
            )

        latest = changes[0]
        actors = sorted({c.actor for c in changes})
        names = sorted({c.event_name for c in changes})
        return Explanation(
            cause=(
                f"{head} {len(changes)} write call(s) to this service in the window: {', '.join(names[:5])}"
                f"{'…' if len(names) > 5 else ''}. The most recent was {latest.event_name} by {latest.actor} {_when(latest, a.day)}"
                f"{' on ' + ', '.join(latest.resources[:2]) if latest.resources else ''}. Correlated in time, not proven causal."
            ),
            confidence="medium",
            recommendation=(
                f"Ask {', '.join(actors[:3])} whether the {latest.event_name} change was intended to persist; "
                f"if it was, adjust the {a.service} budget, otherwise revert it and confirm tomorrow's cost returns to baseline."
            ),
            explained_by="rules",
        )
