# Viperball game modes and features

Current implementation reference, November 25, 2026. This replaces the old Streamlit integration guide. See [DEVELOPMENT_PLAN](docs/DEVELOPMENT_PLAN.md) for unresolved work, and [the rulebook](RULES.md) for playing rules.

## Game engine

The full play engine resolves six-down possessions using player contests, formations, run, lateral and kick-pass families, snap and place kicks, punts, returns and legal recoveries. Six score channels include fractional bells. Delta restarts adjust field position after scores; interception-generated bonus possessions have their own rules. Game plans combine offensive and defensive schools, actual callers, installed packages and staff discretion. The defensive system records committed and actual rushers, pressure, sacks and participant credit.

The engine tracks field participation, two-way midfield shifts, position-specific fatigue, work rate, recovery, substitutions, carryover, injuries and officiating. Conditions vary by period, venue, surface, roof, wind direction and altitude. These systems interact; no generic guaranteed win or scoring target is implied.

## College and dynasty

| System | What happens |
|---|---|
| College season | Configurable programs, conference schedules, polls, standings, bowls and playoffs. |
| Dynasty | Year-by-year progression, recruiting, NIL, transfers, retention, development, awards, staff contracts and histories. |
| High school | Persistent school/player identities and actual competition cohorts feed college recruiting; regular games use a fitted quick model and major postseason rounds use the full engine. |
| Recruiting | Tracked senior cohorts, geography, roster needs, rating/scouting information and CPU tactical fit; real graduating reserve for walk-ons before emergency generation. |
| Coaching | HC, OC, DC, STC and funded position assignments; actual callers, weekly plans, bounded learning, hiring and retirement, mentorship and former-player entry. |
| Player development | Talent ladder and current rating scale, permanent growth, work rate, class progression and position instruction. |
| History | Career tracker, graduates, alumni, season archives, award records and connections to other competitions. |

The active game-day roster is 36 players, with 11 on the field. Team counts and conference sizes come from data and configuration; refer to [CVL competition rules](COLLEGE_RULES.md). No old-save migration is required for the current development work.

## Other competitions

Professional leagues use the parameterized ProLeagueSeason framework for NVL, EL, AL, PL and LA and support a Champions League. WVL has a separate multi-tier system with ownership/career, commissioner, promotion/relegation, recruitment/free agency and financial mechanisms. International FIV provides national teams, continental competition, world rankings and World Cup play. Full-engine pro, WVL and FIV results are distinct from the quicker high-school regular-season model.

## Reporting and research

The stats site provides season, team, player, coach, referee and game reference pages, plus archives and exports. All new score channels and drive totals are reconciled against the final scoreboard. Pick-sixes belong to defensive return scoring, not offensive player touchdowns; defender interceptions and WPA have explicit participant credit.

The thirteen-view college analytics portal includes searchable play/drive records, grouped situational splits, leaderboards, scoring, EP/EPA, decision value, Delta/bonus, DTW, comparisons, heatmaps, customizable columns and CSV. Experimental values are estimated from a supported sample of earlier games, evaluated on later games, and remain distinct from legacy statistics. See [ANALYTICS.md](ANALYTICS.md).

## Development

Use [ENGINE_README.md](ENGINE_README.md), [COACHING_SPEC.md](COACHING_SPEC.md), [tactical schools](docs/OFFENSE_SCHEMAS.md), and [architecture](ARCHITECTURE_STATS_SITE_AND_RECRUITING.md). Dated AARs document experiments and findings at their respective revisions, not permanent gameplay targets.
