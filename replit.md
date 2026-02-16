# Viperball Simulation Sandbox

## Overview
Browser-accessible simulation sandbox for the Collegiate Viperball League (CVL) engine. Designed for playtesting, debugging, and tuning game mechanics from phone, tablet, or laptop.

This is NOT a consumer app — it's a playtest + debugging environment.

## Architecture

```
engine/                  - Core Python simulation engine
  game_engine.py         - Main simulation logic (ViperballEngine, offense/defense styles, play families)
  box_score.py           - Box score generation
  poll_system.py         - Poll/ranking system
  epa.py                 - EPA (Expected Points Added) calculation module
  season.py              - Season simulation (round-robin, standings, playoffs)
  dynasty.py             - Multi-season dynasty mode (career tracking, records, awards)
  viperball_metrics.py   - Custom sabermetrics (OPI, Territory, Pressure, Chaos, Kicking, Drive Quality, Turnover Impact)
  __init__.py            - Package exports
api/                     - FastAPI REST endpoints (standalone API access)
  main.py                - /simulate, /simulate_many, /debug/play, /teams
ui/                      - Streamlit web UI
  app.py                 - 5-page sandbox (Game Simulator, Season Simulator, Dynasty Mode, Debug Tools, Play Inspector)
data/teams/              - Team JSON files
main.py                  - Entry point (launches Streamlit on port 5000)
.streamlit/              - Streamlit configuration
```

## Running
The app runs via `python main.py` which launches Streamlit on port 5000.

## Key Features

### Engine
- **Style System**: 5 offense styles with differentiated effectiveness bonuses
  - power_option: +10% run yards (dive/sweep), +5% fatigue resistance, lateral_risk 0.8
  - lateral_spread: +20% explosive lateral chance, +10% lateral success, +5% yardage vs tired D, lateral_risk 1.4
  - territorial: +10% kick accuracy, +15% pindown chance, lateral_risk 0.8
  - option_spread: +15% option read success, +10% broken-play yardage, +10% broken plays vs tired D, lateral_risk 1.25
  - balanced: +5% to everything, lateral_risk 1.0
- **Play Families**: dive_option, speed_option, sweep_option, lateral_spread, territory_kick
- **Tempo System**: High tempo (+5% fumble risk, more plays) vs low tempo (-5% fumble risk, fewer plays)
- **Deterministic Seeds**: Every sim accepts a seed for reproducibility
- **Scoring**: Touchdowns = 9pts, Snap Kicks = 5pts, Field Goals = 3pts, Safeties = 2pts, Pindowns = 1pt, Strikes = 0.5pts
- **AFL-style kicking**: ~52% of plays are kicks (punts, snap kicks, field goals). Contextual kick triggers based on down/distance/field position
- **Snap kick accuracy**: Tiered success (100%/92%/80%/60% by distance range), viable offensive weapon
- **Field goal accuracy**: Tiered success (95%/88%/75%/55% by distance)
- **CFL Rouge/Pindown**: 1pt awarded when kick lands in end zone and receiver can't return out. Applies to punts, missed snap kicks, missed field goals
- **Strikes**: Fumble recovery by opposing team awards 0.5pts (fractional scoring supported)
- **Lateral risk system**: 8-12% base fumble, +3% per extra lateral, +4% for 3+ chains, +4% for 4+ chains, +5% fatigue penalty; multiplied by style lateral_risk (0.8–1.4)
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

### Defense Style System
- **Base Defense**: Balanced approach, solid fundamentals, no modifiers
- **Pressure Defense**: Aggressive blitzing, +10% fumble forcing, -10% yards allowed, vulnerable to explosive plays +15%, elite kick blocking (1.5x)
- **Contain Defense**: Limits explosives -20%, reduces breakaway chance 0.85x, slightly worse at preventing yards +5%
- **Run-Stop Defense**: Stuffs the run (-15% yards), very weak against kicks (+10% accuracy), vulnerable to laterals +5%
- **Coverage Defense**: Excellent pindown prevention (0.8x), reduces lateral success -10%, slightly better kick coverage (1.3x muff rate)

### UI Pages (5 pages)
1. **Game Simulator**
   - Offense + Defense style selectors for both teams
   - Real box score: quarter-by-quarter scoring + scoring breakdown (TD/DK/PK with point values)
   - Play family distribution: grouped bar chart comparing team play call %
   - Drive outcome panel: table of all drives + outcome distribution chart
   - Play log: position-tagged descriptions with quarter filter
   - Debug panel: fatigue curves, explosive plays, turnover triggers, kick decisions, style params, Viperball Metrics
   - Export: download box score (.md), play log (.csv), drives (.csv), full JSON
2. **Season Simulator** - Full round-robin season with team selection, style configs, standings, radar charts, score distributions, playoffs, CSV export
3. **Dynasty Mode** - Multi-season career mode with configurable features:
   - Conference setup: 1-4 conferences with custom names and team assignment
   - Configurable season length: games-per-team slider (6-20 or full round-robin)
   - Conference-weighted scheduling: prioritizes conference matchups (60% default)
   - 5 tabs: Simulate Season, Standings & Polls, Coach Dashboard, Team History, Record Book
   - Standings & Polls tab: conference standings with conf W-L, weekly Top 25 poll with movement tracking
   - Weekly poll system: rankings based on win% (40%), OPI (20%), point differential (15%), SOS (25%)
   - Poll movement chart: line graph tracking team rankings over the season
   - Coach dashboard, team history, record book, awards, JSON save/load
4. **Debug Tools** - Batch sims (5-200), averages, fatigue curves, turnover rates, drive outcome aggregation
   - Export: batch summary (.csv), all games (.json), full data + plays (.json)
5. **Play Inspector** - Run single plays repeatedly with situation controls
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
- 2026-02-16: Added defensive archetypes system: 5 defense styles (Base, Pressure, Contain, Run-Stop, Coverage) with play modifiers, special teams chaos probabilities
- 2026-02-16: Defense style selectors added to Game Simulator UI for both teams
- 2026-02-16: Viperball Metrics (OPI, Territory, Pressure, Chaos, Kicking, Drive Quality, Turnover Impact) displayed in Game Simulator debug panel
- 2026-02-16: Season Simulator page: round-robin scheduling, standings with metrics, radar charts, score distributions, playoff brackets, CSV export
- 2026-02-16: Dynasty Mode page: multi-season career tracking, coach dashboard, team history, record book, awards, JSON save/load
- 2026-02-16: Dynasty Mode: configurable season length (games-per-team slider), multi-conference setup (1-4 conferences), conference-weighted scheduling
- 2026-02-16: Weekly poll/ranking system: Top 25 rankings after each week, poll movement chart, conference standings view
- 2026-02-16: Dynasty UI overhauled: 5 tabs (Simulate Season, Standings & Polls, Coach Dashboard, Team History, Record Book)
- 2026-02-16: Season/Dynasty integration with viperball_metrics module for OPI, Territory, Pressure, Chaos, Kicking averages in standings
- 2026-02-15: Integrated AFL-style engine: 52% kicks, CFL rouge/pindown (1pt), chaos mechanics, enhanced lateral risk
- 2026-02-15: Tiered kicking accuracy (drop kicks + place kicks), contextual kick triggers
- 2026-02-15: UI updated with pindown stats, kick %, lateral efficiency, punt return TDs in box scores and batch tools
- 2026-02-15: Rebalanced all 5 play styles with differentiated effectiveness bonuses, reduced lateral fumble penalties ~40%, halved contextual kick boosts, added tempo-based fumble scaling, added tired-defense bonuses for high-tempo styles
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
