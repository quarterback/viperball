# Post-Feature Report: Talent Generation Rebalance

**Date:** 2026-03-27
**Branch:** `claude/balance-talent-generation-mS413`
**PR:** #240

## Overview

Complete overhaul of the talent generation system to fix a scoring crisis. Teams were routinely putting up 100+ points because the engine generated too many 90+ OVR players with maxed-out stats. The root cause was a combination of inflated stat centers, narrow gaussian spreads, no hard ceiling on generation, and a hidden per-team offset in the runtime code path that could add +50 points to any team's base stats.

## What Changed

### Files Modified

| File | What changed |
|---|---|
| `scripts/generate_rosters.py` | Archetype centers, spreads, stat ceiling, stat budget, hidden gem caps, archetype thresholds |
| `engine/game_engine.py` | Removed team_center_offset, fixed hidden gem cap |
| `engine/recruiting.py` | Star tier ranges, position boost caps, OVR floor |
| `engine/transfer_portal.py` | Portal stat ranges, position boost caps, potential distribution |
| `engine/development.py` | Development gain tables halved, OVR floor |
| `engine/player_card.py` | OVR floor |
| `engine/season.py` | FCS filler generation disabled |

### The Numbers

#### Archetype stat centers (the big lever)

| Archetype | Before | After | Gap |
|---|---|---|---|
| doormat | 28 | 15 | -13 |
| underdog | 50 | 20 | -30 |
| punching_above | 65 | 35 | -30 |
| regional_power | 78 | 44 | -34 |
| national_power | 89 | 52 | -37 |
| blue_blood | 95 | 64 | -31 |

#### Gaussian spread

All tiers: **3-6 → 38.** Every player's stats swing wildly around their center. A blue blood Viper might roll 85 speed and 26 awareness on the same card. No more clones.

#### Generation ceiling

**99 → 85.** No individual stat can exceed 85 at generation across any pipeline (roster, recruiting, portal). The development system keeps its 99 ceiling for dynasty mode where progression over multiple seasons earns elite stats.

#### Stat budget

Total stat points per player capped at `center × 11 + 44`. If the sum exceeds the budget, excess is trimmed from the highest stats first. This preserves the player's profile shape while preventing uniformly excellent players.

#### Recruiting stat ranges

| Star | Before | After |
|---|---|---|
| 5-star | 83-98 | 49-63 |
| 4-star | 72-90 | 37-54 |
| 3-star | 58-78 | 25-45 |
| 2-star | 45-68 | 15-35 |
| 1-star | 35-58 | 15-25 |

#### Transfer portal stat ranges

| Type | Before | After |
|---|---|---|
| Base (Soph/Jr) | 65-90 | 28-52 |
| Senior/Graduate | 70-93 | 32-56 |

5-star potential in portal: 10% → 6%.

#### Development gains (per stat per offseason)

| Profile | Before | After |
|---|---|---|
| quick | +2 to +5 | +1 to +3 |
| normal | +1 to +3 | +0 to +2 |
| slow | +0 to +2 | +0 to +1 |
| late_bloomer (late) | +3 to +7 | +1 to +4 |

#### Archetype assignment thresholds

Lowered proportionally to match the 85 ceiling (e.g. speed_flanker: 93 → 78, receiving_viper: 90/90 → 75/75). Without this, most archetype slots would never trigger and every player would fall into default categories.

#### OVR floor

40 → 10 across player_card.py, recruiting.py, and development.py. The full talent range is now visible.

#### Other

- **team_center_offset removed.** Was `random.gauss(0, 25)` — could add +50 to a team's effective center, producing entire rosters of 90+ players. This was the single biggest bug.
- **Hidden gem boost caps:** 100 → 85 (game_engine.py), 99 → 85 (generate_rosters.py).
- **FCS filler disabled.** With 205 real teams, fictional schedule-fill teams are unnecessary.
- **Conference floors lowered ~30 points** to match new scale.

## Why This Fixes Scoring

The scoring problem was caused by stat density at the top. When both teams field 11 starters averaging 95+ OVR with no weaknesses, every offensive play has a high probability of success. The engine's play resolution math produces big gains because high speed beats high tackling beats high power in a near-uniform way — there are no mismatches to exploit when everyone is maxed.

With base stats now in the 40s-60s and a hard ceiling of 85:

1. **Contested plays become the norm.** A Viper with 72 speed isn't guaranteed to beat a Keeper with 65 tackling. The outcome depends on scheme, multipliers, and matchup specifics.
2. **Player weaknesses create defensive opportunities.** A speed flanker with 80 speed but 35 kick accuracy and 28 lateral skill is a one-dimensional threat that defenses can scheme against.
3. **Team depth matters.** With spread 38, starters have wildly different profiles. A team's offensive output depends on which players are on the field for which plays, not a uniform wall of talent.
4. **In-game multipliers drive separation.** Two teams with similar raw stats (50s-60s center) are differentiated by coaching scheme, game-day adjustments, and multiplier stacking. The team that coaches better wins, not the team that rolled better at generation.

## What This Means for Each Mode

### Single Season

This is where the fix matters most. There's no development system — what generates IS the final product. With the 85 ceiling, the best player on the best team in the game has stats ranging from ~45-85 with huge variance. No player dominates every phase. Scoring is driven by scheme and matchups.

### Dynasty Mode

Players arrive as raw projects (50s-60s OVR on elite teams). The development system — still capped at 99 — is what creates stars over 2-4 seasons. A 5-star quick developer gains +1-3 per stat per offseason, reaching the mid-70s by junior year and potentially 80+ by senior year. Reaching 90+ requires exceptional potential AND multiple full seasons of quick development. That's the dynasty arc.

### Transfer Portal

Portal players arrive with modest stats (28-56 range). They're depth pieces and role players, not instant stars. A senior portal entry might have one strong stat from position boosts but won't be an all-around elite player.

## Tuning Levers

If the balance needs further adjustment, these are the independent levers:

| Lever | Current | Effect of increasing | File |
|---|---|---|---|
| `stat_center` per archetype | 15-64 | Raises team baseline | `generate_rosters.py` |
| `stat_spread` | 38 | More variance within players | `generate_rosters.py` |
| Generation ceiling | 85 | Higher individual stat peaks | `generate_rosters.py` (+ recruiting, portal, game_engine) |
| Stat budget headroom | center×11+44 | More total stat points allowed | `generate_rosters.py` |
| Development gains | +0-3 per stat | Faster/slower progression | `development.py` |
| Development ceiling | 99 | Max achievable through development | `development.py` |
| Hidden gem boost | 5-30 by tier | Stronger/weaker standout players | `generate_rosters.py` |
| Portal ranges | 28-56 | Better/worse portal talent | `transfer_portal.py` |
| Recruit ranges | 15-63 by star | Better/worse recruiting classes | `recruiting.py` |

The most impactful single lever is the generation ceiling. Moving it from 85 to 90 would immediately allow more dominant individual stats. Moving it to 75 would compress the top end further. Everything else scales around it.

## Known Considerations

- **Archetype thresholds were lowered** to match the 85 ceiling. If the ceiling changes significantly, these thresholds (`assign_archetype()` in generate_rosters.py) need to be rescaled or most players will default to generic archetypes.
- **Existing dynasty saves are unaffected.** Players already generated with inflated stats retain them until they graduate. New recruits and portal entries will arrive at the new, lower baseline.
- **UI display:** Player cards now show stats in the 30s-70s range. This is correct — the numbers represent raw talent, not finished product. In dynasty mode, watching these numbers climb through development is the core loop.
- **FCS generation is disabled but not deleted.** The code remains in `engine/season.py` as dead code. If a future configuration needs fewer than 205 teams, it can be re-enabled with adjusted stat ranges.
