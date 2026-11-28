# AAR: snap kicks miss for three reasons

November 28, 2026

## What was asked

Ron wants snap kicks to be less accurate, so the defense gets more chances. Some misses
should just be misses, some should come from the weather (wind and rain), some from
defensive pressure, and some from more than one of those at once. He asked to land this
for review without further tuning.

## What changed

1. A snap kick now rolls three separate miss chances. Any one failing misses the kick, and
   more than one can fail together.
   * Execution: the kicker's own strike. The range curve is lower: 92 percent point blank
     (was 98), about 90 at 15 yards down to 74 at the edge of comfortable range (was 96 to
     86). Skill, style and archetype bonuses still apply.
   * Weather: rain and snow, crosswind over 5 mph and a headwind over 5 mph; a tailwind
     helps a little. Longer kicks feel it more. This replaces the old weather multiplier on
     snap kicks.
   * Pressure: a 3 percent base, more against kick rush defenses, a blitz, extra rushers and
     the Delta kick pressure packages.
2. A pressured miss comes off low and short, so it is 30 points more likely to be a live
   ball the defense can field and return.
3. Coaches' kick decisions use the expected chance from all three, so they kick a little
   less into weather and kick rush defenses.
4. Each miss is tagged on the play (`kick_miss`) and in the play text, such as "[missed:
   the rush]". Team stats count misses by cause, and the college box score lists them under
   Drop Kicks.
5. Settings: `snap_kick_point_blank`, `snap_kick_range_edge`, `snap_kick_base_pressure` and
   `snap_kick_pressured_live`.
6. Fix found on the way: the play record had lost its `script` field when the option read
   and opening script PRs merged. It is back.

## Three weeks of a full season, old model against new

| Per game | Old | New |
|---|---|---|
| Points | 98.9 | 99.7 |
| Average margin | 20.0 | 18.3 |
| Touchdowns | 5.23 | 5.65 |
| Snap kick attempts | 7.19 | 6.76 |
| Snap kicks made | 6.23 | 5.32 |
| Accuracy | 86.6% | 78.6% |
| Misses fielded by the defense | 0.01 | 0.09 |

Misses per game in the new model: 0.70 off the boot, 0.26 from the rush, 0.09 from weather
and 0.03 with more than one cause. Weather misses are rare because most games are played in
clear conditions. 4th down still draws 4.6 of the 6.8 attempts per game.

## Merge with field width

This branch merged after field width (#409). The kicker's strike is now multiplied by the
angle from the hash (`_kick_angle`) in both the expected value the coach uses and the live
execution roll, before the weather and pressure rolls. The three week numbers above were
measured before that merge.

## Checks

Box score ledger and opening script tests pass. The full suite was not run, at Ron's
request. No further tuning, at Ron's request.
