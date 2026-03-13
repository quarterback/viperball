# AAR: Late-Down Defensive Intensity Clamp & Yardage Tightening (V2.9)

**Date:** 2026-03-13
**Feature:** Defensive intensity ramp on downs 4-6, yardage generation rebalance
**Files Changed:** `engine/game_engine.py`

---

## Problem Statement

Sixth downs were too rare. In a 200-game simulation, only **1.4% of drives** ever reached 6th down, and 5th down appeared in just 4.3%. The entire late-down decision tree — the coaching AI's kick-or-go-for-it logic on 5th and 6th down, the Finnish baseball retention rule, the escalating risk/reward tension — was effectively dead code. Teams converted first downs so easily that the 6-down system played like a 3-down sport.

### Root Cause: Yards Per Play Too Generous

The 20-yard first-down threshold requires teams to sustain drives across multiple plays. But the yardage generation was calibrated for a world where that was too easy:

| Play Type | Avg Yards (Before) | Explosive Rate (20+ yds) |
|---|---|---|
| Run | 13.3 | 18% |
| Kick Pass | 15.5 | 28% |
| Lateral Chain | 8.9 | 9% |

With runs averaging 13.3 yards and kick passes 15.5, teams were converting first downs in ~1.5 plays. The down counter rarely climbed past 3rd. The sport's defining mechanic — six downs of mounting pressure — was invisible.

A secondary problem: the `_fourth_down_decision()` method was dead code from when Viperball briefly used 4 downs. It was never called; `select_kick_decision()` had fully replaced it. Removed as cleanup.

## Solution: Two-Layer Approach

### Layer 1: Tighten Yardage Generation

Reduced yards at the source — no artificial barriers, just tighter natural mechanics.

**Run plays (`_contest_run_yards`):**

| Parameter | Before | After |
|---|---|---|
| `base_yards_multiplier` | 4.2 | 2.3 |
| Explosive rate (early downs) | 26% | 4.5% |
| Explosive multiplier | 1.8x | 1.33x |
| Bust rate (early downs) | 4% | 7% |

**Kick pass plays (`simulate_kick_pass`):**

| Sub-Family | Base Distance Before | Base Distance After |
|---|---|---|
| Quick Kick | 5-8 | 3-6 |
| Territory | 10-16 | 7-12 |
| Bomb | 22-30 | 18-25 |

YAC (yards after catch) also reduced across all sub-families:
- Quick Kick YAC floor: 3-8 → 1-5
- Territory YAC floor: 2-5 → 1-3
- Bomb caught-in-stride rate: 35% → 22%
- Bomb caught-in-stride YAC: 10-20 base → 6-14 base

### Layer 2: Late-Down Defensive Intensity Clamp

On downs 4-6, the defense gets a dice-roll chance to squelch the play — reducing yards to a stuff or minimal gain regardless of what the offense executed. This models the reality that defenses dial up pressure when they smell a stop.

**Method:** `_late_down_defensive_clamp(yards)`

Applied universally at five resolution points:
1. Run plays (before TD/first-down check)
2. Trick plays (before outcome resolution)
3. Lateral chains (after breakaway check)
4. Kick pass completions (after tackle reduction)
5. Kick-lateral completions (after chain resolution)

**Base clamp probabilities (at neutral matchup):**

| Down | Clamp Chance | Yard Reduction Range |
|---|---|---|
| 4th | 20% | -10% to +25% of original |
| 5th | 35% | -15% to +20% of original |
| 6th | 50% (coin flip) | -20% to +15% of original |

### Matchup-Driven Scaling

The clamp probability scales with the H2H talent gap between the defensive and offensive units on the field. This is the key design decision: the clamp isn't a flat dice roll — it respects the matchup.

**How it works:**

1. Compute average defensive rating: `tackling(0.40) + awareness(0.35) + speed(0.25)`, fatigue-weighted
2. Compute average offensive rating: `speed(0.30) + agility(0.25) + power(0.20) + awareness(0.25)`, fatigue-weighted
3. Normalize the gap: `gap_norm = (avg_def - avg_off) / 100.0`
4. Exponential scaling: `matchup_scale = clamp(0.15, 2.2, e^(gap_norm * 5.0))`

**Why exponential?** Small talent deltas should feel random. When OVR 88 plays OVR 87, or OVR 88 plays OVR 79, the gap isn't large enough to be deterministic — the dice should dominate. But when OVR 90 plays OVR 50, the defense should reliably squelch drives. Linear scaling treats a 3-point gap and a 40-point gap the same way (proportionally). Exponential scaling makes small gaps nearly neutral while big gaps diverge fast:

```
gap = 0   (even)    → scale = 1.00  → base rates apply
gap = +5  (slight)  → scale = 1.28  → 4th: 26%, 5th: 45%, 6th: 64%
gap = +15 (big)     → scale = 2.12  → 4th: 42%, 5th: 60%, 6th: 70% (capped)
gap = -5  (off edge)→ scale = 0.78  → 4th: 16%, 5th: 27%, 6th: 39%
gap = -15 (blowout) → scale = 0.47  → 4th: 9%,  5th: 16%, 6th: 24%
```

## Results

200-game simulation (Washington U vs Southern Illinois):

### Down Distribution

| Down | Before (% of plays) | After (% of plays) |
|---|---|---|
| 1st | 44.5% | 38.2% |
| 2nd | 30.5% | 28.8% |
| 3rd | 15.0% | 17.5% |
| 4th | 7.8% | 10.8% |
| 5th | 1.8% | 3.4% |
| 6th | 0.4% | 1.2% |

### Drives Reaching Each Down

| Down | Before | After | Change |
|---|---|---|---|
| 4th | 18.1% | 22.7% | +4.6pp |
| 5th | 4.3% | 8.3% | +4.0pp |
| 6th | 1.4% | 4.9% | **+3.5pp (3.5x)** |

### Yards Per Play

| Play Type | Before | After |
|---|---|---|
| Run | 13.3 | 7.4 |
| Kick Pass | 15.5 | 13.3 |
| Lateral Chain | 8.9 | 9.8 |
| Trick Play | 4.1 | 4.2 |

### Scoring

| Metric | Before | After |
|---|---|---|
| Avg combined score | ~110 | 97.2 |

## What This Unlocks

The coaching AI's late-down decision tree is no longer theoretical. With nearly 5% of drives reaching 6th down:

- `select_kick_decision()` down-5 logic (the "setup shot") fires 8.3% of drives
- `select_kick_decision()` down-6 logic ("last chance — kick > punt > go for it") fires 4.9% of drives
- The `GO_FOR_IT_MATRIX` thresholds on 5th and 6th down are now meaningful decision points
- Finnish baseball retention on snap kick misses creates real 5th→6th down sequences
- Lead management countermeasures (V2.7) that bias toward kick mode on late downs have material impact

## Files Changed

| File | Lines | Change |
|---|---|---|
| `engine/game_engine.py` | 56-61 | `base_yards_multiplier` 4.2 → 2.3 |
| `engine/game_engine.py` | 7186-7203 | Run explosive rate 26%→4.5%, multiplier 1.8x→1.33x, bust 4%→7% |
| `engine/game_engine.py` | 8460-8474 | Kick pass base distances reduced ~25% |
| `engine/game_engine.py` | 8806-8826 | Kick pass YAC reduced, bomb stride rate 35%→22% |
| `engine/game_engine.py` | 4701-4750 | New `_late_down_defensive_clamp()` method |
| `engine/game_engine.py` | 7782,8056,8433,8849,9044 | Clamp wired into 5 play resolution points |
| `engine/game_engine.py` | 4701 (old) | Removed dead `_fourth_down_decision()` (78 lines) |

## Commits

| Hash | Description |
|---|---|
| `b070dbd` | Remove dead `_fourth_down_decision()` from 4-down era |
| `fce32fc` | Tighten yardage generation to increase late-down frequency |
| `af8ddc0` | Lower run explosive rate to 4.5% |
| `45b7436` | Add late-down defensive intensity clamp |
