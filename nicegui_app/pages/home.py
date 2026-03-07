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

    # ── Mode cards ───────────────────────────────────────────────
    with ui.row().classes("w-full gap-6 flex-wrap justify-center mt-4"):
        # New Season
        with ui.card().classes(
            "p-6 w-80 cursor-pointer hover:shadow-lg transition-shadow"
        ).on("click", lambda: switch_fn("Play")):
            with ui.row().classes("items-center gap-3 mb-3"):
                ui.icon("sports_football").classes("text-3xl text-indigo-500")
                ui.label("New Season").classes("text-xl font-bold text-slate-800")
            ui.label(
                "Run a full CVL season with conferences, playoffs, and bowl games. "
                "Coach one or more teams through a 12-week season."
            ).classes("text-sm text-slate-500 leading-relaxed")
            with ui.row().classes("mt-4 gap-2"):
                ui.badge("12 weeks").props("outline color=indigo")
                ui.badge("Playoffs").props("outline color=indigo")
                ui.badge("Bowl Games").props("outline color=indigo")

        # Quick Game
        with ui.card().classes(
            "p-6 w-80 cursor-pointer hover:shadow-lg transition-shadow"
        ).on("click", lambda: switch_fn("Play")):
            with ui.row().classes("items-center gap-3 mb-3"):
                ui.icon("bolt").classes("text-3xl text-amber-500")
                ui.label("Quick Game").classes("text-xl font-bold text-slate-800")
            ui.label(
                "Pick two teams and play a single exhibition game. "
                "Choose offensive styles, weather, and see full box scores."
            ).classes("text-sm text-slate-500 leading-relaxed")
            with ui.row().classes("mt-4 gap-2"):
                ui.badge("Exhibition").props("outline color=amber")
                ui.badge("Custom Styles").props("outline color=amber")
                ui.badge("Box Score").props("outline color=amber")

        # DraftyQueenz
        with ui.card().classes(
            "p-6 w-80 cursor-pointer hover:shadow-lg transition-shadow"
        ).on("click", lambda: switch_fn("Play")):
            with ui.row().classes("items-center gap-3 mb-3"):
                ui.icon("casino").classes("text-3xl text-emerald-500")
                ui.label("DraftyQueenz").classes("text-xl font-bold text-slate-800")
            ui.label(
                "Fantasy betting game with salary caps and parlays. "
                "Build lineups, place bets, and compete against the house."
            ).classes("text-sm text-slate-500 leading-relaxed")
            with ui.row().classes("mt-4 gap-2"):
                ui.badge("Fantasy").props("outline color=green")
                ui.badge("Betting").props("outline color=green")
                ui.badge("$5M Cap").props("outline color=green")

    # ── Secondary modes ──────────────────────────────────────────
    with ui.row().classes("w-full gap-6 flex-wrap justify-center mt-6"):
        # Pro Leagues
        with ui.card().classes(
            "p-5 w-60 cursor-pointer hover:shadow-lg transition-shadow"
        ).on("click", lambda: switch_fn("Pro Leagues")):
            with ui.row().classes("items-center gap-2 mb-2"):
                ui.icon("stadium").classes("text-2xl text-purple-500")
                ui.label("Pro Leagues").classes("text-lg font-bold text-slate-800")
            ui.label(
                "NVL spectator mode — watch pro seasons, browse stats, place bets."
            ).classes("text-sm text-slate-500")

        # WVL
        with ui.card().classes(
            "p-5 w-60 cursor-pointer hover:shadow-lg transition-shadow"
        ).on("click", lambda: switch_fn("WVL")):
            with ui.row().classes("items-center gap-2 mb-2"):
                ui.icon("emoji_events").classes("text-2xl text-rose-500")
                ui.label("WVL Owner Mode").classes("text-lg font-bold text-slate-800")
            ui.label(
                "Multi-tier franchise management with promotion, relegation, and drafts."
            ).classes("text-sm text-slate-500")

        # International
        with ui.card().classes(
            "p-5 w-60 cursor-pointer hover:shadow-lg transition-shadow"
        ).on("click", lambda: switch_fn("International")):
            with ui.row().classes("items-center gap-2 mb-2"):
                ui.icon("public").classes("text-2xl text-sky-500")
                ui.label("International").classes("text-lg font-bold text-slate-800")
            ui.label(
                "FIV tournament — 5-nation international competition."
            ).classes("text-sm text-slate-500")

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
