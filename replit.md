# Viperball Simulation Sandbox

## Overview
The Viperball Simulation Sandbox is a browser-accessible platform for the Collegiate Viperball League (CVL) engine. It serves as an internal tool for playtesting, debugging, and tuning game mechanics across various devices. The platform supports detailed simulation and analysis of Viperball game logic, season progression, and multi-season dynasty modes. It offers insights through features like detailed box scores, play-by-play logs, and custom sabermetrics, aiming to enhance game development and understanding.

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
The user interface is built with Streamlit using a 4-tab navigation system plus sidebar settings:
- **Play**: Manages game modes (New Dynasty, New Season, Quick Game) and simulation controls during active sessions.
- **League**: Displays read-only league-wide data (Standings, Power Rankings, Conferences, Postseason, Schedule, Awards & Stats, Injury Report).
- **My Team**: Provides a focused view of user-coached teams, including Dashboard (with Injury Report), Roster, Schedule, and History (for dynasty mode).
- **Export**: Offers tools for exporting various season and dynasty data in CSV and JSON formats.
- **Settings (sidebar)**: Contains Debug Tools and Play Inspector.
- Session management is handled via the sidebar, indicating the current mode and an option to end the session.
- All 187 teams across 16 conferences are included in seasons, with up to 4 human-coached teams and the rest AI-controlled.
- Dynasty mode supports pre-dynasty history simulation (1-100 years).

### API-First Architecture
The project utilizes a FastAPI backend as the single source of truth for all simulation logic, with the Streamlit UI acting as a thin display layer that interacts with API endpoints.
- **Session-based state management**: All game objects (Season, Dynasty, InjuryTracker) are managed in-memory on the FastAPI server, keyed by session IDs. The UI only stores `api_session_id` and `api_mode`.
- `main.py` launches both FastAPI (port 8000) and Streamlit (port 5000) as dual processes.
- A comprehensive set of API endpoints (45+) manages session lifecycle, season and dynasty operations, roster management, injury tracking, and data retrieval.

### Technical Implementations
The project maintains a clear separation of concerns:
- **`engine/`**: Contains core Python simulation logic for game mechanics, season/dynasty simulations, and custom metrics.
- **`api/main.py`**: FastAPI backend exposing REST endpoints for all simulation operations and state management.
- **`ui/api_client.py`**: A typed Python wrapper for all API HTTP calls.
- **`ui/`**: The Streamlit web application, designed with a modular structure, fetching all data via `api_client`.
- **`data/teams/`**: Stores team configuration in JSON files for 187 teams.
- **`scripts/generate_new_teams.py`**: Script for generating new team data.
- **`main.py`**: The application's entry point, initiating both FastAPI and Streamlit processes.

### Feature Specifications
- **Engine Mechanics**: Includes a comprehensive Style System (9 offense, 5 defense), detailed Play Families, Tempo System, unique Scoring (9pts for Touchdowns), a 6-down system, contextual Kicking mechanics (CFL Rouge/Pindown, max FG range 71 yards, DK range 55 yards), Lateral Risk & Chaos, Fatigue & Breakaways, a dynamic Weather System (6 conditions), and a robust Penalty System (30+ types).
- **Player Archetypes**: 12 archetypes across Zeroback, Viper, and Flanker positions, with auto-assignment and game stat tracking.
- **ZB Style System**: Zerobacks classified as kick_dominant (primary passer, rarely carries), run_dominant (STARTER rusher, less accurate kicker), dual_threat (blend), or distributor (lateral chain orchestrator). Style maps from archetype and influences play selection.
- **Starter-First-Look System (All 3 Phases)**: Replaces complex 4-tier role system. Applied to offense, defense, AND special teams.
  - **Offense**: Top player at each position group becomes STARTER, rest are ROTATION. Style-dependent first-look probability (78% ground_pound, 48% chain_gang). Produces ~1000-1500 rush yards/season for feature backs.
  - **Defense**: Top 2 Keepers + top 3 DL by tackle_score become DEF:STARTER (~65% of tackles). Rotation defenders still contribute (~35%). Ceiling management prevents tackle monopolization.
  - **Special Teams**: Backup-first philosophy — offensive ROTATION players become ST return specialists (93%+ of returns go to non-offensive-starters). Defensive ROTATION players handle coverage tackles (~65% of ST tackles). return_keeper archetype gets massive boost. This is where depth players earn field time.
- **Advanced Play Mechanics**: Enhanced Red Zone model, Play-type-specific Carrier Selection, Explosive Run System, Play Signatures, Viper Jet plays with unique mechanics, Viper and Defensive Alignment systems, and a detailed Run Fumble System with recovery contests.
- **Stat Tracking**: Comprehensive per-player and per-game stat tracking, including lateral stats, kick pass stats, special teams, and defensive stats (tackles, TFL, sacks, hurries). Player Stats UI has 6 tabs: Rushing & Scoring, Lateral Game, Kick Pass, Kicking, Defense, Returns & Special Teams.
- **Drive Tracking**: Logs all possessions and outcomes.
- **Dynamic Roster System**: Generates 36-player rosters for each season/dynasty, with balanced class years and geographic name pipelines. Dynasty mode includes automatic roster maintenance (graduation, recruitment).
- **Pre-Season History**: Supports simulating prior seasons (0-100 years) for historical context in standalone Season mode.
- **Dynasty Mode Enhancements**: Integrated injury tracking, player development, awards system, roster maintenance, and extensive data export.
- **Power Index System**: A 100-point ranking system for Power Rankings, playoff selection, and conference standings, considering win %, Strength of Schedule, Quality Wins, Non-conference record, Conference Strength, and Point Differential.
- **Playoff Selection**: Combines conference champion auto-bids with at-large bids based on Power Index.
- **Rivalry System**: Allows dual rivalry slots per team with guaranteed annual games, in-game boosts, AI assignment, and historical tracking in Dynasty mode.
- **DraftyQueenz System**: An integrated fantasy/prediction mini-game allowing users to bet on games (winner, spread, O/U, chaos factor, kick pass O/U props), play fantasy football (with kick pass scoring), and donate to unlock dynasty boosts.
- **Injury-Aware Auto Depth Chart**: Depth chart automatically adjusts when players are injured — OUT players drop to bottom, healthy players slide up. DTD players stay in their spot but flagged as Questionable. Both roster endpoints (season + dynasty) pass injury data to compute_depth_chart(). UI depth chart view shows Status column (Active/Questionable/OUT) with healthy-first sorting.
- **Injury Recovery Variance**: Weekly resolve_week() applies probabilistic recovery — 25% early return chance when within 1 week of return, 15% when within 2 weeks, 8% setback chance adding 1-3 extra weeks. Injury dataclass tracks original_weeks_out and recovery_note for UI display. Distribution: ~35% early, ~53% on-time, ~12% setback.
- **Enhanced My Team Injury Report**: Dashboard injury table shows Timeline (current vs original weeks), expected Return week, and Recovery notes (ahead of schedule / suffered setback / progressing on schedule). Season injury history available in expandable section.

## Recent Engine Tuning (Feb 2026)
- **Play selection weights**: KP 3.5x boost, run families 1.8x boost, punt suppressed to 5% of original
- **Clock timing**: 11-36 second base range per play (~82 plays/team/game)
- **DK accuracy**: Boosted table (96% at ≤20yd, 68% at ≤40yd, skill_factor floor 0.88)
- **KP mechanics**: INT base 0.055, YAC 3-18 + speed bonus, big-play TD mechanic for 20+ yard completions
- **Run base yards**: Boosted to 6-11+ range across play families
- **Go-for-it aggression**: 1.6/1.5/1.7 multipliers on 4th/5th/6th down
- **Current batch results** (20-game avg per team): Score 57.6, TDs/game 5.20, DK att 11.15/made 4.53, PK att 4.10, KP att 43.75 (58% comp), KP TDs 2.17, Rush 87.6 yds, Punts 0.78
- **Remaining gaps**: KP TDs below ~4 target, rush yards below 100-120 target, KP INTs slightly over 1.0 target

## Conference Structure (16 Conferences, 187 Teams)
Conference assignments are the **source of truth** in each team's JSON file at `data/teams/<id>.json` under `team_info.conference`. The canonical directory is also maintained at `data/conferences.json` and exported as `data/cvl_conference_directory.txt`.

| Conference | Teams |
|---|---|
| Big Pacific | 12 |
| Border Conference | 14 |
| Collegiate Commonwealth | 9 |
| Galactic League | 10 |
| Giant 14 | 13 |
| Interstate Athletic Association | 12 |
| Midwest States Interscholastic Association | 13 |
| Moonshine League | 13 |
| National Collegiate League | 8 |
| Northern Shield | 12 |
| Outlands Coast Conference | 12 |
| Pioneer Athletic Association | 14 |
| Potomac Athletic Conference | 13 |
| Prairie Athletic Union | 12 |
| Southern Sun Conference | 9 |
| Yankee Fourteen | 11 |

The engine reads conferences from team files via `engine/geography.py:get_geographic_conference_defaults()`. Geographic clustering is only used as a fallback if team files lack conference assignments.

## External Dependencies
- **Python 3.11**: Core programming language.
- **Streamlit**: For the interactive web user interface.
- **FastAPI**: For the RESTful API endpoints.
- **Plotly**: For charts and data visualizations.
- **Pandas**: For data manipulation and analysis.