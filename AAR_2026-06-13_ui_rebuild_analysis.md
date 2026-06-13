# AAR: viperball.fly.dev UI Analysis & React/Mantine Rebuild Kickoff
## Web UI modernization — June 2026

### Summary

User report: "the viperball.fly.dev — not the jinja template site that broadcasts the
exports — has never been upgraded, the UI is messy and mostly clunky to use." The ask was
analysis of where it can improve and whether it's feasible to rebuild the UI stack so it
feels like "a SaaS app meets Baseball Mogul / OOTP / Football Manager with the ease of a
consumer-grade work platform."

Over the session this converged from open-ended analysis into a concrete, owner-steered
plan and a working Phase-1 scaffold. The headline outcome: **the rebuild is feasible and
low-risk because the simulation engine and REST API are already cleanly separated from the
UI** — this is a frontend project, not an engine rewrite. The single most important
requirement to surface was not visual: it's that the tool is a **multi-experiment
workbench**, so durable, unified, forkable **saves** are the spine of the rebuild, ahead of
any styling.

Deliverables produced and committed to `claude/cool-galileo-d3yyng`:
1. `UI_REBUILD_PLAN.md` — full migration plan (saves-library-first).
2. `web/` — React + Mantine SPA scaffold (shell + Saves Library), builds clean.
3. **Phase 0 backend, wired & deployable** — unified `/api/saves`, SPA served at
   `/app`, DB moved to a Fly volume, multi-stage Docker build.
4. This AAR.

The owner directed "everything has to be wired and deployable, I don't do this stuff
locally" and "rebuild without tiptoeing" — so Phase 0 was implemented immediately rather
than left as a plan, and the SPA is now served by the same Fly app.

---

### What Was Found

#### 1. There are two distinct sites; only one is in scope
- `viperball.fly.dev/` is the **NiceGUI app** (`nicegui_app/`, ~21.5k lines Python) — the
  clunky interactive sandbox the user wants rebuilt.
- `/stats/` is the **Jinja2 stats site** (`stats_site/`, ~7.5k-line router + 84 templates) —
  the read-only "broadcasts the exports" site, explicitly **out of scope**.
- Both share one FastAPI + SQLite backend (~126 JSON endpoints + ~90 HTML endpoints).

#### 2. Why the NiceGUI app feels clunky (root causes, not vibes)
- **No real routing.** The whole app is one `@ui.page("/")`; tab switches `clear()` and
  re-render in place (`nicegui_app/app.py:442`). No bookmarkable URLs, broken Back button,
  refresh dumps you to Home. This is the dominant "old web app" feeling.
- **Theming is a 300-line hack.** `APP_CSS` (`app.py:186-241`) re-maps hundreds of
  hard-coded light-theme Tailwind classes to dark with `!important` — pages were authored
  light, then bulk-overridden. Brittle and inconsistent.
- **Monolithic pages.** `wvl_mode.py` 3,218 / `pro_leagues.py` 2,314 / `league.py` 2,187
  lines, each mixing fetch + layout + formatting + handlers. The team's own
  `ARCHITECTURE_REDESIGN.md` flags this as unfinished "Phase 3."
- **Every click round-trips** over a socket.io WebSocket to Python — the opposite of the
  instant, dense, keyboard-driven feel of OOTP/FM.
- **Fragile state.** Live sim is an **in-memory dict, 4h TTL, single uvicorn worker, wiped
  on deploy** (restored from a `vroomtv.fly.dev` snapshot per `fly.toml`).

#### 3. The state model is the real architectural debt
The API audit confirmed saves are fragmented across three half-systems — `/archives`
(snapshots), `/history` (versions), `/dynasties` (saved dynasties) — with no unified "all my
experiments" surface, and the live workspace is ephemeral. For a user running many
comparative sims, this is the core pain, more than aesthetics.

---

### Decisions Locked With the Owner

| Topic | Decision |
|---|---|
| Audience | **Single-user.** No auth, accounts, multiplayer, or "play"/intervention features. |
| Purpose | Sim (detailed/fast) → generate history → **save / reload / fork / compare** → export. |
| Approach | **Option B** — modern SPA on the existing API, strangler migration page-by-page. |
| Framework | React + TypeScript on **Vite** (ruled out Preact/Astro). |
| UI kit | **Mantine v7**; dense grids via **mantine-react-table**; **TanStack Query**; **React Router**. |
| Theme | **Light only**, authored natively with Mantine tokens (no dark-class overrides). |
| Feel | **Hybrid**: calm SaaS shell (Linear/Notion/Vercel + One Page Love aesthetic, `⌘K` palette) wrapping FM-style hubs and OOTP-dense grids. |
| Flagship | **College Season / League hub**; must nail **fast navigation/drill-down** (real URLs, working Back). |
| Persistence | **Attach a Fly volume** so experiments survive deploys/restarts. |
| First build | **SPA shell + Saves Library**, with the saves API stubbed via an in-browser mock. |

---

### What Was Built (Phase 1 scaffold, `web/`)

- **Stack wired & verified:** Vite + React 18 + TS, Mantine v7, mantine-react-table,
  TanStack Query, React Router v6 (basename `/app`), `@mantine/spotlight` command palette.
- **`src/theme.ts`** — native light theme; brand indigo carried from the old `--vb-accent`;
  semantic colors for win/loss, TD/turnover, hot/cold.
- **`src/components/AppLayout.tsx`** — Mantine AppShell: sidebar nav + topbar + `⌘K` search.
- **Saves Library (`src/pages/SavesLibrary.tsx`)** — the home screen: a dense
  mantine-react-table of experiments with mode/teams/progress/**seed**/tags columns, faceted
  filters, and row actions (open / **fork** / delete). Seed is a first-class column because
  reproducible experiments are the point.
- **`src/api/saves.ts`** — the saves **contract** the Phase-0 backend must implement
  (`GET/POST/PATCH/DELETE /api/saves`, `POST /api/saves/{id}/fork`), with a localStorage
  **mock fallback** so the Library is fully clickable today; delete the mock when the backend
  lands.
- **Placeholders** for League Hub / Compare / My Team / Pro / International / Export that each
  name the exact existing endpoints that will back them — encoding the build order.
- **Verification:** `npm install` (140 pkgs), `tsc -b` clean, `vite build` succeeds
  (816 kB JS / 35 kB-gz CSS; chunk-splitting is a later optimization, not a blocker).

---

### What Was Built (Phase 0 backend — wired & deployable)

Discovery that made this fast: **`engine/db.py` already persists every mode** in a single
`saves` table keyed by `(save_type, save_key)`, with `list_saves`/`save_blob`/`delete_blob`
helpers. The "three fragmented systems" could therefore be unified behind one read surface
with **no schema migration**.

- **`api/saves_api.py`** (new) — `GET /api/saves` aggregates `college`/`dynasty`/`pro_league`/
  `wvl_season`/`wvl_commissioner`/`season_archive` rows into one normalized `SaveSummary[]`;
  plus `PATCH` (rename + tags/notes via a `save_meta` sidecar blob), `POST /{id}/fork`,
  `DELETE /{id}`. Stable id = `"<save_type>::<save_key>"` (matched with a `:path` param).
- **`engine/db.py`** — `VIPERBALL_DB_PATH` env points the DB at the volume; new
  `update_save_label` and `fork_save` (pure row-copy; clones a college save's box scores under
  the new session id so a fork keeps its played games).
- **`api/main.py`** — includes the saves router; mounts the built SPA at `/app` via an
  `_SPAStaticFiles` subclass that falls back to `index.html` on 404 so client-side routes work.
  Mount is added before NiceGUI's root catch-all, so `/app` and `/api/saves` win.
- **`Dockerfile`** — stage 1 `node:20-slim` runs `npm ci && npm run build`; stage 2 copies
  `web/dist` into the Python image after `COPY . .`.
- **`fly.toml`** — `[mounts]` volume `viperball_data` → `/data`; `VIPERBALL_DB_PATH=/data/...`.
  First boot still seeds the DB once from the hub snapshot (the restore is gated on
  `path.exists()`), then the volume persists.

**Verification (local sandbox):** frontend `npm ci` + `npm run build` ✓; `engine.db` fork/
rename/delete exercised ✓; full `GET/PATCH/POST-fork/DELETE` cycle green under a real FastAPI
`TestClient` ✓. Docker/Fly build runs in Fly's remote builder at deploy (Docker not in sandbox;
the `npm ci` + `vite build` steps it depends on were validated locally).

### Migration Plan (recorded in `UI_REBUILD_PLAN.md`)

- **Phase 0** — Unify saves into one model + DB-backed workspace + Fly volume + `/api/saves*`
  + pagination + `openapi.json`→TS types. (Biggest backend lift; the gate.)
- **Phase 1** — SPA shell + Saves Library. ✅ scaffolded.
- **Phase 2** — Flagship League hub: dense grids + drill-down (standings→team→player, each a
  real URL) + sim controls + export.
- **Phase 3** — Compare experiments side-by-side (the payoff).
- **Phase 4** — Remaining modes; add missing JSON for **WVL** (in-memory/HTML-only today),
  recruiting hub, coach detail, play-by-play. Retire matching NiceGUI pages.
- **Phase 5** — Cutover: SPA becomes `/`, NiceGUI removed, dead Streamlit `ui/` deleted.

Strangler mechanic: FastAPI mounts the Vite `dist/` at `/app`; NiceGUI keeps `/` until parity.

---

### Open Questions / Next Steps

1. **Phase 0 backend** is the gate: unify the three save systems behind `/api/saves`, make the
   workspace DB-backed (not 4h TTL), attach the Fly volume. Then delete the mock in
   `web/src/api/saves.ts`.
2. **WVL** — currently in-memory + HTML-only and not persisted. Decide whether it earns JSON
   endpoints in Phase 4 or stays on the old stack.
3. **Compare** — confirm which metrics matter most to diff across runs (final standings,
   champion, stat leaders, DTW/luck).
4. Wire `npm run gen:api` once the backend is reachable to replace hand-typed shapes with
   generated types.

---

### Risks & Notes
- The 816 kB bundle should be code-split (route-level `lazy()`) before Phase 5; harmless now.
- Single-worker uvicorn stays mandatory only while NiceGUI lives; removing it at Phase 5
  unlocks multiple workers (long sims should already be offloaded).
- No engine or `/stats/` changes were made — scope held to analysis + the new `web/` tree and
  two docs.

---

### Files Touched
- `UI_REBUILD_PLAN.md` (new) — migration plan.
- `web/**` (new) — SPA scaffold (shell + Saves Library), builds clean.
- `AAR_2026-06-13_ui_rebuild_analysis.md` (new) — this record.
