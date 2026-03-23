"""Main NiceGUI application for Viperball Sandbox.

Redesigned IA with:
- Home landing page (session creation / dashboard)
- Grouped navigation: core tabs visible, dev tools behind gear icon
- Session context bar when a session is active
- Flat navigation with clear information hierarchy

Uses app.storage.user (cookie-based) for state, so no async
client.connected() is needed. The page renders synchronously.

IMPORTANT: NiceGUI + FastAPI share a single uvicorn event-loop.
Every blocking HTTP call to the local API must go through
``await run.io_bound(...)`` so the event-loop stays free.
"""

from __future__ import annotations

import traceback
from pathlib import Path

from nicegui import ui, app, run

from ui import api_client
from nicegui_app.state import UserState
from nicegui_app.helpers import OFFENSE_TOOLTIPS, DEFENSE_TOOLTIPS

# ─── Serve P5.js sketch files via NiceGUI's static file support ───
_sketches_dir = Path(__file__).parent / "sketches"
if _sketches_dir.is_dir():
    app.add_static_files("/sketches", _sketches_dir)


APP_CSS = """
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.9.4/p5.min.js"></script>
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background-color: #f1f5f9;
    }

    /* ─── Ambient P5 Background ─── */
    #vb-ambient-bg {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: 0;
        pointer-events: none;
        opacity: 0.6;
    }
    #vb-nav-glow {
        width: 100%;
        height: 3px;
        position: relative;
        z-index: 2001;
        pointer-events: none;
    }
    #vb-page-transition {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: 9999;
        pointer-events: none;
    }

    /* Ensure main content sits above the ambient canvas */
    .q-page, .nicegui-content, .q-header {
        position: relative;
        z-index: 1;
    }

    .score-big { font-size: 2.8rem; font-weight: 800; text-align: center; line-height: 1; color: #0f172a; }
    .team-name { font-size: 1.05rem; font-weight: 600; text-align: center; color: #475569; }
    .drive-td { color: #16a34a; font-weight: 700; }
    .drive-kick { color: #2563eb; font-weight: 700; }
    .drive-fumble { color: #dc2626; font-weight: 700; }
    .drive-downs { color: #d97706; font-weight: 700; }
    .drive-punt { color: #94a3b8; }

    /* Session context bar */
    .session-bar {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
        z-index: 1999;
    }

    @media (max-width: 768px) {
        .desktop-nav { display: none !important; }
        .mobile-menu-btn { display: flex !important; }
        .q-tab { min-width: 0 !important; padding: 0 6px !important; font-size: 0.7rem !important; }
        .q-tab .q-tab__label { display: none !important; }
        .q-tab .q-tab__icon { font-size: 1.3rem !important; }
        .q-table td, .q-table th { padding: 4px 6px !important; font-size: 0.75rem !important; }
        .q-card { padding: 10px !important; }
        .q-card .min-w-\[180px\] { min-width: 120px !important; }
        .nicegui-content { padding: 8px !important; }
        .vb-hero-banner { padding: 14px 16px !important; }
        .vb-hero-banner .vb-hero-top { flex-direction: column !important; gap: 12px !important; }
        .vb-hero-banner .vb-hero-stats { gap: 12px !important; flex-wrap: wrap; justify-content: center; }
        .vb-hero-banner .text-2xl { font-size: 1.25rem !important; }
    }
    @media (min-width: 769px) {
        .mobile-menu-btn { display: none !important; }
    }
    .q-tabs__content { flex-wrap: nowrap !important; }
    .q-tabs { overflow: hidden !important; }
</style>
"""


_shared_cache: dict | None = None


def _load_shared_data() -> dict:
    global _shared_cache
    if _shared_cache is not None:
        return _shared_cache

    from engine import get_available_teams, OFFENSE_STYLES
    from engine.game_engine import DEFENSE_STYLES, ST_SCHEMES

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

    _shared_cache = {
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
    return _shared_cache


# ─── Navigation Structure ───────────────────────────────────────
# All primary tabs — visible in the nav bar
NAV_TABS = [
    ("Home", "home"),
    ("Play", "sports_football"),
    ("Pro Leagues", "stadium"),
    ("WVL", "emoji_events"),
    ("International", "public"),
    ("League", "leaderboard"),
    ("My Team", "groups"),
    ("Export", "download"),
]

# Dev tools — hidden behind a gear icon (not real user-facing features)
NAV_DEV = [
    ("Debug", "bug_report"),
    ("Inspector", "science"),
]


@ui.page("/")
def index():
    ui.add_head_html(APP_CSS)

    # ─── P5.js ambient layers ───
    ui.html('<div id="vb-ambient-bg"></div>')
    ui.html('<div id="vb-page-transition"></div>')

    _P5_INIT_JS = """
    function _vbLoadSketch(src) {
        var s = document.createElement('script');
        s.src = src;
        document.head.appendChild(s);
    }
    _vbLoadSketch('/sketches/ambient_bg.js');
    _vbLoadSketch('/sketches/page_transition.js');
    _vbLoadSketch('/sketches/nav_glow.js');
    """
    ui.timer(0.3, lambda: ui.run_javascript(_P5_INIT_JS), once=True)

    shared = _load_shared_data()
    state = UserState()

    # Check if we should auto-navigate to Pro Leagues (after season creation)
    pending_pro = app.storage.user.get("pro_league_pending_nav")
    if pending_pro:
        app.storage.user["pro_league_pending_nav"] = None

    # Check if we should auto-navigate to WVL (commissioner mode)
    pending_wvl = app.storage.user.get("_wvl_commish_phase")

    if pending_pro:
        initial_section = "Pro Leagues"
    elif pending_wvl:
        initial_section = "WVL"
    else:
        initial_section = "Home"
    active_nav = {"current": initial_section}

    nav_buttons: dict = {}

    async def _switch_to(name: str, *, play_tab: str | None = None):
        if active_nav["current"] == name and play_tab is None:
            return
        active_nav["current"] = name

        # Trigger P5.js page transition animation
        ui.run_javascript("if (window.vbTransition) window.vbTransition();")

        # Update button styling
        for btn_name, btn in nav_buttons.items():
            if btn_name == name:
                btn.classes(remove="text-slate-500", add="text-indigo-600 font-semibold")
            else:
                btn.classes(remove="text-indigo-600 font-semibold", add="text-slate-500")

        content_container.clear()
        with content_container:
            try:
                await _render_section(name, state, shared, _switch_to, play_tab=play_tab)
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

    # ─── Header ──────────────────────────────────────────────────
    with ui.header().classes("bg-white shadow-sm px-4 py-2 items-center").style("z-index: 2000;"):
        with ui.row().classes("w-full items-center gap-1"):
            # Brand — clicking it goes Home
            with ui.row().classes("items-center cursor-pointer gap-0 mr-4").on(
                "click", lambda: _switch_to("Home")
            ):
                ui.label("Viperball").classes("text-lg font-extrabold text-indigo-600")
                ui.label("Sandbox").classes("text-base font-light text-slate-400 ml-1")

            # ── All nav buttons (flat, equal) ────────────────────
            with ui.row().classes("desktop-nav items-center gap-1"):
                for name, icon_name in NAV_TABS:
                    btn = ui.button(name, icon=icon_name, on_click=lambda n=name: _switch_to(n))
                    btn.props("flat dense no-caps size=sm")
                    if name == initial_section:
                        btn.classes("text-indigo-600 font-semibold")
                    else:
                        btn.classes("text-slate-500")
                    nav_buttons[name] = btn

                # ── Separator + gear icon for dev tools ──────────
                ui.separator().props("vertical").classes("mx-1 h-6")
                with ui.button(icon="settings").props(
                    "flat dense size=sm round"
                ).classes("text-slate-400") as gear_btn:
                    nav_buttons["_gear"] = gear_btn
                    with ui.menu().classes("bg-white shadow-lg"):
                        for name, icon_name in NAV_DEV:
                            mi = ui.menu_item(name, on_click=lambda n=name: _switch_to(n))
                            mi.classes("text-slate-700")
                            nav_buttons[name] = mi

            # ── Mobile hamburger menu ────────────────────────────
            with ui.button(icon="menu").props("flat dense").classes("mobile-menu-btn text-slate-600"):
                with ui.menu().classes("bg-white shadow-lg"):
                    for name, icon_name in NAV_TABS:
                        mi = ui.menu_item(name, on_click=lambda n=name: _switch_to(n))
                        mi.classes("text-slate-700")
                        nav_buttons.setdefault(name, mi)
                    ui.separator()
                    for name, icon_name in NAV_DEV:
                        mi = ui.menu_item(name, on_click=lambda n=name: _switch_to(n))
                        mi.classes("text-slate-500 text-sm")
                        nav_buttons.setdefault(name, mi)

            ui.space()

            # ── Session indicator (right side) ───────────────────
            if state.session_id:
                mode_label = state.mode.title() if state.mode else ""
                ui.label(mode_label).classes("text-xs text-indigo-500 font-medium mr-2")
                ui.button("End", icon="stop", on_click=_end_session).props(
                    "flat dense size=sm color=red no-caps"
                )

    # ─── Session Context Bar ─────────────────────────────────────
    # Persistent strip below the header showing session state
    if state.session_id and state.mode in ("season", "dq"):
        with ui.row().classes(
            "session-bar w-full px-4 py-1.5 items-center gap-4"
        ):
            ui.icon("sports_football").classes("text-indigo-300 text-sm")
            # We show basic info synchronously, details load via timer
            mode_text = "Season" if state.mode == "season" else "DraftyQueenz"
            session_label = ui.label(f"{mode_text} Active").classes(
                "text-xs text-indigo-200 font-medium"
            )
            if state.human_teams:
                team_display = shared.get("team_names", {}).get(
                    state.human_teams[0], state.human_teams[0]
                )
                ui.label(f"Team: {team_display}").classes("text-xs text-indigo-300")
            ui.space()

            # Load live details (week, phase) asynchronously
            detail_label = ui.label("").classes("text-xs text-indigo-300")

            async def _load_context():
                try:
                    status = await run.io_bound(
                        api_client.get_season_status, state.session_id
                    )
                    week = status.get("current_week", 0)
                    total = status.get("total_weeks", 10)
                    phase = status.get("phase", "").replace("_", " ").title()
                    name = status.get("name", "")
                    if name:
                        session_label.set_text(name)
                    detail_label.set_text(f"Week {week}/{total}  |  {phase}")
                except Exception:
                    pass

            ui.timer(0.2, _load_context, once=True)

    # Nav glow container
    ui.html('<div id="vb-nav-glow"></div>')

    # ─── Main content area ───────────────────────────────────────
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
            from nicegui_app.pages.home import render_home_sync
            render_home_sync(state, shared, lambda n, **kw: _switch_to(n, **kw))


async def _render_section(name: str, state: UserState, shared: dict, switch_fn, *, play_tab: str | None = None):
    """Route to the correct page module for a given section name."""
    if name == "Home":
        from nicegui_app.pages.home import render_home_section
        await render_home_section(state, shared, switch_fn)
    elif name == "Play":
        from nicegui_app.pages.play import render_play_section
        await render_play_section(state, shared, play_tab=play_tab)
    elif name == "Pro Leagues":
        try:
            from nicegui_app.pages.pro_leagues import render_pro_leagues_section
            await render_pro_leagues_section(state, shared)
        except ImportError:
            ui.label("Pro Leagues module not yet available.").classes("text-gray-400 italic")
    elif name == "WVL":
        try:
            from nicegui_app.pages.wvl_mode import render_wvl_section
            await render_wvl_section(state, shared)
        except ImportError:
            ui.label("WVL module not yet available.").classes("text-gray-400 italic")
    elif name == "International":
        try:
            from nicegui_app.pages.international import render_international_section
            await render_international_section(state, shared)
        except ImportError:
            ui.label("International module not yet available.").classes("text-gray-400 italic")
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
