# After Action Review — Tournament Scoring, Awards System, and Postseason Tracking

**Date:** 2026-03-21
**Branch:** `claude/tournament-win-scoring-NMcw8`

## Mission

Overhaul the CVL tournament scoring system so quality wins are properly scaled by opponent strength, fix media awards not appearing on player cards, revamp All-CVL team selection to use skill positions only, track coach postseason stats, add postseason history to team pages, and generate bowl/playoff MVPs.

## Incident / Starting State

Several interconnected issues:

1. **Quality win scoring was too narrow.** The old 7-tier system (top 5 through top 50, values 5.0 → 0.3) didn't differentiate enough between beating a top-5 team vs a top-10 team. Wins against teams ranked 51-100 counted for nothing. The 20-point cap compressed elite resumes.

2. **Rankings were retroactive.** If you beat a team ranked #3 in week 5 and they dropped to #20 by season end, your quality win was scored at their end-of-season ranking — punishing teams for opponents' late-season collapses.

3. **Media awards (AP, UPI, The Lateral, TSN) never appeared on player cards.** The `/season/awards` endpoint never called `compute_media_awards()`. Even when computed in dynasty mode, awards were written to `PlayerCard` objects but the roster API read from `Player` objects which didn't have `career_awards`.

4. **All-CVL teams included lineman slots** despite linemen having no meaningful offensive stats to differentiate. Players with 2 games played could make national teams because the only gate was `games > 0`.

5. **Coach career records were incomplete.** The dynasty `Coach` class didn't track conference titles, playoff wins, bowl wins, or bowl appearances. AI coaching staff (`CoachCard`) tracked playoff/conference stats but not season W/L or championships.

6. **Team pages showed award winners but nothing about postseason participation** — no bowl game results, no playoff round history.

7. **Bowl games and playoff games had no MVPs.**

8. **Best Kicker award went to players with 0 kick attempts** because the OVR-based fallback scored keepers with 99 kicking rating even if they never kicked.

## Commits

| # | Hash | Summary |
|---|------|---------|
| 1 | `2c3ef4a` | Scale quality wins with 5 rank tiers expanded to top 100 |
| 2 | `07e2a78` | Remove 20-point cap on quality wins component |
| 3 | `b0f10b2` | Use rankings at time of game for quality/loss scoring + add poll history to team page |
| 4 | `7f1073b` | Fix media awards on player cards + revamp All-CVL slot selection |
| 5 | `92d6ac2` | Track coach postseason stats, add team postseason section, bowl/playoff MVPs |

## Scope

8 files changed across engine, API, UI, and stats site.

### Files Modified

| File | What Changed |
|------|-------------|
| `engine/season.py` | New 5-tier quality win scoring, uncapped quality wins component, `_get_rankings_at_week()` for game-time rankings, `_pick_game_mvp()` for bowl/playoff MVPs, MVP assignment in `_play_round()` and `simulate_bowls()` |
| `engine/awards.py` | Removed lineman slots from `_AA_SLOTS`, added kicker slot + full kicker scoring pipeline, 50% games-played floor in `_best_in_position()`, fixed Best Kicker to require actual kick attempts |
| `engine/dynasty.py` | Added `conference_titles`, `playoff_wins`, `bowl_wins`, `bowl_appearances` to dynasty `Coach`; AI coaching staff now gets W/L, seasons, championships, and bowl wins updated each season |
| `api/main.py` | Awards endpoint now calls `compute_media_awards()` and `_apply_awards_to_players()` to write awards onto Player objects; coach serialization exposes new postseason fields |
| `nicegui_app/pages/league.py` | Poll ranking history on team browser, "Postseason Media Awards" section on awards page |
| `nicegui_app/pages/my_team.py` | Coach career display shows Conf. Titles, Postseason Apps, Postseason Wins |
| `stats_site/router.py` | Passes postseason game data and coach postseason stats to templates |
| `stats_site/templates/college/team.html` | New "Bowls & Playoff Appearances" section with result, opponent, score, MVP |
| `stats_site/templates/college/coach.html` | Shows Postseason Apps and Postseason Wins instead of zeroed-out separate fields |

## Key Decisions

### Quality Win Tiers
Went from 7 gates to 5 cleaner tiers with wider spread (10 pts for top-5 vs 1 pt for top-100). The old system had too many narrow bands (top 11-15: 2.5, top 16-20: 1.5) that didn't create meaningful separation. The new system is simpler and more impactful.

### Removing the Quality Win Cap
The 20-point cap compressed elite resumes. A team with two top-5 wins looked the same as a team with four. Removing the cap lets truly elite schedules stand out in the power index.

### Game-Time Rankings
Rankings at time of play matches how real-world selection committees evaluate resumes. Beating a team that was #3 when you played them is a top-5 win regardless of where they finish. The `_get_rankings_at_week()` method finds the most recent poll on or before the game week, falling back to record-based rankings if no poll exists yet.

### Skill Positions Only for All-CVL
Followed the user's basketball analogy — like basketball dropping the center position as the game evolved, viperball doesn't need to force lineman selections when there are no meaningful stats. The kicker slot was added since kicking is a measurable skill position. The 50% games-played floor prevents 2-GP players from making national teams.

### Combined Postseason Stats
Bowls and playoff appearances are combined into "Postseason Apps" and "Postseason Wins" rather than tracked separately, since variable playoff field sizes mean the line between bowl and playoff isn't as meaningful.

### MVP Selection
Uses a composite score of yards, TDs, kick pass yards, tackles, sacks, and WPA — position-agnostic so both offensive and defensive players can win. Assigned immediately after each game simulation.

## Impact

- Teams playing harder schedules get meaningfully more credit without overindexing (conference strength is still only 5 pts in the power index)
- No retroactive ranking inflation/deflation — your resume is what it was when you played
- Media awards now actually appear on player cards and the awards page in single-season mode
- Coaches tell a more complete story with conference titles, postseason records, and bowl results tracked across careers
- Team pages show full postseason participation history with game MVPs
- No more 2-GP wingbacks making First All-CVL or keepers with 0 kicks winning Best Kicker
