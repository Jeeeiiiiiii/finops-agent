"""What changed in the account — the other half of "why".

Two adapters behind one interface:

- CloudTrailSource   — cloudtrail:LookupEvents for write calls in a window,
                       narrowed to the event sources that map to a Cost
                       Explorer service name.
- FixtureChangeSource — a JSON file, for tests and demo scenarios.

The mapping from a billing name ("Amazon Elastic Compute Cloud - Compute")
to audit event sources ("ec2.amazonaws.com") is a small exact table. An
unmapped service gets every write event in the window, unfiltered: noisier,
but never wrong about which service a change belongs to.
"""

from __future__ import annotations

import json
import time as _clock
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Protocol

from ..models import Change

# Cost Explorer SERVICE dimension value -> CloudTrail eventSource(s).
SERVICE_EVENT_SOURCES: dict[str, tuple[str, ...]] = {
    "Amazon Elastic Compute Cloud - Compute": ("ec2.amazonaws.com", "autoscaling.amazonaws.com"),
    "EC2 - Other": ("ec2.amazonaws.com",),
    "Amazon Virtual Private Cloud": ("ec2.amazonaws.com",),
    "Amazon Simple Storage Service": ("s3.amazonaws.com",),
    "AWS Lambda": ("lambda.amazonaws.com",),
    "Amazon Relational Database Service": ("rds.amazonaws.com",),
    "Amazon DynamoDB": ("dynamodb.amazonaws.com",),
    "Amazon Elastic Kubernetes Service": ("eks.amazonaws.com",),
    "Amazon Elastic Container Service": ("ecs.amazonaws.com",),
    "Amazon Elastic Container Registry": ("ecr.amazonaws.com",),
    "Amazon Simple Queue Service": ("sqs.amazonaws.com",),
    "Amazon Simple Notification Service": ("sns.amazonaws.com",),
    "AmazonCloudWatch": ("monitoring.amazonaws.com", "logs.amazonaws.com"),
    "Amazon CloudFront": ("cloudfront.amazonaws.com",),
    "Amazon Route 53": ("route53.amazonaws.com",),
    "Amazon Elastic Load Balancing": ("elasticloadbalancing.amazonaws.com",),
    "AWS Secrets Manager": ("secretsmanager.amazonaws.com",),
    "Amazon Bedrock": ("bedrock.amazonaws.com",),
    "Amazon Athena": ("athena.amazonaws.com",),
    "AWS Glue": ("glue.amazonaws.com",),
    "Amazon OpenSearch Service": ("es.amazonaws.com",),
    "Amazon ElastiCache": ("elasticache.amazonaws.com",),
    "AWS Key Management Service": ("kms.amazonaws.com",),
}

# Read-only event names carry no cost signal; LookupEvents' ReadOnly attribute
# already filters them, but fixtures and older trails may not.
_READ_PREFIXES = ("Describe", "List", "Get", "Lookup", "Head", "BatchGet", "Query", "Scan", "Search")


def event_sources_for(service: str) -> tuple[str, ...]:
    """Exact table lookup only. Guessing from keywords sent every unmapped
    service to ec2.amazonaws.com; an empty tuple means "do not filter"."""
    return SERVICE_EVENT_SOURCES.get(service, ())


def is_write(event_name: str) -> bool:
    return not event_name.startswith(_READ_PREFIXES)


class ChangeSource(Protocol):
    def write_events(self, service: str, start: date, end: date) -> list[Change]:
        """Write calls attributable to `service` between start 00:00 and end 23:59 UTC, newest first."""
        ...


class CloudTrailSource:
    """LookupEvents is 2 requests/s, 50 events/page, and cannot filter by
    source server-side. In a busy account a window can hold thousands of
    pages, so both the page count and the wall-clock are bounded; a partial
    answer is "what we found in the time", not the truth."""

    def __init__(self, client, max_events: int = 200, max_pages: int = 20, time_budget_s: float = 25.0) -> None:
        self._ct = client
        self._max = max_events
        self._max_pages = max_pages
        self._budget = time_budget_s

    def write_events(self, service: str, start: date, end: date) -> list[Change]:
        sources = event_sources_for(service)
        start_at = datetime.combine(start, time.min, tzinfo=timezone.utc)
        end_at = datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc)
        out: list[Change] = []
        token: str | None = None
        started = _clock.monotonic()
        pages = 0
        while len(out) < self._max and pages < self._max_pages and _clock.monotonic() - started < self._budget:
            pages += 1
            kwargs = dict(
                LookupAttributes=[{"AttributeKey": "ReadOnly", "AttributeValue": "false"}],
                StartTime=start_at,
                EndTime=end_at,
                MaxResults=50,
            )
            if token:
                kwargs["NextToken"] = token
            resp = self._ct.lookup_events(**kwargs)
            for ev in resp.get("Events", []):
                source = ev.get("EventSource", "")
                if sources and source not in sources:
                    continue
                name = ev.get("EventName", "")
                if not is_write(name):
                    continue
                at = ev.get("EventTime")
                out.append(
                    Change(
                        at=at.isoformat() if isinstance(at, datetime) else str(at),
                        event_name=name,
                        event_source=source,
                        actor=ev.get("Username", "unknown"),
                        resources=tuple(
                            f"{r.get('ResourceType', '?')}:{r.get('ResourceName', '?')}" for r in ev.get("Resources", [])
                        ),
                    )
                )
            token = resp.get("NextToken")
            if not token:
                break
        out.sort(key=lambda c: c.at, reverse=True)
        return out[: self._max]


class FixtureChangeSource:
    """Reads {"changes": [{"day_offset": -1, "time": "14:05", "event_name": ..., "event_source": ..., "actor": ..., "resources": [...]}]}."""

    def __init__(self, path: Path | None, today: date) -> None:
        self._changes: list[Change] = []
        if path is None:
            return
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for c in data.get("changes", []):
            day = today + timedelta(days=int(c.get("day_offset", 0)))
            self._changes.append(
                Change(
                    at=f"{day.isoformat()}T{c.get('time', '00:00')}:00+00:00",
                    event_name=c["event_name"],
                    event_source=c["event_source"],
                    actor=c.get("actor", "unknown"),
                    resources=tuple(c.get("resources", [])),
                )
            )

    def write_events(self, service: str, start: date, end: date) -> list[Change]:
        sources = event_sources_for(service)
        lo, hi = start.isoformat(), (end + timedelta(days=1)).isoformat()
        picked = [
            c
            for c in self._changes
            if lo <= c.at < hi and is_write(c.event_name) and (not sources or c.event_source in sources)
        ]
        return sorted(picked, key=lambda c: c.at, reverse=True)
