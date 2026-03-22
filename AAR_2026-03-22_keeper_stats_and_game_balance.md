# After-Action Report: Keeper Stats, Game Balance & UI Fixes

**Date:** 2026-03-22
**Branch:** `claude/fix-pro-league-stats-eBU7h`
**Scope:** Fix keeper ERA/awards, field goal physics, playoff balance, quality wins, and UI display issues

---

## Objective

Address multiple interconnected issues affecting keeper stat tracking, award selection, game simulation realism, and stats display quality. The core theme: stats weren't accurately reflecting player impact, and the game engine had variance systems that prevented talent from being a meaningful differentiator.

## Starting State

- Keeper ERA showed 0.00 for all keepers across all games despite 600+ coverage snaps
- National All-CVL keeper awards went to players with negative WPA and no meaningful stats
- Conference-level keeper awards worked correctly
- 90-yard field goals were possible and occasionally made (3-8% success rate)
- Playoffs produced excessive upsets — top seeds couldn't win through the bracket
- Quality wins in rankings were uncapped and distorted power index
- Stats displayed floating point artifacts (e.g. "1477.300000000002 yds")
- Field position displayed as raw 1-99 numbers instead of OWN/OPP format

## Root Causes Found

### 1. Keeper ERA: Points Attribution Bug
**File:** `engine/game_engine.py` — `_attribute_points_to_keeper()`

The function iterated through `def_team.players` and used `break` after finding the FIRST keeper. With 3 keepers per team, only the first in roster order received any points. The other two keepers showed `points_allowed_in_coverage = 0.0` for their entire career, producing ERA 0.00.

Coverage snaps were credited correctly (all 3 keepers got them on every defensive snap), which made the bug visible: 618 coverage snaps, 0 points allowed.

### 2. Keeper ERA: Fast Sim Missing Entirely
**File:** `engine/fast_sim.py`

The fast sim stat generator never tracked `points_allowed_in_coverage` or `coverage_snaps` for keepers at all. The fields weren't even in `_make_player_entry()` defaults.

### 3. National Keeper Awards: No Volume Gate
**File:** `engine/awards.py` — `_passes_volume_gate()`

The volume gate function had position-specific checks for backs (min carries), vipers (min yards/TDs), and zerobacks (min kick passes), but NO check for `keeper_def`. Any keeper with stats passed automatically, regardless of actual play volume.

Additionally, the keeper scoring formula (`_stat_score_for_group`) used 50/50 KPR/ERA blend with no WPA consideration. A keeper with -0.3 WPA could win Diamond Gloves purely on favorable rate stats from a small sample.

### 4. 90-Yard Field Goals
**File:** `engine/game_engine.py` — `_place_kick_success()`, `simulate_place_kick()`

The place kick success model used a "comfortable range" formula that returned 3-8% success even at 90 yards. No hard distance cap existed. The kick decision logic would attempt field goals from any distance.

Additionally, the "stall" handler (end-of-quarter final play) would give teams a free kick from any field position, including their own 20-yard line.

### 5. Playoff Upset Frequency
**File:** `engine/game_engine.py` — Multiple systems

Several variance systems compressed outcomes and reduced talent differentiation:

- **Halo system** (90% override): 90% of plays used team-average ratings instead of individual player ratings, removing star player impact
- **Power ratio exponent** (1.8): Only produced 1.78x multiplier between 90-rated and 60-rated teams
- **Contest variance** ([0.8, 2.2]): Random rolls easily swamped talent edges
- **Playoff composure** (+25% variance): Playoffs INCREASED randomness instead of rewarding consistency
- **Underdog surge** (+2/drive in Q4): Systematic boost to underdogs leading late

### 6. Quality Wins
**File:** `engine/season.py`

`_quality_win_score()` returned uncapped weighted points (10 per top-5 win, 5 per top-10, etc.) fed directly into the power index. A team with multiple ranked wins could accumulate 50+ quality win points, overwhelming the 40-point win percentage component.

### 7. Floating Point Display
**File:** `stats_site/templates/college/awards.html`

Template displayed raw float values (`{{ ss.yards }}`) without rounding, producing artifacts like "1477.300000000002 yds" from accumulated floating point arithmetic.

### 8. Clock Logic
**File:** `engine/game_engine.py`

After scoring plays, no clock time was consumed for the possession reset. A team could score a TD with 0:30 left and the opponent would get the ball at 0:30 — no time for celebration, setup, or transition.

## Changes Made

### Keeper ERA Fix
- **`game_engine.py`**: Changed `_attribute_points_to_keeper()` to distribute points EQUALLY across all active keepers instead of only the first. Each keeper gets `points / n_keepers`.
- **`fast_sim.py`**: Added `points_allowed_in_coverage`, `completions_allowed_in_coverage`, and `keeper_return_yards` to `_make_player_entry()`. Updated `_generate_player_stats()` to compute coverage snaps (~40/game) and distribute opponent score across keepers.

### Keeper Awards Fix
- **`awards.py`**: Added `keeper_def` check to `_passes_volume_gate()` requiring `coverage_snaps >= games * 15` (minimum ~15 snaps/game).
- **`awards.py`**: Updated `_stat_score_for_group()` keeper scoring from 50/50 KPR/ERA to 30/35/35 KPR/ERA/WPA blend so game impact matters.
- **`awards.py`**: Updated Diamond Gloves selection from pure KPR to composite score (35% KPR + 35% inverted ERA + 30% WPA).

### Field Goal Physics
- **`game_engine.py`**: Rewrote `_place_kick_success()` with realistic distance tiers:
  - Under comfortable range: 85-97% (skill-dependent)
  - 55-58 yards: 0.3% (extremely rare)
  - 59-65 yards: 0.1% (near-impossible)
  - Beyond 65: 0.0% (impossible)
- **`game_engine.py`**: Added hard 65-yard cap in `simulate_place_kick()` — kicks beyond this auto-miss.
- **`game_engine.py`**: Kick decision logic now refuses place kicks beyond 54 yards.
- **`game_engine.py`**: Stall handler now requires `fp >= 60` and `distance <= 50` for FG, `distance <= 55` for drop kick.

### Clock Logic
- **`game_engine.py`**: Added 10-second clock drain after all scoring plays (TD, FG, return TD, etc.) to simulate possession reset time.

### Playoff Balance
- **`game_engine.py`**: Disabled halo system entirely (`_should_use_halo()` always returns `False`). Individual player ratings now determine every play.
- **`game_engine.py`**: Increased power ratio exponent from 1.8 → 2.2. A 90 vs 60 matchup now produces 2.25x multiplier (was 1.78x).
- **`game_engine.py`**: Tightened contest variance from [0.8, 2.2] to [0.7, 1.7].
- **`game_engine.py`**: Reduced playoff composure variance from +25% to +8%.
- **`game_engine.py`**: Reduced underdog surge from +2/drive to +1/drive in playoffs.

### Fast Sim Team Strength (Previous Commit)
- **`fast_sim.py`**: `_team_strength()` and `_defensive_strength()` now compute averages from live player attributes instead of cached team values set at season creation. Player attribute edits now immediately affect game outcomes.

### Quality Wins
- **`season.py`**: Capped quality win score component at 20 points in power index.
- **`season.py`**: Display now shows weighted score instead of raw count.

### UI Fixes
- **`stats_site/templates/*/game.html`**: Field position now displays as "OWN 20", "50", "OPP 18" instead of raw 1-99 numbers. Applied to college, pro, WVL, and international templates.
- **`stats_site/templates/college/awards.html`**: All yardage stats now use `|round(1)` filter to prevent floating point display artifacts.

## Impact Summary

| Area | Before | After |
|---|---|---|
| Keeper ERA | 0.00 for all keepers | Realistic ERA based on points allowed per coverage snap |
| Diamond Gloves | Could go to -0.3 WPA keeper | Requires meaningful coverage + positive WPA |
| Field Goals | 90-yard FGs possible (3-8%) | Capped at 65 yards; 55+ yards near-impossible |
| Talent Gap (90 vs 60) | 1.78x multiplier, 90% halo override | 2.25x multiplier, individual ratings always used |
| Contest Variance | [0.8, 2.2] range | [0.7, 1.7] range |
| Playoff Composure | +25% variance (more random) | +8% variance (rewards consistency) |
| Quality Wins | Uncapped (could be 50+) | Capped at 20 points |
| Field Position | "82" | "OPP 18" |
| Yardage Display | "1477.300000000002" | "1477.3" |

## Testing

Ran full engine game simulation to verify keeper ERA fix:
- All 3 keepers per team now receive equal share of points allowed
- ERA calculation: `(13.0 / 44) * 9 = 2.66` — realistic range

## Notes

- The halo system was completely disabled. This is a significant change that makes individual player quality the primary driver of play outcomes. Teams with genuinely better players will now consistently perform better.
- The power ratio exponent increase (1.8 → 2.2) combined with variance tightening means talent gaps produce ~26% larger outcome differences per play. Over a full game (~80 plays), this compounds significantly.
- Field goal distance changes align with real-world physics — even the longest recorded NFL field goal is 66 yards, and viperball's sport design doesn't call for superhuman kicking range.
- Clock drain after scoring is set to 10 seconds (modest) since viperball has no traditional kickoff — just a possession reset.
