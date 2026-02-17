# Viperball Simulation Sandbox

## Overview
The Viperball Simulation Sandbox is a browser-accessible platform for the Collegiate Viperball League (CVL) engine. It functions as an internal tool for playtesting, debugging, and tuning game mechanics, accessible across various devices. The sandbox supports detailed simulation and analysis of Viperball game logic, season progression, and multi-season dynasty modes, offering insights through features like detailed box scores, play-by-play logs, and custom sabermetrics.

## User Preferences
I want iterative development. Ask before making major changes. I prefer detailed explanations.
- **Snap kick (DK) rate**: User confirmed 1.78-2.23/game is PERFECT. Do NOT lower snap kicks — the old 0.5-1.5 target was too low. Updated target range: 1.5-2.5 DK per team per game.
- **Place kick philosophy**: User wants more PK attempts — teams should try field goals instead of punting when drives stall, even from 40+ yards. PK attempts target: 3-5 per team per game. Success rate is secondary to attempt frequency.

## System Architecture

### UI/UX Decisions
The user interface is built with Streamlit and features a 5-page sandbox:
- **Game Simulator**: Allows configuration of offense/defense styles and weather, displaying real-time box scores, play distributions, drive outcomes, penalty tracking, player archetype performance, and a detailed play log. Includes a debug panel for granular data.
- **Season Simulator**: Configurable for various season and playoff formats, featuring standings, radar charts, and score distributions.
- **Dynasty Mode**: A multi-season career mode with customizable conference setups, season lengths, and scheduling. It includes 9 tabs for simulating seasons, tracking standings, coach dashboard, team history, record book, awards, injury reports, player development, and CSV export functionalities.
- **Debug Tools**: Facilitates batch simulations for averaging, analyzing fatigue curves, turnover rates, and drive outcome aggregations.
- **Play Inspector**: Enables repeated execution of single plays under controlled conditions for detailed analysis.

### Technical Implementations
The project follows a clear separation of concerns:
- **`engine/`**: Contains core Python simulation logic, including game simulation, offense/defense styles, play families, weather, penalty systems, player archetypes, box score generation, polling, EPA calculations, season and dynasty simulations, and custom Viperball metrics.
- **`api/`**: Implements FastAPI REST endpoints for programmatic access to simulation functionalities, supporting requests for single simulations, batch simulations, play debugging, and team data, with a weather parameter.
- **`ui/`**: Hosts the Streamlit web application.
- **`data/teams/`**: Stores team configuration in JSON files.
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
- **Drive Tracking**: Logs every possession with detailed outcomes.
- **Position Tag System**: Players identified by position abbreviation + jersey number (e.g., VB1, HB13).
- **Dynasty Mode Enhancements**: Integrated injury tracking (3-tier severity, history, reports), player development (breakout/decline tracking, offseason trends), awards system (individual trophies, All-CVL/Conference teams, historical data), and CSV export for various season and dynasty data.
- **CFL Rouge/Pindown Overhaul**: Comprehensive implementation following CFL rules, affecting punts, missed kicks, and kickoffs, with detailed return chance formulas and ball placement.

## External Dependencies
- **Python 3.11**: Core programming language.
- **Streamlit**: For the interactive web user interface.
- **FastAPI**: For the RESTful API endpoints.
- **Plotly**: For charts and data visualizations.
- **Pandas**: For data manipulation and analysis.