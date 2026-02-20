"""Game Simulator page — NiceGUI version.

Migrated from ui/page_modules/game_simulator.py. Provides team selection,
single-game simulation, and full result display with box scores, drives,
play-by-play, analytics, and export.
"""

from __future__ import annotations

import random
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from nicegui import ui

from engine import ViperballEngine, OFFENSE_STYLES
from engine.game_engine import WEATHER_CONDITIONS
from engine.viperball_metrics import calculate_viperball_metrics
from nicegui_app.state import UserState
from nicegui_app.helpers import (
    load_team, format_time, fmt_vb_score,
    generate_box_score_markdown, generate_play_log_csv,
    generate_drives_csv, safe_filename, drive_result_label,
    drive_result_color, compute_quarter_scores,
)
from nicegui_app.components import metric_card, stat_table, download_button


def render_game_simulator(state: UserState, shared: dict):
    """Render the standalone game simulator UI."""
    teams = shared["teams"]
    styles = shared["styles"]
    team_names = shared["team_names"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]
    off_tips = shared["OFFENSE_TOOLTIPS"]
    def_tips = shared["DEFENSE_TOOLTIPS"]

    team_key_list = [t["key"] for t in teams]
    team_options = {t["key"]: t["name"] for t in teams}
    style_options = {k: styles[k]["label"] for k in style_keys}
    def_style_options = {k: defense_styles[k]["label"] for k in defense_style_keys}
    weather_options = {k: v["label"] for k, v in WEATHER_CONDITIONS.items()}

    ui.label("Game Simulator").classes("text-2xl font-bold text-slate-800 mb-4")

    # ── Team Selection ──
    with ui.row().classes("w-full gap-8"):
        # Home team
        with ui.column().classes("flex-1"):
            ui.label("Home Team").classes("font-bold text-slate-700")
            home_select = ui.select(
                team_options, value=team_key_list[0] if team_key_list else None,
                label="Select Home Team",
            ).classes("w-full")

            with ui.row().classes("w-full gap-4"):
                home_off = ui.select(
                    style_options, value=style_keys[0] if style_keys else None,
                    label="Offense",
                ).classes("flex-1")
                home_def = ui.select(
                    def_style_options, value=defense_style_keys[0] if defense_style_keys else None,
                    label="Defense",
                ).classes("flex-1")

            home_tip = ui.label("").classes("text-sm text-gray-500 italic")

            def _update_home_tip():
                key = home_off.value
                tip = off_tips.get(key, styles.get(key, {}).get("description", ""))
                home_tip.set_text(tip)

            home_off.on_value_change(lambda _: _update_home_tip())
            _update_home_tip()

        # Away team
        with ui.column().classes("flex-1"):
            ui.label("Away Team").classes("font-bold text-slate-700")
            away_select = ui.select(
                team_options,
                value=team_key_list[min(1, len(team_key_list) - 1)] if team_key_list else None,
                label="Select Away Team",
            ).classes("w-full")

            with ui.row().classes("w-full gap-4"):
                away_off = ui.select(
                    style_options, value=style_keys[0] if style_keys else None,
                    label="Offense",
                ).classes("flex-1")
                away_def = ui.select(
                    def_style_options, value=defense_style_keys[0] if defense_style_keys else None,
                    label="Defense",
                ).classes("flex-1")

            away_tip = ui.label("").classes("text-sm text-gray-500 italic")

            def _update_away_tip():
                key = away_off.value
                tip = off_tips.get(key, styles.get(key, {}).get("description", ""))
                away_tip.set_text(tip)

            away_off.on_value_change(lambda _: _update_away_tip())
            _update_away_tip()

    # ── Controls Row ──
    with ui.row().classes("w-full gap-4 items-end mt-2"):
        weather_select = ui.select(weather_options, value="clear", label="Weather").classes("w-48")
        seed_input = ui.number("Seed (0 = random)", value=0, min=0, max=999999).classes("w-48")
        sim_button = ui.button("Simulate Game", icon="play_arrow").classes("ml-auto").props("color=primary size=lg")

    ui.separator().classes("my-4")

    # ── Results Container ──
    results_container = ui.column().classes("w-full")

    @ui.refreshable
    def _render_results():
        if state.last_result is None:
            ui.label("Run a simulation to see results.").classes("text-gray-400 italic")
            return

        result = state.last_result
        actual_seed = state.last_seed
        home_name = result["final_score"]["home"]["team"]
        away_name = result["final_score"]["away"]["team"]
        home_score = result["final_score"]["home"]["score"]
        away_score = result["final_score"]["away"]["score"]
        hs = result["stats"]["home"]
        as_ = result["stats"]["away"]
        plays = result["play_by_play"]

        # Score header
        with ui.row().classes("w-full justify-center items-center gap-8 my-4"):
            with ui.column().classes("items-center"):
                ui.label(home_name).classes("text-base font-semibold").style("color: #475569;")
                ui.label(fmt_vb_score(home_score)).classes("text-5xl font-extrabold").style("color: #0f172a;")
            ui.label("vs").classes("text-xl opacity-40 pt-4")
            with ui.column().classes("items-center"):
                ui.label(away_name).classes("text-base font-semibold").style("color: #475569;")
                ui.label(fmt_vb_score(away_score)).classes("text-5xl font-extrabold").style("color: #0f172a;")

        ui.label(f"Seed: {actual_seed}").classes("text-sm text-gray-400 text-center w-full")

        # Winner banner
        margin = abs(home_score - away_score)
        if home_score > away_score:
            ui.notify(f"{home_name} wins by {fmt_vb_score(margin)}", type="positive")
        elif away_score > home_score:
            ui.notify(f"{away_name} wins by {fmt_vb_score(margin)}", type="positive")
        else:
            ui.notify("Game ended in a tie", type="info")

        # Weather notice
        game_weather = result.get("weather", "clear")
        if game_weather != "clear":
            weather_label = result.get("weather_label", game_weather.title())
            weather_desc = result.get("weather_description", "")
            with ui.card().classes("w-full bg-blue-50 p-3 rounded"):
                ui.label(f"{weather_label} — {weather_desc}").classes("text-sm")

        # Summary metrics
        with ui.row().classes("w-full gap-3 flex-wrap"):
            metric_card("Total Plays", hs["total_plays"] + as_["total_plays"])
            metric_card("Total Yards", hs["total_yards"] + as_["total_yards"])
            metric_card("Turnovers", hs["fumbles_lost"] + as_["fumbles_lost"] + hs["turnovers_on_downs"] + as_["turnovers_on_downs"])
            metric_card("Snap Kicks", hs.get("drop_kicks_made", 0) + as_.get("drop_kicks_made", 0))
            metric_card("Touchdowns", hs.get("touchdowns", 0) + as_.get("touchdowns", 0))

        # Tabbed results
        with ui.tabs().classes("w-full") as result_tabs:
            box_tab = ui.tab("Box Score")
            drives_tab = ui.tab("Drives")
            plays_tab = ui.tab("Play-by-Play")
            analytics_tab = ui.tab("Analytics")
            export_tab = ui.tab("Export")

        with ui.tab_panels(result_tabs, value=box_tab).classes("w-full"):
            with ui.tab_panel(box_tab):
                _render_box_score(result, plays, home_name, away_name, home_score, away_score, hs, as_)
            with ui.tab_panel(drives_tab):
                _render_drives(result, home_name, away_name)
            with ui.tab_panel(plays_tab):
                _render_play_by_play(plays, home_name, away_name)
            with ui.tab_panel(analytics_tab):
                _render_analytics(result, plays, home_name, away_name, hs, as_)
            with ui.tab_panel(export_tab):
                _render_export(result, home_name, away_name, actual_seed)

    def _simulate():
        home_key = home_select.value
        away_key = away_select.value
        if not home_key or not away_key:
            ui.notify("Select both teams", type="warning")
            return

        seed_val = int(seed_input.value or 0)
        actual_seed = seed_val if seed_val > 0 else random.randint(1, 999999)
        home_team = load_team(home_key)
        away_team = load_team(away_key)

        style_overrides = {
            home_team.name: home_off.value,
            away_team.name: away_off.value,
            f"{home_team.name}_defense": home_def.value,
            f"{away_team.name}_defense": away_def.value,
        }

        engine = ViperballEngine(
            home_team, away_team,
            seed=actual_seed,
            style_overrides=style_overrides,
            weather=weather_select.value,
        )
        result = engine.simulate_game()
        state.last_result = result
        state.last_seed = actual_seed
        _render_results.refresh()

    sim_button.on_click(_simulate)

    with results_container:
        _render_results()


# ── Sub-renderers ──

def _render_box_score(result, plays, home_name, away_name, home_score, away_score, hs, as_):
    home_q, away_q = compute_quarter_scores(plays)

    # Quarter scoring table
    qtr_rows = [
        {"Team": home_name, "Q1": fmt_vb_score(home_q[1]), "Q2": fmt_vb_score(home_q[2]),
         "Q3": fmt_vb_score(home_q[3]), "Q4": fmt_vb_score(home_q[4]),
         "Final": fmt_vb_score(home_score)},
        {"Team": away_name, "Q1": fmt_vb_score(away_q[1]), "Q2": fmt_vb_score(away_q[2]),
         "Q3": fmt_vb_score(away_q[3]), "Q4": fmt_vb_score(away_q[4]),
         "Final": fmt_vb_score(away_score)},
    ]
    stat_table(qtr_rows)

    # Scoring breakdown
    ui.label("Scoring").classes("font-bold text-slate-700 mt-4")
    h_frp = hs.get("fumble_recovery_points", 0)
    a_frp = as_.get("fumble_recovery_points", 0)
    h_fr = hs.get("fumble_recoveries", 0)
    a_fr = as_.get("fumble_recoveries", 0)
    h_saf = hs.get("safeties_conceded", 0)
    a_saf = as_.get("safeties_conceded", 0)

    scoring_rows = [
        {"Stat": "TDs (9pts)", home_name: f"{hs['touchdowns']} ({hs['touchdowns']*9}pts)", away_name: f"{as_['touchdowns']} ({as_['touchdowns']*9}pts)"},
        {"Stat": "Snap Kicks (5pts)", home_name: f"{hs['drop_kicks_made']}/{hs.get('drop_kicks_attempted',0)}", away_name: f"{as_['drop_kicks_made']}/{as_.get('drop_kicks_attempted',0)}"},
        {"Stat": "FGs (3pts)", home_name: f"{hs['place_kicks_made']}/{hs.get('place_kicks_attempted',0)}", away_name: f"{as_['place_kicks_made']}/{as_.get('place_kicks_attempted',0)}"},
        {"Stat": "Safeties (2pts)", home_name: str(a_saf), away_name: str(h_saf)},
        {"Stat": "Pindowns (1pt)", home_name: str(hs.get("pindowns", 0)), away_name: str(as_.get("pindowns", 0))},
        {"Stat": "Strikes (\u00bdpt)", home_name: f"{h_fr} ({h_frp:g}pts)", away_name: f"{a_fr} ({a_frp:g}pts)"},
    ]
    stat_table(scoring_rows)

    # Offensive stats
    ui.label("Offensive Stats").classes("font-bold text-slate-700 mt-4")
    off_rows = [
        {"Stat": "Total Yards", home_name: str(hs["total_yards"]), away_name: str(as_["total_yards"])},
        {"Stat": "Rush Yds", home_name: str(hs.get("rushing_yards", 0)), away_name: str(as_.get("rushing_yards", 0))},
        {"Stat": "Lateral Yds", home_name: str(hs.get("lateral_yards", 0)), away_name: str(as_.get("lateral_yards", 0))},
        {"Stat": "KP Yds", home_name: str(hs.get("kick_pass_yards", 0)), away_name: str(as_.get("kick_pass_yards", 0))},
        {"Stat": "Yds/Play", home_name: str(hs["yards_per_play"]), away_name: str(as_["yards_per_play"])},
        {"Stat": "Total Plays", home_name: str(hs["total_plays"]), away_name: str(as_["total_plays"])},
        {"Stat": "Lat Chains", home_name: str(hs["lateral_chains"]), away_name: str(as_["lateral_chains"])},
        {"Stat": "Lat Eff", home_name: f"{hs['lateral_efficiency']}%", away_name: f"{as_['lateral_efficiency']}%"},
        {"Stat": "Fumbles Lost", home_name: str(hs["fumbles_lost"]), away_name: str(as_["fumbles_lost"])},
        {"Stat": "Penalties", home_name: f"{hs.get('penalties',0)} for {hs.get('penalty_yards',0)} yds", away_name: f"{as_.get('penalties',0)} for {as_.get('penalty_yards',0)} yds"},
    ]
    stat_table(off_rows)

    # Player stats
    player_stats = result.get("player_stats", {})
    if player_stats.get("home") or player_stats.get("away"):
        with ui.expansion("Player Performance", icon="person").classes("w-full mt-4"):
            for side, tname in [("home", home_name), ("away", away_name)]:
                pstats = player_stats.get(side, [])
                if not pstats:
                    continue
                ui.label(tname).classes("font-bold text-slate-700 mt-2")

                rushers = [p for p in pstats if p.get("touches", 0) > 0]
                if rushers:
                    ui.label("Rushing & Laterals").classes("text-sm text-gray-500 mt-1")
                    rush_rows = [
                        {
                            "Player": f"{p['tag']} {p['name']}",
                            "TCH": p["touches"], "YDS": p["yards"],
                            "RUSH": p.get("rushing_yards", 0),
                            "LAT": p.get("lateral_yards", 0),
                            "TD": p["tds"], "FUM": p["fumbles"],
                        }
                        for p in rushers
                    ]
                    stat_table(rush_rows)

                kickers = [p for p in pstats if p.get("kick_att", 0) > 0]
                if kickers:
                    ui.label("Kicking").classes("text-sm text-gray-500 mt-1")
                    kick_rows = [
                        {
                            "Player": f"{p['tag']} {p['name']}",
                            "ATT": p["kick_att"], "MADE": p["kick_made"],
                            "PCT": f"{(p['kick_made']/p['kick_att']*100):.0f}%" if p["kick_att"] > 0 else "-",
                        }
                        for p in kickers
                    ]
                    stat_table(kick_rows)

                kp_players = [p for p in pstats if (p.get("kick_passes_thrown", 0) + p.get("kick_pass_receptions", 0)) > 0]
                if kp_players:
                    ui.label("Kick Passing").classes("text-sm text-gray-500 mt-1")
                    kp_rows = [
                        {
                            "Player": f"{p['tag']} {p['name']}",
                            "KP Att": p.get("kick_passes_thrown", 0),
                            "KP Comp": p.get("kick_passes_completed", 0),
                            "KP Yds": p.get("kick_pass_yards", 0),
                            "KP TD": p.get("kick_pass_tds", 0),
                            "KP INT": p.get("kick_pass_interceptions_thrown", 0),
                        }
                        for p in kp_players
                    ]
                    stat_table(kp_rows)

                ui.separator().classes("my-2")


def _render_drives(result, home_name, away_name):
    drives = result.get("drive_summary", [])
    if not drives:
        ui.label("No drive data available.").classes("text-gray-400 italic")
        return

    home_drives = [d for d in drives if d["team"] == "home"]
    away_drives = [d for d in drives if d["team"] == "away"]

    with ui.row().classes("w-full gap-3 flex-wrap"):
        metric_card(f"{home_name} Drives", len(home_drives))
        metric_card(f"{away_name} Drives", len(away_drives))
        home_avg = sum(d["plays"] for d in home_drives) / max(1, len(home_drives))
        away_avg = sum(d["plays"] for d in away_drives) / max(1, len(away_drives))
        metric_card(f"{home_name} Avg Plays/Dr", f"{home_avg:.1f}")
        metric_card(f"{away_name} Avg Plays/Dr", f"{away_avg:.1f}")

    drive_rows = []
    for i, d in enumerate(drives):
        team_label = home_name if d["team"] == "home" else away_name
        result_lbl = drive_result_label(d["result"])
        if d.get("sacrifice_drive"):
            result_lbl += " *"
        drive_rows.append({
            "#": i + 1, "Team": team_label, "Qtr": f"Q{d['quarter']}",
            "Start": f"{d['start_yard_line']}yd", "Plays": d["plays"],
            "Yards": d["yards"], "Result": result_lbl,
        })
    stat_table(drive_rows)

    # Drive outcomes chart
    drive_outcomes = {}
    for d in drives:
        r = drive_result_label(d["result"])
        drive_outcomes[r] = drive_outcomes.get(r, 0) + 1

    fig = px.bar(
        x=list(drive_outcomes.keys()), y=list(drive_outcomes.values()),
        title="Drive Outcomes",
        color=list(drive_outcomes.keys()),
        color_discrete_map={
            "TD": "#16a34a", "SK/FG": "#2563eb", "STRIKE (+\u00bd)": "#dc2626",
            "DOWNS": "#d97706", "PUNT": "#94a3b8",
        },
    )
    fig.update_layout(showlegend=False, height=300, xaxis_title="Outcome",
                      yaxis_title="Count", template="plotly_white")
    ui.plotly(fig).classes("w-full")


def _render_play_by_play(plays, home_name, away_name):
    quarter_filter = ui.select(
        {"All": "All", "1": "Q1", "2": "Q2", "3": "Q3", "4": "Q4"},
        value="All", label="Filter by Quarter",
    ).classes("w-48")

    play_container = ui.column().classes("w-full")

    @ui.refreshable
    def _show_plays():
        filtered = plays
        if quarter_filter.value != "All":
            q = int(quarter_filter.value)
            filtered = [p for p in plays if p.get("quarter") == q]

        if not filtered:
            ui.label("No plays to display.").classes("text-gray-400 italic")
            return

        play_rows = []
        for p in filtered:
            team_label = home_name if p["possession"] == "home" else away_name
            play_rows.append({
                "#": p["play_number"],
                "Team": team_label,
                "Qtr": f"Q{p['quarter']}",
                "Time": format_time(p["time_remaining"]),
                "Down": f"{p['down']}&{p.get('yards_to_go', '')}",
                "FP": f"{p['field_position']}yd",
                "Family": p.get("play_family", ""),
                "Desc": p["description"][:60],
                "Yds": p["yards"],
                "Result": p["result"],
            })
        stat_table(play_rows)

    quarter_filter.on_value_change(lambda _: _show_plays.refresh())

    with play_container:
        _show_plays()


def _render_analytics(result, plays, home_name, away_name, hs, as_):
    ui.label("VPA - Viperball Points Added").classes("font-bold text-slate-700")
    ui.label("Play efficiency vs league-average expectation.").classes("text-sm text-gray-500")

    h_vpa = hs.get("epa", {})
    a_vpa = as_.get("epa", {})

    with ui.row().classes("w-full gap-3 flex-wrap"):
        metric_card(f"{home_name} Total VPA", h_vpa.get("total_vpa", h_vpa.get("total_epa", 0)))
        metric_card(f"{away_name} Total VPA", a_vpa.get("total_vpa", a_vpa.get("total_epa", 0)))
        metric_card(f"{home_name} VPA/Play", h_vpa.get("vpa_per_play", h_vpa.get("epa_per_play", 0)))
        metric_card(f"{away_name} VPA/Play", a_vpa.get("vpa_per_play", a_vpa.get("epa_per_play", 0)))
        metric_card(f"{home_name} Success %", f"{h_vpa.get('success_rate', 0)}%")
        metric_card(f"{away_name} Success %", f"{a_vpa.get('success_rate', 0)}%")

    # Cumulative VPA chart
    vpa_plays = [p for p in plays if "epa" in p]
    if vpa_plays:
        home_vpa_plays = [p for p in vpa_plays if p["possession"] == "home"]
        away_vpa_plays = [p for p in vpa_plays if p["possession"] == "away"]

        fig = go.Figure()
        if home_vpa_plays:
            cum = []
            running = 0
            for p in home_vpa_plays:
                running += p["epa"]
                cum.append(round(running, 2))
            fig.add_trace(go.Scatter(y=cum, mode="lines", name=home_name,
                                     line=dict(color="#2563eb", width=2)))
        if away_vpa_plays:
            cum = []
            running = 0
            for p in away_vpa_plays:
                running += p["epa"]
                cum.append(round(running, 2))
            fig.add_trace(go.Scatter(y=cum, mode="lines", name=away_name,
                                     line=dict(color="#dc2626", width=2)))
        fig.update_layout(title="Cumulative VPA Over Game", xaxis_title="Play #",
                          yaxis_title="Cumulative VPA", height=350, template="plotly_white")
        ui.plotly(fig).classes("w-full")

    # Play family distribution
    ui.label("Play Family Distribution").classes("font-bold text-slate-700 mt-4")
    home_fam = hs.get("play_family_breakdown", {})
    away_fam = as_.get("play_family_breakdown", {})
    all_families = sorted(set(list(home_fam.keys()) + list(away_fam.keys())))
    home_total = sum(home_fam.values()) or 1
    away_total = sum(away_fam.values()) or 1

    chart_data = []
    for f in all_families:
        chart_data.append({"Family": f.replace("_", " ").title(), "Team": home_name,
                           "Pct": round(home_fam.get(f, 0) / home_total * 100, 1)})
        chart_data.append({"Family": f.replace("_", " ").title(), "Team": away_name,
                           "Pct": round(away_fam.get(f, 0) / away_total * 100, 1)})

    if chart_data:
        fig = px.bar(pd.DataFrame(chart_data), x="Family", y="Pct", color="Team",
                     barmode="group", title="Play Call Distribution (%)")
        fig.update_layout(yaxis_ticksuffix="%", height=350, template="plotly_white")
        ui.plotly(fig).classes("w-full")


def _render_export(result, home_name, away_name, actual_seed):
    ui.label("Download game data").classes("text-sm text-gray-500 mb-2")
    home_safe = safe_filename(home_name)
    away_safe = safe_filename(away_name)
    tag = f"{home_safe}_vs_{away_safe}_s{actual_seed}"

    with ui.row().classes("w-full gap-4 flex-wrap"):
        md_content = generate_box_score_markdown(result)
        download_button("Box Score (.md)", md_content, f"{tag}_box_score.md", "text/markdown")

        csv_plays = generate_play_log_csv(result)
        download_button("Play Log (.csv)", csv_plays, f"{tag}_plays.csv")

        csv_drives = generate_drives_csv(result)
        download_button("Drives (.csv)", csv_drives, f"{tag}_drives.csv")

        json_str = json.dumps(result, indent=2, default=str)
        download_button("Full JSON", json_str, f"{tag}_full.json", "application/json")
