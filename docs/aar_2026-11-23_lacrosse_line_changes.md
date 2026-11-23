# AAR: Lacrosse style line changes
## November 23, 2026

## What Ron asked

Lacrosse style substitutions, with rules changed as needed. The written rule that
substitutions happen only at dead balls is not a constraint.

## What it means in a down based game

Every Viperball down ends in a dead ball, so changing between plays was already free. On the
fly only matters when the ball turns over during live play. That is where lacrosse teams get
caught mid change, so that is where the new risk lives.

## Changes (`engine/game_engine.py`)

**Midfield lines** (`midfield_lines_enabled`, `midfield_line`, `_midfield_lines`, `_midfield_on`, `_rotate_midfield`)
- The Viper and four flankers play as one line: a Viper, a Halfback, a Wingback, a Slotback,
  and the best remaining flanker. Each team has three lines, best players on line one.
- Lines play both ways. On defense, the line's four best tacklers play defensive back.
- Each line has its own out mark (74, 80, 86), so the top line takes the longest shifts. All
  lines come back at 90. Work rate and the close fourth quarter ride still move the marks.
- When line one is rested, it goes back out. Otherwise the coach rolls to the next line in
  order that is rested and plays at least 90% as well as the tired line does right now.
- Midfield load is 1.6 per snap, since these players play every snap of their shift.

**Defensive specialist**
- The best tackler on the other lines comes on for defensive possessions when her tackle
  score beats the line's fourth best tackler by 8%. She comes on at 80 energy and goes off
  below 55.

**On the fly and getting caught** (`LIVE_TURNOVER_RESULTS`, `_caught_roll`, `fast_break_boost`)
- Live turnovers: fumble, muffed punt, blocked kick or punt, chaos recovery, returned missed
  snap kick, intercepted kick pass or lateral.
- On the next play, the team that lost the ball can send its specialist on while the ball is
  live (half the time) or change a tired line (only if 3 points past its mark). Either change
  carries a 35% chance of being caught short. A caught team gives up a fast break: the other
  side's contest rating is up 6% for that play.
- Otherwise the coach waits one play and changes at the next dead ball.

**Players are now picked from the eleven on the field**
- Before, ball carriers, returners and tacklers were drawn from every available player on the
  roster, so a third string halfback could carry the ball while "off the field." Now
  `_offense_skill`, `_offense_all`, `_defense_players`, `_pick_tackler` and
  `_pick_def_tackler` use the lineup. Midfielders on defense now get tackle credit on longer
  gains (10% of team tackles).
- Snap counts now credit only players on the field. These counts feed player development,
  so playing time now drives it.
- The offense lineup was 10 players before (one each at HB, WB, SB). With the five player
  line it is 11.

**Cover across groups** (`COVER_FOR`, `_cover_pool`)
- Found during measurement: season rosters can carry only five or six defensive linemen.
  With tackles now landing only on the five on the field, four linemen on one team finished
  a game at 0 energy, and 17% of linemen finished under 50.
- Spare offensive linemen (not in the offense lineup) now fill in on the defensive line, and
  bench midfielders can fill in at Keeper, at 90% of their rating.
- The backup energy rule is now relative: a backup needs 12 more energy than the tired player,
  and at least 60. Before, she needed 80, so late in games nobody qualified.
- Linemen under 50 at the end: 17% → 6%.

**Game result**: `game_day.line_changes` and `game_day.caught_changing` per team.

**README**: Substitution rules rewritten (any time, on the fly through a substitution zone),
Rotations rewritten for lines, specialists, cover and getting caught, Two Way Play updated.

## Results

60 games, share of all snaps (both sides):

| | Line 1 | Line 2 | Line 3 |
|---|---|---|---|
| Midfield | 37% | 25% | 13% |

That is about half the midfield time for line one, a third for line two, the rest for line
three. 9.2 line changes per team per game; a team is caught changing 0.28 times a game.

| Group | Depth chart, share of all snaps |
|---|---|
| Zeroback | 34%, 8% |
| Offensive Line | 42, 42, 40, 39, 38, then 14 and 8 (spares now cover on defense) |
| Defensive Line | 40, 36, 33, 31, 29, 16, 12 |
| Keeper | 40, 40 |

Benchmark (300 games): 59.0 points, 3.6 touchdowns, 3.1 snap kicks, 1.9 field goals per team.

Full seasons:

| | Seed 2026 | Seed 7 |
|---|---|---|
| Points per team | 58.9 | 58.7 |
| Home win | 47.2% | 49.6% |
| Lower prestige wins | 34.1% | 38.3% |
| 30 point margins | 26% | 24% |
| End energy p10 / p50 | 54.6 / 82.5 | 54.8 / 82.4 |

Tests: 72 pass.

## Open

- The Illegal Substitution penalty still fires at its old flat rate. It could fire more often
  on live changes.
- Lines are not shown in the app yet.
- Coaches all use the same line rules; a coach's personality could set how often she risks
  live changes.
