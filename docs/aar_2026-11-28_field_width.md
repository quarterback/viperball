# AAR: field width, the ball's spot across the field and defensive channels

November 28, 2026

## What was asked

Ron asked why the engine had no field positions. It tracked the yard line on every snap but
not where the ball sat across the 53⅓ yard width, and no player had a location. Plays were
contests between a carrier and a tackler drawn from the whole defense. Direction was a fixed
label per play family, and the game plan "lane" only raised the odds that certain defenders
were picked. Ron chose the two middle options from the discussion: carry the ball's lateral
spot from snap to snap, and assign defenders to channels each snap. A full player position
simulation was ruled out.

## What changed

1. New module `engine/field_width.py` holds the rules and math in one place.
   * The spot is measured in yards from the offense's left sideline and mirrored when
     possession changes. Hashes sit 20 yards in from each sideline, NCAA spacing.
   * Every snap is spotted on or between the hashes. A ball downed outside a hash is
     spotted on that hash, per RULES.md.
   * The defense splits into three channels at the snap. Three linemen hold the box, the
     two end linemen each take an edge, and the midfielders and keepers are split between
     the two sides. Stacked and aggressive fronts bring a midfielder into the box; a spread
     front drops a lineman out of it.
   * The defensive coordinator chooses the split that leaves the offense the least to gain
     on either side. A weaker coordinator (lower `instincts_factor`) misses by a player more
     often. The fastest perimeter defenders go to the wide side.
   * Each side has a value: room on that side plus 0.12 per defender below a fair share,
     minus 0.12 per defender above it. Room alone is worth up to about 7.5 percent.
   * The offense leans to the wide side and away from a loaded side. A better play caller
     reads the split more often. Counters and reverses go back to the lighter side. A
     scripted or package lane always wins.
2. The engine (`engine/game_engine.py`):
   * `GameState.ball_x` carries the spot. Kickoffs, bonus possessions and every scoring
     restart reset it to the middle.
   * `simulate_play` sets the end spot once, in `_finish_width`, for every play. Runs drift
     by family, edge runs travel toward their sideline, kick passes land on the target side,
     lateral chains travel about 4 to 7 yards per lateral, punts land at random or near a
     sideline on a corner punt, and a play wiped out by a foul keeps the snap spot.
   * Runs, kick passes, lateral chains and trick plays pick a side before the defender is
     chosen. The option read defender comes from the same channel picture.
   * Run tacklers, lateral tacklers and kick pass coverage are weighted by channel:
     defenders in the attacked channel count double, box defenders as before, backside
     defenders at 0.45.
   * Edge run yards change by 1.5 times the side value, counters by 1.0 times. Kick pass
     completion changes by 0.5 times the value on quick kicks and kick laterals, 0.3 on
     territory kicks and 0.15 on bombs.
   * A lateral chain that runs out of room before the sideline is squeezed to 60 percent
     of its yards and ends at the sideline. One with room gets 1.2 times the side value.
   * A carrier who reaches the sideline goes out about 60 percent of the time. Out of
     bounds stops the clock in the last two minutes of each half, per the rules.
   * The fake width code is gone. The kick pass "near side" weighting that used the
     roster order now uses real channels. The Viper alignment bonus uses the real side.
   * Boundary Switch and Carry, Carry, Release start their setup on the real short side,
     and "pressed" now means the defense put more than its share of players on the setup
     side (or blitzed), not just an aggressive or stacked label.
   * Each play carries a `width` record (snap spot, hash, side, field or short side, room,
     defenders per channel, side value, end spot, out of bounds). The play text gets a
     short tag: wide side, short side, out of bounds.
   * Each game result carries `field_width.unset_plays`, a count of live plays that ended
     without a side. It was 0 in every check.
3. A stale clock check for `result == "incomplete"` was removed. Incomplete kick passes
   report `kick_pass_incomplete`, so the check never matched, and RULES.md says incomplete
   kick passes do not stop the clock. No behavior changed.
4. README: hash spotting and short and wide side added to The Field; a line on width in
   The simulation today.
5. New test `tests/test_field_width.py`.

## Effect (600 seeded games, same pairs and seeds, per team per game)

| | Before | After |
|---|---|---|
| Points per game (both teams) | 104.95 | 104.89 |
| Average margin | 19.42 | 19.95 |
| Total yards | 376.6 | 376.3 |
| Touchdowns | 2.65 | 2.69 |
| Kick pass completions per attempt | 59.1% | 59.9% |
| Kick pass interceptions | 1.02 | 0.97 |
| Lateral chain yards per play | 2.65 | 2.40 |
| Sweep yards per play | 4.42 | 4.57 |

League totals barely moved. The change is in where plays go and what decides them. Over
300 more games, by the value of the attacked side:

| | Open side | Even | Loaded side |
|---|---|---|---|
| Edge run yards per play | 5.38 | 5.04 | 4.17 |
| Edge run first down or TD rate | 13.6% | 14.9% | 9.8% |
| Kick pass yards per play | 8.13 | 7.55 | 7.05 |
| Counter yards per play | 5.27 | 5.37 | 4.65 |

About 71 percent of edge runs go to the wide side. That share depends on the front: spread
defenses get attacked on the wide side much more, stacked fronts split closer to even, and
a balanced front sometimes invites a short side shot. Lateral chains average 2.64 yards to
the wide side and 2.25 to the short side. Out of bounds happens about 0.75 times per game,
mostly at the end of lateral chains, and stops the clock about 0.06 times per game.

## Checks

The new tests pass, along with the package execution, offensive concepts, option read,
opening script, clinic, Delta playbook, rules document, reproducibility, box score ledger,
officiating, coach tactics, data export, root redirect and NiceGUI freeze tests. The full
suite was not run, at Ron's request.

## Left for later

* Kick angle: field goals and snap kicks from a hash are as easy as from the middle.
* Punt and kick returns do not pick a side; the return spot is random.
* The stats site shows the side only in the play text. Hash and side splits on the game
  and team pages are not built.
* The defense does not yet learn an offense's side tendencies during a game.
