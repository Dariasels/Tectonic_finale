from .core import CoreEngine, badge, _read
from .heroes import inject_heroes
from .ingest import IngestMixin
from .queries import QueryMixin
from .tools import ToolsMixin


class TrustEngine(ToolsMixin, IngestMixin, QueryMixin, CoreEngine):
    def __init__(self):
        from .seed_org import DATA_DIR, main as generate
        if not (DATA_DIR / "documents.csv").exists():      # data is git-ignored: create the simulated data on first start
            generate.__wrapped__() if hasattr(generate, "__wrapped__") else self._generate()
        tables = {n: _read(n) for n in ["persons", "teams", "documents", "edges", "feedback", "ground_truth",
                                        "topics", "clients", "countries"]}
        self.heroes = inject_heroes(tables)["_heroes"]
        self._init_runtime()
        super().__init__({k: v for k, v in tables.items() if k != "_heroes"})
        self.last_train_wall = None
        self._init_tools()
        self._seed_resolutions()

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
