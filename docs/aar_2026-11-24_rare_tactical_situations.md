# AAR: Rare defensive situations and matched snap replays

**Date:** November 23 Pacific / November 24, 2026 UTC  
**Status:** Study complete; merged on main. No production tactical coefficients or probabilities changed.  
**Implementation:** [PR #342](https://github.com/quarterback/viperball/pull/342), [merge d3a2f15](https://github.com/quarterback/viperball/commit/d3a2f158f334fd31ed1d08ae739f192128aa0d9b).  
**Predecessor:** [Expanded commitments AAR](aar_2026-11-24_expanded_defensive_commitments.md).

## Objective and method

The prior 792-game study left six-rusher pressure, Kick-In Press, Ride and Exhaustion Press under-sampled. Separate the natural frequency of eligible situations from the conditional consequences of actually making the call.

[Integrated workflow 45337499565](https://github.com/quarterback/viperball/actions/runs/45337499565) passed. The retained [results artifact 14893724541](https://github.com/quarterback/viperball/actions/runs/45337499565/artifacts/14893724541) contains group totals and paired differences. Seed 20261124; 48 complete source games per case, four cases, 192 games total. Two roster matchups and two DC signatures alternate across seeds. The source games retain normal tactical selection and fully familiar single-package fixtures, not naturally acquired dynasty installations.

At eligible pre-snap states, the benchmark copies the live engine, restores the same starting random state in each arm, invokes the real DC decision resolver, then applies a fixed scrimmage response using the normal play resolution. Package arms are off versus forced eligible activation; overload arms use two, four or six actual rushers. The offensive response is set after the call. The experimental arms omit the surrounding penalty/clock/drive-resolution path; they are matched snap replays, not additional full games. Maximum four captures per scenario per source game and 120 per scenario overall. Response families rotate across snapshots; the resulting subtype cells are modest, not identical snapshots for every subtype.

Exhaustion also has controlled fatigue arms: offensive player energy is set to 65 or 78 in both paired arms. These are deliberately enriched conditions and must not be counted as naturally occurring opportunities. Natural source-game energy is variable. The study does not include an independently standardized fresh-offense arm.

**740 sampled pre-snap states, 1,547 experimental play resolutions**, plus the 192 source games. No production engine code or unit-test additions. Existing workflow selects the rare study for changes to its script.

## Natural occurrences

| Case | Scrimmage calls | Primary eligible | Secondary eligible | Activations (primary / secondary) | Captured states |
|---|---:|---:|---:|---:|---:|
| Kick-In Press | 3,067 | 65 | 353 | 54 / 157 | 51 primary, 120 secondary |
| Ride | 3,134 | 191 | 310 | 175 / 126 | 120 primary, 120 secondary |
| Exhaustion Press | 3,041 | 1 | 30 | 1 / 13 | 1 primary, 21 secondary, 240 controlled fatigue |
| Overload | 3,288 | 234 urgent calls | — | No six-rusher kick-pass attempts | 67 urgent |

Across all four source-game cases, nine natural resolved kick passes used six rushers. The overload case itself had none. An urgent call is an opportunity under the current decision rule, not necessarily a kick-pass attempt.

## Six-rusher overload

All 67 urgent snapshots replayed with each of the three commitments. The benchmark reconciles rush/coverage assignments with actual on-field players.

| Rushers | Pressure | Sacks | Completion on non-sack releases | Mean defender energy lost after ordinary snap accounting |
|---:|---:|---:|---:|---:|
| 2 | 28/67 (41.8%) | 11/67 (16.4%) | 30/56 (53.6%) | 1.69 |
| 4 | 35/67 (52.2%) | 15/67 (22.4%) | 35/52 (67.3%) | 2.53 |
| 6 | 45/67 (67.2%) | 20/67 (29.9%) | 33/47 (70.2%) | 3.35 |

| Offensive response | Snap pairs | Yards, two rushers | Yards, four | Yards, six |
|---|---:|---:|---:|---:|
| Quick kick | 23 | 5.22 | 7.91 | 13.22 |
| Territory | 22 | 10.00 | 10.18 | 9.45 |
| Bomb | 22 | 7.95 | 7.18 | 3.00 |

Six rushers produce a clear conditional pressure/coverage tradeoff in this sample. Deep kicks face more sacks and lower yardage; quick kicks exploit the vacated coverage and more than double yardage relative to two rushers. Extra energy costs are measurable. These are descriptive conditional results across sampled game states, not a league-wide recommendation to blitz more. **Retain the current rare six-rusher decision rule.**

## Rare packages

All numbers below are matched eligible snap yards per play, off to on. Sample sizes are pairs per subtype.

| Package / situation | Response | Pairs | Off → on |
|---|---|---:|---:|
| Kick-In Press / primary | Quick kick | 11 | 11.73 → 5.27 |
| Kick-In Press / primary | Territory | 10 | 24.40 → 18.80 |
| Kick-In Press / secondary | Quick kick | 24 | 11.96 → 6.96 |
| Kick-In Press / secondary | Territory | 24 | 17.04 → 14.83 |
| Kick-In Press / secondary | Bomb | 24 | 1.38 → 6.46 |
| Ride / primary | Territory | 24 | 9.00 → 6.42 |
| Ride / primary | Speed option | 24 | 1.42 → 1.04 |
| Ride / primary | Bomb | 24 | 7.63 → 9.08 |
| Ride / secondary | Territory | 24 | 13.96 → 11.54 |
| Ride / secondary | Bomb | 24 | 3.42 → 7.54 |

**Kick-In Press:** The conditional quick/territory suppression and secondary deep concession support the intended identity. Primary bomb observations are too few to establish that concession separately. Retain the broadened eligibility and current effects.

**Ride:** Territory and speed-option suppression with bomb concessions supports the intended tradeoff. Quick-kick yardage was unchanged in both sampled tiers. Retain; do not claim general short-pass suppression.

**Exhaustion Press:** Natural eligibility remains scarce (one primary, thirty secondary calls). Controlled fatigue replays provide conditional evidence, not a frequency estimate.

| Controlled offense energy | Response | Pairs | Off → on yards | Off → on pressure |
|---|---|---:|---:|---:|
| 65 | Quick kick | 24 | 13.08 → 12.13 | 16.7% → 12.5% |
| 65 | Territory | 24 | 5.50 → 6.21 | 41.7% → 41.7% |
| 65 | Bomb | 24 | 2.08 → 5.79 | 70.8% → 66.7% |
| 78 | Quick kick | 24 | 12.38 → 15.50 | 12.5% → 12.5% |
| 78 | Territory | 24 | 11.13 → 8.67 | 41.7% → 45.8% |
| 78 | Bomb | 24 | -1.71 → 6.88 | 62.5% → 62.5% |

Exhaustion Press consistently adds defensive energy cost on kick-pass attempts, but does not consistently increase pressure or reduce short/territory yardage. Bomb vulnerability is evident. Do not increase its activation frequency or advertise its pressure benefit as established. The package remains a high-risk, unproven option. A future calibration should investigate relative offensive protection fatigue, defender readiness and rush efficiency with longer-run natural roster/rotation data; no coefficient adjustment is warranted from these small cells alone.

## Decisions and follow-up

- Keep six-rusher overload, Kick-In Press and Ride unchanged. Their conditional advantages and concessions are observable.
- Keep Exhaustion Press bounded and identify it as a calibration follow-up, not a proven advantage. Do not tune it to force a positive result.
- Continue with multi-season dynasty calibration: natural installations, coordinator turnover, rotation/work rate, fatigue exposure and late-game calls. Full-season progression and live deployment remain unverified.
- Study results do not establish statistical significance; snapshots from the same source game are correlated. Raw counts and paired differences are retained for later clustered analysis.

Reproduce:
`PYTHONHASHSEED=0 python scripts/benchmark_rare_tactics.py --games 48 --cap 120 --seed 20261124 --out reports/rare-defense`.
