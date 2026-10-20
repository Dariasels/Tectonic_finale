# Prompts to visualise how Graphlas works in the backend

Use with an image model (Midjourney, DALL-E / ChatGPT images, Gemini / Imagen, Firefly...). Image models draw text badly, so there are two versions:
**A** asks for short labels (good in Gemini or ChatGPT images), **B** asks for no text at all and you add the labels in PowerPoint (safest for the pitch).
Generate 4 variants, pick one, and fix the labels yourself. Do not use real company logos: the prompt asks for generic icons.

## A. Master prompt (with short labels)

> Create a clean, premium SaaS architecture illustration titled "How Graphlas 2.0 works", 16:9, high resolution, white background, modern flat-isometric style with soft glows, rounded shapes, consistent thin navy (#17104A) line art and generous whitespace. Flow from left to right in six clearly separated zones connected by smooth glowing arrows:
>
> 1. **"Your tools"** (far left): six stacked generic icons, not real logos: a chat bubble with a calendar (meetings), a folder with a document (SharePoint-like library), a cloud (personal drive), a notebook (wiki), a code branch (repository), an old grey hard drive (legacy). Small light pulses leave each icon, labelled "events".
> 2. **"Links, not files"**: a narrow gate. A document icon is stopped and crossed out; only a chain-link icon and a small metadata card (title, owner, team, date, tool, access rights) pass through. Caption: "link + metadata only".
> 3. **"Read and tag"**: a magnifier over a meeting title reading "Nike payroll cut-off, Belgium", producing three coloured tags: topic, customer, country, plus one extracted fact; a paper shredder below destroys the content. Caption: "content is never kept".
> 4. **"Company graph"** (centre, the largest element): a glowing network of nodes in a branching tree: country, then department, then team; around it people (round avatars), documents (small page icons), topics and customers (hexagons). Edges in four styles: solid "wrote / approved", dashed "links to", dotted red "replaced by". One branch (Belgium, Nike) is highlighted.
> 5. **"Trust engine"**: twenty small signal chips (age, owner left, reviews, conflicts, popularity, tool) flowing into a decision-tree-ensemble icon, which outputs a round dial from 0 to 100 with a green, yellow and red band, next to a short list of plain-language reasons. A second smaller block "who knows" turns people-to-topic links into expertise.
> 6. **"The answer"** (far right): a simple search result card: a person avatar and name, a score badge "88" with a green dot, a file title, and a plain location "SharePoint › Team › Policies". A small contact card pops out of the name with an email envelope.
>
> Along the bottom, a calm horizontal band "Keeps itself trusted" with five small icons: a person with a check ("human only when needed"), a trash bin with a restore arrow ("replaced and orphaned documents leave"), a circular arrow ("retrains weekly"), a padlock ("opt-in signals"), a shield ("access rights enforced").
>
> Colour: brand gradient from orange (#FF8B4A) through red (#F0343C) and magenta (#B3308F) to deep purple (#2A1458) for arrows, glows and the graph; navy for line art; green, yellow and red ONLY for the trust dial and badges. Labels: short English captions, maximum three words each, sans-serif (Montserrat style), perfectly spelled. Style reference: modern fintech and data-platform product diagrams, balanced composition, no clutter.
>
> Negative: no photorealism, no people photos, no real brand logos, no dark background, no 3D clutter, no misspelled text, no extra boxes, no watermarks.

## B. Master prompt (no text, label it yourself)

Same as A, but replace the last two paragraphs with:

> Do not render any letters or numbers anywhere: leave every label area as an empty rounded caption plate. Use only icons and shapes. Keep the six zones evenly spaced so labels can be added later.

Labels to add in PowerPoint, left to right: **Your tools** · **Links, not files** · **Read and tag** · **Company graph** · **Trust engine** · **The answer**; bottom band: **Keeps itself trusted: human only when needed, replaced documents leave, weekly retraining, opt-in signals, access rights**.

## C. Short prompt (for tools with a small limit)

> Flat isometric SaaS architecture diagram, 16:9, white background, orange-to-purple gradient arrows. Left to right: generic tool icons (meeting, folder, cloud, notebook, code branch, old drive) -> a gate letting only a chain link and a metadata card through (a document is blocked) -> a magnifier tagging a meeting title with topic, customer, country -> a glowing company graph (country, department, team, people, documents, customers) -> a 0 to 100 trust dial with green, yellow, red -> a search result card with a person avatar, score badge and file location. Bottom band with icons for human check, clean-up, retraining, privacy lock, access shield. Clean, premium, no clutter, no photorealism, no real logos.

## D. If you want a diagram that stays editable
Ask a text-to-diagram tool (Mermaid, draw.io, Miro AI) with this instead, then restyle it in the Graphlas colours:

> Draw a left-to-right flow: Tools (Teams, SharePoint, OneDrive, Notion, GitHub, legacy drives) -> Events (meeting planned, file saved) -> Link + metadata (no files) -> Reader (topic, customer, country, one fact; content discarded) -> Company graph (country > department > team, people, documents, topics, customers) -> Trust engine (20 signals, gradient-boosted trees, expertise, weekly retraining) -> Answer (person, trust score, file title, plain location, contact card). Side loops: team-lead approval only for borderline cases, automatic clean-up of replaced and orphaned documents, access rights, opt-in signals.

## What the picture must get right (check before using it)
- Nothing uploads: documents never enter the system, only links and metadata.
- The answer is a person, not a document list.
- Green, yellow and red are only for trust, never decoration.
- Humans appear only at the edge (approvals, team-lead reviews), not in the main flow.
