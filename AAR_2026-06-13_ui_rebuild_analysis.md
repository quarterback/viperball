# AAR: viperball.fly.dev UI Rebuild — React/Mantine SPA
## Comprehensive after-action — June 13, 2026

---

## 1. Assignment

> "the viperball.fly.dev — not the jinja template site that broadcasts the exports — has
> never been upgraded, the UI is messy and mostly clunky to use… analysis around where it can
> be improved including whether it's feasible to rebuild the UI stack so that it's easier and
> more pleasant to use — think SaaS app meets Baseball Mogul/OOTP/Football Manager with the
> ease of using a consumer-grade work platform."

What began as an analysis request became a full, owner-steered rebuild executed in one session:
analysis → migration plan → API audit → a working React + Mantine SPA covering every mode →
a verified dead-code sweep. All on branch `claude/cool-galileo-d3yyng` / PR #310.

---

## 2. Starting point (what was wrong)

`viperball.fly.dev/` is the **NiceGUI app** (`nicegui_app/`, ~21.5k lines Python on Quasar/Vue
over a socket.io WebSocket). The `/stats/` Jinja site (the "export broadcaster") was explicitly
out of scope. Root causes of the clunk, verified in code, not vibes:

- **No routing.** Whole app is one `@ui.page("/")`; tab switches `clear()`+re-render in place
  (`nicegui_app/app.py:442`). No bookmarkable URLs, broken Back button, refresh resets you.
- **Theming was a 300-line hack.** `APP_CSS` re-mapped hundreds of hard-coded light Tailwind
  classes to dark with `!important` (`app.py:186-241`).
- **Monolith pages.** `wvl_mode.py` 3,218 / `pro_leagues.py` 2,314 / `league.py` 2,187 lines.
- **Every click round-trips** over the WebSocket — the opposite of the dense, instant OOTP feel.
- **Ephemeral state.** Live sim is an in-memory dict (4h TTL, single uvicorn worker, wiped on
  deploy, restored from a hub snapshot). Saves were fragmented across `/archives`, `/history`,
  `/dynasties` with no unified "experiments" view.

**Verdict: feasible and low-risk** — the engine and a ~126-endpoint REST API are already
decoupled from the UI. This was a frontend project, not an engine rewrite.

---

## 3. Decisions locked with the owner

| Topic | Decision |
|---|---|
| Audience | **Single-user.** No auth/accounts/multiplayer/"play" features. |
| Purpose | Sim (detailed/fast) → generate history → **save / reload / fork / compare** → export. The unit of work is a *save / experiment*, not a session. |
| Stack | **React + TypeScript on Vite** (no meta-framework), **Mantine v7**, **mantine-react-table**, **TanStack Query**, **React Router v6**. |
| Theme | **Light only**, authored natively with Mantine tokens (brand indigo carried from `--vb-accent`). |
| Feel | **Hybrid**: calm SaaS shell (Linear/Notion/Vercel + One Page Love) with `⌘K` palette, wrapping FM-style hubs and OOTP-dense grids. |
| Flagship | College Season / League hub; must nail **fast navigation/drill-down**. |
| Persistence | **Fly volume** for durable saves. |
| Migration | **Strangler** — SPA served at `/app`, NiceGUI stays at `/` until parity. |

---

## 4. What was built (by phase)

**Phase 0 — Foundations (backend), deployable.**
Discovery: `engine/db.py` already persists every mode in one `saves` table, so the fragmented
save systems could be unified behind one read surface with **no schema migration**.
- `api/saves_api.py` — `GET /api/saves` aggregates college/dynasty/pro/wvl/archive rows into one
  normalized `SaveSummary[]`; `PATCH` (rename + tags/notes sidecar), `POST /{id}/fork`, `DELETE`.
  Id = `"<save_type>::<save_key>"`.
- `engine/db.py` — `VIPERBALL_DB_PATH` env points the DB at the volume; `fork_save` (clones a
  college save's box scores under the new id) + `update_save_label`.
- `api/main.py` — serves the built SPA at `/app` via an `_SPAStaticFiles` 404→index.html
  fallback; includes the saves router; adds `GET /api/sessions/college` (the hub's picker).
- `Dockerfile` — multi-stage: node builds the SPA, python image copies `web/dist`.
- `fly.toml` — `[mounts]` volume `viperball_data` → `/data`; first boot still seeds the DB once
  from the hub snapshot (restore gated on `path.exists()`), then the volume persists.

**Phase 1 — Shell + Saves Library.** Vite/React/Mantine AppShell (sidebar + topbar + `⌘K`),
TanStack Query, router. Home = Saves Library: open / fork / rename / tag / delete experiments.

**Phase 2 — College / League hub (flagship).** Session picker; four dense grids (Standings /
Schedule / Polls / Leaders); Sim-Week / Sim-Rest; **drill-down** standings → team page → player
page, each a real deep-linkable URL with breadcrumbs + working Back.

**Phase 2.5 — New Season wizard.** 2-step Stepper (identity + **seed** / format); `POST /sessions`
then `/sessions/{id}/season`; seed dice for reproducible experiments. SPA is now standalone for
college — create → sim → browse without touching NiceGUI.

**Phase 3 — Compare runs.** Pick 2–4 active seasons; a team-keyed pivot shows each team's record
per run with a **Δ Wins** spread column sorted to surface divergence. The experiment payoff.

**Phase 4 — All remaining modes** (shapes extracted by a background agent; shared `useDataGrid`):
- **Pro Leagues** — start any of 5 leagues; division standings, schedule, category stat leaders,
  playoff bracket, sim.
- **International (FIV)** — world rankings, World Cup groups + knockout, New-Cycle / Sim-Stage.
- **Dynasty** — load a saved career into a session; coach card, team histories, awards, records.
- **My Team** — roster-builder dashboard: NIL budget pools, roster, retention risks, portal.
- **Export** — standings-JSON download, archive action, archive browser.
- Engineering: vendor chunk splitting → app bundle ~14 KB gzip.

**Dead-code sweep (pre-cutover).** Removed 17 verified-dead files: the legacy Streamlit UI
(`ui/app.py`, `ui/helpers.py`, `ui/page_modules/**`) and the Tkinter desktop app
(`viperball_gui.py`, `launch_gui.sh`). Kept `ui/api_client.py` (still imported by NiceGUI).

---

## 5. Deploy / ops notes

Two deploy issues surfaced and were handled:

1. **`.gitignore` ate a source file (fixed).** Root `.gitignore` is a Python template; its
   `lib/` rule silently excluded `web/src/lib/queryClient.ts`, so it was never committed and the
   Fly/Depot build failed (`tsc: Cannot find module './lib/queryClient'`). Local builds passed
   because the file was on disk. Fixed with a scoped negation (`!web/src/**`) so `lib/`/`build/`/
   `dist/` can never swallow frontend source again.

2. **Volume must exist before deploy (action required).** `[mounts]` auto-create only applies to
   fresh `fly launch`; with machines already running, Fly requires the volume to be created
   manually. The app currently has **2 machines in `ams`**, so deploy asks for 2 volumes.
   - **Recommended (matches the architecture):** run a **single machine** — NiceGUI requires a
     single in-process worker and the saves DB should be one consistent store, not split across
     per-machine volumes. `fly scale count 1 --region ams`, then
     `fly volume create viperball_data -r ams -n 1`, then redeploy.
   - Alternative (2 volumes) would give each machine its own DB → divergent saves; not advised
     for a single-user store.

---

## 6. What's left

**Phase 5 — cutover (deliberately not done yet).** Promote `/app` → `/`, retire `nicegui_app/`,
remove `ui/api_client.py`. This is a one-way door that removes the only verified-working UI, and
the SPA hasn't been exercised against the live backend (deploy hadn't succeeded at time of
writing). Sequence: deploy → click through `/app/` for parity → then cut over.

**Unverified locally:** each mode's live JSON matching the hand-written TypeScript types. The
saves API was validated end-to-end under a real FastAPI `TestClient`; the season/pro/fiv/dynasty/
my-team responses were typed from a code audit, not a running server (FastAPI isn't installed in
the build sandbox). First live pass may need small field-name corrections.

**Deferred features:** WVL has no JSON API (in-memory/HTML only) — not ported; recruiting hub,
coach detail, and play-by-play also lack JSON. Dynasty create/advance and My Team write-actions
(bid/retain/finalize) are read-first for now.

---

## 7. Key decisions & rationale

- **Unify saves by reading existing tables, not migrating** — the `saves` table already held
  everything; a thin aggregation router beat a risky data migration.
- **Single grid hook (`useDataGrid`)** — one dense, faceted, searchable config across every
  screen keeps the OOTP feel consistent and the pages thin.
- **Strangler over big-bang** — SPA at `/app`, NiceGUI at `/`, retire page-by-page. No moment
  where the app is half-broken.
- **Seed as a first-class field** — the wizard and Saves Library surface the RNG seed because
  the owner's core workflow is comparing many runs.

---

## 8. Lessons

- **A Python repo's default `.gitignore` is a landmine for an embedded JS app.** `lib/`, `build/`,
  `dist/`, `var/` silently drop source; only a from-git build (Depot) reveals it. Guard the JS
  subtree explicitly.
- **"Builds locally" ≠ "builds in CI"** when files exist on disk but not in git. Parity check
  (`git ls-files` vs `find`) catches it.
- **Surface architecture truths early** — that college seasons are in-memory-only reframed the
  whole saves model and the League Hub's session-picker design.

---

## 9. File inventory (this branch)

- **New frontend:** `web/**` — Vite/React/Mantine SPA (shell, Saves Library, League hub +
  drill-down, New Season wizard, Compare, Pro, International, Dynasty, My Team, Export).
- **New backend:** `api/saves_api.py`; `GET /api/sessions/college` + `/app` mount in
  `api/main.py`; `fork_save`/`update_save_label`/`VIPERBALL_DB_PATH` in `engine/db.py`.
- **Ops:** multi-stage `Dockerfile`; `[mounts]` + `VIPERBALL_DB_PATH` in `fly.toml`; `.gitignore`
  negation.
- **Removed:** legacy Streamlit UI + Tkinter app (17 files).
- **Docs:** `UI_REBUILD_PLAN.md`, this AAR.
