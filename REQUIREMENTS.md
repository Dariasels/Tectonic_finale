# Requirements

Living document. Claude updates it whenever scope, decisions, or status change.
Last updated: 2026-10-20 (hackathon day, context read, waiting for company interview)

## 1. Challenge (SD Worx finals: "One more challenge")
Round 1 question: *How might we turn fragmented organisational knowledge into a trusted shared resource?*
Finals extra: **Can your solution stay trusted without becoming another task?** ("Keep it trusted. Make it transparent.")
- Knowledge changes, people change roles, expertise evolves, context gets lost. The solution must stay useful, reliable and up to date **without people constantly documenting, updating or maintaining it**.
- Invisible UI, calm technology: automate what can happen in the background, verify only where human judgement adds real value, minimise effort, integrate into existing ways of working, be clear only when people need to know, decide or act.
- Think beyond documents: who has dealt with this before, who really knows this customer/topic, who knows how it works here, who knows why we do things this way. Examples (inspiration, not requirements): a new developer ("How do we do this here?", "Who should I talk to?"); a marketing campaign ("Who has done this before?", "Who knows what worked?"). Could the solution learn from signals already created through everyday work?
- Five questions to answer: (1) What happens automatically? (2) When is human verification genuinely valuable? (3) How do you prevent maintenance from becoming a burden? (4) How does it fit the user's workflow? (5) How does it stay understandable without constant attention?
- Goal is not zero human involvement, but **zero unnecessary effort**.
- Slogan: *Find it. Understand it. Trust it. Keep it trusted. Make it transparent. Make it effortless.*
- Decision: **build on the existing solution and code, do not restart.**

## 2. Day plan and judging (from the Finals Guide, source file in `context/`, not in git)
- Hacking 09:00 to 16:00 (**7 hours**). Submissions close **16:00**. "Final means final": no code or submission edits afterwards.
- Semi-final jury pitch: **3 min pitch + 5 min questions**, strict on time, in person. **Own devices are not allowed**; the demo must be presentable another way (USB stick, deployed URL, video). **Pitch presentation must be ppt or pdf.**
- SD Worx rooms 3 and 4 (16 teams); winner of the SD Worx track pitches again on stage at 18:30.
- Judging: Creativity 25%, Technical ability 20%, Fit 20%, **Pitch quality 25%**, Security 10%.
- Submit on Builderbase: short description, pitch (<3 min), GitHub repo link (**public until judging ends**), **Aikido screenshots** (final scan showing repo name and remaining vulnerabilities). Aikido: app.aikido.dev, sign in with GitHub, connect repo, fix issues, rescan before the deadline. Start early.
- Short README required (what it is, how to run, what is unfinished). Never commit passwords/API keys/confidential data.
- Partners onsite for questions: Aikido, SD Worx staff. Credits: Cursor, ElevenLabs (Discord coupons), Google Cloud (link in Builderbase, valid 1 week).

## 3. Starting point: GRAPHLAS (previous hackathon, github.com/larsvdb19/hackathon)
Streamlit app + Python modules, all data simulated (463 docs, 64 people, 16 topics, 4 clients, 3 countries).
- `seed_data.py`: simulated data, builds a networkx graph (Document, Person, Topic, Client nodes; WROTE, REVIEWS, LINKS_TO, SUPERSEDES, BELONGS_TO_TOPIC edges).
- `trust_engine.py`: graph metrics (PageRank, TrustRank, clustering, Louvain, betweenness), 14 features, **XGBoost** (monotone constraints) predicting P(unreliable), Trust Score = 85% model + 15% author expertise (personalised PageRank on the people graph), scope/customer penalties, feedback adjustments, plain-language reasons + feature contributions, expert fallback (only active people), bus-factor risk, validation vs baselines (top-1 correct about 88% vs newest 82%).
- `query_parser.py`: question to {topic, country, client} via Gemini, keyword fallback; `feedback.py`: confirm/flag votes with access check; `app.py`: Streamlit UI.
- Known weaknesses (the finals challenge targets exactly these): training labels come from **simulated feedback (annotation)**; the whole pipeline **reruns from scratch** for every change; maintenance of data is implicit; no workflow integration.

## 4. Proposed direction (to confirm after the company interview)
Keep the graph + ML scoring core. Move the front end to **React**, keep Python for the engine behind a FastAPI backend.
| Challenge question | Proposed answer |
|---|---|
| What is automatic? | Auto-categorise new documents; dedupe near-duplicates; incremental scoring of a new document with the existing model (no full rerun); scheduled periodic retrain; trust signals from everyday work (meetings, trainings, client interaction, repo activity) |
| Human verification only when valuable | Active learning: ask for verification only on low confidence or conflicting info; approver is **higher in the hierarchy** than the author (no self-evaluation) |
| Maintenance burden | Skip annotation of old data (weak/implicit labels); strict templates for new HR documents with a questionnaire for required fields |
| Workflow fit | Teams/database integration (mocked in the demo); notify only when action is needed |
| Understandable, calm UI | Near-invisible UI, SD Worx colours (yellow to blue gradient), free React building blocks |
| Beyond documents | "Who knows?" expert finding from the graph (roles, hierarchy, signals); team leads listed everywhere must not distort results |

## 5. Functional requirements
_To be filled after the interview and scope decision._
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| F-1 | _TBD_ | | |

## 6. Non-functional requirements
- Time budget: **7 hours of building (09:00 to 16:00)**, then pitch. Happy path works end to end.
- Demo must run without our own device: deployed URL and/or recorded video plus ppt/pdf pitch on USB.
- Security matters (10% + Aikido): no free-form queries from LLM, input validation, server-side access checks, no secrets in repo.
- Runs locally with `./dev.sh`.

## 7. Tech stack
- Frontend: React (Vite), Tailwind v4, react-router-dom, axios, recharts, lucide-react
- Backend: Python, FastAPI, pandas, numpy, scikit-learn; to port from GRAPHLAS: networkx, xgboost (shap optional), Gemini via google-genai (optional)
- Dev: Vite proxies `/api` to the backend on port 8000

## 8. Open questions
- **DEPLOYMENT:** ask organizers whether a live URL is required or a local/USB demo is enough (own devices not allowed). If a URL: Vercel frontend + Render backend, set up early.
- Interview with SD Worx: roles and hierarchy, document types, how data is shared internally, which workflow/tool to integrate (Teams?), which daily signals are really available.
- Tree graph vs random forest: leaning to keep XGBoost (already tree-based).
- Which one or two demo scenarios (new developer, marketing campaign, parental leave)?
- Which improvements make the cut for 7 hours?

## 9. Decisions log
| Date | Decision | Reason |
|------|----------|--------|
| 2026-10-19 | React + FastAPI | Team preference; fast to iterate |
| 2026-10-19 | Lovable/Cursor optional, not default | Avoid two tools editing one repo |
| 2026-10-20 | Build on GRAPHLAS, not restart | Team decision; graph + ML scoring is kept |
| 2026-10-20 | `context/` is git-ignored | 55 MB partner PDF should not go in a public repo |

## 10. Status
- [x] Scaffold, dev.sh, CLAUDE.md, subagents
- [x] Challenge + finals guide + old repo read
- [ ] Company interview and scope decision
- [ ] Port GRAPHLAS engine into `backend/` behind FastAPI
- [ ] React UI
- [ ] Aikido baseline scan (early) and fix round (before 15:00)
- [ ] Pitch (ppt/pdf, 3 min) and demo fallback
