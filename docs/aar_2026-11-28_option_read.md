# AAR: live option read (casebook case 7)

November 28, 2026

## What was asked

Ron asked for the option read from the coaching casebook (Paul Johnson, case 7) to be built.
The policy audit had marked it as missing: on an option call the engine picked the ball
carrier by weight before the snap and never read a defender.

## What changed

1. `ViperballEngine._resolve_option_read` runs on dive, speed and sweep option calls when a
   running or dual threat Zeroback is on the field and another eligible runner is there.
   * The defense commits a real defender, picked the same way it picks a run tackler, to
     either the Zeroback or the other runner. It takes the Zeroback 60 to 80 percent of
     the time depending on its pre-snap alignment; stacked and aggressive fronts crash the
     other runner more often.
   * The Zeroback reads it right with probability 0.78 plus the awareness gap over the
     defender divided by 120, plus the offense's `option_read_bonus` (which the styles
     already set but nothing used until now), held between 0.50 and 0.95.
   * Dive option gives when the defender takes the Zeroback and keeps when the defender
     takes the back. Speed and sweep option pitch or keep the same way.
   * A right read takes the read defender out of the play and the carrier meets a pursuit
     defender. A wrong read runs the ball at the read defender. The yards still come from
     the existing contest; there is no yardage bonus.
2. Kicking and distributing Zerobacks do not read and hand off or pitch as before.
3. Each read is logged on the play as `option_read` (Zeroback, read defender, who the
   defender took, branch, right or wrong, carrier, alignment) and added to the play text.
4. README rules record updated. New test `tests/test_option_read.py`.

## Effect over two weeks of a full season (178 games)

| | Before | After |
|---|---|---|
| Points per game | 99.3 | 101.6 |
| Dive option yards per carry | 4.33 | 3.90 |
| Speed option yards per carry | 4.68 | 4.76 |
| Sweep option yards per carry | 4.89 | 4.79 |
| Zeroback carries | 1,575 | 2,507 |

About 5,000 option calls were read: 1,916 keeps, 1,866 pitches and 1,217 gives, 79 percent
read right. Zerobacks carry about 60 percent more often, because a keep is now a real
branch. That is the main side effect to watch for Zeroback fatigue and kicking.

## Checks

The new tests and the box score, clinic and package execution tests pass. The full suite
was not run, at Ron's request.

## Left for later

The read uses alignment and awareness, not player positions on the field. Option families
called by distributing Zerobacks still do not branch.
