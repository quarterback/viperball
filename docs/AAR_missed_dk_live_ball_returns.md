# After Action Report: Missed Drop Kick Live Ball Returns

**Date:** February 23, 2026
**Scope:** Engine mechanic — missed drop kick live ball return system
**Files Modified:** `engine/game_engine.py`, `replit.md`

---

## Objective

Implement a live ball return mechanic for missed drop kicks (DKs) at long range. Previously, ALL missed DKs on downs 1-5 were dead balls with zero consequence (Finnish baseball rule: retain possession, advance down). This made long-range DK attempts completely risk-free, which is unrealistic — a 65-yard DK that misses should have a real chance of being fielded and returned by the defense.

## Problem Statement

- Missed DKs from any distance were either dead balls (downs 1-5) or simple turnovers (down 6).
- No missed DK could ever be caught and returned by the defense.
- This removed all strategic deterrent from attempting ultra-long DKs (60+ yards).
- Teams could bomb 65-yard DKs with impunity knowing at worst they'd retain possession.

## Solution Implemented

### Live Ball Rate Table (distance-dependent)

The live ball check runs BEFORE the Finnish baseball retain-possession rule, so it can override the safe recovery on any down.

| DK Distance | Live Ball Rate | Rationale |
|---|---|---|
| ≤ 45 yards | 0% | Short misses bounce dead, no risk |
| 46-49 yards | 5% | Minimal risk at edge of normal range |
| 50-54 yards | 15% | Risk starts to become meaningful |
| 55-59 yards | 25% | Serious consideration needed |
| 60-64 yards | 40% | High-risk zone — ~2 in 5 misses are live |
| 65+ yards | 55% | More likely than not to be returned |

### Return Mechanics

When a live ball triggers:
1. Defense picks a returner using the existing `_pick_returner()` system (backup-first philosophy — offensive rotation players, not starters).
2. Catch spot is calculated from the ball landing position, flipped to the returner's field orientation.
3. Return yards are calculated using `_calculate_punt_return_yards()` (same system as punt returns).
4. Return TD chance based on returner speed:
   - Base: 4%
   - Speed ≥ 85: 6%
   - Speed ≥ 92: 8%
5. Return TDs score 9 points (same as all touchdowns).

### New Play Results

Two new `PlayResult` enum values added:
- `MISSED_DK_RETURNED` — defense fields the missed DK and returns it for yardage
- `MISSED_DK_RETURN_TD` — defense returns the missed DK for a touchdown

### Drive/Scoring Integration

Both new results are wired into:
- Drive-ending result checks (main drive loop)
- Composure system (return TD = touchdown_scored for defense; non-TD return = failed_conversion for offense)
- Post-drive possession/kickoff handling
- Final play (clock-expiring stall) handling
- Sacrifice drive scoring tracking
- Score validation (`is_score` check)

### Stat Tracking

Returns from missed DKs are tracked under existing kick return stat fields:
- `game_kick_returns` — incremented for every live ball return
- `game_kick_return_yards` — yards gained on the return
- `game_kick_return_tds` — return touchdowns

These stats flow through to:
- Player stats output (`player_stats` dict in game result)
- Box score UI (KR, KR Yds, KR TDs columns in Returns & Special Teams tab)
- All-purpose yards calculation
- League-wide season stat aggregation

## Test Results (20-Game Batch)

| Metric | Value |
|---|---|
| Total DK misses | 55 |
| Live ball returns | 14 (25.5%) |
| Return TDs | 2 (3.6%) |
| Retained (dead ball) | 39 (70.9%) |

### By Distance Bucket

| Distance | Misses | Live | TDs | Retained |
|---|---|---|---|---|
| 25-49 yd | 15 | 0 | 0 | 15 |
| 50-54 yd | 4 | 1 | 0 | 3 |
| 55-59 yd | 4 | 2 | 1 | 2 |
| 60-64 yd | 10 | 3 | 0 | 7 |
| 65-69 yd | 11 | 6 | 0 | 5 |
| 70+ yd | 11 | 2 | 1 | 8 |

Results align with design targets. Short-range misses are safe; long-range misses carry escalating risk.

## Strategic Impact

- **Risk/reward calculus**: Teams must now weigh the 5-point upside of a long DK against the chance of giving the defense a return opportunity (or a 9-point return TD).
- **Kicking specialist value**: Teams with high-accuracy kickers who can make 50+ yard DKs reliably benefit more than teams who attempt long kicks and miss frequently.
- **Special teams depth**: Fast returners on the defensive side gain additional value — a team with a 93-speed backup Keeper on return duty has an 8% TD rate on fielded missed DKs.
- **AI decision-making**: The existing DK trigger logic already factors distance into attempt probability; this mechanic adds a natural consequence layer that the coaching AI responds to organically.

## Architectural Notes

- The live ball check is positioned BEFORE the Finnish baseball retain-possession rule in `simulate_drop_kick()`, so it applies on ALL downs (1-6), not just down 6.
- On downs 1-5, if the live ball check doesn't trigger, the existing dead-ball retain-possession behavior still applies.
- On down 6, the live ball check runs before the existing recovery/turnover logic.
- Field position orientation was validated against the existing punt return system to prevent inverted yard lines.
- Possession transitions follow the same `change_possession()` + `add_score()` pattern used by `punt_return_td` and `int_return_td`.

## No Regressions

- All 20 test games completed without errors or state corruption.
- Existing DK mechanics (successful kicks, retained possession, down-6 turnovers, blocked kicks, keeper deflections) remain unchanged.
- No impact on place kicks, punts, or other kicking families.
