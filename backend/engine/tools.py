"""Connected tools, personal preferences and the document-created event (simulated webhook)."""
import time

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


class ToolsMixin:
    def _init_tools(self):
        self.team_tools = {}
        share = self.docs.groupby("team_id").source.value_counts(normalize=True)
        for t, g in share.groupby(level=0):
            self.team_tools[t] = set(g[g >= 0.12].droplevel(0).index)
        for t in self.teams.index:
            self.team_tools.setdefault(t, {"Teams"})
        self.onboarded = set()

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
                "answers": pr.get("answers", {}), "questions": ANSWER_KEYS, "onboarded": user_id in self.onboarded,
                "warnings": self.tool_warnings(u.team_id)}

    def set_profile(self, user_id, personal_tools=None, signals=None, team_tools=None, answers=None):
        with self.lock:
            u = self.persons.loc[user_id]
            pr = self.person_prefs.setdefault(user_id, {"personal_tools": set(), "signals": {k: bool(u.opt_in_signals) for k in SIGNALS}, "answers": {}})
            if personal_tools is not None:
                if not set(personal_tools) <= set(PERSONAL):
                    raise ValueError("unknown personal tool")
                pr["personal_tools"] = set(personal_tools)
            if answers is not None:
                for k, v in answers.items():
                    if k in ANSWER_KEYS and v in ANSWER_KEYS[k]:
                        pr["answers"][k] = v
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

    def ingest_event(self, user_id, payload):
        """Simulated webhook: a document was created in a connected tool. Only metadata is captured and scored."""
        t0 = time.time()
        team = self.persons.team_id[user_id]
        source = payload.get("source", "SharePoint")
        if source not in SOURCES:
            raise ValueError("unknown source")
        if source not in self.team_tools[team]:
            return {"status": "ignored", "reason": f"{source} is not connected for {self.teams.name[team]}; nothing was read.",
                    "warnings": self.tool_warnings(team, source), "timings_ms": round((time.time() - t0) * 1000, 1)}
        res = self.ingest({**payload, "template": None}, user_id)
        res["captured"] = "metadata" if res["status"] != "duplicate" else "nothing (duplicate)"
        if res["status"] != "duplicate":
            res["metadata"] = self.doc_metadata(res["document"]["doc_id"])
        res["warnings"] = self.tool_warnings(team)
        res["timings_ms_total"] = round((time.time() - t0) * 1000, 1)
        return res
