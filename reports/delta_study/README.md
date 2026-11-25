# Delta Yards matched on/off study

- Engine: `quarterback/viperball` main @ `8f4c988`
- Design: 3,000 random matchups from all 205 teams, neutral site, 1 in 3 games in rain. Each matchup was played twice with the same rosters, seed and weather: once with Delta Yards on, once with every post-score drive starting at the 20 (`delta_restarts_enabled=False`). 6,000 games total.
- Favorite = team with the higher mean overall rating across its top 22 players.
- CIs: 95% paired bootstrap over matchups (2,000 resamples).
- Reproduce: `PYTHONHASHSEED=0 python scripts/study_delta_yards.py --games 3000 --seed 20261125 --out reports/delta_study` then `python scripts/analyze_delta_study.py reports/delta_study > reports/delta_study/summary.json`. `games.jsonl` (about 16 MB) is not committed.

## Outcomes (per game)

| Metric | Delta on | Delta off | Diff | 95% CI |
|---|---|---|---|---|
| Favorite win rate | 64.7% | 64.1% | +0.6 pp | -1.4 to +2.7 |
| Mean final margin | 20.0 | 28.1 | -8.0 | -8.8 to -7.3 |
| Decided by 9 or less (one TD) | 24.6% | 17.6% | +7.0 pp | +5.0 to +9.0 |
| Decided by 5 or less | 14.5% | 10.1% | +4.4 pp | +2.7 to +6.1 |
| Lead changes | 2.23 | 1.78 | +0.45 | +0.35 to +0.53 |
| Winner trailed by 9+ at some point | 41.1% | 34.3% | +6.8 pp | +4.7 to +9.0 |
| Winner trailed by 18+ | 11.7% | 9.4% | +2.3 pp | +0.9 to +3.7 |
| Team trailing entering Q4 wins | 13.8% | 9.4% | +4.4 pp | +2.9 to +6.0 |
| Total points | 101.4 | 98.3 | +3.1 | +2.2 to +4.1 |

The win-probability slope per point of strength gap is unchanged (logit 0.093 on vs 0.094 off). Favorite win rate by strength gap:

| Strength gap | Games | On | Off |
|---|---|---|---|
| 0–2 | 532 | 56.6% | 51.1% |
| 2–5 | 740 | 57.6% | 57.6% |
| 5–10 | 948 | 62.0% | 63.9% |
| 10+ | 780 | 80.4% | 79.4% |

## Restarts and incentives

- 44,204 score restarts with Delta on. Mean shift 11.8 yards; 56% boosted, 34% penalized. 9.1% hit the floor at the 1-yard line and 0.8% hit the cap at the opponent's 20.
- Each yard of starting field position is worth 0.034 points (95% CI 0.033–0.036), from a regression of drive points on start yard line, controlling for strength gap. Across all drives starting at the 1 to the 50, the figure is 0.029 points per yard.
- So each point scored costs the scorer about 0.03 points of the opponent's next-drive value. Scoring is always worth it, by roughly 30 to 1.

## Caveats

- The same engine produces the data and implements the rule.
- Once any state differs, same-seed games diverge. Winners differ in 32.6% of pairs, but that is mostly path noise. Use the favorite win rate, not the flip rate, as the fairness measure.
- The strength proxy is crude: favorites with a gap under 2 win only 51–57% of games.
- The points-per-yard regression is observational. Teams that are trailing get better field position.
