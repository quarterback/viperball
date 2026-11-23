# AAR: Defensive tactical pathways (DEF-01 / DEF-02 / DEF-03)

**Date:** November 23, 2026  
**Review base:** PR #323, head `ad6551fae1af6c1c9dcfd7ca28602ae935ec9630` at branch creation  
**Implementation branch:** `fix/defensive-tactics-def-01-02-03`  
**Status:** Implementation committed; full-engine and season benchmark **not run here**.

## Purpose

Connect previously disconnected defensive mechanics so schemes matter to specific
plays, not only the final score. Correct the calculation that could reverse a
formation matchup when the coordinator correctly identified the formation.

This work does not introduce new defenses or change the official rules. It is
a deliberately bounded integration step; it is not final statistical tuning.

## Confirmed gaps at the reviewed code

1. `get_defensive_read(play_family)` was defined but called nowhere in the
   full game engine. Trick plays used their own, narrower read roll.
2. `OFFENSE_VS_DEFENSE_MATCHUP` had 128 values (all 16 current offenses × all
   eight defenses) but no runtime lookup.
3. `DEFENSE_STYLES[*].play_family_modifiers`,
   `explosive_suppression`, and `kick_pass_coverage` had no runtime lookups.
4. `_formation_defense_multiplier()` calculated a successful read as
   `1 + (1 - base) * 0.5`. For a defense advantage (0.85) this became
   1.075: the play reversed into an offensive advantage.

## Changes

### DEF-03: Correct formation recognition

A successful formation read now returns `1 + (base - 1) * 0.5`:
an offense advantage of 1.10 becomes 1.05, a defense advantage of 0.85
becomes 0.925, and neutral remains 1.0. An unsuccessful read uses the
unmodified formation matchup. Tests assert direction and magnitude.

### DEF-01: General defensive reads on actual plays

The full engine now calls the common defensive read function on:
- Run-family contests: successful read reduces positive yardage-center
  by 10% (within the existing floor).
- Lateral chains: successful read reduces their positive yards by 10%.
- Kick passes: successful read reduces the completion chance by 10%.
- Trick plays: the existing trick-play disaster on successful read now
  uses the common read pathway, including personnel, situational and
  coaching effects. Its former separate roll was removed.

Counts of attempts and successful reads are available in game results as
`defensive_reads.home/away.{attempts,reads}`, keyed by the **defending** team.
This gives future benchmark and reporting work something testable. The read
effect is gated by `V2_ENGINE_CONFIG["defensive_reads_enabled"]` for
paired-on/off comparisons.

The prior film-study suppression, Solved Puzzle, per-surface personnel
selection, and late-down clamp remain in place. Their effects should be
measured with the new read layer; do not treat all suppression as the same.

### DEF-02: Connect declared scheme matchup and suppression values

The new `_defense_style_multiplier(play_family)` uses both:
- offense × defense matrix: 50% of its deviation from neutral; and
- defense × play-family modifier: 35% of its deviation from neutral.

Deviations are added rather than multiplying both full factors, then
bounded to `[0.75, 1.20]`. This is applied **once per play**:
run contest yardage, lateral yardage, trick yardage (if not read), or
kick-pass completion probability. There is no additional run-style
multiplier applied to kick-lateral yardage.

The scheme's `kick_pass_coverage` now reduces kick-pass completion by
0.25 times its configured value (so 0.22 removes 5.5 percentage points).
Its `explosive_suppression` scales the existing breakaway **chance**,
without directly altering the yards of every successful run.

The independent switch `defense_scheme_effects_enabled` allows an
ablation that preserves baseline play mechanics. Unused `gap_breakdown_bonus`
entries and obsolete `territory_kick` values were removed from the eight
scheme definitions; neither had an active scheme resolution pathway.
All existing player-based coverage/tackling, blitz/rush, fumble pressure
and special teams code remains active.

## Field audit at this step

| Defensive scheme field | Observed usage after this change |
|---|---|
| play_family_modifiers | **Now active** via one bounded play matchup effect for current run, lateral, trick and kick-pass families; retired territory_kick entries removed |
| read_success_rate, gameplan_bias, situational, personnel_weights | **Now active for ordinary run, lateral and kick-pass reads** as well as trick plays |
| kick_pass_coverage | **Now active** via bounded completion probability adjustment |
| explosive_suppression | **Now active** via breakaway chance |
| pressure_factor, turnover_bonus | Already active in fumble recovery |
| fatigue_resistance | Already active in defensive fatigue factor |
| kick_suppression | Already active in punt distance |
| pindown_defense | Already active in return-out chance |
| gameplan_bias / adaptation and coordinator film study | Previously active in other channels; the common read applies a different, recorded stage |
| gap_breakdown_bonus | **Removed** from all eight schemes; declaration-only configuration had no resolution pathway |
| defensive read counters | Newly emitted in full game results |

This is not a claim that every declared field should be connected by
simply multiplying results again. Retired gap-breakdown and territory-kick
configuration was removed instead of applying extra penalties.

## Validation

**Added unit tests:** `tests/test_defensive_tactics.py`.

The tests cover formation read direction for defense-favoring and
offense-favoring matchups, matrix/scheme tradeoffs, the read counter
and defending side, switchable read/scheme ablations, and
explosive-play defense direction. The matrix was also statically checked
and contains all 128 offense × defense combinations.

**Not executed here:** Python test suite, full-engine games, season
benchmarks, and deployed app. The environment used for the GitHub
change cannot clone the repository or execute GitHub Actions.
The tests must run in CI or a checkout. Do not report them as passing
until run.

Suggested next commands after base #323 is available locally:

```sh
python -m pytest tests/test_defensive_tactics.py -q
python -m pytest tests/ -q
python scripts/benchmark_engine.py --help
```

Then run the benchmark against the same fresh rosters, opponent schemes,
and paired seeds with switches on/off. Record for each scheme: yards by
play family, kick-pass completion, explosive plays, stops, bells,
points by type, total scoring, and confidence intervals. Expect some
scoring mix change; do not silently retune other coefficients to
restore a predetermined points or margin distribution.

## Risks and follow-up

- Multiple established defensive layers still stack (coverage/personnel,
  coordinator prep, late-down clamp, form, scheme, reads). The new terms
  are bounded but season-scale effect is **unknown** until benchmarked.
- Removing unused config keys does not by itself verify every external consumer;
  compatibility must be checked when the full suite runs.
- Defense reads are recorded per team in the game payload but not yet
  exposed in React game reports. That display belongs to UI-01.
- DEF-04 (real lineup effects), DEF-05 (old five-style
  `choose_defensive_call()`), and DEF-06 (full matchup benchmark)
  remain separate work items. Do not mark those done based on this PR.
- After #323 and this branch merge, update the agent queue
  `docs/ASSESSMENT_PRD_ENGINE_TACTICS_2026-11-23.md` and link the
  merged implementation PR.
