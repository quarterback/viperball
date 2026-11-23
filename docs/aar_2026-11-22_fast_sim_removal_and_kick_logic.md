# AAR: Fast sim removed from college seasons, kick and quarter logic fixed
## November 22, 2026

## What was asked

Ron: the fast sim needs to go away, and the AARs already record which rules are current. The
current rule set comes from `RULES_EVOLUTION_AAR.md` (10 minute quarters, 4 timeouts per half,
starting field position of 20 minus the lead, missed kicks retain possession) and the March
AARs, chiefly `aar_2026-03-18_early_down_snap_kicks.md`: kicks belong on 6th down, with
exceptions for the end of a half, bonus possessions and garbage time. The README is the
original rulebook and predates those changes.

## Fast sim removed from the college game

- `engine/season.py`: `simulate_game`, `simulate_week`, `simulate_through_week` and
  `simulate_season` lose the `use_fast_sim` argument and the fast sim branch. Every college
  game (regular season, postseason, dynasty seasons, My Team, DraftyQueenz week advance)
  runs the full engine and gets a full box score and play by play.
- `api/main.py`: the `fast_sim` fields are gone from the sim request models; responses report
  `"engine": "full"`. Older clients that still send `fast_sim` (the NiceGUI app) are
  accepted, and the field is ignored.
- `stats_site/router.py`: its two week sim calls use the full engine.
- React app: the Full engine / Fast sim toggle is removed from the League Hub.
- Not changed: `engine/fast_sim.py` still drives the high school league behind recruiting,
  pro leagues and WVL. Dynasty history generation (`fast_sim_season`) is a separate
  ratings only model that writes the backstory years before a dynasty's first season.

Checked: a 205 team season through the API, one week then Sim Rest: 1,143 remaining games
in 116 seconds locally, zero fast sim games, box scores carry play by play.

## Engine logic fixed

| Problem found | Fix |
|---|---|
| Field goals, punts and retired `territory_kick` punts could still be called on downs 1 to 5. The final down gate zeroed their weights, but the next step floored every family except snap kick and kneel at 0.001. One sample had a 109 yard field goal from a team's own 1 on 3rd down. | Kick families zeroed by the gates stay at zero; `territory_kick` is gated with the rest. |
| Field goal weight had no range gate, so a desperation clock early down call could try a 72 yard kick. | Field goal weight is zeroed beyond 54 yards, matching the snap kick gate at 58. |
| The last play of a half always tried the field goal before considering the snap kick. | It takes whichever viable kick has the higher expected points. |
| The forced last play ran at the end of every quarter, so drives were punted or kicked away at the end of Q1 and Q3 (110 times in 60 games). | It runs only at the end of Q2 and Q4; at the end of Q1 and Q3 the possession, down and distance carry over. |
| Bonus possessions were cleared after every quarter, although the code comment says end of half. | Cleared only after Q2 and Q4. |
| A blocked field goal or punt recovered by the kicking team was a turnover on any down. The README says the ball is dead and the down is consumed, which is what the blocked snap kick already did. | Both now consume a down; turnover only after 6th down. |
| `stats_site` My Team portal referred to `session` where the variable is `sess`, so coaching quality never affected portal interest (every team scored a flat 50). | Uses `sess`. |

## Measured after the fixes

200 matchups, each team with its season assigned scheme, per team per game:

| | Before today | After |
|---|---|---|
| Points | 39.3 | 40.4 |
| Touchdowns | 3.9 | 4.1 |
| Snap kick attempts | 0.3 | 0.5 |
| Field goals made | 0.3 | 0.1 |

80 game kick tally: snap kicks 59 before, 105 after. Plays on 7th down or later: 0.

## Open: drive conversion calibration

51% of all drives now end in a touchdown (80 game sample). Teams rarely reach 6th down, and
when they do inside 45 yards they take the snap kick (38 of 48 calls). So the kick rules now
behave as written, and the low snap kick count comes from offense converting too easily. The
last documented targets (`RULES_EVOLUTION_AAR.md`) are 45 to 50 points per team, 1.9 to 3.5
touchdowns and 3 to 5 snap kicks made. Hitting them means lowering how often drives convert
and score from distance; the kick rules themselves don't need to change.

## Checks

`tests/` passes (72). Turnover on downs check: 0 plays on 7th down or later.
