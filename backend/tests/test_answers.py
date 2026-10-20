"""The answer is a person: who to ask, the score, the file title, where it is kept. Never a link."""
import re

import pytest
from fastapi.testclient import TestClient

import main
from engine.questions import persona_ids


@pytest.fixture(scope="module")
def ids(mut):
    return persona_ids(mut)


@pytest.fixture(scope="module")
def client(mut):
    main.state["engine"] = mut
    return TestClient(main.app)


QUESTIONS = ["payroll cut-off for Nike in Belgium", "What is the retirement age in Belgium?", "parental leave Belgium",
             "What do we know about Nike?", "build pipeline timeout", "sick leave Spain", "company car policy in France"]


def test_every_result_names_a_person_who_can_still_help(mut, ids):
    seen = 0
    for q in QUESTIONS:
        for who in ("hr", "es", "dev"):
            for r in mut.search(q, ids[who])["results"]:
                h = r["holder"]
                assert h is not None and h["active"], (q, r["doc_id"])
                assert h["person_id"] in mut.persons.index
                seen += 1
    assert seen > 100


def test_a_departed_owner_is_replaced_by_the_closest_colleague_with_an_explanation(mut, ids):
    r = [x for x in mut.search("What is the retirement age in Belgium?", ids["hr"])["results"] if x["in_scope"]]
    assert r and all(x["holder"]["active"] for x in r)
    assert all(x["holder_note"] and "left the company" in x["holder_note"] for x in r)   # every Belgian author of that topic left
    # a document whose owner is here names the owner and needs no note
    ok = mut.search("parental leave Belgium", ids["hr"])["results"][0]
    assert ok["holder_note"] is None and ok["holder"]["person_id"] in (mut.docs.owner_id[ok["doc_id"]], mut.docs.author_id[ok["doc_id"]])


def test_where_is_plain_words_and_never_a_link(mut, ids):
    for q in QUESTIONS:
        for who in ("hr", "es"):
            for r in mut.search(q, ids[who])["results"]:
                assert "://" not in r["location"] and "http" not in r["location"].lower() and "\\" not in r["location"], r["location"]
                assert r["location"].split(" › ")[0].startswith(("SharePoint", "Teams", "Notion", "GitHub", "Old shared drive")) or "OneDrive" in r["location"]
                assert "link" not in r and "link" not in str(r["holder"])


def test_location_examples(mut):
    d = mut.docs.loc["H001"]
    assert mut.where(d) == "SharePoint › HR Advisory Belgium 1 › Policies"
    d = mut.docs.loc["H011"]
    assert mut.where(d) == "SharePoint › Customer Success Belgium 1 › Customers › Nike"
    od = mut.docs[mut.docs.source == "OneDrive"].iloc[0]
    assert "'s OneDrive › " in mut.where(od)


def test_folder_comes_from_the_path_of_a_saved_file(mut):
    from engine.tools import folder_from_path
    assert folder_from_path("/sites/hr-belgium/Policies/Parental leave Belgium 2026 v5.docx") == "Policies"
    assert folder_from_path("/sites/customer-success/Nike/Payroll cut-off agreement.docx") == "Nike"
    assert folder_from_path("General/Files/Company car/lease rules.docx") == "Company car"
    assert folder_from_path("") == "" and folder_from_path("/sites/x.docx") == ""
    res = mut.ingest_event(mut.heroes["hr_senior"], {"source": "SharePoint", "title": "Expense policy Belgium extra", "topic_id": "expense_policy",
                                                     "country": "BE", "path": "/sites/hr-belgium/Finance rules/Expense policy.docx",
                                                     "key_value": "claim within 61 days", "extract": "Expense policy. Rule: claim within 61 days."})
    assert res["document"]["location"].endswith("› Finance rules")


def test_company_emails_are_unique_and_well_formed(mut):
    e = mut.persons.email
    assert e.is_unique and e.str.match(r"^[a-z.]+\d*@sdworx\.example$").all()
    assert not e.str.contains("..", regex=False).any() and not e.str.startswith(".").any()


def test_contact_details_by_click(mut, client, ids):
    h = mut.search("parental leave Belgium", ids["hr"])["results"][0]["holder"]["person_id"]
    r = client.get(f"/api/people/{h}/contact", params={"user_id": ids["hr"]}).json()
    assert r["email"] == mut.persons.email[h] and r["email"].endswith("@sdworx.example")
    assert r["role"] and r["team"] and r["country"] and "note" in r
    left = mut.persons.index[~mut.persons.active][0]
    gone = client.get(f"/api/people/{left}/contact", params={"user_id": ids["hr"]}).json()
    assert gone["email"] is None and "left the company" in gone["note"]
    assert client.get("/api/people/P99999/contact", params={"user_id": ids["hr"]}).status_code == 404
    assert client.get("/api/people/nope/contact", params={"user_id": ids["hr"]}).status_code == 422
    assert client.get(f"/api/people/{h}/contact").status_code == 422                          # needs a signed-in user


def test_signed_up_people_get_a_company_email(mut):
    team = mut.signup_options("BE", "HR Advisory")["teams"][0]["team_id"]
    r = mut.signup("Zoe Newcomer", "BE", "HR Advisory", "Junior", team_id=team)
    pid = r["person"]["person_id"]
    assert mut.persons.email[pid] == "zoe.newcomer@sdworx.example"
    assert mut.contact(pid)["email"] == "zoe.newcomer@sdworx.example"
    r2 = mut.signup("Zoe Newcomer", "BE", "HR Advisory", "Junior", team_id=team)           # same name: still unique
    assert mut.persons.email[r2["person"]["person_id"]] != mut.persons.email[pid]


def test_emails_are_not_part_of_search_results_or_cards(mut, ids):
    r = mut.search("parental leave Belgium", ids["hr"])
    assert "@" not in str(r)                                                                  # contact details only appear on click


def test_the_explanation_behind_every_score_is_kept(mut, ids):
    r = mut.search("payroll cut-off for Nike in Belgium", ids["es"])["results"]
    for x in r[:3]:                                                                       # the top results carry the full explanation
        assert x["reasons"] and all(set(c) == {"sign", "text"} for c in x["reasons"])
        assert x["contributions"] and all(set(c) == {"label", "effect"} for c in x["contributions"])
    assert any("Verified by" in c["text"] for x in r for c in x["reasons"])
    assert any("Contradicts" in c["text"] for x in r for c in x["reasons"])
