# SITREP — Pro Leagues: NVL Button Fix + International Leagues

**Date:** February 26, 2026
**Branch:** `claude/fix-nvl-play-button-1oEky`
**Commit:** `4bea975` — Fix NVL start button and add international pro leagues (EL, AL, PL, LA)

---

## Summary

Two problems addressed in one commit:

1. **NVL "Start Season" button was non-functional.** Clicking it did nothing visible — no season loaded, no error shown. Three separate root causes identified and fixed.

2. **International leagues didn't exist.** The Pro Leagues spec calls for 6 leagues total: NVL + 4 international (Eurasian League, AfroLeague, Pacific League, LigaAmerica) + Champions League (deferred). All 4 international leagues are now fully built — configs, team data, name pools, UI.

---

## Part 1: NVL Start Button Fix

### Root Causes

| # | Bug | Impact |
|---|-----|--------|
| 1 | `app.storage.user` written inside `run.io_bound` thread pool | Session ID never saved — NiceGUI's per-user cookie storage isn't safely accessible from background threads |
| 2 | `ui.navigate.to("/")` always loads "Play" tab | Even if session saved, user lands on Play section, not Pro Leagues |
| 3 | No try/except around season creation | If `ProLeagueSeason()` threw, exception was silently swallowed — no user feedback |

### Fix

**Split the handler into sync + async parts:**

```
_create_season_sync(config)     → runs in thread pool (CPU work only)
  ├─ generates UUID session ID
  └─ creates ProLeagueSeason(config)

async _start()                  → runs in NiceGUI async context
  ├─ awaits run.io_bound(_create_season_sync, cfg)
  ├─ writes app.storage.user["pro_league_session_id"]   ← safe here
  ├─ writes app.storage.user["pro_league_pending_nav"]  ← new flag
  ├─ calls ui.navigate.to("/")
  └─ wrapped in try/except with ui.notify on failure
```

**Navigation flag in `app.py`:**
```python
pending_pro = app.storage.user.get("pro_league_pending_nav")
if pending_pro:
    app.storage.user["pro_league_pending_nav"] = None
initial_section = "Pro Leagues" if pending_pro else "Play"
```

When the page reloads, it checks the flag and opens Pro Leagues instead of Play. The flag is consumed immediately so subsequent visits default normally.

### Files Changed

| File | What |
|------|------|
| `nicegui_app/pages/pro_leagues.py` | Split handler, add error handling, multi-league UI |
| `nicegui_app/app.py` | Add `pro_league_pending_nav` check, dynamic `initial_section` |

---

## Part 2: International Leagues

### League Configurations

All leagues use the same `ProLeagueSeason` class — adding a league is purely config + team data, no new code paths.

| League | ID | Teams | Divisions | Games | Playoffs | Calendar | Talent Range |
|--------|----|-------|-----------|-------|----------|----------|-------------|
| **NVL** (existing) | `nvl` | 24 | 4 (East, North, Central, West) | 22 | 12 teams, 4 byes | Sep–Feb | 65–95 |
| **Eurasian League** | `el` | 10 | 2 (Nordic, Continental) | 18 | 4 teams, 0 byes | Mar–Jul | 58–85 |
| **AfroLeague** | `al` | 12 | 2 (West, East) | 20 | 4 teams, 0 byes | Apr–Aug | 55–82 |
| **Pacific League** | `pl` | 8 | 2 (North, South) | 14 | 4 teams, 0 byes | Jan–May | 55–80 |
| **LigaAmerica** | `la_league` | 10 | 2 (Norte, Caribe) | 18 | 4 teams, 0 byes | Jun–Oct | 55–82 |

Note: LigaAmerica uses `la_league` as its ID to avoid collision with the NVL's Los Angeles Linx (`la` team key).

### Teams Created

**Eurasian League (10 teams)**
- Nordic: Stockholm Serpents, Helsinki Frost, Copenhagen Vikings, Oslo Trolls, Amsterdam Windmills
- Continental: Brussels Wolves, Berlin Iron Eagles, Prague Golems, Warsaw Hussars, Zurich Alpines

**AfroLeague (12 teams)**
- West: Lagos Lions, Accra Gold Stars, Dakar Teranga, Casablanca Atlas, Abidjan Elephants, Abuja Eagles
- East: Nairobi Harambee, Johannesburg Springboks, Cairo Pharaohs, Dar es Salaam Dhows, Addis Ababa Runners, Kampala Cranes

**Pacific League (8 teams)**
- North: Taipei Dragons, Manila Typhoons, Seoul Tigers, Osaka Samurai
- South: Jakarta Komodos, Bangkok Muay, Ho Chi Minh City Phoenix, Singapore Merlions

**LigaAmerica (10 teams)**
- Norte: Mexico City Aztecas, São Paulo Jaguares, Buenos Aires Gauchos, Bogotá Cóndores, Lima Incas
- Caribe: San Juan Huracanes, Santo Domingo Leones, Havana Cocodrilos, Montevideo Charrúas, Santiago Mineros

### Playoff Fix for International Leagues

The existing `start_playoffs` was hardcoded for NVL's 12-team, 4-division format (top 3 per division, 4 byes). International leagues use 4-team, 2-division playoffs (top 2 per division, 0 byes).

**Changes to `engine/pro_league.py`:**
- `per_div = max(1, self.config.playoff_teams // num_divs)` — dynamic per-division qualifier count
- Non-bye division winners included in first round: `non_bye_seeds = [s for s in top_seeds if s not in bye_teams]`
- Dynamic round names: 4-team uses "Semifinal → Championship"; NVL uses "Wild Card → Divisional → Conference Championship → Championship"

### Name Pools Added

Culturally appropriate player names for East Asian and Southeast Asian regions:

| Pool | First Names | Surnames | Cities |
|------|-------------|----------|--------|
| `east_asian` | 87 (Japanese, Korean, Chinese/Taiwanese) | 83 | Major/secondary tiers |
| `southeast_asian` | 78 (Thai, Vietnamese, Filipino, Indonesian/Malay) | 75 | Major/secondary tiers |

Added to `scripts/generate_names.py`: `pool_key_map`, `select_surname`, `select_hometown`, and `REGION_TO_ORIGIN` for both origins.

European, African, and Latin American names already existed in the pool system.

### UI Changes

The Pro Leagues page now shows a card for each league when no season is active:
- League name, icon, color theme
- Description and calendar window
- Team count, division count, games per season
- Expandable team list by division
- "Start Season" button per league

When a season is active, the dashboard dynamically shows the correct league name and abbreviation instead of hardcoded "NVL".

### Files Changed

| File | What |
|------|------|
| `engine/pro_league.py` | Added EL/AL/PL/LA configs, `ALL_LEAGUE_CONFIGS`, fixed playoff logic |
| `api/main.py` | Registered all league configs via `ALL_LEAGUE_CONFIGS` |
| `nicegui_app/pages/pro_leagues.py` | Multi-league start cards, dynamic dashboard header |
| `scripts/generate_international_teams.py` | New — generates team JSON for all 4 international leagues |
| `scripts/generate_names.py` | Added east_asian, southeast_asian to all name gen functions |
| `data/name_pools/male_first_names.json` | Added east_asian (87), southeast_asian (78) pools |
| `data/name_pools/surnames.json` | Added east_asian (83), southeast_asian (75) pools |
| `data/name_pools/cities.json` | Added east_asia, southeast_asia city pools |
| `data/el_teams/*.json` | 10 team files |
| `data/al_teams/*.json` | 12 team files |
| `data/pl_teams/*.json` | 8 team files |
| `data/la_teams/*.json` | 10 team files |

---

## Architecture Notes

- **Zero new code paths for leagues.** `ProLeagueSeason` is fully parameterized. Each league is a `ProLeagueConfig` + a directory of team JSONs. The engine, API, sim, and UI all work generically.
- **One season at a time per user.** `app.storage.user["pro_league_session_id"]` points to one active session. Starting a new league ends the previous one.
- **Seasons are ephemeral.** No persistence, no continuity between seasons. Each "Start Season" creates a fresh `ProLeagueSeason` in memory. Server restart clears everything.
- **No player movement between leagues.** Each league has its own self-contained roster. Cross-league transfers and Champions League qualification are Phase 2.

---

## What's Not Done (Deferred)

| Item | Reason |
|------|--------|
| **Champions League (CL)** | Requires completed seasons from 2+ leagues to populate 8-team field. Phase 2. |
| **DraftyQueenz multi-league integration** | DQ works per-session already, but the UI doesn't surface games from multiple leagues simultaneously. |
| **Season continuity** | No offseason, no season chaining, no draft. Each start is a clean slate. |
| **`replit.md` update** | Should document international league additions. |

---

## Verification

Tested end-to-end via Python script that:
1. Created a season for each of the 5 leagues
2. Simulated all regular season weeks
3. Started and completed playoffs
4. Verified a champion was crowned for each league
5. Confirmed playoff bracket sizes (12-team for NVL, 4-team for internationals)
