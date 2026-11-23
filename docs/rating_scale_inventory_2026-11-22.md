# Inventory: engine formulas still built for the old 60 to 100 rating scale
## Written November 22, 2026, before any of them were changed

The March 2026 talent rebalance lowered player ratings by about 30 points. On a real
season's rosters, team average ratings now run from 18 to 59 (median 35). The formulas below
still have old scale numbers built in. Line numbers are for `engine/game_engine.py` at
commit `1a55018`.

## A. Who wins each play (the core contest)

| Lines | What it controls | Old scale assumption |
|---|---|---|
| 8810 to 8836 `_get_offensive_rating`, `_get_defensive_rating` | Carrier vs tackler on every run and lateral | Raw ratings go into a ratio, `(carrier / tackler) ** 2.2`. On the old scale a typical mismatch was 87 vs 68 (ratio 1.28). Now it is 50 vs 20. |
| 8940 `max(30.0, ...)` | Floor on both sides of that ratio | Ratings under 30 are treated as 30. A third of the league's players sit below the floor. |
| 9230 to 9300 `_contest_kick_pass_prob` | Kick pass completions | Same ratio and the same floor of 30. |
| 6157 `_late_down_defensive_clamp` | Defensive stops on downs 4 to 6 | Uses the raw point gap between offense and defense; gaps are now much wider. |

## B. Kicking (already fixed today in `1a55018`)

Lines 5692, 5849, 5878, 5980, 6161, 7282, 7283: snap kick and field goal range from
`skill - 60`. Now read through `_kick_skill()`.

## C. Speed, pursuit and breakaways

| Line | What it controls | Assumption |
|---|---|---|
| 8292 | Breakaway chance: `(team.avg_speed - 85) / 100` | Average team speed is 85. Now 34, so every team takes a 0.5 penalty. |
| 8201 | Defensive read bonus: `(avg_score - 75) / 300` | 75 is an average defender. |
| 8746 | Pursuit: `1.0 + (avg_score - 75) / 100` | 75 is baseline. Now cuts pursuit by about 40%. |
| 5078 | Returning a kick out of the end zone: `return_speed / 90` | Team speed near 90. |
| 4166 | Best carrier bonus: `(talent - 60) / 30` | 60 is the floor. Most carriers now get zero. |

## D. Turnovers

| Lines | What it controls | Assumption |
|---|---|---|
| 10093, 10683 | Lateral interception chance from `awareness - 70` and `thrower_skill - 70` | 70 is average. |
| 10650 | Lateral fumble rate from `thrower_skill - 70` | 70 is average. |

## E. Yards after the catch, kick pass distance, returns

| Lines | What it controls | Assumption |
|---|---|---|
| 10440 to 10452 | Kick pass distance bonus from `kick_power - 60/65/70` | Bonus starts at 60 to 70. Most kickers now get none. |
| 10798 to 10810 | Yards after catch from `speed/agility/hands - 60` | Starts at 60. |
| 10732 | Lateral yards from `speed - 60` | Starts at 60. |
| 10120, 11091 | Interception return talent `- 60` | Starts at 60. |
| 11710 | Diving wing block bonus from `tackling - 70`, `speed - 78` | Starts at 70 and 78. |

## F. Prestige (correction to the plan)

The plan said prestige drives most plays. It does not. `_should_use_halo` returns False, so
the prestige based team rating was switched off in March
(`AAR_2026-03-22_keeper_stats_and_game_balance.md`) and every play uses individual ratings.
Prestige still feeds play calling quality, polls and recruiting. `estimate_team_prestige_from_roster`
(`engine/season.py:1124`) maps the average rating straight to prestige, so the median team
is 16 of 99.

So the order of work changes: group A first (it decides every play), then C, D, E, then
prestige.

## How each group will be fixed

One converter, the same one the kick formulas got: `60 + (rating - 15) * 0.5`. A 20 plays as
62, a 35 as 70, a 50 as 78, a 64 as 85. Each group reads ratings through it. Stored ratings
do not change.
