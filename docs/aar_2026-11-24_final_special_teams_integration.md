# AAR: Final special-teams integration, ST-01/ST-02 and STI-VAL

**Date:** November 24, 2026
**Status:** Final reconciliation in review.
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

Await the CI result for the final integration branch, capture exact seed, game counts, counts of blocked-kick bells and errors, and append verified outcomes. Do not merge if a scoreboard, possession, kick attempt or player-credit invariant fails.

## Remaining operational boundary

The live Fly.io instance is not confirmed running. Existing deployment code now checks the Git SHA of a deployed build; a GitHub merge or green simulation cannot certify that the Fly machine is serving the same commit. Do not start a potentially billable machine without explicit approval.

## Scope explicitly closed

- ST-01: coordinators and five ST schemes exercised by game decisions, retained in #354.
- ST-02: eligible kick and return participants, return direction/yardage, blocked kick stats, recovery scoring, correct pindown spot.
- STI-VAL: final acceptance depends on full combined CI benchmark and regression results.
- PEN-01 and INJ-01: already merged; deliberately not reimplemented.
