# AAR: League-scale calibration, rush credits, Delta Yards, and deployment

**Date:** November 24, 2026
**Workstream:** DEF-08, DEL-01, DEL-02, VAL-03 and OPS-02
**Branch:** `engine/league-calibration-rush-delta-20261124`
**Base:** current main, prior to open special-teams PRs #349 and #354.

## Baseline evidence

The national three-week sample from `AAR_2026-11-24_game_plans_report.md` showed a median **70%** of each team's sack-plus-lead-hurry credit assigned to its leading player. A separate 16-team, three-season dynasty study recorded **15,401** resolved kick-pass rush attempts and **1,816** sacks (11.8%). Its schedule generated **94/95/95** regular games instead of **96** each year, despite completing all scheduled games. These are historical benchmark observations, not measurements of this branch.

Current main in `engine/game_engine.py` calls the highest-scoring committed defender the `lead_rusher` on every kick pass, guaranteeing one player all pressure credits whenever they are one of the rushers. The same play can roll an unrelated 35% late-incompletion hurry; that may assign a second player who did not rush or have a resolved hurry. This violates the physical event model.

The Delta restart rule starts a receiving team at a yard line determined by its score differential (subject to bounds); positive `delta_cost` means a worse start and negative means an advantage. However:
- `engine/viperball_metrics.calculate_delta_profile` formerly labeled *offensive yards minus opponent offensive yards* as `delta_yds`, contradicting engine `stats.delta_yards`.
- `calculate_ppd` estimated every scoring kick as 4.2 points and returned 3.0 when there were no drives. New drives carry actual running score snapshots.
- `stats.kill_rate` and `stats.delta_drives` used mutable kickoff counts, while DYE separated **played drives** with positive/negative/zero `delta_cost`.
- An unused restart after the final scoring play could affect the engine's Delta accumulator but never appear on a real drive.

## Implementation

### DEF-08: meaningful individual rusher credit

Each actual rush still commits the same 1–6 eligible defenders. The same physical pressure/sack outcome and defensive contest coefficients remain in place. The lead defender is now selected *among the committed rushers*, with stronger and fresher players favored but not guaranteed every credit. Selection uses a dedicated seeded stream rather than adding draws to the global play RNG. A `rush_credit_model=highest` control reproduces the historical selection for comparison. An actual resolved hurry awards one credit to the winning rusher; the unrelated incomplete-pass 35% roll is removed. Credited sacks and hurries remain subject to accepted-penalty nullification, so compare both physical and official counts.

### DEL-01: counterfactual

`delta_restarts_enabled` defaults to true (unchanged gameplay). When disabled for a matched benchmark, teams receive the ordinary fixed start line after scores and accrue zero Delta Yards. Compare the same game seeds, rosters, weather and rush-credit model with on/off starts; observed differences measure the system-wide outcome change, **not** a pure causal estimate for a specific team or possession.

### DEL-02: consistent definitions

- `Delta Yards` means the sum of observed drive-start costs: positive when score-dependent restarts push the team backward, negative when they help.
- `delta_restart_unplayed` records any difference from an assigned restart that never actually became a played drive.
- `delta_drives`, `delta_scores`, and `kill_rate` refer to the same played penalty-kill drive bucket as the DYE breakdown and DTW.
- `delta_profile.delta_yds` now uses the same Delta Yards definition (legacy key retained), with `net_yards_advantage` separately identified.
- `points per drive` uses actual differences in recorded final scores over offensive drives, rather than a fixed 4.2-point estimate for scoring kicks. Historic records lacking drive scoreboard snapshots use a documented approximate fallback.

### VAL-03: league-scale audit

`scripts/benchmark_national_engine.py` creates a real college API season with a temporary isolated database, records schedule counts for **all** programs, runs complete games using normal rosters and schedules, and reports scoring, passing, penalties, pressure, individual rush shares and package adoption. One-week CI provides a national smoke; `--full-season` provides a separate schedule-fulfillment and league-calibration study. No fast simulator or forced tactical installation. `scripts/benchmark_rush_delta.py` is a seeded paired full-engine on/off study of rush credit and Delta restarts. These benchmarks are diagnostic; they do not impose arbitrary close-game, sack, or kick targets.

## Deployment: verified boundary

The checked-in `fly.toml` targets the `viperball` Fly.io app, with `performance-2x`, 4 GB RAM, and a persistent `/data` volume. Importantly, it has `auto_start_machines=false` and `auto_stop_machines='off'`; the machine may be manually stopped. The repository's deploy workflow validates the Docker build, deploys on
pushes to `main` using the `FLY_API_TOKEN` secret, and then polls
`https://viperball.fly.dev/api/health` for HTTP 200. This branch adds
`VIPERBALL_BUILD_SHA` as a Docker build argument, exposes it in the
read-only health response and changes deployment validation to compare
the exact live SHA to the GitHub commit being deployed. A 200 response
from an older version will no longer count as successful verification.

An external request to `https://viperball.fly.dev/api/health` and `/stats` was not accessible through the available browser tool. **This does not establish that the deployment failed**: the Fly machine might be stopped or the network tool might not reach it. The current branch has not been deployed; no live build SHA or database persistence verification has been observed. Verify the deploy workflow run and Fly machine state after merging; do not start a billable machine as an implicit side effect of the calibration PR.

## Initial observed CI results

[Run 45451097215](https://github.com/quarterback/viperball/actions/runs/45451097215),
seed `20261124`, was a successful milestone run after correcting the
benchmark's distinction between physically resolved rushes and official
sacks/hurries erased by accepted penalties. The full Python suite,
BOX-01 accounting smoke, 8 matched games per condition and the actual
national first-week sample passed.

In eight matched games per condition (16 team-game accounts):
- Historical highest-rusher credit produced a mean leading-player share
  of **77.7%** with Delta starts. Weighted eligible-rusher credit
  produced **49.3%** under the same conditions.
- With neutral starts, the shares were **76.2% vs 52.2%**.
- The Delta restart rule changed the final score in **8/8** matched
  games for each credit model; mean absolute home-score difference
  was **27.375** points with historical credit and **21.062** with
  weighted credit. These are small, matched descriptive samples, not
  proof of a universal causal effect or a target to tune toward.
- Physical rush and official player credits reconciled after excluding
  penalty-nullified sacks and hurries. No new sack probability was set.

The actual national first-week API season contained **205 programs**,
**90 completed full-engine games**, **5,192** kick-pass rush attempts,
**1,685 pressures**, **639 sacks**, and **1,046 hurries**. Team-game
mean points were **52.372**, mean accepted penalties **19.772**,
and the median leading-rusher share was **54.36%** across 178
team-game accounts with any lead pressure credit. A single week
cannot support long-term trends or a national full-season conclusion.

The schedule audit revealed **203 programs assigned 12 regular games
and two assigned 13**, or 1,231 rather than the requested 1,230
games. The original audit erroneously described all 203 correctly
scheduled programs as `under_scheduled` by comparing against 13.
That report was corrected to compare against the requested quota,
and the scheduler now includes a narrow repair for the two excess
slots that does not remove pinned or rivalry games.

## Completed national milestone and matched comparison

[GitHub Actions run 45451738507](https://github.com/quarterback/viperball/actions/runs/45451738507)
completed successfully at commit `ac5b273` with 181 Python tests,
the BOX-01 accounting smoke, 40 matched full games per condition and a
**complete 205-program national regular season**. All five relevant
workflows succeeded on that commit, including defensive and coaching
regressions. The output artifact is available in the same run.

**National season:** 205 teams each had exactly **12 regular-season
games**, yielding **1,230 scheduled and completed games** across 16
simulated weeks. No program was under- or over-scheduled. This fixes
the earlier two-school 13-game surplus for the tested season seed.
It does not prove schedule parity for every future seed or conference
alignment.

**National performance (1,230 games, seed 20261124):**

| Measure | Observed |
|---|---:|
| Average team points/game | 52.393 |
| Average actual offensive points/drive | 3.054 |
| Average accepted penalties/team-game | 21.537 |
| Kick-pass completion fraction | 45.7% |
| Rush attempts / physical pressures / sacks / hurries | 70,473 / 23,058 / 9,227 / 13,831 |
| Physical pressure rate | 32.7% |
| Physical sack rate | 13.1% |
| Median top rusher share of team sack + lead-hurry credits | 54.55% (2,433 teams-with-credits) |
| Defensive package activations | 30,374 |
| Average net Delta Yards/team-game | -48.271 |

The elevated physical sack frequency and penalties remain findings
for a later controlled calibration. They are **not** justification to
change scoring or defeat the score-based restart rule.

**40 matched games per configuration, Delta enabled:**

| Model | Mean top rusher credit share | Median final margin | Mean team points |
|---|---:|---:|---:|
| Historical highest rusher | 78.4% | 21.75 | 75.875 |
| Weighted committed rusher | 52.0% | 19.25 | 77.344 |

The new physical attribution spreads individual credit across actual
participants; it does not apply a new sack-success bonus.
With weighted credit, neutralizing Delta starts increased the
median final margin from **19.25 to 33.0** in the matched sample.
All 40 matched final scores differed; mean absolute home-score
change was **25.275 points**. With the historical credit model,
median margin changed from 21.75 with Delta to 36.0 without.
Different matched paths evolve from the restart change, so these
are system-level comparisons, not individual-play estimates.

**Design decision:** Delta Yards remains the defining Viperball
mechanic. The score differential adjusts the next restart field
position, pushing a team with a lead backward and helping a team
that trails. The `delta_restarts_enabled=False` switch is **only
a calibration/ablation control**; normal games always default to
`True`. No proposal to remove, reduce, or genericize Delta Yards
is made. The observed change in margins supports keeping it
unchanged while using the neutral control only to evaluate its
impact.

**Validation limits:** This is one national seed, one full season,
and 40 matches per counterfactual condition. The national sample
shows a complete schedule and a more distributed individual rush
ledger, but does not establish a long-run league equilibrium.


## Validation and next decisions

Expected milestones:
1. Existing full regression suite and BOX-01 scoring audit.
2. Paired rush/Delta benchmark: player credits agree with the official event model, rushing assignment is roster-eligible, and the measured leader share differs from historical deterministic maximum without modifying pressure coefficients.
3. National first-week smoke and schedule inventory.
4. An eventual full national season across multiple seeds to examine schedule shortfalls, rare package adoption, point distribution and roster attrition.
5. Final live Fly deployment health and actual SHA check when the service is intentionally running.

**Status:** National full-season and matched calibration completed and
passed. Build-SHA verification code is implemented, but a **live Fly
deployment and running build SHA remain unverified**. Do not claim
deployment success until the Fly health endpoint confirms the new SHA.
