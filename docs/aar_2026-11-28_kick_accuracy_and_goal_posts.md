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

## Checks

`tests/test_kick_accuracy.py` (new), field width, Delta and Clinic playbooks, offensive
concepts, box score ledger and rules doc tests pass. The full suite was not run, at Ron's
request.
