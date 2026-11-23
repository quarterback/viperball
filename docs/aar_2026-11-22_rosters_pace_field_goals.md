# AAR: Rosters with real gaps, a faster game, field goals that matter
## November 22, 2026

## What Ron said

- Blowouts are a roster problem. The game evens teams out so a team is good or bad at every
  spot. Real teams have a handful of good players and real gaps. His baseball game may do
  this better: look, then fix it.
- Viperball is too cadenced, like football. It should play more like Australian rules,
  Gaelic football and rugby, with higher scoring.
- A faster game makes field goals matter: teams take points after stops, or when they cannot
  get close enough for the snap kicker. A kick off a tee carries farther than in the NFL.

## What the baseball game does (`quarterback/hybrid-baseball`, `o27v2/league.py`)

`_TALENT_TIERS` is a league wide ladder: 7% elite, 12% excellent, a deliberately hollow
middle (21%), and 60% below average to sub-replacement. Every attribute is rolled against
it. Its comments give the reason: with a fat middle, rosters regress to the league mean and
bench players are clones of starters.

## What Viperball did

`generate_player_attributes` rolled every stat of every player around one team number (the
program archetype's `stat_center`, 15 for a doormat to 64 for a blue blood) with a spread of
38. Eleven noisy stats average out, so every player on a team landed near the team number.
Teams differed from each other by up to 40 rating points and hardly at all inside.

## Changes

**Rosters (`scripts/generate_rosters.py`)**
- `TALENT_LADDER`: the baseball ladder on Viperball's rating scale. Each player rolls her own
  level from it. Stats are then rolled around that level (`PLAYER_STAT_SPREAD` 10), so
  players stay spiky.
- The program archetype now shifts the roll by about -8 to +9 (`ARCHETYPE_SHIFT_SCALE`), so
  blue bloods have more stars, without making whole rosters uniform.
- The stat budget that trimmed standout players is gone.

| Generated rosters | Before | After |
|---|---|---|
| Team average rating, weakest to strongest | 18 to 59 | 24 to 47 |
| Best minus worst player on a team (median) | small | 60 |
| Players rated 60+ per team (median) | | 4 |

**Pace (`engine/game_engine.py`)**
- Seconds between plays: 38 (slowest offense) to 18 (fastest) becomes 28 to 13
  (`play_clock_slow`, `play_clock_fast`). Plays per team go from about 73 to 92.

**Field goals**
- Comfortable range is 15 yards beyond the snap kick's (`place_kick_range_bonus`), and
  attempts are possible to 71 yards (`place_kick_max_distance`), the README's figure. The old
  curve fell to 0.3% at 55 yards.
- Coaches take a field goal when stalled out of snap kick range: on 4th down with 10+ to go,
  on 5th with 4+, at 60% or better (`kick_4th_down_fg_min_ytg`, `kick_5th_down_fg_min_ytg`,
  `kick_fg_min_success`). 6th down already chose the better kick.

**Retuned alongside**
- `field_compression` 0.4 to 0.55, starting at midfield: moves scoring from touchdowns to kicks.
- `rating_scale_slope` 0.3 to 0.45: with gaps now inside rosters, individual talent can count
  for more without bringing blowouts back.
- Benchmark targets now come from the README's Scoring Context (a 63 to 49 game with 3
  touchdowns, 4 snap kicks and 2 field goals).

## Result: full real season, per team per game

| | Before this run | Rosters only | Final | README |
|---|---|---|---|---|
| Points | 47.6 | 49.9 | 60.6 | 45 to 70 |
| Touchdowns | 3.1 | 3.4 | 3.7 | about 3 |
| Snap kicks made | 3.0 | 3.1 | 3.2 | about 4 |
| Field goals made | 0.13 | 0.10 | 2.0 | about 2 |
| Median margin | 19.5 | 17.0 | 19.5 | |
| Decided by 30+ | 27% | 20% | 21% | |
| Within 9 points | 26% | 29% | 25% | |

Margins at the end are on 60 points a game, up from 48, so a 19.5 point margin is a smaller
share of the scoring than before. `tests/` passes (72). No plays on 7th down or later.

## Not changed, and why

- Recruiting, development and the high school league still generate players their old way.
  New recruits will be rolled around a number again until those are moved to the ladder.
- The saved team files in `data/teams` are not regenerated; seasons generate fresh rosters.
- Turnovers rose from 2.1 to 2.7 per team with the extra plays.
