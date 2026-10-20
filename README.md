# Graphlas 2.0 (repo: Tectonic_finale)
Hackathon finale. React (Vite + Tailwind) frontend, FastAPI backend. See REQUIREMENTS.md for scope and status.

## What we built
Read `docs/WHAT_WE_BUILT.md`: 1. plugins into the graph base, 2. graph + machine learning, 3. name + score.

## Run
Backend:  `cd backend && .venv/bin/uvicorn main:app --reload --port 8000`
Frontend: `cd frontend && npm run dev`  (http://localhost:5173, proxies /api -> :8000)

## Setup from scratch
`cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
`cd frontend && npm install`

## Tooling policy
Claude is the main builder. Lovable and Cursor (provided by the hackathon) are optional, not the default.
Claude will ask for one only when it clearly helps, e.g. Lovable for a quick UI draft that gets pasted back and wired to the backend.
Don't have two tools edit the repo at the same time.
