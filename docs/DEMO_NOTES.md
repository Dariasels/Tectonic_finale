# Demo walkthrough notes (2026-10-20) and what we decided

## What the demo shows
- **The data is annotated by us** (the demo files carry their topic, country, customer and stated fact). In production a **locally run agent** does that.
- **The graph hierarchy decides which person holds the most trustworthy document.**
- **The output is a person**, with the relevant document named (for example the parental leave policy).
- There is a removal system (the trash). How it works is written down in `docs/REMOVAL.md`.

A precision for the pitch: the demo does not need word matching to *produce* the features of a document, because we annotated them. Word matching is still used to understand a *question* and a *meeting title* (topic, country, customer through synonyms). Say it that way, not "there is no word matching".

## What is still to build
- **The agent:** on connecting, it asks permission to scan all documents and makes metadata per document. New documents in a folder are scanned automatically (see `docs/IMPROVEMENTS.md`).
- **Connecting the apps** (GitHub, Notion, SharePoint and the others) takes days because of the company's IT permission and approval (see `docs/CONNECTING_TOOLS.md`). One tool was unclear in the notes ("Nooit"); to be confirmed.

## Risk to answer in the pitch
Customers may object that an agent reads all their data. Answer: the agent runs **locally** in the customer's own environment, is **constrained** (read-only, narrowest scope, no content leaves, only a few structured fields and a link are kept), and can be switched off per tool.

## Decisions
- Pitch: the data is manually annotated now; in production a locally run agent does it.
- Pitch is built around three features: platform integrations, the graph, the trust score.
- Next step (Speaker 1): find out how the removal system works: done, see `docs/REMOVAL.md`.
