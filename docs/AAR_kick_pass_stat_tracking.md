# After Action Report: Kick Pass Stat Tracking Fixes

**Date:** February 23, 2026
**Scope:** Engine bug fix — kick pass yards double-counting and possession attribution
**Files Modified:** `engine/game_engine.py`
**Commit:** `19b9b37`

---

## Objective

Fix a three-part bug where kick pass player-level stats (yards, attempts) diverged from team-level stats derived from Play objects. Player stats were overcounting yards on TDs and attempts were being attributed to the wrong team on turnovers.

## Problem Statement

When comparing player-level `game_kick_pass_yards` to team-level stats calculated from Play objects:

- **Yards**: Player stats showed ~60-70 extra yards per game compared to Play object sums. The discrepancy tracked closely with TD play yardage.
- **Attempts**: Player `game_kick_passes_thrown` count didn't match the number of `play_type="kick_pass"` Play objects for each team. One team would show +1, the other -1.
- **Root cause**: State mutation (`change_possession()`, TD yard override) happening before/after stat recording, creating inconsistencies between the two stat sources.

## Bugs Found and Fixed

### Bug 1: TD Yards Double-Counting

**Mechanism:**

```
1. Breakaway check inflates yards_gained (e.g., 90 yards)
2. Line 6868: kicker.game_kick_pass_yards += 90  (pre-TD value)
3. TD check triggers: yards_gained = 100 - field_position = 64
4. Line 6879: kicker.game_kick_pass_yards += (64 - total_yards)  (adjustment)
5. Player total: 90 + (64 - 16) = 138 yards
6. Play object: 64 yards
7. Overcounting: 74 yards
```

When breakaway check inflated `yards_gained` beyond the actual TD distance, the player got both the inflated breakaway yards AND the TD adjustment — effectively double-counting.

**Fix:** Removed the pre-TD yard tracking (old line 6868-6869) and the post-TD adjustment (old line 6879-6880). Added a single yard tracking line AFTER the TD determination, using the final `yards_gained` value. This ensures player stats always match the Play object's yards.

```python
# BEFORE (two-phase tracking with adjustment)
kicker.game_kick_pass_yards += yards_gained       # pre-TD
# ... TD check ...
kicker.game_kick_pass_yards += (yards_gained - total_yards)  # adjustment

# AFTER (single tracking after TD check)
# ... TD check finalizes yards_gained ...
kicker.game_kick_pass_yards += yards_gained       # final value only
```

### Bug 2: INT Possession Attribution

**Mechanism:** Kick pass interceptions called `self.change_possession()` before creating the Play object. The Play's `possession` field then reflected the intercepting team, not the throwing team.

```
1. Home team throws kick pass
2. INT detected → change_possession() → state.possession = "away"
3. Play created with possession = self.state.possession = "away"
4. Result: Home's KP attempt counted as Away's play in the log
5. Team-level: Home attempts -1, Away attempts +1
```

**Fix:** Save `throwing_team = self.state.possession` before `change_possession()`, then use `throwing_team` in the Play object's `possession` field. Applied to both INT and INT-return-TD paths.

### Bug 3: Fumble Possession Attribution

**Mechanism:** Identical to Bug 2, but on the fumble-on-catch path. When defense recovered a KP fumble, `change_possession()` ran before Play creation, misattributing the play.

Three sub-paths affected:
1. Defense recovers fumble (turnover)
2. Offense recovers fumble but turnover on downs (6th down exceeded)
3. Offense recovers fumble (gain continues)

**Fix:** Same pattern — save `throwing_team_fum = self.state.possession` before any fumble-related `change_possession()` call, use it in all three Play objects.

## Verification

### Single-Game Trace (seed=42, Agnes Scott vs Air Force)

| Metric | Before Fix | After Fix |
|---|---|---|
| Home attempts (player vs plays) | 18 vs 17 | 18 vs 18 |
| Away attempts (player vs plays) | 8 vs 9 | 8 vs 8 |
| Home yards (player vs plays) | 274 vs 208 | 210 vs 208 |
| Away yards (player vs plays) | 218 vs 154 | 154 vs 154 |

### Batch Test (20 games, 40 team-sides)

| Metric | Before Fix | After Fix |
|---|---|---|
| Attempts exact match | ~90% | **100% (40/40)** |
| Yards exact match | ~60% | **85% (34/40)** |
| Yards unaccounted diff | Multiple | **0** |

The 6/40 remaining yards differences are all from the **penalty system** (pre-existing, separate issue): during-play penalties replace `play.yards_gained` with penalty yardage after player stats are already recorded. These are NOT kick pass tracking bugs.

## Known Remaining Issue: Penalty Yard Replacement

The `_apply_during_play_penalty()` method replaces `play.yards_gained` with either 0 (offensive penalty) or penalty yards (defensive penalty) AFTER the play function has already recorded player-level stats. This creates a small, predictable divergence:

- **Offensive penalty on KP completion**: Player has original yards, Play has 0 → player overcounts
- **Defensive penalty on KP completion**: Player has original yards, Play has penalty yards → slight mismatch

This affects ~15% of team-sides per batch and is a broader penalty system design question, not specific to kick passes. All other play types (run, lateral) have the same characteristic.

## Design Principle Established

**"Save possession before mutating state"** — Any play that can change possession (INT, fumble recovery, turnover on downs) must save `self.state.possession` to a local variable BEFORE calling `change_possession()`, then use the saved value in the Play object. This ensures Play objects always record WHO initiated the play, not who ended up with the ball.

This same pattern likely exists in run fumble and lateral fumble paths but was not addressed in this fix (scope limited to kick pass tracking).

## Files Changed

| File | Lines Changed | Nature |
|---|---|---|
| `engine/game_engine.py` | ~80 lines | Moved yard tracking after TD check; saved possession before turnovers in 5 Play return paths |
