# AAR: Defensive call log per game

## Decision
#340 records the situation behind every defensive call (`tactical_context`).
I first proposed showing it inside the play by play. The owner corrected that:
it belongs in a separate game log.

## What shipped
- New page `/stats/college/{session}/game/{week}/{idx}/calls`, one tab per
  defense, linked from the box score's Game Plans section.
- One row per defensive call: play number, quarter, clock, down and distance,
  ball position, score (defense first), how the drive started and which snap
  of it, average energy of the defense and the offense on the field, the
  offense's recent tendencies (kick, deep, explosive, perimeter and lateral
  shares), the call (alignment, blitz, rushers called), the package with main
  or side situation and strength, the situations the call was made in, the
  play the offense ran with its result and yards, and the rush (how many were
  sent and the outcome, naming the rusher on a hurry or sack).
- Rows read `defensive_call`, its `tactical_context` and `rush_event` from
  `play_by_play`; down, clock and score fall back to the play record. When a
  defense has no installed packages the engine skips the context, so the
  energy and tendency columns are hidden and the page says why. Older games
  with no calls show an empty state.

## Checked
A fresh season simmed one week: the log renders for both sides of the first
six games, every defense in that sample carried context, and the table fits
a 1440 px window after merging the two energy columns and letting the
tendency and package cells wrap.

## Not done
No season level view of the log; the team page Tactics section covers the
season totals.
