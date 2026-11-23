# AAR: Turnover on downs carryover fix, and an engine audit against the README
## November 22, 2026

## What was asked

Ron came back to the game after five months and wanted to sim college seasons again, and
asked whether the code could be made more logical, measured against the README rulebook.

## Method

The API and engines were run locally, outside the browser:

- Two fast sim and full engine samples of the same matchups (150 and 200 games) drawn from a
  real 205 team CVL season. In the 200 game run, each team carried the scheme the season
  assigned it, passed in the way `Season` passes it.
- Play by play tallies from 60 full engine games (play types, results, downs reached).
- An 80 game check of every turnover on downs and the play that follows it.

## Bug fixed: the down counter carried over after a turnover on downs

When a team failed on 6th down, the play code flipped possession and field position but never
reset the down. The new offense's first snap was logged as 7th down with the old offense's
yards to go, and the 6 down limit (`down > 6`) applied to it immediately. So unless that one
play gained the stale distance, the ball went straight back.

| 80 full engine games | Before | After |
|---|---|---|
| Turnovers on downs | 68 | 56 |
| New possession started on 7th down or later | 51 | 0 |
| New possession turned it back after one play | 16 | 0 |
| Plays logged on downs 7 to 11 | 131 in 60 games | 0 |

**Fix:** `simulate_drive` now sets 1st and 20 when a drive ends in `turnover_on_downs`, next
to the existing reset after a safety. The reset sits at the end of the drive and stays out of
the start of `simulate_drive`, because that function also continues the same possession
after a quarter break or a drive play cap, where the down must carry over.

The `tests/` suite passes (72). `test_season.py` at the repo root fails before simming
because it loads `data/teams/xavier.json`, which no longer exists.

## Findings left for Ron to decide (no code changed)

### The fast sim and the full engine simulate different sports

Same 200 matchups, per team per game:

| | Full engine | Fast sim | README |
|---|---|---|---|
| Points | 39.3 | 35.6 | 45 to 70 typical |
| Touchdowns | 3.9 | 0.4 | 3 in its sample game |
| Snap kicks made | 0.2 | 5.0 | 4 in its sample game |
| Snap kick attempts | 0.3 | 6.0 | 6 to 8 for a kicking ZB |
| Field goals made | 0.3 | 1.7 | 2 |
| Plays | 70 | 100 | |
| Team scores inside 45 to 70 | 35% | 18% | |

The fast sim is the League Hub's default. Other gaps:

- **Schemes are ignored.** The fast sim reads `team.offense_style` and `team.defense_style`,
  which stay at the team file defaults (`balanced` for 199 of 205 teams, `base_defense` for
  all). A season's assigned schemes live in `Season.style_configs`, which only the full
  engine reads. The fast sim's own tables also use names that don't exist in the engine
  (`air_raid`, `smashmouth`, `west_coast`, `bend_no_break`); only `balanced`,
  `ground_pound` and `swarm` overlap.
- **Pindown value differs.** The fast sim scores a pindown as 0.5 points; the full engine and
  the README score it as 1.
- **Speed no longer justifies it.** The full engine ran 200 games in about 10 seconds. A
  whole 1,230 game regular season took about 47 seconds through Sim Rest.

### Snap kicks have nearly disappeared from the full engine

`docs/aar_2026-02-24.md` measured 3.9 snap kick attempts per game and 64.0 points per team.
The full engine now produces about 0.3 attempts per team per game and 39 points. Boot Raid,
the scheme the README describes as built on snap kicks, averaged 0.47 to 0.92 attempts across
the two samples. The March fixes that gated kicks to downs 4 through 6 and moved kicking to
6th down (`aar_2026-03-16_repeating_downs_early_kicks.md`,
`aar_2026-03-18_early_down_snap_kicks.md`) are the likely cause and were not re-measured
against the February baseline.

### The rulebooks disagree with each other and with the engine

- Three rulebooks exist: `README.md`, `RULES.md` (v1.1, with a kickoff section) and
  `docs/RULES.md`. The README says there are no kickoffs.
- The README defines a pindown two ways: a kick into the end zone that isn't returned (the
  scoring table) and a possession that starts inside the 10 (the Pindown section and
  glossary). Its Punt section also says an unfielded punt into the end zone is a touchback at
  the 25, which the scoring table's rule would score as a pindown.
- README: four 15 minute quarters and 3 timeouts per half. Engine: 600 second quarters and 4
  timeouts per half.
- README: a 187 team CVL. Data: 205 team files.
- Delta Yards and the bonus possession after an interception are central engine mechanics
  that the README never mentions.

## Lesson

Tuning passes in March changed kick behavior without rerunning the February validation
table. A fixed benchmark (points, scoring mix, attempts by scheme, downs reached) run after
every engine change would have caught both the snap kick collapse and the 7th down carryover.
