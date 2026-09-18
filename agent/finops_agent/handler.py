"""Lambda entry point. Builds Deps from the environment and the event, runs
one investigation (or the digest), and returns a small JSON summary that
`aws lambda invoke` prints back."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .config import Settings, Wiring, log_event
from .investigate import digest, investigate
from .models import to_json

logging.getLogger().setLevel(logging.INFO)


def run(event: dict[str, Any] | None) -> dict[str, Any]:
    settings = Settings.from_env(event)
    wiring = Wiring(settings, today=datetime.now(timezone.utc).date())  # investigates yesterday unless event.day
    deps = wiring.deps()
    log_event(
        "run starting",
        {
            "mode": settings.mode,
            "day": wiring.today.isoformat(),
            "cost_source": settings.cost_source,
            "change_source": settings.change_source,
            "scenario": settings.scenario if settings.cost_source == "fixture" else None,
            "explainer": wiring.explained_by,
            "notifier": wiring.notifies_via,
            "bucket": settings.bucket,
        },
    )

    if settings.mode == "digest":
        text = digest(wiring.today, deps)
        return {"mode": "digest", "day": wiring.today.isoformat(), "sent": True, "preview": text[:400]}

    report = investigate(wiring.today, deps)
    return {
        "mode": "daily",
        "day": report.day.isoformat(),
        "services_seen": report.services_seen,
        "account_total_usd": round(report.account_total_usd, 4),
        "findings": [
            {
                "service": f.service,
                "kind": f.evidence.anomaly.kind,
                "delta_usd": round(f.evidence.anomaly.delta_usd, 4),
                "explained_by": f.explanation.explained_by,
                "confidence": f.explanation.confidence,
                "suppressed": f.suppressed,
            }
            for f in report.findings
        ],
        "notified": report.notified,
        "notes": report.notes,
        "explainer": wiring.explained_by,
        "notifier": wiring.notifies_via,
    }


def handler(event, _context):
    return to_json(run(event or {}))
