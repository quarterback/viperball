"""Home / landing page — the first thing users see.

Shows session creation cards when no session is active,
or a dashboard summary when a session IS active.
"""

from __future__ import annotations

from nicegui import ui, run

from ui import api_client
from nicegui_app.state import UserState
from nicegui_app.components import metric_card, notify_error, notify_success
from nicegui_app.helpers import fmt_vb_score


def render_home_sync(state: UserState, shared: dict, switch_fn):
    """Synchronous entry — used for initial page load."""
    if state.session_id and state.mode:
        ui.label("Loading session...").classes("text-slate-400")
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


def _render_landing(state: UserState, shared: dict, switch_fn):
    """Landing page with session creation cards."""
    team_count = len(shared.get("teams", []))

    with ui.column().classes("w-full items-center mt-8 mb-8"):
        ui.label("Viperball Sandbox").classes(
            "text-4xl sm:text-5xl font-extrabold text-slate-800 tracking-tight"
        )
        ui.label("Collegiate Viperball League Simulator").classes(
            "text-base text-slate-400 mt-1"
        )

    # ── All game modes — equal grid ─────────────────────────────
    _MODES = [
        {
            "label": "College Season",
            "icon": "sports_football",
            "color": "indigo",
            "nav": "Play",
            "desc": "Run a full CVL season with conferences, playoffs, and bowl games. Coach one or more teams through a 12-week season.",
            "tags": ["12 weeks", "Playoffs", "Bowl Games"],
        },
        {
            "label": "College Dynasty",
            "icon": "school",
            "color": "teal",
            "nav": "Play",
            "desc": "Multi-season career mode. Build a program across multiple years with recruiting, player development, awards, and historical record books.",
            "tags": ["Multi-season", "Recruiting", "Record Books"],
        },
        {
            "label": "Quick Game",
            "icon": "bolt",
            "color": "amber",
            "nav": "Play",
            "desc": "Pick two teams and play a single exhibition game. Choose offensive styles, weather, and see full box scores.",
            "tags": ["Exhibition", "Custom Styles", "Box Score"],
        },
        {
            "label": "Pro Leagues",
            "icon": "stadium",
            "color": "purple",
            "nav": "Pro Leagues",
            "desc": "NVL spectator mode — watch full pro seasons unfold, browse stats and standings, and bet through DraftyQueenz.",
            "tags": ["NVL", "Spectator", "Betting"],
        },
        {
            "label": "WVL Owner Mode",
            "icon": "emoji_events",
            "color": "rose",
            "nav": "WVL",
            "desc": "Women's Viperball League franchise management. Multi-tier system with promotion, relegation, drafts, and finances.",
            "tags": ["Franchise", "Dynasty", "Multi-tier"],
        },
        {
            "label": "International",
            "icon": "public",
            "color": "sky",
            "nav": "International",
            "desc": "FIV international tournament — 5-nation competition with confederation play, knockouts, and national team rosters.",
            "tags": ["FIV", "5 Nations", "Tournament"],
        },
        {
            "label": "DraftyQueenz",
            "icon": "casino",
            "color": "emerald",
            "nav": "Play",
            "desc": "Fantasy betting game with salary caps and parlays. Build lineups, place bets, and compete against the house.",
            "tags": ["Fantasy", "Betting", "$5M Cap"],
        },
    ]

    with ui.element("div").classes(
        "w-full grid gap-5 mt-4"
    ).style(
        "grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));"
    ):
        for m in _MODES:
            with ui.card().classes(
                "p-5 cursor-pointer hover:shadow-lg transition-shadow"
            ).on("click", lambda nav=m["nav"]: switch_fn(nav)):
                with ui.row().classes("items-center gap-3 mb-3"):
                    ui.icon(m["icon"]).classes(f"text-3xl text-{m['color']}-500")
                    ui.label(m["label"]).classes("text-xl font-bold text-slate-800")
                ui.label(m["desc"]).classes("text-sm text-slate-500 leading-relaxed")
                with ui.row().classes("mt-4 gap-2 flex-wrap"):
                    for tag in m["tags"]:
                        ui.badge(tag).props(f"outline color={m['color']}")

    # ── Footer stats ─────────────────────────────────────────────
    with ui.row().classes("w-full justify-center mt-10 gap-6"):
        ui.label(f"{team_count} teams").classes("text-sm text-slate-400")
        ui.label("16 conferences").classes("text-sm text-slate-400")
        ui.label("CVL Engine v2.5").classes("text-sm text-slate-400")


async def _render_dashboard(state: UserState, shared: dict, switch_fn):
    """Active session dashboard — quick overview + navigation."""
    mode = state.mode or "season"

    try:
        status = await run.io_bound(api_client.get_season_status, state.session_id)
    except api_client.APIError:
        # Dynasty in setup/offseason phase — no active season yet
        if mode == "dynasty":
            try:
                dyn_status = await run.io_bound(api_client.get_dynasty_status, state.session_id)
                await _render_dynasty_dashboard(state, shared, switch_fn, dyn_status)
                return
            except api_client.APIError:
                pass
        _render_landing(state, shared, switch_fn)
        return

    season_name = status.get("name", "Season")
    phase = status.get("phase", "regular")
    current_week = status.get("current_week", 0)
    total_weeks = status.get("total_weeks", 10)
    champion = status.get("champion")

    ui.label(season_name).classes("text-2xl font-bold text-slate-800")

    if champion:
        with ui.card().classes("w-full bg-amber-50 border border-amber-200 p-4 rounded-lg mb-4"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("emoji_events").classes("text-3xl text-amber-500")
                ui.label(f"National Champions: {champion}").classes(
                    "text-lg font-bold text-amber-800"
                )

    with ui.row().classes("w-full gap-3 flex-wrap mb-6"):
        metric_card("Week", f"{current_week}/{total_weeks}")
        metric_card("Phase", phase.replace("_", " ").title())
        metric_card("Mode", mode.title())

    # Quick action cards
    with ui.row().classes("w-full gap-4 flex-wrap"):
        with ui.card().classes(
            "p-4 flex-1 min-w-[200px] cursor-pointer hover:shadow-lg transition-shadow"
        ).on("click", lambda: switch_fn("Play")):
            with ui.row().classes("items-center gap-2"):
                ui.icon("play_arrow").classes("text-2xl text-indigo-500")
                ui.label("Continue Playing").classes("text-lg font-bold text-slate-700")
            ui.label("Simulate the next week or advance the season.").classes(
                "text-sm text-slate-500 mt-1"
            )

        with ui.card().classes(
            "p-4 flex-1 min-w-[200px] cursor-pointer hover:shadow-lg transition-shadow"
        ).on("click", lambda: switch_fn("League")):
            with ui.row().classes("items-center gap-2"):
                ui.icon("leaderboard").classes("text-2xl text-emerald-500")
                ui.label("View Standings").classes("text-lg font-bold text-slate-700")
            ui.label("Check conference standings, polls, and stat leaders.").classes(
                "text-sm text-slate-500 mt-1"
            )

        if state.human_teams:
            with ui.card().classes(
                "p-4 flex-1 min-w-[200px] cursor-pointer hover:shadow-lg transition-shadow"
            ).on("click", lambda: switch_fn("My Team")):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("groups").classes("text-2xl text-rose-500")
                    team_name = shared.get("team_names", {}).get(
                        state.human_teams[0], state.human_teams[0]
                    ) if state.human_teams else "My Team"
                    ui.label(team_name).classes("text-lg font-bold text-slate-700")
                ui.label("Dashboard, roster, and schedule for your team.").classes(
                    "text-sm text-slate-500 mt-1"
                )

    # Recent results
    try:
        schedule = await run.io_bound(api_client.get_schedule, state.session_id)
        all_games = schedule.get("games", [])
        completed = [g for g in all_games if g.get("completed")]
        if completed:
            recent = completed[-min(6, len(completed)):]
            ui.label("Recent Results").classes("text-lg font-semibold text-slate-700 mt-6 mb-2")
            with ui.row().classes("w-full gap-3 flex-wrap"):
                for g in reversed(recent):
                    home = g.get("home_team", "")
                    away = g.get("away_team", "")
                    hs = fmt_vb_score(g.get("home_score", 0))
                    aws = fmt_vb_score(g.get("away_score", 0))
                    week = g.get("week", "")
                    with ui.card().classes("p-3 min-w-[180px]").style(
                        "background: #f8fafc; border: 1px solid #e2e8f0;"
                    ):
                        ui.label(f"Week {week}").classes("text-xs text-slate-400 mb-1")
                        ui.label(f"{home} {hs}").classes("text-sm font-semibold text-slate-700")
                        ui.label(f"{away} {aws}").classes("text-sm text-slate-600")
    except api_client.APIError:
        pass


async def _render_dynasty_dashboard(state: UserState, shared: dict, switch_fn, dyn_status: dict):
    """Dashboard for dynasty in setup/offseason phase (no active season)."""
    dynasty_name = dyn_status.get("dynasty_name", "Dynasty")
    current_year = dyn_status.get("current_year", "?")
    coach_info = dyn_status.get("coach", {})
    coach = coach_info.get("name", "")
    team = coach_info.get("team", "")
    seasons_played = dyn_status.get("seasons_played", 0)

    ui.label(dynasty_name).classes("text-2xl font-bold text-slate-800")

    with ui.row().classes("w-full gap-3 flex-wrap mb-6"):
        metric_card("Year", str(current_year))
        metric_card("Seasons", str(seasons_played))
        metric_card("Coach", coach)
        metric_card("Team", team)

    with ui.row().classes("w-full gap-4 flex-wrap"):
        with ui.card().classes(
            "p-4 flex-1 min-w-[200px] cursor-pointer hover:shadow-lg transition-shadow"
        ).on("click", lambda: switch_fn("Play")):
            with ui.row().classes("items-center gap-2"):
                ui.icon("play_arrow").classes("text-2xl text-teal-500")
                ui.label("Start Next Season").classes("text-lg font-bold text-slate-700")
            ui.label("Configure and begin the next season of your dynasty.").classes(
                "text-sm text-slate-500 mt-1"
            )
