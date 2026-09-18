#!/usr/bin/env bash
# A stand-in for Slack: a tiny HTTP server on the emulator's Docker network
# that prints every webhook payload it receives. The function posts to it by
# container name, exactly as it would post to hooks.slack.com.
#
#   bash scripts/slack-catcher.sh          # start (idempotent)
#   docker logs -f finops-slack-catcher    # watch messages arrive
set -euo pipefail

NAME=finops-slack-catcher
NET=floci_default

if docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
  echo "$NAME already running on $NET (http://$NAME:8080/hook)"
  exit 0
fi
docker rm -f "$NAME" >/dev/null 2>&1 || true

docker run -d --name "$NAME" --network "$NET" python:3.12-alpine python -c '
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode("utf-8", "replace")
        try:
            text = json.loads(body).get("text", body)
        except Exception:
            text = body
        print("=== slack message received ===", flush=True)
        print(text, flush=True)
        print("=== end ===", flush=True)
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a):  # quiet
        pass

sys.stdout.reconfigure(encoding="utf-8")
HTTPServer(("0.0.0.0", 8080), H).serve_forever()
' >/dev/null

echo "$NAME listening on http://$NAME:8080/hook (inside $NET)"
