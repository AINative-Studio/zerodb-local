# Dashboard redesign: handoff

Refs #67 · Branch `feat/67-dashboard-redesign`

This branch takes the ZeroLocal dashboard from a read-only viewer to a working tool: every resource can be created from the UI, every page is fully built (no "coming soon"), it uses the ZeroDB brand, and it has light and dark themes. This doc is for whoever finishes it locally. It says what's built, what was decided, where the design and the API disagree, and what's left.

Screenshots of the built pages (light, dark, phone, dialogs) are in [`docs/design/dashboard-redesign/`](../design/dashboard-redesign/). They were taken from a production build with fixture API data, not a live backend.

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
| `/files` | Drag-and-drop or browse upload (multi-file, sequential), list, download, delete |
| `/events` | Feed with family filter chips (`vector.*`, `table.*`…), detail panel with JSON, Live (3s polling) / Paused, **Publish event** dialog |
| `/logs` | Six stat cards replaced by one row of level toggles; service, time-range and line-count filters; search; live refresh; export; always-dark terminal surface |
| `/settings` | Theme, real server values (API URL in use, dashboard origin, backend from `/health`), create-form defaults, cloud sync status + connect with API key |

Shared: the selected project is app-wide (`ProjectProvider`) and shown as a picker in every project-scoped page header, so moving between pages keeps your place. `?new=1` on Projects/Vectors/Tables opens the create dialog (used by Overview and empty states).

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
  services/api-client.ts        createApiClient(http) -- injectable, typed to the real API
  types/index.ts                response types matching api/routers/*.py
  components/providers/         theme-provider, project-provider, query-provider
  components/layout/            sidebar, page-header (+ project picker), mode-badge, theme-toggle, states
  components/ui/                button/badge/input/card (rebranded) + dialog, form-controls
                                (Select, Textarea, Field), segmented, confirm-dialog, copy-field
  components/{projects,vectors,tables,events}/   the create dialogs
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

- `npm test`: **118 passing** (14 files): pure logic, API client (now with an injected HTTP instance; the old suite made real requests to localhost:8000), theme provider, and page-level tests that drive each create flow through the UI.
- `npx tsc --noEmit`, `npm run lint`: clean.
- `npm run build`: all 8 routes prerender.
- Production build loaded in Chromium against fixture API data, every page in light, dark and 390px phone width: **no console errors, no horizontal page scroll**. That pass caught and fixed a hydration mismatch (browser-only values rendered on the server) and table "Actions" labels escaping their scroll box on phones.
- Also fixed two tests already failing on `main`: a timezone-dependent `formatDate` test and the network-calling API client suite.

## Not verified / left to do locally

1. **End-to-end against a real lite-mode API.** Not run here. Lite-mode CRUD for tables, vectors, files and events is blocked server-side by #47 (Postgres-only SQL). Once #47 lands: start the API in lite mode, `npm run dev`, and walk Projects → Vectors → Tables → Files → Events creating one of each.
2. **Vector IDs containing `/`.** Delete calls `DELETE .../vectors/{vector_id}`, and the router matches on `vector_id` (checked). But an ID like `faq/refund-policy` is decoded to a real slash before routing, so it won't reach that route. Either declare the param as `{vector_id:path}` in `api/routers/vectors.py` (same for `GET /{vector_id}`), or have the Upsert form reject `/` in custom IDs.
3. **Large uploads.** Each file is base64-encoded in the browser and posted in one JSON body. Check what the API accepts and add a size guard with a clear message.
4. **Live events.** The feed polls every 3s. `POST /events/subscribe` exists; switch to it if there's an SSE/WebSocket channel to read from.
5. **Memory.** The API stores agent memory (`usage.memory`, `/database/memory`) but there's still no Memory page. Decision #1 says nothing ships as a placeholder; a Memory page is the one gap. Needs a product call.
6. **Next.js 14.2.15 security advisories** (33 npm audit findings) remain. Framework bump is a separate, engineering-owned task.
7. `next start` warns because `next.config.mjs` sets `output: 'standalone'`; for local runs use `node .next/standalone/server.js` (Dockerfile already does).

## Run it

```bash
cd dashboard
npm ci
npm test
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev    # http://localhost:3000
```
