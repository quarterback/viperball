# AAR: Game day form, work rate fatigue, and an organic home field
## November 23, 2026

## What Ron said

- No guaranteed blowout or close game rate. Margins should float out of the play.
- A 60% home win rate is unnatural unless it comes from something that happens in the game.
- Use the baseball game's logic, with a work rate and a fatigue rating or bar.
- Also do the one roll per game from the previous reply.

## What the baseball game does (`quarterback/hybrid-baseball`)

- `o27/config.py` `LOCKED_FORM_*` and `o27/engine/prob.py`: one shared hot or cold draw per
  team per half feeds every channel at once (slugging, running, clutch), so a good night
  compounds instead of averaging out. Its mean leans with the team's best hitter.
- `o27v2/config.py` `HOME_ADVANTAGE_SKILL = 0.0`: the flat home bonus was removed; any home
  edge has to emerge from travel, wellness, fatigue and park.
- `FATIGUE_DEBT_*`: workload carries across games against a stamina budget.

## What Viperball did

| Finding | Detail |
|---|---|
| Flat home bonus | `_apply_home_field_boost` added +1 to +6 to six ratings for every home player. On the current rating scale almost every player got +6. Home teams won 61%. |
| No away bias underneath | With the bonus off and every matchup played both ways (800 games), home teams won 49% to 50%. |
| Fatigue did nothing | Only the ball carrier and tackler lost energy, and every change of possession refunded 3 to 5 to the whole team. Timeouts and stoppages refunded 10 to 15. An offensive starter recovered 0.5 a snap on the sideline while her defense played. Median energy at the final whistle was 100, and the fatigue curve had no cost above 80. |
| Fatigue tiers on the old scale | Tier cutoffs 82 and 62 were for 60 to 100 ratings, so nearly every player sat in the low tier. |
| Snap counts | Every available player was credited with every snap, starters and bench alike, so snap counts could not measure workload. |

## Changes

**`engine/game_engine.py`** (settings in `V2_ENGINE_CONFIG`)

| Change | Settings |
|---|---|
| Flat home bonus off | `home_field_boost`: False |
| Travel: the away team starts with less energy by distance (same state 0, same region 2, same zone 4, next zone 6, cross country 9), using `engine/geography.py` regions | `travel_fatigue` |
| Form: one roll per team per game, mean leaning with the team's best player, times one roll per half; clamped; multiplies every contest rating (runs and laterals, kick passes on both sides, the late down clamp) | `form_game_sigma` 0.05, `form_half_sigma` 0.03, `form_star_weight` 0.003, `form_star_pivot` 88, `form_min` 0.85, `form_max` 1.18 |
| Work rate: every on-field player (5 skill starters and the 5 best linemen on offense, the 5 defensive starters on defense) spends energy every snap, scaled by stamina; sideline players recover a little | `work_rate_per_snap` 0.6, `bench_recovery_per_snap` 0.1 |
| Smaller refunds: change of possession and timeouts or stoppages; halftime unchanged at 30 | `drive_change_recovery_off` 0.5, `drive_change_recovery_def` 0, `stoppage_recovery` 4 |
| Gradual fatigue cost: 0.4% per energy point below 100, meeting the old curve at 60; the cliff below 40 is unchanged | `fatigue_curve_linear`, `fatigue_curve_slope` 0.004 |
| Fatigue tiers read ratings through `scale_rating()` | |
| New per-player `game_field_snaps` counts snaps actually on the field | |
| Result gains `game_day`: travel cost, each team's form (game and halves), and each player's starting and ending energy | |

**`engine/season.py`**: `_carry_workload` carries 30% of a player's end-of-game fatigue into
her next game, scaled by stamina, with 35% of older carried fatigue kept each week (cap 20).
The engine starts each player at 100 minus carried fatigue minus travel.

**React box score** (`web/src/pages/league/GameBoxScore.tsx`): an Energy column with a bar
for each player's energy at the final whistle and her starting energy when below 100.

**README**: new Game Day section (form, work rate and fatigue, home field and travel).

## What floated out

No margin or close game target was set. Settings were chosen so that fatigue actually
registers (starters dip below 80 in some games) and scoring stays in the README range.

| | Before (bonus on, fatigue inert) | Season, seed 2026 | Season, seed 7 |
|---|---|---|---|
| Home win | 61% | 48.2% | 50.1% |
| Lower prestige team wins | | 38.1% | 36.7% |
| Blowout (margin 30%+ of combined score) | 6% | 15% | 14% |
| Close (margin 7% or less of combined score) | 16% | 19% | 22% |
| Points per team | 60.6 | 60.2 | 61.1 |
| Starters' end energy, 10th percentile / median | 98 / 100 | 71 / 92 | 70 / 91 |
| Carried fatigue after a season, 90th / 99th percentile | none | 6.4 / 14.4 | 7.0 / 15.4 |

Home edge measured on 800 mirrored games: 51.9% with travel, 49.6% without. In a
conference season travel is shorter, so the edge is smaller, and the two seasons above
(48.2%, 50.1%) are within noise of 50%.

For scale, from published data: FBS conference games are decided by 17+ points 41.6% of the
time and within one score 38.6% (CBS Sports, 2014 to 2024); AFL games were won by 10+ goals
about 18% of the time and within two goals about 22% (2003 to 2013).

`tests/` passes (72). Benchmark (300 games): 61.2 points, 3.9 touchdowns, 3.3 snap kicks,
1.8 field goals per team.

## Open

- Home field is now about even. Real sports run 55% to 60% home wins. If the game should have
  more home edge, it has to come from another organic source (crowd noise on the away
  offense, familiarity with the home field) rather than a ratings bonus.
- Coaches still rest players only below 45 energy (30 in the first half); with fatigue now
  biting, depth and rotation logic may deserve a look.
- The fatigue bar is in the box score only; roster and My Team pages do not show carried
  fatigue yet.
