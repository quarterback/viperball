# Report: kicking becomes the counterweight to offense

November 28, 2026

## The change

Snap kicks are now Viperball's three pointer. Field goals are a real scoring choice, with
the accuracy of college football plus the lift of wider posts. The goal posts are Gaelic
football H posts. Together with the punting rework (punting skill, punt types and coaching
philosophies), this is a change in what the sport rewards.

## Why

Ron's position, built from months of his own data and research on the sport, is that snap
kicks were too easy and field goals too rare. A snap kick worth 5 points that went in nearly
nine times in ten was a near sure thing from most of the field. Every drive that crossed
midfield could expect points. Defenses had little to play for once the offense reached kick
range. Field goals barely existed because the snap kick was better almost everywhere, and
punting meant little because field position was cheap when any decent drive ended in a kick.

The design aim is a sport where offense has a counterweight. A kick should be a shot with a
real chance to miss, the way a three pointer is. A miss should give the defense something:
a stop, a down taken away, a turnover on 6th down or a ball to field and return. A coach
should have to choose between the 5 point shot, the surer 3 and going for it, and the
choice should change with the down, because a miss on downs 1 to 5 costs a down while a
miss on 6th down costs the ball.

## What the engine does now

1. **Snap kicks.** A typical starting kicker makes about 42 percent from inside 15 yards.
   Each 5 yards farther costs about 3.5 points at first, rising to about 7 at long range.
   Elite kickers fall off much more slowly: a 95 kicker makes about 44 percent from 35
   yards. A kick can miss off the boot, from the weather, from the rush, or from more than
   one of these.
2. **Field goals.** Accuracy starts from college rates by distance through college posts,
   then gets the Gaelic posts' lift.
3. **Goal posts.** Uprights 6.5 meters (21 feet 4 inches) apart, a 2.5 meter (8 feet 2 inch)
   crossbar and uprights at least 7 meters tall. Compared with college posts, the uprights
   are 2 feet 10 inches wider and the bar is 1 foot 10 inches lower. The engine treats a miss
   as either wide or short. The wider uprights catch some wide misses, and the lower bar
   catches some short ones. The lift grows with distance:

   | Field goal, typical starter | College posts | Viperball posts |
   |---|---|---|
   | 25 yards | 95% | 97% |
   | 35 yards | 87% | 92% |
   | 45 yards | 72% | 79% |
   | 55 yards | 49% | 58% |
   | 65 yards | 24% | 32% |

   Snap kicks get the same treatment, with more of their misses counted as short because
   a kick off the bounce flies lower. The snap kick curve is set so the result through
   Viperball's posts is still about one in three.
4. **Coaches** scale their snap kick bars to the new accuracy. They shoot on 4th and 5th
   down, when a miss only costs a down, and usually take the field goal on 6th down.
5. **Punting** (separate AAR) gives punting a trained skill, five punt types and a coaching
   philosophy from "never punts" to "field position first".

## Before and after, per game

| | Before the kicking changes | Now |
|---|---|---|
| Points | 99 to 104 | 87 |
| Snap kick attempts | 7.2 | 5.0 |
| Snap kick accuracy | 87% | 37% to 39% |
| Field goal attempts | rare | 5.2 |
| Field goal accuracy | | 71% |
| Touchdowns | 5.2 to 5.7 | 6.6 |
| Snap kick misses | about 1 | about 3 |

"Before" comes from the snap kick misses AAR (old model) and the punting AAR. "Now" is
three weeks of a season, about 270 games, on this branch.

Accuracy by distance on actual attempts now, across two runs of about 270 games each:

| | 20s | 30s | 40s | 50s | 60s |
|---|---|---|---|---|---|
| Snap kicks | 42% to 44% | 39% to 42% | 30% to 35% | 32% to 34% | few tries |
| Field goals | 93% to 94% | 89% to 90% | 80% to 83% | 66% to 70% | 47% to 53% |

Snap kicks taken run above the typical starter's curve because better kickers take more of
the shots.

## What a drive is worth by where it starts (points per drive, now)

| Start | Own 0 to 9 | Own 10s | Own 20s | Own 30s | Own 40s | Opp 40s | Opp 30s | Opp 20s | Opp 20 and in |
|---|---|---|---|---|---|---|---|---|---|
| Points | 2.9 | 3.1 | 3.5 | 3.3 | 3.5 | 3.3 | 4.1 | 4.6 | 6.5 |

The punting AAR measured about 2.5 points from your own 5 and 3.5 from your own 45 under
the old kick model. The spread between your own goal line and midfield is still only about
half a point. Most of the counterweight so far shows up in fewer points and more missed
kicks. Field position has not yet become much more valuable, because offenses now score
more touchdowns (6.6 a game, up from about 5.5) when they stop settling for the kick.

## Settings

`snap_kick_point_blank`, `snap_kick_drop_near`, `snap_kick_drop_far`,
`kick_reference_skill`, `snap_kick_bar_scale`, `gaelic_posts` (set it to false to kick
through college posts).
