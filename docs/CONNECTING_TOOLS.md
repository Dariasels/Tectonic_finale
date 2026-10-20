# How the real connections work (SharePoint, OneDrive, Teams, Notion, GitHub)

In the demo the connections are simulated: the buttons under *Connected tools* and the *Live capture* page produce the same events that the real tools would send. Everything after the event (link + metadata, extraction, scoring, graph, approvals, clean-up) is already built. What is missing is the part in front of it.

## The flow in production
1. **Connect (once).** A person or team lead presses *Connect* on a tool. The browser goes to the tool's own consent page (OAuth 2.0), the tool shows exactly which read permissions are requested, the user agrees, and the tool sends the browser back to `/api/auth/<tool>/callback` with a one-time code. The backend swaps it for tokens and stores them encrypted (refresh token in a vault, never in the repo or the browser).
2. **First scan (backfill, once).** The connector walks everything the authorisation can see: for each file the metadata (name, folder, owner, dates, version, who can access it). Each file goes to the extraction agent (read once, keep one fact, forget the content) and then into the same `ingest_event` the demo uses.
3. **From then on only changes.** The tool tells us when something is created, changed, moved, deleted or its permissions change (webhooks or delta queries). Only those files are read again. A changed file also triggers the "edited" rules; a deleted file leaves Graphlas like a removed document.
4. **Keep it healthy.** Tokens are refreshed, subscriptions renewed, failed items retried, and each tool can be paused on its own.

So the picture in the question is right: connect, authorise, scan once, then only new and changed files. The extra parts are changes, deletions and permission changes, not only "new uploads".

## Per tool
| Tool | How it connects | Read-only permissions (minimum) | New and changed files | Effort |
|---|---|---|---|---|
| **SharePoint, OneDrive** | Microsoft Entra ID (Azure AD) app registration, Microsoft Graph, admin consent by the company IT | `Sites.Selected` (only chosen sites) or `Files.Read.All`; `User.Read.All` for names | Graph change notifications (webhooks) plus delta queries per library | 2 to 4 days, plus IT approval |
| **Teams** | Same Microsoft app | `Calendars.Read` (meeting titles and descriptions), `OnlineMeetings.Read`; channel files come through SharePoint | Graph subscriptions on calendar events | 2 to 3 days |
| **Notion** | Public integration with OAuth, or an internal integration token; pages must be shared with the integration | Read content / read metadata only | Search API with `last_edited_time` (webhooks are limited) | 1 to 2 days |
| **GitHub** | A GitHub App installed on the organisation | Repository metadata, contents (docs only), pull requests read | Webhooks: push, pull_request, pull_request_review | 1 to 2 days |
| **Legacy drives** | File-share agent or scheduled crawl on the network | Read on selected shares | Scheduled crawl by modified date | 2 to 3 days (agent on their network) |

Work shared by all of them: the backfill queue and workers (retries, back-off, a dead-letter queue), checkpoints so a scan can resume, idempotent events (file id + version), mapping tool permissions to our `acl`, and an audit log. About 3 to 5 days once, then each tool as above.

## Where it goes in this codebase
- `backend/connectors/<tool>.py`: `authorize_url()`, `handle_callback()`, `backfill()`, `handle_webhook()`, each ending in `engine.ingest_event(...)` or `ingest_meeting(...)` (unchanged).
- Endpoints: `GET /api/auth/<tool>/start`, `GET /api/auth/<tool>/callback`, `POST /api/hooks/<tool>` (signed webhooks).
- Tables: connections (tool, who, scope, encrypted token, cursor, status).
- The *Connect* buttons already exist in the interface; they would open the real consent page instead of the simulated one.
- Needs from the company: an app registration per tool with client id and secret, admin consent for Microsoft, a public HTTPS address for the callbacks and webhooks.

## What can go wrong, and what we do about it
- **Permissions.** IT must approve; ask for the narrowest scope (`Sites.Selected`) and show exactly what is read.
- **Privacy law and works council (EU).** Metadata and links only, content in memory only, opt-in signals, access rights enforced on the server, a clear data-protection assessment.
- **Rate limits and volume.** Throttle, use delta queries, scan in the background, cache by file hash so unchanged files are never read twice.
- **Access mapping.** A wrong mapping would show a document to the wrong person: map conservatively (unknown = hidden) and test it.
- **Duplicates across tools** (the same file in OneDrive and SharePoint): the existing duplicate check on the extracted fact handles most.
- **Cost of the language model on a big first scan:** run the rule-based extractor first, use the model only when confidence is low.
