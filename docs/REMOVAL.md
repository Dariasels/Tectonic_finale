# The trash: how removal works

## What "removing" means
Graphlas keeps links and metadata, never the file. So removing a document only means **Graphlas stops showing it**: it disappears from search, from the health numbers, from the conflict checks and from the graph. **The file itself stays in SharePoint, Teams, Notion or wherever it lives.** Every removal is written to a log (what, why, who or "automatic", when, the successor) and can be **restored** by the team lead of the owning team or a technical administrator. It is a trash can, not a shredder.

## Three ways a document ends up in the trash
| Case | What happens | Who decides |
|---|---|---|
| **Replaced** (policy 2025 after policy 2026) | Leaves as soon as the newer version is **verified**. Links to the old one now point to the new one. | Automatic |
| **Orphan** (nobody links to it, nobody who contributed is still here) | Leaves, but only if: no document that stays links to it, owner, author, approver and reviewers have all left, it was never verified, it is over a year old, **and** a trusted document (score 70 or higher) remains on the same subject. | Automatic |
| **Very low score** (below 20) | **Never removed automatically.** The team lead of the owning team (not the whole team, never the author) is asked: "Do you want to remove this document?", with the reasons. | The team lead |

### What the team lead sees
A card with the file title, where it is kept, the score and the reasons ("Trust score 1 is very low", "Last updated 6.8 years ago", "Julia Weber no longer works at the company", "Never reviewed", "Contradicts ..."), and two buttons:
- **Yes, remove it**: goes to the trash and the log.
- **No, keep it: it is reliable**: counts as verified by the team lead and is not offered again for 180 days.
At most 5 open reviews per team lead at a time; the rest wait, so nobody gets an avalanche.

## When it runs
- Right when an approver verifies a new version (the old one leaves at once).
- After each retraining (weekly or at 100 new documents), if clean-up is switched on.
- On demand by a technical administrator (Model & scale, "Run clean-up now", with a "Preview" that changes nothing).

## Safeguards
- Never touches the source file.
- A document is never removed automatically if nothing trusted would remain on its subject: a person decides.
- Young, linked, verified or looked-after documents are never orphans.
- Nobody reviews their own work; one named person, not a group.
- Everything is logged and restorable. Removed documents are left out of the model's checks, but stay in the log.
- Removing a document cancels any approval that was waiting for it.
- Repeated sweeps settle after two rounds (removing documents can leave new orphans behind; the rules still apply to those).

## Where to see and restore
- Team lead: **Approvals** page, section "Trash (removed automatically)", with a Restore button.
- Technical administrator: **Model & scale**, "Automatic clean-up": switch, preview, run now, recently removed with Restore.

## What it did on the simulated data (about 9,600 documents)
212 replaced documents left (all of them stated an outdated value); about 70 orphans left; 2 to 9 were kept for a person to judge; about 730 low scores went to team leads (at most 5 each, 48 waiting). The model's quality did not change (AUC 0.963 to 0.961).

## Open decision
How long does the trash keep entries before the metadata is purged for good? Proposal: 90 days, then purge, unless restored.
