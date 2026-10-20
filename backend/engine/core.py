"""Core of the trust layer: one property graph + XGBoost trust model + expertise.

Intrinsic trust (per document, stored)  = 85% model reliability + 15% author expertise.
Context fit (country, customer, edits, colleague votes) is applied at query time, see queries.py.
"""
import threading
import time

import networkx as nx
import numpy as np
import pandas as pd
import xgboost as xgb
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from .seed_org import DATA_DIR, REFERENCE_DATE

SRC_KEY = {"SharePoint": "sharepoint", "OneDrive": "onedrive", "Teams": "teams", "Notion": "notion",
           "GitHub": "github", "Legacy drive": "legacy"}
FEATURES = (["age_days", "no_owner", "no_dept", "owner_inactive", "n_reviewers", "version", "in_degree",
             "pagerank", "trustrank", "clustering", "ext_link_ratio", "conflict_share", "superseded", "sim_max"]
            + [f"src_{k}" for k in SRC_KEY.values()])
MONOTONE = {"age_days": 1, "no_owner": 1, "owner_inactive": 1, "n_reviewers": -1, "trustrank": -1, "superseded": 1}
NICE = {"age_days": "age", "no_owner": "no owner", "no_dept": "no department", "owner_inactive": "owner left",
        "n_reviewers": "number of reviewers", "version": "version number", "in_degree": "incoming links",
        "pagerank": "popularity (PageRank)", "trustrank": "trust via links (TrustRank)",
        "clustering": "clustering", "ext_link_ratio": "links outside own cluster",
        "conflict_share": "conflicts with other documents", "superseded": "replaced by newer version",
        "sim_max": "overlap with another document", **{f"src_{k}": f"stored in {s}" for s, k in SRC_KEY.items()}}
EXPERT_WEIGHT = 0.15
GREEN, YELLOW = 70, 45
SCOPE_PENALTY, GENERIC_PENALTY, EDIT_PENALTY = 0.6, 0.85, 0.8
# weight of each signal type in the expertise score
EXPERT_W = {"AUTHORED": 1.0, "APPROVED": 0.7, "REVIEWS": 0.5, "ATTENDED": 0.25, "COMPLETED": 0.6}
CSV_BOOL = ["active", "team_lead", "opt_in_signals", "verified"]


def badge(score):
    return "green" if score >= GREEN else "yellow" if score >= YELLOW else "red"


def _read(name):
    df = pd.read_csv(DATA_DIR / f"{name}.csv", keep_default_na=False)
    for c in CSV_BOOL:
        if c in df.columns:
            df[c] = df[c].astype(str) == "True"
    return df


class CoreEngine:
    def __init__(self, tables=None):
        self.lock = threading.RLock()
        self.stats = {}
        self.votes = {}                                  # doc_id -> {"confirm": n, "flag": n}
        self.extra_labels = {}                           # doc_id -> 0/1 from approvals, rejections, confirmations
        self.res_bonus = {}                              # (expertise key, person) -> bonus from confirmed contacts
        self.t = tables or {n: _read(n) for n in ["persons", "teams", "documents", "edges", "feedback",
                                                  "ground_truth", "topics", "clients", "countries"]}
        self.rebuild()

    # ------------------------------------------------------------------ build
    def sync_tables(self):
        """Write the live state (ingested/edited documents, new edges) back so a rebuild keeps it."""
        cols = list(self.t["documents"].columns)
        d = self.docs.copy()
        d["last_modified"] = d.last_modified.dt.date.astype(str)
        d["created"] = d.created.dt.date.astype(str)
        self.t["documents"] = d[cols].reset_index(drop=True)
        self.t["edges"] = self.edges

    def rebuild(self):
        """Full rebuild: graph metrics, expertise, features, model, scores. Timed for the scale demo."""
        t0 = time.time()
        with self.lock:
            self.persons = self.t["persons"].set_index("person_id", drop=False)
            self.teams = self.t["teams"].set_index("team_id", drop=False)
            self.topics = self.t["topics"].set_index("topic_id")
            self.clients = self.t["clients"].set_index("client_id")
            self.countries = self.t["countries"].set_index("country")
            self.edges = self.t["edges"]
            self.docs = self.t["documents"].copy()
            self.docs["last_modified"] = pd.to_datetime(self.docs["last_modified"])
            self.docs["created"] = pd.to_datetime(self.docs["created"])
            self.docs = self.docs.set_index("doc_id", drop=False)
            self.docs["edited"] = False
            self.docs["pending"] = False
            self.docs["pending"] = self.docs.index.isin(getattr(self, "pending_ids", set()))
            self.feedback = self.t["feedback"].set_index("doc_id")
            self.truth = self.t["ground_truth"].set_index("doc_id").states_current_value.astype(str).eq("True")
            self._index_edges()
            self._graph_metrics()
            self._expertise()
            self._tfidf()
            self._features()
            self._fit()
            self._score()
        self.stats["full_rebuild_s"] = round(time.time() - t0, 2)

    def _index_edges(self):
        e = self.edges
        self.reviewers = e[e.type == "REVIEWS"].groupby("target").source.apply(list).to_dict()
        self.approver = e[e.type == "APPROVED"].set_index("target").source.to_dict()
        self.superseded_by = e[e.type == "SUPERSEDES"].groupby("target").source.apply(list).to_dict()
        self.listed = e[e.type == "LISTED_AS"].groupby("target").source.apply(list).to_dict()
        self.reports_to = self.persons.reports_to.to_dict()
        ic = e[e.type == "INTERACTED_WITH"]
        self.user_clients = ic.groupby("source").target.apply(set).to_dict()
        self.team_people = self.persons.groupby("team_id").person_id.apply(list).to_dict()

    def _graph_metrics(self):
        e = self.edges
        dg = nx.DiGraph()
        dg.add_nodes_from(self.docs.index)
        dg.add_edges_from(e[e.type == "LINKS_TO"][["source", "target"]].itertuples(index=False, name=None))
        self.doc_graph = dg
        seeds = {d: float(v) for d, v in self.docs.verified.items()}
        self.pagerank = nx.pagerank(dg)
        self.trustrank = nx.pagerank(dg, personalization=seeds) if any(seeds.values()) else dict(self.pagerank)
        und = dg.to_undirected()
        self.clustering = nx.clustering(und)
        comms = nx.community.louvain_communities(und, seed=42)
        self.community = {d: i for i, c in enumerate(comms) for d in c}
        self.ext_ratio = {}
        for d in und:
            nb = list(und[d])
            self.ext_ratio[d] = (sum(self.community[n] != self.community[d] for n in nb) / len(nb)) if nb else 0.0
        tr = pd.Series(self.trustrank)
        self.tr_pct = tr.rank(pct=True).to_dict()

    def doc_key(self, d):
        """Expertise key a document belongs to: customer if customer-specific, else topic."""
        return f"client:{d.client}" if d.client else f"topic:{d.topic_id}"

    def _expertise(self):
        """Expertise per (key = topic or customer) from daily signals; PageRank-style credit via TrustRank."""
        e = self.edges
        d = self.docs
        key_of = ("topic:" + d.topic_id).to_dict()
        ckey_of = d.client.map(lambda c: f"client:{c}" if c else "").to_dict()
        rows = []
        sig = e[e.type.isin(["AUTHORED", "APPROVED", "REVIEWS", "ATTENDED", "COMMITTED"])]
        for typ, src, tgt, w in zip(sig.type, sig.source, sig.target, sig.weight):
            if tgt not in key_of:
                continue
            if typ == "AUTHORED":
                wt = EXPERT_W["AUTHORED"] * (1 + 2 * self.tr_pct.get(tgt, 0))
            elif typ == "COMMITTED":
                wt = 0.3 * np.log1p(w)
            else:
                wt = EXPERT_W[typ]
            rows.append((src, key_of[tgt], wt))
            if ckey_of[tgt]:
                rows.append((src, ckey_of[tgt], wt))
        comp = e[e.type == "COMPLETED"]
        rows += [(s, "topic:" + t, EXPERT_W["COMPLETED"]) for s, t in zip(comp.source, comp.target)]
        ic = e[e.type == "INTERACTED_WITH"]
        rows += [(s, "client:" + c, min(4.0, 0.06 * w)) for s, c, w in zip(ic.source, ic.target, ic.weight)]
        self.interactions = {(f"client:{c}", s): w for s, c, w in zip(ic.source, ic.target, ic.weight)}
        self.trainings = {("topic:" + t, s) for s, t in zip(comp.source, comp.target)}
        df = pd.DataFrame(rows, columns=["person", "key", "w"])
        raw = df.groupby(["key", "person"]).w.sum()
        self.expert_raw = raw
        self.exp = {k: (g.droplevel(0) / g.max()) for k, g in raw.groupby(level=0)}
        ev = pd.concat([sig.assign(k=sig.target.map(key_of)), sig.assign(k=sig.target.map(ckey_of))])
        ev = ev[ev.k.notna() & (ev.k != "")]
        self.evidence = ev.groupby(["k", "source", "type"]).size().to_dict()

    def _tfidf(self):
        self.vec = TfidfVectorizer(min_df=1)
        self.X = self.vec.fit_transform(self.docs.text)
        self.row_of = {d: i for i, d in enumerate(self.docs.index)}
        topics = self.docs.topic_id.to_numpy()
        self.clf = LogisticRegression(max_iter=300, C=5).fit(self.X, topics)

    # --------------------------------------------------------------- features
    def _features(self):
        d = self.docs
        f = pd.DataFrame(index=d.index)
        f["age_days"] = (REFERENCE_DATE - d.last_modified).dt.days
        f["no_owner"] = (d.owner_id == "").astype(int)
        f["no_dept"] = (d.department == "").astype(int)
        who = d.owner_id.where(d.owner_id != "", d.author_id)
        f["owner_inactive"] = (~who.map(self.persons.active)).astype(int)
        f["n_reviewers"] = [len(self.reviewers.get(x, [])) for x in d.index]
        f["version"] = d.version
        f["in_degree"] = [self.doc_graph.in_degree(x) for x in d.index]
        f["pagerank"] = d.index.map(self.pagerank)
        f["trustrank"] = d.index.map(self.trustrank)
        f["clustering"] = d.index.map(self.clustering)
        f["ext_link_ratio"] = d.index.map(self.ext_ratio)
        f["superseded"] = [int(x in self.superseded_by) for x in d.index]
        kv = d.key_value
        has = kv != ""
        sup = f["superseded"] == 1
        dd = d[has].assign(sup=sup[has].values)
        keyc = ["topic_id", "country", "client"]
        live = dd[~dd.sup]                       # documents that were already replaced are not opponents
        n_live = live.groupby(keyc).doc_id.transform("size").reindex(dd.index).fillna(0)
        n_live = dd[keyc].merge(live.groupby(keyc).size().rename("n"), on=keyc, how="left").n.fillna(0).values
        same_live = dd[keyc + ["key_value"]].merge(live.groupby(keyc + ["key_value"]).size().rename("n"),
                                                   on=keyc + ["key_value"], how="left").n.fillna(0).values
        own = (~dd.sup).astype(int).values
        f["conflict_share"] = 0.0
        f.loc[has, "conflict_share"] = (n_live - same_live) / np.maximum(n_live - own, 1)
        self.groups = d[has].groupby(["topic_id", "country", "client"]).doc_id.apply(list).to_dict()
        # text overlap with other documents on the same topic (+ customer)
        f["sim_max"] = 0.0
        tv = (d.topic_id + "|" + d.client).to_numpy()
        self.topic_rows = {}
        for k in np.unique(tv):
            idx = np.where(tv == k)[0]
            self.topic_rows[k] = idx
            if len(idx) > 1:
                s = (self.X[idx] @ self.X[idx].T).toarray()
                np.fill_diagonal(s, 0)
                f.iloc[idx, f.columns.get_loc("sim_max")] = s.max(axis=1)
        for s, k in SRC_KEY.items():
            f[f"src_{k}"] = (d.source == s).astype(int)
        self.F = f[FEATURES]

    def _fit(self):
        y = self.feedback.unreliable.astype(float).reindex(self.F.index)
        for did, lab in self.extra_labels.items():       # implicit labels: approvals, rejections, confirmed answers
            if did in y.index:
                y[did] = float(lab)
        lab = y.notna()
        self.n_labels = int(lab.sum())
        params = dict(n_estimators=150, max_depth=4, learning_rate=0.1, subsample=0.9, eval_metric="logloss",
                      monotone_constraints=tuple(MONOTONE.get(c, 0) for c in FEATURES), random_state=42, n_jobs=4)
        Xl, yl = self.F[lab], y[lab].astype(int)
        oof = cross_val_predict(xgb.XGBClassifier(**params), Xl, yl, cv=StratifiedKFold(5, shuffle=True, random_state=42),
                                method="predict_proba")[:, 1]
        self.cv_auc = float(roc_auc_score(yl, oof))
        self.oof = pd.Series(oof, index=Xl.index)
        self.model = xgb.XGBClassifier(**params).fit(Xl, yl)
        self.p_unreliable = pd.Series(self.model.predict_proba(self.F)[:, 1], index=self.F.index)
        self.model_trained_at = pd.Timestamp.now()

    def author_expert(self, d):
        a = d.author_id
        if not self.persons.active[a]:
            return 0.0
        return float(self.exp.get(self.doc_key(d), pd.Series(dtype=float)).get(a, 0.0))

    def _score(self):
        d = self.docs
        ml = 100 * (1 - self.p_unreliable)
        ae = pd.Series([self.author_expert(r) for r in d.itertuples()], index=d.index)
        self.ml_score, self.author_exp = ml, ae
        self.trust = (1 - EXPERT_WEIGHT) * ml + EXPERT_WEIGHT * 100 * ae

    # ----------------------------------------------------------------- helpers
    def person_card(self, pid):
        if not pid or pid not in self.persons.index:
            return None
        p = self.persons.loc[pid]
        return {"person_id": pid, "name": p["name"], "role": p.role, "department": p.department,
                "country": p.country, "team": self.teams.name.get(p.team_id, ""), "active": bool(p.active),
                "moved_from": p.previous_department or None}

    def above(self, pid):
        """Approver: first ACTIVE person above `pid` in the REPORTS_TO chain (nobody approves their own work)."""
        cur = self.reports_to.get(pid, "")
        while cur and not self.persons.active[cur]:
            cur = self.reports_to.get(cur, "")
        return cur

    def can_see(self, user_id, d):
        acl = d.acl
        if acl == "all":
            return True
        u = self.persons.loc[user_id]
        if acl.startswith("dept:"):
            return u.department == acl[5:]
        if acl.startswith("client:"):
            return (acl[7:] in self.user_clients.get(user_id, set()) or u.team_id == d.team_id
                    or u.level in ("Country Lead", "Head"))
        return False
