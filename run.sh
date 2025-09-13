#!/usr/bin/env bash
# dev: uses reload for fast iteration
if [ "$1" = "dev" ]; then
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
else
  # production: multiple workers recommended (adjust worker count)
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
fi