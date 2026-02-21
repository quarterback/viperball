"""Debug Tools - Batch Simulation page for the NiceGUI Viperball app.

Runs N simulations of a selected matchup and displays aggregate stats,
score distributions, drive outcomes, fatigue curves, and turnover rates.
Migrated from ui/page_modules/debug_tools.py.
"""

from __future__ import annotations

import json

from nicegui import ui

import plotly.express as px
import plotly.graph_objects as go

from engine import ViperballEngine
from engine.game_engine import WEATHER_CONDITIONS
from nicegui_app.helpers import (
    load_team,
    fmt_vb_score,
    safe_filename,
    generate_batch_summary_csv,
    drive_result_label,
)
from nicegui_app.components import metric_card, download_button


def render_debug_tools(state, shared):
    teams = shared["teams"]
    styles = shared["styles"]
    team_names = shared["team_names"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]

    ui.label("Debug Tools - Batch Simulation").classes("text-3xl font-bold")

    # -- Team selectors -------------------------------------------------------
    team_keys = [t["key"] for t in teams]
    team_options = {t["key"]: team_names[t["key"]] for t in teams}
    style_options = {k: styles[k]["label"] for k in style_keys}

    home_key = {"value": team_keys[0] if team_keys else ""}
    away_key = {"value": team_keys[min(1, len(team_keys) - 1)] if team_keys else ""}
    home_style = {"value": style_keys[0] if style_keys else ""}
    away_style = {"value": style_keys[0] if style_keys else ""}

    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-1"):
            ui.select(
                team_options, label="Home Team", value=home_key["value"],
                on_change=lambda e: home_key.update(value=e.value),
            ).classes("w-full")
            ui.select(
                style_options, label="Home Style", value=home_style["value"],
                on_change=lambda e: home_style.update(value=e.value),
            ).classes("w-full")
        with ui.column().classes("flex-1"):
            ui.select(
                team_options, label="Away Team", value=away_key["value"],
                on_change=lambda e: away_key.update(value=e.value),
            ).classes("w-full")
            ui.select(
                style_options, label="Away Style", value=away_style["value"],
                on_change=lambda e: away_style.update(value=e.value),
            ).classes("w-full")

    # -- Sim controls ---------------------------------------------------------
    weather_options = {k: v["label"] for k, v in WEATHER_CONDITIONS.items()}
    sim_params = {"num_sims": 50, "base_seed": 42, "weather": list(WEATHER_CONDITIONS.keys())[0]}

    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-1"):
            ui.slider(
                min=5, max=200, value=50,
                on_change=lambda e: sim_params.update(num_sims=int(e.value)),
            ).props("label-always").classes("w-full")
            ui.label("Number of Simulations").classes("text-xs text-gray-500")
        with ui.column().classes("flex-1"):
            ui.number(
                "Base Seed (0 = random)", min=0, max=999999, value=42,
                on_change=lambda e: sim_params.update(base_seed=int(e.value) if e.value is not None else 0),
            ).classes("w-full")
        with ui.column().classes("flex-1"):
            ui.select(
                weather_options, label="Weather",
                value=sim_params["weather"],
                on_change=lambda e: sim_params.update(weather=e.value),
            ).classes("w-full")

    # -- Results container (populated after simulation) -----------------------
    results_container = ui.column().classes("w-full")

    async def run_batch():
        num_sims = sim_params["num_sims"]
        base_seed = sim_params["base_seed"]
        weather = sim_params["weather"]

        home_team_data = load_team(home_key["value"])
        away_team_data = load_team(away_key["value"])
        style_overrides = {
            home_team_data.name: home_style["value"],
            away_team_data.name: away_style["value"],
        }

        results_container.clear()
        with results_container:
            progress = ui.linear_progress(value=0).classes("w-full")

        results = []
        for i in range(num_sims):
            s = (base_seed + i) if base_seed > 0 else None
            home_t = load_team(home_key["value"])
            away_t = load_team(away_key["value"])
            engine = ViperballEngine(
                home_t, away_t, seed=s,
                style_overrides=style_overrides, weather=weather,
            )
            r = engine.simulate_game()
            results.append(r)
            progress.set_value((i + 1) / num_sims)

        state.batch_results = results
        _render_results(results_container, results)

    ui.button("Run Batch Simulation", on_click=run_batch, icon="play_arrow").props(
        "color=primary"
    ).classes("w-full mt-2")

    # -- Show existing results if cached --------------------------------------
    if state.batch_results:
        _render_results(results_container, state.batch_results)


def _render_results(container, results):
    """Populate the results container with aggregate stats and charts."""
    container.clear()
    n = len(results)

    home_name = results[0]["final_score"]["home"]["team"]
    away_name = results[0]["final_score"]["away"]["team"]

    home_scores = [r["final_score"]["home"]["score"] for r in results]
    away_scores = [r["final_score"]["away"]["score"] for r in results]
    home_wins = sum(1 for h, a in zip(home_scores, away_scores) if h > a)
    away_wins = sum(1 for h, a in zip(home_scores, away_scores) if a > h)
    ties = n - home_wins - away_wins

    with container:
        ui.separator()
        ui.label(f"Results: {n} Simulations").classes("text-xl font-semibold mt-2")

        home_safe = safe_filename(home_name)
        away_safe = safe_filename(away_name)
        batch_tag = f"batch_{home_safe}_vs_{away_safe}_{n}sims"

        # -- Export buttons ---------------------------------------------------
        with ui.row().classes("w-full gap-4"):
            with ui.column().classes("flex-1"):
                batch_csv = generate_batch_summary_csv(results)
                download_button(
                    "Batch Summary (.csv)",
                    batch_csv,
                    f"{batch_tag}_summary.csv",
                    mime="text/csv",
                )
            with ui.column().classes("flex-1"):
                all_batch_json = json.dumps([{
                    "game": i + 1,
                    "final_score": r["final_score"],
                    "stats": r["stats"],
                    "drive_summary": r.get("drive_summary", []),
                } for i, r in enumerate(results)], indent=2, default=str)
                download_button(
                    "All Games (.json)",
                    all_batch_json,
                    f"{batch_tag}_all.json",
                    mime="application/json",
                )
            with ui.column().classes("flex-1"):
                full_batch_json = json.dumps(results, indent=2, default=str)
                download_button(
                    "Full Data + Plays (.json)",
                    full_batch_json,
                    f"{batch_tag}_full.json",
                    mime="application/json",
                )

        # -- Win/Loss metrics -------------------------------------------------
        with ui.row().classes("w-full gap-4 flex-wrap"):
            metric_card(f"{home_name} Wins", home_wins)
            metric_card(f"{away_name} Wins", away_wins)
            metric_card("Ties", ties)
            metric_card("Tie %", f"{round(ties / n * 100, 1)}%")

        # -- Score Averages ---------------------------------------------------
        ui.label("Score Averages").classes("text-xl font-semibold mt-4")

        home_yards = [r["stats"]["home"]["total_yards"] for r in results]
        away_yards = [r["stats"]["away"]["total_yards"] for r in results]

        with ui.row().classes("w-full gap-4 flex-wrap"):
            metric_card(f"Avg {home_name}", round(sum(home_scores) / n, 1))
            metric_card(f"Avg {away_name}", round(sum(away_scores) / n, 1))
            metric_card(f"Avg {home_name} Yards", round(sum(home_yards) / n, 1))
            metric_card(f"Avg {away_name} Yards", round(sum(away_yards) / n, 1))

        # -- Scoring Breakdown ------------------------------------------------
        ui.label("Scoring Breakdown").classes("text-xl font-semibold mt-4")

        home_tds = [r["stats"]["home"]["touchdowns"] for r in results]
        away_tds = [r["stats"]["away"]["touchdowns"] for r in results]
        home_fumbles = [r["stats"]["home"]["fumbles_lost"] for r in results]
        away_fumbles = [r["stats"]["away"]["fumbles_lost"] for r in results]

        longest_plays = []
        for r in results:
            max_play = max(
                (p["yards"] for p in r["play_by_play"] if p["play_type"] not in ["punt"]),
                default=0,
            )
            longest_plays.append(max_play)

        with ui.row().classes("w-full gap-4 flex-wrap"):
            metric_card("Avg TDs/team", round((sum(home_tds) + sum(away_tds)) / (2 * n), 2))
            metric_card("Avg Fumbles/team", round((sum(home_fumbles) + sum(away_fumbles)) / (2 * n), 2))
            metric_card("Avg Longest Play", round(sum(longest_plays) / n, 1))
            metric_card("Max Longest Play", max(longest_plays))

        # -- Kicking / Special Teams ------------------------------------------
        home_kick_pct = [r["stats"]["home"].get("kick_percentage", 0) for r in results]
        away_kick_pct = [r["stats"]["away"].get("kick_percentage", 0) for r in results]
        avg_kick_pct = round((sum(home_kick_pct) + sum(away_kick_pct)) / (2 * n), 1)

        home_pindowns = [r["stats"]["home"].get("pindowns", 0) for r in results]
        away_pindowns = [r["stats"]["away"].get("pindowns", 0) for r in results]

        home_lat_eff = [r["stats"]["home"].get("lateral_efficiency", 0) for r in results]
        away_lat_eff = [r["stats"]["away"].get("lateral_efficiency", 0) for r in results]
        avg_lat_eff = round((sum(home_lat_eff) + sum(away_lat_eff)) / (2 * n), 1)

        home_dk = [r["stats"]["home"].get("drop_kicks_made", 0) for r in results]
        away_dk = [r["stats"]["away"].get("drop_kicks_made", 0) for r in results]

        with ui.row().classes("w-full gap-4 flex-wrap"):
            metric_card("Avg Kick %", f"{avg_kick_pct}%")
            metric_card("Avg Pindowns/game", round((sum(home_pindowns) + sum(away_pindowns)) / n, 2))
            metric_card("Avg Lateral Eff", f"{avg_lat_eff}%")
            metric_card("Avg Snap Kicks/team", round((sum(home_dk) + sum(away_dk)) / (2 * n), 2))

        home_pk = [r["stats"]["home"].get("place_kicks_made", 0) for r in results]
        away_pk = [r["stats"]["away"].get("place_kicks_made", 0) for r in results]
        home_bells = [r["stats"]["home"].get("bells", 0) for r in results]
        away_bells = [r["stats"]["away"].get("bells", 0) for r in results]
        home_punts = [r["stats"]["home"].get("punts", 0) for r in results]
        away_punts = [r["stats"]["away"].get("punts", 0) for r in results]
        home_saf = [r["stats"]["home"].get("safeties_conceded", 0) for r in results]
        away_saf = [r["stats"]["away"].get("safeties_conceded", 0) for r in results]

        with ui.row().classes("w-full gap-4 flex-wrap"):
            metric_card("Avg FGs Made/team", round((sum(home_pk) + sum(away_pk)) / (2 * n), 2))
            metric_card("Avg Bells/team", round((sum(home_bells) + sum(away_bells)) / (2 * n), 2))
            metric_card("Avg Punts/team", round((sum(home_punts) + sum(away_punts)) / (2 * n), 2))
            metric_card("Avg Safeties/team", round((sum(home_saf) + sum(away_saf)) / (2 * n), 2))

        # -- Down Conversions -------------------------------------------------
        ui.label("Avg Down Conversions").classes("text-base font-bold mt-4")
        with ui.row().classes("w-full gap-4 flex-wrap"):
            for d in [4, 5, 6]:
                rates = []
                for r in results:
                    for side in ["home", "away"]:
                        dc = r["stats"][side].get("down_conversions", {})
                        dd = dc.get(d, dc.get(str(d), {"rate": 0}))
                        rates.append(dd["rate"])
                avg_rate = round(sum(rates) / max(1, len(rates)), 1)
                label = f"{'4th' if d == 4 else '5th' if d == 5 else '6th'} Down Conv %"
                metric_card(label, f"{avg_rate}%")

        # -- VPA (Viperball Points Added) -------------------------------------
        ui.label("Avg VPA (Viperball Points Added)").classes("text-base font-bold mt-4")

        home_total_vpa = [
            r["stats"]["home"].get("epa", {}).get(
                "total_vpa", r["stats"]["home"].get("epa", {}).get("total_epa", 0)
            ) for r in results
        ]
        away_total_vpa = [
            r["stats"]["away"].get("epa", {}).get(
                "total_vpa", r["stats"]["away"].get("epa", {}).get("total_epa", 0)
            ) for r in results
        ]
        home_vpa_pp = [
            r["stats"]["home"].get("epa", {}).get(
                "vpa_per_play", r["stats"]["home"].get("epa", {}).get("epa_per_play", 0)
            ) for r in results
        ]
        away_vpa_pp = [
            r["stats"]["away"].get("epa", {}).get(
                "vpa_per_play", r["stats"]["away"].get("epa", {}).get("epa_per_play", 0)
            ) for r in results
        ]

        with ui.row().classes("w-full gap-4 flex-wrap"):
            metric_card(f"Avg {home_name} VPA", round(sum(home_total_vpa) / n, 2))
            metric_card(f"Avg {away_name} VPA", round(sum(away_total_vpa) / n, 2))
            metric_card(f"Avg {home_name} VPA/Play", round(sum(home_vpa_pp) / n, 3))
            metric_card(f"Avg {away_name} VPA/Play", round(sum(away_vpa_pp) / n, 3))

        home_sr = [r["stats"]["home"].get("epa", {}).get("success_rate", 0) for r in results]
        away_sr = [r["stats"]["away"].get("epa", {}).get("success_rate", 0) for r in results]
        home_exp = [r["stats"]["home"].get("epa", {}).get("explosiveness", 0) for r in results]
        away_exp = [r["stats"]["away"].get("epa", {}).get("explosiveness", 0) for r in results]

        with ui.row().classes("w-full gap-4 flex-wrap"):
            metric_card(f"Avg {home_name} Success Rate", f"{round(sum(home_sr) / n, 1)}%")
            metric_card(f"Avg {away_name} Success Rate", f"{round(sum(away_sr) / n, 1)}%")
            metric_card(f"Avg {home_name} Explosiveness", round(sum(home_exp) / n, 3))
            metric_card(f"Avg {away_name} Explosiveness", round(sum(away_exp) / n, 3))

        # -- Score Distribution chart -----------------------------------------
        ui.label("Score Distribution").classes("text-xl font-semibold mt-4")
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=home_scores, name=home_name, opacity=0.7))
        fig.add_trace(go.Histogram(x=away_scores, name=away_name, opacity=0.7))
        fig.update_layout(
            barmode="overlay", xaxis_title="Score",
            yaxis_title="Frequency", height=350,
        )
        ui.plotly(fig).classes("w-full")

        # -- Drive Outcomes chart ---------------------------------------------
        ui.label("Drive Outcomes (aggregate)").classes("text-xl font-semibold mt-4")
        all_drives = []
        for r in results:
            for d in r.get("drive_summary", []):
                all_drives.append(d)
        if all_drives:
            outcome_counts = {}
            for d in all_drives:
                r_label = drive_result_label(d["result"])
                outcome_counts[r_label] = outcome_counts.get(r_label, 0) + 1
            total_drives = len(all_drives)
            fig = px.bar(
                x=list(outcome_counts.keys()),
                y=[round(v / total_drives * 100, 1) for v in outcome_counts.values()],
                title=f"Drive Outcome Distribution ({total_drives} drives across {n} games)",
                labels={"x": "Outcome", "y": "Percentage"},
                color=list(outcome_counts.keys()),
                color_discrete_map={
                    "TD": "#22c55e", "FG": "#3b82f6", "FUMBLE": "#ef4444",
                    "DOWNS": "#f59e0b", "PUNT": "#94a3b8", "MISSED FG": "#f59e0b",
                    "END OF QUARTER": "#64748b", "PINDOWN": "#a855f7",
                    "PUNT RET TD": "#22c55e", "CHAOS REC": "#f97316",
                },
            )
            fig.update_layout(showlegend=False, height=350, yaxis_ticksuffix="%")
            ui.plotly(fig).classes("w-full")

        # -- Fatigue Curves chart ---------------------------------------------
        ui.label("Fatigue Curves").classes("text-xl font-semibold mt-4")
        home_fatigue = []
        away_fatigue = []
        for r in results:
            plays = r["play_by_play"]
            for p in plays:
                if p["possession"] == "home" and p.get("fatigue") is not None:
                    home_fatigue.append({
                        "play": p["play_number"],
                        "fatigue": p["fatigue"],
                        "team": home_name,
                    })
                elif p["possession"] == "away" and p.get("fatigue") is not None:
                    away_fatigue.append({
                        "play": p["play_number"],
                        "fatigue": p["fatigue"],
                        "team": away_name,
                    })

        if home_fatigue or away_fatigue:
            import pandas as pd
            fat_df = pd.DataFrame(home_fatigue + away_fatigue)
            avg_fat = fat_df.groupby(["play", "team"])["fatigue"].mean().reset_index()
            fig = px.line(
                avg_fat, x="play", y="fatigue", color="team",
                title="Average Fatigue Over Play Number",
            )
            fig.update_yaxes(range=[30, 105])
            fig.update_layout(height=350)
            ui.plotly(fig).classes("w-full")

        # -- Turnover Rates table ---------------------------------------------
        ui.label("Turnover Rates").classes("text-xl font-semibold mt-4")
        home_tod = [r["stats"]["home"]["turnovers_on_downs"] for r in results]
        away_tod = [r["stats"]["away"]["turnovers_on_downs"] for r in results]

        to_rows = [
            {
                "Metric": "Avg Fumbles",
                home_name: str(round(sum(home_fumbles) / n, 2)),
                away_name: str(round(sum(away_fumbles) / n, 2)),
            },
            {
                "Metric": "Avg Turnovers on Downs",
                home_name: str(round(sum(home_tod) / n, 2)),
                away_name: str(round(sum(away_tod) / n, 2)),
            },
            {
                "Metric": "Total Turnovers/Game",
                home_name: str(round((sum(home_fumbles) + sum(home_tod)) / n, 2)),
                away_name: str(round((sum(away_fumbles) + sum(away_tod)) / n, 2)),
            },
        ]
        to_columns = [
            {"name": "Metric", "label": "Metric", "field": "Metric", "align": "left"},
            {"name": home_name, "label": home_name, "field": home_name, "align": "right"},
            {"name": away_name, "label": away_name, "field": away_name, "align": "right"},
        ]
        ui.table(columns=to_columns, rows=to_rows).classes("w-full").props("dense flat")

        # -- Player Impact Report -----------------------------------------------
        _render_batch_player_impact(results, n, home_name, away_name)


def _render_batch_player_impact(results, n, home_name, away_name):
    """Aggregate per-player VPA across all batch simulations."""
    from collections import defaultdict

    ui.label("Player Impact Report").classes("text-xl font-semibold mt-6")
    ui.label(
        f"Average per-player VPA across {n} simulations. "
        "Shows which players consistently produce value."
    ).classes("text-sm text-gray-500")

    for side, team_name in [("home", home_name), ("away", away_name)]:
        # Accumulate stats across games keyed by player name
        accum: dict[str, dict] = defaultdict(lambda: {
            "tag": "", "vpa_sum": 0.0, "plays_sum": 0, "touches_sum": 0,
            "yards_sum": 0, "tds_sum": 0, "fumbles_sum": 0, "games": 0,
        })

        for r in results:
            pstats = r.get("player_stats", {}).get(side, [])
            for p in pstats:
                if p.get("plays_involved", 0) == 0:
                    continue
                key = p["name"]
                rec = accum[key]
                rec["tag"] = p["tag"]
                rec["vpa_sum"] += p.get("vpa", 0)
                rec["plays_sum"] += p.get("plays_involved", 0)
                rec["touches_sum"] += p.get("touches", 0)
                rec["yards_sum"] += p.get("yards", 0)
                rec["tds_sum"] += p.get("tds", 0)
                rec["fumbles_sum"] += p.get("fumbles", 0)
                rec["games"] += 1

        if not accum:
            continue

        # Sort by avg VPA descending
        sorted_players = sorted(
            accum.items(),
            key=lambda kv: kv[1]["vpa_sum"] / max(1, kv[1]["games"]),
            reverse=True,
        )

        ui.label(team_name).classes("text-lg font-bold text-slate-700 mt-4")

        # Top performer summary
        if sorted_players:
            top_name, top_rec = sorted_players[0]
            top_avg_vpa = round(top_rec["vpa_sum"] / max(1, top_rec["games"]), 2)
            from nicegui_app.components import metric_card
            with ui.row().classes("w-full gap-3 flex-wrap"):
                metric_card("Avg Team VPA",
                            round(sum(v["vpa_sum"] for v in accum.values()) / n, 1))
                metric_card("Most Impactful", f"{top_rec['tag']} {top_name}")
                metric_card("Best Avg VPA", top_avg_vpa)
                # Find highest VPA/play among regulars (>= 50% of games)
                regulars = [(nm, rc) for nm, rc in sorted_players if rc["games"] >= n * 0.5]
                if regulars:
                    best_eff = max(regulars, key=lambda x: x[1]["vpa_sum"] / max(1, x[1]["plays_sum"]))
                    metric_card("Most Efficient",
                                f"{best_eff[1]['tag']} {best_eff[0]}")

        # Impact table
        impact_rows = []
        for name, rec in sorted_players:
            games = rec["games"]
            avg_vpa = round(rec["vpa_sum"] / max(1, games), 2)
            avg_plays = round(rec["plays_sum"] / max(1, games), 1)
            avg_vpa_pp = round(rec["vpa_sum"] / max(1, rec["plays_sum"]), 3)
            avg_touches = round(rec["touches_sum"] / max(1, games), 1)
            avg_yards = round(rec["yards_sum"] / max(1, games), 1)
            avg_tds = round(rec["tds_sum"] / max(1, games), 2)
            avg_fumbles = round(rec["fumbles_sum"] / max(1, games), 2)

            impact_rows.append({
                "Player": f"{rec['tag']} {name}",
                "GP": games,
                "Avg VPA": avg_vpa,
                "Avg VPA/Play": avg_vpa_pp,
                "Avg Plays": avg_plays,
                "Avg Touches": avg_touches,
                "Avg Yards": avg_yards,
                "Avg TDs": avg_tds,
                "Avg Fumbles": avg_fumbles,
            })
        if impact_rows:
            from nicegui_app.components import stat_table
            stat_table(impact_rows)

        # VPA distribution bar chart
        chart_data = sorted_players[:10]
        if chart_data:
            names = [f"{rec['tag']} {nm}" for nm, rec in chart_data]
            vpas = [round(rec["vpa_sum"] / max(1, rec["games"]), 2) for _, rec in chart_data]
            colors = ["#16a34a" if v >= 0 else "#dc2626" for v in vpas]
            fig = go.Figure(go.Bar(
                x=vpas, y=names, orientation="h",
                marker_color=colors,
                text=[f"{v:+.1f}" for v in vpas],
                textposition="outside",
            ))
            fig.update_layout(
                title=f"{team_name} — Avg Player VPA ({n} games)",
                xaxis_title="Avg VPA/Game",
                yaxis=dict(autorange="reversed"),
                height=max(250, len(chart_data) * 35 + 80),
                template="plotly_white",
                margin=dict(l=200),
            )
            ui.plotly(fig).classes("w-full")
