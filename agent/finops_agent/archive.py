"""Where findings go, whether or not anyone was told.

Layout in the bucket:  findings/<YYYY-MM-DD>/<service-slug>.json

Two questions the archive answers:
- recently_alerted(service, days): was a notification for this service
  actually delivered in the last N days? Only findings with sent=True count,
  so a failed Slack post never silences the next day's alert. If so today's
  finding is archived but suppressed: a three-day spike is one alert.
- since(days): every finding in a window, for the weekly digest.
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Protocol

from .models import Finding, finding_from_json, to_json


def slug(service: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", service.lower()).strip("-") or "unknown"


class FindingsArchive(Protocol):
    def put(self, finding: Finding) -> str: ...
    def recently_alerted(self, service: str, day: date, days: int) -> date | None: ...
    def since(self, day: date, days: int) -> list[Finding]: ...


class S3Archive:
    def __init__(self, client, bucket: str, prefix: str = "findings") -> None:  # boto3 's3' client
        self._s3 = client
        self._bucket = bucket
        self._prefix = prefix.strip("/")

    def _key(self, day: date, service: str) -> str:
        return f"{self._prefix}/{day.isoformat()}/{slug(service)}.json"

    def put(self, finding: Finding) -> str:
        key = self._key(finding.day, finding.service)
        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=json.dumps(to_json(finding), indent=1).encode("utf-8"),
            ContentType="application/json",
        )
        return key

    def _get(self, key: str) -> Finding | None:
        try:
            obj = self._s3.get_object(Bucket=self._bucket, Key=key)
        except self._s3.exceptions.NoSuchKey:
            return None
        return finding_from_json(json.loads(obj["Body"].read().decode("utf-8")))

    def recently_alerted(self, service: str, day: date, days: int) -> date | None:
        for i in range(1, days + 1):
            d = day - timedelta(days=i)
            f = self._get(self._key(d, service))
            if f is not None and f.sent:
                return d
        return None

    def since(self, day: date, days: int) -> list[Finding]:
        out: list[Finding] = []
        for i in range(days):
            d = day - timedelta(days=i)
            token = None
            while True:
                kwargs = dict(Bucket=self._bucket, Prefix=f"{self._prefix}/{d.isoformat()}/")
                if token:
                    kwargs["ContinuationToken"] = token
                resp = self._s3.list_objects_v2(**kwargs)
                for item in resp.get("Contents", []):
                    f = self._get(item["Key"])
                    if f:
                        out.append(f)
                token = resp.get("NextContinuationToken")
                if not token:
                    break
        out.sort(key=lambda f: (f.day, -f.evidence.anomaly.delta_usd), reverse=True)
        return out


class MemoryArchive:
    """In-process; for tests and the local CLI."""

    def __init__(self) -> None:
        self.items: dict[tuple[date, str], Finding] = {}

    def put(self, finding: Finding) -> str:
        self.items[(finding.day, slug(finding.service))] = finding
        return f"memory/{finding.day.isoformat()}/{slug(finding.service)}.json"

    def recently_alerted(self, service: str, day: date, days: int) -> date | None:
        for i in range(1, days + 1):
            d = day - timedelta(days=i)
            f = self.items.get((d, slug(service)))
            if f is not None and f.sent:
                return d
        return None

    def since(self, day: date, days: int) -> list[Finding]:
        lo = day - timedelta(days=days - 1)
        found = [f for (d, _), f in self.items.items() if lo <= d <= day]
        found.sort(key=lambda f: (f.day, -f.evidence.anomaly.delta_usd), reverse=True)
        return found
