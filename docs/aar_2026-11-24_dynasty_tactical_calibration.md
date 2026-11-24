# AAR: Multi-season dynasty tactical calibration

**Date:** November 24, 2026 UTC  
**Status:** Three-season study complete; production fixes merged.  
**PR:** [#344](https://github.com/quarterback/viperball/pull/344), merge [ed9204a](https://github.com/quarterback/viperball/commit/ed9204afce8e27dad48d93cba556d6e67e54eced).  
**Evidence:** [Integrated run 45340880176](https://github.com/quarterback/viperball/actions/runs/45340880176), [results artifact 14896281090](https://github.com/quarterback/viperball/actions/runs/45340880176/artifacts/14896281090), [existing regression run 45340880191](https://github.com/quarterback/viperball/actions/runs/45340880191). Prior work: [rare tactical situations](aar_2026-11-24_rare_tactical_situations.md).

## Objective and method

Exercise the playable college dynasty path instead of the historical fast simulator. Study natural package installation and growth, coaching changes, recruiting, transfers, roster fit, fatigue and game outcomes. No installed-package fixtures, forced calls, or new tactical coefficients.

The study uses the real application API through FastAPI TestClient, a temporary SQLite database and sixteen existing program files distributed across two conferences. Requested schedule: twelve regular games per program, four-team playoff, no bowls. The designated human program uses the existing auto-recruit helper for its recruiting board; its staff is not subject to automatic firing, consistent with the normal game. CPU scheme assignment uses the normal application path, including yearly seed changes. Seed 20261124. Three seasons (2026–28), two completed offseason cycles and actual database reloads between seasons.

The scheduler produced 94, 95 and 95 regular games rather than the requested 96 per year, plus three playoff games per year. All scheduled games were completed: 293 full-engine games. This is a reduced-league, single seeded trajectory, not a representative national league sample or a causal estimate of coaching effectiveness. First-unit familiarity snapshots are after the first recorded game, not before it.

## Corrections found during implementation

1. The standalone Dynasty file save already preserved team installations, but the application database serializer did not. Added the same versioned installation records to database save/load, with old saves defaulting to an empty record. Also preserved nonnumeric development-history keys (redshirt events) when loading.
2. Player development updated PlayerCards but the app rebuilt its next offseason cards from Player objects that retained old ratings. Copy the developed ratings back before this conversion.
3. Installation sync now rechecks catalog personnel requirements when roster-fit tags change, preserving familiar packages that still fit and retaining coordinator continuity. This uses the existing league-normalized roster profiles, not an absolute talent cutoff.

The study verified equality of installation records, coaching IDs and finalized next-season rosters across both application database round trips and continued through the real load/start-season endpoints. No production tactical coefficients, activation rules or UI changes. No new unit-test suite. All 174 existing tests passed; the older matched-game job was still running at merge.

## Season outcomes

| Measure | 2026 | 2027 | 2028 |
|---|---:|---:|---:|
| Regular games | 94 | 95 | 95 |
| Playoff games | 3 | 3 | 3 |
| Champion | Virginia | Virginia | Michigan State |
| Changed DCs entering season | Initial staff | 2 | 4 |
| Installed defense packages at season end | 28 | 32 | 28 |
| Distinct installed package IDs | 11 | 9 | 9 |
| DC calls | 16,077 | 15,888 | 15,322 |
| Eligible package opportunities (package-level, may overlap) | 9,639 | 10,216 | 7,786 |
| Selected packages | 1,966 | 3,912 | 3,238 |
| Secondary activations | 751 | 1,067 | 968 |
| Selected / eligible package opportunities | 20.4% | 38.3% | 41.6% |
| Mean selected package execution strength | 0.378 | 0.733 | 0.731 |
| Mean installed package familiarity at season end | 0.664 | 0.877 | 0.907 |
| Kick-pass rush attempts | 4,969 | 5,618 | 4,814 |
| Pressure rate | 29.0% | 29.3% | 30.8% |
| Sack rate | 11.6% | 11.5% | 12.4% |
| Final regular-week mean carried fatigue | 6.59 | 5.62 | 4.95 |
| Installed packages failing personnel fit at snapshot | 0 | 0 | 0 |

Total: 47,287 DC calls, 9,116 package activations (2,786 secondary), 15,401 resolved kick-pass rush attempts, 4,567 pressure events (1,816 sacks, 2,751 hurries). Package selection is one per snap, while the eligibility denominator counts all eligible installed packages.

## Staff and learning

| Season / DC cohort | Defensive team-games | Mean execution factor | Selected / eligible package opportunities | Points allowed per team-game |
|---|---:|---:|---:|---:|
| 2027 new DC | 24 | .429 | 15.9% | 55.04 |
| 2027 retained DC | 172 | .910 | 40.8% | 51.04 |
| 2028 new DC | 47 | .385 | 16.1% | 60.66 |
| 2028 retained DC | 149 | .886 | 44.5% | 49.69 |

The observed installation difference is substantial: retained DCs execute more familiar systems and call packages more often. The points difference is descriptive; firing, scheme changes, opponent quality and recruiting are not randomized. The first season uses initial staff and is not a true retained-DC cohort despite the benchmark's group label.

## Offseason and roster continuity

| Transition | Coach hires (all roles) | Teams with coaching changes | Transfers resolved | Signed recruits | Installation records preserved |
|---|---:|---:|---:|---:|---:|
| 2026 → 2027 | 18 | 6 | 7 | 95 | 16/16 |
| 2027 → 2028 | 19 | 5 | 9 | 99 | 16/16 |

Both database reload checks passed and the next season started with the finalized rosters. Across the first transition, programs retained an average of 26.94 players and added 15.00; across the second they retained 32.31 and added 9.88. Returning player stamina ratings increased by an average of 0.95 and 1.02 points per transition; tackling by 0.83 and 0.96. These are observed roster changes, not randomized developmental effects. Roster sizes after the two offseason completions ranged from 40 to 44. Arrival counts include fallback freshmen, transfers and signed recruits, so arrivals are not identical to signed counts.

## Pressure and fatigue

| Actual rushers | Attempts | Pressure events | Pressure rate |
|---:|---:|---:|---:|
| 1 | 1,020 | 211 | 20.7% |
| 2 | 11,327 | 3,203 | 28.3% |
| 3 | 2,397 | 890 | 37.1% |
| 4 | 526 | 207 | 39.4% |
| 5 | 126 | 55 | 43.7% |
| 6 | 5 | 1 | 20.0% |

The pressure gradient through five rushers persists under naturally installed packages and actual coaching staffs. Six-rusher calls remain too rare for an observational effectiveness estimate; retain the earlier matched replay evidence. Defender energy below 75 was associated with roughly 5.71 yards allowed per called snap (5,949 snaps) versus 4.74 at energy 85 or higher (22,658 snaps). These are conditional descriptive observations, not causal fatigue estimates.

## Catalog adoption and unresolved issues

Eleven of thirteen defensive packages were installed during the first season; the last two seasons each had nine distinct IDs. Exhaustion Press and Robber Coverage were never installed in this trajectory. Kick-In Press and Ride appeared in the first season only (13 and 9 activations). The league produced 3,379 DC calls against offenses with on-field energy below 75, but no Exhaustion Press calls. This distinguishes **adoption** from situational execution: natural fatigue exposure exists, but this sample had no qualifying installed Exhaustion Press. Do not infer that it would be effective or change its activation threshold from this evidence.

The schedule shortfall is a separate defect: Duquesne and Virginia played 11 and 9 regular games in 2026; Swarthmore played 10 in 2027; NYU and San Diego State played 11 in 2028. All generated schedules finished; this is not a stalled simulation. Fix schedule fulfillment independently of tactical calibration and verify on reduced and national leagues.

## Decisions

- Keep current defensive coefficients and rare commitment bounds. Familiarity and coaching turnover now produce meaningful variation across seasons, while pressure rates remain relatively stable.
- Prioritize catalog adoption diversity and Exhaustion Press's relative-protection-fatigue mechanism for the next tactical investigation. A larger national dynasty sample is required before declaring natural catalog balance.
- Fix the schedule shortfall, then run a larger league study across multiple seeds. Full national dynasty calibration and live deployment verification remain open. The successful temporary database study is not a live-site deployment test.

Reproduce: `PYTHONHASHSEED=0 python scripts/benchmark_dynasty_tactics.py --seasons 3 --teams 16 --seed 20261124 --out reports/dynasty-calibration`.
