# Report: a counterweight to offense

November 28, 2026

## The change

For months Ron tracked his own season data and research and came to one conclusion: snap
kicks were too easy and field goals were too rare. A team that reached midfield could count
on 5 points, so field position, defense and the punt barely mattered. Four pieces of work
merged on November 28 change that.

1. **Snap kicks are the three pointer** (#414). A typical starting kicker makes about 42
   percent from close in, and accuracy falls 3 to 7 points for every 5 yards. Elite kickers
   still hit from range.
2. **Snap kicks miss for three reasons** (#412). The strike off the boot, the weather and the
   pass rush each roll on their own, and the angle from a hash narrows the target.
3. **Field goals follow college rates** (#414). About 95 percent in the 20s down to about half
   in the 50s, kicked at Gaelic H posts.
4. **Punting is a skill and a philosophy** (#413). Punters are trained players with their own
   styles, head coaches range from never punts to field position first, and the 6th down
   choice weighs a punt against going for it and kicking.

Taken together, the sport now has a counterweight to offense. A drive into range no longer
ends in automatic points, the 6th down decision has three live answers, and the punt has a
reason to exist.

## Before and after

200 engine games between the same randomly drawn pairs of teams, with the same seeds. Before
is main just ahead of these four changes (commit 44a8f35, with field width and the Seagull).
After is main with all four (commit ded034c). Figures are per game, both teams together.

| Per game | Before | After |
|---|---|---|
| Points | 106.1 | 85.4 |
| Touchdowns | 5.44 | 6.26 |
| Snap kick attempts | 7.34 | 5.56 |
| Snap kicks made | 6.59 | 2.13 |
| Snap kick accuracy | 89.8% | 38.2% |
| Field goal attempts | 4.69 | 4.28 |
| Field goals made | 3.79 | 2.99 |
| Field goal accuracy | 80.9% | 69.9% |
| Share of points from kicks | 41.8% | 22.9% |
| Share of points from touchdowns | 46.1% | 65.9% |
| Drives | 26.5 | 22.1 |
| Drives that score | 64.3% | 55.4% |
| 6th down: go for it | 1.30 | 2.09 |
| 6th down: kick | 0.89 | 1.50 |
| 6th down: punt | 0.95 | 1.06 |
| All punts | 1.64 | 1.27 |
| Pindowns | 0.11 | 0.14 |
| Average margin | 19.0 | 20.5 |
| Games decided by 9 or fewer | 25% | 24% |

## What the numbers show

**Offense has to earn its points.** Scoring fell by about a fifth, and the share of drives
that score fell from about two in three to a little over half. Touchdowns went up even as
points went down, because drives that once stopped for a near certain 5 now push on for 9.
Touchdowns carry two thirds of the scoring, up from under half.

**Field goals now outnumber made snap kicks.** Before, a team made almost two snap kicks for
every field goal. After, field goals make up 58 percent of made kicks. In raw count, field
goal attempts did not rise; they held about level while snap kicks collapsed around them.

**6th down is a real decision.** Before, coaches split 6th down about evenly among going for
it, kicking and punting, with few of each. After, every answer is used more often, and going
for it leads.

**Against the calibration targets set in February 2026**, per team per game:

| Per team | Target | Before | After |
|---|---|---|---|
| Touchdowns | 3 to 5 | 2.7 | 3.1 |
| Snap kicks made | 0.5 to 1.5 | 3.3 | 1.1 |
| Field goals made | 1.5 to 2.5 | 1.9 | 1.5 |
| Points per game, both teams | 80 to 120 | 106.1 | 85.4 |

Before, snap kicks ran at more than twice the top of their range and touchdowns sat below
theirs. After, every line is inside its range, with field goals at the bottom edge.

## Still open

* Games are no closer. The average margin and the share of one score games barely moved.
* Field goal accuracy on attempts fell to 70 percent because coaches try long ones on 6th
  down; #414 counted about 220 tries from 60 yards or more in 270 games.
* Pindowns stay rare, about one every seven games.
* The punting study found field position is cheap in this engine: a drive from your own 5 is
  worth about 2.5 points and one from your own 45 about 3.5. With kicks harder, that gap
  should widen, and it has not been measured again since.
* No tuning was done for this report. The numbers are from one 200 game sample, which carries
  about 2 to 3 points of noise on the accuracy figures.

Sources: `aar_2026-11-28_snap_kick_misses.md`, `aar_2026-11-28_kick_accuracy_and_goal_posts.md`,
`aar_2026-11-28_punting.md`, and the measurement script described in
`aar_2026-11-28_kicking_counterweight_report.md`.
