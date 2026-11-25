# DEF-06 assessment: 16 × 8 defensive matchup study

**Date:** November 23, 2026  
**Status:** Study completed and validated in GitHub CI; [implementation PR #326](https://github.com/quarterback/viperball/pull/326) remains unmerged.  
**Source:** [CI run 45233356243](https://github.com/quarterback/viperball/actions/runs/45233356243). Code is in `analysis/def-06-full-matchup-matrix`, based on DEF-01/02/03 PR #325 and engine fixes PR #323.  
**Purpose:** Determine whether the existing defenses behave differently against specific offenses and formations, and give future agents a repeatable diagnostic before any further tuning.

## Executive findings

The defensive schemes now exhibit measurable strengths and concessions. The clearest examples are:

- **Lockdown** suppresses kick passes but concedes ground yardage. Its aggregate kick-pass completion allowed was **50.5%**, versus **64.6%** against Swarm. It allowed **4.99 rushing yards/play**, versus **4.43** against Swarm. Within matched scenarios, its kick-pass rate difference was **−14.1 percentage points** (bootstrap 95% interval −16.3 to −11.8), and its run-yardage difference was **+0.49 yards/play** (+0.30 to +0.69).
- **Fortress** allowed the fewest rushing yards (**4.21/play**), while allowing the highest kick-pass completion (**68.1%**). Its play-type tradeoff is visible, but the matched run-yard reduction relative to Swarm is **−0.18 yards/play** (95% interval −0.32 to +0.00), so do not exaggerate its magnitude.
- **Drift** allowed the fewest 30+ yard gains (**1.68/game**, against **2.06** for Swarm); its matched reduction was **−0.39/game** (95% interval −0.58 to −0.18).
- **Blitz Pack** allowed more running yardage (**4.97/play**) and nearly **one additional 30+ yard gain/game** compared with Swarm. Its matched difference in sacks was **−0.10/game** (95% interval −0.34 to +0.15), not evidence of the promised pressure advantage. Pressure without a sack is not currently exposed as a consistent play-level event.
- **Predator** conceded the most rushing yardage (**5.20/play**) and **2.94 explosive gains/game**, versus Swarm's 4.43 and 2.06. Its matched points-allowed difference was **+0.13 per attacking drive** (95% interval +0.01 to +0.23), an observable cost of aggression in these contexts.
- **Weather:** The corrected clear-versus-rain test found **+0.37 turnovers/game** and **−3.74 ending energy points** for the defensive team in rain. A first, non-reproducible study appeared to show more scoring in rain, but the corrected difference was **+0.02 points/drive** (95% interval −0.07 to +0.11). Treat the early scoring signal as unstable.

These are simulated outcomes for one attacking roster and two defending rosters. They establish **observable tactical differentiation**, not a universal ranking of defensive quality.

## Design and reproducibility

**Main matrix:** 16 current offensive styles × 8 defensive schemes × 4 deliberately forced offensive formations × 2 defensive roster strengths × 2 mirrored home/away assignments × 1 replication = **2,048 full-engine games**. Each offense–defense pairing has 16 game observations, and each defense has 256. All primary games use clear weather and neutral-site settings.

**Weather test:** 4 selected offenses (Boot Raid, Ground Control, Chain Gang, Shock & Awe) × 8 defenses × 2 forced formations (Split, Spread) × 2 defending roster strengths × 2 home/away assignments × 2 weather conditions (clear/rain) × 2 repetitions = **1,024 more games**.

In both experiments the focal attacking team and the two defending rosters are the same freshly generated synthetic CVL teams. They were selected under `seed=20261123` and `PYTHONHASHSEED=0`:

| Use | Team | Benchmark rating |
|---|---|---:|
| Median-strength attacking roster | Kentucky State | 34.9 overall |
| Weaker defending roster, ~15th percentile | Drake | 30.4 defense |
| Stronger defending roster, ~85th percentile | Georgia State | 42.0 defense |

**Shared roster-selection fingerprint:** `de0784c3ec58be4c051b`, verified independently in both completed CI jobs. This is generated synthetic talent; the team names do not imply the corresponding actual programs have those strengths.

**Reproducibility repair:** The first successful run selected different rosters across two CI jobs with the same RNG seed. Direct code inspection found that `engine/season.py::load_teams_from_directory` iterates over unsorted `Path.glob("*.json")` results while random draws allocate talent. PR #326's benchmark now uses a sorted equivalent of the fresh-roster loader; a repeat-selection test passes. The **production loader is still unsorted**, separately tracked as VAL-02. Do not compare old-run averages as if they were produced by the corrected roster population.

The experiment forces one formation at a time **only on the focal offense** for normal scrimmage plays. Its opponent runs a normal Balanced offense. This isolates formation stress tests but changes ordinary play selection; it is not a prediction of formation usage in seasons. Every game uses the actual full engine, not the fast simulator. The observer subclass stamps the pre-snap attacking team to avoid misattributing turnover plays whose state.possession changes before serialization.

## Per-defense full-matrix results

All values are pooled across the 16 offensive styles, four formations, weak/strong defensive rosters and mirrored venue conditions. **Pts/drive** means points credited during the focal attacking team's possessions, rather than all points scored by the team.

| Defense | Games | Attacking pts/drive | Rush yds/play | KP complete | Sacks/KP attempt | 30+ yard gains/game | Drive stop rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Blitz Pack | 256 | 3.90 | 4.97 | 59.5% | 0.086 | 3.04 | 36.4% |
| Chaos | 256 | 3.86 | 4.92 | 59.4% | 0.094 | 2.76 | 35.6% |
| Drift | 256 | 3.62 | 4.56 | 57.2% | 0.092 | 1.68 | 36.4% |
| Fortress | 256 | 3.74 | 4.21 | 68.1% | 0.087 | 2.22 | 36.2% |
| Lockdown | 256 | 3.61 | 4.99 | 50.5% | 0.096 | 2.18 | 38.1% |
| Predator | 256 | 3.86 | 5.20 | 54.0% | 0.089 | 2.94 | 36.3% |
| Shadow | 256 | 3.71 | 4.62 | 58.6% | 0.082 | 2.16 | 35.7% |
| Swarm | 256 | 3.70 | 4.43 | 64.6% | 0.086 | 2.06 | 36.6% |

**Caution:** Sacks per kick-pass attempt are similar across defenses. The full matrix does not verify a distinct Blitz Pack pass-rush advantage. The model may need better pressure instrumentation before changing its sack coefficients.

### Paired differences against Swarm

Each pair holds the offensive style, forced formation, defensive roster, home/away role, weather and repetition fixed. These are **mean game-level differences**, with deterministic 95% percentile-bootstrap intervals over matched contexts. Scoring, running and completion differences above zero generally mean the opponent did better against that defense.

| Defense | Δ pts/drive (95% CI) | Δ run yds/play (95% CI) | Δ kick-pass completion | Δ explosive 30+ gains/game |
|---|---|---|---:|---:|
| Blitz Pack | +0.18 (+0.06, +0.30) | +0.49 (+0.30, +0.69) | −6.1 pp | +0.98 |
| Chaos | +0.14 (+0.04, +0.24) | +0.47 (+0.25, +0.65) | −6.0 pp | +0.70 |
| Drift | −0.08 (−0.19, +0.02) | +0.06 (−0.11, +0.22) | −7.7 pp | −0.39 |
| Fortress | +0.02 (−0.08, +0.13) | −0.18 (−0.32, +0.00) | +2.2 pp | +0.16 |
| Lockdown | −0.11 (−0.22, −0.01) | +0.49 (+0.30, +0.69) | −14.1 pp | +0.12 |
| Predator | +0.13 (+0.01, +0.23) | +0.69 (+0.51, +0.87) | −11.1 pp | +0.88 |
| Shadow | −0.01 (−0.11, +0.09) | +0.13 (−0.02, +0.29) | −5.7 pp | +0.09 |

Uncertainty estimates treat each matched game as one observation, not each play as independent. Random draws can diverge after a scheme changes a play; the same seed does not freeze all later events. These are descriptive intervals, not independent randomized clinical-style causal estimates.

### All 128 offense–defense cells

Attacking points per attacking possession, by offense (rows) and defense (columns). Each cell aggregates 16 games; its individual bootstrap interval and denominators are in the downloadable `matrix.csv`.

| Offense | Blitz | Chaos | Drift | Fortress | Lockdown | Predator | Shadow | Swarm |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Balanced | 3.64 | 4.08 | 3.80 | 3.76 | 3.37 | 3.67 | 3.51 | 3.65 |
| Ball Control | 3.72 | 3.85 | 3.65 | 3.35 | 3.66 | 4.11 | 3.82 | 3.47 |
| Boot Raid | 3.88 | 3.71 | 3.63 | 4.09 | 3.70 | 3.98 | 3.83 | 3.75 |
| Chain Gang | 3.37 | 3.62 | 3.16 | 3.32 | 3.33 | 3.41 | 3.56 | 3.36 |
| East Coast | 4.20 | 4.07 | 3.89 | 4.01 | 3.92 | 4.36 | 4.23 | 3.94 |
| Ghost | 4.08 | 3.85 | 3.53 | 3.55 | 3.40 | 3.76 | 3.46 | 3.63 |
| Ground Control | 3.57 | 3.84 | 3.83 | 3.78 | 3.77 | 3.48 | 3.89 | 3.73 |
| Ironclad | 3.90 | 4.00 | 3.53 | 3.56 | 3.40 | 3.97 | 3.77 | 3.82 |
| Lateral Spread | 3.69 | 3.59 | 3.64 | 3.86 | 3.44 | 3.50 | 3.64 | 3.38 |
| Mismatch | 3.75 | 3.84 | 3.81 | 3.83 | 3.47 | 3.69 | 3.48 | 3.89 |
| Mousetrap | 3.99 | 3.65 | 3.41 | 3.80 | 3.54 | 3.83 | 3.58 | 3.86 |
| Quick Strike | 4.25 | 3.57 | 3.81 | 3.87 | 3.41 | 4.07 | 3.62 | 3.78 |
| Shock & Awe | 4.20 | 4.02 | 3.44 | 3.74 | 3.75 | 3.92 | 3.84 | 3.74 |
| Six Shooter | 3.85 | 3.99 | 3.64 | 3.98 | 3.83 | 3.89 | 3.83 | 3.84 |
| Slick 'n Slide | 4.00 | 3.94 | 3.60 | 3.83 | 3.85 | 3.97 | 3.78 | 3.74 |
| Stampede | 4.22 | 4.17 | 3.62 | 3.54 | 3.96 | 4.19 | 3.67 | 3.61 |

Read these as **context-specific signals**, not a sorted league power ranking. For example, the same Fortress defense that yielded only 4.21 rushing yards/play overall still allowed 4.09 points per Boot Raid attacking drive. Coaching, snap-kick decision, and score-state Delta Yards all remain active in the engine.

## Formation and roster sensitivity

- Forced **Spread** vs Blitz Pack allowed **4.11 points/drive**, compared with **3.76** under Heavy; the expected exposure to wide formations appears.
- Forced **Spread** vs Fortress allowed **4.10**, compared with **3.57** under Heavy; this is consistent with Fortress being stronger against a compressed field.
- Forced **Spread** vs Lockdown allowed **3.55**, compared with **3.69** under Heavy; Lockdown's coverage strength is reflected in the formation test.

Switching from the weak to strong defensive roster while keeping scheme and context matched changed mean points/drive by **−0.22** (bootstrap 95% interval −0.28 to −0.16), rushing yards/play by **−0.64** (−0.75 to −0.52), kick-pass completion rate by **−2.8 percentage points**, and sacks per kick-pass attempt by **+0.025**. Stronger players have an observable effect, especially on running outcomes.

## Clear-versus-rain study (corrected)

The corrected 1,024-game weather test has **512 exact clear/rain paired contexts** (same seed, offense, defense, formation, roster and venue, with weather changed). The roster fingerprint matches the full matrix.

| Metric | Rain minus clear | Approx. 95% paired bootstrap interval |
|---|---:|---:|
| Turnovers per game | +0.365 | +0.16 to +0.56 |
| Defensive team end energy | −3.743 | −4.17 to −3.33 |
| 30+ yard gains per game | +0.293 | +0.07 to +0.50 |
| Attacking points/drive | +0.018 | −0.07 to +0.11 |
| Rushing yards/play | −0.074 | −0.26 to +0.12 |
| Kick-pass completion rate | +0.003 | −0.01 to +0.02 |

Rain increases the observed turnover burden and energy cost in this controlled sample. It does **not** provide reliable evidence that rain increases points/drive or rushing efficiency. The earlier unpinned pilot's scoring increase failed to reproduce after the roster ordering fix. Preserve that distinction in any future discussion.

## What remains unproven or missing

1. **Blitz pressure:** sacks alone do not capture hurries, unsuccessful blitzes, pressure events, or how often the extra rusher changes the tackle. Do not claim Blitz Pack generates substantially more pass pressure until that evidence exists.
2. **Runtime role alignment:** `engine/game_engine.py` assigns `game_role` before applying `style_overrides`. This can cause lead carrier and receiver roles to reflect the team's previous default style despite the intended offensive scheme. Tracked as ROST-02.
3. **Production deterministic rosters:** the benchmark workaround sorts input files, but the production season loaders still use unsorted `glob`. Tracked as VAL-02. Python's `hash()` also appears in seeds elsewhere.
4. **Single attacking roster:** only a synthetic median-strength attacking team was used. Results can depend on elite kickers, line strength, roster holes, work rate, and depth; use additional roster profiles before treating any scheme as globally strongest.
5. **Partial surface attribution:** the engine's ordinary kick-pass box score reports completions and sacks, but defensive hurry/pressure attempts are not in a consistent play event; team bell totals may include events outside the focal attack; and individual defensive read successes are aggregated by team.
6. **Other tactics remain active:** form, fatigue, weather, score-based Delta Yards restarts, late-down clamps and Solved Puzzle adaptation were not individually disabled in this factorial. Differences may reflect their interactions with scheme.
7. **Small per-cell sample:** each offense-defense cell has 16 games, split across four forced formations, two roster strengths and two venues. Individual formation-by-tier results have few observations. Do not infer precise rankings within small cells.
8. **Historical and mode parity:** pro/WVL/HS fast sim paths were not part of this full-engine college test, and no live deployment was exercised.

## Reproduction, artifacts and validation

```sh
PYTHONHASHSEED=0 python scripts/defense_matchup_matrix.py --seed 20261123 --reps 1 --out reports/def06
PYTHONHASHSEED=0 python scripts/defense_matchup_matrix.py --seed 20261123 --reps 2 --offenses boot_raid,ground_control,chain_gang,shock_and_awe --formations split,spread --weathers clear,rain --out reports/def06-weather
python -m pytest tests/test_defense_matchup_matrix.py -q
python -m pytest tests/ -q
```

**Validated in [CI run 45233356243](https://github.com/quarterback/viperball/actions/runs/45233356243):** 8 DEF-06 unit/smoke tests passed; 94 repository tests passed; 2,048-game full matrix and 1,024-game weather study completed; both shared the exact roster fingerprint `de0784c3ec58be4c051b`. Nothing was changed in scoring rules or the core play engine in PR #326.

Raw tables and per-cell intervals are attached as downloadable GitHub Actions artifacts (90-day retention):
- [Full 16×8 matrix, games, play-family counts, contrasts, report, metadata](https://github.com/quarterback/viperball/actions/runs/45233356243/artifacts/14848212750)
- [Weather study, paired contexts, report and metadata](https://github.com/quarterback/viperball/actions/runs/45233356243/artifacts/14847544187)

The code is permanent once merged; rerun the experiment to regenerate expired artifacts.

## Work queue decisions

**DEF-06 evidence collection:** Complete for this defined one-attacker, two-defender-roster factorial; mark **IN REVIEW** until PR #326 is merged. This establishes that tactical distinctions can appear. It does not mean the defensive engine's realism or balance is finished.

**New follow-up:** `DEF-07` — instrument actual defensive pressure events (rushers sent, blitz called, quarterback/kicker pressure, hurry, sack, protection assignment and yardage consequence). A sample with Blitz Pack should show a measurable pressure mechanism and corresponding risk, with matched personnel; do not optimize directly for sacks.

**Existing follow-ups:** `ROST-02` — assign roles after resolved style, `VAL-02` — deterministic production roster and scheme seeds, `DEF-04` — individual defensive lineup effects, `UI-01` — player-facing scheme and defensive-impact reports. A separate weather-mechanics check should isolate why rain increased turnovers, energy drain and 30-yard gains without a reliable scoring rise.

**No tuning requested:** Do not impose a target score, percentage of close games, home win rate, or required distribution of defensive winners based on this one experiment.
