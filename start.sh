#!/bin/sh
# Entrypoint for Cloud Run: runs the Python API and Next.js frontend
# in a single container.  Cloud Run health-checks the Next.js port.

# Python API (internal only — Next.js proxies /api/backend/* to it)
python -m uvicorn api:app --host 127.0.0.1 --port 8000 &

# Next.js standalone server (Cloud Run sends traffic here)
cd /app/frontend
HOSTNAME=0.0.0.0 PORT=${PORT:-8080} exec node server.js
