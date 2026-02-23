"""Play section — NiceGUI version.

Orchestrates the main Play tab: mode selection (New Dynasty / New Season /
Quick Game) when no session is active, or the active season/dynasty
simulation UI when a session exists.

All API calls use ``await run.io_bound()`` so that the blocking HTTP
round-trip runs in a thread-pool, keeping the NiceGUI / uvicorn event-loop
free to actually process the request (NiceGUI + FastAPI share one process).
"""

from __future__ import annotations

import os
import random

from nicegui import ui, run

from ui import api_client
from nicegui_app.state import UserState
from nicegui_app.helpers import OFFENSE_TOOLTIPS, DEFENSE_TOOLTIPS, fmt_vb_score
from nicegui_app.components import metric_card, stat_table, notify_error, notify_info, notify_success
from nicegui_app.pages.game_simulator import render_game_simulator
from nicegui_app.pages.season_simulator import render_season_simulator
from nicegui_app.pages.dynasty_mode import render_dynasty_mode


async def render_play_section(state: UserState, shared: dict):
    """Main play section entry point."""

    @ui.refreshable
    async def _play_content():
        if state.mode == "dynasty":
            await _render_dynasty_play(state, shared)
        elif state.mode == "season":
            await _render_season_play(state, shared)
        else:
            _render_mode_selection(state, shared)

    await _play_content()


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
            try:
                render_dynasty_mode(state, shared)
            except Exception as e:
                ui.label(f"Error loading dynasty mode: {e}").classes("text-red-500")

        with ui.tab_panel(season_tab):
            try:
                render_season_simulator(state, shared)
            except Exception as e:
                ui.label(f"Error loading season setup: {e}").classes("text-red-500")

        with ui.tab_panel(quick_tab):
            try:
                render_game_simulator(state, shared)
            except Exception as e:
                ui.label(f"Error loading game simulator: {e}").classes("text-red-500")


_PORTAL_POSITIONS = ["All", "VP", "HB", "WB", "SB", "ZB", "LB", "CB", "LA", "LM"]


async def _render_season_portal(state: UserState, refresh_fn):
    """Render the transfer portal UI for season mode.

    Lets the human player browse available transfers, commit players to
    their roster, and advance past the portal phase to start the regular
    season.
    """
    ui.label("Transfer Portal").classes("text-xl font-bold text-slate-700 mt-2")
    ui.label(
        "Browse available transfer players and add them to your roster before the season begins."
    ).classes("text-sm text-gray-500 mb-2")

    try:
        portal_resp = await run.io_bound(api_client.season_portal_get, state.session_id)
    except api_client.APIError as e:
        notify_error(f"Could not load portal: {e.detail}")
        return

    entries = portal_resp.get("entries", [])
    committed = portal_resp.get("committed", [])
    cap = portal_resp.get("transfer_cap", 0)
    remaining = portal_resp.get("transfers_remaining", 0)
    if remaining == -1:
        remaining = cap

    # ── Metrics ──────────────────────────────────────────────────────
    with ui.row().classes("w-full gap-3 flex-wrap mb-4"):
        metric_card("Available Players", len(entries))
        metric_card("Transfer Cap", cap)
        metric_card("Slots Remaining", remaining)

    # ── Committed players ────────────────────────────────────────────
    if committed:
        ui.label("Your Incoming Transfers").classes("font-bold text-slate-700 mt-2")
        committed_rows = []
        for c in committed:
            committed_rows.append({
                "Name": c.get("name", ""),
                "Pos": c.get("position", ""),
                "OVR": c.get("overall", 0),
                "Year": c.get("year", ""),
                "From": c.get("origin_team", ""),
            })
        stat_table(committed_rows)

    ui.separator().classes("my-4")

    # ── Filters ──────────────────────────────────────────────────────
    with ui.row().classes("gap-4 items-end mb-2"):
        pos_filter = ui.select(
            {p: p for p in _PORTAL_POSITIONS},
            value="All", label="Position Filter",
        ).classes("w-40")
        ovr_filter = ui.number(
            "Min Overall", value=0, min=0, max=99, step=1,
        ).classes("w-32")

    # Container that re-renders the player table when filters change
    table_container = ui.column().classes("w-full")

    def _apply_filters():
        filtered = entries
        pv = pos_filter.value
        ov = ovr_filter.value or 0
        if pv and pv != "All":
            filtered = [e for e in filtered if e.get("position", "") == pv]
        if ov > 0:
            filtered = [e for e in filtered if e.get("overall", 0) >= ov]
        return filtered

    def _rebuild_table():
        table_container.clear()
        filtered = _apply_filters()
        with table_container:
            if not filtered:
                ui.label("No available portal players matching your filters.").classes(
                    "text-sm text-gray-400 italic"
                )
                return

            rows = []
            for e in filtered:
                reason = e.get("reason", "").replace("_", " ").title()
                rows.append({
                    "Name": e.get("name", ""),
                    "Pos": e.get("position", ""),
                    "OVR": e.get("overall", 0),
                    "Year": e.get("year", ""),
                    "From": e.get("origin_team", ""),
                    "Reason": reason,
                    "Stars": e.get("potential", 0),
                })
            stat_table(rows)

            if remaining > 0:
                ui.label("Commit a Player").classes("font-bold text-slate-700 mt-4")
                player_options = {
                    i: f"{e.get('name', '')} ({e.get('position', '')}, OVR {e.get('overall', 0)}) — from {e.get('origin_team', '')}"
                    for i, e in enumerate(filtered)
                }
                sel = ui.select(player_options, value=0, label="Select Player").classes("w-full max-w-lg")

                async def _commit_player():
                    idx = sel.value
                    if idx is None:
                        return
                    selected = filtered[idx]
                    global_idx = selected.get("global_index", -1)
                    if global_idx < 0:
                        notify_error("Cannot interact with this player — try refreshing.")
                        return
                    team_name = portal_resp.get("human_team", "")
                    if not team_name:
                        notify_error("Could not determine your team name.")
                        return
                    try:
                        result = await run.io_bound(
                            api_client.season_portal_commit,
                            state.session_id,
                            team_name=team_name,
                            entry_index=global_idx,
                        )
                        pname = result.get("player", {}).get("name", selected.get("name", ""))
                        slots = result.get("transfers_remaining", 0)
                        notify_success(f"Committed {pname}! ({slots} slots remaining)")
                        refresh_fn.refresh()
                    except api_client.APIError as e:
                        notify_error(f"Commit failed: {e.detail}")

                ui.button(
                    "Commit Selected Player", on_click=_commit_player, icon="person_add",
                ).props("color=primary").classes("mt-2")
            else:
                ui.label("You've used all your transfer slots.").classes(
                    "text-sm text-amber-600 italic mt-2"
                )

    pos_filter.on_value_change(lambda _: _rebuild_table())
    ovr_filter.on_value_change(lambda _: _rebuild_table())
    _rebuild_table()

    # ── Action buttons ───────────────────────────────────────────────
    ui.separator().classes("my-4")
    with ui.row().classes("gap-4"):
        async def _done_portal():
            try:
                await run.io_bound(api_client.season_portal_skip, state.session_id)
                notify_success("Portal complete — starting regular season!")
                refresh_fn.refresh()
            except api_client.APIError as e:
                notify_error(f"Could not advance: {e.detail}")

        async def _skip_portal():
            try:
                await run.io_bound(api_client.season_portal_skip, state.session_id)
                notify_info("Portal skipped.")
                refresh_fn.refresh()
            except api_client.APIError as e:
                notify_error(f"Could not skip: {e.detail}")

        ui.button(
            "Done with Portal — Start Season", on_click=_done_portal, icon="sports_football",
        ).props("color=primary")
        ui.button("Skip Portal", on_click=_skip_portal, icon="skip_next")


async def _render_season_play(state: UserState, shared: dict):
    """Render the active season simulation UI."""
    if not state.session_id:
        ui.label("No active session.").classes("text-gray-400 italic")
        return

    try:
        status = await run.io_bound(api_client.get_season_status, state.session_id)
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
    async def _season_actions():
        try:
            status = await run.io_bound(api_client.get_season_status, state.session_id)
        except api_client.APIError:
            return

        phase = status.get("phase", "regular")
        current_week = status.get("current_week", 0)
        total_weeks = status.get("total_weeks", 10)

        if phase == "portal":
            await _render_season_portal(state, _season_actions)

        elif phase == "regular":
            with ui.row().classes("gap-4"):
                async def _sim_week():
                    try:
                        result = await run.io_bound(api_client.simulate_week, state.session_id)
                        week = result.get("week", current_week + 1)
                        notify_success(f"Week {week} simulated!")
                        _season_actions.refresh()
                    except api_client.APIError as e:
                        notify_error(f"Simulation failed: {e.detail}")

                async def _sim_rest():
                    try:
                        await run.io_bound(api_client.simulate_rest, state.session_id)
                        notify_success("Regular season complete!")
                        _season_actions.refresh()
                    except api_client.APIError as e:
                        notify_error(f"Simulation failed: {e.detail}")

                ui.button(f"Simulate Week {current_week + 1}", on_click=_sim_week, icon="play_arrow").props("color=primary")
                ui.button("Sim Rest of Season", on_click=_sim_rest, icon="fast_forward")

        elif phase == "playoffs_pending":
            async def _run_playoffs():
                try:
                    await run.io_bound(api_client.run_playoffs, state.session_id)
                    notify_success("Playoffs complete!")
                    _season_actions.refresh()
                except api_client.APIError as e:
                    notify_error(f"Playoffs failed: {e.detail}")

            ui.button("Run Playoffs", on_click=_run_playoffs, icon="emoji_events").props("color=primary")

        elif phase == "bowls_pending":
            async def _run_bowls():
                try:
                    await run.io_bound(api_client.run_bowls, state.session_id)
                    notify_success("Bowl games complete!")
                    _season_actions.refresh()
                except api_client.APIError as e:
                    notify_error(f"Bowls failed: {e.detail}")

            ui.button("Run Bowl Games", on_click=_run_bowls, icon="stadium").props("color=primary")

        elif phase == "complete":
            with ui.card().classes("w-full bg-green-50 p-4 rounded"):
                ui.label("Season Complete!").classes("font-bold text-green-700")
                ui.label("Check the League tab for final standings and awards.").classes("text-sm text-green-600")

        # Show full schedule (completed + upcoming)
        try:
            schedule = await run.io_bound(api_client.get_schedule, state.session_id)
            all_games = schedule.get("games", [])
            if all_games:
                completed = [g for g in all_games if g.get("completed")]
                upcoming = [g for g in all_games if not g.get("completed")]

                if completed:
                    recent = completed[-min(10, len(completed)):]
                    with ui.expansion(
                        f"Recent Results ({len(completed)} games played)",
                        icon="history",
                    ).classes("w-full mt-4"):
                        rows = []
                        for g in reversed(recent):
                            rows.append({
                                "Week": g.get("week", ""),
                                "Home": g.get("home_team", ""),
                                "Score": f"{fmt_vb_score(g.get('home_score', 0))} - {fmt_vb_score(g.get('away_score', 0))}",
                                "Away": g.get("away_team", ""),
                            })
                        stat_table(rows)

                if upcoming:
                    with ui.expansion(
                        f"Upcoming Games ({len(upcoming)} remaining)",
                        icon="event",
                    ).classes("w-full mt-2"):
                        rows = []
                        for g in upcoming[:30]:
                            rows.append({
                                "Week": g.get("week", ""),
                                "Home": g.get("home_team", ""),
                                "Away": g.get("away_team", ""),
                                "Conf": "Yes" if g.get("is_conference_game") else "",
                            })
                        stat_table(rows)
        except api_client.APIError:
            pass

    with results_container:
        await _season_actions()


async def _render_dynasty_play(state: UserState, shared: dict):
    """Render the active dynasty simulation UI."""
    if not state.session_id:
        ui.label("No active session.").classes("text-gray-400 italic")
        return

    try:
        dyn_status = await run.io_bound(api_client.get_dynasty_status, state.session_id)
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
    async def _dynasty_actions():
        try:
            dyn_status = await run.io_bound(api_client.get_dynasty_status, state.session_id)
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

            async def _start_season():
                try:
                    await run.io_bound(
                        api_client.dynasty_start_season,
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
            await _render_season_play(state, shared)

    with results_container:
        await _dynasty_actions()
