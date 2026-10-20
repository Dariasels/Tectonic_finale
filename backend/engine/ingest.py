"""The "keep it trusted" loop: ingest, edit, approvals, votes, resolution memory, retraining policy."""
import threading
import time
import uuid

import numpy as np
import pandas as pd
from scipy import sparse

from .core import FEATURES, SRC_KEY, badge, EXPERT_WEIGHT
from .seed_org import REFERENCE_DATE
from .tools import make_link

DUP_SIM = 0.85            # text similarity above which an upload counts as a duplicate
UNSURE = 0.25             # |P(unreliable) - 0.5| below this: the model is unsure, ask a human
TOPIC_CONF = 0.6          # below this the auto-categoriser asks a human to confirm the topic


class IngestMixin:
    def _init_runtime(self):
        self.approvals = {}
        self.notifications = []
        self.resolutions = {}                 # intent key -> {("person"|"doc", id): {...}}
        self.policy = {"auto": True, "min_new_docs": 100, "max_days": 7, "min_gap_hours": 24}
        self.new_since_train = 0
        self.last_train = REFERENCE_DATE - pd.Timedelta(days=2)
        self.retrain_log = []
        self.ingest_ms = []
        self.pending_ids = set()
        self.event_log = []
        self.seen_votes = set()

    # --------------------------------------------------------------- ingestion
    def ingest(self, payload, user_id):
        """Add one document without a rerun: classify, dedupe, score with the existing model, route approval."""
        t0 = time.time()
        with self.lock:
            author = payload.get("author_id") or user_id
            if author not in self.persons.index:
                raise KeyError("unknown author")
            title = str(payload.get("title", "")).strip()[:200] or "Untitled"
            # only a short extracted fact is kept, never the document itself
            text = str(payload.get("extract") or payload.get("text") or title).strip()[:300]
            is_meeting = payload.get("doc_type") == "meeting"
            source = payload.get("source", "SharePoint")
            if source not in SRC_KEY:
                raise ValueError("unknown source")
            vec = self.vec.transform([f"{title}. {text}"])
            topic, classified = payload.get("topic_id"), None
            if topic and topic not in self.topics.index:
                raise ValueError("unknown topic")
            if not topic:
                probs = self.clf.predict_proba(vec)[0]
                i = int(np.argmax(probs))
                topic = self.clf.classes_[i]
                classified = {"topic_id": topic, "topic_name": self.topics.name[topic], "confidence": round(float(probs[i]), 2)}
            client = payload.get("client") or ""
            if client and client not in self.clients.index:
                raise ValueError("unknown client")
            country = payload.get("country") or self.persons.country[author]
            key_value = str(payload.get("key_value", ""))[:100]
            a = self.persons.loc[author]
            tkey = f"{topic}|{client}"
            idx = self.topic_rows.get(tkey, np.array([], dtype=int))
            sims = (vec @ self.X[idx].T).toarray().ravel() if len(idx) else np.array([])
            if len(sims) and not is_meeting:
                j = int(np.argmax(sims))
                twin = self.docs.index[idx[j]]
                if sims[j] >= DUP_SIM and self.docs.key_value[twin] == key_value and self.docs.country[twin] == country:
                    return {"status": "duplicate", "duplicate_of": twin, "similarity": round(float(sims[j]), 2),
                            "document": self.doc_json(self.docs.loc[twin]), "classified": classified,
                            "timings_ms": round((time.time() - t0) * 1000, 1),
                            "message": "Already known: nothing added, nobody has to check it again."}
            did = f"N{len(self.docs) + 1:05d}"
            row = {"doc_id": did, "title": title, "doc_type": payload.get("doc_type", "policy"), "topic_id": topic,
                   "country": country, "client": client, "department": a.department, "team_id": a.team_id,
                   "author_id": author, "owner_id": payload.get("owner_id") or author, "created": REFERENCE_DATE,
                   "last_modified": REFERENCE_DATE, "version": int(payload.get("version", 1)), "source": source,
                   "language": self.countries.language.get(country, "en"), "key_value": key_value, "verified": False,
                   "acl": payload.get("acl") or ("client:" + client if client else "all"), "text": text,
                   "link": str(payload.get("link") or make_link(source, self.teams.name.get(a.team_id, ""), did, a["name"])),
                   "edited": False, "pending": False}
            grp = self.groups.get((topic, country, client), [])
            diff = [y for y in grp if key_value and self.docs.key_value[y] != key_value and y not in self.superseded_by]
            f = {"age_days": 0, "no_owner": 0, "no_dept": 0, "owner_inactive": 0, "n_reviewers": 0,
                 "version": row["version"], "in_degree": 0, "pagerank": min(self.pagerank.values()),
                 "trustrank": min(self.trustrank.values()), "clustering": 0.0, "ext_link_ratio": 0.0,
                 "superseded": 0, "conflict_share": (len(diff) / len(grp)) if (key_value and grp) else 0.0,
                 "sim_max": float(sims.max()) if len(sims) else 0.0}
            for s, k in SRC_KEY.items():
                f[f"src_{k}"] = int(source == s)
            F = pd.DataFrame([f], index=[did])[FEATURES]
            p = float(self.model.predict_proba(F)[0, 1])
            drow = pd.Series(row, name=did)
            ae = self.author_expert(drow)
            ml = 100 * (1 - p)
            # register the document everywhere (graph, edges, text index, features, scores)
            self.docs = pd.concat([self.docs, pd.DataFrame([row]).set_index("doc_id", drop=False).astype(self.docs.dtypes.to_dict(), errors="ignore")])
            self.docs["last_modified"] = pd.to_datetime(self.docs["last_modified"])
            self.docs["created"] = pd.to_datetime(self.docs["created"])
            self.F = pd.concat([self.F, F])
            self.p_unreliable[did] = p
            self.ml_score[did] = ml
            self.author_exp[did] = ae
            self.trust[did] = (1 - EXPERT_WEIGHT) * ml + EXPERT_WEIGHT * 100 * ae
            self.X = sparse.vstack([self.X, vec]).tocsr()
            self.row_of[did] = self.X.shape[0] - 1
            self.topic_rows[tkey] = np.append(idx, self.X.shape[0] - 1)
            if key_value:
                self.groups[(topic, country, client)] = grp + [did]
            self.doc_graph.add_node(did)
            new_edges = [(author, did, "AUTHORED", 1), (did, topic, "ABOUT", 1), (did, source, "STORED_IN", 1),
                         (did, row["team_id"], "OWNED_BY", 1)]
            if client:
                new_edges.append((did, client, "ABOUT", 1))
            self.edges = pd.concat([self.edges, pd.DataFrame(new_edges, columns=self.edges.columns)], ignore_index=True)
            # does a human need to look at this? only if it matters
            why = []
            verified_conflict = [y for y in diff if self.docs.verified[y]]
            if is_meeting:                                   # meetings are signals, never reviewed
                diff, verified_conflict = [], []
            if verified_conflict:
                y = verified_conflict[0]
                why.append(f"Contradicts verified document {y}: '{key_value}' versus '{self.docs.key_value[y]}'")
            elif diff:
                why.append(f"Contradicts {len(diff)} existing document(s) on the same topic and country")
            if abs(p - 0.5) < UNSURE and not is_meeting:
                why.append("The model is unsure about this document")
            if classified and classified["confidence"] < TOPIC_CONF:
                why.append(f"Topic is unclear (best guess: {classified['topic_name']})")
            approval = None
            if why:
                approver = self.above(author) or self.countries_lead(country)
                approval = self._open_approval(did, approver, why)
            if payload.get("template") is not None and approval is None and p < 0.5:
                pass
            self._count_new(1)
            ms = round((time.time() - t0) * 1000, 1)
            self.ingest_ms.append(ms)
            self.stats["last_ingest_ms"] = ms
            out = {"status": "pending_approval" if approval else "published", "classified": classified,
                   "document": self.doc_json(self.docs.loc[did]), "approval": approval,
                   "timings_ms": ms, "retrain": self.retrain_status()}
            return out

    def countries_lead(self, cc):
        c = self.persons[(self.persons.country == cc) & (self.persons.role == "Country Lead")]
        return c.index[0] if len(c) else None

    # ---------------------------------------------------------------- approvals
    def _open_approval(self, doc_id, approver, why):
        aid = uuid.uuid4().hex[:8]
        self.approvals[aid] = {"approval_id": aid, "doc_id": doc_id, "requested_from": approver, "status": "pending",
                               "reasons": why, "created": str(REFERENCE_DATE.date())}
        self.docs.loc[doc_id, "pending"] = True
        self.pending_ids.add(doc_id)
        return self.approval_json(self.approvals[aid])

    def approval_json(self, a):
        d = self.docs.loc[a["doc_id"]]
        return {**a, "approver": self.person_card(a["requested_from"]), "author": self.person_card(d.author_id),
                "document": {"doc_id": d.doc_id, "title": d.title, "key_value": d.key_value, "source": d.source,
                             "topic_name": self.topics.name.get(d.topic_id, d.topic_id), "country": d.country,
                             "trust": round(float(self.trust[d.doc_id]), 1), "badge": badge(float(self.trust[d.doc_id])),
                             "extract": d.text, "link": d.link}}

    def list_approvals(self, user_id, status="pending"):
        return [self.approval_json(a) for a in self.approvals.values()
                if a["requested_from"] == user_id and a["status"] == status]

    def decide(self, approval_id, user_id, decision):
        with self.lock:
            a = self.approvals.get(approval_id)
            if not a:
                raise KeyError("unknown approval")
            if a["requested_from"] != user_id:                    # server-side check, nobody approves for someone else
                raise PermissionError("only the assigned approver can decide")
            if a["status"] != "pending":
                raise ValueError("already decided")
            if decision not in ("approve", "reject"):
                raise ValueError("decision must be approve or reject")
            did = a["doc_id"]
            v = self.votes.setdefault(did, {"confirm": 0, "flag": 0})
            if decision == "approve":
                self.docs.loc[did, "verified"] = True
                self.docs.loc[did, "edited"] = False
                self.approver[did] = user_id
                self.edges = pd.concat([self.edges, pd.DataFrame([(user_id, did, "APPROVED", 1)], columns=self.edges.columns)], ignore_index=True)
                v["confirm"] += 2
                self.extra_labels[did] = 0
                d = self.docs.loc[did]
                grp = self.groups.get((d.topic_id, d.country, d.client), [])
                old = [y for y in grp if y != did and d.key_value and self.docs.key_value[y] != d.key_value
                       and self.docs.verified[y] and y not in self.superseded_by]
                for y in old:                                          # the new verified value replaces the old one
                    self.superseded_by.setdefault(y, []).append(did)
                    self.docs.loc[y, "verified"] = False
                    self.approver.pop(y, None)
                    self.F.loc[y, "superseded"] = 1
                    self.edges = pd.concat([self.edges, pd.DataFrame([(did, y, "SUPERSEDES", 1)], columns=self.edges.columns)], ignore_index=True)
                self.F.loc[did, "conflict_share"] = 0.0
                self._rescore(old + [did])
            else:
                v["flag"] += 2
                self.extra_labels[did] = 1
                self.notifications.append({"to": self.docs.author_id[did], "text": f"Your document {did} was rejected by {self.persons.name[user_id]}"})
            a["status"] = "approved" if decision == "approve" else "rejected"
            self.docs.loc[did, "pending"] = False
            self.pending_ids.discard(did)
            self._count_new(0)
            return {"approval": self.approval_json(a), "document": self.doc_json(self.docs.loc[did])}

    def _rescore(self, ids):
        p = self.model.predict_proba(self.F.loc[ids])[:, 1]
        for did, pp in zip(ids, p):
            self.p_unreliable[did] = pp
            self.ml_score[did] = 100 * (1 - pp)
            self.trust[did] = (1 - EXPERT_WEIGHT) * self.ml_score[did] + EXPERT_WEIGHT * 100 * self.author_exp[did]

    # -------------------------------------------------------------------- edits
    def edit(self, doc_id, user_id, text=None, key_value=None):
        with self.lock:
            if doc_id not in self.docs.index:
                raise KeyError("unknown document")
            d = self.docs.loc[doc_id]
            if user_id not in (d.author_id, d.owner_id):
                raise PermissionError("only the author or owner can edit")
            old_text, old_val = d.text, d.key_value
            text = (text if text is not None else old_text)[:5000]
            key_value = key_value if key_value is not None else old_val
            sim = float((self.vec.transform([old_text]) @ self.vec.transform([text]).T).toarray()[0, 0])
            material = key_value != old_val or sim < 0.9
            self.docs.loc[doc_id, ["text", "key_value", "last_modified"]] = [text, key_value, REFERENCE_DATE]
            self.docs.loc[doc_id, "edited"] = True
            if key_value != old_val:
                grp = self.groups.get((d.topic_id, d.country, d.client), [])
                diff = [y for y in grp if y != doc_id and self.docs.key_value[y] != key_value]
                self.F.loc[doc_id, "conflict_share"] = len(diff) / max(len(grp) - 1, 1)
            self.F.loc[doc_id, "age_days"] = 0
            p = float(self.model.predict_proba(self.F.loc[[doc_id]])[0, 1])
            self.p_unreliable[doc_id] = p
            self.ml_score[doc_id] = 100 * (1 - p)
            self.trust[doc_id] = (1 - EXPERT_WEIGHT) * self.ml_score[doc_id] + EXPERT_WEIGHT * 100 * self.author_exp[doc_id]
            approval = None
            if d.verified:                                           # an edit removes the verified badge until re-approved
                self.docs.loc[doc_id, "verified"] = False
                self.approver.pop(doc_id, None)
                ap = self.above(d.author_id)
                if ap:
                    approval = self._open_approval(doc_id, ap, ["A verified document was edited and needs a new check"])
            if material:
                self._count_new(1)
            return {"material": material, "similarity": round(sim, 2), "approval": approval,
                    "document": self.doc_json(self.docs.loc[doc_id]), "retrain": self.retrain_status()}

    # -------------------------------------------------------------------- votes
    def vote(self, doc_id, user_id, kind):
        with self.lock:
            if kind not in ("confirm", "flag"):
                raise ValueError("kind must be confirm or flag")
            d = self.docs.loc[doc_id]
            if not self.can_see(user_id, d):
                raise PermissionError("no access to this document")
            if (doc_id, user_id) in self.seen_votes:
                raise ValueError("already voted")
            self.seen_votes.add((doc_id, user_id))
            self.votes.setdefault(doc_id, {"confirm": 0, "flag": 0})[kind] += 1
            self.extra_labels.setdefault(doc_id, 0 if kind == "confirm" else 1)
            return self.doc_json(d)

    # ------------------------------------------------------ resolution memory
    def resolve(self, user_id, topic, country, client, person_id=None, doc_id=None):
        """One click: 'this helped'. The next person with the same question skips the search."""
        with self.lock:
            if bool(person_id) == bool(doc_id):
                raise ValueError("give person_id or doc_id")
            if person_id and person_id not in self.persons.index:
                raise KeyError("unknown person")
            if doc_id and not self.can_see(user_id, self.docs.loc[doc_id]):
                raise PermissionError("no access to this document")
            key = self.intent_key(topic, country, client)
            tgt = ("person", person_id) if person_id else ("doc", doc_id)
            e = self.resolutions.setdefault(key, {}).setdefault(tgt, {"users": set(), "last": REFERENCE_DATE})
            if user_id in e["users"]:
                raise ValueError("already confirmed")
            e["users"].add(user_id)
            e["last"] = REFERENCE_DATE
            if person_id:
                xk = f"client:{client}" if client else f"topic:{topic}"
                self.res_bonus[(xk, person_id)] = min(0.6, self.res_bonus.get((xk, person_id), 0) + 0.2)
            else:
                self.extra_labels[doc_id] = 0                          # implicit label instead of annotation
            return {"intent": key, "confirmations": len(e["users"])}

    def shortcuts(self, topic, country, client):
        out = []
        for (kind, tid), e in self.resolutions.get(self.intent_key(topic, country, client), {}).items():
            age = (REFERENCE_DATE - e["last"]).days
            weight = len(e["users"]) * 0.5 ** (age / 180)               # confirmations fade
            if kind == "person":
                if not self.persons.active[tid]:
                    continue                                              # contact left: shortcut is dropped
                item = {"type": "person", "person": self.person_card(tid)}
            else:
                if tid in self.superseded_by:
                    continue                                              # document was replaced: dropped
                item = {"type": "document", "document": {"doc_id": tid, "title": self.docs.title[tid]}}
            out.append({**item, "confirmations": len(e["users"]), "last_confirmed": str(e["last"].date()),
                        "weight": round(weight, 2),
                        "message": f"{len(e['users'])} colleague(s) confirmed this, last on {e['last'].date()}"})
        return sorted(out, key=lambda x: -x["weight"])

    # ----------------------------------------------------- retraining policy
    def _count_new(self, n):
        self.new_since_train += n
        due, why = self._retrain_due()
        if due and self.policy["auto"]:
            threading.Thread(target=self.retrain, args=(why,), daemon=True).start()

    def _retrain_due(self):
        p = self.policy
        hours = (pd.Timestamp.now() - self.last_train_wall).total_seconds() / 3600 if getattr(self, "last_train_wall", None) is not None else 1e9
        if hours < p["min_gap_hours"] and getattr(self, "last_train_wall", None) is not None:
            return False, "gap"
        days = (REFERENCE_DATE - self.last_train).days
        if self.new_since_train >= p["min_new_docs"]:
            return True, f"{self.new_since_train} new or materially changed documents"
        if days >= p["max_days"]:
            return True, f"{days} days since the last training"
        return False, ""

    def retrain_status(self):
        p = self.policy
        return {"auto": p["auto"], "new_since_train": self.new_since_train, "threshold": p["min_new_docs"],
                "progress": round(min(1.0, self.new_since_train / p["min_new_docs"]), 2),
                "days_since": (REFERENCE_DATE - self.last_train).days, "max_days": p["max_days"],
                "min_gap_hours": p["min_gap_hours"], "last_trained": str(self.last_train.date()),
                "rule": "A new document or a material edit counts as 1. Cosmetic edits and duplicates count as 0. "
                        "Retrain at the threshold or after max_days, never twice within the minimum gap.",
                "log": self.retrain_log[-5:], "model_auc_cv": round(self.cv_auc, 3),
                "n_labels": self.n_labels}

    def retrain(self, reason="manual"):
        with self.lock:
            before = self.trust.copy()
            auc0 = self.cv_auc
            t0 = time.time()
            self.sync_tables()
            self.rebuild()
            secs = round(time.time() - t0, 2)
            changed = (self.trust.reindex(before.index) - before).abs()
            self.new_since_train = 0
            self.last_train = REFERENCE_DATE
            self.last_train_wall = pd.Timestamp.now()
            self.retrain_log.append({"reason": reason, "seconds": secs, "auc_before": round(auc0, 3),
                                     "auc_after": round(self.cv_auc, 3), "documents": int(len(self.docs)),
                                     "scores_changed_over_5_points": int((changed > 5).sum())})
            return self.retrain_log[-1]

    def set_policy(self, **kw):
        for k, v in kw.items():
            if k in self.policy and v is not None:
                self.policy[k] = type(self.policy[k])(v)
        return self.retrain_status()
