# PEN-03 / PEN-04: Player discipline and penalty calibration

2026-11-25. Follow-up to PEN-01/PEN-02, not a replacement for their enforcement or officiating work.

## Implemented on this branch

- Immediate game ejection for called Targeting, Fighting and Throwing Punch.
- Second called qualifying unsportsmanlike foul by the same player in the same game ejects: Unsportsmanlike Conduct, Taunting, Excessive Celebration, Provoking Ill Will, Obscene Language. Routine safety and administrative fouls do not count toward the two-strike limit.
- Yardage acceptance/decline and ejection are separate; the original play resolves before the player is removed. Game-local ejection state is separate from injury and reversible bench state; availability, rotation, lineup caches and emergency fallbacks exclude ejected players.
- Player names and IDs travel with flags. Play records include ejection, reason, misconduct count and identifiable replacement (if the depth-chart comparison identifies one). Game summaries include player discipline, ejection events, team counts and accepted fouls by type.
- Serious infractions are always material and cannot be deliberately let go; officials can still miss them. Phantom-flag sampling excludes disciplinary infractions because there is no penalty appeal mechanism. No automatic next-game suspension or numerical disadvantage is imposed.
- Provisional immediate-foul rate multiplier 0.20, with bounded composure, coaching leadership and defensive intensity modifiers for misconduct. Offender selection uses awareness and fatigue proxies, not a new roster attribute.

## Verification and calibration (PEN-04)

Regression tests: `pytest -q tests/test_player_discipline.py tests/test_rules_doc.py`.
Run full suite: `pytest -q tests`.
Run benchmark: `python scripts/benchmark_discipline.py --games 1000 --seed 130300 > discipline-calibration.json`.
Repeat with different seeds; inspect accepted flags and yards per game, game share with ejection, reasons, repeat-offender rate and team distribution. Compare against the pre-change officiating benchmark (roughly 16.8 flags/game, 72 penalty yards/team/game); tune severe-foul rates separately, not by increasing routine fouls. Add stratification by defense scheme, rivalry, composure and weather in a follow-up if sample permits. No measured post-change rates yet.

Acceptance gates: no player reappears after ejection; no duplicate ejections; side and player attribution reconcile across play and summary records; declined flags still disqualify; ordinary fouls never count as misconduct; halftime, rotation, overtime and fresh games behave correctly. Inspect box-score UI consumers separately: the engine emits the fields but dedicated presentation is not included here. Existing terminal-drive fallback kick bypasses normal penalty sampling; no change to that enforcement path in this work. Full simulation and CI results are not yet verified.

## Policy decisions pending

Whether the league wants additional suspensions, formal ejection review, flagrant contact categories or bench/coach ejections. Do not invent these policies in dynasty code.
