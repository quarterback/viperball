# After Action Review — Fix Repeating Downs & Field Goals on Early Downs

**Date:** 2026-03-16
**Branch:** `claude/fix-championship-game-logic-zoWVE`

## Mission

Fix play-by-play showing duplicate down & distance on consecutive plays, and prevent the coaching AI from kicking field goals on downs 1-3.

## Incident

National Championship box score (Arizona State 72.0 vs Nebraska Omaha 74.5) showed multiple instances of "repeating downs" — consecutive plays displaying identical down, distance, and field position. Examples:

```
17:24  UNO  55  2&17  speed option  3
17:07  UNO  55  2&17  KICK PASS    45  — TOUCHDOWN!
```

```
50  3&5  sweep option   3
50  3&5  SPEED OPTION  50  — TOUCHDOWN!
```

```
42  2&13  PENALTY  7   — draw 7 + Unsportsmanlike on D 15 yds
42  2&13  KICK PASS 58 — TOUCHDOWN!
```

Additionally, a field goal was kicked on what was effectively 3rd down:

```
44:55  ASU  86  2&17  FIELD GOAL  15  — 39yd FG GOOD!
```

Kicking a field goal with 4 downs remaining is irrational — you can always kick later if the drive stalls.

## Commits

| # | Hash | Summary |
|---|------|---------|
| 1 | `d8070a6` | Fix repeating downs in play-by-play and field goals on early downs |

## Scope

1 file changed, +48 / -3 lines

- `engine/game_engine.py` — 4 distinct fixes across penalty handling, play state recording, and play selection

## Root Cause Analysis

Four independent bugs combined to produce the observed symptoms.

### Bug 1 — During-Play Offensive Penalties Don't Replay the Down

**Severity:** Critical
**Location:** `_apply_during_play_penalty()` (line ~5116)

**Mechanism:** When an offensive penalty (holding, illegal block) occurs during a play:

1. `simulate_run()` executes the play: gains 3 yards on 1st & 20
2. State is advanced: `state.down = 2`, `state.yards_to_go = 17`, `state.field_position = 41`
3. `_apply_during_play_penalty()` is called with the holding penalty
4. Handler reverses field position: `41 - 3 - 10 = 28` (play yards + penalty yards)
5. Handler zeros `play.yards_gained` and sets `play.result = "penalty"`
6. **BUG:** `state.down` remains `2`, `state.yards_to_go` remains `17`

**Expected:** Offensive penalty negates the play — down should replay as 1st & 20 at FP 28.
**Actual:** State shows 2nd & 17 at FP 28. The team lost a down for free.

**Impact:** Every offensive during-play penalty silently consumed a down. Over a full game this could cost a team 2-4 downs, affecting conversion rates and drive outcomes.

**Fix:** Restore `state.down` and `state.yards_to_go` to their pre-play values (saved at the start of `simulate_play()`):

```python
if on_offense:
    pre_fp = getattr(self, '_pre_play_fp', self.state.field_position)
    pre_down = getattr(self, '_pre_play_down', self.state.down)
    pre_ytg = getattr(self, '_pre_play_ytg', self.state.yards_to_go)
    self.state.field_position = max(1, pre_fp - penalty.yards)
    self.state.down = pre_down
    self.state.yards_to_go = pre_ytg
    play.yards_gained = 0
    play.result = "penalty"
```

### Bug 2 — Post-Play Defensive Penalties Don't Grant Automatic First Down

**Severity:** High
**Location:** `_apply_post_play_penalty()` (line ~5155)

**Mechanism:** After a play completes, a defensive post-play penalty (late hit, unsportsmanlike conduct) adds yardage to field position but never checks whether the penalty yards exceed the remaining yards to go.

**Example from the game:**
- Play: draw gains 7 on 1st & 20 → state becomes 2nd & 13 at FP 27
- Post-play penalty: Unsportsmanlike Conduct on defense, +15 yards → FP 42
- **BUG:** State remains 2nd & 13. The 15-yard penalty exceeds the remaining 13 yards to go, but no first down is awarded.

**Expected:** 1st & 20 at FP 42 (penalty yards 15 >= yards_to_go 13).
**Actual:** 2nd & 13 at FP 42.

**Comparison:** `_apply_pre_snap_penalty()` already had this check (line 5083-5085). `_apply_during_play_penalty()` for defensive penalties also had it (line 5127-5129). Only `_apply_post_play_penalty()` was missing it.

**Fix:**

```python
else:
    self.state.field_position = min(99, self.state.field_position + penalty.yards)
    if penalty.yards >= self.state.yards_to_go:
        self.state.down = 1
        self.state.yards_to_go = 20
```

### Bug 3 — Play Objects Store Inconsistent State (Pre-Play vs Post-Play)

**Severity:** High (display) / Medium (EPA calculation)
**Location:** `simulate_play()` and all `simulate_*()` functions

**Mechanism:** The `Play` dataclass stores `field_position`, `down`, and `yards_to_go`. These values are set from `self.state` at the time the Play object is created inside each simulation function. However:

- **GAIN/FIRST_DOWN plays:** State is modified *before* Play creation → stores **post-play** values
- **TOUCHDOWN/scoring plays:** State is *not* modified (drive ends) → stores **pre-play** values

This means a GAIN play followed by a TD play both display the same down/FP/ytg — the GAIN's post-state equals the TD's pre-state.

| Play | Result | FP stored | Down stored | Interpretation |
|------|--------|-----------|-------------|----------------|
| Sweep → 3 | GAIN | 50 (post) | 3 (post) | "After this play: 3rd & 5 at 50" |
| Speed → 50 | TD | 50 (pre) | 3 (pre) | "Before this play: 3rd & 5 at 50" |

The play-by-play shows both as "50, 3&5" — a confusing "repeated down."

**Secondary impact:** EPA calculation uses `calculate_ep(p.field_position, p.down)` as `ep_before`. For GAIN plays this was using post-play state, giving incorrect EPA values.

**Fix:** `simulate_play()` now saves pre-play state and stamps it on every returned Play:

```python
def simulate_play(self) -> Play:
    self.state.play_number += 1
    self._pre_play_fp = self.state.field_position
    self._pre_play_down = self.state.down
    self._pre_play_ytg = self.state.yards_to_go

    play = self._simulate_play_core()

    play.field_position = self._pre_play_fp
    play.down = self._pre_play_down
    play.yards_to_go = self._pre_play_ytg
    return play
```

Every play now consistently shows the *starting* situation, matching standard football box score conventions ("3rd & 5 at the 50: WB79 speed option → 50 — TOUCHDOWN!").

### Bug 4 — Field Goals and Snap Kicks Selectable on Downs 1-3

**Severity:** High
**Location:** `select_play_family()` (line ~5598)

**Mechanism:** `select_kick_decision()` correctly gates kick decisions to downs 4-6 (`if down <= 3: return None`). However, `select_play_family()` — the general play selection function — maintains non-zero weights for `snap_kick` and `field_goal` on ALL downs. When the weighted random selection happens to pick one of these families on downs 1-3, the play is dispatched as a kick, bypassing the kick decision gate entirely.

**Code path:**

```
simulate_play()
  → _simulate_play_core()
    → select_play_family()          ← can return FIELD_GOAL on down 2
      → PLAY_FAMILY_TO_TYPE[FIELD_GOAL] = PLACE_KICK
    → _dispatch_play(PLACE_KICK)
      → simulate_place_kick()       ← field goal on 2nd down
```

The `select_kick_decision()` gate is never consulted because the play was routed through the normal play selection path, not the kick decision path.

**Fix:** Zero out kick and punt weights on downs 1-3 in `select_play_family()`, with an exception for desperation clock situations (Q2/Q4 under 45 seconds) where the team may not have time to burn downs:

```python
desperation_clock = (quarter in (2, 4) and time_left <= 45)
if down <= 3 and not desperation_clock:
    weights["field_goal"] = 0.0
    weights["snap_kick"] = 0.0
    weights["punt"] = 0.0
```

Snap kicks on downs 2-3 are still possible through `_check_snap_kick_shot_play()`, which is a controlled decision (kicker skill + coaching style check), not a random weight selection. The desperation exception allows last-second kicks when there literally isn't time for another play.

## Interaction Between Bugs

The bugs compounded in the championship game:

1. **Bug 1** (penalty steals a down) → offense is on 2nd down when it should be 1st
2. **Bug 4** (FG on early downs) → weighted selection picks field_goal on that 2nd down
3. **Bug 3** (inconsistent state) → play-by-play shows "2&17" twice in a row
4. **Bug 2** (no auto-first-down) → defensive personal foul doesn't reset the down, perpetuating the off-by-one

A single offensive holding call early in a drive could cascade into a lost down, a premature field goal, and a confusing box score — all from one penalty.

## Design Note: Pre-Play State Stamping

The `_pre_play_*` attributes serve dual purpose:

1. **Display consistency** — Every play shows its starting situation
2. **Penalty rollback** — `_apply_during_play_penalty` uses the saved state to restore down/ytg when an offensive penalty negates a play

This avoids needing to reverse-engineer the pre-play state from the post-play state (which would require knowing exactly which code path modified state and how).

## What Was Not Changed

- **Pre-snap penalty handling** — Already correctly replayed the down (offensive) and checked for auto-first-down (defensive)
- **During-play defensive penalty handling** — Already checked for auto-first-down at line 5127-5129
- **`_check_snap_kick_shot_play()`** — Opportunistic snap kicks on downs 2-3 still work; only the uncontrolled weight-based selection was gated
- **EPA calculation** — Now implicitly fixed: `p.field_position` and `p.down` are pre-play values, so `calculate_ep(p.field_position, p.down)` correctly computes `ep_before`
- **Drive summary stats** — Drive yards are accumulated from `play.yards_gained` (unchanged), not from field position deltas, so the fix doesn't affect drive totals
