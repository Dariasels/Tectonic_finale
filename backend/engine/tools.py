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
        parsed = self.parse_query(title)
        topic = None if parsed["alternatives"] else parsed["topic"]
        client = parsed["client"]
        if not topic and not client:
            self._log("meeting", user_id, title, "Teams", "ignored: no topic or customer in the title")
            return {"status": "ignored", "reason": "No topic or customer recognised in the title: nothing is stored.",
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
               "attendees": {"invited": len(people), "counted": len(counted), "not_opted_in": len(people) - len(counted)},
               "expertise_updates": added, "metadata": self.doc_metadata(did), "link": res["document"]["link"],
               "timings_ms": round((time.time() - t0) * 1000, 1)}
        self._log("meeting", user_id, title, "Teams", f"captured; {added} expertise updates")
        return out
