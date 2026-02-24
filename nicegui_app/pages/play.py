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
from nicegui_app.pages.postseason import render_playoff_bracket, render_bowl_games
from nicegui_app.pages.game_simulator import render_game_simulator
from nicegui_app.pages.season_simulator import render_season_simulator
from nicegui_app.pages.dynasty_mode import render_dynasty_mode
from nicegui_app.pages.dq_mode import render_dq_setup, render_dq_play


def render_play_section_sync(state: UserState, shared: dict):
    """Synchronous entry point — used for initial page render in NiceGUI 3.x."""
    if state.mode in ("dynasty", "season", "dq"):
        ui.label("Loading session...").classes("text-slate-400")
        ui.timer(0.1, lambda: _deferred_play_load(state, shared), once=True)
    else:
        _render_mode_selection(state, shared)


async def _deferred_play_load(state: UserState, shared: dict):
    """Load active session content asynchronously after page render."""
    try:
        if state.mode == "dynasty":
            await _render_dynasty_play(state, shared)
        elif state.mode == "season":
            await _render_season_play(state, shared)
        elif state.mode == "dq":
            await render_dq_play(state, shared)
    except Exception as exc:
        ui.label(f"Error: {exc}").classes("text-red-500")


async def render_play_section(state: UserState, shared: dict):
    """Async entry point — used when switching tabs via nav buttons."""
    if state.mode == "dynasty":
        await _render_dynasty_play(state, shared)
    elif state.mode == "season":
        await _render_season_play(state, shared)
    elif state.mode == "dq":
        await render_dq_play(state, shared)
    else:
        _render_mode_selection(state, shared)


def _render_mode_selection(state: UserState, shared: dict):
    """Show mode selection tabs when no active session."""
    ui.label("Play").classes("text-2xl font-bold text-slate-800")
    ui.label("Start a new dynasty, season, or play a quick exhibition game").classes("text-sm text-gray-500 mb-4")

    with ui.tabs().classes("w-full") as mode_tabs:
        dynasty_tab = ui.tab("New Dynasty")
        season_tab = ui.tab("New Season")
        quick_tab = ui.tab("Quick Game")
        dq_tab = ui.tab("DraftyQueenz")

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

        with ui.tab_panel(dq_tab):
            try:
                render_dq_setup(state, shared)
            except Exception as e:
                ui.label(f"Error loading DraftyQueenz: {e}").classes("text-red-500")


_PORTAL_POSITIONS = ["All", "VP", "HB", "WB", "SB", "ZB", "LB", "CB", "LA", "LM"]

_ROLE_LABELS = {
    "head_coach": "Head Coach",
    "oc": "Off. Coordinator",
    "dc": "Def. Coordinator",
    "stc": "Special Teams",
}


async def _render_coaching_selection(state: UserState, refresh_fn):
    """Coaching staff selection — shown during the portal phase.

    Users can view their current staff, generate a pool of candidates,
    and hire replacements for HC, OC, DC, or STC before the season starts.
    """
    ui.label("Coaching Staff").classes("text-xl font-bold text-slate-700 mt-2")
    ui.label(
        "Review your coaching staff and optionally hire new coaches before the season."
    ).classes("text-sm text-gray-500 mb-2")

    # ── Current staff ────────────────────────────────────────────────
    try:
        staff_resp = await run.io_bound(
            api_client.season_coaching_staff_get, state.session_id,
        )
    except api_client.APIError as e:
        notify_error(f"Could not load coaching staff: {e.detail}")
        return

    staff = staff_resp.get("staff", {})
    team_name = staff_resp.get("team", "")
    dev_aura_pct = staff_resp.get("dev_aura_max_boost_pct", 0)

    with ui.row().classes("w-full gap-3 flex-wrap mb-2"):
        metric_card("Team", team_name)
        metric_card("Dev Aura", f"+{dev_aura_pct}%")

    staff_rows = []
    for role_key, label in _ROLE_LABELS.items():
        coach = staff.get(role_key)
        if coach:
            staff_rows.append({
                "Role": label,
                "Name": coach.get("name", "—"),
                "OVR": coach.get("visible_score", ""),
                "Style": coach.get("classification_label", ""),
                "Stars": coach.get("star_rating", ""),
                "LDR": coach.get("leadership", ""),
                "DEV": coach.get("development", ""),
                "REC": coach.get("recruiting", ""),
            })
        else:
            staff_rows.append({
                "Role": label, "Name": "— Vacant —",
                "OVR": "", "Style": "", "Stars": "",
                "LDR": "", "DEV": "", "REC": "",
            })
    stat_table(staff_rows)

    # ── Pool generation & hiring ─────────────────────────────────────
    pool_container = ui.column().classes("w-full")

    async def _generate_pool():
        try:
            pool_resp = await run.io_bound(
                api_client.season_coaching_pool_generate, state.session_id,
            )
            pool = pool_resp.get("pool", [])
            _show_pool(pool)
        except api_client.APIError as e:
            notify_error(f"Could not generate pool: {e.detail}")

    def _show_pool(pool: list):
        pool_container.clear()
        with pool_container:
            if not pool:
                ui.label("No candidates available.").classes(
                    "text-sm text-gray-400 italic"
                )
                return

            for role_key, label in _ROLE_LABELS.items():
                candidates = [c for c in pool if c.get("role") == role_key]
                if not candidates:
                    continue

                with ui.expansion(
                    f"{label} Candidates ({len(candidates)})",
                    icon="person_search",
                ).classes("w-full mt-2"):
                    rows = []
                    for c in candidates:
                        rows.append({
                            "Name": c.get("name", ""),
                            "OVR": c.get("visible_score", ""),
                            "Style": c.get("classification_label", ""),
                            "Stars": c.get("star_rating", ""),
                            "LDR": c.get("leadership", ""),
                            "CMP": c.get("composure", ""),
                            "DEV": c.get("development", ""),
                            "REC": c.get("recruiting", ""),
                        })
                    stat_table(rows)

                    hire_options = {
                        i: f"{c.get('name', '')} (OVR {c.get('visible_score', '?')}, {c.get('classification_label', '')})"
                        for i, c in enumerate(candidates)
                    }
                    sel = ui.select(
                        hire_options, value=0, label="Select Coach to Hire",
                    ).classes("w-full max-w-lg")

                    async def _hire(sel=sel, candidates=candidates, role_key=role_key):
                        idx = sel.value
                        if idx is None:
                            return
                        coach = candidates[idx]
                        cid = coach.get("coach_id", "")
                        if not cid:
                            notify_error("Missing coach ID.")
                            return
                        try:
                            result = await run.io_bound(
                                api_client.season_coaching_hire,
                                state.session_id,
                                coach_id=cid,
                                role=role_key,
                            )
                            hired_name = result.get("coach", {}).get("name", "")
                            notify_success(f"Hired {hired_name} as {_ROLE_LABELS.get(role_key, role_key)}!")
                            refresh_fn.refresh()
                        except api_client.APIError as e:
                            notify_error(f"Hire failed: {e.detail}")

                    ui.button(
                        f"Hire as {label}", on_click=_hire, icon="how_to_reg",
                    ).props("color=primary").classes("mt-2")

    ui.button(
        "Browse Available Coaches", on_click=_generate_pool, icon="group_add",
    ).classes("mt-2")


async def _render_season_portal(state: UserState, refresh_fn):
    """Render the transfer portal UI for season mode.

    Lets the human player browse available transfers, commit players to
    their roster, and advance past the portal phase to start the regular
    season.
    """
    ui.label("Pre-Season Portal").classes("text-xl font-bold text-slate-700 mt-2")
    ui.label(
        "Pick transfer players and coaching staff, then start the season when ready."
    ).classes("text-sm text-gray-500 mb-2")

    # ── Prominent Start Season bar at top ─────────────────────────
    async def _start_season():
        try:
            await run.io_bound(api_client.season_portal_skip, state.session_id)
            notify_success("Portal complete — starting regular season!")
            refresh_fn.refresh()
        except api_client.APIError as e:
            notify_error(f"Could not advance: {e.detail}")

    with ui.card().classes("w-full bg-green-50 p-4 rounded mb-4"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("When you're done picking transfers and coaches:").classes("text-green-800")
            ui.button(
                "Start Season", on_click=_start_season, icon="sports_football",
            ).props("color=primary size=lg")

    ui.label("Transfer Portal").classes("text-lg font-semibold text-slate-700 mt-2")

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

    # ── Coaching Staff Selection ─────────────────────────────────────
    ui.separator().classes("my-4")
    await _render_coaching_selection(state, refresh_fn)

    # ── Bottom Start Season button (mirrors the top one) ────────────
    ui.separator().classes("my-4")
    with ui.card().classes("w-full bg-green-50 p-4 rounded"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Ready to play? Start the regular season.").classes("text-green-800")
            ui.button(
                "Start Season", on_click=_start_season, icon="sports_football",
            ).props("color=primary size=lg")


async def _fetch_bracket(session_id: str) -> dict:
    try:
        return await run.io_bound(api_client.get_playoff_bracket, session_id)
    except api_client.APIError:
        return {}


async def _fetch_bowls(session_id: str) -> dict:
    try:
        return await run.io_bound(api_client.get_bowl_results, session_id)
    except api_client.APIError:
        return {}


async def _render_season_play(state: UserState, shared: dict):
    """Render the active season simulation UI."""
    if not state.session_id:
        ui.label("No active session.").classes("text-gray-400 italic")
        return

    try:
        status = await run.io_bound(api_client.get_season_status, state.session_id)
    except api_client.APIError:
        state.clear_session()
        notify_info("Previous session expired. Please start a new one.")
        _render_mode_selection(state, shared)
        return

    season_name = status.get("name", "Season")
    ui.label(f"{season_name}").classes("text-2xl font-bold text-slate-800")

    @ui.refreshable
    async def _season_actions():
        try:
            status = await run.io_bound(api_client.get_season_status, state.session_id)
        except api_client.APIError:
            return

        phase = status.get("phase", "regular")
        current_week = status.get("current_week", 0)
        total_weeks = status.get("total_weeks", 10)

        next_week = status.get("next_week")
        games_played = status.get("games_played", 0)
        total_games = status.get("total_games", 0)

        with ui.row().classes("w-full gap-3 flex-wrap mb-4"):
            metric_card("Week", f"{current_week}/{total_weeks}")
            metric_card("Phase", phase.replace("_", " ").title())
            if phase == "regular" and total_games > 0:
                metric_card("Games", f"{games_played}/{total_games}")

        if phase == "portal":
            await _render_season_portal(state, _season_actions)

        elif phase == "regular":
            ui.separator().classes("my-4")

            week_label = f"Simulate Week {next_week}" if next_week else "Season Complete"
            with ui.row().classes("gap-3 items-center"):
                week_btn = ui.button(week_label, icon="play_arrow").props("color=primary")
                rest_btn = ui.button("Sim Rest of Season", icon="fast_forward").props("color=secondary outlined")

            async def _sim_week():
                week_btn.disable()
                rest_btn.disable()
                week_btn.text = "Simulating..."
                try:
                    result = await run.io_bound(api_client.simulate_week, state.session_id)
                    week = result.get("week", "?")
                    games_count = result.get("games_count", 0)
                    notify_success(f"Week {week} simulated — {games_count} games")
                    try:
                        _season_actions.refresh()
                    except RuntimeError:
                        pass
                except api_client.APIError as e:
                    notify_error(f"Simulation failed: {e.detail}")
                    week_btn.enable()
                    rest_btn.enable()
                    week_btn.text = week_label

            async def _sim_rest():
                rest_btn.disable()
                week_btn.disable()
                rest_btn.text = "Simulating season..."
                try:
                    result = await run.io_bound(api_client.simulate_rest, state.session_id)
                    notify_success("Regular season complete!")
                    try:
                        _season_actions.refresh()
                    except RuntimeError:
                        pass
                except api_client.APIError as e:
                    notify_error(f"Simulation failed: {e.detail}")
                    rest_btn.enable()
                    week_btn.enable()
                    rest_btn.text = "Sim Rest of Season"

            week_btn.on_click(_sim_week)
            rest_btn.on_click(_sim_rest)

        elif phase == "playoffs_pending":
            bracket_data = await _fetch_bracket(state.session_id)
            if bracket_data.get("bracket"):
                render_playoff_bracket(bracket_data, user_team=state.human_teams[0] if state.human_teams else None)

            playoff_btn = ui.button("Run Playoffs", icon="emoji_events").props("color=primary")

            async def _run_playoffs():
                playoff_btn.disable()
                playoff_btn.text = "Running playoffs..."
                try:
                    await run.io_bound(api_client.run_playoffs, state.session_id)
                    notify_success("Playoffs complete!")
                    try:
                        _season_actions.refresh()
                    except RuntimeError:
                        pass
                except api_client.APIError as e:
                    notify_error(f"Playoffs failed: {e.detail}")
                    playoff_btn.enable()
                    playoff_btn.text = "Run Playoffs"

            playoff_btn.on_click(_run_playoffs)

        elif phase == "bowls_pending":
            bracket_data = await _fetch_bracket(state.session_id)
            user_t = state.human_teams[0] if state.human_teams else None
            render_playoff_bracket(bracket_data, user_team=user_t)

            bowls_data = await _fetch_bowls(state.session_id)
            if bowls_data.get("bowl_results"):
                render_bowl_games(bowls_data, user_team=user_t, show_results=False)

            bowl_btn = ui.button("Run Bowl Games", icon="stadium").props("color=primary")

            async def _run_bowls():
                bowl_btn.disable()
                bowl_btn.text = "Running bowls..."
                try:
                    await run.io_bound(api_client.run_bowls, state.session_id)
                    notify_success("Bowl games complete!")
                    try:
                        _season_actions.refresh()
                    except RuntimeError:
                        pass
                except api_client.APIError as e:
                    notify_error(f"Bowls failed: {e.detail}")
                    bowl_btn.enable()
                    bowl_btn.text = "Run Bowl Games"

            bowl_btn.on_click(_run_bowls)

        elif phase in ("playoffs_complete", "bowls_complete", "complete"):
            user_t = state.human_teams[0] if state.human_teams else None
            bracket_data = await _fetch_bracket(state.session_id)
            render_playoff_bracket(bracket_data, user_team=user_t)

            bowls_data = await _fetch_bowls(state.session_id)
            if bowls_data.get("bowl_results"):
                ui.separator().classes("my-3")
                render_bowl_games(bowls_data, user_team=user_t)

            with ui.card().classes("w-full bg-green-50 p-3 rounded mt-3"):
                ui.label("Season Complete! Check the League tab for full standings and awards.").classes("text-sm text-green-600")

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

    await _season_actions()


async def _render_dynasty_play(state: UserState, shared: dict):
    """Render the active dynasty simulation UI."""
    if not state.session_id:
        ui.label("No active session.").classes("text-gray-400 italic")
        return

    try:
        dyn_status = await run.io_bound(api_client.get_dynasty_status, state.session_id)
    except api_client.APIError:
        state.clear_session()
        notify_info("Previous session expired. Please start a new one.")
        _render_mode_selection(state, shared)
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

            start_btn = ui.button("Start Season", icon="play_arrow").props("color=primary").classes("mt-2")

            async def _start_season():
                start_btn.disable()
                start_btn.text = "Starting season..."
                try:
                    await run.io_bound(
                        api_client.dynasty_start_season,
                        state.session_id,
                        offense_style=off_sel.value,
                        defense_style=def_sel.value,
                        st_scheme=st_sel.value,
                    )
                    notify_success("Season started!")
                    try:
                        _dynasty_actions.refresh()
                    except RuntimeError:
                        pass
                except api_client.APIError as e:
                    notify_error(f"Failed to start season: {e.detail}")
                    start_btn.enable()
                    start_btn.text = "Start Season"

            start_btn.on_click(_start_season)

        else:
            # Season is active — show simulation controls
            await _render_season_play(state, shared)

    with results_container:
        await _dynasty_actions()
