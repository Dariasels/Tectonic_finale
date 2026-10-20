"""Hand-crafted demo scenarios injected into the simulated tables (all data is simulated).

S1  Parental leave BE: current verified policy (green) vs old, most-linked, ownerless policy (red) + conflicting drafts.
S2  Retirement age BE: every author has left; one active colleague is the real expert.
S3  Nike: contacts across countries; the top expert left, the next one is active in another country.
"""
import numpy as np
import pandas as pd


def inject_heroes(t, seed=11):
    rng = np.random.default_rng(seed)
    P = t["persons"].set_index("person_id", drop=False)
    D = t["documents"]
    E = t["edges"]
    FB, GT = t["feedback"], t["ground_truth"]
    reports = P.reports_to.to_dict()
    new_docs, new_edges, new_fb, new_gt, drop_ids = [], [], [], [], set()

    def above(pid):
        cur = reports.get(pid, "")
        while cur and not P.active[cur]:
            cur = reports.get(cur, "")
        return cur

    def mk(did, title, topic, country, client, author, source, modified, value, text, current, verified=False,
           owner=True, version=1, acl="all", approver=None, views=60, flag_rate=None):
        a = P.loc[author]
        new_docs.append({"doc_id": did, "title": title, "doc_type": "policy", "topic_id": topic, "country": country,
                         "client": client, "department": a.department, "team_id": a.team_id, "author_id": author,
                         "owner_id": author if owner else "", "created": modified, "last_modified": modified,
                         "version": version, "source": source, "language": "en", "key_value": value, "verified": verified,
                         "text": text, "acl": acl})
        new_edges.extend([(author, did, "AUTHORED", 1), (did, topic, "ABOUT", 1), (did, source, "STORED_IN", 1),
                          (did, a.team_id, "OWNED_BY", 1)])
        if client:
            new_edges.append((did, client, "ABOUT", 1))
        if verified and approver:
            new_edges.append((approver, did, "APPROVED", 1))
        rate = flag_rate if flag_rate is not None else (0.1 if current else 0.6)
        fl = int(round(views * rate))
        new_fb.append((did, views, fl, round(fl / views, 3), int(fl / views >= 0.35)))
        new_gt.append((did, current))

    def group_ids(topic, country, client=""):
        return set(D[(D.topic_id == topic) & (D.country == country) & (D.client == client)].doc_id)

    be_hr = P[(P.country == "BE") & (P.department == "HR Advisory")]
    active = be_hr[be_hr.active & (be_hr.level.isin(["Senior", "Medior"]))]
    senior = active[active.level == "Senior"].index[0]
    medior = active[active.level == "Medior"].index[0]
    junior = be_hr[be_hr.active & (be_hr.level == "Junior")].index[0]
    left = list(be_hr[~be_hr.active].index)
    if len(left) < 3:                                    # make sure there are former colleagues
        extra = [i for i in be_hr[be_hr.active & (be_hr.level == "Junior")].index[1:4]]
        P.loc[extra, "active"] = True
        P.loc[extra, "active"] = False
        left += extra
    appr = above(senior)

    # ---- S1 parental leave BE
    drop_ids |= group_ids("parental_leave", "BE")
    mk("H001", "Parental leave policy Belgium 2026", "parental_leave", "BE", "", senior, "SharePoint", "2026-09-10",
       "17 weeks per parent", "Parental leave. Rule: 17 weeks per parent. Valid from 1 September 2026.", True,
       verified=True, version=4, approver=appr)
    mk("H002", "Handbook: Parental leave Belgium", "parental_leave", "BE", "", left[0], "SharePoint", "2021-06-14",
       "13 weeks per parent", "Parental leave. Rule: 13 weeks per parent. Step by step handbook for employees.", False,
       version=3)
    mk("H003", "Parental leave draft (new rule)", "parental_leave", "BE", "", junior, "OneDrive", "2025-11-03",
       "15 weeks per parent", "Parental leave. Rule: 15 weeks per parent. Draft, to be confirmed.", False, owner=False)
    mk("H004", "Team meeting: parental leave decision", "parental_leave", "BE", "", medior, "Teams", "2026-08-21",
       "17 weeks per parent", "Parental leave. Rule: 17 weeks per parent. Decision taken in the HR leadership meeting.", True)
    mk("H005", "Old shared drive copy: parental leave", "parental_leave", "BE", "", left[1], "Legacy drive", "2020-02-05",
       "13 weeks per parent", "Parental leave. Rule: 13 weeks per parent. Copy from the old shared drive.", False, owner=False)
    topic_docs = D[(D.topic_id == "parental_leave") & (~D.doc_id.isin(drop_ids))].doc_id.tolist()
    for src in rng.choice(topic_docs, 12, replace=False):          # the old policy is the most linked one
        new_edges.append((src, "H002", "LINKS_TO", 1))
    new_edges += [("H004", "H001", "LINKS_TO", 1), ("H001", "H002", "SUPERSEDES", 1)]

    # ---- S2 retirement age BE: every author left, one active expert
    pen = group_ids("pension", "BE")
    D = D.copy()
    for i, did in enumerate(sorted(pen)):
        who = left[i % len(left)]
        D.loc[D.doc_id == did, ["author_id", "owner_id", "verified"]] = [who, who, False]
    FB = FB.copy()
    FB.loc[FB.doc_id.isin(pen), ["views", "flags_wrong", "flag_rate", "unreliable"]] = [80, 52, 0.65, 1]   # colleagues flag them as unmaintained
    E = E[~((E.type == "APPROVED") & E.target.isin(pen))]
    E = E.copy()
    E.loc[(E.type == "AUTHORED") & E.target.isin(pen), "source"] = E[(E.type == "AUTHORED") & E.target.isin(pen)].target.map(
        D.set_index("doc_id").author_id)
    expert = active[active.level == "Medior"].index[min(1, len(active[active.level == "Medior"]) - 1)]
    new_edges += [(expert, "pension", "COMPLETED", 1)] + [(expert, d, "REVIEWS", 1) for d in sorted(pen)[:2]]

    # ---- S3 Nike
    es = P[(P.country == "ES") & P.active & P.department.isin(["Sales", "Customer Success", "Internationals"]) & P.level.isin(["Medior", "Senior"])]
    be_cs = P[(P.country == "BE") & P.active & (P.department == "Customer Success") & (P.level == "Senior")].index[0]
    nl_cs = P[(P.country == "NL") & (P.department == "Customer Success")].index[0]
    pl_dev = P[(P.country == "PL") & P.active & (P.department == "Engineering") & (P.level == "Senior")].index[0]
    P.loc[nl_cs, "active"] = False
    new_edges += [(es.index[0], "C01", "INTERACTED_WITH", 40), (be_cs, "C01", "INTERACTED_WITH", 90),
                  (nl_cs, "C01", "INTERACTED_WITH", 150), (pl_dev, "C01", "INTERACTED_WITH", 12)]
    nike_docs = D[D.client == "C01"].doc_id.tolist()
    for did in nike_docs[:3]:
        D.loc[D.doc_id == did, ["author_id", "owner_id"]] = [be_cs, be_cs]
        E.loc[(E.type == "AUTHORED") & (E.target == did), "source"] = be_cs
    for did in nike_docs[3:6]:
        D.loc[D.doc_id == did, ["author_id", "owner_id"]] = [nl_cs, nl_cs]
        E.loc[(E.type == "AUTHORED") & (E.target == did), "source"] = nl_cs

    drop_ids |= group_ids("client_cutoff", "BE", "C01") | group_ids("payroll_cutoff", "BE")
    be_lead_appr = above(be_cs)
    mk("H011", "Nike payroll cut-off agreement 2026", "client_cutoff", "BE", "C01", be_cs, "SharePoint", "2026-09-01",
       "cut-off on day 15", "Payroll cut-off agreement. Rule: cut-off on day 15. Agreed with Nike.", True, verified=True,
       version=3, acl="client:C01", approver=be_lead_appr)
    mk("H012", "Nike cut-off meeting notes (old)", "client_cutoff", "BE", "C01", nl_cs, "Teams", "2023-03-12",
       "cut-off on day 20", "Payroll cut-off agreement. Rule: cut-off on day 20. Notes from the 2023 kick-off.", False,
       owner=False, acl="client:C01")
    mk("H013", "Standard payroll cut-off Belgium", "payroll_cutoff", "BE", "", senior, "SharePoint", "2026-03-15",
       "cut-off on day 20", "Payroll cut-off. Rule: cut-off on day 20. Standard for all Belgian customers.", True,
       verified=True, version=5, approver=appr)
    new_edges += [("H011", "H013", "LINKS_TO", 1), ("H011", "H012", "SUPERSEDES", 1)]
    keep = ~D.doc_id.isin(drop_ids)
    D = pd.concat([D[keep], pd.DataFrame(new_docs)], ignore_index=True)
    E = E[~(E.source.isin(drop_ids) | E.target.isin(drop_ids))]
    E = pd.concat([E, pd.DataFrame(new_edges, columns=E.columns)], ignore_index=True)
    t["documents"] = D
    t["edges"] = E
    t["persons"] = P.reset_index(drop=True)
    t["feedback"] = pd.concat([FB[~FB.doc_id.isin(drop_ids)], pd.DataFrame(new_fb, columns=FB.columns)], ignore_index=True)
    t["ground_truth"] = pd.concat([GT[~GT.doc_id.isin(drop_ids)], pd.DataFrame(new_gt, columns=GT.columns)], ignore_index=True)
    t["_heroes"] = {"hr_senior": senior, "hr_medior": medior, "hr_junior": junior, "approver": appr,
                    "es_sales": es.index[0], "be_cs": be_cs, "pension_expert": expert, "nl_cs_left": nl_cs}
    return t
