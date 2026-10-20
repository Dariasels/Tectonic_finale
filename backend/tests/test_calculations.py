"""The numbers: trust score, context multipliers, conflicts, expertise, model behaviour."""
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from engine.core import FEATURES, badge

# the specification, written out on purpose (not imported from the code under test)
EXPERT_W = {"AUTHORED": 1.0, "APPROVED": 0.7, "REVIEWS": 0.5, "ATTENDED": 0.25, "COMPLETED": 0.6}
SCOPE_PENALTY, GENERIC_PENALTY, EDIT_PENALTY = 0.6, 0.85, 0.8


def test_trust_formula_for_every_document(eng):
    expected = 0.85 * eng.ml_score + 0.15 * 100 * eng.author_exp
    assert np.allclose(eng.trust.reindex(expected.index), expected)
    assert eng.trust.between(0, 100).all()
    assert np.allclose(eng.ml_score, 100 * (1 - eng.p_unreliable))
    assert eng.author_exp.between(0, 1).all()


def test_badge_thresholds():
    assert [badge(x) for x in (100, 70, 69.9, 45, 44.9, 0)] == ["green", "green", "yellow", "yellow", "red", "red"]


def test_inactive_authors_get_no_expertise_credit(eng):
    gone = eng.docs[~eng.docs.author_id.map(eng.persons.active)]
    assert len(gone) > 100
    assert (eng.author_exp[gone.index] == 0).all()


def test_context_multipliers(mut):
    d = mut.docs.loc["H001"].copy()                         # Belgian policy, no customer
    base = mut.trust["H001"]
    mut.votes.pop("H001", None)
    assert mut.final_trust(d, "BE")[0] == pytest.approx(base)
    t, in_scope, _ = mut.final_trust(d, "NL")
    assert t == pytest.approx(base * SCOPE_PENALTY) and not in_scope
    assert mut.final_trust(d, "BE", client="C01")[0] == pytest.approx(base * GENERIC_PENALTY)
    assert mut.final_trust(d, "NL", client="C01")[0] == pytest.approx(base * SCOPE_PENALTY * GENERIC_PENALTY)
    d["edited"] = True
    assert mut.final_trust(d, "BE")[0] == pytest.approx(base * EDIT_PENALTY)
    assert mut.final_trust(d, "ALL_COUNTRIES")[0] == pytest.approx(base * SCOPE_PENALTY * EDIT_PENALTY)   # unknown country = other country


def test_country_all_is_never_out_of_scope(mut):
    d = mut.docs[mut.docs.country == "ALL"].iloc[0]
    assert mut.final_trust(d, "BE")[1] is True


def test_vote_deltas_are_capped_and_clipped(mut):
    d = mut.docs.loc["H003"]
    base = mut.trust["H003"]
    mut.votes["H003"] = {"confirm": 1, "flag": 0}
    assert mut.final_trust(d, "BE")[0] == pytest.approx(min(100, base + 4))
    mut.votes["H003"] = {"confirm": 9, "flag": 0}
    assert mut.final_trust(d, "BE")[0] == pytest.approx(min(100, base + 12))
    mut.votes["H003"] = {"confirm": 0, "flag": 9}
    assert mut.final_trust(d, "BE")[0] == pytest.approx(max(0, base - 32))
    top = mut.docs.loc["H001"]
    mut.votes["H001"] = {"confirm": 9, "flag": 0}
    assert mut.final_trust(top, "BE")[0] <= 100
    mut.votes.pop("H001"); mut.votes.pop("H003")


def test_conflict_share_matches_independent_recomputation(eng):
    d = eng.docs[eng.docs.key_value != ""]
    sup = set(eng.superseded_by)
    sample = d.sample(300, random_state=3).index
    for did in sample:
        r = d.loc[did]
        grp = d[(d.topic_id == r.topic_id) & (d.country == r.country) & (d.client == r.client)]
        live = [x for x in grp.index if x not in sup]
        opp = [x for x in live if x != did and d.key_value[x] != r.key_value]
        denom = max(len(live) - (1 if did in live else 0), 1)
        assert eng.F.conflict_share[did] == pytest.approx(len(opp) / denom), did


def test_replaced_document_does_not_penalise_its_successor(eng):
    # H002 (13 weeks) is replaced by H001 (17 weeks): H001 must not be punished for contradicting its predecessor
    live = [x for x in eng.groups[("parental_leave", "BE", "")] if x not in eng.superseded_by]
    assert "H002" not in live and "H001" in live
    opp = [x for x in live if x != "H001" and eng.docs.key_value[x] != eng.docs.key_value["H001"]]
    assert eng.F.conflict_share["H001"] == pytest.approx(len(opp) / (len(live) - 1))


SIGNAL_TYPES = {"ATTENDED", "COMMITTED", "COMPLETED", "INTERACTED_WITH"}


def expected_raw(e, pid, key):
    ed, d = e.edges, e.docs
    total = 0.0
    for r in ed[ed.source == pid].itertuples():
        if r.type in SIGNAL_TYPES and not e.persons.opt_in_signals[pid]:      # personal signals are opt-in
            continue
        if r.type in ("AUTHORED", "APPROVED", "REVIEWS", "ATTENDED", "COMMITTED") and r.target in d.index:
            doc = d.loc[r.target]
            if key not in (f"topic:{doc.topic_id}", f"client:{doc.client}" if doc.client else None):
                continue
            if r.type == "AUTHORED":
                total += 1.0 * (1 + 2 * e.tr_pct.get(r.target, 0))
            elif r.type == "COMMITTED":
                total += 0.3 * np.log1p(r.weight)
            else:
                total += EXPERT_W[r.type]
        elif r.type == "COMPLETED" and key == f"topic:{r.target}":
            total += EXPERT_W["COMPLETED"]
        elif r.type == "INTERACTED_WITH" and key == f"client:{r.target}":
            total += min(4.0, 0.06 * r.weight)
    return total


def test_expertise_matches_independent_recomputation(eng):
    raw = eng.expert_raw
    rng = np.random.default_rng(5)
    idx = rng.choice(len(raw), 40, replace=False)
    checked = 0
    for i in idx:
        key, pid = raw.index[i]
        assert raw.iloc[i] == pytest.approx(expected_raw(eng, pid, key), rel=1e-6), (pid, key)
        checked += 1
    assert checked == 40


def test_expertise_is_normalised_per_key(eng):
    for key, s in eng.exp.items():
        assert s.max() == pytest.approx(1.0) and s.min() >= 0, key


def test_people_who_only_appear_as_listed_get_no_credit(eng):
    e = eng.edges
    listed = set(zip(e[e.type == "LISTED_AS"].source, e[e.type == "LISTED_AS"].target))
    real = e[e.type.isin(["AUTHORED", "APPROVED", "REVIEWS", "ATTENDED", "COMMITTED"])]
    real_pairs = set(zip(real.source, real.target))
    only = sorted((p, d) for p, d in listed if (p, d) not in real_pairs)[:200]
    assert only
    kept = 0
    for p, d in only:
        key = f"topic:{eng.docs.topic_id[d]}"
        if (key, p) in eng.expert_raw.index:
            # allowed only through some other, real signal on that topic
            assert expected_raw(eng, p, key) == pytest.approx(eng.expert_raw[(key, p)])
            kept += 1
    assert kept < len(only)


def test_experts_are_active_and_same_country_first(eng):
    for key, country in (("client:C01", "BE"), ("topic:parental_leave", "BE"), ("topic:build_pipeline", "PL")):
        ex = eng.experts_for(key, country)
        assert ex and all(x["active"] for x in ex)
        flags = [x["same_country"] for x in ex]
        assert flags == sorted(flags, reverse=True), "same-country experts must come first"


def test_model_is_monotone_where_promised(eng):
    X = eng.F.sample(400, random_state=2)
    base = eng.model.predict_proba(X)[:, 1]

    def bump(col, delta):
        Y = X.copy()
        Y[col] = Y[col] + delta
        return eng.model.predict_proba(Y)[:, 1]

    tol = 1e-6
    assert (bump("age_days", 800) >= base - tol).all()
    Y = X.copy(); Y["owner_inactive"] = 1
    assert (eng.model.predict_proba(Y)[:, 1] >= base - tol).all()
    Y = X.copy(); Y["no_owner"] = 1
    assert (eng.model.predict_proba(Y)[:, 1] >= base - tol).all()
    Y = X.copy(); Y["superseded"] = 1
    assert (eng.model.predict_proba(Y)[:, 1] >= base - tol).all()
    assert (bump("n_reviewers", 2) <= base + tol).all()
    assert (bump("trustrank", 0.01) <= base + tol).all()


def test_model_inputs_do_not_leak_the_answer(eng):
    banned = {"verified", "states_current_value", "unreliable", "flag_rate", "flags_wrong", "truth"}
    assert not banned & set(FEATURES)
    assert len(FEATURES) == 20


def test_model_quality_on_simulated_data(eng):
    assert eng.cv_auc > 0.9
    assert roc_auc_score(eng.truth, eng.trust.reindex(eng.truth.index)) > 0.85


def test_hero_scenarios(eng):
    t = eng.trust
    assert t["H001"] >= 70 and eng.docs.verified["H001"]
    assert t["H002"] < 45 and t["H003"] < 45 and t["H012"] < 10
    assert t["H011"] >= 70 and t["H013"] >= 70
    pen = eng.docs[(eng.docs.topic_id == "pension") & (eng.docs.country == "BE") & (eng.docs.client == "")]
    assert len(pen) and (eng.trust[pen.index] < 45).all()
    assert not eng.persons.active[pen.author_id].any()
