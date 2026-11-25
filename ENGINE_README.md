# Viperball simulation engine

Python engine for the college, professional, women's professional and international competitions. The current application uses the same full-engine mechanics across these modes, except the fitted high-school quick model for ordinary rounds (state finals and later major rounds run on the full engine).

## Run and inspect

Install dependencies as in [QUICKSTART.md](QUICKSTART.md). To run the web application use `python main.py`. The CLI accepts `python simulate_game.py <home_team> <away_team> [--tempo uptempo|standard]`; see the script and actual school identifiers in data/teams. To call the engine directly:

```python
from engine.game_engine import ViperballEngine, load_team_from_json

home = load_team_from_json("data/teams/<home-file>.json")
away = load_team_from_json("data/teams/<away-file>.json")
result = ViperballEngine(home, away, seed=20261125).simulate_game()
print(result["final_score"])
```

Replace the placeholder paths with actual JSON files. For complete seasons and dynasty persistence, use the application API rather than manually looping individual games.

## Modules

| Concern | Source |
|---|---|
| Play resolution, contest mechanics, schools, formations and clock | engine/game_engine.py |
| Tactical callers, packages, roster fit, installation | coach_tactics.py, defensive_commitments.py, playbook_catalog.py, team_installation.py, ai_coach.py |
| Coaching employment and learning | coaching.py, coaching_portal.py, coach_career.py, coach_roles.py, coach_learning.py, coach_school_continuity.py, position_staff.py |
| Recruiting and development | recruiting.py, coach_recruiting_fit.py, college_feeder.py, roster_continuity.py, transfer_portal.py, development.py, talent.py, rating_scale.py |
| Weather, penalties, injuries | weather.py, officiating.py, injuries.py |
| Seasons and careers | season.py, dynasty.py, player_card.py, player_career_tracker.py, hs_league.py |
| Other leagues | pro_league.py, wvl_season.py, wvl_dynasty.py, wvl_career.py, wvl_commissioner.py, fiv.py |
| Results and research | box_score.py, box_score_ledger.py, viperball_metrics.py, epa.py, dtw.py, analytics_events.py, empirical_ep.py, dtw_research.py, fingerprint.py |
| Persistence and interface | engine/db.py, api/main.py, stats_site/router.py |

The 11 physical/technical attributes in rating_scale.py use the current scale; a median player is around 35 and stars can reach the 60s–80s. Legacy formula conversion maps current 35 to old 70, with half a legacy point per current point. Do not reuse old 60–100 thresholds on current player ratings. Coach attributes are a separate scale.

## Result contract

A game emits final_score, stats, player_stats, drive_summary and play_by_play, along with tactical, weather, injury and other game context. Score snapshots determine awarded points and scoring side. Explicit drive spans attach only eligible offensive scoring to a drive. Snap possession differs from resolution possession and score credit. A return TD or a bell must not inflate an originating offense's scoring. Defender participants are exported as defenders; defensive interceptions and interception TDs are separate from offensive TDs. Lateral yards are included in rushing, not added again to total yards. Failed-challenge timeouts are counted; remaining timeouts refer to the current half/OT.

AN-02 adds pre-resolution and immediate resolution state to new plays, with a versioned adapter for possession transitions, scoring, bonus provenance and unknown attribution. [Analytics](ANALYTICS.md) describes the finite-horizon experimental value model. Keep existing public metric definitions explicit.

## Validate

```sh
python -m pip install pytest
python -m pytest -q tests
PYTHONHASHSEED=0 python scripts/benchmark_analytics_clarity.py --games 12
PYTHONHASHSEED=0 python scripts/benchmark_boxscore_reconciliation.py --games 8 --seed 20261124
PYTHONHASHSEED=0 python scripts/benchmark_advanced_analytics.py --games 48
PYTHONHASHSEED=0 python scripts/benchmark_dynasty_tactics.py --seasons 3 --teams 16 --seed 20261124 --out reports/dynasty
```

For national validation use scripts/benchmark_national_dynasty.py with --seasons 2 --analytics and independent seeds. Use --longitudinal on the dynasty benchmark for multi-year cohort and staff observations. Reports are evidence for their revision and seed, not proof of future balance. The current integrated workflow also checks the rulebook and box-score credit through regression tests; no byte-identical historical stat output is required after accounting corrections. Do not change rules or gameplay to make analytics look better.

See [RULES.md](RULES.md), [coaching specification](COACHING_SPEC.md), [tactical schools](docs/OFFENSE_SCHEMAS.md) and [current queue](docs/DEVELOPMENT_PLAN.md).
