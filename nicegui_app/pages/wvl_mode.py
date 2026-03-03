"""
WVL Owner Mode — NiceGUI UI Page
==================================

Owner mode interface for the Women's Viperball League.
Tab-based layout with week-by-week sim controls, roster management,
financial dashboard, and multi-step offseason flow.
"""

from nicegui import ui, app
from typing import Optional
import logging

_log = logging.getLogger("viperball.wvl")

from engine.wvl_config import (
    ALL_CLUBS, CLUBS_BY_KEY, CLUBS_BY_TIER, ALL_WVL_TIERS,
    TIER_BY_NUMBER, RIVALRIES,
)
from engine.wvl_owner import (
    OWNER_ARCHETYPES, PRESIDENT_ARCHETYPES,
    generate_president_pool, InvestmentAllocation,
)
from engine.wvl_dynasty import create_wvl_dynasty, WVLDynasty


_WVL_DYNASTY_KEY = "wvl_dynasty"
_WVL_PHASE_KEY = "wvl_phase"
_WVL_SEASON_KEY = "wvl_last_season"


def _get_dynasty() -> Optional[WVLDynasty]:
    return app.storage.user.get(_WVL_DYNASTY_KEY)


def _set_dynasty(dynasty: Optional[WVLDynasty]):
    app.storage.user[_WVL_DYNASTY_KEY] = dynasty


def _get_phase() -> str:
    return app.storage.user.get(_WVL_PHASE_KEY, "setup")


def _set_phase(phase: str):
    app.storage.user[_WVL_PHASE_KEY] = phase


def _register_wvl_season(dynasty, season, year=None):
    try:
        from api.main import wvl_sessions
        effective_year = year if year is not None else dynasty.current_year - 1
        session_id = f"wvl_{dynasty.dynasty_name}_{effective_year}"
        session_id = session_id.lower().replace(" ", "_").replace("'", "")
        wvl_sessions[session_id] = {
            "season": season,
            "dynasty": dynasty,
            "dynasty_name": dynasty.dynasty_name,
            "year": effective_year,
            "club_key": dynasty.owner.club_key,
        }
    except Exception:
        pass


def _ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    s = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{s}"


def _rating_color(val: int) -> str:
    if val >= 85:
        return "color: #15803d; font-weight: 700;"
    elif val >= 75:
        return "color: #16a34a;"
    elif val >= 65:
        return "color: #ca8a04;"
    elif val >= 55:
        return "color: #ea580c;"
    else:
        return "color: #dc2626;"


# ═══════════════════════════════════════════════════════════════
# SETUP PAGE
# ═══════════════════════════════════════════════════════════════

def _render_setup(container):
    with container:
        with ui.element("div").classes("w-full").style(
            "background: linear-gradient(135deg, #312e81 0%, #4338ca 100%); padding: 32px; border-radius: 12px;"
        ):
            ui.label("Women's Viperball League").classes("text-3xl font-bold text-white")
            ui.label("Galactic Premiership — Owner Mode").classes("text-lg text-indigo-200")

        with ui.card().classes("w-full p-6 mt-4"):
            ui.label("Step 1: Create Your Owner").classes("text-lg font-semibold")
            name_input = ui.input("Owner Name", value="").classes("w-64")

            ui.label("Owner Archetype:").classes("font-medium mt-2")
            archetype_select = ui.select(
                options={k: f"{v['label']} — {v['description']}" for k, v in OWNER_ARCHETYPES.items()},
                value="patient_builder",
            ).classes("w-full")

        with ui.card().classes("w-full p-6 mt-4"):
            ui.label("Step 2: Pick Your Club").classes("text-lg font-semibold")
            ui.label("Choose from any tier — even Tier 4 for the ultimate challenge.").classes("text-sm text-gray-400")

            club_options = {}
            for tier_num in [1, 2, 3, 4]:
                for club in CLUBS_BY_TIER[tier_num]:
                    club_options[club.key] = f"T{tier_num}: {club.name} ({club.country})"

            club_select = ui.select(options=club_options, value="vimpeli").classes("w-full")

        async def _start():
            owner_name = name_input.value.strip() or "The Owner"
            archetype = archetype_select.value
            club_key = club_select.value

            dynasty = create_wvl_dynasty(
                dynasty_name=f"{owner_name}'s WVL",
                owner_name=owner_name,
                owner_archetype=archetype,
                club_key=club_key,
            )

            import random
            pool = generate_president_pool(5, random.Random())
            dynasty.president = pool[0]

            _set_dynasty(dynasty)
            _set_phase("pre_season")
            ui.notify(f"Dynasty created! You own {CLUBS_BY_KEY[club_key].name}.", type="positive")
            container.clear()
            _render_main(container)

        ui.button("Start Dynasty", on_click=_start).classes(
            "mt-4 bg-indigo-600 text-white px-6 py-2 rounded-lg"
        )


# ═══════════════════════════════════════════════════════════════
# MAIN TAB LAYOUT
# ═══════════════════════════════════════════════════════════════

def _render_main(container):
    dynasty = _get_dynasty()
    if not dynasty:
        _render_setup(container)
        return

    club = CLUBS_BY_KEY.get(dynasty.owner.club_key)
    club_name = club.name if club else dynasty.owner.club_key
    club_tier = dynasty.tier_assignments.get(dynasty.owner.club_key, 1)
    tier_config = TIER_BY_NUMBER.get(club_tier)
    tier_name = tier_config.tier_name if tier_config else f"Tier {club_tier}"

    containers = {}

    with container:
        with ui.element("div").classes("w-full").style(
            "background: linear-gradient(135deg, #312e81 0%, #4338ca 100%); padding: 20px 28px; border-radius: 8px;"
        ):
            with ui.row().classes("w-full items-center justify-between"):
                with ui.column().classes("gap-0"):
                    ui.label(club_name).classes("text-2xl font-bold text-white")
                    ui.label(f"{tier_name} | Year {dynasty.current_year} | Owner: {dynasty.owner.name}").classes(
                        "text-sm text-indigo-200"
                    )
                with ui.row().classes("items-center gap-4"):
                    summary = dynasty.get_owner_team_summary()
                    with ui.column().classes("items-center gap-0"):
                        ui.label(f"${dynasty.owner.bankroll:.1f}M").classes("text-xl font-bold text-green-300")
                        ui.label("Bankroll").classes("text-[10px] text-indigo-300 uppercase")
                    with ui.column().classes("items-center gap-0"):
                        ui.label(str(summary.get("roster_size", 0))).classes("text-xl font-bold text-white")
                        ui.label("Roster").classes("text-[10px] text-indigo-300 uppercase")
                    with ui.column().classes("items-center gap-0"):
                        ui.label(str(summary.get("overall_rating", 0))).classes("text-xl font-bold text-amber-300")
                        ui.label("OVR").classes("text-[10px] text-indigo-300 uppercase")

        with ui.tabs().classes("w-full mt-2") as tabs:
            tab_dash = ui.tab("Dashboard", icon="dashboard")
            tab_roster = ui.tab("My Team", icon="groups")
            tab_schedule = ui.tab("Schedule", icon="calendar_month")
            tab_league = ui.tab("League", icon="leaderboard")
            tab_finance = ui.tab("Finances", icon="account_balance")

        with ui.tab_panels(tabs, value=tab_dash).classes("w-full"):
            with ui.tab_panel(tab_dash):
                containers["dashboard"] = ui.column().classes("w-full")
            with ui.tab_panel(tab_roster):
                containers["roster"] = ui.column().classes("w-full")
            with ui.tab_panel(tab_schedule):
                containers["schedule"] = ui.column().classes("w-full")
            with ui.tab_panel(tab_league):
                containers["league"] = ui.column().classes("w-full")
            with ui.tab_panel(tab_finance):
                containers["finance"] = ui.column().classes("w-full")

    _fill_dashboard(containers, dynasty)
    _fill_roster(containers, dynasty)
    _fill_schedule(containers, dynasty)
    _fill_league(containers, dynasty)
    _fill_finance(containers, dynasty)

    def _refresh_all():
        dynasty_fresh = _get_dynasty()
        if not dynasty_fresh:
            return
        for key in containers:
            try:
                containers[key].clear()
            except Exception:
                pass
        _fill_dashboard(containers, dynasty_fresh)
        _fill_roster(containers, dynasty_fresh)
        _fill_schedule(containers, dynasty_fresh)
        _fill_league(containers, dynasty_fresh)
        _fill_finance(containers, dynasty_fresh)

    app.storage.user["_wvl_refresh"] = _refresh_all


# ═══════════════════════════════════════════════════════════════
# DASHBOARD TAB
# ═══════════════════════════════════════════════════════════════

def _fill_dashboard(containers, dynasty):
    c = containers.get("dashboard")
    if not c:
        return

    season = app.storage.user.get(_WVL_SEASON_KEY)

    with c:
        phase = _get_phase()

        with ui.row().classes("w-full gap-3 flex-wrap mb-4"):
            with ui.card().classes("flex-1 min-w-[180px] p-4 text-center"):
                ui.label("Phase").classes("text-xs text-slate-400 uppercase")
                phase_label = {
                    "setup": "Setup",
                    "pre_season": "Pre-Season",
                    "in_season": "In Season",
                    "playoffs": "Playoffs",
                    "offseason": "Offseason",
                    "season_complete": "Season Complete",
                }.get(phase, phase)
                ui.label(phase_label).classes("text-lg font-bold text-slate-800")

            if season and hasattr(season, 'tier_seasons'):
                owner_tier = dynasty.tier_assignments.get(dynasty.owner.club_key, 1)
                ts = season.tier_seasons.get(owner_tier)
                if ts:
                    with ui.card().classes("flex-1 min-w-[180px] p-4 text-center"):
                        ui.label("Week").classes("text-xs text-slate-400 uppercase")
                        ui.label(f"{ts.current_week} / {ts.total_weeks}").classes("text-lg font-bold text-slate-800")

                    rec = ts.standings.get(dynasty.owner.club_key)
                    if rec:
                        with ui.card().classes("flex-1 min-w-[180px] p-4 text-center"):
                            ui.label("Record").classes("text-xs text-slate-400 uppercase")
                            ui.label(f"{rec.wins}-{rec.losses}").classes("text-lg font-bold text-slate-800")

            with ui.card().classes("flex-1 min-w-[180px] p-4 text-center"):
                ui.label("Year").classes("text-xs text-slate-400 uppercase")
                ui.label(str(dynasty.current_year)).classes("text-lg font-bold text-slate-800")

        with ui.row().classes("w-full gap-2 mb-4 flex-wrap"):
            if phase == "pre_season":
                async def _start_season():
                    d = _get_dynasty()
                    if not d:
                        return
                    s = d.start_season()
                    if not s.tier_seasons:
                        ui.notify("No team files found. Run scripts/generate_wvl_teams.py first.", type="warning")
                        return
                    app.storage.user[_WVL_SEASON_KEY] = s
                    _set_phase("in_season")
                    _set_dynasty(d)
                    _register_wvl_season(d, s, year=d.current_year)
                    ui.notify("Season started!", type="positive")
                    refresh = app.storage.user.get("_wvl_refresh")
                    if refresh:
                        refresh()

                ui.button("Start Season", icon="play_arrow", on_click=_start_season).classes(
                    "bg-green-600 text-white"
                )

            elif phase == "in_season":
                _engine_opts = {"use_fast_sim": True}

                async def _sim_week():
                    d = _get_dynasty()
                    s = app.storage.user.get(_WVL_SEASON_KEY)
                    if not d or not s:
                        return
                    results = s.sim_week_all_tiers(use_fast_sim=_engine_opts["use_fast_sim"])

                    owner_tier = d.tier_assignments.get(d.owner.club_key, 1)
                    ts = s.tier_seasons.get(owner_tier)

                    all_done = all(
                        t.current_week >= t.total_weeks or t.phase != "regular_season"
                        for t in s.tier_seasons.values()
                    )
                    if all_done:
                        _set_phase("playoffs")
                        s.start_playoffs_all()

                    app.storage.user[_WVL_SEASON_KEY] = s
                    _set_dynasty(d)
                    _register_wvl_season(d, s, year=d.current_year)

                    owner_result = _get_owner_week_result(results, d, owner_tier)
                    if owner_result:
                        ui.notify(owner_result, type="info", position="top", timeout=4000)
                    else:
                        ui.notify("Week simulated!", type="info")

                    refresh = app.storage.user.get("_wvl_refresh")
                    if refresh:
                        refresh()

                async def _sim_rest():
                    d = _get_dynasty()
                    s = app.storage.user.get(_WVL_SEASON_KEY)
                    if not d or not s:
                        return
                    ui.notify("Simulating remaining regular season...", type="info")
                    while s.phase == "regular_season" or any(
                        t.phase == "regular_season" and t.current_week < t.total_weeks
                        for t in s.tier_seasons.values()
                    ):
                        s.sim_week_all_tiers(use_fast_sim=True)

                    _set_phase("playoffs")
                    s.start_playoffs_all()
                    app.storage.user[_WVL_SEASON_KEY] = s
                    _set_dynasty(d)
                    _register_wvl_season(d, s, year=d.current_year)
                    ui.notify("Regular season complete! Playoffs started.", type="positive")
                    refresh = app.storage.user.get("_wvl_refresh")
                    if refresh:
                        refresh()

                ui.button("Sim Week", icon="skip_next", on_click=_sim_week).classes("bg-green-600 text-white")
                ui.button("Sim Rest of Season", icon="fast_forward", on_click=_sim_rest).classes("bg-blue-600 text-white")
                ui.toggle(
                    {True: "Fast Sim", False: "Full Engine"},
                    value=True,
                    on_change=lambda e: _engine_opts.update({"use_fast_sim": e.value}),
                ).props("dense no-caps").classes("ml-2")

            elif phase == "playoffs":
                async def _advance_playoffs():
                    d = _get_dynasty()
                    s = app.storage.user.get(_WVL_SEASON_KEY)
                    if not d or not s:
                        return
                    results = s.advance_playoffs_all()

                    champs = [r.get("champion") for r in results.values() if r.get("champion")]
                    if s.phase == "season_complete":
                        d.snapshot_season(s)
                        _set_phase("offseason")
                        ui.notify("Season complete! Proceed to offseason.", type="positive")
                    elif champs:
                        ui.notify(f"Champions crowned: {', '.join(champs)}", type="positive")
                    else:
                        ui.notify("Playoff round complete!", type="info")

                    app.storage.user[_WVL_SEASON_KEY] = s
                    _set_dynasty(d)
                    _register_wvl_season(d, s, year=d.current_year)
                    refresh = app.storage.user.get("_wvl_refresh")
                    if refresh:
                        refresh()

                ui.button("Advance Playoffs", icon="emoji_events", on_click=_advance_playoffs).classes(
                    "bg-amber-600 text-white"
                )

            elif phase == "offseason":
                _render_offseason_controls(c, dynasty)
                return

        _render_owner_results_compact(dynasty, season)


def _get_owner_week_result(results, dynasty, owner_tier):
    tier_results = results.get(owner_tier, {})
    games = tier_results.get("games", [])
    for game in games:
        if game.get("home_key") == dynasty.owner.club_key:
            score = f"{int(game.get('home_score', 0))}-{int(game.get('away_score', 0))}"
            won = game.get("home_score", 0) > game.get("away_score", 0)
            return f"{'W' if won else 'L'} {score} vs {game.get('away_name', '?')}"
        elif game.get("away_key") == dynasty.owner.club_key:
            score = f"{int(game.get('away_score', 0))}-{int(game.get('home_score', 0))}"
            won = game.get("away_score", 0) > game.get("home_score", 0)
            return f"{'W' if won else 'L'} {score} @ {game.get('home_name', '?')}"
    return None


def _render_owner_results_compact(dynasty, season):
    if not season or not hasattr(season, 'tier_seasons'):
        if dynasty.last_season_owner_results:
            _render_results_table(dynasty.last_season_owner_results)
        return

    owner_tier = dynasty.tier_assignments.get(dynasty.owner.club_key, 1)
    ts = season.tier_seasons.get(owner_tier)
    if not ts:
        return

    schedule = ts.get_schedule()
    results = []
    for week_data in schedule.get("weeks", []):
        wk = week_data.get("week", 0)
        for game in week_data.get("games", []):
            if not game.get("completed"):
                continue
            is_home = game.get("home_key") == dynasty.owner.club_key
            is_away = game.get("away_key") == dynasty.owner.club_key
            if not (is_home or is_away):
                continue
            hs = game.get("home_score", 0)
            aws = game.get("away_score", 0)
            if is_home:
                my_score, opp_score = hs, aws
                opp_name = game.get("away_name", "")
                loc = "H"
            else:
                my_score, opp_score = aws, hs
                opp_name = game.get("home_name", "")
                loc = "A"
            result = "W" if my_score > opp_score else "L" if my_score < opp_score else "D"
            results.append({
                "week": wk, "opponent": opp_name, "location": loc,
                "my_score": my_score, "opp_score": opp_score, "result": result,
            })

    if results:
        ui.label("Your Results").classes("text-sm font-semibold text-slate-600 mt-2 mb-1")
        _render_results_table(results)


def _render_results_table(results):
    columns = [
        {"name": "wk", "label": "Wk", "field": "wk", "align": "center"},
        {"name": "result", "label": "", "field": "result", "align": "center"},
        {"name": "score", "label": "Score", "field": "score", "align": "center"},
        {"name": "loc", "label": "", "field": "loc", "align": "center"},
        {"name": "opponent", "label": "Opponent", "field": "opponent", "align": "left"},
    ]
    rows = []
    for g in results:
        rows.append({
            "wk": g.get("week", ""),
            "result": g.get("result", ""),
            "score": f"{int(g.get('my_score', 0))}-{int(g.get('opp_score', 0))}",
            "loc": g.get("location", ""),
            "opponent": g.get("opponent", ""),
            "_result": g.get("result", ""),
        })
    tbl = ui.table(columns=columns, rows=rows, row_key="wk").classes("w-full").props("dense flat")
    tbl.add_slot("body", r"""
        <q-tr :props="props" :style="{
            'background-color':
                props.row._result === 'W' ? '#f0fdf4' :
                props.row._result === 'L' ? '#fef2f2' : ''
        }">
            <q-td v-for="col in props.cols" :key="col.name" :props="props"
                  :style="col.name === 'result' ? {
                      'color': props.row._result === 'W' ? '#16a34a' :
                               props.row._result === 'L' ? '#dc2626' : '#d97706',
                      'font-weight': '700'
                  } : {}">
                {{ col.value }}
            </q-td>
        </q-tr>
    """)


# ═══════════════════════════════════════════════════════════════
# MY TEAM (ROSTER) TAB
# ═══════════════════════════════════════════════════════════════

def _fill_roster(containers, dynasty):
    c = containers.get("roster")
    if not c:
        return

    with c:
        roster = dynasty.get_owner_roster()
        summary = dynasty.get_owner_team_summary()

        with ui.row().classes("w-full gap-3 flex-wrap mb-4"):
            for label, value in [
                ("Roster Size", f"{summary.get('roster_size', 0)} / 40"),
                ("Avg OVR", str(summary.get("overall_rating", 0))),
                ("Avg Age", str(summary.get("average_age", 0))),
            ]:
                with ui.card().classes("flex-1 min-w-[140px] p-3 text-center"):
                    ui.label(label).classes("text-xs text-slate-400 uppercase")
                    ui.label(value).classes("text-lg font-bold text-slate-800")

            pos_counts = summary.get("position_counts", {})
            if pos_counts:
                with ui.card().classes("flex-1 min-w-[200px] p-3"):
                    ui.label("Positional Depth").classes("text-xs text-slate-400 uppercase mb-1")
                    with ui.row().classes("gap-2 flex-wrap"):
                        for pos, cnt in sorted(pos_counts.items(), key=lambda x: -x[1]):
                            ui.badge(f"{pos}: {cnt}").props("outline")

        with ui.tabs().classes("w-full") as roster_tabs:
            tab_full = ui.tab("Full Roster")
            tab_fa = ui.tab("Free Agents")

        with ui.tab_panels(roster_tabs, value=tab_full).classes("w-full"):
            with ui.tab_panel(tab_full):
                _render_roster_table(roster, dynasty)
            with ui.tab_panel(tab_fa):
                _render_free_agents(dynasty)


def _render_roster_table(roster, dynasty):
    if not roster:
        ui.label("No roster data available. Start a season first.").classes("text-sm text-slate-400 italic")
        return

    columns = [
        {"name": "num", "label": "#", "field": "number", "align": "center"},
        {"name": "name", "label": "Name", "field": "name", "align": "left", "sortable": True},
        {"name": "pos", "label": "Pos", "field": "position", "align": "center"},
        {"name": "age", "label": "Age", "field": "age", "align": "center", "sortable": True},
        {"name": "ovr", "label": "OVR", "field": "overall", "align": "center", "sortable": True},
        {"name": "spd", "label": "SPD", "field": "speed", "align": "center", "sortable": True},
        {"name": "kick", "label": "KICK", "field": "kicking", "align": "center", "sortable": True},
        {"name": "lat", "label": "LAT", "field": "lateral_skill", "align": "center", "sortable": True},
        {"name": "tkl", "label": "TKL", "field": "tackling", "align": "center", "sortable": True},
        {"name": "arch", "label": "Archetype", "field": "archetype", "align": "left"},
        {"name": "dev", "label": "Dev", "field": "development", "align": "center"},
        {"name": "action", "label": "", "field": "action", "align": "center"},
    ]

    rows = []
    for p in sorted(roster, key=lambda x: -x.get("overall", 0)):
        rows.append({
            "number": str(p.get("number", "")),
            "name": p.get("name", "?"),
            "position": p.get("position", ""),
            "age": str(p.get("age", "")),
            "overall": str(p.get("overall", 0)),
            "speed": str(p.get("speed", 0)),
            "kicking": str(p.get("kicking", 0)),
            "lateral_skill": str(p.get("lateral_skill", 0)),
            "tackling": str(p.get("tackling", 0)),
            "archetype": p.get("archetype", ""),
            "development": p.get("development", ""),
            "action": "cut",
        })

    tbl = ui.table(columns=columns, rows=rows, row_key="name").classes("w-full").props(
        "dense flat bordered virtual-scroll"
    ).style("max-height: 500px;")

    tbl.add_slot("body-cell-ovr", r'''
        <q-td :props="props">
            <span :style="{
                color: parseInt(props.row.overall) >= 85 ? '#15803d' :
                       parseInt(props.row.overall) >= 75 ? '#16a34a' :
                       parseInt(props.row.overall) >= 65 ? '#ca8a04' :
                       parseInt(props.row.overall) >= 55 ? '#ea580c' : '#dc2626',
                fontWeight: '700'
            }">{{ props.row.overall }}</span>
        </q-td>
    ''')

    tbl.add_slot("body-cell-action", r'''
        <q-td :props="props">
            <q-btn flat dense size="sm" color="red" icon="person_remove" label="Cut"
                   @click="$parent.$emit('cut_player', props.row)" />
        </q-td>
    ''')

    async def _on_cut(e):
        d = _get_dynasty()
        if not d:
            return
        name = e.args.get("name", "")
        success, msg = d.cut_player(name)
        if success:
            _set_dynasty(d)
            ui.notify(msg, type="positive")
            refresh = app.storage.user.get("_wvl_refresh")
            if refresh:
                refresh()
        else:
            ui.notify(msg, type="warning")

    tbl.on("cut_player", _on_cut)


def _render_free_agents(dynasty):
    fa_list = dynasty.get_available_free_agents(count=25)
    if not fa_list:
        ui.label("No free agents available.").classes("text-sm text-slate-400 italic")
        return

    ui.label("Available Free Agents").classes("text-sm font-semibold text-slate-600 mb-2")
    ui.label("Sign players to add to your roster (max 40).").classes("text-xs text-slate-400 mb-2")

    columns = [
        {"name": "name", "label": "Name", "field": "name", "align": "left", "sortable": True},
        {"name": "pos", "label": "Pos", "field": "position", "align": "center"},
        {"name": "age", "label": "Age", "field": "age", "align": "center", "sortable": True},
        {"name": "ovr", "label": "OVR", "field": "overall", "align": "center", "sortable": True},
        {"name": "spd", "label": "SPD", "field": "speed", "align": "center", "sortable": True},
        {"name": "kick", "label": "KICK", "field": "kicking", "align": "center", "sortable": True},
        {"name": "arch", "label": "Archetype", "field": "archetype", "align": "left"},
        {"name": "sal", "label": "Salary", "field": "asking_salary", "align": "center"},
        {"name": "action", "label": "", "field": "action", "align": "center"},
    ]

    rows = []
    for p in sorted(fa_list, key=lambda x: -x.get("overall", 0)):
        rows.append({
            "name": p.get("name", "?"),
            "position": p.get("position", ""),
            "age": str(p.get("age", "")),
            "overall": str(p.get("overall", 0)),
            "speed": str(p.get("speed", 0)),
            "kicking": str(p.get("kicking", 0)),
            "archetype": p.get("archetype", ""),
            "asking_salary": f"Tier {p.get('asking_salary', 1)}",
            "action": "sign",
            "_idx": p.get("_idx", 0),
        })

    tbl = ui.table(columns=columns, rows=rows, row_key="name").classes("w-full").props(
        "dense flat bordered virtual-scroll"
    ).style("max-height: 400px;")

    tbl.add_slot("body-cell-ovr", r'''
        <q-td :props="props">
            <span :style="{
                color: parseInt(props.row.overall) >= 85 ? '#15803d' :
                       parseInt(props.row.overall) >= 75 ? '#16a34a' :
                       parseInt(props.row.overall) >= 65 ? '#ca8a04' :
                       parseInt(props.row.overall) >= 55 ? '#ea580c' : '#dc2626',
                fontWeight: '700'
            }">{{ props.row.overall }}</span>
        </q-td>
    ''')

    tbl.add_slot("body-cell-action", r'''
        <q-td :props="props">
            <q-btn flat dense size="sm" color="green" icon="person_add" label="Sign"
                   @click="$parent.$emit('sign_player', props.row)" />
        </q-td>
    ''')

    async def _on_sign(e):
        d = _get_dynasty()
        if not d:
            return
        name = e.args.get("name", "")
        fa_pool = getattr(d, '_fa_pool', [])
        target = None
        for fa in fa_pool:
            if fa.player_card.full_name == name:
                target = fa
                break
        if not target:
            ui.notify("Player not found in FA pool.", type="warning")
            return
        success, msg = d.sign_free_agent(target.player_card, target.asking_salary)
        if success:
            _set_dynasty(d)
            ui.notify(msg, type="positive")
            refresh = app.storage.user.get("_wvl_refresh")
            if refresh:
                refresh()
        else:
            ui.notify(msg, type="warning")

    tbl.on("sign_player", _on_sign)


# ═══════════════════════════════════════════════════════════════
# SCHEDULE TAB
# ═══════════════════════════════════════════════════════════════

def _fill_schedule(containers, dynasty):
    c = containers.get("schedule")
    if not c:
        return

    season = app.storage.user.get(_WVL_SEASON_KEY)

    with c:
        if not season or not hasattr(season, 'tier_seasons'):
            if dynasty.last_season_schedule:
                ui.label("Last Season Schedule").classes("text-sm font-semibold text-slate-600 mb-2")
            else:
                ui.label("Start a season to see the schedule.").classes("text-sm text-slate-400 italic")
            return

        owner_tier = dynasty.tier_assignments.get(dynasty.owner.club_key, 1)
        schedule_data = season.get_schedule(owner_tier)
        weeks = schedule_data.get("weeks", [])

        if not weeks:
            ui.label("No schedule available.").classes("text-sm text-slate-400 italic")
            return

        completed_weeks = [w for w in weeks if any(g.get("completed") for g in w.get("games", []))]
        latest_week = completed_weeks[-1]["week"] if completed_weeks else weeks[0]["week"]

        week_options = {w["week"]: f"Week {w['week']}" for w in weeks}
        selected_week = {"val": latest_week}
        sched_box = ui.column().classes("w-full")

        def _fill_week():
            sched_box.clear()
            wk = selected_week["val"]
            week_data = next((w for w in weeks if w["week"] == wk), None)
            if not week_data:
                return

            with sched_box:
                for game in week_data["games"]:
                    is_owner = (
                        game.get("home_key") == dynasty.owner.club_key or
                        game.get("away_key") == dynasty.owner.club_key
                    )
                    border = "border-left: 4px solid #6366f1;" if is_owner else "border-left: 4px solid transparent;"

                    with ui.card().classes("p-3 mb-2 w-full").style(f"border: 1px solid #e2e8f0; {border}"):
                        if game.get("completed"):
                            h_score = int(game.get("home_score", 0))
                            a_score = int(game.get("away_score", 0))
                            h_bold = "font-bold" if h_score > a_score else ""
                            a_bold = "font-bold" if a_score > h_score else ""
                            with ui.row().classes("items-center gap-3 flex-wrap"):
                                ui.label(game["away_name"]).classes(f"text-sm {a_bold} min-w-[160px]")
                                ui.label(str(a_score)).classes(f"text-lg {a_bold} w-8 text-center")
                                ui.label("@").classes("text-xs text-slate-400")
                                ui.label(str(h_score)).classes(f"text-lg {h_bold} w-8 text-center")
                                ui.label(game["home_name"]).classes(f"text-sm {h_bold}")

                                mk = game.get("matchup_key", "")
                                if mk:
                                    def _show_box(t=owner_tier, w=wk, m=mk):
                                        from nicegui_app.pages.pro_leagues import _show_box_score_dialog
                                        box = season.get_box_score(t, w, m)
                                        if box:
                                            _show_box_score_dialog(box)
                                        else:
                                            ui.notify("Box score not available.", type="warning")

                                    ui.button("Box Score", icon="assessment", on_click=_show_box).props(
                                        "flat dense no-caps size=sm color=indigo"
                                    )
                        else:
                            with ui.row().classes("items-center gap-3"):
                                ui.label(game["away_name"]).classes("text-sm min-w-[160px]")
                                ui.label("@").classes("text-xs text-slate-400")
                                ui.label(game["home_name"]).classes("text-sm")
                                ui.label("Upcoming").classes("text-xs text-slate-400 italic")

        def _on_week_change(e):
            selected_week["val"] = e.value
            _fill_week()

        ui.select(
            options=week_options,
            value=selected_week["val"],
            label="Select Week",
            on_change=_on_week_change,
        ).classes("w-40 mb-3")

        _fill_week()


# ═══════════════════════════════════════════════════════════════
# LEAGUE TAB
# ═══════════════════════════════════════════════════════════════

def _fill_league(containers, dynasty):
    c = containers.get("league")
    if not c:
        return

    season = app.storage.user.get(_WVL_SEASON_KEY)

    with c:
        if season and hasattr(season, 'tier_seasons'):
            all_standings = season.get_all_standings()
        else:
            all_standings = dynasty.last_season_standings or {}

        if not all_standings:
            ui.label("No standings available yet.").classes("text-sm text-slate-400 italic")
            return

        for tier_num in sorted(all_standings.keys()):
            tc = TIER_BY_NUMBER.get(tier_num)
            tier_standings = all_standings.get(tier_num, {})
            ranked = tier_standings.get("ranked", [])
            is_owner_tier = (tier_num == dynasty.tier_assignments.get(dynasty.owner.club_key, 1))

            header_parts = [f"Tier {tier_num}"]
            if tc:
                header_parts[0] += f" — {tc.tier_name}"

            with ui.expansion(" | ".join(header_parts), icon="table_chart", value=is_owner_tier).classes("w-full"):
                if ranked:
                    _render_zone_standings(ranked, dynasty.owner.club_key)
                else:
                    ui.label("No standings data.").classes("text-sm text-slate-400 italic")

        if season and hasattr(season, 'tier_seasons'):
            leaders = season.get_all_stat_leaders()
            if any(leaders.values()):
                ui.separator().classes("mt-4")
                ui.label("Season Stat Leaders").classes("text-lg font-semibold text-slate-700 mb-2")
                _render_stat_leaders(leaders, season, dynasty)


def _render_zone_standings(ranked, owner_club_key):
    columns = [
        {"name": "pos", "label": "#", "field": "pos", "align": "center"},
        {"name": "team", "label": "Team", "field": "team", "align": "left"},
        {"name": "country", "label": "", "field": "country", "align": "left"},
        {"name": "record", "label": "W-L", "field": "record", "align": "center"},
        {"name": "pct", "label": "PCT", "field": "pct", "align": "center"},
        {"name": "pf", "label": "PF", "field": "pf", "align": "right"},
        {"name": "pa", "label": "PA", "field": "pa", "align": "right"},
        {"name": "diff", "label": "DIFF", "field": "diff", "align": "right"},
        {"name": "streak", "label": "STR", "field": "streak", "align": "center"},
    ]
    rows = []
    for i, t in enumerate(ranked):
        key = t.get("team_key", "")
        club_info = CLUBS_BY_KEY.get(key)
        zone = t.get("zone", "safe")
        diff_val = t.get("diff", 0)
        try:
            diff_val = int(diff_val)
        except (ValueError, TypeError):
            diff_val = 0
        rows.append({
            "pos": t.get("position", i + 1),
            "team": t.get("team_name", key),
            "country": club_info.country if club_info else "",
            "record": f"{t.get('wins', 0)}-{t.get('losses', 0)}",
            "pct": f"{float(t.get('pct', 0)):.3f}" if t.get("pct") else ".000",
            "pf": t.get("pf", t.get("points_for", 0)),
            "pa": t.get("pa", t.get("points_against", 0)),
            "diff": f"{diff_val:+d}" if diff_val else "0",
            "streak": t.get("streak", "-"),
            "_zone": zone,
            "_owner": key == owner_club_key,
        })

    table = ui.table(columns=columns, rows=rows, row_key="pos").classes("w-full").props("dense flat")
    table.add_slot("body", r"""
        <q-tr :props="props" :style="{
            'background-color':
                props.row._owner && props.row._zone === 'promotion' ? '#dcfce7' :
                props.row._owner && props.row._zone === 'relegation' ? '#fee2e2' :
                props.row._owner && props.row._zone === 'playoff' ? '#fef3c7' :
                props.row._owner ? '#e0e7ff' :
                props.row._zone === 'promotion' ? '#f0fdf4' :
                props.row._zone === 'relegation' ? '#fef2f2' :
                props.row._zone === 'playoff' ? '#fffbeb' : '',
            'font-weight': props.row._owner ? '700' : '400'
        }">
            <q-td v-for="col in props.cols" :key="col.name" :props="props">
                {{ col.value }}
            </q-td>
        </q-tr>
    """)
    with ui.row().classes("gap-4 mt-1 text-[10px] text-gray-400"):
        ui.html('<span style="background:#f0fdf4;padding:2px 6px;border-radius:3px;">Promotion</span>')
        ui.html('<span style="background:#fffbeb;padding:2px 6px;border-radius:3px;">Playoff</span>')
        ui.html('<span style="background:#fef2f2;padding:2px 6px;border-radius:3px;">Relegation</span>')


def _render_stat_leaders(leaders, season, dynasty):
    from nicegui_app.pages.pro_leagues import _show_player_card as _show_pc

    def _stat_table(data, col_spec):
        if not data:
            ui.label("No data yet.").classes("text-sm text-slate-400")
            return
        columns = [
            {"name": k, "label": lbl, "field": k, "sortable": True,
             "align": "left" if k in ("name", "team") else "center"}
            for k, lbl in col_spec
        ]
        rows = [
            {**{k: p.get(k, "") for k, _ in col_spec},
             "team_key": p.get("team_key", ""), "tier_num": p.get("tier_num", 0),
             "_idx": i}
            for i, p in enumerate(data[:50])
        ]
        tbl = (
            ui.table(columns=columns, rows=rows, row_key="_idx")
            .classes("w-full")
            .props("dense flat bordered virtual-scroll")
            .style("max-height: 400px;")
        )
        tbl.add_slot("body-cell-name", '''
            <q-td :props="props">
                <a class="text-indigo-600 font-semibold cursor-pointer hover:underline"
                   @click="$parent.$emit('player_click', props.row)">
                    {{ props.row.name }}
                </a>
            </q-td>
        ''')

        def _on_click(e):
            tier_num = e.args.get("tier_num", 0)
            team_key = e.args.get("team_key", "")
            name = e.args.get("name", "")
            ts = season.tier_seasons.get(tier_num) if season else None
            if ts:
                _show_pc(ts, team_key, name)

        tbl.on("player_click", _on_click)

    with ui.tabs().classes("w-full") as st:
        tab_r = ui.tab("Rushing")
        tab_k = ui.tab("Kick-Pass")
        tab_s = ui.tab("Scoring")
        tab_d = ui.tab("Defense")

    with ui.tab_panels(st, value=tab_r).classes("w-full"):
        with ui.tab_panel(tab_r):
            _stat_table(leaders.get("rushing", []), [
                ("name", "Player"), ("team", "Team"), ("tier", "Tier"),
                ("yards", "Rush Yds"), ("carries", "Car"), ("ypc", "YPC"), ("games", "GP"),
            ])
        with ui.tab_panel(tab_k):
            _stat_table(leaders.get("kick_pass", []), [
                ("name", "Player"), ("team", "Team"), ("tier", "Tier"),
                ("yards", "KP Yds"), ("completions", "Comp"), ("attempts", "Att"),
                ("pct", "Pct%"), ("games", "GP"),
            ])
        with ui.tab_panel(tab_s):
            _stat_table(leaders.get("scoring", []), [
                ("name", "Player"), ("team", "Team"), ("tier", "Tier"),
                ("touchdowns", "TD"), ("dk_made", "DK"), ("games", "GP"),
            ])
        with ui.tab_panel(tab_d):
            _stat_table(leaders.get("tackles", []), [
                ("name", "Player"), ("team", "Team"), ("tier", "Tier"),
                ("tackles", "TKL"), ("fumbles", "FUM"), ("games", "GP"),
            ])


# ═══════════════════════════════════════════════════════════════
# FINANCES TAB
# ═══════════════════════════════════════════════════════════════

def _fill_finance(containers, dynasty):
    c = containers.get("finance")
    if not c:
        return

    with c:
        with ui.row().classes("w-full gap-4 flex-wrap mb-4"):
            with ui.card().classes("flex-1 min-w-[200px] p-4"):
                ui.label("Current Bankroll").classes("text-xs text-slate-400 uppercase")
                color = "text-green-600" if dynasty.owner.bankroll > 15 else "text-amber-600" if dynasty.owner.bankroll > 5 else "text-red-600"
                ui.label(f"${dynasty.owner.bankroll:.1f}M").classes(f"text-3xl font-bold {color}")
                if dynasty.owner.bankroll < 5:
                    ui.label("Warning: Low bankroll! Risk of forced sale.").classes("text-xs text-red-500 mt-1")

            with ui.card().classes("flex-1 min-w-[200px] p-4"):
                ui.label("Seasons Owned").classes("text-xs text-slate-400 uppercase")
                ui.label(str(dynasty.owner.seasons_owned)).classes("text-3xl font-bold text-slate-800")

            with ui.card().classes("flex-1 min-w-[200px] p-4"):
                arch = OWNER_ARCHETYPES.get(dynasty.owner.archetype, {})
                ui.label("Owner Archetype").classes("text-xs text-slate-400 uppercase")
                ui.label(arch.get("label", dynasty.owner.archetype)).classes("text-lg font-bold text-indigo-700")
                ui.label(arch.get("description", "")).classes("text-xs text-slate-500")

        with ui.row().classes("w-full gap-4 flex-wrap mb-4"):
            with ui.card().classes("flex-1 min-w-[300px] p-4"):
                ui.label("President").classes("text-sm font-semibold text-slate-700 mb-2")
                if dynasty.president:
                    parch = PRESIDENT_ARCHETYPES.get(dynasty.president.archetype, {})
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.icon("badge", size="sm").classes("text-amber-600")
                        ui.label(dynasty.president.name).classes("font-semibold")
                        ui.badge(parch.get("label", ""), color="amber").props("outline dense")
                    ui.label(f"Contract: {dynasty.president.contract_years}yr remaining").classes("text-xs text-slate-500")
                    with ui.row().classes("gap-4 mt-2"):
                        for lbl, val in [
                            ("ACU", dynasty.president.acumen),
                            ("BDG", dynasty.president.budget_mgmt),
                            ("EYE", dynasty.president.recruiting_eye),
                            ("HIR", dynasty.president.staff_hiring),
                        ]:
                            with ui.column().classes("items-center"):
                                ui.label(str(val)).classes("text-lg font-bold text-gray-800")
                                ui.label(lbl).classes("text-[10px] text-gray-400 uppercase")
                else:
                    ui.label("No president hired").classes("text-red-500 text-sm italic")

            with ui.card().classes("flex-1 min-w-[300px] p-4"):
                ui.label("Investment Allocation").classes("text-sm font-semibold text-slate-700 mb-2")
                inv = dynasty.investment
                allocs = [
                    ("Training", inv.training),
                    ("Coaching", inv.coaching),
                    ("Stadium", inv.stadium),
                    ("Youth Academy", inv.youth),
                    ("Sports Science", inv.science),
                    ("Marketing", inv.marketing),
                ]
                for label, val in allocs:
                    with ui.row().classes("items-center gap-2 w-full"):
                        ui.label(label).classes("text-xs text-slate-600 w-28")
                        pct = val * 100
                        ui.linear_progress(value=val, size="12px").classes("flex-1").props(
                            f"color={'green' if val > 0.2 else 'blue'}"
                        )
                        ui.label(f"{pct:.0f}%").classes("text-xs text-slate-500 w-10 text-right")

        if dynasty.financial_history:
            with ui.card().classes("w-full p-4"):
                ui.label("Financial History").classes("text-sm font-semibold text-slate-700 mb-2")
                fh_cols = [
                    {"name": "year", "label": "Year", "field": "year", "align": "center"},
                    {"name": "revenue", "label": "Revenue", "field": "revenue", "align": "right"},
                    {"name": "expenses", "label": "Expenses", "field": "expenses", "align": "right"},
                    {"name": "net", "label": "Net", "field": "net", "align": "right"},
                    {"name": "bankroll", "label": "Bankroll", "field": "bankroll", "align": "right"},
                ]
                fh_rows = []
                for year in sorted(dynasty.financial_history.keys()):
                    fh = dynasty.financial_history[year]
                    rev = fh.get("total_revenue", 0)
                    exp = fh.get("total_expenses", 0)
                    net = rev - exp
                    fh_rows.append({
                        "year": str(year),
                        "revenue": f"${rev:.1f}M",
                        "expenses": f"${exp:.1f}M",
                        "net": f"{'+'if net>=0 else ''}{net:.1f}M",
                        "bankroll": f"${fh.get('bankroll_end', 0):.1f}M",
                    })
                ui.table(columns=fh_cols, rows=fh_rows, row_key="year").classes("w-full").props("dense flat bordered")


# ═══════════════════════════════════════════════════════════════
# OFFSEASON FLOW — MULTI-STEP WIZARD
# ═══════════════════════════════════════════════════════════════

_OFFSEASON_STEPS = [
    ("recap", "Season Recap", "emoji_events"),
    ("prom_rel", "Promotion & Relegation", "swap_vert"),
    ("retirements", "Retirements", "airline_seat_flat"),
    ("import", "Player Import", "file_upload"),
    ("free_agency", "Free Agency", "groups"),
    ("development", "Development", "trending_up"),
    ("investment", "Investment", "savings"),
    ("financials", "Financial Summary", "account_balance"),
]


def _render_offseason_controls(container, dynasty):
    offseason_data = app.storage.user.get("_wvl_offseason_data")
    step_idx = app.storage.user.get("_wvl_offseason_step", 0)

    if not offseason_data or not isinstance(offseason_data, dict):
        _render_offseason_start(container, dynasty)
    else:
        if not isinstance(step_idx, int) or step_idx < 0 or step_idx >= len(_OFFSEASON_STEPS):
            step_idx = 0
            app.storage.user["_wvl_offseason_step"] = 0
        _render_offseason_step(container, dynasty, offseason_data, step_idx)


def _render_offseason_start(container, dynasty):
    with ui.element("div").classes("w-full").style(
        "background: linear-gradient(135deg, #92400e 0%, #d97706 100%); padding: 24px; border-radius: 8px;"
    ):
        ui.label(f"Year {dynasty.current_year} Offseason").classes("text-2xl font-bold text-white")
        ui.label("Process your end-of-season transitions step by step.").classes("text-sm text-amber-100")

    cached_graduates = app.storage.user.get("cvl_graduates")
    if cached_graduates:
        with ui.row().classes("items-center gap-2 mt-3 mb-1"):
            ui.icon("check_circle").classes("text-green-600")
            ui.label(
                f"{len(cached_graduates)} CVL graduates available for import."
            ).classes("text-sm text-green-700 font-semibold")

    with ui.row().classes("gap-2 mt-4"):
        async def _begin_offseason():
            import random
            d = _get_dynasty()
            s = app.storage.user.get(_WVL_SEASON_KEY)
            if not d or not s:
                ui.notify("No season data.", type="warning")
                return

            rng = random.Random()
            cached_grads = app.storage.user.get("cvl_graduates")

            ui.notify("Processing offseason...", type="info")

            offseason = d.run_offseason(
                s,
                investment_budget=5.0,
                import_data=cached_grads,
                rng=rng,
            )

            _set_dynasty(d)
            _register_wvl_season(d, s)

            app.storage.user["_wvl_offseason_data"] = offseason
            app.storage.user["_wvl_offseason_step"] = 0

            refresh = app.storage.user.get("_wvl_refresh")
            if refresh:
                refresh()

        ui.button("Begin Offseason", icon="autorenew", on_click=_begin_offseason).classes(
            "bg-amber-600 text-white px-6 py-2 rounded-lg"
        )

        async def _reset():
            _set_dynasty(None)
            _set_phase("setup")
            app.storage.user.pop(_WVL_SEASON_KEY, None)
            app.storage.user.pop("_wvl_offseason_data", None)
            app.storage.user.pop("_wvl_offseason_step", None)
            refresh = app.storage.user.get("_wvl_refresh")
            if refresh:
                refresh()

        ui.button("New Dynasty", icon="restart_alt", on_click=_reset).classes(
            "bg-red-600 text-white px-4 py-2 rounded-lg"
        )


def _render_offseason_step(container, dynasty, data, step_idx):
    step_key, step_title, step_icon = _OFFSEASON_STEPS[step_idx]
    total_steps = len(_OFFSEASON_STEPS)

    with ui.element("div").classes("w-full").style(
        "background: linear-gradient(135deg, #92400e 0%, #d97706 100%); padding: 20px 24px; border-radius: 8px;"
    ):
        with ui.row().classes("w-full items-center justify-between"):
            with ui.column().classes("gap-0"):
                ui.label(f"Offseason — Step {step_idx + 1}/{total_steps}").classes("text-lg font-bold text-white")
                ui.label(step_title).classes("text-sm text-amber-100")
            with ui.row().classes("gap-1"):
                for i in range(total_steps):
                    dot_color = "bg-white" if i <= step_idx else "bg-amber-300 opacity-40"
                    ui.element("div").classes(f"w-2 h-2 rounded-full {dot_color}")

    with ui.card().classes("w-full p-5 mt-3"):
        step_renderers = {
            "recap": _offseason_step_recap,
            "prom_rel": _offseason_step_prom_rel,
            "retirements": _offseason_step_retirements,
            "import": _offseason_step_import,
            "free_agency": _offseason_step_free_agency,
            "development": _offseason_step_development,
            "investment": _offseason_step_investment,
            "financials": _offseason_step_financials,
        }
        renderer = step_renderers.get(step_key)
        if renderer:
            renderer(dynasty, data)

    with ui.row().classes("w-full justify-between mt-3"):
        if step_idx > 0:
            async def _prev():
                app.storage.user["_wvl_offseason_step"] = step_idx - 1
                refresh = app.storage.user.get("_wvl_refresh")
                if refresh:
                    refresh()
            ui.button("Back", icon="arrow_back", on_click=_prev).props("flat no-caps")
        else:
            ui.element("div")

        if step_idx < total_steps - 1:
            async def _next():
                app.storage.user["_wvl_offseason_step"] = step_idx + 1
                refresh = app.storage.user.get("_wvl_refresh")
                if refresh:
                    refresh()
            ui.button("Next", icon="arrow_forward", on_click=_next).classes(
                "bg-amber-600 text-white"
            ).props("no-caps")
        else:
            async def _finish():
                app.storage.user.pop("_wvl_offseason_data", None)
                app.storage.user.pop("_wvl_offseason_step", None)
                app.storage.user.pop(_WVL_SEASON_KEY, None)
                _set_phase("pre_season")
                refresh = app.storage.user.get("_wvl_refresh")
                if refresh:
                    refresh()
            ui.button("Start Next Season", icon="play_arrow", on_click=_finish).classes(
                "bg-green-600 text-white"
            ).props("no-caps")


def _offseason_step_recap(dynasty, data):
    ui.label("Season Recap").classes("text-lg font-semibold text-slate-700 mb-3")

    owner_results = dynasty.last_season_owner_results
    wins = sum(1 for r in owner_results if r.get("result") == "W")
    losses = sum(1 for r in owner_results if r.get("result") == "L")

    club = CLUBS_BY_KEY.get(dynasty.owner.club_key)
    club_name = club.name if club else dynasty.owner.club_key
    owner_tier = dynasty.tier_assignments.get(dynasty.owner.club_key, 1)

    with ui.row().classes("w-full gap-4 flex-wrap mb-4"):
        with ui.card().classes("flex-1 min-w-[160px] p-4 text-center"):
            ui.label(club_name).classes("text-xs text-slate-400 uppercase")
            ui.label(f"{wins}-{losses}").classes("text-3xl font-bold text-slate-800")

        for tier_num in sorted(dynasty.last_season_champions.keys()):
            champ_key = dynasty.last_season_champions[tier_num]
            champ_club = CLUBS_BY_KEY.get(champ_key)
            champ_name = champ_club.name if champ_club else champ_key
            tc = TIER_BY_NUMBER.get(tier_num)
            tier_label = tc.tier_name if tc else f"Tier {tier_num}"
            is_owner = champ_key == dynasty.owner.club_key
            with ui.card().classes(f"flex-1 min-w-[160px] p-4 text-center {'ring-2 ring-amber-400' if is_owner else ''}"):
                ui.label(f"{tier_label} Champion").classes("text-xs text-amber-500 uppercase")
                ui.icon("emoji_events", size="md").classes("text-amber-500")
                ui.label(champ_name).classes(f"text-sm font-bold {'text-amber-700' if is_owner else 'text-slate-700'}")

    if owner_results:
        _render_results_table(owner_results)


def _offseason_step_prom_rel(dynasty, data):
    ui.label("Promotion & Relegation").classes("text-lg font-semibold text-slate-700 mb-3")

    prom_rel = data.get("promotion_relegation") or {}
    movements = prom_rel.get("movements") or []

    if not movements:
        ui.label("No promotion or relegation movements this season.").classes("text-sm text-slate-400 italic")
        return

    promotions = [m for m in movements if m["to_tier"] < m["from_tier"]]
    relegations = [m for m in movements if m["to_tier"] > m["from_tier"]]

    if promotions:
        ui.label("Promoted").classes("text-sm font-semibold text-green-700 mb-1")
        for m in promotions:
            is_owner = m.get("team_key") == dynasty.owner.club_key
            with ui.row().classes("items-center gap-2 mb-1"):
                ui.icon("arrow_upward", size="sm").classes("text-green-600")
                text = f"{m['team_name']} — Tier {m['from_tier']} to Tier {m['to_tier']}"
                if is_owner:
                    text = f"YOUR CLUB: {text}"
                ui.label(text).classes(f"text-sm {'font-bold text-green-700' if is_owner else ''}")

    if relegations:
        ui.label("Relegated").classes("text-sm font-semibold text-red-700 mb-1 mt-3")
        for m in relegations:
            is_owner = m.get("team_key") == dynasty.owner.club_key
            with ui.row().classes("items-center gap-2 mb-1"):
                ui.icon("arrow_downward", size="sm").classes("text-red-600")
                text = f"{m['team_name']} — Tier {m['from_tier']} to Tier {m['to_tier']}"
                if is_owner:
                    text = f"YOUR CLUB: {text}"
                ui.label(text).classes(f"text-sm {'font-bold text-red-700' if is_owner else ''}")


def _offseason_step_retirements(dynasty, data):
    ui.label("Retirements & Departures").classes("text-lg font-semibold text-slate-700 mb-3")

    retirements = data.get("retirements") or {}
    if not isinstance(retirements, dict):
        retirements = {}
    if not retirements or sum(len(v) for v in retirements.values()) == 0:
        ui.label("No retirements this offseason.").classes("text-sm text-slate-400 italic")
        return

    owner_retirements = retirements.get(dynasty.owner.club_key, [])
    other_count = sum(len(v) for k, v in retirements.items() if k != dynasty.owner.club_key) if isinstance(retirements, dict) else 0

    if owner_retirements:
        ui.label("Your Team").classes("text-sm font-semibold text-indigo-700 mb-1")
        columns = [
            {"name": "name", "label": "Player", "field": "name", "align": "left"},
            {"name": "pos", "label": "Position", "field": "pos", "align": "center"},
            {"name": "age", "label": "Age", "field": "age", "align": "center"},
            {"name": "ovr", "label": "OVR", "field": "ovr", "align": "center"},
        ]
        rows = []
        for i, p in enumerate(owner_retirements):
            if isinstance(p, str):
                rows.append({"name": p, "pos": "-", "age": "-", "ovr": "-", "_idx": i})
            elif isinstance(p, dict):
                rows.append({
                    "name": p.get("name", p.get("player_name", "?")),
                    "pos": p.get("position", "-"),
                    "age": str(p.get("age", "-")),
                    "ovr": str(p.get("overall", "-")),
                    "_idx": i,
                })
            else:
                rows.append({"name": str(p), "pos": "-", "age": "-", "ovr": "-", "_idx": i})
        ui.table(columns=columns, rows=rows, row_key="_idx").classes("w-full mb-3").props("dense flat bordered")

    if other_count:
        ui.label(f"{other_count} other players retired across the league.").classes("text-sm text-slate-500 mt-2")


def _offseason_step_import(dynasty, data):
    ui.label("Player Import").classes("text-lg font-semibold text-slate-700 mb-3")

    cached_graduates = app.storage.user.get("cvl_graduates")
    cached_year = app.storage.user.get("cvl_graduates_year")

    if cached_graduates:
        ui.label(
            f"CVL Class of {cached_year or '?'} — {len(cached_graduates)} graduates available"
        ).classes("text-sm text-green-700 font-semibold mb-2")
        ui.label(
            "These players were automatically included in this offseason's free agency pool."
        ).classes("text-xs text-slate-500 mb-3")

        preview = cached_graduates[:15]
        columns = [
            {"name": "name", "label": "Name", "field": "name", "align": "left"},
            {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
            {"name": "school", "label": "School", "field": "school", "align": "left"},
            {"name": "ovr", "label": "OVR", "field": "ovr", "align": "center"},
        ]
        rows = []
        for i, p in enumerate(preview):
            name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip() or p.get("name", "?")
            rows.append({
                "name": name,
                "pos": p.get("position", "-"),
                "school": p.get("graduating_from", "-"),
                "ovr": str(p.get("overall", "-")),
                "_idx": i,
            })
        ui.table(columns=columns, rows=rows, row_key="_idx").classes("w-full").props("dense flat bordered")
        if len(cached_graduates) > 15:
            ui.label(f"... and {len(cached_graduates) - 15} more").classes("text-xs text-slate-400 italic mt-1")
    else:
        ui.label("No CVL graduates available.").classes("text-sm text-slate-400 italic mb-2")
        ui.label(
            "To import college players, run a CVL season first and use "
            "Export > Export Graduating Class before starting WVL offseason."
        ).classes("text-xs text-slate-500")

    ui.separator().classes("mt-3 mb-3")
    ui.label("Custom Player Import").classes("text-sm font-semibold text-slate-600")
    ui.label("Paste a JSON array of player objects to add to the FA pool.").classes("text-xs text-slate-400 mb-2")

    json_input = ui.textarea(
        label="Player JSON",
        placeholder='[{"first_name": "Jane", "last_name": "Doe", "position": "ZB", ...}]',
    ).classes("w-full").props("outlined rows=3")

    async def _import_custom():
        import json as _json
        d = _get_dynasty()
        if not d:
            return
        text = json_input.value.strip()
        if not text:
            ui.notify("Paste player data first.", type="warning")
            return
        try:
            players = _json.loads(text)
            if not isinstance(players, list):
                players = [players]
        except _json.JSONDecodeError as exc:
            ui.notify(f"Invalid JSON: {exc}", type="negative")
            return

        from engine.wvl_free_agency import build_free_agent_pool_from_data
        new_fas = build_free_agent_pool_from_data(players)
        d._fa_pool.extend(new_fas)
        for fa in new_fas:
            roster = d._team_rosters.get(d.owner.club_key, [])
            if len(roster) < 40:
                roster.append(fa.player_card)
                d._team_rosters[d.owner.club_key] = roster

        _set_dynasty(d)
        ui.notify(f"Imported {len(new_fas)} players!", type="positive")
        refresh = app.storage.user.get("_wvl_refresh")
        if refresh:
            refresh()

    ui.button("Import Players", icon="file_upload", on_click=_import_custom).props("no-caps").classes("mt-1")


def _offseason_step_free_agency(dynasty, data):
    ui.label("Free Agency Results").classes("text-lg font-semibold text-slate-700 mb-3")

    fa = data.get("free_agency") or {}
    if not fa:
        ui.label("No free agency activity.").classes("text-sm text-slate-400 italic")
        return

    ots = fa.get("owner_targeted_signing")
    if ots:
        with ui.card().classes("w-full p-3 mb-3").style("border-left: 4px solid #6366f1;"):
            ui.label("Your Targeted Signing").classes("text-xs text-indigo-500 uppercase font-semibold")
            ui.label(ots.get("player_name", "?")).classes("text-lg font-bold text-indigo-700")
            sal = ots.get("salary", "?")
            ui.label(f"Salary Tier: {sal}").classes("text-sm text-slate-500")

    signings = fa.get("signings", [])
    total = fa.get("total_signed", len(signings))
    unsigned = fa.get("unsigned", [])

    with ui.row().classes("gap-4 flex-wrap mb-3"):
        with ui.card().classes("p-3 text-center min-w-[120px]"):
            ui.label("Signed").classes("text-xs text-slate-400 uppercase")
            ui.label(str(total)).classes("text-2xl font-bold text-green-600")
        with ui.card().classes("p-3 text-center min-w-[120px]"):
            ui.label("Unsigned").classes("text-xs text-slate-400 uppercase")
            ui.label(str(len(unsigned))).classes("text-2xl font-bold text-slate-500")

    if signings:
        owner_signings = [s for s in signings if s.get("team_key") == dynasty.owner.club_key]
        if owner_signings:
            ui.label("Signed to Your Club").classes("text-sm font-semibold text-indigo-600 mb-1")
            for s in owner_signings:
                ui.label(f"  {s.get('player_name', '?')} (Salary: {s.get('salary', '?')})").classes("text-sm")

        with ui.expansion("All League Signings", icon="list").classes("w-full mt-2"):
            columns = [
                {"name": "player", "label": "Player", "field": "player", "align": "left"},
                {"name": "team", "label": "Team", "field": "team", "align": "left"},
                {"name": "salary", "label": "Salary", "field": "salary", "align": "center"},
            ]
            rows = [{"player": s.get("player_name", "?"), "team": s.get("team_key", "?"),
                      "salary": str(s.get("salary", "")), "_idx": i}
                     for i, s in enumerate(signings[:50])]
            ui.table(columns=columns, rows=rows, row_key="_idx").classes("w-full").props("dense flat bordered")


def _offseason_step_development(dynasty, data):
    ui.label("Player Development").classes("text-lg font-semibold text-slate-700 mb-3")

    dev = data.get("development", [])
    if not dev:
        ui.label("No development events.").classes("text-sm text-slate-400 italic")
        return

    owner_dev = [e for e in dev if e.get("team") == dynasty.owner.club_key]
    other_dev = [e for e in dev if e.get("team") != dynasty.owner.club_key]

    if owner_dev:
        ui.label("Your Team").classes("text-sm font-semibold text-indigo-700 mb-1")
        for e in owner_dev:
            ev_type = e.get("type", "")
            icon_name = "trending_up" if ev_type in ("improved", "breakout") else "trending_down" if ev_type == "declined" else "swap_horiz"
            color = "text-green-600" if ev_type in ("improved", "breakout") else "text-red-600" if ev_type == "declined" else "text-slate-500"
            with ui.row().classes("items-center gap-2 mb-1"):
                ui.icon(icon_name, size="xs").classes(color)
                ui.label(f"{e.get('player', '?')}: {e.get('description', '')}").classes("text-sm")

    if other_dev:
        ui.label(f"{len(other_dev)} development events across other teams.").classes("text-sm text-slate-500 mt-3")


def _offseason_step_investment(dynasty, data):
    ui.label("Investment Allocation").classes("text-lg font-semibold text-slate-700 mb-3")
    ui.label("Adjust how your budget is distributed for next season.").classes("text-xs text-slate-500 mb-3")

    inv = dynasty.investment
    sliders = {}

    for label_text, attr in [
        ("Training", "training"),
        ("Coaching", "coaching"),
        ("Stadium", "stadium"),
        ("Youth Academy", "youth"),
        ("Sports Science", "science"),
        ("Marketing", "marketing"),
    ]:
        current_val = getattr(inv, attr, 0.0)
        with ui.row().classes("items-center gap-3 w-full mb-2"):
            ui.label(label_text).classes("text-sm text-slate-600 w-32")
            slider = ui.slider(min=0, max=50, value=int(current_val * 100), step=5).classes("flex-1")
            pct_label = ui.label(f"{int(current_val * 100)}%").classes("text-sm text-slate-500 w-10 text-right")
            slider.on("update:model-value", lambda e, lbl=pct_label: lbl.set_text(f"{int(e.args)}%"))
            sliders[attr] = slider

    async def _save_investment():
        d = _get_dynasty()
        if not d:
            return
        total = sum(s.value for s in sliders.values())
        if total == 0:
            ui.notify("Allocate at least some budget.", type="warning")
            return
        for attr, slider in sliders.items():
            setattr(d.investment, attr, slider.value / total)
        _set_dynasty(d)
        ui.notify("Investment allocation saved!", type="positive")

    ui.button("Save Allocation", icon="save", on_click=_save_investment).props("no-caps").classes("mt-2")


def _offseason_step_financials(dynasty, data):
    ui.label("Financial Summary").classes("text-lg font-semibold text-slate-700 mb-3")

    fin = data.get("financials", {})
    if not fin:
        ui.label("No financial data available.").classes("text-sm text-slate-400 italic")
        return

    rev = fin.get("total_revenue", 0)
    exp = fin.get("total_expenses", 0)
    net = rev - exp

    with ui.row().classes("w-full gap-4 flex-wrap mb-4"):
        with ui.card().classes("flex-1 min-w-[140px] p-4 text-center"):
            ui.label("Revenue").classes("text-xs text-slate-400 uppercase")
            ui.label(f"${rev:.1f}M").classes("text-2xl font-bold text-green-600")
        with ui.card().classes("flex-1 min-w-[140px] p-4 text-center"):
            ui.label("Expenses").classes("text-xs text-slate-400 uppercase")
            ui.label(f"${exp:.1f}M").classes("text-2xl font-bold text-red-600")
        with ui.card().classes("flex-1 min-w-[140px] p-4 text-center"):
            ui.label("Net Income").classes("text-xs text-slate-400 uppercase")
            color = "text-green-600" if net >= 0 else "text-red-600"
            ui.label(f"{'+'if net>=0 else ''}{net:.1f}M").classes(f"text-2xl font-bold {color}")
        with ui.card().classes("flex-1 min-w-[140px] p-4 text-center"):
            ui.label("Bankroll").classes("text-xs text-slate-400 uppercase")
            bankroll = fin.get("bankroll_end", dynasty.owner.bankroll)
            bcolor = "text-green-600" if bankroll > 15 else "text-amber-600" if bankroll > 5 else "text-red-600"
            ui.label(f"${bankroll:.1f}M").classes(f"text-2xl font-bold {bcolor}")

    rev_breakdown = fin.get("revenue_breakdown", {})
    exp_breakdown = fin.get("expense_breakdown", {})

    if rev_breakdown or exp_breakdown:
        with ui.row().classes("w-full gap-4 flex-wrap"):
            if rev_breakdown:
                with ui.card().classes("flex-1 min-w-[250px] p-4"):
                    ui.label("Revenue Breakdown").classes("text-sm font-semibold text-slate-600 mb-2")
                    for key, val in rev_breakdown.items():
                        label_text = key.replace("_", " ").title()
                        with ui.row().classes("items-center justify-between"):
                            ui.label(label_text).classes("text-xs text-slate-500")
                            ui.label(f"${val:.1f}M" if isinstance(val, (int, float)) else str(val)).classes("text-xs font-semibold")
            if exp_breakdown:
                with ui.card().classes("flex-1 min-w-[250px] p-4"):
                    ui.label("Expense Breakdown").classes("text-sm font-semibold text-slate-600 mb-2")
                    for key, val in exp_breakdown.items():
                        label_text = key.replace("_", " ").title()
                        with ui.row().classes("items-center justify-between"):
                            ui.label(label_text).classes("text-xs text-slate-500")
                            ui.label(f"${val:.1f}M" if isinstance(val, (int, float)) else str(val)).classes("text-xs font-semibold")

    if data.get("forced_sale"):
        ui.separator().classes("mt-3")
        ui.label("FORCED SALE: Your club has been sold due to financial collapse!").classes(
            "text-lg font-bold text-red-600 mt-3"
        )
    elif data.get("pressure_mounting"):
        ui.separator().classes("mt-3")
        ui.label("Warning: Pressure mounting from poor results and low bankroll.").classes(
            "text-sm font-semibold text-amber-600 mt-2"
        )


# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

async def render_wvl_section(state, shared):
    container = ui.column().classes("w-full max-w-5xl mx-auto p-4")

    dynasty = _get_dynasty()
    if dynasty:
        _render_main(container)
    else:
        _render_setup(container)
