## After-Action Review — March 7, 2026

### Mobile Compatibility Fix and WVL State Persistence Migration

**Branch:** `claude/fix-mobile-compatibility-bvVQV`
**Files Modified:** `main.py`, `nicegui_app/app.py`, `nicegui_app/pages/wvl_mode.py`, `engine/db.py`, `nicegui_app/pages/play.py`, `nicegui_app/pages/pro_leagues.py`, `nicegui_app/pages/international.py`, `nicegui_app/pages/draftyqueenz.py`

---

### Problem Statement

**1. The app was unusable on mobile devices**

The WVL owner mode dashboard had 7 navigation tabs (Dashboard, My Team, Schedule, Playoffs, League, Finances, History) displayed in a horizontal row. On mobile screens, all tab labels rendered at full width, overlapping each other and producing an unreadable jumble of text ("DASHBOARDEASCHEDULPLAYOESAGUEINANGEISTO"). The hero banner — showing club name, tier, bankroll, roster size, OVR, and fanbase — was similarly laid out in a single horizontal row that overflowed on narrow screens.

This affected every tab bar in the app, not just WVL mode. Pro Leagues, Play, International, and DraftyQueenz all had tab bars without mobile scroll support.

**2. WVL mode lost state mid-season, making it unplayable**

Users couldn't finish a full WVL season because state was regularly lost. Two root causes:

- **Cookie-based storage overflow:** `app.storage.user` (NiceGUI's user storage) is backed by browser cookies or a small JSON file. The `WVLMultiTierSeason` object — containing 4 tier seasons, 64 teams worth of standings, full schedules, game results with box scores, player season stats, injury trackers, and playoff brackets — was stored directly via `app.storage.user["wvl_last_season"] = s`. This object had no `to_dict()`/`from_dict()` serialization methods. NiceGUI's storage layer couldn't JSON-serialize it, so it lived only in server memory. Any page reload, server restart, or session timeout lost the entire season.

- **30-second reconnect timeout:** `reconnect_timeout=30.0` in `main.py` meant that locking a phone screen, switching apps, or briefly losing cellular signal for more than 30 seconds would drop the WebSocket session and destroy all in-memory state.

Meanwhile, the app already had a perfectly functional SQLite database (`engine/db.py`) with a `saves` table and JSON blob storage. Pro Leagues, FIV cycles, and season archives all used it. WVL mode simply never got wired up to it.

**3. Pre-existing serialization bug: ties/draws not persisted**

`serialize_pro_league_season()` in `engine/db.py` omitted the `ties` and `div_ties` fields from `ProTeamRecord`. This meant that when a Pro League or WVL season was saved and restored from the database, all tie records were silently zeroed out. In a soccer-style league with promotion/relegation, losing tie records corrupts standings and can incorrectly relegate teams.

---

### What We Did

#### 1. Mobile Tab Navigation (all pages)

**CSS changes in `app.py`:**
- On screens `<768px`, tab labels are now hidden (`.q-tab .q-tab__label { display: none }`) and only icons are shown (`.q-tab .q-tab__icon { font-size: 1.3rem }`)
- Tabs have tighter padding (`padding: 0 6px`) and no minimum width (`min-width: 0`)
- Added `.q-tabs__content { flex-wrap: nowrap }` and `.q-tabs { overflow: hidden }` to prevent tab wrapping globally

**Props on all tab bars:**
Every `ui.tabs()` call across 7 files now includes `.props("mobile-arrows outside-arrows")`, which enables Quasar's built-in horizontal scroll arrows on overflow. Previously only some pages (league.py, dq_mode.py, export.py) had this; the rest (wvl_mode.py, play.py, pro_leagues.py, international.py, draftyqueenz.py) did not.

#### 2. Responsive Hero Banner (WVL mode)

Added CSS classes `vb-hero-banner`, `vb-hero-top`, `vb-hero-stats` to the WVL dashboard banner. On mobile:
- The banner stacks vertically (`flex-direction: column`) instead of cramming club info and stats into one row
- Stats row wraps and centers (`flex-wrap: wrap; justify-content: center`)
- Padding and font sizes are reduced

#### 3. WVL Season Serialization (`engine/db.py`)

Added complete serialization for `WVLMultiTierSeason`:

- **`serialize_wvl_season()`** — Serializes the multi-tier wrapper (tier_assignments, phase, current_week, promotion_result) and delegates each tier's `ProLeagueSeason` to the existing `serialize_pro_league_season()`. Also serializes the `InjuryTracker` per tier (active injuries and season log).

- **`deserialize_wvl_season()`** — Reconstructs the full object graph. Uses `__new__` to bypass `__init__` (which would re-load teams and regenerate schedules). Includes a fallback to scan all WVL tier directories for team JSON files, since promoted/relegated teams may live in a different tier's directory than their current assignment.

- **`_serialize_injury_tracker()` / `_deserialize_injury_tracker()`** — Roundtrip the `InjuryTracker` dataclass tree. Uses `Injury.__dataclass_fields__` to filter out computed properties (`is_season_ending`, `game_status`) during deserialization.

- **`save_wvl_season()` / `load_wvl_season()` / `delete_wvl_season()`** — High-level functions using the existing `save_blob()`/`load_blob()` pattern with save_type `"wvl_season"`.

#### 4. WVL Mode Database Migration (`wvl_mode.py`)

Replaced all `app.storage.user[_WVL_SEASON_KEY]` reads/writes with database-backed functions:

- **`_get_wvl_season()`** — Checks in-memory cache first, then database, then falls back to legacy `app.storage.user` (for migration). If found in legacy storage, auto-migrates to the database and clears the cookie.

- **`_save_wvl_season(s)`** — Writes to both in-memory cache and database. Called after every sim week, playoff advance, season start, and offseason step.

- **`_clear_wvl_season()`** — Clears cache, database, and legacy storage. Called on dynasty reset and offseason completion.

Dynasty data (`WVLDynasty`) still uses `app.storage.user` via `to_dict()`/`from_dict()` which was already working correctly. Only the season object needed migration.

#### 5. Reconnect Timeout (`main.py`)

Changed `reconnect_timeout` from `30.0` to `43200.0` (12 hours). This prevents session loss when users lock their phone, switch apps, or lose connectivity temporarily.

#### 6. Ties Serialization Fix (`engine/db.py`)

Added `ties` and `div_ties` to both `serialize_pro_league_season()` and `deserialize_pro_league_season()`. Old saves without these fields gracefully default to 0 via `.get("ties", 0)`.

---

### Architecture Notes

**Storage layer summary after this change:**

| Data | Storage | Serialization |
|------|---------|---------------|
| WVL Dynasty | `app.storage.user` (JSON) | `WVLDynasty.to_dict()` / `.from_dict()` |
| WVL Season | SQLite `saves` table | `serialize_wvl_season()` / `deserialize_wvl_season()` |
| WVL Phase | `app.storage.user` (string) | Plain string, no serialization needed |
| Pro Leagues | SQLite `saves` table | `serialize_pro_league_season()` (existing) |
| FIV Cycles | SQLite `saves` table | Existing |

**Why not move dynasty to the database too?** `WVLDynasty` already has working `to_dict()`/`from_dict()` and is much smaller than the season object. The cookie storage works fine for it. The season was the critical piece because it contains the bulk of the data (game results, player stats, schedules across 4 tiers).

**In-memory cache pattern:** `_wvl_season_cache` is a module-level dict. This avoids hitting the database on every `_get_wvl_season()` call during a session (which happens frequently — dashboard, roster, schedule, and other tabs all read the season). The cache is populated on first read and updated on every write. It's cleared on season reset. This is safe because WVL mode is single-user (one dynasty per browser session).
