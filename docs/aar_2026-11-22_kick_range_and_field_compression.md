# AAR: Why snap kicks vanished, and the fix
## November 22, 2026

## What was asked

Ron: work on what's next, which was getting drives to stall inside kicking range so teams
trade snap kicks.

## Root cause found

The kick range formulas were written when kickers were rated 60 to 100. The March talent
rebalance (`feature_report_talent_generation_rebalance_2026_03_27.md`) lowered every rating
by about 30 points. Nobody rescaled the kick formulas. On the rosters a real season
generates:

| Team's best kicker | Rating | Comfortable snap kick range |
|---|---|---|
| Bottom 10% of teams | 25 | 4 yards (cannot make any kick) |
| Median team | 51 | 23 yards (ball at the opponent's 13) |
| Top 10% | 85 | 49 yards |

Earlier measurements this session missed it because they loaded the saved team files, whose
kickers are still on the old scale (median 84). Real seasons load teams with `fresh=True`,
which generates new rosters.

## Changes (`engine/game_engine.py`)

| Change | Detail |
|---|---|
| Kick skill rescale | `_kick_skill()` maps the current rating scale onto the one the formulas expect: `60 + (rating - 15) * 0.5`. A 25 kicker plays as 65, 51 as 78, 85 as 95. Median comfortable range becomes about 43 yards. Config: `kick_skill_rescale`. |
| Field goal range | The place kick's comfortable range now sits 8 yards beyond the snap kick's, as the README says. It was shorter, so a field goal was never the better choice. |
| Goal line | A play ending at the 1 to 5 no longer gets a 20 to 55% bonus touchdown without crossing the line. Config: `goal_line_bonus_td` (now False). Before this, 62.5% of plays inside the 10 were touchdowns. |
| Field compression | Gains shrink as the offense nears the goal line: full yardage at midfield side of the opponent's 40, down to 75% at the goal line. Config: `field_compression` (0.25). |
| 5th down kick | Taken at 55% or better, without the extra comfort zone limit. |
| 6th down kick | Any snap kick at 40% or better is an option. In the red zone on 6th down, teams kick unless the goal line is within 3 yards. |

## Measured (benchmark, 200 games, real season rosters and schemes)

| Per team, per game | Start of day | Now | Target |
|---|---|---|---|
| Points | 40.5 | 39.9 | 45 to 50 |
| Touchdowns | 4.2 | 3.0 | 1.9 to 3.5 |
| Snap kicks made | 0.3 | 2.1 | 3 to 5 |
| Field goals made | 0.06 | 0.14 | |

Touchdown rate by drive start is now 23 to 26% from a team's own half and 45% from the
opponent's half. Tests pass (72). No plays on 7th down or later.

## Tried and not kept

- `power_ratio_exponent` (2.2 down to 1.2) and `base_yards_multiplier` (2.3 down to 1.6, up
  to 3.2): small effects on kicks and none on margins. Left unchanged.
- Field compression at 0.4 to 0.7: more kicks (up to 2.3) but points fell to 31 to 37.

## Still open

- Points are 5 below target and snap kicks 1 below. Field goals are still rare.
- Blowouts: evenly matched teams (roster rating gap under 2) have a median margin of 14.5 and
  11% of games decided by 30+. Teams 5+ apart have a median margin of 31. Roster averages
  run from 18 to 59 across the league, a wider spread than the engine's formulas handle
  well. Other formulas written for the 60 to 100 scale (the prestige halo table, where the
  median team's prestige is now 16) likely need the same rescale the kick formulas got.
