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

    # ── Season Setup Form ──
    ui.label("Season Setup").classes("text-lg font-semibold text-slate-700 mt-2")

    season_name = ui.input("Season Name", value="2026 CVL Season").classes("w-96")

    # Human team selection
    ui.label("Your Teams (up to 4)").classes("font-semibold text-slate-600 mt-4")
    ui.label("Pick teams to coach yourself. Everyone else is AI-controlled.").classes("text-sm text-gray-500")

    human_select = ui.select(
        {name: name for name in all_team_names},
        label="Select teams",
        multiple=True,
    ).classes("w-full").props("use-chips")

    # AI Seed
    with ui.row().classes("gap-4 items-end mt-4"):
        ai_seed = ui.number("AI Coaching Seed (0 = random)", value=0, min=0, max=999999).classes("w-64")

        def _reroll():
            ai_seed.set_value(random.randint(1, 999999))

        ui.button("Re-roll AI", on_click=_reroll, icon="casino")

    # Conference setup
    ui.separator().classes("my-4")
    ui.label("Conference Setup").classes("text-lg font-semibold text-slate-700")

    total_teams = len(all_team_names)
    max_conf = max(1, total_teams // 9)

    ui.label(f"Number of Conferences ({total_teams} teams)").classes("text-sm text-slate-600")
    num_conferences = ui.slider(
        min=1, max=min(max_conf, 12), value=min(max_conf, 10), step=1,
    ).classes("w-96")

    # Human team style config
    style_options = {k: styles[k]["label"] for k in style_keys}
    def_options = {k: defense_styles[k]["label"] for k in defense_style_keys}
    st_options = {k: st_schemes[k]["label"] for k in st_scheme_keys} if st_scheme_keys else {"aces": "Aces"}

    style_container = ui.column().classes("w-full mt-4")

    @ui.refreshable
    def _render_human_config():
        selected = human_select.value or []
        if not selected:
            return

        ui.label("Your Team Configuration").classes("text-lg font-semibold text-slate-700")
        for tname in selected[:4]:  # max 4
            identity = team_identities.get(tname, {})
            mascot = identity.get("mascot", "")
            conf = identity.get("conference", "")

            with ui.card().classes("w-full p-4 mb-2"):
                ui.label(f"{tname}").classes("font-bold text-slate-800")
                if mascot or conf:
                    ui.label(f"{mascot} | {conf}").classes("text-sm text-gray-500")

                with ui.row().classes("gap-4"):
                    ui.select(style_options, value="balanced", label="Offense").classes("w-48").props(f"id=off_{tname}")
                    ui.select(def_options, value="swarm", label="Defense").classes("w-48").props(f"id=def_{tname}")
                    ui.select(st_options, value="aces", label="Special Teams").classes("w-48").props(f"id=st_{tname}")

    human_select.on_value_change(lambda _: _render_human_config.refresh())

    with style_container:
        _render_human_config()

    # League history
    ui.separator().classes("my-4")
    ui.label("League History").classes("text-lg font-semibold text-slate-700")
    ui.label("Generate pre-existing seasons so the league has history.").classes("text-sm text-gray-500")

    with ui.row().classes("gap-4 items-center"):
        ui.label("Years of History").classes("text-sm text-slate-600")
        history_years = ui.slider(min=0, max=100, value=0).classes("w-64")
        history_years_label = ui.label("0 years").classes("text-sm font-semibold text-slate-700 min-w-[60px]")
        ui.label("Games per Team").classes("text-sm text-slate-600")
        games_per_team = ui.slider(min=8, max=12, value=10).classes("w-64")
        games_label = ui.label("10 games").classes("text-sm font-semibold text-slate-700 min-w-[60px]")

    def _update_history_label():
        v = int(history_years.value)
        history_years_label.set_text(f"{v} year{'s' if v != 1 else ''}")
    history_years.on_value_change(lambda _: _update_history_label())

    def _update_games_label():
        games_label.set_text(f"{int(games_per_team.value)} games")
    games_per_team.on_value_change(lambda _: _update_games_label())

    ui.separator().classes("my-4")

    # Create button
    def _create_season():
        selected_humans = human_select.value or []
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

        try:
            api_client.create_season(
                state.session_id,
                name=season_name.value,
                games_per_team=int(games_per_team.value),
                human_teams=selected_humans,
                num_conferences=int(num_conferences.value),
                ai_seed=actual_seed,
                history_years=int(history_years.value),
            )
            state.mode = "season"
            state.human_teams = selected_humans
            notify_success("Season created! Switch to the Play tab to start simulating.")
            ui.navigate.to("/")
        except api_client.APIError as e:
            notify_error(f"Failed to create season: {e.detail}")

    ui.button("Create Season", on_click=_create_season, icon="sports_score").props("color=primary size=lg").classes("mt-2")
