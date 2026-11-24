# AAR: fast sim removed, scoring floats, college and pro officiating levels (November 24, 2026)

Branch `claude/rules-drift-sacks-ladder-fastsim` (PR #367).

## What Ron asked

1. Get rid of the old fast sim entirely.
2. Stop benchmarking scoring against the README. Scoring should float on the game's
   mechanics; the 45 to 70 range was set when the rules were very different.
3. College referees are worse than pro referees and should be more spread out, high and
   low, because there are far more of them.

## 1. Fast sim removed

- `engine/fast_sim.py` is deleted. Pro league weeks, WVL tiers, the WVL commissioner and the
  NiceGUI screens lose their fast sim option; the "Full Engine (Box Scores)" switches are
  gone. Every game is a full engine game.
- College and dynasty back history used its own rating coin flip (`fast_sim_season`). It is
  now `history_season`: every history game is played on the engine and only records, titles
  and the final four are kept. A 16 team history year took 5 seconds; the 205 team league
  takes about three minutes a history year.
- Fast sim result handling is gone from the stats site, the three box score templates, pro
  box scores and DTW. Old saved games that were fast simmed show their scores and stats
  without drive summaries or a fast sim note.

The high school league keeps its quick model for regular season games (see Open).

## 2. Scoring floats

- `scripts/benchmark_engine.py` reports numbers with no targets and no ok or off marks.
- README drops the 45 to 70 point range and the sample 63 to 49 game. ANALYTICS.md and the
  game analysis text drop the range too.
- No engine setting enforces a scoring total; none were found.

## 3. Officiating levels

`engine/officiating.py` LEVELS, applied to every game's crew:

| Level | Mean accuracy | Accuracy spread | Strictness spread | Home lean spread |
|---|---|---|---|---|
| Pro (pro leagues, WVL, FIV) | 96.5% | half the pool | 9% | half the pool |
| College (default) | 94% | 1.5 times the pool | 18% | 1.5 times the pool |
| High school (HS title games) | 91% | twice the pool | 25% | twice the pool |

A less accurate crew sees fewer material fouls (accuracy cubed) and throws more bad flags.

200 matched games:

| | Pro | College |
|---|---|---|
| Flags a game | 17.8 | 16.4 |
| Missed calls a game | 2.3 (sd 1.75) | 4.0 (sd 3.4) |
| Bad flags | 0.35 | 0.46 |
| Crew accuracy range | 0.95 to 0.98 | 0.90 to 0.98 |

## Numbers now (real three week college season)

54.4 points, 2.88 touchdowns, 3.42 snap kicks, 2.13 field goals, 2.64 turnovers per team.
Median margin 19.5.

Tests: 201 pass, plus the five root scripts.

## Open

- High school regular season (about 7,100 games a year) stays on the quick model by Ron's
  decision; on the engine it would take about 11 minutes each dynasty offseason.
- Back history requested for many years will take about three minutes a year.
