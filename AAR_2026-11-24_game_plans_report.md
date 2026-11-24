# AAR: Game plans and team tactics on the stats site

## Decision
The engine work merged in #332, #334, #337 and #339 writes the coaches' game
plans and the pass rush into every game result, but the stats site showed
none of it. This is the open part of UI-01. The owner asked for the gap work.

## What shipped
- **Box score, Game Plans section** (`college/game.html`), one column per team:
  - Offense: the OC's name and signature, featured position, formation mix,
    top six play families and the packages called with counts.
  - Defense: the DC's name, signature, coverage focus and read focus; calls,
    blitzes and plays read; alignment mix; packages called against eligible
    snaps (or how many eligible snaps went uncalled); read success by play type.
  - Pass rush: attempts faced, pressures and rate, hurries, sacks, rushers per
    attempt, a table by number of rushers, and the rushers by name with snaps,
    hurries and sacks, linked to their player pages.
  The same section appears on one off Game Sim games; there the coach lines are
  empty because those teams carry no staff.
- **Team page, Tactics section** (`college/team.html`): the same data summed
  over every played game, shown as shares, with the most used OC and DC
  signature and pressure and completion rates by rusher count.
- Everything reads `coach_tactics`, `defensive_coach_tactics`,
  `defensive_reads` and `defensive_rush` from `full_result`. Nothing is
  computed on the page that the engine did not record. Package ids become
  names from `data/playbooks/packages.json`. Games without these fields show
  no section.

## Checked
A fresh season simmed three weeks: box score and team pages render, the team
section counts three games, and the box score section reflows at 420 px wide
(the first version overflowed and was fixed).

## Engine finding for the engine workstream
Pressure credit lands on one player per team. After three weeks Alabama's
DL26 had 28 of 28 lead hurries and 27 sacks, with every other rusher at zero;
Ohio State showed the same shape (16 hurries, 10 sacks, one player). The
`rusher` on each rush event looks like it is always the team's best rusher, so
season sack totals will be far out of range. Logged here and in the work
queue; engine code was left alone because PR #340 is changing the same rush
assignment code.

## Recheck after #340
#340 merged a few minutes before this PR and changed the rush assignment
code. Measured again on main with both merged (fresh season, three weeks, all
205 teams): the top rusher holds a median 70% of a team's lead hurries plus
sacks, 96% at the 90th percentile; a median of four players get any credit;
the median team leader has 6 sacks and the highest has 22. Much better than
one player taking everything, still too concentrated. The work queue note was
updated to these numbers.

## Not done
- Score by channel and period, kick attempts by kind, bells and halftime
  adjustments from the UI-01 list still need their own pass.
- Season level tactics for pro and WVL games.
