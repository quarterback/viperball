"""Pro Leagues spectator dashboard for the NiceGUI Viperball app.

Spectator-only mode: browse standings, stats, box scores, playoffs.
No team management. Users watch seasons unfold and bet via DraftyQueenz.
"""

from __future__ import annotations

import logging
_log = logging.getLogger("viperball.pro_leagues")

from nicegui import ui, run, app
from nicegui_app.components import metric_card, stat_table

from engine.pro_league import (
    ProLeagueSeason, ALL_LEAGUE_CONFIGS,
    archive_season, get_completed_leagues, create_champions_league,
)
from engine.draftyqueenz import (
    DraftyQueenzManager, generate_game_odds, GameOdds,
    MIN_BET, MAX_BET, STARTING_BANKROLL, PARLAY_MULTIPLIERS,
    _prob_to_american,
)


_pro_sessions: dict[str, ProLeagueSeason] = {}
_pro_dq_managers: dict[str, DraftyQueenzManager] = {}


def _get_all_user_sessions() -> dict[str, tuple[str, ProLeagueSeason, DraftyQueenzManager]]:
    """Return {league_id: (session_id, season, dq_mgr)} for all active leagues."""
    sessions_map: dict = app.storage.user.get("pro_league_sessions") or {}
    result = {}
    stale_keys = []
    for league_id, sid in sessions_map.items():
        if sid in _pro_sessions:
            season = _pro_sessions[sid]
            dq = _pro_dq_managers.get(sid)
            if dq is None:
                dq = DraftyQueenzManager(manager_name=f"{season.config.league_name} Bettor")
                _pro_dq_managers[sid] = dq
            result[league_id] = (sid, season, dq)
        else:
            stale_keys.append(league_id)
    if stale_keys:
        for k in stale_keys:
            sessions_map.pop(k, None)
        app.storage.user["pro_league_sessions"] = sessions_map
    return result


def _get_active_league_id() -> str | None:
    """Return the league_id the user is currently viewing."""
    return app.storage.user.get("pro_league_active")


def _set_active_league(league_id: str | None):
    """Set which league the user is currently viewing."""
    app.storage.user["pro_league_active"] = league_id


def _register_session(league_id: str, sid: str, season: ProLeagueSeason, dq: DraftyQueenzManager):
    """Register a new league session in both the global store and the user's session map."""
    _pro_sessions[sid] = season
    _pro_dq_managers[sid] = dq
    sessions_map: dict = app.storage.user.get("pro_league_sessions") or {}
    sessions_map[league_id] = sid
    app.storage.user["pro_league_sessions"] = sessions_map
    _set_active_league(league_id)


def _unregister_session(league_id: str):
    """Remove a league session from the user's map and global store."""
    sessions_map: dict = app.storage.user.get("pro_league_sessions") or {}
    sid = sessions_map.pop(league_id, None)
    app.storage.user["pro_league_sessions"] = sessions_map
    if sid:
        if sid in _pro_sessions:
            archive_season(_pro_sessions[sid])
            del _pro_sessions[sid]
        _pro_dq_managers.pop(sid, None)
    if _get_active_league_id() == league_id:
        _set_active_league(None)


def _get_session_and_dq():
    """Get the currently active league's season and DQ manager.

    Supports both new multi-session storage and legacy single-session storage.
    """
    # New multi-session path
    active_lid = _get_active_league_id()
    if active_lid:
        all_sessions = _get_all_user_sessions()
        if active_lid in all_sessions:
            sid, season, dq = all_sessions[active_lid]
            return season, dq, sid

    # Legacy single-session fallback
    sid = app.storage.user.get("pro_league_session_id")
    if sid and sid in _pro_sessions:
        season = _pro_sessions[sid]
        dq = _pro_dq_managers.get(sid)
        if dq is None:
            league_name = season.config.league_name
            dq = DraftyQueenzManager(manager_name=f"{league_name} Bettor")
            _pro_dq_managers[sid] = dq
        # Migrate to new multi-session storage
        league_id = season.config.league_id
        sessions_map: dict = app.storage.user.get("pro_league_sessions") or {}
        sessions_map[league_id] = sid
        app.storage.user["pro_league_sessions"] = sessions_map
        _set_active_league(league_id)
        return season, dq, sid
    if sid and sid not in _pro_sessions:
        app.storage.user["pro_league_session_id"] = None
    return None, None, None


def _create_season_sync(config) -> tuple[str, 'ProLeagueSeason']:
    """CPU-bound season creation. No NiceGUI context access here."""
    import uuid
    sid = str(uuid.uuid4())[:8]
    season = ProLeagueSeason(config)
    return sid, season


# League display metadata
_LEAGUE_META = {
    "nvl": {"color": "indigo", "icon": "stadium", "desc": "Men's professional Viperball. 24 teams, 4 divisions. The flagship league."},
    "el": {"color": "blue", "icon": "public", "desc": "European & Nordic pro Viperball. 10 teams, 2 divisions."},
    "al": {"color": "amber", "icon": "public", "desc": "African pro Viperball. 12 teams, 2 divisions."},
    "pl": {"color": "teal", "icon": "public", "desc": "Asia-Pacific pro Viperball. 8 teams, 2 divisions."},
    "la_league": {"color": "red", "icon": "public", "desc": "Latin American pro Viperball. 10 teams, 2 divisions."},
    "cl": {"color": "amber", "icon": "emoji_events", "desc": "Cross-league tournament. Top 2 from each completed league."},
}


def _render_league_start_card(config, meta):
    """Render a start card for a single league."""
    from engine.pro_league import DATA_DIR
    import json

    with ui.card().classes("p-5 max-w-md").style("border: 1px solid #e2e8f0;"):
        with ui.row().classes("items-center gap-2 mb-2"):
            ui.icon(meta["icon"]).classes(f"text-{meta['color']}-600 text-xl")
            ui.label(config.league_name).classes(f"text-lg font-bold text-{meta['color']}-700")
        ui.label(meta["desc"]).classes("text-xs text-slate-500 mb-2")
        ui.label(f"{config.calendar_start}–{config.calendar_end}").classes("text-xs text-slate-400 mb-2")

        num_teams = sum(len(v) for v in config.divisions.values())
        num_divs = len(config.divisions)
        ui.label(f"{num_teams} teams  |  {num_divs} divisions  |  {config.games_per_season} games").classes("text-xs text-slate-600 mb-2")

        with ui.expansion("Teams", icon="groups").classes("w-full text-xs"):
            for div_name, team_keys in config.divisions.items():
                ui.label(f"{div_name} Division").classes("text-xs font-bold text-slate-600 mt-1")
                for key in team_keys:
                    fp = DATA_DIR.parent / config.teams_dir / f"{key}.json"
                    try:
                        with open(fp) as f:
                            info = json.load(f)
                        name = info["team_info"]["school_name"]
                    except Exception:
                        name = key
                    ui.label(f"  {name}").classes("text-xs text-slate-500")

        league_id = config.league_id

        async def _start(lid=league_id, cfg=config):
            try:
                ui.notify(f"Creating {cfg.league_name} season...", type="info")
                sid, new_season = await run.io_bound(_create_season_sync, cfg)
                dq = DraftyQueenzManager(manager_name=f"{cfg.league_name} Bettor")
                _register_session(lid, sid, new_season, dq)
                app.storage.user["pro_league_pending_nav"] = True
                ui.navigate.to("/")
            except Exception as e:
                ui.notify(f"Failed to create season: {e}", type="negative")

        ui.button(
            f"Start {config.league_name.split()[-1] if len(config.league_name.split()) > 1 else config.league_name} Season",
            icon="play_arrow", on_click=_start,
        ).props(f"color={meta['color']} no-caps").classes("mt-2 w-full")


def _render_champions_league_card(completed: dict):
    """Render the Champions League start card when ≥2 leagues have completed."""
    meta = _LEAGUE_META["cl"]
    num_teams = len(completed) * 2
    league_names = [snap["league_name"] for snap in completed.values()]

    with ui.card().classes("p-5 w-full max-w-2xl").style(
        "border: 2px solid #f59e0b; background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);"
    ):
        with ui.row().classes("items-center gap-2 mb-2"):
            ui.icon(meta["icon"]).classes("text-amber-600 text-2xl")
            ui.label("Champions League").classes("text-xl font-bold text-amber-700")
        ui.label(meta["desc"]).classes("text-xs text-slate-500 mb-3")

        ui.label(f"{num_teams} teams from {len(completed)} leagues").classes("text-sm font-semibold text-slate-700 mb-2")

        for league_id, snap in completed.items():
            abbr = league_id.upper().replace("_LEAGUE", "")
            champ_marker = ""
            qualifiers = []
            for t in snap["top_teams"]:
                marker = " (Champion)" if t.get("is_champion") else ""
                qualifiers.append(f"{t['team_name']} {t['wins']}-{t['losses']}{marker}")
            ui.label(f"{abbr}: {', '.join(qualifiers)}").classes("text-xs text-slate-600")

        async def _start_cl():
            try:
                ui.notify("Creating Champions League...", type="info")
                sid, cl_season = await run.io_bound(
                    lambda: _create_cl_sync()
                )
                dq = DraftyQueenzManager(manager_name="Champions League Bettor")
                _register_session("cl", sid, cl_season, dq)
                app.storage.user["pro_league_pending_nav"] = True
                ui.navigate.to("/")
            except Exception as e:
                ui.notify(f"Failed to create Champions League: {e}", type="negative")

        ui.button(
            "Start Champions League",
            icon="emoji_events", on_click=_start_cl,
        ).props("color=amber no-caps").classes("mt-3 w-full")


def _create_cl_sync():
    """CPU-bound CL creation. No NiceGUI context."""
    import uuid
    sid = str(uuid.uuid4())[:8]
    season = create_champions_league()
    return sid, season


# ═══════════════════════════════════════════════════════════════════════
# CALENDAR MONTHS — used for the World Calendar timeline
# ═══════════════════════════════════════════════════════════════════════

_MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
_MONTH_ABBR = {m: m[:3] for m in _MONTH_ORDER}
_MONTH_IDX = {m: i for i, m in enumerate(_MONTH_ORDER)}


def _months_in_range(start: str, end: str) -> list[int]:
    """Return list of month indices (0-11) for a calendar range, wrapping around year end."""
    s = _MONTH_IDX.get(start, 0)
    e = _MONTH_IDX.get(end, 11)
    if s <= e:
        return list(range(s, e + 1))
    return list(range(s, 12)) + list(range(0, e + 1))


def _league_phase_label(season: ProLeagueSeason) -> str:
    """Return a human-readable phase label for a league season."""
    if season.champion:
        return "Complete"
    if season.phase == "playoffs":
        return "Playoffs"
    pct = season.current_week / max(1, season.total_weeks)
    if pct == 0:
        return "Not Started"
    if pct < 0.5:
        return f"Week {season.current_week}/{season.total_weeks}"
    return f"Week {season.current_week}/{season.total_weeks}"


def _render_league_hub(all_sessions: dict):
    """Render the League Hub — 'World of Viperball' dashboard.

    Shows all leagues with their calendar windows, current status,
    and allows starting new leagues or jumping into active ones.
    """
    ui.label("World of Viperball").classes("text-2xl font-bold text-slate-800")
    ui.label(
        "Global professional Viperball — all leagues run concurrently across the calendar year. "
        "Start multiple leagues and switch between them freely."
    ).classes("text-sm text-slate-500 mb-4")

    # ── World Calendar Timeline ──────────────────────────────────
    completed = get_completed_leagues()

    with ui.card().classes("w-full p-4 mb-4").style(
        "border: 1px solid #e2e8f0; background: #f8fafc;"
    ):
        ui.label("Viperball World Calendar").classes("text-sm font-bold text-slate-700 mb-3")

        # Month header row
        with ui.row().classes("w-full gap-0 mb-1"):
            ui.element("div").classes("min-w-[100px]")  # label column spacer
            for m in _MONTH_ORDER:
                with ui.element("div").classes("flex-1 text-center"):
                    ui.label(_MONTH_ABBR[m]).classes("text-[10px] font-bold text-slate-400")

        # League rows
        for lid, config in ALL_LEAGUE_CONFIGS.items():
            meta = _LEAGUE_META.get(lid, {"color": "gray", "icon": "public", "desc": ""})
            active_months = set(_months_in_range(config.calendar_start, config.calendar_end))
            has_session = lid in all_sessions

            with ui.row().classes("w-full gap-0 items-center"):
                with ui.element("div").classes("min-w-[100px]"):
                    label_classes = f"text-xs font-semibold text-{meta['color']}-700"
                    if has_session:
                        label_classes += " underline"
                    ui.label(config.league_name.split()[-1] if len(config.league_name.split()) > 1 else config.league_name).classes(label_classes)

                for i in range(12):
                    with ui.element("div").classes("flex-1 h-5"):
                        if i in active_months:
                            if has_session:
                                _, season, _ = all_sessions[lid]
                                if season.champion:
                                    bg = f"bg-{meta['color']}-200"
                                elif season.phase == "playoffs":
                                    bg = f"bg-{meta['color']}-500"
                                else:
                                    bg = f"bg-{meta['color']}-400"
                            elif lid in completed:
                                bg = f"bg-{meta['color']}-200"
                            else:
                                bg = f"bg-{meta['color']}-100"
                            ui.element("div").classes(f"w-full h-full {bg} rounded-sm").style(
                                "min-height: 16px;"
                            )

        # Legend
        with ui.row().classes("mt-2 gap-4"):
            with ui.row().classes("items-center gap-1"):
                ui.element("div").classes("w-3 h-3 bg-indigo-100 rounded-sm")
                ui.label("Not started").classes("text-[10px] text-slate-400")
            with ui.row().classes("items-center gap-1"):
                ui.element("div").classes("w-3 h-3 bg-indigo-400 rounded-sm")
                ui.label("In season").classes("text-[10px] text-slate-400")
            with ui.row().classes("items-center gap-1"):
                ui.element("div").classes("w-3 h-3 bg-indigo-500 rounded-sm")
                ui.label("Playoffs").classes("text-[10px] text-slate-400")
            with ui.row().classes("items-center gap-1"):
                ui.element("div").classes("w-3 h-3 bg-indigo-200 rounded-sm")
                ui.label("Complete").classes("text-[10px] text-slate-400")

    # ── Active Leagues Section ───────────────────────────────────
    if all_sessions:
        ui.label("Active Leagues").classes("text-lg font-bold text-slate-700 mb-2")
        with ui.row().classes("gap-3 flex-wrap mb-4"):
            for lid, (sid, season, dq) in all_sessions.items():
                meta = _LEAGUE_META.get(lid, {"color": "gray", "icon": "public", "desc": ""})
                config = season.config
                league_abbr = lid.upper().replace("_LEAGUE", "")
                st = season.get_status()
                phase_label = _league_phase_label(season)

                with ui.card().classes("p-4 min-w-[240px] max-w-[300px] cursor-pointer").style(
                    f"border: 2px solid var(--q-{meta['color']}); border-radius: 10px;"
                ):
                    with ui.row().classes("items-center gap-2 mb-1"):
                        ui.icon(meta["icon"]).classes(f"text-{meta['color']}-600")
                        ui.label(config.league_name).classes(f"text-sm font-bold text-{meta['color']}-700")
                    ui.label(f"{config.calendar_start}–{config.calendar_end}").classes("text-[10px] text-slate-400")

                    with ui.row().classes("gap-3 mt-2"):
                        metric_card("Week", f"{st['current_week']}/{st['total_weeks']}")
                        metric_card("Phase", phase_label)

                    if st["champion_name"]:
                        ui.label(f"Champion: {st['champion_name']}").classes(
                            "text-xs font-bold text-green-600 mt-1"
                        )

                    with ui.row().classes("gap-2 mt-2"):
                        async def _enter(l=lid):
                            _set_active_league(l)
                            app.storage.user["pro_league_pending_nav"] = True
                            ui.navigate.to("/")

                        if st["champion"]:
                            ui.button("View Results", icon="visibility", on_click=_enter).props(
                                f"color={meta['color']} outline no-caps size=sm"
                            ).classes("flex-1")
                        else:
                            ui.button("Enter League", icon="play_arrow", on_click=_enter).props(
                                f"color={meta['color']} no-caps size=sm"
                            ).classes("flex-1")

        ui.separator().classes("my-3")

    # ── Start New Leagues ────────────────────────────────────────
    started_ids = set(all_sessions.keys()) | set(completed.keys())
    available = {lid: cfg for lid, cfg in ALL_LEAGUE_CONFIGS.items() if lid not in all_sessions}

    if available:
        ui.label("Start a New League").classes("text-lg font-bold text-slate-700 mb-2")
        with ui.row().classes("gap-4 flex-wrap"):
            for lid, config in available.items():
                meta = _LEAGUE_META.get(lid, {"color": "gray", "icon": "public", "desc": ""})
                _render_league_start_card(config, meta)

    # Champions League card — appears when ≥2 leagues are completed
    cl_completed = get_completed_leagues()
    if len(cl_completed) >= 2 and "cl" not in all_sessions:
        ui.separator().classes("my-4")
        _render_champions_league_card(cl_completed)


def _render_league_switcher(all_sessions: dict, active_lid: str):
    """Render a horizontal bar for switching between active leagues and returning to the hub."""
    if not all_sessions and not active_lid:
        return

    with ui.element("div").classes("w-full mb-3").style(
        "background: linear-gradient(135deg, #1e293b 0%, #334155 100%); "
        "border-radius: 8px; padding: 8px 16px;"
    ):
        with ui.row().classes("w-full items-center gap-2 flex-wrap"):
            # Hub button
            async def _go_hub():
                _set_active_league(None)
                app.storage.user["pro_league_pending_nav"] = True
                ui.navigate.to("/")

            ui.button("League Hub", icon="public", on_click=_go_hub).props(
                "flat dense no-caps size=sm text-color=white"
            ).classes("text-slate-300 hover:text-white")

            ui.label("|").classes("text-slate-500 text-xs mx-1")

            # League buttons
            for lid, (sid, season, dq) in all_sessions.items():
                meta = _LEAGUE_META.get(lid, {"color": "gray", "icon": "public", "desc": ""})
                config = season.config
                abbr = lid.upper().replace("_LEAGUE", "")
                is_active = lid == active_lid

                phase_icon = ""
                if season.champion:
                    phase_icon = " (done)"
                elif season.phase == "playoffs":
                    phase_icon = " (playoffs)"

                async def _switch(l=lid):
                    _set_active_league(l)
                    app.storage.user["pro_league_pending_nav"] = True
                    ui.navigate.to("/")

                btn = ui.button(
                    f"{abbr}{phase_icon}", icon=meta["icon"], on_click=_switch
                ).props(f"{'unelevated' if is_active else 'flat'} dense no-caps size=sm")
                if is_active:
                    btn.classes(f"bg-{meta['color']}-600 text-white")
                else:
                    btn.classes("text-slate-300 hover:text-white")


async def render_pro_leagues_section(state, shared):
    all_sessions = _get_all_user_sessions()
    active_lid = _get_active_league_id()

    # If we have an active league selected and it exists, show that league
    if active_lid and active_lid in all_sessions:
        season, dq_mgr, session_id = _get_session_and_dq()
    elif active_lid and active_lid not in all_sessions:
        # Active league was cleared, fall back
        _set_active_league(None)
        active_lid = None
        season, dq_mgr, session_id = None, None, None
    else:
        season, dq_mgr, session_id = _get_session_and_dq()

    if not season:
        # ═══════════════════════════════════════════════════════════
        # LEAGUE HUB — "World of Viperball" dashboard
        # ═══════════════════════════════════════════════════════════
        _render_league_hub(all_sessions)
        return

    # ═══════════════════════════════════════════════════════════
    # ACTIVE LEAGUE VIEW — show league switcher bar + season
    # ═══════════════════════════════════════════════════════════
    _render_league_switcher(all_sessions, active_lid or season.config.league_id)

    dq_box = ui.row().classes("w-full gap-4 flex-wrap mb-2")

    def _fill_dq_summary():
        dq_box.clear()
        with dq_box:
            metric_card("DQ$ Balance", f"${dq_mgr.bankroll.balance:,}")
            picks_made = dq_mgr.total_picks_made
            picks_won = dq_mgr.total_picks_won
            pct = (picks_won / picks_made * 100) if picks_made > 0 else 0
            metric_card("Pick Record", f"{picks_won}/{picks_made} ({pct:.0f}%)")
            roi = ((dq_mgr.bankroll.balance - STARTING_BANKROLL) / STARTING_BANKROLL * 100)
            metric_card("ROI", f"{roi:+.1f}%")

    _fill_dq_summary()

    containers = {}

    def _refresh_container(name, render_fn, *args):
        c = containers.get(name)
        if c is None:
            return
        c.clear()
        with c:
            try:
                render_fn(*args)
            except Exception as e:
                _log.error(f"Error rendering {name}: {e}", exc_info=True)
                ui.label(f"Error: {e}").classes("text-red-500 text-sm")

    def _refresh_all_tabs():
        _log.info(f"_refresh_all_tabs: week={season.current_week}")
        _fill_dq_summary()
        _refresh_container("standings", _render_standings, season)
        _refresh_container("schedule", _render_schedule, season)
        _refresh_container("stats", _render_stats, season)
        _refresh_container("playoffs", _render_playoffs, season)
        _refresh_container("teams", _render_teams, season)
        _refresh_container("betting", _render_betting, season, dq_mgr)
        _log.info("_refresh_all_tabs complete")

    with ui.tabs().classes("w-full") as tabs:
        tab_dash = ui.tab("Dashboard", icon="dashboard")
        tab_betting = ui.tab("Betting", icon="casino")
        tab_stand = ui.tab("Standings", icon="leaderboard")
        tab_sched = ui.tab("Schedule", icon="calendar_month")
        tab_stats = ui.tab("Stats", icon="bar_chart")
        tab_playoffs = ui.tab("Playoffs", icon="emoji_events")
        tab_teams = ui.tab("Teams", icon="groups")

    with ui.tab_panels(tabs, value=tab_dash).classes("w-full"):
        with ui.tab_panel(tab_dash):
            await _render_dashboard(season, dq_mgr, _refresh_all_tabs)
        with ui.tab_panel(tab_betting):
            containers["betting"] = ui.column().classes("w-full")
            with containers["betting"]:
                _render_betting(season, dq_mgr)
        with ui.tab_panel(tab_stand):
            containers["standings"] = ui.column().classes("w-full")
            with containers["standings"]:
                _render_standings(season)
        with ui.tab_panel(tab_sched):
            containers["schedule"] = ui.column().classes("w-full")
            with containers["schedule"]:
                _render_schedule(season)
        with ui.tab_panel(tab_stats):
            containers["stats"] = ui.column().classes("w-full")
            with containers["stats"]:
                _render_stats(season)
        with ui.tab_panel(tab_playoffs):
            containers["playoffs"] = ui.column().classes("w-full")
            with containers["playoffs"]:
                _render_playoffs(season)
        with ui.tab_panel(tab_teams):
            containers["teams"] = ui.column().classes("w-full")
            with containers["teams"]:
                _render_teams(season)


async def _render_dashboard(season: ProLeagueSeason, dq_mgr: DraftyQueenzManager, refresh_all_tabs=None):
    league_abbr = season.config.league_id.upper()
    league_name = season.config.league_name

    header_box = ui.column().classes("w-full")
    controls_box = ui.column().classes("w-full")
    results_box = ui.column().classes("w-full")

    def _fill_header():
        header_box.clear()
        with header_box:
            st = season.get_status()
            ui.label(f"{league_abbr} — {league_name}").classes("text-2xl font-bold text-slate-800")
            with ui.row().classes("w-full gap-4 flex-wrap mb-4"):
                metric_card("Phase", st["phase"].replace("_", " ").title())
                metric_card("Week", f"{st['current_week']} / {st['total_weeks']}")
                metric_card("Teams", st["team_count"])
                if st["champion"]:
                    metric_card("Champion", st["champion_name"])

    def _fill_results():
        results_box.clear()
        with results_box:
            if season.current_week > 0:
                last_week = season.current_week
                week_results = season.results.get(last_week, {})
                if week_results:
                    ui.label(f"Week {last_week} Results").classes("text-lg font-semibold mt-4 mb-2")
                    with ui.row().classes("w-full gap-3 flex-wrap"):
                        for mk, game in week_results.items():
                            with ui.card().classes("p-3 min-w-[220px]").style(
                                "border: 1px solid #e2e8f0; border-radius: 8px;"
                            ):
                                h_score = int(game["home_score"])
                                a_score = int(game["away_score"])
                                h_bold = "font-bold" if h_score > a_score else ""
                                a_bold = "font-bold" if a_score > h_score else ""
                                ui.label(f"{game['away_name']}").classes(f"text-sm {a_bold}")
                                ui.label(f"@ {game['home_name']}").classes(f"text-sm {h_bold}")
                                ui.label(f"{a_score} - {h_score}").classes("text-lg font-bold text-indigo-600 mt-1")

            if season.phase == "playoffs":
                bracket = season.get_playoff_bracket()
                if bracket.get("rounds"):
                    ui.label("Playoff Bracket").classes("text-lg font-semibold mt-4 mb-2")
                    for rd in bracket["rounds"]:
                        ui.label(rd["round_name"]).classes("text-sm font-bold text-indigo-600 mt-2")
                        if rd.get("bye_teams"):
                            bye_names = ", ".join(t["team_name"] for t in rd["bye_teams"])
                            ui.label(f"Byes: {bye_names}").classes("text-xs text-slate-500 italic")
                        for m in rd["matchups"]:
                            if m.get("winner"):
                                h = m["home"]["team_name"]
                                a = m["away"]["team_name"] if m.get("away") else "BYE"
                                hs = int(m.get("home_score", 0))
                                asc = int(m.get("away_score", 0))
                                winner = m.get("winner_name", "")
                                ui.label(f"  {a} {asc} @ {h} {hs} — {winner} wins").classes("text-xs text-slate-700")
                            else:
                                h = m["home"]["team_name"]
                                a = m["away"]["team_name"] if m.get("away") else "BYE"
                                ui.label(f"  {a} @ {h}").classes("text-xs text-slate-500")

    def _fill_controls():
        controls_box.clear()
        with controls_box:
            st = season.get_status()

            if st["champion"]:
                with ui.card().classes("p-4 bg-green-50 w-full"):
                    ui.label(f"Season Complete — {st['champion_name']} are {league_abbr} Champions!").classes(
                        "text-lg font-bold text-green-700"
                    )

                    # Show other active leagues the user can jump to
                    other_active = _get_all_user_sessions()
                    current_lid = season.config.league_id
                    other_leagues = {k: v for k, v in other_active.items() if k != current_lid}
                    if other_leagues:
                        ui.label("Other active leagues:").classes("text-sm text-slate-600 mt-2 mb-1")
                        with ui.row().classes("gap-2 flex-wrap"):
                            for olid, (_, oseas, _) in other_leagues.items():
                                ometa = _LEAGUE_META.get(olid, {"color": "gray", "icon": "public"})
                                oabbr = olid.upper().replace("_LEAGUE", "")
                                ost = oseas.get_status()
                                olabel = f"{oabbr} — Wk {ost['current_week']}/{ost['total_weeks']}"
                                if ost["champion_name"]:
                                    olabel = f"{oabbr} (done)"

                                async def _jump(l=olid):
                                    _set_active_league(l)
                                    app.storage.user["pro_league_pending_nav"] = True
                                    ui.navigate.to("/")

                                ui.button(olabel, icon=ometa["icon"], on_click=_jump).props(
                                    f"outline no-caps size=sm color={ometa['color']}"
                                )

                    with ui.row().classes("gap-2 mt-3"):
                        async def _back_to_hub():
                            # Archive but keep session alive for viewing
                            archive_season(season)
                            _set_active_league(None)
                            app.storage.user["pro_league_pending_nav"] = True
                            ui.navigate.to("/")

                        ui.button("Back to League Hub", icon="public", on_click=_back_to_hub).props(
                            "color=indigo no-caps"
                        )

                        async def _new():
                            current_lid = season.config.league_id
                            _unregister_session(current_lid)
                            app.storage.user["pro_league_pending_nav"] = True
                            ui.navigate.to("/")

                        ui.button("Restart This League", icon="replay", on_click=_new).props(
                            "color=green outline no-caps"
                        )
                return

            with ui.row().classes("gap-3"):
                if st["phase"] == "regular_season" and st["current_week"] < st["total_weeks"]:
                    async def _sim_week():
                        next_week = season.current_week + 1
                        _log.info(f"_sim_week starting week {next_week}")
                        await run.io_bound(season.sim_week)
                        _log.info(f"_sim_week done, now week {season.current_week}")
                        _resolve_dq_bets(season, dq_mgr, next_week)
                        _refresh_everything()

                    ui.button("Sim Week", icon="skip_next", on_click=_sim_week).props("color=indigo no-caps")

                    async def _sim_all():
                        start_week = season.current_week + 1
                        await run.io_bound(season.sim_all)
                        for w in range(start_week, season.current_week + 1):
                            _resolve_dq_bets(season, dq_mgr, w)
                        _refresh_everything()

                    ui.button("Sim All", icon="fast_forward", on_click=_sim_all).props("color=blue no-caps")

                if st["phase"] == "regular_season" and st["current_week"] >= st["total_weeks"]:
                    async def _start_playoffs():
                        await run.io_bound(season.start_playoffs)
                        _refresh_everything()

                    ui.button("Start Playoffs", icon="emoji_events", on_click=_start_playoffs).props("color=amber no-caps")

                if st["phase"] == "playoffs" and not st["champion"]:
                    async def _advance():
                        await run.io_bound(season.advance_playoffs)
                        _refresh_everything()

                    ui.button("Advance Playoffs", icon="skip_next", on_click=_advance).props("color=amber no-caps")

    def _refresh_everything():
        _log.info(f"_refresh_everything: week={season.current_week}, phase={season.phase}")
        try:
            _fill_header()
        except Exception as e:
            _log.error(f"header refresh failed: {e}", exc_info=True)
        try:
            _fill_controls()
        except Exception as e:
            _log.error(f"controls refresh failed: {e}", exc_info=True)
        try:
            _fill_results()
        except Exception as e:
            _log.error(f"results refresh failed: {e}", exc_info=True)
        if refresh_all_tabs:
            try:
                refresh_all_tabs()
            except Exception as e:
                _log.error(f"tab refresh failed: {e}", exc_info=True)
        _log.info("_refresh_everything complete")

    _fill_header()
    _fill_controls()
    _fill_results()


def _resolve_dq_bets(season: ProLeagueSeason, dq_mgr: DraftyQueenzManager, week: int):
    contest = dq_mgr.weekly_contests.get(week)
    if not contest or contest.resolved:
        return
    game_results = season.build_dq_game_results(week)
    if game_results:
        dq_mgr.resolve_week(week, game_results)


def _generate_nvl_odds(season: ProLeagueSeason, week: int) -> list:
    if week < 1 or week > season.total_weeks:
        return []
    matchups = season.schedule[week - 1]
    odds_list = []
    import random as _rng
    rng = _rng.Random(week * 7919)
    for m in matchups:
        home = season.teams.get(m.home_key)
        away = season.teams.get(m.away_key)
        if not home or not away:
            continue
        h_rec = season.get_team_record(m.home_key)
        a_rec = season.get_team_record(m.away_key)
        odds = generate_game_odds(
            home.name, away.name, home.prestige, away.prestige,
            h_rec, a_rec, rng,
        )
        odds_list.append(odds)
    return odds_list


def _render_betting(season: ProLeagueSeason, dq_mgr: DraftyQueenzManager):
    league_abbr = season.config.league_id.upper().replace("_LEAGUE", "")
    ui.label(f"DraftyQueenz — {league_abbr} Betting").classes("text-xl font-bold text-slate-800 mb-2")

    balance = dq_mgr.bankroll.balance

    if season.phase != "regular_season" or season.current_week >= season.total_weeks:
        _render_betting_history(dq_mgr)
        return

    next_week = season.current_week + 1

    contest = dq_mgr.weekly_contests.get(next_week)
    if contest is None:
        odds_list = _generate_nvl_odds(season, next_week)
        from engine.draftyqueenz import WeeklyContest
        contest = WeeklyContest(week=next_week)
        contest.odds = odds_list
        dq_mgr.weekly_contests[next_week] = contest

    odds_list = contest.odds
    if not odds_list:
        ui.label("No games available for betting this week.").classes("text-sm text-slate-500")
        return

    ui.label(f"Week {next_week} — {len(odds_list)} games | Balance: ${balance:,} DQ$").classes(
        "text-sm text-slate-500 mb-3"
    )

    existing_picks = contest.picks
    existing_parlays = contest.parlays

    if existing_picks or existing_parlays:
        with ui.card().classes("w-full p-4 mb-4").style("border: 1px solid #e2e8f0; border-radius: 10px;"):
            if existing_picks:
                ui.label("Your Active Bets").classes("font-bold text-indigo-700")
                for p in existing_picks:
                    icon = ""
                    if p.result == "win":
                        icon = " [WIN]"
                    elif p.result == "loss":
                        icon = " [LOSS]"
                    ui.label(
                        f"  {p.pick_type.title()}: {p.selection} "
                        f"on {p.game_away} @ {p.game_home} — ${p.amount:,}{icon}"
                    ).classes("text-sm")
            if existing_parlays:
                ui.label("Your Parlays").classes("font-bold mt-2 text-indigo-700")
                for pl in existing_parlays:
                    legs_str = ", ".join(p.selection for p in pl.legs)
                    ui.label(
                        f"  {len(pl.legs)}-leg ({pl.multiplier}x): {legs_str} — ${pl.amount:,}"
                    ).classes("text-sm")

    ui.label("This Week's Lines").classes("font-bold text-indigo-600 mt-2 mb-1")
    for odds in odds_list:
        spread_str = f"{odds.spread:+.1f}"
        ou_str = f"{odds.over_under:.1f}"
        h_ml = _prob_to_american(odds.home_win_prob)
        a_ml = _prob_to_american(1 - odds.home_win_prob)
        h_ml_str = f"{h_ml:+d}" if h_ml != 0 else "EVEN"
        a_ml_str = f"{a_ml:+d}" if a_ml != 0 else "EVEN"
        h_rec = season.get_team_record(
            next((k for k, t in season.teams.items() if t.name == odds.home_team), "")
        )
        a_rec = season.get_team_record(
            next((k for k, t in season.teams.items() if t.name == odds.away_team), "")
        )
        h_rec_str = f"({h_rec[0]}-{h_rec[1]})" if h_rec else ""
        a_rec_str = f"({a_rec[0]}-{a_rec[1]})" if a_rec else ""

        with ui.card().classes("p-3 mb-2 w-full max-w-2xl").style("border: 1px solid #e2e8f0;"):
            with ui.row().classes("w-full items-center gap-4"):
                with ui.column().classes("flex-1"):
                    ui.label(f"{odds.away_team} {a_rec_str}").classes("text-sm font-semibold")
                    ui.label(f"ML {a_ml_str}").classes("text-xs text-slate-500")
                ui.label("@").classes("text-xs text-slate-400")
                with ui.column().classes("flex-1"):
                    ui.label(f"{odds.home_team} {h_rec_str}").classes("text-sm font-semibold")
                    ui.label(f"ML {h_ml_str}").classes("text-xs text-slate-500")
                with ui.column():
                    ui.label(f"Spread {spread_str}").classes("text-xs text-slate-600")
                    ui.label(f"O/U {ou_str}").classes("text-xs text-slate-600")

    ui.separator()
    ui.label("Place a Bet").classes("font-bold text-indigo-600")

    if balance < MIN_BET:
        ui.label(f"Insufficient balance (${balance:,}). Need at least ${MIN_BET:,} DQ$.").classes(
            "text-sm text-red-500"
        )
        _render_betting_history(dq_mgr)
        return

    game_labels = {i: f"{o.away_team} @ {o.home_team}" for i, o in enumerate(odds_list)}
    bet_type_labels = {
        "winner": "Winner",
        "spread": "Spread",
        "over_under": "Over / Under",
    }

    bet_state = {
        "game_idx": 0,
        "pick_type": "winner",
        "selection": odds_list[0].home_team if odds_list else "",
        "amount": min(500, min(MAX_BET, balance)),
    }

    pick_container = ui.column().classes("w-full")

    def _update_pick_options():
        pick_container.clear()
        sel_odds = odds_list[bet_state["game_idx"]] if bet_state["game_idx"] < len(odds_list) else None
        if not sel_odds:
            return
        if bet_state["pick_type"] in ("winner", "spread"):
            pick_options = [sel_odds.home_team, sel_odds.away_team]
        else:
            pick_options = ["over", "under"]
        bet_state["selection"] = pick_options[0]
        with pick_container:
            ui.radio(
                pick_options, value=pick_options[0],
                on_change=lambda e: bet_state.update(selection=e.value),
            ).props("inline")

    ui.select(
        game_labels, label="Game", value=0,
        on_change=lambda e: (
            bet_state.update(game_idx=e.value),
            _update_pick_options(),
        ),
    ).classes("w-full max-w-xl")

    ui.radio(
        bet_type_labels, value="winner",
        on_change=lambda e: (
            bet_state.update(pick_type=e.value),
            _update_pick_options(),
        ),
    ).props("inline")

    pick_container

    max_wager = min(MAX_BET, balance)
    default_wager = min(500, max_wager)

    with ui.row().classes("w-full gap-4 items-end max-w-xl"):
        with ui.column().classes("flex-[3]"):
            ui.slider(
                min=MIN_BET, max=max_wager, value=default_wager, step=250,
                on_change=lambda e: bet_state.update(amount=int(e.value)),
            ).classes("w-full")
            ui.label("Wager (DQ$)").classes("text-xs text-gray-500")
        with ui.column().classes("flex-1"):
            ui.number(
                "Exact", min=MIN_BET, max=max_wager, value=default_wager, step=250,
                on_change=lambda e: bet_state.update(
                    amount=int(e.value) if e.value is not None else default_wager
                ),
            ).classes("w-full")

    async def _place_bet():
        pick, err = contest.make_pick(
            dq_mgr.bankroll,
            bet_state["pick_type"],
            bet_state["game_idx"],
            bet_state["selection"],
            bet_state["amount"],
        )
        if err:
            ui.notify(err, type="negative")
        else:
            ui.notify(f"Bet placed! {bet_state['pick_type'].title()}: "
                       f"{bet_state['selection']} — ${bet_state['amount']:,} DQ$. "
                       f"Balance: ${dq_mgr.bankroll.balance:,}", type="positive")
            ui.navigate.to("/")

    ui.button("Place Bet", on_click=_place_bet, icon="casino").props(
        "color=indigo no-caps"
    ).classes("w-full max-w-xl mt-2")

    _update_pick_options()

    _render_betting_history(dq_mgr)


def _render_betting_history(dq_mgr: DraftyQueenzManager):
    resolved_weeks = [
        (w, c) for w, c in sorted(dq_mgr.weekly_contests.items())
        if c.resolved and (c.picks or c.parlays)
    ]
    if not resolved_weeks:
        return

    ui.separator()
    ui.label("Betting History").classes("font-bold text-indigo-600 mt-2")

    total_wagered = 0
    total_won = 0
    for w, c in resolved_weeks:
        for p in c.picks:
            total_wagered += p.amount
            total_won += p.payout
        for pl in c.parlays:
            total_wagered += pl.amount
            total_won += pl.payout

    with ui.row().classes("w-full gap-4 flex-wrap mb-2"):
        metric_card("Total Wagered", f"${total_wagered:,}")
        metric_card("Total Won", f"${total_won:,}")
        net = total_won - total_wagered
        metric_card("Net P/L", f"${net:+,}")

    columns = [
        {"name": "week", "label": "Week", "field": "week", "align": "center"},
        {"name": "bets", "label": "Bets", "field": "bets", "align": "center"},
        {"name": "won", "label": "Won", "field": "won", "align": "center"},
        {"name": "wagered", "label": "Wagered", "field": "wagered", "align": "right"},
        {"name": "payout", "label": "Payout", "field": "payout", "align": "right"},
        {"name": "net", "label": "Net", "field": "net", "align": "right"},
    ]
    rows = []
    for w, c in resolved_weeks:
        picks_won = sum(1 for p in c.picks if p.result == "win")
        wag = sum(p.amount for p in c.picks) + sum(pl.amount for pl in c.parlays)
        pay = sum(p.payout for p in c.picks) + sum(pl.payout for pl in c.parlays)
        rows.append({
            "week": str(w),
            "bets": str(len(c.picks) + len(c.parlays)),
            "won": str(picks_won),
            "wagered": f"${wag:,}",
            "payout": f"${pay:,}",
            "net": f"${pay - wag:+,}",
        })
    ui.table(columns=columns, rows=rows, row_key="week").classes("w-full max-w-2xl").props("dense flat bordered")


def _source_league_abbr(team_key: str) -> str:
    """Extract source league abbreviation from a CL prefixed team key."""
    # CL keys are like "nvl_nj", "el_sto", "la_league_mex"
    for lid in ALL_LEAGUE_CONFIGS:
        if team_key.startswith(lid + "_"):
            return lid.upper().replace("_LEAGUE", "")
    return ""


def _render_standings(season: ProLeagueSeason):
    standings = season.get_standings()
    is_cl = season.config.league_id == "cl"
    league_abbr = season.config.league_id.upper().replace("_LEAGUE", "")

    if is_cl:
        ui.label("Champions League Standings").classes("text-xl font-bold text-amber-700 mb-2")
    else:
        ui.label(f"{league_abbr} Division Standings").classes("text-xl font-bold text-slate-800 mb-2")
    ui.label(f"Week {standings['week']} of {standings['total_weeks']}").classes("text-sm text-slate-500 mb-4")

    for div_name, teams in standings["divisions"].items():
        if not is_cl:
            ui.label(f"{div_name} Division").classes("text-lg font-semibold text-indigo-600 mt-4 mb-1")

        columns = [
            {"name": "rank", "label": "#", "field": "rank", "align": "center", "sortable": False},
            {"name": "team", "label": "Team", "field": "team_name", "align": "left", "sortable": True},
        ]
        if is_cl:
            columns.append({"name": "league", "label": "League", "field": "league", "align": "center"})
        columns.extend([
            {"name": "record", "label": "W-L", "field": "record", "align": "center", "sortable": True},
            {"name": "pct", "label": "PCT", "field": "pct", "align": "center", "sortable": True},
            {"name": "pf", "label": "PF", "field": "pf", "align": "center", "sortable": True},
            {"name": "pa", "label": "PA", "field": "pa", "align": "center", "sortable": True},
            {"name": "diff", "label": "DIFF", "field": "diff", "align": "center", "sortable": True},
        ])
        if not is_cl:
            columns.extend([
                {"name": "div", "label": "DIV", "field": "div_record", "align": "center"},
            ])
        columns.extend([
            {"name": "streak", "label": "STR", "field": "streak", "align": "center"},
            {"name": "l5", "label": "L5", "field": "last_5", "align": "center"},
        ])

        rows = []
        for i, t in enumerate(teams):
            row = {
                "rank": i + 1,
                "team_name": t["team_name"],
                "record": f"{t['wins']}-{t['losses']}",
                "pct": f"{t['pct']:.3f}",
                "pf": t["pf"],
                "pa": t["pa"],
                "diff": f"{t['diff']:+d}",
                "streak": t["streak"],
                "last_5": t["last_5"],
            }
            if is_cl:
                row["league"] = _source_league_abbr(t["team_key"])
            else:
                row["div_record"] = t["div_record"]
            rows.append(row)

        ui.table(columns=columns, rows=rows, row_key="rank").classes(
            "w-full"
        ).props("dense flat bordered")


def _render_schedule(season: ProLeagueSeason):
    schedule = season.get_schedule()

    ui.label("Schedule & Results").classes("text-xl font-bold text-slate-800 mb-2")

    selected_week = {"val": season.current_week if season.current_week > 0 else 1}

    week_options = {w["week"]: f"Week {w['week']}" for w in schedule["weeks"]}

    week_box = ui.column().classes("w-full")

    def _fill_week():
        week_box.clear()
        with week_box:
            wk = selected_week["val"]
            week_data = None
            for w in schedule["weeks"]:
                if w["week"] == wk:
                    week_data = w
                    break
            if not week_data:
                ui.label("No games this week").classes("text-sm text-slate-500")
                return

            ui.label(f"Week {wk}").classes("text-lg font-semibold text-indigo-600 mb-2")

            for game in week_data["games"]:
                with ui.card().classes("p-3 mb-2 w-full max-w-xl").style("border: 1px solid #e2e8f0;"):
                    if game["completed"]:
                        h_score = int(game.get("home_score", 0))
                        a_score = int(game.get("away_score", 0))
                        h_bold = "font-bold" if h_score > a_score else ""
                        a_bold = "font-bold" if a_score > h_score else ""
                        with ui.row().classes("items-center gap-4"):
                            ui.label(f"{game['away_name']}").classes(f"text-sm {a_bold} min-w-[180px]")
                            ui.label(f"{a_score}").classes(f"text-lg {a_bold}")
                            ui.label("@").classes("text-xs text-slate-400")
                            ui.label(f"{h_score}").classes(f"text-lg {h_bold}")
                            ui.label(f"{game['home_name']}").classes(f"text-sm {h_bold}")

                        async def _show_box(mk=game["matchup_key"], w=wk):
                            box = season.get_box_score(w, mk)
                            if box:
                                _show_box_score_dialog(box, season)

                        ui.button("Box Score", icon="assessment", on_click=_show_box).props(
                            "flat dense no-caps size=sm color=indigo"
                        )
                    else:
                        with ui.row().classes("items-center gap-4"):
                            ui.label(f"{game['away_name']}").classes("text-sm min-w-[180px]")
                            ui.label("@").classes("text-xs text-slate-400")
                            ui.label(f"{game['home_name']}").classes("text-sm")
                            ui.label("Upcoming").classes("text-xs text-slate-400 italic")

    def _on_week_change(e):
        selected_week["val"] = e.value
        _fill_week()

    ui.select(
        options=week_options,
        value=selected_week["val"],
        label="Select Week",
        on_change=_on_week_change,
    ).classes("w-48 mb-4")

    _fill_week()


def _show_player_card(season: ProLeagueSeason, team_key: str, player_name: str):
    card_data = season.get_player_card(team_key, player_name)
    if not card_data:
        ui.notify(f"Player '{player_name}' not found.", type="warning")
        return

    bio = card_data["bio"]
    ratings = card_data["ratings"]
    stats = card_data.get("season_stats", {})

    with ui.dialog() as dlg, ui.card().classes("p-0 max-w-3xl").style("min-width:640px;"):
        with ui.column().classes("w-full p-0 gap-0"):
            with ui.element("div").classes(
                "w-full px-5 py-4"
            ).style("background:#013369; border-bottom:4px solid #D50A0A;"):
                ui.label(f"#{bio['number']} {bio['name']}").classes(
                    "text-2xl font-extrabold text-white tracking-tight"
                )
                ui.label(
                    f"{bio['position']} | {bio['team_name']}"
                ).classes("text-sm font-semibold").style("color:#B0B7BC;")

            with ui.element("div").classes("w-full px-5 py-3"):
                with ui.row().classes("w-full gap-6 flex-wrap"):
                    with ui.column().classes("gap-1").style("min-width:200px;"):
                        def _bio_line(label, value):
                            with ui.row().classes("gap-1 items-baseline"):
                                ui.label(f"{label}:").classes("text-xs font-bold text-slate-500")
                                ui.label(str(value)).classes("text-xs text-slate-800")

                        hometown = bio.get("hometown_city", "")
                        state = bio.get("hometown_state", "")
                        loc = f"{hometown}, {state}" if hometown and state else hometown or state

                        _bio_line("Position", bio.get("position", ""))
                        if bio.get("height"):
                            _bio_line("Height", bio["height"])
                        if bio.get("weight"):
                            _bio_line("Weight", f"{bio['weight']} lbs")
                        if loc:
                            _bio_line("Hometown", loc)
                        arch = bio.get("archetype", "none")
                        if arch and arch != "none":
                            _bio_line("Archetype", arch.replace("_", " ").title())
                        var_arch = bio.get("variance_archetype", "")
                        if var_arch:
                            _bio_line("Play Style", var_arch.title())
                        div_name = bio.get("division", "")
                        if div_name:
                            _bio_line("Division", f"{div_name}")
                        _bio_line("Team Record", bio.get("team_record", "0-0"))

                    with ui.column().classes("gap-1 flex-1"):
                        ovr = ratings.get("overall", 0)
                        ovr_color = "#16a34a" if ovr >= 85 else ("#d97706" if ovr >= 75 else "#64748b")
                        ui.label(f"OVR").classes("text-[10px] font-bold text-slate-400 mb-0")
                        ui.label(str(ovr)).classes("text-4xl font-extrabold mb-2").style(f"color:{ovr_color}; line-height:1;")

                        rating_display = [
                            ("SPD", "speed"), ("STA", "stamina"), ("KICK", "kicking"),
                            ("LAT", "lateral_skill"), ("TKL", "tackling"), ("AGI", "agility"),
                            ("PWR", "power"), ("AWR", "awareness"), ("HND", "hands"),
                            ("KPW", "kick_power"), ("KAC", "kick_accuracy"),
                        ]

                        with ui.element("div").classes("flex flex-wrap gap-1"):
                            for abbr, key in rating_display:
                                val = ratings.get(key, 0)
                                if val >= 85:
                                    bg = "#dcfce7"; fg = "#166534"; bd = "#86efac"
                                elif val >= 75:
                                    bg = "#dbeafe"; fg = "#1e40af"; bd = "#93c5fd"
                                elif val >= 65:
                                    bg = "#fef3c7"; fg = "#92400e"; bd = "#fcd34d"
                                else:
                                    bg = "#f1f5f9"; fg = "#475569"; bd = "#cbd5e1"
                                with ui.element("div").classes(
                                    "flex flex-col items-center px-1.5 py-0.5 rounded"
                                ).style(f"background:{bg}; color:{fg}; border:1px solid {bd}; min-width:42px;"):
                                    ui.label(abbr).classes("text-[9px] font-bold leading-tight")
                                    ui.label(str(val)).classes("text-xs font-extrabold leading-tight")

            with ui.element("div").classes("w-full px-5 py-3").style(
                "border-top:1px solid #e2e8f0;"
            ):
                if stats and stats.get("games", 0) > 0:
                    gp = stats.get("games", 0)

                    rush_yds = stats.get("rushing_yards", 0)
                    rush_car = stats.get("rushing_carries", 0)
                    tds = stats.get("touchdowns", 0)
                    kp_yds = stats.get("kick_pass_yards", 0)
                    kp_comp = stats.get("kick_pass_completions", 0)
                    kp_att = stats.get("kick_pass_attempts", 0)
                    lat_yds = stats.get("lateral_yards", 0)
                    laterals = stats.get("laterals", 0)
                    dk_made = stats.get("dk_made", 0)
                    dk_att = stats.get("dk_attempted", 0)
                    tackles = stats.get("tackles", 0)
                    fumbles = stats.get("fumbles", 0)
                    total_yds = stats.get("total_yards", 0)

                    has_offense = rush_yds > 0 or rush_car > 0 or tds > 0 or kp_yds > 0 or kp_att > 0
                    has_defense = tackles > 0
                    has_kicking = dk_made > 0 or dk_att > 0

                    if has_offense:
                        ui.label("Rushing, Receiving & Kick Passing").classes(
                            "text-sm font-bold text-slate-700 mb-1"
                        ).style("border-bottom:2px solid #013369;")

                        ypc = round(rush_yds / max(1, rush_car), 1)
                        kp_pct = round(kp_comp / max(1, kp_att) * 100, 1)
                        ypg = round(total_yds / max(1, gp), 1)

                        off_cols = [
                            {"name": "gp", "label": "GP", "field": "gp", "align": "center"},
                            {"name": "rush_yds", "label": "Rush Yds", "field": "rush_yds", "align": "center"},
                            {"name": "car", "label": "Car", "field": "car", "align": "center"},
                            {"name": "ypc", "label": "YPC", "field": "ypc", "align": "center"},
                            {"name": "td", "label": "TD", "field": "td", "align": "center"},
                            {"name": "kp_yds", "label": "KP Yds", "field": "kp_yds", "align": "center"},
                            {"name": "kp_comp", "label": "Comp", "field": "kp_comp", "align": "center"},
                            {"name": "kp_att", "label": "Att", "field": "kp_att", "align": "center"},
                            {"name": "kp_pct", "label": "Pct%", "field": "kp_pct", "align": "center"},
                            {"name": "lat_yds", "label": "Lat Yds", "field": "lat_yds", "align": "center"},
                            {"name": "total", "label": "Total Yds", "field": "total", "align": "center"},
                            {"name": "ypg", "label": "YPG", "field": "ypg", "align": "center"},
                        ]
                        off_rows = [{
                            "gp": str(gp), "rush_yds": str(rush_yds), "car": str(rush_car),
                            "ypc": str(ypc), "td": str(tds),
                            "kp_yds": str(kp_yds), "kp_comp": str(kp_comp),
                            "kp_att": str(kp_att), "kp_pct": f"{kp_pct}",
                            "lat_yds": str(lat_yds), "total": str(total_yds), "ypg": str(ypg),
                        }]
                        ui.table(columns=off_cols, rows=off_rows, row_key="gp").classes(
                            "w-full"
                        ).props("dense flat bordered hide-bottom")

                    if has_defense:
                        ui.label("Defense").classes(
                            "text-sm font-bold text-slate-700 mt-3 mb-1"
                        ).style("border-bottom:2px solid #013369;")

                        def_cols = [
                            {"name": "gp", "label": "GP", "field": "gp", "align": "center"},
                            {"name": "tkl", "label": "Tackles", "field": "tkl", "align": "center"},
                            {"name": "fum", "label": "Fumbles", "field": "fum", "align": "center"},
                        ]
                        def_rows = [{"gp": str(gp), "tkl": str(tackles), "fum": str(fumbles)}]
                        ui.table(columns=def_cols, rows=def_rows, row_key="gp").classes(
                            "w-full"
                        ).props("dense flat bordered hide-bottom")

                    if has_kicking:
                        ui.label("Drop Kicking").classes(
                            "text-sm font-bold text-slate-700 mt-3 mb-1"
                        ).style("border-bottom:2px solid #013369;")

                        dk_pct = round(dk_made / max(1, dk_att) * 100, 1)
                        dk_cols = [
                            {"name": "gp", "label": "GP", "field": "gp", "align": "center"},
                            {"name": "dk_m", "label": "DK Made", "field": "dk_m", "align": "center"},
                            {"name": "dk_a", "label": "DK Att", "field": "dk_a", "align": "center"},
                            {"name": "dk_pct", "label": "DK%", "field": "dk_pct", "align": "center"},
                        ]
                        dk_rows = [{"gp": str(gp), "dk_m": str(dk_made), "dk_a": str(dk_att), "dk_pct": f"{dk_pct}"}]
                        ui.table(columns=dk_cols, rows=dk_rows, row_key="gp").classes(
                            "w-full"
                        ).props("dense flat bordered hide-bottom")
                else:
                    ui.label("No season stats recorded yet.").classes("text-sm text-slate-400 italic")

            with ui.element("div").classes("w-full px-5 py-2 flex justify-end").style(
                "background:#f8fafc; border-top:1px solid #e2e8f0;"
            ):
                ui.button("Close", on_click=dlg.close).props("flat no-caps color=grey")

    dlg.open()


def _generate_pro_forum_box_score(box: dict) -> str:
    hs = box["home_stats"]
    aws = box["away_stats"]
    home_name = box["home_name"]
    away_name = box["away_name"]
    home_score = int(box["home_score"])
    away_score = int(box["away_score"])
    weather = box.get("weather", "Clear")

    winner = home_name if home_score > away_score else away_name
    w_score = max(home_score, away_score)
    loser = away_name if winner == home_name else home_name
    l_score = min(home_score, away_score)

    league_label = box.get("league", "NATIONAL VIPERBALL LEAGUE")

    lines = []
    lines.append("=" * 62)
    lines.append(f"{league_label.upper()} — OFFICIAL BOX SCORE")
    lines.append("=" * 62)
    lines.append("")
    lines.append(f"  {winner} {w_score}, {loser} {l_score}")
    lines.append(f"  Weather: {weather}")
    lines.append("")

    lines.append("-" * 62)
    lines.append("FINAL SCORE")
    lines.append("-" * 62)
    col_w = max(len(home_name), len(away_name), 6) + 2
    lines.append(f"  {'Team':<{col_w}}  Final")
    lines.append(f"  {'-'*col_w}  -----")
    lines.append(f"  {away_name:<{col_w}}  {away_score:>5}")
    lines.append(f"  {home_name:<{col_w}}  {home_score:>5}")
    lines.append("")

    lines.append("-" * 62)
    lines.append("TEAM STATISTICS")
    lines.append("-" * 62)
    stat_w = max(len(home_name), len(away_name), 6) + 2

    def _sl(label, h_val, a_val):
        return f"  {label:<24} {str(a_val):>{stat_w}}  {str(h_val):>{stat_w}}"

    lines.append(f"  {'':24} {away_name:>{stat_w}}  {home_name:>{stat_w}}")
    lines.append(_sl("Total Yards", hs.get("total_yards", 0), aws.get("total_yards", 0)))

    h_td = hs.get("touchdowns", 0)
    a_td = aws.get("touchdowns", 0)
    lines.append(_sl("Touchdowns (9pts)", f"{h_td} ({h_td*9}pts)", f"{a_td} ({a_td*9}pts)"))

    h_car = hs.get("rushing_carries", 0)
    a_car = aws.get("rushing_carries", 0)
    h_ryds = hs.get("rushing_yards", 0)
    a_ryds = aws.get("rushing_yards", 0)
    lines.append(_sl("Rushing", f"{h_car} car, {h_ryds} yds", f"{a_car} car, {a_ryds} yds"))

    lines.append(_sl("KP Comp/Att",
                      f"{hs.get('kick_passes_completed',0)}/{hs.get('kick_passes_attempted',0)}",
                      f"{aws.get('kick_passes_completed',0)}/{aws.get('kick_passes_attempted',0)}"))
    lines.append(_sl("KP Yards", hs.get("kick_pass_yards", 0), aws.get("kick_pass_yards", 0)))
    lines.append(_sl("Snap Kicks",
                      f"{hs.get('drop_kicks_made',0)}/{hs.get('drop_kicks_attempted',0)}",
                      f"{aws.get('drop_kicks_made',0)}/{aws.get('drop_kicks_attempted',0)}"))
    lines.append(_sl("Field Goals",
                      f"{hs.get('place_kicks_made',0)}/{hs.get('place_kicks_attempted',0)}",
                      f"{aws.get('place_kicks_made',0)}/{aws.get('place_kicks_attempted',0)}"))
    lines.append(_sl("Fumbles Lost", hs.get("fumbles_lost", 0), aws.get("fumbles_lost", 0)))
    lines.append(_sl("KP Interceptions", hs.get("kick_pass_interceptions", 0), aws.get("kick_pass_interceptions", 0)))
    lines.append(_sl("Lateral Chains", hs.get("lateral_chains", 0), aws.get("lateral_chains", 0)))
    lines.append(_sl("Penalties",
                      f"{hs.get('penalties',0)} for {hs.get('penalty_yards',0)}yds",
                      f"{aws.get('penalties',0)} for {aws.get('penalty_yards',0)}yds"))

    for side_key, side_name in [("away", away_name), ("home", home_name)]:
        plist = box.get(f"{side_key}_player_stats", [])
        if not plist:
            continue
        lines.append("")
        lines.append("-" * 62)
        lines.append(f"{side_name.upper()}")
        lines.append("-" * 62)

        rushers = sorted(
            [p for p in plist if p.get("rush_carries", 0) > 0],
            key=lambda x: x.get("rushing_yards", 0), reverse=True
        )
        if rushers:
            lines.append("  RUSHING:")
            for p in rushers[:6]:
                ypc = round(p.get("rushing_yards", 0) / max(1, p.get("rush_carries", 1)), 1)
                lines.append(f"    {p.get('name','?'):<22} {p.get('rush_carries',0):>3} car  {p.get('rushing_yards',0):>4} yds  {ypc:>5} avg  {p.get('rushing_tds',0):>2} TD")

        passers = [p for p in plist if p.get("kick_passes_thrown", 0) > 0]
        if passers:
            lines.append("  KICK PASSING:")
            for p in passers[:3]:
                lines.append(f"    {p.get('name','?'):<22} {p.get('kick_passes_completed',0)}/{p.get('kick_passes_thrown',0)}  {p.get('kick_pass_yards',0):>4} yds  {p.get('kick_pass_tds',0):>2} TD  {p.get('kick_pass_interceptions_thrown',0):>2} INT")

        receivers = sorted(
            [p for p in plist if p.get("kick_pass_receptions", 0) > 0],
            key=lambda x: x.get("kick_pass_receptions", 0), reverse=True
        )
        if receivers:
            lines.append("  RECEIVING:")
            for p in receivers[:5]:
                lines.append(f"    {p.get('name','?'):<22} {p.get('kick_pass_receptions',0):>3} rec")

        lateralists = sorted(
            [p for p in plist if p.get("laterals_thrown", 0) + p.get("lateral_receptions", 0) > 0],
            key=lambda x: x.get("lateral_yards", 0), reverse=True
        )
        if lateralists:
            lines.append("  LATERALS:")
            for p in lateralists[:4]:
                lines.append(f"    {p.get('name','?'):<22} {p.get('laterals_thrown',0):>2} thr  {p.get('lateral_receptions',0):>2} rec  {p.get('lateral_yards',0):>3} yds")

        defenders = sorted(
            [p for p in plist if p.get("tackles", 0) > 0],
            key=lambda x: x.get("tackles", 0), reverse=True
        )
        if defenders:
            lines.append("  DEFENSE:")
            for p in defenders[:5]:
                lines.append(f"    {p.get('name','?'):<22} {p.get('tackles',0):>3} tkl  {p.get('tfl',0):>2} tfl  {p.get('sacks',0):>2} sck  {p.get('hurries',0):>2} hur")

        kickers = [p for p in plist if p.get("dk_att", p.get("drop_kicks_attempted", 0)) + p.get("pk_att", p.get("place_kicks_attempted", 0)) > 0]
        if kickers:
            lines.append("  KICKING:")
            for p in kickers:
                dk_m = p.get("dk_made", p.get("drop_kicks_made", 0))
                dk_a = p.get("dk_att", p.get("drop_kicks_attempted", 0))
                pk_m = p.get("pk_made", p.get("place_kicks_made", 0))
                pk_a = p.get("pk_att", p.get("place_kicks_attempted", 0))
                lines.append(f"    {p.get('name','?'):<22} DK {dk_m}/{dk_a}  PK {pk_m}/{pk_a}")

    lines.append("")
    lines.append("=" * 62)
    lines.append(f"{league_label} | 6-down, 20-yard Viperball")
    lines.append("=" * 62)
    return "\n".join(lines)


def _show_box_score_dialog(box: dict, season: ProLeagueSeason = None):
    with ui.dialog().props("maximized") as dlg:
        with ui.card().classes("w-full h-full overflow-auto p-0"):
            with ui.element("div").classes("w-full").style(
                "background: linear-gradient(135deg, #1e293b 0%, #334155 100%); padding: 24px 32px;"
            ):
                with ui.row().classes("w-full items-center justify-between"):
                    with ui.column().classes("gap-0"):
                        ui.label(f"{box['away_name']} @ {box['home_name']}").classes(
                            "text-2xl font-bold text-white"
                        )
                        ui.label(f"Weather: {box.get('weather', 'Clear')}").classes(
                            "text-sm text-slate-300"
                        )
                    with ui.row().classes("items-center gap-6"):
                        with ui.column().classes("items-center gap-0"):
                            ui.label(box["away_name"].split()[-1]).classes("text-xs text-slate-400 uppercase tracking-wider")
                            away_s = int(box["away_score"])
                            away_won = away_s > int(box["home_score"])
                            ui.label(str(away_s)).classes(
                                f"text-4xl font-black {'text-white' if away_won else 'text-slate-400'}"
                            )
                        ui.label("—").classes("text-2xl text-slate-500 font-light")
                        with ui.column().classes("items-center gap-0"):
                            ui.label(box["home_name"].split()[-1]).classes("text-xs text-slate-400 uppercase tracking-wider")
                            home_s = int(box["home_score"])
                            home_won = home_s > away_s
                            ui.label(str(home_s)).classes(
                                f"text-4xl font-black {'text-white' if home_won else 'text-slate-400'}"
                            )
                        ui.label("FINAL").classes("text-xs font-bold text-amber-400 tracking-widest ml-4")

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    async def _copy_forum():
                        text = _generate_pro_forum_box_score(box)
                        await ui.run_javascript(
                            f'navigator.clipboard.writeText({repr(text)}).then(() => {{ }})'
                        )
                        ui.notify("Box score copied to clipboard!", type="positive", position="top")

                    ui.button("Copy for Forum", icon="content_copy", on_click=_copy_forum).props(
                        "flat no-caps size=sm text-color=white"
                    ).classes("bg-slate-600 hover:bg-slate-500")
                    ui.button("Close", icon="close", on_click=dlg.close).props(
                        "flat no-caps size=sm text-color=white"
                    ).classes("bg-slate-600 hover:bg-slate-500")

            with ui.element("div").classes("w-full px-4 md:px-8 py-6").style("max-width: 1200px; margin: 0 auto;"):
                with ui.tabs().classes("w-full") as bs_tabs:
                    tab_team = ui.tab("Team Stats")
                    tab_offense = ui.tab("Offense")
                    tab_defense = ui.tab("Defense")
                    tab_kicking = ui.tab("Kicking")
                    tab_forum = ui.tab("Forum Export")

                with ui.tab_panels(bs_tabs, value=tab_team).classes("w-full"):
                    with ui.tab_panel(tab_team):
                        _render_team_stat_comparison(box)
                    with ui.tab_panel(tab_offense):
                        _render_offense_stats(box, season)
                    with ui.tab_panel(tab_defense):
                        _render_defense_stats(box, season)
                    with ui.tab_panel(tab_kicking):
                        _render_kicking_stats(box, season)
                    with ui.tab_panel(tab_forum):
                        _render_forum_export(box)

    dlg.open()


def _render_team_stat_comparison(box: dict):
    hs = box["home_stats"]
    aws = box["away_stats"]

    stat_rows = [
        ("Total Yards", aws.get("total_yards", 0), hs.get("total_yards", 0)),
        ("Rushing Yards", aws.get("rushing_yards", 0), hs.get("rushing_yards", 0)),
        ("Rushing Carries", aws.get("rushing_carries", 0), hs.get("rushing_carries", 0)),
        ("Kick Pass Yards", aws.get("kick_pass_yards", 0), hs.get("kick_pass_yards", 0)),
        ("KP Comp/Att",
         f"{aws.get('kick_passes_completed',0)}/{aws.get('kick_passes_attempted',0)}",
         f"{hs.get('kick_passes_completed',0)}/{hs.get('kick_passes_attempted',0)}"),
        ("Lateral Yards", aws.get("lateral_yards", 0), hs.get("lateral_yards", 0)),
        ("Touchdowns", aws.get("touchdowns", 0), hs.get("touchdowns", 0)),
        ("Snap Kicks (DK)",
         f"{aws.get('drop_kicks_made',0)}/{aws.get('drop_kicks_attempted',0)}",
         f"{hs.get('drop_kicks_made',0)}/{hs.get('drop_kicks_attempted',0)}"),
        ("Field Goals (PK)",
         f"{aws.get('place_kicks_made',0)}/{aws.get('place_kicks_attempted',0)}",
         f"{hs.get('place_kicks_made',0)}/{hs.get('place_kicks_attempted',0)}"),
        ("Fumbles Lost", aws.get("fumbles_lost", 0), hs.get("fumbles_lost", 0)),
        ("KP Interceptions", aws.get("kick_pass_interceptions", 0), hs.get("kick_pass_interceptions", 0)),
        ("Penalties",
         f"{aws.get('penalties',0)} / {aws.get('penalty_yards',0)} yds",
         f"{hs.get('penalties',0)} / {hs.get('penalty_yards',0)} yds"),
        ("Punts", aws.get("punts", 0), hs.get("punts", 0)),
    ]

    with ui.element("div").classes("w-full overflow-x-auto"):
        with ui.element("table").classes("w-full").style(
            "border-collapse: collapse; font-size: 14px;"
        ):
            with ui.element("thead"):
                with ui.element("tr").style("background: #f1f5f9; border-bottom: 2px solid #cbd5e1;"):
                    ui.element("th").classes("text-left py-2 px-3 font-semibold text-slate-600").style("width:40%")
                    with ui.element("th").classes("text-center py-2 px-3 font-semibold text-slate-800").style("width:30%"):
                        ui.label(box["away_name"])
                    with ui.element("th").classes("text-center py-2 px-3 font-semibold text-slate-800").style("width:30%"):
                        ui.label(box["home_name"])
            with ui.element("tbody"):
                for i, (label, away_val, home_val) in enumerate(stat_rows):
                    bg = "background: #f8fafc;" if i % 2 == 0 else ""
                    with ui.element("tr").style(f"{bg} border-bottom: 1px solid #e2e8f0;"):
                        with ui.element("td").classes("py-2 px-3 font-medium text-slate-700"):
                            ui.label(label)
                        with ui.element("td").classes("text-center py-2 px-3 text-slate-800 font-semibold"):
                            ui.label(str(away_val))
                        with ui.element("td").classes("text-center py-2 px-3 text-slate-800 font-semibold"):
                            ui.label(str(home_val))


def _make_clickable_player_table(columns, rows, season, team_key):
    tbl = ui.table(columns=columns, rows=rows, row_key="name").classes("w-full").props(
        "dense flat bordered"
    )
    if season and team_key:
        tbl.add_slot("body-cell-name", '''
            <q-td :props="props">
                <a class="text-indigo-600 font-semibold cursor-pointer hover:underline"
                   @click="$parent.$emit('player_click', props.row)">
                    {{ props.row.name }}
                </a>
            </q-td>
        ''')
        tbl.on("player_click", lambda e, _s=season, _tk=team_key: _show_player_card(
            _s, _tk, e.args.get("name", "")
        ))
    return tbl


def _render_offense_stats(box: dict, season: ProLeagueSeason = None):
    for side_key, side_name in [("away", box["away_name"]), ("home", box["home_name"])]:
        players = box.get(f"{side_key}_player_stats", [])
        team_key = box.get(f"{side_key}_key", "")
        if not players:
            continue

        ui.label(side_name).classes("text-lg font-bold text-indigo-700 mt-4 mb-1")
        ui.separator().classes("mb-2")

        rushers = sorted(
            [p for p in players if p.get("rush_carries", 0) > 0],
            key=lambda x: x.get("rushing_yards", 0), reverse=True
        )
        if rushers:
            ui.label("Rushing").classes("text-sm font-semibold text-slate-600 mb-1")
            rush_cols = [
                {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
                {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
                {"name": "car", "label": "Car", "field": "car", "align": "center", "sortable": True},
                {"name": "yds", "label": "Yds", "field": "yds", "align": "center", "sortable": True},
                {"name": "avg", "label": "Avg", "field": "avg", "align": "center", "sortable": True},
                {"name": "td", "label": "TD", "field": "td", "align": "center", "sortable": True},
                {"name": "fum", "label": "Fum", "field": "fum", "align": "center"},
                {"name": "long", "label": "Lng", "field": "long", "align": "center"},
            ]
            rush_rows = []
            for p in rushers:
                car = p.get("rush_carries", 0)
                yds = p.get("rushing_yards", 0)
                avg = round(yds / max(1, car), 1)
                rush_rows.append({
                    "name": p.get("name", "?"), "pos": p.get("position", ""),
                    "car": str(car), "yds": str(yds), "avg": str(avg),
                    "td": str(p.get("rushing_tds", 0)),
                    "fum": str(p.get("fumbles", 0)),
                    "long": str(p.get("long_rush", "-")),
                })
            _make_clickable_player_table(rush_cols, rush_rows, season, team_key)

        passers = [p for p in players if p.get("kick_passes_thrown", 0) > 0]
        if passers:
            ui.label("Kick Passing").classes("text-sm font-semibold text-slate-600 mt-3 mb-1")
            kp_cols = [
                {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
                {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
                {"name": "comp", "label": "Cmp", "field": "comp", "align": "center", "sortable": True},
                {"name": "att", "label": "Att", "field": "att", "align": "center"},
                {"name": "yds", "label": "Yds", "field": "yds", "align": "center", "sortable": True},
                {"name": "td", "label": "TD", "field": "td", "align": "center", "sortable": True},
                {"name": "int", "label": "INT", "field": "int_thrown", "align": "center"},
                {"name": "pct", "label": "Pct", "field": "pct", "align": "center"},
            ]
            kp_rows = []
            for p in passers:
                comp = p.get("kick_passes_completed", 0)
                att = p.get("kick_passes_thrown", 0)
                pct = round(100 * comp / max(1, att), 1)
                kp_rows.append({
                    "name": p.get("name", "?"), "pos": p.get("position", ""),
                    "comp": str(comp), "att": str(att),
                    "yds": str(p.get("kick_pass_yards", 0)),
                    "td": str(p.get("kick_pass_tds", 0)),
                    "int_thrown": str(p.get("kick_pass_interceptions_thrown", 0)),
                    "pct": f"{pct}%",
                })
            _make_clickable_player_table(kp_cols, kp_rows, season, team_key)

        receivers = sorted(
            [p for p in players if p.get("kick_pass_receptions", 0) > 0],
            key=lambda x: x.get("kick_pass_receptions", 0), reverse=True
        )
        if receivers:
            ui.label("Receiving").classes("text-sm font-semibold text-slate-600 mt-3 mb-1")
            rec_cols = [
                {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
                {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
                {"name": "rec", "label": "Rec", "field": "rec", "align": "center", "sortable": True},
            ]
            rec_rows = [{"name": p.get("name", "?"), "pos": p.get("position", ""), "rec": str(p.get("kick_pass_receptions", 0))} for p in receivers]
            _make_clickable_player_table(rec_cols, rec_rows, season, team_key)

        lateralists = sorted(
            [p for p in players if p.get("laterals_thrown", 0) + p.get("lateral_receptions", 0) > 0],
            key=lambda x: x.get("lateral_yards", 0), reverse=True
        )
        if lateralists:
            ui.label("Laterals").classes("text-sm font-semibold text-slate-600 mt-3 mb-1")
            lat_cols = [
                {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
                {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
                {"name": "thr", "label": "Thr", "field": "thr", "align": "center"},
                {"name": "recv", "label": "Rec", "field": "recv", "align": "center"},
                {"name": "yds", "label": "Yds", "field": "yds", "align": "center", "sortable": True},
                {"name": "ast", "label": "Ast", "field": "ast", "align": "center"},
                {"name": "td", "label": "TD", "field": "td", "align": "center"},
            ]
            lat_rows = [{
                "name": p.get("name", "?"), "pos": p.get("position", ""),
                "thr": str(p.get("laterals_thrown", 0)),
                "recv": str(p.get("lateral_receptions", 0)),
                "yds": str(p.get("lateral_yards", 0)),
                "ast": str(p.get("lateral_assists", 0)),
                "td": str(p.get("lateral_tds", 0)),
            } for p in lateralists]
            _make_clickable_player_table(lat_cols, lat_rows, season, team_key)


def _render_defense_stats(box: dict, season: ProLeagueSeason = None):
    for side_key, side_name in [("away", box["away_name"]), ("home", box["home_name"])]:
        players = box.get(f"{side_key}_player_stats", [])
        team_key = box.get(f"{side_key}_key", "")
        if not players:
            continue

        defenders = sorted(
            [p for p in players if p.get("tackles", 0) > 0],
            key=lambda x: x.get("tackles", 0), reverse=True
        )
        if not defenders:
            continue

        ui.label(side_name).classes("text-lg font-bold text-indigo-700 mt-4 mb-1")
        ui.separator().classes("mb-2")

        def_cols = [
            {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
            {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
            {"name": "tkl", "label": "Tkl", "field": "tkl", "align": "center", "sortable": True},
            {"name": "tfl", "label": "TFL", "field": "tfl", "align": "center", "sortable": True},
            {"name": "sck", "label": "Sck", "field": "sck", "align": "center", "sortable": True},
            {"name": "hur", "label": "Hur", "field": "hur", "align": "center"},
            {"name": "int", "label": "INT", "field": "ints", "align": "center"},
            {"name": "st", "label": "ST Tkl", "field": "st", "align": "center"},
        ]
        def_rows = [{
            "name": p.get("name", "?"), "pos": p.get("position", ""),
            "tkl": str(p.get("tackles", 0)),
            "tfl": str(p.get("tfl", 0)),
            "sck": str(p.get("sacks", 0)),
            "hur": str(p.get("hurries", 0)),
            "ints": str(p.get("kick_pass_ints", 0)),
            "st": str(p.get("st_tackles", 0)),
        } for p in defenders]
        _make_clickable_player_table(def_cols, def_rows, season, team_key)


def _render_kicking_stats(box: dict, season: ProLeagueSeason = None):
    for side_key, side_name in [("away", box["away_name"]), ("home", box["home_name"])]:
        players = box.get(f"{side_key}_player_stats", [])
        team_key = box.get(f"{side_key}_key", "")
        if not players:
            continue

        kickers = [p for p in players if
                   p.get("dk_att", p.get("drop_kicks_attempted", 0)) +
                   p.get("pk_att", p.get("place_kicks_attempted", 0)) > 0]
        if not kickers:
            continue

        ui.label(side_name).classes("text-lg font-bold text-indigo-700 mt-4 mb-1")
        ui.separator().classes("mb-2")

        kick_cols = [
            {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
            {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
            {"name": "dk", "label": "DK M/A", "field": "dk", "align": "center"},
            {"name": "dk_pts", "label": "DK Pts", "field": "dk_pts", "align": "center"},
            {"name": "pk", "label": "PK M/A", "field": "pk", "align": "center"},
            {"name": "pk_pts", "label": "PK Pts", "field": "pk_pts", "align": "center"},
            {"name": "total", "label": "Total Pts", "field": "total", "align": "center", "sortable": True},
        ]
        kick_rows = []
        for p in kickers:
            dk_m = p.get("dk_made", p.get("drop_kicks_made", 0))
            dk_a = p.get("dk_att", p.get("drop_kicks_attempted", 0))
            pk_m = p.get("pk_made", p.get("place_kicks_made", 0))
            pk_a = p.get("pk_att", p.get("place_kicks_attempted", 0))
            kick_rows.append({
                "name": p.get("name", "?"), "pos": p.get("position", ""),
                "dk": f"{dk_m}/{dk_a}", "dk_pts": str(dk_m * 5),
                "pk": f"{pk_m}/{pk_a}", "pk_pts": str(pk_m * 3),
                "total": str(dk_m * 5 + pk_m * 3),
            })
        _make_clickable_player_table(kick_cols, kick_rows, season, team_key)


def _render_forum_export(box: dict):
    text = _generate_pro_forum_box_score(box)
    ui.label("Copy this text to share on forums, Discord, etc.").classes("text-sm text-slate-500 mb-2")

    async def _copy():
        await ui.run_javascript(
            f'navigator.clipboard.writeText({repr(text)}).then(() => {{ }})'
        )
        ui.notify("Copied to clipboard!", type="positive", position="top")

    ui.button("Copy to Clipboard", icon="content_copy", on_click=_copy).props(
        "no-caps color=indigo size=sm"
    ).classes("mb-3")

    with ui.element("pre").classes("w-full overflow-x-auto bg-slate-900 text-green-300 p-4 rounded-lg text-xs leading-relaxed").style(
        "font-family: 'Courier New', monospace; white-space: pre; max-height: 600px; overflow-y: auto;"
    ):
        ui.label(text).style("white-space: pre; font-family: inherit; color: inherit;")


def _render_stats(season: ProLeagueSeason):
    leaders = season.get_stat_leaders()

    ui.label("League Stat Leaders").classes("text-xl font-bold text-slate-800 mb-4")

    if not any(leaders.values()):
        ui.label("No stats available yet. Simulate some weeks first.").classes("text-sm text-slate-500")
        return

    with ui.tabs().classes("w-full") as stat_tabs:
        tab_rush = ui.tab("Rushing")
        tab_kp = ui.tab("Kick Pass")
        tab_score = ui.tab("Scoring")
        tab_total = ui.tab("Total Yards")

    with ui.tab_panels(stat_tabs, value=tab_rush).classes("w-full"):
        with ui.tab_panel(tab_rush):
            _stat_leader_table(season, leaders.get("rushing", []), [
                ("name", "Player"), ("team", "Team"), ("yards", "Yards"),
                ("carries", "Carries"), ("ypc", "YPC"), ("games", "GP"),
            ])
        with ui.tab_panel(tab_kp):
            _stat_leader_table(season, leaders.get("kick_pass", []), [
                ("name", "Player"), ("team", "Team"), ("yards", "Yards"),
                ("completions", "Comp"), ("attempts", "Att"), ("pct", "Pct%"), ("games", "GP"),
            ])
        with ui.tab_panel(tab_score):
            _stat_leader_table(season, leaders.get("scoring", []), [
                ("name", "Player"), ("team", "Team"), ("touchdowns", "TD"),
                ("dk_made", "DK"), ("total_yards", "Yds"), ("games", "GP"),
            ])
        with ui.tab_panel(tab_total):
            _stat_leader_table(season, leaders.get("total_yards", []), [
                ("name", "Player"), ("team", "Team"), ("total_yards", "Total"),
                ("rushing", "Rush"), ("kick_pass", "KP"), ("games", "GP"),
            ])


def _stat_leader_table(season: ProLeagueSeason, data: list, col_spec: list):
    if not data:
        ui.label("No data yet.").classes("text-sm text-slate-400")
        return

    columns = [{"name": k, "label": lbl, "field": k, "align": "left" if k == "name" else "center",
                 "sortable": True} for k, lbl in col_spec]

    rows = []
    for i, p in enumerate(data[:20]):
        row = {"_rank": i + 1, "team_key": p.get("team_key", "")}
        for k, _ in col_spec:
            row[k] = str(p.get(k, ""))
        rows.append(row)

    tbl = ui.table(columns=columns, rows=rows, row_key="_rank").classes("w-full").props("dense flat bordered")
    tbl.add_slot("body-cell-name", '''
        <q-td :props="props">
            <a class="text-indigo-600 font-semibold cursor-pointer hover:underline"
               @click="$parent.$emit('player_click', props.row)">
                {{ props.row.name }}
            </a>
        </q-td>
    ''')
    tbl.on("player_click", lambda e: _show_player_card(
        season, e.args.get("team_key", ""), e.args.get("name", "")
    ))


def _render_playoffs(season: ProLeagueSeason):
    league_abbr = season.config.league_id.upper().replace("_LEAGUE", "")
    ui.label(f"{league_abbr} Playoffs").classes("text-xl font-bold text-slate-800 mb-2")

    if season.phase != "playoffs" and not season.champion:
        remaining = season.total_weeks - season.current_week
        if remaining > 0:
            ui.label(f"Playoffs haven't started yet. {remaining} regular season weeks remain.").classes(
                "text-sm text-slate-500"
            )
        else:
            ui.label("Regular season complete. Start playoffs from the Dashboard tab.").classes(
                "text-sm text-slate-500"
            )
        return

    bracket = season.get_playoff_bracket()

    if bracket.get("champion_name"):
        with ui.card().classes("p-4 bg-gradient-to-r from-yellow-50 to-amber-50 mb-4"):
            ui.label(f"{league_abbr} Champion: {bracket['champion_name']}").classes(
                "text-xl font-extrabold text-amber-700"
            )

    for rd in bracket.get("rounds", []):
        ui.label(rd["round_name"]).classes("text-lg font-semibold text-indigo-600 mt-4 mb-2")

        if rd.get("bye_teams"):
            bye_names = ", ".join(t["team_name"] for t in rd["bye_teams"])
            ui.label(f"First-round byes: {bye_names}").classes("text-xs text-slate-500 italic mb-1")

        for m in rd["matchups"]:
            with ui.card().classes("p-3 mb-2 max-w-lg").style("border: 1px solid #e2e8f0;"):
                away = m["away"]["team_name"] if m.get("away") else "BYE"
                home = m["home"]["team_name"]

                if m.get("winner"):
                    hs = int(m.get("home_score", 0))
                    asc = int(m.get("away_score", 0))
                    h_bold = "font-bold" if m["winner"] == m["home"]["team_key"] else ""
                    a_bold = "font-bold" if m.get("away") and m["winner"] == m["away"]["team_key"] else ""
                    ui.label(f"{away} {asc}  @  {home} {hs}").classes("text-sm")
                    ui.label(f"Winner: {m['winner_name']}").classes(f"text-sm font-bold text-green-600")
                else:
                    ui.label(f"{away}  @  {home}").classes("text-sm text-slate-600")
                    ui.label("TBD").classes("text-xs text-slate-400 italic")


def _render_teams(season: ProLeagueSeason):
    is_cl = season.config.league_id == "cl"
    league_abbr = season.config.league_id.upper().replace("_LEAGUE", "")
    ui.label(f"{league_abbr} Teams").classes("text-xl font-bold text-slate-800 mb-2")

    team_options = {}
    for div_name, keys in season.config.divisions.items():
        for key in keys:
            if key in season.teams:
                if is_cl:
                    src = _source_league_abbr(key)
                    team_options[key] = f"{season.teams[key].name} ({src})"
                else:
                    team_options[key] = f"{season.teams[key].name} ({div_name})"

    selected = {"key": None}

    team_box = ui.column().classes("w-full")

    def _fill_team_detail():
        team_box.clear()
        with team_box:
            if not selected["key"]:
                ui.label("Select a team to view details.").classes("text-sm text-slate-500")
                return

            detail = season.get_team_detail(selected["key"])
            if not detail:
                ui.label("Team not found.").classes("text-sm text-red-500")
                return

            ui.label(f"{detail['team_name']}").classes("text-xl font-bold text-indigo-600")
            ui.label(f"{detail['division']} Division | {detail['record']} | "
                     f"Style: {detail['offense_style']} / {detail['defense_style']}").classes("text-sm text-slate-500 mb-3")

            with ui.tabs().classes("w-full") as team_tabs:
                tab_roster = ui.tab("Roster")
                tab_tstats = ui.tab("Season Stats")
                tab_tsched = ui.tab("Schedule")

            current_team_key = selected["key"]

            with ui.tab_panels(team_tabs, value=tab_roster).classes("w-full"):
                with ui.tab_panel(tab_roster):
                    columns = [
                        {"name": "num", "label": "#", "field": "number", "align": "center"},
                        {"name": "name", "label": "Name", "field": "name", "align": "left"},
                        {"name": "pos", "label": "Pos", "field": "position", "align": "center"},
                        {"name": "spd", "label": "SPD", "field": "speed", "align": "center"},
                        {"name": "kick", "label": "KICK", "field": "kicking", "align": "center"},
                        {"name": "lat", "label": "LAT", "field": "lateral_skill", "align": "center"},
                        {"name": "ovr", "label": "OVR", "field": "overall", "align": "center"},
                        {"name": "arch", "label": "Archetype", "field": "archetype", "align": "left"},
                    ]
                    rows = [{k: str(v) for k, v in p.items() if k in [c["field"] for c in columns]}
                            for p in detail["roster"]]
                    tbl = ui.table(columns=columns, rows=rows, row_key="name").classes("w-full").props("dense flat bordered")
                    tk = current_team_key
                    tbl.add_slot("body-cell-name", f'''
                        <q-td :props="props">
                            <a class="text-indigo-600 font-semibold cursor-pointer hover:underline"
                               @click="$parent.$emit('player_click', props.row)">
                                {{{{ props.row.name }}}}
                            </a>
                        </q-td>
                    ''')
                    tbl.on("player_click", lambda e, _tk=tk: _show_player_card(season, _tk, e.args.get("name", "")))

                with ui.tab_panel(tab_tstats):
                    if detail["season_stats"]:
                        columns = [
                            {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
                            {"name": "pos", "label": "Pos", "field": "position", "align": "center"},
                            {"name": "gp", "label": "GP", "field": "games", "align": "center"},
                            {"name": "rush", "label": "Rush Yds", "field": "rushing_yards", "align": "center", "sortable": True},
                            {"name": "td", "label": "TD", "field": "touchdowns", "align": "center", "sortable": True},
                            {"name": "kp", "label": "KP Yds", "field": "kick_pass_yards", "align": "center", "sortable": True},
                            {"name": "total", "label": "Total", "field": "total_yards", "align": "center", "sortable": True},
                        ]
                        rows = [{k: str(v) for k, v in p.items() if k in [c["field"] for c in columns]}
                                for p in sorted(detail["season_stats"], key=lambda x: -x.get("total_yards", 0))]
                        tbl2 = ui.table(columns=columns, rows=rows, row_key="name").classes("w-full").props("dense flat bordered")
                        tk2 = current_team_key
                        tbl2.add_slot("body-cell-name", f'''
                            <q-td :props="props">
                                <a class="text-indigo-600 font-semibold cursor-pointer hover:underline"
                                   @click="$parent.$emit('player_click', props.row)">
                                    {{{{ props.row.name }}}}
                                </a>
                            </q-td>
                        ''')
                        tbl2.on("player_click", lambda e, _tk=tk2: _show_player_card(season, _tk, e.args.get("name", "")))
                    else:
                        ui.label("No stats yet — sim some weeks first.").classes("text-sm text-slate-400")

                with ui.tab_panel(tab_tsched):
                    if detail["schedule"]:
                        for game in detail["schedule"]:
                            prefix = "vs" if game["home"] else "@"
                            status = ""
                            if game["completed"]:
                                result = "W" if game.get("won") else "L"
                                score = game.get("score", "")
                                status = f"  {result} {score}"
                            else:
                                status = "  —"
                            ui.label(f"Wk {game['week']}: {prefix} {game['opponent_name']}{status}").classes(
                                "text-xs text-slate-700"
                            )
                    else:
                        ui.label("No schedule data.").classes("text-sm text-slate-400")

    def _on_team_select(e):
        selected["key"] = e.value
        _fill_team_detail()

    ui.select(
        options=team_options,
        label="Select Team",
        on_change=_on_team_select,
    ).classes("w-72 mb-4")

    _fill_team_detail()
