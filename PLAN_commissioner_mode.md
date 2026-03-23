# WVL Commissioner Mode — Implementation Plan

## What It Is

Commissioner Mode is a unified simulation hub where you run the entire women's
viperball world: the 64-team WVL pro league, the FIV international tournament cycle,
and CVL college graduates flowing into both. You observe, influence, and track player
careers from college recruit to retirement — with a persistent Hall of Fame.

## Core Design Decisions

- **No team ownership** — all 64 WVL teams are AI-managed (existing AI owner profiles)
- **No financial simulation** — no bankroll/fanbase/infrastructure/loans/bourse
- **Single-button seasons** — sim a full WVL season or FIV cycle with one click
- **Full commissioner power** — move any player between any team at any time
- **Integrated international play** — FIV World Cup cycle runs between/during WVL seasons
- **Lifetime career tracking** — college → pro → international for every player
- **Persistent Hall of Fame** — saved player cards as permanent artifacts in SQLite

## The Annual Cycle

```
Year N:
  1. WVL Season (64 teams, 4 tiers) — sim week-by-week or all at once
  2. FIV International Cycle — continental championships → playoff → World Cup
     (WVL players called up to national teams based on nationality)
  3. Offseason — all automated:
     a. CVL graduates auto-imported via bridge DB
     b. Retirements processed → eligible for Hall of Fame
     c. Promotion/relegation across WVL tiers
     d. Free agency (all AI)
     e. Player development
  4. Commissioner interventions — move players, add countries, edit rosters
  5. Start Year N+1
```

## Implementation Phases

### Phase 1: Engine — `engine/wvl_commissioner.py` (new file)

`WVLCommissionerDynasty` — simplified `WVLDynasty` without owner/financial machinery,
plus FIV integration and career tracking.

**Fields:**
- `dynasty_name`, `current_year`, `tier_assignments`
- `team_histories` (reuse `WVLTeamHistory`)
- `ai_team_owners` (reuse `AI_OWNER_PROFILES` for all 64 teams)
- `linked_cvl_dynasty` — name of CVL dynasty for auto-import
- `career_tracker` — `PlayerCareerTracker` (Phase 2)
- `hall_of_fame` — `HallOfFame` (Phase 3)
- `fiv_rankings` — persistent Elo rankings across cycles (reuse `FIVRankings`)
- `fiv_history` — list of past World Cup results
- `custom_nations` — user-added countries for league expansion
- `_current_season`, `_current_fiv_cycle`
- `_team_rosters`, `_fa_pool_dicts`

**Key methods:**

*WVL Season (reusing existing modules):*
- `start_season()` — creates `WVLMultiTierSeason`, injects prestige-based modifiers
- `sim_week()` / `sim_full_season()` — delegates to `WVLMultiTierSeason`
- `advance_season(season)` — record team histories, feed career tracker

*FIV International (reusing `engine/fiv.py`):*
- `start_fiv_cycle(host=None)` — creates `FIVCycle`, routes WVL players to national teams
- `sim_fiv_cycle()` — runs continental → playoff → World Cup
- `get_fiv_results()` — World Cup champion, Golden Boot, MVP, updated rankings
- Player routing: WVL rosters → national teams via nationality + `_resolve_fiv_code()`

*Offseason (simplified, all automated):*
- `run_offseason(season, rng)`:
  1. `process_retirements()` → feed retired players to HoF evaluation
  2. `season.run_promotion_relegation()`
  3. Auto-import CVL graduates via bridge DB
  4. `run_free_agency()` with all AI teams
  5. `apply_pro_development()` for all rosters
  6. Roster cuts
  7. Record career stats in tracker

*Commissioner Tools:*
- `move_player(player_name, from_team, to_team)` — instant transfer
- `add_nation(code, name, confederation, tier)` — league expansion
- `get_team_roster(team_key)` — view any team
- `nominate_hall_of_fame(player_name)` — manually induct a player

**Factory:** `create_commissioner_dynasty(name, year, linked_cvl=None)`

### Phase 2: Career Tracker — `engine/player_career_tracker.py` (new file)

Tracks every player from college through pro and international play.

**`PlayerCareerRecord`:**
```
player_id, full_name, position, nationality

# College phase (from CVL bridge data)
college_team, college_conference, college_prestige
college_seasons: [{year, team, games, yards, tds, awards...}]

# Pro phase (from WVL season stats)
pro_seasons: [{year, team_key, team_name, tier, games, yards, tds, awards...}]
pro_teams_history: ["Team A (2026-2028)", "Team B (2029-present)"]

# International phase (from FIV cycle data)
national_team: str  # e.g., "USA"
international_caps: int
international_seasons: [{year, competition, games, yards, tds...}]
world_cup_appearances: int

# Status
career_status: "college" | "active" | "retired" | "hall_of_fame"
draft_year, retirement_year
career_awards: [str]
```

**`PlayerCareerTracker`:**
- `ingest_cvl_graduates(pool, year)` — create records from bridge export
- `record_wvl_season(rosters, season, year)` — capture pro stats
- `record_fiv_cycle(cycle, year)` — capture international stats
- `record_retirement(player_name, year)` — mark retired
- `get_career(player_name)` → full career card
- `search_players(query, filters)` → filtered list
- `get_all_time_leaders(stat)` → career stat leaders
- `to_dict()` / `from_dict()`

### Phase 3: Hall of Fame — `engine/hall_of_fame.py` (new file)

Persistent player cards that survive refreshes — stored in SQLite as individual blobs.

**`HallOfFameEntry`:**
```
player_id, full_name, position, nationality
induction_year: int
career_record: PlayerCareerRecord  # full frozen career snapshot
induction_reason: str  # "Auto: career stats" or "Commissioner selection"
portrait_data: dict  # attribute ratings at retirement for display
```

**`HallOfFame`:**
- `auto_evaluate(player, career)` — check if player qualifies:
  - 8+ pro seasons, or
  - 3+ All-Star/award selections, or
  - World Cup MVP/Golden Boot, or
  - 5000+ career yards, or
  - Commissioner nomination
- `induct(player_name, reason)` — add to HoF
- `get_inductees(sort_by)` → sorted list
- `get_entry(player_name)` → full HoF card with career timeline

**Persistence:** Each HoF entry saved as individual blob in SQLite via
`save_blob("hall_of_fame", player_id, entry.to_dict())`. These are permanent —
they survive dynasty resets, page refreshes, server restarts.

### Phase 4: Persistence — `engine/db.py` (modify)

Add functions following existing pattern:
- `save_commissioner_dynasty()` / `load_commissioner_dynasty()` / `delete_commissioner_dynasty()`
- `save_commissioner_season()` / `load_commissioner_season()` / `delete_commissioner_season()`
- `save_hall_of_fame_entry()` / `load_hall_of_fame()` / `delete_hall_of_fame_entry()`
- Career tracker data stored inside the dynasty blob

### Phase 5: UI — `nicegui_app/pages/wvl_commissioner.py` (new file)

Tab-based layout, simpler than the 3200-line owner mode:

**Tabs:**

1. **Overview** — current year, WVL tier champions, World Cup champion,
   recent pro/rel moves, upcoming events

2. **WVL** — WVL-specific view:
   - "Sim Full Season" or week-by-week controls
   - Standings for all 4 tiers (reuse `_render_zone_standings`)
   - Playoff brackets
   - Stat leaders

3. **International** — FIV view:
   - "Run World Cup Cycle" button
   - World rankings table
   - Continental championship results
   - World Cup bracket and results
   - National team rosters (shows which WVL club each player is from)

4. **Rosters** — browse any WVL team's roster:
   - Click team → see players with career summaries
   - "Move Player" button → transfer dialog
   - "Edit Player" dialog (reuse from `wvl_mode.py`)

5. **Players** — career search and tracking:
   - Search bar + position/tier/nationality filters
   - Player career card: college stats → pro stats → international stats
   - Full timeline visualization
   - "Nominate for Hall of Fame" button

6. **Hall of Fame** — persistent player museum:
   - Inductee gallery with career summaries
   - Sortable by induction year, position, nationality
   - Click → full career card with frozen attributes
   - Auto-induction notifications after retirements

7. **Expansion** — league management:
   - Add new nations to FIV (name, code, confederation, tier)
   - View confederation membership
   - History of expansion decisions

8. **History** — season-by-season records:
   - WVL champions by year and tier
   - World Cup champions by year
   - Pro/rel movements
   - All-time stat leaders

**Phase flow:**
1. Setup → dynasty name, optionally link CVL dynasty
2. Dashboard → simulate WVL + FIV, observe, intervene
3. Offseason → single "Process Offseason" button → summary → tweaks → next year

### Phase 6: Navigation — `nicegui_app/pages/wvl_mode.py` + `app.py` (modify)

On the WVL setup page, add mode selector:
- **Owner Mode** (existing) — pick a team, manage finances
- **Commissioner Mode** (new) — run the whole world

### Phase 7: FIV ↔ WVL Integration — `engine/fiv.py` (modify)

Add method to build national team rosters from live WVL rosters:

- `build_national_teams_from_wvl(wvl_rosters, tier_assignments)`:
  - For each player in WVL rosters, resolve nationality → FIV nation code
  - Assign to national team (best players from each country)
  - Fill remaining slots with homegrown generation (existing logic)
  - Handle nations with no WVL players (fully generated)
  - Handle user-added expansion nations

This replaces the current standalone national team generation for commissioner mode,
making WVL stars actually appear on their national teams.

## Reuse Map

| Component | Source File | Strategy |
|-----------|-----------|----------|
| WVL Season sim | `wvl_season.py` | Direct reuse, no changes |
| WVL Tier config | `wvl_config.py` | Direct reuse |
| Pro/rel | `promotion_relegation.py` | Direct reuse |
| CVL import | `db.py` bridge functions | Direct reuse |
| Free agency | `wvl_free_agency.py` | Direct reuse (all AI) |
| Development | `development.py` | Direct reuse |
| Retirements | `wvl_free_agency.py` | Direct reuse |
| AI owners | `wvl_owner.py` | Direct reuse |
| Player cards | `player_card.py` | Direct reuse |
| FIV engine | `fiv.py` | Reuse + new WVL integration method |
| FIV rankings | `fiv.py` FIVRankings | Direct reuse |
| FIV nations | `data/fiv_nations.json` | Direct reuse + expansion support |
| Standings UI | `wvl_mode.py` | Import rendering functions |
| International UI | `international.py` | Import/adapt rendering functions |
| SQLite persistence | `db.py` | Extend with new save/load functions |

## New Files
- `engine/wvl_commissioner.py` (~400 lines)
- `engine/player_career_tracker.py` (~250 lines)
- `engine/hall_of_fame.py` (~150 lines)
- `nicegui_app/pages/wvl_commissioner.py` (~1200 lines)

## Modified Files
- `engine/db.py` — add commissioner + HoF save/load (~60 lines)
- `engine/fiv.py` — add WVL roster integration method (~80 lines)
- `nicegui_app/pages/wvl_mode.py` — add mode selector on setup (~20 lines)
- `nicegui_app/app.py` — route commissioner mode (~5 lines)
