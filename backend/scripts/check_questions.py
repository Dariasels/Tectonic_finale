"""Run curated and generated questions through the engine and report what works.

Usage: .venv/bin/python -m scripts.check_questions   (writes ../docs/QUESTION_CHECK.md)
"""
import statistics
import time
from pathlib import Path

from engine import TrustEngine
from engine.queries import SYNONYMS
from engine.questions import CURATED, persona_ids

OUT = Path(__file__).resolve().parents[2] / "docs" / "QUESTION_CHECK.md"


def check_curated(e, ids):
    rows, fails = [], []
    for cat, text, who, exp in CURATED:
        uid = ids[who]
        ucountry = e.persons.country[uid]
        problems = []
        try:
            t0 = time.time()
            r = e.search(text, uid)
            ms = (time.time() - t0) * 1000
        except Exception as ex:                      # a crash is always a failure
            rows.append((cat, text, who, "-", "-", "-", f"CRASH {ex!r}"))
            fails.append((text, who, f"crash {ex!r}"))
            continue
        it = r["intent"]
        for k in ("topic", "client"):
            if k in exp and it[k] != exp[k]:
                problems.append(f"{k}: got {it[k]}, expected {exp[k]}")
        if "country" in exp:
            want = ucountry if exp["country"] == "user" else exp["country"]
            if it["country"] != want:
                problems.append(f"country: got {it['country']}, expected {want}")
        n = len(r["results"])
        if "results" in exp:
            if exp["results"] == 0 and n != 0:
                problems.append(f"expected no results, got {n}")
            if exp["results"] > 0 and n < exp["results"]:
                problems.append(f"expected >= {exp['results']} results, got {n}")
        if exp.get("banner") and not r["banner"]:
            problems.append("expected a conflict banner")
        if exp.get("ambiguous") and not r["did_you_mean"]:
            problems.append("expected 'did you mean' suggestions")
        if exp.get("experts") and not r["experts"]:
            problems.append("expected experts")
        if exp.get("ask_expert") and not r["ask_expert"]:
            problems.append("expected 'ask an expert'")
        for x in r["results"]:                       # safety checks on every question
            d = e.docs.loc[x["doc_id"]]
            if not e.can_see(uid, d):
                problems.append(f"ACL LEAK {x['doc_id']}")
            if not 0 <= x["trust"] <= 100:
                problems.append(f"score out of range {x['doc_id']}")
        if it["country"] and r["results"] and not r["results"][0]["in_scope"] and it["mode"] == "topic":
            if any(x["in_scope"] for x in r["results"]):
                problems.append("an out-of-scope document ranks first")
        top = r["results"][0] if r["results"] else None
        rows.append((cat, text, who, f"{it['topic']}/{it['country']}/{it['client']}", n,
                     f"{top['trust']:.0f} {top['badge']}" if top else "-", "OK" if not problems else "; ".join(problems)))
        if problems:
            fails.append((text, who, "; ".join(problems)))
    return rows, fails


def check_generated(e, uid):
    """One question per (topic, country): is it understood, and is the top answer a correct document?"""
    scoped = [t for t in e.topics.index if e.topics.scoped[t] and not t.startswith("client_")]
    ok_en = ok_syn = n_syn = 0
    mixed = correct = total = 0
    lat = []
    bad = []
    for t in scoped:
        name = e.topics.name[t]
        syn = SYNONYMS.get(t, [None])[0]
        for cc, crow in e.countries.iterrows():
            qs = [(f"{name} in {crow['name']}", "en")] + ([(f"{syn} in {crow['name']}", "syn")] if syn else [])
            for q, kind in qs:
                t0 = time.time()
                r = e.search(q, uid)
                lat.append((time.time() - t0) * 1000)
                good = r["intent"]["topic"] == t and r["intent"]["country"] == cc
                if kind == "en":
                    ok_en += good
                else:
                    n_syn += 1
                    ok_syn += good
                if not good and len(bad) < 15:
                    bad.append((q, r["intent"]["topic"], r["intent"]["country"], t, cc))
                if kind == "en":
                    grp = e.docs[(e.docs.topic_id == t) & (e.docs.country == cc) & (e.docs.client == "") & (e.docs.key_value != "")]
                    truth = e.truth[grp.index]
                    if 0 < truth.sum() < len(grp) and r["results"]:       # only groups with both correct and outdated documents
                        mixed += 1
                        correct += bool(e.truth.get(r["results"][0]["doc_id"], False))
    n_en = len(scoped) * len(e.countries)
    return {"questions": n_en + n_syn, "en_parse": ok_en / n_en, "syn_parse": ok_syn / max(n_syn, 1),
            "mixed_groups": mixed, "top1_correct": correct / max(mixed, 1),
            "p50_ms": statistics.median(lat), "p95_ms": sorted(lat)[int(len(lat) * 0.95)], "bad": bad}


def main():
    e = TrustEngine()
    ids = persona_ids(e)
    rows, fails = check_curated(e, ids)
    gen = check_generated(e, ids["hr"])
    passed = len(rows) - len(fails)
    lines = ["# Question check", "",
             "Run with `cd backend && .venv/bin/python -m scripts.check_questions`. All data is simulated.", "",
             f"## Summary", "",
             f"- Curated questions: **{passed} of {len(rows)} pass** (understood correctly, right access, sensible result).",
             f"- Generated questions: {gen['questions']} (every country-specific topic in every country, English and a local-language synonym).",
             f"  - English phrasing understood (topic and country): **{gen['en_parse']:.1%}**",
             f"  - Local-language synonym understood: **{gen['syn_parse']:.1%}**",
             f"  - Top answer is a correct document (hidden ground truth, {gen['mixed_groups']} groups that contain both correct and outdated documents): **{gen['top1_correct']:.1%}**",
             f"  - Search time: median {gen['p50_ms']:.0f} ms, 95th percentile {gen['p95_ms']:.0f} ms", ""]
    if fails:
        lines += ["## Failures", ""] + [f"- `{t}` ({w}): {p}" for t, w, p in fails] + [""]
    if gen["bad"]:
        lines += ["## Generated questions that were not understood (first 15)", ""] + \
                 [f"- `{q}`: got {gt}/{gc}, expected {t}/{c}" for q, gt, gc, t, c in gen["bad"]] + [""]
    lines += ["## Curated questions", "", "| Category | Question | As | Understood (topic/country/customer) | Results | Top | Verdict |",
              "|---|---|---|---|---|---|---|"]
    lines += [f"| {c} | {q or '(empty)'} | {w} | {u} | {n} | {t} | {v} |" for c, q, w, u, n, t, v in rows]
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:16]))
    for t, w, p in fails:
        print("FAIL", repr(t), w, p)


if __name__ == "__main__":
    main()
