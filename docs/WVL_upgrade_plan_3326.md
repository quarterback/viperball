# Objective
Upgrade the WVL (Women's Viperball League) from a thin spectator-with-levers experience into a robust Owner Mode dynasty. The current state has the basic framework (bankroll, president hiring, one targeted FA, investment allocation, promotion/relegation), but lacks depth — the owner doesn't have much to actually *do*, the game sim doesn't generate enough detail for engagement, and the UI is sparse compared to the CVL college experience. This session focuses on core feature depth and UI refinement to make WVL feel like a real dynasty mode.

**Current State Assessment:**
- Engine: 4-tier pyramid (64 clubs), promotion/relegation works, free agency exists but owner only picks 1 FA, investments exist but feel passive, no week-by-week sim control, entire season sims at once
- UI: Setup flow works, standings show zones, season results table exists, box scores are accessible, stats leaders exist, management section is a tiny expansion at bottom
- Missing: Week-by-week sim control, roster viewer for your team, depth chart management, player development visibility, trade/waiver system, scouting, offseason flow with multiple decision points, financial dashboard, season history tracking in the UI

# Tasks

### T001: Week-by-Week Season Control
- **Blocked By**: []
- **Details**:
  - Currently WVL sims the entire season at once with one button. Convert to week-by-week simulation like the NVL pro leagues
  - Add `sim_week()` to `WVLMultiTierSeason` that simulates one week across all tiers and returns results
  - Add sim controls to WVL dashboard: "Sim Week", "Sim Rest of Season", phase indicator (Pre-Season / Week X of Y / Playoffs / Offseason)
  - Owner sees their game result highlighted after each week
  - Keep "Sim All" as a convenience option for users who want instant seasons
  - Files: `engine/wvl_season.py`, `nicegui_app/pages/wvl_mode.py`
  - Acceptance: Can sim WVL season week-by-week, standings update each week, owner's game highlighted

### T002: Owner's Team Roster Viewer
- **Blocked By**: []
- **Details**:
  - Add a "My Team" section/tab to the WVL dashboard showing the owner's full 36-player roster
  - Display: Name, Position, Age, OVR, SPD, KICK, LAT, Archetype, Contract stub, Development trait
  - Color-code ratings (green 80+, yellow 60-79, red <60)
  - Player names clickable for player cards (reuse existing `_show_player_card` pattern)
  - Show team overall rating, average age, positional depth counts
  - Files: `nicegui_app/pages/wvl_mode.py`
  - Acceptance: Owner can see their full roster with all ratings, click players for cards

### T003: Roster Management — Cuts, Signings, Depth
- **Blocked By**: [T002]
- **Details**:
  - Owner can cut players from their roster (up to roster minimum of 30)
  - Owner can sign free agents from a persistent FA pool (not just 1 per offseason — allow mid-season pickups)
  - Show depth chart by position group with drag-or-button reordering
  - Roster cap of 40 players (currently 36 generated, room for FA signings)
  - Engine: Add `cut_player()`, `sign_free_agent()`, `get_depth_chart()` methods to WVLDynasty
  - UI: Roster tab gets "Cut" buttons per player, "Free Agents" sub-tab with available players and "Sign" buttons
  - Files: `engine/wvl_dynasty.py`, `engine/wvl_free_agency.py`, `nicegui_app/pages/wvl_mode.py`
  - Acceptance: Owner can cut and sign players, roster size enforced, depth chart visible

### T004: Player Import from CVL
- **Blocked By**: [T003]
- **Details**:
  - Streamline the CVL graduate import pipeline — currently requires manual file path or obscure export flow
  - Add a direct "Import CVL Graduates" button that pulls from the most recent CVL dynasty season if one exists
  - Show available graduates with their stats/ratings before importing
  - Imported players appear in the FA pool with realistic pro-level attribute adjustments (college players are 40-80, pros are 65-95 — scale up appropriately)
  - Allow importing custom player JSON (paste or file upload) for user-created players
  - Files: `engine/wvl_free_agency.py`, `engine/wvl_dynasty.py`, `nicegui_app/pages/wvl_mode.py`
  - Acceptance: Can import CVL graduates into WVL free agency, attributes scale appropriately, custom import works

### T005: Financial Dashboard
- **Blocked By**: [T001]
- **Details**:
  - Replace the tiny management expansion with a proper Financial Dashboard section
  - Show: Current bankroll, revenue breakdown (ticket sales, tier bonus, playoff bonus, investment returns), expense breakdown (salaries, president, operations)
  - Season-over-season financial history chart (bankroll trend line)
  - Investment allocation with sliders (Training/Coaching/Stadium/Youth/Science/Marketing) and real-time projected ROI
  - Forced sale warning when bankroll is dangerously low
  - President card with ratings and option to fire/hire new president
  - Files: `nicegui_app/pages/wvl_mode.py`, `engine/wvl_owner.py`
  - Acceptance: Owner sees full financial picture, can adjust investments with visual feedback, president management is accessible

### T006: Offseason Flow — Multi-Step Decision Points
- **Blocked By**: [T001, T003, T005]
- **Details**:
  - Instead of running offseason silently in one function call, break it into an interactive multi-step wizard:
    1. **Season Recap**: Show final standings, your record, champion, awards
    2. **Promotion/Relegation Results**: Animated reveal of who moved up/down, your new tier
    3. **Retirements & Departures**: Show who left, ages, career highlights
    4. **Free Agency**: Browse full FA pool, pick your targeted signing(s), see AI signings
    5. **Player Development**: Show which players improved/declined with before/after ratings
    6. **Investment Allocation**: Set next season's budget split
    7. **President Review**: Keep, fire, or let contract expire; hire from new pool
    8. **Financial Summary**: Revenue, expenses, new bankroll
  - Each step renders in the dashboard with "Next" to advance
  - Files: `nicegui_app/pages/wvl_mode.py`, `engine/wvl_dynasty.py`
  - Acceptance: Offseason plays out step-by-step with owner decisions at each point

### T007: UI Polish — Tab-Based Layout & Responsive Design
- **Blocked By**: [T001, T002, T005]
- **Details**:
  - Restructure WVL page into a proper tab layout (matching NVL Pro Leagues pattern):
    - **Dashboard**: Hero header with club info + sim controls + current standings
    - **My Team**: Roster, depth chart, team stats
    - **Schedule**: Week-by-week with box scores (already partially exists)
    - **League**: All-tier standings, stat leaders, promotion/relegation tracker
    - **Finances**: Full financial dashboard
    - **Offseason**: Multi-step offseason wizard (when in offseason phase)
  - Consistent styling with the rest of the app (dark headers, card-based layout)
  - Mobile-responsive tables and controls
  - Files: `nicegui_app/pages/wvl_mode.py`
  - Acceptance: WVL page has clean tab navigation, consistent with NVL styling, works on mobile

### T008: Update replit.md & Integration Testing
- **Blocked By**: [T001-T007]
- **Details**:
  - Update replit.md with WVL Owner Mode architecture and feature documentation
  - End-to-end test: Create WVL dynasty → sim weeks → view roster → cut/sign player → view finances → complete season → step through offseason → import CVL graduates → start next season
  - Verify box scores use the redesigned full-screen dialog
  - Files: `replit.md`
  - Acceptance: Full WVL lifecycle works, documentation updated
