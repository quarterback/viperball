# AAR: Snap kick decision logic restored to Ron's design
## November 22, 2026

## What Ron said

A snap kick can happen on any down. It is a shot at goal from open play, in the way
Australian rules and Gaelic football have kicked goals. A coach would not logically take it
before 4th down, more often on 5th, and earlier when it is late in the game. Teams trading
snap kicks at different times is what should make the sport more dynamic than football.

## What was wrong

`aar_2026-03-18_early_down_snap_kicks.md` fixed real bugs (kicks on 1st to 3rd down, kicking
8 yards from the end zone) but then set a rule Ron never made: kicks only on 6th down. That
ignored the missed kick rule. A miss on downs 1 to 5 keeps the ball, so 5th down is the
better kicking down and 6th is the last resort.

## What changed (`select_kick_decision`, play dispatcher)

- **Downs 1 to 3:** keep driving, except in the last two minutes of a half. Then a team in
  comfortable range takes the shot. In the 4th quarter this only applies when 5 points would
  tie the game or take the lead.
- **4th down:** snap kick when the drive has stalled (10+ yards to go, 7+ for green light
  kickers and coaches), in range, at 70% or better.
- **5th down:** the main kicking down. Snap kick in range at 50% or better unless it is
  short yardage (under 4 to go). A miss leaves 6th down.
- **6th down:** unchanged.
- Kept from March: no kicks near the goal line, and no late kicks that cannot tie or win.
- README "When Teams Kick" section rewritten to say this.

## Measured (benchmark, 200 games)

Snap kicks made per team per game: 0.28 before, about 0.6 to 0.7 after. Tests pass (72).

## Still open

Kicks stay rare because drives that get into range usually score a touchdown before 4th
down. A sweep of the two global dials (`power_ratio_exponent` 2.2 to 1.2,
`base_yards_multiplier` 2.3 to 1.6, 120 games each) moved touchdowns from 3.95 to 3.06 and
snap kicks from 0.69 to 0.97, and left the median margin near 27 points. Neither dial was
changed. Trading snap kicks needs defenses that stop drives inside kicking range, which is
the next piece of work.
