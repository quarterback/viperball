"""Season Simulator setup page — NiceGUI version.

Migrated from ui/page_modules/season_simulator.py and the _render_new_season
portion of section_play.py. Handles season creation with team selection,
conference configuration, and AI coaching assignment.
"""

from __future__ import annotations

import os
import random

from nicegui import ui

from engine.season import load_teams_from_directory
from engine.conference_names import generate_conference_names
from engine.geography import get_geographic_conference_defaults
from engine.ai_coach import load_team_identity
from ui import api_client
from nicegui_app.state import UserState
from nicegui_app.helpers import OFFENSE_TOOLTIPS, DEFENSE_TOOLTIPS
from nicegui_app.components import metric_card, notify_error, notify_success, notify_info


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
TEAMS_DIR = os.path.join(DATA_DIR, "teams")


def render_season_simulator(state: UserState, shared: dict):
    """Render the season setup UI."""
    teams = shared["teams"]
    styles = shared["styles"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]
    st_schemes = shared.get("st_schemes", {})
    st_scheme_keys = shared.get("st_scheme_keys", [])

    ui.label("Season Simulator").classes("text-2xl font-bold text-slate-800")
    ui.label("Simulate a full round-robin season with standings, metrics, and playoffs").classes("text-sm text-gray-500 mb-4")

    all_teams = load_teams_from_directory(TEAMS_DIR)
    all_team_names = sorted(all_teams.keys())
    team_identities = load_team_identity(TEAMS_DIR)

    if len(all_team_names) < 2:
        ui.label("Not enough teams loaded to run a season.").classes("text-yellow-600")
        return

    # Count conferences
    conf_set = sorted(set(
        team_identities.get(t, {}).get("conference", "Independent")
        for t in all_team_names
    ))

    # ── Season Setup Form ──
    ui.label("Season Setup").classes("text-lg font-semibold text-slate-700 mt-2")

    season_name = ui.input("Season Name", value="2026 CVL Season").classes("w-96")

    # ── Human team selection with conference browsing ──
    ui.label("Your Teams (human-coached, up to 4)").classes("font-semibold text-slate-600 mt-4")
    ui.label(f"{len(all_team_names)} teams across {len(conf_set)} conferences").classes("text-sm text-gray-500")

    # Browse mode
    browse_mode = ui.radio(
        {"conference": "Conference", "all": "All Teams (A-Z)"},
        value="conference",
    ).props("inline").classes("mt-1")

    # Conference selector for browse
    conf_browse_select = ui.select(
        {c: c for c in conf_set},
        value=conf_set[0] if conf_set else None,
        label="Select Conference",
    ).classes("w-64")

    # Track selected human teams
    _human_teams: list[str] = []

    # Team add controls
    team_add_container = ui.column().classes("w-full")

    @ui.refreshable
    def _render_team_add():
        mode = browse_mode.value
        if mode == "conference":
            conf = conf_browse_select.value
            if conf:
                available = [t for t in all_team_names
                             if team_identities.get(t, {}).get("conference", "Independent") == conf
                             and t not in _human_teams]
            else:
                available = [t for t in all_team_names if t not in _human_teams]
        else:
            available = [t for t in all_team_names if t not in _human_teams]

        # Build enriched labels
        opts = {}
        for t in sorted(available):
            ident = team_identities.get(t, {})
            conf = ident.get("conference", "")
            label = f"{t} ({conf})" if conf else t
            opts[t] = label

        with ui.row().classes("w-full gap-4 items-end"):
            add_select = ui.select(
                opts,
                label=f"Add team ({len(available)} available)",
                value=list(opts.keys())[0] if opts else None,
            ).classes("flex-1")

            def _add_team():
                if add_select.value and add_select.value not in _human_teams:
                    if len(_human_teams) >= 4:
                        notify_error("Maximum 4 human-coached teams")
                        return
                    _human_teams.append(add_select.value)
                    _render_team_add.refresh()
                    _render_human_config.refresh()

            ui.button("Add", on_click=_add_team, icon="add").props("color=primary")

        # Show current selections
        if _human_teams:
            ui.label("Selected teams:").classes("text-sm font-semibold text-slate-600 mt-2")
            for t in list(_human_teams):
                with ui.row().classes("items-center gap-2"):
                    ident = team_identities.get(t, {})
                    mascot = ident.get("mascot", "")
                    conf = ident.get("conference", "")
                    info = f" — {mascot} ({conf})" if mascot else f" ({conf})" if conf else ""
                    ui.label(f"{t}{info}").classes("text-sm")

                    def _make_remove(team_name):
                        def _remove():
                            _human_teams.remove(team_name)
                            _render_team_add.refresh()
                            _render_human_config.refresh()
                        return _remove
                    ui.button(icon="close", on_click=_make_remove(t)).props("flat round dense size=xs color=red")

    browse_mode.on_value_change(lambda _: _render_team_add.refresh())
    conf_browse_select.on_value_change(lambda _: _render_team_add.refresh())

    with team_add_container:
        _render_team_add()

    # AI Seed
    with ui.row().classes("gap-4 items-end mt-4"):
        ai_seed = ui.number("AI Coaching Seed (0 = random)", value=0, min=0, max=999999).classes("w-64")

        def _reroll():
            ai_seed.set_value(random.randint(1, 999999))

        ui.button("Re-roll AI", on_click=_reroll, icon="casino")

    # Human team style config
    style_options = {k: styles[k]["label"] for k in style_keys}
    def_options = {k: defense_styles[k]["label"] for k in defense_style_keys}
    st_options = {k: st_schemes[k]["label"] for k in st_scheme_keys} if st_scheme_keys else {"aces": "Aces"}

    # Track style selections per human team
    _style_selects: dict = {}

    style_container = ui.column().classes("w-full mt-4")

    @ui.refreshable
    def _render_human_config():
        _style_selects.clear()
        if not _human_teams:
            return

        ui.label("Your Team Configuration").classes("text-lg font-semibold text-slate-700")
        for tname in _human_teams[:4]:  # max 4
            identity = team_identities.get(tname, {})
            mascot = identity.get("mascot", "")
            conf = identity.get("conference", "")

            with ui.card().classes("w-full p-4 mb-2"):
                ui.label(f"{tname}").classes("font-bold text-slate-800")
                if mascot or conf:
                    ui.label(f"{mascot} | {conf}").classes("text-sm text-gray-500")

                with ui.row().classes("gap-4"):
                    off_sel = ui.select(style_options, value="balanced", label="Offense").classes("w-48")
                    def_sel = ui.select(def_options, value="swarm", label="Defense").classes("w-48")
                    st_sel = ui.select(st_options, value="aces", label="Special Teams").classes("w-48")
                    _style_selects[tname] = {"off": off_sel, "def": def_sel, "st": st_sel}

    with style_container:
        _render_human_config()

    # ── Conference setup ──
    ui.separator().classes("my-4")
    ui.label("Conference Setup").classes("text-lg font-semibold text-slate-700")

    # Load stock conferences from team files
    from engine.geography import read_conferences_from_team_files
    stock_conferences = read_conferences_from_team_files(TEAMS_DIR, all_team_names) or {}
    # Track editable conference assignments (team → conference name)
    _conf_assignments: dict[str, str] = {}
    for conf_name, members in stock_conferences.items():
        for t in members:
            _conf_assignments[t] = conf_name
    # Fill in unassigned teams
    for t in all_team_names:
        if t not in _conf_assignments:
            _conf_assignments[t] = "Independent"

    conf_container = ui.column().classes("w-full")

    @ui.refreshable
    def _render_conferences():
        # Build conference → team list from current assignments
        conf_map: dict[str, list[str]] = {}
        for t, c in sorted(_conf_assignments.items()):
            conf_map.setdefault(c, []).append(t)

        ui.label(f"{len(conf_map)} conferences, {len(all_team_names)} teams").classes("text-sm text-gray-500")

        with ui.expansion("View / Edit Conferences", icon="groups").classes("w-full"):
            for conf_name in sorted(conf_map.keys()):
                members = sorted(conf_map[conf_name])
                with ui.expansion(f"{conf_name} ({len(members)} teams)").classes("w-full"):
                    for t in members:
                        with ui.row().classes("items-center gap-2"):
                            ui.label(t).classes("text-sm flex-1")
                            # Reassign dropdown
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

    # ── Schedule configuration ──
    total_teams = len(all_team_names)
    REGULAR_SEASON_GAMES = 13

    ui.separator().classes("my-4")
    with ui.row().classes("w-full gap-8"):
        with ui.column().classes("flex-1"):
            ui.label("Regular Season").classes("text-sm text-slate-600")
            ui.label(f"{REGULAR_SEASON_GAMES} games per team").classes("text-lg font-semibold text-slate-700")

        with ui.column().classes("flex-1"):
            ui.label("Playoff Format").classes("text-sm text-slate-600")
            playoff_options = [p for p in [4, 8, 12, 16, 24, 32] if p <= total_teams]
            if not playoff_options:
                playoff_options = [total_teams]
            playoff_opts = {str(p): str(p) for p in playoff_options}
            playoff_format = ui.radio(playoff_opts, value=str(playoff_options[0])).props("inline")

    with ui.column().classes("w-full mt-2"):
        ui.label("Number of Bowl Games").classes("text-sm text-slate-600")
        max_bowls = min(12, (total_teams - int(playoff_options[0])) // 2)
        bowl_count = ui.slider(min=0, max=max(max_bowls, 1), value=min(4, max(max_bowls, 0))).classes("w-96")
        bowl_label = ui.label("4 bowls").classes("text-sm font-semibold text-slate-700")

        def _update_bowl_label():
            bowl_label.set_text(f"{int(bowl_count.value)} bowls")
        bowl_count.on_value_change(lambda _: _update_bowl_label())

    # ── League History ──
    ui.separator().classes("my-4")
    ui.label("League History").classes("text-lg font-semibold text-slate-700")
    ui.label("Generate pre-existing seasons so the league has history.").classes("text-sm text-gray-500")

    with ui.row().classes("gap-4 items-center"):
        ui.label("Years of History").classes("text-sm text-slate-600")
        history_years = ui.slider(min=0, max=100, value=0).classes("w-64")
        history_years_label = ui.label("0 years").classes("text-sm font-semibold text-slate-700 min-w-[60px]")

    def _update_history_label():
        v = int(history_years.value)
        history_years_label.set_text(f"{v} year{'s' if v != 1 else ''}")
    history_years.on_value_change(lambda _: _update_history_label())

    ui.separator().classes("my-4")

    # Create button
    async def _create_season():
        selected_humans = list(_human_teams)
        if len(selected_humans) > 4:
            notify_error("Maximum 4 human-coached teams")
            return

        # Ensure we have a session
        if not state.session_id:
            try:
                resp = api_client.create_session()
                state.session_id = resp["session_id"]
            except api_client.APIError as e:
                notify_error(f"Failed to create session: {e.detail}")
                return

        seed_val = int(ai_seed.value or 0)
        actual_seed = seed_val if seed_val > 0 else hash(season_name.value) % 999999

        # Build human configs from style selects
        human_configs = {}
        for tname, sels in _style_selects.items():
            human_configs[tname] = {
                "offense_style": sels["off"].value,
                "defense_style": sels["def"].value,
                "st_scheme": sels["st"].value,
            }

        # Build conferences dict from current assignments
        conf_dict: dict[str, list[str]] = {}
        for tname, cname in _conf_assignments.items():
            if cname and cname != "Independent":
                conf_dict.setdefault(cname, []).append(tname)

        create_btn.disable()
        create_btn.text = "Creating season..."
        import asyncio
        await asyncio.sleep(0.05)  # Let the UI update before blocking

        try:
            api_client.create_season(
                state.session_id,
                name=season_name.value,
                games_per_team=REGULAR_SEASON_GAMES,
                playoff_size=int(playoff_format.value),
                bowl_count=int(bowl_count.value),
                human_teams=selected_humans,
                human_configs=human_configs,
                num_conferences=len(conf_dict),
                conferences=conf_dict,
                ai_seed=actual_seed,
                history_years=int(history_years.value),
            )
            state.mode = "season"
            state.human_teams = selected_humans
            state.playoff_size = int(playoff_format.value)
            state.bowl_count = int(bowl_count.value)
            notify_success("Season created! Switch to the Play tab to start simulating.")
            ui.navigate.to("/")
        except api_client.APIError as e:
            notify_error(f"Failed to create season: {e.detail}")
        finally:
            create_btn.enable()
            create_btn.text = "Create Season"

    create_btn = ui.button("Create Season", on_click=_create_season, icon="sports_score").props("color=primary size=lg").classes("mt-2")
