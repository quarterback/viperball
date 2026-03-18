# PRD: Playbook Boost Rebalance — March 2026

**Status:** Implemented
**Date:** 2026-03-18
**Branch:** `claude/balance-playbook-boosts-Fv94P`

---

## Problem Statement

Offensive playbook bonuses and coaching personality effects stack multiplicatively without caps, creating runaway amplification that distorts game outcomes:

1. **Excessive interception return TDs (pick-sixes):** INT returns averaged 35–60 yards with high variance, turning ~3.7% of all drives into defensive touchdowns. This makes turnovers disproportionately game-deciding compared to the offensive play that preceded them.

2. **Uncapped coaching multiplier stacking on play selection:** Coaching personality factors (aggression, tempo_preference, chaos_appetite, variance_tolerance) and sub-archetype/hidden-trait multipliers all compound independently on kick_pass and lateral weights. A coach with favorable sliders could push the combined multiplier above 2.4x, warping the play distribution.

3. **Offensive style bonus compounding:** `kick_pass_bonus` (up to 0.12), `explosive_lateral_bonus` (up to 0.25), and `lateral_success_bonus` (up to 0.15) feed into secondary multipliers (spacing factor, fumble reduction) that further amplify the base play weights.

4. **Aggressive defensive archetypes over-generating turnovers:** Predator defense's `turnover_bonus` (0.35) and `kick_pass_coverage` (0.20), combined with blitz_pack (0.30) and chaos (0.22), produce INT rates well above the 3–4% target.

---

## Goals

| Goal | Metric | Before | After | Target |
|------|--------|--------|-------|--------|
| Reduce pick-six frequency | INT return TD % of drives | 3.7% | 2.7% | 2–3% |
| Lower kick pass INT rate | KP INT / KP attempts | 5.0% | 4.6% | 3–4% |
| Cap coaching stacking | Max kick_pass weight multiplier | ~2.4x | 1.35x | ≤1.4x |
| Cap lateral stacking | Max lateral weight multiplier | ~1.8x | 1.30x | ≤1.3x |
| Normalize turnover_bonus | Predator turnover_bonus | 0.35 | 0.28 | 0.25–0.30 |

---

## Changes

### 1. Interception Return Yardage Reduction

**Lateral interceptions:**
- Mean return: `35 + talent * 25` → `20 + talent * 18`
- Std dev: 18 → 15

**Kick pass interceptions:**
- Mean return: `35 + talent * 20` → `18 + talent * 15`
- Std dev: 18 → 15

**Rationale:** The old formula produced a mean of 35–60 yards with 18-yard variance, meaning ~30% of INTs reached the end zone. The new formula yields 20–38 yard means, making pick-sixes require genuinely elite return talent or short-field position.

### 2. Coaching Multiplier Caps

| Multiplier Chain | Old Range | New Cap |
|---|---|---|
| kick_pass: `agg * tempo * kp_sub * kp_trait` | 0.56–2.44 | **1.35** |
| lateral_spread: `chaos * lat_mult` | 0.56–1.75 | **1.30** |
| trick_play: `risk * trick_mult` | 0.56–2.00 | **1.40** |
| variance_tolerance (explosive families) | 0.75–1.25 | **1.20** |

**Rationale:** The 3–4 layer multiplicative chain was unbounded. A coach with 100 aggression (1.25), 100 tempo (1.25), innovator sub-archetype (1.05), and lateral_enthusiast trait (1.15) could reach 1.25 × 1.25 × 1.05 × 1.15 = 1.89x on kick_pass alone. The cap ensures no single coaching profile warps play selection beyond ±35%.

### 3. Offensive Style Bonus Reductions

| Style | Bonus | Old | New |
|---|---|---|---|
| lateral_spread | explosive_lateral_bonus | 0.20 | 0.14 |
| lateral_spread | lateral_success_bonus | 0.10 | 0.08 |
| chain_gang | explosive_lateral_bonus | 0.25 | 0.18 |
| chain_gang | broken_play_bonus | 0.12 | 0.10 |
| chain_gang | lateral_success_bonus | 0.15 | 0.10 |
| boot_raid | kick_pass_bonus | 0.12 | 0.08 |
| ghost | kick_pass_bonus | 0.08 | 0.06 |
| shock_and_awe | explosive_lateral_bonus | 0.12 | 0.08 |
| shock_and_awe | broken_play_bonus | 0.10 | 0.08 |

**Rationale:** These bonuses feed into secondary systems (spacing factor, fumble reduction, explosive play modifiers) that compound them further. The reductions are 20–30%, preserving each style's identity while limiting the ceiling.

### 4. Defensive Turnover Bonus Reductions

| Defense | turnover_bonus | Old | New |
|---|---|---|---|
| predator | turnover_bonus | 0.35 | 0.28 |
| predator | kick_pass_coverage | 0.20 | 0.18 |
| blitz_pack | turnover_bonus | 0.30 | 0.25 |
| chaos | turnover_bonus | 0.22 | 0.18 |

**Rationale:** Predator's 0.35 turnover_bonus was the highest in the game by a wide margin and stacked with its 0.20 kick_pass_coverage to create a ~25% combined INT boost. The reduction narrows the gap between predator and other styles while keeping it the clear turnover leader.

### 5. Kick Pass INT Base Rate Reduction

| Subfamily | Old | New |
|---|---|---|
| Quick Kick | 0.09 | 0.07 |
| Territory | 0.16 | 0.13 |
| Bomb | 0.22 | 0.18 |
| Kick Lateral | 0.09 | 0.07 |

**Rationale:** ~20% across-the-board reduction to bring the aggregate kick pass INT rate from 5.0% toward the 3–4% target. These base rates are then modified by H2H matchups, coaching effects, and situational factors.

---

## Validation (Batch Sim: 200 games)

| Metric | Before | After | Target |
|---|---|---|---|
| INT return TD (% drives) | 3.7% | 2.7% | 2–3% |
| Kick pass INT rate | 5.0% | 4.6% | 3–4% |
| Avg score/team | ~42 | ~42 | 65–85 |
| TD/team | ~4.4 | ~4.3 | 6–8 |
| KP att/comp/int per game | 6692/4031/337 | 6779/4106/311 | — |
| Lateral INT rate | 11.8% | 11.4% | — |

**Note:** Avg score/team and TDs/team are below the 65–85 and 6–8 targets respectively. These are pre-existing calibration gaps unrelated to the boost rebalance; they affect snap kick and FG call rates (0.3 and 0.6/team vs 2–4 and 1–3 targets).

---

## Risk Assessment

- **Low risk:** All changes are numerical tuning to existing parameters. No structural/logic changes.
- **Style identity preserved:** Each offensive/defensive style retains its distinctive strengths — the changes only reduce the ceiling, not the floor.
- **Coaching personality still matters:** The caps are generous enough (1.35x for kick_pass, 1.30x for laterals) that coaching differences are still meaningful. Only extreme all-in-one-direction builds are constrained.

---

## Files Changed

- `engine/game_engine.py` — All changes in one file (34 insertions, 29 deletions)
