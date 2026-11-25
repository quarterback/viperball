# Viperball analytics reference

The college season's **Analytics** tab opens the Viperball analytics portal. This is a statistical reference for the game being played, not a separate simulation. All observed data come from completed games in the selected session.

## Portal guide

| View | What to inspect |
|---|---|
| Overview | Completed-game coverage and team leaders |
| Players | WAR, ZBR, VPR, legacy WPA, yards, touchdowns, kicking and defensive statistics |
| Teams | Points for/against, drive efficiency, turnovers and kicking |
| Scoring | Six scoring channels, return TD splits, drive/non-drive totals, unaudited points |
| Expected points | Experimental exchange EP/EPA, matched realized net points and down/field-zone heatmap |
| Decision value | Observed conditional outcomes for continue offense, snap kick, field goal and punt |
| Delta & bonus | Drive buckets, scoring incidence, supported context contrasts |
| Deserve to Win | Published DTW and separate research model when supported |
| Play finder | Raw events or grouped splits, with game links |
| Drive finder | Raw drives or grouped splits by origin, zone, result and school |
| Team compare | Up to four teams, peer percentiles |
| Player compare | Up to four players, position-matched qualified peers |
| Glossary | Definitions and support rules |

Use team/opponent, conference, week, game scope and situational filters where applicable. Play searches support down, field zone, distance, period, margin, family, school, pressure and restart context. Change Group by to compare splits or individual records. Click a heatmap cell or split to drill down. Tables support sorting, column selection and CSV export. Player totals use the whole selected season rather than play filters. The portal is currently college-session scoped, not a cross-era or all-league database.

## Six scoring channels

| Method | Points |
|---|---:|
| Touchdown (rush, lateral, kick pass or return) | 9 |
| Snap kick (drop kick) | 5 |
| Field goal (place kick) | 3 |
| Safety | 2 |
| Pindown | 1 |
| Bell | 0.5 |

A blocked kick returned for a touchdown may also carry a bell, for 9.5 points. Snap possession identifies the side that started the play; actual score changes identify who scored. A return TD belongs to the scoring defense or special teams as applicable. Do not use mutable possession to assign a score. The score ledger (engine/box_score_ledger.py) uses final play snapshots and half-open drive spans. Unknown methods, units and players remain unknown. Do not infer missing categories from residual score arithmetic.

**Offensive PPD** = eligible offensive drive points / drive segments. The engine excludes non-drive return TDs, bells and safeties, and includes pindown points when the kicking side owns the drive. Sum drive and non-drive points to reconcile to the scoreboard. A pindown alone does not count toward TD/made-kick incidence. Rates use summed denominators, not an average of individual game percentages.

## Other observed metrics

| Metric | Reading |
|---|---|
| Conversion rate | Successful conversions relative to relevant attempts; inspect down/zone splits. |
| Turnover margin | Forced minus lost, using snap-side credit; includes fumbles, downs and kick-pass/lateral interceptions. |
| Lateral efficiency | Successful lateral activity, excluding intercepted chains from successes. |
| Kick accuracy | Made kicks / attempts; examine drop and place separately. |
| Total yards | Rushing + kick-pass yards. Lateral yards are already in rushing, so do not add them again. |
| Defensive interceptions | Kick-pass plus lateral interceptions. Interception return TDs are separate from offensive touchdowns. |
| Workload | Snap participation, shifts, carries, touches and fatigue; do not treat these as interchangeable. |

The existing player WAR is a yards-above-positional-replacement heuristic with volume scaling. ZBR and VPR are position-specific composites; see the player aggregation and glossary for their calculation. Legacy player WPA is a play-value allocation, not a calibrated win-probability statistic. Defender WPA uses the negative offensive play value divided among credited defenders (PR #386). Do not describe any of these as a fitted replacement-value or causal player-impact model.

## Delta Yards and bonus possessions

After a score, the receiving side starts at clamp(20 − its score lead, 1, 80), subject to the engine's restart settings. Positive delta_cost is a penalty kill (lost field position); negative is a power play (gained field position); zero is neutral. Not every possession transfer is a Delta restart. Interceptions can award a delayed extra possession; bonus eligibility, cancellation and half boundaries are governed by [RULES.md](RULES.md).

Report the bucket's drive count, points, PPD, touchdown and made-kick incidence. Mess Rate is the difference between power-play and penalty-kill scoring percentages where supported, not the number of turnovers. Keep actual scoring separate from conditional model values.

## Expected points and decisions

The legacy EPA in engine/epa.py uses a fixed field/down lookup and partial score/possession handling. It is not a complete accounting of returns, bonuses and Delta value. Negative legacy EPA can coexist with a win.

The experimental model (engine/empirical_ep.py, net-possession-exchange-v1) estimates signed net points through the current and next possession, stopping at the half or OT period. Same-side restarts count as new possessions, not quarter fragments. It also learns one-possession continuation values.

EPA = immediate signed reward + signed remaining-horizon continuation value − pre-state value. Perspective changes with possession. Rolling two-possession EPA does not telescope across an entire game.

The portal trains on a bounded sample of earlier regular-season games and shows estimates on later games. Cells require at least 30 observations and eight distinct games, with hierarchical context pooling; a coarse match does not imply all state details match. A dash means unsupported or unavailable. The national offline study is a separate corpus and does not supply a pretrained model to this portal.

Decision value compares observed conditional net-point means in supported action groups. Above continue = selected action mean − continue-offense mean. Regret = best supported observed mean − selected mean. These are observational comparisons affected by play selection, roster, coaching and unmeasured conditions. They are not causal counterfactuals or player replacement values.

Delta/bonus context contrasts use sequential supported estimates: neutral field/no bonus → actual field/no bonus → actual bonus context. Delta and bonus differences reconcile by construction, not by establishing a causal entitlement effect. Report sample counts for each contrast separately.

## Deserve to Win

Published DTW (engine/dtw.py) is a descriptive weighted index of 13 postgame signals; team shares sum to one. A 55–45 separation is required before calling the outcome an upset. Expected wins sum these shares; ties count as half a win in the portal. Do not treat the shares as calibrated probabilities. Raw performance, Delta and bonus conversion are signed contributions, not independent causal effects.

The experimental retrospective outcome-alignment model uses a symmetric no-intercept fit on separate earlier games, evaluated on later games. It excludes quarter-win proxy from the candidate; it still uses postgame information and is not a pregame predictor or proof of deservedness. Research xW and matched legacy xW use only supported games. National held-out validation and coefficient replacement remain separate release decisions.

## Writing and research

Use [the rulebook](RULES.md), [culture/style guide](docs/CULTURE.md), and actual game events. Distinguish observed points, model estimates, sample size and uncertainty. Never invent possessions, individual credit, or imply a model value is an official score. Old benchmark rates are not current league norms; use a documented reference population and revision.

Technical references: [event/model AAR](docs/aar_2026-11-25_advanced_analytics.md), [portal AAR](docs/aar_2026-11-25_analytics_portal.md), [current development plan](docs/DEVELOPMENT_PLAN.md). See [ranking systems](docs/RANKING_SYSTEMS.md) for the independent ranking methods.
