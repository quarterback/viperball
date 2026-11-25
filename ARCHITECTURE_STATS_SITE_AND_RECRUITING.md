# Viperball application architecture

Current reference after the November 2026 UI consolidation. The older two-site/read-only terminal model is superseded by one Python application with league browsing and management in the stats site.

## One process, shared data

```text
Browser -> FastAPI (api/main.py)
             /stats/ -> Jinja2 sub-application -> live session and SQLite
             /api/   -> simulation / management actions
             NiceGUI -> remaining interactive pages
                          |
                       engine/
                          |
                        data/
```

main.py imports the FastAPI app, registers NiceGUI routes and mounts NiceGUI. Uvicorn serves main:fastapi_app. The Dockerfile uses Python 3.11 and one worker to preserve in-process session state. The stats router is mounted as a sub-application, so its path prefix and routing precedence matter. Do not restore the retired React app or build a parallel session system.

stats_site/router.py obtains live API references lazily and uses templates extending base.html. Read-only analytics lives in stats_site/analytics_portal.py. Management POSTs call existing application actions (including season advance and the dynasty hub). The router caches season aggregation against session-season identity and completed-game count. Do not mutate result dictionaries when constructing derived views; maintain explicit missingness and consistent denominator definitions.

## Recruiting source of truth

A dynasty owns its high-school league and its tracked prospects. engine/hs_league.py provides persistent player identity and competition results; engine/college_feeder.py connects the tracked graduating cohort to college recruiting, carries returning prospects, and handles the reserve for walk-ons. The API and standalone offseason path use the same feeder contract. CPU targeting incorporates school/caller fit and funded position teaching; the user controls their recruiting board.

The former /stats/recruiting tree is deprecated and redirected to /stats/dynasty/. Recruitment actions belong to the live dynasty, not a separately generated recruitment website. High School is a view into the same feeder. Do not create a duplicate recruit for a player who already has an identity.

## Storage

engine/db.py handles SQLite persistence, game records and saves. Full result data is the evidence for game and season reporting. Live sessions, archives and older incomplete records are different sources; do not fabricate missing play events or attribute points from a final score alone. Current development assumes fresh seasons. Database location is configurable with VIPERBALL_DB_PATH.

## Running and deploying

Local: install requirements.txt and run python main.py; default port 5000. Production: Dockerfile runs Uvicorn on port 8080, one worker; fly.toml defines the viperball Fly app, persistent /data volume, rolling strategy and /api/health check. VIPERBALL_BUILD_SHA is included in build provenance. The configured restore URL is for initial database restoration when a persistent database is absent. The machine is configured for manual start/stop; requests do not wake a stopped machine.

Verify deployed health and revision, create a fresh season, simulate a week, check game/analytics routes, and test persistence before claiming deployment. No live deployment claim follows from the configuration alone.

See [stats site routes](docs/stats-site.md), [engine](ENGINE_README.md), [quick start](QUICKSTART.md) and [current plan](docs/DEVELOPMENT_PLAN.md).
