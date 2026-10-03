"""Ship's log: put a cost story in front of the deployed agent and watch it work.

Runs on your machine, not in the emulator. For each run it:

  invokes  the deployed `finops-agent` Lambda on Floci with a fixture scenario,
           exactly as scripts/demo.sh does (one attempt: a client retry would
           run the agent twice and send the alert twice)
  reads    what the run left behind: the findings it archived in S3, its own
           JSON log lines in CloudWatch, and the message the Slack stand-in
           (finops-slack-catcher) received

The scenario's fixture files are the run's *input*; the page shows them
read through the agent's own FixtureCostSource, anchored to the same day, and
the per-engine "why not" lines use the agent's own detect.baseline_for. The
verdict, the explanation and the message are only ever the deployed
function's output.

Standard library plus boto3 (installed for the lab). Started by scripts/ops.sh.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import boto3
from botocore.config import Config

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "agent"))

from finops_agent.archive import slug  # noqa: E402
from finops_agent.detect import Thresholds, baseline_for, cost_on  # noqa: E402
from finops_agent.sources.changes import FixtureChangeSource, event_sources_for, is_write  # noqa: E402
from finops_agent.sources.cost import FixtureCostSource  # noqa: E402

PORT = int(os.environ.get("OPS_PORT", "8096"))
ENDPOINT = os.environ.get("AWS_ENDPOINT", "http://localhost:4566")
FIXTURES = Path(ROOT, "agent", "finops_agent", "fixtures")
SCENARIOS = ["quiet", "spike-nat", "new-service", "usage-spike", "multi"]
CATCHER = "finops-slack-catcher"
LOOKBACK = 14  # Deps.lookback_days
CHANGE_WINDOW = 2  # Deps.change_window_days


def terraform_outputs():
    out = subprocess.run(["terraform", f"-chdir={os.path.join(ROOT, 'terraform')}", "output", "-json"],
                         capture_output=True, text=True, check=True).stdout
    return {k: v["value"] for k, v in json.loads(out).items()}


TF = terraform_outputs()
FUNCTION, BUCKET, LOG_GROUP = TF["function_name"], TF["findings_bucket"], TF["log_group"]

session = boto3.session.Session(aws_access_key_id="test", aws_secret_access_key="test", region_name="us-east-1")
quick = Config(retries={"max_attempts": 2}, connect_timeout=3, read_timeout=15)
lam = session.client("lambda", endpoint_url=ENDPOINT, config=quick)
lam_invoke = session.client("lambda", endpoint_url=ENDPOINT,
                            config=Config(retries={"total_max_attempts": 1}, connect_timeout=3, read_timeout=150))
s3 = session.client("s3", endpoint_url=ENDPOINT, config=quick)
logs = session.client("logs", endpoint_url=ENDPOINT, config=quick)
events = session.client("events", endpoint_url=ENDPOINT, config=quick)


# --- reading the ship ---------------------------------------------------------------

def scenario_note(name):
    out = {}
    for kind in ("costs", "changes"):
        p = FIXTURES / f"{name}.{kind}.json"
        if p.exists():
            out[kind] = json.loads(p.read_text(encoding="utf-8")).get("note", "")
    return out


def function_state():
    c = lam.get_function_configuration(FunctionName=FUNCTION)
    env = c.get("Environment", {}).get("Variables", {})
    return {"name": FUNCTION, "state": c.get("State"), "runtime": c.get("Runtime"), "timeout": c.get("Timeout"),
            "memory": c.get("MemorySize"), "modified": c.get("LastModified"),
            "thresholds": {"ratio": float(env.get("FINOPS_RATIO", 0.25)),
                           "min_delta_usd": float(env.get("FINOPS_MIN_DELTA_USD", 1)),
                           "new_service_floor_usd": float(env.get("FINOPS_NEW_SERVICE_FLOOR_USD", 1)),
                           "baseline_days": 7, "dedupe_days": int(env.get("FINOPS_DEDUPE_DAYS", 3))},
            "explainer": env.get("FINOPS_EXPLAINER"), "notifier": env.get("FINOPS_NOTIFIER")}


def schedules():
    return [{"name": r["Name"].removeprefix(FUNCTION + "-"), "cron": r.get("ScheduleExpression"), "state": r.get("State")}
            for r in events.list_rules(NamePrefix=FUNCTION)["Rules"]]


def archive_index():
    keys, token = [], None
    while True:
        kw = {"Bucket": BUCKET, "Prefix": "findings/"}
        if token:
            kw["ContinuationToken"] = token
        page = s3.list_objects_v2(**kw)
        for o in page.get("Contents", []):
            parts = o["Key"].split("/")
            if len(parts) == 3:
                keys.append({"key": o["Key"], "day": parts[1], "service": parts[2].removesuffix(".json"),
                             "bytes": o["Size"], "written": int(o["LastModified"].timestamp() * 1000)})
        token = page.get("NextContinuationToken")
        if not token:
            break
    return sorted(keys, key=lambda k: (k["day"], k["service"]), reverse=True)


def catcher_state():
    p = subprocess.run(["docker", "inspect", "-f", "{{.State.Status}}", CATCHER], capture_output=True, text=True)
    return p.stdout.strip() or "missing"


def catcher_messages(since_s):
    p = subprocess.run(["docker", "logs", "--since", str(since_s), CATCHER], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    text = p.stdout + p.stderr
    return [m.strip() for m in re.findall(r"=== slack message received ===\n(.*?)\n=== end ===", text, re.S)]


def run_logs(since_ms):
    """The function's JSON log lines for runs since a moment, grouped by request id."""
    by_req, token = {}, None
    for _ in range(10):
        kw = {"logGroupName": LOG_GROUP, "startTime": since_ms}
        if token:
            kw["nextToken"] = token
        page = logs.filter_log_events(**kw)
        for e in page.get("events", []):
            parts = e["message"].split("\t")
            start = e["message"].find("{")
            if len(parts) < 3 or start < 0:
                continue
            try:
                body = json.loads(e["message"][start:])
            except ValueError:
                continue
            by_req.setdefault(parts[2], []).append({"ts": e["timestamp"], **body})
        token = page.get("nextToken")
        if not token or not page.get("events"):
            break
    return by_req


# --- the input, read the way the agent reads it -----------------------------------------

def logbook(scenario, day, thresholds):
    start = day - timedelta(days=LOOKBACK - 1)
    rows = FixtureCostSource(FIXTURES / f"{scenario}.costs.json", day).daily_by_service(start, day)
    t = Thresholds(ratio=thresholds["ratio"], min_delta_usd=thresholds["min_delta_usd"],
                   new_service_floor_usd=thresholds["new_service_floor_usd"])
    days = [(start + timedelta(days=i)).isoformat() for i in range(LOOKBACK)]
    engines = []
    for svc in sorted({r.service for r in rows}, key=lambda s: -cost_on(rows, s, day)):
        base, had = baseline_for(rows, svc, day, t)
        today = cost_on(rows, svc, day)
        engines.append({"service": svc, "burn": [round(cost_on(rows, svc, date.fromisoformat(d)), 4) for d in days],
                        "median": round(base, 4), "had_history": had, "today": round(today, 4),
                        "line_ratio": round(base * (1 + t.ratio), 4), "line_floor": round(base + t.min_delta_usd, 4),
                        "sources": list(event_sources_for(svc))})
    changes = FixtureChangeSource(FIXTURES / f"{scenario}.changes.json", day)._changes
    window_lo = (day - timedelta(days=CHANGE_WINDOW)).isoformat()
    orders = [{"at": c.at, "event": c.event_name, "source": c.event_source, "actor": c.actor,
               "resources": list(c.resources), "in_window": c.at[:10] >= window_lo,
               "write": is_write(c.event_name)} for c in changes]
    return {"days": days, "engines": engines, "orders": orders, "window_from": window_lo}


# --- a run ------------------------------------------------------------------------------

class Ship:
    def __init__(self):
        self.lock = threading.Lock()
        self.last = None
        self.busy = False

    def run(self, scenario):
        with self.lock:
            if self.busy:
                raise RuntimeError("a run is already under way")
            self.busy = True
        try:
            since_ms = int(time.time() * 1000) - 1000
            since_s = int(time.time()) - 1
            fn = function_state()
            t0 = time.monotonic()
            resp = lam_invoke.invoke(FunctionName=FUNCTION, Payload=json.dumps(
                {"mode": "daily", "cost_source": "fixture", "scenario": scenario}).encode())
            ms = round((time.monotonic() - t0) * 1000)
            summary = json.loads(resp["Payload"].read() or b"{}")
            if resp.get("FunctionError") or "errorMessage" in summary:
                raise RuntimeError(f"the function failed: {summary.get('errorType')}: {summary.get('errorMessage')}")
            day = date.fromisoformat(summary["day"])

            # The log stream lags the invoke. The run has no "done" line, but the
            # summary says how many findings it archived: wait for that many.
            want = len(summary.get("findings", []))
            deadline = time.monotonic() + 20
            while True:
                steps = run_logs(since_ms)
                req = next((r for r, ev in steps.items()
                            if any(e.get("msg") == "run starting" and e.get("scenario") == scenario for e in ev)), None)
                mine = sorted(steps.get(req, []), key=lambda e: e["ts"])
                msgs = [e.get("msg") for e in mine]
                if "detection done" in msgs and msgs.count("finding archived") >= want or time.monotonic() > deadline:
                    break
                time.sleep(0.5)
            # Each finding the summary reports, read from S3: by the key the log
            # line names, or (if the log stream is still behind) by the agent's
            # own key rule, archive.slug. Never leave a reported finding out.
            logged = {l["service"]: l["key"] for l in mine if l.get("msg") == "finding archived" and l.get("key")}
            findings = []
            for f in summary.get("findings", []):
                key = logged.get(f["service"]) or f"findings/{summary['day']}/{slug(f['service'])}.json"
                try:
                    body = json.loads(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read())
                    findings.append({"key": key, "read_by": "log" if f["service"] in logged else "key rule", **body})
                except Exception as e:
                    findings.append({"key": key, "missing": str(e), "service": f["service"]})

            result = {
                "scenario": scenario, "note": scenario_note(scenario), "ms": ms, "at": int(time.time() * 1000),
                "summary": summary, "request_id": req, "steps": mine, "findings": findings,
                "slack": catcher_messages(since_s), "catcher": catcher_state(),
                "log": logbook(scenario, day, fn["thresholds"]), "thresholds": fn["thresholds"],
                "other_runs": [r for r in steps if r != req],
            }
            with self.lock:
                self.last = result
            return result
        finally:
            with self.lock:
                self.busy = False


SHIP = Ship()


def snapshot():
    errors, fn, sched, archive = [], None, [], []
    for label, call in (("function", function_state), ("schedules", schedules), ("archive", archive_index)):
        try:
            v = call()
            fn = v if label == "function" else fn
            sched = v if label == "schedules" else sched
            archive = v if label == "archive" else archive
        except Exception as e:
            errors.append(f"{label}: {e}")
    with SHIP.lock:
        last, busy = SHIP.last, SHIP.busy
    return {"function": fn, "schedules": sched, "archive": archive, "catcher": catcher_state(), "bucket": BUCKET,
            "scenarios": [{"name": s, **scenario_note(s)} for s in SCENARIOS], "busy": busy, "last": last,
            "endpoint": ENDPOINT, "now": int(time.time() * 1000), "errors": errors}


# --- HTTP ---------------------------------------------------------------------

FONT_TYPES = {".woff2": "font/woff2"}


class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                self.send(200, f.read(), "text/html; charset=utf-8")
        elif path == "/api/ship":
            self.send(200, snapshot())
        elif path == "/frame":
            # Capture aid: the page at a phone width in a same-origin iframe
            # (headless Chrome will not open a window narrower than ~500px).
            q = self.path.partition("?")[2]
            w = re.search(r"(?:^|&)w=(\d+)", q)
            inner = re.sub(r"(?:^|&)w=\d+", "", q).lstrip("&")
            self.send(200, (f'<!doctype html><body style="margin:0"><iframe src="/?{inner}" '
                            f'style="width:{w[1] if w else 390}px;height:100vh;border:0;display:block"></iframe>').encode(),
                      "text/html; charset=utf-8")
        elif path.startswith("/fonts/") and "/" not in path[7:] and ".." not in path:
            f = os.path.join(HERE, "fonts", path[7:])
            if not os.path.isfile(f):
                return self.send(404, {"error": "no such font"})
            with open(f, "rb") as fh:
                self.send(200, fh.read(), FONT_TYPES.get(os.path.splitext(f)[1], "application/octet-stream"))
        else:
            self.send(404, {"error": f"no route for {path}"})

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except ValueError:
            return self.send(400, {"error": "body is not JSON"})
        try:
            if path == "/api/run":
                scenario = body.get("scenario")
                if scenario not in SCENARIOS:
                    return self.send(400, {"error": f"scenario must be one of {', '.join(SCENARIOS)}"})
                self.send(200, SHIP.run(scenario))
            else:
                self.send(404, {"error": f"no route for {path}"})
        except Exception as e:
            self.send(502, {"error": str(e)})

    def log_message(self, fmt, *args):
        if "/api/ship" not in self.path:
            print(f"{self.command} {self.path} -> {args[1] if len(args) > 1 else ''}", flush=True)


if __name__ == "__main__":
    print(f"ship's log on http://localhost:{PORT}  (function {FUNCTION}, emulator {ENDPOINT})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
