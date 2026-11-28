# AAR: position fit, the high school short line, two Seagulls on the line, Seagulls in college only

November 28, 2026. Second run of the session; the first is
`aar_2026-11-28_formations_motion_seagull.md`. Same branch and PR (#410).

## What was asked

Ron answered the first run's open items:

1. Build the high school short line.
2. Seagulls are SG for short and can play anywhere. Rate how well a player plays outside
   her own group. He preferred the approach most sports games use: each group asks for a
   certain set of skills, so a player's ratings make her more or less able to play it, with
   bare minimums kept in the code. A coach can still play anyone anywhere. A more adaptable
   player, with more agility and a wider set of skills, should be able to do more.
3. Build the rule that only one of two Seagulls on the line may move.
4. Seagulls are like ATH: a college thing, not in the pros or high school.

## What changed

### Position fit (`engine/position_fit.py`, new)

* Seven groups: Zeroback, Viper, flanker, offensive line, defensive line, Keeper and
  defensive back. Each has a skill profile; a player's fit is the weighted average of the
  ratings her profile uses.
* Natural fit: each group has minimums on the two skills it cannot do without, set near the
  league average for players who play the group now. The line groups need 188 pounds or
  more; Viper and flanker allow at most 190 and Keeper and defensive back at most 192. Rosters
  barely differ by position in their ratings, so size is what separates linemen from
  everyone else.
* Adaptability (0 to 100) comes from agility, awareness and how even a player's skills are.
  Outside her own group a player's fit gives up 8%, less the more adaptable she is.
* Fit is used for coach decisions. The plays themselves still use each player's actual
  ratings.

### Seagull listing and roles

* College only. High school and pro games list no Seagulls.
* Candidates are every available player except the starting Zeroback and the top midfield
  line. A player is listed in another group when she is a natural fit there and her fit is
  within 3% of the player she would replace: the second line's Viper, weakest flanker or
  fourth best tackler, the weaker starting Keeper, or the weakest starting lineman. At least
  one of her groups has to be in the open field; a lineman who can only play both lines is a
  cover player. Candidates are ranked by fit, by how many groups they cover and by
  adaptability, and the top two are listed.
* Any Seagull listed at Viper can take the jersey, whatever her position. While she wears it
  she plays as the Viper, so Viper calls go to her. On other snaps she plays as SG.
* New defensive line role: a Seagull listed there comes on for the most tired lineman when
  she rates 5% better.
* A Seagull listed on the offensive line stays in to block when she plays on the line; others
  release.
* Two Seagulls on the line: when one goes on the line, a second fresh one joins her a quarter
  of the time, and the offense picks one of them to slide. Illegal Motion is a little likelier
  on those snaps.
* Box score rows carry each Seagull's fit in her groups. The college game page shows fit
  beside each group and a defensive line column.

### High school short line

On downs 1 to 4, a high school offense lines up short at a rate set by its style: about a
third of the time for Chain Gang and Lateral Spread, a quarter for Ghost and Slick n Slide, 5%
for power offenses, 12% by default. One or two linemen (two on 35% of short snaps) come off
and the fastest fresh bench midfielders take their places in the backfield, never leaving
fewer than three on the line. Protection counts only the linemen left, inside runs lose 5% of
a positive gain for each lineman missing, the extra players widen the lateral chain pool, and
Illegal Formation is 50% likelier. Each play records `short_line` and `on_line`.

## Effect

College, 400 benchmark games against the code before both runs:

| | Before | After both runs |
|---|---|---|
| Points per team | 49.8 | 50.6 |
| Touchdowns per team | 2.72 | 2.87 |
| Sack rate on kick passes | 7.6% | 7.2% |
| Before the snap flags per game | 8.2 | 7.4 |

Teams list about two Seagulls a game. Per listed Seagull per game: about 23 snaps in the
Viper jersey, 15 at defensive back, 9 on the line, 4 on the defensive line and 1 at Keeper,
with about 10 jersey reports per game between the two teams. Most Seagulls are Keepers and
flankers who can also play defensive back, Viper or flanker; a few are light linemen.

High school, 150 games: points per team 48.5 to 50.5, lateral chain yards per play 4.08 to
4.34, short line on 14% of all snaps, sack rate 7.7% to 7.8%.

## Checks

The Seagull tests were extended to cover college only listing, the short line (never fewer
than three on the line, never in college), two Seagulls on the line and position fit. These
pass: the new tests, rules doc, option read, officiating, snap participation, box score credit
and ledger, offensive package execution, reproducibility, opening script, discipline, clinic,
NiceGUI frozen, high school pages, UI unslop and PWA tests. Six college game pages were
rendered through the API with the Seagulls section. The full suite was not run.

## Left for later

1. A Zeroback Seagull can be listed by the rules, but the engine never lists one, because the
   starting Zeroback rarely comes off.
2. Position fit isn't shown on player pages yet, only in the Seagull box score.
3. The Fulcrum defense is not built.
