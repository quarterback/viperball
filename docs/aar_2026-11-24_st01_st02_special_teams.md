# ST-01/ST-02: special-teams coaching and participant attribution

**Date:** November 24, 2026
**Working PR:** #349 (draft)
**Base:** main before PEN-01 / INJ-01, both owned by another agent.

## Work committed

ST-01 introduces `engine/special_teams_tactics.py`, which reads the
persisted STC tactical profile and respects HC delegation. The five existing
scheme coefficients remain the primary identity. In the live engine, an STC
has a bounded effect on fake-punt decisions (field-position preference),
kick-block pressure, muff risk, punt-return yardage and return TD risk
(return aggression). An absent STC retains the original coefficients.
No new points, yardage bonuses or automatic success flags were introduced.

ST-02 selects a single eligible punt returner per kick, using that same
player for the muff, return-TD, and normal-return path instead of
drawing independently for each consequence. Kick-blocking personnel now
come from available specialist/depth candidates, with a Diving Wing
preference, instead of always crediting the fastest DL. The fallback
excludes unavailable injured players. Normal punt coverage second-player
credit excludes unavailable players. A blocked punt recovered by the
defense now flips field position from the kicking side correctly.
Fake punts can score when crossing the goal line, and successful trick
plays must actually reach the yards to gain to reset downs.

`scripts/benchmark_special_teams.py` supplies a full-engine, seeded
comparison of the five schemes, three coordinator cases, and clear/rain
conditions. At 20 games per condition it proposes 600 complete games.
Its output counts block, muff, fake, return, pindown and score events.

## Limits / merge gate

The code has not yet been run locally. The GitHub connector can edit and
read the repository but does not provide a direct Python runtime for the
remote repository. Do not claim calibration or correctness from code
inspection alone.

Before marking both tickets complete:
- Run the existing regression suite and the paired benchmark, report
  observed denominators and effect sizes. Check scheme concessions as
  well as strengths. A fast-sim result is not sufficient.
- Verify every blocked drop kick and place kick's recovered-ball scoring,
  return-player credit, return field orientation and touchdown handling.
- Exercise shallow/depleted squads and multiple returners; reconcile
  player statistics and legal substitution at injury boundaries.
- Rebase after the separate PEN-01 and INJ-01 PRs to ensure physical
  special-teams exposure and accepted/declined fouls are attributed once.
- Verify canonical pindown/rouge behavior and its documented scoring;
  no rule interpretation has been changed here.
- Run a live dynasty smoke before claiming end-to-end completion.

This report is an implementation handoff, **not** a completed AAR.
