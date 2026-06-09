# Architecture: `viperball.fly.dev` → `viperball.xyz`, the Stats Terminal, and the Recruiting Site

> **Why this doc exists:** a reference explanation of how the deployed app, the
> public stats terminal, and the recruiting section are wired together — written
> so it can be handed to an agent (or a future me) to understand the
> architecture/design before building a similar read-only "feed" site (e.g. a
> juniors tour / recruiting page for the tennis simulation).

---

## One process, two faces

There is **a single Python app** deployed on Fly.io (`app = 'viperball'` in
`fly.toml`, served on internal port 8080). It is **not** two services.
`main.py` boots one FastAPI app and then mounts NiceGUI onto it via
`ui.run_with(fastapi_app, ...)`. So a single uvicorn process serves:

- **NiceGUI** — the interactive *simulator* frontend (Vue under the hood). This
  is where seasons / dynasties / pro cycles actually get run. Routes registered
  in `nicegui_app/`.
- **FastAPI** — the JSON API (`api/main.py`) plus a **mounted sub-app at
  `/stats`** (`stats_site/`), which is the read-only, server-rendered
  "Bloomberg-terminal" stats site.

`viperball.fly.dev` and `viperball.xyz` are **the same machine**. The only
difference is a tiny ASGI middleware in `api/main.py`
(`DomainRedirectMiddleware`): if the request `Host` is `viperball.xyz` and the
path is `/`, it 302-redirects to `/stats/`. So `viperball.xyz` is just "the fly
app, but the front door drops you straight into the stats terminal instead of
the simulator." `viperball.fly.dev` lands on the NiceGUI sim; `viperball.xyz`
lands on `/stats/`.

```
                    one uvicorn process on Fly.io
   ┌─────────────────────────────────────────────────────────┐
   │  FastAPI app (api/main.py)                                │
   │   ├── DomainRedirectMiddleware  (xyz/ → /stats/)          │
   │   ├── /api/...        JSON sim API                        │
   │   ├── /stats   ──►  mounted sub-app (stats_site/router.py)│
   │   │                  Jinja2 server-rendered, no JS framework
   │   └── Mount("")  ──► NiceGUI sim UI (nicegui_app/)        │
   └─────────────────────────────────────────────────────────┘
   viperball.fly.dev → sim UI      viperball.xyz → /stats terminal
```

### Key files

| Concern | Where |
|---|---|
| Process entrypoint (mounts NiceGUI onto FastAPI) | `main.py` |
| FastAPI app, JSON API, domain redirect, `/stats` mount | `api/main.py` |
| Stats terminal router (all `/stats/...` routes) | `stats_site/router.py` |
| Stats terminal templates (Jinja2) | `stats_site/templates/` |
| Stats terminal nav / themes / shell | `stats_site/templates/base.html` |
| Sim UI | `nicegui_app/` |
| Fly deploy config | `fly.toml` |

---

## How data "feeds" from the sim into the stats site

This is the important part, and it's simpler than it looks: **there is no export
step, no second database call, no HTTP hop.** The stats site reads the
simulator's **live in-memory state directly**, because they're in the same
process.

When you run a season in the NiceGUI sim, the resulting objects live in
module-level dicts in `api/main.py`: `sessions`, `pro_sessions`, `wvl_sessions`,
plus FIV (international) cycle state. The stats router pulls them in lazily via
`_get_api()` (`stats_site/router.py`), which just imports those dicts and the
serializer functions. Helpers like `_find_all_sessions()`,
`_get_recruiting_pipeline()`, etc. walk that shared state and hand it to Jinja2
templates. The router's own docstring says it plainly: *"All data comes from the
in-memory sessions/pro_sessions/FIV state — no extra HTTP calls."*

So the flow is:

```
sim runs  →  mutates shared in-memory state  →  /stats templates render
             (sessions / pro_sessions /         whatever is currently in
              wvl_sessions / FIV)                that state
```

The terminal "updates in real time as simulations run" for exactly this reason.

Archived / saved seasons additionally come from a DB layer via `_get_archives()`
/ `_get_all_saved_data()`, for leagues no longer held in memory.

---

## How the recruiting site specifically works

Recruiting is just one **section** of the `/stats` terminal — same pattern as
College / Pro / WVL / International. Nav lives in `base.html`; the recruiting
routes and templates are:

- **Routes** (`stats_site/router.py`), all under `/stats/recruiting/`:
  - `/recruiting/` → `index.html` (top prospects)
  - `/recruiting/hs-rankings` → `hs_rankings.html`
  - `/recruiting/draft-classes` → `draft_classes.html`
  - `/recruiting/pro-pipeline` → `pro_pipeline.html`
  - `/recruiting/signing-tracker` → `signing_tracker.html`
  - `/recruiting/recruit/{recruit_id}` → `recruit_profile.html` (individual
    profile w/ rankings, shortlist, crystal ball)
  - `/recruiting/commissioner` → admin view (force-sign etc.)
- **Templates**: `stats_site/templates/recruiting/*.html`, all extending
  `base.html`.

The data source is the engine's recruiting pipeline. `_get_recruiting_pipeline()`
reaches into the active dynasty/session, grabs the `HSRecruitingPipeline` (from
`engine/recruiting.py`), seeds interest data if missing, and exposes things like
`pipeline.get_top_prospects(...)`, per-grade classes, offers, and rankings. The
route handler reshapes those engine objects into plain dicts and the Jinja
template presents them. Faces are generated pixel-art served from
`/stats/static/faces/<id>.png` (and a recruit's `recruit_id` becomes their
`player_id` once they sign, so the same face follows them).

So "presentable format" =

```
engine produces raw objects  →  stats router is a thin read-only adapter
                                 that reshapes + ranks them
                              →  renders Jinja templates in the terminal aesthetic
```

Zero client-side framework; themes / keyboard shortcuts come free from
`base.html`.

---

## Applying this to the tennis simulation's juniors tour / recruiting page

The pattern to copy is: **keep the simulation as the source of truth, and add a
thin read-only presentation layer that reads its state and renders server-side
templates.** Two ways to mirror it:

1. **Same-process (what Viperball does):** mount a stats sub-app/router on the
   tennis sim's web server; have it import the sim's in-memory state and render
   Jinja templates. No export, live updates. Best if the tennis sim is already a
   Python web app.
2. **Decoupled feed:** if the tennis sim and the public page are separate
   deployments, have the sim emit JSON (or write to a shared DB), and a small
   FastAPI + Jinja "terminal" reads that feed. Same presentation layer, but the
   "feed" is an actual data handoff instead of shared memory.

Either way the design principle is identical to Viperball's recruiting section:

```
engine objects in  →  thin adapter reshapes / ranks  →  Jinja server-rendered
                                                          page out, under a
                                                          /recruiting-style
                                                          section of a
                                                          terminal-styled
                                                          read-only site
```
