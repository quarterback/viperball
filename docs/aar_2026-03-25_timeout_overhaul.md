# AAR: Timeout System Overhaul

**Date:** 2026-03-25
**Branch:** `claude/referee-bias-system-B6KAy`

---

## Problem

Timeouts were being hoarded until the final 2-5 minutes of each half. A typical game had only 1-2 charged timeouts total, almost all in Q4, with both teams ending the game with 3-4 unused timeouts per half. This produced unrealistic gameplay:

1. **No mid-game coaching**: Coaches never called timeout to stop momentum, reset after a bad play, ice a kicker, or give tired players a breather
2. **Victory formation abuse**: With so many TOs left late, the kneeling math allowed 4-minute kneel sequences
3. **No strategic variety**: Every game had the same late-game timeout pattern — defense burns TOs after opponent kneels, offense hoards them all

Real coaches use timeouts throughout the game. The 3-minute warning in Viperball (like the 2-minute warning in NFL) acts as a "free timeout," so teams can afford to be more aggressive with early-game usage.

## Root Cause

The old system had 5 categories, but 4 of them only triggered in the final minutes:

| Category | Old Trigger Window | % of Game Covered |
|----------|-------------------|-------------------|
| Strategic clock stop | Q4 <5min or Q2 <1min | ~12% |
| Offensive clock stop | Q2/Q4 <2min | ~8% |
| Star fatigue rest | Red zone + exhausted stars | ~2% (too narrow) |
| Personnel regrouping | Q1-Q3, 4+ plays with ≤2 yards | ~5% (but `_drive_yards` wasn't tracked) |
| Injury (official) | Random 0.3% per play | Always available |

The personnel regrouping category had a bug: it checked `_drive_yards` but that attribute was never set (always defaulted to 0 via `getattr`), so it could trigger on any drive with 4+ plays — but at only 5% probability, it rarely did.

## What Changed

### New Timeout Categories

| Category | Caller | When | Quarters | Probability |
|----------|--------|------|----------|-------------|
| **Momentum stop** | Defense | After 2+ consecutive opponent scoring drives | Any | 8-20% per play |
| **Scheme reset** | Offense | After sack/big loss or 2+ consecutive negative plays | Any | 12-25% per play |
| **Icing the kicker** | Defense | Before kick attempt on 5th-6th down in close games | Any | 20-35% |
| **Fresh legs** | Either | 3+ starters have energy below 40% | Q1-Q3 | 10-20% |

### Existing Categories Retuned

| Category | Old Trigger | New Trigger |
|----------|-------------|-------------|
| Strategic clock stop | Q4 <5min, Q2 <1min | Q4 <5min, Q2 <90s |
| Offensive clock stop | Q2/Q4 <2min | Q2/Q4 <3min |
| Personnel regrouping | Q1-Q3 only, 5% prob | Any quarter, 10% prob, uses real `_drive_yards` |
| Star fatigue rest | Unchanged | Unchanged |

### Coaching Intelligence

- **3-minute warning awareness**: Coaches budget their TOs knowing the 3MW acts as a free clock stop. Good clock managers (`clock_mgmt > 0.5`) save at least 1 TO as a reserve.
- **Q4 suppression**: Non-clock timeout categories (momentum, scheme reset, fresh legs) are heavily suppressed in Q4 with <3 minutes left to preserve TOs for strategic use.
- **Trait integration**: `timeout_hoarder` coaches resist all categories by 30-60%. `timeout_sprinter` coaches burn them 25-50% faster.

### Bug Fixes

1. **`_drive_yards` now actually tracked** as an instance attribute, updated per play
2. **`_drive_consecutive_negative`** tracked for scheme reset logic
3. **`_consecutive_opponent_scores`** tracked per team for momentum stop logic
4. **Victory formation** restricted to ≤50 seconds remaining (separate commit)

## Results

**20-game sample (70-rated teams):**

| Metric | Before | After |
|--------|--------|-------|
| Avg TOs per game | ~2 | 6.3 |
| TOs remaining (avg/team) | 3-4 | ~2 |
| Q1-Q3 timeouts | Rare | Common |
| Timeout categories used | 2-3 | 5-6 |
| Most common category | Strategic clock stop | Scheme reset (34%) |

**Category breakdown (20 games, 126 charged TOs):**
- Scheme reset: 34%
- Momentum stop: 26%
- Offensive clock stop: 24%
- Strategic clock stop: 12%
- Defensive kneel stop: 4%

**Sample game timeline:**
```
Q1 09:30 — Gonzaga (scheme reset, 3 left)
Q2 01:18 — Gonzaga (offensive clock stop, 2 left)
Q3 07:27 — Gonzaga (scheme reset, 3 left)
Q4 04:41 — Oregon State (momentum stop, 3 left)
Q4 01:13 — Gonzaga (offensive clock stop, 2 left)
Q4 00:19 — Gonzaga (offensive clock stop, 1 left)
```

## What's Not Done Yet

- **Icing the kicker** and **fresh legs** didn't trigger in the 20-game sample (both require specific game state that didn't occur with 70-rated generic rosters). They should appear organically in full-season simulations with varied rosters and weather.
- **Timeout budgeting per half**: Currently teams get 4/half and reset. The system doesn't model coaches who deliberately save 2 TOs for the end vs. those who burn all 4 early. This could be a future coaching personality dimension.
- **Pre-3MW timeout**: A specific "use timeout at 3:15 to get one more play before the warning" pattern isn't modeled. The 3MW suppression of early-game TOs partially handles this.
- **Wasted challenges**: The coach challenge system (separate feature) can waste a TO on a failed challenge. This isn't integrated with the timeout budget yet.
