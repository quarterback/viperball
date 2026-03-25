"""Dynasty Mode setup page — NiceGUI version.

Migrated from the _render_new_dynasty portion of section_play.py. Handles
dynasty creation with team selection, conference setup, program archetype,
and history generation.
"""

from __future__ import annotations

import os
import random

from nicegui import ui, run

from engine.season import load_teams_from_directory
from engine.conference_names import generate_conference_names
from engine.geography import get_geographic_conference_defaults, read_conferences_from_team_files
from engine.ai_coach import load_team_identity
from scripts.generate_rosters import PROGRAM_ARCHETYPES
from ui import api_client
from nicegui_app.state import UserState
from nicegui_app.helpers import OFFENSE_TOOLTIPS, DEFENSE_TOOLTIPS
from nicegui_app.components import metric_card, notify_error, notify_success


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
TEAMS_DIR = os.path.join(DATA_DIR, "teams")


async def _render_saved_dynasties(state: UserState, container):
    """Load saved dynasties asynchronously and render resume cards."""
    try:
        resp = await run.io_bound(api_client.list_saved_dynasties)
        dynasties = resp.get("dynasties", [])
    except api_client.APIError:
        dynasties = []
    except Exception:
        dynasties = []

    if not dynasties:
        return

    with container:
        ui.label("Saved Dynasties").classes("text-lg font-semibold text-slate-700 mt-2")

        for d in dynasties:
            save_key = d.get("save_key", "")
            label = d.get("label", "Dynasty")

            with ui.card().classes("w-full p-3 mb-2"):
                with ui.row().classes("w-full items-center justify-between"):
                    with ui.column().classes("gap-0"):
                        ui.label(label).classes("font-bold text-slate-700")
                        ui.label(f"Key: {save_key}").classes("text-xs text-slate-400")
                    with ui.row().classes("gap-2"):
                        async def _load(sk=save_key, lbl=label):
                            # Always create a fresh session so stale cookie
                            # session IDs don't cause load failures.
                            try:
                                resp = await run.io_bound(api_client.create_session)
                                state.session_id = resp["session_id"]
                            except api_client.APIError as e:
                                notify_error(f"Failed to create session: {e.detail}")
                                return
                            except Exception as e:
                                notify_error(f"Failed to create session: {e}")
                                return
                            try:
                                await run.io_bound(
                                    api_client.load_saved_dynasty, state.session_id, sk,
                                )
                                state.mode = "dynasty"
                                notify_success(f"Loaded dynasty: {lbl}")
                                ui.navigate.to("/")
                            except api_client.APIError as e:
                                notify_error(f"Failed to load dynasty: {e.detail}")
                            except Exception as e:
                                notify_error(f"Failed to load dynasty: {e}")

                        ui.button("Resume", on_click=_load, icon="play_arrow").props("color=primary size=sm")


def render_dynasty_mode(state: UserState, shared: dict):
    """Render the dynasty creation UI with load-from-database support."""
    teams = shared["teams"]

    ui.label("College Dynasty").classes("text-2xl font-bold text-slate-800")
    ui.label("Multi-season career mode with historical tracking, awards, and record books").classes("text-sm text-gray-500 mb-4")

    # ── Load Saved Dynasty (async to avoid deadlocking the shared event loop) ──
    saved_container = ui.column().classes("w-full")
    ui.timer(0.1, lambda: _render_saved_dynasties(state, saved_container), once=True)

    ui.separator().classes("my-4")
    ui.label("Create New Dynasty").classes("text-xl font-bold text-slate-700")

    # Cache heavy disk I/O in shared dict so it's only loaded once per session
    if "_all_teams" not in shared:
        shared["_all_teams"] = load_teams_from_directory(TEAMS_DIR)
    if "_team_identities" not in shared:
        shared["_team_identities"] = load_team_identity(TEAMS_DIR)
    all_teams = shared["_all_teams"]
    all_team_names_sorted = sorted(all_teams.keys())
    team_identities = shared["_team_identities"]

    # ── Dynasty Info ──
    with ui.row().classes("w-full gap-4"):
        dynasty_name = ui.input("Dynasty Name", value="My Viperball Dynasty").classes("flex-1")
        coach_name = ui.input("Coach Name", value="Coach").classes("flex-1")

    # ── Team Selection ──
    ui.label("Choose Your Team").classes("font-bold text-slate-700 mt-4")

    # Shared mutable ref so the _create_dynasty callback can read the selection
    _selected = {"team": all_team_names_sorted[0] if all_team_names_sorted else ""}

    # Conference filter + team picker
    conf_set = sorted(set(
        team_identities.get(t, {}).get("conference", "Independent")
        for t in all_team_names_sorted
    ))
    conf_filter_opts = {"all": "All Conferences"}
    for c in conf_set:
        conf_filter_opts[c] = c

    with ui.row().classes("w-full gap-4 items-end"):
        conf_filter = ui.select(conf_filter_opts, value="all", label="Filter by Conference").classes("w-64")

        # Build enriched team options: "Name (Conference) — Archetype [OVR]"
        def _build_team_options(conf_value):
            if conf_value == "all":
                names = all_team_names_sorted
            else:
                names = [t for t in all_team_names_sorted
                         if team_identities.get(t, {}).get("conference", "Independent") == conf_value]
            opts = {}
            for t in sorted(names):
                ident = team_identities.get(t, {})
                conf = ident.get("conference", "")
                label = f"{t} ({conf})" if conf else t
                opts[t] = label
            return opts

        initial_opts = _build_team_options("all")
        team_select = ui.select(
            initial_opts,
            label="Your Team",
            value=_selected["team"],
        ).classes("flex-1")

    # Keep _selected in sync
    def _on_team_change(e):
        if e.value:
            _selected["team"] = e.value
    team_select.on_value_change(_on_team_change)

    def _on_conf_filter_change(e):
        new_opts = _build_team_options(e.value)
        team_select.options = new_opts
        team_select.update()
        if new_opts and _selected["team"] not in new_opts:
            first_key = list(new_opts.keys())[0]
            team_select.set_value(first_key)
            _selected["team"] = first_key
    conf_filter.on_value_change(_on_conf_filter_change)

    # Show team info below
    team_info_label = ui.label("").classes("text-sm text-gray-500")

    def _update_team_info():
        t = _selected["team"]
        ident = team_identities.get(t, {})
        mascot = ident.get("mascot", "")
        conf = ident.get("conference", "")
        colors = ident.get("colors", [])
        parts = [p for p in [mascot, conf, " / ".join(colors[:2])] if p]
        team_info_label.set_text(" | ".join(parts) if parts else "")
    team_select.on_value_change(lambda _: _update_team_info())
    _update_team_info()

    start_year = ui.number("Starting Year", value=2026, min=1906, max=2050).classes("w-48 mt-2")

    # ── Program Archetype ──
    ui.separator().classes("my-4")
    ui.label("Program Archetype").classes("text-lg font-semibold text-slate-700")
    ui.label("Choose your starting program level. This determines roster talent and difficulty.").classes("text-sm text-gray-500")

    arch_keys = list(PROGRAM_ARCHETYPES.keys())
    arch_options = {k: PROGRAM_ARCHETYPES[k]["label"] for k in arch_keys}
    default_arch = "regional_power" if "regional_power" in arch_keys else arch_keys[0]

    arch_select = ui.radio(arch_options, value=default_arch).props("inline")

    arch_desc = ui.label("").classes("text-sm text-gray-500 italic mt-1")

    def _update_arch_desc():
        key = arch_select.value
        desc = PROGRAM_ARCHETYPES.get(key, {}).get("description", "")
        arch_desc.set_text(desc)

    arch_select.on_value_change(lambda _: _update_arch_desc())
    _update_arch_desc()

    # ── Conference Setup ──
    ui.separator().classes("my-4")
    ui.label("Conference Setup").classes("text-lg font-semibold text-slate-700")

    # Load stock conferences from team files
    stock_conferences = read_conferences_from_team_files(TEAMS_DIR, all_team_names_sorted) or {}

    # Track editable conference assignments (team → conference name)
    _conf_assignments: dict[str, str] = {}
    for conf_name, members in stock_conferences.items():
        for t in members:
            _conf_assignments[t] = conf_name
    for t in all_team_names_sorted:
        if t not in _conf_assignments:
            _conf_assignments[t] = "Independent"

    total_teams = len(all_team_names_sorted)
    num_stock = len(stock_conferences)
    ui.label(f"{num_stock} conferences, {total_teams} teams").classes("text-sm text-gray-500")

    conf_container = ui.column().classes("w-full")

    @ui.refreshable
    def _render_conferences():
        conf_map: dict[str, list[str]] = {}
        for t, c in sorted(_conf_assignments.items()):
            conf_map.setdefault(c, []).append(t)

        with ui.expansion("View / Edit Conferences", icon="groups").classes("w-full"):
            for conf_name in sorted(conf_map.keys()):
                members = sorted(conf_map[conf_name])
                with ui.expansion(f"{conf_name} ({len(members)} teams)").classes("w-full"):
                    for t in members:
                        with ui.row().classes("items-center gap-2"):
                            ui.label(t).classes("text-sm flex-1")
                            all_conf_names = sorted(set(_conf_assignments.values()))
                            conf_opts = {c: c for c in all_conf_names}

                            def _make_reassign(team_name):
                                def _reassign(e):
                                    _conf_assignments[team_name] = e.value
                                    _render_conferences.refresh()
                                return _reassign

                            ui.select(
                                conf_opts, value=conf_name,
                                on_change=_make_reassign(t),
                            ).classes("w-48").props("dense")

    with conf_container:
        _render_conferences()

    # ── League History ──
    ui.separator().classes("my-4")
    ui.label("League History").classes("text-lg font-semibold text-slate-700")
    ui.label("Generate past seasons so your dynasty has an established history with champions, records, and rivalries.").classes("text-sm text-gray-500")

    with ui.row().classes("gap-4 items-center"):
        ui.label("Years of History").classes("text-sm text-slate-600")
        history_years = ui.slider(min=0, max=100, value=0).classes("w-64")
        history_years_label = ui.label("0 years").classes("text-sm font-semibold text-slate-700 min-w-[60px]")
        ui.label("0 = start fresh. Higher values take longer.").classes("text-sm text-gray-400 self-center")

    def _update_history_label():
        v = int(history_years.value)
        history_years_label.set_text(f"{v} year{'s' if v != 1 else ''}")
    history_years.on_value_change(lambda _: _update_history_label())

    # ── Season Settings ──
    ui.separator().classes("my-4")
    ui.label("Season Settings").classes("text-lg font-semibold text-slate-700")
    ui.label("These settings apply to every season in your dynasty.").classes("text-sm text-gray-500")

    with ui.row().classes("gap-4 flex-wrap"):
        season_games_per = ui.number("Games per Team", value=12, min=6, max=16).classes("w-40")
        season_playoff_options = {p: f"{p} teams" for p in [4, 8, 12, 16, 24, 32] if p <= total_teams}
        season_playoff_default = 8 if 8 in season_playoff_options else next(iter(season_playoff_options))
        season_playoff_sz = ui.select(
            season_playoff_options, value=season_playoff_default, label="Playoff Size",
        ).classes("w-40")
        initial_max_bowls = min(16, max(0, (total_teams - season_playoff_default) // 2))
        season_bowl_ct = ui.number("Bowl Games", value=min(4, initial_max_bowls), min=0, max=initial_max_bowls).classes("w-32")

        def _update_bowl_max():
            ps = int(season_playoff_sz.value)
            new_max = min(16, max(0, (total_teams - ps) // 2))
            season_bowl_ct.max = new_max
            if season_bowl_ct.value > new_max:
                season_bowl_ct.value = new_max
            season_bowl_ct.update()

        season_playoff_sz.on_value_change(lambda _: _update_bowl_max())

    # ── Create Dynasty Button ──
    ui.separator().classes("my-4")

    creating_spinner = ui.spinner(size="lg").classes("hidden")

    async def _create_dynasty():
        selected_team = _selected["team"]
        if not selected_team:
            notify_error("Please select a team")
            return

        # Always create a fresh session for a new dynasty so stale cookie
        # session IDs (e.g. after server restart) don't cause silent failures.
        try:
            resp = await run.io_bound(api_client.create_session)
            state.session_id = resp["session_id"]
        except api_client.APIError as e:
            notify_error(f"Failed to create session: {e.detail}")
            return
        except Exception as e:
            notify_error(f"Failed to create session: {e}")
            return

        creating_spinner.classes(remove="hidden")

        # Build conferences dict from current assignments
        conf_dict: dict[str, list[str]] = {}
        for tname, cname in _conf_assignments.items():
            if cname and cname != "Independent":
                conf_dict.setdefault(cname, []).append(tname)

        try:
            await run.io_bound(
                api_client.create_dynasty,
                state.session_id,
                dynasty_name=dynasty_name.value,
                coach_name=coach_name.value,
                coach_team=selected_team,
                starting_year=int(start_year.value or 2026),
                num_conferences=len(conf_dict) or 18,
                conferences=conf_dict if conf_dict else None,
                history_years=int(history_years.value or 0),
                program_archetype=arch_select.value,
                games_per_team=int(season_games_per.value),
                playoff_size=int(season_playoff_sz.value),
                bowl_count=int(season_bowl_ct.value),
            )
            state.mode = "dynasty"
            state.dynasty_teams = [selected_team]
            notify_success("Dynasty created!")
            creating_spinner.classes(add="hidden")
            ui.navigate.to("/")
        except api_client.APIError as e:
            creating_spinner.classes(add="hidden")
            notify_error(f"Failed to create dynasty: {e.detail}")
        except Exception as e:
            creating_spinner.classes(add="hidden")
            notify_error(f"Failed to create dynasty: {e}")

    ui.button("Create Dynasty", on_click=_create_dynasty, icon="emoji_events").props("color=primary size=lg")
