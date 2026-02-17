# Viperball UI Implementation Spec
## Handoff for: Streamlit UI Engineer

This document describes all backend systems that have been built and exactly what
needs to be implemented in `ui/app.py` to expose them.

---

## WHAT ALREADY EXISTS

### Current UI (`ui/app.py`) — 3 pages:
1. **Game Simulator** — pick 2 teams, offensive style only, run 1 game, see box score + play-by-play
2. **Debug Tools** — batch simulation, score distributions, fatigue curves
3. **Play Inspector** — single play runner with stats

### Current imports in `ui/app.py`:
```python
from engine import ViperballEngine, load_team_from_json, get_available_teams, get_available_styles, OFFENSE_STYLES
```

---

## WHAT WAS BUILT (backend only, no UI yet)

### 1. Defensive Styles (`engine/game_engine.py`)

A full defensive system now exists alongside offensive styles. Import:
```python
from engine.game_engine import DEFENSE_STYLES
```

`DEFENSE_STYLES` is a dict with keys:
- `"pressure_defense"` — aggressive, blocks kicks, creates turnovers
- `"coverage_defense"` — suppresses kick distance, prevents pindowns, forces muffs
- `"contain_defense"` — shuts down laterals, limits explosive plays
- `"run_stop_defense"` — elite vs power/sweep option runs
- `"base_defense"` — balanced fundamentals

Each entry has `"label"` and `"description"` keys (same shape as `OFFENSE_STYLES`).

Style overrides are passed to the engine like this:
```python
style_overrides = {
    home_team.name: home_offense_style,           # existing
    away_team.name: away_offense_style,            # existing
    f"{home_team.name}_defense": home_def_style,  # NEW
    f"{away_team.name}_defense": away_def_style,  # NEW
}
engine = ViperballEngine(home_team, away_team, seed=seed, style_overrides=style_overrides)
```

### 2. Viperball Metrics (`engine/viperball_metrics.py`)

After `engine.simulate_game()` returns `result`, call:
```python
from engine.viperball_metrics import calculate_viperball_metrics

home_metrics = calculate_viperball_metrics(result, 'home')
away_metrics  = calculate_viperball_metrics(result, 'away')
```

Each metrics dict has these keys (all 0–100 except drive_quality which is 0–10):
```python
{
    "opi":               float,  # Overall Performance Index (0-100)
    "territory_rating":  float,  # Field position dominance (0-100)
    "pressure_index":    float,  # Clutch conversion rate (0-100)
    "chaos_factor":      float,  # Lateral/explosive success (0-100)
    "kicking_efficiency":float,  # Pindowns + kick accuracy (0-100)
    "drive_quality":     float,  # Points per drive (0-10)
    "turnover_impact":   float,  # Net turnovers created (0-100)
}
```

### 3. Special Teams Events (`engine/game_engine.py`)

Three new `result` values now appear in `play_by_play`:
- `"blocked_punt"` — punt blocked at line
- `"muffed_punt"` — returner dropped the punt
- `"blocked_kick"` — FG or snapkick blocked

These show up in `p["result"]` in the play-by-play list. Descriptions include
phrases like "BLOCKED", "MUFFED", "RETURNED FOR TOUCHDOWN".

### 4. Season Simulation (`engine/season.py` + `engine/season_ui.py`)

```python
from engine import load_team_from_json
from engine.season import create_season

# Build teams dict and style_configs dict (team_name → {offense_style, defense_style})
teams = {"Gonzaga": load_team_from_json(...), ...}
style_configs = {
    "Gonzaga": {"offense_style": "territorial", "defense_style": "coverage_defense"},
    ...
}

season = create_season("2026 Season", teams, style_configs)
season.generate_round_robin_schedule()   # populates season.schedule (List[Game])
season.simulate_season()                 # simulates all regular season games
season.simulate_playoff(num_teams=8)     # runs 8-team playoff bracket

# Access results:
season.schedule          # List[Game] — each has .week, .home_team, .away_team, .home_score, .away_score
season.standings         # Dict[team_name, TeamRecord]
season.champion          # str — winning team name
season.playoff_bracket   # List[Game] — playoff games (week 998=QF, 999=SF, 1000=final)
```

`TeamRecord` attributes (from `season.standings[name]`):
```python
record.team_name
record.wins / record.losses
record.win_percentage       # 0.0–1.0
record.points_for / record.points_against
record.point_differential   # per game average
record.avg_opi              # season average OPI
record.avg_territory / avg_pressure / avg_chaos / avg_kicking / avg_drive_quality / avg_turnover_impact
record.offense_style / record.defense_style
record.games_played
```

Sorted standings:
```python
season.get_standings_sorted()   # List[TeamRecord], best first
season.get_playoff_teams(8)     # top 8 for playoffs
```

### 5. Dynasty Mode (`engine/dynasty.py` + `engine/dynasty_ui.py`)

```python
from engine.dynasty import create_dynasty

dynasty = create_dynasty(
    dynasty_name="My Dynasty",
    coach_name="Coach Smith",
    coach_team="Gonzaga",
    starting_year=2026
)
dynasty.add_conference("Big East", list(teams.keys()))

# After each season:
dynasty.advance_season(season)   # updates all records, advances current_year by 1

# Save / load:
dynasty.save("path/save.json")
dynasty = Dynasty.load("path/save.json")
```

Key data structures after multiple seasons:

`dynasty.coach` (Coach):
```python
coach.name / coach.team_name
coach.career_wins / career_losses / win_percentage
coach.championships / playoff_appearances
coach.years_coached          # list of ints
coach.season_records         # {year: {wins, losses, points_for, points_against, champion, playoff}}
```

`dynasty.team_histories` (Dict[str, TeamHistory]):
```python
h = dynasty.team_histories["Gonzaga"]
h.total_wins / total_losses / win_percentage
h.total_championships / championship_years   # list of ints
h.total_playoff_appearances
h.points_per_game
h.best_season_wins / best_season_year
h.season_records   # {year: {wins, losses, points_for, points_against, avg_opi, champion, playoff}}
```

`dynasty.awards_history` (Dict[int, SeasonAwards]):
```python
a = dynasty.awards_history[2026]
a.year / a.champion / a.best_record / a.highest_scoring
a.best_defense / a.highest_opi / a.most_chaos / a.best_kicking
```

`dynasty.record_book` (RecordBook):
```python
rb = dynasty.record_book
rb.most_wins_season       # {"team": str, "wins": int, "year": int}
rb.most_points_season     # {"team": str, "points": float, "year": int}
rb.best_defense_season    # {"team": str, "ppg_allowed": float, "year": int}
rb.highest_opi_season     # {"team": str, "opi": float, "year": int}
rb.most_chaos_season      # {"team": str, "chaos": float, "year": int}
rb.most_championships     # {"team": str, "championships": int}
rb.highest_win_percentage # {"team": str, "win_pct": float, "games": int}
rb.most_coaching_wins          # {"coach": str, "wins": int}
rb.most_coaching_championships # {"coach": str, "championships": int}
```

---

## WHAT NEEDS TO BE BUILT IN `ui/app.py`

Add these navigation pages to `st.sidebar.radio`:

```python
page = st.sidebar.radio("Navigation", [
    "Game Simulator",
    "Season Mode",
    "Dynasty Mode",
    "Debug Tools",
    "Play Inspector",
], index=0)
```

---

### CHANGE 1 — Game Simulator: Add Defensive Style Selectors

In the existing home/away column layout, add a defensive style selector
**below each offensive style selector**:

```python
# Add this import at top of file
from engine.game_engine import DEFENSE_STYLES

defense_style_keys = list(DEFENSE_STYLES.keys())

# In col1 (home team section), after home_style selectbox:
home_def_style = st.selectbox(
    "Home Defense Style",
    defense_style_keys,
    format_func=lambda x: DEFENSE_STYLES[x]["label"],
    key="home_def_style"
)
st.caption(DEFENSE_STYLES[home_def_style]["description"])

# In col2 (away team section), after away_style selectbox:
away_def_style = st.selectbox(
    "Away Defense Style",
    defense_style_keys,
    format_func=lambda x: DEFENSE_STYLES[x]["label"],
    key="away_def_style"
)
st.caption(DEFENSE_STYLES[away_def_style]["description"])
```

Update the style_overrides dict:
```python
style_overrides = {
    home_team.name: home_style,
    away_team.name: away_style,
    f"{home_team.name}_defense": home_def_style,
    f"{away_team.name}_defense": away_def_style,
}
```

---

### CHANGE 2 — Game Simulator: Add Metrics Dashboard

After the box score section, add a **Viperball Metrics** section:

```python
from engine.viperball_metrics import calculate_viperball_metrics

# After result is computed:
home_metrics = calculate_viperball_metrics(result, 'home')
away_metrics  = calculate_viperball_metrics(result, 'away')

st.subheader("Viperball Metrics")
st.caption("All metrics are 0–100 (higher = better). Drive Quality is 0–10.")

metric_labels = {
    "opi":                "⭐ Overall Performance Index",
    "territory_rating":   "🗺️  Territory Rating",
    "pressure_index":     "💪 Pressure Index",
    "chaos_factor":       "⚡ Chaos Factor",
    "kicking_efficiency": "👟 Kicking Efficiency",
    "drive_quality":      "📍 Drive Quality",
    "turnover_impact":    "🛡️  Turnover Impact",
}
metric_max = {k: 10 if k == "drive_quality" else 100 for k in metric_labels}

rows = []
for key, label in metric_labels.items():
    rows.append({
        "Metric": label,
        home_name: round(home_metrics.get(key, 0), 1),
        away_name: round(away_metrics.get(key, 0), 1),
    })
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# Radar chart comparing both teams
import plotly.graph_objects as go

radar_keys = ["opi", "territory_rating", "pressure_index", "chaos_factor", "kicking_efficiency", "turnover_impact"]
radar_labels = [metric_labels[k] for k in radar_keys]

fig = go.Figure()
fig.add_trace(go.Scatterpolar(
    r=[home_metrics.get(k, 0) for k in radar_keys],
    theta=radar_labels, fill='toself', name=home_name
))
fig.add_trace(go.Scatterpolar(
    r=[away_metrics.get(k, 0) for k in radar_keys],
    theta=radar_labels, fill='toself', name=away_name
))
fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100])), height=400,
                  title="Performance Radar")
st.plotly_chart(fig, use_container_width=True)
```

---

### CHANGE 3 — Game Simulator: Add Special Teams Events Panel

In the existing Debug Panel expander, add a Special Teams section:

```python
st.markdown("**Special Teams Events**")
blocked_punts = [p for p in plays if p.get("result") == "blocked_punt"]
muffed_punts  = [p for p in plays if p.get("result") == "muffed_punt"]
blocked_kicks = [p for p in plays if p.get("result") == "blocked_kick"]

st_c1, st_c2, st_c3 = st.columns(3)
st_c1.metric("Blocked Punts", len(blocked_punts))
st_c2.metric("Muffed Punts",  len(muffed_punts))
st_c3.metric("Blocked Kicks", len(blocked_kicks))

all_st_events = blocked_punts + muffed_punts + blocked_kicks
if all_st_events:
    for ev in sorted(all_st_events, key=lambda p: p["play_number"]):
        st.text(f"  Q{ev['quarter']} | {ev['result'].replace('_',' ').upper()} | {ev['description']}")
else:
    st.caption("No special teams chaos this game.")
```

Also update `drive_result_label` and `drive_result_color` to handle the new results:
```python
def drive_result_label(result):
    labels = {
        # ... existing ...
        "blocked_punt": "BLOCKED PUNT",
        "muffed_punt":  "MUFFED PUNT",
        "blocked_kick": "BLOCKED KICK",
    }
    return labels.get(result, result.upper())

def drive_result_color(result):
    colors = {
        # ... existing ...
        "blocked_punt": "#a855f7",
        "muffed_punt":  "#ec4899",
        "blocked_kick": "#a855f7",
    }
    return colors.get(result, "#94a3b8")
```

---

### NEW PAGE 1 — Season Mode

Full page for single-season simulation with standings, playoff bracket, and award display.

```python
elif page == "Season Mode":
    st.title("Season Simulation")

    from engine.season import create_season

    # --- Team & Conference Setup ---
    st.subheader("Configure Season")

    available_team_keys = [t["key"] for t in teams]
    selected_keys = st.multiselect(
        "Select teams (6–12 recommended)",
        available_team_keys,
        default=available_team_keys[:8],
        format_func=lambda x: team_names[x],
        key="season_teams"
    )

    if len(selected_keys) < 4:
        st.warning("Select at least 4 teams.")
        st.stop()

    # Style config per team (use expanders)
    st.subheader("Team Styles")
    style_configs = {}
    for key in selected_keys:
        with st.expander(f"{team_names[key]} styles"):
            o_style = st.selectbox(f"Offense", style_keys,
                                   format_func=lambda x: styles[x]["label"],
                                   key=f"season_o_{key}")
            d_style = st.selectbox(f"Defense", defense_style_keys,
                                   format_func=lambda x: DEFENSE_STYLES[x]["label"],
                                   key=f"season_d_{key}")
            style_configs[team_names[key]] = {
                "offense_style": o_style,
                "defense_style": d_style,
            }

    playoff_size = st.selectbox("Playoff field", [4, 8], index=1)
    season_seed  = st.number_input("Season seed (0=random)", 0, 999999, 0, key="season_seed")

    run_season = st.button("Simulate Season", type="primary", use_container_width=True)

    if run_season:
        actual_seed = season_seed if season_seed > 0 else random.randint(1, 999999)
        random.seed(actual_seed)

        team_objects = {team_names[k]: load_team(k) for k in selected_keys}
        year = 2026   # or pull from dynasty state if wired up later

        season = create_season(f"{year} Season", team_objects, style_configs)
        season.generate_round_robin_schedule()

        with st.spinner(f"Simulating {len(season.schedule)} regular season games..."):
            season.simulate_season()

        with st.spinner("Running playoffs..."):
            season.simulate_playoff(num_teams=playoff_size)

        st.session_state["season_result"] = season

    if "season_result" in st.session_state:
        season = st.session_state["season_result"]
        standings = season.get_standings_sorted()

        # --- Champion Banner ---
        if season.champion:
            st.success(f"🏆 Champion: **{season.champion}**")

        # --- Standings Table ---
        st.subheader("Standings")
        rows = []
        for i, r in enumerate(standings, 1):
            rows.append({
                "#": i,
                "Team": r.team_name,
                "Offense": r.offense_style.replace("_", " ").title(),
                "Defense": r.defense_style.replace("_", " ").title(),
                "W": r.wins,
                "L": r.losses,
                "Win%": f"{r.win_percentage*100:.1f}%",
                "PF/G": f"{r.points_for/max(1,r.games_played):.1f}",
                "PA/G": f"{r.points_against/max(1,r.games_played):.1f}",
                "DIFF": f"{r.point_differential:+.1f}",
                "OPI": f"{r.avg_opi:.1f}",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        # --- Season Awards ---
        st.subheader("Season Awards")
        best_record    = standings[0]
        highest_score  = max(standings, key=lambda r: r.points_for/max(1,r.games_played))
        best_defense   = min(standings, key=lambda r: r.points_against/max(1,r.games_played))
        highest_opi    = max(standings, key=lambda r: r.avg_opi)
        most_chaos     = max(standings, key=lambda r: r.avg_chaos)
        best_kicking   = max(standings, key=lambda r: r.avg_kicking)

        aw1, aw2, aw3 = st.columns(3)
        aw1.metric("🥇 Best Record",     f"{best_record.team_name} ({best_record.wins}-{best_record.losses})")
        aw2.metric("⚡ Highest Scoring", f"{highest_score.team_name} ({highest_score.points_for/max(1,highest_score.games_played):.1f} PPG)")
        aw3.metric("🛡️  Best Defense",   f"{best_defense.team_name} ({best_defense.points_against/max(1,best_defense.games_played):.1f} PA/G)")
        aw4, aw5, aw6 = st.columns(3)
        aw4.metric("⭐ Highest OPI",     f"{highest_opi.team_name} ({highest_opi.avg_opi:.1f})")
        aw5.metric("💥 Chaos Award",     f"{most_chaos.team_name} ({most_chaos.avg_chaos:.1f})")
        aw6.metric("👟 Kicking Award",   f"{best_kicking.team_name} ({best_kicking.avg_kicking:.1f})")

        # --- Metrics Leaderboard ---
        st.subheader("Season Metrics Leaderboard")
        metric_cols = {
            "OPI": "avg_opi",
            "Territory": "avg_territory",
            "Pressure": "avg_pressure",
            "Chaos": "avg_chaos",
            "Kicking": "avg_kicking",
            "Drive Quality": "avg_drive_quality",
            "Turnover Impact": "avg_turnover_impact",
        }
        leader_rows = []
        for r in standings:
            row = {"Team": r.team_name}
            for label, attr in metric_cols.items():
                row[label] = f"{getattr(r, attr, 0):.1f}"
            leader_rows.append(row)
        st.dataframe(pd.DataFrame(leader_rows), hide_index=True, use_container_width=True)

        # --- Playoff Bracket ---
        if season.playoff_bracket:
            st.subheader("Playoff Bracket")
            quarterfinals = [g for g in season.playoff_bracket if g.week == 998]
            semifinals    = [g for g in season.playoff_bracket if g.week == 999]
            championship  = [g for g in season.playoff_bracket if g.week == 1000]

            def bracket_row(game):
                winner = game.home_team if game.home_score > game.away_score else game.away_team
                loser  = game.away_team if winner == game.home_team else game.home_team
                ws = max(game.home_score, game.away_score)
                ls = min(game.home_score, game.away_score)
                return f"**{winner}** {ws:.1f}  def.  {loser} {ls:.1f}"

            if quarterfinals:
                st.markdown("**Quarterfinals**")
                for g in quarterfinals:
                    st.markdown(f"- {bracket_row(g)}")
            if semifinals:
                st.markdown("**Semifinals**")
                for g in semifinals:
                    st.markdown(f"- {bracket_row(g)}")
            if championship:
                st.markdown("**🏆 Championship**")
                st.markdown(f"### {bracket_row(championship[0])}")

        # --- Score chart per week ---
        st.subheader("Week-by-Week Results")
        week_rows = []
        for g in sorted(season.schedule, key=lambda x: x.week):
            if g.completed:
                winner = g.home_team if g.home_score > g.away_score else g.away_team
                week_rows.append({
                    "Week": g.week,
                    "Home": g.home_team,
                    "Away": g.away_team,
                    "Home Score": g.home_score,
                    "Away Score": g.away_score,
                    "Winner": winner,
                })
        if week_rows:
            st.dataframe(pd.DataFrame(week_rows), hide_index=True, use_container_width=True)
```

---

### NEW PAGE 2 — Dynasty Mode

Multi-season dynasty mode page. Uses `st.session_state["dynasty"]` to persist across
Streamlit reruns.

```python
elif page == "Dynasty Mode":
    st.title("Dynasty Mode")

    from engine.dynasty import create_dynasty, Dynasty
    from engine.season import create_season
    import os

    SAVE_PATH = "dynasty_save.json"  # already in .gitignore

    # --- Sidebar controls ---
    with st.sidebar:
        st.subheader("Dynasty Controls")
        if st.button("New Dynasty"):
            st.session_state.pop("dynasty", None)
            st.session_state.pop("dynasty_teams", None)
            st.session_state.pop("dynasty_styles", None)
        if os.path.exists(SAVE_PATH) and st.button("Load Saved Dynasty"):
            st.session_state["dynasty"] = Dynasty.load(SAVE_PATH)

    # --- Setup screen (if no dynasty yet) ---
    if "dynasty" not in st.session_state:
        st.subheader("Start Your Dynasty")

        coach_name = st.text_input("Your Coach Name", value="Coach Smith")
        coach_team_key = st.selectbox("Your Team", [t["key"] for t in teams],
                                      format_func=lambda x: team_names[x])
        start_year = st.number_input("Starting Year", 2020, 2050, 2026)

        selected_keys = st.multiselect(
            "League teams (include your team)",
            [t["key"] for t in teams],
            default=[t["key"] for t in teams][:8],
            format_func=lambda x: team_names[x],
        )

        # Style config
        st.subheader("Initial Team Styles")
        style_configs = {}
        for key in selected_keys:
            with st.expander(f"{team_names[key]} styles"):
                o = st.selectbox("Offense", style_keys,
                                 format_func=lambda x: styles[x]["label"],
                                 key=f"dyn_setup_o_{key}")
                d = st.selectbox("Defense", defense_style_keys,
                                 format_func=lambda x: DEFENSE_STYLES[x]["label"],
                                 key=f"dyn_setup_d_{key}")
                style_configs[team_names[key]] = {"offense_style": o, "defense_style": d}

        if st.button("Start Dynasty", type="primary") and len(selected_keys) >= 4:
            dynasty = create_dynasty(
                dynasty_name=f"{coach_name}'s Dynasty",
                coach_name=coach_name,
                coach_team=team_names[coach_team_key],
                starting_year=int(start_year),
            )
            dynasty.add_conference("Conference", [team_names[k] for k in selected_keys])
            st.session_state["dynasty"]       = dynasty
            st.session_state["dynasty_teams"] = {team_names[k]: load_team(k) for k in selected_keys}
            st.session_state["dynasty_styles"] = style_configs
            st.rerun()

    else:
        # --- Main dynasty view ---
        dynasty      = st.session_state["dynasty"]
        team_objects = st.session_state.get("dynasty_teams", {})
        style_configs = st.session_state.get("dynasty_styles", {})

        # Top summary bar
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Year",  dynasty.current_year)
        c2.metric("Seasons Played", len(dynasty.seasons))
        c3.metric("Career Record", f"{dynasty.coach.career_wins}-{dynasty.coach.career_losses}")
        c4.metric("Championships", dynasty.coach.championships)

        tab_sim, tab_standings, tab_coach, tab_history, tab_records = st.tabs([
            "Simulate Season", "Standings & Awards", "Coach Career",
            "Team Histories", "Record Book"
        ])

        # ── TAB 1: Simulate Season ──────────────────────────────
        with tab_sim:
            st.subheader(f"Simulate {dynasty.current_year} Season")
            playoff_size = st.selectbox("Playoff field", [4, 8], index=1, key="dyn_playoff_size")
            sim_seed = st.number_input("Seed (0=random)", 0, 999999, 0, key="dyn_sim_seed")

            if st.button("Simulate Season", type="primary", key="dyn_run"):
                actual_seed = sim_seed if sim_seed > 0 else random.randint(1, 999999)
                random.seed(actual_seed)

                season = create_season(
                    f"{dynasty.current_year} Season",
                    team_objects,
                    style_configs,
                )
                season.generate_round_robin_schedule()

                prog = st.progress(0)
                total = len(season.schedule)
                for i, game in enumerate(season.schedule):
                    season.simulate_game(game)
                    prog.progress((i + 1) / total)
                prog.empty()

                season.simulate_playoff(num_teams=playoff_size)
                dynasty.advance_season(season)

                # Auto-save
                dynasty.save(SAVE_PATH)

                st.success(f"🏆 {dynasty.current_year - 1} Champion: **{season.champion}**")
                st.session_state["dynasty"] = dynasty
                st.rerun()

        # ── TAB 2: Standings & Awards ────────────────────────────
        with tab_standings:
            if not dynasty.seasons:
                st.info("Simulate at least one season first.")
            else:
                year_options = sorted(dynasty.seasons.keys(), reverse=True)
                sel_year = st.selectbox("Year", year_options, key="dyn_standings_year")
                season = dynasty.seasons[sel_year]
                standings = season.get_standings_sorted()

                if season.champion:
                    st.success(f"🏆 {sel_year} Champion: **{season.champion}**")

                rows = []
                for i, r in enumerate(standings, 1):
                    rows.append({
                        "#": i, "Team": r.team_name,
                        "Offense": r.offense_style.replace("_", " ").title(),
                        "Defense": r.defense_style.replace("_", " ").title(),
                        "W-L": f"{r.wins}-{r.losses}",
                        "Win%": f"{r.win_percentage*100:.1f}%",
                        "PF/G": f"{r.points_for/max(1,r.games_played):.1f}",
                        "PA/G": f"{r.points_against/max(1,r.games_played):.1f}",
                        "Diff": f"{r.point_differential:+.1f}",
                        "OPI": f"{r.avg_opi:.1f}",
                    })
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

                # Awards
                st.subheader(f"{sel_year} Awards")
                if sel_year in dynasty.awards_history:
                    awards = dynasty.awards_history[sel_year]
                    a1, a2, a3 = st.columns(3)
                    a1.metric("🏆 Champion",         awards.champion)
                    a2.metric("🥇 Best Record",       awards.best_record)
                    a3.metric("⚡ Highest Scoring",   awards.highest_scoring)
                    a4, a5, a6 = st.columns(3)
                    a4.metric("🛡️  Best Defense",     awards.best_defense)
                    a5.metric("⭐ Highest OPI",        awards.highest_opi)
                    a6.metric("💥 Chaos Award",        awards.most_chaos)

                # Award history table
                st.subheader("Award History (All Seasons)")
                award_rows = []
                for yr in sorted(dynasty.awards_history.keys()):
                    a = dynasty.awards_history[yr]
                    award_rows.append({
                        "Year": yr,
                        "Champion": a.champion,
                        "Best Record": a.best_record,
                        "Scoring": a.highest_scoring,
                        "Defense": a.best_defense,
                        "OPI": a.highest_opi,
                        "Chaos": a.most_chaos,
                        "Kicking": a.best_kicking,
                    })
                st.dataframe(pd.DataFrame(award_rows), hide_index=True, use_container_width=True)

        # ── TAB 3: Coach Career ──────────────────────────────────
        with tab_coach:
            coach = dynasty.coach
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Career Record", f"{coach.career_wins}-{coach.career_losses}")
            m2.metric("Win %",         f"{coach.win_percentage*100:.1f}%")
            m3.metric("Championships", coach.championships)
            m4.metric("Playoff Apps",  coach.playoff_appearances)

            if coach.season_records:
                coach_rows = []
                for yr in sorted(coach.season_records.keys()):
                    r = coach.season_records[yr]
                    coach_rows.append({
                        "Year": yr,
                        "W-L": f"{r['wins']}-{r['losses']}",
                        "PF": f"{r['points_for']:.1f}",
                        "PA": f"{r['points_against']:.1f}",
                        "Playoff": "✓" if r.get("playoff") else "-",
                        "Champion": "🏆" if r.get("champion") else "-",
                    })
                st.subheader("Season-by-Season")
                st.dataframe(pd.DataFrame(coach_rows), hide_index=True, use_container_width=True)

                # Win trend chart
                win_data = pd.DataFrame([
                    {"Year": yr, "Wins": r["wins"], "Losses": r["losses"]}
                    for yr, r in sorted(coach.season_records.items())
                ])
                fig = px.line(win_data, x="Year", y=["Wins", "Losses"],
                              title="Wins/Losses Per Season", markers=True)
                st.plotly_chart(fig, use_container_width=True)

        # ── TAB 4: Team Histories ────────────────────────────────
        with tab_history:
            team_sel = st.selectbox(
                "Select Team",
                list(dynasty.team_histories.keys()),
                key="dyn_team_hist"
            )
            h = dynasty.team_histories[team_sel]

            hm1, hm2, hm3, hm4 = st.columns(4)
            hm1.metric("All-Time Record", f"{h.total_wins}-{h.total_losses}")
            hm2.metric("Win %",           f"{h.win_percentage*100:.1f}%")
            hm3.metric("Championships",   h.total_championships)
            hm4.metric("Playoff Apps",    h.total_playoff_appearances)

            if h.championship_years:
                st.success(f"Championship years: {', '.join(map(str, h.championship_years))}")

            if h.best_season_year:
                st.info(f"Best season: {h.best_season_wins} wins in {h.best_season_year}")

            if h.season_records:
                hist_rows = []
                for yr in sorted(h.season_records.keys()):
                    r = h.season_records[yr]
                    hist_rows.append({
                        "Year": yr,
                        "W-L": f"{r['wins']}-{r['losses']}",
                        "PF": f"{r['points_for']:.1f}",
                        "PA": f"{r['points_against']:.1f}",
                        "OPI": f"{r.get('avg_opi', 0):.1f}",
                        "Playoff": "✓" if r.get("playoff") else "-",
                        "Champion": "🏆" if r.get("champion") else "-",
                    })
                st.dataframe(pd.DataFrame(hist_rows), hide_index=True, use_container_width=True)

                # Win trend
                trend = pd.DataFrame([
                    {"Year": yr, "Wins": r["wins"]}
                    for yr, r in sorted(h.season_records.items())
                ])
                fig = px.bar(trend, x="Year", y="Wins",
                             title=f"{team_sel} Wins Per Season",
                             color="Wins", color_continuous_scale="blues")
                st.plotly_chart(fig, use_container_width=True)

            # All-time standings across programs
            st.subheader("All-Time Program Standings")
            prog_rows = []
            for tname, th in sorted(dynasty.team_histories.items(),
                                    key=lambda x: x[1].total_championships, reverse=True):
                prog_rows.append({
                    "Team": tname,
                    "W-L": f"{th.total_wins}-{th.total_losses}",
                    "Win%": f"{th.win_percentage*100:.1f}%",
                    "Championships": th.total_championships,
                    "Playoff Apps": th.total_playoff_appearances,
                    "PPG": f"{th.points_per_game:.1f}",
                })
            st.dataframe(pd.DataFrame(prog_rows), hide_index=True, use_container_width=True)

        # ── TAB 5: Record Book ───────────────────────────────────
        with tab_records:
            rb = dynasty.record_book
            st.subheader("Single-Season Records")

            rec_data = []
            if rb.most_wins_season["team"]:
                rec_data.append({"Record": "Most Wins",
                                 "Value": rb.most_wins_season["wins"],
                                 "Team": rb.most_wins_season["team"],
                                 "Year": rb.most_wins_season["year"]})
            if rb.most_points_season["team"]:
                rec_data.append({"Record": "Most Points",
                                 "Value": f"{rb.most_points_season['points']:.1f}",
                                 "Team": rb.most_points_season["team"],
                                 "Year": rb.most_points_season["year"]})
            if rb.best_defense_season["team"]:
                rec_data.append({"Record": "Best Defense (PPG allowed)",
                                 "Value": f"{rb.best_defense_season['ppg_allowed']:.1f}",
                                 "Team": rb.best_defense_season["team"],
                                 "Year": rb.best_defense_season["year"]})
            if rb.highest_opi_season["team"]:
                rec_data.append({"Record": "Highest OPI",
                                 "Value": f"{rb.highest_opi_season['opi']:.1f}",
                                 "Team": rb.highest_opi_season["team"],
                                 "Year": rb.highest_opi_season["year"]})
            if rb.most_chaos_season["team"]:
                rec_data.append({"Record": "Most Chaos",
                                 "Value": f"{rb.most_chaos_season['chaos']:.1f}",
                                 "Team": rb.most_chaos_season["team"],
                                 "Year": rb.most_chaos_season["year"]})
            if rec_data:
                st.dataframe(pd.DataFrame(rec_data), hide_index=True, use_container_width=True)

            st.subheader("All-Time Records")
            alltime_data = []
            if rb.most_championships["team"]:
                alltime_data.append({"Record": "Most Championships",
                                     "Value": rb.most_championships["championships"],
                                     "Team/Coach": rb.most_championships["team"]})
            if rb.highest_win_percentage["team"]:
                alltime_data.append({"Record": f"Highest Win% (min 20 games)",
                                     "Value": f"{rb.highest_win_percentage['win_pct']*100:.1f}%",
                                     "Team/Coach": rb.highest_win_percentage["team"]})
            if rb.most_coaching_wins["coach"]:
                alltime_data.append({"Record": "Most Coaching Wins",
                                     "Value": rb.most_coaching_wins["wins"],
                                     "Team/Coach": rb.most_coaching_wins["coach"]})
            if rb.most_coaching_championships["coach"]:
                alltime_data.append({"Record": "Most Coaching Championships",
                                     "Value": rb.most_coaching_championships["championships"],
                                     "Team/Coach": rb.most_coaching_championships["coach"]})
            if alltime_data:
                st.dataframe(pd.DataFrame(alltime_data), hide_index=True, use_container_width=True)
```

---

## KEY NOTES FOR IMPLEMENTATION

1. **All new imports go at the top of `ui/app.py`** — add alongside the existing import line.

2. **`defense_style_keys = list(DEFENSE_STYLES.keys())`** — define this once at module level,
   same as `style_keys`.

3. **Session state** — `"dynasty"` persists across Streamlit reruns within a browser session.
   The dynasty is also auto-saved to `dynasty_save.json` after each simulated season.
   `dynasty_save.json` is already in `.gitignore`.

4. **Progress bar** — the `season.simulate_game(game)` loop in Dynasty Mode runs games one
   at a time with a progress bar. The existing `season.simulate_season()` method runs all at
   once; for the progress bar, call `season.simulate_game(game)` in a loop instead.

5. **`team_objects` and `style_configs`** — these need to be stored in `st.session_state`
   when the dynasty is created so they survive Streamlit reruns.

6. **The `drive_result_label` / `drive_result_color` helpers** — the additions are purely
   additive, just extend the existing dicts.

7. **The radar chart** requires `plotly.graph_objects as go` — already imported in `app.py`.

8. **No changes needed to any engine files** — all backend is complete and tested.
   Only `ui/app.py` needs to be modified.
