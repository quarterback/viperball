"""Home / landing page — the first thing users see.

Shows session creation cards when no session is active,
or a dashboard summary when a session IS active.
"""

from __future__ import annotations

from nicegui import ui, run

from ui import api_client
from nicegui_app.state import UserState
from nicegui_app.components import metric_card, notify_error, notify_success, section_header, empty_state, loading_card_skeleton
from nicegui_app.helpers import fmt_vb_score


def render_home_sync(state: UserState, shared: dict, switch_fn):
    """Synchronous entry — used for initial page load."""
    if state.session_id and state.mode:
        ui.label("Loading session...").classes("text-slate-500")
        ui.timer(0.1, lambda: _deferred_dashboard(state, shared, switch_fn), once=True)
    else:
        _render_landing(state, shared, switch_fn)


async def render_home_section(state: UserState, shared: dict, switch_fn):
    """Async entry — used when switching tabs."""
    if state.session_id and state.mode:
        await _render_dashboard(state, shared, switch_fn)
    else:
        _render_landing(state, shared, switch_fn)


async def _deferred_dashboard(state: UserState, shared: dict, switch_fn):
    await _render_dashboard(state, shared, switch_fn)


# ═══════════════════════════════════════════════════════════════
# LANDING PAGE
# ═══════════════════════════════════════════════════════════════

def _render_landing(state: UserState, shared: dict, switch_fn):
    """Landing page with session creation cards."""
    team_count = len(shared.get("teams", []))

    # Hero section
    with ui.element("div").classes("w-full text-center mt-6 mb-8"):
        ui.icon("sports_football").classes("text-5xl mb-2").style("color: var(--vb-accent);")
        ui.label("VIPERBALL SANDBOX").classes(
            "text-4xl sm:text-5xl font-black tracking-wider"
        ).style("color: #fff; letter-spacing: 0.1em;")
        ui.label("Collegiate Viperball League Simulator").classes(
            "text-sm mt-2"
        ).style("color: var(--vb-text-muted);")

    # Mode cards
    _MODES = [
        {
            "label": "College Season",
            "icon": "sports_football",
            "gradient": "linear-gradient(135deg, #312e81, #4338ca)",
            "accent": "#818cf8",
            "nav": "Play",
            "play_tab": "season",
            "desc": "Run a full CVL season with conferences, playoffs, and bowl games.",
            "tags": ["12 weeks", "Playoffs", "Bowl Games"],
        },
        {
            "label": "College Dynasty",
            "icon": "school",
            "gradient": "linear-gradient(135deg, #134e4a, #0d9488)",
            "accent": "#5eead4",
            "nav": "Play",
            "play_tab": "dynasty",
            "desc": "Multi-season career mode with recruiting, development, and record books.",
            "tags": ["Multi-season", "Recruiting", "Record Books"],
        },
        {
            "label": "Quick Game",
            "icon": "bolt",
            "gradient": "linear-gradient(135deg, #78350f, #d97706)",
            "accent": "#fbbf24",
            "nav": "Play",
            "play_tab": "quick",
            "desc": "Pick two teams. Play one game. Full box scores and play-by-play.",
            "tags": ["Exhibition", "Custom Styles", "Box Score"],
        },
        {
            "label": "Pro Leagues",
            "icon": "stadium",
            "gradient": "linear-gradient(135deg, #3b0764, #7c3aed)",
            "accent": "#c4b5fd",
            "nav": "Pro Leagues",
            "desc": "NVL spectator mode — watch pro seasons unfold and bet via DraftyQueenz.",
            "tags": ["NVL", "Spectator", "Betting"],
        },
        {
            "label": "WVL Owner Mode",
            "icon": "emoji_events",
            "gradient": "linear-gradient(135deg, #4c0519, #e11d48)",
            "accent": "#fda4af",
            "nav": "WVL",
            "desc": "WVL franchise management with promotion, relegation, and finances.",
            "tags": ["Franchise", "Dynasty", "Multi-tier"],
        },
        {
            "label": "International",
            "icon": "public",
            "gradient": "linear-gradient(135deg, #0c4a6e, #0284c7)",
            "accent": "#7dd3fc",
            "nav": "International",
            "desc": "FIV 5-nation tournament with confederation play and knockouts.",
            "tags": ["FIV", "5 Nations", "Tournament"],
        },
        {
            "label": "DraftyQueenz",
            "icon": "casino",
            "gradient": "linear-gradient(135deg, #064e3b, #059669)",
            "accent": "#6ee7b7",
            "nav": "Play",
            "play_tab": "dq",
            "desc": "Fantasy betting with salary caps, parlays, and lineup building.",
            "tags": ["Fantasy", "Betting", "$5M Cap"],
        },
    ]

    with ui.element("div").classes("w-full grid gap-4 mt-2").style(
        "grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));"
    ):
        for m in _MODES:
            play_tab = m.get("play_tab")

            with ui.element("div").classes("cursor-pointer group").style(
                f"background: {m['gradient']}; border-radius: 14px; padding: 20px; "
                f"border: 1px solid rgba(255,255,255,0.08); "
                f"transition: transform 0.15s, box-shadow 0.15s; "
            ).on("click", lambda nav=m["nav"], pt=play_tab: switch_fn(nav, play_tab=pt)):
                with ui.row().classes("items-center gap-3 mb-3"):
                    ui.icon(m["icon"]).classes("text-2xl").style(f"color: {m['accent']};")
                    ui.label(m["label"]).classes("text-lg font-bold text-white")
                ui.label(m["desc"]).classes("text-xs leading-relaxed").style(
                    "color: rgba(255,255,255,0.7);"
                )
                with ui.row().classes("mt-3 gap-2 flex-wrap"):
                    for tag in m["tags"]:
                        ui.element("span").classes("text-[10px] font-semibold px-2 py-0.5 rounded-full").style(
                            f"color: {m['accent']}; background: rgba(255,255,255,0.1); "
                            f"border: 1px solid rgba(255,255,255,0.15);"
                        ).text = tag

    # Footer stats
    with ui.row().classes("w-full justify-center mt-10 gap-8"):
        for label in [f"{team_count} teams", "16 conferences", "CVL Engine v2.5"]:
            ui.label(label).classes("text-xs").style("color: var(--vb-text-dim);")


# ═══════════════════════════════════════════════════════════════
# DASHBOARD (active session)
# ═══════════════════════════════════════════════════════════════

async def _render_dashboard(state: UserState, shared: dict, switch_fn):
    """Active session dashboard — quick overview + navigation."""
    mode = state.mode or "season"

    try:
        status = await run.io_bound(api_client.get_season_status, state.session_id)
    except api_client.APIError:
        if mode == "dynasty":
            try:
                dyn_status = await run.io_bound(api_client.get_dynasty_status, state.session_id)
                await _render_dynasty_dashboard(state, shared, switch_fn, dyn_status)
                return
            except api_client.APIError:
                pass
        state.clear_session()
        _render_landing(state, shared, switch_fn)
        return

    season_name = status.get("name", "Season")
    phase = status.get("phase", "regular")
    current_week = status.get("current_week", 0)
    total_weeks = status.get("total_weeks", 10)
    champion = status.get("champion")

    section_header(season_name, icon="sports_football")

    if champion:
        with ui.element("div").classes("w-full p-4 rounded-xl mb-4").style(
            "background: linear-gradient(135deg, #78350f, #d97706); "
            "border: 1px solid rgba(251,191,36,0.3);"
        ):
            with ui.row().classes("items-center gap-3"):
                ui.icon("emoji_events").classes("text-3xl").style("color: #fbbf24;")
                ui.label(f"National Champions: {champion}").classes(
                    "text-lg font-bold text-white"
                )

    with ui.row().classes("w-full gap-3 flex-wrap mb-6"):
        metric_card("Week", f"{current_week}/{total_weeks}", icon="calendar_today")
        metric_card("Phase", phase.replace("_", " ").title(), icon="flag")
        metric_card("Mode", mode.title(), icon="sports_football")

    # Quick action cards
    _actions = [
        ("Continue Playing", "Simulate the next week or advance.", "play_arrow", "Play", "#4338ca"),
        ("View Standings", "Conference standings, polls, leaders.", "leaderboard", "League", "#059669"),
    ]
    if state.human_teams:
        team_name = shared.get("team_names", {}).get(
            state.human_teams[0], state.human_teams[0]
        )
        _actions.append((team_name, "Dashboard, roster, and schedule.", "groups", "My Team", "#e11d48"))

    with ui.row().classes("w-full gap-4 flex-wrap"):
        for title, desc, icon, nav, color in _actions:
            with ui.element("div").classes(
                "flex-1 min-w-[200px] p-4 rounded-xl cursor-pointer"
            ).style(
                f"background: var(--vb-surface); border: 1px solid var(--vb-border); "
                f"transition: border-color 0.15s;"
            ).on("click", lambda n=nav: switch_fn(n)):
                with ui.row().classes("items-center gap-2"):
                    ui.icon(icon).classes("text-xl").style(f"color: {color};")
                    ui.label(title).classes("text-base font-bold text-white")
                ui.label(desc).classes("text-xs mt-1").style("color: var(--vb-text-muted);")

    # Recent results
    try:
        schedule = await run.io_bound(api_client.get_schedule, state.session_id)
        all_games = schedule.get("games", [])
        completed = [g for g in all_games if g.get("completed")]
        if completed:
            recent = completed[-min(6, len(completed)):]
            ui.label("Recent Results").classes("text-sm font-semibold mt-6 mb-2").style(
                "color: var(--vb-text-muted);"
            )
            with ui.row().classes("w-full gap-3 flex-wrap"):
                for g in reversed(recent):
                    home = g.get("home_team", "")
                    away = g.get("away_team", "")
                    hs = fmt_vb_score(g.get("home_score", 0))
                    aws = fmt_vb_score(g.get("away_score", 0))
                    week = g.get("week", "")
                    with ui.element("div").classes("p-3 min-w-[170px] rounded-lg").style(
                        "background: var(--vb-surface-2); border: 1px solid var(--vb-border);"
                    ):
                        ui.label(f"Week {week}").classes("text-[10px] mb-1").style(
                            "color: var(--vb-text-dim);"
                        )
                        ui.label(f"{home} {hs}").classes("text-sm font-bold text-white")
                        ui.label(f"{away} {aws}").classes("text-sm").style(
                            "color: var(--vb-text-muted);"
                        )
    except api_client.APIError:
        pass


async def _render_dynasty_dashboard(state: UserState, shared: dict, switch_fn, dyn_status: dict):
    """Dashboard for dynasty in setup/offseason phase."""
    dynasty_name = dyn_status.get("dynasty_name", "Dynasty")
    current_year = dyn_status.get("current_year", "?")
    coach_info = dyn_status.get("coach", {})
    coach = coach_info.get("name", "")
    team = coach_info.get("team", "")
    seasons_played = dyn_status.get("seasons_played", 0)
    history_years = dyn_status.get("history_years", 0)

    section_header(dynasty_name, icon="school")

    with ui.row().classes("w-full gap-3 flex-wrap mb-6"):
        metric_card("Year", str(current_year), icon="calendar_today")
        metric_card("Seasons", str(seasons_played), icon="replay")
        if history_years > 0:
            metric_card("History", f"{history_years} yrs", icon="history")
        metric_card("Coach", coach, icon="person")
        metric_card("Team", team, icon="groups")

    with ui.element("div").classes("p-4 rounded-xl cursor-pointer").style(
        "background: var(--vb-surface); border: 1px solid var(--vb-border);"
    ).on("click", lambda: switch_fn("Play")):
        with ui.row().classes("items-center gap-2"):
            ui.icon("play_arrow").classes("text-xl").style("color: var(--vb-green);")
            ui.label("Start Next Season").classes("text-base font-bold text-white")
        ui.label("Configure and begin the next season of your dynasty.").classes(
            "text-xs mt-1"
        ).style("color: var(--vb-text-muted);")
