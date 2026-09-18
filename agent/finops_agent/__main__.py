"""Run the agent from a terminal, no Lambda, no account:

    python -m finops_agent                         # spike-nat scenario, rules explainer, stdout
    python -m finops_agent --scenario quiet
    python -m finops_agent --explainer claude      # needs ANTHROPIC_API_KEY
    python -m finops_agent --cost-source ce --endpoint http://localhost:4566   # live Cost Explorer on Floci
    python -m finops_agent --mode digest
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from .handler import run


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="finops-agent", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["daily", "digest"], default=None)
    p.add_argument("--scenario", default=None, help="fixture name under finops_agent/fixtures/")
    p.add_argument("--day", default=None, help="YYYY-MM-DD to investigate; default yesterday (UTC), the last complete day")
    p.add_argument("--cost-source", choices=["ce", "fixture"], default=None)
    p.add_argument("--change-source", choices=["cloudtrail", "fixture"], default=None)
    p.add_argument("--explainer", choices=["auto", "rules", "claude"], default=None)
    p.add_argument("--notifier", choices=["auto", "slack", "stdout"], default=None)
    p.add_argument("--endpoint", default=None, help="emulator endpoint, e.g. http://localhost:4566")
    p.add_argument("--bucket", default=None, help="S3 bucket for findings (default: in-memory)")
    p.add_argument("--json", action="store_true", help="print the run summary as JSON")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)

    # Slack text carries arrows and bullets; a cp1252 console must not crash on them.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(level=logging.INFO if a.verbose else logging.WARNING, format="%(message)s", stream=sys.stderr)
    if a.endpoint:
        os.environ["FINOPS_ENDPOINT"] = a.endpoint
        os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    if a.bucket:
        os.environ["FINOPS_BUCKET"] = a.bucket
    if not a.endpoint and not a.cost_source:
        os.environ.setdefault("FINOPS_COST_SOURCE", "fixture")

    event = {k: v for k, v in {
        "mode": a.mode, "scenario": a.scenario, "day": a.day, "cost_source": a.cost_source,
        "change_source": a.change_source, "explainer": a.explainer, "notifier": a.notifier,
    }.items() if v}
    summary = run(event)
    if a.json:
        print(json.dumps(summary, indent=2))
    else:
        alerted = [f for f in summary.get("findings", []) if not f["suppressed"]]
        print(f"\n[{summary['mode']}] {summary['day']} · explainer={summary['explainer']} notifier={summary['notifier']}", file=sys.stderr)
        if summary["mode"] == "daily":
            print(f"services={summary['services_seen']} total=${summary['account_total_usd']:.2f} findings={len(summary['findings'])} alerted={len(alerted)} notified={summary['notified']}", file=sys.stderr)
            for n in summary.get("notes", []):
                print(f"note: {n}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
