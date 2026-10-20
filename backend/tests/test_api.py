"""HTTP layer: validation, access errors, removed endpoints."""
import pytest
from fastapi.testclient import TestClient

import main
from engine.questions import persona_ids


@pytest.fixture(scope="module")
def client(mut):
    main.state["engine"] = mut
    return TestClient(main.app)                       # no context manager: the engine above is used, no rebuild


@pytest.fixture(scope="module")
def ids(mut):
    return persona_ids(mut)


def test_health_and_root(client):
    assert client.get("/api/health").json() == {"status": "ok", "ready": True}
    assert client.get("/", follow_redirects=False).status_code in (302, 307)


def test_validation_and_unknown_users(client, ids):
    assert client.get("/api/search", params={"q": "x", "user_id": "bad"}).status_code == 422
    assert client.get("/api/search", params={"q": "x" * 301, "user_id": ids["hr"]}).status_code == 422
    assert client.get("/api/search", params={"q": "parental leave", "user_id": "P99999"}).status_code == 404
    assert client.get("/api/search", params={"q": "parental leave", "user_id": ids["hr"], "limit": 500}).status_code == 422


def test_hostile_input_is_harmless(client, ids):
    for q in ("'; DROP TABLE documents; --", "<script>alert(1)</script>", "../../etc/passwd", "%00", "{{7*7}}"):
        r = client.get("/api/search", params={"q": q, "user_id": ids["hr"]})
        assert r.status_code == 200, q


def test_uploading_documents_is_not_possible(client, ids):
    assert client.post("/api/documents", json={"user_id": ids["hr"], "title": "x", "text": "y"}).status_code in (404, 405)


def test_event_validation(client, ids):
    good = {"user_id": ids["hr"], "source": "SharePoint", "title": "t"}
    assert client.post("/api/events/document", json={**good, "link": "javascript:alert(1)"}).status_code == 422
    assert client.post("/api/events/document", json={**good, "source": "Dropbox"}).status_code == 400
    assert client.post("/api/events/document", json={**good, "title": "x" * 201}).status_code == 422
    assert client.post("/api/events/meeting", json={"user_id": ids["hr"], "title": "t", "attendees": ["P00001"] * 41}).status_code == 422


def test_hidden_document_is_forbidden(client, mut, ids):
    hidden = mut.docs[mut.docs.acl.str.startswith("dept:")].index[0]
    assert client.get(f"/api/documents/{hidden}", params={"user_id": ids["dev"]}).status_code == 403
    assert client.get(f"/api/documents/{hidden}/metadata", params={"user_id": ids["dev"]}).status_code == 403
    assert client.get(f"/api/documents/{hidden}", params={"user_id": ids["hr"]}).status_code == 200
    assert client.get("/api/documents/NOPE1", params={"user_id": ids["hr"]}).status_code == 404


def test_wrong_approver_gets_403(client, mut, ids):
    h = mut.heroes
    r = client.post("/api/events/document", json={"user_id": h["hr_senior"], "source": "SharePoint", "title": "Parental leave Belgium update",
                                                    "topic_id": "parental_leave", "country": "BE", "key_value": "19 weeks per parent",
                                                    "extract": "Parental leave. Rule: 19 weeks per parent."}).json()
    assert r["status"] == "pending_approval"                       # contradicts the verified policy
    aid = r["approval"]["approval_id"]
    assert client.post(f"/api/approvals/{aid}/decision", json={"user_id": ids["dev"], "decision": "approve"}).status_code == 403
    assert client.post(f"/api/approvals/{aid}/decision", json={"user_id": r["approval"]["requested_from"], "decision": "maybe"}).status_code == 422


def test_retraining_needs_management_or_admin(client, mut, ids):
    assert client.post("/api/model/retrain", json={"user_id": ids["hr"]}).status_code == 403
    assert client.post("/api/model/settings", json={"user_id": ids["dev"], "auto": False}).status_code == 403
    assert client.get("/api/model/status", params={"user_id": ids["hr"]}).status_code == 403
    assert client.get("/api/model/status", params={"user_id": mut.heroes["admin"]}).json()["can_retrain"] is True
    assert client.post("/api/model/settings", json={"user_id": ids["lead"], "min_new_docs": 0}).status_code == 422


def test_vote_endpoint_toggles(client, ids):
    p = {"user_id": ids["pay"], "kind": "flag"}
    assert client.post("/api/documents/H002/vote", json=p).json()["my_vote"] == "flag"
    assert client.post("/api/documents/H002/vote", json=p).json()["my_vote"] is None
    assert client.post("/api/documents/H002/vote", json={**p, "kind": "love"}).status_code == 422


def test_signup_and_people_endpoints(client):
    opt = client.get("/api/signup/options", params={"country": "BE", "department": "HR Advisory"}).json()
    team = opt["teams"][0]["team_id"]
    ok = client.post("/api/signup", json={"name": "Api Person", "country": "BE", "department": "HR Advisory", "level": "Medior", "team_id": team})
    assert ok.status_code == 200 and ok.json()["person"]["name"] == "Api Person"
    assert client.post("/api/signup", json={"name": "A", "country": "BE", "department": "HR Advisory", "level": "Medior", "team_id": team}).status_code == 422
    assert client.post("/api/signup", json={"name": "Api Person", "country": "BE", "department": "HR Advisory", "level": "Medior"}).status_code == 400
    assert client.get("/api/signup/options", params={"country": "ZZ", "department": "HR Advisory"}).status_code == 400
    assert any(p["name"] == "Api Person" for p in client.get("/api/people/search", params={"q": "api person"}).json())
    assert client.get("/api/people/search", params={"q": "x" * 61}).status_code == 422


def test_validation_and_department_endpoints(client):
    assert client.get("/api/validation").json()["top_answer_correct"]["graphlas"] > 0.8
    assert len(client.get("/api/org/departments").json()) == 9


def test_profile_rules_over_http(client, ids):
    assert client.post("/api/profile", json={"user_id": ids["hr"], "team_tools": ["Teams"]}).status_code == 403
    assert client.post("/api/profile", json={"user_id": ids["hr"], "connections": ["Evil"]}).status_code == 400
    assert client.post("/api/profile", json={"user_id": ids["hr"], "answers": {"find": "bogus"}}).json()["answers"].get("find") == []
    two = client.post("/api/profile", json={"user_id": ids["hr"], "answers": {"find": ["ask a colleague", "search SharePoint"]}}).json()
    assert two["answers"]["find"] == ["ask a colleague", "search SharePoint"]
    assert [p["provider"] for p in client.get("/api/auth/providers").json()] == ["GitHub", "Teams", "Notion"]


def test_questions_endpoint_has_no_hostile_samples(client):
    qs = client.get("/api/demo/questions").json()
    assert len(qs) >= 70 and all("DROP TABLE" not in q["text"] and "<script>" not in q["text"] for q in qs)


def test_technical_pages_are_closed_to_everyone_else(client, mut, ids):
    for who in ("hr", "dev", "pay", "es"):
        u = {"user_id": ids[who]}
        assert client.get("/api/scale", params=u).status_code == 403, who
        assert client.get("/api/model/status", params=u).status_code == 403, who
        assert client.get("/api/events/recent", params=u).status_code == 403, who
        assert client.get("/api/demo/presets", params=u).status_code == 403, who
        assert client.post("/api/demo/reset", json=u).status_code == 403, who
        assert client.get("/api/access", params=u).json()["can_view_technical"] is False
    for who in (mut.heroes["admin"], mut.heroes["ceo"], ids["lead"]):
        u = {"user_id": who}
        assert client.get("/api/scale", params=u).status_code == 200
        assert client.get("/api/access", params=u).json()["can_view_technical"] is True
    assert client.get("/api/validation").status_code == 200          # the explanation of the score stays public
