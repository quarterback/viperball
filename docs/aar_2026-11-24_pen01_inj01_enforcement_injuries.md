# AAR 2026-11-24: PEN-01 and INJ-01, penalty enforcement and injury attribution

Scope: the two integrity items from `aar_2026-11-24_special_teams_penalties_injuries.md`. ST-01 and ST-02 belong to the special teams workstream (PR #349) and were not touched here. The two branches merge without conflict.

## What changed

### PEN-01: penalties

**Fouls are charged to the sides as they lined up.** `simulate_play` now records who had the ball at the snap (`_snap_possession`) and the score at the snap. `_check_penalties` uses the snap side for every foul during or after a play, including phantom flags. Before, it read the live possession, so a holding call on a play that ended in a turnover or punt was charged to the wrong team.

**The team that did not foul makes the choice.** `_should_decline_penalty` was written from the wrong side: the offense "declined" its own holding call on a touchdown, and the offense declined a defensive foul when it had fumbled. The new rules:

| Foul by | Play result | Decision |
|---|---|---|
| Offense | Offense scored | Accepted, points come off |
| Offense | Turnover, punt or defensive score | Declined, defense keeps it |
| Offense | Offense kept the ball | Accepted unless the play already lost more than the penalty |
| Defense | Offense scored | Declined, points stand |
| Defense | Turnover or defensive score | Accepted, turnover erased |
| Defense | Punt | Accepted only if the foul keeps the drive alive |
| Defense | Missed kick | Accepted |
| Defense | Offense kept the ball | Accepted, yards added on top |

**An accepted foul that wipes out a play now really wipes it out.** `_nullify_play` restores possession, both scores, kick mode, the pending bonus possession, and every numeric `game_*` stat counter to their values at the snap. Clock, fatigue and injuries stay, because the play was physically run. To keep this cheap, the live ball foul is now rolled just before the play runs (`_pre_roll_live_foul`), and stat counters are saved only on the plays that drew a flag.

**Enforcement spots and distance.** Each penalty now records how it was enforced (`previous_spot`, `end_of_play`, `succeeding_spot`) and whether the play was nullified, and both appear in the play-by-play penalty data.
- Offensive fouls walk back from the previous spot. Distance to go grows by the yards actually walked off (half the distance near the goal line is already handled by the 1-yard floor). Loss of down fouls cost a down; on the last down that is a turnover on downs.
- Defensive fouls on a play the offense kept are added at the end of the play. The play's own yards stay as the play's yards instead of being overwritten with the penalty yardage. First down comes from the foul's own flag or from total gain since the snap reaching the line to gain; otherwise the down is replayed with less to go.
- The automatic first down flag now travels on the penalty from the catalog entry that was rolled. The old lookup searched by name in three catalogs and skipped the kick pass catalog, so contact on a kick pass receiver, roughing the kickpasser and kickpass interference never granted a first down.
- Pre-snap fouls now change the distance too. Before, a false start moved the ball back 5 yards and left the distance unchanged, and a 5-yard offside short of the line left it unchanged.
- Dead ball fouls after the play are enforced against whichever side committed them from where the ball ended up, and always stand (there is nothing to decline).

**Delay of game no longer lands on a play that already happened.** The play clock check runs after a play resolves. It used to move the ball back 5 yards and reset the down to the pre-play down, after the play's yards and down had already counted. Now a violation is queued and enforced as a pre-snap foul at the next snap, if the same offense lines up in the same quarter.

**Team penalty counts** in the game summary now come from the team that committed the foul. They used to be counted on whichever team had the ball, so every defensive foul showed up in the offense's penalty column.

### INJ-01: injuries

- `check_in_game_injury` and `check_defender_injury` now find the injured player's team from the rosters, by identity. Before, a ball carrier who fumbled was "injured" for the team that recovered, which put him in the wrong injured set and sent the substitute search to the wrong roster.
- Both now share one roll (`_roll_player_injury`) with the fatigue multiplier. Defenders previously skipped it.
- New contact exposure for plays that never rolled: the punt returner on a returned punt, and the passer and rusher on a sack. Each participant is looked up by the label on the play or the rush event, on their own roster. If nobody is named, nobody is rolled.

### Found along the way
A sack moved the ball back but left the distance to go unchanged. It now grows by the sack yardage.

## What it looks like

Six seeded benchmark games (`scripts/benchmark_engine.py` matchups, seeds 100 to 105):

| Enforcement | Count |
|---|---|
| Pre-snap, previous spot | 63 |
| Live ball, play nullified | 43 |
| Live ball, end of play | 36 |
| Dead ball, succeeding spot | 35 |
| Declined | 8 |

Examples from the play-by-play:
- `ZB48 field goal 58yd — GOOD! +3 | PENALTY: Holding on OFFENSE (SB86) — 10 yds, play nullified`. On main this holding call was declined by the offense and the kick counted.
- `HB45 sweep → 5 | PENALTY: Illegal Use of Hands on OFFENSE (VP55) — 10 yds, play nullified`.

Across those six games no nullified play left a score change or a possession change behind. Across 20 seeded games, player rushing touchdowns matched the play log exactly, including 4 nullified touchdown plays.

Two week college season run (about 180 games each side):

| | main | this branch |
|---|---|---|
| In-game injuries | 141 in 180 games | 157 in 177 games |
| Zeroback injuries | 11 | 27 |
| Penalties declined | 537 | 291 |

The Zeroback rise is the new sack exposure. Declines fall because offenses no longer decline defensive fouls after turnovers and defenses no longer decline holding on scores.

## Validation

Existing suite (`tests/`): 174 passed. The root level `test_wvl.py` fails to import `compute_season_revenue` on main as well; unrelated. Trial merge with PR #349 (ST-01/ST-02) is clean, and the punt returner label the exposure check reads is unchanged on that branch. STI-VAL belongs after both land.

## Limits
- Run plays on main still show a gap between play log rushing yards and player rushing yards. Correction from the follow up run (`aar_2026-11-24_spot_errors_return_fouls.md`): spot errors were a small part of it. Most of the gap was runs that end in a fumble or a safety, which never credited the carrier, and lateral chain fumbles.
- The sack safety branch in the kick pass code can never fire (`max(1, ...)` before a `<= 0` check). Left alone.
- Kicking team fouls during a punt return are declined by the receiving team rather than added to the end of the return. Fixed in the follow up run.
- Rolling the live ball foul before the play changes the random number sequence, so seeded games differ from main. Seeds still reproduce run to run.
