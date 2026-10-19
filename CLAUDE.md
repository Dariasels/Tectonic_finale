# Tectonic (hackathon project)

Claude is the main builder and owns the thinking and the work. Lovable and Cursor are optional: ask the user to use one only when it clearly helps (e.g. Lovable for a quick UI draft), never by default.

## Layout
- `frontend/`: Vite + React, Tailwind v4, react-router-dom, axios, recharts, lucide-react. Dev proxy sends `/api` to port 8000.
- `backend/`: FastAPI in `main.py`, venv in `.venv`, deps in `requirements.txt` (re-freeze after installing).
- `REQUIREMENTS.md`: living requirements doc. Update it and push when scope, decisions, or status change.

## Run
`./dev.sh` starts both servers (frontend http://localhost:5173, API http://localhost:8000/docs).

## Rules
- All API routes live under `/api`. Keep frontend calls and backend routes in sync.
- Secrets go in `.env` (git-ignored); keep `.env.example` current.
- Commit small and often, push to `main`. Commit messages end with the Co-Authored-By line from the session.
- Run `npm run build` and hit the endpoint before calling a feature done.
- Subagents in `.claude/agents/`: reviewer, tester, researcher, demo-prep. Use them for separable jobs, not by default.
