"""Main NiceGUI application for Viperball Sandbox.

Defines the root page layout with sidebar navigation, tab panels,
and mounts the existing FastAPI backend.

IMPORTANT: NiceGUI + FastAPI share a single uvicorn event-loop.
Every blocking HTTP call to the local API must go through
``await run.io_bound(...)`` so the event-loop stays free to
process the request.  Tab panels other than the default (Play)
are lazy-loaded on first selection to avoid blocking the
initial page render.
"""

from __future__ import annotations

from nicegui import ui, app, run, Client

from ui import api_client
from nicegui_app.state import UserState
from nicegui_app.helpers import OFFENSE_TOOLTIPS, DEFENSE_TOOLTIPS

from engine import get_available_teams, OFFENSE_STYLES
from engine.game_engine import DEFENSE_STYLES, ST_SCHEMES


# ── Custom CSS (ported from Streamlit custom styles) ──

APP_CSS = """
<style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    .score-big { font-size: 2.8rem; font-weight: 800; text-align: center; line-height: 1; color: #0f172a; }
    .team-name { font-size: 1.05rem; font-weight: 600; text-align: center; color: #475569; }
    .drive-td { color: #16a34a; font-weight: 700; }
    .drive-kick { color: #2563eb; font-weight: 700; }
    .drive-fumble { color: #dc2626; font-weight: 700; }
    .drive-downs { color: #d97706; font-weight: 700; }
    .drive-punt { color: #94a3b8; }
    .sidebar-brand { font-size: 1.4rem; font-weight: 800; color: #ffffff; letter-spacing: -0.02em; }
    .sidebar-tagline { font-size: 0.75rem; color: #64748b; margin-top: 2px; }
</style>
"""


def _load_shared_data() -> dict:
    """Load teams and styles directly from the engine (no HTTP loopback)."""
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


def _get_mode_label_sync(state: UserState) -> str:
    """Compute mode label — runs in a thread-pool via run.io_bound."""
    if not state.session_id or not state.mode:
        return "No Active Session"
    if state.mode == "dynasty":
        try:
            dyn_status = api_client.get_dynasty_status(state.session_id)
            dynasty_name = dyn_status.get("dynasty_name", "Dynasty")
            current_year = dyn_status.get("current_year", "")
            return f"Dynasty: {dynasty_name} ({current_year})"
        except api_client.APIError:
            return "Dynasty (loading...)"
    if state.mode == "season":
        try:
            status = api_client.get_season_status(state.session_id)
            return f"Season: {status.get('name', 'Season')}"
        except api_client.APIError:
            return "Season (loading...)"
    return "No Active Session"


def _loading_placeholder(label: str = "Loading..."):
    """Render a spinner + label as a placeholder while a tab loads."""
    with ui.column().classes("w-full items-center justify-center py-12"):
        ui.spinner("dots", size="lg")
        ui.label(label).classes("text-gray-400 text-sm mt-2")


@ui.page("/")
async def index(client: Client):
    """Main application page."""
    await client.connected()
    state = UserState()
    shared = _load_shared_data()

    ui.add_head_html(APP_CSS)

    # Sidebar drawer
    drawer = ui.left_drawer(value=True).classes("bg-slate-900 text-white p-4").style("width: 280px;")
    with drawer:
        ui.html('<p class="sidebar-brand">Viperball Sandbox</p>')
        ui.html('<p class="sidebar-tagline">Collegiate Viperball League Simulator</p>')
        ui.separator().classes("my-3").style("border-color: #334155;")

        # Mode label — fetched without blocking the event-loop
        mode_text = await run.io_bound(_get_mode_label_sync, state)
        mode_label = ui.label(mode_text).classes("font-bold text-sm text-white")

        async def _end_session():
            if state.session_id:
                try:
                    await run.io_bound(api_client.delete_session, state.session_id)
                except api_client.APIError:
                    pass
            state.clear_session()
            ui.notify("Session ended", type="info")
            ui.navigate.to("/")  # Refresh to show mode selection

        ui.button("End Session", on_click=_end_session, icon="stop").classes("w-full mt-2")

        ui.separator().classes("my-3").style("border-color: #334155;")

        # Settings navigation
        ui.label("Settings").classes("text-xs font-semibold uppercase tracking-wide text-slate-400 mt-2")

        def _on_settings_change(e):
            settings_container.clear()
            if e.value == "none":
                main_container.set_visibility(True)
                settings_container.set_visibility(False)
            else:
                main_container.set_visibility(False)
                settings_container.set_visibility(True)
                with settings_container:
                    if e.value == "debug":
                        from nicegui_app.pages.debug_tools import render_debug_tools
                        render_debug_tools(state, shared)
                    elif e.value == "inspector":
                        from nicegui_app.pages.play_inspector import render_play_inspector
                        render_play_inspector(state, shared)

        ui.radio(
            {"none": "Main View", "debug": "Debug Tools", "inspector": "Play Inspector"},
            value="none",
            on_change=_on_settings_change,
        ).classes("text-slate-300")

        ui.separator().classes("my-3").style("border-color: #334155;")
        num_teams = len(shared["teams"])
        ui.label("v2.5 — CVL Engine").classes("text-xs text-slate-500")
        ui.label(f"{num_teams} teams across 16 conferences").classes("text-xs text-slate-500")

    # Header
    with ui.header().classes("bg-white shadow-sm px-6 py-3 items-center"):
        ui.button(icon="menu", on_click=drawer.toggle).props("flat round dense")
        ui.label("Viperball Sandbox").classes("text-lg font-bold text-slate-800 ml-3")

    # Main content
    with ui.column().classes("w-full max-w-7xl mx-auto p-4"):

        # Settings pages (rendered when selected)
        settings_container = ui.column().classes("w-full")
        settings_container.set_visibility(False)

        # Main tabs
        main_container = ui.column().classes("w-full")

        with main_container:
            with ui.tabs().classes("w-full") as tabs:
                play_tab = ui.tab("Play")
                league_tab = ui.tab("League")
                team_tab = ui.tab("My Team")
                export_tab = ui.tab("Export")

            with ui.tab_panels(tabs, value=play_tab).classes("w-full"):
                # Play tab — rendered immediately (async-safe)
                with ui.tab_panel(play_tab):
                    from nicegui_app.pages.play import render_play_section
                    await render_play_section(state, shared)

                # Remaining tabs — lazy-loaded on first selection to avoid
                # blocking the event-loop with synchronous HTTP calls.
                with ui.tab_panel(league_tab):
                    league_container = ui.column().classes("w-full")
                    with league_container:
                        _loading_placeholder("Select this tab to load league data")

                with ui.tab_panel(team_tab):
                    team_container = ui.column().classes("w-full")
                    with team_container:
                        _loading_placeholder("Select this tab to load team data")

                with ui.tab_panel(export_tab):
                    export_container = ui.column().classes("w-full")
                    with export_container:
                        _loading_placeholder("Select this tab to load export options")

            # --- Lazy tab loader ---
            loaded_tabs: set[str] = {"Play"}

            async def _on_tab_change(e):
                tab_name = e.value
                if tab_name in loaded_tabs:
                    return
                loaded_tabs.add(tab_name)

                try:
                    if tab_name == "League":
                        league_container.clear()
                        with league_container:
                            from nicegui_app.pages.league import render_league_section
                            await render_league_section(state, shared)
                    elif tab_name == "My Team":
                        team_container.clear()
                        with team_container:
                            from nicegui_app.pages.my_team import render_my_team_section
                            await render_my_team_section(state, shared)
                    elif tab_name == "Export":
                        export_container.clear()
                        with export_container:
                            from nicegui_app.pages.export import render_export_section
                            await render_export_section(state, shared)
                except RuntimeError:
                    loaded_tabs.discard(tab_name)

            tabs.on_value_change(_on_tab_change)
