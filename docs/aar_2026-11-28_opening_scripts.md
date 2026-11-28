# AAR: opening scripts (casebook case 3)

November 28, 2026

## What was asked

Ron asked for the rest of the coaching casebook and cross sport work to be built, starting
with the pieces still missing. This run covers Walsh's opening script. Earlier sequencing
only linked plays in pairs.

## What changed

1. New module `engine/coach_script.py`.
   * A play caller's script length comes from a stable hash of the caller's ID: none, 3, 4,
     5 or 6 calls. About a quarter of callers do not script.
   * Probes in order: inside run, perimeter run, quick kick pass, Viper motion, draw, deep
     kick pass. Each uses the first family the offense's style actually calls, and the
     style's most used formation. A probe the style never calls is left out.
   * Urgent situations hold the next call: kick mode, fifth and sixth down, fourth and
     long, the last three minutes of a half in a close game (all from the existing drive
     plan rules), third or later down with two yards or less, and the red zone.
   * After the script, the probe that gained the most against each front seen, at least
     five yards, becomes that front's answer.
2. `engine/game_engine.py`. At each first half snap the engine asks for the next scripted
   call. It steers the existing formation, family and kick pass selectors the same way a
   package design does, and only when no package design is active. A held call stays next
   in line. A call the engine did not make (a kick, an unavailable action) also stays next.
   Penalties do not use a call. On the first snap of a later first half drive, the caller
   goes to the answer for the front the defense showed last. Each play records `script`
   (probe, status, front, yards) and the game result records `opening_scripts`.
   `opening_scripts_enabled` turns it off.
3. The college box score shows each team's script: the call, the front shown, yards and
   result, what was held and why, and the answers used.
4. README rules record and `tests/test_opening_script.py`.

## Effect over two weeks of a full season (178 games)

282 of 364 offenses scripted. All 1,276 scripted calls were run. Calls were held 452 times:
277 for down and distance, 79 for the red zone, 78 for a different game action and 18 for
short yardage. 254 answers were found and used 505 times. Points per game were 99.1 with
scripts off and 100.8 with them on.

## Checks

New tests, box score ledger and coach tactics tests pass. The full suite was not run, at
Ron's request. The option read is in its own open PR (#404).

## Left for later

Scripts only act in the first half and only for callers with a coaching staff. The answer
uses the last front shown, not a prediction of the next one.
