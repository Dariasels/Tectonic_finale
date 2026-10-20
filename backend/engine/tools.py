"""Connected tools, personal preferences and the document-created event (simulated webhook)."""
import re
import time

import pandas as pd

from .seed_org import DEPTS

SOURCES = ["SharePoint", "Teams", "OneDrive", "Notion", "GitHub", "Legacy drive"]
OFFICIAL = {"SharePoint", "GitHub"}
PERSONAL = ["OneDrive", "Notion"]
SIGNALS = {"meetings": "Meeting titles and agenda (Teams)", "commits": "GitHub activity",
           "trainings": "Completed trainings", "customers": "Customer interactions"}
TOOL_NOTE = {"SharePoint": "official, versioned", "Teams": "meetings and chat", "OneDrive": "personal files",
             "Notion": "personal wiki", "GitHub": "code and docs, reviewed", "Legacy drive": "old shared and local drives"}
ANSWER_KEYS = {"find": ["ask a colleague", "search in Teams", "search SharePoint", "I do not know where to look"],
               "frequency": ["daily", "weekly", "monthly", "rarely"],
               "templates": ["yes, fixed templates", "some", "no"],
               "versions": ["file name", "folder", "ask someone", "I do not know"]}
LEAD_LEVELS = ("Team Lead", "Head", "Lead")

# Accounts a person can link. `reads` and `never` are shown on the consent screen (one source of truth).
PROVIDERS = {
    "GitHub": {"label": "GitHub", "signal": "commits", "personal_tool": None,
               "reads": ["Which repositories and folders you work in", "Commit counts and dates", "Pull-request reviews you did", "CODEOWNERS entries"],
               "never": ["The code itself"]},
    "Teams": {"label": "Microsoft Teams", "signal": "meetings", "personal_tool": None,
              "reads": ["Titles and times of meetings you plan or attend", "Links to files saved in channel folders"],
              "never": ["Chat messages", "Meeting recordings", "File contents"]},
    "Notion": {"label": "Notion", "signal": None, "personal_tool": "Notion",
               "reads": ["Titles, owners and edit dates of your pages, as links"],
               "never": ["Page contents"]},
}


def make_link(source, team, doc_id, author=""):
    """Fake but realistic link into the source tool (the document itself is never copied)."""
    slug = "".join(c if c.isalnum() else "-" for c in team.lower()).strip("-") or "team"
    me = "".join(c if c.isalnum() else "." for c in author.lower()).strip(".")
    return {"SharePoint": f"https://sdworx.sharepoint.example/sites/{slug}/Shared/{doc_id}",
            "Teams": f"https://teams.example/l/file/{doc_id}?team={slug}",
            "OneDrive": f"https://sdworx-my.sharepoint.example/personal/{me}/{doc_id}",
            "Notion": f"https://notion.example/sdworx/{doc_id}",
            "GitHub": f"https://github.example/sdworx/{slug}/blob/main/{doc_id}.md",
            "Legacy drive": f"file://legacy-drive/{slug}/{doc_id}"}[source]


FOLDER_OF_TYPE = {"policy": "Policies", "manual": "Manuals", "technical": "Technical docs", "customer": "Customers",
                  "meeting notes": "Meeting notes", "meeting": "Meeting notes", "draft": "Drafts", "personal notes": "Personal notes",
                  "README": "Docs", "working document": "Working documents"}
GENERIC_FOLDERS = {"sites", "site", "personal", "general", "files", "shared documents", "shared", "documents", "teams"}


def folder_from_path(path):
    """Last real folder of a path, as readable words ('/sites/hr-belgium/Policies/x.docx' -> 'Policies')."""
    parts = [p for p in re.split(r"[\\/]+", path or "") if p]
    if parts and "." in parts[-1]:
        parts = parts[:-1]
    parts = [p for p in parts if p.lower() not in GENERIC_FOLDERS]
    if not parts:
        return ""
    f = re.sub(r"[-_]+", " ", parts[-1]).strip()
    return f[:1].upper() + f[1:]


class ToolsMixin:
    def _init_tools(self):
        self.team_tools = {}
        share = self.docs.groupby("team_id").source.value_counts(normalize=True)
        for t, g in share.groupby(level=0):
            self.team_tools[t] = set(g[g >= 0.12].droplevel(0).index)
        for t in self.teams.index:
            self.team_tools.setdefault(t, {"Teams"})
        self.onboarded = set()

    # --------------------------------------------- who to ask, and where it is kept
    def where(self, d):
        """Plain words for where the document lives. Never a link."""
        team = self.teams.name.get(d.team_id, "its team")
        folder = (d.get("folder") if hasattr(d, "get") else "") or ""
        if not folder:
            folder = FOLDER_OF_TYPE.get(d.doc_type, "Documents")
            if d.client:
                folder = f"Customers › {self.clients.name.get(d.client, '')}"
        first = self.persons.name[d.author_id].split(" ")[0]
        return {"SharePoint": f"SharePoint › {team} › {folder}",
                "Teams": f"Teams › {team} › Files › {folder}",
                "OneDrive": f"{first}'s OneDrive › {folder}",
                "Notion": f"Notion › {team} › {folder}",
                "GitHub": f"GitHub › {team} repository › {folder if folder != 'Policies' else 'docs'}",
                "Legacy drive": f"Old shared drive › {team} › {folder}"}[d.source]

    def holder(self, d):
        """The person to contact for this document: its owner, else its author, else the closest colleague who is still here."""
        for pid in (d.owner_id, d.author_id):
            if pid and self.persons.active[pid]:
                return pid, None
        near = self.approver.get(d.doc_id)
        if not (near and self.persons.active[near]):
            near = self.above(d.author_id)
        if near:
            return near, f"{self.persons.name[d.owner_id or d.author_id]} left the company. {self.persons.name[near]} is the closest colleague."
        return None, None

    def contact(self, person_id):
        if person_id not in self.persons.index:
            raise KeyError("unknown person")
        p = self.persons.loc[person_id]
        boss = self.reports_to.get(person_id, "")
        out = {**self.person_card(person_id), "manager": self.person_card(boss) if boss else None}
        if p.active:
            out["email"] = p.get("email")
            out["note"] = "Company email given when this colleague signed up."
        else:
            out["email"] = None
            out["note"] = "This colleague has left the company."
        return out

    # ----------------------------------------------------- sign-in and sign-up
    LEVELS_SIGNUP = ["Junior", "Medior", "Senior", "Team Lead"]

    def search_people(self, q, limit=10):
        q = (q or "").strip().lower()
        if len(q) < 2:
            return []
        hit = self.persons[self.persons.name.str.lower().str.contains(re.escape(q)) & self.persons.active]
        hit = hit[hit.level.isin(["Junior", "Medior", "Senior", "Team Lead", "Head", "Lead", "Admin"])].head(limit)
        return [self.person_card(p) for p in hit.index]

    def signup_options(self, country, department):
        if country not in self.countries.index or department not in DEPTS:
            raise ValueError("unknown country or department")
        t = self.teams[(self.teams.country == country) & (self.teams.department == department)]
        return {"departments": list(DEPTS), "levels": self.LEVELS_SIGNUP, "sources": SOURCES,
                "teams": [{"team_id": i, "name": r["name"], "has_lead": bool(r.lead_id), "people": len(self.team_people.get(i, [])),
                           "tools": sorted(self.team_tools.get(i, []))} for i, r in t.iterrows()]}

    def signup(self, name, country, department, level, team_id=None, new_team_name=None, team_tools=None):
        """Create a new login. Joining a team needs no tools; a new team must be created by its team lead, who picks the tools."""
        with self.lock:
            name = re.sub(r"\s+", " ", (name or "").strip())
            if not re.fullmatch(r"[A-Za-zÀ-ÿ' .-]{2,60}", name):
                raise ValueError("enter a name of 2 to 60 letters")
            if country not in self.countries.index or department not in DEPTS or level not in self.LEVELS_SIGNUP:
                raise ValueError("unknown country, department or level")
            if getattr(self, "_signups", 0) >= 200:
                raise ValueError("sign-up limit reached for this demo")
            if team_id:
                if team_id not in self.teams.index or self.teams.country[team_id] != country or self.teams.department[team_id] != department:
                    raise ValueError("that team does not belong to this country and department")
                if level == "Team Lead" and self.teams.lead_id[team_id]:
                    raise ValueError("this team already has a team lead")
                created = False
            else:
                if level != "Team Lead":
                    raise ValueError("only a team lead can create a new team")
                nm = re.sub(r"\s+", " ", (new_team_name or "").strip())
                if not 2 <= len(nm) <= 60:
                    raise ValueError("give the new team a name")
                tools = set(team_tools or [])
                if not tools or not tools <= set(SOURCES):
                    raise ValueError("choose at least one known tool for the new team")
                prefix = f"T_{country}_{department[:3].upper()}_"
                n = 1 + sum(str(i).startswith(prefix) for i in self.teams.index)
                team_id = f"{prefix}{n}"
                while team_id in self.teams.index:
                    n += 1
                    team_id = f"{prefix}{n}"
                created = True
            pid = f"P{int(self.persons.index.str[1:].astype(int).max()) + 1:05d}"
            head = self.persons[(self.persons.country == country) & (self.persons.role == f"Head of {department}")]
            boss = self.teams.lead_id.get(team_id, "") if not created else ""
            reports = (boss if level != "Team Lead" and boss else (head.index[0] if len(head) else self.countries_lead(country))) or ""
            email = self._make_emails(pd.DataFrame({"name": list(self.persons.name) + [name]}))[-1]
            row = {"person_id": pid, "name": name, "email": email, "department": department, "country": country,
                   "role": f"{department} Team Lead" if level == "Team Lead" else f"{level} {department} specialist",
                   "level": level, "team_id": team_id, "reports_to": reports, "team_lead": level == "Team Lead", "active": True,
                   "previous_department": "", "opt_in_signals": False}
            if created:
                trow = {"team_id": team_id, "name": f"{nm} ({self.countries.name[country]})", "department": department,
                        "country": country, "lead_id": pid if level == "Team Lead" else ""}
                self.teams = pd.concat([self.teams, pd.DataFrame([trow]).set_index("team_id", drop=False)])
                self.t["teams"] = pd.concat([self.t["teams"], pd.DataFrame([trow])], ignore_index=True)
                self.team_tools[team_id] = set(tools)
                self.team_people[team_id] = []
            elif level == "Team Lead":
                self.teams.loc[team_id, "lead_id"] = pid
            self.persons = pd.concat([self.persons, pd.DataFrame([row]).set_index("person_id", drop=False)])
            self.t["persons"] = pd.concat([self.t["persons"], pd.DataFrame([row])], ignore_index=True)
            self.reports_to[pid] = reports
            self.team_people.setdefault(team_id, []).append(pid)
            self._signups = getattr(self, "_signups", 0) + 1
            tools = sorted(self.team_tools[team_id])
            return {"person": self.person_card(pid), "team": {"team_id": team_id, "name": self.teams.name[team_id], "created": created},
                    "can_edit_team": self.can_manage(pid, team_id),
                    "connect_links": {s: f"https://graphlas.example/connect/{team_id}/{s.lower().replace(' ', '-')}" for s in tools},
                    "note": "Connect links are simulated in this demo."}

    # ---------------------------------------------------------------- profile
    def can_manage(self, user_id, team_id):
        u = self.persons.loc[user_id]
        t = self.teams.loc[team_id]
        if u.level == "Team Lead":
            return u.team_id == team_id
        if u.level == "Head":
            return t.department == u.department and t.country == u.country
        return u.level == "Lead" and t.country == u.country

    def tool_warnings(self, team_id, source=None):
        out = []
        tools = self.team_tools.get(team_id, set())
        if source and source not in tools:
            out.append(f"{source} is not connected for this team, so documents there are not read.")
        if not (tools & OFFICIAL):
            out.append("No official source (SharePoint or GitHub) is connected: this team's knowledge stays invisible.")
        return out

    def profile(self, user_id):
        u = self.persons.loc[user_id]
        pr = self.person_prefs.get(user_id, {})
        sig = pr.get("signals") or {k: bool(u.opt_in_signals) for k in SIGNALS}
        tools = self.team_tools[u.team_id]
        return {"person": self.person_card(user_id), "team": {"team_id": u.team_id, "name": self.teams.name[u.team_id]},
                "team_tools": [{"source": s, "enabled": s in tools, "official": s in OFFICIAL, "note": TOOL_NOTE[s]} for s in SOURCES],
                "can_edit_team": self.can_manage(user_id, u.team_id),
                "personal_tools": [{"source": s, "enabled": s in pr.get("personal_tools", set()), "note": TOOL_NOTE[s]} for s in PERSONAL],
                "signals": [{"key": k, "label": v, "enabled": bool(sig.get(k, False))} for k, v in SIGNALS.items()],
                "connections": [{"provider": k, "label": v["label"], "connected": k in pr.get("connections", set()),
                                 "reads": v["reads"], "never": v["never"]} for k, v in PROVIDERS.items()],
                "answers": pr.get("answers", {}), "questions": ANSWER_KEYS, "onboarded": user_id in self.onboarded,
                "warnings": self.tool_warnings(u.team_id)}

    def set_profile(self, user_id, personal_tools=None, signals=None, team_tools=None, answers=None, connections=None):
        with self.lock:
            u = self.persons.loc[user_id]
            pr = self.person_prefs.setdefault(user_id, {"personal_tools": set(), "signals": {k: bool(u.opt_in_signals) for k in SIGNALS}, "answers": {}})
            pr.setdefault("connections", set())
            if connections is not None:
                if not set(connections) <= set(PROVIDERS):
                    raise ValueError("unknown provider")
                signals = dict(signals or {})
                personal_tools = set(pr["personal_tools"] if personal_tools is None else personal_tools)
                for k, v in PROVIDERS.items():                  # linking an account is the consent for what it reads
                    was, now = k in pr["connections"], k in connections
                    if was == now:
                        continue
                    if v["signal"]:
                        signals[v["signal"]] = now
                    if v["personal_tool"]:
                        (personal_tools.add if now else personal_tools.discard)(v["personal_tool"])
                pr["connections"] = set(connections)
                personal_tools = sorted(personal_tools)
            if personal_tools is not None:
                if not set(personal_tools) <= set(PERSONAL):
                    raise ValueError("unknown personal tool")
                pr["personal_tools"] = set(personal_tools)
            if answers is not None:                      # optional, and several answers per question are allowed
                for k, v in answers.items():
                    if k in ANSWER_KEYS:
                        vals = [v] if isinstance(v, str) else list(v)
                        pr["answers"][k] = [x for x in dict.fromkeys(vals) if x in ANSWER_KEYS[k]]
            if team_tools is not None:
                if not self.can_manage(user_id, u.team_id):
                    raise PermissionError("only a team lead (or higher) can change the tools of a team")
                if not team_tools or not set(team_tools) <= set(SOURCES):
                    raise ValueError("choose at least one known tool")
                self.team_tools[u.team_id] = set(team_tools)
            changed = False
            if signals is not None:
                for k, v in signals.items():
                    if k in SIGNALS and pr["signals"].get(k) != bool(v):
                        pr["signals"][k] = bool(v)
                        changed = True
            self.onboarded.add(user_id)
            if changed:                              # opt-out takes effect immediately on expertise
                self._expertise()
                self._score()
            return self.profile(user_id)

    def tools_status(self, user_id):
        u = self.persons.loc[user_id]
        g = self.docs[self.docs.team_id == u.team_id].source.value_counts().to_dict()
        adoption = {s: sum(s in t for t in self.team_tools.values()) for s in SOURCES}
        return {"team": self.teams.name[u.team_id], "connected": [{"source": s, "documents": int(g.get(s, 0)), "last_sync": "just now (simulated)"}
                                                                    for s in SOURCES if s in self.team_tools[u.team_id]],
                "adoption_teams": adoption, "teams_total": len(self.teams),
                "teams_without_official_source": sum(not (t & OFFICIAL) for t in self.team_tools.values())}

    # ------------------------------------------------------------ metadata
    def doc_metadata(self, doc_id):
        d = self.docs.loc[doc_id]
        return {"doc_id": doc_id, "source": d.source, "title": d.title, "author": self.persons.name[d.author_id],
                "team": self.teams.name.get(d.team_id, ""), "country": d.country, "language": d.language,
                "topic": self.topics.name.get(d.topic_id, d.topic_id), "version": int(d.version),
                "modified": str(d.last_modified.date()), "access": d.acl, "stated_value": d.key_value or None}

    def signal_allowed(self, pid, kind):
        pr = self.person_prefs.get(pid)
        return bool(pr["signals"].get(kind, False)) if pr else bool(self.persons.opt_in_signals[pid])

    def _log(self, kind, user_id, title, source, summary):
        self.event_log.append({"kind": kind, "who": self.persons.name[user_id], "source": source, "title": title, "summary": summary})
        del self.event_log[:-40]

    def recent_events(self, n=15):
        return list(reversed(self.event_log))[:n]

    def team_members(self, user_id):
        t = self.persons.team_id[user_id]
        ids = [p for p in self.team_people.get(t, []) if p != user_id and self.persons.active[p]][:12]
        return [{**self.person_card(p), "meetings_opt_in": self.signal_allowed(p, "meetings")} for p in ids]

    def ingest_event(self, user_id, payload):
        """Simulated webhook: a file was saved in a connected tool. Only the LINK and metadata are kept."""
        t0 = time.time()
        team = self.persons.team_id[user_id]
        source = payload.get("source", "SharePoint")
        if source not in SOURCES:
            raise ValueError("unknown source")
        title = str(payload.get("title", ""))
        if source not in self.team_tools[team]:
            self._log("document", user_id, title, source, "ignored: tool not connected")
            return {"status": "ignored", "reason": f"{source} is not connected for {self.teams.name[team]}; nothing was read.",
                    "warnings": self.tool_warnings(team, source), "timings_ms": round((time.time() - t0) * 1000, 1)}
        payload["folder"] = folder_from_path(payload.get("path"))
        parsed = self.parse_query(f"{title} {payload.get('path') or ''}")      # the title and folder tell what it is about
        derived = {}
        for k, v in (("topic_id", parsed["topic"]), ("country", parsed["country"]), ("client", parsed["client"])):
            if not payload.get(k) and v and not (k == "topic_id" and parsed["alternatives"]):
                payload[k] = v
                derived[k] = v
        res = self.ingest({**payload, "template": None}, user_id)
        res["derived_from_title"] = derived
        res["captured"] = "link and metadata" if res["status"] != "duplicate" else "nothing (duplicate)"
        if res["status"] != "duplicate":
            res["metadata"] = self.doc_metadata(res["document"]["doc_id"])
        res["warnings"] = self.tool_warnings(team)
        res["timings_ms_total"] = round((time.time() - t0) * 1000, 1)
        self._log("document", user_id, title, source, f"{res['status']}; trust {res['document']['trust']}")
        return res

    def _bump(self, pid, key, w, ev_type=None):
        raw = self.expert_raw
        raw.loc[(key, pid)] = raw.get((key, pid), 0.0) + w
        g = raw.loc[key]
        self.exp[key] = g / g.max()
        if ev_type:
            self.evidence[(key, pid, ev_type)] = self.evidence.get((key, pid, ev_type), 0) + 1

    def ingest_meeting(self, user_id, payload):
        """A meeting was planned in Teams: dissect the title, store a link, turn attendance into expertise signals."""
        t0 = time.time()
        team = self.persons.team_id[user_id]
        title = str(payload.get("title", "")).strip()[:200]
        if "Teams" not in self.team_tools[team]:
            self._log("meeting", user_id, title, "Teams", "ignored: Teams not connected")
            return {"status": "ignored", "reason": f"Teams is not connected for {self.teams.name[team]}; nothing was read.",
                    "timings_ms": round((time.time() - t0) * 1000, 1)}
        description = str(payload.get("description") or "").strip()[:1000]
        by_title = self.parse_query(title)
        parsed = self.parse_query(f"{title}. {description}") if description else by_title
        topic = None if parsed["alternatives"] else parsed["topic"]
        client = parsed["client"]
        # what only the description revealed (the description itself is never stored)
        from_description = [k for k, a, b in (("topic", by_title["topic"], parsed["topic"]), ("customer", by_title["client"], parsed["client"]),
                                              ("country", by_title["country"], parsed["country"])) if b and not a]
        if not topic and not client:
            self._log("meeting", user_id, title, "Teams", "ignored: no topic or customer in the title or description")
            return {"status": "ignored", "reason": "No topic or customer recognised in the title or description: nothing is stored.",
                    "extracted": {"topic": None, "country": parsed["country"], "client": None},
                    "timings_ms": round((time.time() - t0) * 1000, 1)}
        with self.lock:
            people = [user_id] + [a for a in payload.get("attendees", []) if a in self.persons.index and a != user_id]
            counted = [p for p in people if self.signal_allowed(p, "meetings")]
            res = self.ingest({"title": title, "extract": title, "source": "Teams", "doc_type": "meeting", "topic_id": topic,
                               "country": parsed["country"], "client": client or "", "link": payload.get("link"), "template": None},
                              user_id)
            did = res["document"]["doc_id"]
            edges = [(p, did, "ATTENDED", 1) for p in counted]
            keys = [f"topic:{res['document']['topic_id']}"] + ([f"client:{client}"] if client else [])
            for p in counted:
                for k in keys:
                    self._bump(p, k, 0.25, "ATTENDED")
            added = len(counted) * len(keys)
            if client:
                for p in people:
                    if self.signal_allowed(p, "customers"):
                        self._bump(p, f"client:{client}", 0.06)
                        self.interactions[(f"client:{client}", p)] = self.interactions.get((f"client:{client}", p), 0) + 1
                        edges.append((p, client, "INTERACTED_WITH", 1))
                        added += 1
            import pandas as pd
            self.edges = pd.concat([self.edges, pd.DataFrame(edges, columns=self.edges.columns)], ignore_index=True)
        out = {"status": "captured", "captured": "link, title and attendance (no content)",
               "extracted": {"topic": res["document"]["topic_id"], "topic_name": res["document"]["topic_name"],
                             "country": parsed["country"], "client": client, "client_name": self.clients.name.get(client) if client else None},
               "read_from_description": from_description,
               "attendees": {"invited": len(people), "counted": len(counted), "not_opted_in": len(people) - len(counted)},
               "expertise_updates": added, "metadata": self.doc_metadata(did), "link": self.docs.link[did],
               "timings_ms": round((time.time() - t0) * 1000, 1)}
        self._log("meeting", user_id, title, "Teams", f"captured; {added} expertise updates")
        return out
