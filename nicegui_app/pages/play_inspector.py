"""Play Inspector - Single Play Runner page for the NiceGUI Viperball app.

Runs N single plays with a chosen style/situation and displays aggregate
stats, yards distribution, result breakdown, and play-family pie chart.
Migrated from ui/page_modules/play_inspector.py.
"""

from __future__ import annotations

import csv
import io

from nicegui import ui

import plotly.express as px

from engine import ViperballEngine, OFFENSE_STYLES
from engine.game_engine import WEATHER_CONDITIONS
from nicegui_app.helpers import load_team
from nicegui_app.components import metric_card, download_button


def render_play_inspector(state, shared):
    teams = shared["teams"]
    styles = shared["styles"]
    style_keys = shared["style_keys"]

    ui.label("Play Inspector - Single Play Runner").classes("text-3xl font-bold")

    # -- Offense style & situation ------------------------------------------
    style_options = {k: styles[k]["label"] for k in style_keys}
    params = {
        "style": style_keys[0] if style_keys else "balanced",
        "field_pos": 40,
        "down": 1,
        "ytg": 20,
        "num_plays": 50,
        "seed": 0,
        "weather": list(WEATHER_CONDITIONS.keys())[0],
    }

    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-1"):
            def _on_style(e):
                params["style"] = e.value
                _update_style_info()

            style_select = ui.select(
                style_options, label="Offense Style",
                value=params["style"], on_change=_on_style,
            ).classes("w-full")

            style_info_container = ui.column().classes("w-full")

            def _update_style_info():
                style_info_container.clear()
                s = params["style"]
                info = OFFENSE_STYLES.get(s, {})
                with style_info_container:
                    ui.label(styles.get(s, {}).get("description", "")).classes(
                        "text-xs text-gray-500"
                    )
                    with ui.row().classes("gap-4 flex-wrap"):
                        ui.label(f"Tempo: {info.get('tempo', '?')}").classes("text-xs")
                        ui.label(f"Lateral Risk: {info.get('lateral_risk', '?')}").classes("text-xs")
                        ui.label(f"Kick Rate: {info.get('kick_rate', '?')}").classes("text-xs")
                        ui.label(f"Option Rate: {info.get('option_rate', '?')}").classes("text-xs")

            _update_style_info()

        with ui.column().classes("flex-1"):
            ui.slider(
                min=1, max=99, value=params["field_pos"],
                on_change=lambda e: params.update(field_pos=int(e.value)),
            ).props("label-always").classes("w-full")
            ui.label("Field Position (yards from own goal)").classes("text-xs text-gray-500")

            ui.select(
                {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th"},
                label="Down", value=params["down"],
                on_change=lambda e: params.update(down=e.value),
            ).classes("w-full")

            ui.number(
                "Yards to Go", min=1, max=99, value=params["ytg"],
                on_change=lambda e: params.update(
                    ytg=int(e.value) if e.value is not None else 20
                ),
            ).classes("w-full")

    # -- Sim controls ------------------------------------------------------
    weather_options = {k: v["label"] for k, v in WEATHER_CONDITIONS.items()}
    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-1"):
            ui.slider(
                min=1, max=500, value=params["num_plays"],
                on_change=lambda e: params.update(num_plays=int(e.value)),
            ).props("label-always").classes("w-full")
            ui.label("Number of Plays to Run").classes("text-xs text-gray-500")
        with ui.column().classes("flex-1"):
            ui.number(
                "Base Seed (0 = random)", min=0, max=999999, value=params["seed"],
                on_change=lambda e: params.update(
                    seed=int(e.value) if e.value is not None else 0
                ),
            ).classes("w-full")
        with ui.column().classes("flex-1"):
            ui.select(
                weather_options, label="Weather", value=params["weather"],
                on_change=lambda e: params.update(weather=e.value),
            ).classes("w-full")

    # -- Results container -------------------------------------------------
    results_container = ui.column().classes("w-full")

    async def run_plays():
        home_team = load_team(teams[0]["key"])
        away_team = load_team(
            teams[1]["key"] if len(teams) > 1 else teams[0]["key"]
        )

        results_container.clear()
        with results_container:
            progress = ui.linear_progress(value=0).classes("w-full")

        play_results = []
        n = params["num_plays"]
        for i in range(n):
            s = (params["seed"] + i) if params["seed"] > 0 else None
            engine = ViperballEngine(home_team, away_team, seed=s, weather=params["weather"])
            result = engine.simulate_single_play(
                style=params["style"],
                field_position=params["field_pos"],
                down=params["down"],
                yards_to_go=params["ytg"],
            )
            result["run_number"] = i + 1
            play_results.append(result)
            progress.set_value((i + 1) / n)

        state.play_inspector_results = play_results
        _render_results(results_container, play_results)

    ui.button("Run Plays", on_click=run_plays, icon="play_arrow").props(
        "color=primary"
    ).classes("w-full mt-2")

    # -- Show cached results -----------------------------------------------
    if getattr(state, "play_inspector_results", None):
        _render_results(results_container, state.play_inspector_results)


def _render_results(container, play_results):
    """Populate the results container with aggregate stats and charts."""
    container.clear()
    n = len(play_results)

    yards_list = [p["yards"] for p in play_results]
    results_list = [p["result"] for p in play_results]
    families = [p.get("play_family", "unknown") for p in play_results]

    with container:
        ui.separator()
        ui.label(f"Results: {n} Plays").classes("text-xl font-semibold mt-2")

        # -- Export CSV ----------------------------------------------------
        pi_output = io.StringIO()
        pi_writer = csv.writer(pi_output)
        pi_writer.writerow([
            "run", "play_family", "play_type", "yards", "result",
            "description", "fatigue", "field_position",
        ])
        for pr in play_results:
            pi_writer.writerow([
                pr.get("run_number", ""), pr.get("play_family", ""),
                pr.get("play_type", ""), pr["yards"], pr["result"],
                pr.get("description", ""), pr.get("fatigue", ""),
                pr.get("field_position", ""),
            ])
        download_button(
            "Export Plays (.csv)",
            pi_output.getvalue(),
            f"play_inspector_{n}plays.csv",
            mime="text/csv",
        )

        # -- Metrics -------------------------------------------------------
        td_count = sum(1 for r in results_list if r == "touchdown")
        fd_count = sum(1 for r in results_list if r == "first_down")
        fumble_count = sum(1 for r in results_list if r == "fumble")
        gain_count = sum(1 for r in results_list if r == "gain")
        negative = sum(1 for y in yards_list if y < 0)

        with ui.row().classes("w-full gap-4 flex-wrap"):
            metric_card("Avg Yards", round(sum(yards_list) / n, 2))
            metric_card("Max Yards", max(yards_list))
            metric_card("Min Yards", min(yards_list))
            metric_card("TD Rate", f"{round(td_count / n * 100, 1)}%")

        with ui.row().classes("w-full gap-4 flex-wrap"):
            metric_card("First Down Rate", f"{round(fd_count / n * 100, 1)}%")
            metric_card("Fumble Rate", f"{round(fumble_count / n * 100, 1)}%")
            metric_card("Gain (no FD)", f"{round(gain_count / n * 100, 1)}%")
            metric_card("Negative Plays", f"{round(negative / n * 100, 1)}%")

        # -- Yards Distribution chart --------------------------------------
        ui.label("Yards Distribution").classes("text-xl font-semibold mt-4")
        fig = px.histogram(x=yards_list, nbins=30, title="Yards Gained Distribution")
        fig.update_xaxes(title="Yards")
        fig.update_yaxes(title="Frequency")
        fig.update_layout(height=350)
        ui.plotly(fig).classes("w-full")

        # -- Result Breakdown chart ----------------------------------------
        ui.label("Result Breakdown").classes("text-xl font-semibold mt-4")
        result_counts: dict[str, int] = {}
        for r in results_list:
            result_counts[r] = result_counts.get(r, 0) + 1
        fig = px.bar(
            x=list(result_counts.keys()), y=list(result_counts.values()),
            title="Play Results",
        )
        fig.update_xaxes(title="Result")
        fig.update_yaxes(title="Count")
        fig.update_layout(height=350)
        ui.plotly(fig).classes("w-full")

        # -- Play Family pie chart -----------------------------------------
        ui.label("Play Family Distribution").classes("text-xl font-semibold mt-4")
        fam_counts: dict[str, int] = {}
        for f in families:
            fam_counts[f] = fam_counts.get(f, 0) + 1
        fig = px.pie(
            values=list(fam_counts.values()), names=list(fam_counts.keys()),
            title="Play Families Selected",
        )
        fig.update_layout(height=350)
        ui.plotly(fig).classes("w-full")

        # -- Play-by-play detail table -------------------------------------
        ui.label("Play-by-Play Detail").classes("text-xl font-semibold mt-4")
        display_cols = [
            "run_number", "play_family", "play_type", "yards",
            "result", "description", "fatigue", "field_position",
        ]
        available = [c for c in display_cols if c in play_results[0]]
        col_defs = [
            {"name": c, "label": c.replace("_", " ").title(), "field": c, "align": "left", "sortable": True}
            for c in available
        ]
        rows = [
            {c: str(p.get(c, "")) for c in available}
            for p in play_results
        ]
        ui.table(columns=col_defs, rows=rows).classes("w-full").props(
            "dense flat virtual-scroll"
        ).style("max-height: 400px;")
