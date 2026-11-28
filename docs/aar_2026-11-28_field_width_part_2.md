# AAR: field width, part 2: kick angle, returns, side learning, stats site

November 28, 2026

## What was asked

The first field width run (`aar_2026-11-28_field_width.md`) listed four things it did not
build. Ron asked for all of them:

1. Field goals and snap kicks from a hash were as easy as from the middle.
2. Punt and kick returns did not pick a side.
3. The stats site showed the side only in the play text.
4. The defense did not learn an offense's side habit during a game.

## What changed

1. **Kick angle.** `field_width.kick_angle_factor` gives the share of the uprights a kicker
   sees from the snap spot. The posts sit on the middle of the field, and from a hash the
   kicker is 6⅔ yards off center, so the opening narrows by the cosine of the angle. That
   costs about 5 percent on a 20 yard kick and about 1 percent on a 45 yard kick. It is
   applied inside `_place_kick_success` and `_drop_kick_success`, which the coaches' kick
   decisions also call, so play callers weigh the angle before they kick.
2. **Returns.** Viperball has no kickoff returns, so the returns are punt returns and live
   missed snap kicks. Both run through `_calculate_punt_return_yards`, which now:
   * places the landing across the field (`punt_landing`): a corner punt goes to the short
     side's sideline, other punts drift up to 14 yards from the snap spot, and a missed
     snap kick comes down near the posts;
   * shrinks the return when the catch is near a sideline and grows it slightly in the
     middle of the field; strong coverage units cost the returner a little more
     (`return_plan`);
   * runs the returner toward the open side and records where he went down
     (`return_end`). That spot becomes the next snap's spot, mirrored for the new offense.
   The special teams event now carries `landing_x`, `return_x`, `return_side` and
   `sideline_room`.
3. **Side learning.** The engine logs each offense's wide and short side plays and the
   yards they gained. Once it has seen four, the defense builds a lean: positive when the
   offense goes wide more than the usual 65 percent or gains more there, negative the other
   way, and stronger as the sample grows. A sharper defensive coordinator acts on it more
   often. When it acts, one perimeter player moves to the expected side. The offense does
   not need new logic: the moved player changes the side values it already reads, so it
   tends to go to the other side. `V2_ENGINE_CONFIG["side_learning_enabled"]` turns it off.
   Each play's `width` record shows `defense_lean` when a player moved.
4. **Stats site.** New `stats_site/width_report.py` and the partial
   `templates/_field_width.html`. A "Field width" section shows, for each team, plays,
   share, yards per play and success rate by wide side, short side and middle; snaps and
   kicks made by left hash, between the hashes and right hash; out of bounds; and how often
   the defense shifted a player. It appears on the college game page, the single game sim
   page, the pro and international game pages, and the college team page, where it shows
   the team's offense and where opponents attacked its defense for the season. The plays
   table for Observable gains `hash`, `snap_x`, `end_x`, `attack_side`, `side_label`,
   `side_room`, `side_value`, `defenders_left`, `defenders_box`, `defenders_right`,
   `defense_lean` and `out_of_bounds`.
5. Play text tags: kicks from a hash read "[from the left hash]"; returns caught within 8
   yards of the sideline read "[caught near the sideline]".

## Bugs found and fixed along the way

* **Left side bias.** When the perimeter had an odd number of players and the ball sat dead
  center, two defensive splits scored the same and the code always took the first, which
  left the left side a player light. Offenses went left slightly more often and the ball
  drifted to the left hash: 35 percent of snaps from the left hash against 16 to 20 percent
  from the right in a test season. Ties now break at random. Over 120 games the sides are
  now even (6,185 left, 6,158 right).
* **Packages defaulted left.** Boundary Switch, Carry Carry Release and Cape Cod started on
  the left when the ball was dead center. They now pick a side at random there.
* **One way learning.** The first version measured each offense against a 60 percent wide
  side rate. Offenses actually go wide about 65 to 70 percent of the time, so nearly every
  offense looked wide heavy and defenses only ever shifted toward the wide side. The
  baseline is now 65 percent, and shifts go both ways.

## Effect (600 seeded games, same pairs and seeds)

| | Main | Width part 1 | Width part 2 |
|---|---|---|---|
| Points per game | 104.95 | 104.89 | 104.92 |
| Average margin | 19.42 | 19.95 | 19.70 |
| Total yards per team | 376.6 | 376.3 | 382.9 |
| Field goals made per team | 1.92 | 1.91 | 1.86 |
| Field goal attempts per game | 4.78 | 4.78 | 4.64 |
| Snap kicks made per team | 3.30 | 3.26 | 3.24 |
| Kick pass completion | 59.1% | 59.9% | 59.8% |

Yards rose because play callers take slightly fewer field goals from a hash and keep the
drive going; points held. Over 300 more games:

* Punt returns average 11.7 yards when caught with more than 18 yards to the nearer
  sideline, 10.5 yards between 8 and 18, and 9.9 yards within 8.
* On snaps where the defense had shifted a player to the side it expected, offenses gained
  5.89 yards per play to the wide side (6.20 without a shift) and 6.09 to the short side
  (6.34 without).
* Make rates by hash do not show the angle on their own. Coaches pass on marginal kicks from
  a hash, so the hash kicks that are taken are the easier ones. The unit test checks the
  angle directly on the same kicker and distance.

## Checks

`tests/test_field_width.py` adds tests for the kick angle, sideline returns, the defensive
shift and the stats site section (the college game page, the team page and the plays
export). The test for paired drive pace (`test_paired_drive_changes_calls_against_observed_fronts`)
runs a single fixed game. Side learning made the fortress defense stop every probe in that
game, so quick pace correctly never fired. The test now switches side learning off, since
it is about pace. 392 tests across the engine, coaching, special teams, box score, site and
export files pass. The full suite was not run, at Ron's request.

## Left for later

* Teams do not center the ball on the down before a kick, the way football teams do.
* The returner's side does not yet depend on the coverage unit's lanes player by player.
* Season leaderboards (team stats page) have no side or hash columns; the splits are on
  game and team pages.
