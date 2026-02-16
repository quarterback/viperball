# Viperball Simulation Sandbox

## Overview
The Viperball Simulation Sandbox is a browser-accessible environment for the Collegiate Viperball League (CVL) engine. Its primary purpose is to serve as a playtesting, debugging, and tuning platform for game mechanics, accessible from various devices. This tool is designed for internal use, not as a consumer application, focusing on detailed simulation and analysis of Viperball game logic, season progression, and multi-season dynasty modes. It aims to provide comprehensive insights into game mechanics through features like detailed box scores, play-by-play logs, and custom sabermetrics.

## User Preferences
I want iterative development. Ask before making major changes. I prefer detailed explanations.

## System Architecture

### UI/UX Decisions
The user interface is built with Streamlit, providing a 5-page sandbox:
- **Game Simulator**: Allows selection of offense and defense styles, displays real-time box scores, play family distributions, drive outcomes, and a detailed play log with quarter filters. Includes a debug panel for granular data like fatigue curves, explosive plays, and Viperball Metrics.
- **Season Simulator**: Configurable for 8-12 game regular seasons, conference round-robin scheduling, 4/8/12/16-team playoff brackets, and a bowl system for non-playoff teams. Features standings, radar charts, and score distributions.
- **Dynasty Mode**: A multi-season career mode with customizable conference setups (1-4 conferences), season lengths, and scheduling. It includes tabs for simulating seasons, tracking standings and polls (weekly Top 25 with movement charts), a coach dashboard, team history, and a record book.
- **Debug Tools**: Facilitates batch simulations (5-200 games) for averaging, analyzing fatigue curves, turnover rates, and drive outcome aggregations.
- **Play Inspector**: Enables repeated execution of single plays under controlled situations for detailed analysis.

### Technical Implementations
The project is structured with a clear separation of concerns:
- **`engine/`**: Contains the core Python simulation logic, including `game_engine.py` (main simulation, offense/defense styles, play families), `box_score.py`, `poll_system.py`, `epa.py` (Expected Points Added), `season.py` (season simulation), `dynasty.py` (multi-season mode), and `viperball_metrics.py` (custom sabermetrics like OPI, Territory, Pressure, Chaos, Kicking, Drive Quality, Turnover Impact).
- **`api/`**: Implements FastAPI REST endpoints for programmatic access to simulation functionalities, including `/simulate`, `/simulate_many`, `/debug/play`, and `/teams`.
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
    - **Red Zone & Penalties**: Enhanced red zone TD model, and a comprehensive penalty system with 14 types and decline logic.
- **Drive Tracking**: Logs every possession with team, quarter, start yard, plays, yards, and result (touchdown, successful_kick, fumble, turnover_on_downs, punt, missed_kick, pindown, punt_return_td, chaos_recovery, stall).
- **Position Tag System**: Players are identified by position abbreviation + jersey number (e.g., VB1, HB13).

## External Dependencies
- **Python 3.11**: Core programming language.
- **Streamlit**: Used for building the interactive web user interface.
- **FastAPI**: Provides the framework for the RESTful API endpoints.
- **Plotly**: Utilized for generating charts and data visualizations within the UI.
- **Pandas**: Used for data manipulation and analysis, particularly for data displayed in charts and tables.