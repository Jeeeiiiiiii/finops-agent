"""Telling someone. Slack incoming webhook, or stdout for local runs.

The message carries its evidence — the numbers, the correlated changes, and
which explainer wrote the words — so the reader can judge it without opening
a console. Formatting is a pure function so it is tested without a network.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import date
from typing import Protocol

from .models import Finding, Report


def _usd(v: float) -> str:
    return f"${v:,.2f}"


def format_finding(f: Finding) -> str:
    a = f.evidence.anomaly
    x = f.explanation
    if a.kind == "new":
        head = f"*{a.service}* — new: {_usd(a.today_usd)} today, no cost in the baseline window"
    else:
        head = f"*{a.service}* — {_usd(a.baseline_usd)} → {_usd(a.today_usd)} ({a.ratio:.1f}x, +{_usd(a.delta_usd)})"
    lines = [head, f"_{x.cause}_", f"*Do:* {x.recommendation}"]
    if f.evidence.changes:
        top = f.evidence.changes[:3]
        lines.append(
            "*Changes in window:* "
            + "; ".join(f"{c.event_name} by {c.actor} at {c.at[:16].replace('T', ' ')}" for c in top)
            + (f"; +{len(f.evidence.changes) - 3} more" if len(f.evidence.changes) > 3 else "")
        )
    else:
        lines.append("*Changes in window:* none found")
    lines.append(f"confidence {x.confidence} · explained by {x.explained_by}" + (f" · {x.tool_calls} tool call(s)" if x.tool_calls else ""))
    return "\n".join(lines)


def format_daily(report: Report) -> str:
    alerted = report.alerted
    head = (
        f":warning: *FinOps — {report.day.isoformat()}* — {len(alerted)} anomal{'y' if len(alerted) == 1 else 'ies'} "
        f"across {report.services_seen} services, {_usd(report.account_total_usd)} today"
    )
    parts = [head] + [format_finding(f) for f in alerted]
    suppressed = [f for f in report.findings if f.suppressed]
    if suppressed:
        parts.append("_still elevated, already alerted: " + ", ".join(f.service for f in suppressed) + "_")
    return "\n\n".join(parts)


def format_digest(day: date, findings: list[Finding], days: int) -> str:
    if not findings:
        return f":white_check_mark: *FinOps weekly — {day.isoformat()}* — no anomalies in the last {days} days."
    by_service: dict[str, list[Finding]] = {}
    for f in findings:
        by_service.setdefault(f.service, []).append(f)
    lines = [f":bar_chart: *FinOps weekly — {day.isoformat()}* — {len(findings)} finding(s), {len(by_service)} service(s), last {days} days"]
    for service, items in sorted(by_service.items(), key=lambda kv: -sum(i.evidence.anomaly.delta_usd for i in kv[1])):
        total = sum(i.evidence.anomaly.delta_usd for i in items)
        days_hit = sorted({i.day.isoformat() for i in items})
        lines.append(f"• *{service}* — +{_usd(total)} over {len(days_hit)} day(s) ({days_hit[0]} → {days_hit[-1]}); latest: {items[0].explanation.cause[:140]}…")
    return "\n".join(lines)


class Notifier(Protocol):
    def send(self, text: str) -> None: ...


class SlackNotifier:
    def __init__(self, webhook_url: str, timeout: float = 10.0) -> None:
        self._url = webhook_url
        self._timeout = timeout

    def send(self, text: str) -> None:
        body = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(self._url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310 - URL comes from Secrets Manager
            if resp.status >= 300:
                raise RuntimeError(f"slack webhook returned {resp.status}")


class StdoutNotifier:
    def __init__(self, stream=None) -> None:
        self._stream = stream or sys.stdout

    def send(self, text: str) -> None:
        self._stream.write(text + "\n")
        self._stream.flush()


class CollectingNotifier:
    """For tests."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, text: str) -> None:
        self.sent.append(text)
