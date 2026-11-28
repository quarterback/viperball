# AAR: play calling during a game (casebook case 10)

November 28, 2026

## What was asked

Ron asked for Reid's mid-game changes from the coaching casebook: a head coach taking over
or handing off play calling during a game, and assistants suggesting calls between series.

## What changed

1. New module `engine/coach_handoff.py`.
   * Struggling offense at halftime: down 9 or more, or behind with fewer than 15 points.
   * A head coach who delegated takes the offense over when her offensive readiness is at
     least 0.85, with a chance of (0.80 minus her delegation) times 2, capped at 0.80.
     A coordinator who has been a head coach keeps her calls, as before the game.
   * A head coach who kept the calls hands them to her coordinator with a chance of
     (delegation minus 0.30) times 1.5, capped at 0.60.
   * The new caller's tactics are built from her own card, with the same authority rules
     as pregame, and the team's installation is applied again.
   * Between series, after a drive without a touchdown or scoring kick, the coach who is
     not calling looks at this game's run, kick pass and lateral snaps. If one family with
     three or more snaps averages at least 1.5 yards more than the offense overall, she
     suggests it. The caller takes it with a chance of 0.30 plus half her adaptability minus
     0.30 of her stubbornness, between 0.10 and 0.85.
2. `engine/game_engine.py`. The halftime change runs before the existing halftime
   adjustments. A taken suggestion becomes the first call of the next drive when no
   package design or opening script call is active and no urgent situation applies. The
   game result records `midgame_calls` per side (caller changes, every suggestion, taken,
   called and yards) and each play records `suggested_call` when one was called.
   `midgame_calls_enabled` turns it off.
3. The college box score has a "Play calling during the game" table.
4. README rules record and `tests/test_midgame_calls.py`.

## Effect over two weeks of a full season (about 185 games)

36 halftime caller changes: 31 head coaches took the offense over and 5 handed it off. The
teams that changed callers were outscored by 4.0 points on average in the second half.
1,420 suggestions, 610 taken and 421 called, averaging 5.9 yards. Points per game were
101.0 with the feature on and off.

## Checks

New tests, opening script, box score ledger and coach tactics tests pass. The full suite
was not run, at Ron's request.

## Left for later

Caller changes happen only at halftime. Defensive calls do not change hands. A suggestion
is a play family, not a full call with formation and subtype.
