from .cleanup import CleanupMixin
from .core import CoreEngine, badge, _read
from .heroes import inject_heroes
from .ingest import IngestMixin
from .queries import QueryMixin
from .tools import ToolsMixin


class TrustEngine(CleanupMixin, ToolsMixin, IngestMixin, QueryMixin, CoreEngine):
    def __init__(self):
        from .seed_org import DATA_DIR, main as generate
        if not (DATA_DIR / "documents.csv").exists():      # data is git-ignored: create the simulated data on first start
            generate.__wrapped__() if hasattr(generate, "__wrapped__") else self._generate()
        tables = {n: _read(n) for n in ["persons", "teams", "documents", "edges", "feedback", "ground_truth",
                                        "topics", "clients", "countries"]}
        self.heroes = inject_heroes(tables)["_heroes"]
        from .tools import make_link
        tn = tables["teams"].set_index("team_id").name
        pn = tables["persons"].set_index("person_id").name
        d = tables["documents"]
        d["folder"] = ""                                       # readable folder, filled for documents that arrive through events
        d["link"] = [make_link(s, tn.get(t, ""), i, pn.get(a, "")) for s, t, i, a in zip(d.source, d.team_id, d.doc_id, d.author_id)]
        tables["persons"]["email"] = self._make_emails(tables["persons"])
        self._init_runtime()
        super().__init__({k: v for k, v in tables.items() if k != "_heroes"})
        self.last_train_wall = None
        self._init_tools()
        self._seed_resolutions()

    @staticmethod
    def _make_emails(persons):
        """Company address for everyone, like firstname.lastname@sdworx.example (numbered if two people share a name)."""
        import re
        import unicodedata
        seen, out = {}, []
        for name in persons["name"]:
            base = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
            base = re.sub(r"[^a-z]+", ".", base).strip(".") or "colleague"
            seen[base] = seen.get(base, 0) + 1
            out.append(f"{base}{'' if seen[base] == 1 else seen[base]}@sdworx.example")
        return out

    @staticmethod
    def _generate():
        from .seed_org import DATA_DIR, gen
        DATA_DIR.mkdir(exist_ok=True)
        for name, df in gen().items():
            df.to_csv(DATA_DIR / f"{name}.csv", index=False)

    def _seed_resolutions(self):
        """A few historical 'this helped' confirmations so the memory is not empty in the demo."""
        import pandas as pd
        h = self.heroes
        key = self.intent_key("client_sla", "ES", "C01")
        self.resolutions[key] = {("person", h["be_cs"]): {"users": {"u1", "u2", "u3"}, "last": pd.Timestamp("2026-10-02")}}

    def demo_users(self):
        users = super().demo_users()
        return users
