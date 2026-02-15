# Viperball Dynasty Manager - Desktop GUI

A complete desktop application for managing your women's Viperball dynasty mode.

![Viperball Dynasty Manager](https://img.shields.io/badge/Python-3.11+-blue)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green)

## Features

### 📊 Dashboard
- Season overview with current year and week
- Your team's record and stats
- Recent games history

### 👥 Team Roster
- View all 36 players on your roster
- Player stats (Speed, Kicking, Lateral, Tackling)
- Player details (Height, Weight, Position, Year)
- Hometown and high school information

### 🎓 Recruiting
- Browse high school recruits
- Make scholarship offers
- Track recruiting commitments
- Generate new recruiting classes

### 🏆 Standings
- Conference standings
- League-wide rankings
- Win-loss records
- Points for/against

### 📜 Dynasty History
- Track your dynasty's progression
- Season-by-season results
- Championship history

### 💾 Save/Load
- Save your dynasty progress
- Load saved dynasties
- Export/import dynasty files

## Installation

### Requirements
- Python 3.11 or higher
- Tkinter (usually comes with Python)

### Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd viperball

# No additional dependencies needed!
# Tkinter comes with Python
```

## Usage

### Launch the GUI

```bash
python viperball_gui.py
```

Or make it executable:

```bash
chmod +x viperball_gui.py
./viperball_gui.py
```

### Quick Start

1. **Create a Dynasty**
   - File → New Dynasty
   - Select your team from 102 D1 schools
   - Click "Select Team"

2. **View Your Roster**
   - Go to "Team Roster" tab
   - Click "Load Roster"
   - (If roster doesn't exist, generate it first - see below)

3. **Manage Your Season**
   - Use "Advance Week" to simulate one week
   - Use "Simulate Season" to fast-forward to next year
   - Track standings in the "Standings" tab

4. **Save Your Progress**
   - File → Save Dynasty
   - Choose a location
   - Your dynasty is saved as JSON

### Generating Rosters

Before viewing team rosters, you need to generate them:

**From GUI:**
- Tools → Generate All Rosters

**From Command Line:**
```bash
# Generate all 102 team rosters
python scripts/generate_rosters.py --all

# Generate specific teams
python scripts/generate_rosters.py --schools gonzaga,villanova,vcu
```

## Features Coming Soon

- ✅ Full season simulation engine
- ✅ Recruiting offers and commitments
- ✅ Player development system
- ✅ Conference tournaments
- ✅ National championship
- ✅ Transfer portal
- ✅ Coaching staff management
- ✅ Game-by-game box scores
- ✅ Statistical leaders

## File Structure

```
viperball/
├── viperball_gui.py          # Main GUI application
├── data/
│   ├── conferences.json       # Conference structure
│   ├── schools/
│   │   └── d1_non_football.json  # All 102 schools
│   ├── teams/                 # Generated team rosters
│   │   ├── gonzaga.json
│   │   ├── villanova.json
│   │   └── ...
│   └── name_pools/            # Name generation data
├── scripts/
│   ├── generate_names.py      # Name generator
│   ├── generate_teams.py      # Team profile generator
│   └── generate_rosters.py    # Roster generator
└── saves/                     # Your saved dynasties
```

## Dynasty Save Format

Dynasties are saved as JSON files containing:

```json
{
  "dynasty_name": "Gonzaga Bulldogs Dynasty",
  "current_year": 2028,
  "current_week": 5,
  "user_team": "gonzaga",
  "standings": {...},
  "recruiting_class": [...],
  "history": [...]
}
```

You can edit these manually if needed!

## Keyboard Shortcuts

- `Ctrl+N` - New Dynasty (coming soon)
- `Ctrl+S` - Save Dynasty (coming soon)
- `Ctrl+O` - Load Dynasty (coming soon)
- `Ctrl+Q` - Quit (coming soon)

## Troubleshooting

### "No roster found for this team"

Generate the roster first:
```bash
python scripts/generate_rosters.py --schools <team_id>
```

### "Module not found" errors

Make sure you're running from the viperball directory:
```bash
cd /path/to/viperball
python viperball_gui.py
```

### GUI doesn't launch

Check that Tkinter is installed:
```bash
python -c "import tkinter; print('Tkinter OK')"
```

If not installed:
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# macOS (should be included)
# Windows (should be included)
```

## Development

Want to contribute or customize?

### Adding New Features

1. **Add a new tab:**
   - Create setup method (e.g., `setup_mytab()`)
   - Add to `setup_tabs()`
   - Create update method if needed

2. **Add new data:**
   - Update `ViperballDynasty` class
   - Add save/load logic
   - Update UI to display it

3. **Add simulation logic:**
   - Create simulation module in `scripts/`
   - Call from GUI event handlers

### Code Structure

- `ViperballDynasty` - Data model for dynasty state
- `ViperballGUI` - Main GUI application class
- `setup_*` methods - Create UI tabs
- `update_*` methods - Refresh displays
- Event handlers - Respond to user actions

## License

[Your License Here]

## Credits

Built with Python and Tkinter for the Viperball women's sports management simulation.

---

**Enjoy your dynasty! 🏈**
