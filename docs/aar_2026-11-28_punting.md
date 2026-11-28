# AAR: punting skill, punt types and coaching philosophies

November 28, 2026

## What was asked

Ron's decisions: punting skill is a must; punt types should make Viperball different from
the other gridiron codes, with Australian style punting next to the North American style,
both effective in different ways; and coaches should run from those who never punt, as
some real coaches do, to aggressive 6th down punters. A punt before 6th down should happen
only for an extreme reason such as the clock.

## What changed

New module `engine/punting.py`, wired into `engine/game_engine.py`.

1. **Punting skill.** Every player has a profile: distance, placement, an overall rating
   and a style (aussie, continental or both). It comes from kick power, kick accuracy and
   kicking plus a personal knack that stays the same every run, and about one player in
   twelve is a natural punter. The best punter on the roster punts, whatever his position.
   Across 80 teams the best punter rates 59 to 99 (average 79), with about 2.4 players per
   team at 70 or better, and they come from every position group, because kick ratings in
   the team files barely differ by position.
2. **Punt types.**
   * spiral: distance from deep in your own end; past midfield it is aimed at the end zone
     for a pindown.
   * drop punt: placed to land around the 7 and check up with backspin; much shorter
     returns.
   * rugby roll out: low and bouncing, hard to block and hard to field.
   * quick kick: a 5th down surprise with no returner back.
   * corner punt: the Corner Chase package, as before.
   * pindown try: the last play of a half out of kick range, a spiral aimed at the end
     zone.
   An aussie punter drops it inside the 10 past midfield and mixes drop, roll out and
   torpedo spiral around midfield; a continental punter uses the spiral and plays for the
   pindown. A kick rush or a wind in the punter's face brings out the rugby punt.
3. **Coaching philosophy.** Each head coach has a value from -1 (never punts) to +1 (field
   position first). The existing Punt Hater and Field Position Purist traits set the two
   ends; until now they only scaled a play weight the kick decision never read. Everyone
   else sits by the late down aggression slider. Across 600 generated head coaches: 73%
   punt by the book, 17% lean on field position, 5% put field position first, 4.5% never
   punt. Teams without a staff use their style's punt settings. Head coach pages show it.
4. **The 6th down decision** weighs a punt, going for it and the best kick using what a
   drive is worth from each spot, fitted from 400 engine games, plus 6th down conversion
   rates by distance, with the coach's philosophy added to the punt. A team trailing in the
   fourth quarter, or by more than 9 in the third, never punts.
5. **No punts from play calling.** Play selection could call a punt on any down; about 0.9
   punts a game came from 1st through 5th down that way, plus forced punts on the last play
   of a half from anywhere on the field. Play calling no longer picks punts, and the last
   play of a half punts only within reach of the end zone.
6. **Site.** Player pages show punting, punt distance, punt placement and style; the
   college roster has a PUN column and a Punting sort; head coach pages show the punting
   philosophy.

## Findings

* Field position is cheap in this engine. A drive from your own 5 is worth about 2.5
  points and one from your own 45 about 3.5, because offenses score kicks from most of the
  field. On pure points, going for it on 6th down beats punting almost everywhere past
  your own 25. That matches the separate snap kick study: kicks are accurate enough that
  field position matters little.
* Head to head over 400 games each, the philosophies are even: never punts against field
  position first won 50.0%; never punts against by the book 50.1%; by the book against
  field position first 50.4%. Margins were within about a point and inside the noise.

## Numbers (200 games each, philosophy forced for both teams)

| | Never punts | By the book | Field position first |
|---|---|---|---|
| Points per game | 104.8 | 103.9 | 102.6 |
| 6th down punts per game | 0 | 1.52 | 2.20 |
| 6th down tries per game | 2.56 | 1.21 | 0.65 |
| All punts per team | 0.00 | 0.86 | 1.18 |

On main, 6th down punts ran about 0.94 a game.

## Checks

Seven new tests in `tests/test_punting.py` passed. The wider targeted test run was stopped
at Ron's request before it finished, so no other tests have been confirmed on this branch.

## Left for later

* Punt types on the game page and season punting stats by type.
* A punter's style does not develop or change over a career.
