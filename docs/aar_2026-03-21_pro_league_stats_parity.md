# After Action Review — Pro League Stats Parity

**Date:** 2026-03-21
**Branch:** `claude/fix-pro-league-stats-eBU7h`

## Mission

Bring pro league (NVL, EL, AL, PL, LA) and WVL stats pages to parity with the college (CVL) stats system. Fix empty keeper stat leaders, upgrade flat team stats tables to full tabbed category views, and fix the "Back to League Hub" navigation bug.

## Incident / Starting State

Three interconnected issues degraded the pro/WVL stats experience compared to college:

1. **Keeper stat leaders showed no data.** The `/stats` page for any pro league displayed a "Keeper" section with column headers but zero rows. Every other stat category (rushing, kick pass, scoring, defense, sacks, kick returns, laterals) populated correctly.

2. **Team stats were a single flat table** with 20 columns (YDS, Y/G, YPP, TD, RUSH, KP, KP%, LAT, EPA, E/G, RTG, VE, ΔY, FUM, PEN). College team stats had 15 tabbed categories spanning offense, defense, special teams, turnovers, penalties, and analytics. Pro/WVL had no defensive stats at all — no opponent yards, no scoring defense, no turnover margins.

3. **"Back to League Hub" button didn't work** after completing a season. Clicking it appeared to do nothing — the page reloaded showing the same completed league instead of the hub.

## Root Cause Analysis

### Keeper stats: fast_sim never generates them

Pro leagues use `fast_sim_game()` by default (`use_fast_sim=True` in `ProLeagueSeason.sim_week()`). The fast sim's `_make_player_entry()` initializes `keeper_bells: 0`, `keeper_tackles: 0`, and `kick_deflections: 0`, but `_generate_player_stats()` never populates these fields for any player.

The defender loop (line 818) creates entries for Defensive Line, Linebacker, Cornerback, Lineman, and Keeper positions with tackles/TFL/sacks/hurries/ints — but no keeper-specific stats. The full game engine (`ViperballEngine`) does generate these stats (fixed in commit 947e9f8), but that code path is never hit during fast sim.

The accumulator in `pro_league.py:790` correctly reads `keeper_bells` from results — the data just wasn't there.

### Team stats: router only collected own-side stats

The `pro_team_stats()` router iterated `for side in ("home", "away")` and extracted only the current side's stats. It never looked at the opponent side's stats dict. The college router used `for side, opp_side in [("home", "away"), ("away", "home")]` and collected both `s = stats.get(side)` and `opp_s = stats.get(opp_side)`.

The pro router also didn't track scoring (points_for/points_against), special teams (kick/punt returns), or penalty details for opponents. The template had no category tabs — just one monolithic table.

### League Hub navigation: legacy storage re-activated the league

The `_back_to_hub()` callback correctly called `_set_active_league(None)` to clear `pro_league_active` in user storage. But `_get_session_and_dq()` has a legacy fallback path (lines 175-190) that checks `pro_league_session_id`. If that key still had a value, it found the season in `_pro_sessions`, re-migrated it to the new multi-session storage, called `_set_active_league(league_id)`, and returned the season — undoing the hub navigation.

The same issue affected the `_go_hub()` callback in the league switcher bar.

## Commits

| # | Hash | Summary |
|---|------|---------|
| 1 | `f9ade63` | Fix pro league stats parity: keeper stats, team stats tabs, and League Hub nav |

## Changes

### `engine/fast_sim.py`

Added keeper-specific stat generation in the defender loop. When a defender has `position == "Keeper"`, they now receive:
- `keeper_bells`: ~1.5/game (gaussian, mean=1.5, sd=1.0)
- `keeper_tackles`: ~3/game (gaussian, mean=3, sd=1.5)
- `kick_deflections`: ~1/game (gaussian, mean=1.0, sd=0.8)

Non-keeper defenders still get 0 for all three fields.

### `nicegui_app/pages/pro_leagues.py`

Added `app.storage.user["pro_league_session_id"] = None` to both `_back_to_hub()` and `_go_hub()` callbacks. This prevents the legacy fallback in `_get_session_and_dq()` from re-activating the league after the active league is cleared.

### `stats_site/router.py` — `pro_team_stats()`

Rewrote the aggregation loop to:
- Use `for side, opp_side in [("home", "away"), ("away", "home")]` instead of `for side in ("home", "away")`
- Collect opponent stats: `opp_total_yards`, `opp_rushing_yards`, `opp_kp_yards`, `opp_kp_comp`, etc.
- Collect scoring data: `points_for`, `points_against` from `game["home_score"]`/`game["away_score"]`
- Collect special teams: `kr_yards`, `kr_count`, `kr_tds`, `pr_yards`, `pr_count`, `pr_tds`, `muffs`
- Collect opponent special teams, turnovers (`opp_fumbles`, `opp_tod`), and penalties (`opp_penalties`, `opp_penalty_yards`)
- Compute derived stats: `ppg`, `opp_ppg`, `scoring_margin`, `avg_rushing`, `yards_per_carry`, `kp_ypg`, `kr_avg`, `pr_avg`, `turnover_margin`, `takeaways`, down conversion rates, `kill_rate`
- Add `_LOWER_IS_BETTER` set for correct sort direction on defensive stats
- Expand `valid_sorts` to include all new sort keys

### `stats_site/router.py` — `wvl_team_stats()`

Same changes as pro. The WVL router previously had a comment "same logic as pro_team_stats" and now both match the college-level fidelity.

### `stats_site/templates/pro/team_stats.html`

Replaced 110-line flat table with ~600-line tabbed template matching the college structure:
- **Offense tabs:** Scoring Offense, Total Offense, Rushing Offense, Kick-Pass Offense, Special Teams OFF
- **Defense tabs:** Scoring Defense, Total Defense, Rushing Defense, Kick-Pass Defense, Special Teams DEF, Turnovers, Penalties
- **Analytics tabs:** Efficiency (with 4D/5D/6D conversion rates), Delta System, Bonus Possessions

Uses Jinja `cat_map` dict to map sort keys to active categories, with `sort_url()` macro for clean URL generation. Division filter preserved.

### `stats_site/templates/wvl/team_stats.html`

Same tabbed redesign as pro, adapted for WVL (no division column, tier selector preserved, `t.get()` safety for optional fields).

## Key Decisions

1. **Generate keeper stats synthetically rather than switch to full engine.** The fast sim exists for performance (~1ms vs ~1-3s per game). Adding 3 gaussian distributions per keeper per game is negligible overhead vs switching pro leagues to the full engine.

2. **Match college template structure exactly.** Pro leagues are the flagship product — their stats should be at least as detailed as college. Used the same category names, sort keys, and table structures. Only differences are Div column (pro) vs Conf column (college), and no quarter-by-quarter scoring (fast sim doesn't generate play-by-play for quarter breakdowns).

3. **Clear legacy storage key rather than remove the fallback.** The `pro_league_session_id` legacy path still serves users who might have old sessions stored. Clearing the key on hub navigation is less disruptive than removing the fallback entirely.

## Lessons Learned

- **Fast sim stat gaps are invisible until someone checks the stats page.** The fast sim was built for score generation and basic stat distribution. Keeper stats were added to `_make_player_entry()` as fields but never wired up. Need to audit all stat categories when adding new ones to the full engine.

- **"Same logic as X" comments are a code smell.** The WVL router had "same logic as pro_team_stats" but both were independently limited. When the college router was upgraded with opponent stats, the pro and WVL routers weren't updated to match. Shared extraction logic would prevent this drift.

- **Legacy storage migration paths can create loops.** The `_get_session_and_dq()` legacy fallback was designed to migrate old single-session users to multi-session storage. But it also re-activates leagues that were intentionally deactivated, because clearing the active league doesn't clear the legacy key. Migration code needs to be one-way — it should not re-activate state that was explicitly cleared.
