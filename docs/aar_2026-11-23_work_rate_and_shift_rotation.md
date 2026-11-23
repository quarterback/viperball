# AAR: Work rate rating and shift rotations
## November 23, 2026

## What Ron said

- Fatigue belongs on the roster and My Team pages, not the box score.
- It should be a work rate rating: a player with a high work rate and good stamina can be
  used a lot, so tiredness should not hit everyone the same way.
- Make coach rest and rotations realistic. Substitution is unlimited, as in hockey, so
  something like shifts, but no unit leaving all at once: some position groups stay on
  longer and others swap out individually, as in basketball, and more dynamic than either.

## What Viperball did before

- Rest was drive based. A starter was benched for a full drive, and only below 30 to 45
  energy; that rarely happened. Defensive linemen and linemen never rotated.
- Only Keepers and the defensive line counted as defenders, though the README says the best
  athletes play both ways.
- Fatigue tiers were set by a player's overall rating, so stars both drained slower and felt
  tiredness less.

## Changes

**Ratings (`engine/game_engine.py`, `scripts/generate_rosters.py`)**
- New `work_rate` rating. New rosters roll it from stamina plus a large personal spread
  (`gauss(stamina * 0.5 + 18, 13)`), so a modest athlete can have a high work rate and a
  star a low one. Players created elsewhere (recruits, older saves) get a stable value from
  stamina plus a per-player offset through `Player.work_rate_rating`.
- Stamina now sets how fast a player drains and recovers. Work rate sets how much tiredness
  costs her (0.5x at the top of the scale, 1.4x at the bottom) and how long her coach leaves
  her on. Overall rating no longer decides either (`work_rate_effect_enabled`).

**Shift rotation (`_rotate_shifts`, `_lineup`, `rotation_profiles`)**
- At every dead ball (the README's substitution rule), each team checks each position group.
- Each group has slots on the field, an "out" energy mark, a "back" mark, a per-snap load,
  and a "rest" allowance:

| Group | Slots | Out | Back | Load | Rest |
|---|---|---|---|---|---|
| Zeroback | 1 | 46 | 72 | 0.8 | 2% |
| Viper | 1 | 58 | 80 | 1.0 | 5% |
| Halfback, Wingback, Slotback | 1 each | 66 | 86 | 1.1 | 7% |
| Offensive Line | 5 | 66 | 86 | 1.3 | 7% |
| Defensive Line | 5 | 76 | 90 | 1.7 | 10% |
| Keeper | 2 | 52 | 76 | 0.85 | 3% |
| Two-way defensive backs (best tacklers among Vipers and flankers) | 4 | 64 | 84 | 1.0 | 7% |

- A player's out mark drops by half a point per work rate point above 75 (on the 60 to 100
  scale) and by 10 in a fourth quarter within 9 points, when coaches ride their starters.
- A tired player comes off only if a fresh backup would play nearly as well as the tired
  starter does right now: the backup's rating times her fatigue modifier must be within the
  group's rest allowance of the starter's. So deep groups rotate and thin ones ride
  starters, without a fixed talent cutoff. An earlier version used a 12 point overall gap,
  which almost never let linemen rotate on the new rosters.
- At most two linemen or two defensive backs swap at one dead ball, one for other groups.
- Rested players return once at their back mark. Players resting are unavailable for plays.
- On-field energy cost per snap is 1.0 times stamina and group load; sideline recovery is 0.5
  per snap times stamina. The old drive based fatigue benching is skipped when shifts are on;
  blowout and performance benching are unchanged.
- `game_field_snaps` and `game_shifts` are tracked per player.

**App**
- Work rate (WRK) and stamina (STA) columns on the team roster and My Team; work rate on the
  player page. API: `work_rate` in `_serialize_player` and the My Team roster.
- The box score energy column added in the previous run is removed.

**README**: Game Day section rewritten for stamina versus work rate, and a new Rotations part.

## What it produces (60 games, share of a side's snaps)

| Group | Starter | Next on the depth chart | Rests per game for the starter |
|---|---|---|---|
| Zeroback | about 74% (blowout benching takes the rest) | about 12% | 0 |
| Keeper | about 82% each of two | rarely | 0 |
| Offensive Line | about 76% to 84% for the top five | 6% to 12% | 0.1 |
| Defensive Line | 82%, 76%, 70%, 64%, 60% | 36%, 30% | 0.3 |
| Viper and flankers | offense plus two-way defense; about 53% of all snaps | about 25% of all snaps | 1.3 to 1.6 |

Starters finish games at a median of 82 energy (10th percentile 63).

Full season (1,230 games): 62.0 points per team, home teams 47.7%, lower prestige team wins
35.3%, median margin 23. Carried fatigue after a season: median 3.7, 90th percentile 13.4.
Benchmark: 59.1 points, 3.7 touchdowns, 3.2 snap kicks, 1.9 field goals per team. `tests/`
passes (72).

## Open

- Recruits do not roll a work rate yet; they use the derived value.
- Players' work rate does not develop between seasons.
- The rotation does not yet respond to a coach's personality (some coaches ride starters
  harder than others); every coach uses the same profiles.
