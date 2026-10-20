"""Invariants of the simulated organisation, documents and graph."""
import numpy as np
import pandas as pd

from engine.tools import SOURCES


def chain(e, pid):
    out, cur = [], e.reports_to.get(pid, "")
    while cur and len(out) < 10:
        out.append(cur)
        cur = e.reports_to.get(cur, "")
    return out


def test_sizes(eng):
    assert len(eng.persons) >= 10000
    assert len(eng.countries) == 26
    assert len(eng.teams) >= 900
    assert len(eng.docs) >= 9000


def test_ids_unique(eng):
    t = eng.t
    assert t["persons"].person_id.is_unique
    assert t["documents"].doc_id.is_unique
    assert t["teams"].team_id.is_unique


def test_hierarchy_reaches_country_lead(eng):
    leads = eng.persons[eng.persons.role == "Country Lead"]
    assert sorted(leads.country) == sorted(eng.countries.index)          # exactly one lead per country
    for pid in eng.persons.sample(600, random_state=1).person_id:
        c = chain(eng, pid)
        if eng.persons.role[pid] == "Country Lead":
            assert c == []
        else:
            assert c and eng.persons.role[c[-1]] == "Country Lead", pid
            assert len(c) <= 4
            assert eng.persons.country[c[-1]] == eng.persons.country[pid]


def test_document_references(eng):
    d = eng.docs
    assert d.author_id.isin(eng.persons.index).all()
    assert d.team_id.isin(eng.teams.index).all()
    assert d.topic_id.isin(eng.topics.index).all()
    assert d.client[d.client != ""].isin(eng.clients.index).all()
    assert d.source.isin(SOURCES).all()
    assert d.link.str.match(r"^(https?|file)://").all()
    assert (d.owner_id.isin(eng.persons.index) | (d.owner_id == "")).all()


def test_github_documents_always_have_owner(eng):
    g = eng.docs[eng.docs.source == "GitHub"]
    assert (g.owner_id != "").all()


def test_acl_format_and_customer_confidentiality(eng):
    d = eng.docs
    ok = (d.acl == "all") | d.acl.str.startswith("dept:") | d.acl.str.startswith("client:")
    assert ok.all()
    cust = d[d.client != ""]
    assert (cust.acl == "client:" + cust.client).all(), "a document about a customer must be customer-scoped"
    depts = {a[5:] for a in d.acl if a.startswith("dept:")}
    assert depts <= set(eng.persons.department)


def test_edge_endpoints(eng):
    e = eng.edges
    P, D = set(eng.persons.index), set(eng.docs.index)
    T, C, S, TM = set(eng.topics.index), set(eng.clients.index), set(SOURCES), set(eng.teams.index)
    spec = {"AUTHORED": (P, D), "APPROVED": (P, D), "REVIEWS": (P, D), "LISTED_AS": (P, D), "ATTENDED": (P, D),
            "COMMITTED": (P, D), "LINKS_TO": (D, D), "SUPERSEDES": (D, D), "ABOUT": (D, T | C), "STORED_IN": (D, S),
            "OWNED_BY": (D, TM), "COMPLETED": (P, T), "INTERACTED_WITH": (P, C)}
    assert set(e.type) == set(spec)
    for typ, (src, tgt) in spec.items():
        g = e[e.type == typ]
        assert g.source.isin(src).all(), typ
        assert g.target.isin(tgt).all(), typ


def test_every_document_has_one_author_edge_matching_its_author(eng):
    a = eng.edges[eng.edges.type == "AUTHORED"].drop_duplicates("target").set_index("target").source
    assert len(a) == len(eng.docs)
    assert (a.reindex(eng.docs.index) == eng.docs.author_id).all()


def test_nobody_approves_their_own_work_and_approver_is_above(eng):
    ap = eng.edges[eng.edges.type == "APPROVED"]
    author = eng.docs.author_id
    for p, d in zip(ap.source, ap.target):
        assert p != author[d], d
        assert p in chain(eng, author[d]), f"{p} is not above the author of {d}"


def test_verified_documents_have_an_approver(eng):
    v = eng.docs[eng.docs.verified]
    assert v.index.isin(list(eng.approver)).all()


def test_superseding_documents_are_newer(eng):
    s = eng.edges[eng.edges.type == "SUPERSEDES"]
    lm = eng.docs.last_modified
    assert (lm[s.source].values >= lm[s.target].values).all()


def test_feedback_matches_hidden_truth(eng):
    fb = eng.feedback.unreliable.astype(float)
    assert set(fb.index) == set(eng.docs.index)
    assert fb[~eng.truth.reindex(fb.index)].mean() > fb[eng.truth.reindex(fb.index)].mean() + 0.3


def test_signals_only_for_people_who_opted_in_by_default(eng):
    sig = eng.edges[eng.edges.type.isin(["COMPLETED", "INTERACTED_WITH"])]
    optin = eng.persons.opt_in_signals
    hero = set(eng.heroes.values())
    bad = sig[~optin[sig.source].values & ~sig.source.isin(hero).values]
    assert bad.empty
