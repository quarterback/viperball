# WVL Owner Mode Upgrade — Project Report

**Date**: March 3, 2026
**Scope**: Full upgrade of the Women's Viperball League (WVL) from thin spectator experience to robust Owner Mode dynasty
**Files Modified**: `nicegui_app/pages/wvl_mode.py` (1,603 lines), `engine/wvl_dynasty.py` (641 lines), `replit.md`
**Commits**: `558d488`, `99817ec`

---

## 1. Problem Statement

The WVL had a functioning 4-tier pyramid (64 clubs) with promotion/relegation, but the owner experience was shallow:

- The entire season simulated at once with a single button press — no week-by-week engagement.
- No roster viewer existed — the owner couldn't see their own players.
- Roster management was absent — no ability to cut or sign players during or between seasons.
- The offseason was a single silent function call with a brief summary popup.
- Financial information was buried in a tiny expandable section at the bottom of the page.
- The UI was a single scrolling page instead of an organized tab layout.
- CVL graduate import required manual file handling.

The goal was to transform WVL into a mode where the owner has meaningful decisions, visibility into their team, and a step-by-step offseason progression — matching the depth of the NVL Pro Leagues interface.

---

## 2. Architecture Decisions

### 2.1 Tab-Based UI (Container Refresh Pattern)

The WVL page was restructured into 5 tabs: **Dashboard**, **My Team**, **Schedule**, **League**, and **Finances**. This mirrors the NVL Pro Leagues pattern and provides clear information hierarchy.

Each tab renders into a dedicated `ui.column()` container. A shared `_refresh_all()` function clears and re-renders all containers when state changes (sim results, roster moves, etc.). This container-based refresh pattern was chosen over NiceGUI's `@ui.refreshable` decorator because it handles complex nested tab panels more reliably — a lesson learned from the NVL Pro Leagues implementation.

### 2.2 Engine-Side Roster Management

Five new methods were added to `WVLDynasty`:

| Method | Purpose | Guards |
|--------|---------|--------|
| `get_owner_roster()` | Returns full roster as list of dicts | Falls back to `_current_season` if `_team_rosters` empty |
| `cut_player(name)` | Removes player by name | Enforces minimum roster of 30; returns `(bool, str)` |
| `sign_free_agent(card, salary)` | Adds player to roster | Enforces maximum roster of 40; removes from FA pool |
| `get_owner_team_summary()` | Team overview (avg OVR, age, positions) | Handles empty rosters gracefully |
| `get_available_free_agents(count)` | Generates/returns cached FA pool | Caches in `_fa_pool` field |

The `_fa_pool` field (non-persisted) was added to the dataclass to cache free agents across interactions within a session.

### 2.3 Multi-Step Offseason Wizard

Rather than decomposing the `run_offseason()` engine method into separate step-by-step calls (which would have been a risky refactor of complex interdependent logic), the wizard uses a **compute-then-present** pattern:

1. `run_offseason()` executes once, producing a comprehensive summary dict.
2. The summary is stored in `app.storage.user["_wvl_offseason_data"]`.
3. The wizard presents the results across 8 interactive steps, with the user navigating forward/backward.
4. Interactive decisions (investment allocation) modify dynasty state directly during the wizard.
5. On final step completion, the offseason data is cleared and phase advances to pre-season.

This approach preserves engine integrity while providing the interactive experience.

### 2.4 CVL Graduate Pipeline

The CVL export system already cached graduates to `app.storage.user["cvl_graduates"]`. The WVL offseason now:

- Auto-detects cached graduates and passes them as `import_data` to `run_offseason()`.
- Shows a preview table of the top 15 graduates (name, position, school, OVR) in the Player Import wizard step.
- Also supports custom JSON import for user-created players, with the imported players added to both `_fa_pool` and the owner's roster.

---

## 3. Features Delivered

### 3.1 Dashboard Tab

- **Phase indicator**: Shows current phase (Pre-Season / In Season / Playoffs / Offseason).
- **Week counter**: Displays current week and total weeks during the season.
- **Record card**: Shows owner's W-L record, updated each week.
- **Sim controls**:
  - "Sim Week" — simulates one week across all 4 tiers, shows owner's game result as a notification.
  - "Sim Rest of Season" — fast-forwards through remaining regular season, auto-starts playoffs.
  - Fast/Full toggle — switches between `fast_sim` (instant) and full engine simulation.
- **Results table**: Running log of owner's game results with W/L row coloring.
- **Playoff advancement**: Single button to advance each playoff round.

### 3.2 My Team Tab

- **Summary metrics**: Roster size (X/40), average OVR, average age in card format.
- **Positional depth**: Badge display of position counts (e.g., ZB: 8, V: 12, FL: 10).
- **Full Roster sub-tab**: Sortable table with #, Name, Pos, Age, OVR (color-coded), SPD, KICK, LAT, TKL, Archetype, Dev trait, and Cut button per player.
- **Free Agents sub-tab**: Browse 25 available FAs with Sign button. Shows name, position, age, OVR, speed, kicking, archetype, and salary tier.
- **Roster enforcement**: Cut blocked below 30 players, sign blocked above 40.

### 3.3 Schedule Tab

- **Week picker dropdown**: Select any week to view matchups.
- **Game cards**: Show away team @ home team with final scores (bold for winner).
- **Owner highlight**: Owner's games have an indigo left border.
- **Box Score buttons**: Opens the full-screen maximized box score dialog (reuses NVL pattern).
- **Auto-focuses** on the most recently completed week.

### 3.4 League Tab

- **All-tier standings**: Expandable sections for each tier (owner's tier auto-expanded).
- **Zone coloring**: Green rows = promotion zone, amber = playoff zone, red = relegation zone, indigo highlight for owner's team.
- **Legend**: Color key below each standings table.
- **Stat leaders**: Tabbed display (Rushing, Kick-Pass, Scoring, Defense) with clickable player names for player cards.

### 3.5 Finances Tab

- **Bankroll card**: Large display with color-coded health (green > $15M, amber > $5M, red < $5M). Low bankroll warning when at risk of forced sale.
- **Seasons owned counter**.
- **Owner archetype card**: Shows archetype label and description.
- **President card**: Name, archetype badge, contract years remaining, 4 ratings (Acumen, Budget Mgmt, Recruiting Eye, Staff Hiring).
- **Investment allocation**: 6 categories with progress bars and percentage labels.
- **Financial history table**: Year-by-year revenue, expenses, net income, and ending bankroll.

### 3.6 Multi-Step Offseason Wizard (8 Steps)

| Step | Content |
|------|---------|
| 1. Season Recap | Owner's final record, tier champions with trophy icons |
| 2. Promotion & Relegation | Promoted/relegated teams with directional arrows, owner's club highlighted |
| 3. Retirements | Table of owner's retired players (name, position, age, OVR), league-wide count |
| 4. Player Import | CVL graduate preview table (auto-detected), custom JSON import textarea |
| 5. Free Agency | Owner's targeted signing highlight, signed/unsigned counts, full league signing list |
| 6. Development | Owner's player improvement/decline events with trend icons, league-wide count |
| 7. Investment | 6-category sliders for next season's budget allocation with save button |
| 8. Financial Summary | Revenue/expenses/net/bankroll cards, breakdown tables, forced sale warning |

Progress dots show completion. Back/Next navigation between steps. "Start Next Season" button on final step.

---

## 4. Code Quality & Robustness

Issues identified during code review and resolved:

1. **Step index bounds checking**: `_wvl_offseason_step` from user storage is validated and clamped to prevent `IndexError` on stale or corrupted state.
2. **Offseason data validation**: `offseason_data` is checked for both truthiness and `isinstance(dict)` to handle malformed state.
3. **Defensive defaults**: All offseason step renderers use `data.get("key") or {}` pattern (handles both missing keys and `None` values). Retirement data validated as `dict` before iteration.
4. **Custom import refresh**: UI refresh triggered after custom player import so changes are immediately visible across tabs.

---

## 5. File Inventory

| File | Lines | Role |
|------|-------|------|
| `nicegui_app/pages/wvl_mode.py` | 1,603 | Full WVL Owner Mode UI — setup, tabs, sim controls, roster, schedule, league, finances, offseason wizard |
| `engine/wvl_dynasty.py` | 641 | WVLDynasty dataclass — roster management methods, offseason logic, save/load, factory |
| `engine/wvl_season.py` | — | WVLMultiTierSeason — sim_week_all_tiers, playoffs, standings, schedule, box scores |
| `engine/wvl_free_agency.py` | — | FA pool generation, attractiveness scoring, free agency execution |
| `engine/wvl_owner.py` | — | Owner archetypes, president system, investment allocation, financials |
| `engine/wvl_config.py` | — | 64 clubs, tier definitions, rivalries |
| `data/wvl_teams/` | 64 files | Club JSON configurations |
| `data/wvl_tier_assignments.json` | — | Persisted tier mapping (updated each offseason) |

---

## 6. Known Limitations & Future Work

- **Custom imports are in-memory only**: Players imported via custom JSON during the offseason wizard are added to `_fa_pool` and roster but do not persist through a page reload. A future enhancement could serialize custom imports into dynasty state.
- **No mid-season trading**: Cut/sign is available, but there is no trade system between clubs.
- **No scouting system**: Free agents show all ratings openly. A future scouting mechanic could reveal ratings progressively based on scouting investment.
- **No depth chart reordering**: The roster viewer shows players sorted by OVR but does not allow drag-and-drop depth chart management.
- **President hiring/firing UI**: The president card is visible in Finances, but there is no interactive hire/fire flow yet (presidents are auto-assigned at dynasty creation).
- **Season history browser**: Financial history is shown as a table, but there is no dedicated season archive with historical standings, champions, and player awards across multiple years.

---

## 7. Testing

- Syntax validation: Both `wvl_mode.py` and `wvl_dynasty.py` pass `py_compile` checks.
- Method verification: All 5 new `WVLDynasty` methods confirmed present via import assertion.
- Server startup: Application starts cleanly with no errors in workflow logs.
- Architect code review: 3 critical issues identified and resolved (bounds checking, defensive defaults, import refresh).
