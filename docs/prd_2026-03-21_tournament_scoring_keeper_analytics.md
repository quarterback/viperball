# PRD: Tournament Scoring, Keeper Analytics & Awards Overhaul

**Date:** 2026-03-21
**Branch:** `claude/tournament-win-scoring-NMcw8`
**Status:** Implemented

---

## Problem Statement

The CVL awards and rankings system had several interconnected issues undermining competitive integrity and statistical credibility:

1. **Quality win scoring was too narrow.** The 7-tier system capped at top-50 and maxed at 20 points, compressing elite resumes and ignoring wins against teams ranked 51-100.

2. **Rankings were retroactive.** Beating a team ranked #3 in week 5 was scored at their end-of-season ranking — punishing teams whose opponents collapsed late.

3. **Low-volume players won awards.** A wingback with 1 carry for 86 yards (86.2 YPC) could make All-Conference because per-game rate stats inflated tiny sample sizes. The only gate was `games > 0`.

4. **Keepers had no meaningful analytics.** The position was lumped with safeties, scored using sacks and TFLs they rarely produce, with no stat capturing their actual defensive value.

5. **Lateral stats were overweighted.** An early-era vestige of the sport, laterals got their own scoring weight in awards formulas and a dedicated "Lateral Chain" section on player pages, despite most teams rarely using them.

6. **Game logs were incomplete.** No rushing yards column, no kick pass yards, no WPA — key stats tracked by the engine but never shown to users.

7. **Media awards, postseason history, and coach records were missing or broken** across the stats site and player cards.

---

## Solution

### 1. Quality Win Scoring Reform

**Before:** 7 tiers (top 5 → top 50), values 5.0 → 0.3, capped at 20 points.

**After:** 5 cleaner tiers with wider spread, no cap.

| Opponent Rank | Points |
|--------------|--------|
| Top 5 | 10.0 |
| Top 10 | 7.0 |
| Top 25 | 4.0 |
| Top 50 | 2.0 |
| Top 100 | 1.0 |

Rankings are now evaluated **at the time of the game** via `_get_rankings_at_week()`, not retroactively. Beating a team that was #3 when you played them is a top-5 win permanently.

### 2. Awards Eligibility Gates

All award paths — All-Conference, All-National, MVP, POY, Best Kicker, Diamond Gloves, Freshman of the Year — now require:

- **80% of team games played** (up from 50%)
- **Position-specific volume minimums:**
  - Backs: ≥ 2 carries per game played
  - Zerobacks: ≥ 2 kick pass attempts per game played
  - Vipers: nonzero yards or TDs

Enforced via `_passes_volume_gate()` applied consistently across every award selection path.

### 3. Keeper Analytics: KPR and ERA

Keepers are now their own position group (`keeper_def`), separate from safeties, with two defensive analytics stats:

#### KPR (Keeper Rating)
- **Type:** Composite counting stat. **Higher is better.**
- **Scale:** 0–10
- **Formula:** `(deflections * 10 + keeper_tackles * 5 + bells * 8 + tackles * 2 + coverage_snaps * 0.3 - muffs * 6) / games`, scaled by 0.8
- **Measures:** Total defensive impact — disrupting the aerial attack (deflections), last-line stops (tackles), loose ball recoveries (bells), involvement (coverage snaps), minus mistakes (muffs)

#### Keeper ERA
- **Type:** Rate stat. **Lower is better.**
- **Scale:** 0.00–9.99 (mirrors baseball ERA)
- **Formula:** `(points_allowed_in_coverage / coverage_snaps) * 9`
- **Measures:** How many points the opposition scores while this keeper is the coverage defender, per 9 coverage snaps
- **Tiers:** Elite < 2.50 | Good 2.50–4.00 | Average 4.00–5.50 | Poor > 5.50

#### Per-Play Attribution (Engine Changes)
ERA is built on real per-play tracking, not team-level proxying:

- **`game_points_allowed_in_coverage`** — When any score happens, `add_score()` calls `_attribute_points_to_keeper()` which finds the defending team's primary keeper/safety and charges them with the points. The keeper is the captain of the backline; all scoring goes against their ERA, like a goalie in hockey.
- **`game_completions_allowed_in_coverage`** — When a kick pass is completed and the `matched_defender` is a keeper or safety, the completion is attributed to them.
- **`game_coverage_snaps`** — Incremented on each scoring play attribution and existing coverage duty tracking.

#### Awards Scoring
Keeper scoring uses a **50/50 blend** of KPR and inverted ERA:
```
score = KPR * 0.5 + (10.0 - ERA) * 0.5
```

### 4. Diamond Gloves Award

**New award** for keepers and safeties, national and conference level.

- Selection: Highest combined KPR + inverted ERA score
- Eligibility: 80% GP, ≥ 20 coverage snaps, ≥ .500 team record (national)
- Display: Shows both KPR and ERA in the award description

### 5. Lateral Deemphasis

- **Awards scoring:** `lateral_yards` removed from zeroback, viper, and any-offense formulas. Weight redistributed to rushing/kick pass yards.
- **Player pages:** Standalone "Lateral Chain" section eliminated. Lateral stats folded into a single line in the Rushing section, shown only when nonzero.
- **Stat line displays:** Lateral yards removed from viper award stat lines.

Laterals still exist in leaderboard tabs and the Best Lateral Specialist award — they're opt-in rather than front-and-center.

### 6. Game Log Expansion

Player game logs now show:

| Column | Stat | New? |
|--------|------|------|
| TCH | Touches | |
| **RUSH** | **Rushing Yards** | **Yes** |
| YDS | Total Yards | |
| TD | Touchdowns | |
| FUM | Fumbles | |
| KM/KA | Kicks Made/Attempted | |
| **KP** | **Kick Pass Comp/Att** | **Yes** |
| **KPY** | **Kick Pass Yards** | **Yes** |
| **RET** | **Return Yards** | **Yes** |
| TKL | Tackles | |
| SCK | Sacks | |
| **WPA** | **Win Probability Added** | **Yes** |

Applied to both college and WVL player pages.

### 7. All-Conference / All-National Team Changes

- Keepers now have a dedicated **Keeper** slot (was lumped into "Safety/Keeper")
- Safeties retain their own **Safety** slot
- Total slots increased from 9 to 10 per team

### 8. Player Page: Keeper Section

The Keeper section on player pages now displays:

- **KPR** (color-coded: ≥ 7.0 elite, ≥ 4.0 good)
- **ERA** (color-coded: ≤ 2.50 elite, ≤ 4.00 good, ≥ 6.00 bad)
- Keeper Tackles, Bells, Kick Deflections, Coverage Snaps
- **Pts Allowed** — total points scored while in coverage
- **Comp. Allowed** — kick pass completions allowed in coverage
- Muffs (shown only when > 0, highlighted as bad)
- Keeper Return Yards (when applicable)

### 9. Postseason & Media Awards Fixes

- Media awards now appear on player cards (endpoint calls `compute_media_awards()`)
- Coach postseason stats tracked: conference titles, playoff wins, bowl wins, bowl appearances
- Team pages show bowl/playoff participation history with MVPs
- Bowl and playoff game MVPs generated via `_pick_game_mvp()`

---

## Files Changed

| File | Changes |
|------|---------|
| `engine/game_engine.py` | Per-play ERA tracking: `game_points_allowed_in_coverage`, `game_completions_allowed_in_coverage`, `_attribute_points_to_keeper()`, completion attribution to matched_defender |
| `engine/awards.py` | New `keeper_def` position group, `_compute_kpr()`, `_compute_keeper_era()`, `_passes_volume_gate()`, Diamond Gloves award (national + conference), lateral deemphasis in scoring, 80% GP + volume gates on all award paths, dedicated Keeper slot in `_AA_SLOTS` |
| `engine/player_card.py` | `points_allowed_in_coverage` and `completions_allowed_in_coverage` on GameLog and SeasonStats, accumulation in `add_game()` |
| `engine/season.py` | Quality win tiers, uncapped quality wins, game-time rankings, bowl/playoff MVPs |
| `engine/dynasty.py` | Coach postseason stat tracking |
| `api/main.py` | Media awards pipeline fix |
| `stats_site/router.py` | KPR/ERA computation in season_totals, new stat aggregation |
| `stats_site/templates/college/player.html` | Game log columns (RUSH, KP, KPY, RET, WPA), Keeper section with KPR/ERA/Pts Allowed/Comp. Allowed, lateral section folded into rushing |
| `stats_site/templates/wvl/player.html` | Same as college player template |
| `stats_site/templates/college/team.html` | Postseason history section |

---

## Commits

| # | Hash | Summary |
|---|------|---------|
| 1 | `2c3ef4a` | Scale quality wins with 5 rank tiers expanded to top 100 |
| 2 | `07e2a78` | Remove 20-point cap on quality wins component |
| 3 | `b0f10b2` | Use rankings at time of game for quality/loss scoring |
| 4 | `7f1073b` | Fix media awards on player cards + revamp All-CVL slot selection |
| 5 | `92d6ac2` | Track coach postseason stats, team postseason section, bowl/playoff MVPs |
| 6 | `0a592f6` | Require 80% games played + minimum volume for all awards |
| 7 | `77e2a14` | Add KPY, RET, and WPA columns to player game logs |
| 8 | `d6b9dd5` | Add RUSH column to game logs, deemphasize laterals across stats |
| 9 | `352bae7` | Add Keeper Rating (KPR), Keeper ERA, and Diamond Gloves award |
| 10 | `e3af98a` | Track actual points/completions allowed per keeper for real ERA |
