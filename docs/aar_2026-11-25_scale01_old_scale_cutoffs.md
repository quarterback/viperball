# AAR: SCALE-01, cutoffs still on the old rating scale (November 25, 2026)

## What was asked

Ron asked for the hotfix on the run fumble check, before the weather work.

## What was wrong

The engine's contest formulas already read ratings through `scale_rating`. But fourteen fixed cutoffs in `engine/game_engine.py` still compared current ratings (median 35) to numbers written for the old 60 to 100 scale. Players with median ratings fell under every cutoff written for an average player, and only the rarest players reached the ones written for good players.

A census of all 7,389 players in `data/teams` before the fix:

| Check | Before |
|---|---|
| Carriers with the run fumble penalty (hands under 60) | 87% |
| Carriers with the sure hands bonus (85 and up) | 1% |
| Players with a specialist position archetype | 1% (75 players) |
| Variance archetype "explosive" | 67% |

## What changed

Every cutoff now reads the old scale equivalent through `engine.rating_scale.current_to_legacy` (imported as `_old`). That is the exact inverse of the data conversion, so each cutoff now separates the same players it did when it was written.

1. Position archetypes (kicking, running, distributor zerobacks, receiving, power and decoy vipers, the flanker and keeper types).
2. Variance archetypes. The `100 - awareness` term assumed the old scale, so low ratings made nearly everyone explosive.
3. Star designation (75).
4. Change of pace back (speed 82).
5. Bomb kick power gate (70). Nearly every kicker was being cut down on bombs.
6. Run fumble ball security (60 and 85).
7. Kick return yards (speed and agility over 80). Returns were running at about half the size the formula intended.
8. Performance floor on yards (overall minus 50).
9. Tackle skill after the catch (tackling minus 30). Tacklers were taking almost nothing off yards after the catch.
10. Kick lateral entry quality (80 and 60).
11. Return touchdown speed tiers (92 and 85), in two places.
12. Lateral target weights (speed and lateral skill minus 40), in two places.
13. Starter vs backup rating gap (12).

Cutoffs on game energy, coach cards and the kick formulas (already converted through `_kick_skill`) were left alone.

## Results

The census after the fix:

| Check | After |
|---|---|
| Carriers with the run fumble penalty | 20% |
| Carriers with the sure hands bonus | 9% |
| Players with a specialist position archetype | 11% (804 players) |
| Variance archetypes | 48% clutch, 48% reliable, 5% explosive |

120 games each way, same seed, per team per game:

| | Before | After |
|---|---|---|
| Points | 52.8 | 53.9 |
| Touchdowns | 2.86 | 3.00 |
| Turnovers | 2.61 | 2.58 |
| Touchdowns of 30+ yards | 39% | 33% |
| Games decided by 30+ | 23% | 17% |

Turnovers barely moved. The fumble penalty went away, but tacklers taking yards off after the catch and the change in archetypes offset it. Scoring wasn't tuned toward any number.

## Tests

1. Added `tests/test_scale_cutoffs.py`. It checks that specialist archetypes appear, that "explosive" doesn't take over, and that a median carrier sits between the fumble cutoffs.
2. `tests/test_rating_scale.py` and `tests/test_talent_ladder.py` pass.
3. The full suite was not run.
