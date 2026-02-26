# Viperball Simulation Sandbox

## Overview
The Viperball Simulation Sandbox is a browser-accessible platform for Viperball simulation. It contains two core modes: the Collegiate Viperball League (CVL) for women's college play with team management, and the NVL (National Viperball League) professional men's league as a spectator-only experience. The platform facilitates detailed simulation and analysis of Viperball game logic, season progression, and professional league tracking. Its purpose is to enhance game development and understanding by providing insights through features like detailed box scores, play-by-play logs, and custom sabermetrics.

## User Preferences
I want iterative development. Ask before making major changes. I prefer detailed explanations.
- **Snap kick (DK) rate**: NBA 3-pointer philosophy — DK is the premium scoring play. Target: 3.5-4.0 DK per team per game. Specialist teams (kicking_zb archetype or kicking ≥85) should hit 4.5-6+. Non-specialists ~3.0-3.5. Teams should DK almost every time they're in range with a specialist.
- **Place kick philosophy**: User wants more PK attempts — teams should try field goals instead of punting when drives stall, even from 40+ yards. PK attempts target: 3-5 per team per game. Max FG range: 71 yards. Success rate is secondary to attempt frequency.
- **Snap kick philosophy**: Drop kicks (snap kicks) should be strongly preferred over place kicks from close range (≤25 yards: why take 3 when you can get 5?). Common at 25-40 yards, plausible at 40-58 yards. Kicking specialists get massive DK preference boosts (2.2x shot play trigger, 1.8x EV multiplier).
- **Kick passing**: Real offensive weapon, not a prayer. Target completion rate: 55-70% (comparable to rugby kick-pass / NFL pass). Short kicks (≤12 yds) ~75%, medium ~63%, long ~50%, deep ~35%, bomb ~22%. Interceptions only happen on failed completions. YAC potential is high (2-14 base + speed bonus). Kick pass threat creates floor-spacing effect that improves run/lateral efficiency.
- **Stat variance**: User wants all stat categories to produce a natural low-to-high range across seasons, NOT predictive clustering. Per-game rhythm/intensity factors (0.65-1.35 range) create this variance.
- **Lateral chain risk**: User wants laterals to be genuinely risky. Target fumble rate ~25% (was 7%). Per-exchange fumble 0.035 with chain-length scaling.

## System Architecture

### UI/UX Decisions
The user interface is built with NiceGUI using a 7-section top navigation bar: Play, Pro Leagues, League, My Team, Export, Debug, and Inspector. On mobile (<768px), the nav bar collapses to a hamburger dropdown menu, tab bars show scroll arrows, tables scroll horizontally, and metric cards flex-wrap to fit narrow screens. The CVL system supports up to 4 human-coached teams out of 188 across 16 conferences, with the rest AI-controlled. Dynasty mode has been replaced by the Pro Leagues spectator experience.

### API-First Architecture
The project utilizes a FastAPI backend as the single source of truth for all simulation logic, with the NiceGUI app acting as a thin display layer that interacts with API endpoints. Game objects are managed in-memory on the FastAPI server, keyed by session IDs. `main.py` launches the unified FastAPI+NiceGUI server on port 5000. A comprehensive set of API endpoints (55+) manages session lifecycle, season operations, roster management, injury tracking, data retrieval, and pro league operations.

### Technical Implementations
The project maintains a clear separation of concerns:
- **`engine/`**: Core Python simulation logic.
- **`engine/pro_league.py`**: ProLeagueSeason/ProLeagueConfig framework for professional leagues.
- **`api/main.py`**: FastAPI backend.
- **`ui/api_client.py`**: Typed Python wrapper for API calls.
- **`nicegui_app/`**: NiceGUI web application.
- **`data/teams/`**: CVL team configuration in JSON files (188 teams).
- **`data/nvl_teams/`**: NVL team configuration in JSON files (24 teams, male players).
- **`data/name_pools/`**: Name pools for player generation (female: `first_names.json`, male: `male_first_names.json`).
- **`main.py`**: Application entry point.

### Pro League System (NVL)
- **Spectator-only**: No team management, no coaching, no roster moves. Users watch seasons unfold and browse stats.
- **24 teams across 4 divisions**: East (6), North (6), Central (6), West (6). 5 Canadian franchises.
- **Male players**: Separate name pool from CVL. Pro-level attributes (65-95 range vs college 40-80).
- **Fast sim**: All NVL games use `fast_sim_game()` for ~0.14s full-season simulation.
- **Season structure**: ~22 games per team, divisional opponents 2x + cross-division fills, ~28 weeks.
- **Playoffs**: Top 3 per division (12 teams), #1 seeds get byes, single-elimination bracket through Wild Card → Divisional → Conference Championship → NVL Championship.
- **Parameterized framework**: `ProLeagueConfig` dataclass configures any league. Adding international leagues (Eurasian, AfroLeague, Pacific, LigaAmerica, Champions League) requires only config + team data files, not new code.
- **Season continuity (Phase 2)**: Data model includes `contract` stubs on players and `export_snapshot()` for future season chaining.
- **API endpoints**: `/api/pro/{league}/new`, `standings`, `schedule`, `sim-week`, `sim-all`, `game/{week}/{matchup}`, `playoffs`, `stats`, `team/{team_key}`, `active`.
- **UI tabs**: Dashboard (sim controls), Standings (4-division tables), Schedule & Results (week-by-week with box score viewer), Stats Leaders (rushing/kick pass/scoring/total yards), Playoffs (bracket), Teams (roster + season stats + schedule).

### Feature Specifications
- **Engine Mechanics**: Includes a Style System (9 offense, 5 defense), Play Families, Tempo System, unique Scoring (9pts for Touchdowns), 6-down system, contextual Kicking mechanics (CFL Rouge/Pindown, max FG range 71 yards, DK range 58 yards hard cap), Lateral Risk & Chaos, Fatigue & Breakaways, dynamic Weather System, Penalty System (30+ types), Victory Formation (kneel-down with 35-40s clock burn), and Defensive Timeout Strategy (Q4 trailing defense calls TOs to preserve clock).
- **Player Archetypes**: 12 archetypes across Zeroback, Viper, and Flanker positions with auto-assignment and stat tracking. ZB Style System classifies Zerobacks (kick_dominant, run_dominant, dual_threat, distributor).
- **Rating-Driven Touch Distribution**: LEAD/COMPLEMENT backs and ranked receivers (1-5) are exempt from ceiling/decay — their ratings dictate volume. LEAD backs get ~54% forced carry share (style-dependent), COMPLEMENT ~20%. Receivers are ranked by recv_score with rating-weighted target shares. Spread-the-love only manages rotation players. Stars on bad teams still dominate via rating gaps.
- **Advanced Play Mechanics**: Enhanced Red Zone model, Play-type-specific Carrier Selection, Explosive Run System, Play Signatures, Viper Jet plays, Viper and Defensive Alignment systems, and a detailed Run Fumble System.
- **Stat Tracking**: Comprehensive per-player and per-game stat tracking, including lateral stats, kick pass stats, special teams, and defensive stats. Lateral yards are counted as rushing yards (the player who gains yards on a lateral gets rushing yard credit). Total yards = rushing + kick pass (no separate lateral component). `lateral_yards` field is retained as a detail stat for breakdown purposes. All box score yardage derives from player stat objects as single source of truth via reconciliation in `generate_game_summary()`. Trick plays and fake punts credit rushing yards on the carrier.
- **Delta Yards Efficiency (DYE)**: Post-game analytic measuring how the score-differential kickoff system affects each team. Drives are bucketed as penalized (team was leading, started deeper), boosted (trailing, started closer), or neutral (tied). DYE ratio = yards/drive in that bucket vs neutral baseline. DYE > 1.0 means the team outperformed despite/beyond the delta adjustment. Visualized in Analytics tab with metric cards, breakdown table, and grouped bar charts for yards/drive and scoring rate by situation. Season-level DYE accumulates across all games per team (stored in TeamRecord) and surfaces in League Awards/Stats with a net yard impact leaderboard showing most hurt/helped teams. Debug batch tool aggregates DYE across 200 games with "Wins Despite Δ", opponent "cheap" boost scores, and bonus possession impact. Tracks `dye_opponent_boosted_scores` (scores opponents got from the delta system) and `dye_wins_despite_penalty` (games won while being penalized).
- **Dynamic Roster System**: Generates 36-player rosters, with balanced class years and geographic name pipelines.
- **Power Index System**: A 100-point ranking system for Power Rankings, playoff selection, and conference standings.
- **Playoff Selection**: Combines conference champion auto-bids with at-large bids based on Power Index.
- **Rivalry System**: Allows dual rivalry slots per team with guaranteed annual games and in-game boosts.
- **DraftyQueenz System**: An integrated fantasy/prediction mini-game for betting, fantasy football, and dynasty boosts. NVL betting is integrated directly into the Pro Leagues Betting tab — users can place winner, spread, and over/under bets on NVL games using the same DQ$ bankroll. Bets resolve automatically when weeks are simulated. Betting history with P/L tracking is shown per-week. No fantasy roster for NVL (predictions only).
- **Injury-Aware Auto Depth Chart**: Adjusts depth chart for injured players, showing status and sorting by health.
- **Injury Recovery Variance**: Probabilistic recovery system with early return chances, setbacks, and detailed recovery notes.

## External Dependencies
- **Python 3.11**: Core programming language.
- **NiceGUI**: For the interactive web user interface.
- **FastAPI**: For the RESTful API endpoints.
- **Plotly**: For charts and data visualizations.
- **Pandas**: For data manipulation and analysis.
