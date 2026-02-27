# Feature Case Study: FIV World Cup & Continental Championships

## Overview

The FIV (Fédération Internationale de Viperball) system adds a complete women's international Viperball simulation to the existing Collegiate Viperball League (CVL) and National Viperball League (NVL) ecosystem. It introduces 68 member nations across 5 confederations, continental championships, a cross-confederation playoff, and a 32-team World Cup — all running on the full `ViperballEngine` for authentic play-by-play simulation.

## Architecture

### Data Flow: CVL → FIV Pipeline

The most significant architectural decision was the **CVL-to-FIV player pipeline**. Rather than generating all international players from scratch, the system routes CVL college players to their home nations using existing nationality data.

**Problem**: CVL players already had international origins (Nordic, Caribbean, African, East Asian, etc.) embedded in their `hometown_state` and `hometown_country` fields by the name generator, but no system existed to route these players to national teams.

**Solution**: A comprehensive mapping layer (`CVL_STATE_TO_FIV_CODE`, `CVL_COUNTRY_TO_FIV_CODE`) translates the ~50 country codes used by `scripts/generate_names.py` into the 68 FIV nation codes. The `_resolve_fiv_code()` function handles the translation with fallback logic:

1. Try `hometown_state` first (more specific: "JPN", "NGA", "JAM")
2. Fall back to `hometown_country` ("Japan", "Nigeria", "Jamaica")
3. Handle edge cases: ZAF→RSA, PHL→PHI, ENG/SCO/WAL→GBR, Australian state codes→AUS

**Result**: When a CVL season exists, international CVL players flow onto their national teams automatically. A Japanese-origin player at Gonzaga becomes available for Team Japan. This gives non-North American nations real CVL-quality players rather than purely generated rosters, creating a meaningful connection between the college and international systems.

### Three-Pathway Roster Construction

Each national team's 36-player roster is built through three pathways:

1. **CVL Pipeline** — International CVL players sorted by overall rating
2. **Homegrown Generation** — Tier-appropriate generated players fill remaining slots
3. **Mercenary Naturalization** — Wealthy nations (KSA, UAE, KAZ) recruit high-rated players from other nations

### Tier System

Nations are classified into four tiers that drive attribute ranges:

| Tier | Attr Range | Rating Range | Starting Elo | Example Nations |
|------|-----------|-------------|-------------|-----------------|
| Elite | 70-95 | 85-95 | 1800 | USA, Canada |
| Strong | 60-88 | 72-84 | 1500 | Japan, Sweden, Brazil, Nigeria |
| Competitive | 50-80 | 58-71 | 1200 | Australia, UK, Jamaica, China |
| Developing | 40-72 | 40-57 | 900 | India, Fiji, Haiti, Mongolia |

## Tournament Structure

### Continental Championships (5 confederations)

Each confederation runs an independent tournament:
- **CAV** (Americas): 12 nations, 6 WC spots
- **IFAV** (Africa/Middle East): 14 nations, 6 WC spots
- **EVV** (Europe): 16 nations, 6 WC spots
- **AAV** (Asia): 10 nations, 6 WC spots
- **CMV** (Oceania/Caribbean): 16 nations, 4 WC spots

Format: Group stage (round-robin) → knockout bracket. Top finishers earn automatic World Cup qualification.

### Cross-Confederation Playoff

8 teams (top 2 non-qualifiers from each confederation) compete for 4 remaining World Cup spots. Quarterfinals → Semifinals, with all 4 semifinalists qualifying.

### 32-Team World Cup

- **Seeded Draw**: 4 pots by world ranking, confederation separation constraints
- **Group Stage**: 8 groups of 4, round-robin (48 matches)
- **Knockout Stage**: R16 → QF → SF → Third Place → Final (16 matches)
- **Awards**: Golden Boot (top scorer), MVP (highest cumulative VPA)

## FIV World Rankings

Elo-style rating system with competition-weighted K-factors:

| Competition | Weight |
|-------------|--------|
| Continental Group | 1.0x |
| Continental Knockout | 1.5x |
| Playoff | 1.5x |
| WC Group | 2.0x |
| WC Knockout | 3.0x |
| WC Semi/Final | 4.0x |

Rankings persist across cycles via SQLite, creating long-term continuity.

## UI Design: Best of Both Worlds

The FIV international page merges design patterns from both existing league UIs:

### From the NVL (Pro League)
- **Maximized dialog** with dark gradient header for box scores
- **Tabbed interface**: Team Stats, Offense, Defense, Kicking, Drives, Play-by-Play
- **Polished score display** with away/home columns, FINAL badge
- **Sortable stat tables** using Quasar `ui.table` with dense/flat/bordered props

### From the CVL (College)
- **Quarter-by-quarter scoring breakdown** computed from play-by-play
- **Drive summary table** with delta drive markers (Δ)
- **Full play-by-play** with down/distance, field position, time remaining
- **Special teams detail**: kick returns, punt returns, ST tackles, keeper bells
- **Pindowns, strikes, yards-per-play** in team stat comparisons

### FIV-Specific Features
- **Clickable match chips** on group tables and knockout brackets open full box scores
- **Team roster dialog** with OVR/SPD/STA/KCK/TKL attributes, age, caps, and CVL source
- **Tournament stat leaders** tab: scoring, rushing, kick passing, defense, kicking
- **Nation click-through** from world rankings to full roster view

## Files Modified/Created

| File | Action | Purpose |
|------|--------|---------|
| `engine/fiv.py` | Created (~1900 lines) | Core FIV module: data models, roster generation, tournament engines, rankings, persistence |
| `data/fiv_nations.json` | Created | 68 nations, 5 confederations, tier configs, heritage/diaspora/mercenary tables |
| `api/main.py` | Modified (+400 lines) | 23 FIV API endpoints |
| `ui/api_client.py` | Modified (+80 lines) | Typed client methods for all FIV endpoints |
| `nicegui_app/pages/international.py` | Created (~900 lines) | Full international UI page |
| `nicegui_app/app.py` | Modified | Added "International" to NAV_SECTIONS |

## Key Technical Decisions

1. **Full ViperballEngine for all matches** — No `fast_sim`. Every international match produces full play-by-play, player attribution, drive summaries, and box scores. This was more computationally expensive but essential for the deep stat tracking and box score detail.

2. **Preserve play-by-play in serialization** — The `_slim_result()` function was expanded to retain `drive_summary`, `play_by_play`, and `in_game_injuries` alongside the standard `stats` and `player_stats`. This allows the UI to render CVL-depth box scores from stored match data.

3. **Single mapping layer, not dual nationality on Player** — Rather than modifying the `Player` dataclass (which would affect all existing systems), the FIV-specific nationality routing lives entirely in `engine/fiv.py` with the `CVL_STATE_TO_FIV_CODE` mapping. The `NationalTeamPlayer` wrapper adds FIV-specific fields (nationalities, caps, naturalized, etc.) without touching the core engine.

4. **Stats computed from live MatchResult objects** — Tournament stat leaders are computed on-demand from the in-memory `FIVCycle` object's `all_results` lists, which retain full `game_result` dicts. This avoids pre-computing and storing redundant stat tables while still providing instant stat leader queries.

## Testing

End-to-end cycle test verified:
- 68 teams generated across 5 confederations
- All 5 continental championships simulated to completion
- Cross-confederation playoff produced 4 qualifiers
- 32-team World Cup: group draw with confederation separation, 48 group matches, 16 knockout matches
- Golden Boot and MVP awards computed correctly
- Rankings updated with proper weights
- Persistence round-trip (save → load → verify) successful
- CVL pipeline successfully routed international players to national teams
