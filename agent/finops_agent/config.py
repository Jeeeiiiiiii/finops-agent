"""Turn environment + invocation payload into Deps.

This is the only module that reads os.environ or touches boto3 constructors,
so "what does this run talk to?" has one answer. Every choice is a small
enum-like string with a safe default that works with no account and no key:

    FINOPS_COST_SOURCE   ce | fixture            (default: fixture when no endpoint/credentials, else ce)
    FINOPS_CHANGE_SOURCE cloudtrail | fixture    (default follows cost source)
    FINOPS_SCENARIO      name of a fixture under finops_agent/fixtures/ (default: spike-nat)
    FINOPS_EXPLAINER     auto | rules | claude   (auto: claude if a key can be found, else rules)
    FINOPS_MODEL_PROVIDER anthropic | bedrock
    FINOPS_MODEL         model id (default claude-opus-5; bedrock: anthropic.claude-opus-5)
    FINOPS_NOTIFIER      auto | slack | stdout   (auto: slack if a webhook can be found, else stdout)
    FINOPS_BUCKET        S3 bucket for findings (no bucket -> in-memory archive)
    FINOPS_ENDPOINT      emulator endpoint for every AWS client ("" = real AWS)
    FINOPS_SLACK_SECRET_ID / FINOPS_SLACK_WEBHOOK_URL
    FINOPS_ANTHROPIC_SECRET_ID / ANTHROPIC_API_KEY
    FINOPS_RATIO, FINOPS_MIN_DELTA_USD, FINOPS_NEW_SERVICE_FLOOR_USD, FINOPS_DEDUPE_DAYS

The invocation payload may override `scenario`, `day`, `explainer`, `cost_source`
and `mode` so one deployed function can be poked at from the CLI.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import boto3

from .archive import MemoryArchive, S3Archive
from .detect import Thresholds
from .explain import RuleExplainer
from .investigate import Deps
from .notify import SlackNotifier, StdoutNotifier
from .sources.changes import CloudTrailSource, FixtureChangeSource
from .sources.cost import CostExplorerSource, FixtureCostSource

FIXTURES = Path(__file__).parent / "fixtures"
# Per-request ceiling for the model, and a budget for the whole investigation.
# The Lambda has 120s; one hung request must not eat all of it, or the rules
# fallback never gets its turn.
MODEL_TIMEOUT_S = 30.0
MODEL_TIME_BUDGET_S = 70.0
log = logging.getLogger("finops")


def log_event(msg: str, fields: dict[str, Any]) -> None:
    log.info(json.dumps({"msg": msg, **fields}, default=str))


@dataclass
class Settings:
    mode: str = "daily"
    day: date | None = None
    endpoint: str | None = None
    cost_source: str = "fixture"
    change_source: str = "fixture"
    scenario: str = "spike-nat"
    explainer: str = "auto"
    model_provider: str = "anthropic"
    model: str | None = None
    notifier: str = "auto"
    bucket: str | None = None
    region: str = "us-east-1"
    slack_secret_id: str | None = None
    slack_webhook_url: str | None = None
    anthropic_secret_id: str | None = None
    anthropic_api_key: str | None = None
    thresholds: Thresholds = Thresholds()
    dedupe_days: int = 3

    @classmethod
    def from_env(cls, event: dict[str, Any] | None = None) -> "Settings":
        env = os.environ
        event = event or {}
        endpoint = env.get("FINOPS_ENDPOINT") or None
        default_source = "ce" if (endpoint or env.get("AWS_ACCESS_KEY_ID") or env.get("AWS_EXECUTION_ENV")) else "fixture"
        cost_source = event.get("cost_source") or env.get("FINOPS_COST_SOURCE") or default_source
        # The change source follows the cost source unless something says otherwise:
        # a fixture scenario in the event must not be paired with the live trail.
        follows = "cloudtrail" if cost_source == "ce" else "fixture"
        if event.get("change_source"):
            change_source = event["change_source"]
        elif event.get("cost_source"):
            change_source = follows
        else:
            change_source = env.get("FINOPS_CHANGE_SOURCE") or follows
        s = cls(
            mode=event.get("mode") or env.get("FINOPS_MODE") or "daily",
            day=date.fromisoformat(event["day"]) if event.get("day") else None,
            endpoint=endpoint,
            cost_source=cost_source,
            change_source=change_source,
            scenario=event.get("scenario") or env.get("FINOPS_SCENARIO") or "spike-nat",
            explainer=event.get("explainer") or env.get("FINOPS_EXPLAINER") or "auto",
            model_provider=env.get("FINOPS_MODEL_PROVIDER") or "anthropic",
            model=env.get("FINOPS_MODEL") or None,
            notifier=event.get("notifier") or env.get("FINOPS_NOTIFIER") or "auto",
            bucket=env.get("FINOPS_BUCKET") or None,
            region=env.get("AWS_REGION") or env.get("AWS_DEFAULT_REGION") or "us-east-1",
            slack_secret_id=env.get("FINOPS_SLACK_SECRET_ID") or None,
            slack_webhook_url=env.get("FINOPS_SLACK_WEBHOOK_URL") or None,
            anthropic_secret_id=env.get("FINOPS_ANTHROPIC_SECRET_ID") or None,
            anthropic_api_key=env.get("ANTHROPIC_API_KEY") or None,
            thresholds=Thresholds(
                ratio=float(env.get("FINOPS_RATIO", 0.25)),
                min_delta_usd=float(env.get("FINOPS_MIN_DELTA_USD", 1.0)),
                new_service_floor_usd=float(env.get("FINOPS_NEW_SERVICE_FLOOR_USD", 1.0)),
            ),
            dedupe_days=int(env.get("FINOPS_DEDUPE_DAYS", 3)),
        )
        return s


class Wiring:
    """Builds Deps from Settings. Lazy about clients and secrets; a run that
    uses fixtures, rules and stdout never creates a boto3 client at all."""

    def __init__(self, s: Settings, today: date) -> None:
        self.s = s
        # Investigate the last complete day. "Today" is partial and Cost Explorer
        # lags a few hours, so comparing it with seven full days would hide spikes.
        self.today = s.day or (today - timedelta(days=1))
        self._clients: dict[str, Any] = {}
        self.explained_by = "rules"
        self.notifies_via = "stdout"

    def client(self, name: str):
        if name not in self._clients:
            self._clients[name] = boto3.client(name, region_name=self.s.region, endpoint_url=self.s.endpoint)
        return self._clients[name]

    def secret(self, secret_id: str | None) -> str | None:
        if not secret_id:
            return None
        try:
            resp = self.client("secretsmanager").get_secret_value(SecretId=secret_id)
        except Exception as e:  # noqa: BLE001 - a missing secret means "feature off", not "run failed"
            log_event("secret unavailable", {"secret_id": secret_id, "error": f"{type(e).__name__}"})
            return None
        value = resp.get("SecretString") or ""
        return value.strip() or None

    def fixture(self, kind: str) -> Path | None:
        candidates = [FIXTURES / f"{self.s.scenario}.{kind}.json", FIXTURES / f"{self.s.scenario}.json"]
        for p in candidates:
            if p.exists():
                return p
        return None

    # ---- the pieces ------------------------------------------------------ #

    def costs(self):
        if self.s.cost_source == "ce":
            return CostExplorerSource(self.client("ce"))
        path = self.fixture("costs")
        if path is None:
            raise FileNotFoundError(f"no cost fixture for scenario {self.s.scenario!r} under {FIXTURES}")
        return FixtureCostSource(path, self.today)

    def changes(self):
        if self.s.change_source == "cloudtrail":
            return CloudTrailSource(self.client("cloudtrail"))
        return FixtureChangeSource(self.fixture("changes"), self.today)

    def explainer(self, costs, changes):
        choice = self.s.explainer
        rules = RuleExplainer()
        if choice == "rules":
            return rules

        client = None
        if self.s.model_provider == "bedrock":
            from anthropic import AnthropicBedrockMantle

            client = AnthropicBedrockMantle(aws_region=self.s.region, timeout=MODEL_TIMEOUT_S, max_retries=1)
            model = self.s.model or "anthropic.claude-opus-5"
        else:
            key = self.s.anthropic_api_key or self.secret(self.s.anthropic_secret_id)
            if key:
                from anthropic import Anthropic

                client = Anthropic(api_key=key, timeout=MODEL_TIMEOUT_S, max_retries=1)
            model = self.s.model or "claude-opus-5"

        if client is None:
            if choice == "claude":
                log_event("explainer=claude requested but no API key found; using rules", {})
            return rules

        from .explain.claude import ClaudeExplainer

        self.explained_by = "claude"
        return ClaudeExplainer(client, costs, changes, model=model, fallback=rules, log=log_event, time_budget_s=MODEL_TIME_BUDGET_S)

    def archive(self):
        if self.s.bucket:
            return S3Archive(self.client("s3"), self.s.bucket)
        return MemoryArchive()

    def notifier(self):
        if self.s.notifier == "stdout":
            return StdoutNotifier()
        url = self.s.slack_webhook_url or self.secret(self.s.slack_secret_id)
        if url:
            self.notifies_via = "slack"
            return SlackNotifier(url)
        if self.s.notifier == "slack":
            log_event("notifier=slack requested but no webhook found; using stdout", {})
        return StdoutNotifier()

    def deps(self) -> Deps:
        costs = self.costs()
        changes = self.changes()
        return Deps(
            costs=costs,
            changes=changes,
            explainer=self.explainer(costs, changes),
            archive=self.archive(),
            notifier=self.notifier(),
            thresholds=self.s.thresholds,
            dedupe_days=self.s.dedupe_days,
            log=log_event,
        )
