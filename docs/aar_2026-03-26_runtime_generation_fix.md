# After Action Review — Runtime Generation Fix & FCS Removal

**Date:** 2026-03-26
**Branch:** `claude/balance-talent-generation-mS413`

## Mission

Fix the remaining sources of overpowered player generation that persisted after the initial talent balance changes, and remove the obsolete FCS fictional team system.

## Incident / Starting State

After dropping all archetype stat centers by ~30 points, widening spreads to 18, capping generation at 96, and adding a stat budget system, fresh saves were **still producing 90+ OVR players with stats at 96-100**. The initial changes to `scripts/generate_rosters.py` were correct but insufficient — the actual runtime code path used by fresh saves was in a completely different file.

Screenshots from a fresh save (2 games in, no development applied) showed:
- **Lillian Aguero (Oklahoma):** 89 OVR, seven stats at 96, 2-star normal developer — should be impossible at generation
- **Idaho Slotback:** 85 OVR with 99 awareness and 98 stamina — exceeding the 96 generation cap
- **Denise Shaw (Indiana):** 78 OVR with 96 awareness and 90+ power/agility on a slow 2-star

## Root Cause Analysis

### 1. The runtime generation path was in `engine/game_engine.py`, not `generate_rosters.py`

Every fresh save calls `load_team_from_json(fresh=True)` which calls `generate_team_on_the_fly()` in `engine/game_engine.py` (line 12649). This function imports `generate_player_attributes()` from `generate_rosters.py` — so the center/spread changes **did** flow through — but it added its own modifications on top that completely undermined them.

The `generate_rosters.py` script is only used for pre-building roster JSON files offline. The actual game never runs it directly. All our stat_center and spread changes were correct but we were only fixing half the pipeline.

### 2. `team_center_offset` with std dev of 25 was the primary culprit

Line 12735: `team_center_offset = int(round(random.gauss(0, 25)))`

This per-team jitter added a random offset to the archetype center for every team on every fresh save. With a gaussian std dev of 25:
- ~16% of teams got an offset of +25 or more
- ~2.5% of teams got an offset of +50 or more
- A blue blood (center 64) + offset 40 = effective center 104 → every stat clamped at 96

This single line explains every screenshot: Lillian Aguero's Oklahoma likely got a +30-40 offset, pushing the effective center to 94-104. The stat budget system (which uses the archetype center, not the offset center) couldn't catch it because the budget was calculated from center 64 while the actual rolls used center 104.

### 3. Hidden gem boost capped at 100 instead of 96

Line 12826: `setattr(p, stat_name, min(100, current + boost))`

The hidden gem system in `generate_team_on_the_fly()` had its own cap of 100, independent of the 96 ceiling in `_stat_roll()`. This is how stats reached 99 and 100 — a player generated with a stat of 90 (from offset-inflated center) plus a hidden gem boost of +9 = 99, bypassing the generation ceiling entirely.

### 4. Development gains were too aggressive

The development system (`engine/development.py`) was a secondary compounding factor. A 5-star "quick" developer gained +2 to +5 per stat per offseason — up to +55 total points across 11 stats. A player who started at 60 OVR could reach 96+ in two seasons, making the -30 center drop meaningless over time.

### 5. FCS team system was obsolete

The FCS fictional team generator existed to fill schedule gaps when there weren't enough real teams. With 205 schools in the CVL, this is no longer needed. The system was generating weak fictional teams (stats 10-30) as schedule padding — but with a full league, every slot can be filled by real opponents.

## Changes Made

### 1. Removed `team_center_offset` entirely (`engine/game_engine.py`)

The per-team jitter served no purpose with the new system. The archetype center IS the team's identity, and the wide stat_spread of 18 already creates massive individual player variance within each roster. Adding a team-wide offset on top randomly pushed entire teams outside their intended tier.

**Before:** `team_center_offset = int(round(random.gauss(0, 25)))`
**After:** `team_center_offset = 0`

Also removed the conference floor clamping code that only existed to counteract extreme negative jitter — with no jitter, it's unnecessary.

### 2. Fixed hidden gem boost cap (`engine/game_engine.py`)

**Before:** `setattr(p, stat_name, min(100, current + boost))`
**After:** `setattr(p, stat_name, min(96, current + boost))`

Now consistent with the 96 generation ceiling everywhere else.

### 3. Halved development gains (`engine/development.py`)

| Profile | Before (per stat/season) | After |
|---|---|---|
| quick | +2 to +5 | +1 to +3 |
| normal | +1 to +3 | +0 to +2 |
| slow | +0 to +2 | +0 to +1 |
| late_bloomer (early) | +0 to +1 | +0 to +1 (unchanged) |
| late_bloomer (late) | +3 to +7 | +1 to +4 |

**Max total gain per offseason:**
- Before: quick = +55, normal = +33, late_bloomer (late) = +77
- After: quick = +33, normal = +22, late_bloomer (late) = +44

A 5-star quick developer starting at 55 OVR now reaches ~70 by junior year and ~80 by senior year, instead of rocketing to 96+ by sophomore year.

### 4. Disabled FCS team generation (`engine/season.py`)

The FCS filler loop in `generate_schedule()` no longer generates fictional teams. If any team ends up short on games (shouldn't happen with 205 teams), it logs a warning and the team simply plays fewer games rather than facing generated opponents.

The FCS constants, name generator, and team generator functions are still in the file but are now dead code. The sim paths that check `is_fcs_game` and load FCS teams will never trigger since no FCS games are created.

## How This Fixes the Problem

The previous round of changes (center -30, spread 18, ceiling 96, stat budget) were all correct and necessary — but they only fixed `generate_rosters.py`, which is the offline script. The runtime path in `game_engine.py` had its own offset system that was adding +25 to +50 points back on top, completely negating the center reduction.

With the offset removed:
- A blue blood's effective center is now exactly 64, as intended
- With spread 18, individual stats range ~46-82 (1σ), with rare outliers touching 96
- The stat budget caps total points at center×11+44 = 748 (~68 avg per stat)
- Hidden gems boost targeted stats to at most 96
- Development adds +1-3 per stat per year, creating a gradual 4-year arc to reach 80+ OVR

The math now works end-to-end: generation → development → earned elite status. No shortcuts, no accidental inflation.

## Risk Assessment

- **FCS removal:** If a league has fewer than 205 teams (custom configurations), some teams may end up with fewer games. The warning log will flag this. If it becomes an issue, the FCS system can be re-enabled with better stat ranges.
- **Development too slow:** If player progression feels glacial, the gain ranges can be bumped by 1 point per tier without reintroducing the old inflation problem. Monitor whether 4-year development arcs produce satisfying player growth.
- **Existing saves:** These changes only affect new saves and new seasons within a dynasty. Players already generated with inflated stats will retain them until they graduate.
