# Viperball Simulation Sandbox

## Overview
The Viperball Simulation Sandbox is a browser-accessible environment for the Collegiate Viperball League (CVL) engine. Its primary purpose is to serve as a playtesting, debugging, and tuning platform for game mechanics, accessible from various devices. This tool is designed for internal use, not as a consumer application, focusing on detailed simulation and analysis of Viperball game logic, season progression, and multi-season dynasty modes. It aims to provide comprehensive insights into game mechanics through features like detailed box scores, play-by-play logs, and custom sabermetrics.

## User Preferences
I want iterative development. Ask before making major changes. I prefer detailed explanations.

## System Architecture

### UI/UX Decisions
The user interface is built with Streamlit, providing a 5-page sandbox:
- **Game Simulator**: Allows selection of offense and defense styles, weather conditions, displays real-time box scores, play family distributions, drive outcomes, penalty tracker, player archetype performance, and a detailed play log with quarter filters. Includes a debug panel for granular data like fatigue curves, explosive plays, and Viperball Metrics.
- **Season Simulator**: Configurable for 8-12 game regular seasons, conference round-robin scheduling, 4/8/12/16-team playoff brackets, and a bowl system for non-playoff teams. Features standings, radar charts, and score distributions. Games have random weather assigned.
- **Dynasty Mode**: A multi-season career mode with customizable conference setups (1-4 conferences), season lengths, and scheduling. It includes tabs for simulating seasons, tracking standings and polls (weekly Top 25 with movement charts), a coach dashboard, team history, and a record book.
- **Debug Tools**: Facilitates batch simulations (5-200 games) with weather selection for averaging, analyzing fatigue curves, turnover rates, and drive outcome aggregations.
- **Play Inspector**: Enables repeated execution of single plays under controlled situations with weather selection for detailed analysis.

### Technical Implementations
The project is structured with a clear separation of concerns:
- **`engine/`**: Contains the core Python simulation logic, including `game_engine.py` (main simulation, offense/defense styles, play families, weather system, penalty system, player archetypes), `box_score.py`, `poll_system.py`, `epa.py` (Expected Points Added), `season.py` (season simulation), `dynasty.py` (multi-season mode), and `viperball_metrics.py` (custom sabermetrics like OPI, Territory, Pressure, Chaos, Kicking, Drive Quality, Turnover Impact).
- **`api/`**: Implements FastAPI REST endpoints for programmatic access to simulation functionalities, including `/simulate`, `/simulate_many`, `/debug/play`, and `/teams`. Supports weather parameter.
- **`ui/`**: Hosts the Streamlit web application (`app.py`).
- **`data/teams/`**: Stores team configuration JSON files.
- **`main.py`**: The entry point for the application, launching Streamlit on port 5000.

### Feature Specifications
- **Engine Mechanics**:
    - **Style System**: 5 offense styles (power_option, lateral_spread, territorial, option_spread, balanced) with unique effectiveness bonuses and lateral risk profiles. 5 defense styles (Base, Pressure, Contain, Run-Stop, Coverage) influencing play outcomes and special teams.
    - **Play Families**: Organized play calling into categories like dive_option, speed_option, sweep_option, lateral_spread, territory_kick.
    - **Tempo System**: High vs. low tempo affecting fumble risk and play count.
    - **Scoring**: Unique point values for Touchdowns (9pts), Snap Kicks (5pts), Field Goals (3pts), Safeties (2pts), Pindowns (1pt), and Strikes (0.5pts).
    - **Down System**: 6 downs to gain 20 yards.
    - **Kicking**: Contextual kick triggers, tiered accuracy for snap kicks and field goals, CFL Rouge/Pindown mechanics.
    - **Lateral Risk & Chaos**: Detailed system for lateral fumble risk compounding, and mechanics for tipped punts, chaos bounces, and punt return TDs.
    - **Fatigue & Breakaways**: Per-play fatigue tracking, breakaway mechanics based on speed/fatigue, and defensive fatigue scaling.
    - **Weather System**: 6 weather conditions (clear, rain, snow, sleet, heat, wind) affecting fumble rates (+0.005 to +0.035), kick accuracy (-2% to -15%), stamina drain (+5% to +30%), muff probability, punt distance, lateral fumble rates, and player speed. Season games get random weather; game simulator has explicit weather selector.
    - **Penalty System**: 30+ penalty types across 5 phase catalogs (pre_snap, during_play_run, during_play_lateral, during_play_kick, post_play). Play-type-specific penalty selection, weather-boosted penalty rates, Q4 pressure factor (+15%), targeting 10-16 penalties/game. Includes Viperball-specific penalties (Illegal Viper Alignment, Illegal Viper Contact, Lateral Interference, Illegal Forward Lateral). Full penalty tracker UI with per-penalty detail table.
    - **Player Archetypes**: 12 archetypes across 3 position groups: Zeroback (Kicking/Running/Distributor/Dual-Threat), Viper (Receiving/Power/Decoy/Hybrid), Flanker (Speed/Power/Elusive/Reliable). Auto-assigned based on player stats. Modifiers for run yards, kick accuracy, fumble rate, lateral throw, breakaway, TD rate. Per-player game stat tracking (touches, yards, TDs, fumbles, kicks).
    - **Red Zone & Penalties**: Enhanced red zone TD model with comprehensive penalty system.
- **Drive Tracking**: Logs every possession with team, quarter, start yard, plays, yards, and result (touchdown, successful_kick, fumble, turnover_on_downs, punt, missed_kick, pindown, punt_return_td, chaos_recovery, stall).
- **Position Tag System**: Players are identified by position abbreviation + jersey number (e.g., VB1, HB13).

## Recent Changes
- **2026-02-16 (conference names + score formatting)**: Added conference name generator (`engine/conference_names.py`) with 60+ themed names (geographic, mythological, Viperball lore). Integrated into Dynasty Mode with "New Names" regenerate button and editable text inputs. Added conference name editing to Season Simulator via expander with regenerate button. Score formatting overhauled: whole numbers display without `.0`, half-points render as `½` (not `.5`). Applied globally to box scores, game results, playoff brackets, bowl games, standings, CSV exports, and play descriptions. Drive result labels updated ("STRIKE (+½)"). Scoring breakdown label changed from "0.5pts" to "½pt".
- **2026-02-16 (tuning)**: Calibrated kick decision engine: PK 1.6/game (target 1.5-2.5), DK 0.76/game (target 0.5-1.5), scoring drive rate ~39.5% (target 40%+), penalties 15.2/game (target 10-16). PK gets 1.15x reliability EV boost. Kicking ZB archetype gets 1.20x DK boost with snapkick trigger. Expanded FG range to 58 yards. Reduced penalty probabilities ~35%. Reduced fumble rates (base run, fatigue, lateral chain). Boosted red zone TD probabilities (added 80-yard-line check). Increased breakaway threshold/chance. Fixed PENALTY_CATALOG KeyError for during_play subcatalogs. Boosted go-for-it aggressiveness via matrix and conversion rates.
- **2026-02-16**: Added comprehensive weather system (6 conditions), expanded penalty system (30+ types with play-type-specific catalogs), and player archetype system (12 archetypes with gameplay modifiers). Weather selector added to Game Simulator, Debug Tools, and Play Inspector. Penalty Tracker and Player Performance & Archetypes sections added to game results UI. Season games get random weather. API updated with weather parameter.

## External Dependencies
- **Python 3.11**: Core programming language.
- **Streamlit**: Used for building the interactive web user interface.
- **FastAPI**: Provides the framework for the RESTful API endpoints.
- **Plotly**: Utilized for generating charts and data visualizations within the UI.
- **Pandas**: Used for data manipulation and analysis, particularly for data displayed in charts and tables.
