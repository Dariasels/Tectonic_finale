"""Tectonic API: a trust layer on top of Teams, SharePoint, OneDrive, Notion, GitHub and legacy drives."""
import threading
from contextlib import asynccontextmanager
from typing import Optional, Union

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


class EditDoc(BaseModel):
    user_id: str = Field(pattern=r"^P\d{5}$")
    text: Optional[str] = Field(default=None, max_length=5000)
    key_value: Optional[str] = Field(default=None, max_length=100)


class Vote(BaseModel):
    user_id: str = Field(pattern=r"^P\d{5}$")
    kind: str = Field(pattern="^(confirm|flag|none)$")


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


class ProfileIn(BaseModel):
    user_id: str = Field(pattern=r"^P\d{5}$")
    personal_tools: Optional[list[str]] = Field(default=None, max_length=6)
    team_tools: Optional[list[str]] = Field(default=None, max_length=6)
    signals: Optional[dict[str, bool]] = None
    answers: Optional[dict[str, Union[str, list[str]]]] = None      # optional; several answers per question are allowed
    connections: Optional[list[str]] = Field(default=None, max_length=5)


class DocEvent(BaseModel):
    """A file was saved in a connected tool. Only the link and metadata are sent, never the document."""
    user_id: str = Field(pattern=r"^P\d{5}$")
    source: str = Field(max_length=20)
    title: str = Field(max_length=200)
    link: Optional[str] = Field(default=None, max_length=300, pattern=r"^(https?|file)://")
    path: Optional[str] = Field(default=None, max_length=300)
    extract: Optional[str] = Field(default=None, max_length=300)      # one fact read at the source, e.g. "Rule: 17 weeks"
    key_value: str = Field(default="", max_length=100)
    topic_id: Optional[str] = Field(default=None, max_length=40)
    country: Optional[str] = Field(default=None, max_length=3)
    client: Optional[str] = Field(default=None, max_length=4)


class MeetingEvent(BaseModel):
    user_id: str = Field(pattern=r"^P\d{5}$")
    title: str = Field(max_length=200)
    attendees: list[str] = Field(default_factory=list, max_length=40)
    link: Optional[str] = Field(default=None, max_length=300, pattern=r"^https?://")


class Signup(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    country: str = Field(max_length=3)
    department: str = Field(max_length=40)
    level: str = Field(max_length=12)
    team_id: Optional[str] = Field(default=None, max_length=24)
    new_team_name: Optional[str] = Field(default=None, max_length=60)
    team_tools: Optional[list[str]] = Field(default=None, max_length=6)


class Actor(BaseModel):
    user_id: str = Field(pattern=r"^P\d{5}$")


class Policy(BaseModel):
    user_id: str = Field(pattern=r"^P\d{5}$")
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


@app.get("/api/org/departments")
def org_departments():
    return eng().org_departments()


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
def model_status(user_id: Optional[str] = Query(None, pattern=r"^P\d{5}$")):
    return {**eng().retrain_status(), "can_retrain": bool(user_id and eng().can_retrain(user_id)),
            "who_can_retrain": "Higher management (country leads, department heads) and the system admin."}


@app.post("/api/model/retrain")
def model_retrain(b: Actor):
    if not eng().can_retrain(b.user_id):
        raise HTTPException(403, "only higher management and the system admin can retrain the model")
    return eng().retrain("manual")


@app.post("/api/model/settings")
def model_settings(b: Policy):
    return call(eng().set_policy, **b.model_dump())


@app.get("/api/validation")
def validation():
    return eng().validation()


@app.get("/api/people/search")
def people_search(q: str = Query("", max_length=60)):
    return eng().search_people(q)


@app.get("/api/signup/options")
def signup_options(country: str = Query(..., max_length=3), department: str = Query(..., max_length=40)):
    return call(eng().signup_options, country.upper(), department)


@app.post("/api/signup")
def signup(b: Signup):
    return call(eng().signup, b.name, b.country.upper(), b.department, b.level, b.team_id, b.new_team_name, b.team_tools)


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


@app.get("/api/profile")
def get_profile(user_id: str = UID):
    return call(eng().profile, user_id)


@app.post("/api/profile")
def post_profile(b: ProfileIn):
    return call(eng().set_profile, b.user_id, b.personal_tools, b.signals, b.team_tools, b.answers, b.connections)


@app.get("/api/auth/providers")
def auth_providers():
    """Accounts that can be linked, with what is read and what never is (shown on the consent screen).
    The OAuth step itself is simulated in this proof of concept."""
    from engine.tools import PROVIDERS
    return [{"provider": k, "label": v["label"], "reads": v["reads"], "never": v["never"], "mode": "simulated"}
            for k, v in PROVIDERS.items()]


@app.get("/api/tools/status")
def tools_status(user_id: str = UID):
    return call(eng().tools_status, user_id)


@app.post("/api/events/document")
def document_event(b: DocEvent):
    """Simulated webhook from a connected tool: link and metadata are captured and scored immediately."""
    payload = b.model_dump(exclude={"user_id"})
    return call(eng().ingest_event, b.user_id, payload)


@app.post("/api/events/meeting")
def meeting_event(b: MeetingEvent):
    """Simulated webhook: a meeting was planned in Teams. The title is dissected; attendance becomes expertise signals."""
    return call(eng().ingest_meeting, b.user_id, b.model_dump(exclude={"user_id"}))


@app.get("/api/events/recent")
def events_recent():
    return eng().recent_events()


@app.get("/api/team/members")
def team_members(user_id: str = UID):
    return call(eng().team_members, user_id)


@app.get("/api/documents/{doc_id}/metadata")
def document_metadata(doc_id: str, user_id: str = UID):
    e = eng()
    if doc_id not in e.docs.index:
        raise HTTPException(404, "unknown document")
    if not e.can_see(user_id, e.docs.loc[doc_id]):
        raise HTTPException(403, "no access to this document")
    return e.doc_metadata(doc_id)


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


@app.get("/api/demo/presets")
def demo_presets():
    """Ready-made events for the demo. In production the tools send these themselves."""
    h = eng().heroes
    docs = [
        {"name": "Conflicting update saved in SharePoint (needs approval)", "user_id": h["hr_senior"],
         "body": {"user_id": h["hr_senior"], "source": "SharePoint", "title": "Parental leave Belgium (update)",
                  "path": "/sites/hr-belgium/Policies/Parental leave Belgium 2026 v5.docx", "key_value": "18 weeks per parent",
                  "extract": "Parental leave. Rule: 18 weeks per parent. Proposed update."}},
        {"name": "Same file saved again (duplicate, nothing added)", "user_id": h["hr_medior"],
         "body": {"user_id": h["hr_medior"], "source": "OneDrive", "title": "Parental leave policy Belgium",
                  "path": "/personal/hr/Parental leave policy Belgium.docx", "key_value": "17 weeks per parent",
                  "extract": "Parental leave. Rule: 17 weeks per parent. Valid from 1 September 2026."}},
        {"name": "File in a Teams channel: topic found from the title", "user_id": h["hr_junior"],
         "body": {"user_id": h["hr_junior"], "source": "Teams", "title": "New company car lease rules Belgium",
                  "path": "General/Files/Company car/lease rules.docx", "key_value": "CO2 limit 95 g/km",
                  "extract": "Company car policy. Rule: CO2 limit 95 g/km."}},
        {"name": "Customer file, nothing contradicts it (published automatically)", "user_id": h["be_cs"],
         "body": {"user_id": h["be_cs"], "source": "SharePoint", "title": "Nike payroll cut-off agreement Germany",
                  "path": "/sites/customer-success/Nike/Payroll cut-off agreement.docx", "country": "DE", "client": "C01",
                  "topic_id": "client_cutoff", "key_value": "cut-off on day 14",
                  "extract": "Payroll cut-off agreement. Rule: cut-off on day 14. New German entity."}},
    ]
    meetings = [
        {"name": "Nike payroll cut-off review with the Belgian team", "user_id": h["be_cs"],
         "body": {"user_id": h["be_cs"], "title": "Nike payroll cut-off review with Belgium team"}},
        {"name": "Weekly build pipeline sync", "user_id": h["hr_senior"],
         "body": {"user_id": h["hr_senior"], "title": "Weekly build pipeline sync"}},
        {"name": "Private 1:1 (nothing recognised, nothing stored)", "user_id": h["hr_senior"],
         "body": {"user_id": h["hr_senior"], "title": "1:1 catch-up"}},
    ]
    return {"documents": docs, "meetings": meetings}


@app.post("/api/demo/reset")
def demo_reset():
    def run():
        state["engine"] = TrustEngine()
    threading.Thread(target=run, daemon=True).start()
    return {"status": "resetting"}
