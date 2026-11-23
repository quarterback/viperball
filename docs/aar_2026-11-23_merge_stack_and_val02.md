# AAR: Merging the stack, reconciling CCH-02, and repeatable runs (VAL-02)
## November 23, 2026

## What Ron asked

Merge the open stack in order, then do the reconciliation work.

## Merges into main

| Order | PR | What | Merge commit |
|---|---|---|---|
| 1 | #323 | Engine and app reboot (fast sim out, rules, rosters, game day, rotations, lines) | 1014393c |
| 2 | #325 | DEF-01/02/03 defensive reads and scheme matchups (base moved to main first) | f98c6a14 |
| 3 | #326 | DEF-06 defense matrix study (base moved to main first) | 3664a6ff |
| 4 | #324 | Assessment work queue and the coach and playbook plan | 7b70f4c5 |
| 5 | #330 | PBK-01/02/04 playbook catalog (tested against the merged engine first: 114 pass) | 544f0b7f |
| 6 | #327 | CCH-01 coach tactical identities (tested merged first: 127 pass) | 63663e14 |
| 7 | #328 | CCH-02 coach game day tactics, after reconciliation | a3c3c5ef |

#329 (the playbook prototype) stays an open draft, now based on main, as a reference for
the COACH track.

## Reconciling #328

#328 was built on the old main, so it had to be merged with #323 and #325.

- One conflict, in `V2_ENGINE_CONFIG`: both sides added switches (`coach_tactics_enabled`;
  `defensive_reads_enabled`, `defense_scheme_effects_enabled`). Kept all three.
- Checked each auto-merged #328 change against the merged engine: one `random.seed` at the
  top of `__init__` (before the game day form and travel rolls from #323); game role
  assignment moved after the final style overrides (ROST-02), with the old pre-override
  call gone; coordinator biases on formation, play family, kick pass and carrier choice;
  per side coaching random streams; `coach_tactics` in results.
- 136 tests passed and all six CI checks passed on the reconciled branch. The CCH-02
  matched benchmark runs on the merged engine: two Boot Raid coordinators split Spread
  52% and 48%, Heavy 4% and 5%, bombs 9.5% and 7.3% of kick passes.

## What reconciliation turned up: runs did not repeat

With no coaching staff, the coach tactics switch should change nothing, but the benchmark
moved (53.98 points with it on, 53.42 off). Two identical runs also differed. Tracing the
first random draw whose inputs differed led back to the rosters: core ratings matched across
processes, but every player's chemistry traits (reach, pull, glue, voice, fit, drama) did
not. `generate_chemistry_attributes` rolled from `random.Random()` with no seed whenever no
stream was passed, and roster generation never passed one. Chemistry feeds the game, so no
two processes played the same games.

The search also found 22 seeds built on Python's `hash()`, which changes every time Python
starts, and a set turned into a list in the name generator (`list(DOMESTIC_KEYS)`), which
changed the order of recruiting regions with the hash seed.

## VAL-02 fix

- `engine/stable_hash.py`: `stable_hash(value)`, a crc32 of the string, the same in every
  process.
- Chemistry at creation is seeded from the player's identity (ID, name, position, number):
  the same player always gets the same chemistry. The season end range shift uses the
  season's seeded random stream.
- `hash()` replaced with `stable_hash` in AI scheme seeds, schedule home and away
  alternation, the referee pool, dynasty history, recruiting, the pro league, DraftyQueenz,
  injury seeds, My Team portal and retention rolls, and the face, banner, stadium and
  referee art pickers (a player's face could change on restart).
- Team file loading sorted in `load_teams_from_directory`, `load_teams_with_states`,
  `load_coaching_staffs_from_directory` and the dynasty loader.
- `scripts/generate_names.py`: `sorted(DOMESTIC_KEYS)`.

Not changed: the unseeded `random.Random()` defaults in `engine/coaching.py`,
`coaching_portal.py` and `bourse.py` (coach generation and markets). Those files belong to
the COACH track; handed off in the PR.

## Checks

- Rosters, scheme assignments and a full game are identical under PYTHONHASHSEED 1, 2, 3
  and 7.
- The 60 game benchmark run twice unpinned, plus once with coach tactics off: byte for byte
  identical output.
- A season's first week through the API under two hash seeds: the same 92 results and the
  same scheme assignments.
- New `tests/test_reproducibility.py` runs games in three separate processes with different
  hash seeds. 139 tests pass.

## Numbers on main after everything

Benchmark, 300 games: 53.0 points, 2.71 touchdowns, 3.31 snap kicks, 2.20 field goals per
team, 91 plays, median margin 20.5.

Full season, seed 2026, 1,231 games: 54.3 points per team, home 48.8%, lower prestige wins
37.9%, median margin 20.5, 30 point margins 24%.
