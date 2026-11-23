# Dashboard redesign: handoff

Refs #67 · Branch `feat/67-dashboard-redesign`

This branch takes the ZeroLocal dashboard from a read-only viewer to a working tool: every resource can be created from the UI, every page is fully built (no "coming soon"), it uses the ZeroDB brand, and it has light and dark themes. This doc is for whoever finishes it locally. It says what's built, what was decided, where the design and the API disagree, and what's left.

Screenshots of the 10 built pages, light and dark, are in [`docs/design/dashboard-redesign/`](../design/dashboard-redesign/), taken this session (Nov 22) against a real `zerodb serve` lite-mode backend with real data. The phone-width and dialog screenshots there are from an earlier pass against fixture API data and were not retaken this session.

## Decisions (design review, Nov 22, 2026)

1. **Nothing ships as a placeholder.** Every page is real, Files included.
2. **Events has its own page**, separate from Logs. Events = structured "what happened" feed; Logs = raw server output.
3. **Dark mode is in.** Light / Dark / System, toggle in every page header, full choice in Settings.
4. **ZeroDB branding**, the same token system as zerodb.ainative.studio (Signal Cyan `#38BDF8`, Space Grotesk / Inter / JetBrains Mono, block "Z" mark).
5. **Create flows serve developers and vibe coders**: guided forms by default, an "Advanced JSON" view of the exact request body one click away. Edits carry across both views. Settings lets a user default to Advanced.

## What's built

| Route | What it does |
|---|---|
| `/` Overview | Lite/full mode badge from `/health`, totals summed from each project's `usage`, services for the backend actually running, API endpoint (real value), recent events, "first five minutes" guide until there's data |
| `/projects` | Search, cards with usage counts, **New project** dialog (with "Show API request"), delete with in-page confirm |
| `/vectors` | List by namespace, semantic search (scored), delete, **Upsert vector** dialog: Guided (text, namespace, ID, tags→metadata) / Advanced JSON |
| `/tables` | Table list, row viewer typed from the schema, **Create table** dialog: Column builder (plain-language types, required, enum options) / JSON schema, **Add row** dialog with typed inputs, delete table |
| `/memory` | Agent memory by session (conversation view, roles, token estimate), semantic search across memory, agent filter, **Add memory** dialog (Guided / Advanced JSON, pre-fills the open session), delete session |
| `/files` | Drag-and-drop or browse upload (multi-file, sequential), list, download, delete |
| `/events` | Feed with family filter chips (`vector.*`, `table.*`…), detail panel with JSON, Live (3s polling) / Paused, **Publish event** dialog |
| `/sync` | Pending changes, last sync, cloud connection; **Preview sync** (push / pull / both, conflict rule) shows counts, schema changes, warnings and steps before **Run sync**; conflicts with side-by-side versions and keep-local / keep-cloud; history |
| `/logs` | Six stat cards replaced by one row of level toggles; service, time-range and line-count filters; search; live refresh; export; always-dark terminal surface |
| `/settings` | Theme, real server values (API URL in use, dashboard origin, backend from `/health`), **Connection** (API key for servers with cloud sign-in), create-form defaults, cloud sync status + connect with API key |

Shared: the selected project is app-wide (`ProjectProvider`) and shown as a picker in every project-scoped page header, so moving between pages keeps your place. `?new=1` on Projects/Vectors/Tables opens the create dialog (used by Overview and empty states).

## Audit: pages, sign-in and setup (Nov 22, second pass)

Every API router was checked against the dashboard. Result:

| API area | Before | Now |
|---|---|---|
| Projects, vectors, tables, files, events, logs | built in the first pass | — |
| Memory (`/database/memory/*`) | no page; client called a route that doesn't exist | **Memory page** |
| Sync: plan / execute / status, conflicts, history | no page | **Sync page** |
| Sync internals: change log, schema diff, export bundles, pull preview/apply, rollback, sync state | no page | Left to the CLI on purpose; the Sync page covers the user-facing flow through the orchestrator |
| `raymond` router | — | Client-specific, not dashboard material |

**Sign-in.** There are no user accounts, login routes or passwords in the API. Before this branch, full mode defaulted to cloud sign-in and the dashboard sent no credentials, so **every dashboard request failed with 401 in Docker** unless `CLOUD_API_KEY` was set on the server. Now both modes default to no login (see the security model below), and when a server does want a key (local access key or cloud mode), Settings › Connection stores it and the client sends it as a Bearer token; any 401/403 shows a banner on every page pointing there.

**Setup gaps fixed in this pass:**
- `dashboard/Dockerfile` copies `public/`, which didn't exist, so the dashboard image build failed. Added `public/` (brand mark) and an app icon. *Not built here (no Docker daemon in this environment); run `docker compose build dashboard`.*
- Compose passed `VITE_API_URL` to a Next.js app that reads `NEXT_PUBLIC_API_URL`, and as a runtime env var although Next bakes it in at build. Now a build arg (+ `API_INTERNAL_URL` at runtime).
- README referenced `.env.local.example`, which didn't exist. Added it (container settings), plus `.env.example` for ports and bind address: Compose only reads those from `.env`, so they never worked from `.env.local`.
- README rewritten for first-time setup: how to run the dashboard in lite mode (it isn't in the pip package), ports table, sign-in and the built-in local user, default service credentials (Postgres `zerodb` / `localpass`, MinIO `minioadmin` / `minioadmin`), the security note below, a page guide, troubleshooting. Its vector upsert/search curl examples used fields the API doesn't accept (`vector_embedding`, `query_vector`); fixed. The pip-installed `zerodb serve` only has `--host/--port/--reload`; README now uses `ZERODB_DATA_DIR` / `CLOUD_API_KEY`, which work either way.

**Security model (decided Nov 22, implemented on this branch).** Open-core split: local is single-player and frictionless; sign-in, users and teams are ZeroDB Cloud's job. So:

1. **This machine only by default.** `zerodb serve` (both CLI entry points) and `python api/main.py` default to `127.0.0.1`; Docker publishes every port on `${ZERODB_BIND_ADDRESS:-127.0.0.1}`. `zerodb serve --host 0.0.0.0` without a key prints a warning. Tests updated: `cli/tests/test_serve_command.py` (+ exposure warning tests).
2. **Optional local access key.** `ZERODB_LOCAL_API_KEY`: when set, local mode requires `Authorization: Bearer <key>` (constant-time compare, key never echoed). Dashboard sends it from Settings › Connection. Tests: `api/tests/test_local_access_key.py`.
3. **No login by default in Docker either.** `ZERODB_AUTH_MODE` now defaults to `local` in both backends (was `cloud` for full mode, which made the open-source Docker setup unusable without a ZeroDB account). `cloud` stays available as an opt-in.
4. **Every router behind the sign-in check.** Seven routers had no auth at all (cloud sync, export, logs, pull sync, sync history, sync orchestrator, raymond), so neither cloud mode nor a key protected them. `api/main.py` now adds the dependency on every `include_router`; `/health` and `/` stay open. Tests: `api/tests/test_router_auth_coverage.py`.
5. **No local user accounts or default password**, on purpose: a well-known default password protects nothing, and accounts/teams are the cloud's upgrade path.

Also fixed: `api/tests/test_qdrant_startup.py` was already failing on `main` (it expected `6333:6333`, the file has had a port variable for a while).

## End-to-end pass against a real lite-mode API (this session)

Merged `main` in (brings #47's lite-mode CRUD fix, plus #64/#66/#71), then ran the full walkthrough against a real `zerodb serve` (lite mode) and `npm run dev` dashboard, driven by real browser automation, in both light and dark theme.

**Fixed as part of this pass** (own issue/branch/PR each, TDD -- failing test first):
- **#73**: lite-mode `sync_history` table was missing `sync_id` and several other ORM-expected columns (`direction`, `mode`, `bytes_transferred`, `error_message`, `error_stack`, `snapshot_id`, `updated_at`) -- `GET /sync/history` 503'd on every lite install. `sync_state` already matched its ORM model and needed no change. Fixed in `lite/db/schema_lite.sql`.
- **#75**: `zerodb serve` (the README's own documented quickstart) crashed immediately with `ModuleNotFoundError: No module named 'app'` -- `cli/commands/serve.py` pointed uvicorn at a package (`app.main:app`) that doesn't exist anywhere. The existing test suite had mocked this exact call and asserted the wrong module string, so it stayed green while the command was completely broken for every user. Fixed to resolve and `chdir` into the real `api/` package.
- **#77**: Memory page's **Add memory** dialog stored a memory successfully with a blank Session field, but the memory then vanished permanently -- `api/services/memory_service.py`'s `list_sessions()` filters out any `session_id IS NULL` row, and the dialog's own "Leave blank to start a new one" hint wasn't implemented; blank really meant null. Fixed client-side to generate a session id when the field is blank.
- **#79**: lite-mode `conflict_log` table had an older, different column shape than the `ConflictLog` ORM model (no `detected_at`/`conflict_metadata`/`notes`, different names for the rest) -- `GET /sync/conflicts/` 503'd, hit while exercising the Sync page. Same family as #73; fixed the same way.
- **#80**: Every page showed a false "This server needs an API key" banner whenever a project simply wasn't connected to ZeroDB Cloud (a `cloud/status` 401 by design) -- even with `zerodb serve` started with **no** `ZERODB_LOCAL_API_KEY` at all and every real local-API request succeeding. The global 401/403 handler couldn't tell a cloud-auth 401 apart from a local-key 401. Fixed by excluding `cloud/status` from the generic auth-error path.

**Verified working, no changes needed:**
- Create a project; Overview/Projects both reflect it immediately.
- Vectors: Guided and Advanced JSON upsert, both with a custom ID containing `/` (confirms the `{vector_id:path}` fix from a prior session still holds post-merge); semantic search with real relevance scores; delete (including a slash-ID vector).
- Tables: column builder and JSON schema, both create working tables; Add row respects the schema's types.
- Memory: add (now always listed, see #77), semantic search across stored memories.
- Files: upload, download, delete; the 10 MB client-side guard (`exceedsUploadLimit` in `dashboard/lib/files.ts`) verified via its existing unit test rather than a live oversized browser upload (the upload tool itself caps combined size well under the limit, so a true 10MB+ upload wasn't practical to drive through the browser this pass).
- Events: publish, family filter chips, detail panel.
- Sync: preview (push, with real counts: tables/rows/vectors/memories/events/files) -- not executed (`Run sync`/push/pull need a real cloud connection, gated on `CLOUD_API_KEY`, not present this session; see below).
- Theme (light/dark/system) and Settings form defaults (Guided ⇄ Advanced JSON) persist correctly across pages and reloads.
- API key flow (step below): banner only appears when a real key is actually configured; pasting the correct key in Settings restores access; `zerodb serve --host 0.0.0.0` with no key prints the documented security warning to stdout.

**Found, filed, not fixed (out of scope for this pass):**
- **#83**: `docker compose up`/`docker compose build` fails outright -- `docker-compose.yml`'s `minio` service references `ainative-studio/minio:local`, which exists nowhere (not on Docker Hub, not built locally, no Dockerfile or build step for it). The comment pointing at a `minio-fork-maintenance-plan.md` doc is dead; that file doesn't exist. Independently confirmed `minio/minio:latest` really is gone from Docker Hub (so the stated reason for moving off it is real), but the replacement was never actually built. The dashboard's own Docker image builds and runs fine in isolation; it's the full compose stack that's blocked, since `zerodb-api` hard-depends on `minio: condition: service_healthy`. This is a real infrastructure gap (sourcing/building/maintaining a MinIO fork) out of scope to improvise inside this session -- filed and left for dedicated follow-up.
- A deeper, separate lite-mode gap found but **not** fixed: `POST /sync/execute` still fails with `no such table: sync_plans` -- `api/models/sync_plan.py`'s ORM model (added for #71's sync-plan-persistence work) has no corresponding table in `lite/db/schema_lite.sql` at all (not just missing columns, the whole table). This blocks a real end-to-end push/pull run in lite mode even once cloud-connected. Flagged here rather than fixed, since it's materially larger than #73/#79's column-mismatch shape and wasn't part of this pass's original scope. No issue filed yet for this specific gap -- worth its own issue before anyone attempts a live cloud sync run in lite mode.

## Where things live

```
dashboard/
  app/globals.css               brand tokens, light + .dark (HSL vars)
  tailwind.config.ts            token colours, cyan scale, font families
  app/layout.tsx                providers, self-hosted fonts, no-flash theme script
  lib/theme.ts                  preference parsing/resolution + head script
  lib/schema-builder.ts         column builder <-> API schema, validation, row coercion
  lib/vector-form.ts            guided form <-> upsert body, JSON parsing
  lib/events.ts                 family grouping/filtering, data parsing, summaries
  lib/files.ts                  base64 helpers, download, content-type names
  lib/preferences.ts            per-browser create-form defaults
  lib/memory-form.ts            guided memory form <-> store body
  lib/api-key.ts                optional API key for cloud sign-in servers
  services/api-client.ts        createApiClient(http) -- injectable, typed to the real API
  types/index.ts                response types matching api/routers/*.py
  components/providers/         theme-provider, project-provider, query-provider
  components/layout/            sidebar, page-header (+ project picker), mode-badge, theme-toggle, states
  components/ui/                button/badge/input/card (rebranded) + dialog, form-controls
                                (Select, Textarea, Field), segmented, confirm-dialog, copy-field
  components/{projects,vectors,tables,memory,events}/   the create dialogs
  components/layout/auth-notice.tsx               401 banner
```

Conventions kept from the existing kit: Radix primitive where one exists, `cva` variants, `forwardRef`, Tailwind classes that read CSS variables. No new UI framework. New dependencies: `@fontsource-variable/{inter,space-grotesk,jetbrains-mono}` (fonts are bundled so the dashboard works offline; `next/font/google` needs network at build) and `@testing-library/user-event` (dev).

## Where the code follows the API instead of the mockup

The design canvas was drawn before checking the request models. The code follows the API; update the canvas if you want them to match.

- **Vectors use `namespace`, not "collection".** `VectorUpsert` is `{document, metadata, namespace, vector_id}`. The old client also sent `collection` to search, which the API ignores; fixed.
- **No embedding-model picker and no "bring your own vector".** The upsert endpoint embeds `document` server-side and accepts neither a model nor raw values. Both need API changes first; the guided form says "We'll turn this into a vector for you" and leaves it there.
- **Search threshold defaults to 0** (API default is 0.7, which hides most results for short queries). Results are ranked by score instead.
- **File upload shows per-file state, not a percentage.** The API takes base64 in a JSON body, so there's no streaming progress to report.
- **Event filter chips are computed from the loaded feed** (last 200 events), not from `/events/stats/summary`. Swap in stats if counts over a longer window matter.
- **Types were wrong before this branch** (`File.name` vs `file_name`, `Event.type` vs `event_type`, `Table.row_count` that doesn't exist, …). `types/index.ts` now mirrors the Python response models.

## Verified

- `npm test`: **152 passing** (16 files): pure logic, API client (now with an injected HTTP instance; the old suite made real requests to localhost:8000), theme provider, and page-level tests that drive each create flow through the UI.
- `npx tsc --noEmit`, `npm run lint`: clean.
- `npm run build`: all 10 routes prerender (also rebuilt inside `docker compose build dashboard`, which succeeds cleanly -- see Docker note below).
- Production build loaded in Chromium against fixture API data, every page in light, dark and 390px phone width (plus the 401 banner): **no console errors, no horizontal page scroll**. That pass caught and fixed a hydration mismatch (browser-only values rendered on the server) and table "Actions" labels escaping their scroll box on phones.
- Also fixed two tests already failing on `main`: a timezone-dependent `formatDate` test and the network-calling API client suite.
- **End-to-end against a real `zerodb serve` (lite mode) API**, driven by real browser automation, light and dark theme: see the session writeup above for exactly what was exercised and what it found. Python suite: `python -m pytest tests/ -v --no-cov` 261 passed / 9 skipped; `cd api && python -m pytest tests/ --no-cov` 69 passed / 120 skipped (the 120 need a real docker-compose Postgres, correctly skip without one).
- `zerodb serve` is confirmed working end-to-end post-#75 (it crashed on every invocation before that fix).
- API key flow (no key → open; `ZERODB_LOCAL_API_KEY` set → banner + per-page error until the key is pasted in Settings → Connection, after which it works; `--host 0.0.0.0` with no key prints the documented warning to stdout) -- all confirmed against a real server, not mocked.
- Light/dark/system theme and Settings form defaults verified live, not just unit-tested.
- Screenshots in `docs/design/dashboard-redesign/` for all 10 pages in light and dark are from this session's real lite-mode server with real data (replacing the prior fixture-data screenshots for those 20 files). The dialog (`dlg-*`), phone (`phone-*`), and `light-auth-banner.png` screenshots from the prior fixture-data pass were **not** retaken this session -- left as-is; worth a follow-up pass since the auth-banner one in particular now shows a state (#80's false positive) that no longer occurs the way it did when it was captured.

## Not verified / left to do locally

1. ~~**End-to-end against a real lite-mode API.**~~ Done this session (see above). Found and fixed #73, #75, #77, #79, #80 along the way; found and filed #83 (Docker, not fixed) and a `sync_plans` lite-mode gap (not yet filed as its own issue -- see above).
2. ~~**Vector IDs containing `/`.**~~ Fixed in 7895271 (`{vector_id:path}` in `api/routers/vectors.py`). Reconfirmed working this session, both Guided and Advanced JSON upsert and delete, after the `main` merge.
3. ~~**Large uploads.**~~ Fixed in 3915a83: client-side 10 MB guard with a clear error (`MAX_UPLOAD_BYTES` in `dashboard/lib/files.ts`). The API itself still has no limit. Reconfirmed via its unit test this session (see above for why not a live oversized upload).
4. **Live events.** The feed polls every 3s. `POST /events/subscribe` exists; switch to it if there's an SSE/WebSocket channel to read from.
5. ~~**Lite-mode sync tables.**~~ Fixed this session: #73 (`sync_history`) and #79 (`conflict_log`). A related, larger gap remains: `sync_plans` has no lite-mode table at all, blocking `POST /sync/execute` end to end (see above) -- not yet filed as its own issue.
6. **Sync against a real cloud account.** Preview confirmed working this session (real counts from a real lite-mode project). Push/pull execution still not run against a real cloud account -- no `CLOUD_API_KEY` was available this session either. Also blocked in lite mode by the `sync_plans` gap above until that's fixed.
7. **Docker / full mode.** Dashboard's own Docker image builds and runs cleanly (`docker compose build dashboard` succeeds, all 10 routes present in the build output). The full compose stack cannot start at all: see #83 -- `ainative-studio/minio:local` doesn't exist anywhere, and `zerodb-api` hard-depends on `minio` being healthy. Not fixed this session (real infra work, out of scope here). `ZERODB_BIND_ADDRESS=0.0.0.0` publishing on all interfaces instead of loopback could not be verified for the same reason -- the stack never came up.
8. **Next.js 14.2.15 security advisories** (33 npm audit findings) remain. Framework bump is a separate, engineering-owned task.
9. `next start` warns because `next.config.mjs` sets `output: 'standalone'`; for local runs use `node .next/standalone/server.js` (Dockerfile already does).

## Run it

```bash
cd dashboard
npm ci
npm test
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev    # http://localhost:3000
```
