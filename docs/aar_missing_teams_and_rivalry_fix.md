# After-Action Report: Missing Teams in Ratings & Rivalry Fix

**Date:** 2026-03-25
**Issue:** Composite ratings showed 197/200 teams; inaccurate rivalry assignments
**Severity:** High — 3 teams completely invisible in all rankings and stats

## Problem

The ratings page header declared "200 teams" but the composite rankings table only
listed 197 teams. Three teams were missing entirely:

1. **Mississippi Valley State** (Heritage League)
2. **North Dakota State** (Northern Shield)
3. **Pepperdine** (Mountain West)

Additionally, the auto-assigned rivalries were geographically generated without
any knowledge of real-world college rivalries, producing nonsensical pairings
like Purdue-Rutgers instead of Penn State-Rutgers.

## Root Cause Analysis

### Missing Teams

The `realign_conferences.py` script (which executed the 200-team conference
realignment) created new team files for NDSU and Mississippi Valley State using
a template-copy approach. During creation, it ran:

```python
ti.pop("school", None)    # line 162 — removes 'school' key
ti["school_name"] = school_name  # sets school_name instead
```

This left the three teams with `school_name` but no `school` key. While most
code paths have a fallback (`get("school") or get("school_name")`), **the
composite ranking system (`engine/ranking_composite.py`) builds its team list
exclusively from completed games** (lines 2436-2438):

```python
all_teams: set = set()
for g in games:
    all_teams.add(g.home_team)
    all_teams.add(g.away_team)
```

If a team plays zero games, it never enters the rankings at all. The schedule
generation algorithm in `engine/season.py` (`_generate_partial_schedule`) uses
multi-pass non-conference fill with 3 passes (lines 1404-1415, 1417-1444) and
an FCS filler fallback (lines 1446-1455). However, with 200 teams competing for
limited game slots, edge cases in the pairing algorithm can leave some teams
with no opponents — particularly when the combination of conference size,
geographic isolation, and pair-exclusion logic conspires against a team.

**Key lesson:** The ranking composite has no safeguard to include teams that
exist in the season but played zero games. There is no validation step that
checks `len(ranked_teams) == len(season.teams)`.

### Rivalry Assignment

The `auto_assign_rivalries()` function (season.py:3267) assigns rivals purely
by geographic proximity using state-neighbor distance. It had no knowledge of
real-world rivalries. The only "protected" rivalry was Colorado State vs Wyoming
(from `data/rivalries.json`), and even that entry had the wrong team name
("University of Wyoming" instead of "Wyoming").

## Changes Made

### Team Roster Changes
| Action | Team | Conference | Replaces |
|--------|------|-----------|----------|
| Added | North Carolina Central | Heritage League | Pepperdine |
| Added | Lafayette | Midwest States | Saint Louis |
| Moved | Sacramento State | Moonshine League | (was Galactic League) |
| Fixed | Mississippi Valley State | Heritage League | (added `school` field) |
| Fixed | North Dakota State | Northern Shield | (added `school` field) |
| Deleted | Pepperdine | — | — |
| Deleted | Saint Louis | — | — |

### Conference Size After Changes
| Conference | Teams |
|-----------|-------|
| Galactic League | 10 (was 11) |
| Heritage League | 13 (was 12) |
| Moonshine League | 10 (was 9) |
| Mountain West | 11 (was 12) |
| All others | unchanged |

### Rivalry System Overhaul

Replaced the single-entry `data/rivalries.json` with 43 protected rivalries:
- **33 conference rivalries** (e.g., Ohio State-Michigan, Alabama-Auburn,
  Army-Navy, Oregon-Oregon State)
- **10 non-conference rivalries** (e.g., Kansas-Missouri Border War,
  Pittsburgh-West Virginia Backyard Brawl, Florida-Florida State)

All entries use correct team names matching `school`/`school_name` in team JSON
files.

### Files Modified
- `data/teams/north_carolina_central.json` — new
- `data/teams/lafayette.json` — new
- `data/teams/pepperdine.json` — deleted
- `data/teams/saint_louis.json` — deleted
- `data/teams/sacramento_state.json` — conference field updated
- `data/teams/mississippi_valley_state.json` — added `school` field
- `data/teams/ndsu.json` — added `school` field
- `data/conferences.json` — rebuilt from team files
- `data/cvl_conference_directory.txt` — rebuilt with rivalry section
- `data/rivalries.json` — complete rewrite with 43 protected rivalries
- `scripts/realign_conferences.py` — TARGET dict updated

## Prevention Checklist

To prevent similar issues in the future:

1. **Always include the `school` field** when creating team JSON files. Use
   both `school` and `school_name` for maximum compatibility.

2. **Validate team counts after schedule generation.** Add an assertion:
   ```python
   scheduled_teams = {g.home_team for g in games} | {g.away_team for g in games}
   assert scheduled_teams >= set(self.teams.keys()), \
       f"Unscheduled teams: {set(self.teams.keys()) - scheduled_teams}"
   ```

3. **Validate team counts in composite rankings.** The ranking system should
   include all season teams, even those with 0 games (ranked last).

4. **Use protected rivalries** for all well-known real-world matchups rather
   than relying on geographic auto-assignment alone.

5. **After any realignment script runs**, verify:
   - `ls data/teams/*.json | wc -l` equals expected count
   - Every team file has both `school` and `school_name` fields
   - Every team's `conference` field matches `conferences.json`
   - Run a test simulation and confirm all teams appear in standings
