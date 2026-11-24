# AAR: BOX-01 — box-score source-of-truth reconciliation

**Date:** 2026-11-24  
**Branch:** `engine/boxscore-ledger-reconciliation-20261124`  
**Base:** `main` after merged PEN-01/INJ-01 (#350, merge b5ca69a).  
**Scope:** authoritative finalized scoring breakdowns, kick-pass team/player parity, turnover attribution, and a scored-event audit. ST-01/02 remains separately owned in draft #349.

## Trigger: UALR at Lehigh, Week 1, from pre-ST main

The user-provided complete box score reports UALR 64.5, Lehigh 68.0. The
presentation simultaneously reports four touchdowns for each team, five
UALR snap kicks and four Lehigh snap kicks, one place kick apiece, and
one UALR return TD. These visible methods imply **73 vs 59** without
bells, safeties, or pindowns; they do not reconcile with the official
final. The same report showed:

| Measure | UALR team | UALR thrower totals | Lehigh team | Lehigh thrower totals |
|---|---:|---:|---:|---:|
| KP attempts | 45 | 45 | 26 | 26 |
| KP completions | 22 | 16 | 23 | 16 |
| KP INTs thrown | 3 | 3 | 1 | 2 |

Receiver detail lists 16 catches for each side. Lehigh had a kickoff/
return defensive context that is not reliably attributable by the old
possession-only scoring method. This is diagnostic evidence from one
historical box score, not a reproduced deterministic seed.

## Confirmed root causes in code

1. `calculate_scoring_profile` inferred team ownership from
   `play.possession`, which can represent the offense that snapped a
   play even when the opponent scored a return touchdown. It also
   computed `bonus_scores * 7` as additional scoring, double-counting
   points already included in touchdown or kick totals. Bills of
   scoring methods therefore need not equal the scoreboard.
2. `calculate_team_stats` treated all kick-pass outcomes named
   `gain`, `first_down` or `touchdown` as completions. Individual
   `game_kick_passes_completed` counters increment on actual caught
   balls. The resulting completion rate differed from thrower and
   receiver detail. Team KP interceptions were inferred from outcome
   labels, sometimes disagreeing with final player credits.
3. Turnover margin ignored intercepted kick passes and laterals and
   counted a safety as a turnover. Defensive impact also omitted
   return touchdowns from its interception bucket.
4. Team event aggregation grouped by final `play.possession` rather
   than the saved `snap_possession`; some scoring return paths change
   possession before writing the Play record.
5. A kick-pass touchdown credits both the kicker and target individually.
   Summing player KP touchdown credits therefore doubles team TDs.
6. **Newly demonstrated by the full-engine audit:** synthetic bonus-possession
   and overtime markers were appended with uninitialized score snapshots
   (default 0-0), generating spurious *negative* score changes followed
   by apparent phantom scoring. Fixing only the analytics layer would hide
   this upstream event-log defect.

## Changes in this branch

- New `engine/box_score_ledger.py`: read the *post-resolution*
  home/away score values on each chronological play. Allocate each
  increment to the actual scoring team; classify touchdown, snap kick,
  place kick, return TD, safety, pindown and half-point bell by the
  event type. A combined 9.5-point return+bell is recorded as two
  scoring channels. Unknown positive increments remain explicitly
  `other_pts`; negative scoreboard changes and gaps to `final_score`
  set `score_consistent=False` and `unrecorded_points`. No silent
  correction changes the official final score.
- `engine/viperball_metrics.py` scoring profile now uses the ledger
  whenever play score snapshots exist; historical records without
  snapshots retain a limited legacy fallback. Bonus drive conversions
  remain *non-additive annotations* and no longer invent seven points.
  Turnover margin and defensive impact cover interceptions (including
  interception return TDs) with snap-team attribution.
- `engine/game_engine.py` reconciles team kick-pass attempts,
  catches and INTs from the final player counters after accepted
  penalties are resolved. Team kick-pass TDs count scored events,
  not both participants' individual credits. Team play partitions
  use the snap owner. The final score is attached to each team's
  metrics context. Synthetic bonus/overtime play markers now retain the
  actual current score instead of the default zero snapshot.
- College, WVL and pro box-score templates show safeties, pindowns,
  bells, unknown scores, and a warning on an unreconciled score.
  Bonus conversions appear below scoring methods rather than as
  another scoring method.
- `tests/test_box_score_ledger.py` covers snap-vs-scorer ownership,
  pick-sixes, 9.5-point return+bell, bonus-drive double counting,
  safeties, pindowns, score gaps and turnover margin.
- `scripts/benchmark_boxscore_reconciliation.py` exercises complete
  game resolution against final scores, scoring-method totals,
  team/player kick-pass parity and seeded weather/roster conditions.
  Added a smoke step to the **existing** CCH-03/04 integration
  workflow; no new test workflow.

## Validation and acceptance

### Observed first CI run

The existing suite passed **181 tests** and the focused coaching
integration passed **35**. The first eight-game source-of-truth smoke
reported **15/16 team-game score ledger failures**, all with zero
final-score difference but interim score reversals. That diagnostic
revealed the zero-snapshot bonus/overtime markers above. The audit was
not waived or weakened; the engine markers were repaired at their
source. The failing run's trace showed the synthetic
`bonus_possession` marker at index 92 resetting scores from
46.5/40.0 to 0/0; this directly confirmed the cause.

### Corrected integration result

[CI run 45435203046](https://github.com/quarterback/viperball/actions/runs/45435203046),
seed `20261124`, `PYTHONHASHSEED=0`:

- **181 full Python tests passed**, including seven BOX-01 invariants.
- Focused CCH-03/04 installation tests passed: **35**.
- **8 complete game simulations**, two roster matchups and alternating
  clear/rain; **16 team-game score accounts**, **199 scoring events**.
- **1,141.5 combined points** across those 16 team-game accounts,
  reconciled exactly with the official final scores.
- **0 score reversals, 0 unmatched final-score points, 0 unclassified
  scoring points, 0 team/player kick-pass discrepancies**.
- The initial audit failed 15 of 16 team-game accounts solely because
  the old synthetic markers had zeroed snapshots. The corrected audit
  does not ignore or filter such events.

### Final validation gate

Re-run after the synthetic marker fix:

```sh
PYTHONHASHSEED=0 python -m pytest tests/test_box_score_ledger.py -q
PYTHONHASHSEED=0 python -m pytest tests/ -q
PYTHONHASHSEED=0 python scripts/benchmark_boxscore_reconciliation.py --games 8 --seed 20261124
```

The targeted scoring/box-score gate is **PASSED**. All five
existing workflows passed on the corrected engine commit
[`3943c72`](https://github.com/quarterback/viperball/commit/3943c72ea576ff6f109de5627d5656cb7d30c034):
CCH-03/CCH-04 integration, CCH-02 coach decisions, CCH-03
defensive decisions, defensive tactics regression, and integrated
engine calibration. **Merged into `main` via
[PR #351](https://github.com/quarterback/viperball/pull/351),
merge commit [`b00257e`](https://github.com/quarterback/viperball/commit/b00257e706150c22e7164999b2563bc1a84406fb).**
No live deployment or historical UALR/Lehigh event-log backfill has
been verified.

## Outside this PR

- ST-01/02 remains draft #349: returner selection, kick attribution and
  blocked-kick bells will alter the real scored events; re-run this
  audit once that PR merges.
- PEN-01/INJ-01 is merged on main. This work reads *finalized* credited
  outcomes after their existing nullification logic, and does not edit
  penalty resolution or injury exposure.
- Timeout limits, per-rusher sack concentration, and additional
  historical box-score backfills are separate follow-ups.
- The original UALR/Lehigh game lacks a known reproducible seed or
  finalized source event log in the provided export. This PR cannot
  reconstruct its exact historical plays; re-simulation establishes
  whether future box scores reconcile.
