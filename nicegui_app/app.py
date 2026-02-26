"""Main NiceGUI application for Viperball Sandbox.

SaaS-style layout with top navigation bar and all sections visible.

Uses app.storage.user (cookie-based) for state, so no async
client.connected() is needed. The page renders synchronously.

IMPORTANT: NiceGUI + FastAPI share a single uvicorn event-loop.
Every blocking HTTP call to the local API must go through
``await run.io_bound(...)`` so the event-loop stays free.
"""

from __future__ import annotations

import traceback

from nicegui import ui, app, run

from ui import api_client
from nicegui_app.state import UserState
from nicegui_app.helpers import OFFENSE_TOOLTIPS, DEFENSE_TOOLTIPS

from engine import get_available_teams, OFFENSE_STYLES
from engine.game_engine import DEFENSE_STYLES, ST_SCHEMES


APP_CSS = """
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background-color: #f1f5f9;
    }
    .score-big { font-size: 2.8rem; font-weight: 800; text-align: center; line-height: 1; color: #0f172a; }
    .team-name { font-size: 1.05rem; font-weight: 600; text-align: center; color: #475569; }
    .drive-td { color: #16a34a; font-weight: 700; }
    .drive-kick { color: #2563eb; font-weight: 700; }
    .drive-fumble { color: #dc2626; font-weight: 700; }
    .drive-downs { color: #d97706; font-weight: 700; }
    .drive-punt { color: #94a3b8; }

    @media (max-width: 768px) {
        .desktop-nav { display: none !important; }
        .mobile-menu-btn { display: flex !important; }
        .q-tab { min-width: 0 !important; padding: 0 8px !important; font-size: 0.75rem !important; }
        .q-table td, .q-table th { padding: 4px 6px !important; font-size: 0.75rem !important; }
    }
    @media (min-width: 769px) {
        .mobile-menu-btn { display: none !important; }
    }
    .q-tabs--scrollable .q-tabs__content { flex-wrap: nowrap !important; }
</style>
"""


def _load_shared_data() -> dict:
    try:
        teams = get_available_teams()
    except Exception:
        teams = []

    styles = {k: {"label": v.get("label", k), "description": v.get("description", "")}
              for k, v in OFFENSE_STYLES.items()}
    defense_styles = {k: {"label": v.get("label", k), "description": v.get("description", "")}
                      for k, v in DEFENSE_STYLES.items()}
    st_schemes = {k: {"label": v.get("label", k), "description": v.get("description", "")}
                  for k, v in ST_SCHEMES.items()}

    return {
        "teams": teams,
        "styles": styles,
        "team_names": {t["key"]: t["name"] for t in teams},
        "style_keys": list(styles.keys()),
        "defense_style_keys": list(defense_styles.keys()),
        "defense_styles": defense_styles,
        "st_schemes": st_schemes,
        "st_scheme_keys": list(st_schemes.keys()),
        "OFFENSE_TOOLTIPS": OFFENSE_TOOLTIPS,
        "DEFENSE_TOOLTIPS": DEFENSE_TOOLTIPS,
    }


NAV_SECTIONS = [
    ("Play", "sports_football"),
    ("Pro Leagues", "stadium"),
    ("League", "leaderboard"),
    ("My Team", "groups"),
    ("Export", "download"),
    ("Debug", "bug_report"),
    ("Inspector", "science"),
]


@ui.page("/")
def index():
    ui.add_head_html(APP_CSS)

    shared = _load_shared_data()
    state = UserState()

    # Check if we should auto-navigate to Pro Leagues (after season creation)
    pending_pro = app.storage.user.get("pro_league_pending_nav")
    if pending_pro:
        app.storage.user["pro_league_pending_nav"] = None
    initial_section = "Pro Leagues" if pending_pro else "Play"
    active_nav = {"current": initial_section}

    async def _switch_to(name: str):
        if active_nav["current"] == name:
            return
        active_nav["current"] = name

        for btn_name, btn in nav_buttons.items():
            if btn_name == name:
                btn.classes(remove="text-slate-500", add="text-indigo-600 font-semibold")
            else:
                btn.classes(remove="text-indigo-600 font-semibold", add="text-slate-500")

        content_container.clear()
        with content_container:
            try:
                if name == "Play":
                    from nicegui_app.pages.play import render_play_section
                    await render_play_section(state, shared)
                elif name == "Pro Leagues":
                    try:
                        from nicegui_app.pages.pro_leagues import render_pro_leagues_section
                        await render_pro_leagues_section(state, shared)
                    except ImportError:
                        ui.label("Pro Leagues module not yet available.").classes("text-gray-400 italic")
                elif name == "League":
                    from nicegui_app.pages.league import render_league_section
                    await render_league_section(state, shared)
                elif name == "My Team":
                    from nicegui_app.pages.my_team import render_my_team_section
                    await render_my_team_section(state, shared)
                elif name == "Export":
                    from nicegui_app.pages.export import render_export_section
                    await render_export_section(state, shared)
                elif name == "Debug":
                    from nicegui_app.pages.debug_tools import render_debug_tools
                    render_debug_tools(state, shared)
                elif name == "Inspector":
                    from nicegui_app.pages.play_inspector import render_play_inspector
                    render_play_inspector(state, shared)
            except Exception as exc:
                import logging
                logging.getLogger("viperball").error(f"Error loading {name}: {exc}", exc_info=True)
                ui.label(f"Error loading {name}: {exc}").classes("text-red-500")
                traceback.print_exc()

    async def _end_session():
        if state.session_id:
            try:
                await run.io_bound(api_client.delete_session, state.session_id)
            except Exception:
                pass
        state.clear_session()
        ui.notify("Session ended", type="info")
        ui.navigate.to("/")

    with ui.header().classes("bg-white shadow-sm px-4 py-2 items-center").style("z-index: 2000;"):
        with ui.row().classes("w-full items-center gap-1"):
            ui.label("Viperball").classes("text-lg font-extrabold text-indigo-600")
            ui.label("Sandbox").classes("text-base font-light text-slate-400 ml-1 mr-6")

            nav_buttons = {}

            with ui.row().classes("desktop-nav items-center gap-1"):
                for name, icon_name in NAV_SECTIONS:
                    btn = ui.button(name, icon=icon_name, on_click=lambda n=name: _switch_to(n))
                    btn.props("flat dense no-caps size=sm")
                    if name == initial_section:
                        btn.classes("text-indigo-600 font-semibold")
                    else:
                        btn.classes("text-slate-500")
                    nav_buttons[name] = btn

            with ui.button(icon="menu").props("flat dense").classes("mobile-menu-btn text-slate-600"):
                with ui.menu().classes("bg-white shadow-lg"):
                    for name, icon_name in NAV_SECTIONS:
                        mi = ui.menu_item(name, on_click=lambda n=name: _switch_to(n))
                        mi.classes("text-slate-700")
                        nav_buttons.setdefault(name, mi)

            ui.space()

            if state.session_id:
                mode_label = state.mode.title() if state.mode else ""
                ui.label(mode_label).classes("text-xs text-indigo-500 font-medium mr-2")
                ui.button("End", icon="stop", on_click=_end_session).props(
                    "flat dense size=sm color=red no-caps"
                )

    content_container = ui.column().classes("w-full max-w-7xl mx-auto p-4 sm:p-4 px-2")

    if initial_section == "Pro Leagues":
        async def _init_pro():
            content_container.clear()
            with content_container:
                try:
                    from nicegui_app.pages.pro_leagues import render_pro_leagues_section
                    await render_pro_leagues_section(state, shared)
                except Exception as exc:
                    import logging
                    logging.getLogger("viperball").error(f"Pro Leagues render error: {exc}", exc_info=True)
                    ui.label(f"Error loading Pro Leagues: {exc}").classes("text-red-500")
                    traceback.print_exc()
        ui.timer(0.1, _init_pro, once=True)
    else:
        with content_container:
            from nicegui_app.pages.play import render_play_section_sync
            render_play_section_sync(state, shared)
