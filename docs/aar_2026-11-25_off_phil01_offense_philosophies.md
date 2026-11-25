# AAR: OFF-PHIL-01, offense philosophies and a touchdown first Ground Control (November 25, 2026)

## What was asked

Ron wanted a gridiron style, touchdown first offense: run the ball, use kick passes to open the field, kick only if it has to. He asked what other offensive variation was missing. Then he asked for the plan to be built.

## What was wrong

1. **Every coach used the same kicking rules.** The 4th, 5th and 6th down kick choices were the same for every offense. Only snap kick range (`snap_kick_aggression`) varied.
2. **Most style settings were never read.** These settings did nothing for any offense: `kick_mode_aggression`, `red_zone_run_pct`, `early_down_run_rate`, `run_vs_lateral`, `early_down_aggression`, `option_rate`, `run_bonus`, `punt_aggression`, `field_position_priority` and `turnover_aversion`.
3. **The result: run teams were field goal teams.** Ground Control got 41% of its points from touchdowns, and Ironclad 38%. Pass heavy styles got 52%.
4. **Five offenses had no teams.** Ironclad, Six Shooter, Quick Strike, Mousetrap and Mismatch were on no philosophy list, so no AI team ran them.

## What changed (`engine/game_engine.py`, `engine/ai_coach.py`)

1. **Kicking philosophy by offense.**
   1. `kick_mode_aggression` (0.5 is the old shared behavior) now moves the 4th down stall kick, the 5th down snap kick and field goal thresholds, and the red zone kick on 6th down.
   2. A touchdown first offense keeps driving on 4th down, needs a longer 5th down and a surer kick before it gives up on the drive, and goes for it closer to the goal line.
2. **Go-for-it appetite by offense.** A new `go_for_it` setting (0.5 is the old behavior) moves the 6th down go line. Values run from Ironclad 0.2 to Chain Gang 0.75, and Ground Control is 0.7.
3. **Punting philosophy.** `punt_aggression` and `field_position_priority` move the 6th down punt line, so Ironclad punts from farther up the field.
4. **Play calling identity settings now work.**
   1. `red_zone_run_pct` inside the 20 and `early_down_run_rate` on downs 1 and 2 set the run share.
   2. `option_rate` sets option runs against downhill runs.
   3. `run_vs_lateral` sets how much of the ground game goes into lateral chains.
   4. `early_down_aggression` sets trick plays and jet sweeps on early downs.
   5. `turnover_aversion` cuts risky throws, chains and trick plays.
   6. `run_bonus` adds to run yardage.
5. **Ground Control is the touchdown first offense.**
   1. It has no snap kick or field goal plays in its play mix.
   2. Its settings: `kick_mode_aggression` 0.10, `go_for_it` 0.70, `early_down_run_rate` 0.65 and `red_zone_run_pct` 0.85.
   3. Its kick pass mix keeps mostly short kicks to loosen the defense.
6. **Style assignment.**
   1. The five unused offenses were added to the philosophy lists as niche choices.
   2. Ground Control is weighted up as a common philosophy. It now covers 13% of AI teams, up from 11%, and the share leader is Slick 'n Slide at 14%.

## Results

80 games per offense against a Balanced offense, per game for that offense's team:

| Offense | TDs before | TDs now | Share of points from TDs, before | Now | Field goals before | Now | Run share now | Wins vs Balanced, before | Now |
|---|---|---|---|---|---|---|---|---|---|
| Ground Control | 2.12 | 2.99 | 41% | 56% | 2.58 | 1.39 | 68% | 54% | 64% |
| Ironclad | 1.86 | 1.98 | 38% | 38% | 2.67 | 2.71 | 63% | 60% | 65% |
| Six Shooter | 2.05 | 2.05 | 39% | 37% | 2.19 | 2.96 | 65% | 50% | 52% |
| Stampede | 3.00 | 3.65 | 47% | 57% | 2.61 | 1.64 | 70% | 61% | 61% |
| Boot Raid | 2.77 | 2.54 | 47% | 45% | 2.10 | 2.25 | 36% | 52% | 38% |
| Balanced | 2.69 | 2.65 | 48% | 49% | 2.12 | 1.93 | 46% | 48% | n/a |

1. **The run teams now split in two.** Ground Control and Stampede are touchdown first. Ironclad and Six Shooter are run first, kick first teams.
2. **Against the whole field** (200 games, each team keeping its own style), Ground Control won 62%. The old Ground Control won 60%.
3. **An earlier version was too strong.** It had more power runs, fewer laterals and a 0.85 go-for-it, and it won 72% against the field. It held the ball so long that opponents averaged 11.5 drives instead of 13.3. That version was pulled back to the play mix it already had.

**League, per team per game:**

| | Before | Now |
|---|---|---|
| 200 random games: points | 52.0 | 52.3 |
| 200 random games: touchdowns | 2.74 | 3.02 |
| 200 random games: field goals | 2.19 | 1.77 |
| 3 real season weeks: touchdowns | 2.62 | 2.80 |
| 3 real season weeks: field goals | 2.28 | 1.91 |
| 3 real season weeks: points | 52.5 | 51.8 |

Scoring wasn't tuned toward any number.

## Also found

**A UI test was failing on main during this run.** `tests/test_ui_unslop.py` (from #380) tried to simulate a week while the season was still in the transfer portal phase. A season with a human team opens there, and has since #261. This run fixed it by skipping the portal first. #381 fixed the same test on main while this run was going, so main's version was kept at rebase.

## Tests

1. Before rebasing onto #381 and #382, `tests`, `test_wvl.py` and `test_recruiting.py` passed (334). After the rebase, `tests` passed (290).
2. `test_season.py` runs clean.

## Not done

1. Chain Gang (20% wins against Balanced) and Lateral Spread (29%) were weak before this change and still are.
2. The style settings that still do nothing (`kick_rate` aside, any listed only in the style table) were not audited beyond the ten above.
