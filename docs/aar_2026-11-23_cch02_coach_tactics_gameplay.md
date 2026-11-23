# CCH-02 AAR: coordinator identity affects live play-calling

**Date:** November 23, 2026  
**Implementation:** [PR #328](https://github.com/quarterback/viperball/pull/328), branch `feature/coach-tactics-gameplay-cch-02`.  
**Base:** coach-card persistence [PR #327](https://github.com/quarterback/viperball/pull/327), still open at the time of the work.  
**Validation:** [GitHub Actions run 45242379413](https://github.com/quarterback/viperball/actions/runs/45242379413) — 9 dedicated CCH-02 tests passed, all 94 tests passed; 320 matched full-engine games completed.  
**Merge status:** not merged or deployed. PR #323 and PR #325 also change the engine and need integration/rebase before deployment.

## Decision and scope

Two coaches using the same named offense now make **different legal decisions**, based on persistent, saved OC signatures from CCH-01. This is a first version of coordinator-driven tactical identity; the other agent can independently design playbook *packages* from `data/playbooks/**` and `engine/playbook_catalog.py`. CCH-02 does not add new plays, define packages, or increase raw yardage/accuracy ratings.

### Implemented

1. **Coordinator preference resolution:** `engine/coach_tactics.py::resolve_offensive_tactics` selects the OC's saved profile and allows the head coach's saved delegation value to limit its authority. If there is no OC, the new tactical layer is neutral; existing HC personality and countermeasure systems remain intact.
2. **Formation selection:** the coordinator can favor certain Tight/Split/Spread/Heavy shells. Relative preference adjustments apply after the existing formation-specific game-state and weather adjustments, before normalization.
3. **Play family:** a bounded bias affects eligible run, lateral, trick and kick-pass choices after game-state adjustments and final kick/down/range gating. It changes relative weights only; it cannot create a nonexistent play family or revive an explicit zero.
4. **Kick-pass subtype:** the OC can favor Quick Kick, Territory, Bomb or Kick-Lateral after physical kicker limits, game situation and existing style adjustments.
5. **Featured position:** eligible players at the coach's featured position receive a capped 18% relative selection preference when considered as runners or kick-pass targets. Existing starter/lead ranks, fatigue, individual skills and depth stay active; ineligible players cannot be selected.
6. **ROST-02 sequencing:** `assign_game_roles` is now called **after** offensive style overrides and migration, instead of before. This fixes the ordering. The existing role-scoring function is not yet deeply scheme-specialized, so additional role-fitting behavior belongs to ROST-02 follow-up rather than being claimed complete here.
7. **Visibility:** `full_result.coach_tactics.home/away` includes the OC ID, interpretation, HC-approved authority, featured position and actual counts of formation, play family, subtype and featured-position usage. Each `play_by_play` entry now includes the already-existing `Play.formation` and `Play.kick_pass_subfamily`.
8. **Ablation:** `V2_ENGINE_CONFIG["coach_tactics_enabled"]` disables the new OC layer without disabling the old coaching model, for matched comparisons.

**Caps:** preference bias is a proportional ±20% modification to the nonzero candidate weight, not an additive 20-percentage-point jump. The featured player preference is a maximum +18% of the existing weight. Head-coach delegation reduces these further. This avoids repeating the compounding problems documented in `docs/prd_playbook_boost_rebalance_2026_03_18.md`.

## Corrected RNG integrity

The first CCH-02 experiment showed that two *identical-attribute* OCs produced different outcomes even with the new tactical layer switched off. That made the comparison unreliable.

The investigation found two independent reasons:

- `game_engine.py` applied the seed after some pregame archetype/role generation. The seed now applies **before** any pregame player setup when supplied.
- `engine/coaching.py::compute_gameday_modifiers` and `roll_dc_gameplan` create an independently OS-seeded `random.Random()` when no RNG is passed. The engine now supplies persistent **per-side, game-seeded local RNG streams** when `seed` is provided, including halftime rerolls. Unseeded games retain their normal behavior. This change modifies only seeded reproducibility, not tactical rules.

The benchmark now asserts that the two OCs yield an **identical score in every corresponding game** when `coach_tactics_enabled=False`. The corrected CI passes that assertion.

## Full-engine matched-coach benchmark

`scripts/benchmark_coach_tactics.py --games 80 --seed 20261123` tested the same base **Boot Raid** offense and opponent with one offensive roster, the same HC and two OCs with identical inherited attributes and personality sliders. Only the OCs' stored tactical interpretations differed: `vertical_attack` vs `run_to_kick`. They played 80 matched seeded games per coordinator with tactics enabled and the same 80 games again with tactics disabled (**320 games**). The comparison is sensitive to random-stream divergence once coaching preferences change a play, and it is not a confidence-interval or balance claim.

| Observed result | Vertical Attack OC | Run-to-Kick OC |
|---|---:|---:|
| Share of formations that were Spread | 52.83% | 49.28% |
| Share of formations that were Heavy | 4.12% | 4.99% |
| Share of selected play families that were kick passes | 56.33% | 51.08% |
| Share of selected play families that were Power | 3.08% | 3.69% |
| Share of kick-pass subtypes selected as Bomb | 10.16% | 9.65% |
| Share of kick-pass subtypes selected as Quick Kick | 35.50% | 38.82% |
| Points/team with coach tactics on | 76.22 | 71.34 |
| Points/team with coach tactics **off** | **75.94** | **75.94** |

The intended directional difference in Spread, play-family kick passes and Quick Kicks appears. The Bomb preference difference is smaller than other measures in this sample and needs more repetitions or another roster before claiming consistent superiority. Scoring differences are observations, **not** targets, and the underlying base branch has not yet incorporated all of PR #323's engine balance fixes. Do not treat those point totals as the current full league's scoring calibration.

### Testing

- **9 CCH-02 tests passed** (bounded weights, no revival of a zero, HC authority, featured-position eligibility, formation/subtype choices, default neutral behavior, post-override role order, actual full-game counters, and identical seeded ablation control).
- **94 tests passed** across the entire `tests/` suite from this PR's source base.
- CI benchmark succeeded across 320 full-engine games, recorded in `reports/cch02/results.json` GitHub artifact.
- No API front-end interface tests or deployed-site tests have been run. Existing game results carry the new fields for future UI use.

## Known limits and follow-ups

1. **Stacking and merge order:** CCH-02 starts from #327, which starts from main. Separate engine commits in #323, defensive mechanics in #325, and analysis in #326 are not in this branch. Integration is required, with the same targeted tests and benchmark rerun on that merged engine.
2. **Scheme identity:** both tested OCs run Boot Raid, but no new package or play family exists yet. The package-catalog agent should work independently under `PBK-01` and `PBK-02`.
3. **No DC coach-specific decision layer yet:** this remains CCH-03, to be validated against the DEF-06 matrix and future DEF-07 pressure instrumentation.
4. **No new installation/learning curve:** coach changes, inherited playbooks and gradual adoption remain CCH-04.
5. **Role selection:** changing the sequence of `assign_game_roles` prevents stale style input, but the role-selection function itself still needs richer style-dependent criteria; CCH-02's featured-position preference does not replace that future work.
6. **Base engine scoring:** 71–76 points/team in this small, main-based matchup is not a new baseline or authorized tuning goal. Compare only after the #323 game engine improvements land.
7. **Repeated schemes:** OC signature profiles remain persistent; their efficacy depends on the roster. More roster profiles and a second opponent defensive scheme are appropriate follow-up tests.

## Reproduce

```sh
PYTHONHASHSEED=0 python -m pytest tests/test_coach_tactics_gameplay.py -q
PYTHONHASHSEED=0 python -m pytest tests/ -q
PYTHONHASHSEED=0 python scripts/benchmark_coach_tactics.py --games 80 --seed 20261123 --out reports/cch02
```

**Work boundaries:** coach runtime, saved identity and game-day decision adapter belong to CCH-02. The other agent owns `engine/playbook_catalog.py`, `data/playbooks/**`, catalog tests and packages. Integrate through the shared schema in `docs/PRD_COACH_OWNED_SCHEMES_AND_PLAYBOOKS_2026-11-23.md`, which currently lives on documentation PR #324.
