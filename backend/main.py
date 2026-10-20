"""Tectonic API: a trust layer on top of Teams, SharePoint, OneDrive, Notion, GitHub and legacy drives."""
import threading
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from engine import TrustEngine
from engine.core import SRC_KEY

state = {"engine": None}
UID = Query(..., min_length=3, max_length=12, pattern=r"^P\d{5}$")


@asynccontextmanager
async def lifespan(app):
    state["engine"] = TrustEngine()
    yield


app = FastAPI(title="Tectonic API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])


def eng():
    return state["engine"]


def call(fn, *a, **kw):
    """Map engine errors to HTTP errors."""
    try:
        return fn(*a, **kw)
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'"))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


class NewDoc(BaseModel):
    user_id: str = Field(pattern=r"^P\d{5}$")
    title: str = Field(max_length=200)
    text: str = Field(min_length=1, max_length=5000)
    source: str = "SharePoint"
    topic_id: Optional[str] = Field(default=None, max_length=40)
    country: Optional[str] = Field(default=None, max_length=3)
    client: Optional[str] = Field(default=None, max_length=4)
    key_value: str = Field(default="", max_length=100)
    doc_type: str = Field(default="policy", max_length=20)
    template: bool = True


class EditDoc(BaseModel):
    user_id: str = Field(pattern=r"^P\d{5}$")
    text: Optional[str] = Field(default=None, max_length=5000)
    key_value: Optional[str] = Field(default=None, max_length=100)


class Vote(BaseModel):
    user_id: str = Field(pattern=r"^P\d{5}$")
    kind: str = Field(pattern="^(confirm|flag)$")


class Decision(BaseModel):
    user_id: str = Field(pattern=r"^P\d{5}$")
    decision: str = Field(pattern="^(approve|reject)$")


class Resolution(BaseModel):
    user_id: str = Field(pattern=r"^P\d{5}$")
    topic: Optional[str] = Field(default=None, max_length=40)
    country: Optional[str] = Field(default=None, max_length=3)
    client: Optional[str] = Field(default=None, max_length=4)
    person_id: Optional[str] = Field(default=None, pattern=r"^P\d{5}$")
    doc_id: Optional[str] = Field(default=None, max_length=10)


class Policy(BaseModel):
    auto: Optional[bool] = None
    min_new_docs: Optional[int] = Field(default=None, ge=1, le=10000)
    max_days: Optional[int] = Field(default=None, ge=1, le=90)
    min_gap_hours: Optional[int] = Field(default=None, ge=0, le=168)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/api/health")
def health():
    return {"status": "ok", "ready": eng() is not None}


@app.get("/api/meta")
def meta():
    e = eng()
    return {"topics": [{"topic_id": i, "name": r["name"], "department": r.department} for i, r in e.topics.iterrows()],
            "clients": [{"client_id": i, "name": r["name"]} for i, r in e.clients.iterrows()],
            "countries": [{"country": i, "name": r["name"], "language": r.language} for i, r in e.countries.iterrows()],
            "sources": list(SRC_KEY)}


@app.get("/api/users")
def users():
    return eng().demo_users()


@app.get("/api/search")
def search(q: str = Query("", max_length=300), user_id: str = UID, country: Optional[str] = Query(None, max_length=3),
           client: Optional[str] = Query(None, max_length=4), limit: int = Query(10, ge=1, le=30)):
    return call(eng().search, q, user_id, country, client, limit)


@app.get("/api/documents/{doc_id}")
def document(doc_id: str, user_id: str = UID):
    e = eng()
    if doc_id not in e.docs.index:
        raise HTTPException(404, "unknown document")
    d = e.docs.loc[doc_id]
    if not e.can_see(user_id, d):
        raise HTTPException(403, "no access to this document")
    return e.doc_json(d, detail=True)


@app.post("/api/documents")
def add_document(b: NewDoc):
    e = eng()
    payload = b.model_dump()
    payload["template"] = {} if b.template else None
    return call(e.ingest, payload, b.user_id)


@app.post("/api/documents/{doc_id}/edit")
def edit_document(doc_id: str, b: EditDoc):
    return call(eng().edit, doc_id, b.user_id, b.text, b.key_value)


@app.post("/api/documents/{doc_id}/vote")
def vote_document(doc_id: str, b: Vote):
    return call(eng().vote, doc_id, b.user_id, b.kind)


@app.get("/api/approvals")
def approvals(user_id: str = UID, status: str = Query("pending", pattern="^(pending|approved|rejected)$")):
    return eng().list_approvals(user_id, status)


@app.post("/api/approvals/{approval_id}/decision")
def decide(approval_id: str, b: Decision):
    return call(eng().decide, approval_id, b.user_id, b.decision)


@app.post("/api/resolutions")
def resolve(b: Resolution):
    return call(eng().resolve, b.user_id, b.topic, b.country, b.client, b.person_id, b.doc_id)


@app.get("/api/experts")
def experts(topic: Optional[str] = Query(None, max_length=40), client: Optional[str] = Query(None, max_length=4),
            country: Optional[str] = Query(None, max_length=3)):
    key = f"client:{client}" if client else f"topic:{topic}"
    return eng().experts_for(key, country)


@app.get("/api/org/overview")
def org_overview():
    return eng().org_overview()


@app.get("/api/org/country/{cc}")
def org_country(cc: str):
    return call(eng().org_country, cc.upper())


@app.get("/api/org/department/{cc}/{dept}")
def org_department(cc: str, dept: str):
    return call(eng().org_department, cc.upper(), dept)


@app.get("/api/org/team/{team_id}")
def org_team(team_id: str):
    return call(eng().org_team, team_id)


@app.get("/api/risks")
def risks(country: Optional[str] = Query(None, max_length=3)):
    return eng().risks(country)


@app.get("/api/model/status")
def model_status():
    return eng().retrain_status()


@app.post("/api/model/retrain")
def model_retrain():
    return eng().retrain("manual")


@app.post("/api/model/settings")
def model_settings(b: Policy):
    return eng().set_policy(**b.model_dump())


@app.get("/api/scale")
def scale():
    e = eng()
    ms = e.ingest_ms
    return {"people": int(len(e.persons)), "teams": int(len(e.teams)), "countries": int(len(e.countries)),
            "documents": int(len(e.docs)), "edges": int(len(e.edges)), "sources": list(SRC_KEY),
            "full_rebuild_seconds": e.stats["full_rebuild_s"],
            "last_ingest_ms": e.stats.get("last_ingest_ms"),
            "avg_ingest_ms": round(sum(ms) / len(ms), 1) if ms else None,
            "speedup": round(e.stats["full_rebuild_s"] * 1000 / e.stats["last_ingest_ms"]) if e.stats.get("last_ingest_ms") else None,
            "model_auc_cv": round(e.cv_auc, 3), "note": "All data is simulated."}


@app.get("/api/demo/questions")
def demo_questions():
    """Mock questions per category, each with the persona that should ask it."""
    from engine.questions import CURATED
    e = eng()
    labels = {u["label"].split(",")[0].split(" ")[0].lower(): u for u in e.demo_users()}
    who = {"es": "Sales", "hr": "HR", "dev": "Back-end", "pay": "Payroll", "lead": "Country"}
    out = []
    for cat, text, w, exp in CURATED:
        if not text or "DROP TABLE" in text or "<script>" in text:
            continue
        u = labels.get(who[w].lower())
        out.append({"category": cat, "text": text, "persona": u["person_id"] if u else None,
                    "persona_label": u["label"] if u else None})
    return out


@app.get("/api/demo/samples")
def demo_samples():
    e = eng()
    h = e.heroes
    return [
        {"name": "Conflicting update of a verified policy (needs approval)", "user_id": h["hr_senior"],
         "body": {"user_id": h["hr_senior"], "title": "Parental leave Belgium (update)", "source": "SharePoint",
                  "topic_id": "parental_leave", "country": "BE", "key_value": "18 weeks per parent",
                  "text": "Parental leave. Rule: 18 weeks per parent. Proposed update."}},
        {"name": "Duplicate of a known document (nothing added)", "user_id": h["hr_medior"],
         "body": {"user_id": h["hr_medior"], "title": "Parental leave policy Belgium", "source": "OneDrive",
                  "topic_id": "parental_leave", "country": "BE", "key_value": "17 weeks per parent",
                  "text": "Parental leave. Rule: 17 weeks per parent. Valid from 1 September 2026."}},
        {"name": "No topic given: auto-categorised", "user_id": h["hr_junior"],
         "body": {"user_id": h["hr_junior"], "title": "New lease rules", "source": "Teams", "country": "BE",
                  "key_value": "CO2 limit 95 g/km", "text": "Company car policy. Rule: CO2 limit 95 g/km."}},
        {"name": "New customer document, nothing contradicts it (published automatically)", "user_id": h["be_cs"],
         "body": {"user_id": h["be_cs"], "title": "Nike payroll cut-off agreement 2026", "source": "SharePoint",
                  "topic_id": "client_cutoff", "country": "DE", "client": "C01", "key_value": "cut-off on day 14",
                  "text": "Payroll cut-off agreement. Rule: cut-off on day 14. New German entity."}},
    ]


@app.post("/api/demo/reset")
def demo_reset():
    def run():
        state["engine"] = TrustEngine()
    threading.Thread(target=run, daemon=True).start()
    return {"status": "resetting"}
