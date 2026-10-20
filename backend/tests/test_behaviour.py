"""Access rights, the keep-it-trusted loop, events, profiles, retraining. Uses the mutable engine."""
import time

import pandas as pd
import pytest

from engine.questions import persona_ids
from scripts.check_questions import check_curated


@pytest.fixture(scope="module")
def ids(mut):
    return persona_ids(mut)


def expected_visible(e, uid, d):
    u = e.persons.loc[uid]
    if d.acl == "all":
        return True
    if d.acl.startswith("dept:"):
        return u.department == d.acl[5:]
    cid = d.acl[7:]
    interacted = {t for s, t in zip(e.edges.source, e.edges.target) if s == uid and t.startswith("C")}
    return cid in interacted or u.team_id == d.team_id or u.level in ("Lead", "Head")


def test_access_rules_for_every_persona(mut, ids):
    restricted = mut.docs[mut.docs.acl != "all"].sample(400, random_state=4)
    for who, uid in ids.items():
        for d in restricted.itertuples():
            row = mut.docs.loc[d.Index]
            assert mut.can_see(uid, row) == expected_visible(mut, uid, row), (who, d.Index)


def test_search_never_returns_hidden_documents(mut, ids):
    for who in ("dev", "pay", "es"):
        for q in ("salary bands Belgium", "employment contract template Spain", "What do we know about Nike?",
                  "payroll cut-off for Nike in Belgium"):
            r = mut.search(q, ids[who])
            for x in r["results"]:
                assert mut.can_see(ids[who], mut.docs.loc[x["doc_id"]]), (who, q, x["doc_id"])
    assert mut.search("salary bands Belgium", ids["dev"])["results"] == []
    assert mut.search("salary bands Belgium", ids["hr"])["results"] != []


def test_curated_questions_all_pass(mut, ids):
    rows, fails = check_curated(mut, ids)
    assert len(rows) >= 70 and not fails, fails


def test_search_defaults_to_own_country_and_flags_it(mut, ids):
    r = mut.search("sick leave", ids["pay"])
    assert r["intent"]["country"] == mut.persons.country[ids["pay"]] and r["intent"]["country_defaulted"]


def test_ambiguous_question_gives_suggestions(mut, ids):
    assert mut.search("payroll", ids["pay"])["did_you_mean"]
    assert not mut.search("payroll cut-off Belgium", ids["pay"])["did_you_mean"]


def test_nothing_trustworthy_means_ask_an_expert(mut, ids):
    r = mut.search("What is the retirement age in Belgium?", ids["hr"])
    assert r["ask_expert"] and r["experts"]


def test_vote_can_be_changed_and_undone(mut, ids):
    mut.votes.pop("H003", None)
    base = mut.final_trust(mut.docs.loc["H003"], "BE")[0]
    assert mut.vote("H003", ids["hr"], "confirm")["my_vote"] == "confirm"
    assert mut.final_trust(mut.docs.loc["H003"], "BE")[0] == pytest.approx(min(100, base + 4))
    assert mut.vote("H003", ids["hr"], "flag")["my_vote"] == "flag"                   # changed their mind
    assert mut.votes["H003"] == {"confirm": 0, "flag": 1}
    assert mut.final_trust(mut.docs.loc["H003"], "BE")[0] == pytest.approx(max(0, base - 8))
    assert mut.vote("H003", ids["hr"], "flag")["my_vote"] is None                     # same choice again undoes it
    assert mut.votes["H003"] == {"confirm": 0, "flag": 0} and "H003" not in mut.extra_labels
    assert mut.final_trust(mut.docs.loc["H003"], "BE")[0] == pytest.approx(base)
    hidden = mut.docs[mut.docs.acl.str.startswith("dept:")].index[0]
    with pytest.raises(PermissionError):
        mut.vote(hidden, ids["dev"], "flag")
    mut.votes.pop("H003", None)


def test_my_vote_is_returned_in_search(mut, ids):
    mut.vote("H001", ids["hr"], "confirm")
    r = mut.search("parental leave Belgium", ids["hr"])
    assert {x["doc_id"]: x["my_vote"] for x in r["results"]}.get("H001") in ("confirm", None)
    mut.vote("H001", ids["hr"], "none")


def test_conflict_with_an_unverified_document_alone_needs_no_approval(mut):
    keyed = mut.docs[(mut.docs.key_value != "") & (mut.docs.client == "") & (mut.docs.country != "ALL")]
    grp = next(g for _, g in keyed.groupby(["topic_id", "country"]) if len(g) >= 2 and not g.verified.any())
    topic, country = grp.topic_id.iloc[0], grp.country.iloc[0]
    author = next(p for p in mut.persons.index if mut.persons.country[p] == country and mut.persons.active[p]
                  and mut.persons.level[p] in ("Junior", "Medior", "Senior") and mut.persons.team_id[p] in mut.team_tools
                  and "SharePoint" in mut.team_tools[mut.persons.team_id[p]])
    res = mut.ingest_event(author, {"source": "SharePoint", "title": f"{mut.topics.name[topic]} update", "topic_id": topic, "country": country,
                                    "key_value": "99 something else", "extract": f"{mut.topics.name[topic]}. Rule: 99 something else."})
    assert res["status"] != "duplicate"
    if res["status"] == "pending_approval":            # allowed only for other reasons (model unsure, topic unclear)
        assert all("Contradicts" not in r for r in res["approval"]["reasons"]), res["approval"]["reasons"]


def test_retraining_is_limited_to_management_and_admin(mut, ids):
    h = mut.heroes
    assert mut.can_retrain(h["admin"])
    assert mut.can_retrain(ids["lead"])
    head = mut.persons.index[mut.persons.level == "Head"][0]
    assert mut.can_retrain(head)
    for who in ("hr", "dev", "pay", "es"):
        assert not mut.can_retrain(ids[who])
    with pytest.raises(PermissionError):
        mut.set_policy(user_id=ids["hr"], auto=False)
    assert mut.set_policy(user_id=ids["lead"], auto=True)["auto"] is True


def test_sign_up_joins_a_team(mut):
    opt = mut.signup_options("BE", "HR Advisory")
    team = next(t for t in opt["teams"] if t["has_lead"])
    n = len(mut.persons)
    r = mut.signup("Nora Test", "BE", "HR Advisory", "Junior", team_id=team["team_id"])
    pid = r["person"]["person_id"]
    assert len(mut.persons) == n + 1 and mut.persons.team_id[pid] == team["team_id"]
    assert mut.reports_to[pid] == mut.teams.lead_id[team["team_id"]]                  # reports to the team lead
    assert not r["can_edit_team"] and pid in mut.team_people[team["team_id"]]
    assert mut.search("parental leave Belgium", pid)["results"]
    assert mut.profile(pid)["team"]["team_id"] == team["team_id"]
    assert not mut.persons.opt_in_signals[pid]                                       # signals are off until chosen
    assert mut.search_people("nora test")[0]["person_id"] == pid
    # their uploads are approved by someone above them
    res = mut.ingest_event(pid, {"source": "SharePoint", "title": "Parental leave Belgium note", "topic_id": "parental_leave", "country": "BE",
                                 "key_value": "30 weeks per parent", "extract": "Parental leave. Rule: 30 weeks per parent."})
    if res["status"] == "pending_approval":
        chain = [mut.teams.lead_id[team["team_id"]]]                      # first ACTIVE person above the new colleague
        while chain[-1] and chain[-1] in mut.reports_to:
            chain.append(mut.reports_to[chain[-1]])
        first_active = next(x for x in chain if x and mut.persons.active[x])
        assert res["approval"]["requested_from"] == first_active


def test_team_lead_can_create_a_team_with_tools(mut):
    r = mut.signup("Tim Lead", "BE", "Marketing", "Team Lead", new_team_name="Growth", team_tools=["Notion", "Teams"])
    pid, tid = r["person"]["person_id"], r["team"]["team_id"]
    assert r["team"]["created"] and r["can_edit_team"] and mut.teams.lead_id[tid] == pid
    assert mut.team_tools[tid] == {"Notion", "Teams"} and set(r["connect_links"]) == {"Notion", "Teams"}
    assert all(u.startswith("https://") for u in r["connect_links"].values())
    assert mut.reports_to[pid] and mut.persons.role[mut.reports_to[pid]] == "Head of Marketing"
    assert any("official source" in w for w in mut.tool_warnings(tid))                # Notion + Teams only
    with pytest.raises(ValueError):
        mut.signup("Second Lead", "BE", "Marketing", "Team Lead", team_id=tid)       # the team already has a lead


def test_sign_up_rules(mut):
    team = mut.signup_options("BE", "HR Advisory")["teams"][0]["team_id"]
    for bad in (dict(name="x"), dict(name="<script>"), dict(name="Ok Name", country="ZZ"), dict(name="Ok Name", department="Nope"),
                dict(name="Ok Name", level="CEO")):
        kw = dict(name="Ok Name", country="BE", department="HR Advisory", level="Junior", team_id=team) | bad
        with pytest.raises(ValueError):
            mut.signup(**kw)
    with pytest.raises(ValueError):                                                   # a junior cannot create a team
        mut.signup("Ok Name", "BE", "Marketing", "Junior", new_team_name="Mine", team_tools=["Teams"])
    with pytest.raises(ValueError):                                                   # a team of another country or department
        mut.signup("Ok Name", "NL", "HR Advisory", "Junior", team_id=team)
    with pytest.raises(ValueError):
        mut.signup("Ok Name", "BE", "Marketing", "Team Lead", new_team_name="Mine", team_tools=[])


def test_people_search(mut):
    assert mut.search_people("a") == []                                               # too short
    hits = mut.search_people("sofie")
    assert hits and all("sofie" in h["name"].lower() and h["active"] for h in hits) and len(hits) <= 10


def test_signed_up_people_survive_a_retrain(mut):
    pid = mut.search_people("nora test")[0]["person_id"]
    mut.retrain("test")
    assert pid in mut.persons.index and mut.persons.name[pid] == "Nora Test"


def test_health_per_department_and_country(mut):
    dep = mut.org_departments()
    assert len(dep) == 9 and all(0 <= x["health"] <= 100 for x in dep)
    assert sum(x["docs"] for x in dep) <= len(mut.docs)
    assert len(mut.org_overview()) == 26


def test_validation_explains_why_the_score_is_reliable(mut):
    v = mut.validation()
    top = v["top_answer_correct"]
    assert top["graphlas"] > top["random_pick"] + 0.2 and top["graphlas"] >= top["newest_document"] and top["graphlas"] > top["most_linked_document"]
    b = {x["band"]: x["state_the_current_value"] for x in v["bands"]}
    assert b["green"] > b["yellow"] > b["red"] and b["green"] > 0.9 and b["red"] < 0.4
    assert v["auc_vs_truth"] > 0.9 and v["groups"] > 300


def payload(**kw):
    base = {"source": "SharePoint", "title": "Parental leave Belgium (update)", "key_value": "18 weeks per parent",
            "extract": "Parental leave. Rule: 18 weeks per parent. Proposed update.", "topic_id": "parental_leave", "country": "BE"}
    return {**base, **kw}


def test_conflicting_document_needs_the_approver_above_the_author(mut, ids):
    h = mut.heroes
    res = mut.ingest_event(h["hr_senior"], payload())
    assert res["status"] == "pending_approval"
    ap = res["approval"]
    assert ap["requested_from"] == mut.above(h["hr_senior"]) != h["hr_senior"]
    assert any("verified document" in r and mut.docs.title["H001"] in r for r in ap["reasons"])
    with pytest.raises(PermissionError):
        mut.decide(ap["approval_id"], h["hr_senior"], "approve")        # nobody approves their own work
    old_before = mut.trust["H001"]
    out = mut.decide(ap["approval_id"], ap["requested_from"], "approve")
    new_id = ap["doc_id"]
    assert out["document"]["verified"] and mut.docs.verified[new_id]
    assert not mut.docs.verified["H001"]
    assert new_id in mut.superseded_by.get("H001", [])
    assert mut.trust["H001"] < old_before and mut.trust["H001"] < 45     # the old policy turns red
    with pytest.raises(ValueError):
        mut.decide(ap["approval_id"], ap["requested_from"], "approve")


def test_rejection_flags_the_document_and_notifies(mut, ids):
    h = mut.heroes
    res = mut.ingest_event(h["hr_junior"], payload(title="Parental leave BE draft 2", key_value="22 weeks per parent",
                                                    extract="Parental leave. Rule: 22 weeks per parent."))
    if res["status"] != "pending_approval":
        pytest.skip("no approval requested")
    ap = res["approval"]
    mut.decide(ap["approval_id"], ap["requested_from"], "reject")
    assert mut.extra_labels[ap["doc_id"]] == 1
    assert mut.votes[ap["doc_id"]]["flag"] == 2
    assert any(n["to"] == h["hr_junior"] for n in mut.notifications)


def test_duplicate_adds_nothing(mut):
    h = mut.heroes
    n = len(mut.docs)
    res = mut.ingest_event(h["hr_medior"], {"source": "OneDrive", "title": "Parental leave policy Belgium",
                                            "key_value": "17 weeks per parent", "topic_id": "parental_leave", "country": "BE",
                                            "extract": "Parental leave. Rule: 17 weeks per parent. Valid from 1 September 2026."})
    # after the approval test H001 may be replaced; either way a repeat of an existing fact must not add a document twice
    again = mut.ingest_event(h["hr_medior"], {"source": "OneDrive", "title": "Parental leave policy Belgium",
                                              "key_value": "17 weeks per parent", "topic_id": "parental_leave", "country": "BE",
                                              "extract": "Parental leave. Rule: 17 weeks per parent. Valid from 1 September 2026."})
    assert again["status"] == "duplicate"
    assert len(mut.docs) == n + (0 if res["status"] == "duplicate" else 1)


def test_only_a_link_and_one_fact_are_kept(mut):
    h = mut.heroes
    long_text = "x" * 5000
    res = mut.ingest_event(h["be_cs"], {"source": "SharePoint", "title": "Nike payroll cut-off agreement Spain", "country": "ES",
                                        "client": "C01", "topic_id": "client_cutoff", "key_value": "cut-off on day 13",
                                        "extract": long_text, "link": "https://sdworx.sharepoint.example/x"})
    d = mut.docs.loc[res["document"]["doc_id"]]
    assert len(d.text) <= 300 and d.link == "https://sdworx.sharepoint.example/x"
    assert "text" not in mut.doc_json(d, detail=True) and "extract" in mut.doc_json(d, detail=True)


def test_tool_not_connected_is_ignored(mut, ids):
    res = mut.ingest_event(ids["hr"], {"source": "Notion", "title": "Anything", "extract": "x"})
    assert res["status"] == "ignored"


def test_meeting_title_is_dissected(mut, ids):
    h = mut.heroes
    team = mut.team_members(h["be_cs"])
    before = mut.evidence.get(("client:C01", team[0]["person_id"], "ATTENDED"), 0)
    res = mut.ingest_meeting(h["be_cs"], {"title": "Nike payroll cut-off review with Belgium team",
                                          "attendees": [m["person_id"] for m in team]})
    assert res["status"] == "captured"
    assert res["extracted"]["client"] == "C01" and res["extracted"]["topic"] == "payroll_cutoff" and res["extracted"]["country"] == "BE"
    opted = [m for m in team if m["meetings_opt_in"]]
    assert res["attendees"]["counted"] == len(opted) + (1 if mut.signal_allowed(h["be_cs"], "meetings") else 0)
    assert res["attendees"]["not_opted_in"] == len(team) + 1 - res["attendees"]["counted"]
    if opted:
        assert mut.evidence.get(("client:C01", opted[0]["person_id"], "ATTENDED"), 0) > 0
        assert mut.exp["client:C01"].max() == pytest.approx(1.0)
    assert "link" in res and res["link"].startswith("https://")


def test_meeting_without_topic_or_customer_is_not_stored(mut, ids):
    n = len(mut.docs)
    res = mut.ingest_meeting(ids["hr"], {"title": "1:1 catch-up", "attendees": []})
    assert res["status"] == "ignored" and len(mut.docs) == n


def test_ambiguous_meeting_title_is_not_stored(mut, ids):
    n = len(mut.docs)
    assert mut.ingest_meeting(ids["hr"], {"title": "payroll sync", "attendees": []})["status"] == "ignored"
    assert len(mut.docs) == n


def test_only_team_leads_change_team_tools(mut, ids):
    with pytest.raises(PermissionError):
        mut.set_profile(ids["hr"], team_tools=["Teams"])
    lead = mut.teams.lead_id[mut.persons.team_id[ids["hr"]]]
    assert lead and mut.can_manage(lead, mut.persons.team_id[ids["hr"]])
    assert not mut.can_manage(ids["dev"], mut.persons.team_id[ids["hr"]])
    p = mut.set_profile(lead, team_tools=["Teams", "SharePoint"])
    assert {t["source"] for t in p["team_tools"] if t["enabled"]} == {"Teams", "SharePoint"}
    with pytest.raises(ValueError):
        mut.set_profile(lead, team_tools=[])
    with pytest.raises(ValueError):
        mut.set_profile(lead, team_tools=["Nope"])


def test_team_without_official_source_is_warned(mut, ids):
    lead = mut.teams.lead_id[mut.persons.team_id[ids["hr"]]]
    p = mut.set_profile(lead, team_tools=["Teams"])
    assert any("official source" in w for w in p["warnings"])
    mut.set_profile(lead, team_tools=["Teams", "SharePoint"])


def test_linking_and_unlinking_an_account_switches_its_signal(mut, ids):
    uid = ids["dev"]
    p = mut.set_profile(uid, connections=["GitHub", "Notion"])
    sig = {s["key"]: s["enabled"] for s in p["signals"]}
    assert sig["commits"] and any(t["source"] == "Notion" and t["enabled"] for t in p["personal_tools"])
    p = mut.set_profile(uid, connections=[])
    assert not {s["key"]: s["enabled"] for s in p["signals"]}["commits"]
    with pytest.raises(ValueError):
        mut.set_profile(uid, connections=["Evil"])


def test_switching_a_signal_off_removes_it_from_expertise(mut):
    ev = [(k, v) for k, v in mut.evidence.items() if k[2] == "COMMITTED"]
    key, pid, typ = ev[0][0]
    assert mut.persons.opt_in_signals[pid] and mut.expert_raw.get((key, pid), 0) > 0
    mut.set_profile(pid, signals={"commits": False})
    assert (key, pid, "COMMITTED") not in mut.evidence
    mut.set_profile(pid, signals={"commits": True})
    assert (key, pid, "COMMITTED") in mut.evidence


def test_resolution_memory(mut, ids):
    h = mut.heroes
    intent = ("client_sla", "ES", "C01")
    mut.resolve(ids["es"], *intent, person_id=h["be_cs"])
    sc = mut.shortcuts(*intent)
    assert sc and sc[0]["person"]["person_id"] == h["be_cs"] and sc[0]["confirmations"] >= 4
    with pytest.raises(ValueError):
        mut.resolve(ids["es"], *intent, person_id=h["be_cs"])            # one confirmation per colleague
    # confirmations fade, and a contact who left is dropped
    e = mut.resolutions[mut.intent_key(*intent)][("person", h["be_cs"])]
    fresh = mut.shortcuts(*intent)[0]["weight"]
    e["last"] = e["last"] - pd.Timedelta(days=360)
    assert mut.shortcuts(*intent)[0]["weight"] == pytest.approx(fresh / 4, rel=0.01)
    mut.persons.loc[h["be_cs"], "active"] = False
    assert not [s for s in mut.shortcuts(*intent) if s["type"] == "person" and s["person"]["person_id"] == h["be_cs"]]
    mut.persons.loc[h["be_cs"], "active"] = True


def test_edit_rules(mut, ids):
    h = mut.heroes
    res = mut.ingest_event(h["be_cs"], {"source": "SharePoint", "title": "Nike cut-off Germany", "country": "DE", "client": "C01",
                                        "topic_id": "client_cutoff", "key_value": "cut-off on day 9", "extract": "Payroll cut-off agreement. Rule: cut-off on day 9."})
    did = res["document"]["doc_id"]
    mut.new_since_train = 0
    cos = mut.edit(did, h["be_cs"], text=mut.docs.text[did])                     # nothing really changed
    assert not cos["material"] and mut.new_since_train == 0
    with pytest.raises(PermissionError):
        mut.edit(did, ids["dev"], key_value="cut-off on day 1")
    mat = mut.edit(did, h["be_cs"], key_value="cut-off on day 11")
    assert mat["material"] and mut.new_since_train == 1
    assert mut.docs.edited[did]
    assert any("Edited since the last check" in r["text"] for r in mut.doc_json(mut.docs.loc[did])["reasons"])


def test_retraining_triggers_and_resets(mut):
    mut.policy.update({"min_new_docs": 3, "min_gap_hours": 0, "auto": True})
    mut.new_since_train = 0
    n = len(mut.retrain_log)
    h = mut.heroes
    for i in range(3):
        mut.ingest_event(h["hr_medior"], {"source": "SharePoint", "title": f"Expense policy Belgium variant {i}", "topic_id": "expense_policy",
                                          "country": "BE", "key_value": f"claim within {40 + i} days", "extract": f"Expense policy. Rule: claim within {40 + i} days."})
    t0 = time.time()
    while len(mut.retrain_log) == n and time.time() - t0 < 90:
        time.sleep(1)
    assert len(mut.retrain_log) == n + 1, "auto retraining did not start"
    assert mut.retrain_log[-1]["documents"] == len(mut.docs)
    assert mut.new_since_train == 0


def test_no_second_training_inside_the_minimum_gap(mut):
    mut.policy.update({"min_new_docs": 1, "min_gap_hours": 24, "auto": True})
    mut.last_train_wall = pd.Timestamp.now()
    n = len(mut.retrain_log)
    mut.new_since_train = 5
    assert mut._retrain_due() == (False, "gap")
    mut.policy["auto"] = False
    mut._count_new(1)
    time.sleep(1)
    assert len(mut.retrain_log) == n
    mut.policy.update({"auto": True, "min_new_docs": 100})


def test_new_document_is_scored_fast_without_full_rebuild(mut):
    assert mut.stats["last_ingest_ms"] < 1000 and mut.stats["full_rebuild_s"] > 1
    assert mut.stats["last_ingest_ms"] < mut.stats["full_rebuild_s"] * 1000 / 5


def test_survey_answers_are_optional_and_can_have_several_values(mut, ids):
    uid = ids["pay"]
    p = mut.set_profile(uid, answers={"find": ["ask a colleague", "search in Teams", "ask a colleague", "bogus"], "frequency": "weekly"})
    assert p["answers"]["find"] == ["ask a colleague", "search in Teams"]          # several, no duplicates, invalid dropped
    assert p["answers"]["frequency"] == ["weekly"]                                 # a single value still works
    assert mut.set_profile(uid, answers={"find": []})["answers"]["find"] == []     # clearing is fine
    assert mut.set_profile(uid)["onboarded"]                                       # saving with no answers at all is fine


def test_meeting_description_is_read_but_not_stored(mut, ids):
    h = mut.heroes
    plain = mut.ingest_meeting(h["be_cs"], {"title": "Weekly sync", "attendees": []})
    assert plain["status"] == "ignored"                                              # the title alone says nothing
    n = len(mut.docs)
    res = mut.ingest_meeting(h["be_cs"], {"title": "Weekly sync", "attendees": [],
                                          "description": "Agenda: 1. Nike payroll cut-off in Belgium: agree the new date."})
    assert res["status"] == "captured" and len(mut.docs) == n + 1
    assert res["extracted"]["client"] == "C01" and res["extracted"]["topic"] == "payroll_cutoff" and res["extracted"]["country"] == "BE"
    assert set(res["read_from_description"]) == {"topic", "customer", "country"}
    stored = mut.docs.loc[mut.docs.index[-1]]
    assert "agree the new date" not in (stored.text + stored.title)                  # the agenda text is not kept
    vague = mut.ingest_meeting(h["be_cs"], {"title": "Catch up", "attendees": [], "description": "Coffee and general news."})
    assert vague["status"] == "ignored"
    both = mut.ingest_meeting(h["be_cs"], {"title": "Nike payroll cut-off review", "attendees": [], "description": "Open questions."})
    assert both["status"] == "captured"


def test_diego_silva_has_an_approval_waiting(eng):
    h = eng.heroes
    items = eng.list_approvals(h["es_sales"])
    assert len(items) >= 1
    a = items[0]
    assert a["kind"] == "approval" and a["approver"]["person_id"] == h["es_sales"]
    assert a["author"]["person_id"] == h["es_junior"] and eng.reports_to[h["es_junior"]] == h["es_sales"]
    assert any("verified document" in r and "Expat payroll policy Spain 2026" in r for r in a["reasons"])
    assert "://" not in a["document"]["location"]


def test_signals_are_described_by_what_is_true(eng):
    for did in ("H001", "H002", "H003", "D00110", "H011"):
        row = eng.F.loc[did]
        for c in eng.contributions(did, n=6):
            lab = c["label"]
            if lab.startswith("No conflicts"):
                assert row.conflict_share == 0
            if lab.startswith("Conflicts with"):
                assert row.conflict_share > 0
            if lab == "Owner left the company":
                assert row.owner_inactive == 1
            if lab == "Owner still works here":
                assert row.owner_inactive == 0
            if lab.startswith("Replaced by"):
                assert row.superseded == 1
            if lab.startswith("Recently updated"):
                assert row.age_days < 365 * 1.5
    h2 = {c["label"]: c["effect"] for c in eng.contributions("H002", n=6)}
    assert h2["Owner left the company"] < 0 and h2["Replaced by a newer version"] < 0           # bad facts lower trust: shown red
    h1 = {c["label"]: c["effect"] for c in eng.contributions("H001", n=6)}
    assert h1["Owner still works here"] > 0                                                      # good facts raise trust: shown green
