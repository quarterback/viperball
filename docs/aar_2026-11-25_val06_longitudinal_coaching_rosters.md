# VAL-06 — Longitudinal college coaching and roster study

Baseline: merged main b2bc68a, including CCH-09, CCH-08, FAT-01, DEF-04/05, HS-01 and offensive package calibration. Study only: no gameplay or development coefficient changes.

## Questions

- Are coach ratings, development tiers and reputation meaningfully distinct over long careers? Does the market reward strong records without forcing weak-program coaches to regress?
- Do ordinary, late and exceptional developers show different observed trajectories without universal rating inflation? Do ready but nonaspiring specialists remain in coordination? Do promotions, former-HC assistants, smaller-program moves, and multiple appointments occur?
- Are long-lived careers credible? No persistent unemployed coach pool is assumed. A coach leaving active staff is not necessarily retired; age and disappearance are observed separately.
- Do programs improve through recruiting, returning-player growth, staff continuity and on-field results? Does roster class ordering and positional depth survive 5 and 10 years? Are walk-ons, emergency fills and transfer identities reconciled?
- Is the pregame roster-based expectation proxy calibrated? Record observed win frequencies and Brier error by probability bin; never infer causal coach contribution from it.

## Runs and evidence

Reuse scripts/benchmark_dynasty_tactics.py and its full-engine API, recruiting, high-school feeder, injury, portal and DB reload invariants. The observational module records opening snapshots, completed regular/postseason outcomes, development before recruiting, and finalized offseason transition. Every year writes JSON (atomic checkpoint for observation files). No synthetic wins or forced careers. Final season is played but not advanced, so N seasons provide N-1 offseason transitions. Study is descriptive; compare across cohorts and seeds before proposing tuning.

| Seed | Programs | Played seasons | Planned full games | Purpose |
|---|---:|---:|---:|---|
| 20261124 | 16 | 30 | 2,970 | Long coaching trajectory and roster milestones |
| 20261125 | 16 | 20 | 1,980 | Independent-seed check |
| 20261126 | 32 | 10 | 1,950 | Broader roster and market sample |

Five- and ten-year observations are prefixes of longer trajectories, not independent additional runs. Sixteen-program leagues have 96 regular games and three playoff games per year; 32 have 192+3. Planned total 6,900 games, subject to actual schedule and completion. Reduced leagues are not representative national coaching markets; separate existing 204-team two-season national runs remain the breadth check. One designated human program does not participate in automated coaching carousel, as in existing benchmark; report this limitation. No cross-division promotion simulation or deployment claims.

Reports: summary.json, annual opening snapshots, program season outcomes, per-player permanent development deltas, transition staff and hire ledgers, full coach and program trajectories. Include raw ability and attributes, role years, ambition/readiness, reputation, age, salary, actual calling authority, retention and position/class distributions. Study does not manufacture historical experience or label departed coaches retired. Opening ratings and post-development values are paired by player ID, descriptive not causal effects of staff. Age, exposure and role must be considered when comparing development tiers.

Commands: PYTHONHASHSEED=0 python scripts/benchmark_dynasty_tactics.py --seasons 30 --teams 16 --seed 20261124 --longitudinal --out reports/longitudinal-dynasty (vary matrix values). Existing workflow runs extended matrix on study branches or explicit manual input; existing 3-season study exercises same observer. No separate feature CI suite.

## Status and continuation

Implemented observer and study configuration; runtime results pending. Read annual artifacts and record actual sample sizes, failed gates and observed distributions in this AAR. Investigate extreme ages, market mobility and rating tails, then decide whether targeted fixes are warranted. Only after evidence: remaining leadership preferences, continuity, career presentation, final integrated and deployment verification.
