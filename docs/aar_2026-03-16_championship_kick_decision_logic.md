# After Action Review — Fix Championship Game Kick Decision Logic

**Date:** 2026-03-16
**Branch:** `claude/fix-championship-game-logic-zoWVE`

## Mission

Fix irrational late-game coaching AI decisions where the offense would kick field goals or snap kicks when trailing by more than the kick could score, and add smart snap kick mode activation for trailing teams in Q4.

## Incident

National Championship game: Arizona State (72.0) vs Nebraska Omaha (74.5). ASU trailed by ~5.5 points with seconds remaining. On the final drive, the coaching AI elected a **place kick (field goal, +3)** at the 63-yard line with 0:01 on the clock. The score moved to 72.0 — still losing by 2.5. A snap kick (+5) would have brought ASU to 74.5 (tie). A touchdown (+9) would have won outright. The AI chose the one option that was guaranteed to still lose.

**Why it happened:** Neither `select_kick_decision()` nor the stall/final-play auto-kick logic ever checked whether a kick's point value could overcome the deficit. The clock pressure flag (`Q4, <=3:00`) actually *encouraged* kicking — it was designed for "points are urgent" situations but didn't distinguish between "useful points" and "futile points."

Additionally, the stall/final-play code (V2.5) had a rigid preference hierarchy — `fp >= 55 → place kick` — that ignored the score entirely. It would always kick a FG from close range even when trailing by 6.

## Commits

| # | Hash | Summary |
|---|------|---------|
| 1 | `816ccf4` | Fix late-game coaching AI making irrational kick decisions when trailing |

## Scope

1 file changed, +78 / -11 lines

- `engine/game_engine.py` — all changes

## Issues Found & Fixed

### Critical — No Deficit Awareness in Kick Decisions

**Problem:** `select_kick_decision()` computed `score_diff` but only used it for clock pressure and lead management. It never asked "can this kick actually tie or win the game?" Every kick return path — 4th down gimme kicks, clock pressure kicks, green light kicks, stalling kicks, 5th/6th down kicks — was blind to the deficit.

**Fix — New helper method `_kick_can_tie_or_win()` (line ~4798):**

```python
def _kick_can_tie_or_win(self, kick_type, score_diff):
    if score_diff >= 0:
        return True  # Leading or tied — any points help
    deficit = abs(score_diff)
    if kick_type == PlayType.DROP_KICK:
        return deficit <= 5
    elif kick_type == PlayType.PLACE_KICK:
        return deficit <= 3
    return True
```

**Fix — Futility flags in `select_kick_decision()` (line ~4600):**

When `quarter == 4` and `time_left <= 180` and `score_diff < 0`:

| Deficit | `dk_futile` (snap kick) | `pk_futile` (field goal) | Action |
|---------|------------------------|-------------------------|--------|
| ≤ 3 | False | False | Either kick viable |
| 3.5 – 5 | False | **True** | Only snap kick considered |
| > 5 | **True** | **True** | Go for touchdown |

All kick return paths in downs 4, 5, and 6 are now gated by these flags. On down 6, if trailing with no viable kick and <=3:00 in Q4, the AI goes for it instead of punting (punting while losing is giving up).

**Scope:** This only applies in Q4 with <=3 minutes. Earlier in the game, kicking for partial points is rational because more possessions are coming.

### Critical — Stall/Final-Play Auto-Kick Ignores Score

**Problem:** The V2.5 clock-management final play (line ~4327) had a rigid hierarchy: `fp >= 55 → place kick`, `in dk range → snap kick`, `else → punt`. It never checked the score. This is the direct cause of the championship game incident — ASU's drive stalled at the 63, and the code blindly kicked a FG.

**Fix — Deficit-aware final play selection (line ~4340):**

The stall logic now computes the deficit and determines which kicks are viable:

| Deficit | Place kick viable? | Drop kick viable? | Decision |
|---------|--------------------|-------------------|----------|
| 0 (tied/leading) | Yes | Yes | Original hierarchy (FG if close, DK if in range, punt) |
| 1 – 3 | Yes | Yes | FG or DK based on range |
| 3.5 – 5 | **No** | Yes | Skip FG, attempt DK if in range |
| > 5 | **No** | **No** | Punt (no kick can help) |

In the championship scenario, ASU trailing by 5.5 at fp=63: place kick is skipped (deficit > 3), drop kick is skipped (deficit > 5), falls through to punt. Not ideal (a Hail Mary attempt would be better), but at least the AI isn't burning the last play on a kick that mathematically cannot win.

### High — kick_mode Never Activated (Dead Code)

**Problem:** `GameState.kick_mode` was declared (line 1179), checked in `simulate_play()` (line ~5343), and reset in multiple places (drive start, first down, change of possession) — but **never set to True anywhere**. The entire "rapid-fire snap kick on 4th-6th" system was dead code.

**Why this matters:** Snap kicks that miss only cost a down, not possession. When trailing by ≤5 late in Q4, the optimal strategy is to get into snap kick range and fire repeatedly — you get up to 3 attempts (4th, 5th, 6th down) to hit one. This is the Viperball equivalent of a no-huddle field goal offense.

**Fix — Late-game trailing snap kick mode activation (line ~5359):**

When `select_kick_decision()` returns `DROP_KICK` on 4th down AND:
- `quarter == 4`
- `time_remaining <= 180`
- `score_diff < 0` (trailing)
- `abs(score_diff) <= 5` (snap kick can tie/win)

→ Set `self.state.kick_mode = True`

This activates the existing kick_mode code path on 5th and 6th down, giving the team up to 3 consecutive snap kick attempts. Each miss advances the down but doesn't surrender possession, maximizing the chance of converting.

## Design Rationale

**Q: Why 3 minutes (180s) as the threshold?**
This matches the existing `clock_pressure` threshold. With <=3 minutes in Q4, the trailing team likely has 1-2 possessions left at most. Kicking for insufficient points wastes one of those precious possessions.

**Q: Why not also apply this in Q2 before the half?**
Before the half, any points have value because the game continues. Kicking a FG when trailing by 6 before halftime is reasonable — you're chipping away. In Q4 with the clock dying, it's not.

**Q: What about the edge case of trailing by exactly 5 and attempting a snap kick?**
A successful snap kick (+5) ties the game. Tying is strictly better than losing, so the kick is rational. The futility check uses `deficit <= 5` (not `< 5`) to allow tie-producing kicks.

**Q: Could kick_mode create degenerate behavior?**
It only activates under very specific late-game conditions (Q4, <=3min, trailing by <=5, on 4th down with a viable snap kick). It resets on first down, change of possession, or new drive — so it can't persist into normal play. The worst case is 3 missed snap kicks followed by turnover on downs, which is no worse than the old behavior of kicking a futile FG and losing anyway.

## What Was Not Changed

- **Lead management countermeasures** — The Slow Drip tendency still encourages kick-mode when leading. Deficit awareness only overrides when trailing.
- **Red zone logic** — The `fp >= 90` always-chase-TD rule was already correct and remains untouched.
- **Q2/halftime kicks** — Kicking for partial points before the half is still allowed regardless of deficit.
- **Defensive clamp rates** — Late-down defensive intensity is unchanged.
- **fast_sim.py** — The CPU fast-sim path doesn't model individual kick decisions, so no changes needed there.
