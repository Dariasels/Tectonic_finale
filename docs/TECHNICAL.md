# How the system works (for the UI team)

All data is simulated: 10,261 people, 26 countries, 935 teams, ~9,600 documents from 6 tools (SharePoint, Teams, OneDrive, Notion, GitHub, Legacy drive), ~84k graph edges. Run `./dev.sh`; API docs at http://localhost:8000/docs. Generate data once: `cd backend && .venv/bin/python -c "from engine.seed_org import main; main()"` (data is git-ignored). First start takes ~10 s while the model trains.

## 1. Concepts
- **Graph**: one property graph. Nodes: Country, Department, Team, Person, Document, Topic, Client, Source. Edges: PART_OF/MEMBER_OF/REPORTS_TO (org tree), AUTHORED, APPROVED, REVIEWS, LISTED_AS (ignored for expertise), LINKS_TO (also across countries), SUPERSEDES, ABOUT, STORED_IN, and signal edges ATTENDED, COMMITTED, COMPLETED, INTERACTED_WITH.
- **Trust score (0-100)** per document = 85% XGBoost reliability (age, owner left, reviewers, source type, conflicts with other documents, replaced, PageRank/TrustRank/clustering...) + 15% author expertise. Badge: green >= 70, yellow 45-69, red < 45.
- **Context at query time** (does not change the stored score): other country x0.6, general policy when the question is about a customer x0.85, edited since last check x0.8, colleague votes (+4 confirm, -8 flag).
- **Verified** is a separate human badge (approved by someone higher in the REPORTS_TO chain). It is not a model input; it seeds TrustRank.
- **Expertise** per topic/customer from daily signals (authoring, approvals, reviews, meetings, commits, trainings, customer interactions), only for people who still work here. Same country first, other countries after.
- **Resolution memory**: one click "this helped" stores intent (topic, country, customer) -> person/document. Next person gets it as a shortcut. Confirmations fade (half-life 180 days) and drop if the person left or the document was replaced.
- **ACL**: every document has `acl` (`all`, `dept:HR Advisory`, `client:C01`). Enforced on the server; hidden documents are never returned.
- **Retraining policy**: a new document or material edit counts 1; cosmetic edit or duplicate counts 0. Retrain at 100 (about 1% of corpus) or after 7 days, never twice within 24 h, with an on/off switch. New documents are scored immediately without retraining.

## 2. The "keep it trusted" loop (what happens on upload)
`POST /api/documents` -> classify topic (if missing) -> dedupe (text similarity >= 0.85 and same value/country: nothing is added) -> score with the existing model (about 40 ms vs 6 s full rebuild) -> a human is asked ONLY if it contradicts a verified/other document, the model is unsure, or the topic is unclear. Approver = first active person above the author (nobody approves their own work); wrong user gets 403. Approving a conflicting update supersedes the old verified document, which turns red automatically.

## 3. Demo users
`GET /api/users` returns personas (ids change if data is regenerated, never hard-code them). Every call that acts as a user takes `user_id` (demo sign-in, no real auth).

## 4. Endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | /api/users, /api/meta | demo personas; topics, clients, countries, sources |
| GET | /api/search?q=&user_id=&country=&client= | main search (see shape below) |
| GET | /api/documents/{id}?user_id= | detail incl. `contributions`, `text` |
| POST | /api/documents | upload `{user_id,title,text,source,topic_id?,country?,client?,key_value?}` -> `status`: `published` / `pending_approval` / `duplicate`, `classified`, `approval`, `timings_ms` |
| POST | /api/documents/{id}/edit | `{user_id,text?,key_value?}` -> `material`, edit penalty, re-approval if it was verified |
| POST | /api/documents/{id}/vote | `{user_id,kind: confirm\|flag}` |
| GET | /api/approvals?user_id=&status= | approvals assigned to this user |
| POST | /api/approvals/{id}/decision | `{user_id,decision: approve\|reject}` |
| POST | /api/resolutions | `{user_id,topic,country,client,person_id\|doc_id}` ("this helped") |
| GET | /api/experts?topic=&client=&country= | who knows |
| GET | /api/org/overview, /org/country/{cc}, /org/department/{cc}/{dept}, /org/team/{id} | drill-down with health per level |
| GET | /api/risks?country= | topics with <= 1 active expert |
| GET | /api/model/status, POST /model/retrain, POST /model/settings | retraining policy and manual retrain |
| GET | /api/scale | people/documents/edges, full rebuild seconds, last ingest ms, speed-up |
| GET/POST | /api/profile | sign-in profile: team tools (team lead only, 403 otherwise), personal tools, opt-in signals, survey answers (`find`, `frequency`, `templates`, `versions`); switching a signal off updates expertise immediately |
| GET | /api/tools/status | tools connected for the user's team, adoption across all teams, teams without an official source |
| POST | /api/events/document | simulated webhook from a connected tool: metadata captured and scored at once; `status: ignored` if the tool is not connected for the team |
| GET | /api/documents/{id}/metadata | the metadata that is kept (source, title, author, team, country, language, topic, version, date, access, stated value) |
| GET | /api/demo/questions | 74 example questions per category with the persona that asks them |
| GET | /api/demo/samples, POST /api/demo/reset | ready-made uploads for the demo; reset state (takes ~10 s) |

### Search response (abridged)
```json
{"query": "...", "intent": {"mode": "topic|client|text", "topic": "parental_leave", "country": "BE", "client": null, "user_country": "ES"},
 "banner": {"type": "conflict", "message": "Sources disagree: ...", "values": [{"value": "...", "doc_ids": [], "best_trust": 86.8}]},
 "results": [{"doc_id": "H001", "title": "...", "source": "SharePoint", "country": "BE", "key_value": "17 weeks per parent",
   "trust": 86.8, "badge": "green", "in_scope": true, "verified": true, "pending_approval": false,
   "author": {"person_id": "...", "name": "...", "role": "...", "department": "...", "country": "BE", "active": true, "moved_from": null},
   "approved_by": {...}, "reasons": [{"sign": 1, "text": "Recently updated"}], "contributions": [{"label": "age", "effect": -0.4}]}],
 "related_notes": 12, "ask_expert": false,
 "experts": [{"person_id": "...", "name": "...", "country": "BE", "score": 0.98, "evidence": ["wrote 3", "90 customer interactions"], "same_country": true}],
 "shortcuts": [{"type": "person", "person": {...}, "confirmations": 3, "last_confirmed": "2026-10-02", "message": "..."}],
 "graph": {"nodes": [{"id": "H001", "type": "document|person", "label": "...", "badge": "green"}], "edges": [{"source": "", "target": "", "type": "AUTHORED|APPROVED|LINKS_TO|SUPERSEDES"}]},
 "timings_ms": 90}
```
`reasons[].sign`: +1 good, -1 bad, 0 info. `ask_expert` is true when nothing in scope scores 45 or more.

## 4b. Sign-in and connected tools
First visit shows a 3-step sign-in: pick a colleague (demo, no password) -> questions and tools (team tools editable by team leads only; survey asks the questions the interview left open: how often documents are made, templates, how the current version is known) -> privacy (opt-in signals) and simulated connect buttons. `?demo` in the URL skips the sign-in. Everything can be changed later under Connected tools. A team without SharePoint or GitHub gets a warning that its knowledge stays invisible; an upload from a tool that is not connected is ignored (event) or warned about (upload form).

## 5. UI screens (suggested, near-invisible by default)
1. **Search**: one box; result cards with colour badge, source icon, "why this score" expander (reasons + contributions), conflict banner, "who knows" panel with country flags, shortcut chip on top, "this helped" button on expert/document, confirm/flag.
2. **Approvals inbox** (only for people who have items): card per request with reason, one-click approve/reject (mock Teams card).
3. **Upload / template**: questionnaire (title, topic, country, customer, valid until, source), result shows published / needs approval / duplicate, with `timings_ms`.
4. **Organisation**: Country -> Department -> Team drill-down coloured by `health`, risks list.
5. **Model and scale**: retraining progress bar (`new_since_train / threshold`), policy switch, rebuild vs ingest timings.
Theme: Graphlas 2.0 (orange-to-purple header gradient, Montserrat, trust shown as green/yellow/red dots).

## 6. Honest limits (say them in the pitch)
Data and user feedback are simulated; the AUC (~0.95) shows the pipeline works, not real-world accuracy. Topic classification uses templated text. Graph metrics for a brand-new document are approximate until the next retrain. No real login. Connectors to Teams/SharePoint/OneDrive/Notion/GitHub are mocked; swapping in real APIs changes only the input, not the graph or the model.
