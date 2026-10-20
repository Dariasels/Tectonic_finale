"""Automatic clean-up: replaced and orphaned documents leave Graphlas, very low scores go to the team lead."""
import pytest
from fastapi.testclient import TestClient

import main
from engine.cleanup import KEEP_QUIET_DAYS, REVIEW_CAP, VERY_LOW
from engine.questions import persona_ids
from engine.seed_org import REFERENCE_DATE


@pytest.fixture(scope="module")
def ids(clean):
    return persona_ids(clean)


@pytest.fixture(scope="module")
def before(clean):
    """What the data looked like before the sweep, so the rules can be checked independently."""
    e = clean.edges
    links = e[e.type == "LINKS_TO"]
    return {"indeg": links.target.value_counts().to_dict(), "sources": links.groupby("target").source.apply(set).to_dict(), "superseded_by": {k: list(v) for k, v in clean.superseded_by.items()},
            "verified": set(clean.docs.index[clean.docs.verified]), "docs": clean.docs.copy(), "n_live": len(clean._live()),
            "links_to_h002": sorted(set(links[links.target == "H002"].source))}


@pytest.fixture(scope="module")
def sweep(clean, before):
    return clean.cleanup()


def test_dry_run_changes_nothing(clean):
    n = len(clean._live())
    r = clean.cleanup(dry_run=True)
    assert r["dry_run"] and len(clean._live()) == n and not clean.retired
    assert not any(a.get("kind") == "review" for a in clean.approvals.values())


def test_a_verified_successor_retires_the_old_document(clean, before, sweep):
    assert "H002" in sweep["superseded"] and clean.docs.retired["H002"]
    assert clean.retired["H002"]["rule"] == "superseded" and clean.retired["H002"]["successor"] == "H001"
    for old in sweep["superseded"]:
        succ = [n for n in before["superseded_by"][old] if n in before["verified"]]
        assert succ, f"{old} was removed without a verified successor"


def test_an_unverified_successor_does_not_retire_anything(clean, before, sweep):
    kept = [o for o, news in before["superseded_by"].items() if not any(n in before["verified"] for n in news)]
    assert kept, "the data should contain replaced documents whose successor is not verified"
    assert not any(clean.docs.retired[o] for o in kept if o not in sweep["orphans"])


def test_links_to_the_old_document_now_point_to_the_new_one(clean, before, sweep):
    e = clean.edges
    new_links = set(e[(e.type == "LINKS_TO") & (e.target == "H001")].source)
    assert len(before["links_to_h002"]) >= 10
    moved = [s for s in before["links_to_h002"] if not clean.docs.retired[s]]
    assert moved and all(s in new_links for s in moved)
    assert clean.retired["H002"]["links_redirected"] >= len(moved) - 1


def test_orphans_follow_the_rules(clean, before, sweep):
    d = before["docs"]
    assert sweep["orphans"]
    for did in sweep["orphans"]:
        r = d.loc[did]
        # nobody links to it any more; links from documents that left in the same sweep (replaced ones) do not count
        assert not (before["sources"].get(did, set()) - set(sweep["superseded"])), did
        assert not r.verified
        assert (REFERENCE_DATE - r.last_modified).days >= 365
        people = [r.owner_id, r.author_id, clean.approver.get(did, "")] + clean.reviewers.get(did, [])
        assert not any(p and clean.persons.active[p] for p in people), did                 # nobody who contributed is still here
        assert clean.docs.retired[did] and clean.retired[did]["rule"] == "orphan"


def test_documents_that_are_not_orphans_stay(clean, before, sweep):
    d = before["docs"]
    gone = set(sweep["orphans"]) | set(sweep["superseded"])
    young = d[(REFERENCE_DATE - d.last_modified).dt.days < 365].index
    linked = [i for i in d.index if before["sources"].get(i, set()) - set(sweep["superseded"])]
    active_owner = d.index[d.owner_id.map(lambda p: bool(p) and clean.persons.active[p])]
    for group in (young, linked, active_owner):
        assert not (set(group) & set(sweep["orphans"]))
    assert not (before["verified"] & set(sweep["orphans"]))
    assert len(gone) < before["n_live"] * 0.05                                              # a sweep removes a small part, never a mass


def test_the_only_document_on_a_subject_goes_to_a_person_not_the_bin(clean, sweep):
    assert sweep["protected"]
    for did in sweep["protected"]:
        assert not clean.docs.retired[did]
        reviews = [a for a in clean.approvals.values() if a.get("kind") == "review" and a["doc_id"] == did]
        assert reviews and reviews[0]["status"] == "pending"


def test_very_low_scores_go_to_the_team_lead_with_a_cap(clean, sweep):
    reviews = [a for a in clean.approvals.values() if a.get("kind") == "review"]
    assert reviews and sweep["reviews_opened"] == len(reviews)
    per = {}
    for a in reviews:
        d = clean.docs.loc[a["doc_id"]]
        who = a["requested_from"]
        per[who] = per.get(who, 0) + 1
        assert isinstance(who, str) and clean.persons.active[who]                           # one named person, never "the team"
        assert who not in (d.author_id, d.owner_id)                                         # nobody reviews their own work
        lead = clean.teams.lead_id[d.team_id]
        if lead and clean.persons.active[lead] and lead not in (d.author_id, d.owner_id):
            assert who == lead                                                              # the team lead of the owning team
        assert not d.retired and d.doc_id not in clean.superseded_by
        assert clean.trust[d.doc_id] < VERY_LOW or d.doc_id in sweep["protected"]
        assert not d.pending                                                                # reviews are not shown as awaiting approval
    assert max(per.values()) <= REVIEW_CAP
    assert not clean.docs.retired[[a["doc_id"] for a in reviews if a["doc_id"] not in sweep["protected"]]].any()   # never removed automatically


def test_repeated_sweeps_settle_and_never_duplicate_reviews(clean, sweep):
    for _ in range(6):                                        # removing documents can leave new orphans behind; that dies out quickly
        r = clean.cleanup()
        if not r["superseded"] and not r["orphans"]:
            break
    else:
        pytest.fail("the clean-up keeps removing documents")
    pending = [a["doc_id"] for a in clean.approvals.values() if a.get("kind") == "review" and a["status"] == "pending"]
    assert len(pending) == len(set(pending))                  # a document is never reviewed twice at the same time


def test_keeping_a_document_makes_it_verified_and_it_is_not_offered_again(clean, ids, sweep):
    a = next(x for x in clean.approvals.values() if x.get("kind") == "review" and x["status"] == "pending" and x["doc_id"] not in sweep["protected"])
    other = next(p for p in (ids["dev"], ids["pay"], ids["es"]) if p != a["requested_from"])
    with pytest.raises(PermissionError):
        clean.decide(a["approval_id"], other, "keep")                                       # only the assigned team lead
    with pytest.raises(ValueError):
        clean.decide(a["approval_id"], a["requested_from"], "approve")                      # a review is answered with keep or remove
    out = clean.decide(a["approval_id"], a["requested_from"], "keep")
    assert a["status"] == "kept" and clean.docs.verified[a["doc_id"]] and not out["removed"]
    assert clean.approver[a["doc_id"]] == a["requested_from"]
    assert (REFERENCE_DATE - clean.review_kept[a["doc_id"]]).days < KEEP_QUIET_DAYS
    clean.cleanup()
    assert not any(x["doc_id"] == a["doc_id"] and x["status"] == "pending" for x in clean.approvals.values())
    with pytest.raises(ValueError):
        clean.decide(a["approval_id"], a["requested_from"], "keep")                         # already decided


def test_removing_a_document_after_review_is_logged(clean, sweep):
    a = next(x for x in clean.approvals.values() if x.get("kind") == "review" and x["status"] == "pending" and x["doc_id"] not in sweep["protected"])
    out = clean.decide(a["approval_id"], a["requested_from"], "remove")
    assert out["removed"] and clean.docs.retired[a["doc_id"]] and a["status"] == "removed"
    entry = clean.retired[a["doc_id"]]
    assert entry["rule"] == "review" and entry["by"] == a["requested_from"]


def test_removed_documents_disappear_from_search_and_health(clean, ids, before):
    h = ids["hr"]
    r = clean.search("parental leave Belgium", h)
    assert "H002" not in [x["doc_id"] for x in r["results"]]
    assert "H001" in [x["doc_id"] for x in r["results"]]                                      # the current policy is still there
    assert sum(x["docs"] for x in clean.org_overview()) == len(clean._live()) < before["n_live"]
    assert clean.validation()["groups"] > 300                                               # the score check only looks at live documents
    assert "H002" not in sum(clean.groups.values(), [])                                     # and not in conflict checks


def test_a_removed_document_can_be_restored_by_the_right_people(clean, ids):
    team = clean.docs.team_id["H002"]
    with pytest.raises(PermissionError):
        clean.restore("H002", ids["dev"])
    lead = clean.teams.lead_id[team]
    who = lead if lead and clean.can_manage(lead, team) else clean.heroes["admin"]
    clean.restore("H002", who)
    assert not clean.docs.retired["H002"] and "H002" in sum(clean.groups.values(), [])
    assert clean.retire_log[[e["doc_id"] for e in clean.retire_log].index("H002")]["restored"]
    assert clean.search("parental leave Belgium", ids["hr"])["results"]
    with pytest.raises(KeyError):
        clean.restore("H002", who)                                                          # it was not removed any more


def test_the_log_is_visible_to_team_leads_and_technical_people_only(clean, ids):
    with pytest.raises(PermissionError):
        clean.cleanup_log(ids["hr"])
    assert len(clean.cleanup_log(clean.heroes["admin"])) == min(200, len(clean.retire_log))
    team_lead = next(p for p in clean.persons.index if clean.persons.level[p] == "Team Lead" and clean.persons.active[p]
                     and any(e["team_id"] == clean.persons.team_id[p] for e in clean.retire_log))
    own = clean.cleanup_log(team_lead)
    assert own and all(e["team_id"] == clean.persons.team_id[team_lead] for e in own)
    assert all(e["by_name"] for e in own)


def test_verifying_a_new_version_removes_the_old_one_at_once(clean):
    clean.policy["auto_cleanup"] = True
    h = clean.heroes
    res = clean.ingest_event(h["be_cs"], {"source": "SharePoint", "title": "Nike payroll cut-off agreement 2027", "topic_id": "client_cutoff",
                                          "country": "BE", "client": "C01", "key_value": "cut-off on day 16",
                                          "extract": "Payroll cut-off agreement. Rule: cut-off on day 16."})
    assert res["status"] == "pending_approval"
    ap = res["approval"]
    old = [x for x in clean.groups[("client_cutoff", "BE", "C01")] if clean.docs.verified[x] and x != ap["doc_id"]]
    assert old
    out = clean.decide(ap["approval_id"], ap["requested_from"], "approve")
    assert all(clean.docs.retired[x] and clean.retired[x]["successor"] == ap["doc_id"] for x in old)
    assert clean.search("payroll cut-off for Nike in Belgium", h["es_sales"])["results"][0]["doc_id"] == ap["doc_id"]
    clean.policy["auto_cleanup"] = False


def test_retraining_runs_the_clean_up_when_it_is_switched_on(clean):
    clean.policy["auto_cleanup"] = True
    log = clean.retrain("test")
    assert log["cleanup"] is not None and set(log["cleanup"]) == {"superseded", "orphans", "reviews_opened"}
    assert all(clean.docs.retired[k] for k in clean.retired)                               # removals survive the rebuild
    clean.policy["auto_cleanup"] = False
    assert clean.retrain("test")["cleanup"] is None


@pytest.fixture(scope="module")
def client(clean):
    main.state["engine"] = clean
    return TestClient(main.app)


def test_cleanup_endpoints_are_closed_to_normal_users(client, clean, ids):
    for who in ("hr", "dev", "es"):
        assert client.post("/api/cleanup/run", json={"user_id": ids[who]}).status_code == 403
        assert client.get("/api/cleanup/log", params={"user_id": ids[who]}).status_code == 403
        assert client.post("/api/cleanup/H002/restore", json={"user_id": ids[who]}).status_code == 403
    r = client.post("/api/cleanup/run", json={"user_id": clean.heroes["admin"], "dry_run": True})
    assert r.status_code == 200 and r.json()["dry_run"] and "stays in its tool" in r.json()["note"]
    assert client.get("/api/cleanup/log", params={"user_id": clean.heroes["ceo"]}).status_code == 200
    assert client.post("/api/model/settings", json={"user_id": ids["lead"], "auto_cleanup": False}).json()["auto"] in (True, False)


def test_a_team_lead_sees_the_reviews_and_answers_over_http(client, clean):
    clean.cleanup()
    a = next(x for x in clean.approvals.values() if x.get("kind") == "review" and x["status"] == "pending")
    lead = a["requested_from"]
    mine = client.get("/api/approvals", params={"user_id": lead}).json()
    review = next(x for x in mine if x["approval_id"] == a["approval_id"])
    assert review["kind"] == "review" and review["reasons"] and review["document"]["location"] and "://" not in review["document"]["location"]
    assert client.post(f"/api/approvals/{a['approval_id']}/decision", json={"user_id": lead, "decision": "reject"}).status_code == 400
    assert client.post(f"/api/approvals/{a['approval_id']}/decision", json={"user_id": lead, "decision": "banana"}).status_code == 422
    assert client.post(f"/api/approvals/{a['approval_id']}/decision", json={"user_id": lead, "decision": "remove"}).status_code == 200
