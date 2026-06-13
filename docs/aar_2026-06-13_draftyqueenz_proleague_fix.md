# AAR: DraftyQueenz ProLeague Season Bug Fix

**Date:** 2026-06-13  
**Scope:** Fix "No games to bet for week N" in DraftyQueenz when running a ProLeague (CVL/NVL) season  
**File changed:** `api/main.py` — `dq_start_week` function

---

## Problem

DraftyQueenz Board showed "No games to bet for week 6" on a 2026 CVL ProLeague season.
The issue was confirmed across all weeks — no game data was reaching the sportsbook.

## Root Cause (Three Bugs in One Line)

`dq_start_week` in `api/main.py` contained:

```python
week_games = [g for g in season.schedule if g.week == week and not g.completed]
```

This line was written for **College seasons**, where `Season.schedule` is a flat
`List[Game]` and each `Game` has `.week` (int) and `.completed` (bool).

**Bug 1 — nested list:** `ProLeagueSeason.schedule` is `List[List[Matchup]]` — one inner
list per week. Iterating over it yields `List[Matchup]` objects, not `Matchup` objects.
Accessing `.week` on a list raises `AttributeError`, the route returns HTTP 500, and the
API client (`api_client.dq_start_week`) swallows the error as `{}`. The UI sees
`odds_resp.get("odds", [])` → empty list → "No games to bet."

**Bug 2 — attribute names:** Even if Bug 1 were fixed, `Matchup` has `home_key`/`away_key`
not `home_team`/`away_team`. `generate_odds` (in `engine/draftyqueenz.py:967`) accesses
`game.home_team` and `game.away_team` — another `AttributeError` inside odds generation.

**Bug 3 — no completion flag:** `Matchup` has no `completed` attribute. ProLeague tracks
completion via `season.current_week`: a game is done when its `week_num <= current_week`.

## Fix

Replaced the single broken line with season-type–aware logic in `dq_start_week`:

```python
from engine.pro_league import ProLeagueSeason
from types import SimpleNamespace
if isinstance(season, ProLeagueSeason):
    week_idx = week - 1
    if week <= season.current_week or week_idx < 0 or week_idx >= len(season.schedule):
        week_games = []
    else:
        week_games = [
            SimpleNamespace(
                home_team=season.teams[m.home_key].name if m.home_key in season.teams else m.home_key,
                away_team=season.teams[m.away_key].name if m.away_key in season.teams else m.away_key,
                week=m.week,
                matchup_key=m.matchup_key,
                home_key=m.home_key,
                away_key=m.away_key,
            )
            for m in season.schedule[week_idx]
        ]
else:
    week_games = [g for g in season.schedule if g.week == week and not g.completed]
```

`SimpleNamespace` gives each Matchup the `home_team`/`away_team` shape `generate_odds`
and `build_pool` expect, without touching those functions. College season path unchanged.

## Error Report

| # | Location | Error type | Symptom |
|---|----------|-----------|---------|
| 1 | `api/main.py:4675` | `AttributeError: 'list' object has no attribute 'week'` | 500 → API client returns `{}` → empty odds |
| 2 | `engine/draftyqueenz.py:975` | `AttributeError: 'Matchup' object has no attribute 'home_team'` | Would trigger if Bug 1 were fixed alone |
| 3 | Same line | `AttributeError: 'Matchup' object has no attribute 'completed'` | Same |

All three errors were silent: the NiceGUI `run.io_bound` call returned `{}` and the UI
fell through to its "No games" empty state rather than surfacing the 500.

## What Was NOT Verified

- No live ProLeague session was available in this environment to test against a real DB.
  The fix was validated by code inspection only. Verify with a real CVL session: start
  DQ, advance to the first unplayed week, confirm game cards appear on the Board.
- `_get_prestige_map` returns a dict keyed by team key or team name — unverified. If keyed
  by team key and `generate_odds` now looks up by name, all prestige lookups will return
  the default (50). Functional but not ideal; worth checking if odds feel flat.
- College season DQ path is unchanged and was not re-tested.
