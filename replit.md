# Viperball Simulation Sandbox

## Overview
Browser-accessible simulation sandbox for the Collegiate Viperball League (CVL) engine. Designed for playtesting, debugging, and tuning game mechanics from phone, tablet, or laptop.

This is NOT a consumer app — it's a playtest + debugging environment.

## Architecture

```
engine/           - Core Python simulation engine
  game_engine.py  - Main simulation logic (ViperballEngine, styles, play families)
  box_score.py    - Box score generation
  poll_system.py  - Poll/ranking system
  __init__.py     - Package exports
api/              - FastAPI REST endpoints (standalone API access)
  main.py         - /simulate, /simulate_many, /debug/play, /teams
ui/               - Streamlit web UI
  app.py          - 3-page sandbox (Game Simulator, Debug Tools, Play Inspector)
engine/epa.py     - EPA (Expected Points Added) calculation module
data/teams/       - Team JSON files (7 teams)
main.py           - Entry point (launches Streamlit on port 5000)
.streamlit/       - Streamlit configuration
```

## Running
The app runs via `python main.py` which launches Streamlit on port 5000.

## Key Features

### Engine
- **Style System**: 5 offense styles (power_option, lateral_spread, territorial, option_spread, balanced)
- **Play Families**: dive_option, speed_option, sweep_option, lateral_spread, territory_kick
- **Deterministic Seeds**: Every sim accepts a seed for reproducibility
- **Scoring**: Touchdowns = 9pts, Snap Kicks = 5pts, Field Goals = 3pts, Safeties = 2pts, Pindowns = 1pt, Strikes = 0.5pts
- **AFL-style kicking**: ~52% of plays are kicks (punts, snap kicks, field goals). Contextual kick triggers based on down/distance/field position
- **Snap kick accuracy**: Tiered success (100%/92%/80%/60% by distance range), viable offensive weapon
- **Field goal accuracy**: Tiered success (95%/88%/75%/55% by distance)
- **CFL Rouge/Pindown**: 1pt awarded when kick lands in end zone and receiver can't return out. Applies to punts, missed snap kicks, missed field goals
- **Strikes**: Fumble recovery by opposing team awards 0.5pts (fractional scoring supported)
- **Lateral risk system**: 5-7% base fumble, +4% per additional lateral, +8-10% under pressure, +6% cross-field, +5% if fatigued
- **Chaos mechanics**: 4% tipped punts (12% kicking team recovery), 7% chaos bounces, 8% punt return TDs, contested recoveries
- **Fatigue tracking**: Per-play fatigue logged in play-by-play
- **Breakaway system**: 12+ yard runs can explode into big plays based on speed/fatigue
- **Red zone TD model**: Inside 85/93 yard line, TD probability spikes (requires 2+ yards gained)
- **Defensive fatigue scaling**: Long drives (5/8/12+ plays) degrade defense by 1.05/1.15/1.25x
- **Lateral chain compounding**: Each lateral in chain adds 5% explosive chance

### Position Tag System
- Players identified by position abbreviation + jersey number (e.g. VB1, HB13, WE8, CB11)
- Position mappings: viperback→VB, halfback→HB, wingend→WE, winglet→WI, center_back→CB, zone_end→ZE, linebacker→LI, winglock→WL, sweeper_back→SB

### Drive Tracking
- Every possession logged with: team, quarter, start yard line, plays, yards, result
- Results: touchdown, successful_kick, fumble, turnover_on_downs, punt, missed_kick, pindown, punt_return_td, chaos_recovery, stall (quarter end)
- Drive yards count positive non-punt gains only

### UI Pages (5 views per game)
1. **Game Simulator**
   - Real box score: quarter-by-quarter scoring + scoring breakdown (TD/DK/PK with point values)
   - Play family distribution: grouped bar chart comparing team play call %
   - Drive outcome panel: table of all drives + outcome distribution chart
   - Play log: position-tagged descriptions with quarter filter
   - Debug panel: fatigue curves, explosive plays, turnover triggers, kick decisions, style params
   - Export: download box score (.md), play log (.csv), drives (.csv), full JSON
2. **Debug Tools** - Batch sims (5-200), averages, fatigue curves, turnover rates, drive outcome aggregation
   - Export: batch summary (.csv), all games (.json), full data + plays (.json)
3. **Play Inspector** - Run single plays repeatedly with situation controls
   - Export: play results (.csv)

### API Endpoints
- `POST /simulate` - Single game
- `POST /simulate_many` - Batch games with averages
- `POST /debug/play` - Single play resolution
- `GET /teams` - List teams + styles

## Teams Available
creighton, gonzaga, marquette, nyu, ut_arlington, vcu, villanova

## Tuning Diagnostics (50-sim, Gonzaga vs Villanova)
- Avg score: 31-36 per team
- Kick %: 52.5% (target: ~53%)
- Pindowns: 3.3/game (range 0-7)
- Lateral efficiency: 75.5% (target: 65-80%)
- Kick % range: 43.8-60.7%

## Recent Changes
- 2026-02-15: Integrated AFL-style engine: 52% kicks, CFL rouge/pindown (1pt), chaos mechanics, enhanced lateral risk
- 2026-02-15: Tiered kicking accuracy (drop kicks + place kicks), contextual kick triggers
- 2026-02-15: UI updated with pindown stats, kick %, lateral efficiency, punt return TDs in box scores and batch tools
- 2026-02-15: Added position tag system (VB1, HB13, etc.) replacing generic player names
- 2026-02-15: Added drive summary tracking (team, quarter, start yd, plays, yards, result per possession)
- 2026-02-15: Overhauled Game Simulator UI with 5 views: box score, play family chart, drive panel, role-tagged play log, debug panel
- 2026-02-15: Built complete sandbox (engine styles, FastAPI, Streamlit UI)
- 2026-02-15: Added EPA (Expected Points Added) engine with EP table, down multipliers, lateral penalties, chaos bonuses
- 2026-02-15: EPA integrated into play-by-play (ep_before, epa per play), team stats (total/offense/special teams/chaos EPA)
- 2026-02-15: Cumulative EPA chart in Game Simulator, batch EPA averages in Debug Tools
- 2026-02-15: Added 3rd/4th/5th down conversion rate tracking and display
- 2026-02-15: Renamed terminology: Drop Kicks→Snap Kicks, Place Kicks→Field Goals, Fumble Recoveries→Strikes
- 2026-02-15: Tuned game balance — breakaway system, red zone TD model, defensive fatigue, lateral compounding
- 2026-02-15: Fixed red zone TD bug (requires yards_gained >= 2)
- 2026-02-15: Fixed drive play count timing (increment before simulate_play)
- 2026-02-15: Reduced territory_kick weights across all styles to prevent excessive kicking
- Touchdowns changed from 6pts to 9pts
- Added play family system replacing random play selection
- Added field position flip on turnovers
- Fixed kickoff possession after scoring plays

## Tech Stack
- Python 3.11
- Streamlit (UI)
- FastAPI (API)
- Plotly + Pandas (charts/data)
