## After-Action Review — March 3, 2026

### wVL Mode: Tie Support, Box Score Parity, and /stats Wiring

**Branch:** `claude/improve-wvl-mode-Ffp0p`
**Files Modified:** `engine/pro_league.py`, `nicegui_app/pages/pro_leagues.py`, `stats_site/router.py`, `stats_site/templates/base.html`, `stats_site/templates/wvl/season.html`, `stats_site/templates/wvl/game.html`, `stats_site/templates/wvl/schedule.html`, `stats_site/templates/wvl/team.html`

---

### Problem Statement

Three distinct gaps existed between the wVL (Women's Viperball League) experience and the rest of the sim:

**1. Draws were silently corrupted into double losses**

`ProTeamRecord.record_result()` took a `won: bool` parameter. When two teams scored equal points, `sim_week()` called `record_result(won=home_score > away_score, ...)` and `record_result(won=away_score > home_score, ...)`, both of which evaluated to `False`. Both teams recorded a loss. Neither got a point. The table points were wrong. The standings were wrong. The streak tracking was wrong. The div record was wrong.

This mattered because the wVL is a soccer-style pyramid with promotion and relegation — draws are a normal, common result (roughly 20–25% of professional soccer fixtures). Mis-counting them as losses could push a club into a relegation zone it didn't deserve to be in, or deny a promotion to a team that earned it via draws.

There was also no T column in the standings at all, so even if a draw had been properly detected, there was nowhere to display it.

**2. wVL box scores were abbreviated or blank**

The NiceGUI in-app box score dialog (shared between wVL and pro leagues, defined in `pro_leagues.py`) had five tabs: Team Stats, Offense, Defense, Kicking, Forum Export. For wVL games, which are usually fast-simmed, the Offense/Defense/Kicking tabs were silently blank — the loop iterated over player stats, found empty lists, called `continue`, and rendered nothing. There was no indication that this was a fast-sim limitation rather than a bug.

There was also no quarterly scoring breakdown anywhere in the dialog — the CVL/international dialogs show a Q1-Q2-Q3-Q4 scoring line, but the wVL dialog jumped straight to stats tables.

On the `/stats` site, `wvl/game.html` was also missing two sections present in `college/game.html`: Play Distribution (counts by play family) and Plays Per Quarter. The data was available in the box dict — it just wasn't being rendered.

Both score cells in `wvl/game.html` and `wvl/schedule.html` used a two-way conditional: `{% if score > other %}score-win{% else %}score-loss{% endif %}`. A draw assigned `score-loss` styling to both teams, which was wrong and confusing.

**3. Recent engineer work on the financial dashboard wasn't surfaced on /stats**

The previous engineer added a financial dashboard (`get_owner_team_summary`, dynasty `financial_history`, `InvestmentAllocation`) to the wVL owner mode UI. None of that data reached the `/stats/wvl/{id}/team/{key}` page for the owner's club. A user who navigated from the in-app dashboard to the stats site for their club would see no trace of what they'd spent or earned.

---

### What We Did

#### 1. Full Tie Support in the Engine (`engine/pro_league.py`)

**`ProTeamRecord` dataclass:**

Added `ties: int = 0` and `div_ties: int = 0` fields. Added a `points` property implementing the standard 3/1/0 soccer table points:

```python
@property
def points(self) -> int:
    return 3 * self.wins + self.ties
```

Updated `pct` to weight draws as half a win:

```python
@property
def pct(self) -> float:
    total = self.wins + self.losses + self.ties
    return (self.wins + 0.5 * self.ties) / total if total > 0 else 0.0
```

**`record_result()` — signature change from `won: bool` to `won: Optional[bool]`:**

- `won=True` → win (existing behaviour)
- `won=False` → loss (existing behaviour)
- `won=None` → draw (new)

The `"T"` character is now a valid `streak_type` and can appear in `last_5`. Division tracking gets `div_ties` incremented on draws.

**`sim_week()` — tie detection:**

```python
is_tie = home_score == away_score
self.standings[matchup.home_key].record_result(
    won=None if is_tie else (home_score > away_score), ...
)
self.standings[matchup.away_key].record_result(
    won=None if is_tie else (away_score > home_score), ...
)
```

Previously, a 14–14 final would call `record_result(won=False)` for both teams. Now it calls `record_result(won=None)` for both.

**`get_standings()` — sort and display:**

Sort key changed from `(-r.wins, -r.pct, -r.point_diff)` to `(-r.points, -r.pct, -r.point_diff)`. Each team dict now includes `"ties"`, `"points"`, and an updated `"div_record"` formatted as W-L-T.

**`get_team_detail()` — record and schedule:**

The `rec_dict` now exposes `"ties"` and `"points"`. The per-game schedule entries now tag draws as `won=None` (they were previously `won=False`).

---

#### 2. Stats Site: Standings (`stats_site/templates/wvl/season.html`)

The standings table previously had a single `W-L` column. It now has four separate columns:

| PTS | W | L | T |
|-----|---|---|---|

`PTS` (bold, bright) is the primary visible sort indicator. `T` draws are shown dimmed since they're usually 0 at the start of a season.

The `last_5` loop now assigns `.t` (amber) for draw characters alongside the existing `.w` (green) and `.l` (red).

Both the ranked-tier table and the division sub-table received the same treatment.

**`stats_site/templates/base.html`:**

Added two new global CSS classes:

```css
.t { color: var(--yellow); }
.score-tie { color: var(--yellow); font-weight: bold; }
```

These cascade to all templates that use them — schedule, game, and team pages.

---

#### 3. Stats Site: Game Template (`stats_site/templates/wvl/game.html`)

**Tie CSS fix:**

Two-way conditionals replaced with three-way:

```html
{% if score > other %}score-win{% elif score < other %}score-loss{% else %}score-tie{% endif %}
```

The center label between the scores now reads `DRAW` instead of `FINAL` when scores are equal.

**Play Distribution (ported from `college/game.html`):**

Uses `stats.home.play_family_breakdown` / `stats.away.play_family_breakdown` — a dict of `{family_name: count}` already present in the fast-sim output. Renders a side-by-side table showing how many plays each team ran by family (rush, kick_pass, lateral, etc.). Wrapped in `{% if a_pfb or h_pfb %}` so it only appears when data exists.

**Plays Per Quarter (ported from `college/game.html`):**

Uses `stats.home.plays_per_quarter` / `stats.away.plays_per_quarter` — a dict of `{quarter_num: count}`. Same guard pattern.

Both sections are placed after Team Stats and before Player Stats.

---

#### 4. Stats Site: Schedule Template (`stats_site/templates/wvl/schedule.html`)

Score cells in both schedule table formats (dict-of-weeks and list-of-week-objects) updated to use the three-way win/loss/draw CSS. Intermediary `as_` / `hs_` variables extracted to avoid evaluating `g.get(...)` twice.

---

#### 5. Stats Site: Team Template (`stats_site/templates/wvl/team.html`)

**Record display:**

The `ties` variable is now extracted from the `rec` dict alongside `wins` and `losses`. The metric card shows:

```
W-L     (when ties == 0)
W-L-T   (when ties > 0, T in amber)
```

**Schedule result column:**

Games tagged `won=None` now display `D` (amber) rather than `L` (red). The result class/label are derived through a three-way conditional on `won_val`:

```python
result_class = 'w' if won_val == true else ('l' if won_val == false else 't')
result_label = 'W' if won_val == true else ('L' if won_val == false else 'D')
```

Note: Jinja2 `== true` and `== false` are used rather than Python `is True` / `is False` because Jinja2 evaluates `None == false` as truthy without the explicit equality check.

**Club Finances section (owner club only):**

A new section appears at the bottom of the team page when `is_owner_club` is true and `financial` data is available. It displays:

- Bankroll (green, in $M)
- Owner archetype
- Revenue and expenses from the most recent season (from `financial_history`)
- Investment Allocation table — each non-zero category and its level, with `stat-elite` / `stat-good` coloring for high-investment areas

---

#### 6. Stats Site Router (`stats_site/router.py`)

The `wvl_team` route now builds a `financial` snapshot dict from the dynasty object stored in `wvl_sessions[session_id]["dynasty"]`:

```python
financial = {
    "bankroll": owner.bankroll,
    "archetype": owner.archetype,
    "investment": { training, coaching_staff, stadium, youth_academy, sports_science, marketing },
    "season_financials": latest_fin,   # from financial_history[current_year]
}
```

This is only constructed when `is_owner_club` is true. It's passed to the template as `financial=financial` (else `financial=None`, and the template section is suppressed).

No dynasty methods were modified — the data was already computed and stored by the previous engineer's work; it just needed a read path to the stats site.

---

#### 7. NiceGUI Box Score Dialog (`nicegui_app/pages/pro_leagues.py`)

**Tie-aware score display:**

The header score block now computes `is_draw = away_s == home_s` and uses it to:
- Color tied scores in `text-yellow-400` instead of `text-slate-400`
- Show `"DRAW"` instead of `"FINAL"` in the label

**`_render_quarterly_scoring()` (new function):**

Computes per-quarter scores by walking the play-by-play list (when available) and accumulating score deltas per quarter — the same algorithm used in `engine/box_score.py`. Renders a compact 6-column table (Team | Q1 | Q2 | Q3 | Q4 | F) placed above the tab bar in every box score dialog.

For fast-simmed games without play-by-play, all quarter cells show `0` and only the final score column is meaningful — this is acceptable since the game was not tracked play-by-play.

**`_render_drives()` (new function) + "Drives" tab:**

Reads `box.get("drive_summary", [])` — already returned by `get_box_score()` — and renders a table with columns: `#`, Team, Start, Plays, Yards, Result. Scoring drives are highlighted green. An empty `drive_summary` shows a graceful "No drive data available" message.

The tab bar now has six tabs: Team Stats, Offense, Defense, Kicking, **Drives**, Forum Export.

**Graceful empty state for player stat tabs:**

`_render_offense_stats`, `_render_defense_stats`, and `_render_kicking_stats` now check for player data presence up front:

```python
has_any = any(box.get(f"{side}_player_stats", []) for side in ("away", "home"))
if not has_any:
    ui.label("Player stats not available for fast-simmed games.").classes(...)
    return
```

Previously these functions silently skipped empty lists and rendered nothing, leaving tabs blank with no explanation. The message makes the fast-sim limitation explicit rather than looking like a bug.

---

### What Was Not Changed

**CVL tie prevention in `_fast_sim_game`:** CVL playoff brackets still force a winner by adding random points on a tied score. This is correct — CVL is an American college league with a playoff bracket where ties are impossible. The ProTeamRecord changes only affect `ProLeagueSeason`, which is the base class for wVL and other pro leagues, not the CVL `Season` class.

**`_generate_pro_forum_box_score` / the Forum Export tab:** The existing forum export function was left as-is. It reads team stats, not quarterly data, so it doesn't need the play_by_play walk.

**Promotion/relegation cutoffs:** The engine's promotion/relegation logic already uses `get_standings()` output for ranking — it reads `position` from the ranked list, which is now ordered by `points`. No additional change was needed there.

---

### Known Limitations and Follow-Up Candidates

- **Streak label for draws:** The streak display shows `T3` for a three-game unbeaten-draw run. This is technically correct but unusual. Some leagues might prefer `U3` (unbeaten). Not changed since it would require a template-level style decision, not an engine fix.

- **PCT column for soccer:** Win percentage (`PCT`) remains in the standings as a tiebreaker. In real soccer tables, `PCT` isn't shown at all — points, goal difference, and goals scored are the tiebreakers. The `PCT` column is harmless but could be replaced with a goal-difference-only tiebreaker display in a future pass.

- **Fast-sim quarterly scores show all zeros:** The quarterly table in the NiceGUI dialog gracefully degrades when play-by-play is absent, but the zero-filled quarters could confuse a user who doesn't know what fast-sim means. A label like "( fast-sim — quarterly breakdown unavailable )" could be added conditionally.

- **Financial history on /stats requires a saved dynasty:** If the user views a team page on `/stats` before completing a full season with the offseason wizard (i.e., `financial_history` is empty), the Club Finances section is suppressed. This is correct behavior — there's nothing to show — but a note like "No financial history yet" could improve clarity.
