# Injury & Substitution UI Implementation Spec

## Context

The injury/substitution engine was rebuilt from scratch. The old system tracked injuries but never connected them to gameplay. The new system:

- Processes injuries BEFORE each week's games (players miss games)
- Generates in-game injuries during plays (with automatic substitutions)
- Has 4 injury categories and 5 severity tiers
- Tracks everything in `Injury.to_dict()` and `InGameInjuryEvent`

**The existing UI has 3 injury report surfaces that need updating, plus several new surfaces to build.**

---

## Data Model (What's Available)

### Injury dict (from `Injury.to_dict()`)

```python
{
    "player_name": "Sarah Chen",
    "team_name": "MIT",
    "position": "Halfback",
    "tier": "moderate",           # NEW: was only minor/moderate/severe
    "category": "on_field_contact",  # NEW FIELD
    "description": "MCL sprain (grade 2)",
    "body_part": "knee",            # NEW FIELD
    "week_injured": 4,
    "weeks_out": 3,
    "week_return": 7,
    "is_season_ending": False,
    "in_game": True,               # NEW FIELD: happened during a game
    "game_status": "OUT",          # NEW FIELD: "OUT" | "DOUBTFUL" | "QUESTIONABLE"
}
```

**Tier values** (was 3, now 5):
- `day_to_day` — QUESTIONABLE, playing through it or misses 0-1 games
- `minor` — DOUBTFUL, out 1-2 weeks
- `moderate` — OUT, 3-5 weeks
- `major` — OUT, 6-8 weeks (NEW tier)
- `severe` — OUT FOR SEASON

**Category values** (NEW — was not tracked):
- `on_field_contact` — football hits (ACL tear, concussion, stinger, broken collarbone)
- `on_field_noncontact` — soft tissue (hamstring strain, groin pull, Achilles tear)
- `practice` — training injuries (tweaked knee in practice, conditioning injury)
- `off_field` — non-sport (academic probation, illness, family emergency, transfer portal)

### In-game injury dict (from game summary `result["in_game_injuries"]`)

```python
{
    "player": "Sarah Chen",
    "position": "Halfback",
    "description": "sprained ankle",
    "tier": "minor",
    "category": "on_field_contact",
    "season_ending": False,
    "substitute": "Maria Lopez",     # who replaced them (or null)
    "sub_position": "Wingback",      # sub's actual position
    "out_of_position": True,         # sub is playing a different position
}
```

### InjuryTracker query methods (available to the API/backend)

```python
tracker.get_active_injuries(team_name, week)    # -> List[Injury]
tracker.get_unavailable_names(team_name, week)  # -> Set[str] (players who can't play)
tracker.get_dtd_names(team_name, week)          # -> Set[str] (playing through injury)
tracker.get_team_injury_penalties(team_name, week) # -> {"yards_penalty": 0.95, ...}
tracker.get_injury_report_by_category()         # -> {team: {category: count}}
tracker.get_season_injury_report()              # -> {team: [injury_dicts]}
tracker.get_season_injury_counts()              # -> {team: total_count}
```

---

## Surface 1: League Injury Report (UPDATE EXISTING)

**File:** `ui/page_modules/section_league.py` lines 1087-1143

**Current state:** Shows active injuries and season log with basic fields (tier, week, description).

**Changes needed:**

### 1a. Update metric cards (add new tiers)

Replace 3-column metrics with 5 columns:
```
Active Injuries | Day-to-Day | Out (Minor+) | Season-Ending | Most Affected Team
```

### 1b. Add category and game_status to active injuries table

```
Team | Player | Position | Injury | Body Part | Category | Status | Week Out | Return
MIT  | Chen   | HB       | MCL sprain | knee  | Contact  | OUT    | Wk 4    | Wk 7
MIT  | Lopez  | WB       | quad tightness | quad | Non-contact | QUESTIONABLE | Wk 5 | Wk 5
```

**Status column color coding** (use inline CSS or emoji fallback):
- `QUESTIONABLE` — yellow/amber
- `DOUBTFUL` — orange
- `OUT` — red
- `OUT FOR SEASON` — dark red/bold

### 1c. Add category breakdown chart

New expandable section: "Injuries by Category"
- Bar chart: X = category (Contact / Non-Contact / Practice / Off-Field), Y = count
- Stacked by tier (color code: green DTD, yellow minor, orange moderate, red major, dark red severe)

### 1d. Update season log table

Add columns: `Category`, `Body Part`, `In-Game` (boolean — was this during a game or between weeks?), `Game Status`

---

## Surface 2: My Team Dashboard Injury Report (UPDATE EXISTING)

**File:** `ui/page_modules/section_my_team.py` lines 202-237

**Changes needed:**

### 2a. Update metric cards

```
Active Injuries | Questionable | Out | Season-Ending | Season Total
```

### 2b. Add game_status badge to active injuries table

Same table structure as Surface 1b but without Team column (it's already team-scoped).

### 2c. Add "Impact" section

Show the team penalty multipliers from `get_team_injury_penalties()`:
```
Yards Impact: -3.2% | Kicking Impact: -1.8% | Lateral Impact: -2.1%
```
Use red/green delta indicators (Streamlit `st.metric` with `delta` parameter).

---

## Surface 3: Dynasty Injury Report (UPDATE EXISTING)

**File:** `ui/page_modules/dynasty_mode.py` lines 814-877

**Changes needed:**

### 3a. Update tier metric cards

Replace current 4 columns (Total / Minor / Moderate / Severe) with:
```
Total | Day-to-Day | Minor | Moderate | Major | Severe
```

Note: the existing code has `tier_counts = {"minor": 0, "moderate": 0, "severe": 0}` — this needs to include `"day_to_day"` and `"major"`.

### 3b. Add category breakdown

New bar chart: Injuries by Category per season, stacked by team or by tier.

### 3c. Add in-game vs between-game split

Pie chart or metric pair:
```
In-Game Injuries: 23 (34%) | Between-Game: 45 (66%)
```

### 3d. Update trends chart

Current chart tracks Total and Severe across seasons. Add lines for:
- Major
- In-Game (count where `in_game == True`)
- Off-Field (count where `category == "off_field"`)

---

## Surface 4: Game Detail — In-Game Injuries (NEW)

**File:** `ui/helpers.py` — inside `render_game_detail()`

This is the most important new surface. Games now generate real injuries.

### 4a. Add "In-Game Injuries" section

Place between the Player Stats and Drive Summary sections. Only render if `result.get("in_game_injuries")` is non-empty.

```
### In-Game Injuries

Q2 | HOME | Sarah Chen (HB) — sprained ankle [MINOR]
         -> Maria Lopez (WB) substituted in (out of position)
Q3 | AWAY | DeShawn Williams (OL) — stinger [DAY-TO-DAY]
         -> Ashley Price (OL) substituted in
```

Implementation:
```python
in_game_inj = result.get("in_game_injuries", [])
if in_game_inj:
    st.markdown("### In-Game Injuries & Substitutions")
    for ig in in_game_inj:
        severity = "OUT FOR SEASON" if ig["season_ending"] else ig["tier"].replace("_", "-").upper()
        line = f"**{ig['player']}** ({ig['position']}) — {ig['description']} [{severity}]"
        if ig.get("substitute"):
            oop = " *(out of position)*" if ig.get("out_of_position") else ""
            line += f"  \n&emsp;-> {ig['substitute']} ({ig['sub_position']}) sub in{oop}"
        st.markdown(line)
```

### 4b. Play-by-play injury highlighting

In the play-by-play table, injury events are already appended to the `description` field as:
```
| INJURY: Sarah Chen (Halfback) — sprained ankle [MINOR] | SUB IN: Maria Lopez (Wingback) (out of position)
```

Add conditional row styling — if `" | INJURY:" in description`, highlight the row in light red/pink. The existing DataFrame doesn't support per-row styling easily in Streamlit, so as an alternative: add a column `"INJ"` that shows a red indicator when the play has an injury.

```python
play_rows.append({
    ...existing columns...,
    "INJ": "!" if "INJURY:" in p['description'] else "",
})
```

---

## Surface 5: Roster Status Column (NEW)

**File:** `ui/page_modules/section_my_team.py` (Roster tab, lines 299-354)
**File:** `ui/page_modules/section_league.py` (Team Browser)

### 5a. Add "Status" column to all roster tables

Every roster viewer should show player availability:

```
# | Name         | Pos | Year | OVR | Status
7 | Sarah Chen   | HB  | Jr   | 82  | OUT (MCL sprain, Wk 7)
3 | Maria Lopez  | WB  | So   | 76  | HEALTHY
9 | Tanya Bell   | ZB  | Sr   | 88  | QUESTIONABLE (quad tightness)
```

**Status values:**
- `HEALTHY` — no active injury (default, no special styling)
- `QUESTIONABLE` — day-to-day, description in parentheses
- `DOUBTFUL` — minor injury
- `OUT (description, return Wk X)` — moderate/major
- `OUT FOR SEASON (description)` — severe

This requires cross-referencing the roster with active injuries from the tracker. The API's `get_injuries(session_id, team=team_name)` returns active injuries — match by `player_name`.

---

## Surface 6: Pre-Game Injury Report (NEW)

**File:** `ui/page_modules/game_simulator.py`

Before the "Simulate" button (or in a sidebar panel), show both teams' injury status:

```
### Matchup Health Report

HOME: MIT Engineers          | AWAY: Stanford Cardinal
Active: 3 out, 1 questionable | Active: 1 out, 2 questionable

OUT:                         | OUT:
- Sarah Chen (HB) - MCL     | - Kim Park (OL) - broken hand
- Jay Patel (DL) - flu      |
- ...                        |
QUESTIONABLE:                | QUESTIONABLE:
- Tanya Bell (ZB) - quad    | - Alex Reyes (VP) - stinger
                             | - Jess Moore (KP) - ankle
```

This only applies when the game is run in season/dynasty context (where the injury tracker exists). For standalone games, skip this section.

---

## Surface 7: Weekly Injury Feed (NEW — optional but high-value)

**File:** `ui/page_modules/section_league.py` or new component

If the season is being simulated week-by-week (not all at once), show a weekly injury ticker after each week's simulation:

```
### Week 5 Injury Report

NEW INJURIES:
  MIT: Sarah Chen (HB) — MCL sprain (grade 2) [OUT 3 weeks]
  MIT: Jay Patel (DL) — flu [OUT 1 week]
  Stanford: Kim Park (OL) — broken hand [OUT 4 weeks]

RETURNING:
  MIT: Lisa Wang (WB) — cleared to play (was: sprained ankle)
  Cal: DeShawn Williams (SB) — cleared to play (was: hamstring strain)
```

Data source: Compare `tracker.get_active_injuries(team, week)` vs `tracker.get_active_injuries(team, week-1)`. New entries = new injuries. Entries present last week but gone now = returning players.

---

## Color Scheme (matches existing app.py CSS)

| Status | Color | Hex | Usage |
|--------|-------|-----|-------|
| Healthy | — | — | Default, no highlight |
| Questionable (DTD) | Yellow | `#fbbf24` | Status badge, row tint |
| Doubtful (Minor) | Orange | `#f59e0b` | Status badge, row tint |
| Out (Moderate/Major) | Red | `#dc2626` | Status badge, row tint |
| Season-Ending | Dark Red | `#991b1b` | Status badge, bold text |
| Returning | Green | `#22c55e` | Weekly feed "cleared" entries |

These align with the existing red accent (`#dc2626`) already used throughout the app.

---

## Implementation Priority

1. **Update existing 3 injury surfaces** (Surfaces 1-3) — they will break without updates because the tier list changed from 3 to 5. The dynasty report's `tier_counts` dict needs `day_to_day` and `major` keys added or it'll silently miss those injuries.

2. **Game detail in-game injuries** (Surface 4) — this is the most visible new feature. Every game now generates injury data in `result["in_game_injuries"]` that currently goes unshown.

3. **Roster status column** (Surface 5) — high-value, low-effort. Just cross-reference active injuries with roster names.

4. **Pre-game report** (Surface 6) — context for game outcomes. "Why did MIT lose? Their starting HB was out."

5. **Weekly feed** (Surface 7) — nice to have, makes the season feel alive.

---

## Key Files to Modify

| File | What to change |
|------|----------------|
| `ui/page_modules/section_league.py:1087-1143` | Update league injury report (Surface 1) |
| `ui/page_modules/section_my_team.py:202-237` | Update team dashboard injuries (Surface 2) |
| `ui/page_modules/section_my_team.py:299-354` | Add status column to roster (Surface 5) |
| `ui/page_modules/dynasty_mode.py:814-877` | Update dynasty injury report (Surface 3) |
| `ui/helpers.py:476-682` | Add in-game injuries to game detail (Surface 4) |
| `ui/page_modules/game_simulator.py` | Add pre-game report (Surface 6) |
| `ui/api_client.py:161-165` | May need new endpoint params for category/tier filtering |

## Key Backend Files (read-only reference)

| File | What it provides |
|------|------------------|
| `engine/injuries.py` | Full injury model, all data structures, substitution logic |
| `engine/game_engine.py:4932` | `in_game_injuries` list in game summary dict |
| `engine/game_engine.py:563-564` | Player `injured_in_game` and `is_dtd` flags |

---

## Testing Checklist

- [ ] Dynasty mode: simulate 3+ seasons, verify injury trends chart includes new tiers
- [ ] Dynasty mode: verify tier counts include `day_to_day` and `major` (not silently dropped)
- [ ] League view: injury report shows category column and all 5 status types
- [ ] My Team: roster shows status column for injured players
- [ ] My Team: dashboard shows injury impact penalties
- [ ] Game detail: in-game injuries section appears when injuries occurred
- [ ] Game detail: play-by-play shows injury marker on plays with injuries
- [ ] Pre-game: injury report shows for season/dynasty games (not standalone)
- [ ] Verify no crash when `in_game_injuries` is empty (most games will have 0-2)
- [ ] Verify no crash when injury_tracker is None (standalone game mode)
- [ ] Verify `"off_field"` category injuries display correctly (body_part is "n/a")
- [ ] CSV exports include new fields (category, body_part, in_game, game_status)
