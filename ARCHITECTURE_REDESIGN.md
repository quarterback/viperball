# Viperball UI Architecture Redesign

## Problem Statement

The current Streamlit UI has grown organically and drifted from the original IA spec. The result is a disorganized experience where `section_play.py` alone is 2,268 lines handling session creation, dynasty management, game simulation, recruiting, betting, and more — all in one file behind one tab.

---

## Current Architecture (What's Wrong)

```
app.py
├── Sidebar
│   ├── Brand / session status
│   ├── End Session button
│   └── Settings radio (Debug Tools, Play Inspector)  ← dev tools mixed with nav
│
├── Tab: Play (2,268 lines — god module)
│   ├── Session creation (dynasty vs season)
│   ├── Conference/schedule setup
│   ├── Game simulation
│   ├── Season simulation
│   ├── Playoff brackets
│   ├── Offseason flows (recruiting, transfers, development)
│   ├── DraftyQueenz betting
│   └── Injury management
│
├── Tab: League (1,270 lines)
│   ├── Standings
│   ├── Schedule
│   ├── Stats leaders
│   ├── Polls
│   └── Conference views
│
├── Tab: My Team (777 lines)
│   ├── Dashboard
│   ├── Roster
│   └── Schedule
│
└── Tab: Export (460 lines)
    └── Various export options
```

**Key issues:**
- `section_play.py` mixes 7+ concerns in one file
- No home/onboarding screen — cold start dumps users into empty tabs
- Sidebar conflates session mgmt + dev tools + navigation
- No search or command bar
- No contextual panels (everything inline)
- Dynasty vs Season creates confusing dual-path UX in the same tab

---

## Proposed Architecture

### Navigation Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  VIPERBALL SANDBOX                                    [⚙️] [🔍] │
├─────────────────────────────────────────────────────────────────┤
│  [Home]     [League]     [My Team]     [Play]     [Export]      │
└─────────────────────────────────────────────────────────────────┘
```

### New Tab: Home (replaces cold-start problem)

When no session is active, Home is the landing page:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   VIPERBALL SANDBOX                                             │
│   Collegiate Viperball League Simulator                         │
│                                                                 │
│   ┌────────────────────┐  ┌────────────────────┐                │
│   │  NEW DYNASTY        │  │  QUICK SEASON       │               │
│   │  Multi-year career  │  │  Single season sim  │               │
│   │  with recruiting,   │  │  with any team(s)   │               │
│   │  transfers, awards  │  │                     │               │
│   │  [Start →]          │  │  [Start →]          │               │
│   └────────────────────┘  └────────────────────┘                │
│                                                                 │
│   ┌────────────────────┐                                        │
│   │  EXHIBITION GAME    │                                       │
│   │  Pick two teams,    │                                       │
│   │  play one game      │                                       │
│   │  [Play →]           │                                       │
│   └────────────────────┘                                        │
│                                                                 │
│   187 teams · 16 conferences · CVL Engine v2.5                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

When a session IS active, Home shows a dashboard summary.

### File Structure Redesign

```
ui/
├── app.py                          # ~80 lines: config, nav, routing
├── api_client.py                   # API layer (unchanged)
├── helpers.py                      # Shared utilities (unchanged)
├── components/                     # Reusable UI components
│   ├── __init__.py
│   ├── scoreboard.py               # Game score cards
│   ├── player_card.py              # Player detail display
│   ├── team_card.py                # Team summary display
│   ├── injury_report.py            # Injury tables (extracted from section_play)
│   ├── game_detail_panel.py        # Box score / play-by-play viewer
│   └── search_bar.py               # Command bar / search
│
├── pages/                          # One file per top-level tab
│   ├── __init__.py
│   ├── home.py                     # NEW: Landing + session creation
│   ├── league.py                   # Standings, schedule, leaders
│   ├── my_team.py                  # Dashboard, roster, schedule
│   ├── play.py                     # Sim week, sim season, quick game
│   └── export.py                   # Export templates + custom
│
├── flows/                          # Multi-step wizards (extracted from section_play)
│   ├── __init__.py
│   ├── dynasty_setup.py            # Dynasty creation wizard
│   ├── season_setup.py             # Season creation wizard
│   ├── offseason.py                # Recruiting, transfers, development
│   ├── playoffs.py                 # Bracket + championship flow
│   └── game_sim.py                 # Single game simulation + results
│
└── settings/                       # Moved out of main nav
    ├── __init__.py
    ├── debug_tools.py              # Debug panel
    └── play_inspector.py           # Play inspector
```

### What Changes

| Area | Before | After |
|------|--------|-------|
| **Session creation** | Buried inside Play tab, 500+ lines | `flows/dynasty_setup.py` and `flows/season_setup.py`, accessed from Home |
| **Game simulation** | Inside Play tab | `flows/game_sim.py`, triggered from Play tab |
| **Offseason** | Inside Play tab | `flows/offseason.py`, triggered at season end |
| **Playoffs** | Inside Play tab | `flows/playoffs.py`, triggered when season ends |
| **Injury reports** | Duplicated in section_play | `components/injury_report.py`, reused everywhere |
| **DraftyQueenz** | Embedded in section_play | Stays in `page_modules/draftyqueenz_ui.py`, imported into game_sim flow |
| **Debug/Inspector** | Sidebar settings radio | `settings/` folder, accessed via gear icon |
| **Home screen** | Doesn't exist | `pages/home.py` — landing page + active session dashboard |

### Sidebar Redesign

The sidebar becomes simpler — just context, not navigation:

```
┌─────────────────────────────┐
│  VIPERBALL SANDBOX          │
│  CVL Simulator              │
│  ─────────────────────────  │
│                             │
│  ACTIVE SESSION             │
│  Dynasty: My Dynasty (2027) │
│  Team: Boston University    │
│  Record: 7-0 (1st)         │
│  Week: 8 of 12             │
│                             │
│  ─────────────────────────  │
│  [End Session]              │
│                             │
│  ─────────────────────────  │
│  v2.5 · 187 teams           │
└─────────────────────────────┘
```

No navigation in the sidebar. Navigation lives in the top tabs.
No dev tools in the sidebar. Those move behind a gear icon.

### Play Tab Simplified

After the split, the Play tab becomes ~300 lines instead of 2,268:

```
Play Tab
├── If no session → redirect to Home
├── If season in progress:
│   ├── Show current week matchups
│   ├── [Simulate Week] button → calls flows/game_sim.py
│   ├── [Simulate to Playoffs] → calls flows/playoffs.py
│   └── Results display
├── If offseason:
│   └── Redirect to flows/offseason.py
└── If season complete:
    └── Show season summary + [Start Next Season]
```

---

## Implementation Phases

### Phase 1: Extract and Split (no visible UI changes)
1. Extract injury report code into `components/injury_report.py`
2. Extract game simulation into `flows/game_sim.py`
3. Extract dynasty setup into `flows/dynasty_setup.py`
4. Extract season setup into `flows/season_setup.py`
5. Extract offseason into `flows/offseason.py`
6. Extract playoffs into `flows/playoffs.py`
7. Verify `section_play.py` is now ~300 lines, all imports

### Phase 2: Add Home Page
1. Create `pages/home.py` with session creation cards
2. Move session creation logic out of Play tab
3. Route to Home when no session is active

### Phase 3: Sidebar + Settings Cleanup
1. Strip nav from sidebar, keep only session context
2. Move debug tools behind gear icon
3. Add settings modal/page

### Phase 4: Search Bar (stretch)
1. Add `components/search_bar.py`
2. Wire up team/player/game search via API
3. Keyboard shortcut (`/`) to focus

---

## Design Principles

1. **One file, one concern** — no file over 400 lines
2. **Flat navigation** — 5 top-level tabs, no nesting
3. **Context in sidebar, actions in main area** — sidebar shows state, doesn't drive navigation
4. **Flows are temporary** — setup wizards and offseason sequences are modal flows, not permanent tabs
5. **Components are reusable** — scoreboard, player card, injury table used across multiple pages
6. **Dev tools are hidden** — debug and inspector behind a gear icon, not alongside core UI
