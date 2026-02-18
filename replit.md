# Viperball Simulation Sandbox

## Overview
The Viperball Simulation Sandbox is a browser-accessible platform for the Collegiate Viperball League (CVL) engine. It functions as an internal tool for playtesting, debugging, and tuning game mechanics, accessible across various devices. The sandbox supports detailed simulation and analysis of Viperball game logic, season progression, and multi-season dynasty modes, offering insights through features like detailed box scores, play-by-play logs, and custom sabermetrics.

## User Preferences
I want iterative development. Ask before making major changes. I prefer detailed explanations.
- **Snap kick (DK) rate**: User confirmed 1.78-2.23/game is PERFECT. Do NOT lower snap kicks — the old 0.5-1.5 target was too low. Updated target range: 1.5-2.5 DK per team per game.
- **Place kick philosophy**: User wants more PK attempts — teams should try field goals instead of punting when drives stall, even from 40+ yards. PK attempts target: 3-5 per team per game. Success rate is secondary to attempt frequency.
- **Stat variance**: User wants all stat categories to produce a natural low-to-high range across seasons, NOT predictive clustering. Per-game rhythm/intensity factors (0.65-1.35 range) create this variance.
- **Lateral chain risk**: User wants laterals to be genuinely risky. Target fumble rate ~25% (was 7%). Per-exchange fumble 0.035 with chain-length scaling.

## System Architecture

### UI/UX Decisions — New Information Architecture (Feb 2026)
The user interface is built with Streamlit using a 4-tab navigation system plus sidebar settings:
- **Play** (tab): Mode selection when no session active (New Dynasty, New Season, Quick Game). During an active session, shows week-by-week simulation controls (Sim Next Week, Sim to Week X, Sim Rest of Season) with progress bar, current standings, and recent results. After regular season, transitions through playoffs and bowls as separate phases. Dynasty mode adds per-week injury tracking and explicit "Advance to Next Season" step. Quick Game available in all modes.
- **League** (tab): Read-only league-wide data from the active season/dynasty. Sub-tabs: Standings, Power Rankings, Conferences, Postseason, Schedule, Awards & Stats. Supports both standalone season and dynasty modes.
- **My Team** (tab): Focused view of the user's coached team(s). Sub-tabs: Dashboard (metrics, radar chart), Roster (player attributes), Schedule (team game log with detail viewer), History (dynasty only — career stats, record book, team history).
- **Export** (tab): Data export tools. Season Data tab has CSV standings, CSV schedule, and comprehensive JSON context (for LLM analysis). Dynasty Data tab adds dynasty-wide CSV exports (standings, awards, injuries, development, All-CVL, All-Conference) plus dynasty save/load.
- **Settings** (sidebar): Debug Tools and Play Inspector, accessible without leaving the main tabs.
- **Session Management**: Sidebar shows current mode (No Active Session / Season name / Dynasty name + year). End Session button clears state.
- All 125 teams always included in seasons. Human coach picks up to 4 teams; rest AI-controlled.
- Dynasty supports pre-dynasty history simulation (1-100 years).
- Old 6-page sidebar navigation (Game Simulator, Season Simulator, Dynasty Mode, Team Roster, Debug Tools, Play Inspector) replaced by this IA structure. Legacy page modules preserved but no longer routed from app.py.

### Technical Implementations
The project follows a clear separation of concerns:
- **`engine/`**: Contains core Python simulation logic, including game simulation, offense/defense styles, play families, weather, penalty systems, player archetypes, box score generation, polling, EPA calculations, season and dynasty simulations, and custom Viperball metrics.
- **`api/`**: Implements FastAPI REST endpoints for programmatic access to simulation functionalities, supporting requests for single simulations, batch simulations, play debugging, and team data, with a weather parameter.
- **`ui/`**: Hosts the Streamlit web application (modular structure with `ui/app.py` as thin shell routing to `ui/page_modules/`).
- **`data/teams/`**: Stores team configuration in JSON files (125 teams total, including D3, metro, legacy, women's, and international programs). 12 geographic conferences: Capital Athletic, Moonshine League, Gateway League, Great Lakes Union, Metro Atlantic, New England Athletic, Pacific Rim, Skyline Conference, Southern Athletic, Sun Country, West Coast Conference, Yankee Conference.
- **`scripts/generate_new_teams.py`**: Team generation script for adding new schools with proper rosters, stats, and metadata.
- **`main.py`**: The application's entry point, launching Streamlit.

### Feature Specifications
- **Engine Mechanics**:
    - **Style System**: 9 offense styles (Ground & Pound, Lateral Spread, Boot Raid, Ball Control, Ghost Formation, Rouge Hunt, Chain Gang, Triple Threat, Balanced) with unique play weights, tempo, lateral risk, kick rates, and situational modifiers. 5 defense styles (Base, Pressure, Contain, Run-Stop, Coverage) influencing play outcomes and special teams.
    - **Play Families**: Categorized play calling (e.g., dive_option, speed_option, lateral_spread).
    - **Tempo System**: Affects fumble risk and play count.
    - **Scoring**: Unique point values for Touchdowns (9pts), Snap Kicks (5pts), Field Goals (3pts), Safeties (2pts), Pindowns (1pt), and Strikes (0.5pts).
    - **Down System**: 6 downs to gain 20 yards.
    - **Kicking**: Contextual kick triggers, tiered accuracy, and CFL Rouge/Pindown mechanics.
    - **Lateral Risk & Chaos**: Detailed system for lateral fumble risk, tipped punts, chaos bounces, and punt return TDs.
    - **Fatigue & Breakaways**: Per-play fatigue tracking and breakaway mechanics.
    - **Weather System**: 6 conditions (clear, rain, snow, sleet, heat, wind) affecting various game aspects like fumble rates, kick accuracy, and stamina drain. Season games have random weather; simulators allow explicit selection.
    - **Penalty System**: 30+ types across 5 phases, with play-type-specific selection, weather boosts, and Q4 pressure factors, targeting 10-16 penalties/game. Includes Viperball-specific penalties.
    - **Player Archetypes**: 12 archetypes across Zeroback, Viper, and Flanker positions, with auto-assignment and modifiers for various gameplay stats. Includes per-player game stat tracking.
    - **Red Zone**: Enhanced red zone TD model.
    - **Carrier Selection**: Play-type-specific carrier weights using position tags (HB, WB, SB, ZB, VP). Each play family (dive, power, sweep, speed_option, counter, draw, viper_jet) has unique primary_positions, carrier_weights, and archetype_bonus multipliers.
    - **Explosive Run System**: 8-28% base chances per play family, modified by carrier speed/agility and defensive fatigue. Keeper matchup scoring integrated.
    - **Play Signatures**: Each play family produces a unique signature string (e.g., "KP cheats inside — edge open", "correct read", "jet motion") stored on the Play dataclass and exported in play_by_play output.
    - **Viper Jet**: Distinct simulation path for VP-only plays with botched exchange mechanic (higher fumble rate * 1.40), jet motion descriptions, and unique signature outcomes.
    - **Viper Alignment**: VIPER_ALIGNMENT_BONUS lookup table providing direction-based bonuses (left/right/center/free) against play families.
    - **Defensive Alignment**: ALIGNMENT_VS_PLAY rock-paper-scissors system with 5 alignments (balanced, aggressive, stacked_box, wide, contain). Aggressive alignment added with high-risk/high-reward modifiers.
    - **Run Fumble System**: Play-family-specific fumble rates using ball_security (hands attribute). Weather multiplier (1.40x for rain/snow/sleet). Archetype fumble_modifier applied.
    - **Fumble Recovery Contest**: Player-based recovery scoring using awareness, speed, power, and proximity. No longer fixed probability.
    - **Stat Tracking**: Per-player lateral_assists, lateral_receptions, lateral_tds. Special teams: kick_returns, kick_return_yards, kick_return_tds, punt_returns, punt_return_yards, punt_return_tds, muffs, st_tackles. Rushing/lateral yard split (game_rushing_yards vs game_lateral_yards).
- **Drive Tracking**: Logs every possession with detailed outcomes.
- **Position Tag System**: Players identified by position abbreviation + jersey number (e.g., VB1, HB13). Actual tags: HB, WB, SB, ZB, VP, LB, CB, LA, KP, ED, BK.
- **Dynasty Mode Enhancements**: Integrated injury tracking (3-tier severity, history, reports), player development (breakout/decline tracking, offseason trends), awards system (individual trophies, All-CVL/Conference teams, historical data), and CSV export for various season and dynasty data.
- **Power Index System**: Comprehensive 100-point ranking system replacing simple poll scores. Components: Win % (30pts), Strength of Schedule with 2-level depth (20pts), Quality Wins weighted by opponent rank (20pts), Non-conference record (10pts), Conference Strength based on non-conf performance (10pts), Point Differential (10pts), minus Loss Quality penalties (bad losses penalized more). Used for weekly Power Rankings, playoff selection, and conference standings.
- **Playoff Selection**: Conference champion auto-bids (best conference record wins the auto-bid for each conference) plus at-large bids filled by highest Power Index. Teams seeded by Power Index regardless of bid type. Bid types (AUTO/AT-LARGE) displayed in playoff field table.
- **CFL Rouge/Pindown Overhaul**: Comprehensive implementation following CFL rules, affecting punts, missed kicks, and kickoffs, with detailed return chance formulas and ball placement.

## External Dependencies
- **Python 3.11**: Core programming language.
- **Streamlit**: For the interactive web user interface.
- **FastAPI**: For the RESTful API endpoints.
- **Plotly**: For charts and data visualizations.
- **Pandas**: For data manipulation and analysis.