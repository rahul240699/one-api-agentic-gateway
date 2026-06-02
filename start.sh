#!/usr/bin/env bash
set -e
exec gunicorn app.main:app -w 1 -k uvicorn.workers.UvicornWorker --bind "0.0.0.0:${PORT:-10000}"
