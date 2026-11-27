# Quick start

## Run locally

Use Python 3.11 or later. From a checkout of the repository:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`. Open [http://localhost:5000/stats/](http://localhost:5000/stats/). Alternatively run `uvicorn main:fastapi_app --host 127.0.0.1 --port 5000 --workers 1`. The engine and both browser surfaces run in the same process. Use the pinned requirements; no npm build, Tkinter, Streamlit or old desktop launcher is needed.

## Choose a mode

| Goal | Where to begin |
|---|---|
| Play one game | /stats/game-sim |
| Run a college season | /stats/college/new |
| Build or import a custom playbook | /stats/playbooks |
| Manage a college program across years | /stats/dynasty/new |
| Find current sessions and saves | /stats/ and /stats/saves |
| Follow the high-school feeder | /stats/high-school/ |
| Browse professional leagues | /stats/pro/ |
| Follow the women's league | /stats/wvl/ |
| Follow international competition | /stats/international/ |

In a college season, choose the programs and settings, select your offense and defense when applicable, complete or skip the portal stage, then simulate a week or the remaining games. The season page has controls for the postseason. A dynasty adds annual recruiting, player development, retention, staff changes and a new season.

The supplied school files provide the source data. The game creates rosters; you do not need to generate every roster before playing. The actual league size and schedule depend on your selected settings and the available school files.

## Build a custom playbook

Open the **Playbook Cookbook** from My Team or either college setup page. Choose offense or defense and a base school. Add up to four compatible packages. Preview a concept on the field and optionally give one package priority when it is eligible. Save the book, then select it for the appropriate side when creating a college season or dynasty. The chosen book sets that side's base school. The coordinator still uses the base school when no package fits the situation.

Enable **Let computer teams use saved playbooks** at setup to put some of your library into AI teams’ hands. This also works in an all computer college season. Teams draw from books that fit their school and roster.

Use **Download JSON** to share a saved book. Importing a file opens a draft you can preview before saving. After a game, **Custom playbook usage** in the box score shows eligible, selected, and executed package calls with links to their snaps.

## Study a game

Open Schedule, select a completed game, then inspect the scoring ledger, team and player statistics, drives, defensive calls, line changes and play-by-play. A box score links directly to Analytics play and drive searches.

From the season menu, choose **Analytics**. Use the thirteen views described in [ANALYTICS.md](ANALYTICS.md). Try Play finder with down 6, group by offensive school, then drill into an individual result. State-value estimates need enough completed games in earlier weeks; blank cells mean unavailable, not zero.

## Saves and deployment

The application uses live sessions with SQLite persistence. Use the game's saves, import/export and archive controls; do not copy or edit the database while a session is writing to it. Back up your data before changing revisions. The current development target is newly created seasons; old-save compatibility is not promised.

Set VIPERBALL_DB_PATH to select a database location. In production, fly.toml mounts /data and uses /data/viperball.db. For local troubleshooting, check /api/health (including build_sha when supplied), the server terminal and the actual page URL. The Fly configuration disables automatic wake-up; a stopped machine must be started deliberately.

See [architecture](ARCHITECTURE_STATS_SITE_AND_RECRUITING.md) for deployment details and [development plan](docs/DEVELOPMENT_PLAN.md) for validation status.
