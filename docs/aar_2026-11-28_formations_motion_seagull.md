# AAR: formations, Canadian motion, the Viper jersey and the Seagull (rulebook v2.1)

November 28, 2026

## What was asked

Ron designed two new pieces of the sport in conversation and asked for them to be built:

1. Canadian style motion in place of the NFL one player rule, with the A11 idea that the
   defense should not know who is who, held together by one fixed point: the Viper jersey.
2. The Seagull, which he wanted to be both things discussed: a positionless player listed
   for more than one group, free to declare, floating outside the midfield lines, and the
   one line player allowed to move before the snap.

He chose a lower line minimum in high school than in college and the pros.

## How the session went

1. Read the defense engine, catalog and rules to assess his Fulcrum defense document. Verdict
   given in chat: it works as the first defense with a strong side, but its kick rush and
   lateral claims repeat Keeper Hunt, Swarm and Chaos Lateral Trap. Not built in this run.
2. Worked out the Seagull from rugby's seagull, football's Joker, ATH and Taysom Hill roles,
   and the libero, NFL eligibility reporting and MLB two way rules.
3. Found that motion was never modeled: the Viper's alignment was a random pick each snap,
   Ghost's `pre_snap_motion` setting was never read, and the Viper and numbering fouls were
   flat random flags.
4. Drafted rulebook v2.1, then added the Seagull's line motion freedom.
5. Built it (this record).

## What changed

### Rules

* RULES.md v2.1: sections 11 (Seagull), 12 (rewritten: the line, the Seagull on the line,
  the backfield, motion, the Viper jersey, the snap), 13 (Seagull reporting), 16 (Umpire and
  Side Judge duties), 19 (glossary) and 20 (version history). Penalty table regenerated.
* README: Formations and Motion rewritten, Seagull added under Positions, Rotations and
  Officials updated, glossary entries added.
* Retired from the penalty catalog and `engine/officiating.py`: Illegal Viper Alignment,
  Illegal Numbering and Illegal Formation (Numbering Exception).

### Engine

New module `engine/presnap.py` holds the listing rule, the motion chances, the Seagull line
rates by style and the foul scaling. `ViperballEngine` changes:

1. **Line minimum.** `self.line_minimum` is 3 for `officiating_level="high_school"` and 5
   otherwise, and is in the result as `line_minimum`.
2. **Seagull listing.** The first time a team's lineup is built, the coach lists up to two
   Seagulls from the midfield players off the top line. A player is listed when she is as good
   as the players already in another group: defensive back (tackling within 3% of the top
   line's fourth DB), Keeper (within 5% of the weaker starting Keeper) or flanker for a Viper.
   Only a Viper by position is listed at Viper. Listed Seagulls are left out of the midfield
   lines.
3. **Seagull roles, set at each dead ball** (`_set_seagull_roles`):
   * Offense: she takes the Viper jersey when she rates 3% better than the line's Viper and
     has 65 energy, and keeps it down to 50 energy. The jersey returns to the line's Viper at a
     change of possession or a timeout, and taking it again is a new report. If she is not in
     the jersey, she plays on the line in place of the weakest lineman on downs 1 to 4, at a
     rate set by the offense style (22% of snaps for Chain Gang down to 6% for power
     offenses, 10% by default), and slides on 85% of those snaps.
   * Defense: she comes on at Keeper when a starting Keeper is below 62 energy, or at
     defensive back when she tackles 5% better than the weakest DB, while she has 70 energy.
   * `_lineup` puts her into that slot. On the line her role is `Seagull`, so kick pass
     protection counts four linemen.
4. **Backfield motion** (`_set_pre_snap`): each midfield player on offense is in motion at the
   snap with chance 0.08 plus 0.30 times the style's `pre_snap_motion` (0.30 by default,
   0.80 for Ghost), cut to 40% on downs 5 and 6 and in kick mode. A Decoy Viper moves 60%
   more often.
5. **Effects on the play:**
   * Running start: a carrier in motion gains 6% more on a positive run on perimeter calls
     (sweep, speed option, Viper jet, counter, lateral spread, trick play) and 3% on others. A
     kick pass receiver in motion is 3 points easier to complete to.
   * A Viper in motion finishes on the side that suits the call, worth 60% of the Viper
     alignment table, unless the defense adjusts with her (40% of the time, up to 60% for a
     DC with top instincts).
   * With a Seagull on the line, dive option, power and draw lose 5% of a positive gain.
6. **Before the snap fouls follow the snap.** Illegal Motion and Illegal Shift scale with the
   number of movers and a sliding Seagull; False Start is 30% likelier when a Seagull slides;
   Missing Viper Jersey is likelier on a jersey change and rare otherwise; Illegal Viper
   Substitution happens only when a Seagull is on the field for the offense. The flag goes to
   the player involved: a mover, the sliding Seagull or the Seagull in the jersey.
7. **Records.** Each play carries `motion` (movers, who moved, Viper motion and alignment,
   Seagull on the line, slide, Seagull in the jersey, jersey report, defense adjusted). The play
   text notes jersey reports and a Seagull on the line. The result carries `seagulls` (listed
   players, groups, snaps by role) and `seagull_reports`.

### Stats site

The college game page has a Seagulls section after Penalties and Discipline: each listed
Seagull, her groups and her snaps by role, and a list of Viper jersey reports.

## Effect over 400 benchmark games (same matchups and seeds)

| | Before | After |
|---|---|---|
| Points per team | 49.8 | 51.0 |
| Touchdowns per team | 2.72 | 2.89 |
| Plays per team | 82.3 | 83.1 |
| Counter yards per carry | 5.60 | 5.80 |
| Sweep option yards per carry | 4.83 | 5.08 |
| Viper jet yards per carry | 6.49 | 6.78 |
| Dive option, power, draw yards per carry | 4.33, 4.70, 4.81 | 4.35, 4.65, 4.83 |
| Sack rate on kick passes | 7.6% | 7.5% |
| Before the snap flags per game | 8.2 | 7.7 |

About 0.9 players are in motion per snap, the Viper on 17% of snaps. A Seagull plays on the
line on about 9% of snaps. Teams list 1.7 Seagulls a game on average; each listed Seagull
plays about 22 snaps at defensive back, 6 in the Viper jersey, 4 on the line and 1 at Keeper,
with about 5 jersey reports per game. The drop in before the snap flags is the three retired
fouls; the remaining motion and jersey fouls now happen only when someone moves or changes.

The first version gave a Viper in motion the full leverage on every snap and lifted scoring
by about 3 points per team, most of it on counters. Letting the defense adjust brought that
to the numbers above. There are no scoring targets; this is reported so the change is visible.

## Checks

New `tests/test_formations_motion_seagull.py`. These pass: the new tests, rules doc, option
read, officiating, snap participation, box score credit and ledger, offensive package
execution, reproducibility, opening script, player discipline, discipline box score, clinic
playbook, NiceGUI frozen, high school pages, UI unslop and PWA tests. A college game page was
rendered through the API with the Seagulls section. The full suite was not run, at Ron's
request.

## Left for later

Updated after the second run (`aar_2026-11-28_position_fit_short_line_seagull_college.md`):
items 1, 2, 3 and 5 are done or settled. The short line is built, position fit replaces the
midfield only listing, two Seagulls can play on the line, and Seagulls are college only, so
no other game pages need the section. The Fulcrum is still open.

1. The high school line minimum of 3 is in the rules and the engine, but the engine still
   fields five linemen on every snap, so no offense yet uses a short line.
2. The engine lists Seagulls only from midfield players. The rules allow Zeroback, line and
   Keeper Seagulls; there are no cross group ratings for linemen yet.
3. Only one Seagull plays on the line per snap, so the rule that only one of two may move is
   never tested.
4. The Fulcrum defense is not built. It needs a strength side set from the Viper jersey and a
   bump or swing answer to motion.
5. Pro, WVL and high school game pages do not show the Seagulls section yet.
