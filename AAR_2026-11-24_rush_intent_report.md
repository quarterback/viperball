# AAR: Rushers called and package call detail

## Decision
#340 added per-snap fields to each defensive call (intended rushers, package
strength, eligibility, familiarity, focus, situations, tactical context) and
the intended count to each rush event. Its AAR names them as the contract for
the stats site. The Game Plans section shipped in #341 only read the per-game
summaries, so these were the next additions.

## What shipped
- `stats_site/templates/_tactics.html`: one shared macro used by the box score
  and the team page.
  - **Rushers called:** the share of all defensive calls by how many rushers
    the coordinator called, then a table for kick-pass attempts by called
    count: attempts, average sent, attempts where fewer rushed than called,
    pressure rate, sacks and completion rate.
  - **Package calls:** each package called, with calls in its main situation
    against a secondary one, average execution strength, how well the team
    knows it, yards per play allowed on those calls and the situations it was
    called in, set against yards per play on all snaps.
- `stats_site/router.py`: `_side_calls` reads the per-snap calls from
  `play_by_play`; `_call_details` turns them into the tables. The team page
  sums every played game's snaps. Column meanings live in header tooltips.

## Checked
A fresh season simmed three weeks on current main: both pages render, the
detail sits in two columns on desktop and stacks in the narrow box score
column. Over the league, 15,750 kick-pass attempts: 32.1% pressured, 13.1%
sacked, and no attempt sent fewer rushers than were called.

## Work queue update
The pass rush note now carries a reference point (a real team's sack leader
has roughly a third of the sacks), the league sack rate above against real
football's 6 to 7% of dropbacks, and the fact that intended and sent rushers
only differ in depleted lineups, so the Short column will usually read zero.

## Not done
`tactical_context` (recent offensive tendencies, energy, score and clock at
the call) is not shown. It is per snap and reads best inside play by play,
which is a separate change.
