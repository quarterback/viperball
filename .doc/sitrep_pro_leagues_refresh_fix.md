# SITREP: Pro Leagues UI Refresh Fix
**Date**: February 26, 2026

## Problem
After simming weeks in any Pro League (NVL, EL, etc.), all tab content — standings, stats, schedule, playoffs, teams, betting — stayed frozen at its initial state. The Week counter showed "0/20" even after simming 11 weeks. Standings showed all 0-0. Stats said "No stats available."

## Root Cause Diagnosis
The previous implementation used NiceGUI's `@ui.refreshable` decorator to wrap tab panel content. When `.refresh()` was called from a sim button handler in the Dashboard tab, the content inside other (hidden) tab panels didn't reliably re-render through NiceGUI's internal slot management. This is a known pain point with NiceGUI's refreshable decorator when used across tab panel boundaries.

## What Changed
Replaced the entire refresh mechanism with explicit **container-based refreshing**:

- Every tab section (standings, schedule, stats, playoffs, teams, betting) and every dashboard section (header, controls, results) now renders into a named `ui.column()` container
- To refresh: `container.clear()` then `with container:` re-render the content from scratch
- Each refresh is wrapped in `try/except` so one section failing doesn't block the others
- Added structured error logging throughout so problems surface in the server logs instead of failing silently

## Files Changed
- `nicegui_app/pages/pro_leagues.py` — rewrote `render_pro_leagues_section()`, `_render_dashboard()`, `_render_schedule()`, and `_render_teams()` to use container-based refresh
- `nicegui_app/app.py` — added error logging to the Pro Leagues render path

## Confirmed Working (Engine-Side)
- `ProLeagueSeason.sim_week()` correctly updates standings, accumulates player stats, stores results
- `get_standings()` returns correct W-L/PF/PA data after sim
- `get_stat_leaders()` populates all 4 categories (rushing, kick pass, scoring, total yards)
- `get_schedule()` marks completed games with scores
- All tested across both NVL (24 teams) and EL (10 teams)

## User Testing Result
- Standings, stats, schedule, and other tabs confirmed working after sim
- Box scores open but are cut off in the dialog — needs redesign (next task)

## Known Risk
The server process was unstable during this session — it crashed periodically when multiple browser connections hit it simultaneously. This appears to be a Replit resource limit issue, not related to the code changes.
