# DEF-11 — Defensive coordinator package preferences

Status: implementation committed; candidate runtime validation pending. College-only. Branch builds on VAL-05 #372 (head 00fd1a3), itself based on merged main 49d3a1d. No professional or international changes.

## Verified merged baseline

[VAL-05 workflow 45507629966](https://github.com/quarterback/viperball/actions/runs/45507629966) passed the reduced-league, rare-replay and two national jobs. National jobs 138849742524/138849742418 each completed 2,462 full games (1,224 regular + seven playoffs in each of two seasons). Both naturally reached all 13 defensive packages in year two and reported zero package-fit violations.

| Seed/year | Package calls | Installed IDs | Exhaustion calls | Robber calls |
|---|---:|---:|---:|---:|
| 20261124/2026 | 23722 | 12 | 44 | 0 |
| 20261124/2027 | 42267 | 13 | 53 | 39 |
| 20261125/2026 | 22718 | 12 | 17 | 0 |
| 20261125/2027 | 41882 | 13 | 19 | 32 |

Total 4,924 national games, 130,589 package calls, 133 Exhaustion Press calls and 71 Robber Coverage calls. The reduced-league study also completed 891 games. National physical rush ledger: 258,684 attempts, 83,568 pressures, 18,514 sacks. These rates describe the engine, not calibration targets. National roster opening freshmen mean 32.39; second-year freshman means 35.80 and 35.81. First reduced trajectory 2028 freshman mean 43.26 vs senior mean 39.66; investigate cohort selection and development in ROST-02/HS-01.

## Mechanism

Previous ranking gave all pressure packages the same pressure term, all coverage packages the same pressure/coverage term, and both wall packages the same support term. Native-book preference and alphabetical ordering then decided many distinct tactical jobs. The national study shows rare packages are reachable; equal adoption is not the objective.

Keep existing pressure/support and native-book terms. Match each package to its documented defensive task using primary and adjacent coverage focus (.08/.04), plus read-group overlap (maximum .025). These are installation preference weights, not play-success modifiers. The table is explicit and editable, not inferred from simulated outcomes; its weights are a proposed model to test. Deep and intermediate coverage coordinators can distinguish Prevent and Robber; intermediate and perimeter preferences can distinguish the two Predator press packages. Resolve remaining exact ties with a stable hash of coach and package ID, not global RNG or alphabetical priority. No new coordinator profile fields; no save migration, forced replacement of valid learned packages, changes to personnel gates, live eligibility, activation probabilities, rush/coverage physics, fatigue costs or scoring. Offensive package ranking is unchanged.

Diagnostics expose category, coverage, read and native-book score components, and adoption snapshots retain the existing ranking and fit contract. Focus-level adoption summaries distinguish end-season installed packages and top-two ranking from game-day call denominators.

## Acceptance

Focused tests cover different focuses at identical pressure, read/native terms, stable exact ties, unchanged RNG, agreement between diagnostics and fresh installation, and retained/removal behavior. Existing integrated workflow compares the same seeds against VAL-05, with national/reduced schedule, roster and persistence gates intact. Report per-focus preference and installation distributions, activation counts, pressure/coverage and rare replay tradeoffs without imposing utilization targets. Do not infer a causal package effect from observational adoption rates. Existing saves retain valid installations and may only reflect the new preferences when ordinary installation selection occurs.

Next: CCH-07 coaching development, career movement and adaptation; PBK-05 offensive package execution; ROST-02/HS-01 college roster and recruiting continuity. Final integrated validation and live college deployment verification remain outstanding.
