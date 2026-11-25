# Viperball efficiency glossary

This describes the season-record KenPom-style table in engine/season.py:kenpom_metrics. It is not the same as the audited offensive drive PPD in the Analytics portal.

| Metric | Current calculation |
|---|---|
| Raw O | Total points for / own drives × 10 |
| Raw D | Opponent points / opponent drives × 10 |
| Net rating | Raw O − Raw D |
| Adj T | Plays per game (pace; not opponent-adjusted) |
| EK% | (5/3 × snap-kick makes + place-kick makes) / attempts × 100 |
| Opp EK% | Same for opponents |
| TO% | Committed turnovers / own drives × 100 |
| TOD% | Forced turnovers / opponent drives × 100 |
| LR% | Successful laterals / lateral chains × 100, using recorded accumulators |
| FDR | Penalties drawn / own plays × 100 |
| RLE | Rushing yards / recorded carries |
| Opp RLE | Opponent rushing yards / estimated 15 carries per game; approximate |
| KP% / Opp KP% | Kick-pass completions / attempts × 100 |
| KP YPA | Kick-pass yards / attempts |
| Stop rate | Recorded defensive stops / opponent drives × 100 |
| Bonus conversion | Recorded bonus scores / bonus possessions × 100 |
| Pythagorean win share | PF² / (PF² + PA²), with nonzero floors |
| Pythagorean luck | Actual wins − expected wins from scoring |
| DTW luck | Actual wins − summed published DTW shares |

The season implementation guards empty denominators with one; an opening zero is not a measured performance rate. Weighted kick percentage can exceed 100 because a snap kick is worth more. Raw O includes all points for, whereas the portal offensive PPD excludes non-drive scores; do not interchange them. The season-record calculations are not opponent adjusted; independent ranking methods are documented in [RANKING_SYSTEMS.md](RANKING_SYSTEMS.md).

Use the actual league's observed distribution before calling a rate elite or poor. [ANALYTICS.md](../ANALYTICS.md) describes current score accounting, model support and other metrics.
