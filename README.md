# Viperball — Collegiate Sports Dynasty Simulator

A complete dynasty management simulator for **Viperball**, a tactical gridiron sport inspired by pre-1906 football. Build your program, recruit players, and compete for championships in the Collegiate Viperball League (CVL).

## What is Viperball?

Viperball is a modernized version of pre-forward pass football, featuring:
- **5-for-20 down system** (5 downs to gain 20 yards)
- **Lateral chain mechanics** — strategic ball distribution across the field
- **Live-ball kicking** — punts and drop-kicks as tactical offensive options
- **No forward passes** — all advancement is through rushing and laterals
- **Strategic depth** — specialized positions like Viper, Zeroback, and Shiftback

Created from a Reddit thought experiment about early football, Viperball honors the historical roots of the game while developing modern tactical complexity.

**📖 For complete rules, see [RULES.md](RULES.md) — the Official Rulebook (v1.1)**

## Origin Story

Viperball began as a thought experiment from a Reddit discussion: [What if the entire 1894 Yale team came back to life?](https://www.reddit.com/r/CFB/comments/1r4qgd3/what_if_the_entire_1894_yale_team_came_back_to/)

The question sparked an idea: what if we created a modern tactical sport that honors the rules and style of early football—no forward pass, heavier kicking, fewer specialized roles—while developing its own strategic depth? Viperball is the answer.

## Features

### 🎮 Dynasty Mode
- **102 D1 non-football schools** competing in 8 conferences
- **Full season simulation** with conference tournaments and national championship
- **Dynasty progression** across multiple seasons
- **Season-by-season tracking** of your program's history

### 👥 Roster Management
- **36-player rosters** with 4 key attributes: Speed, Kicking, Lateral, Tackling
- **Positional depth** across offensive and defensive positions
- **Player development** and progression system
- **Fatigue modeling** affecting late-game performance

### 🎓 Recruiting System
- **High school recruit database** with regional distribution
- **Scholarship offers** and recruiting battles
- **Recruiting classes** that develop over time
- **Transfer portal** for roster adjustments

### 📊 Advanced Statistics
- Complete game simulation with play-by-play
- Viper Efficiency and Lateral Efficiency metrics
- Comprehensive team and player statistics
- Game logs and historical tracking

### 🖥️ Desktop GUI
Full-featured Tkinter desktop application for managing your dynasty. See [GUI_README.md](GUI_README.md) for details.

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/quarterback/viperball.git
cd viperball

# No external dependencies needed - Python 3.8+ standard library only
```

### Launch the GUI

```bash
# Method 1: Use the launcher script
./launch_gui.sh

# Method 2: Direct launch
python viperball_gui.py
```

### First-Time Setup

1. **Generate team rosters** (required before creating a dynasty):
   ```bash
   # Generate all 102 teams (~2 minutes)
   python scripts/generate_rosters.py --all
   
   # Or generate specific teams
   python scripts/generate_rosters.py --schools gonzaga,villanova,vcu
   ```

2. **Create your dynasty**:
   - Open the GUI: `./launch_gui.sh`
   - Click **File → New Dynasty**
   - Select your team from 102 schools
   - Start building your program!

3. **Save your progress**:
   - **File → Save Dynasty**
   - Your dynasty is saved as JSON

For detailed setup and usage, see [QUICKSTART.md](QUICKSTART.md).

## Command-Line Simulation

You can also simulate games directly from the command line:

```bash
# Simulate a single game
python simulate_game.py gonzaga villanova

# Run season simulation
python test_season.py

# Test dynasty progression
python test_dynasty.py
```

See [ENGINE_README.md](ENGINE_README.md) for engine documentation.

## Documentation

- **[RULES.md](RULES.md)** — Official Viperball Rulebook (v1.1) - Complete game rules
- **[QUICKSTART.md](QUICKSTART.md)** — Quick start guide for the GUI
- **[GUI_README.md](GUI_README.md)** — Desktop application documentation  
- **[ENGINE_README.md](ENGINE_README.md)** — Simulation engine documentation
- **[FEATURES.md](FEATURES.md)** — Developer guide for advanced systems
- **[COLLEGE_RULES.md](COLLEGE_RULES.md)** — Collegiate league structure
- **[VIPERBALL_CASE_STUDY.md](VIPERBALL_CASE_STUDY.md)** — Design and development notes

## Project Structure

```
viperball/
├── viperball_gui.py          # Main GUI application
├── simulate_game.py          # Command-line game simulator
├── engine/                   # Core simulation engine
│   ├── game_engine.py        # Main game logic
│   ├── recruiting.py         # Recruiting system
│   ├── injuries.py           # Injury system
│   └── ...
├── ui/                       # Streamlit UI components
├── data/
│   ├── schools/              # 102 school profiles
│   ├── teams/                # Generated rosters (36 players each)
│   ├── conferences.json      # 8 conference structure
│   └── name_pools/           # Name generation data
├── scripts/
│   ├── generate_rosters.py   # Roster generator
│   └── generate_names.py     # Name generator
└── saves/                    # Your saved dynasties
```

## Game Philosophy

Viperball strips away the forward pass to create a different kind of football:
- **Positioning matters** — field position and kicking strategy are critical
- **Laterals create risk and reward** — broken chains lead to fumbles
- **Kicking is offensive** — punts and drop-kicks are live-ball tactical options
- **Fatigue impacts strategy** — stamina management affects late-game performance
- **Specialized roles** — positions like Viper create unique tactical opportunities

The result is a gridiron sport that feels familiar yet plays completely differently from modern football.

## Contributing

This is an open-source project. Contributions are welcome!

Areas for contribution:
- UI/UX improvements
- Additional statistical tracking
- Enhanced recruiting logic
- Play-by-play narrative generation
- Historical tracking and records

## License

MIT License - See LICENSE file for details

## Credits

Created by the Viperball community from a thought experiment on r/CFB.

Simulation engine and dynasty manager built with Python.

---

**Ready to build your Viperball dynasty? Let's go! 🏈**
