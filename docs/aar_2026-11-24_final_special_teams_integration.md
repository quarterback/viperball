# AAR: Final special-teams integration, ST-01/ST-02 and STI-VAL

**Date:** November 24, 2026
**Status:** MERGED — [PR #356](https://github.com/quarterback/viperball/pull/356), merge `95556facc1f0b432f8e05dc1c587c46c0712d69b`.
**Primary implementation:** [PR #354](https://github.com/quarterback/viperball/pull/354), merged after PEN-01, INJ-01, spot errors, return fouls and BOX-01/Delta accounting.
**Earlier competing implementation:** [PR #349](https://github.com/quarterback/viperball/pull/349), superseded by #354 plus this reconciliation; do not merge its old engine wholesale.

## Decision

PR #354 is the retained implementation. It already connects saved STC preferences, makes the five established ST schemes playable, picks one returner per punt, accounts for fatigue, records named kicking/return/coverage participants, and fixes punt/return/blocked-punt field orientation. The other agent tested it against the current engine and reported 181 passing tests, 400-game before/after comparisons and 300-game coordinator comparisons. Its retained AAR is [here](aar_2026-11-24_pr354_special_teams_coordinators.md).

PR #349 independently introduced several overlapping changes. Porting its entire engine would duplicate coordinator logic and discard #354's game-event records. Instead, this patch imports only the missing correctness behavior.

## Problems reconciled

1. **Blocked snap and place kicks are attempts.** #354 counted successful/missed kicks at the player level but exited early on blocked kicks without crediting an attempt. The team play ledger counted the blocked attempt, so official player and team counts disagreed. Each blocked kick now increments its kicker's overall and DK/PK attempt counters once.
2. **Recovery of a blocked live kick earns a bell.** RULES.md explicitly awards a half-point to the recovering team for a blocked kick. Defensive recoveries of blocked snap/place kicks now credit 0.5 points even when the return also scores a nine-point touchdown. The text shows the +½ bell. The BOX-01 scoring ledger already supports combined 9.5-point return events.
3. **One eligible blocked-kick participant.** Blocked punts and place kicks now name a rusher drawn from available participants with relevant skill/specialist weights. Blocked snap kicks continue to prefer a real available diving wing; their attempt is credited even when blocked. Returners and coverage participants retain #354's fatigue and availability logic. The event record carries the selected blocker.
4. **Accepted, nullifying penalty does not count a kick attempt.** The penalty code correctly restores player credits when it wipes out a play, but the team statistics formerly counted the original `play_type=drop_kick/place_kick/punt` even after the result changed to a nullified penalty. Official kick and punt totals now exclude those snapshots.
5. **Pindown restart on a final half-ending play.** RULES.md sets the next receiving possession to its own 25 after a one-point pindown. The standard path does so already; the special end-of-half forced-punt path reset the spot to the 1–5 yard line. Both paths now agree on the receiving team's own 25.
6. **Territory-first fifth-down coaching.** #354's positive `field_position_bias` lowered the minimum yards-to-gain at which a coach would attempt a fifth-down snap kick. This conflicted with the stated intention to reserve an extra opportunity for field position. Positive territory bias now raises, rather than lowers, the fifth-down minimum.

No Viperball scoring, six-down, or score-dependent Delta Yards rule has been replaced. Delta Yards remains enabled by default.

## Integration and verification

`scripts/benchmark_special_teams_integrated.py` records actual per-event ST data (not description-string searches). It compares **five ST schemes × three saved STC profiles (neutral, territory, attack) × clear/rain × 20 seeded full games = 600 games**. The neutral profile keeps coaching staff present in the baseline, eliminating a design error in the previous #349 study. The home side is the controlled ST implementation; the away side is a fixed Aces opponent. Each cell varies weather and games but keeps the seeds/rosters matched across coordinator profiles.

The study requires exact team-vs-player parity for:
- snap-kick attempts;
- place-kick attempts;
- punt returns and credited punt-return yards;
- BOX-01 final score ledger.

The benchmark also reports fake punts, blocks, muffed returns, named blockers, nullified kicks and team points, retaining zero-denominator or rare-event limitations rather than inventing certainty. The existing CCH integration workflow runs the **full tests, BOX-01 audit, 40-game rush/Delta comparison, national full-season check and STI-VAL in one integrated milestone**, without adding an independent per-PR CI suite.

### Previous evidence already verified

The #354 AAR reports 400 independent games with roughly stable punt calls (2.24 → 2.23/game), 5.0% muff rate and 1.8% return TD rate after its changes; on 300 coordinator games, attack returned 9.6 yards per punt against 8.0 for territory. These are branch-reported findings before this final patch, not yet validation of the combined implementation. The #349 reviewer independently corrected its benchmark and verified 181 tests and a 200-game return/blocked-kick evaluation.

### Current milestone

Complete: final integration and CI passed; merged via #356.

## Final integration results

The final regression run [45471108920](https://github.com/quarterback/viperball/actions/runs/45471108920) completed successfully on the final branch head `8e2ee7d`, including 181 Python tests, the existing BOX-01 reconciliation, matched rush/Delta checks, a 205-team full national-season simulation, and the STI-VAL 600-game benchmark. All five triggered workflows were green.

STI-VAL used seed `20261124`: 5 schemes × 2 weather conditions × 3 coordinator profiles × 20 games = **600 full games, 30 study cells, zero failed accounting invariants**. All scored-event ledgers and tested kick/return player-vs-team totals reconciled.

Across 200 games for each coordinator profile (five schemes, clear and rain):

| Coordinator | Home punts | Home snap kicks | Home kick blocks | Home fakes | Punt returns / yards credited to home | Mean home points |
|---|---:|---:|---:|---:|---:|---:|
| Neutral | 324 | 1,108 | 54 | 4 | 160 / 1,769 | 71.790 |
| Territory | 329 | 1,088 | 54 | 4 | 164 / 1,568 | 70.648 |
| Attack | 309 | 1,108 | 56 | 8 | 170 / 2,250 | 70.865 |

The attack profile increased return yards and fake attempts, and territory yielded somewhat more punts and fewer snap kicks. Return touchdowns and fakes remain rare; these results do not justify a balance retune. The benchmark includes scoreboard parity and named blocker totals, with penalty-nullified events excluded from official kick attempts. A complete national-season simulation was run again on this integrated special-teams branch, not merely inherited from earlier calibration.

The duplicate #349 was **closed without merge**. Its distinct blocked-kick accounting and restarts were reconciled in #356; #354 remains the retained special-teams coordinator/event implementation. The sport's score-dependent **Delta Yards** rule was not changed.

## Remaining operational boundary

The live Fly.io instance is not confirmed running. Existing deployment code now checks the Git SHA of a deployed build; a GitHub merge or green simulation cannot certify that the Fly machine is serving the same commit. Do not start a potentially billable machine without explicit approval.

## Scope explicitly closed

- ST-01: coordinators and five ST schemes exercised by game decisions, retained in #354.
- ST-02: eligible kick and return participants, return direction/yardage, blocked kick stats, recovery scoring, correct pindown spot.
- STI-VAL: accepted; 600 full games, zero parity failures, and green combined CI.
- PEN-01 and INJ-01: already merged; deliberately not reimplemented.
