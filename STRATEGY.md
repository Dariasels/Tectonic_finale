# Strategy: "Keep it trusted" layer on top of existing tools

Pitch line: **Find it. Understand it. Trust it. Keep it trusted.** One trust layer over Teams, SharePoint, OneDrive, Notion, GitHub and legacy drives. No migration, no extra documentation work. It also sits behind their existing copilot: the copilot retrieves, we score and explain.

## 1. Architecture
```
Sources (mock adapters)        Ingest                Graph + ML                 API / UI
Teams  SharePoint  OneDrive -> normalise to one  ->  one property graph     ->  FastAPI -> React
Notion GitHub  Legacy drive    Document schema       (org tree inside)          search, approvals,
                               + dedup + classify    + XGBoost trust model      org drill-down, experts
                               + ACL + signals       + expert scores
```
- Connector interface: each adapter yields `Document` (id, source, path, title, text, language, owner, authors, last_modified, version, acl, team, country) and `Signal` events (meeting attended, commit, PR review, training completed, client interaction). Demo adapters read fixtures; swapping in real APIs changes input only, not the graph.
- Source type is a model feature (official versioned SharePoint vs personal OneDrive vs meeting note vs legacy drive vs code repo).
- Per-team source mix (shows variety): Engineering = GitHub + Notion + Teams; HR/Payroll = SharePoint (templates) + Teams; Sales/CS = Teams + OneDrive + SharePoint; Country leads = Teams; legacy = shared drive + old C-drives.

### GitHub as a source (engineering teams)
READMEs and docs-in-repo; **CODEOWNERS = a real owner** (no "ownerless" documents); **PR reviews = built-in human verification** that costs nobody extra effort; commits show who really knows the code (`COMMITTED` edges); last commit date = freshness; stale repos get flagged.

## 2. Graph
One graph. Nodes: Country, Department, Team, Person, Document, Topic, Client, Source. Org tree edges: Team -PART_OF-> Department -IN-> Country; Person -MEMBER_OF-> Team; Person -REPORTS_TO-> Person.
Knowledge edges: AUTHORED, APPROVED, REVIEWS, LISTED_AS (does not count), LINKS_TO (also across countries), SUPERSEDES, ABOUT, STORED_IN, plus signal edges (ATTENDED, COMMITTED, COMPLETED, INTERACTED_WITH) that feed expertise.
The tree is used for: routing filter, approver lookup, ACL, team-health roll-up, expert filter.

## 3. Scoring (query-independent vs query-dependent)
- **Intrinsic trust** (stored, per document): XGBoost P(unreliable) on metadata, source type and graph features, plus 15% author expertise. Not dependent on the question.
- **Context fit** (at query time): country scope x0.6, customer-specific rules, language. Not used to route approvals.
- **Verified badge** (human): separate from the score; a verified document is a TrustRank seed.
- **Edit penalty**: a document edited since the last scoring gets a temporary x0.8 until re-verified or retrained.
- Team health = mean intrinsic trust of the team's documents.

## 4. What runs automatically
1. New document: classify (topic), dedupe (near-duplicate by TF-IDF cosine inside topic), score with the existing model (inference only, no rerun).
2. Retraining: weekly, or after N new documents (default 30), with a minimum gap between runs (no double training), a global on/off switch (holidays), and a stated rule on whether edits count as new documents (they do not; they trigger the edit penalty).
3. Signals from daily work (meetings, commits, PR reviews, trainings, client interactions) update expertise. Metadata only, aggregated, opt-in.
4. Review reminders from the template's "valid until" field.

## 5. When a human is needed
Only when the model is uncertain (probability near 0.5), when sources conflict, or when a template document is created. The approver is the first person above the author in the REPORTS_TO chain; nobody approves their own work. One click, shown as a mocked Teams card.

## 5b. Resolution memory (captured as a by-product of work)
When someone searches for a long time and finally finds the right contact or document, one click ("this helped") stores it: intent (topic, country, customer) -> person/document, with a confirmation count and last-confirmed date. The next person with the same intent gets that shortcut immediately ("3 colleagues confirmed: Anna, last 2 weeks ago") and skips the whole trajectory. Nobody writes documentation. Safeguards: confirmations decay over time; the shortcut is dropped if the person left or the document was superseded; it respects ACL; it boosts expert ranking but never overrides the document's own trust score. These confirmations are also implicit training labels, which replaces manual annotation.

## 6. Template (questionnaire) for new HR documents
Title, document type, owner, team, country, language, applies-to (country/customer), valid until, approver, source-of-truth link, supersedes (optional).

## 7. Role changes and people
Knowledge stays linked to the document its author wrote. After a role change the person is shown as "name, current department" with their internal career path; ownership transfers to the new owner; ties prefer someone still in the department. Previous employers are not used (only skills).

## 8. Privacy and security
ACL per document enforced on the server; HR-only documents are never returned to others. Team leads listed on many documents do not inflate expertise. Roles shown by default, names on click. Signals are opt-in, aggregated metadata. LLM never writes queries and never decides trust. No secrets in repo. Aikido scan early and before 15:00.

## 9. Assumptions (put on a slide)
Country > Department > Team is the standard hierarchy; not every team has a lead; every role exists in every country; templates will be adopted for new documents; interview did not answer: version tracking, existing templates, document creation frequency.

## 10. Build order (7h, 09:00 to 16:00)
1. Mock org + documents + signals generator (10k people, 26 countries, scale test data)
2. Port the engine: new schema, source features, ACL, incremental scoring, dedup, classifier, approvals
3. FastAPI endpoints
4. React UI: search with trust + explanation, approval queue, org drill-down, expert finder, SD Worx yellow-to-blue theme
5. Aikido baseline scan, then fixes
6. Demo video + ppt/pdf pitch (3 minutes)
7. Cut line: multilingual, Teams card mock, handover brief
