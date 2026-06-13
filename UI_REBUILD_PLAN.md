# Viperball Web UI Rebuild — Plan

> Target: replace the NiceGUI app at `viperball.fly.dev/` with a React + Mantine SPA.
> The Jinja `/stats/` site and the simulation engine are **not** in scope to rewrite —
> the SPA consumes the existing FastAPI API.

## 1. What this is (and isn't)

- **Single-user simulation workbench.** Just the owner. **No auth, no accounts, no
  multiplayer, no "user intervention" features.** Do not build login, permissions, or
  per-user state.
- **Not a game to "play."** The job is: set up leagues → sim (detailed or fast) →
  generate history → edit → **save / reload / compare experiments** → export.
- **Experiments are the point.** The user runs many sims and compares data across runs.
  The unit of work is a *save*, not a *session*. See §3 — this is the spine of the rebuild.

## 2. Design direction (locked with the owner)

| Decision | Choice |
|---|---|
| Framework | **React + TypeScript SPA on Vite** (no meta-framework; ruled out Preact/Astro) |
| UI kit | **Mantine v7** |
| Data grid | **mantine-react-table** (TanStack Table under the hood) |
| Data fetching | **TanStack Query** |
| Routing | **React Router v6** — real deep-linkable URLs, working back button |
| API types | **openapi-typescript** generated from FastAPI `/openapi.json` |
| Charts | Mantine Charts / Recharts (replaces Plotly + P5 layer) |
| Theme | **Light only**, authored natively with Mantine tokens (no dark-class overrides) |
| Feel | **Hybrid**: calm SaaS shell (Linear/Notion/Vercel) + One Page Love aesthetic, wrapping FM-style hubs and OOTP-dense grids |
| Flagship screen | **College Season / League hub** |
| #1 thing it must nail | **Fast navigation/drill-down** — click any team/player → instant entity page with a real URL |

### Aesthetic notes
- One Page Love → generous spacing, strong typographic hierarchy, elegant overview pages.
- Linear/Notion/Vercel → command palette (`Cmd/Ctrl-K`), keyboard nav, fast tables, quiet chrome.
- Football Manager → hub/overview panels, drill-down information architecture.
- Light palette: neutral grays + one indigo accent (brand continuity from current `--vb-accent`),
  semantic colors for W/L, TD/turnover, hot/cold. Tokenized so dark mode is a later toggle, not a rewrite.

## 3. Pillar #1 — Saves & Experiments (the front door)

**The home screen is a Saves Library, not a "create session" button.**

A *save* = a named, persisted sim (college season, dynasty, pro, WVL, or FIV cycle) with metadata:
`name, mode, teams, current week/season, seed, created_at, last_simmed_at, tags/notes`.

Library operations:
- **Open** — load a save back into a live workspace.
- **Duplicate / Fork** — branch an experiment from any point (sim the same setup with a new seed, etc.).
- **Compare** — open 2+ saves side-by-side to diff standings/leaders/outcomes across runs.
- **Rename / Tag / Note** — organize experiments.
- **Export** — standings, box scores, history in existing formats.
- **Delete**.

### Backend work this forces (prerequisite, blocks the SPA)
The audit found the live sim is **in-memory only (4h TTL, wiped on deploy)** and saves are split
across `/archives`, `/history`, and `/dynasties`. Before/alongside the SPA:

1. **Unify saves into one model + table** (`saves`) with consistent metadata, replacing the
   three fragmented systems (or wrapping them behind one `/api/saves` surface).
2. **Make the live workspace DB-backed**, loadable on demand — not a 4-hour TTL dict. Opening a
   save rehydrates state from the DB.
3. **Durable storage on Fly** — attach a volume (or make the snapshot-restore deliberate and
   verified) so deploys never lose experiments.
4. **Save/fork/compare endpoints**: `GET /api/saves`, `GET /api/saves/{id}`, `POST /api/saves`,
   `POST /api/saves/{id}/fork`, `PATCH /api/saves/{id}` (rename/tag), `DELETE /api/saves/{id}`.

## 4. API readiness (from the audit)

- **~126 JSON endpoints** already exist; **~90 stats-site endpoints render HTML** (no JSON).
- College/dynasty/pro/FIV gameplay is **well covered** by JSON. The flagship League hub can be
  built today against: `/sessions/{id}/season/{standings,schedule,polls,power-rankings,awards,
  player-stats,injuries,dtw}`, `/team/{team}`, `/season/roster/{team}`, and the
  `simulate-week|through|rest` mutations.
- **Gaps to add JSON for** (not needed for flagship, but for full parity):
  recruiting hub, **WVL (currently in-memory + HTML only, not persisted)**, coach detail,
  play-by-play detail.
- **No pagination anywhere** — add `limit`/`offset` on schedule / player-stats / injuries before
  long dynasties balloon responses.
- **Response-shape inconsistencies** — optional fields (`full_result`, `prestige_map`) vary by
  context; the generated TS client + Zod-style guards absorb this.

## 5. Migration strategy — strangler, page by page

Run the SPA **alongside** NiceGUI; never big-bang.

- Serve the built SPA from the same Fly app (FastAPI mounts the Vite `dist/` as static at a new
  prefix, e.g. `/app`). NiceGUI keeps serving `/` until parity is reached, then they swap.
- Migrate by pain/traffic; retire each NiceGUI page as its SPA equivalent ships.
- Keep `/stats/` (Jinja) untouched as the shareable export-broadcast surface; optionally fold it
  into the SPA much later (separate decision).

## 6. Phases

**Phase 0 — Foundations (backend)**
Unify the saves model + DB-backed workspace + durable Fly storage + `/api/saves*` endpoints.
Add pagination. Generate `openapi.json` → TS types.

**Phase 1 — SPA shell + Saves Library**
Vite/React/Mantine app, AppShell (sidebar + topbar), command palette, router, TanStack Query,
typed API client. Home = Saves Library (list/open/fork/rename/tag/delete). This proves
navigation + the experiment model.

**Phase 2 — Flagship: College Season / League hub**
Standings + schedule + polls + leaders as dense mantine-react-table grids; sim controls
(week / through / rest, detailed vs fast); **drill-down**: standings → team page → player page,
each with a real URL and working back button. Export surface.

**Phase 3 — Compare experiments**
Side-by-side view diffing 2+ saves (standings, champions, leaders, DTW/luck) — the experiment payoff.

**Phase 4 — Remaining modes**
Dynasty, Pro, FIV/International, My Team, recruiting. Add the missing JSON endpoints (WVL,
recruiting hub, coach, play-by-play) as each lands. Retire matching NiceGUI pages.

**Phase 5 — Cutover**
SPA becomes `/`; NiceGUI removed; delete dead Streamlit `ui/` dir.

**WVL — purpose note (owner, 2026-06-13).** WVL's only value to the owner is as the
**destination for college (CVL) graduates** — the talent pipeline out of the college game,
not a standalone league. The CVL→WVL bridge already exists in the engine
(`engine/wvl_dynasty.py` auto-imports via `load_graduating_pools`/`consume_graduating_pool`;
`api/main.py` tags players with `cvl_source`). The SPA currently ships a basic WVL league
(create / multi-tier standings with pro-rel zones / sim) but does **not yet surface the
graduate import** — that pipeline UI is the remaining WVL work if/when prioritized.

**`/stats` redesign — CANCELLED (owner decision, 2026-06-13).**
The owner is keeping the `/stats` site's existing dense/terminal design as-is and does not
want the SPA's look carried over to it. `/stats` stays untouched (only the DraftyQueenz
banner link was added). Do not restyle `/stats`.

## 7. Effort (rough, single developer-agent)

| Phase | Scope | Rough size |
|---|---|---|
| 0 | Saves unification + persistence + API hardening | Medium — biggest backend lift |
| 1 | Shell + Saves Library | Small–Medium |
| 2 | League hub + drill-down + sim/export | Medium |
| 3 | Compare | Small |
| 4 | Remaining modes + new endpoints | Large (parallelizable per mode) |
| 5 | Cutover + cleanup | Small |

Phases 1–2 are the proof-of-value; if the feel isn't right there, stop and rethink before Phase 4.

## 8. Open questions for the owner

1. Persistence: attach a **Fly volume** (simplest durable answer) vs. keep the snapshot-restore
   model deliberately? (Recommend: volume.)
2. Is **WVL** important enough to build JSON endpoints for in Phase 4, or can it stay on the old
   stack / be dropped?
3. For **Compare**, which metrics matter most to diff across experiments (final standings,
   champion, stat leaders, DTW/luck, something else)?
