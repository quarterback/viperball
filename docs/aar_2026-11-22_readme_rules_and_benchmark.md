# AAR: README brought up to the current rules; engine benchmark added
## November 22, 2026

## What was asked

Ron: update the README to the current rules instead of asking which rulebook is real, and say
what we do about the scoring numbers that are still off.

## README changes

Each change was checked against the AARs and the engine code:

| Section | Was | Now | Source |
|---|---|---|---|
| Overview | 187-team CVL | 205 teams | `data/teams` |
| Quarters | Four 15-minute quarters | Four 10-minute quarters | `RULES_EVOLUTION_AAR.md`; `GameState.time_remaining = 600` |
| Clock | 3 timeouts per half | 4 per half, plus a 3-minute warning each half | `aar_2026-03-25_timeout_overhaul.md`; `GameState` |
| Coach's Challenge | Absent | 3 per game; spot, turnover on downs, fumble or interception, catch, short TD; penalties not reviewable | `aar_2026-03-27_challenge_system_rework.md` |
| Downs | No automatic punt situation; convert, punt or kick any time | Turnover on downs starts a fresh series; 6th down is the kicking down, with the end of half, bonus possession and garbage time exceptions | `aar_2026-03-18_early_down_snap_kicks.md`; `AAR_garbage_time_and_mismatch_mercy.md` |
| Pindown | Two conflicting definitions (kick not returned out of the end zone; possession starting inside the 10) and a touchback at the 25 in the Punt section | One definition: a punt, missed snap kick or missed field goal into the end zone that isn't returned out; 1 point; receiving team at its own 25 | `_check_rouge_pindown`, `_apply_rouge_pindown` |
| Interceptions | Kick pass only | Kick pass or lateral; Bonus Possession rule added | `simulate_drive` bonus logic |
| Restarts | Own 20 to 35 | Delta Yards: own 20 minus the lead or plus the deficit, between own 1 and opponent's 20; after a safety, own 20 | `kickoff()` |
| Overtime | One possession each from the opponent's 35, no timeouts | Postseason only; regular season ties stand; 8-minute periods, alternating possession, own 20, 4 timeouts, up to five periods | `_simulate_overtime` |
| Glossary | | Bonus Possession and Delta Yards added; Pindown corrected | |

Sections that still match the engine were left in Ron's wording.

## Benchmark added

`scripts/benchmark_engine.py` runs a fixed set of full engine matchups (fixed seeds, each team
on its season assigned schemes) and prints points, touchdowns and kicks per team against the
`RULES_EVOLUTION_AAR.md` targets, plus touchdown rate by drive start, touchdown play length and
6th downs in kick range. Same code, same numbers, so any engine change can be measured.

Baseline at this commit (200 games, seed 2026):

| Per team, per game | Now | Target |
|---|---|---|
| Points | 40.5 | 45 to 50 |
| Touchdowns | 4.2 | 1.9 to 3.5 |
| Snap kicks made | 0.3 | 3 to 5 |
| 6th downs within 45 yards of a kick | 0.65 | |

Touchdown rate by drive start: own 1 to 14, 29%; own 15 to 25, 37%; own 26 to 49, 36%;
opponent's half, 62%. 32% of drives start in the opponent's half. Of those starts, 26% come
from the Delta Yards bonus and about 45% follow a turnover. Median final margin is 32 points,
and 54% of games are decided by 30 or more.

## Correction

An earlier measurement this session reported a touchdown rate of about 50% from every
starting spot and 38% of touchdowns from 30+ yards. That sample loaded teams straight from
their files, which give every team the defense `base_defense`. That name isn't one of the
engine's defenses, so it doesn't reflect real play. The benchmark uses season assigned
schemes and supersedes it.

## Open

The scoring targets were set in February, before kicks moved to 6th down. With about 8 real
possessions per team and at most one 6th down kick per drive, 3 to 5 snap kicks made per team
would need more than half of all drives to stall on 6th down inside kicking range. That fits
neither the touchdown target nor a normal share of turnovers and punts. The next pass lowers
touchdown rate and blowout margins, using the benchmark to measure each change.
