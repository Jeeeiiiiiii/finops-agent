"""Pretty-print the JSON summary a Lambda invoke returns. Used by demo.sh.

Reads stdin: the function's response followed (with --output text) by the
status code line the CLI appends. Everything after the last '}' is ignored.
"""

import json
import sys

sys.stdin.reconfigure(encoding="utf-8", errors="replace")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
raw = sys.stdin.read()
body = raw[: raw.rfind("}") + 1]
try:
    d = json.loads(body)
except Exception:  # noqa: BLE001
    print(raw)
    sys.exit(0)

if "errorMessage" in d:
    print("    FUNCTION ERROR:", d.get("errorType"), d.get("errorMessage"))
    sys.exit(0)

if d.get("mode") == "digest":
    print("    digest sent:", d.get("sent"))
    print("    " + d.get("preview", "").replace("\n", "\n    "))
else:
    print(
        f"    services={d['services_seen']} total=${d['account_total_usd']:.2f} "
        f"explainer={d['explainer']} notifier={d['notifier']} notified={d['notified']}"
    )
    for f in d.get("findings", []):
        flag = "  [suppressed]" if f["suppressed"] else ""
        print(f"    - {f['service']}: {f['kind']} +${f['delta_usd']:.2f} confidence={f['confidence']} explained_by={f['explained_by']}{flag}")
    for n in d.get("notes", []):
        print("    note:", n)
