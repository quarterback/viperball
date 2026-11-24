# Engine follow-up: defensive packages, pressure, and situational events

## CCH-05 — initial implementation (in progress)
Commit d0862394 adds one optional installed package to the existing DC pre-snap call. The package must belong to the current coordinator and scheme, match a catalog situation, and be present in the roster-filtered installation. The catalog's league-normalized roster fit is established during installation, not recalculated on incompatible raw rating scales. Familiarity controls selection and effect; a separate seeded random stream leaves the original DC draw sequence intact. At most one package can influence a snap. The base defensive posture remains available.

Seven packages use existing alignment, blitz and read-resolution mechanics. The inside wall emphasizes stacked alignment; the shell and bracket emphasize spread and reduced blitz; pressure and rush line emphasize aggression. A small family-specific read allocation favors the prepared family and concedes others. Prevent uses spread and lower blitz; its actual explosive-play effect is unproven. Kick-In Press and Ride are deferred until CCH-06 can identify drive events. No new yardage or sack multiplier. Values are initial hypotheses, not calibrated findings.

Play logs expose package ID, effective familiarity and focus; the DC summary reports eligible and selected counts. These are additive fields for the UI agent. The runtime switch is defensive_packages_enabled. No React work.

Benchmark script: `PYTHONHASHSEED=0 python scripts/benchmark_defensive_packages.py --games 40`. It holds installed record, opponent, staff and seeds fixed within each on/off comparison for three scheme/package combinations. It reports calls, eligibility, activation, blitz, alignment, conditional yards and explosives; selected-only comparisons are descriptive. Use a one-game-per-condition smoke first. The benchmark uses explicit installed fixtures to isolate effects; natural installation frequency needs later dynasty calibration. **No smoke or benchmark results yet.** Do not mark CCH-05 complete before running them.

## Next
DEF-07 pressure/hurry instrumentation, CCH-06 drive/score/turnover/fatigue context, combined calibration and nonblocking deployment smoke. No new test suite per task. See the shared assessment queue.


## Integrated implementation — DEF-07 and CCH-06
Commits 279da397, 002dee23 and 3f41b1a3 connect the rush contest and package context. A single existing sack roll partitions clean release, hurry and sack; the initial hurry threshold is 2.5 times the final sack probability (capped at 0.65). A hurry reduces completion probability by 15% relative. These are tuning hypotheses. Rush event records include defender side, called blitz, rusher/blocker, skill estimates, release type and completion probabilities before/after. Blitz is a commitment indicator, not a count of physical rushers. Possession origin and snap index carry across quarter breaks; opening, turnover, bonus, score restart and other restart are distinct. On-field defensive energy feeds the catalog. Kick-In Press and Ride require both opening snap and their respective field/origin predicates. The existing package benchmark now also measures rush outcomes and event packages (five matched scheme/package pairs). Run the combined study only; no modular validation gate. Stats-site migration PR #336 is separate; fields are additive, no React changes. No runtime evidence yet.

