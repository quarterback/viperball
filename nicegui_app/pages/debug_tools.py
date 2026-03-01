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
    generate_batch_full_export,
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

    def_style_options = {k: defense_styles[k]["label"] for k in defense_style_keys}

    home_key = {"value": team_keys[0] if team_keys else ""}
    away_key = {"value": team_keys[min(1, len(team_keys) - 1)] if team_keys else ""}
    home_style = {"value": style_keys[0] if style_keys else ""}
    away_style = {"value": style_keys[0] if style_keys else ""}
    home_def_style = {"value": defense_style_keys[0] if defense_style_keys else ""}
    away_def_style = {"value": defense_style_keys[0] if defense_style_keys else ""}

    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-1"):
            ui.select(
                team_options, label="Home Team", value=home_key["value"],
                on_change=lambda e: home_key.update(value=e.value),
            ).classes("w-full")
            ui.select(
                style_options, label="Home Offense", value=home_style["value"],
                on_change=lambda e: home_style.update(value=e.value),
            ).classes("w-full")
            ui.select(
                def_style_options, label="Home Defense", value=home_def_style["value"],
                on_change=lambda e: home_def_style.update(value=e.value),
            ).classes("w-full")
        with ui.column().classes("flex-1"):
            ui.select(
                team_options, label="Away Team", value=away_key["value"],
                on_change=lambda e: away_key.update(value=e.value),
            ).classes("w-full")
            ui.select(
                style_options, label="Away Offense", value=away_style["value"],
                on_change=lambda e: away_style.update(value=e.value),
            ).classes("w-full")
            ui.select(
                def_style_options, label="Away Defense", value=away_def_style["value"],
                on_change=lambda e: away_def_style.update(value=e.value),
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
            f"{home_team_data.name}_defense": home_def_style["value"],
            f"{away_team_data.name}_defense": away_def_style["value"],
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
            with ui.column().classes("flex-1"):
                analysis_json = json.dumps(
                    generate_batch_full_export(results), indent=2, default=str,
                )
                download_button(
                    "Full Analysis (.json)",
                    analysis_json,
                    f"{batch_tag}_analysis.json",
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

        # -- WPA (Win Probability Added) -------------------------------------
        ui.label("Avg WPA (Win Probability Added)").classes("text-base font-bold mt-4")

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
            metric_card(f"Avg {home_name} WPA", round(sum(home_total_vpa) / n, 2))
            metric_card(f"Avg {away_name} WPA", round(sum(away_total_vpa) / n, 2))
            metric_card(f"Avg {home_name} WPA/Play", round(sum(home_vpa_pp) / n, 3))
            metric_card(f"Avg {away_name} WPA/Play", round(sum(away_vpa_pp) / n, 3))

        home_sr = [r["stats"]["home"].get("epa", {}).get("success_rate", 0) for r in results]
        away_sr = [r["stats"]["away"].get("epa", {}).get("success_rate", 0) for r in results]
        home_exp = [r["stats"]["home"].get("epa", {}).get("explosiveness", 0) for r in results]
        away_exp = [r["stats"]["away"].get("epa", {}).get("explosiveness", 0) for r in results]

        with ui.row().classes("w-full gap-4 flex-wrap"):
            metric_card(f"Avg {home_name} Success Rate", f"{round(sum(home_sr) / n, 1)}%")
            metric_card(f"Avg {away_name} Success Rate", f"{round(sum(away_sr) / n, 1)}%")
            metric_card(f"Avg {home_name} Explosiveness", round(sum(home_exp) / n, 3))
            metric_card(f"Avg {away_name} Explosiveness", round(sum(away_exp) / n, 3))

        # -- DYE (Power Play / Penalty Kill) across batch -------------------------
        ui.label("DYE — Power Play / Penalty Kill (Batch)").classes("text-base font-bold mt-4")
        ui.label("How much did delta kickoff and bonus possessions affect outcomes across all games?").classes("text-sm text-gray-500")

        all_pk_ypd = []
        all_pp_ypd = []
        all_neu_ypd = []
        all_pk_sr = []
        all_pp_sr = []
        all_neu_sr = []
        total_opp_pp_scores = 0
        wins_despite_delta = 0
        total_bonus_scores = 0
        total_bonus_drives = 0

        for r in results:
            for side in ["home", "away"]:
                dye = r["stats"][side].get("dye", {})
                pk = dye.get("penalty_kill", {})
                pp = dye.get("power_play", {})
                neu = dye.get("neutral", {})
                if pk.get("count", 0) > 0:
                    all_pk_ypd.append(pk["yards_per_drive"])
                    all_pk_sr.append(pk["score_rate"])
                if pp.get("count", 0) > 0:
                    all_pp_ypd.append(pp["yards_per_drive"])
                    all_pp_sr.append(pp["score_rate"])
                if neu.get("count", 0) > 0:
                    all_neu_ypd.append(neu["yards_per_drive"])
                    all_neu_sr.append(neu["score_rate"])
                total_bonus_scores += r["stats"][side].get("bonus_possession_scores", 0)
                total_bonus_drives += r["stats"][side].get("bonus_possessions", 0)

            winner = "home" if r["final_score"]["home"]["score"] > r["final_score"]["away"]["score"] else "away"
            loser = "away" if winner == "home" else "home"
            w_dye = r["stats"][winner].get("dye", {})
            l_dye = r["stats"][loser].get("dye", {})
            if w_dye.get("penalty_kill", {}).get("count", 0) > 0:
                wins_despite_delta += 1
            total_opp_pp_scores += l_dye.get("power_play", {}).get("scores", 0)

        with ui.row().classes("w-full gap-4 flex-wrap"):
            avg_pk = round(sum(all_pk_ypd) / max(1, len(all_pk_ypd)), 1) if all_pk_ypd else 0
            avg_pp = round(sum(all_pp_ypd) / max(1, len(all_pp_ypd)), 1) if all_pp_ypd else 0
            avg_neu = round(sum(all_neu_ypd) / max(1, len(all_neu_ypd)), 1) if all_neu_ypd else 0
            metric_card("Penalty Kill YPD", avg_pk)
            metric_card("Power Play YPD", avg_pp)
            metric_card("Neutral YPD", avg_neu)
            dye_ratio = round(avg_pk / avg_neu, 2) if avg_neu > 0 else "—"
            metric_card("DYE Ratio (PK/Neu)", dye_ratio)

        with ui.row().classes("w-full gap-4 flex-wrap"):
            avg_pk_sr = round(sum(all_pk_sr) / max(1, len(all_pk_sr)), 1) if all_pk_sr else 0
            avg_pp_sr = round(sum(all_pp_sr) / max(1, len(all_pp_sr)), 1) if all_pp_sr else 0
            avg_neu_sr = round(sum(all_neu_sr) / max(1, len(all_neu_sr)), 1) if all_neu_sr else 0
            metric_card("Kill Rate (PK Score%)", f"{avg_pk_sr}%")
            metric_card("PP%", f"{avg_pp_sr}%")
            metric_card("Neutral Score%", f"{avg_neu_sr}%")
            batch_mess = round(avg_pp_sr - avg_pk_sr, 1) if all_pp_sr and all_pk_sr else "—"
            metric_card("Batch Mess Rate", batch_mess)
            metric_card("Wins Despite Δ Penalty", f"{wins_despite_delta}/{n}")

        with ui.row().classes("w-full gap-4 flex-wrap"):
            metric_card("Opp PP Scores", round(total_opp_pp_scores / n, 1))
            bonus_sr = round(total_bonus_scores / max(1, total_bonus_drives) * 100, 1)
            metric_card("Bonus Poss. Score%", f"{bonus_sr}%")
            metric_card("Bonus Scores/Game", round(total_bonus_scores / n, 2))

        dye_chart_data = []
        for label, ypd_val, sr_val in [("Penalty Kill", avg_pk, avg_pk_sr),
                                        ("Power Play", avg_pp, avg_pp_sr),
                                        ("Neutral", avg_neu, avg_neu_sr)]:
            dye_chart_data.append({"Situation": label, "Yds/Drive": ypd_val, "Score %": sr_val})

        if dye_chart_data:
            import pandas as pd
            df = pd.DataFrame(dye_chart_data)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df["Situation"], y=df["Yds/Drive"], name="Yds/Drive",
                                 marker_color="#2563eb"))
            fig.add_trace(go.Bar(x=df["Situation"], y=df["Score %"], name="Score %",
                                 marker_color="#dc2626", yaxis="y2"))
            fig.update_layout(
                title="DYE: Yards/Drive & Score Rate by Situation (Batch Avg)",
                yaxis=dict(title="Yards / Drive", side="left"),
                yaxis2=dict(title="Score %", side="right", overlaying="y", ticksuffix="%"),
                barmode="group", height=350, template="plotly_white",
            )
            ui.plotly(fig).classes("w-full")

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

        # -- Defensive Stats ----------------------------------------------------
        _render_defensive_stats(results, n, home_name, away_name)

        # -- Player Impact Report -----------------------------------------------
        _render_batch_player_impact(results, n, home_name, away_name)


def _render_defensive_stats(results, n, home_name, away_name):
    """Render defensive metrics: INTs, turnovers forced, DC gameplan, adaptation."""
    from collections import defaultdict

    ui.separator()
    ui.label("Defensive Performance").classes("text-2xl font-semibold mt-4")

    # ── Turnovers Forced (defense view: your INTs = opponent's thrown INTs) ──
    # Home defense forces turnovers on away offense, and vice versa
    home_def_kp_ints = [r["stats"]["away"].get("kick_pass_interceptions", 0) for r in results]
    home_def_lat_ints = [r["stats"]["away"].get("lateral_interceptions", 0) for r in results]
    home_def_fumbles = [r["stats"]["away"].get("fumbles_lost", 0) for r in results]
    away_def_kp_ints = [r["stats"]["home"].get("kick_pass_interceptions", 0) for r in results]
    away_def_lat_ints = [r["stats"]["home"].get("lateral_interceptions", 0) for r in results]
    away_def_fumbles = [r["stats"]["home"].get("fumbles_lost", 0) for r in results]

    home_def_total_ints = [k + l for k, l in zip(home_def_kp_ints, home_def_lat_ints)]
    away_def_total_ints = [k + l for k, l in zip(away_def_kp_ints, away_def_lat_ints)]
    home_def_total_to = [i + f for i, f in zip(home_def_total_ints, home_def_fumbles)]
    away_def_total_to = [i + f for i, f in zip(away_def_total_ints, away_def_fumbles)]

    # Yards allowed
    home_def_yards_allowed = [r["stats"]["away"]["total_yards"] for r in results]
    away_def_yards_allowed = [r["stats"]["home"]["total_yards"] for r in results]
    home_def_tds_allowed = [r["stats"]["away"]["touchdowns"] for r in results]
    away_def_tds_allowed = [r["stats"]["home"]["touchdowns"] for r in results]

    ui.label("Turnovers Forced (Defensive View)").classes("text-xl font-semibold mt-2")

    def_rows = [
        {
            "Metric": "Avg KP INTs Forced",
            f"{home_name} DEF": str(round(sum(home_def_kp_ints) / n, 2)),
            f"{away_name} DEF": str(round(sum(away_def_kp_ints) / n, 2)),
        },
        {
            "Metric": "Avg Lateral INTs Forced",
            f"{home_name} DEF": str(round(sum(home_def_lat_ints) / n, 2)),
            f"{away_name} DEF": str(round(sum(away_def_lat_ints) / n, 2)),
        },
        {
            "Metric": "Avg Total INTs Forced",
            f"{home_name} DEF": str(round(sum(home_def_total_ints) / n, 2)),
            f"{away_name} DEF": str(round(sum(away_def_total_ints) / n, 2)),
        },
        {
            "Metric": "Avg Fumbles Forced",
            f"{home_name} DEF": str(round(sum(home_def_fumbles) / n, 2)),
            f"{away_name} DEF": str(round(sum(away_def_fumbles) / n, 2)),
        },
        {
            "Metric": "Avg Total Turnovers Forced",
            f"{home_name} DEF": str(round(sum(home_def_total_to) / n, 2)),
            f"{away_name} DEF": str(round(sum(away_def_total_to) / n, 2)),
        },
        {
            "Metric": "Avg Yards Allowed",
            f"{home_name} DEF": str(round(sum(home_def_yards_allowed) / n, 1)),
            f"{away_name} DEF": str(round(sum(away_def_yards_allowed) / n, 1)),
        },
        {
            "Metric": "Avg TDs Allowed",
            f"{home_name} DEF": str(round(sum(home_def_tds_allowed) / n, 2)),
            f"{away_name} DEF": str(round(sum(away_def_tds_allowed) / n, 2)),
        },
    ]
    def_columns = [
        {"name": "Metric", "label": "Metric", "field": "Metric", "align": "left"},
        {"name": f"{home_name} DEF", "label": f"{home_name} DEF",
         "field": f"{home_name} DEF", "align": "right"},
        {"name": f"{away_name} DEF", "label": f"{away_name} DEF",
         "field": f"{away_name} DEF", "align": "right"},
    ]
    ui.table(columns=def_columns, rows=def_rows).classes("w-full").props("dense flat")

    # ── DC Gameplan & Modifier Stack (V2.4) ──
    ui.label("DC Gameplan & Modifier Stack").classes("text-xl font-semibold mt-4")
    ui.label(
        "Per-game DC suppression rolls and combined modifier picture. "
        "Values < 1.0 = suppression, > 1.0 = vulnerability."
    ).classes("text-sm text-gray-500")

    play_types = ("run", "lateral", "kick_pass", "trick")

    # Aggregate DC gameplan values and modifier stack across sims
    for side, label in [("home_defense", f"{home_name} DEF"), ("away_defense", f"{away_name} DEF")]:
        dc_accum = {pt: [] for pt in play_types}
        temp_counts = defaultdict(int)
        stack_labels = []
        solved_counts = defaultdict(int)
        nfz_count = 0

        for r in results:
            ms = r.get("modifier_stack", {}).get(side, {})
            if not ms:
                continue
            gp = ms.get("dc_gameplan", {})
            for pt in play_types:
                if pt in gp:
                    dc_accum[pt].append(gp[pt])
            temp = ms.get("game_temperature", "neutral")
            temp_counts[temp] += 1
            sl = ms.get("stack_label", "")
            if sl:
                stack_labels.append(sl)
            for fam in ms.get("solved_families", {}):
                solved_counts[fam] += 1
            if ms.get("no_fly_zone", False):
                nfz_count += 1

        # Only render if we have data
        has_data = any(len(v) > 0 for v in dc_accum.values())
        if not has_data:
            ui.label(f"{label}: No V2.4 modifier data (coaching may not be configured)").classes(
                "text-sm text-gray-400 italic"
            )
            continue

        ui.label(label).classes("text-lg font-bold text-slate-700 mt-2")

        # DC gameplan avg suppression per play type
        gp_rows = []
        for pt in play_types:
            vals = dc_accum[pt]
            if vals:
                avg_val = round(sum(vals) / len(vals), 3)
                min_val = round(min(vals), 3)
                max_val = round(max(vals), 3)
            else:
                avg_val = min_val = max_val = "-"
            pt_label = {"run": "Run", "lateral": "Lateral", "kick_pass": "Kick Pass", "trick": "Trick"}
            gp_rows.append({
                "Play Type": pt_label.get(pt, pt),
                "Avg Suppression": str(avg_val),
                "Min (Best Game)": str(min_val),
                "Max (Worst Game)": str(max_val),
            })
        gp_columns = [
            {"name": "Play Type", "label": "Play Type", "field": "Play Type", "align": "left"},
            {"name": "Avg Suppression", "label": "Avg Suppression", "field": "Avg Suppression", "align": "right"},
            {"name": "Min (Best Game)", "label": "Min (Best Game)", "field": "Min (Best Game)", "align": "right"},
            {"name": "Max (Worst Game)", "label": "Max (Worst Game)", "field": "Max (Worst Game)", "align": "right"},
        ]
        ui.table(columns=gp_columns, rows=gp_rows).classes("w-full").props("dense flat")

        # Game temperature distribution
        total_temps = sum(temp_counts.values())
        if total_temps > 0:
            with ui.row().classes("w-full gap-4 flex-wrap mt-1"):
                for temp in ["cold", "neutral", "hot"]:
                    count = temp_counts.get(temp, 0)
                    pct = round(count / total_temps * 100, 1)
                    color = {"cold": "#3b82f6", "neutral": "#94a3b8", "hot": "#ef4444"}.get(temp, "#94a3b8")
                    emoji = {"cold": "Cold", "neutral": "Neutral", "hot": "Hot"}.get(temp, temp)
                    metric_card(f"{emoji} Games", f"{count}/{total_temps} ({pct}%)")

        # Solved families frequency
        if solved_counts:
            with ui.row().classes("w-full gap-4 flex-wrap mt-1"):
                for fam, count in sorted(solved_counts.items(), key=lambda x: -x[1]):
                    metric_card(f"Solved: {fam}", f"{count}/{n} games")

        # NFZ count
        if nfz_count > 0:
            metric_card("No-Fly Zone Active", f"{nfz_count}/{n} games")

        # Most common stack label
        if stack_labels:
            from collections import Counter
            most_common = Counter(stack_labels).most_common(1)[0]
            ui.label(f"Most frequent modifier story: \"{most_common[0]}\" ({most_common[1]}x)").classes(
                "text-sm text-gray-600 italic mt-1"
            )

    # ── DC Suppression Heatmap ──
    # Build a heatmap showing avg suppression per play type per side
    heatmap_data = []
    for side, label in [("home_defense", f"{home_name} DEF"), ("away_defense", f"{away_name} DEF")]:
        for pt in play_types:
            vals = []
            for r in results:
                ms = r.get("modifier_stack", {}).get(side, {})
                gp = ms.get("dc_gameplan", {})
                if pt in gp:
                    # Combine DC gameplan with solved family suppression
                    base = gp[pt]
                    solved = ms.get("solved_families", {})
                    if pt in solved:
                        base *= solved[pt]
                    vals.append(base)
            if vals:
                pt_label = {"run": "Run", "lateral": "Lateral", "kick_pass": "Kick Pass", "trick": "Trick"}
                heatmap_data.append({
                    "side": label, "play_type": pt_label.get(pt, pt),
                    "value": round(sum(vals) / len(vals), 3),
                })

    if heatmap_data:
        ui.label("Suppression Heatmap (DC + Adaptation Combined)").classes("text-xl font-semibold mt-4")

        sides = list(dict.fromkeys(d["side"] for d in heatmap_data))
        pts = list(dict.fromkeys(d["play_type"] for d in heatmap_data))
        z = []
        for s in sides:
            row = []
            for pt in pts:
                match = [d for d in heatmap_data if d["side"] == s and d["play_type"] == pt]
                row.append(match[0]["value"] if match else 1.0)
            z.append(row)

        fig = go.Figure(data=go.Heatmap(
            z=z, x=pts, y=sides,
            colorscale=[[0, "#1e40af"], [0.5, "#fbbf24"], [1, "#dc2626"]],
            zmin=0.75, zmax=1.12,
            text=[[f"{v:.3f}" for v in row] for row in z],
            texttemplate="%{text}",
            hovertemplate="Side: %{y}<br>Play Type: %{x}<br>Suppression: %{z:.3f}<extra></extra>",
        ))
        fig.update_layout(
            title="Avg Effective Suppression by Play Type",
            height=250,
            xaxis_title="Play Type",
            yaxis_title="",
            margin=dict(l=200),
        )
        ui.plotly(fig).classes("w-full")

    # ── Adaptation Log ──
    all_adaptation_events = []
    for r in results:
        events = r.get("adaptation_log", [])
        all_adaptation_events.extend(events)

    if all_adaptation_events:
        ui.label("Defensive Adaptation Events").classes("text-xl font-semibold mt-4")

        from collections import Counter
        event_counts = Counter(all_adaptation_events)
        total_events = len(all_adaptation_events)

        with ui.row().classes("w-full gap-4 flex-wrap"):
            metric_card("Total Adaptation Events", total_events)
            metric_card("Avg Events/Game", round(total_events / n, 1))

            solve_events = sum(c for e, c in event_counts.items() if "INSIGHT" in e or "solved" in e.lower())
            decay_events = sum(c for e, c in event_counts.items() if "BROKEN" in e or "reset" in e.lower())
            metric_card("Solves", solve_events)
            metric_card("Resets (Tendency Broken)", decay_events)

        # Top adaptation events
        top_events = event_counts.most_common(8)
        if top_events:
            event_rows = [
                {"Event": ev, "Count": str(ct), "Per Game": str(round(ct / n, 2))}
                for ev, ct in top_events
            ]
            event_columns = [
                {"name": "Event", "label": "Event", "field": "Event", "align": "left"},
                {"name": "Count", "label": "Count", "field": "Count", "align": "right"},
                {"name": "Per Game", "label": "Per Game", "field": "Per Game", "align": "right"},
            ]
            ui.table(columns=event_columns, rows=event_rows).classes("w-full").props("dense flat")

    # ── Offensive Performance ──
    _render_offensive_stats(results, n, home_name, away_name)


def _render_offensive_stats(results, n, home_name, away_name):
    """Render offensive performance: rushing, kick passing, laterals, trick plays by style."""
    ui.separator()
    ui.label("Offensive Performance").classes("text-2xl font-semibold mt-4")

    def _avg(vals):
        return round(sum(vals) / max(1, len(vals)), 2)

    def _side_stats(side):
        return [r["stats"][side] for r in results]

    for side, label in [("home", home_name), ("away", away_name)]:
        stats_list = _side_stats(side)
        ui.label(f"{label} Offense").classes("text-xl font-semibold mt-4")

        rush_car = [s.get("rushing_carries", 0) for s in stats_list]
        rush_yds = [s.get("rushing_yards", 0) for s in stats_list]
        rush_tds = [s.get("rushing_touchdowns", 0) for s in stats_list]
        kp_att = [s.get("kick_passes_attempted", 0) for s in stats_list]
        kp_comp = [s.get("kick_passes_completed", 0) for s in stats_list]
        kp_yds = [s.get("kick_pass_yards", 0) for s in stats_list]
        kp_tds = [s.get("kick_pass_tds", 0) for s in stats_list]
        kp_ints = [s.get("kick_pass_interceptions", 0) for s in stats_list]
        lat_chains = [s.get("lateral_chains", 0) for s in stats_list]
        lat_eff = [s.get("lateral_efficiency", 0) for s in stats_list]
        lat_yds = [s.get("lateral_yards", 0) for s in stats_list]
        dk_att = [s.get("drop_kicks_attempted", 0) for s in stats_list]
        dk_made = [s.get("drop_kicks_made", 0) for s in stats_list]
        pk_att = [s.get("place_kicks_attempted", 0) for s in stats_list]
        pk_made = [s.get("place_kicks_made", 0) for s in stats_list]
        total_yds = [s.get("total_yards", 0) for s in stats_list]
        total_plays = [s.get("total_plays", 0) for s in stats_list]
        tds = [s.get("touchdowns", 0) for s in stats_list]
        tricks = [s.get("play_family_breakdown", {}).get("trick_play", 0) for s in stats_list]

        avg_comp_pct = round(sum(kp_comp) / max(1, sum(kp_att)) * 100, 1)
        avg_dk_pct = round(sum(dk_made) / max(1, sum(dk_att)) * 100, 1)

        with ui.row().classes("w-full gap-3 flex-wrap"):
            metric_card("Avg Total Yds", _avg(total_yds))
            metric_card("Avg TDs", _avg(tds))
            metric_card("Avg Yds/Play", round(sum(total_yds) / max(1, sum(total_plays)), 1))
            metric_card("Avg Plays", _avg(total_plays))

        off_rows = [
            {"Category": "Rushing", "Avg/Game": f"{_avg(rush_car)} car, {_avg(rush_yds)} yds ({round(sum(rush_yds)/max(1,sum(rush_car)),1)} YPC)", "Total": str(sum(rush_yds)), "Avg TDs": str(_avg(rush_tds))},
            {"Category": "Kick Pass", "Avg/Game": f"{_avg(kp_att)} att, {_avg(kp_comp)} comp ({avg_comp_pct}%)", "Total": f"{sum(kp_yds)} yds", "Avg TDs": str(_avg(kp_tds))},
            {"Category": "KP Yards", "Avg/Game": f"{_avg(kp_yds)} yds", "Total": str(sum(kp_yds)), "Avg TDs": f"{_avg(kp_ints)} INTs"},
            {"Category": "Laterals", "Avg/Game": f"{_avg(lat_chains)} chains", "Total": f"{sum(lat_yds)} yds", "Avg TDs": f"{_avg(lat_eff)}% eff"},
            {"Category": "Snap Kicks", "Avg/Game": f"{_avg(dk_att)} att, {_avg(dk_made)} made ({avg_dk_pct}%)", "Total": f"{sum(dk_made)}/{sum(dk_att)}", "Avg TDs": "-"},
            {"Category": "Field Goals", "Avg/Game": f"{_avg(pk_att)} att, {_avg(pk_made)} made", "Total": f"{sum(pk_made)}/{sum(pk_att)}", "Avg TDs": "-"},
            {"Category": "Trick Plays", "Avg/Game": f"{_avg(tricks)}/game", "Total": str(sum(tricks)), "Avg TDs": "-"},
        ]
        off_columns = [
            {"name": "Category", "label": "Category", "field": "Category", "align": "left"},
            {"name": "Avg/Game", "label": "Avg/Game", "field": "Avg/Game", "align": "right"},
            {"name": "Total", "label": "Total", "field": "Total", "align": "right"},
            {"name": "Avg TDs", "label": "Extra", "field": "Avg TDs", "align": "right"},
        ]
        ui.table(columns=off_columns, rows=off_rows).classes("w-full").props("dense flat")

        # Play family distribution for this side
        fam_accum = {}
        for s in stats_list:
            fb = s.get("play_family_breakdown", {})
            for fam, count in fb.items():
                fam_accum[fam] = fam_accum.get(fam, 0) + count
        total_fam = sum(fam_accum.values()) or 1

        if fam_accum:
            sorted_fams = sorted(fam_accum.items(), key=lambda x: -x[1])
            fam_rows = [
                {
                    "Play Family": fam.replace("_", " ").title(),
                    "Total Calls": str(count),
                    "Avg/Game": str(round(count / n, 1)),
                    "Share": f"{round(count / total_fam * 100, 1)}%",
                }
                for fam, count in sorted_fams
            ]
            with ui.expansion(f"{label} Play Call Distribution", icon="analytics").classes("w-full mt-2"):
                fam_columns = [
                    {"name": "Play Family", "label": "Play Family", "field": "Play Family", "align": "left"},
                    {"name": "Total Calls", "label": "Total", "field": "Total Calls", "align": "right"},
                    {"name": "Avg/Game", "label": "Avg/Game", "field": "Avg/Game", "align": "right"},
                    {"name": "Share", "label": "Share %", "field": "Share", "align": "right"},
                ]
                ui.table(columns=fam_columns, rows=fam_rows).classes("w-full").props("dense flat")


def _render_batch_player_impact(results, n, home_name, away_name):
    """Aggregate per-player WPA across all batch simulations."""
    from collections import defaultdict

    ui.label("Player Impact Report").classes("text-xl font-semibold mt-6")
    ui.label(
        f"Average per-player WPA across {n} simulations. "
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

        # Sort by avg WPA descending
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
                metric_card("Avg Team WPA",
                            round(sum(v["vpa_sum"] for v in accum.values()) / n, 1))
                metric_card("Most Impactful", f"{top_rec['tag']} {top_name}")
                metric_card("Best Avg WPA", top_avg_vpa)
                # Find highest WPA/play among regulars (>= 50% of games)
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
                "Avg WPA": avg_vpa,
                "Avg WPA/Play": avg_vpa_pp,
                "Avg Plays": avg_plays,
                "Avg Touches": avg_touches,
                "Avg Yards": avg_yards,
                "Avg TDs": avg_tds,
                "Avg Fumbles": avg_fumbles,
            })
        if impact_rows:
            from nicegui_app.components import stat_table
            stat_table(impact_rows)

        # WPA distribution bar chart
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
                title=f"{team_name} — Avg Player WPA ({n} games)",
                xaxis_title="Avg WPA/Game",
                yaxis=dict(autorange="reversed"),
                height=max(250, len(chart_data) * 35 + 80),
                template="plotly_white",
                margin=dict(l=200),
            )
            ui.plotly(fig).classes("w-full")
