# AAR: snap kicks as three pointers, field goals at college rates, Gaelic goal posts

November 28, 2026

## What was asked

Ron wants a snap kick to be about as successful as a three pointer in basketball, with
accuracy dropping 3 to 7 percent per step of distance, more at longer range. Elite kickers
should still hit theirs. Field goals should follow real world rates. Coaches should still
attempt snap kicks, weighing whether a miss costs a down or the ball. He also asked to settle
the goal posts and their measurements.

## What changed

1. Goal posts (README, The Field). Gaelic football H posts on the end line: uprights 6.5
   meters (21 feet 4 inches) apart, crossbar 2.5 meters (8 feet 2 inches) high, uprights at
   least 7 meters tall. A kick scores between the uprights and over the bar. Nothing scores
   under the bar. The engine does not yet use the wider posts to change accuracy; the curves
   below were set to the target rates directly.
2. Snap kick curve (`_drop_kick_success_base`). A typical starting kicker makes 42 percent
   inside 15 yards. Each 5 yards costs 3 points at first, rising to 7 points by 55 yards. A
   better kicker plays the kick as if it were shorter and is surer close in. Settings:
   `snap_kick_point_blank`, `snap_kick_drop_near`, `snap_kick_drop_far`.
3. Field goal curve (`_place_kick_success_base`). Follows college rates: about 95 percent in
   the 20s, 87 in the 30s, 72 in the 40s, about half in the 50s for a typical starter.
4. `kick_reference_skill` is 80, because the best kicker on each team averages about 81 on
   the kick range scale. Both curves are set for that kicker.
5. Coaches' snap kick bars are scaled by `snap_kick_bar_scale` (0.40). The old bars assumed a
   snap kick went in about 85 percent of the time. On 4th and 5th down a miss only costs a
   down, so coaches still take the shot; on 6th down the surer field goal usually wins.
6. Merged main into the snap kick misses branch (#412). Main's 6th down kick rush rule now
   lives in the pressure miss chance: the rush counts 0.10 per point of kick rush on 6th down
   and 0.04 on other downs. The hash angle from main applies to snap kicks too.

## Three weeks of a season, per game

| | #412 (misses) | This change |
|---|---|---|
| Points | 99.7 | 88.4 |
| Touchdowns | 5.65 | 6.83 |
| Snap kick attempts | 6.76 | 4.93 |
| Snap kicks made | 5.32 | 1.78 |
| Snap kick accuracy | 78.6% | 36.1% |
| Field goal attempts | | 5.24 |
| Field goal accuracy | | 65.5% |
| Misses fielded by the defense | 0.09 | 0.07 |

Snap kick accuracy by distance on attempts: 46 percent from 10 to 19 yards, 38 in the 20s,
38 in the 30s, 36 in the 40s, 25 in the 50s. These run higher than the typical starter's
curve because better kickers take more of the shots.

Field goal accuracy by distance on attempts: 91 percent in the 20s, 84 in the 30s, 76 in the
40s, 63 in the 50s, 36 in the 60s.

Attempts by down: 4th down 2.64 at 36 percent, 5th down 1.37 at 34 percent, 6th down 0.40.

## Open

Scoring fell about 11 points a game and field goals now outnumber snap kicks. About 220 field
goals from 60 yards or more were tried in 270 games; coaches choose them on 6th down over a
long snap kick or a punt. Not tuned further, at Ron's request to see it first.

## Merged after punting, the turnover study and snap kick misses

This branch merged after #411, #412 and #413. Two things came along. The coaches' snap kick
bars on 4th and 5th down now add the turnover study's margin on top of
`snap_kick_bar_scale`; the margin is zero while the study rule is off. The live snap kick
roll now also takes the angle from the hash, which the coaches' expected value already used.

A quick check of 80 exhibition games between random teams (same seeds on both builds):

| Per game | This branch alone | After the merges |
|---|---|---|
| Snap kick attempts | 4.41 | 5.09 |
| Snap kick accuracy | 36.8% | 40.0% |
| Field goal attempts | 5.05 | 3.81 |
| Field goal accuracy | 73.3% | 77.4% |

Punting (#413) now competes on 6th down, so fewer long field goals are tried and the kicks
that remain are shorter. Eighty games is a small sample, about 2.5 points either way on snap
kick accuracy. Not tuned.

## Checks

`tests/test_kick_accuracy.py` (new), field width, Delta and Clinic playbooks, offensive
concepts, box score ledger and rules doc tests pass. The full suite was not run, at Ron's
request.

## Follow up: the posts change accuracy (November 28)

Ron asked for the wider posts to change accuracy in the engine.

1. `field_width.goal_post_factor` turns a kick's chance through college posts into its
   chance through Viperball's posts. A miss is either wide or short. The wide part comes
   from a sideways spread that grows with distance, and the 21 foot 4 inch uprights catch
   more of it than college's 18 foot 6 inch ones. The short part falls with the 8 foot 2
   inch crossbar against college's 10 feet. Place kicks are rarely short inside 35 yards
   and often short past 60. Snap kicks fly lower off the bounce, so more of their misses
   are short.
2. Field goals: the college curve is now `_place_kick_college`, and
   `_place_kick_success_base` adds the posts. A typical starter goes from 87 to 92 percent
   at 35 yards and from 49 to 58 at 55.
3. Snap kicks: the posts add about 6 points, so `snap_kick_point_blank` went from 0.42 to
   0.36 and `snap_kick_drop_far` from 0.014 to 0.0128. Through Viperball's posts a typical
   starter still makes about 42 percent inside 15 yards, losing 3.5 to 7 points per 5 yards.
4. `gaelic_posts` (default true) turns the posts off for comparison.
5. Report on why the kicking changed: `report_2026-11-28_kicking_counterweight.md`.
6. Rulebook (RULES.md) brought in line with the README: Gaelic post dimensions, snap kick
   and field goal accuracy tables, the three miss causes, pressured misses being fielded
   more often, and teams taking the field goal on 6th down. The README also gained the
   pressured miss rule and the 6th down field goal line.

Three weeks, main against this change (about 270 games each):

| Per game | Main | Gaelic posts |
|---|---|---|
| Points | 87.6 | 86.7 to 87.6 |
| Snap kick attempts | 5.19 | 4.81 to 5.03 |
| Snap kick accuracy | 36.6% | 37.4% to 39.2% |
| Field goal attempts | 4.20 | 5.05 to 5.17 |
| Field goal accuracy | 68.3% | 70.7% to 71.2% |

Checks: `tests/test_kick_accuracy.py` (a new posts test), field width and rules doc tests
pass. The full suite was not run.
