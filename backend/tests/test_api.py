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
    r = client.post("/api/events/document", json={"user_id": h["hr_senior"], "source": "SharePoint", "title": "Sick leave Belgium",
                                                    "topic_id": "sick_leave", "country": "BE", "key_value": "certificate after 9 days",
                                                    "extract": "Sick leave. Rule: certificate after 9 days."}).json()
    if r["status"] == "pending_approval":
        aid = r["approval"]["approval_id"]
        assert client.post(f"/api/approvals/{aid}/decision", json={"user_id": ids["dev"], "decision": "approve"}).status_code == 403
        assert client.post(f"/api/approvals/{aid}/decision", json={"user_id": r["approval"]["requested_from"], "decision": "maybe"}).status_code == 422


def test_profile_rules_over_http(client, ids):
    assert client.post("/api/profile", json={"user_id": ids["hr"], "team_tools": ["Teams"]}).status_code == 403
    assert client.post("/api/profile", json={"user_id": ids["hr"], "connections": ["Evil"]}).status_code == 400
    assert client.post("/api/profile", json={"user_id": ids["hr"], "answers": {"find": "bogus"}}).json()["answers"].get("find") != "bogus"
    assert [p["provider"] for p in client.get("/api/auth/providers").json()] == ["GitHub", "Teams", "Notion"]


def test_questions_endpoint_has_no_hostile_samples(client):
    qs = client.get("/api/demo/questions").json()
    assert len(qs) >= 70 and all("DROP TABLE" not in q["text"] and "<script>" not in q["text"] for q in qs)
