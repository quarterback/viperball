# AAR: calls, no calls and missed calls; one rating scale (November 24, 2026)

Branch `claude/rules-drift-sacks-ladder-fastsim` (PR #367), after the rules, drift, sacks,
ladder and fast sim run.

## What Ron asked

1. Real sports are full of no calls and missed calls; officials do not catch everything.
   Research the distinction and make the game work the same way, so the flag count comes
   down.
2. Convert the old rating scale too.

## 1. Officiating

### What the research says

- **Not every foul is a flag.** The NFL's officiating chief said holding that has no effect
  on the play and is away from the point of attack is let go, because no one wants a flag on
  every play (Dean Blandino). Holding is the most subjective foul; football people say it
  could be called on every play.
- **Misses outnumber bad flags.** The NBA's Last Two Minute reports grade every call and
  material non-call. Correct calls run about 96 to 98%, while incorrect non-calls ran 1.4 to
  2.5 per period against 0.1 to 0.2 incorrect calls.
- **Mistakes per game.** The NFL put its graded errors at about 4.3 to 4.5 a game in about
  160 plays, and claims about 98.9% accuracy.
- **Crews differ.** In one NFL season the strictest crew averaged 20.4 flags a game and the
  loosest 13.1. Points of emphasis move the count a lot (holding flags up 66% in the first
  two weeks of 2019).
- **Omission bias.** Officials lean toward not deciding a big moment with a whistle (Tobias
  Moskowitz, *Scorecasting*). The NBA's late game data does not show it within the last two
  minutes, so the effect here is modest.
- **College level.** About 6 accepted penalties per team per game (Action Network, 2020 to
  2024).

### What the game does now (`engine/officiating.py`)

The catalog rate is how often a foul happens. For each foul the crew decides:

- **Called:** a flag.
- **Let go (no call):** the foul did not affect the play, and the official leaves it.
- **Missed:** the foul mattered and no flag came.

Each class of foul has its own share that matter, its own chance a material foul is seen
and its own chance an immaterial one is flagged anyway:

| Class | Matter | Material seen | Immaterial flagged |
|---|---|---|---|
| Procedural (false start, offsides) | 95% | 92% | 40% |
| Blocking (holding, illegal blocks) | 30% | 70% | 6% |
| Coverage (interference, contact) | 55% | 68% | 12% |
| Safety (facemask, roughing, targeting) | 85% | 80% | 45% |
| Ball rules (forward laterals, kicks) | 90% | 85% | 35% |
| Conduct (taunting, celebration) | 30% | 80% | 8% |

Crews call tighter or looser (about plus or minus 20%, fixed per crew), a home leaning crew
misses a few more home fouls on judgment calls, judgment calls are let go more in the last
five minutes of a game within 9 points (0.85) and slightly more in playoffs (0.95). Crews
still throw the occasional flag for a foul that did not happen. This replaces the flat
"swallowed whistle" rate.

The box score's officials line shows flags, fouls let go, missed calls and bad flags.
README and RULES.md describe the rule.

### Result (200 matched games)

| Per game | Before | After |
|---|---|---|
| Fouls that happened | 27 | 27 |
| Flags | 28.8 accepted | 16.8 thrown, 8.4 accepted per team |
| Let go | | 7.6 |
| Missed calls | 0.03 | 3.0 |
| Bad flags | 0.5 | 0.5 |
| Penalty yards per team | 135 | 72 |
| Points per team | 57.5 | 51.7 |
| Touchdowns per team | 3.23 | 2.79 |

About 3.5 graded mistakes a game, 85% of them missed calls, as in the research. Scoring
falls because defensive flags were helping offenses.

## 2. One rating scale (PRO-01)

Every stored team file was on the old 60 to 100 scale, including the college files
(mean 79), which one off games and several benchmarks played directly.

- `scripts/convert_rating_scale.py` converts all 325 files and marks them.
  - College: player ratings re-rolled with the current roster generator by position, class,
    archetype and philosophy; names and everything else kept. Team stats take the new spread
    at each program's old league rank.
  - Pro, WVL and FIV: ratings and team stats through the inverse of `scale_rating`
    (old 70 is 35, slope 2), which keeps every gap between players and tiers.
- `engine/pro_scale.py` (the per game conversion) is removed.
- Moved to the new scale: pro development age curves (doubled), retirement cuts, WVL owner
  investment boosts, WVL career decline, synthetic free agents, salaries, the star player
  rejection rule, FIV tier attributes, mercenary cuts and team rating, stated attribute
  ranges, and the stats site's rating colors.
- AI scheme assignment reads current team stats through a quantile fit to the old spread, so
  each program keeps its scheme odds. Offense mix before and after: slick and slide 38 to 32,
  boot raid 28 to 27, east coast 25 to 26. Playbook personnel thresholds are rank mapped.
- Old WVL dynasty and career saves convert their old scale cards on load.

| WVL tier | Mean stat | Points per team |
|---|---|---|
| 1 | 67 | 71 |
| 2 | 50 | 56 |
| 3 | 37 | 50 |
| 4 | 23 | 44 |

NVL 44 points. FIV: developing nations 42, competitive 54, strong 60. Real three week
college season 53.9 points and 2.90 touchdowns per team; matched benchmark 51.1 and 2.72.

Tests: 200 pass, plus the five root scripts and the box score reconciliation smoke.

## Not verified

Live site. A multi season WVL dynasty played through the app.

## Open

- `engine/fast_sim.py` is reachable only with `use_fast_sim=True`; its formulas still assume
  the old scale.
- WVL tier 1 scores 71 a team, one point over the README's college range.
