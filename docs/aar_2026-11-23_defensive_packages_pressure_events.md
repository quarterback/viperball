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



## Merge and integrated evidence
PR #336 (stats-site redesign) merged first at 1a8ddc8. PR #337 merged at 0532e02 after the integrated benchmark and existing full regression suite succeeded. The first 400-game run (45309901984) established package activation and rush-event attribution, but all 200 paired scores were identical. The legacy run contest calculated an alignment adjustment without applying it; commit 7706f81 applies the chosen alignment to the existing run contest center. Commit 8d50a4d updates the obsolete existing assertion that opening-drive triggers are unsupported. No new unit-test suite was added.

Corrected run: https://github.com/quarterback/viperball/actions/runs/45310851890 (artifact 14882458324; seed 20261123; 40 matched games per condition; 400 games total). The full existing regression suite passed 174 tests in run 45310851905; the DEF and CCH-02/03 workflows also succeeded. The older CCH-03/04 matched-game job was still running at merge.

| Package | Eligible | Activated | Pressure on (attempt denominator) | Points allowed off/on | Paired scores changed |
|---|---:|---:|---:|---:|---:|
| Fortress wall | 93 | 62 | 19.1% (771) | 66.1375 / 66.45 | 2/40 |
| Lockdown bracket | 472 | 303 | 30.5% (1365) | 57.625 / 58.725 | 3/40 |
| Blitz short-yardage | 84 | 58 | 22.5% (703) | 74.175 / 74.575 | 3/40 |
| Kick-In Press | 28 | 19 | 28.5% (1389) | 68.1 / 68.1 | 0/40 |
| Ride | 131 | 85 | 28.5% (1444) | 72.075 / 72.425 | 2/40 |

Every selected Kick-In Press and Ride occurred on an opening snap; all 85 Ride activations occurred on turnover/bonus possessions. Enabled Blitz Pack had 13.2% hurry and 9.2% sack rates; base comparison 13.0% and 8.7%. Comparisons are within each scheme/attack pair, not causal comparisons across different attacking styles. Conditional short power gains against Fortress went from 4.14 to 4.64 yards (28 attempts each); long kick-pass gains against Lockdown went from 6.06 to 6.61 (272/279 attempts). These results do not establish the expected package benefits. Avoid tuning overall scoring to an arbitrary target; investigate conditional coverage and interior-run effects in a broader matched study. Physical rusher counts, full dynasty progression and live deployment verification remain outstanding. The merged engine is operational in full-game CI; balance and deployment are not certified.


## Tactical calibration and physical rush personnel — November 24 UTC
PR [#339](https://github.com/quarterback/viperball/pull/339) merged as e3446d9. The run/lateral/coverage contest now has bounded package-specific tradeoffs scaled by installation familiarity instead of an added package read bonus. On kick-pass attempts the engine commits two actual on-field defenders to the base rush, three on a normal blitz, and four on a Blitz Pack blitz (subject to available personnel). Remaining defenders cover; rushers cannot also be the matched coverage defender. Protection uses actual on-field blockers, and extra commitments increase pressure potential while conceding coverage space. The new `defensive_rush` game summary and `rush_event` play records include counts, names, pressure, hurries, sacks and completions. This does not model a spatial tracking system; counts are assignments within the simulated contest.

**Evidence:** [final integrated run 45322016267](https://github.com/quarterback/viperball/actions/runs/45322016267), artifact 14887578008, seed 20261123. 600 full games, 24 games per condition (11 package/opponent pairs with packages on/off, plus three base-scheme controls), alternating two roster matchups. 16,603 resolved away-defense kick-pass attempts and 37,170 rusher commitments reconciled with play logs; no overlap between rush and coverage assignments. Results were identical to the preliminary run after the compatibility correction for teams without installed packages. Existing 174-test suite passed. No new test suite.

### Matched results
| Comparison | Packages off | Packages on |
|---|---:|---:|
| Lockdown long bracket vs Boot Raid: long-situation kick-pass yards/attempt | 10.35 (173) | 9.52 (183) |
| Same: completion rate | 45.7% | 43.2% |
| Lockdown long bracket vs Ground Pound: eligible inside-run yards/attempt | 6.56 (55) | 8.32 (65) |
| Blitz short-yardage pressure vs Ground Pound: eligible inside-run yards/attempt | 9.00 (25) | 5.23 (26) |
| Rugby rush line vs Lateral Spread: eligible sweep/speed/lateral yards/attempt | 2.91 (219) | 2.03 (210) |
| Same: eligible kick-pass yards/attempt | 7.07 (531) | 7.63 (565) |
| Drift prevent vs Shock & Awe: eligible kick-pass yards/attempt | 5.33 (344) | 3.40 (347) |
| Same: eligible inside-run yards/attempt | 1.16 (19) | 2.32 (19) |

Base-scheme controls against Boot Raid: Swarm pressure 31.9% (790 attempts), Lockdown 30.4% (773), Blitz Pack 38.8% (760). Within Blitz Pack, two rushers: 30.5% pressure, 11.8% sacks, 40.0% completion on non-sack releases (442 attempts); four: 50.3% pressure, 20.4% sacks, 43.1% completion on non-sack releases (318 attempts). These are descriptive conditional rates, not randomized per-snap comparisons. The four-rusher call adds seven percentage points to the pre-hurry completion model; greater pressure can still reduce overall completion.

All nine packages activated. Goal-line stand, bracket, prevent, short-yardage pressure and rush-line effects broadly support their intended tradeoffs, but some cells are small and overall scoring differences are uncertain. Kick-In Press activated only ten times and produced no change in paired scores; Ride activated fifty times. Short Yardage Wall results were mixed. Do not claim universal optimization or force scoring targets. Further tuning of those rare situations should use larger dynasty samples rather than repeated narrow PR benchmarks. Full-season/dynasty and live deployment remain unverified. The stats-site agent can consume `full_result.defensive_rush` and `play_by_play[].rush_event` without changing the engine.
