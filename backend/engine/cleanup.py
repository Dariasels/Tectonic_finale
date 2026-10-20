"""Automatic clean-up: superseded and orphaned documents leave Graphlas by themselves, very low scores go to the team lead.

"Removing" only stops Graphlas from showing a document (we keep links and metadata, never the file). Everything is logged and can be restored.
"""
import uuid

import pandas as pd

from .seed_org import REFERENCE_DATE

VERY_LOW = 20                 # intrinsic trust below this goes to the team lead for review, never removed automatically
REVIEW_CAP = 5                # open reviews per team lead at a time, so nobody gets an avalanche
ORPHAN_MIN_AGE_DAYS = 365     # a young document is never an orphan
KEEP_QUIET_DAYS = 180         # a document the team lead kept is not offered again for this long
GOOD = 70                     # an orphan only leaves if a trusted (green) document remains on the same subject


class CleanupMixin:
    def _live(self):
        return self.docs[~self.docs.retired]

    def _refresh_groups(self):
        d = self._live()
        self.groups = d[d.key_value != ""].groupby(["topic_id", "country", "client"]).doc_id.apply(list).to_dict()

    # ---------------------------------------------------------------- who reviews
    def reviewer_for(self, d):
        """The team lead of the owning team (never the whole team, never the author)."""
        who = self.teams.lead_id.get(d.team_id, "")
        if not (who and self.persons.active[who]):
            who = self.above(d.author_id)
        for _ in range(5):
            if who and who in (d.author_id, d.owner_id):
                who = self.above(who)
        return who or self.countries_lead(self.teams.country.get(d.team_id))

    # ------------------------------------------------------------------ retiring
    def retire(self, did, rule, by, successor=None, refresh=True):
        d = self.docs.loc[did]
        self.docs.loc[did, "retired"] = True
        entry = {"doc_id": did, "title": d.title, "location": self.where(d), "team_id": d.team_id, "rule": rule, "by": by,
                 "when": str(REFERENCE_DATE.date()), "successor": successor, "links_redirected": 0, "restored": False}
        entry["reason"] = {"superseded": "Replaced by a verified newer document.",
                           "orphan": "Nobody links to it, nobody who contributed is still here, it was never verified, and a trusted document on the same subject remains.",
                           "review": "The team lead judged that it can go."}[rule]
        if successor:                                            # links to the old document now point to its successor
            e = self.edges
            inc = e[(e.type == "LINKS_TO") & (e.target == did)].source.tolist()
            have = set(e[(e.type == "LINKS_TO") & (e.target == successor)].source)
            new = [(s, successor, "LINKS_TO", 1) for s in dict.fromkeys(inc)
                   if s != successor and s not in have and s in self.docs.index and not self.docs.retired[s]]
            if new:
                self.edges = pd.concat([self.edges, pd.DataFrame(new, columns=e.columns)], ignore_index=True)
                self.doc_graph.add_edges_from((s, t) for s, t, _, _ in new)
            entry["links_redirected"] = len(new)
        if did in self.doc_graph:
            self.doc_graph.remove_edges_from(list(self.doc_graph.in_edges(did)) + list(self.doc_graph.out_edges(did)))
        for a in self.approvals.values():                         # a document that is gone needs no check
            if a["doc_id"] == did and a["status"] == "pending":
                a["status"] = "cancelled"
        self.pending_ids.discard(did)
        self.docs.loc[did, "pending"] = False
        self.retired[did] = entry
        self.retire_log.append(entry)
        if refresh:
            self._refresh_groups()
        return entry

    def restore(self, did, user_id):
        if did not in self.retired:
            raise KeyError("this document was not removed")
        d = self.docs.loc[did]
        if not (self.can_retrain(user_id) or self.can_manage(user_id, d.team_id)):
            raise PermissionError("only the team lead of the owning team or a technical administrator can restore a document")
        with self.lock:
            self.docs.loc[did, "retired"] = False
            self.retired.pop(did)
            for e in self.retire_log:
                if e["doc_id"] == did and not e["restored"]:
                    e["restored"] = True
            self._refresh_groups()
            return self.doc_json(self.docs.loc[did])

    def cleanup_log(self, user_id, limit=200):
        if self.can_retrain(user_id):
            rows = self.retire_log
        elif self.persons.level[user_id] == "Team Lead":
            rows = [e for e in self.retire_log if self.can_manage(user_id, e["team_id"])]
        else:
            raise PermissionError("only team leads and technical administrators see the clean-up log")
        out = []
        for e in reversed(rows[-limit:]):
            succ = e["successor"]
            out.append({**e, "by_name": "Graphlas (automatic)" if e["by"] == "system" else self.persons.name.get(e["by"], e["by"]),
                        "successor_title": self.docs.title.get(succ) if succ else None})
        return out

    # ------------------------------------------------------------------- finding
    def _orphans(self):
        d = self._live()
        e = self.edges
        links = e[(e.type == "LINKS_TO") & e.source.isin(d.index)]
        indeg = links.target.value_counts()
        out = []
        for did, r in d.iterrows():
            if indeg.get(did, 0) > 0 or r.verified or (REFERENCE_DATE - r.last_modified).days < ORPHAN_MIN_AGE_DAYS:
                continue
            people = [r.owner_id, r.author_id, self.approver.get(did, "")] + self.reviewers.get(did, [])
            if any(p and self.persons.active[p] for p in people):
                continue
            out.append(did)
        return out

    def _no_good_alternative(self, did, going=()):
        """True if no other live, trusted document (green) remains on the same subject. Then a person decides, not the sweep."""
        r = self.docs.loc[did]
        d = self._live()
        same = d[(d.topic_id == r.topic_id) & (d.country == r.country) & (d.client == r.client) & (d.index != did)]
        same = same[~same.index.isin(list(going))]
        return not (self.trust[same.index] >= GOOD).any()

    def _open_reviews(self):
        out = {}
        for a in self.approvals.values():
            if a.get("kind") == "review" and a["status"] == "pending":
                out[a["requested_from"]] = out.get(a["requested_from"], 0) + 1
        return out

    def _open_review(self, did, why):
        d = self.docs.loc[did]
        who = self.reviewer_for(d)
        aid = uuid.uuid4().hex[:8]
        self.approvals[aid] = {"approval_id": aid, "doc_id": did, "requested_from": who, "status": "pending", "kind": "review",
                               "reasons": why, "created": str(REFERENCE_DATE.date())}
        return who

    # ----------------------------------------------------------------------- run
    def cleanup(self, run_by="system", dry_run=False):
        """One sweep: remove replaced and orphaned documents, send very low scores to the team lead."""
        with self.lock:
            out = {"superseded": [], "orphans": [], "protected": [], "reviews_opened": 0, "reviews_waiting": 0, "dry_run": dry_run}
            for old, news in list(self.superseded_by.items()):
                if old not in self.docs.index or self.docs.retired[old]:
                    continue
                succ = [n for n in news if n in self.docs.index and self.docs.verified[n] and not self.docs.retired[n]]
                if succ:
                    out["superseded"].append(old)
                    if not dry_run:
                        self.retire(old, "superseded", run_by, succ[0], refresh=False)
            review = []
            orphans = self._orphans()
            for did in orphans:
                if self._no_good_alternative(did, going=orphans):     # nothing trusted would remain on that subject: a person decides
                    out["protected"].append(did)
                    review.append(did)
                else:
                    out["orphans"].append(did)
                    if not dry_run:
                        self.retire(did, "orphan", run_by, refresh=False)
            if not dry_run:
                self._refresh_groups()
            live = self._live()
            t = self.trust[live.index]
            open_now = self._open_reviews()
            already = {a["doc_id"] for a in self.approvals.values() if a.get("kind") == "review" and a["status"] == "pending"}
            low = [i for i in t[t < VERY_LOW].sort_values().index if i not in self.superseded_by]
            for did in dict.fromkeys(review + low):               # documents nobody may remove automatically come first
                if did in already or self.docs.retired[did] or did in out["orphans"]:
                    continue
                if (REFERENCE_DATE - self.review_kept.get(did, REFERENCE_DATE - pd.Timedelta(days=999))).days < KEEP_QUIET_DAYS:
                    continue
                who = self.reviewer_for(self.docs.loc[did])
                if open_now.get(who, 0) >= REVIEW_CAP:
                    out["reviews_waiting"] += 1                    # waits until the team lead has handled some
                    continue
                out["reviews_opened"] += 1
                open_now[who] = open_now.get(who, 0) + 1
                if not dry_run:
                    d = self.docs.loc[did]
                    why = [f"Trust score {t.get(did, self.trust[did]):.0f} is very low"] + [x for s, x in self.reasons(d) if s < 0][:4]
                    self._open_review(did, why)
            self.stats["last_cleanup"] = {k: (len(v) if isinstance(v, list) else v) for k, v in out.items()}
            return out

    def decide_review(self, a, user_id, decision):
        if decision not in ("keep", "remove"):
            raise ValueError("a review is answered with keep or remove")
        did = a["doc_id"]
        with self.lock:
            if decision == "keep":                                # the team lead judged it reliable: it counts as verified
                import pandas as pd2
                self.docs.loc[did, "verified"] = True
                self.approver[did] = user_id
                self.edges = pd2.concat([self.edges, pd2.DataFrame([(user_id, did, "APPROVED", 1)], columns=self.edges.columns)], ignore_index=True)
                v = self.votes.setdefault(did, {"confirm": 0, "flag": 0})
                v["confirm"] += 2
                self.extra_labels[did] = 0
                self.review_kept[did] = REFERENCE_DATE
                a["status"] = "kept"
            else:
                self.retire(did, "review", user_id)
                a["status"] = "removed"
            return {"approval": self.approval_json(a), "document": self.doc_json(self.docs.loc[did]), "removed": decision == "remove"}
