#!/usr/bin/env bash
# Build the Lambda zip: the package, its fixtures, and the anthropic SDK with
# Linux x86_64 wheels (the Lambda container is not this machine). boto3 is
# in the runtime already and is not bundled.
set -euo pipefail
cd "$(dirname "$0")/../agent"

BUILD=build
ZIP=finops-agent.zip
rm -rf "$BUILD" "$ZIP"
mkdir -p "$BUILD"

python -m pip install --quiet --upgrade \
  --target "$BUILD" \
  --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.12 \
  -r requirements.txt

cp -r finops_agent "$BUILD/finops_agent"
find "$BUILD" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$BUILD" -name 'tests' -type d -prune -exec rm -rf {} + 2>/dev/null || true

# python's zipfile so the archive is the same from Git Bash and from Linux.
python - <<'PY'
import os, zipfile
root, out = "build", "finops-agent.zip"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            z.write(p, os.path.relpath(p, root))
print(f"{out}: {os.path.getsize(out) / 1e6:.1f} MB")
PY
