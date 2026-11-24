# AAR: rulebooks, touchdown drift, sack rate, talent ladder and the fast sim (November 24, 2026)

Branch `claude/rules-drift-sacks-ladder-fastsim`, built on the status check branch (#362).

## What Ron asked

Work on five items from the status check, in this order: the rulebooks, the touchdown and
turnover drift, the sack rate, player generation on the talent ladder, and the fast sim in
the pro and high school leagues.

## 1. Rulebooks (RULE-01)

`RULES.md` (v1.1) described a different game: five downs, 12 to 15 minute quarters, kickoffs
with touchbacks and onside kicks, a 2 minute warning, a 40 second play clock and positions
the game does not have (Shiftback, Line Anchors, Spotbacks, Lastback). `docs/RULES.md` was an
old copy of the README. `COLLEGE_RULES.md` described a 24 team poll league with 15 minute
quarters.

- `RULES.md` v2.0 is rewritten to the engine and the README. Its penalty table is generated
  from `PENALTY_CATALOG` by `scripts/build_rules_penalty_table.py`.
- The README's play clock said 25 seconds; the engine uses 40. The README now says 40.
- The README penalty tables had wrong rows (Fair Catch Interference is on the kicking team,
  not the defense) and said Illegal Forward Lateral is the only loss of down; there are
  four. The README now lists the most common fouls, all checked against the catalog, and
  points to RULES.md for the rest.
- The engine has no ejections, so the rulebook does not claim them.
- `docs/RULES.md` points to the two books. `COLLEGE_RULES.md` describes the 205 team CVL.
- `tests/test_rules_doc.py` checks the books against the engine (catalog, downs, clock,
  timeouts, challenges, scoring values) and plays three seeded games checking downs and
  scoring.

## 2. Touchdown and turnover drift

Matched games at each merge (`scripts/diag_scoring_drift.py`, 300 games, seed 2026) and ablations
on main found:

| Change on main | TDs per team | Points |
|---|---|---|
| Main as found | 2.51 | 52.0 |
| Defensive reads off | 2.69 | 53.3 |
| Defensive scheme effects off | 2.99 | 55.9 |
| Scheme tables centered (kept) | 2.99 | 55.5 |

- **Cause.** Every defensive scheme's play family table averaged below 1.0 (0.84 to 0.97),
  kick pass coverage was positive for all eight schemes and explosive suppression was below
  1 for most. These tables sat unused until DEF-02 (#325) turned them on, and then the
  average play lost 4.4%. This was the single largest drop (3.32 to 2.90 touchdowns).
- **Fix.** Schemes are now measured against the league's average scheme
  (`defense_scheme_centered`, `_defense_scheme_means`). Each scheme keeps its relative
  strengths: Drift still allows the fewest points and Swarm the most.
- **Turnovers.** The rise of about 0.3 per team in #351 was counting. Lateral interceptions
  on kick laterals were not counted before. Drives ending in a lateral interception stayed
  at 5% across every merge.
- **Rain penalties.** Weather added 0.003 to every one of the 19 to 34 fouls in a phase, so
  rain games had 34 accepted flags per team instead of 15. Weather now scales the rate
  (1.2 rain, snow and sleet; 1.1 heat).
- **Penalty level, not changed.** Clear weather games have about 14 accepted flags and 135
  yards per team, more than twice the NCAA average of 6 (Action Network, 2020 to 2024).
  `penalty_rate_scale` exists at 1.0. At 0.55 flags match the NCAA rate, but points fall
  from 52 to 49 because defensive flags help offenses. Logged as PEN-02.
- **Benchmark gap.** `scripts/benchmark_engine.py` loads teams without coaching staffs, so
  coach tactics and defensive packages never run in it. Real season runs (`--season 3`)
  are the check for those.

## 3. Sack rate

The rush contest put 12.9% of kick passes down as sacks, with pressure on 32%. Football runs
6 to 7% of dropbacks. `sack_rate_scale` 0.55 now sets how much of the contest's pressure ends
in a sack; the pressure share is unchanged. Matched games: sacks 6.9%, pressure 31.7%,
touchdowns 2.99 to 3.25. Real three week season: sacks 7.4%, pressure 33%.

## 4. Player generation on the talent ladder (ROST-01)

| | Old | New |
|---|---|---|
| Recruit class overall, 10th to 90th percentile | 23 to 47 | 14 to 58 |
| Opening roster freshmen | 13 to 58 | 13 to 58 |
| Lineman recruit speed | 55 (floor) | 29 |
| College growth, freshman to senior | +1.45 | +4.4 (roster class gap 4.4) |

- `engine/talent.py` uses the opening roster ladder for recruits, high school players and
  quick portal players. Stars follow the rolled level (5 stars is the top 3%).
- Old recruits rolled every stat flat inside a star band, so classes had no stars and no
  projects. Position boosts from the old scale floored lineman speed at 55.
- HS players sit 2 points a year below the college freshman they become; HS growth is about
  2 a year with the old cap of 75 removed. HS graduates match roster freshmen (33.5 mean).
- College development rounded the top of small gain ranges down, so a normal player grew
  about half a point a year. Gains are now drawn as fractions and `DEV_GAIN_SCALE` 2.1
  matches the roster class gaps.
- Work rate is now carried on recruits, player cards and dynasty roster fills.
- Four offline offseasons (graduate, develop, sign HS graduates): the league holds a mean of
  35 and team best players at a median of 72. On old main the same loop drove team best
  players from 73 to 49 and squeezed everyone into 26 to 47.
- `tests/test_talent_ladder.py` covers class shape, stars, lineman speed, HS classes and
  development.

## 5. Fast sim (SIM-01)

- Pro league weeks and playoffs, WVL tiers, promotion playoffs and WVL career mode run on the
  full engine. Fast sim WVL games scored 32 to 39 a team.
- Pro and WVL rosters and team stats are on the old 60 to 100 scale. Fed to the engine as
  they are, WVL tier 1 scored 85 a team. `engine/pro_scale.py` converts both rosters around
  the league mean for each game (38 on the current scale, WVL tiers 3 points apart) and
  restores every rating after, so pro development, free agency and valuations keep their
  scale. WVL now scores 55 to 59 a team with 3.2 touchdowns, 3.2 snap kicks and 2.1 field
  goals. NVL scores 51.
- WVL career mode already used the engine, with CVL graduates (current scale) on rosters of
  old scale pros. Graduates now convert to the pro scale when they join.
- WVL owner investment (0 to 8 strength points in the fast sim) now lifts game day form,
  0.006 per point.
- HS: about 7,200 games a season would take about 17 minutes on the full engine each dynasty
  offseason. State finals, regionals and national games (about 100) run on the engine; the
  rest stay on the quick model, refitted to the engine (47 points a team; it gave 16).
- Dynasty back history (`fast_sim_season`) still uses its own fast model.
- WVL full season on the engine takes about 2.5 minutes; NVL about 40 seconds.

## Final numbers

| | Main as found | This branch |
|---|---|---|
| Matched benchmark points | 52.0 | 57.5 |
| Touchdowns | 2.50 | 3.23 |
| Snap kicks | 3.46 | 3.26 |
| Field goals | 2.37 | 2.23 |
| Real season (3 weeks) points | 52.6 | 55.9 |
| Real season touchdowns | 2.51 | 3.03 |
| Sack rate | 12.5 to 13.1% | 6.9 to 7.4% |

Tests: 191 pass, plus the five root scripts.

## Not verified

Live site. A full dynasty run through the app with several offseasons (the offline loop
covers the talent pipeline only). Benchmarks are one or two seeds each.

## Open

- PEN-02: penalty level.
- PRO-01: move pro systems to the current scale and drop the per game conversion.
- HS regular season on the engine if offseason time allows.
