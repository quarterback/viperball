# Viperball Stats Site

Read-only stats browser for all Viperball leagues. Accessible at `/stats/` when the app is running.

## Architecture

- **Framework**: Jinja2 templates on the existing FastAPI app (no new server or process)
- **Data source**: Reads directly from in-memory session state (zero HTTP overhead)
- **Styling**: Dark monospace Bloomberg-terminal aesthetic with dense, hyperlinked tables
- **Dependencies**: None beyond what FastAPI/Starlette already provides (Jinja2 ships with Starlette)

### File Layout

```
stats_site/
  __init__.py
  router.py                  # 22 GET routes on an APIRouter
  templates/
    base.html                # Shared layout: topbar, nav, CSS, footer
    home.html                # Dashboard showing all active sessions
    search.html              # Cross-league search
    college/
      index.html             # List of active college seasons
      season.html            # Season overview (poll + standings)
      standings.html         # Full standings with conference breakdowns
      schedule.html          # Week-by-week schedule with box score links
      polls.html             # Weekly rankings with power index, SOS, bid type
      team.html              # Team page: roster, metrics, schedule
      game.html              # Box score: team stats, player stats, drives, play-by-play
      players.html           # Season stat leaders (sortable/filterable)
      awards.html            # Season awards
    pro/
      index.html             # List of active pro leagues
      season.html            # Division standings
      schedule.html          # Full schedule
      game.html              # Box score with play-by-play
      team.html              # Team detail with roster
      stats.html             # Stat leaders
    international/
      index.html             # FIV cycle overview
      rankings.html          # Full world rankings
      confederation.html     # Continental championship detail
      worldcup.html          # World Cup groups, bracket, awards
      team.html              # National team roster
```

### How It Wires In

The router is included in `api/main.py` right after the FastAPI app is created:

```python
from stats_site.router import router as stats_router
app.include_router(stats_router)
```

All data access uses lazy imports from `api.main` to avoid circular dependencies. The helper `_get_api()` returns references to the live `sessions`, `pro_sessions`, and serialization functions.

## Routes

### Global

| Route | Description |
|-------|-------------|
| `GET /stats/` | Home dashboard — lists all active college seasons, pro leagues, FIV cycles |
| `GET /stats/search?q=...` | Cross-league search for teams, players, and nations |

### College (CVL)

| Route | Description |
|-------|-------------|
| `GET /stats/college/` | Index of active college seasons |
| `GET /stats/college/{session_id}/` | Season overview with latest poll and top 25 standings |
| `GET /stats/college/{session_id}/standings` | Full standings with conference breakdowns and advanced metrics |
| `GET /stats/college/{session_id}/schedule?week=N` | Schedule with scores, filterable by week |
| `GET /stats/college/{session_id}/polls?week=N` | Weekly poll rankings with power index, quality wins, SOS |
| `GET /stats/college/{session_id}/team/{team_name}` | Team page: roster sorted by OVR, metrics dashboard, schedule |
| `GET /stats/college/{session_id}/game/{week}/{idx}` | Box score: team stats, player stats, drive summary, play-by-play |
| `GET /stats/college/{session_id}/players?sort=X&conference=Y` | Season player stat leaders, sortable and filterable |
| `GET /stats/college/{session_id}/awards` | Season awards (individual, coach of year, all-conference) |

### Pro Leagues

| Route | Description |
|-------|-------------|
| `GET /stats/pro/` | Index of active pro league sessions |
| `GET /stats/pro/{league}/{session_id}/` | Division standings |
| `GET /stats/pro/{league}/{session_id}/schedule` | Full schedule by week |
| `GET /stats/pro/{league}/{session_id}/game/{week}/{matchup}` | Box score with play-by-play |
| `GET /stats/pro/{league}/{session_id}/team/{team_key}` | Team detail with roster and schedule |
| `GET /stats/pro/{league}/{session_id}/stats?category=X` | Stat leaders by category |

### International (FIV)

| Route | Description |
|-------|-------------|
| `GET /stats/international/` | FIV cycle overview with confederations and top 20 rankings |
| `GET /stats/international/rankings` | Full world rankings with tier badges |
| `GET /stats/international/confederation/{conf}` | Continental championship: groups, results, knockout |
| `GET /stats/international/worldcup` | World Cup: groups, knockout bracket, awards |
| `GET /stats/international/team/{code}` | National team roster with caps and CVL source |

## Features

### Box Scores

Every completed game gets a full box score page showing:

- **Scoreboard** with final score, home/away labels, game tags (CONF, RIV)
- **Team stats comparison** table (yards, plays, TDs, kicks, laterals, fumbles, efficiency)
- **Player stats** for both teams (touches, yards, TDs, fumbles, laterals, kicks, tackles, sacks)
- **Drive summary** (quarter, start position, plays, yards, result — scoring drives highlighted)
- **Full play-by-play** with:
  - Quarter/time/possession/field position/down-and-distance
  - Play family tags (color-coded: yellow for scoring, red for turnovers)
  - Yards gained and EPA per play
  - Full description text
  - Client-side quarter filter (click Q1/Q2/Q3/Q4 to filter)
  - Row highlighting: dark yellow for scoring plays, dark red for turnovers

### Search

Cross-league search accessible from the nav bar. Searches:

- **College teams** by name, mascot, or abbreviation
- **College players** by name (shows team, position, OVR, year)
- **Pro teams** by name or key
- **FIV nations** by code or name

Results are grouped by category with direct links to the relevant detail pages.

### Player Stats

Season-aggregated player statistics across all completed games:

- Sortable by: yards, TDs, touches, YPC, tackles, sacks, kick%, kick pass yards, fumbles
- Filterable by conference
- Shows: games played, touches, yards, Y/T, TDs, fumbles, laterals, kick attempts/made/%, tackles, TFL, sacks, return yards

### Standings

- **Overall standings** sorted by win percentage with 16 columns of advanced metrics
- **Conference standings** with conference record, overall record, PF/PA, rating, PPD
- Color-coded point differential and team rating

### Visual Design

Dark monospace terminal aesthetic:
- Background: `#0a0a0a`, text: `#c8c8c8`, accent: `#ff6600`
- Green for wins/good stats, red for losses/bad stats, yellow for elite/scoring
- Tabular-nums for all numeric columns
- Sticky column headers
- Dense tables with hover highlighting
- Responsive grid layouts that collapse to single column on mobile
- Tags with colored borders for positions (cyan), conferences (blue), rivalry (red), playoff (yellow)

## Adding New Pages

1. Add a route in `stats_site/router.py`
2. Create a template in `stats_site/templates/` extending `base.html`
3. Use `_get_api()` for lazy access to session data
4. Pass `section="college"` (or `"pro"`, `"international"`, `"search"`) for nav highlighting
5. Use `_ctx(request, ...)` to build template context
