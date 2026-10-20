# Features used

All data is simulated. "Feature" here means (A) the signals the ML model reads, (B) the signals that feed expertise, (C) the context rules applied per question, (D) product features.

## A. ML model: 20 signals per document (XGBoost predicts P(unreliable))
| Feature | Meaning | Constraint |
|---|---|---|
| age_days | days since last modification | older never more reliable |
| no_owner | document has no owner (GitHub always has one via CODEOWNERS) | more = less reliable |
| no_dept | no department assigned | |
| owner_inactive | owner/author no longer works at the company | more = less reliable |
| n_reviewers | people who reviewed it (PR reviewers on GitHub) | more = more reliable |
| version | version number | |
| in_degree | incoming links from other documents | |
| pagerank | popularity in the link graph | |
| trustrank | trust flowing from verified documents along links | more = more reliable |
| clustering | do its neighbours only link to each other (echo chamber) | |
| ext_link_ratio | share of links leaving its own community (Louvain) | |
| conflict_share | share of other live documents (same topic, country, customer) that state a different value; replaced documents are ignored | |
| superseded | replaced by a newer version | more = less reliable |
| sim_max | text overlap with another document on the same topic | |
| src_sharepoint / src_onedrive / src_teams / src_notion / src_github / src_legacy | which tool the document lives in (6 flags) | |

Not a model input on purpose: `verified` (human approval). It only seeds TrustRank and gives a visible badge.
Training labels: simulated colleague feedback (flag rate >= 35% = unreliable; documents of departed owners are flagged more). Later: implicit labels from approvals, rejections and confirmed answers.

## B. Expertise signals (who knows), per topic or customer
| Signal | Weight | Source tool |
|---|---|---|
| Authored a document | 1.0, x(1 + 2 x TrustRank percentile of the document) | SharePoint, Notion, OneDrive, GitHub |
| Approved a document | 0.7 | SharePoint approval |
| Reviewed a document / pull request | 0.5 | SharePoint, GitHub PR reviews |
| Completed a training on the topic | 0.6 | training records |
| Attended a meeting about it | 0.25 | Teams meeting titles |
| Committed to a repo document | 0.3 x log(1 + commits) | GitHub |
| Customer interactions | min(4, 0.06 x count) | CRM / client interaction |
| Confirmed by colleagues as the right contact ("this helped") | +0.2 each, max +0.6 | resolution memory |
Not counted: being listed as a team lead on a document someone else wrote (LISTED_AS). Only people who still work here are suggested; same country first.

## C. Context rules at question time
Different country than the question x0.6 | general policy when asking about a customer x0.85 | edited since last check x0.8 | colleague confirm +4 (max +12), flag -8 (max -32) | document ACL (all, department, customer) | expert shortcuts fade with a 180-day half-life and drop if the person left or the document was replaced.

## D. Product features
Trust score with colour and plain-language reasons | conflict banner | "ask this expert" fallback | who-knows panel across countries | resolution memory | documents are never uploaded: tools send events, only the link and metadata are kept | Teams meeting titles are dissected into topic, customer and country, attendance becomes expertise (opt-in) | topic found from title and folder | duplicate detection | incremental scoring (about 40 ms vs 6 s full rebuild) | approval by the first active person above the author (nobody approves their own work) | approving a conflicting update replaces the old verified document | edit penalty until re-verified | weekly or 100-document retraining with on/off switch | organisation drill-down (country, department, team) with health | knowledge-risk list (topics with <= 1 active expert) | ACL enforced on the server | per-team tool mix (Teams, SharePoint, OneDrive, Notion, GitHub, legacy drives) | planned: Teams-style approval card, multilingual questions.
