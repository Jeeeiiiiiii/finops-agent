"""The whole run behind one function.

    investigate(day, deps) -> Report

Scripted where the answer is arithmetic (which services moved, by how much,
what changed in the window), agentic only where judgement is needed (what it
means, what to do). The Lambda handler and the CLI both call this and nothing
else; tests call it with fakes.

Order of operations, and why:
1. costs      one Cost Explorer call for the whole lookback window
2. detect     pure math; the thresholds are configuration, not prompt text
3. quiet?     no anomalies -> Report with no findings, nothing sent
4. evidence   per anomaly: the service's series + write calls in the window
5. explain    RuleExplainer or ClaudeExplainer (which itself falls back)
6. dedupe     archived either way; suppressed if a send succeeded recently
7. archive    every finding lands in S3 before anything is sent
8. notify     one message, only if something is not suppressed; then the
              sent findings are re-archived with sent=True (a failed send
              leaves them sent=False, so tomorrow alerts again)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

from .archive import FindingsArchive
from .detect import Thresholds, account_total, detect, series_for
from .explain import Explainer
from .models import Evidence, Finding, Report
from .notify import Notifier, format_daily, format_digest
from .sources.changes import ChangeSource
from .sources.cost import CostSource

Logger = Callable[[str, dict], None]


@dataclass
class Deps:
    costs: CostSource
    changes: ChangeSource
    explainer: Explainer
    archive: FindingsArchive
    notifier: Notifier
    thresholds: Thresholds = field(default_factory=Thresholds)
    lookback_days: int = 14
    """Cost window pulled up front; must cover baseline_days + 1."""
    change_window_days: int = 2
    """CloudTrail window per anomaly: today and this many days before."""
    dedupe_days: int = 3
    """Suppress a repeat alert for the same service within this many days."""
    max_findings: int = 5
    """Explain at most this many anomalies per run (biggest first); the rest are noted."""
    log: Logger = lambda msg, fields: None


def investigate(day: date, deps: Deps) -> Report:
    start = day - timedelta(days=deps.lookback_days - 1)
    rows = deps.costs.daily_by_service(start, day)
    total = account_total(rows, day)
    services = {r.service for r in rows}
    report = Report(day=day, services_seen=len(services), account_total_usd=total)
    deps.log("costs loaded", {"rows": len(rows), "services": len(services), "total_today_usd": round(total, 4)})

    anomalies = detect(rows, day, deps.thresholds)
    deps.log("detection done", {"anomalies": [a.service for a in anomalies]})
    if not anomalies:
        report.notes.append("no anomalies; nothing sent")
        return report

    if len(anomalies) > deps.max_findings:
        skipped = anomalies[deps.max_findings :]
        report.notes.append("not explained (over max_findings): " + ", ".join(a.service for a in skipped))
        anomalies = anomalies[: deps.max_findings]

    for anomaly in anomalies:
        window_start = day - timedelta(days=deps.change_window_days)
        try:
            changes = deps.changes.write_events(anomaly.service, window_start, day)
        except Exception as e:  # noqa: BLE001 - the trail being unavailable must not lose the alert
            deps.log("change source failed; continuing without changes", {"service": anomaly.service, "error": f"{type(e).__name__}: {e}"})
            report.notes.append(f"changes unavailable for {anomaly.service}: {type(e).__name__}")
            changes = []
        evidence = Evidence(
            anomaly=anomaly,
            series=tuple(series_for(rows, anomaly.service)),
            changes=tuple(changes),
            account_total_today_usd=total,
        )
        explanation = deps.explainer.explain(evidence)
        finding = Finding(evidence=evidence, explanation=explanation)

        prior = deps.archive.recently_alerted(anomaly.service, day, deps.dedupe_days)
        if prior is not None:
            finding.suppressed = True
            finding.suppressed_reason = f"alerted on {prior.isoformat()}"

        key = deps.archive.put(finding)
        deps.log(
            "finding archived",
            {
                "service": anomaly.service,
                "kind": anomaly.kind,
                "delta_usd": round(anomaly.delta_usd, 4),
                "changes": len(changes),
                "explained_by": explanation.explained_by,
                "suppressed": finding.suppressed,
                "key": key,
            },
        )
        report.findings.append(finding)

    if report.alerted:
        # Send, then record the send. If this raises, the findings stay
        # sent=False in the archive and tomorrow's run alerts again.
        deps.notifier.send(format_daily(report))
        report.notified = True
        for f in report.alerted:
            f.sent = True
            deps.archive.put(f)
    else:
        report.notes.append("all findings suppressed by dedupe; nothing sent")
    return report


def digest(day: date, deps: Deps, days: int = 7) -> str:
    """The weekly summary: everything archived in the window, sent once."""
    findings = deps.archive.since(day, days)
    text = format_digest(day, findings, days)
    deps.notifier.send(text)
    deps.log("digest sent", {"findings": len(findings), "days": days})
    return text
