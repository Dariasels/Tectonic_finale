#!/usr/bin/env bash
# Start backend and frontend together; Ctrl+C stops both.
set -e
cd "$(dirname "$0")"
[ -f backend/.env ] && set -a && . backend/.env && set +a
(cd backend && .venv/bin/uvicorn main:app --reload --port 8000) &
BACK=$!
trap 'kill $BACK 2>/dev/null' EXIT INT TERM
cd frontend && npm run dev
