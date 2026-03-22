#!/bin/sh
# Entrypoint for Cloud Run: runs the Python API and Next.js frontend
# in a single container.  Cloud Run health-checks the Next.js port.

echo "[start.sh] Starting Python API on :8000 ..."
python -m uvicorn api:app --host 127.0.0.1 --port 8000 &
API_PID=$!

# Wait for the API to actually respond on port 8000
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "[start.sh] Python API is healthy (pid=$API_PID)"
    break
  fi
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "[start.sh] FATAL: Python API crashed before becoming healthy." >&2
    exit 1
  fi
  sleep 1
done

# Final check
if ! curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
  echo "[start.sh] FATAL: Python API never became healthy after 10s." >&2
  kill "$API_PID" 2>/dev/null
  exit 1
fi

# Next.js standalone server (Cloud Run sends traffic here)
echo "[start.sh] Starting Next.js on :${PORT:-8080} ..."
cd /app/frontend
HOSTNAME=0.0.0.0 PORT=${PORT:-8080} exec node server.js
