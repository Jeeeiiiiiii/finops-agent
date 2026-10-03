#!/usr/bin/env bash
# The engine-room log: run each cost story through the deployed agent and
# watch the arithmetic, the remark, the filed finding and the radio message.
# Needs the lab up (emulator, slack-catcher.sh, terraform apply) and boto3.
set -euo pipefail
cd "$(dirname "$0")/.."

PY="$(command -v python3 || command -v python)"
echo "open http://localhost:${OPS_PORT:-8096}"
exec "$PY" ops/server.py
