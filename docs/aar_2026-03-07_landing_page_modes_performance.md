# After Action Review — Landing Page Modes & Performance Fix

**Date:** 2026-03-07
**Branch:** `claude/fix-landing-page-modes-1FCor`

## Mission

Fix broken landing page mode cards and improve page load performance on the Viperball NiceGUI app.

## Commits

| # | Hash | Summary |
|---|------|---------|
| 1 | `d78bdf1` | Fix landing page mode cards and improve load performance |
| 2 | `1b36b6e` | Improve performance: lazy imports, caching, and fix play_tab forwarding |

## Scope

9 files changed, +117 / -50 lines

## Issues Found & Fixed

### Critical — Mode Cards Broken

- **play.py** — Tab rendering used hardcoded mode keys that didn't match the tab panel names, so clicking "College Season", "Quick Game", etc. from the landing page opened blank panels.
- **play.py** — The `_render_tab()` function loaded content into detached containers because it ran inside a timer callback without the proper NiceGUI context. Rewrote to use `tab_panel` context correctly.

### High — Performance: Synchronous Disk I/O

- **dynasty_mode.py** — `load_teams_from_directory()` and `load_team_identity()` read every team JSON file from disk on every render. **Fixed:** cached in `shared` dict.
- **season_simulator.py** — `read_conferences_from_team_files()` re-read all team files on every render. **Fixed:** cached in `shared` dict.

### High — Performance: Eager Module Loading

- **play.py** — Four heavy page modules (game_simulator, season_simulator, dynasty_mode, dq_mode) were imported at module level, forcing all their transitive dependencies (pandas, plotly, engine) to load at startup. **Fixed:** moved to lazy imports inside tab render functions.

### Medium — Performance: P5.js Sketches

- **ambient_bg.js**, **nav_glow.js**, **page_transition.js** — All three sketches started immediately and ran continuously even when not visible. **Fixed:** added `isLooping()` guards and frame-rate throttling.

### Medium — UX Bug: play_tab Forwarding

- **app.py** — The initial sync render lambda `lambda n: _switch_to(n)` silently dropped `play_tab` kwargs, so mode cards couldn't direct to specific sub-tabs. **Fixed:** `lambda n, **kw: _switch_to(n, **kw)`.

### Medium — Deferred Imports in game_simulator.py

- **game_simulator.py** — `pandas` and `plotly` imported at module level. **Fixed:** moved to lazy imports inside the functions that use them.

## Known Remaining Items

| Item | Severity | Notes |
|------|----------|-------|
| `_simulate()` sync handler in game_simulator.py | Low | `load_team()` is blocking I/O but user-triggered, not on load path |
| `get_available_teams()` sync on initial load | Low | Unavoidable — home page needs team metadata before first paint |
| `_all_teams` vs `shared["teams"]` naming | Trivial | Two different data shapes; could benefit from a docstring |

## Testing Notes

- Mode card navigation should now correctly open the corresponding play tab
- Landing page should render faster due to deferred module loading and cached disk I/O
- P5.js animations should consume less CPU when idle
