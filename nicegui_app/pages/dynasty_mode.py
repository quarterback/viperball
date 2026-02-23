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
from engine.geography import get_geographic_conference_defaults
from engine.ai_coach import load_team_identity
from scripts.generate_rosters import PROGRAM_ARCHETYPES
from ui import api_client
from nicegui_app.state import UserState
from nicegui_app.helpers import OFFENSE_TOOLTIPS, DEFENSE_TOOLTIPS
from nicegui_app.components import metric_card, notify_error, notify_success


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
TEAMS_DIR = os.path.join(DATA_DIR, "teams")


def render_dynasty_mode(state: UserState, shared: dict):
    """Render the dynasty creation UI."""
    teams = shared["teams"]

    ui.label("Create New Dynasty").classes("text-2xl font-bold text-slate-800")
    ui.label("Multi-season career mode with historical tracking, awards, and record books").classes("text-sm text-gray-500 mb-4")

    all_teams = load_teams_from_directory(TEAMS_DIR)
    all_team_names_sorted = sorted(all_teams.keys())
    team_identities = load_team_identity(TEAMS_DIR)

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

    total_teams = len(all_team_names_sorted)
    max_conf = max(1, total_teams // 9)

    ui.label(f"Number of Conferences ({total_teams} teams available)").classes("text-sm text-slate-600")
    num_conferences = ui.slider(
        min=1, max=min(max_conf, 12), value=min(max_conf, 10), step=1,
    ).classes("w-96")

    teams_per_label = ui.label("").classes("text-sm text-gray-500")

    def _update_conf_label():
        n = int(num_conferences.value)
        per = total_teams // max(1, n)
        rem = total_teams % max(1, n)
        if rem == 0:
            teams_per_label.set_text(f"~{per} teams per conference")
        else:
            teams_per_label.set_text(f"~{per}-{per + 1} teams per conference")

    num_conferences.on_value_change(lambda _: _update_conf_label())
    _update_conf_label()

    # Conference name editing + geographic defaults
    _conf_state = {
        "seed": random.randint(0, 999999),
        "use_geo": True,
    }

    conf_names_container = ui.column().classes("w-full mt-2")

    # Track conference name inputs
    _conf_name_inputs: list = []

    @ui.refreshable
    def _render_conf_names():
        _conf_name_inputs.clear()
        n = int(num_conferences.value)

        # Generate names
        if _conf_state["use_geo"]:
            geo_clusters = get_geographic_conference_defaults(TEAMS_DIR, all_team_names_sorted, n)
            generated = list(geo_clusters.keys())
            if len(generated) < n:
                generated.extend(generate_conference_names(
                    count=n - len(generated), seed=_conf_state["seed"]
                ))
        else:
            generated = generate_conference_names(count=n, seed=_conf_state["seed"])

        # Pad if needed
        while len(generated) < n:
            generated.append(f"Conference {len(generated) + 1}")

        # "New Names" button
        with ui.row().classes("w-full justify-end"):
            def _regen():
                _conf_state["seed"] = random.randint(0, 999999)
                _conf_state["use_geo"] = False
                _render_conf_names.refresh()

            ui.button("New Names", on_click=_regen, icon="casino")

        # Editable conference name grid (4 per row)
        cols_per_row = min(n, 4)
        for row_start in range(0, n, cols_per_row):
            row_end = min(row_start + cols_per_row, n)
            with ui.row().classes("w-full gap-4"):
                for ci in range(row_start, row_end):
                    inp = ui.input(
                        f"Conference {ci + 1}",
                        value=generated[ci],
                    ).classes("flex-1")
                    _conf_name_inputs.append(inp)

    num_conferences.on_value_change(lambda _: _render_conf_names.refresh())

    with conf_names_container:
        _render_conf_names()

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

    # ── Create Dynasty Button ──
    ui.separator().classes("my-4")

    creating_spinner = ui.spinner(size="lg").classes("hidden")

    async def _create_dynasty():
        selected_team = _selected["team"]
        if not selected_team:
            notify_error("Please select a team")
            return

        if not state.session_id:
            try:
                resp = await run.io_bound(api_client.create_session)
                state.session_id = resp["session_id"]
            except api_client.APIError as e:
                notify_error(f"Failed to create session: {e.detail}")
                return

        creating_spinner.classes(remove="hidden")

        try:
            await run.io_bound(
                api_client.create_dynasty,
                state.session_id,
                dynasty_name=dynasty_name.value,
                coach_name=coach_name.value,
                coach_team=selected_team,
                starting_year=int(start_year.value),
                num_conferences=int(num_conferences.value),
                history_years=int(history_years.value),
                program_archetype=arch_select.value,
            )
            state.mode = "dynasty"
            state.dynasty_teams = [selected_team]
            notify_success("Dynasty created!")
            creating_spinner.classes(add="hidden")
            ui.navigate.to("/")
        except api_client.APIError as e:
            creating_spinner.classes(add="hidden")
            notify_error(f"Failed to create dynasty: {e.detail}")

    ui.button("Create Dynasty", on_click=_create_dynasty, icon="emoji_events").props("color=primary size=lg")
