"""Query side: parse a question, rank documents the user may see, explain, find experts, org roll-ups."""
import re
import time

import numpy as np
import pandas as pd
import xgboost as xgb

from .core import (SRC_KEY, EDIT_PENALTY, GENERIC_PENALTY, NICE, SCOPE_PENALTY, FEATURES, badge)

STOP = {"policy", "process", "procedure", "template", "rules", "guidelines", "agreement", "sheet", "working", "key"}
SYNONYMS = {
    "parental_leave": ["ouderschapsverlof", "congé parental", "geboorteverlof", "permiso parental", "baja parental",
                       "elternzeit", "parental", "baby"],
    "pension": ["pensioen", "retraite", "pension", "jubilación", "âge de la retraite", "rente", "retirement"],
    "company_car": ["bedrijfswagen", "voiture de société", "firmenwagen", "coche de empresa", "company car", "leasewagen"],
    "payroll_cutoff": ["cutoff", "afsluitdatum", "deadline loonlijst"],
    "sick_leave": ["ziekteverlof", "ziekte", "ziek", "arbeidsongeschiktheid", "baja por enfermedad", "congé maladie", "sick"],
    "remote_work": ["telewerk", "thuiswerk", "home office", "télétravail", "teletrabajo", "remote"],
    "gdpr_retention": ["gdpr", "avg", "bewaartermijn", "personnel file", "how long do we keep", "data retention", "privacy"],
    "build_pipeline": ["build pipeline", "ci/cd", "pipeline", "build"],
    "deployment_process": ["deployment", "deploy", "release process", "naar productie", "production release"],
    "incident_response": ["incident", "on call", "outage", "storing"],
    "client_sla": ["sla", "service level"],
    "client_contacts": ["contacts", "contact person", "contactpersoon", "who is the contact", "key contact"],
    "correction_process": ["correct", "correction", "error", "mistake", "fout", "rectificatie"],
    "bonus_payment": ["bonus", "13th month", "dertiende maand"],
    "escalation_path": ["escalate", "escalation path"],
    "training_budget": ["opleidingsbudget", "opleiding", "formation", "formación"],
    "working_hours": ["werkuren", "arbeidsduur", "werktijd", "heures de travail"],
    "expense_policy": ["onkosten", "onkostenvergoeding", "dépenses", "gastos", "expenses"],
    "api_guidelines": ["api"],
    "leave_carryover": ["carry over", "overdracht verlof", "verlof overdragen"],
    "year_end_closing": ["jaarafsluiting", "year end", "clôture annuelle"],
    "tax_withholding": ["bedrijfsvoorheffing", "withholding", "précompte"],
}
COUNTRY_SYN = {"espagne": "ES", "alemania": "DE", "allemagne": "DE", "belgica": "BE", "pays bas": "NL", "polonia": "PL",
               "pologne": "PL", "francia": "FR", "italia": "IT", "oostenrijk": "AT", "belgië": "BE", "belgie": "BE", "belgique": "BE", "nederland": "NL", "holland": "NL", "duitsland": "DE",
               "frankrijk": "FR", "spanje": "ES", "españa": "ES", "polen": "PL", "polska": "PL", "italië": "IT",
               "oostenrijk": "AT", "griekenland": "GR", "zweden": "SE", "denemarken": "DK", "uk": "GB"}
CLIENT_TOPIC = {"payroll_cutoff": "client_cutoff", "escalation_path": "client_escalation"}
SRC_TEXT = {"SharePoint": "official, versioned", "GitHub": "versioned, reviewed through pull requests",
            "Teams": "meeting notes", "OneDrive": "personal drive", "Notion": "personal workspace",
            "Legacy drive": "legacy drive without metadata"}


class QueryMixin:
    # ------------------------------------------------------------------ parsing
    def parse_query(self, text):
        norm = lambda t: re.sub(r"[-_/]", " ", t.lower())
        q = norm(text)
        has = lambda w: re.search(rf"\b{re.escape(norm(w))}", q) is not None
        country = None
        for name, cc in COUNTRY_SYN.items():
            if has(name):
                country = cc
        for cc, row in self.countries.iterrows():
            if has(row["name"]):
                country = cc
        if not country:
            m = re.search(r"\b(?:in|for|voor|en|à)\s+([A-Z]{2})\b", text)
            if m and m.group(1) in self.countries.index:
                country = m.group(1)
        client = next((cid for cid, r in self.clients.iterrows() if has(r["name"])), None)
        best, best_score = None, 0.0
        scored = []
        for tid, r in self.topics.iterrows():
            score = 0.0
            for syn in SYNONYMS.get(tid, []):
                if has(syn):
                    score = max(score, 1.0 + len(syn) / 100)
            words = [w for w in re.split(r"\s+", norm(r["name"])) if w not in STOP and len(w) >= 3]
            if words:
                hit = [w for w in words if has(w)]
                if hit and len(hit) / len(words) >= 0.5:
                    score = max(score, len(hit) / len(words) + sum(map(len, hit)) / 100)
            if score > 0:
                scored.append((score, tid))
            if score > best_score:
                best, best_score = tid, score
        scored.sort(reverse=True)
        close = [t for sc, t in scored[:4] if sc >= best_score - 0.1 and not t.startswith("client_")]
        ambiguous = best_score < 1.0 and len(close) >= 2          # only a partial match on several topics
        return {"topic": best, "country": country, "client": client, "alternatives": close if ambiguous else []}

    # -------------------------------------------------------------------- votes
    def vote_delta(self, doc_id):
        v = self.votes.get(doc_id, {"confirm": 0, "flag": 0})
        return min(12, 4 * v["confirm"]) - min(32, 8 * v["flag"])

    def final_trust(self, d, country=None, client=None):
        t = float(self.trust[d.doc_id])
        notes = []
        in_scope = True
        if country and d.country not in (country, "ALL"):
            t *= SCOPE_PENALTY
            in_scope = False
            notes.append((-1, f"Applies to {self.countries.name.get(d.country, d.country)}, not "
                              f"{self.countries.name.get(country, country)} (score x{SCOPE_PENALTY})"))
        if client and not d.client:
            t *= GENERIC_PENALTY
            notes.append((-1, f"General policy: {self.clients.name[client]} may have its own agreement (score x{GENERIC_PENALTY})"))
        if d.client:
            notes.append((0, f"Customer-specific document for {self.clients.name[d.client]}"))
        if d.edited:
            t *= EDIT_PENALTY
            notes.append((-1, f"Edited since the last check: score x{EDIT_PENALTY} until re-verified or retrained"))
        delta = self.vote_delta(d.doc_id)
        if delta:
            notes.append((1 if delta > 0 else -1, f"Colleague feedback: {delta:+d} points"))
        return float(min(100, max(0, t + delta))), in_scope, notes

    # ------------------------------------------------------------------ explain
    def reasons(self, d):
        x = self.F.loc[d.doc_id]
        out = []
        yrs = x.age_days / 365
        out.append((-1, f"Last updated {yrs:.1f} years ago") if yrs >= 1.5
                   else (1, f"Recently updated ({int(x.age_days)} days ago)"))
        out.append((0, f"Stored in {d.source} ({SRC_TEXT[d.source]})"))
        if x.no_owner:
            out.append((-1, "No owner assigned"))
        else:
            out.append((1, f"Owner: {self.persons.name[d.owner_id]}" + (" (CODEOWNERS)" if d.source == "GitHub" else "")))
        if x.owner_inactive:
            who = self.persons.name[d.owner_id or d.author_id]
            out.append((-1, f"{who} no longer works at the company"))
        elif self.author_exp[d.doc_id] >= 0.5:
            out.append((1, f"Author {self.persons.name[d.author_id]} is a top expert here"))
        revs = self.reviewers.get(d.doc_id, [])
        pr = "pull request reviewers" if d.source == "GitHub" else "Reviewed by"
        out.append((1, f"{pr}: " + ", ".join(self.persons.name[r] for r in revs[:3])) if revs else (-1, "Never reviewed"))
        if d.doc_id in self.approver:
            out.append((1, f"Verified by {self.persons.name[self.approver[d.doc_id]]} (higher in the hierarchy)"))
        for o in self.superseded_by.get(d.doc_id, []):
            out.append((-1, f"Replaced by \"{self.docs.title[o]}\""))
        grp = self.groups.get((d.topic_id, d.country, d.client), [])
        diff = sorted([y for y in grp if y != d.doc_id and self.docs.key_value[y] != d.key_value],
                      key=lambda y: self.docs.last_modified[y], reverse=True)
        for o in diff[:2]:
            out.append((-1, f"Contradicts \"{self.docs.title[o]}\": '{d.key_value}' versus '{self.docs.key_value[o]}'"))
        if len(diff) > 2:
            out.append((-1, f"... and {len(diff) - 2} more documents state a different value"))
        if x.in_degree >= 4 and self.ml_score[d.doc_id] < 50:
            out.append((-1, f"Linked {int(x.in_degree)} times but probably outdated: popular is not reliable"))
        if x.n_reviewers == 0 and x.ext_link_ratio == 0 and self.doc_graph.degree(d.doc_id) >= 2:
            out.append((-1, "Echo chamber: only linked inside its own cluster and never reviewed"))
        if d.doc_id in self.listed:
            out.append((0, "A team lead is listed on this document but did not write it (ignored for expertise)"))
        return out

    def signal_text(self, feature, row):
        """A signal in plain words that says what is TRUE for this document (not just the name of the signal)."""
        v = row[feature]
        med = self._signal_medians
        if feature == "age_days":
            y = v / 365
            return f"Last updated {y:.1f} years ago" if y >= 1.5 else "Recently updated"
        if feature == "no_owner":
            return "No owner" if v else "Has an owner"
        if feature == "no_dept":
            return "No department" if v else "Belongs to a department"
        if feature == "owner_inactive":
            return "Owner left the company" if v else "Owner still works here"
        if feature == "n_reviewers":
            return "Never reviewed" if v == 0 else f"Reviewed by {int(v)} {'person' if v == 1 else 'people'}"
        if feature == "version":
            return f"Version {int(v)}"
        if feature == "in_degree":
            return "Nobody links to it" if v == 0 else f"Linked from {int(v)} other documents"
        if feature == "pagerank":
            return "Many documents point to it (popular)" if v > med["pagerank"] else "Few documents point to it"
        if feature == "trustrank":
            return "Trusted documents point to it" if v > med["trustrank"] else "Few trusted documents point to it"
        if feature == "clustering":
            return "Only linked inside its own small group" if v > 0.3 else "Linked across different groups"
        if feature == "ext_link_ratio":
            return "Reaches outside its own group" if v > 0.3 else "Only connected inside its own group"
        if feature == "conflict_share":
            return f"Conflicts with {round(v * 100)}% of the other documents on this subject" if v > 0 else "No conflicts with other documents"
        if feature == "superseded":
            return "Replaced by a newer version" if v else "Not replaced"
        if feature == "sim_max":
            return "Almost identical to another document" if v > 0.9 else "Has its own content"
        if feature.startswith("src_"):
            tool = next(t for t, k in SRC_KEY.items() if f"src_{k}" == feature)
            return f"Stored in {tool}" if v else f"Not stored in {tool}"
        return NICE[feature]

    def contributions(self, doc_id, n=4):
        """The biggest reasons behind the model's score. Each says what is true; effect > 0 raises trust (shown green), < 0 lowers it (red)."""
        if not hasattr(self, "_signal_medians"):
            self._signal_medians = {"pagerank": float(self.F.pagerank.median()), "trustrank": float(self.F.trustrank.median())}
        row = self.F.loc[[doc_id]]
        c = self.model.get_booster().predict(xgb.DMatrix(row), pred_contribs=True)[0][:-1]
        s = pd.Series(c, index=FEATURES)
        top = s.reindex(s.abs().sort_values(ascending=False).index)[:n]
        vals = row.iloc[0]
        return [{"label": self.signal_text(k, vals), "effect": round(-float(v), 2)} for k, v in top.items()]  # minus: contribution to P(unreliable)

    def doc_json(self, d, country=None, client=None, detail=False):
        t, in_scope, notes = self.final_trust(d, country, client)
        out = {"doc_id": d.doc_id, "title": d.title, "doc_type": d.doc_type, "source": d.source,
               "country": d.country, "language": d.language, "topic_id": d.topic_id,
               "topic_name": self.topics.name.get(d.topic_id, d.topic_id),
               "client": d.client or None, "client_name": self.clients.name.get(d.client) if d.client else None,
               "key_value": d.key_value, "trust": round(t, 1), "badge": badge(t), "in_scope": in_scope,
               "verified": bool(d.verified), "pending_approval": bool(d.pending), "edited": bool(d.edited),
               "last_modified": str(d.last_modified.date()), "version": int(d.version),
               "author": self.person_card(d.author_id), "owner": self.person_card(d.owner_id),
               "approved_by": self.person_card(self.approver.get(d.doc_id)),
               "team": self.teams.name.get(d.team_id, ""), "acl": d.acl, "location": self.where(d),
               "holder": self.person_card(self.holder(d)[0]), "holder_note": self.holder(d)[1],
               "reasons": [{"sign": s, "text": x} for s, x in self.reasons(d) + notes]}
        if detail:
            out["contributions"] = self.contributions(d.doc_id)
            out["extract"] = d.text            # one extracted fact; the document itself is never stored
            out["links_in"] = int(self.F.in_degree[d.doc_id])
            out["intrinsic_trust"] = round(float(self.trust[d.doc_id]), 1)
        return out

    # ------------------------------------------------------------------- search
    def intent_key(self, topic, country, client):
        return f"{topic or '-'}|{country or '-'}|{client or '-'}"

    def search(self, text, user_id, country=None, client=None, limit=10):
        t0 = time.time()
        text = (text or "").strip()[:300]
        if user_id not in self.persons.index:
            raise KeyError("unknown user")
        user = self.persons.loc[user_id]
        parsed = self.parse_query(text)
        topic = parsed["topic"]
        country = country or parsed["country"]
        client = client or parsed["client"]
        defaulted = False
        if topic and not country and not client and bool(self.topics.scoped.get(topic, False)):
            country, defaulted = user.country, True          # country-specific topic without a country: use the user's own
        d = self.docs
        if topic:
            topics = [topic] + ([CLIENT_TOPIC[topic]] if client and topic in CLIENT_TOPIC else [])
            cand = d[d.topic_id.isin(topics)]
            if client and topic not in CLIENT_TOPIC and not topic.startswith("client_"):
                cand = cand[(cand.client == "") | (cand.client == client)]
            elif client:
                cand = cand[(cand.client == client) | (cand.client == "")]
            mode = "topic"
        elif client:
            cand = d[d.client == client]
            mode = "client"
        else:
            sims = (self.vec.transform([text]) @ self.X.T).toarray().ravel() if text else np.zeros(len(d))
            cand = d.iloc[np.argsort(-sims)[:60]]
            cand = cand[sims[[self.row_of[i] for i in cand.index]] > 0.05]
            mode = "text"
        cand = cand[~cand.retired]
        cand = cand[[self.can_see(user_id, r) for r in cand.itertuples()]]
        related_notes = 0
        if mode == "topic" and (cand.key_value != "").sum() >= 2:      # keep loose notes out of the main list
            related_notes = int((cand.key_value == "").sum())
            cand = cand[cand.key_value != ""]
        rows = []
        for r in cand.itertuples():
            r = d.loc[r.Index]
            t, in_scope, _ = self.final_trust(r, country, client)
            rows.append((t, in_scope, r))
        rows.sort(key=lambda x: (not (x[1] or mode == "client"), -x[0]) if mode != "client" else (-x[0],))
        if mode == "client":                      # overview: best 2 per topic
            seen, keep = {}, []
            for t, s, r in rows:
                seen[r.topic_id] = seen.get(r.topic_id, 0) + 1
                if seen[r.topic_id] <= 2:
                    keep.append((t, s, r))
            rows = sorted(keep, key=lambda x: -x[0])
        rows = rows[:limit]
        results = [self.doc_json(r, country, client, detail=(i < 3)) for i, (_, _, r) in enumerate(rows)]
        for x in results:
            x["my_vote"] = self.user_votes.get((x["doc_id"], user_id))
        banner = self._conflict_banner(rows, country)
        key = f"client:{client}" if client else (f"topic:{topic}" if topic else None)
        best = max([x["trust"] for x in results if x["in_scope"]], default=0)
        experts = self.experts_for(key, country) if key else []
        shortcuts = self.shortcuts(topic, country, client)
        return {"query": text,
                "intent": {"mode": mode, "topic": topic, "topic_name": self.topics.name.get(topic) if topic else None,
                           "country": country, "country_defaulted": defaulted, "client": client,
                           "client_name": self.clients.name.get(client) if client else None,
                           "user_country": user.country},
                "did_you_mean": [{"topic_id": t, "name": self.topics.name[t]} for t in parsed["alternatives"]],
                "banner": banner, "related_notes": related_notes, "results": results, "ask_expert": bool(results == [] or best < 45),
                "experts": experts, "shortcuts": shortcuts, "graph": self._subgraph(results),
                "timings_ms": round((time.time() - t0) * 1000, 1)}

    def _conflict_banner(self, rows, country):
        by = {}
        for t, s, r in rows:
            if r.key_value and (s or not country):
                by.setdefault((r.topic_id, r.client), {}).setdefault(r.key_value, []).append((t, r.doc_id))
        for (tid, cl), vals in by.items():
            if len(vals) > 1:
                items = [{"value": v, "doc_ids": [i for _, i in sorted(l, reverse=True)],
                          "best_trust": round(max(t for t, _ in l), 1)} for v, l in vals.items()]
                items.sort(key=lambda x: -x["best_trust"])
                return {"type": "conflict", "topic_id": tid,
                        "message": "Sources disagree: " + " vs ".join(f"'{i['value']}'" for i in items[:3]) +
                                   f". The most trusted source says '{items[0]['value']}'.",
                        "values": items}
        return None

    def _subgraph(self, results):
        ids = [r["doc_id"] for r in results[:8]]
        nodes, edges, seen = [], [], set()

        def add(nid, typ, label, **kw):
            if nid not in seen:
                seen.add(nid)
                nodes.append({"id": nid, "type": typ, "label": label, **kw})

        for r in results[:8]:
            add(r["doc_id"], "document", r["title"], badge=r["badge"], trust=r["trust"])
            if r["author"]:
                add(r["author"]["person_id"], "person", r["author"]["name"], active=r["author"]["active"])
                edges.append({"source": r["author"]["person_id"], "target": r["doc_id"], "type": "AUTHORED"})
            if r["approved_by"]:
                add(r["approved_by"]["person_id"], "person", r["approved_by"]["name"], active=True)
                edges.append({"source": r["approved_by"]["person_id"], "target": r["doc_id"], "type": "APPROVED"})
        for s in ids:
            for t in self.doc_graph.successors(s):
                if t in seen:
                    edges.append({"source": s, "target": t, "type": "LINKS_TO"})
            for o in self.superseded_by.get(s, []):
                if o in seen:
                    edges.append({"source": o, "target": s, "type": "SUPERSEDES"})
        return {"nodes": nodes, "edges": edges}

    # ------------------------------------------------------------------ experts
    def experts_for(self, key, country=None, n=5):
        s = self.exp.get(key, pd.Series(dtype=float)).copy()
        for (k, pid), b in self.res_bonus.items():       # contacts that colleagues confirmed
            if k == key:
                s[pid] = s.get(pid, 0.0) + b
        if s.empty:
            return []
        out = []
        if country:                                       # same country first, other countries still visible
            bonus = pd.Series({p: 1.0 for p in s.index if self.persons.country[p] == country})
            order = (s + bonus.reindex(s.index).fillna(0)).sort_values(ascending=False).index
            s = s.reindex(order)
        else:
            s = s.sort_values(ascending=False)
        for pid, sc in s.items():
            if not self.persons.active[pid] or self.persons.level[pid] in ("Lead", "Head") and sc < 0.9:
                continue
            ev = []
            for typ, label in [("AUTHORED", "wrote {n} document(s) on this"), ("APPROVED", "approved {n} on this"), ("REVIEWS", "reviewed {n} on this"),
                               ("ATTENDED", "joined {n} meeting(s) about this"), ("COMMITTED", "worked on {n} document(s) in GitHub")]:
                c = self.evidence.get((key, pid, typ))
                if c:
                    ev.append(label.format(n=c))
            ic = self.interactions.get((key, pid))
            if ic:
                ev.append(f"{int(ic)} contacts with this customer")
            if (key, pid) in self.res_bonus:
                ev.append("colleagues said they were the right contact")
            if (key, pid) in self.trainings:
                ev.append("followed a training on this")
            card = self.person_card(pid)
            card.update({"score": round(float(sc), 2), "evidence": ev, "same_country": bool(country and card["country"] == country)})
            out.append(card)
            if len(out) == n:
                break
        # people who changed department stay visible, with their current department
        return out

    # ------------------------------------------------------- org roll-ups / risk
    def _health(self, g):
        t = self.trust[g.index]
        return {"docs": int(len(g)), "health": round(float(t.mean()), 1) if len(g) else None,
                "red_share": round(float((t < 45).mean()), 3) if len(g) else None,
                "badge": badge(float(t.mean())) if len(g) else None}

    def org_overview(self):
        out = []
        people = self.persons.groupby("country").size()
        D = self._live()
        for cc, g in D.groupby(D.team_id.map(self.teams.country)):
            out.append({"country": cc, "name": self.countries.name[cc], "people": int(people.get(cc, 0)),
                        "teams": int((self.teams.country == cc).sum()), **self._health(g)})
        return sorted(out, key=lambda x: x["health"] or 0)

    def org_departments(self):
        """Average trust per department across all countries."""
        D = self._live()
        dep = D.team_id.map(self.teams.department)
        out = []
        for dept, g in D.groupby(dep):
            out.append({"department": dept, "people": int((self.persons.department == dept).sum()),
                        "teams": int((self.teams.department == dept).sum()), **self._health(g)})
        return sorted(out, key=lambda x: x["health"] or 0)

    def validation(self):
        """Why the 0-100 score deserves trust, measured against the hidden truth (does a document state the current value?).
        Uses out-of-fold model predictions, so no document is scored by a model that trained on it."""
        key = (len(self.docs), len(self.retired), str(self.model_trained_at))            # new, removed documents or a retrain
        if getattr(self, "_validation_cache", None) and self._validation_cache[0] == key:
            return self._validation_cache[1]
        from sklearn.metrics import roc_auc_score
        d = self._live()
        lab = d.index.intersection(self.oof.index).intersection(self.truth.index)
        trust = 0.85 * 100 * (1 - self.oof.reindex(lab)) + 0.15 * 100 * self.author_exp.reindex(lab)
        truth = self.truth.reindex(lab)
        keyed = d.loc[lab][d.loc[lab].key_value != ""]
        rows = []
        for _, g in keyed.groupby(["topic_id", "country", "client"]):
            ok = truth[g.index]
            if ok.sum() in (0, len(g)):
                continue
            rows.append({"ranking": bool(ok[trust[g.index].idxmax()]), "newest": bool(ok[g.last_modified.idxmax()]),
                         "linked": bool(ok[pd.Series(self.pagerank)[g.index].idxmax()]), "random": float(ok.mean())})
        r = pd.DataFrame(rows)
        bands = []
        kt = trust[keyed.index]
        for name, lo, hi in (("green", 70, 101), ("yellow", 45, 70), ("red", 0, 45)):
            m = (kt >= lo) & (kt < hi)
            bands.append({"band": name, "range": f"{lo}-{min(hi - 1, 100)}", "documents": int(m.sum()),
                          "state_the_current_value": round(float(truth[kt[m].index].mean()), 3) if m.sum() else None})
        out = {"groups": int(len(r)), "top_answer_correct": {"graphlas": round(float(r.ranking.mean()), 3),
                                                             "newest_document": round(float(r.newest.mean()), 3),
                                                             "most_linked_document": round(float(r.linked.mean()), 3),
                                                             "random_pick": round(float(r.random.mean()), 3)},
               "auc_vs_truth": round(float(roc_auc_score(truth, trust)), 3), "bands": bands,
               "note": "Simulated data with a hidden ground truth. It shows the method works, not accuracy in a real company."}
        self._validation_cache = (key, out)
        return out

    def org_country(self, cc):
        D = self._live()
        tc = D.team_id.map(self.teams.country)
        dd = D[tc == cc]
        out = []
        for dept, g in dd.groupby(dd.team_id.map(self.teams.department)):
            out.append({"department": dept, "teams": int(((self.teams.country == cc) & (self.teams.department == dept)).sum()),
                        "people": int(((self.persons.country == cc) & (self.persons.department == dept)).sum()), **self._health(g)})
        return {"country": cc, "name": self.countries.name[cc], "departments": sorted(out, key=lambda x: x["health"] or 0)}

    def org_department(self, cc, dept):
        t = self.teams[(self.teams.country == cc) & (self.teams.department == dept)]
        out = []
        for tid in t.team_id:
            D = self._live()
            g = D[D.team_id == tid]
            out.append({"team_id": tid, "name": t.name[tid], "lead": self.person_card(t.lead_id[tid]) if t.lead_id[tid] else None,
                        "people": len(self.team_people.get(tid, [])), **self._health(g)})
        return {"country": cc, "department": dept, "teams": sorted(out, key=lambda x: x["health"] or 0)}

    def org_team(self, tid):
        D = self._live()
        g = D[D.team_id == tid]
        worst = g.assign(t=self.trust[g.index]).sort_values("t").head(8)
        return {"team_id": tid, "name": self.teams.name[tid],
                "lead": self.person_card(self.teams.lead_id[tid]) if self.teams.lead_id[tid] else None,
                "has_lead": bool(self.teams.lead_id[tid]), **self._health(g),
                "tools": sorted(self.team_tools.get(tid, [])), "warnings": self.tool_warnings(tid),
                "sources": g.source.value_counts().to_dict(),
                "worst_documents": [{"doc_id": r.doc_id, "title": r.title, "source": r.source, "trust": round(float(r.t), 1)}
                                    for r in worst.itertuples()],
                "members": [self.person_card(p) for p in self.team_people.get(tid, [])[:12]]}

    def risks(self, country=None, n=12):
        """Topics where knowledge sits with <=1 active expert (bus factor)."""
        rows = []
        for key, s in self.exp.items():
            if not key.startswith("topic:") or key.startswith("topic:client_"):
                continue
            strong = s[s >= 0.35]
            if country:
                strong = strong[[self.persons.country[p] == country for p in strong.index]]
            act = [p for p in strong.index if self.persons.active[p]]
            left = [p for p in strong.index if not self.persons.active[p]]
            if len(act) <= 1:
                rows.append({"topic_id": key[6:], "topic_name": self.topics.name[key[6:]], "active_experts": len(act),
                             "experts_left": len(left),
                             "only_expert": self.person_card(act[0]) if act else None,
                             "severity": "high" if not act else "medium"})
        return sorted(rows, key=lambda r: (r["active_experts"], -r["experts_left"]))[:n]

    # --------------------------------------------------------------- demo users
    def demo_users(self):
        p = self.persons
        out = []

        def pick(label, mask, client=None):
            c = p[mask & p.active]
            if client:
                c = c[[client in self.user_clients.get(i, set()) for i in c.index]]
            if len(c):
                card = self.person_card(c.index[0])
                card["label"] = label
                out.append(card)

        pick("Sales, Spain (works with Nike)", (p.country == "ES") & (p.department.isin(["Sales", "Customer Success", "Internationals"])) & p.level.isin(["Medior", "Senior"]), "C01")
        pick("HR Advisor, Belgium", (p.country == "BE") & (p.department == "HR Advisory") & (p.level == "Senior"))
        pick("Back-end developer, Poland", (p.country == "PL") & (p.department == "Engineering") & (p.level == "Medior"))
        pick("Payroll specialist, Netherlands", (p.country == "NL") & (p.department == "Payroll Operations") & (p.level == "Junior"))
        pick("System admin", (p.role == "System Admin"))
        pick("CEO", (p.role == "Chief Executive Officer"))
        pick("Country Lead, Belgium", (p.country == "BE") & (p.role == "Country Lead"))
        return out
