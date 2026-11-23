# AAR: Blowouts, snap kicks and prestige
## November 22, 2026

## What was asked

Ron: stop reporting leftovers one round at a time; fix the blowouts, snap kicks and prestige.

## What changed

| Area | Change | Setting (`V2_ENGINE_CONFIG`) |
|---|---|---|
| Blowouts | How much a rating gap counts is now a dial. A median player still plays as 70; each rating point above or below counts 0.3 instead of 0.5. | `rating_scale_slope`: 0.3 |
| Snap kicks | Coaches shoot sooner once in range: on 4th down with 4+ yards to go (was 10+), on 5th down with 1+ (was 4+). Still never on downs 1 to 3 except late in a half. | `kick_4th_down_min_ytg`: 4, `kick_5th_down_min_ytg`: 1 |
| Snap kicks | Defense tightens more near the goal line, so more drives stall in range. | `field_compression`: 0.4 (was 0.25) |
| Points | More breakaways, to replace the touchdowns that compression removes. | `breakaway_speed_baseline`: 92 (was 98) |
| Prestige | The engine keeps each team's own prestige when the caller passes none. It used to overwrite every team with 50 on its first game, so the underdog surge and trap game logic never saw a favorite. | `ViperballEngine.__init__` |
| Benchmark | `--season WEEKS` sims a real season through the app's own code. Fresh rosters are now seeded so runs repeat. | `scripts/benchmark_engine.py` |

## Result: a full real season (1,200+ games), per team per game

| | Start of day | Before this run | Now | Target |
|---|---|---|---|---|
| Points | 40.5 | 44.6 | 47.6 | 45 to 50 |
| Touchdowns | 4.2 | 3.2 | 3.1 | 1.9 to 3.5 |
| Snap kicks made | 0.3 | 2.4 | 3.0 | 3 to 5 |
| Median margin | 32 | 23.5 | 19.5 | |
| Games decided by 30+ | 54% | 33% | 27% | |
| Games within 9 points | | 21% | 26% | |

All three scoring targets are met. `tests/` passes (72). No plays on 7th down or later.

## What the blowout work found

- **A real season is as lopsided as random matchups.** Conference games had the same margins
  as all games, so conferences are not grouped by strength.
- **Evenly matched teams play close.** With a roster gap under 3 rating points the median
  margin was 8 to 14.5.
- **The league is very uneven.** 36% of matchups pair teams 15+ rating points apart. Before
  the change those games averaged 63 to 27, and the favorite won 96% of them.
- **What did not move margins:** `power_ratio_exponent` (2.2 to 1.4), the breakaway baseline,
  `base_yards_multiplier`, and switching off composure, stars, hero ball, fatigue tiers or
  defensive adaptation.
- **What did:** the rating gap dial. At 0.35 the 30+ share fell to 27%; at 0.25 to 24%, with
  favorites in the widest mismatches still winning 82%. 0.3 is the setting.

## Limits

- 27% of games are still decided by 30+. Lower slopes keep reducing that but also make the
  best teams lose to the worst more often. The rest of the gap comes from the size of the
  talent spread itself (team average ratings from 18 to 59), which is a roster generation
  question, not an engine one.
- Field goals are still rare (0.13 per team). A snap kick is worth more whenever both are in
  range, so coaches almost always take the snap kick.
