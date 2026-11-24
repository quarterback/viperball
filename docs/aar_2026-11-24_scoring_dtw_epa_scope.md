# AAR: scoring-value metrics, DTW separation and EPA scope

**Date:** November 24, 2026. **Track:** AN-01/DTW-01/EPA-01.
**Context:** Four reviewed college box scores exposed equal Power Play scoring rates that hid different point values, near-50/50 DTW results labeled as upsets, and EPA sign mismatches despite wins created by return touchdowns and bonus possessions.

## Code findings on main

1. `engine/game_engine.py` grouped DYE drives as penalty-kill (score-dependent restarts against the leader), power-play (restart advantage for the team behind), and neutral. It reported yards per drive and percentage of drives with a score, but did not expose the point value, touchdowns or kicks by bucket. Its original score-rate numerator also included some defensive-return outcomes that should not be treated as offensive scoring.
2. `engine/dtw.py` had a ±3 percentage-point toss-up band, but the independent `upset` test still used a simple >50% threshold. Both teams could visibly round to 50–50 while carrying a DTW upset label. The current model is a weighted sigmoid of 13 performance and context signals, including four Delta-context signals, and bonus-possession conversion. **It does not directly include turnover margin.**
3. `engine/epa.py` uses a static expected-point table by field position and down, with discrete adjustments for some score results. It is neither empirically fitted by start position nor a complete scoreboard reconstruction. Some return touchdowns are handled, but interception and missed-kick return TD pathways are incomplete. Bonus possessions, all bells, and the score-dependent Delta restart counterfactual have no separately modeled expected value. The aggregator uses logged possession, which can change during turnovers and returns. The value shown on the box score is a partial field-position metric, not the difference between points scored.

## Implemented changes

### Actual scoring value by Delta drive bucket

The game engine now follows the **recorded running score after each played drive**, distinguishing the possessing team's added points from opponent scoring on defensive returns. For every DYE bucket it reports:
- `points`, `points_per_drive`;
- `scores`, `score_rate` (TD or made scoring kick incidence);
- `touchdowns`, `touchdown_rate`;
- `kicks`, `kick_rate`, plus distinct successful `drop_kicks` and `place_kicks` counts when the last scoring play is identifiable;
- `points_vs_start_ep`, using the existing static field-position/first-down EP table as an **unfitted comparison**, not as replacement value.

The box score now shows actual PPD, scoring incidence and TD/kick mix in the same Power Play/Penalty Kill/Neutral rows, rather than a single percent. The normal overall PPD metric was previously fixed to score snapshots in BOX-01 and remains unchanged.

**Points above replacement is not estimated.** A genuine replacement-value model needs the expected scoring outcome of the *alternative* tactical choice (e.g., taking the three-point place kick, five-point drop kick, or trying for nine points) at the same position, down, personnel, opponent and game state. A fixed `EP_TABLE` by field position/down cannot provide those counterfactuals. We label the available comparator `points_vs_start_ep` and explain its scope rather than misrepresenting it as replacement.

### DTW separation and component accounting

The model now requires an adjusted **55–45** split before choosing a deserving winner or declaring a DTW upset. 45–55 is `too_close`, and the box score prints one decimal place plus a TOO CLOSE indicator. A 50–50 presentation can no longer be labeled an upset.

The DTW result now carries `component_edges`, the **actual summed weighted contributions** for:
- raw performance (set efficiency, stops, success rate, EPA/play, conversions, kick-pass accuracy, kick accuracy and team rating);
- Delta context (PK score rate, PK efficiency, PP conversion and mess rate);
- turnover-derived bonus-possession conversion;
- final adjusted weighted composite edge (sum of those three).

The result explicitly states that **direct turnover margin has no coefficient** (`direct_turnover_margin=None`). These numbers are signed *weighted edges*, not percentage-point adjustments or confidence intervals. The underlying model coefficients and sigmoid are unchanged.

### EPA scope disclosure

`engine/epa.py` now returns a machine-readable `scope` object in each game-level EPA result, listing its actual inputs and missing or incomplete scoring pathways. The box score explains that EPA is a partial static field-position model and that a team can win through scoring channels its EPA does not fully credit. No silent rebuild or calibration of the EPA method was attempted. The user-facing title and hover explanation no longer imply that EPA precisely measures contribution to the final score.

## Verification

`scripts/benchmark_analytics_clarity.py` is a focused full-engine integration smoke. It confirms:
- DYE buckets partition actual offensive drives and their TD/kick counts sum to score incidence;
- scoreboard-derived points per drive match bucket totals, and offensive drive points do not exceed the final score;
- the DTW component contributions reconcile to the composite edge;
- equal signals in a 50–49 result cannot produce a DTW upset;
- EPA scope metadata is present.

The script runs in the **existing** CCH-03/CCH-04 integration workflow alongside the existing 181-test regression suite and BOX-01 game-ledger checks. No new per-feature CI suite or probability retuning.

**Current status:** Pending run evidence. Append result counts, seed and any defects before merging.

## Unresolved research

The fixed EPA curve and DTW signal weights are not a validated expected-value model for all six scoring channels. Follow-up research should build an outcome-conditioned EP model by start position, score differential, restart type, possessions and alternatives, with explicit allocation for:
- nine-point touchdowns and defensive/return touchdowns;
- five-point drop kicks and three-point place kicks;
- two-point safeties, one-point pindowns and half-point bells;
- bonus possessions and possession-transfer costs;
- Delta Yards field-position changes;
- six-down turnover-on-downs exposure.

Do not blend tactical replacement value into the current displayed scoreboard until benchmarked against full games. Keep the six-channel scoring and score-dependent Delta Yard restart rules unchanged.
