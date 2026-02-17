# Viperball — New Features Developer Guide

This document describes the five major systems added to the engine and explains
how a future engineer should wire them into the Streamlit UI (`ui/app.py` /
`main.py`).

---

## 1. Injury System (`engine/injuries.py`)

### What it does
Tracks player injuries across an entire season with three tiers:

| Tier     | Weeks Out | Performance Penalty |
|----------|-----------|---------------------|
| Minor    | 1–2 wks   | ~3% team OVR drop   |
| Moderate | 3–4 wks   | ~7% team OVR drop   |
| Severe   | Season-ending | ~12% team OVR drop |

Injury probability is driven by position and player stamina; it accumulates
slightly over the season to model fatigue. The system returns team-level
performance penalty multipliers (`yards_penalty`, `kick_penalty`,
`lateral_penalty`) that can be fed into the game engine.

### Key API
```python
from engine.injuries import InjuryTracker

tracker = InjuryTracker()
tracker.seed(season_seed)               # optional: reproducible results

# Call once per week before simulating games
new_injuries = tracker.process_week(week, season.teams, season.standings)

# After simulating each game
tracker.resolve_week(week)

# Query penalties for a team heading into a game
penalties = tracker.get_team_injury_penalties("MIT", week)
# → {"yards_penalty": 0.93, "kick_penalty": 0.97, "lateral_penalty": 0.95}

# Display active roster injuries
tracker.display_injury_report("MIT", week)
```

### Dynasty integration
Pass the tracker into `Dynasty.advance_season()`:
```python
dynasty.advance_season(season, injury_tracker=tracker)
```
This stores the season injury report in `dynasty.injury_history[year]`.

### Streamlit UI hooks
- Show active injury list in a "Team Roster" tab per week using
  `tracker.get_active_injuries(team_name, week)`.
- Show a full season injury log at season end with
  `display_season_injury_report(dynasty, year)` (from `dynasty_ui.py`).
- The injury counts by team could feed a "Injury Tracker" sidebar widget.

---

## 2. Player Development Arcs (`engine/development.py`)

### What it does
Applies offseason attribute changes to `PlayerCard` objects based on four
development profiles:

| Profile      | Description                                                   |
|--------------|---------------------------------------------------------------|
| `quick`      | +4–5 avg gains; biggest jumps Freshman → Sophomore           |
| `normal`     | +2–3 avg gains; consistent across all years                  |
| `slow`       | +1–2 avg gains; never dominant but reliable                  |
| `late_bloomer` | +0–1 early, then +5–8 breakout at Junior → Senior year    |

Senior/Graduate players on `normal`/`slow` profiles take slight physical
decline in speed, stamina, and agility.

Notable development events (breakouts, declines) are returned for display.

### Key API
```python
from engine.development import apply_team_development, get_preseason_breakout_candidates

# After the season, apply development to all PlayerCards for every team
report = apply_team_development(player_cards_list, rng=random.Random(seed))

# Notable events
for event in report.notable_events:
    print(event.player_name, event.event_type, event.description)

# Preview who is likely to break out next season
candidates = get_preseason_breakout_candidates(player_cards_list, top_n=3)
```

### Dynasty integration
Pass a `{team_name: [PlayerCard, ...]}` dict to `Dynasty.advance_season()`:
```python
dynasty.advance_season(season, player_cards=all_player_cards)
```
Events are stored in `dynasty.development_history[year]` as a list of dicts.

### Streamlit UI hooks
- Show "Breakout Watch" panel pre-season using `get_preseason_breakout_candidates`.
- Show "Offseason Development" recap at the start of each new year using
  `display_development_report(dynasty, year)` (from `dynasty_ui.py`).
- Player card display should reflect updated attribute values each season.

---

## 3. Defensive Play-Calling AI (`engine/ai_coach.py`)

### What it does
Adds `choose_defensive_call()` which returns a `DefensivePackage` — a
situational defensive scheme with multiplicative performance modifiers.

Each defensive style has characteristic tendencies:

| Style            | Character                                          |
|------------------|----------------------------------------------------|
| `pressure_defense` | High aggression, forces fumbles, gives up big plays |
| `run_stop_defense` | Limits yards, neutral on big plays                |
| `coverage_defense` | Suppresses big plays and laterals, passive        |
| `contain_defense`  | Balanced, keeps everything in front               |
| `base_defense`     | Vanilla, slight bump to all categories            |

The call is adjusted situationally: down, yards to go, field position, score
differential, and time remaining all influence aggression and the Viper-spy
decision.

### Key API
```python
from engine.ai_coach import choose_defensive_call

pkg = choose_defensive_call(
    defense_style="coverage_defense",
    down=3,
    yards_to_go=14,
    field_pos=65,
    score_diff=-7,   # defensive team is losing by 7
    time_remaining=180,
)
print(pkg.scheme, pkg.aggression, pkg.viper_spy)
print(pkg.to_dict())
```

### Game engine integration (future)
The `DefensivePackage` modifiers are designed to be consumed by the
`ViperballEngine` play simulator. To wire them in:
1. Call `choose_defensive_call()` at the start of each possession or play.
2. Apply `pkg.yards_allowed_mod` to the run/lateral yards result.
3. Apply `pkg.fumble_forced_mod` to the fumble probability roll.
4. Apply `pkg.big_play_mod` to the touchdown / breakaway chance.
5. Apply `pkg.kick_block_mod` to the kick-block probability.
6. If `pkg.viper_spy` is True, reduce Viper archetype bonuses by ~10%.

### Streamlit UI hooks
- Show the active defensive scheme on the game-by-game play call panel.
- In a "Scouting Report" view, display tendency breakdowns by defense style.

---

## 4. End-of-Season Awards (`engine/awards.py`, `engine/dynasty.py`, `engine/dynasty_ui.py`)

### What it does
Computes a complete `SeasonHonors` object at the end of each season with:

**Individual Awards**
| Award                  | Criteria                                      |
|------------------------|-----------------------------------------------|
| The Roper Award        | Best Zeroback (kicking + lateral + awareness) |
| The Viper Claw Award   | Best Viper (speed + lateral + agility)        |
| The Iron Chain Award   | Best lateral specialist                       |
| The Brickwall Award    | Best defensive stopper (lineman or safety)    |
| The Kicker's Crown     | Best territorial/scoring kicker               |
| Offensive Player of the Year | Overall best offensive player          |
| Defensive Player of the Year | Overall best defensive player          |

**Team-Level Honors**
- Coach of the Year (win% × OPI surprise factor)
- Chaos King (highest avg chaos_factor team)
- Most Improved Team (biggest win gain vs prior season)

**Collective Teams**
- 1st and 2nd Team All-American (9 position slots each)
- 1st Team All-Conference (one per conference, 9 slots)

Selection uses player attribute ratings weighted by position, scaled by team
performance context (0.88–1.10× multiplier based on win% and avg OPI).

### Key API
```python
from engine.awards import compute_season_awards

honors = compute_season_awards(
    season=season,
    year=2026,
    conferences=dynasty.get_conferences_dict(),
    prev_season_wins=prev_wins,   # dict of team -> wins from last year
)

# Access individual award
roper = honors.get_award("The Roper Award")
print(roper.player_name, roper.team_name, roper.overall_rating)

# Store in dynasty
dynasty.honors_history[2026] = honors.to_dict()
```

Calling `dynasty.advance_season(season)` calls `compute_season_awards()`
automatically and stores results in `dynasty.honors_history[year]`.

### Dynasty retrieval
```python
dynasty.get_honors(year)                        # full SeasonHonors dict
dynasty.get_all_americans(year)                 # {"first_team": ..., "second_team": ...}
dynasty.get_all_conference(year, "Yankee Conference")
dynasty.get_individual_award(year, "The Roper Award")
```

### Streamlit UI hooks
All display functions live in `engine/dynasty_ui.py`:
```python
from engine.dynasty_ui import (
    display_individual_awards,
    display_all_american,
    display_all_conference,
    display_full_season_honors,
)
```

For Streamlit, convert the terminal-print functions to `st.write` / table
renders by pulling from `dynasty.honors_history[year]` directly:

```python
honors = dynasty.get_honors(year)

# Individual awards table
import pandas as pd
df = pd.DataFrame(honors["individual_awards"])
st.dataframe(df[["award_name", "player_name", "team_name", "position", "overall_rating"]])

# All-American first team
slots = honors["all_american_first"]["slots"]
st.table(pd.DataFrame(slots)[["award_name", "player_name", "team_name", "overall_rating"]])

# All-Conference selector
conf_options = list(honors["all_conference_teams"].keys())
selected_conf = st.selectbox("Conference", conf_options)
conf_slots = honors["all_conference_teams"][selected_conf]["slots"]
st.table(pd.DataFrame(conf_slots)[["award_name", "player_name", "team_name", "overall_rating"]])
```

---

## 5. Exportable Stats (`engine/export.py`)

### What it does
Exports any season or multi-season dynasty data to CSV files for external
analysis (Excel, pandas, Tableau, etc.).

| Function                           | Output                                    |
|------------------------------------|-------------------------------------------|
| `export_season_standings_csv`      | One row per team, full sabermetric stats  |
| `export_season_game_log_csv`       | One row per game, scores + metrics        |
| `export_dynasty_standings_csv`     | One row per (year, team)                  |
| `export_dynasty_awards_csv`        | All team + individual awards by year      |
| `export_injury_history_csv`        | All injuries by season                    |
| `export_development_history_csv`   | All notable development events            |
| `export_all_american_csv`          | All-American picks by year                |
| `export_all_conference_csv`        | All-Conference picks by year + conference |
| `export_dynasty_full(dynasty, dir)`| All of the above in one call              |
| `export_season_full(season, dir)`  | Standings + games in one call             |

### Key API
```python
from engine.export import export_dynasty_full, export_season_full

# Export everything from a dynasty
paths = export_dynasty_full(dynasty, "exports/my_dynasty")
# → {"standings": "exports/.../standings.csv", "awards": ..., ...}

# Export a single season
paths = export_season_full(season, "exports/season_2026")
```

### Streamlit UI hooks
Add a "Export Data" section to the dynasty sidebar or settings page:

```python
import streamlit as st
from engine.export import export_dynasty_full
import tempfile, os, zipfile, io

if st.button("Export Dynasty Stats (CSV)"):
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = export_dynasty_full(dynasty, tmpdir)

        # Bundle into a zip for download
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for name, path in paths.items():
                zf.write(path, arcname=os.path.basename(path))
        zip_buffer.seek(0)

        st.download_button(
            label="Download ZIP",
            data=zip_buffer,
            file_name="viperball_dynasty_export.zip",
            mime="application/zip",
        )
```

---

## Architecture Notes for Streamlit Engineers

### Where things live
```
engine/
├── injuries.py       ← NEW: InjuryTracker, Injury dataclasses
├── development.py    ← NEW: apply_offseason_development, DevelopmentReport
├── awards.py         ← NEW: compute_season_awards, SeasonHonors, AllAmericanTeam, etc.
├── export.py         ← NEW: all CSV export functions
├── ai_coach.py       ← UPDATED: added DefensivePackage + choose_defensive_call()
├── dynasty.py        ← UPDATED: SeasonAwards now has honors field; Dynasty stores
│                                injury_history, development_history, honors_history;
│                                advance_season() accepts injury_tracker + player_cards
└── dynasty_ui.py     ← UPDATED: added display_individual_awards(), display_all_american(),
                                  display_all_conference(), display_season_injury_report(),
                                  display_development_report(), display_full_season_honors()
```

### Season simulation loop (recommended pattern)
```python
from engine.injuries import InjuryTracker
from engine.ai_coach import choose_defensive_call

tracker = InjuryTracker()
tracker.seed(random_seed)

season.generate_schedule(games_per_team=10)

for week in sorted(set(g.week for g in season.schedule)):
    # Injury check before games
    new_injuries = tracker.process_week(week, season.teams, season.standings)

    # Simulate games
    week_games = [g for g in season.schedule if g.week == week]
    for game in week_games:
        season.simulate_game(game)

    # Resolve returning players
    tracker.resolve_week(week)

season.simulate_playoff()

# Advance dynasty with full context
dynasty.advance_season(
    season,
    injury_tracker=tracker,
    player_cards=player_cards_by_team,   # dict[str, list[PlayerCard]] if available
)
```

### Data access cheat sheet (Streamlit)
```python
# Honors / Awards
honors   = dynasty.get_honors(year)                              # full dict
aa_teams = dynasty.get_all_americans(year)                       # dict
ac_team  = dynasty.get_all_conference(year, "Yankee Conference") # dict
award    = dynasty.get_individual_award(year, "The Roper Award") # dict or None

# Injuries
inj_report = dynasty.get_injury_report(year)   # dict[team -> list[injury_dict]]

# Development
dev_events = dynasty.get_development_events(year)  # list[dict]

# Exports
from engine.export import export_dynasty_full
paths = export_dynasty_full(dynasty, "exports/")
```
