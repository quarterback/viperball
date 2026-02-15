# Collegiate Viperball Simulation Engine

A turn-based simulation engine for the Collegiate Viperball League (CVL), featuring 24 universities without football programs competing in a modernized version of pre-1906 football.

## Overview

This engine simulates complete Viperball games with:
- **5-for-20 down system** (5 downs to gain 20 yards)
- **Lateral chain mechanics** with broken chain (fumble) probability
- **Live-ball kicking** (punts and drop-kicks as tactical offensive options)
- **Two-way player fatigue model** affecting late-game performance
- **Viper positioning logic** that modifies play success probabilities
- **Advanced statistics** tracking including Viper Efficiency and Lateral Efficiency

## Installation

No external dependencies required - uses Python 3.8+ standard library only.

```bash
# Clone the repository
git clone https://github.com/quarterback/viperball.git
cd viperball
```

## Quick Start

### Simulate a Game

```bash
python simulate_game.py <home_team> <away_team>
```

**Available Teams:**
- `nyu` - New York University (Empire Elite)
- `gonzaga` - Gonzaga University (Coastal Vanguard)
- `marquette` - Marquette University (Heartland Union)
- `ut_arlington` - UT Arlington (Southern Heritage)

**Example:**
```bash
python simulate_game.py nyu gonzaga
```

### Generate Poll Rankings

```bash
python generate_poll.py
```

This generates a sample CVL Top 25 Poll based on win-loss records, strength of schedule, and Viper Efficiency.

## Components

### Game Engine (`engine/game_engine.py`)

Core simulation logic including:

- **Play Types:**
  - Run plays
  - Lateral chains (2-5 player sequences)
  - Punts (live-ball, possession changes)
  - Drop kicks (5 points)
  - Place kicks (3 points)

- **Fatigue System:**
  - Stamina drains with each play
  - Performance degrades below 70% stamina
  - Two-way players affected throughout game

- **Viper Impact:**
  - Alignment-exempt player position
  - Dynamic positioning (free, left, right, deep)
  - 1.0-1.3x multiplier on play success

### Box Score Generator (`engine/box_score.py`)

Generates markdown-formatted box scores with:

**Standard Stats:**
- Total yards, plays, yards per play
- Lateral chains and success rate
- Kicks made (drop kicks and place kicks)

**Advanced Metrics:**
- **Viper Efficiency:** `(Yards/Plays) × (1 + Lateral Success) × Viper Impact`
- **Micro-Scoring Differential:** `(Drop Kicks × 5) - (Place Kicks × 3)`
- **Lateral Efficiency:** `(Successful Laterals / Total Attempts) × 100%`

### Poll System (`engine/poll_system.py`)

Top 25 ranking algorithm:

**Ranking Formula:**
```
Score = (Win% × 40) + (SOS × 30) + (Viper Efficiency × 20) + (Point Diff × 10)
```

- **Win Percentage:** 40% weight
- **Strength of Schedule:** 30% weight
- **Viper Efficiency:** 20% weight
- **Point Differential:** 10% weight

National Champion = #1 ranked team at season end (no playoff)

## File Structure

```
viperball/
├── COLLEGE_RULES.md          # CVL-specific rulebook
├── data/
│   ├── conferences.json       # Conference structure (4 conferences, 24 teams)
│   └── teams/                 # Team rosters and stats
│       ├── nyu.json
│       ├── gonzaga.json
│       ├── marquette.json
│       └── ut_arlington.json
├── engine/                    # Simulation engine
│   ├── __init__.py
│   ├── game_engine.py         # Core game simulation
│   ├── box_score.py           # Box score generator
│   └── poll_system.py         # Top 25 rankings
├── examples/
│   ├── box_scores/            # Sample box scores (markdown)
│   ├── play_by_play_*.json    # Play-by-play JSON logs
│   └── cvl_top_25_poll.md     # Sample poll
├── simulate_game.py           # Game simulation script
└── generate_poll.py           # Poll generation script
```

## Output Formats

### Play-by-Play JSON

Each play includes:
```json
{
  "play_number": 1,
  "quarter": 1,
  "time_remaining": 900,
  "possession": "home",
  "field_position": 20,
  "down": 1,
  "yards_to_go": 20,
  "play_type": "lateral_chain",
  "players": ["Marcus Chen", "DeShawn Williams"],
  "yards": 15,
  "result": "gain",
  "description": "Lateral chain with 2 players for 15 yards",
  "laterals": 2,
  "fumble": false
}
```

### Box Score Markdown

Includes:
- Final score
- Team statistics (yards, plays, laterals, kicks)
- Advanced metrics (Viper Efficiency, Micro-Scoring Differential, Lateral Efficiency)
- Key plays (touchdowns, big gains, successful kicks)
- Game notes

See `examples/box_scores/` for samples.

## Conferences

### Empire Elite (East)
NYU, St. John's, George Mason, VCU, American, Vermont

### Heartland Union (Midwest)
Marquette, DePaul, Loyola Chicago, Xavier, Creighton, Wichita State

### Coastal Vanguard (West)
Gonzaga, Pepperdine, UC Irvine, UC Santa Barbara, Cal State Fullerton, Long Beach State

### Southern Heritage (South)
UT Arlington, High Point, UNC Asheville, Charleston, Oral Roberts, Little Rock

## Game Rules (CVL-Specific)

- **15-minute quarters** (60 minutes total)
- **Clock stops on first downs** for chain setting
- **5-for-20 system:** 5 downs to gain 20 yards
- **36-player rosters** (two-way play, no specialists)
- **Poll-based championship** (no playoff)

See `COLLEGE_RULES.md` for complete rulebook.

## Player Attributes

Each player has five core stats (0-100 scale):
- **Speed:** Base yards gained per play
- **Stamina:** Resistance to fatigue
- **Kicking:** Success probability for kicks
- **Lateral Skill:** Lateral chain success rate
- **Tackling:** Defensive impact (currently simplified)

## Advanced Features

### Lateral Chain Mechanics

- Chain length: 2-5 players randomly selected
- Base fumble probability: 5%
- Increases 15% per additional player
- Reduced by team lateral proficiency
- Bonus yards: 1.5 yards per player in chain

### Fatigue Model

- Starts at 100% stamina
- Drains per play: 3 (run), 5 (lateral chain), 2 (punt)
- Minimum stamina: 40%
- Performance impact below 70%:
  - Factor = 0.7 + (stamina/70 × 0.3)
  - Example: 50% stamina → 0.91x performance

### Viper Impact

Dynamic positioning system:
- **Free:** 1.15x multiplier (most aggressive)
- **Left/Right:** 1.10x multiplier
- **Deep:** 1.05x multiplier (most conservative)

Position changes randomly each play.

## Development

### Adding New Teams

1. Create JSON file in `data/teams/`
2. Follow structure of existing team files
3. Include 10+ players with all five stats
4. Add team to appropriate conference in `data/conferences.json`

### Extending the Engine

Key classes to modify:
- `ViperballEngine`: Game simulation logic
- `Play`: Individual play mechanics
- `GameState`: Game state tracking
- `PollSystem`: Ranking calculations

## Examples

See `examples/` directory for:
- Sample box scores (markdown)
- Play-by-play JSON outputs
- CVL Top 25 Poll

## License

See repository license.

## Credits

Based on the Viperball rulebook (v1.2) - a modernized version of pre-1906 football.

Original concept inspired by: [What if the entire 1894 Yale team came back to life?](https://www.reddit.com/r/CFB/comments/1r4qgd3/what_if_the_entire_1894_yale_team_came_back_to/)
