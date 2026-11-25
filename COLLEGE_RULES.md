# Collegiate Viperball League (CVL) Competition Rules (v2.0)

Playing rules are in [RULES.md](RULES.md) and the [README](README.md). This document covers
how the CVL runs its competition.

## League

- The supplied configuration has 205 women's college programs in 17 conferences, from the 9 team Border Conference to the
  16 team Big Ten and Pac-16.
- Programs are drawn from schools across the United States, many without a college football
  team.

## Season

- 12 regular season games per team by default, of which up to 8 are conference games.
- A season needs an even number of programs. If the count is odd when a dynasty season
  starts, Coast Guard is retired, or Merchant Marine if Coast Guard is the human's program.
- Regular season ties stand.
- Schedule construction validates requested quotas and protects conference/rivalry constraints. An impossible request must not be treated as a fulfilled schedule.

## Postseason

- An 8 team playoff decides the national champion by default.
- 4 bowl games by default for teams outside the playoff, drawn from Premier, Major and
  Standard tiers.
- Bowls are played before the playoff. Postseason games go to overtime if tied (see
  RULES.md §17).
- Season size, playoff size and bowl count can be set when a season or dynasty is created.

## Rosters

- 36 player game day roster. Every player is eligible on any down.
- Players play both ways. The Viper and the flankers form two way midfield lines (RULES.md
  §13).

## Dynasty and feeder

The college dynasty follows actual school/player cohorts through the high-school feeder, recruiting, transfer and development cycles. The high-school regular-season quick model is separate from full college gameplay. Coaching contracts, retirement, position assignments and installations progress annually. See [FEATURES.md](FEATURES.md) and [COACHING_SPEC.md](COACHING_SPEC.md). These are simulation systems, not additional playing rules.

## Version history

- v2.0, November 24, 2026: rewritten for the current league. v1.1 described a 24 team,
  poll only league with 15 minute quarters and five downs, none of which apply.
- v1.1: added a kick pass rule, now part of the main rules.
- v1.0: initial release.
