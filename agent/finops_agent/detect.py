"""Spike detection. Pure functions over DailyCost rows; no I/O, no model.

Two rules, both with explicit numbers that live in Thresholds, not in a prompt:

- spike:  today > median(baseline window) * (1 + ratio) AND the difference is
          at least min_delta_usd. The absolute floor is what stops a service
          going from $0.001 to $0.003 (a 200% "spike") from paging anyone.
- new:    the service has no cost at all in the baseline window and today is
          at least new_service_floor_usd.

The median, not the mean, so one earlier spike does not hide the next one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median

from .models import Anomaly, DailyCost


@dataclass(frozen=True)
class Thresholds:
    ratio: float = 0.25
    """Flag when today exceeds the baseline by this fraction (0.25 = +25%)."""
    min_delta_usd: float = 1.0
    """...and by at least this many dollars."""
    new_service_floor_usd: float = 1.0
    """A service with no history is flagged once it costs this much in a day."""
    baseline_days: int = 7


def series_for(rows: list[DailyCost], service: str) -> list[DailyCost]:
    return sorted((r for r in rows if r.service == service), key=lambda r: r.day)


def cost_on(rows: list[DailyCost], service: str, day: date) -> float:
    return sum(r.usd for r in rows if r.service == service and r.day == day)


def baseline_for(rows: list[DailyCost], service: str, day: date, t: Thresholds) -> tuple[float, bool]:
    """(median of the window before `day`, whether the window had any cost)."""
    window = [day - timedelta(days=i) for i in range(1, t.baseline_days + 1)]
    values = [cost_on(rows, service, d) for d in window]
    return (median(values) if values else 0.0), any(v > 0 for v in values)


def detect(rows: list[DailyCost], day: date, t: Thresholds = Thresholds()) -> list[Anomaly]:
    services = sorted({r.service for r in rows})
    found: list[Anomaly] = []
    for service in services:
        today = cost_on(rows, service, day)
        base, had_history = baseline_for(rows, service, day, t)

        if not had_history:
            if today >= t.new_service_floor_usd:
                found.append(Anomaly(service, day, today, 0.0, today, float("inf"), "new"))
            continue

        delta = today - base
        if base > 0 and today > base * (1 + t.ratio) and delta >= t.min_delta_usd:
            found.append(Anomaly(service, day, today, base, delta, today / base, "spike"))

    # Biggest dollar impact first: that is the order a human would read them in.
    found.sort(key=lambda a: a.delta_usd, reverse=True)
    return found


def account_total(rows: list[DailyCost], day: date) -> float:
    return sum(r.usd for r in rows if r.day == day)
