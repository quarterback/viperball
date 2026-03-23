# WVL Commissioner Mode — Implementation Plan

## What It Is

Commissioner Mode lets you run the entire WVL as an all-powerful league commissioner
instead of managing a single team. You sim seasons, watch the league evolve, move
players around, and CVL graduates flow in automatically from your college dynasty.

## Core Design Decisions

- **No team ownership** — all 64 teams are AI-managed (using existing AI owner profiles)
- **No financial simulation** — no bankroll/fanbase/infrastructure/loans/bourse
- **Single-button offseason** — runs everything automatically, shows summary, then you make manual tweaks
- **Full commissioner power** — move any player between any team at any time
- **Player career tracking** — college → pro career timeline for every player

## Implementation Phases

### Phase 1: Engine — `engine/wvl_commissioner.py` (new file)

`WVLCommissionerDynasty` class — simplified `WVLDynasty` without owner/financial machinery.

**Fields:**
- `dynasty_name`, `current_year`, `tier_assignments`
- `team_histories` (reuse `WVLTeamHistory`)
- `ai_team_owners` (reuse `AI_OWNER_PROFILES` for all 64 teams)
- `linked_cvl_dynasty` — name of CVL dynasty for auto-import
- `career_tracker` — new `PlayerCareerTracker`
- `_current_season`, `_team_rosters`, `_fa_pool_dicts`

**Key methods (all reusing existing modules):**
- `start_season()` — same as `WVLDynasty.start_season()` minus owner investment injection
- `run_full_auto_season()` — calls `WVLMultiTierSeason.run_full_season()`
- `advance_season(season)` — record team histories (reuse logic from `WVLDynasty`)
- `run_offseason(season, rng)` — simplified:
  1. `process_retirements()` (reuse)
  2. `season.run_promotion_relegation()` (reuse)
  3. Auto-import CVL graduates via bridge DB (reuse)
  4. `run_free_agency()` with all AI teams (reuse)
  5. `apply_pro_development()` for all rosters (reuse)
  6. Roster cuts (reuse)
  7. Record career stats
- `move_player(player_name, from_team, to_team)` — commissioner tool
- `get_team_roster(team_key)` — view any team
- `to_dict()` / `from_dict()` — serialization

**Factory:** `create_commissioner_dynasty(dynasty_name, starting_year, linked_cvl_dynasty=None)`

### Phase 2: Career Tracker — `engine/player_career_tracker.py` (new file)

**`PlayerCareerRecord`:**
- `player_id`, `full_name`, `position`, `nationality`
- `college_team`, `college_conference`, `college_years` (from bridge data)
- `pro_teams` — list of `{year, team_key, tier, stats...}`
- `career_status` — "college" | "active" | "retired"

**`PlayerCareerTracker`:**
- `ingest_cvl_graduates(pool, year)` — create records from bridge export data
- `record_season_stats(rosters, season, year)` — capture each year's stats
- `record_retirement(player_name, year)` — mark retired
- `get_career(player_name)` — full career lookup
- `search_players(query, filters)` — for UI search
- `to_dict()` / `from_dict()`

### Phase 3: Persistence — `engine/db.py` (modify)

Add functions following existing pattern:
- `save_commissioner_dynasty()` / `load_commissioner_dynasty()` / `delete_commissioner_dynasty()`
- `save_commissioner_season()` / `load_commissioner_season()` / `delete_commissioner_season()`
- Career tracker data stored inside the dynasty blob

### Phase 4: UI — `nicegui_app/pages/wvl_commissioner.py` (new file)

Tab-based layout, much simpler than the 3200-line owner mode:

**Tabs:**
1. **Overview** — current year, tier champions, recent pro/rel moves
2. **Simulate** — "Sim Full Season" button, or week-by-week controls
3. **Standings** — reuse `_render_zone_standings` from `wvl_mode.py`
4. **Rosters** — browse any team's roster, edit players, "Move Player" dialog
5. **Players** — search all players, click for full career timeline (college → pro)
6. **History** — season-by-season league history, champion records

**Phase flow:**
1. Setup → enter dynasty name, optionally link CVL dynasty
2. Dashboard → simulate, observe, intervene
3. Offseason → single "Process Offseason" button → summary → manual tweaks → next season

### Phase 5: Navigation — `nicegui_app/pages/wvl_mode.py` + `app.py` (modify)

On the WVL setup page, add mode selector:
- **Owner Mode** (existing) — pick a team, manage finances, deep sim
- **Commissioner Mode** (new) — run the league, observe, influence

## Reuse Map

| Component | Source File | Strategy |
|-----------|-----------|----------|
| Season sim | `wvl_season.py` | Direct reuse, no changes |
| Tier config | `wvl_config.py` | Direct reuse |
| Pro/rel | `promotion_relegation.py` | Direct reuse |
| CVL import | `db.py` bridge functions | Direct reuse |
| Free agency | `wvl_free_agency.py` | Direct reuse (all AI) |
| Development | `development.py` | Direct reuse |
| Retirements | `wvl_free_agency.py` | Direct reuse |
| AI owners | `wvl_owner.py` | Direct reuse |
| Player cards | `player_card.py` | Direct reuse |
| Standings UI | `wvl_mode.py` | Import rendering functions |

## New Files
- `engine/wvl_commissioner.py` (~300 lines)
- `engine/player_career_tracker.py` (~200 lines)
- `nicegui_app/pages/wvl_commissioner.py` (~800 lines)

## Modified Files
- `engine/db.py` — add commissioner save/load (~40 lines)
- `nicegui_app/pages/wvl_mode.py` — add mode selector on setup page (~20 lines)
- `nicegui_app/app.py` — route commissioner mode (~5 lines)
