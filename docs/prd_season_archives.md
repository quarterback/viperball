# PRD — Season Archive System

> Source of truth: `engine/db.py`, `api/main.py` (archive endpoints), `stats_site/router.py` (archive routes), `stats_site/templates/archives/`

## Problem

Simulated season data lives entirely in memory. When the app restarts — or when a user starts a new season — all standings, schedules, box scores, polls, awards, and rosters from the previous season are gone. Users who simulate a full 12-week college season with playoffs and bowls have no way to look back at that season's results once they move on. The stats site is only useful for the current active session.

This applies to all league types:

| League | Current Persistence | Gap |
|---|---|---|
| College (CVL) | None — RAM only | Everything lost on restart |
| Pro (NVL, etc.) | Auto-saved to SQLite | Already handled |
| International (FIV) | Cycle saved to SQLite | Rankings/cycle survive, but no explicit archive workflow |

Pro leagues already have full save/load through `db_save_pro_league` / `db_load_pro_league`. The gap is college seasons (the most-used mode) and an explicit archive action for FIV cycles.

---

## Solution

A one-click **Archive** button on the stats site that snapshots a completed season into the existing SQLite database (`data/viperball.db`). Archived seasons get their own browsable section in the stats site with the same pages available for live sessions: standings, schedule, polls, team pages, playoffs, and awards.

### Design Principles

1. **Archive is a snapshot, not a live reference.** The archive captures all displayable data at archive time. It does not depend on the in-memory session or any engine objects existing after the fact.
2. **Read-only.** Archived seasons cannot be modified, simulated further, or resumed. They are historical records.
3. **Same database layer.** Uses the existing `engine/db.py` `saves` table with `save_type = "season_archive"`. No schema changes required.
4. **Same visual language.** Archive pages reuse the Bloomberg-terminal dark aesthetic from the live stats site. An `ARCHIVED` tag badge distinguishes them from live sessions.

---

## Data Model

### Archive Blob Structure (College)

Each college archive is a single JSON blob stored via `save_blob("season_archive", key, data)`.

| Field | Type | Description |
|---|---|---|
| `type` | `"college"` | Discriminator for archive type |
| `label` | string | Display name (season name, or dynasty name + year) |
| `session_id` | string | Original session UUID |
| `season_name` | string | From `Season.name` |
| `champion` | string or null | Championship winner |
| `team_count` | int | Number of teams |
| `total_games` | int | Scheduled games |
| `games_played` | int | Completed games |
| `standings` | list[dict] | Serialized `TeamRecord` objects (same format as `/stats/college/{id}/standings`) |
| `schedule` | list[dict] | All games with `full_result` included (box score data) |
| `polls` | list[dict] | All weekly polls with rankings, power index, SOS, bid type |
| `conferences` | dict | Conference name → list of team names |
| `team_conferences` | dict | Team name → conference name |
| `bowl_games` | list[dict] | Bowl name, tier, game data, seeds, records |
| `playoff_bracket` | list[dict] | Playoff games with full results |
| `awards` | dict or null | Output of `compute_season_awards()` — individual awards, all-conference, coach of year |
| `team_rosters` | dict | Team name → `{players: [...], mascot, abbreviation}` |
| `is_dynasty` | bool | Whether this was a dynasty season |
| `dynasty_name` | string or null | Dynasty name if applicable |
| `dynasty_year` | int or null | Dynasty year if applicable |
| `style_configs` | dict | Team name → offense/defense style |

### Archive Blob Structure (FIV)

| Field | Type | Description |
|---|---|---|
| `type` | `"fiv"` | Discriminator |
| `label` | string | `"FIV Cycle {N}"` |
| `cycle_number` | int | Cycle number |
| `phase` | string | Final phase at archive time |
| `host_nation` | string | World Cup host |
| `fiv_data` | dict | Full cycle data from `FIVCycle.to_dict()` |
| `rankings` | dict or null | World rankings from `FIVRankings.to_dict()` |

### Database Key Format

Archive keys are deterministic and include a timestamp to allow multiple archives of the same session:

- College: `college_{session_id}_{unix_timestamp}`
- FIV: `fiv_cycle_{cycle_number}_{unix_timestamp}`

---

## API Endpoints

All endpoints are on the main FastAPI app (not the stats sub-app).

| Method | Route | Description |
|---|---|---|
| `POST` | `/archives/college/{session_id}` | Archive a college session. Requires an active season in memory. |
| `POST` | `/archives/fiv` | Archive the current FIV cycle. |
| `GET` | `/archives` | List all archives (metadata only — key, label, timestamps, size). |
| `GET` | `/archives/{archive_key}` | Load full archive blob. |
| `DELETE` | `/archives/{archive_key}` | Delete an archive. |

### Archive Response Example (POST)

```json
{
  "archive_key": "college_abc123_1709150400",
  "label": "2025 CVL Season",
  "message": "Season archived successfully"
}
```

---

## Stats Site Routes

All archive viewing routes are under `/stats/archives/` and pass `section="archives"` for nav highlighting.

| Route | Template | Description |
|---|---|---|
| `GET /stats/archives/` | `archives/index.html` | List of all archived seasons with champion, team count, game count |
| `GET /stats/archives/{key}/` | `archives/college_season.html` or `archives/fiv.html` | Season overview — latest poll + top 25 standings |
| `GET /stats/archives/{key}/standings` | `archives/standings.html` | Full standings with conference breakdowns |
| `GET /stats/archives/{key}/schedule?week=N` | `archives/schedule.html` | Week-by-week schedule with scores |
| `GET /stats/archives/{key}/polls?week=N` | `archives/polls.html` | Weekly poll rankings |
| `GET /stats/archives/{key}/team/{name}` | `archives/team.html` | Team page: record, season stats, schedule, roster |
| `GET /stats/archives/{key}/playoffs` | `archives/playoffs.html` | Playoff bracket + bowl games |
| `GET /stats/archives/{key}/awards` | `archives/awards.html` | Individual awards, all-conference, coach of year |

### Navigation

- **Top bar**: New "Archives" link between "International" and "Search"
- **Home page**: Archived seasons listed below the active sessions grid
- **Season page**: "Archive This Season" button appears when a champion exists (season complete)
- **International page**: "Archive This Cycle" button appears when phase is `completed`

---

## UI Flow

### Archiving a Season

```
1. User completes a season (playoffs + bowls → champion crowned)
2. User navigates to /stats/college/{session_id}/
3. "Archive This Season" button is visible in the page header
4. User clicks button → JS POSTs to /archives/college/{session_id}
5. Button text changes to "Archived", status message shows "Archived! View in Archives tab."
6. Season data is now persisted in viperball.db
```

### Browsing Archives

```
1. User clicks "Archives" in top nav → /stats/archives/
2. Table shows all archived seasons (name, type, teams, games, champion)
3. User clicks a season name → /stats/archives/{key}/
4. Full stats-site-style browsing with standings, schedule, polls, teams, playoffs, awards
5. All pages show "ARCHIVED" badge to distinguish from live data
```

---

## Template Layout

```
stats_site/templates/archives/
  index.html             # Archive listing
  college_season.html    # Season overview (poll + standings)
  standings.html         # Full standings + conference breakdowns
  schedule.html          # Week-by-week schedule
  polls.html             # Weekly poll rankings
  team.html              # Team page: stats, schedule, roster
  playoffs.html          # Playoff bracket + bowl games
  awards.html            # Season awards
  fiv.html               # FIV cycle overview (rankings, confederations, world cup)
```

All templates extend `base.html` and use the same CSS classes, table structures, and tag badges as the live stats site. Archive templates include a consistent tab bar for navigating between pages within an archived season.

---

## Persistence Layer

### New Functions in `engine/db.py`

| Function | Description |
|---|---|
| `save_season_archive(key, snapshot, user_id)` | Upsert archive blob |
| `load_season_archive(key, user_id)` | Load archive blob or return None |
| `list_season_archives(user_id)` | List all archive metadata (no blob data) |
| `delete_season_archive(key, user_id)` | Remove archive |

These are thin wrappers around the existing `save_blob` / `load_blob` / `list_saves` / `delete_blob` CRUD functions. No new tables or schema migrations needed.

---

## Stats Aggregation

Archive team pages compute season statistics on-the-fly from the archived `schedule` data, the same way the live stats site does. The `_aggregate_archive_team_stats()` function in `stats_site/router.py` iterates completed games, extracts the team's side (`home` or `away`) from `full_result.stats`, and sums up:

- Total/average yards, plays, yards/play
- Rushing: yards, carries, TDs, YPC
- Kick passing: yards, completions, attempts, comp%, TDs, INTs
- Touchdowns, fumbles, penalties, penalty yards

This is a subset of what the live team page computes (the live version also has laterals, delta yards, EPA, down conversions, and viperball metrics). The archive version covers the core stats that matter for historical reference.

---

## What's Not Included (and Why)

| Feature | Status | Rationale |
|---|---|---|
| Box score pages for individual archived games | Not included | Archive blob already contains `full_result` data per game; adding per-game box score routes is straightforward but not needed for v1 |
| Player detail pages in archives | Not included | Roster snapshots are stored; player game logs would require iterating schedule which is doable but deferred |
| Re-importing archives into live sessions | Not included | Archives are read-only snapshots, not save files. Reconstructing a live `Season` object from a snapshot is fragile and not the goal |
| Auto-archive on season completion | Not included | Explicit user action preferred — avoids filling the DB with abandoned/test seasons |
| Archive size management | Not included | JSON blobs with full_result data can be 5-20 MB per season. For v1 this is fine; if it becomes an issue, `_slim_game_result()` from pro league serialization can strip play-by-play |
| Pro league archives | Not needed | Pro leagues already auto-save to SQLite via `db_save_pro_league()` |

---

## Files Modified

| File | Change |
|---|---|
| `engine/db.py` | Added `save_season_archive`, `load_season_archive`, `list_season_archives`, `delete_season_archive` |
| `api/main.py` | Added archive import, `_build_college_archive()`, `_build_fiv_archive()`, 5 archive endpoints |
| `stats_site/router.py` | Added `_get_archives()` helper, archives passed to home page, 8 archive routes, `_aggregate_archive_team_stats()` |
| `stats_site/templates/base.html` | Added Archives nav link |
| `stats_site/templates/home.html` | Added archived seasons table below active sessions |
| `stats_site/templates/college/season.html` | Added "Archive This Season" button (visible when champion exists) |
| `stats_site/templates/international/index.html` | Added "Archive This Cycle" button (visible when phase is completed) |
| `stats_site/templates/archives/*.html` | 9 new templates for archive browsing |

---

## Verification Checklist

- [ ] Archiving a completed college season returns success and persists to `data/viperball.db`
- [ ] Archiving the same session twice creates two separate archive entries (timestamped keys)
- [ ] Archives list on `/stats/archives/` shows all saved seasons with correct metadata
- [ ] Archive overview page displays final poll and top 25 standings
- [ ] Standings page shows overall + per-conference breakdowns
- [ ] Schedule page filters by week, shows scores and tags
- [ ] Polls page navigates between weeks
- [ ] Team page shows record, aggregated season stats, game-by-game schedule, and roster
- [ ] Playoffs page shows bracket and bowl games
- [ ] Awards page shows individual awards and all-conference teams
- [ ] Archives survive app restart (data loaded from SQLite, not memory)
- [ ] FIV cycle archive captures rankings, confederations, and world cup data
- [ ] "Archive" button only appears on completed seasons (champion set)
- [ ] Deleting an archive via API removes it from the list
