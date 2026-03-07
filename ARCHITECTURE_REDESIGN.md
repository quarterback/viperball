# Viperball UI Architecture Redesign

## Status: Phase 1 Implemented

The NiceGUI app (`nicegui_app/`) has been restructured with visible IA and UI improvements.

---

## What Changed (Phase 1)

### 1. New Home Landing Page (`nicegui_app/pages/home.py`)

**Before:** App opened directly to the Play tab showing mode selection sub-tabs (New Season / Quick Game / DraftyQueenz) — no context, no onboarding.

**After:** App opens to a Home page with:
- Hero branding section
- Three primary mode cards (New Season, Quick Game, DraftyQueenz) with descriptions and badges
- Three secondary mode cards (Pro Leagues, WVL Owner Mode, International)
- Footer with team/conference counts
- When a session IS active: dashboard with quick-action cards, recent results, and season metrics

### 2. Reorganized Navigation

**Before:** 9 flat nav buttons — Play, Pro Leagues, WVL, International, League, My Team, Export, Debug, Inspector — all treated equally, cluttering the nav bar.

**After:** Navigation grouped by purpose:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Viperball Sandbox    [Home] [Play] [League] [My Team] [Export]  [Modes ▼]  [⚙]  │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Core tabs** (always visible): Home, Play, League, My Team, Export
- **Modes dropdown**: Pro Leagues, WVL, International — secondary game modes
- **Gear icon**: Debug, Inspector — dev tools hidden from main nav
- **Brand click**: Returns to Home

### 3. Session Context Bar

**Before:** Only a tiny mode label ("Season") and End button in the far-right header corner. No persistent session context.

**After:** When a session is active, a dark gradient context bar appears below the header showing:
- Active session name
- Your team name
- Current week / total weeks
- Season phase (Portal, Regular, Playoffs, etc.)

This bar is always visible across all tabs so you always know where you are.

### 4. Clickable Brand

The "Viperball Sandbox" logo in the header is now clickable and navigates to the Home page. Standard SaaS pattern.

---

## Architecture: Before vs After

### Before (9 flat tabs, no hierarchy)

```
Header: [Play] [Pro Leagues] [WVL] [International] [League] [My Team] [Export] [Debug] [Inspector]
                                                                              ↑ dev tools mixed in
Content: Play tab does everything — mode selection + simulation + setup
```

### After (grouped navigation, clear hierarchy)

```
Header: [Home] [Play] [League] [My Team] [Export]    [Modes ▼]    [⚙]
                                                      ├─ Pro Leagues
Session Bar: "Season 2027 | Team: Boston U | Week 8/12 | Regular"
                                                      ├─ WVL
Content: Home = landing/dashboard, Play = simulation only         ├─ International
                                                      [⚙] ├─ Debug
                                                           └─ Inspector
```

---

## File Changes

| File | Change |
|------|--------|
| `nicegui_app/app.py` | Rewritten — grouped nav, session context bar, Home routing |
| `nicegui_app/pages/home.py` | **NEW** — landing page + active session dashboard |

---

## Future Phases

### Phase 2: Play Tab Cleanup
- Extract setup flows into separate modules
- Play tab becomes pure simulation controls when a session exists
- Play tab redirects to Home when no session exists

### Phase 3: Component Extraction
- Extract reusable components (injury report, player card, scoreboard)
- Break up giant page files (pro_leagues 2,356 lines, wvl_mode 3,123 lines)

### Phase 4: Search / Command Bar
- Add search bar to header
- Search teams, players, games across the active session
- Keyboard shortcut (`/`) to focus

---

## Design Principles

1. **Home is home** — clear landing page, always one click away
2. **Core tabs visible, extras hidden** — 5 tabs in the bar, modes and dev tools tucked away
3. **Session context always visible** — dark bar shows where you are in the season
4. **One file, one concern** — target no file over 500 lines (future phases)
5. **Cards over tabs for entry points** — visual mode selection, not text sub-tabs
6. **Dev tools are dev tools** — behind a gear icon, not alongside core navigation
