# AAR: Expanded defensive commitments and package catalog

**Date:** November 23, 2026 (Pacific); November 24 UTC  
**Status:** Merged to main; integrated calibration complete for this sample  
**Implementation:** [PR #340](https://github.com/quarterback/viperball/pull/340), merge [716aa39](https://github.com/quarterback/viperball/commit/716aa39c6a16fb88daf2054c252bc9fa441be59e)  
**Prior work:** [CCH-05 / DEF-07 / CCH-06 integration and calibration](aar_2026-11-23_defensive_packages_pressure_events.md), PRs #337 and #339.

## Objective

Expand the range of meaningful defensive decisions without adding unbounded bonuses, separate defensive engines or arbitrary score targets. Make packages recognizable through both advantages and concessions. Give coordinators more discretion over actual personnel commitments and allow an installed package to serve more than one narrow situation.

## Changes delivered

- `engine/defensive_commitments.py`: shared primary/secondary eligibility rules, execution strength, and pre-snap rusher commitment selection. Primary activation has an upper bound of 90% at full familiarity; secondary situations use 45% of primary eligibility. At most one package is selected per snap.
- `engine/game_engine.py`: one to six intended rushers, capped by actual available on-field personnel with coverage retained. Rushers and coverage defenders remain distinct. Additional rushers cost energy and concede coverage space. Six-rusher decisions are reserved for urgent situations. The existing rush/protection contest resolves pressure, hurries and sacks.
- Package run effects replace the chosen alignment's effect and apply once after the generic suppression floor. This allows a specific tactical commitment to matter even when the generic floor would otherwise erase it. Kick-pass completion adjustments are subtype-specific. Prevent also reduces the existing breakaway probability; pressure packages can increase it.
- Execution strength depends on installation familiarity, coordinator authority and on-field defender energy. Coordinator aggression, pressure preference, adaptability and stubbornness affect personnel commitments; recent completed plays inform responses to deep kicks, perimeter runs, laterals and explosive gains. No future offensive play family is available to the pre-snap call.
- `engine/coach_tactics.py` and `engine/team_installation.py`: use existing saved coordinator preferences when choosing defensive packages and pressure commitments. Existing package records and save format are retained. No extra package slots were added.
- `data/playbooks/packages.json`: adds four implemented defensive packages, bringing the catalog to thirteen. Existing packages retain their IDs.
- `scripts/benchmark_defensive_packages.py`: extends the existing integrated benchmark and uses the same eligibility rules as the engine. No separate test suite or feature-specific CI workflow.

### Coverage commitments

| Intended rushers | Coverage players with full XI | Completion probability adjustment before pressure |
|---:|---:|---:|
| 1 | 10 | -4.5 percentage points |
| 2 | 9 | 0 |
| 3 | 8 | +3.5 points |
| 4 | 7 | +8 points |
| 5 | 6 | +13.5 points |
| 6 | 5 | +20 points |

These are model parameters, not observed completion-rate differences. Pressure can reduce actual completion. A depleted lineup may send fewer players than intended. Rush assignments are part of the contest model, not spatial player tracking.

### New packages

| Package | Tactical advantage | Concession |
|---|---|---|
| Containment | Reduce perimeter yardage and breakaway potential | Interior runs |
| Robber Coverage | Contest territory/intermediate kick passes | Deep bombs and inside runs |
| Lateral Trap | Reduce interception chance on first lateral and increase it on subsequent transfers | Direct interior runs and quick kicks |
| Exhaustion Press | Pressure tired offensive personnel and contest short releases | Added rush energy cost and exposed deep space |

## Integrated benchmark

[Run 45327151900](https://github.com/quarterback/viperball/actions/runs/45327151900), artifact [14890456592](https://github.com/quarterback/viperball/actions/runs/45327151900/artifacts/14890456592), seed 20261123. 792 full games = 15 package/opponent pairs × two package conditions × 24 games, plus three base-scheme controls × 24 games. Two roster matchups and two DC signatures alternate across matched seeds. Installed packages use fully familiar fixtures; this measures execution, not natural dynasty acquisition.

All six PR workflows succeeded; the existing full suite passed 174 tests (CCH-03/04 integration run [45327151857](https://github.com/quarterback/viperball/actions/runs/45327151857)). No new unit tests. No UI changes.

### Activation and assignment accounting

- 49,908 recorded away-defense DC calls across benchmark conditions.
- 4,868 package activations, of which 1,903 (39.1%) occurred in secondary situations.
- All thirteen package IDs activated.
- 23,269 resolved away-defense kick-pass attempts and 53,565 rusher commitments reconciled between play logs and game summaries. No rush/coverage overlap, duplicate assignment, or out-of-bound count was reported by benchmark accounting checks.

| Package | Activated | Secondary activations |
|---|---:|---:|
| Goal Line Stand | 176 | 35 |
| Short Yardage Wall (two opponents) | 129 | 23 |
| Kick Range Shell | 338 | 37 |
| Long Yardage Bracket (two opponents) | 733 | 303 |
| Prevent | 602 | 182 |
| Short Yardage Pressure | 43 | 10 |
| Rush Line | 1,033 | 122 |
| Kick-In Press | 96 | 67 |
| Ride | 131 | 58 |
| Containment | 557 | 322 |
| Robber Coverage | 572 | 361 |
| Lateral Trap | 446 | 377 |
| Exhaustion Press | 12 | 6 |

### Actual rush count distribution

| Actual rushers | Attempts | Pressure events | Pressure rate |
|---:|---:|---:|---:|
| 1 | 1,402 | 325 | 23.2% |
| 2 | 15,714 | 4,906 | 31.2% |
| 3 | 4,147 | 1,661 | 40.1% |
| 4 | 1,742 | 808 | 46.4% |
| 5 | 258 | 146 | 56.6% |
| 6 | 6 | 0 | 0.0% |

Pooled counts combine distinct offenses, schemes, coaches and repeated control conditions. They are descriptive, not independent randomized observations. The six-rusher sample is insufficient for an effectiveness conclusion.

Within the enabled Rush Line case against Lateral Spread, two-rusher attempts generated 32.5% pressure (403 attempts) and 45.6% completion on releases; four-rusher attempts generated 47.2% pressure (369 attempts) and 56.4% completion on releases; five-rusher attempts generated 57.7% pressure (52 attempts) and 58.5% completion on releases. This is consistent with the intended pressure/coverage concession, subject to selection and release-type differences.

### Tactical outcomes

Eligible-play comparisons below use the full on/off conditions, not selected-only snaps. Run-family aggregate rates are weighted by attempts.

| Package / opponent / outcome | Off | On |
|---|---:|---:|
| Short Yardage Pressure / Ground Pound / dive + power yards per play | 9.93 (43) | 6.70 (37) |
| Rush Line / Lateral Spread / sweep + speed + lateral yards per play | 3.94 (281) | 3.11 (269) |
| Rush Line / same / kick-pass yards per attempt | 7.53 (669) | 7.87 (771) |
| Long Yardage Bracket / Boot Raid / kick-pass completion | 28.1% (548) | 26.5% (487) |
| Long Yardage Bracket / Ground Pound / dive + power yards per play | 12.76 (114) | 14.58 (114) |
| Prevent / Shock & Awe / kick-pass yards per attempt | 4.08 (504) | 2.86 (549) |
| Prevent / same / kick passes gaining 30+ yards | 3.4% | 2.6% |
| Containment / Lateral Spread / sweep + speed yards per play | 3.13 (156) | 2.22 (139) |
| Lateral Trap / Lateral Spread / lateral yards per play | 6.11 (62) | 4.62 (69) |

The broader sample supports several intended tactical distinctions: perimeter suppression with kick-pass concessions, short-yardage pressure, and deep coverage with open interior lanes. Not all packages improved every targeted outcome. For example, Kick-In Press increased eligible kick-pass yards from 11.90 to 13.42, Ride increased them from 5.39 to 6.76, and Robber Coverage left overall eligible kick-pass completion approximately unchanged (35.2% vs 35.2%). Those aggregate measures do not isolate short versus deep subtypes. Exhaustion Press activated only 12 times. Avoid declaring the catalog universally effective or retuning based on these small cells.

## Decision and remaining work

Merge the expanded mechanics because integrated execution, accounting, and regression checks succeeded, and several expected tradeoffs were observed. Retain the bounds until a multi-season dynasty study provides more rare-event observations. Do not increase six-rusher frequency simply to improve the benchmark sample.

Next study: natural package installation and coordinator turnover, player quality and conditioning, per-subtype release outcomes, laterals intercepted by transfer number, rare exhaustion and six-rusher calls, and league-wide scoring distributions. A full dynasty and a live deployment smoke test remain unverified. No claim of production deployment is made here.

Simulated pressure, rotating pressure disguise and receiver-specific double coverage were discussed but are not catalog entries in this change. They require explicit pre-snap offensive response and receiver/defender assignment mechanics; labels alone would not implement them.

### Reproduce

`PYTHONHASHSEED=0 python scripts/benchmark_defensive_packages.py --games 24 --seed 20261123 --out reports/expanded-defense`

Game reporting contract: additive `defensive_call.intended_rushers`, `defensive_call.package_strength`, `defensive_call.package_eligibility`, `defensive_call.tactical_context`, `rush_event.intended_rusher_count` and existing actual assignment/summary fields. The stats site can consume these from the existing full result.
