"""Simulated SD Worx-like organisation: 26 countries, ~10k people, documents from several tools.

Writes CSVs to backend/data/ (git-ignored, regenerate with `python -m engine.seed_org`).
Everything is SIMULATED. A hidden ground truth (does a document state the current value?)
is stored separately and never used for scoring, only for validation.

Tables: countries, departments(teams), persons, clients, topics, documents, edges,
feedback (simulated user flags), ground_truth.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REFERENCE_DATE = pd.Timestamp("2026-10-20")

# code: (name, language, weight)
COUNTRIES = {
    "BE": ("Belgium", "nl", 14), "NL": ("Netherlands", "nl", 9), "FR": ("France", "fr", 9),
    "DE": ("Germany", "de", 9), "ES": ("Spain", "es", 6), "PT": ("Portugal", "pt", 3),
    "IT": ("Italy", "it", 5), "PL": ("Poland", "pl", 8), "CZ": ("Czechia", "cs", 3),
    "SK": ("Slovakia", "sk", 2), "HU": ("Hungary", "hu", 3), "RO": ("Romania", "ro", 3),
    "BG": ("Bulgaria", "bg", 2), "GR": ("Greece", "el", 3), "AT": ("Austria", "de", 3),
    "CH": ("Switzerland", "de", 3), "IE": ("Ireland", "en", 3), "GB": ("United Kingdom", "en", 5),
    "DK": ("Denmark", "da", 2), "SE": ("Sweden", "sv", 3), "NO": ("Norway", "no", 2),
    "FI": ("Finland", "fi", 2), "LU": ("Luxembourg", "fr", 2), "HR": ("Croatia", "hr", 1),
    "SI": ("Slovenia", "sl", 1), "LT": ("Lithuania", "lt", 1),
}
# department: (share of staff, documents per person, titles)
DEPTS = {
    "Payroll Operations": (0.22, 2.0, ["Payroll Specialist", "Payroll Analyst"]),
    "Engineering": (0.20, 3.0, ["Back-end Developer", "Front-end Developer", "DevOps Engineer"]),
    "HR Advisory": (0.12, 3.5, ["HR Advisor", "HR Consultant"]),
    "Internationals": (0.09, 1.5, ["International Payroll Consultant", "Account Manager"]),
    "SMB": (0.09, 1.0, ["SMB Consultant", "Account Manager"]),
    "Customer Success": (0.08, 1.5, ["Customer Success Manager", "Client Consultant"]),
    "Sales": (0.07, 0.7, ["Sales Executive", "Sales Manager"]),
    "Marketing": (0.05, 1.0, ["Marketing Specialist", "Content Manager"]),
    "Legal & Compliance": (0.04, 3.5, ["Legal Counsel", "Compliance Officer"]),
}
LEVELS = [("Junior", 0.35), ("Medior", 0.40), ("Senior", 0.25)]
# source mix per department (variety across teams)
SOURCES = ["SharePoint", "OneDrive", "Teams", "Notion", "GitHub", "Legacy drive"]
SOURCE_MIX = {
    "Engineering": [0.20, 0.03, 0.12, 0.25, 0.40, 0.0],
    "HR Advisory": [0.65, 0.12, 0.10, 0.03, 0.0, 0.10],
    "Payroll Operations": [0.60, 0.12, 0.08, 0.02, 0.0, 0.18],
    "Legal & Compliance": [0.70, 0.08, 0.05, 0.02, 0.0, 0.15],
    "Internationals": [0.45, 0.20, 0.20, 0.05, 0.0, 0.10],
    "SMB": [0.45, 0.20, 0.20, 0.05, 0.0, 0.10],
    "Customer Success": [0.30, 0.25, 0.30, 0.10, 0.0, 0.05],
    "Sales": [0.30, 0.30, 0.30, 0.10, 0.0, 0.0],
    "Marketing": [0.30, 0.25, 0.20, 0.25, 0.0, 0.0],
}

# topic: (name, owner dept, scoped per country?, value format, lo, hi, acl)
TOPICS = {
    # HR Advisory
    "parental_leave": ("Parental leave", "HR Advisory", True, "{n} weeks per parent", 12, 30, "all"),
    "pension": ("Retirement age", "HR Advisory", True, "retirement at {n}", 60, 68, "all"),
    "company_car": ("Company car policy", "HR Advisory", True, "CO2 limit {n} g/km", 60, 140, "all"),
    "sick_leave": ("Sick leave", "HR Advisory", True, "certificate after {n} days", 1, 5, "all"),
    "working_hours": ("Working hours", "HR Advisory", True, "{n} hours per week", 36, 40, "all"),
    "remote_work": ("Remote work", "HR Advisory", True, "{n} remote days per week", 1, 4, "all"),
    "expense_policy": ("Expense policy", "HR Advisory", True, "claim within {n} days", 14, 60, "all"),
    "leave_carryover": ("Leave carry-over", "HR Advisory", True, "carry over {n} days", 0, 10, "all"),
    "training_budget": ("Training budget", "HR Advisory", True, "{n} EUR per year", 500, 2500, "all"),
    # Payroll Operations
    "payroll_cutoff": ("Payroll cut-off", "Payroll Operations", True, "cut-off on day {n}", 10, 25, "all"),
    "payslip_format": ("Payslip format", "Payroll Operations", True, "layout version {n}", 1, 6, "all"),
    "tax_withholding": ("Tax withholding", "Payroll Operations", True, "withholding rate {n} percent", 10, 40, "all"),
    "social_security": ("Social security filing", "Payroll Operations", True, "file by day {n}", 5, 25, "all"),
    "year_end_closing": ("Year-end closing", "Payroll Operations", True, "close on December {n}", 15, 31, "all"),
    "correction_process": ("Payroll corrections", "Payroll Operations", True, "corrections within {n} days", 3, 30, "all"),
    "bonus_payment": ("Bonus payment", "Payroll Operations", True, "paid in month {n}", 1, 12, "all"),
    # Legal & Compliance
    "gdpr_retention": ("GDPR retention", "Legal & Compliance", True, "keep for {n} years", 1, 10, "all"),
    "works_council": ("Works council", "Legal & Compliance", True, "notice period {n} days", 5, 60, "all"),
    "dpa_template": ("Data processing agreement", "Legal & Compliance", True, "template version {n}", 1, 8, "all"),
    "whistleblower": ("Whistleblower procedure", "Legal & Compliance", True, "respond within {n} days", 3, 30, "all"),
    "salary_bands": ("Salary bands", "Legal & Compliance", True, "band review every {n} months", 6, 24, "dept:HR Advisory"),
    "employment_contract": ("Employment contract template", "Legal & Compliance", True, "template version {n}", 1, 8, "dept:HR Advisory"),
    # Internationals
    "expat_payroll": ("Expat payroll", "Internationals", True, "split payroll {n} percent", 10, 90, "all"),
    "shadow_payroll": ("Shadow payroll", "Internationals", True, "report within {n} days", 5, 30, "all"),
    "cross_border_tax": ("Cross-border tax", "Internationals", True, "{n} days threshold", 30, 183, "all"),
    "posting_rules": ("Posted workers rules", "Internationals", True, "declare after {n} days", 1, 30, "all"),
    # SMB
    "smb_onboarding": ("SMB onboarding", "SMB", True, "onboarding takes {n} days", 5, 30, "all"),
    "smb_support": ("SMB support", "SMB", True, "first response within {n} hours", 2, 24, "all"),
    # Sales / CS / Marketing (scoped per country)
    "pricing_sheet": ("Pricing sheet", "Sales", True, "price list version {n}", 1, 9, "all"),
    "sales_playbook": ("Sales playbook", "Sales", True, "playbook version {n}", 1, 9, "all"),
    "client_onboarding": ("Client onboarding", "Customer Success", True, "kick-off within {n} days", 3, 20, "all"),
    "escalation_path": ("Escalation path", "Customer Success", True, "escalate after {n} hours", 2, 48, "all"),
    "campaign_playbook": ("Campaign playbook", "Marketing", True, "approval lead time {n} days", 3, 20, "all"),
    "brand_guidelines": ("Brand guidelines", "Marketing", True, "guideline version {n}", 1, 9, "all"),
    # Engineering (global topics, several variants each)
    "build_pipeline": ("Build pipeline", "Engineering", False, "pipeline timeout {n} minutes", 10, 60, "all"),
    "deployment_process": ("Deployment process", "Engineering", False, "{n} approvals required", 1, 4, "all"),
    "incident_response": ("Incident response", "Engineering", False, "page on-call within {n} minutes", 5, 30, "all"),
    "api_guidelines": ("API guidelines", "Engineering", False, "API version v{n}", 1, 5, "all"),
    "code_review": ("Code review", "Engineering", False, "{n} reviewers required", 1, 3, "all"),
    "release_calendar": ("Release calendar", "Engineering", False, "release every {n} weeks", 1, 8, "all"),
    "db_migration": ("Database migration", "Engineering", False, "freeze {n} hours before", 1, 24, "all"),
    "access_requests": ("Access requests", "Engineering", False, "access granted within {n} days", 1, 10, "all"),
}
SYSTEMS = ["Payroll Engine", "Portal", "Time Tracking", "Reporting", "Gateway", "Mobile App",
           "Data Platform", "Identity", "Billing", "Notifications"]
CLIENTS = ["Nike", "Decathlon", "Zalando", "AS Adventure", "Delhaize", "Proximus", "IKEA", "Bosch",
           "Carrefour", "Philips", "Inditex", "Lidl"]
CLIENT_TOPICS = {  # topic -> (name, format, lo, hi)
    "client_cutoff": ("Payroll cut-off agreement", "cut-off on day {n}", 10, 25),
    "client_sla": ("Service level agreement", "{n} working days to resolve", 1, 10),
    "client_contacts": ("Key contacts", "{n} named contacts", 1, 6),
    "client_escalation": ("Escalation agreement", "escalate after {n} hours", 2, 48),
}
CLIENT_NAME = {}
FIRST = {"nl": ["Sofie", "Thomas", "Laura", "Jens", "An", "Gert", "Lotte", "Wim", "Eline", "Bram", "Nele", "Koen"],
         "de": ["Anna", "Lukas", "Julia", "Felix", "Hannah", "Jonas", "Lena", "Paul", "Mia", "Max", "Clara", "Tim"],
         "ro": ["Marie", "Pierre", "Chiara", "Marco", "Lucia", "Carlos", "Elena", "Javier", "Sara", "Diego", "Ines", "Luca"],
         "sl": ["Piotr", "Katarzyna", "Jakub", "Magda", "Tomasz", "Ewa", "Pavel", "Eva", "Marek", "Zofia", "Ivan", "Petra"],
         "en": ["Emma", "James", "Sophie", "Oliver", "Niamh", "Liam", "Freya", "Noah", "Eva", "Sven", "Maja", "Nikos"]}
LAST = {"nl": ["Peeters", "Maes", "Janssens", "Willems", "Goossens", "Hermans", "Claes", "Wouters", "Mertens", "Dubois"],
        "de": ["Müller", "Schmidt", "Weber", "Fischer", "Wagner", "Becker", "Hoffmann", "Koch", "Richter", "Klein"],
        "ro": ["Garcia", "Martin", "Rossi", "Ferrari", "Lopez", "Bernard", "Moreau", "Costa", "Silva", "Esposito"],
        "sl": ["Nowak", "Kowalski", "Wiśniewski", "Novák", "Horváth", "Ivanov", "Kovač", "Popescu", "Dimitrov", "Petrov"],
        "en": ["Smith", "Taylor", "Murphy", "Andersson", "Nielsen", "Hansen", "Johansson", "Papadopoulos", "Brown", "Wilson"]}
REGION = {"nl": "nl", "fr": "ro", "pt": "ro", "es": "ro", "it": "ro", "de": "de", "da": "en", "sv": "en", "no": "en",
          "fi": "en", "el": "en", "en": "en", "hr": "sl", "pl": "sl", "cs": "sl", "sk": "sl", "hu": "sl", "bg": "sl",
          "sl": "sl", "lt": "sl", "ro": "sl"}


def _pick(rng, options, probs=None):
    return options[rng.choice(len(options), p=probs)]


def build_people(rng, n_people):
    """Countries -> departments -> teams -> persons with a REPORTS_TO hierarchy."""
    w = np.array([c[2] for c in COUNTRIES.values()], float)
    per_country = np.maximum((w / w.sum() * n_people).round().astype(int), 30)
    dshare = np.array([d[0] for d in DEPTS.values()])
    dshare = dshare / dshare.sum()
    persons, teams = [], []
    pid = 0

    def person(name_region, **kw):
        nonlocal pid
        pid += 1
        first = rng.choice(FIRST[name_region])
        last = rng.choice(LAST[name_region])
        persons.append({"person_id": f"P{pid:05d}", "name": f"{first} {last}", **kw})
        return persons[-1]["person_id"]

    for (cc, (cname, lang, _)), n_c in zip(COUNTRIES.items(), per_country):
        region = REGION[lang]
        lead = person(region, role="Country Lead", level="Lead", department="Management", team_id=f"T_{cc}_MGT",
                      country=cc, reports_to="", team_lead=False)
        teams.append({"team_id": f"T_{cc}_MGT", "name": f"{cname} Country Office", "department": "Management",
                      "country": cc, "lead_id": lead})
        counts = np.maximum((dshare * n_c).round().astype(int), 4)
        for (dept, (_, _, titles)), n_d in zip(DEPTS.items(), counts):
            head = person(region, role=f"Head of {dept}", level="Head", department=dept, team_id="", country=cc,
                          reports_to=lead, team_lead=False)
            n_teams = max(1, n_d // 10)
            sizes = np.full(n_teams, n_d // n_teams)
            sizes[: n_d % n_teams] += 1
            for ti, size in enumerate(sizes):
                tid = f"T_{cc}_{dept[:3].upper()}_{ti + 1}"
                has_lead = rng.random() < 0.85
                lead_id = ""
                if has_lead:
                    lead_id = person(region, role=f"{dept} Team Lead", level="Team Lead", department=dept, team_id=tid,
                                     country=cc, reports_to=head, team_lead=True)
                    size -= 1
                for _ in range(size):
                    lvl = _pick(rng, [l[0] for l in LEVELS], [l[1] for l in LEVELS])
                    person(region, role=f"{lvl} {rng.choice(titles)}", level=lvl, department=dept, team_id=tid,
                           country=cc, reports_to=lead_id or head, team_lead=False)
                teams.append({"team_id": tid, "name": f"{dept} {cname} {ti + 1}", "department": dept,
                              "country": cc, "lead_id": lead_id})
    p = pd.DataFrame(persons)
    p["active"] = rng.random(len(p)) > 0.10                        # 10% have left
    p.loc[p.level.isin(["Country Lead", "Lead"]), "active"] = True
    p["previous_department"] = ""
    moved = (rng.random(len(p)) < 0.04) & p.active & (p.level != "Lead")
    others = list(DEPTS)
    p.loc[moved, "previous_department"] = [rng.choice([d for d in others if d != cur]) for cur in p.department[moved]]
    p["opt_in_signals"] = rng.random(len(p)) < 0.7                 # signals are opt-in
    for c in ["team_lead"]:
        p[c] = p[c].astype(bool)
    # team heads are the department heads: fix team_id of heads
    first_team = p[p.team_id != ""].groupby(["country", "department"]).team_id.first()
    mask = p.team_id == ""
    p.loc[mask, "team_id"] = [first_team[(c, d)] for c, d in zip(p.country[mask], p.department[mask])]
    return p, pd.DataFrame(teams)


def gen(n_people=10000, n_notes=5000, seed=7):
    rng = np.random.default_rng(seed)
    persons, teams = build_people(rng, n_people)
    persons = persons.set_index("person_id", drop=False)
    team_country = teams.set_index("team_id").country
    by_dept_country = {k: g.person_id.tolist() for k, g in persons[persons.level.isin(["Junior", "Medior", "Senior", "Team Lead"])].groupby(["department", "country"])}
    dept_weight = {d: v[1] for d, v in DEPTS.items()}
    source_mix = {d: np.array(m) / sum(m) for d, m in SOURCE_MIX.items()}
    reports_to = persons.reports_to.to_dict()

    def above(pid):
        """First person above `pid` in the hierarchy who is still active (approver)."""
        cur = reports_to.get(pid, "")
        while cur and not persons.active[cur]:
            cur = reports_to.get(cur, "")
        return cur

    docs, edges = [], []
    did = 0

    def new_doc(topic, country, client, dept, value, stated_current, author, age_days, source, doc_type, text_extra=""):
        nonlocal did
        did += 1
        lm = REFERENCE_DATE - pd.Timedelta(days=int(age_days))
        created = lm - pd.Timedelta(days=int(rng.integers(0, 400)))
        no_owner = rng.random() < (0.12 if source in ("Legacy drive", "OneDrive") else 0.0 if source == "GitHub" else 0.04)  # GitHub: CODEOWNERS
        official = source in ("SharePoint", "GitHub")
        docs.append({
            "doc_id": f"D{did:05d}", "title": "", "doc_type": doc_type, "topic_id": topic, "country": country,
            "client": client, "department": dept if rng.random() > 0.05 else "", "team_id": persons.team_id[author],
            "author_id": author, "owner_id": "" if no_owner else author, "created": created.date(),
            "last_modified": lm.date(), "version": int(rng.integers(1, 6)) if official else 1,
            "source": source, "language": COUNTRIES[country][1] if country in COUNTRIES else "en",
            "key_value": value, "stated_current": stated_current, "verified": False,
            "acl": ("client:" + client) if client else TOPICS[topic][6], "text": text_extra})
        return docs[-1]

    def author_for(dept, country):
        pool = by_dept_country.get((dept, country)) or by_dept_country[(dept, "BE")]
        wts = np.array([(1.0 if not persons.team_lead[p] else 0.6) for p in pool])
        return rng.choice(pool, p=wts / wts.sum())

    def age_sample():
        return int(min(rng.exponential(650) + 5, 2500))

    def make_group(topic, country, client, dept, fmt, lo, hi, doc_type, label):
        truth_n = int(rng.integers(lo, hi + 1))
        n_docs = int(rng.choice([2, 3, 4, 5, 6, 8], p=[0.15, 0.2, 0.25, 0.2, 0.12, 0.08]))
        group = []
        for _ in range(n_docs):
            age = age_sample()
            author = author_for(dept, country if country in COUNTRIES else "BE")
            p_out = 1 / (1 + np.exp(-(age - 900) / 350))
            p_out = min(0.8, max(0.06, p_out + (0.25 if not persons.active[author] else 0)))
            current = rng.random() > p_out
            n = truth_n if current else int(np.clip(truth_n + rng.choice([-1, 1]) * rng.integers(1, 5), lo, hi + 4))
            if n == truth_n:
                current = True
            src = _pick(rng, SOURCES, source_mix[dept] if dept in source_mix else None)
            if age > 1500 and rng.random() < 0.5:
                src = "Legacy drive"
            d = new_doc(topic, country, client, dept, fmt.format(n=n), bool(current), author, age, src, doc_type,
                        f"{label}. Rule: {fmt.format(n=n)}.")
            ctry = "Europe" if country == "ALL" else COUNTRIES.get(country, ("", "", 0))[0]
            d["title"] = f"{label} ({ctry or country}) v{d['version']}" if not client else f"{label}: {CLIENT_NAME.get(client, client)} ({ctry}) v{d['version']}"
            group.append(d)
        return group

    groups = []
    for topic, (name, dept, scoped, fmt, lo, hi, acl) in TOPICS.items():
        if scoped:
            for cc in COUNTRIES:
                groups.append(make_group(topic, cc, "", dept, fmt, lo, hi, "policy", name))
        else:
            for s in SYSTEMS[:8]:
                g = make_group(topic, "ALL", "", dept, fmt, lo, hi, "technical", f"{name} {s}")
                for d in g:
                    d["title"] = f"{name}: {s} v{d['version']}"
                groups.append(g)
    # client-specific agreements (served in 3 countries each)
    cids = {c: f"C{i + 1:02d}" for i, c in enumerate(CLIENTS)}
    CLIENT_NAME.update({v: k for k, v in cids.items()})
    clist = list(COUNTRIES)
    for c, cid in cids.items():
        ctrs = ["BE", "NL", "ES"] if cid == "C01" else list(rng.choice(clist[:12], 3, replace=False))
        for t, (name, fmt, lo, hi) in CLIENT_TOPICS.items():
            for cc in ctrs:
                g = make_group(t, cc, cid, "Customer Success", fmt, lo, hi, "customer", name)
                for d in g:
                    d["topic_id"] = t
                    d["acl"] = "client:" + cid
                groups.append(g)

    docs_df_topics = {t: v[0] for t, v in TOPICS.items()}
    docs_df_topics.update({t: v[0] for t, v in CLIENT_TOPICS.items()})

    # ---------- notes: meeting notes, personal notes, drafts (no stated value) ----------
    note_dept = list(DEPTS)
    wts = np.array([DEPTS[d][0] * DEPTS[d][1] for d in note_dept])
    wts = wts / wts.sum()
    note_docs = []
    for _ in range(n_notes):
        dept = _pick(rng, note_dept, wts)
        cc = _pick(rng, list(COUNTRIES), np.array([c[2] for c in COUNTRIES.values()]) / sum(c[2] for c in COUNTRIES.values()))
        author = author_for(dept, cc)
        src = _pick(rng, ["Teams", "OneDrive", "Notion", "SharePoint", "Legacy drive"], [0.45, 0.2, 0.15, 0.12, 0.08])
        if dept == "Engineering" and rng.random() < 0.4:
            src = "GitHub"
        topic = rng.choice([t for t, v in TOPICS.items() if v[1] == dept] or list(TOPICS))
        client = ""
        if dept in ("Customer Success", "Sales", "Internationals") and rng.random() < 0.5:
            client = cids[rng.choice(CLIENTS)]
        kind = {"Teams": "meeting notes", "OneDrive": "draft", "Notion": "personal notes", "GitHub": "README"}.get(src, "working document")
        d = new_doc(topic, cc, client, dept, "", True, author, age_sample(), src, kind,
                    f"{kind.capitalize()} about {TOPICS[topic][0]}.")
        d["title"] = f"{TOPICS[topic][0]}: {kind} ({cc})"
        note_docs.append(d)

    docs_df = pd.DataFrame(docs)

    # ---------- verification, reviewers, approvals ----------
    for d in docs:
        official = d["source"] in ("SharePoint", "GitHub")
        age = (REFERENCE_DATE - pd.Timestamp(d["last_modified"])).days
        author = d["author_id"]
        if d["doc_type"] != "meeting notes" and official and rng.random() < (0.55 if age < 700 else 0.2):
            ap = above(author)
            if ap:
                d["verified"] = True
                edges.append((ap, d["doc_id"], "APPROVED", 1))
        for r in range(int(rng.choice([0, 1, 2], p=[0.45, 0.4, 0.15]) if official else int(rng.random() < 0.08))):
            pool = by_dept_country.get((d["department"] or persons.department[author], persons.country[author]), [])
            if pool:
                rv = rng.choice(pool)
                if rv != author:
                    edges.append((rv, d["doc_id"], "REVIEWS", 1))
        edges.append((author, d["doc_id"], "AUTHORED", 1))
        edges.append((d["doc_id"], d["topic_id"], "ABOUT", 1))
        if d["client"]:
            edges.append((d["doc_id"], d["client"], "ABOUT", 1))
        edges.append((d["doc_id"], d["source"], "STORED_IN", 1))
        edges.append((d["doc_id"], d["team_id"], "OWNED_BY", 1))
        # team leads often appear on documents they did not write
        if rng.random() < 0.35:
            tl = teams.set_index("team_id").lead_id.get(d["team_id"], "")
            if tl and tl != author:
                edges.append((tl, d["doc_id"], "LISTED_AS", 1))

    # ---------- supersedes (newest in a group replaces some older ones) ----------
    for g in groups:
        g.sort(key=lambda x: x["last_modified"], reverse=True)
        for old in g[1:]:
            if g[0]["stated_current"] and not old["stated_current"] and rng.random() < 0.6:
                edges.append((g[0]["doc_id"], old["doc_id"], "SUPERSEDES", 1))

    # ---------- links: preferential attachment toward OLD documents ----------
    by_topic = {}
    for d in docs:
        by_topic.setdefault(d["topic_id"], []).append(d)
    for t, ds in by_topic.items():
        age = np.array([(REFERENCE_DATE - pd.Timestamp(d["last_modified"])).days + 150 for d in ds], float)
        p = age / age.sum()
        for d in ds:
            for _ in range(rng.poisson(1.4)):
                tgt = ds[rng.choice(len(ds), p=p)]
                if tgt["doc_id"] != d["doc_id"]:
                    edges.append((d["doc_id"], tgt["doc_id"], "LINKS_TO", 1))

    # ---------- signals from daily work ----------
    pers_ids = persons.person_id.to_numpy()
    active_opt = persons[persons.active & persons.opt_in_signals]
    # meetings: attendees of Teams notes
    for d in docs:
        if d["source"] == "Teams":
            pool = by_dept_country.get((persons.department[d["author_id"]], persons.country[d["author_id"]]), [])
            for a in rng.choice(pool, size=min(len(pool), int(rng.integers(3, 9))), replace=False) if pool else []:
                if persons.opt_in_signals[a]:
                    edges.append((a, d["doc_id"], "ATTENDED", 1))
        if d["source"] == "GitHub":
            for a in set(rng.choice(by_dept_country.get(("Engineering", persons.country[d["author_id"]]), [d["author_id"]]), 2)):
                edges.append((a, d["doc_id"], "COMMITTED", int(rng.integers(1, 40))))
    topic_ids = list(TOPICS)
    for pid_ in active_opt.person_id:
        dept = persons.department[pid_]
        own = [t for t, v in TOPICS.items() if v[1] == dept] or topic_ids
        for t in rng.choice(own, size=min(len(own), int(rng.integers(0, 4))), replace=False):
            edges.append((pid_, t, "COMPLETED", 1))
        if dept in ("Customer Success", "Sales", "Internationals", "SMB") and rng.random() < 0.7:
            for c in rng.choice(list(cids.values()), size=int(rng.integers(1, 3)), replace=False):
                edges.append((pid_, c, "INTERACTED_WITH", int(rng.integers(1, 60))))

    # ---------- simulated feedback (colleagues flag wrong documents) ----------
    fb = []
    for d in docs:
        views = int(rng.integers(5, 120))
        rate = (0.12 if d["stated_current"] else 0.55) + rng.normal(0, 0.07)
        if not persons.active[d["owner_id"] or d["author_id"]]:       # colleagues distrust documents nobody maintains
            rate += 0.3
        rate = float(np.clip(rate, 0, 1))
        flags = int(rng.binomial(views, rate))
        fb.append((d["doc_id"], views, flags, round(flags / views, 3), int(flags / views >= 0.35)))
    feedback = pd.DataFrame(fb, columns=["doc_id", "views", "flags_wrong", "flag_rate", "unreliable"])

    docs_df = pd.DataFrame(docs)
    truth = docs_df[["doc_id", "stated_current"]].rename(columns={"stated_current": "states_current_value"})
    docs_df = docs_df.drop(columns=["stated_current"])
    topics_df = pd.DataFrame([{"topic_id": t, "name": v[0], "department": v[1], "scoped": v[2]} for t, v in TOPICS.items()]
                             + [{"topic_id": t, "name": v[0], "department": "Customer Success", "scoped": True}
                                for t, v in CLIENT_TOPICS.items()])
    clients_df = pd.DataFrame([{"client_id": cid, "name": c} for c, cid in cids.items()])
    countries_df = pd.DataFrame([{"country": k, "name": v[0], "language": v[1]} for k, v in COUNTRIES.items()])
    edges_df = pd.DataFrame(edges, columns=["source", "target", "type", "weight"])
    return dict(persons=persons.reset_index(drop=True), teams=teams, documents=docs_df, edges=edges_df,
                feedback=feedback, ground_truth=truth, topics=topics_df, clients=clients_df, countries=countries_df)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--people", type=int, default=10000)
    ap.add_argument("--notes", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    DATA_DIR.mkdir(exist_ok=True)
    tables = gen(a.people, a.notes, a.seed)
    for name, df in tables.items():
        df.to_csv(DATA_DIR / f"{name}.csv", index=False)
        print(f"{name:12s} {len(df):>8,d} rows")


if __name__ == "__main__":
    main()
