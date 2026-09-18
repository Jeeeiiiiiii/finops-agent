"""Where daily cost-by-service comes from.

Two adapters behind one interface:

- CostExplorerSource  — ce:GetCostAndUsage, DAILY, grouped by SERVICE. The
                        real thing; Floci implements it locally too.
- FixtureCostSource   — a JSON file. What the tests and the demo scenarios
                        use, and how a spike is put in front of the agent on
                        demand without waiting for one to happen.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

from ..models import DailyCost


class CostSource(Protocol):
    def daily_by_service(self, start: date, end: date) -> list[DailyCost]:
        """Rows for every day in [start, end] inclusive. Missing days mean $0."""
        ...


class CostExplorerSource:
    def __init__(self, client) -> None:  # boto3 'ce' client
        self._ce = client

    def daily_by_service(self, start: date, end: date) -> list[DailyCost]:
        rows: list[DailyCost] = []
        token: str | None = None
        while True:
            kwargs = dict(
                TimePeriod={"Start": start.isoformat(), "End": (end + timedelta(days=1)).isoformat()},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )
            if token:
                kwargs["NextPageToken"] = token
            resp = self._ce.get_cost_and_usage(**kwargs)
            for bucket in resp.get("ResultsByTime", []):
                day = date.fromisoformat(bucket["TimePeriod"]["Start"][:10])
                for group in bucket.get("Groups", []):
                    usd = float(group["Metrics"]["UnblendedCost"]["Amount"])
                    if usd:
                        rows.append(DailyCost(day, group["Keys"][0], usd))
            token = resp.get("NextPageToken")
            if not token:
                return rows


class FixtureCostSource:
    """Reads {"costs": [{"day_offset": -3, "service": "...", "usd": 1.2}, ...]}.

    Offsets are relative to `today` so a scenario file never goes stale.
    """

    def __init__(self, path: Path, today: date) -> None:
        self._rows = self._load(path, today)

    @staticmethod
    def _load(path: Path, today: date) -> list[DailyCost]:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return [
            DailyCost(today + timedelta(days=int(r["day_offset"])), r["service"], float(r["usd"]))
            for r in data["costs"]
        ]

    def daily_by_service(self, start: date, end: date) -> list[DailyCost]:
        return [r for r in self._rows if start <= r.day <= end]
