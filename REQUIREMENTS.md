# Requirements

Living document. Claude updates it whenever scope, decisions, or status change.
Last updated: 2026-10-19 (prep complete, waiting for problem statement)

## 1. Problem statement
_TBD: provided on hackathon day._

## 2. Goals and success criteria
_TBD._

## 3. Functional requirements
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| F-1 | _TBD_ | | |

## 4. Non-functional requirements
- Demo-ready within the hackathon time limit; the happy path must work end to end.
- Runs locally with two commands (see README.md).

## 5. Tech stack
- Frontend: React (Vite), Tailwind CSS v4, react-router-dom, axios, recharts, lucide-react
- Backend: Python, FastAPI, uvicorn, pandas, numpy, scikit-learn
- Dev: Vite proxies `/api` to the backend on port 8000

## 6. Constraints and assumptions
- Claude is the main builder. Lovable and Cursor are optional, requested only when they clearly help.
- _Hackathon rules, judging criteria, and deadlines: TBD._

## 7. Open questions
- What is the problem, and how is it judged?

## 8. Decisions log
| Date | Decision | Reason |
|------|----------|--------|
| 2026-10-19 | React + FastAPI | Team preference; fast to iterate |
| 2026-10-19 | Lovable/Cursor optional, not default | Avoid two tools editing one repo |

## 9. Status
- [x] Scaffold: frontend, backend, health check wired through the proxy
- [x] Prep: CLAUDE.md, dev.sh, backend/.env.example, subagents (reviewer, tester, researcher, demo-prep)
- [ ] Requirements captured from problem statement
