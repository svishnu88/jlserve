#!/usr/bin/env bash
# Entrypoint for serverless_jlserve.
#
#   JLSERVE_APP   path to the customer's app file (default /model_weights/jlserve/app.py)
#   JLSERVE_PORT  port to serve on (default 8000; the platform's readiness probe expects it)
#
# Exit codes: 2 if the app file is missing, 3 if requirements never install,
# otherwise whatever `jlserve dev` exits with (non-zero when setup() raises).
set -uo pipefail

APP="${JLSERVE_APP:-/model_weights/jlserve/app.py}"
PORT="${JLSERVE_PORT:-8000}"
NET_WAIT="${JLSERVE_NET_WAIT_SECONDS:-120}"

if [ ! -f "$APP" ]; then
  echo "jlserve-entrypoint: app file not found: $APP" >&2
  exit 2
fi

# Requirements the app declares, read from the file without importing it.
mapfile -t REQS < <(python - "$APP" <<'PY'
import sys
from jlserve.requirements import extract_requirements_from_file
for r in extract_requirements_from_file(sys.argv[1]):
    print(r)
PY
)

# Install what is missing. If everything is already in the image this is an
# offline audit and returns at once. If something is missing, the worker may
# not have its network yet, so retry for a while before giving up.
if [ "${#REQS[@]}" -gt 0 ]; then
  echo "jlserve-entrypoint: requirements: ${REQS[*]}"
  deadline=$(( $(date +%s) + NET_WAIT ))
  until uv pip install "${REQS[@]}"; do
    if [ "$(date +%s)" -ge "$deadline" ]; then
      echo "jlserve-entrypoint: could not install requirements within ${NET_WAIT}s" >&2
      exit 3
    fi
    echo "jlserve-entrypoint: install failed, waiting for network ..." >&2
    sleep 5
  done
fi

echo "jlserve-entrypoint: starting $APP on port $PORT"
exec jlserve dev "$APP" --port "$PORT"
