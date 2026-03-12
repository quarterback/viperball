# After Action Review — Fix Interception & Down Conversion Rates

**Date:** 2026-03-12
**Branch:** `claude/fix-interception-down-rates-26Keq`

## Mission

Fix unrealistically low interception rates and underperforming 5th/6th down conversion rates in the Viperball simulation engine.

## Commits

| # | Hash | Summary |
|---|------|---------|
| 1 | `d6c8d23` | Fix low interception rates and boost 5th/6th down conversion |

## Scope

2 files changed, +18 / -17 lines

- `engine/game_engine.py` — 14 lines changed across 8 locations
- `engine/fast_sim.py` — 4 lines changed

## Issues Found & Fixed

### Critical — Interception Rates Too Low

**Problem:** Games averaged ~1 INT/game, and 47% of games had zero interceptions — far too rare for a sport where kick passes replace traditional passing.

**Root cause:** Base INT rates for kick pass sub-families were set conservatively at 5–16%, and the INT floor/ceiling clamp (2%–25%) further suppressed outliers.

**Fix (game_engine.py lines 9034–9040):**

| Sub-family | Before | After |
|------------|--------|-------|
| Quick Kick | 5% | 9% |
| Territory | 10% | 16% |
| Bomb | 16% | 22% |
| Kick Lateral | 5% | 9% |

**Fix (game_engine.py line 9063):** Widened the INT clamp from `[0.02, 0.25]` to `[0.04, 0.30]`.

**Expected outcome:** ~2.25 INTs/game, only ~11% zero-INT games.

### High — Lateral Interception Rates Too Low

**Problem:** Lateral INTs were nearly non-existent due to a 3% base rate clamped to `[1.5%, 6%]`.

**Fix (game_engine.py lines 8115, 8697):** Raised base rate from 3% to 5% in both lateral chain locations (standalone laterals and kick-pass lateral chains).

**Fix (game_engine.py lines 8119, 8701):** Widened clamp from `[1.5%, 6%]` to `[2.5%, 10%]`.

### High — 5th/6th Down Conversion Rates Too Low

**Problem:** 5th and 6th down conversions were around 51%, well below the design targets of ~71% (5th) and ~63% (6th). The urgency modifiers for late downs were *reducing* performance instead of reflecting desperation play-calling.

**Fix — Run yard generation (game_engine.py lines 7008, 7021):**
Urgency multiplier for run plays changed from `{5: 0.82, 6: 0.65}` to `{5: 1.20, 6: 1.10}`. Previously, 5th/6th down runs aimed *shorter* than 4th down — now they aim slightly *longer*, reflecting aggressive play-calling.

**Fix — Kick pass completion probability (game_engine.py line 7336):**
Late-down urgency bonus changed from `{5: 0.28, 6: 0.18}` to `{5: 0.55, 6: 0.50}`. This gives kickers a meaningful accuracy boost under pressure on must-convert downs.

**Fix — Kick pass distance targeting (game_engine.py lines 8474–8477):**
On 5th/6th down, the kick distance now blends more aggressively toward yards-to-go:

| Down | Old blend (kick/target) | New blend (kick/target) |
|------|------------------------|------------------------|
| 4th | 50/50 | 45/55 |
| 5th | 50/50 | 35/65 |
| 6th | 50/50 | 30/70 |

Target distance also raised from `ytg` to `ytg + 3` to overshoot slightly.

**Fix — Lateral chain yard boost (game_engine.py line 8310):**
Urgency boost changed from `{5: 1.0, 6: 0.5}` to `{5: 1.5, 6: 1.2}`, giving lateral chains meaningful extra yardage on late downs.

### Medium — Fast Sim INT Rates Out of Sync

**Fix (fast_sim.py lines 366, 370):** Aligned CPU fast-sim INT generation with new engine rates:
- Kick pass INT rate: `0.10` → `0.16`
- Lateral INTs per game: `gauss(0.5, 0.5)` → `gauss(1.0, 0.6)`

## Design Rationale

**Interceptions:** Viperball's kick pass is the primary "passing" mechanism. With 15–25 kick pass attempts per game, a ~15% average INT rate yields ~2–3 INTs/game — creating meaningful turnover battles and strategic tension without making the kick pass unusable.

**Down conversions:** Viperball allows 6 downs (vs football's 4). 5th and 6th downs should feel desperate but not hopeless — teams are playing aggressively and taking risks. The old urgency multipliers (<1.0) counterintuitively made late-down plays *worse*, as if teams gave up. The new values (>1.0) reflect the expected aggressive play-calling while still keeping conversion below 4th-down rates due to defensive adjustments captured elsewhere in the model.

## Known Remaining Items

| Item | Severity | Notes |
|------|----------|-------|
| Turnover Machine prestige bonus unchanged | Low | +2% INT / +3% fumble still stacks on top of new rates; may need tuning if turnover-machine teams produce too many turnovers |
| Gameday Manager INT reduction unchanged | Low | The `int_chance_reduction` multiplier still applies; verify it doesn't over-suppress INTs with the new higher base rates |
| Diagnostic validation | Medium | Run `diag_conversion.py` over a large sample to confirm actual rates match targets |

## Testing Notes

- Simulated games should now average ~2.25 interceptions per game
- Zero-INT games should drop from ~47% to ~11%
- 5th down conversion rate should be approximately 71%
- 6th down conversion rate should be approximately 63%
- Run `python diag_conversion.py` for a large-sample validation pass
