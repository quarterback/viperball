# Viperball - Quick Start Guide

## 🚀 Launch the GUI

```bash
# Method 1: Use the launcher (checks dependencies)
./launch_gui.sh

# Method 2: Direct launch
python viperball_gui.py
```

## 📋 First Time Setup

### 1. Generate Team Rosters

Before creating a dynasty, generate rosters for all teams:

```bash
# Generate all 102 teams (takes ~2 minutes)
python scripts/generate_rosters.py --all
```

Or generate just a few teams to start:

```bash
# Generate specific teams
python scripts/generate_rosters.py --schools gonzaga,villanova,vcu,marquette,davidson
```

### 2. Create Your Dynasty

1. Open the GUI: `./launch_gui.sh`
2. Click **File → New Dynasty**
3. Search for and select your team
4. Click "Select Team"
5. You're ready to go!

## 🎮 Basic Operations

### View Your Roster
1. Go to "👥 Team Roster" tab
2. Click "Load Roster"
3. Browse your 36-player roster

### Simulate Games
- **Advance Week**: Toolbar button (simulates 1 week)
- **Simulate Season**: Toolbar button (simulates full season)

### Check Standings
- Go to "🏆 Standings" tab
- Select a conference from dropdown
- View rankings and records

### Save Your Progress
- **File → Save Dynasty**
- Choose location
- File saved as `.json`

### Load Saved Dynasty
- **File → Load Dynasty**
- Select your saved `.json` file

## 📁 Important Files

```
viperball/
├── viperball_gui.py       ← Main GUI application
├── launch_gui.sh          ← GUI launcher script
├── data/
│   ├── teams/             ← Generated team rosters (36 players each)
│   ├── schools/           ← School database (102 schools)
│   └── conferences.json   ← 8 conferences
├── scripts/
│   ├── generate_rosters.py  ← Generate team rosters
│   └── generate_names.py    ← Name generator
└── saves/                 ← Your saved dynasties (create this folder)
```

## 🎯 Common Tasks

### Generate More Rosters

```bash
# Single team
python scripts/generate_rosters.py --schools <school_id>

# Multiple teams
python scripts/generate_rosters.py --schools team1,team2,team3

# All teams
python scripts/generate_rosters.py --all
```

### Find School IDs

School IDs are in `data/schools/d1_non_football.json`.

Common examples:
- `gonzaga` - Gonzaga University
- `villanova` - Villanova University
- `vcu` - Virginia Commonwealth University
- `marquette` - Marquette University
- `davidson` - Davidson College
- `gonzaga` - Gonzaga University
- `boston_university` - Boston University

### Create Saves Folder

```bash
mkdir saves
```

## 🔧 Troubleshooting

### "Tkinter not found"
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# macOS - Should be included
# Windows - Should be included
```

### "No roster found"
Generate the roster first:
```bash
python scripts/generate_rosters.py --schools <team_id>
```

### "Module not found"
Make sure you're in the viperball directory:
```bash
cd /path/to/viperball
python viperball_gui.py
```

## 🏆 Tips

1. **Generate all rosters first** - Makes the experience smoother
2. **Save often** - Especially after big wins!
3. **Explore conferences** - 8 different conferences to choose from
4. **Check recruiting** - Build your dynasty with great recruits
5. **Track history** - Watch your dynasty grow over the years

## 📚 More Info

- Full documentation: `GUI_README.md`
- Name generation system: `scripts/generate_names.py`
- School database: `data/schools/d1_non_football.json`

---

**Ready to build your dynasty? Let's go! 🏈**
