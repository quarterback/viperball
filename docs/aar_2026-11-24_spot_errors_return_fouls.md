# AAR 2026-11-24: referee spot errors, kick return fouls, blocked kick drives

Follow up to `aar_2026-11-24_pen01_inj01_enforcement_injuries.md`, which left two open items: spot errors and kicking team fouls during a punt return. The run also turned up a drive control bug after blocked kicks, which is fixed here.

## Spot errors

**What was wrong.** A spot error changed the play's yards and the field position after the play had already settled the down and distance. The down, the distance and the first down call stayed as if the ball had been spotted correctly. The ball carrier's stats kept the true yards, so the play log and the player line disagreed. The play description kept the true yards too. The check also ran on punts and after a change of possession. Coach challenges on a spot were decided by a coin flip, and an "overturned" challenge changed nothing on the field. The booth review in the last three minutes reviewed nothing.

**What it does now.**
- The spot error is rolled at the snap (its rate never depended on the play). Stat counters are saved only on the plays that get one.
- It applies only where the officials spot the ball: runs, laterals, kick passes and trick plays where the offense kept the ball, nothing scored and no foul was accepted.
- Field position, the yards on the play, the description, the down and distance all move together. A bad spot can give or take away a first down. A bad spot short of the line on 6th down is a turnover on downs.
- The yardage counters credited on the play (`game_yards`, rushing, lateral and kick pass yards) move by the same amount, for every player the play credited.
- Replay can measure a spot. The team the bad spot hurt is much more likely to challenge, especially when it decided a first down. A spot challenge is overturned exactly when the spot was wrong, and the ball, down, distance, result and stats go back. Inside the three minute warning the booth fixes every bad spot on its own.
- Plays carry `spot_error` and `spot_error_corrected` in the play-by-play data.

**Runs that never credited the carrier.** Measuring the gap between play log rushing and player rushing showed spot errors were a small part of it, which corrects the previous AAR. Most of the gap came from runs ending in a fumble or a safety. Those plays count their yards in team rushing, but the run code never put them on the carrier. They are now credited to the carrier, as the scorebook does. Over 40 seeded games, the remaining gap fell from 169 yards on main to 76. All 76 are lateral chain fumbles, where the play's yards are not a real spot (a lost lateral fumble puts the ball back at the original spot). Those are left alone.

## Kick return fouls

**What was wrong.** A kicking team foul during a punt return was declined by the receiving team, so the foul cost the kicking team nothing. Blocking fouls the receiving team committed during its own return were treated like fouls against the kicker. Fair Catch Interference and Kick Catch Interference were charged to the receiving team, and could be called on field goals and snap kicks, where nobody catches.

**What it does now.**
- A kicking team foul on a returned punt or a returned missed kick is accepted and added to the end of the return.
- An Illegal Block in Back, Clipping or Targeting by the receiving team during the return is walked off against the receivers. On a return touchdown, the touchdown comes off. The foul is placed halfway through the return, the returner keeps the yards up to that spot, and the return touchdown comes off his line.
- Both catch interference fouls are charged to the kicking team and can only happen on punts.
- The play-by-play names the teams "KICKING TEAM" and "RECEIVING TEAM" on these calls.

## Blocked kicks and muffed punts end the drive

A blocked kick, a blocked punt and a muffed punt were missing from the drive's list of ending results, because the kicking team sometimes keeps the ball. When the other side recovered, the old drive kept running with the new offense. When the block was returned for a touchdown, there was no kickoff: the team that scored kept the ball near midfield and kept snapping. Now a recovery by the other side ends the drive as a turnover, and a return touchdown ends it with a kickoff by the scoring team. Over 300 seeded games there were 13 blocked kick return touchdowns, and the scoring team kicked off after every one.

## What it looks like

A three week college season (262 games):
- 39 spot errors. 9 were corrected: 5 on a coach's challenge, 4 by the booth. Example: `WB70 sweep → 2 — FIRST DOWN | REPLAY REVIEW — spot corrected`.
- 25 kicking team fouls added to the end of a punt return. Example: `ZB30 punt → 35 yards, SB18 returns 3 yards | PENALTY: Illegal Kick on KICKING TEAM (OL77) — 10 yds, added to the end of the play`.
- 2 receiving team blocking fouls. Example: `HB2 returns 16 yards | PENALTY: Illegal Block in Back on RECEIVING TEAM (VP96) — 10 yds, walked off against the return`.
- Challenges overall: 156 overturned and 348 stood, plus 5 overturned spot challenges.

## Validation

Existing suite (`tests/`): 174 passed. Merged with the special teams PR #349, the suite also passes and that branch's benchmark runs (review posted on #349).

## Limits
- The halfway point for a return foul on a touchdown is an assumption. The engine does not record where during the return the foul happened.
- Return touchdown stat trimming relies on the return length in the play's yards. On main, punt return touchdowns record the catch spot there instead. PR #349 corrects that, and the two land together.
- Lateral chain fumble yards still don't reach a player's line.
