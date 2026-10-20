# Testing

Run everything: `cd backend && .venv/bin/python -m pytest tests -q` (about 80 s, builds the engine twice) and
`.venv/bin/python -m scripts.check_questions` (about 2.5 min, writes `docs/QUESTION_CHECK.md`).
All data is simulated, so these tests prove the pipeline and the rules, not real-world accuracy.

## What is tested (106 tests)
**Data (`tests/test_data.py`)**: sizes; unique ids; every person reaches the country lead (one per country); every reference
(author, team, topic, customer, tool, link) resolves; every document about a customer is customer-scoped (no leak); every edge type
connects the right kinds of nodes; one author edge per document; nobody approves their own work and the approver is above the author;
verified documents have an approver; replacing documents are newer; feedback tracks the hidden truth; signals exist only for people who opted in.

**Calculations (`tests/test_calculations.py`)**: trust = 85% model + 15% expertise for all ~9.6k documents; bounds; badge thresholds;
departed authors get no expertise; context multipliers (other country x0.6, general policy for a customer x0.85, edited x0.8, combinations);
colleague votes (+4 each up to +12, -8 each down to -32, clipped to 0..100); conflict share recomputed independently for 300 documents;
a replaced document does not penalise its successor; expertise recomputed by hand from the edges for random person/topic pairs;
normalisation per topic; people only *listed* on documents earn nothing; experts are active and same-country first;
the model is monotone where promised (older, owner left, no owner, replaced = never more reliable; more reviewers, more TrustRank = never less);
no answer-leaking inputs; AUC above 0.9; the demo scenarios behave as designed.

**Behaviour (`tests/test_behaviour.py`)**: access rules re-implemented independently and compared for every persona on 400 restricted documents;
search never returns hidden documents; all 77 curated questions pass; own-country default; "did you mean"; ask-an-expert; one vote per person;
conflicting update needs the approver above the author, wrong approver is refused, approving replaces the old verified document (which turns red);
rejection flags and notifies; duplicates add nothing; only a link and one short fact are kept; unconnected tools are ignored;
meeting titles are dissected, attendees without opt-in are not counted, titles without a topic or customer are not stored;
only team leads change team tools; linking and unlinking accounts switches their signals; switching a signal off removes it from expertise;
resolution memory (one confirmation per person, fades, dropped when the contact left); edit rules (cosmetic edit counts 0, material edit counts 1);
automatic retraining starts at the threshold and resets; never twice inside the minimum gap; ingest is much faster than a rebuild.

**Also covered since the pitch review**: a vote can be changed or undone; a conflict with an unverified document alone needs no approval (only conflicts with verified claims, an unclear topic or an unsure prediction do);
retraining only for higher management and the system admin; signing up (join a team, a team lead creates a team with tools, rules and limits); people search;
signed-up people survive a retrain; health per department and per country; the score validation (top answer 92% vs 83% newest, 42% most linked, 59% random; green 98%, red 20%).

**Answers (`tests/test_answers.py`)**: every result names a colleague who still works here; a departed owner is replaced by the closest colleague with an explanation; "where" is plain words and never a link (and matches the real tool and team); folders are read from the path of a saved file; company emails are unique and well formed; contact details appear only on click (never in search results) and not for people who left; signed-up people get an email; the reasons and model signals behind each score are kept.

**Clean-up (`tests/test_cleanup.py`)**: a preview changes nothing; a replaced document leaves only when its successor is verified; links are redirected; orphans follow every rule (no links, nobody left who contributed, unverified, older than a year) and young, linked, verified or looked-after documents stay; the only document on a subject goes to a person, not the bin; very low scores go to one named team lead, never the author, at most 5 each, never removed automatically; keep makes it verified and it is not offered again; remove is logged; removed documents vanish from search, health and conflict checks; restore needs the team lead or a technical person; the log is limited to team leads and technical people; verifying a new version removes the old one at once; retraining runs the clean-up when it is on; repeated sweeps settle.

**HTTP (`tests/test_api.py`)**: validation (ids, lengths, limits), unknown users, hostile input, no upload endpoint, link scheme checks,
403 for hidden documents and wrong approvers, profile rules, question list.

## Do the tests catch mistakes?
Four deliberate breakages were each caught: hidden documents visible to everyone, the approver equal to the author, the expert weight changed
from 0.15 to 0.20, and the scope penalty changed from 0.6 to 0.7.

## Bugs the tests and checks found (all fixed)
Country leads had no extra access (wrong level name); notes about a customer were visible to everyone; vague questions silently picked one topic;
re-assigned demo documents kept an approval from someone who was no longer above the author.

## Not covered
No browser tests of the screens (checked by eye in screenshots; dark mode and sign-in steps 2 and 3 were not viewed); no load test beyond
single requests (median search about 90 ms); no real OAuth or real tool connections (simulated); no test that the model stays good on real data.
