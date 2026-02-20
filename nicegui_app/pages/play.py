"""Play section — NiceGUI version.

Orchestrates the main Play tab: mode selection (New Dynasty / New Season /
Quick Game) when no session is active, or the active season/dynasty
simulation UI when a session exists.
"""

from __future__ import annotations

import os
import random

from nicegui import ui

from ui import api_client
from nicegui_app.state import UserState
from nicegui_app.helpers import OFFENSE_TOOLTIPS, DEFENSE_TOOLTIPS, fmt_vb_score
from nicegui_app.components import metric_card, stat_table, notify_error, notify_info, notify_success
from nicegui_app.pages.game_simulator import render_game_simulator
from nicegui_app.pages.season_simulator import render_season_simulator
from nicegui_app.pages.dynasty_mode import render_dynasty_mode


def render_play_section(state: UserState, shared: dict):
    """Main play section entry point."""

    @ui.refreshable
    def _play_content():
        if state.mode == "dynasty":
            _render_dynasty_play(state, shared)
        elif state.mode == "season":
            _render_season_play(state, shared)
        else:
            _render_mode_selection(state, shared)

    _play_content()


def _render_mode_selection(state: UserState, shared: dict):
    """Show mode selection tabs when no active session."""
    ui.label("Play").classes("text-2xl font-bold text-slate-800")
    ui.label("Start a new dynasty, season, or play a quick exhibition game").classes("text-sm text-gray-500 mb-4")

    with ui.tabs().classes("w-full") as mode_tabs:
        dynasty_tab = ui.tab("New Dynasty")
        season_tab = ui.tab("New Season")
        quick_tab = ui.tab("Quick Game")

    with ui.tab_panels(mode_tabs, value=quick_tab).classes("w-full"):
        with ui.tab_panel(dynasty_tab):
            render_dynasty_mode(state, shared)

        with ui.tab_panel(season_tab):
            render_season_simulator(state, shared)

        with ui.tab_panel(quick_tab):
            render_game_simulator(state, shared)


def _render_season_play(state: UserState, shared: dict):
    """Render the active season simulation UI."""
    if not state.session_id:
        ui.label("No active session.").classes("text-gray-400 italic")
        return

    try:
        status = api_client.get_season_status(state.session_id)
    except api_client.APIError as e:
        notify_error(f"Failed to load season: {e.detail}")
        return

    season_name = status.get("name", "Season")
    current_week = status.get("current_week", 0)
    total_weeks = status.get("total_weeks", 10)
    phase = status.get("phase", "regular")

    ui.label(f"{season_name}").classes("text-2xl font-bold text-slate-800")

    with ui.row().classes("w-full gap-3 flex-wrap mb-4"):
        metric_card("Week", f"{current_week}/{total_weeks}")
        metric_card("Phase", phase.title())

    results_container = ui.column().classes("w-full")

    @ui.refreshable
    def _season_actions():
        try:
            status = api_client.get_season_status(state.session_id)
        except api_client.APIError:
            return

        phase = status.get("phase", "regular")
        current_week = status.get("current_week", 0)
        total_weeks = status.get("total_weeks", 10)

        if phase == "regular":
            with ui.row().classes("gap-4"):
                def _sim_week():
                    try:
                        result = api_client.simulate_week(state.session_id)
                        week = result.get("week_simulated", current_week + 1)
                        notify_success(f"Week {week} simulated!")
                        _season_actions.refresh()
                    except api_client.APIError as e:
                        notify_error(f"Simulation failed: {e.detail}")

                def _sim_rest():
                    try:
                        api_client.simulate_rest(state.session_id)
                        notify_success("Regular season complete!")
                        _season_actions.refresh()
                    except api_client.APIError as e:
                        notify_error(f"Simulation failed: {e.detail}")

                ui.button(f"Simulate Week {current_week + 1}", on_click=_sim_week, icon="play_arrow").props("color=primary")
                ui.button("Sim Rest of Season", on_click=_sim_rest, icon="fast_forward")

        elif phase == "postseason" or phase == "playoffs":
            def _run_playoffs():
                try:
                    api_client.run_playoffs(state.session_id)
                    notify_success("Playoffs complete!")
                    _season_actions.refresh()
                except api_client.APIError as e:
                    notify_error(f"Playoffs failed: {e.detail}")

            ui.button("Run Playoffs", on_click=_run_playoffs, icon="emoji_events").props("color=primary")

        elif phase == "bowls":
            def _run_bowls():
                try:
                    api_client.run_bowls(state.session_id)
                    notify_success("Bowl games complete!")
                    _season_actions.refresh()
                except api_client.APIError as e:
                    notify_error(f"Bowls failed: {e.detail}")

            ui.button("Run Bowl Games", on_click=_run_bowls, icon="stadium").props("color=primary")

        elif phase == "complete":
            with ui.card().classes("w-full bg-green-50 p-4 rounded"):
                ui.label("Season Complete!").classes("font-bold text-green-700")
                ui.label("Check the League tab for final standings and awards.").classes("text-sm text-green-600")

        # Show recent results
        try:
            schedule = api_client.get_schedule(state.session_id, completed_only=True)
            games = schedule.get("games", [])
            if games:
                recent = games[-min(10, len(games)):]
                with ui.expansion(f"Recent Results ({len(games)} games played)", icon="history").classes("w-full mt-4"):
                    rows = []
                    for g in reversed(recent):
                        rows.append({
                            "Week": g.get("week", ""),
                            "Home": g.get("home_team", ""),
                            "Score": f"{fmt_vb_score(g.get('home_score', 0))} - {fmt_vb_score(g.get('away_score', 0))}",
                            "Away": g.get("away_team", ""),
                        })
                    stat_table(rows)
        except api_client.APIError:
            pass

    with results_container:
        _season_actions()


def _render_dynasty_play(state: UserState, shared: dict):
    """Render the active dynasty simulation UI."""
    if not state.session_id:
        ui.label("No active session.").classes("text-gray-400 italic")
        return

    try:
        dyn_status = api_client.get_dynasty_status(state.session_id)
    except api_client.APIError as e:
        notify_error(f"Failed to load dynasty: {e.detail}")
        return

    dynasty_name = dyn_status.get("dynasty_name", "Dynasty")
    current_year = dyn_status.get("current_year", "")
    coach_name = dyn_status.get("coach_name", "Coach")
    coach_team = dyn_status.get("coach_team", "")
    total_wins = dyn_status.get("total_wins", 0)
    total_losses = dyn_status.get("total_losses", 0)

    ui.label(f"{dynasty_name} - {current_year}").classes("text-2xl font-bold text-slate-800")

    with ui.row().classes("w-full gap-3 flex-wrap mb-4"):
        metric_card("Coach", coach_name)
        metric_card("Team", coach_team)
        metric_card("Record", f"{total_wins}-{total_losses}")
        metric_card("Year", str(current_year))

    dynasty_phase = dyn_status.get("season_phase", "")

    results_container = ui.column().classes("w-full")

    @ui.refreshable
    def _dynasty_actions():
        try:
            dyn_status = api_client.get_dynasty_status(state.session_id)
        except api_client.APIError:
            return

        season_active = dyn_status.get("season_active", False)
        season_phase = dyn_status.get("season_phase", "")

        if not season_active:
            # Need to start a new season
            ui.label("Start New Season").classes("font-bold text-slate-700 mt-2")
            ui.label("Configure your team's strategy for the upcoming season.").classes("text-sm text-gray-500")

            styles = shared["styles"]
            style_keys = shared["style_keys"]
            defense_style_keys = shared["defense_style_keys"]
            defense_styles = shared["defense_styles"]
            st_schemes = shared["st_schemes"]
            st_scheme_keys = shared["st_scheme_keys"]
            style_options = {k: styles[k]["label"] for k in style_keys}
            def_options = {k: defense_styles[k]["label"] for k in defense_style_keys}
            st_options = {k: st_schemes[k]["label"] for k in st_scheme_keys} if st_scheme_keys else {"aces": "Aces"}

            off_sel = ui.select(style_options, value="balanced", label="Offense Style").classes("w-64")
            def_sel = ui.select(def_options, value="swarm", label="Defense Style").classes("w-64")
            st_sel = ui.select(st_options, value="aces", label="Special Teams").classes("w-64")

            def _start_season():
                try:
                    api_client.dynasty_start_season(
                        state.session_id,
                        offense_style=off_sel.value,
                        defense_style=def_sel.value,
                        st_scheme=st_sel.value,
                    )
                    notify_success("Season started!")
                    _dynasty_actions.refresh()
                except api_client.APIError as e:
                    notify_error(f"Failed to start season: {e.detail}")

            ui.button("Start Season", on_click=_start_season, icon="play_arrow").props("color=primary").classes("mt-2")

        else:
            # Season is active — show simulation controls
            _render_season_play(state, shared)

    with results_container:
        _dynasty_actions()
