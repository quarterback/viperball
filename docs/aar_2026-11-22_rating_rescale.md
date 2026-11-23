# AAR: Engine formulas moved to the current rating scale
## November 22, 2026

Plan agreed with Ron beforehand: (1) list every formula built for the old 60 to 100 ratings,
(2) fix them in groups, one commit per step, with numbers. The list is
`docs/rating_scale_inventory_2026-11-22.md`, committed first (`d69e91c`).

## Change to the plan

The plan named prestige as the first fix because it "drives most plays." Reading the code for
the inventory showed that is wrong: the prestige based team rating (`_should_use_halo`) has
been switched off since March, and every play uses individual ratings. The core contest went
first instead. Prestige was still fixed, last.

## What changed

One converter, `scale_rating(raw) = 60 + (raw - 15) * 0.5`, in `engine/game_engine.py`. Each
group reads ratings through it and has its own on/off switch in `V2_ENGINE_CONFIG`. Stored
player ratings are untouched.

| Step | Switch | Formulas |
|---|---|---|
| A | `rescale_contest` | Carrier vs tackler, kick pass contest, late-down defensive clamp |
| C | `rescale_speed` | Pursuit, defensive reads, end zone returns, best carrier bonus |
| C | `rescale_breakaway`, `breakaway_speed_baseline` (98) | Breakaway chance from team speed |
| D | `rescale_turnovers` | Lateral interception and fumble rates |
| E | `rescale_yac` | Yards after catch, kick pass distance, lateral yards, return talent, diving wing |
| F | (none) | Prestige derived from team average rating on the new scale; the median team goes from 16 to 50 |

Also fixed: a kneel on 6th down now turns the ball over instead of running to a 7th down.

## Numbers (benchmark, 200 games unless noted, per team per game)

| Step | Points | TDs | Snap kicks made | Turnovers | Median margin |
|---|---|---|---|---|---|
| Before (`1a55018`) | 40.5 | 3.10 | 2.02 | 1.92 | 25.5 |
| A: core contest | 34.8 | 2.28 | 2.38 | 1.92 | 20.2 |
| A + D turnovers | 34.9 | 2.26 | 2.41 | 1.89 | 18.5 |
| A + E yards after catch | 37.8 | 2.56 | 2.29 | 1.83 | 20.5 |
| A + D + E + C without breakaway | 37.7 | 2.46 | 2.37 | 1.83 | 18.5 |
| All groups, breakaway baseline 85 (the old value) | 55.0 | 4.45 | 2.21 | 1.91 | 23.5 |
| All groups, baseline 92 / 97 / 102 / 108 | 49.5 / 45.1 / 42.4 / 40.0 | 3.81 / 3.35 / 2.97 / 2.71 | 2.3 | 1.9 | 22.5 to 26.8 |
| **Final: all groups, baseline 98 (400 games)** | **44.3** | **3.30** | **2.18** | **1.90** | **23.5** |

Targets: 45 to 50 points, 1.9 to 3.5 touchdowns, 3 to 5 snap kicks.

## Findings

- **Breakaways were switched off by accident.** The breakaway formula assumed team speed of
  85. With team speed near 34, every team carried a 0.5 penalty and long runs almost never
  happened. Restoring it at the old baseline overshoots (55 points), so the baseline is now
  the dial for long touchdowns: 25% of touchdowns are 30+ yards, up from 6%.
- **Blowouts moved less than hoped.** Median margin went from 25.5 to 23.5. The share of games
  decided by 30+ ran between 30% and 39% across samples (42% before), and did not respond to
  the breakaway dial or to `base_yards_multiplier` (2.3 to 3.3 tested). The benchmark pairs
  teams at random across a league whose rosters run from 18 to 59 average rating, so many of
  its games are mismatches a conference schedule would not produce.
- **Snap kicks are flat at about 2.2.** The rescale did not move them.

## Not changed

`base_yards_multiplier` (2.3) and `power_ratio_exponent` (2.2): tested, no clear gain.

## Open

- `Season.simulate_game` never passes prestige to the engine, so every game runs at the
  default 50 vs 50 and overwrites each team's prestige with 50. Trap game and prestige
  decision logic are inert in season play.
- Measure margins on a real conference schedule before tuning blowouts further.
- Snap kicks at 2.2 vs a 3 to 5 target; field goals at 0.14.
