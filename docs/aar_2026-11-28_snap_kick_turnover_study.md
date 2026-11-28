# AAR: study of a turnover on every missed snap kick

November 28, 2026

## What was asked

Ron asked what the data would look like under a rule where a missed snap kick turns the
ball over on any down, compared with today's rule, where a miss on downs 1 through 5 keeps
the ball. He is considering a rule change, or making it optional.

## What changed

Two engine settings, both off by default, so the current rule is unchanged:

* `missed_snap_kick_turnover`: a miss on any down follows today's 6th down logic.
* `missed_snap_kick_turnover_coaches_adapt`: with the rule on, coaches price in the miss
  by wanting a 0.15 surer kick before a 4th or 5th down snap kick.

## Runs

Three weeks of a full season each, same league seed.

| Per game | Current rule | Turnover, coaches unchanged | Turnover, coaches adapt |
|---|---|---|---|
| Games | 269 | 260 | 263 |
| Points | 100.3 | 100.1 | 102.2 |
| Average margin | 19.3 | 19.8 | 19.4 |
| Games within 9 points | 27.9% | 26.5% | 26.6% |
| Touchdowns | 5.52 | 5.42 | 5.61 |
| Snap kick attempts | 7.23 | 7.05 | 6.76 |
| Snap kicks made | 6.27 | 6.12 | 6.00 |
| Accuracy | 86.7% | 86.7% | 88.8% |
| 4th down attempts | 5.12 | 5.18 | 4.64 |
| 5th down attempts | 0.94 | 0.81 | 0.85 |
| 6th down attempts | 0.25 | 0.22 | 0.33 |
| Drives | 25.6 | 25.5 | 26.0 |
| Plays | 167.8 | 167.3 | 169.0 |
| Median play gap between teams | 29 | 27 | 28 |

## Findings

1. Under the current rule only about 0.9 snap kicks per game miss on downs 1 through 5, so
   the free miss is worth little. Coaches kick at 87 percent, mostly from close range.
2. 71 percent of snap kicks come on 4th down. The 4th down kick is the habit the free miss
   supports, and it barely moves under the turnover rule because those kicks are so sure.
3. Points, margins, touchdowns, drives and play counts all stayed within run to run noise
   (about 1.5 points per game). Points by offensive school moved by several points in both
   directions, which is noise at 20 to 60 team games per school.
4. With coaches adapting, 4th down kicks fell about 10 percent, accuracy rose two points and
   more kicks moved to 6th down. Those are the only clear behavior changes.

## Checks

Default behavior is unchanged: both settings are off. Engine import checked. The full
suite was not run, at Ron's request.

## Two test fixes made while merging

1. `test_corner_chase_dispatches_through_the_sixth_down_decision` broke when punting (#413)
   merged. Punting changed the rule: trailing teams are forced to go for it only in the
   fourth quarter, or in the third when down by more than 9. The test trailed by one in the
   first quarter, so it now sets the fourth quarter.
2. `test_playbook_library_team_setup_and_simulated_week` failed about one run in three. The
   season setup drew from an unseeded global random, so the schedule and opponent changed
   between runs, and against some opponents the custom package was eligible but never picked.
   The test now seeds the setup and sorts the team list, so it plays the same game every run.
