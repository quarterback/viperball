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
    :root {
        --vb-bg: #0f0f1a;
        --vb-surface: #1a1a2e;
        --vb-surface-2: #222240;
        --vb-border: #2a2a4a;
        --vb-border-light: #333360;
        --vb-text: #e2e8f0;
        --vb-text-muted: #94a3b8;
        --vb-text-dim: #64748b;
        --vb-accent: #818cf8;
        --vb-accent-bright: #a5b4fc;
        --vb-accent-dim: #4f46e5;
        --vb-green: #34d399;
        --vb-red: #f87171;
        --vb-amber: #fbbf24;
    }

    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background-color: var(--vb-bg);
        color: var(--vb-text);
    }

    /* ─── Ambient P5 Background ─── */
    #vb-ambient-bg {
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        z-index: 0;
        pointer-events: none;
        opacity: 0.4;
    }
    #vb-nav-glow {
        width: 100%;
        height: 2px;
        position: relative;
        z-index: 2001;
        pointer-events: none;
        background: linear-gradient(90deg, transparent, var(--vb-accent-dim), transparent);
        opacity: 0.5;
    }
    #vb-page-transition {
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        z-index: 9999;
        pointer-events: none;
    }

    /* Ensure main content sits above the ambient canvas */
    .q-page, .nicegui-content, .q-header {
        position: relative;
        z-index: 1;
    }

    /* ─── Dark theme overrides for Quasar components ─── */
    .q-card {
        background: var(--vb-surface) !important;
        color: var(--vb-text) !important;
        border: 1px solid var(--vb-border) !important;
        border-radius: 12px !important;
    }

    .q-table {
        background: var(--vb-surface) !important;
        color: var(--vb-text) !important;
    }
    .q-table th {
        background: var(--vb-surface-2) !important;
        color: var(--vb-text-muted) !important;
        font-weight: 700 !important;
        font-size: 11px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        border-bottom: 1px solid var(--vb-border) !important;
    }
    .q-table td {
        color: var(--vb-text) !important;
        border-bottom: 1px solid var(--vb-border) !important;
        font-size: 13px !important;
    }
    .q-table tbody tr:hover td {
        background: var(--vb-surface-2) !important;
    }

    .q-tabs {
        overflow: hidden !important;
    }
    .q-tabs__content {
        flex-wrap: nowrap !important;
    }
    .q-tab {
        color: var(--vb-text-muted) !important;
    }
    .q-tab--active {
        color: var(--vb-accent-bright) !important;
    }
    .q-tab-panel {
        padding: 12px 0 !important;
    }

    .q-separator {
        background: var(--vb-border) !important;
    }

    .q-field__control {
        color: var(--vb-text) !important;
    }
    .q-field__label {
        color: var(--vb-text-muted) !important;
    }
    .q-field--outlined .q-field__control:before {
        border-color: var(--vb-border) !important;
    }

    .q-expansion-item {
        border: 1px solid var(--vb-border) !important;
        border-radius: 8px !important;
        margin-bottom: 4px;
    }
    .q-expansion-item__container {
        background: var(--vb-surface) !important;
        color: var(--vb-text) !important;
    }

    .q-menu {
        background: var(--vb-surface-2) !important;
        border: 1px solid var(--vb-border) !important;
    }
    .q-item {
        color: var(--vb-text) !important;
    }
    .q-item:hover {
        background: var(--vb-surface) !important;
    }

    /* Notify / toast overrides */
    .q-notification {
        border-radius: 8px !important;
    }

    /* ─── Custom classes ─── */
    .score-big { font-size: 2.8rem; font-weight: 800; text-align: center; line-height: 1; color: #fff; }
    .team-name { font-size: 1.05rem; font-weight: 600; text-align: center; color: var(--vb-text-muted); }
    .drive-td { color: var(--vb-green); font-weight: 700; }
    .drive-kick { color: var(--vb-accent); font-weight: 700; }
    .drive-fumble { color: var(--vb-red); font-weight: 700; }
    .drive-downs { color: var(--vb-amber); font-weight: 700; }
    .drive-punt { color: var(--vb-text-dim); }

    /* ─── Remap light-theme Tailwind text colors → dark-theme equivalents ─── */
    /* These override the hundreds of hardcoded text-slate-800, text-gray-500, etc.
       across all page modules so they're readable on dark backgrounds. */

    /* Headings / primary text (were dark, now light) */
    .text-slate-800, .text-slate-900, .text-gray-800, .text-gray-900,
    .text-zinc-800, .text-zinc-900 {
        color: #f1f5f9 !important;
    }
    .text-slate-700, .text-gray-700, .text-zinc-700 {
        color: #e2e8f0 !important;
    }
    .text-slate-600, .text-gray-600, .text-zinc-600 {
        color: #cbd5e1 !important;
    }

    /* Muted / secondary text (were medium-dark, now medium-light) */
    .text-slate-500, .text-gray-500, .text-zinc-500 {
        color: #b0bec5 !important;
    }
    .text-slate-400, .text-gray-400, .text-zinc-400 {
        color: #b0bec5 !important;
    }

    /* Indigo accent headings — make them brighter */
    .text-indigo-600 { color: #a5b4fc !important; }
    .text-indigo-700, .text-indigo-800 { color: #c7d2fe !important; }
    .text-indigo-500 { color: #818cf8 !important; }
    .text-indigo-200, .text-indigo-300 { color: #a5b4fc !important; }

    /* Other accent colors — brighten for dark bg */
    .text-teal-500, .text-teal-600, .text-teal-700 { color: #5eead4 !important; }
    .text-emerald-500, .text-emerald-600 { color: #6ee7b7 !important; }
    .text-amber-500, .text-amber-600 { color: #fbbf24 !important; }
    .text-rose-500, .text-rose-600 { color: #fda4af !important; }
    .text-purple-500, .text-purple-600, .text-purple-700 { color: #c4b5fd !important; }
    .text-sky-500, .text-sky-600 { color: #7dd3fc !important; }
    .text-blue-500, .text-blue-600, .text-blue-700, .text-blue-800 { color: #93c5fd !important; }
    .text-blue-200 { color: #93c5fd !important; }
    .text-green-800 { color: #86efac !important; }
    .text-amber-800 { color: #fde68a !important; }
    .text-red-500, .text-red-600 { color: #fca5a5 !important; }

    /* Background overrides for info cards that assumed light bg */
    .bg-blue-50, .bg-green-50, .bg-amber-50, .bg-red-50,
    .bg-indigo-50, .bg-teal-50, .bg-purple-50 {
        background: var(--vb-surface-2) !important;
    }
    .bg-slate-50 { background: var(--vb-surface) !important; }
    .bg-white { background: var(--vb-surface) !important; }

    /* Border overrides */
    .border-blue-200, .border-green-200, .border-amber-200,
    .border-red-200, .border-indigo-200 {
        border-color: var(--vb-border) !important;
    }

    /* Input / form field backgrounds */
    .q-field__control {
        background: var(--vb-surface) !important;
    }
    .q-field--outlined .q-field__control:after {
        border-color: var(--vb-border-light) !important;
    }
    .q-field--focused .q-field__control:after {
        border-color: var(--vb-accent) !important;
    }

    /* Badge overrides */
    .q-badge {
        border-color: var(--vb-border-light) !important;
    }

    /* Slider overrides */
    .q-slider__track-container {
        background: var(--vb-border) !important;
    }
    .q-slider__thumb { color: var(--vb-accent) !important; }
    .q-slider__selection { background: var(--vb-accent) !important; }
    .q-slider__text { color: var(--vb-text) !important; }

    /* Radio button / checkbox / toggle overrides */
    .q-radio__label, .q-checkbox__label, .q-toggle__label {
        color: var(--vb-text) !important;
    }
    .q-radio__inner, .q-checkbox__inner {
        color: var(--vb-text-muted) !important;
    }
    .q-radio__inner--truthy, .q-checkbox__inner--truthy {
        color: var(--vb-accent) !important;
    }
    .q-option-group .q-radio, .q-option-group .q-checkbox {
        color: var(--vb-text) !important;
    }

    /* Select / dropdown overrides */
    .q-select .q-field__native, .q-select .q-field__input {
        color: var(--vb-text) !important;
    }
    .q-select .q-field__native span {
        color: var(--vb-text) !important;
    }
    .q-select__dropdown-icon {
        color: var(--vb-text-muted) !important;
    }
    .q-virtual-scroll__content .q-item__label {
        color: var(--vb-text) !important;
    }

    /* Input text should be visible */
    .q-field__native, .q-field__prefix, .q-field__suffix, .q-field__input {
        color: var(--vb-text) !important;
    }

    /* Chip overrides (used in multi-selects) */
    .q-chip { background: var(--vb-surface-2) !important; color: var(--vb-text) !important; }

    /* Dialog overrides */
    .q-dialog .q-card {
        background: var(--vb-surface) !important;
    }

    /* Session context bar */
    .session-bar {
        background: var(--vb-surface-2);
        border-bottom: 1px solid var(--vb-border);
        z-index: 1999;
    }

    /* ─── Responsive ─── */
    @media (max-width: 768px) {
        .desktop-nav { display: none !important; }
        .mobile-menu-btn { display: flex !important; }
        .q-tab { min-width: 0 !important; padding: 0 6px !important; font-size: 0.7rem !important; }
        .q-tab .q-tab__label { display: none !important; }
        .q-tab .q-tab__icon { font-size: 1.3rem !important; }
        .q-table td, .q-table th { padding: 4px 6px !important; font-size: 0.75rem !important; }
        .q-card { padding: 10px !important; }
        .nicegui-content { padding: 8px !important; }
        .vb-hero-banner { padding: 14px 16px !important; }
        .vb-hero-banner .vb-hero-top { flex-direction: column !important; gap: 12px !important; }
        .vb-hero-banner .vb-hero-stats { gap: 12px !important; flex-wrap: wrap; justify-content: center; }
        .vb-hero-banner .text-2xl { font-size: 1.25rem !important; }
    }
    @media (min-width: 769px) {
        .mobile-menu-btn { display: none !important; }
    }
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

    from engine.fiv import get_fiv_nation_list

    _shared_cache = {
        "teams": teams,
        "intl_teams": get_fiv_nation_list(),
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

    # Validate stored session
    if state.session_id:
        from api.main import sessions as _api_sessions
        if state.session_id not in _api_sessions:
            state.clear_session()

    # Check if we should auto-navigate to a section (one-shot flags)
    pending_pro = app.storage.user.get("pro_league_pending_nav")
    if pending_pro:
        app.storage.user["pro_league_pending_nav"] = None

    pending_wvl = app.storage.user.pop("_wvl_pending_nav", None)

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

        ui.run_javascript("if (window.vbTransition) window.vbTransition();")

        # Update button styling
        for btn_name, btn in nav_buttons.items():
            if btn_name == name:
                btn.classes(remove="text-slate-500 hover:text-slate-300", add="text-indigo-400 font-semibold")
            else:
                btn.classes(remove="text-indigo-400 font-semibold", add="text-slate-500 hover:text-slate-300")

        # Show loading skeleton while content loads
        content_container.clear()
        with content_container:
            from nicegui_app.components import loading_page_skeleton
            loading_page_skeleton()

        content_container.clear()
        with content_container:
            try:
                await _render_section(name, state, shared, _switch_to, play_tab=play_tab)
            except Exception as exc:
                import logging
                logging.getLogger("viperball").error(f"Error loading {name}: {exc}", exc_info=True)
                ui.label(f"Error loading {name}: {exc}").classes("text-red-400")

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
    with ui.header().classes("px-4 py-2 items-center").style(
        "z-index: 2000; background: var(--vb-surface); "
        "border-bottom: 1px solid var(--vb-border); "
        "box-shadow: 0 1px 12px rgba(0,0,0,0.3);"
    ):
        with ui.row().classes("w-full items-center gap-1"):
            # Brand
            with ui.row().classes("items-center cursor-pointer gap-1 mr-6").on(
                "click", lambda: _switch_to("Home")
            ):
                ui.icon("sports_football").classes("text-lg").style("color: var(--vb-accent);")
                ui.label("VIPERBALL").classes("text-base font-black tracking-widest").style(
                    "color: var(--vb-accent-bright); letter-spacing: 0.15em;"
                )

            # ── Nav buttons ─────────────────────────────────────
            with ui.row().classes("desktop-nav items-center gap-0"):
                for name, icon_name in NAV_TABS:
                    btn = ui.button(name, icon=icon_name, on_click=lambda n=name: _switch_to(n))
                    btn.props("flat dense no-caps size=sm")
                    if name == initial_section:
                        btn.classes("text-indigo-400 font-semibold")
                    else:
                        btn.classes("text-slate-500 hover:text-slate-300")
                    btn.style("transition: color 0.15s;")
                    nav_buttons[name] = btn

                # ── Dev tools gear ──────────────────────────────
                ui.separator().props("vertical").classes("mx-2 h-5")
                with ui.button(icon="settings").props(
                    "flat dense size=sm round"
                ).classes("text-slate-600 hover:text-slate-400") as gear_btn:
                    nav_buttons["_gear"] = gear_btn
                    with ui.menu():
                        for name, icon_name in NAV_DEV:
                            mi = ui.menu_item(name, on_click=lambda n=name: _switch_to(n))
                            nav_buttons[name] = mi

            # ── Mobile hamburger ─────────────────────────────────
            with ui.button(icon="menu").props("flat dense").classes("mobile-menu-btn").style(
                "color: var(--vb-text-muted);"
            ):
                with ui.menu():
                    for name, icon_name in NAV_TABS:
                        mi = ui.menu_item(name, on_click=lambda n=name: _switch_to(n))
                        nav_buttons.setdefault(name, mi)
                    ui.separator()
                    for name, icon_name in NAV_DEV:
                        mi = ui.menu_item(name, on_click=lambda n=name: _switch_to(n))
                        nav_buttons.setdefault(name, mi)

            ui.space()

            # ── Session indicator ────────────────────────────────
            if state.session_id:
                mode_label = state.mode.title() if state.mode else ""
                with ui.row().classes("items-center gap-2"):
                    ui.badge(mode_label).props("color=indigo outline").classes("text-xs")
                    ui.button("End", icon="stop", on_click=_end_session).props(
                        "flat dense size=sm no-caps"
                    ).style("color: var(--vb-red);")

    # ─── Session Context Bar ─────────────────────────────────────
    if state.session_id and state.mode in ("season", "dq"):
        with ui.row().classes("session-bar w-full px-4 py-1.5 items-center gap-4"):
            ui.icon("sports_football").classes("text-sm").style("color: var(--vb-accent);")
            mode_text = "Season" if state.mode == "season" else "DraftyQueenz"
            session_label = ui.label(f"{mode_text} Active").classes(
                "text-xs font-medium"
            ).style("color: var(--vb-text-muted);")
            if state.human_teams:
                team_display = shared.get("team_names", {}).get(
                    state.human_teams[0], state.human_teams[0]
                )
                ui.label(f"Team: {team_display}").classes("text-xs").style("color: var(--vb-accent);")
            ui.space()

            detail_label = ui.label("").classes("text-xs").style("color: var(--vb-text-dim);")

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

    # Nav glow
    ui.html('<div id="vb-nav-glow"></div>')

    # ─── Main content area ───────────────────────────────────────
    content_container = ui.column().classes("w-full max-w-7xl mx-auto p-4 sm:p-6 px-3")

    if initial_section != "Home":
        async def _init_section():
            content_container.clear()
            with content_container:
                try:
                    await _render_section(initial_section, state, shared, _switch_to)
                except Exception as exc:
                    import logging
                    logging.getLogger("viperball").error(f"{initial_section} render error: {exc}", exc_info=True)
                    ui.label(f"Error loading {initial_section}: {exc}").classes("text-red-400")
        ui.timer(0.1, _init_section, once=True)
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
            ui.label("Pro Leagues module not yet available.").classes("text-slate-500 italic")
    elif name == "WVL":
        try:
            from nicegui_app.pages.wvl_mode import render_wvl_section
            await render_wvl_section(state, shared)
        except ImportError:
            ui.label("WVL module not yet available.").classes("text-slate-500 italic")
    elif name == "International":
        try:
            from nicegui_app.pages.international import render_international_section
            await render_international_section(state, shared)
        except ImportError:
            ui.label("International module not yet available.").classes("text-slate-500 italic")
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
