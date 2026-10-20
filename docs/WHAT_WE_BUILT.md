# What we built, exactly (in three steps)

**1. Plugins into the graph base. 2. Graph + machine learning. 3. Name + score.**
All data is simulated (10,000+ people, 26 countries, about 9,600 documents). What is simulated and what is real is stated per step.

## 1. Plugins into the graph base (the input)
**Idea:** nothing is uploaded. Each tool the team already uses is connected; the tool tells Graphlas when something happens, and Graphlas keeps only a link and metadata.

**What is built**
- **Six tools:** Teams, SharePoint, OneDrive, Notion, GitHub, legacy drives. A team lead chooses which tools count for the team; each person can link their own account and switch signals on or off (opt-in, effective at once). Sign-up and sign-in screens collect this.
- **Two events per tool type** (`POST /api/events/document`, `POST /api/events/meeting`):
  - *File saved:* title, folder, tool, author, date, version, access rights, plus one extracted fact (for example "17 weeks per parent"). Kept: **link + metadata + that one fact**. Never the file. The topic, country and customer are worked out from the title and folder.
  - *Meeting planned:* title **and description** are read for topic, customer, country; attendees who opted in earn expertise; a meeting with no recognised topic ("catch-up") is not stored; the description is not kept.
- **Every event goes through the same pipeline:** duplicate check, topic classification if missing, scoring, and a human check only if needed. A new document takes about 40 ms (a full rebuild about 6 s).
- **Into the graph base:** one graph with nodes Country, Department, Team, Person, Document, Topic, Customer, Tool, and edges such as *part of, member of, reports to, wrote, approved, reviewed, links to, replaced by, about, stored in, owned by*, plus signal edges (*attended, committed, completed, interacted with*).

**Simulated vs real:** the events are produced by the *Live capture* page and by the data generator; the real OAuth connections and webhooks are not built (plan in `docs/CONNECTING_TOOLS.md`). In the demo the facts per document are annotated by us; in production a locally run agent does that (`docs/IMPROVEMENTS.md`).
**Code:** `backend/engine/tools.py`, `ingest.py`, `seed_org.py`; screens `Splash`, `Login`, `Tools`, `Capture`.

## 2. Graph + machine learning (the scoring)
**Idea:** the graph says how documents and people are connected; a model learns from colleague feedback which combinations of signals mean "unreliable".

**What is built**
- **Graph measures per document:** PageRank (popularity), TrustRank (trust flowing from verified documents along links), clustering (echo chamber), communities (silos), incoming links.
- **20 signals per document** (`docs/FEATURES.md`): age, no owner, no department, owner left, number of reviewers, version, incoming links, PageRank, TrustRank, clustering, links outside its group, conflict share (how many other live documents on the same subject state a different value), replaced, text overlap, and six tool flags.
- **Model:** XGBoost, 150 trees of depth 4, with rules it cannot break (older, owner left, no owner, replaced = never more reliable; more reviewers or TrustRank = never less). "Verified" is not an input; it only seeds TrustRank.
- **Training:** automatic, from colleague feedback (confirm, flag, approvals, rejections, "this helped"); simulated feedback in the demo. Retrains weekly or at 100 new or materially changed documents, never twice within 24 hours, only switchable by management or the system admin.
- **Expertise per person and topic or customer** from daily work: wrote 1.0, approved 0.7, reviewed 0.5, training 0.6, meeting 0.25, commits, customer contacts, "this helped" confirmations. Only people who still work here; being merely listed counts for nothing.
- **Human in the loop only at the edge:** a team lead or someone above the author approves only a conflict with a verified document, an unclear topic or an unsure prediction. Very low scores go to the team lead with the reasons.
- **Clean-up (the trash):** replaced and orphaned documents leave Graphlas by themselves; everything logged and restorable (`docs/REMOVAL.md`).

**How well it works (simulated data, hidden ground truth):** the top answer is a correct document 91% to 92% of the time, against 81% to 83% for "always the newest", 42% for "most linked", 60% for a random pick; 98% of green documents state the current value, against about 20% of red ones.
**Code:** `backend/engine/core.py`, `queries.py`, `ingest.py`, `cleanup.py`; checks in `tests/` (110 tests) and `scripts/check_questions.py` (77 curated and 1,274 generated questions).

## 3. Name + score (the answer)
**Idea:** the answer to a question is a **person**, with the trust score, the title of the file, and where it is kept.

**What is built**
- A question is understood (topic, country, customer; vague ones get "did you mean"), scoped to the right branch of the graph, and filtered by what the user may see (access rights enforced on the server).
- Each result shows only: **the name of the person to ask** (the owner, else the author, else, if they left, the closest colleague who is still here, with a note), **the trust score** (a green, yellow or red dot, 0 to 100), **the file title**, and **where it is kept in plain words** ("SharePoint › HR Advisory Belgium 1 › Policies"). No links.
- **Click the name:** contact card with role, team, manager and the company email.
- **"Why this score?"** keeps the explanation: what it says, author, verified by, the reasons in plain language, the biggest model signals (green raises trust, red lowers it, each stated as a fact), and confirm / flag (can be changed or undone).
- **Context:** another country counts ×0.6, a general rule for a customer question ×0.85, an edited, not yet re-verified document ×0.8. A conflict banner shows when sources disagree. "Other colleagues who can help" and "This helped" (the next person with the same question sees the confirmed contact first).
- **Why trust the score:** a card with the validation numbers above, public for everyone. Model, scale and live capture are only for the system admin, executives and higher management.
- Interface in 21 languages (main labels), white page with light pink options, optional light pink or dark background.

**Code:** `backend/engine/queries.py`, `tools.py`; screens `Search`, `PersonDialog`, `Approvals`.

## Where to read more
`docs/TECHNICAL.md` (endpoints and shapes) · `docs/FEATURES.md` (every signal) · `docs/REMOVAL.md` (the trash) · `docs/CONNECTING_TOOLS.md` (real connections) · `docs/IMPROVEMENTS.md` (agent and next steps) · `docs/PITCH.md` (script, slides, Q&A) · `docs/TESTING.md` · `docs/DEMO_NOTES.md` · `REQUIREMENTS.md` (decisions) · `STRATEGY.md`.
