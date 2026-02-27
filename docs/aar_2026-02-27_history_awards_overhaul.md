## After-Action Review — February 27, 2026

### History Rankings, Awards System, and CVL Player Card Overhaul

**Branch:** `claude/fix-history-rankings-0JXnL`
**Files Modified:** `engine/season.py`, `engine/awards.py`, `api/main.py`, `nicegui_app/pages/league.py`

---

### Problem Statement

The pre-created history generator and the end-of-season awards system had four distinct issues:

1. **History table showed wrong data** — The "Top 5" column listed the top 5 teams by regular-season win record, but the champion and runner-up came from the playoff bracket. This meant the champion could appear at rank 3 in their own championship year, or the runner-up might not appear in the top 5 at all. The columns told contradictory stories.

2. **Coach of the Year displayed a school name** — Both the national and conference Coach of the Year awards stored the *team name* (e.g., "Providence College") in the `player_name` field instead of the actual head coach's name. The `CoachCard` objects with `first_name` and `last_name` were available on `Season.coaching_staffs` but never consulted.

3. **All-League teams selected by ratings, not stats** — All-CVL and All-Conference teams were chosen using `_player_score()`, a function that calculates a weighted average of raw player attributes (speed, power, tackling, etc.). A player who rode the bench all season but had elite attribute ratings would be selected over the league's rushing leader. This is the opposite of how real All-American teams work.

4. **CVL award player names were not interactive** — In the NVL (pro league), clicking a player name in any stat table opens a full player card dialog with bio, ratings, and season stats. The CVL awards section rendered player names as flat text with no interactivity.

---

### What We Did

#### 1. Replace Top 5 with Final Four (`engine/season.py`)

**Before:** `_fast_sim_bracket()` returned `(champion, runner_up)`. `fast_sim_season()` returned `top_5: ranked[:5]` — just the top 5 teams by regular-season record, completely disconnected from the bracket.

**After:** `_fast_sim_bracket()` now captures the 4 teams entering the semifinal round during bracket simulation and returns `(champion, runner_up, final_four)`. The `final_four` list is always ordered: `[champion, runner_up, semi_loser_1, semi_loser_2]`.

The UI now shows three columns:
- **Champion** — bracket winner (always `final_four[0]`)
- **Runner-Up** — championship game loser (always `final_four[1]`)
- **Other Semifinalists** — the two teams eliminated in the semis

This eliminates the contradiction where the champion might not appear in the old "Top 5" column.

**Edge cases handled:**
- 1-team bracket: returns `(team, "N/A", [team])`
- 2-team bracket: returns `(winner, loser, [winner, loser])`
- 4+ team bracket: captures semifinalists when `len(bracket) == 4`

**API cleanup:** Added stripping of internal `_records` (dict) and `_playoff_teams` (set — not JSON-serializable) fields before returning history to clients.

---

#### 2. Coach of the Year Now Uses Coach Names (`engine/awards.py`)

Added `_get_head_coach_name(team_name, coaching_staffs)` helper:
- Looks up `coaching_staffs[team_name]["head_coach"]`
- Reads `first_name` and `last_name` from the `CoachCard` dataclass
- Returns `"Coach Name (School)"` format, falling back to just the school name if no coaching staff data exists

Updated three call sites:
- `_select_team_awards()` — national Coach of the Year
- `_select_conference_individual_awards()` — conference Coach of the Year
- `compute_season_awards()` — passes `coaching_staffs` from `season.coaching_staffs` to both functions

The fallback ensures backward compatibility — if a season was created without coaching staffs (older saves, sandbox mode without coaches), the display falls back to the school name.

---

#### 3. Stats-Based All-League Selection (`engine/awards.py`)

This was the largest change. Four new functions:

| Function | Purpose |
|---|---|
| `_aggregate_player_season_stats(season)` | Walks `season.schedule` and `season.playoff_bracket`, accumulates per-player stats from `game.full_result["player_stats"]` |
| `_stat_score_for_group(stats, group, mult)` | Position-aware scoring using actual stats instead of ratings |
| `_format_stat_line(stats, group)` | Builds display strings like `"12 GP \| 1847 yds, 142 car, 13.0 YPC, 18 TD"` |
| `_build_season_stats_dict(stats, group)` | Builds a serializable dict of key stats for the API response |

**Scoring formulas (per game, scaled by team performance multiplier):**

| Position Group | Formula |
|---|---|
| Zeroback | `(KP_yds × 0.4 + rush_yds × 0.3 + lat_yds × 0.2 + TDs × 15 + KP_TDs × 12) / GP` |
| Viper | `(yards × 0.4 + lat_yds × 0.3 + TDs × 20) / GP` |
| Halfback/Wingback | `(rush_yds × 0.4 + YPC × 8 + TDs × 20) / GP` |
| Lineman | `(tackles × 2 + sacks × 12 + TFL × 6) / GP` |
| Safety/Keeper | `(tackles × 2.5 + sacks × 10 + TFL × 5) / GP` |

**Fallback behavior:** If a player has no accumulated stats (e.g., they were injured all season, or the season used fast-sim without player stats), the system falls back to the original rating-based `_player_score()` function. This means the system degrades gracefully rather than producing empty All-League teams.

**Data model change:** Added `season_stats: Optional[Dict]` field to `AwardWinner` dataclass. When present, the UI shows the stat line instead of the overall rating.

---

#### 4. Clickable CVL Player Cards (`nicegui_app/pages/league.py`)

Added `_show_cvl_player_card(session_id, team_name, player_name)` — an async function that:
1. Fetches the team roster via `api_client.get_team_roster()`
2. Finds the player by name
3. Opens a NVL-style dialog with:
   - Header bar (jersey number, name, position, team)
   - Bio section (year, archetype, height/weight, hometown)
   - OVR badge + color-coded attribute chips (SPD, STA, KICK, LAT, TKL, AGI, PWR, AWR, HND, KPW, KAC)
   - Season stats section (fetched from `api_client.get_player_stats()`)
   - Close button

Made three UI areas interactive:
- **Individual awards** — Each award card (`ui.card`) gets an `on("click")` handler that opens the player card. Coach awards are excluded.
- **All-CVL tier tables** — Tables use Quasar's `body-cell-Player` slot to render player names as blue, underlined, clickable links. Click emits `player_click` event → opens dialog.
- **All-Conference tier tables** — Same slot/event pattern as national tiers.

---

### Key Design Decisions

**Why Final Four instead of Top 5?**
The original "Top 5 by record" was fundamentally misleading — it measured regular-season success, not postseason results. Showing the Final Four directly ties the history table to the bracket outcome. Every team in the table earned its spot through playoff performance, not just win-loss record.

**Why per-game stats scoring?**
Raw volume stats would penalize players on teams that played fewer games or had byes. Dividing by games played levels the field. The team performance multiplier (0.88–1.10) still gives a modest edge to players on winning teams, which mirrors real-world voter behavior.

**Why fallback to ratings?**
Fast-sim seasons (used in history generation and some AI-only weeks) don't produce per-player stats. Rather than breaking All-League selection for these cases, the system transparently falls back. This also means dynasty saves from before this change continue to work.

---

### What Went Well

- The `_fast_sim_bracket` change was surgical — one function, three return values, no impact on the 15+ call sites that only use `champion`.
- Stats aggregation reuses the same field names as the existing `season_player_stats` API endpoint, so there's no translation layer needed.
- The clickable player card dialog shares the NVL's visual language (color-coded attribute chips, same layout) without duplicating code from `pro_leagues.py`.

### What to Watch

- **Stats-based selection in short seasons:** With only 6-8 games, small sample sizes could produce volatile All-League picks. A player with one monster 300-yard game in a 6-game season could outscore a consistent performer. May want to add a minimum-games threshold (e.g., 4 GP) before stats are used.
- **History generation doesn't produce player stats:** The fast history generator (`fast_sim_season`) uses rating-based game outcomes without per-player stat generation. This means All-League selection for history years will always fall back to ratings. If history-era awards are ever displayed, they'll show "Rating" instead of stat lines.
- **Coach name persistence in dynasty saves:** The `coach_of_year` field is stored as a string. If a coach is fired and rehired, or if their name changes (shouldn't happen, but defensive note), the historical award record will show the name at the time of the award. This is correct behavior — it matches how real record books work.
- **Dialog performance on large rosters:** The player card dialog fetches the full roster + full player stats endpoint on every click. For 188-team leagues this is fine (single team fetch), but if the pattern is extended to batch operations, consider caching.
