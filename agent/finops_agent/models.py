"""The nouns. Plain dataclasses, JSON-serialisable, no behaviour beyond that.

Everything that crosses a seam (a source, the explainer, the archive, the
notifier) is one of these, so the adapters agree on shape without importing
each other.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class DailyCost:
    day: date
    service: str
    usd: float


@dataclass(frozen=True)
class Anomaly:
    service: str
    day: date
    today_usd: float
    baseline_usd: float
    """Median of the baseline window. 0.0 for a service with no history."""
    delta_usd: float
    ratio: float
    """today / baseline; inf for a new service."""
    kind: str
    """'spike' (over baseline) or 'new' (no history)."""


@dataclass(frozen=True)
class Change:
    """A write call from the audit trail that might explain a cost change."""

    at: str  # ISO timestamp
    event_name: str
    event_source: str
    actor: str
    resources: tuple[str, ...] = ()


@dataclass(frozen=True)
class Evidence:
    """Everything the explainer is given. Deterministically gathered."""

    anomaly: Anomaly
    series: tuple[DailyCost, ...]
    """The service's daily costs over the lookback window, oldest first."""
    changes: tuple[Change, ...]
    account_total_today_usd: float


@dataclass(frozen=True)
class Explanation:
    cause: str
    confidence: str
    """'high' | 'medium' | 'low'."""
    recommendation: str
    explained_by: str
    """Which explainer produced this: 'rules', 'claude', or 'claude→rules' on fallback."""
    tool_calls: int = 0


@dataclass
class Finding:
    evidence: Evidence
    explanation: Explanation
    suppressed: bool = False
    """True when the same service was already alerted within the dedupe window."""
    suppressed_reason: str = ""
    sent: bool = False
    """True once a notification carrying this finding was delivered. Dedupe counts only these."""

    @property
    def service(self) -> str:
        return self.evidence.anomaly.service

    @property
    def day(self) -> date:
        return self.evidence.anomaly.day


@dataclass
class Report:
    day: date
    services_seen: int
    account_total_usd: float
    findings: list[Finding] = field(default_factory=list)
    notified: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def alerted(self) -> list[Finding]:
        return [f for f in self.findings if not f.suppressed]


# --------------------------------------------------------------------------- #
# JSON in and out. Dates become ISO strings; tuples become lists.
# --------------------------------------------------------------------------- #

def to_json(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: to_json(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: to_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_json(v) for v in obj]
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, float) and obj == float("inf"):
        return "inf"
    return obj


def finding_from_json(data: dict[str, Any]) -> Finding:
    ev = data["evidence"]
    an = ev["anomaly"]
    ratio = an["ratio"]
    anomaly = Anomaly(
        service=an["service"],
        day=date.fromisoformat(an["day"]),
        today_usd=an["today_usd"],
        baseline_usd=an["baseline_usd"],
        delta_usd=an["delta_usd"],
        ratio=float("inf") if ratio == "inf" else ratio,
        kind=an["kind"],
    )
    evidence = Evidence(
        anomaly=anomaly,
        series=tuple(DailyCost(date.fromisoformat(s["day"]), s["service"], s["usd"]) for s in ev["series"]),
        changes=tuple(Change(c["at"], c["event_name"], c["event_source"], c["actor"], tuple(c["resources"])) for c in ev["changes"]),
        account_total_today_usd=ev["account_total_today_usd"],
    )
    ex = data["explanation"]
    explanation = Explanation(ex["cause"], ex["confidence"], ex["recommendation"], ex["explained_by"], ex.get("tool_calls", 0))
    return Finding(evidence, explanation, data.get("suppressed", False), data.get("suppressed_reason", ""), data.get("sent", False))
