"""International Viperball (FIV) UI for the NiceGUI Viperball app.

Best-of-both-worlds design: NVL's polished maximized dialog with dark gradient
headers and tabbed interface, combined with the CVL's deep detail — quarter
scoring, drive summaries, play-by-play, individual player stat tables,
tournament stat leaders, and team roster views.
"""

from __future__ import annotations

import logging

_log = logging.getLogger("viperball.international")

from nicegui import ui, run, app

from ui import api_client
from nicegui_app.helpers import (
    fmt_vb_score,
    format_time,
    drive_result_label,
    drive_result_color,
    compute_quarter_scores,
)

# ═══════════════════════════════════════════════════════════════
# CONFEDERATION DISPLAY NAMES
# ═══════════════════════════════════════════════════════════════

CONF_LABELS = {
    "cav": "CAV — Confédération Américaine de Viperball",
    "ifav": "IFAV — Africa & Middle East",
    "evv": "EVV — Europäischer Viperball-Verband",
    "aav": "AAV — Asociación Asiática de Viperball",
    "cmv": "CMV — Confederación Marítima de Viperball",
}

CONF_SHORT = {
    "cav": "CAV (Americas)",
    "ifav": "IFAV (Africa/ME)",
    "evv": "EVV (Europe)",
    "aav": "AAV (Asia)",
    "cmv": "CMV (Oceania/Caribbean)",
}


# ═══════════════════════════════════════════════════════════════
# MAIN RENDER
# ═══════════════════════════════════════════════════════════════

async def render_international_section(state, shared):
    """Render the International (FIV) section."""

    active_tab = {"current": "dashboard"}

    cycle_data = {"data": None}
    try:
        data = await run.io_bound(api_client.fiv_active_cycle)
        cycle_data["data"] = data
    except Exception:
        cycle_data["data"] = None

    tab_container = ui.row().classes("w-full mb-4 gap-1 flex-wrap")
    content_area = ui.column().classes("w-full")

    tabs = [
        ("dashboard", "Dashboard", "dashboard"),
        ("rankings", "World Rankings", "leaderboard"),
        ("continental", "Continental", "emoji_events"),
        ("playoff", "Playoff", "sports_score"),
        ("worldcup", "World Cup", "emoji_events"),
        ("leaders", "Stat Leaders", "bar_chart"),
    ]

    tab_buttons: dict = {}

    async def _switch_tab(name: str):
        active_tab["current"] = name
        for btn_name, btn in tab_buttons.items():
            if btn_name == name:
                btn.classes(remove="bg-gray-100 text-gray-600", add="bg-indigo-600 text-white")
            else:
                btn.classes(remove="bg-indigo-600 text-white", add="bg-gray-100 text-gray-600")
        content_area.clear()
        with content_area:
            try:
                if name == "dashboard":
                    await _render_dashboard(cycle_data)
                elif name == "rankings":
                    await _render_rankings()
                elif name == "continental":
                    await _render_continental(cycle_data)
                elif name == "playoff":
                    await _render_playoff(cycle_data)
                elif name == "worldcup":
                    await _render_world_cup(cycle_data)
                elif name == "leaders":
                    await _render_stat_leaders()
            except Exception as exc:
                _log.error(f"Error rendering {name}: {exc}", exc_info=True)
                ui.label(f"Error: {exc}").classes("text-red-500")

    with tab_container:
        for tab_id, label, icon in tabs:
            btn = ui.button(label, icon=icon, on_click=lambda t=tab_id: _switch_tab(t))
            btn.props("flat dense no-caps size=sm")
            if tab_id == "dashboard":
                btn.classes("bg-indigo-600 text-white rounded-lg px-3")
            else:
                btn.classes("bg-gray-100 text-gray-600 rounded-lg px-3")
            tab_buttons[tab_id] = btn

    with content_area:
        await _render_dashboard(cycle_data)


# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════

async def _render_dashboard(cycle_data: dict):
    """FIV Dashboard: cycle status, quick actions, rankings summary."""

    ui.label("FIV — Fédération Internationale de Viperball").classes(
        "text-2xl font-bold text-slate-800 mb-2"
    )
    ui.label("Women's International Viperball").classes("text-sm text-slate-500 mb-4")

    data = cycle_data.get("data")

    if data is None:
        with ui.card().classes("w-full p-6"):
            ui.label("No Active Cycle").classes("text-lg font-semibold text-slate-700 mb-2")
            ui.label(
                "Start a new FIV cycle to generate national team rosters, "
                "run continental championships, and compete in the World Cup."
            ).classes("text-slate-500 mb-4")

            with ui.row().classes("gap-4"):
                host_input = ui.input("Host Nation (code)", placeholder="e.g. FRA").classes("w-32")

                async def _start_cycle():
                    ui.notify("Starting FIV cycle... This may take a moment.", type="info")
                    try:
                        result = await run.io_bound(
                            api_client.fiv_new_cycle,
                            host_input.value or None,
                        )
                        cycle_data["data"] = result
                        ui.notify(
                            f"Cycle {result.get('cycle_number', 1)} started! "
                            f"{result.get('team_count', 0)} teams generated.",
                            type="positive",
                        )
                        ui.navigate.to("/")
                    except Exception as exc:
                        ui.notify(f"Error: {exc}", type="negative")

                ui.button("Start New Cycle", icon="play_arrow", on_click=_start_cycle).props(
                    "color=indigo no-caps"
                )
        return

    phase = data.get("phase", "unknown")
    cycle_num = data.get("cycle_number", 1)
    host = data.get("host_nation", "?")

    with ui.row().classes("w-full gap-4 mb-4 flex-wrap"):
        with ui.card().classes("p-4 flex-1 min-w-48"):
            ui.label("Cycle").classes("text-xs text-slate-500 uppercase tracking-wide")
            ui.label(f"#{cycle_num}").classes("text-2xl font-bold text-indigo-600")
        with ui.card().classes("p-4 flex-1 min-w-48"):
            ui.label("Phase").classes("text-xs text-slate-500 uppercase tracking-wide")
            phase_labels = {
                "roster_generation": "Rosters Ready",
                "continental": "Continental Championships",
                "playoff": "Playoff",
                "wc_draw": "World Cup Draw",
                "wc_groups": "World Cup Groups",
                "wc_knockout": "World Cup Knockout",
                "completed": "Cycle Complete",
            }
            ui.label(phase_labels.get(phase, phase.title())).classes(
                "text-lg font-semibold text-slate-700"
            )
        with ui.card().classes("p-4 flex-1 min-w-48"):
            ui.label("Host Nation").classes("text-xs text-slate-500 uppercase tracking-wide")
            ui.label(host).classes("text-2xl font-bold text-amber-600")
        with ui.card().classes("p-4 flex-1 min-w-48"):
            ui.label("Teams").classes("text-xs text-slate-500 uppercase tracking-wide")
            team_count = len(data.get("national_teams", {}))
            ui.label(str(team_count)).classes("text-2xl font-bold text-slate-700")

    # Quick actions
    with ui.card().classes("w-full p-4 mb-4"):
        ui.label("Quick Actions").classes("text-sm font-semibold text-slate-600 mb-2")
        with ui.row().classes("gap-2 flex-wrap"):
            if phase == "roster_generation":
                async def _sim_all_continental():
                    ui.notify("Simulating all continental championships...", type="info")
                    try:
                        await run.io_bound(api_client.fiv_sim_all_continental)
                        ui.notify("Continental championships complete!", type="positive")
                        ui.navigate.to("/")
                    except Exception as exc:
                        ui.notify(f"Error: {exc}", type="negative")
                ui.button("Sim All Continental Championships", icon="fast_forward",
                          on_click=_sim_all_continental).props("color=indigo no-caps")

            elif phase == "continental":
                async def _sim_playoff():
                    ui.notify("Simulating playoff...", type="info")
                    try:
                        result = await run.io_bound(api_client.fiv_sim_playoff)
                        ui.notify(f"Playoff complete! Qualifiers: {result.get('qualifiers', [])}", type="positive")
                        ui.navigate.to("/")
                    except Exception as exc:
                        ui.notify(f"Error: {exc}", type="negative")
                ui.button("Sim Cross-Confederation Playoff", icon="fast_forward",
                          on_click=_sim_playoff).props("color=indigo no-caps")

            elif phase == "playoff":
                async def _wc_draw():
                    ui.notify("Drawing World Cup groups...", type="info")
                    try:
                        await run.io_bound(api_client.fiv_world_cup_draw)
                        ui.notify("World Cup draw complete!", type="positive")
                        ui.navigate.to("/")
                    except Exception as exc:
                        ui.notify(f"Error: {exc}", type="negative")
                ui.button("World Cup Draw", icon="casino",
                          on_click=_wc_draw).props("color=amber no-caps")

            elif phase in ("wc_draw", "wc_groups"):
                async def _sim_wc_stage():
                    ui.notify("Simulating World Cup stage...", type="info")
                    try:
                        result = await run.io_bound(api_client.fiv_sim_world_cup_stage)
                        champ = result.get("champion")
                        if champ:
                            ui.notify(f"World Cup complete! Champion: {champ}", type="positive")
                        else:
                            ui.notify("World Cup stage complete!", type="positive")
                        ui.navigate.to("/")
                    except Exception as exc:
                        ui.notify(f"Error: {exc}", type="negative")
                ui.button("Sim World Cup Stage", icon="fast_forward",
                          on_click=_sim_wc_stage).props("color=amber no-caps")

            elif phase == "completed":
                wc = data.get("world_cup", {})
                champion = wc.get("champion", "?")
                ui.label(f"World Cup Champion: {champion}").classes(
                    "text-xl font-bold text-amber-600"
                )

    # Continental results summary
    confs = data.get("confederations_data", {})
    if confs:
        with ui.card().classes("w-full p-4"):
            ui.label("Continental Championships").classes("text-sm font-semibold text-slate-600 mb-2")
            columns = [
                {"name": "conf", "label": "Confederation", "field": "conf", "align": "left"},
                {"name": "phase", "label": "Status", "field": "phase"},
                {"name": "champion", "label": "Champion", "field": "champion"},
                {"name": "qualifiers", "label": "WC Qualifiers", "field": "qualifiers"},
            ]
            rows = []
            for conf_id, cc in confs.items():
                rows.append({
                    "conf": CONF_SHORT.get(conf_id, conf_id.upper()),
                    "phase": cc.get("phase", "not_started").replace("_", " ").title(),
                    "champion": cc.get("champion", "—"),
                    "qualifiers": ", ".join(cc.get("qualifiers", [])) or "—",
                })
            ui.table(columns=columns, rows=rows, row_key="conf").props(
                "flat dense bordered"
            ).classes("w-full")


# ═══════════════════════════════════════════════════════════════
# WORLD RANKINGS
# ═══════════════════════════════════════════════════════════════

async def _render_rankings():
    """Display FIV World Rankings."""
    ui.label("FIV World Rankings").classes("text-xl font-bold text-slate-800 mb-4")

    try:
        data = await run.io_bound(api_client.fiv_rankings)
    except Exception:
        ui.label("No rankings available. Start a new FIV cycle first.").classes(
            "text-slate-500 italic"
        )
        return

    rankings = data.get("rankings", [])
    if not rankings:
        ui.label("No rankings data.").classes("text-slate-500 italic")
        return

    columns = [
        {"name": "rank", "label": "#", "field": "rank", "align": "center", "sortable": True},
        {"name": "code", "label": "Nation", "field": "code", "align": "left", "sortable": True},
        {"name": "rating", "label": "Rating", "field": "rating", "align": "center", "sortable": True},
    ]

    tbl = ui.table(columns=columns, rows=rankings, row_key="code").props(
        "flat dense bordered"
    ).classes("w-full max-w-lg")
    tbl.add_slot("body-cell-code", '''
        <q-td :props="props">
            <a class="text-indigo-600 font-semibold cursor-pointer hover:underline"
               @click="$parent.$emit('nation_click', props.row)">
                {{ props.row.code }}
            </a>
        </q-td>
    ''')
    tbl.on("nation_click", lambda e: _show_team_roster_dialog(e.args.get("code", "")))


# ═══════════════════════════════════════════════════════════════
# CONTINENTAL CHAMPIONSHIPS
# ═══════════════════════════════════════════════════════════════

async def _render_continental(cycle_data: dict):
    """Render continental championship results with clickable match scores."""
    ui.label("Continental Championships").classes("text-xl font-bold text-slate-800 mb-4")

    data = cycle_data.get("data")
    if data is None:
        ui.label("No active cycle.").classes("text-slate-500 italic")
        return

    confs = data.get("confederations_data", {})
    if not confs:
        ui.label("Continental championships not yet started.").classes("text-slate-500 italic")
        return

    for conf_id in ("cav", "ifav", "evv", "aav", "cmv"):
        cc = confs.get(conf_id, {})
        conf_label = CONF_LABELS.get(conf_id, conf_id.upper())

        with ui.expansion(conf_label, icon="emoji_events").classes("w-full mb-2"):
            phase = cc.get("phase", "not_started")
            champion = cc.get("champion")

            if phase == "completed" and champion:
                ui.label(f"Champion: {champion}").classes("text-lg font-bold text-amber-600 mb-2")
                ui.label(f"Qualifiers: {', '.join(cc.get('qualifiers', []))}").classes(
                    "text-sm text-slate-600 mb-2"
                )

            # Group tables with match results
            groups = cc.get("groups", [])
            if groups:
                ui.label("Group Stage").classes("text-sm font-semibold text-slate-600 mt-2 mb-1")
                for group in groups:
                    group_name = group.get("group_name", "?")
                    table = group.get("table", {})
                    ui.label(f"Group {group_name}").classes("text-xs font-semibold text-slate-500 mt-1")

                    columns = [
                        {"name": "team", "label": "Team", "field": "team", "align": "left"},
                        {"name": "p", "label": "P", "field": "p", "align": "center"},
                        {"name": "w", "label": "W", "field": "w", "align": "center"},
                        {"name": "d", "label": "D", "field": "d", "align": "center"},
                        {"name": "l", "label": "L", "field": "l", "align": "center"},
                        {"name": "pf", "label": "PF", "field": "pf", "align": "center"},
                        {"name": "pa", "label": "PA", "field": "pa", "align": "center"},
                        {"name": "pts", "label": "Pts", "field": "pts", "align": "center"},
                    ]

                    ranked = group.get("ranked", list(table.keys()))
                    rows = []
                    for code in ranked:
                        stats = table.get(code, {})
                        rows.append({
                            "team": code,
                            "p": stats.get("played", 0),
                            "w": stats.get("won", 0),
                            "d": stats.get("drawn", 0),
                            "l": stats.get("lost", 0),
                            "pf": fmt_vb_score(stats.get("points_for", 0)),
                            "pa": fmt_vb_score(stats.get("points_against", 0)),
                            "pts": stats.get("points", 0),
                        })

                    ui.table(columns=columns, rows=rows, row_key="team").props(
                        "flat dense bordered"
                    ).classes("w-full max-w-xl mb-1")

                    # Match results for this group
                    results = group.get("results", [])
                    if results:
                        with ui.row().classes("gap-2 flex-wrap mb-2"):
                            for r in results:
                                _render_match_chip(r)

            # Knockout bracket
            knockout = cc.get("knockout_rounds", [])
            if knockout:
                ui.label("Knockout Stage").classes("text-sm font-semibold text-slate-600 mt-2 mb-1")
                for kr in knockout:
                    ui.label(kr.get("round_name", "")).classes("text-xs font-semibold text-slate-500")
                    for m in kr.get("matchups", []):
                        _render_bracket_matchup(m)


# ═══════════════════════════════════════════════════════════════
# PLAYOFF
# ═══════════════════════════════════════════════════════════════

async def _render_playoff(cycle_data: dict):
    """Render cross-confederation playoff results."""
    ui.label("Cross-Confederation Playoff").classes("text-xl font-bold text-slate-800 mb-4")

    data = cycle_data.get("data")
    if data is None:
        ui.label("No active cycle.").classes("text-slate-500 italic")
        return

    playoff = data.get("playoff")
    if not playoff:
        ui.label("Playoff not yet started.").classes("text-slate-500 italic")
        return

    qualifiers = playoff.get("qualifiers", [])
    if qualifiers:
        ui.label(f"World Cup Qualifiers: {', '.join(qualifiers)}").classes(
            "text-lg font-bold text-amber-600 mb-4"
        )

    bracket = playoff.get("bracket", [])
    for kr in bracket:
        ui.label(kr.get("round_name", "")).classes("text-sm font-semibold text-slate-600 mt-2")
        for m in kr.get("matchups", []):
            _render_bracket_matchup(m)


# ═══════════════════════════════════════════════════════════════
# WORLD CUP
# ═══════════════════════════════════════════════════════════════

async def _render_world_cup(cycle_data: dict):
    """Render World Cup groups, bracket, and stats."""
    ui.label("FIV World Cup").classes("text-xl font-bold text-slate-800 mb-4")

    data = cycle_data.get("data")
    if data is None:
        ui.label("No active cycle.").classes("text-slate-500 italic")
        return

    wc = data.get("world_cup")
    if not wc:
        ui.label("World Cup not yet started.").classes("text-slate-500 italic")
        return

    phase = wc.get("phase", "not_started")
    champion = wc.get("champion")

    if champion:
        with ui.card().classes("w-full p-6 bg-amber-50 mb-4"):
            ui.label("World Cup Champion").classes("text-sm text-amber-700 uppercase tracking-wide")
            ui.label(champion).classes("text-3xl font-extrabold text-amber-600")

            golden_boot = wc.get("golden_boot")
            mvp = wc.get("mvp")
            with ui.row().classes("gap-8 mt-2"):
                if golden_boot:
                    with ui.column():
                        ui.label("Golden Boot").classes("text-xs text-amber-600 uppercase")
                        ui.label(f"{golden_boot.get('name', '?')} ({golden_boot.get('nation', '?')})").classes(
                            "text-sm font-semibold text-slate-700"
                        )
                        ui.label(f"{golden_boot.get('tds', 0)} TDs").classes("text-xs text-slate-500")
                if mvp:
                    with ui.column():
                        ui.label("MVP").classes("text-xs text-amber-600 uppercase")
                        ui.label(f"{mvp.get('name', '?')} ({mvp.get('nation', '?')})").classes(
                            "text-sm font-semibold text-slate-700"
                        )
                        ui.label(f"VPA: {mvp.get('vpa', 0)}").classes("text-xs text-slate-500")

    # Seed pots
    pots = wc.get("seed_pots", {})
    if pots and phase != "not_started":
        with ui.expansion("Seed Pots", icon="casino").classes("w-full mb-2"):
            for pot_name, teams in pots.items():
                ui.label(f"{pot_name}: {', '.join(teams)}").classes("text-sm text-slate-600")

    # Group stage
    groups = wc.get("groups", [])
    if groups:
        with ui.expansion("Group Stage", icon="grid_view", value=True).classes("w-full mb-2"):
            for group in groups:
                group_name = group.get("group_name", "?")
                table = group.get("table", {})
                ui.label(f"Group {group_name}").classes("text-sm font-semibold text-slate-600 mt-2")

                columns = [
                    {"name": "team", "label": "Team", "field": "team", "align": "left"},
                    {"name": "p", "label": "P", "field": "p", "align": "center"},
                    {"name": "w", "label": "W", "field": "w", "align": "center"},
                    {"name": "d", "label": "D", "field": "d", "align": "center"},
                    {"name": "l", "label": "L", "field": "l", "align": "center"},
                    {"name": "pf", "label": "PF", "field": "pf", "align": "center"},
                    {"name": "pa", "label": "PA", "field": "pa", "align": "center"},
                    {"name": "pts", "label": "Pts", "field": "pts", "align": "center"},
                ]

                ranked = group.get("ranked", list(table.keys()))
                rows = []
                for code in ranked:
                    stats = table.get(code, {})
                    rows.append({
                        "team": code,
                        "p": stats.get("played", 0),
                        "w": stats.get("won", 0),
                        "d": stats.get("drawn", 0),
                        "l": stats.get("lost", 0),
                        "pf": fmt_vb_score(stats.get("points_for", 0)),
                        "pa": fmt_vb_score(stats.get("points_against", 0)),
                        "pts": stats.get("points", 0),
                    })

                ui.table(columns=columns, rows=rows, row_key="team").props(
                    "flat dense bordered"
                ).classes("w-full max-w-xl mb-1")

                # Match results for this group
                results = group.get("results", [])
                if results:
                    with ui.row().classes("gap-2 flex-wrap mb-2"):
                        for r in results:
                            _render_match_chip(r)

    # Knockout bracket
    knockout = wc.get("knockout_rounds", [])
    if knockout:
        with ui.expansion("Knockout Stage", icon="account_tree", value=True).classes("w-full mb-2"):
            for kr in knockout:
                round_name = kr.get("round_name", "")
                ui.label(round_name).classes("text-sm font-bold text-slate-700 mt-2")
                for m in kr.get("matchups", []):
                    _render_bracket_matchup(m)


# ═══════════════════════════════════════════════════════════════
# STAT LEADERS
# ═══════════════════════════════════════════════════════════════

async def _render_stat_leaders():
    """Display tournament stat leaders for World Cup and continental championships."""
    ui.label("Tournament Stat Leaders").classes("text-xl font-bold text-slate-800 mb-4")

    # World Cup stats first
    try:
        wc_stats = await run.io_bound(api_client.fiv_world_cup_stats)
        leaders = wc_stats.get("leaders")
        if leaders:
            ui.label("World Cup Leaders").classes("text-lg font-semibold text-amber-700 mb-2")
            _render_leaders_tables(leaders)
            return
    except Exception:
        pass

    # Fall back to continental stats
    for conf_id in ("cav", "ifav", "evv", "aav", "cmv"):
        try:
            data = await run.io_bound(api_client.fiv_continental_stats, conf_id)
            leaders = data.get("leaders")
            if leaders and any(leaders.get(k) for k in leaders):
                conf_label = CONF_SHORT.get(conf_id, conf_id.upper())
                ui.label(f"{conf_label} Leaders").classes("text-md font-semibold text-indigo-700 mt-4 mb-2")
                _render_leaders_tables(leaders)
        except Exception:
            continue

    ui.label("No stat data available yet. Run some matches first.").classes(
        "text-slate-500 italic"
    )


def _render_leaders_tables(leaders: dict):
    """Render stat leader tables from the computed leaders dict."""

    # Scoring leaders
    scoring = leaders.get("scoring", [])
    if scoring:
        ui.label("Scoring Leaders").classes("text-sm font-semibold text-slate-600 mb-1")
        cols = [
            {"name": "rank", "label": "#", "field": "rank", "align": "center"},
            {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
            {"name": "nation", "label": "Nation", "field": "nation", "align": "center"},
            {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
            {"name": "gp", "label": "GP", "field": "gp", "align": "center"},
            {"name": "tds", "label": "TDs", "field": "tds", "align": "center", "sortable": True},
            {"name": "rush_td", "label": "Rush TD", "field": "rush_td", "align": "center"},
            {"name": "kp_td", "label": "KP TD", "field": "kp_td", "align": "center"},
            {"name": "lat_td", "label": "Lat TD", "field": "lat_td", "align": "center"},
        ]
        rows = []
        for i, p in enumerate(scoring[:15]):
            rows.append({
                "rank": i + 1, "name": p["name"], "nation": p["nation"],
                "pos": p.get("position", ""), "gp": p.get("games", 0),
                "tds": p.get("total_tds", 0),
                "rush_td": p.get("rushing_tds", 0),
                "kp_td": p.get("kick_pass_tds", 0),
                "lat_td": p.get("lateral_tds", 0),
            })
        ui.table(columns=cols, rows=rows, row_key="name").props("flat dense bordered").classes("w-full max-w-3xl mb-4")

    # Rushing leaders
    rushing = leaders.get("rushing", [])
    if rushing:
        ui.label("Rushing Leaders").classes("text-sm font-semibold text-slate-600 mb-1")
        cols = [
            {"name": "rank", "label": "#", "field": "rank", "align": "center"},
            {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
            {"name": "nation", "label": "Nation", "field": "nation", "align": "center"},
            {"name": "gp", "label": "GP", "field": "gp", "align": "center"},
            {"name": "car", "label": "Car", "field": "car", "align": "center", "sortable": True},
            {"name": "yds", "label": "Yds", "field": "yds", "align": "center", "sortable": True},
            {"name": "avg", "label": "Avg", "field": "avg", "align": "center"},
            {"name": "td", "label": "TD", "field": "td", "align": "center"},
            {"name": "lng", "label": "Lng", "field": "lng", "align": "center"},
        ]
        rows = []
        for i, p in enumerate(rushing[:15]):
            car = p.get("rush_carries", 0)
            yds = p.get("rushing_yards", 0)
            rows.append({
                "rank": i + 1, "name": p["name"], "nation": p["nation"],
                "gp": p.get("games", 0),
                "car": car, "yds": yds,
                "avg": round(yds / max(1, car), 1),
                "td": p.get("rushing_tds", 0),
                "lng": p.get("long_rush", 0),
            })
        ui.table(columns=cols, rows=rows, row_key="name").props("flat dense bordered").classes("w-full max-w-3xl mb-4")

    # Kick passing leaders
    kp = leaders.get("kick_passing", [])
    if kp:
        ui.label("Kick Passing Leaders").classes("text-sm font-semibold text-slate-600 mb-1")
        cols = [
            {"name": "rank", "label": "#", "field": "rank", "align": "center"},
            {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
            {"name": "nation", "label": "Nation", "field": "nation", "align": "center"},
            {"name": "gp", "label": "GP", "field": "gp", "align": "center"},
            {"name": "comp", "label": "Cmp", "field": "comp", "align": "center"},
            {"name": "att", "label": "Att", "field": "att", "align": "center"},
            {"name": "yds", "label": "Yds", "field": "yds", "align": "center", "sortable": True},
            {"name": "td", "label": "TD", "field": "td", "align": "center"},
            {"name": "int", "label": "INT", "field": "int_thrown", "align": "center"},
            {"name": "pct", "label": "Pct", "field": "pct", "align": "center"},
        ]
        rows = []
        for i, p in enumerate(kp[:15]):
            comp = p.get("kick_passes_completed", 0)
            att = p.get("kick_passes_thrown", 0)
            rows.append({
                "rank": i + 1, "name": p["name"], "nation": p["nation"],
                "gp": p.get("games", 0),
                "comp": comp, "att": att,
                "yds": p.get("kick_pass_yards", 0),
                "td": p.get("kick_pass_tds", 0),
                "int_thrown": p.get("kick_pass_interceptions_thrown", 0),
                "pct": f"{round(100 * comp / max(1, att), 1)}%",
            })
        ui.table(columns=cols, rows=rows, row_key="name").props("flat dense bordered").classes("w-full max-w-3xl mb-4")

    # Defensive leaders
    defense = leaders.get("defensive", [])
    if defense:
        ui.label("Defensive Leaders").classes("text-sm font-semibold text-slate-600 mb-1")
        cols = [
            {"name": "rank", "label": "#", "field": "rank", "align": "center"},
            {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
            {"name": "nation", "label": "Nation", "field": "nation", "align": "center"},
            {"name": "gp", "label": "GP", "field": "gp", "align": "center"},
            {"name": "tkl", "label": "Tkl", "field": "tkl", "align": "center", "sortable": True},
            {"name": "tfl", "label": "TFL", "field": "tfl", "align": "center"},
            {"name": "sck", "label": "Sck", "field": "sck", "align": "center"},
            {"name": "hur", "label": "Hur", "field": "hur", "align": "center"},
            {"name": "ints", "label": "INT", "field": "ints", "align": "center"},
        ]
        rows = []
        for i, p in enumerate(defense[:15]):
            rows.append({
                "rank": i + 1, "name": p["name"], "nation": p["nation"],
                "gp": p.get("games", 0),
                "tkl": p.get("tackles", 0), "tfl": p.get("tfl", 0),
                "sck": p.get("sacks", 0), "hur": p.get("hurries", 0),
                "ints": p.get("kick_pass_ints", 0),
            })
        ui.table(columns=cols, rows=rows, row_key="name").props("flat dense bordered").classes("w-full max-w-3xl mb-4")

    # Kicking leaders
    kicking = leaders.get("kicking", [])
    if kicking:
        ui.label("Kicking Leaders").classes("text-sm font-semibold text-slate-600 mb-1")
        cols = [
            {"name": "rank", "label": "#", "field": "rank", "align": "center"},
            {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
            {"name": "nation", "label": "Nation", "field": "nation", "align": "center"},
            {"name": "gp", "label": "GP", "field": "gp", "align": "center"},
            {"name": "dk", "label": "DK M/A", "field": "dk", "align": "center"},
            {"name": "pk", "label": "PK M/A", "field": "pk", "align": "center"},
            {"name": "pts", "label": "Pts", "field": "pts", "align": "center", "sortable": True},
        ]
        rows = []
        for i, p in enumerate(kicking[:15]):
            dk_m = p.get("drop_kicks_made", 0)
            dk_a = p.get("drop_kicks_attempted", 0)
            pk_m = p.get("place_kicks_made", 0)
            pk_a = p.get("place_kicks_attempted", 0)
            rows.append({
                "rank": i + 1, "name": p["name"], "nation": p["nation"],
                "gp": p.get("games", 0),
                "dk": f"{dk_m}/{dk_a}", "pk": f"{pk_m}/{pk_a}",
                "pts": dk_m * 5 + pk_m * 3,
            })
        ui.table(columns=cols, rows=rows, row_key="name").props("flat dense bordered").classes("w-full max-w-3xl mb-4")


# ═══════════════════════════════════════════════════════════════
# SHARED: MATCH CHIP & BRACKET MATCHUP RENDERERS
# ═══════════════════════════════════════════════════════════════

def _render_match_chip(result: dict):
    """Render a compact clickable match result chip."""
    home = result.get("home_code", "?")
    away = result.get("away_code", "?")
    hs = result.get("home_score", "")
    as_ = result.get("away_score", "")
    match_id = result.get("match_id", "")

    label = f"{away} {fmt_vb_score(as_)} - {fmt_vb_score(hs)} {home}"
    winner = result.get("winner", "")

    async def _open_box(mid=match_id):
        if not mid:
            return
        try:
            data = await run.io_bound(api_client.fiv_match_detail, mid)
            if data:
                _show_fiv_box_score_dialog(data)
        except Exception as exc:
            ui.notify(f"Could not load match: {exc}", type="negative")

    btn = ui.button(label, on_click=_open_box).props("flat dense no-caps size=sm")
    btn.classes("text-xs rounded bg-slate-100 hover:bg-slate-200 px-2 py-1")


def _render_bracket_matchup(m: dict):
    """Render a single knockout bracket matchup with clickable score."""
    home = m.get("home", "?")
    away = m.get("away", "?")
    winner = m.get("winner", "")
    hs = m.get("home_score", "")
    as_ = m.get("away_score", "")
    match_id = m.get("match_id", "")
    is_winner_home = winner == home

    async def _open_box(mid=match_id):
        if not mid:
            return
        try:
            data = await run.io_bound(api_client.fiv_match_detail, mid)
            if data:
                _show_fiv_box_score_dialog(data)
        except Exception as exc:
            ui.notify(f"Could not load match: {exc}", type="negative")

    with ui.row().classes("gap-2 items-center ml-4 mb-1"):
        home_cls = "font-bold text-indigo-600" if is_winner_home else "text-slate-600"
        away_cls = "font-bold text-indigo-600" if not is_winner_home and winner else "text-slate-600"
        ui.label(home).classes(f"text-sm {home_cls} w-12")
        if hs != "":
            btn_label = f"{fmt_vb_score(hs)} — {fmt_vb_score(as_)}"
            ui.button(btn_label, on_click=_open_box).props(
                "flat dense no-caps size=sm"
            ).classes("text-xs font-mono bg-slate-100 hover:bg-slate-200 rounded px-2")
        ui.label(away).classes(f"text-sm {away_cls} w-12")


# ═══════════════════════════════════════════════════════════════
# TEAM ROSTER DIALOG
# ═══════════════════════════════════════════════════════════════

def _show_team_roster_dialog(nation_code: str):
    """Show a dialog with the national team roster."""
    async def _load_and_show():
        try:
            data = await run.io_bound(api_client.fiv_team_detail, nation_code)
        except Exception as exc:
            ui.notify(f"Could not load team: {exc}", type="negative")
            return

        nation_info = data.get("nation", {})
        roster = data.get("roster", [])
        rating = data.get("rating", 0)

        with ui.dialog().props("maximized") as dlg:
            with ui.card().classes("w-full h-full overflow-auto p-0"):
                # Header
                with ui.element("div").classes("w-full").style(
                    "background: linear-gradient(135deg, #1e293b 0%, #334155 100%); padding: 24px 32px;"
                ):
                    with ui.row().classes("w-full items-center justify-between"):
                        with ui.column().classes("gap-0"):
                            ui.label(f"{nation_info.get('name', nation_code)} ({nation_code})").classes(
                                "text-2xl font-bold text-white"
                            )
                            ui.label(
                                f"Tier: {nation_info.get('tier', '?').title()} | "
                                f"Confederation: {nation_info.get('confederation', '?').upper()} | "
                                f"Rating: {rating}"
                            ).classes("text-sm text-slate-300")
                        ui.button("Close", icon="close", on_click=dlg.close).props(
                            "flat no-caps size=sm text-color=white"
                        ).classes("bg-slate-600 hover:bg-slate-500")

                # Roster table
                with ui.element("div").classes("w-full px-4 md:px-8 py-6").style("max-width: 1200px; margin: 0 auto;"):
                    ui.label(f"{len(roster)} Players").classes("text-lg font-semibold text-slate-700 mb-2")

                    columns = [
                        {"name": "num", "label": "#", "field": "num", "align": "center"},
                        {"name": "name", "label": "Name", "field": "name", "align": "left", "sortable": True},
                        {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
                        {"name": "ovr", "label": "OVR", "field": "ovr", "align": "center", "sortable": True},
                        {"name": "arch", "label": "Archetype", "field": "arch", "align": "left"},
                        {"name": "spd", "label": "SPD", "field": "spd", "align": "center"},
                        {"name": "sta", "label": "STA", "field": "sta", "align": "center"},
                        {"name": "kck", "label": "KCK", "field": "kck", "align": "center"},
                        {"name": "tkl", "label": "TKL", "field": "tkl", "align": "center"},
                        {"name": "age", "label": "Age", "field": "age", "align": "center"},
                        {"name": "caps", "label": "Caps", "field": "caps", "align": "center"},
                        {"name": "src", "label": "Source", "field": "src", "align": "left"},
                    ]
                    rows = []
                    for p in roster:
                        rows.append({
                            "num": p.get("player_id", "")[:4] if not isinstance(p.get("number"), int) else p.get("number", ""),
                            "name": p.get("name", "?"),
                            "pos": p.get("position", ""),
                            "ovr": p.get("overall", 0),
                            "arch": p.get("archetype", ""),
                            "spd": p.get("speed", 0),
                            "sta": p.get("stamina", 0),
                            "kck": p.get("kicking", 0),
                            "tkl": p.get("tackling", 0),
                            "age": p.get("age", "?"),
                            "caps": p.get("caps", 0),
                            "src": p.get("cvl_source") or ("Naturalized" if p.get("naturalized") else "Homegrown"),
                        })
                    rows.sort(key=lambda r: -r["ovr"])
                    ui.table(columns=columns, rows=rows, row_key="name").props(
                        "flat dense bordered"
                    ).classes("w-full")

        dlg.open()

    import asyncio
    asyncio.ensure_future(_load_and_show())


# ═══════════════════════════════════════════════════════════════
# FIV BOX SCORE DIALOG — NVL design + CVL detail
# ═══════════════════════════════════════════════════════════════

def _show_fiv_box_score_dialog(match_data: dict):
    """Show a maximized box score dialog for an FIV match.

    Merges the NVL's polished tabbed dialog design with the CVL's deep
    game detail: quarter scoring, drive summaries, play-by-play, and
    full individual player stat tables.
    """
    # Extract the game_result (engine output) from the match data
    gr = match_data.get("game_result") or match_data.get("result", {})
    if isinstance(gr, dict) and "game_result" in gr:
        gr = gr["game_result"]

    if not gr:
        ui.notify("No game result data for this match.", type="warning")
        return

    final = gr.get("final_score", {})
    home_info = final.get("home", {})
    away_info = final.get("away", {})
    home_name = match_data.get("home_code") or home_info.get("team", "Home")
    away_name = match_data.get("away_code") or away_info.get("team", "Away")
    home_score = home_info.get("score", match_data.get("home_score", 0))
    away_score = away_info.get("score", match_data.get("away_score", 0))
    weather = gr.get("weather", "Clear")
    stats = gr.get("stats", {})
    hs = stats.get("home", {})
    as_ = stats.get("away", {})
    ps = gr.get("player_stats", {})
    home_ps = ps.get("home", [])
    away_ps = ps.get("away", [])
    plays = gr.get("play_by_play", [])
    drives = gr.get("drive_summary", [])

    with ui.dialog().props("maximized") as dlg:
        with ui.card().classes("w-full h-full overflow-auto p-0"):
            # ── Dark gradient header (NVL style) ──
            with ui.element("div").classes("w-full").style(
                "background: linear-gradient(135deg, #1e293b 0%, #334155 100%); padding: 24px 32px;"
            ):
                with ui.row().classes("w-full items-center justify-between"):
                    with ui.column().classes("gap-0"):
                        ui.label(f"{away_name} @ {home_name}").classes(
                            "text-2xl font-bold text-white"
                        )
                        comp = match_data.get("competition", "").replace("_", " ").title()
                        stage = match_data.get("stage", "").replace("_", " ").title()
                        ui.label(f"{comp} — {stage} | Weather: {weather}").classes(
                            "text-sm text-slate-300"
                        )
                    with ui.row().classes("items-center gap-6"):
                        with ui.column().classes("items-center gap-0"):
                            ui.label(away_name).classes("text-xs text-slate-400 uppercase tracking-wider")
                            a_s = int(float(away_score))
                            a_won = a_s > int(float(home_score))
                            ui.label(fmt_vb_score(away_score)).classes(
                                f"text-4xl font-black {'text-white' if a_won else 'text-slate-400'}"
                            )
                        ui.label("—").classes("text-2xl text-slate-500 font-light")
                        with ui.column().classes("items-center gap-0"):
                            ui.label(home_name).classes("text-xs text-slate-400 uppercase tracking-wider")
                            h_s = int(float(home_score))
                            h_won = h_s > a_s
                            ui.label(fmt_vb_score(home_score)).classes(
                                f"text-4xl font-black {'text-white' if h_won else 'text-slate-400'}"
                            )
                        ui.label("FINAL").classes("text-xs font-bold text-amber-400 tracking-widest ml-4")

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Close", icon="close", on_click=dlg.close).props(
                        "flat no-caps size=sm text-color=white"
                    ).classes("bg-slate-600 hover:bg-slate-500")

            # ── Tabbed content ──
            with ui.element("div").classes("w-full px-4 md:px-8 py-6").style("max-width: 1200px; margin: 0 auto;"):

                # Quarter scoring (CVL feature)
                if plays:
                    home_q, away_q = compute_quarter_scores(plays)
                    with ui.element("div").classes("w-full overflow-x-auto mb-4"):
                        with ui.element("table").classes("w-full").style(
                            "border-collapse: collapse; font-size: 14px;"
                        ):
                            with ui.element("thead"):
                                with ui.element("tr").style("background: #f1f5f9; border-bottom: 2px solid #cbd5e1;"):
                                    ui.element("th").classes("text-left py-2 px-3 font-semibold text-slate-600").style("width:30%")
                                    for q in ("Q1", "Q2", "Q3", "Q4", "Final"):
                                        with ui.element("th").classes("text-center py-2 px-3 font-semibold text-slate-800"):
                                            ui.label(q)
                            with ui.element("tbody"):
                                for team_label, q_scores, total in [
                                    (away_name, away_q, away_score),
                                    (home_name, home_q, home_score),
                                ]:
                                    with ui.element("tr").style("border-bottom: 1px solid #e2e8f0;"):
                                        with ui.element("td").classes("py-2 px-3 font-semibold text-slate-700"):
                                            ui.label(team_label)
                                        for q in (1, 2, 3, 4):
                                            with ui.element("td").classes("text-center py-2 px-3 text-slate-800"):
                                                ui.label(fmt_vb_score(q_scores.get(q, 0)))
                                        with ui.element("td").classes("text-center py-2 px-3 font-bold text-slate-900"):
                                            ui.label(fmt_vb_score(total))

                with ui.tabs().classes("w-full") as bs_tabs:
                    tab_team = ui.tab("Team Stats")
                    tab_offense = ui.tab("Offense")
                    tab_defense = ui.tab("Defense")
                    tab_kicking = ui.tab("Kicking")
                    tab_drives = ui.tab("Drives")
                    if plays:
                        tab_pbp = ui.tab("Play-by-Play")

                with ui.tab_panels(bs_tabs, value=tab_team).classes("w-full"):
                    with ui.tab_panel(tab_team):
                        _fiv_render_team_stats(home_name, away_name, hs, as_)
                    with ui.tab_panel(tab_offense):
                        _fiv_render_offense_stats(home_name, away_name, home_ps, away_ps)
                    with ui.tab_panel(tab_defense):
                        _fiv_render_defense_stats(home_name, away_name, home_ps, away_ps)
                    with ui.tab_panel(tab_kicking):
                        _fiv_render_kicking_stats(home_name, away_name, home_ps, away_ps)
                    with ui.tab_panel(tab_drives):
                        _fiv_render_drive_summary(home_name, away_name, drives)
                    if plays:
                        with ui.tab_panel(tab_pbp):
                            _fiv_render_play_by_play(home_name, away_name, plays)

    dlg.open()


# ── Team Stats Comparison (NVL style HTML table) ──

def _fiv_render_team_stats(home_name: str, away_name: str, hs: dict, as_: dict):
    stat_rows = [
        ("Total Yards", as_.get("total_yards", 0), hs.get("total_yards", 0)),
        ("Touchdowns (9pts)",
         f"{as_.get('touchdowns', 0)} ({as_.get('touchdowns', 0) * 9}pts)",
         f"{hs.get('touchdowns', 0)} ({hs.get('touchdowns', 0) * 9}pts)"),
        ("Rushing",
         f"{as_.get('rushing_carries', 0)} car, {as_.get('rushing_yards', 0)} yds",
         f"{hs.get('rushing_carries', 0)} car, {hs.get('rushing_yards', 0)} yds"),
        ("KP Comp/Att",
         f"{as_.get('kick_passes_completed', 0)}/{as_.get('kick_passes_attempted', 0)}",
         f"{hs.get('kick_passes_completed', 0)}/{hs.get('kick_passes_attempted', 0)}"),
        ("KP Yards", as_.get("kick_pass_yards", 0), hs.get("kick_pass_yards", 0)),
        ("Lateral Yards", as_.get("lateral_yards", 0), hs.get("lateral_yards", 0)),
        ("Snap Kicks (DK)",
         f"{as_.get('drop_kicks_made', 0)}/{as_.get('drop_kicks_attempted', 0)}",
         f"{hs.get('drop_kicks_made', 0)}/{hs.get('drop_kicks_attempted', 0)}"),
        ("Field Goals (PK)",
         f"{as_.get('place_kicks_made', 0)}/{as_.get('place_kicks_attempted', 0)}",
         f"{hs.get('place_kicks_made', 0)}/{hs.get('place_kicks_attempted', 0)}"),
        ("Pindowns", as_.get("pindowns", 0), hs.get("pindowns", 0)),
        ("Yards/Play", as_.get("yards_per_play", 0), hs.get("yards_per_play", 0)),
        ("Total Plays", as_.get("total_plays", 0), hs.get("total_plays", 0)),
        ("Fumbles Lost", as_.get("fumbles_lost", 0), hs.get("fumbles_lost", 0)),
        ("KP Interceptions", as_.get("kick_pass_interceptions", 0), hs.get("kick_pass_interceptions", 0)),
        ("Penalties",
         f"{as_.get('penalties', 0)} / {as_.get('penalty_yards', 0)} yds",
         f"{hs.get('penalties', 0)} / {hs.get('penalty_yards', 0)} yds"),
        ("Punts", as_.get("punts", 0), hs.get("punts", 0)),
    ]

    with ui.element("div").classes("w-full overflow-x-auto"):
        with ui.element("table").classes("w-full").style(
            "border-collapse: collapse; font-size: 14px;"
        ):
            with ui.element("thead"):
                with ui.element("tr").style("background: #f1f5f9; border-bottom: 2px solid #cbd5e1;"):
                    ui.element("th").classes("text-left py-2 px-3 font-semibold text-slate-600").style("width:40%")
                    with ui.element("th").classes("text-center py-2 px-3 font-semibold text-slate-800").style("width:30%"):
                        ui.label(away_name)
                    with ui.element("th").classes("text-center py-2 px-3 font-semibold text-slate-800").style("width:30%"):
                        ui.label(home_name)
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


# ── Offense Stats (NVL tabular design) ──

def _fiv_render_offense_stats(home_name: str, away_name: str, home_ps: list, away_ps: list):
    for side_name, players in [(away_name, away_ps), (home_name, home_ps)]:
        if not isinstance(players, list) or not players:
            continue

        ui.label(side_name).classes("text-lg font-bold text-indigo-700 mt-4 mb-1")
        ui.separator().classes("mb-2")

        # Rushing
        rushers = sorted(
            [p for p in players if p.get("rush_carries", 0) > 0],
            key=lambda x: x.get("rushing_yards", 0), reverse=True,
        )
        if rushers:
            ui.label("Rushing").classes("text-sm font-semibold text-slate-600 mb-1")
            cols = [
                {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
                {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
                {"name": "car", "label": "Car", "field": "car", "align": "center", "sortable": True},
                {"name": "yds", "label": "Yds", "field": "yds", "align": "center", "sortable": True},
                {"name": "avg", "label": "Avg", "field": "avg", "align": "center"},
                {"name": "td", "label": "TD", "field": "td", "align": "center", "sortable": True},
                {"name": "fum", "label": "Fum", "field": "fum", "align": "center"},
                {"name": "long", "label": "Lng", "field": "long", "align": "center"},
            ]
            rows = []
            for p in rushers:
                car = p.get("rush_carries", 0)
                yds = p.get("rushing_yards", 0)
                rows.append({
                    "name": p.get("name", "?"), "pos": p.get("position", ""),
                    "car": str(car), "yds": str(yds),
                    "avg": str(round(yds / max(1, car), 1)),
                    "td": str(p.get("rushing_tds", 0)),
                    "fum": str(p.get("fumbles", 0)),
                    "long": str(p.get("long_rush", "-")),
                })
            ui.table(columns=cols, rows=rows, row_key="name").props("dense flat bordered").classes("w-full")

        # Kick Passing
        passers = [p for p in players if p.get("kick_passes_thrown", 0) > 0]
        if passers:
            ui.label("Kick Passing").classes("text-sm font-semibold text-slate-600 mt-3 mb-1")
            cols = [
                {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
                {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
                {"name": "comp", "label": "Cmp", "field": "comp", "align": "center"},
                {"name": "att", "label": "Att", "field": "att", "align": "center"},
                {"name": "yds", "label": "Yds", "field": "yds", "align": "center", "sortable": True},
                {"name": "td", "label": "TD", "field": "td", "align": "center"},
                {"name": "int", "label": "INT", "field": "int_thrown", "align": "center"},
                {"name": "pct", "label": "Pct", "field": "pct", "align": "center"},
            ]
            rows = []
            for p in passers:
                comp = p.get("kick_passes_completed", 0)
                att = p.get("kick_passes_thrown", 0)
                rows.append({
                    "name": p.get("name", "?"), "pos": p.get("position", ""),
                    "comp": str(comp), "att": str(att),
                    "yds": str(p.get("kick_pass_yards", 0)),
                    "td": str(p.get("kick_pass_tds", 0)),
                    "int_thrown": str(p.get("kick_pass_interceptions_thrown", 0)),
                    "pct": f"{round(100 * comp / max(1, att), 1)}%",
                })
            ui.table(columns=cols, rows=rows, row_key="name").props("dense flat bordered").classes("w-full")

        # Receiving
        receivers = sorted(
            [p for p in players if p.get("kick_pass_receptions", 0) > 0],
            key=lambda x: x.get("kick_pass_receptions", 0), reverse=True,
        )
        if receivers:
            ui.label("Receiving").classes("text-sm font-semibold text-slate-600 mt-3 mb-1")
            cols = [
                {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
                {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
                {"name": "rec", "label": "Rec", "field": "rec", "align": "center", "sortable": True},
                {"name": "yds", "label": "Yds", "field": "yds", "align": "center"},
                {"name": "td", "label": "TD", "field": "td", "align": "center"},
            ]
            rows = [{
                "name": p.get("name", "?"), "pos": p.get("position", ""),
                "rec": str(p.get("kick_pass_receptions", 0)),
                "yds": str(p.get("kick_pass_yards", 0)),
                "td": str(p.get("kick_pass_tds", 0)),
            } for p in receivers]
            ui.table(columns=cols, rows=rows, row_key="name").props("dense flat bordered").classes("w-full")

        # Laterals
        lateralists = sorted(
            [p for p in players if p.get("laterals_thrown", 0) + p.get("lateral_receptions", 0) > 0],
            key=lambda x: x.get("lateral_yards", 0), reverse=True,
        )
        if lateralists:
            ui.label("Laterals").classes("text-sm font-semibold text-slate-600 mt-3 mb-1")
            cols = [
                {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
                {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
                {"name": "thr", "label": "Thr", "field": "thr", "align": "center"},
                {"name": "recv", "label": "Rec", "field": "recv", "align": "center"},
                {"name": "yds", "label": "Yds", "field": "yds", "align": "center", "sortable": True},
                {"name": "ast", "label": "Ast", "field": "ast", "align": "center"},
                {"name": "td", "label": "TD", "field": "td", "align": "center"},
            ]
            rows = [{
                "name": p.get("name", "?"), "pos": p.get("position", ""),
                "thr": str(p.get("laterals_thrown", 0)),
                "recv": str(p.get("lateral_receptions", 0)),
                "yds": str(p.get("lateral_yards", 0)),
                "ast": str(p.get("lateral_assists", 0)),
                "td": str(p.get("lateral_tds", 0)),
            } for p in lateralists]
            ui.table(columns=cols, rows=rows, row_key="name").props("dense flat bordered").classes("w-full")

        # Special Teams (CVL detail)
        st_players = [p for p in players if (
            p.get("kick_returns", 0) + p.get("punt_returns", 0)
            + p.get("st_tackles", 0) + p.get("keeper_bells", 0) > 0
        )]
        if st_players:
            ui.label("Special Teams").classes("text-sm font-semibold text-slate-600 mt-3 mb-1")
            cols = [
                {"name": "name", "label": "Player", "field": "name", "align": "left"},
                {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
                {"name": "kr", "label": "KR", "field": "kr", "align": "center"},
                {"name": "kr_yds", "label": "KR Yds", "field": "kr_yds", "align": "center"},
                {"name": "pr", "label": "PR", "field": "pr", "align": "center"},
                {"name": "pr_yds", "label": "PR Yds", "field": "pr_yds", "align": "center"},
                {"name": "st_tkl", "label": "ST Tkl", "field": "st_tkl", "align": "center"},
                {"name": "bells", "label": "Bells", "field": "bells", "align": "center"},
            ]
            rows = [{
                "name": p.get("name", "?"), "pos": p.get("position", ""),
                "kr": str(p.get("kick_returns", 0)),
                "kr_yds": str(p.get("kick_return_yards", 0)),
                "pr": str(p.get("punt_returns", 0)),
                "pr_yds": str(p.get("punt_return_yards", 0)),
                "st_tkl": str(p.get("st_tackles", 0)),
                "bells": str(p.get("keeper_bells", 0)),
            } for p in st_players]
            ui.table(columns=cols, rows=rows, row_key="name").props("dense flat bordered").classes("w-full")


# ── Defense Stats ──

def _fiv_render_defense_stats(home_name: str, away_name: str, home_ps: list, away_ps: list):
    for side_name, players in [(away_name, away_ps), (home_name, home_ps)]:
        if not isinstance(players, list) or not players:
            continue

        defenders = sorted(
            [p for p in players if p.get("tackles", 0) > 0],
            key=lambda x: x.get("tackles", 0), reverse=True,
        )
        if not defenders:
            continue

        ui.label(side_name).classes("text-lg font-bold text-indigo-700 mt-4 mb-1")
        ui.separator().classes("mb-2")

        cols = [
            {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
            {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
            {"name": "tkl", "label": "Tkl", "field": "tkl", "align": "center", "sortable": True},
            {"name": "tfl", "label": "TFL", "field": "tfl", "align": "center", "sortable": True},
            {"name": "sck", "label": "Sck", "field": "sck", "align": "center", "sortable": True},
            {"name": "hur", "label": "Hur", "field": "hur", "align": "center"},
            {"name": "ints", "label": "INT", "field": "ints", "align": "center"},
            {"name": "st", "label": "ST Tkl", "field": "st", "align": "center"},
        ]
        rows = [{
            "name": p.get("name", "?"), "pos": p.get("position", ""),
            "tkl": str(p.get("tackles", 0)),
            "tfl": str(p.get("tfl", 0)),
            "sck": str(p.get("sacks", 0)),
            "hur": str(p.get("hurries", 0)),
            "ints": str(p.get("kick_pass_ints", 0)),
            "st": str(p.get("st_tackles", 0)),
        } for p in defenders]
        ui.table(columns=cols, rows=rows, row_key="name").props("dense flat bordered").classes("w-full")


# ── Kicking Stats ──

def _fiv_render_kicking_stats(home_name: str, away_name: str, home_ps: list, away_ps: list):
    for side_name, players in [(away_name, away_ps), (home_name, home_ps)]:
        if not isinstance(players, list) or not players:
            continue

        kickers = [p for p in players if
                   p.get("dk_att", p.get("drop_kicks_attempted", 0)) +
                   p.get("pk_att", p.get("place_kicks_attempted", 0)) > 0]
        if not kickers:
            continue

        ui.label(side_name).classes("text-lg font-bold text-indigo-700 mt-4 mb-1")
        ui.separator().classes("mb-2")

        cols = [
            {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
            {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
            {"name": "dk", "label": "DK M/A", "field": "dk", "align": "center"},
            {"name": "dk_pts", "label": "DK Pts", "field": "dk_pts", "align": "center"},
            {"name": "pk", "label": "PK M/A", "field": "pk", "align": "center"},
            {"name": "pk_pts", "label": "PK Pts", "field": "pk_pts", "align": "center"},
            {"name": "total", "label": "Total Pts", "field": "total", "align": "center", "sortable": True},
        ]
        rows = []
        for p in kickers:
            dk_m = p.get("dk_made", p.get("drop_kicks_made", 0))
            dk_a = p.get("dk_att", p.get("drop_kicks_attempted", 0))
            pk_m = p.get("pk_made", p.get("place_kicks_made", 0))
            pk_a = p.get("pk_att", p.get("place_kicks_attempted", 0))
            rows.append({
                "name": p.get("name", "?"), "pos": p.get("position", ""),
                "dk": f"{dk_m}/{dk_a}", "dk_pts": str(dk_m * 5),
                "pk": f"{pk_m}/{pk_a}", "pk_pts": str(pk_m * 3),
                "total": str(dk_m * 5 + pk_m * 3),
            })
        ui.table(columns=cols, rows=rows, row_key="name").props("dense flat bordered").classes("w-full")


# ── Drive Summary (CVL feature) ──

def _fiv_render_drive_summary(home_name: str, away_name: str, drives: list):
    if not drives:
        ui.label("No drive data available for this match.").classes("text-slate-500 italic")
        return

    ui.label("Drive Summary").classes("text-sm font-semibold text-slate-600 mb-2")

    cols = [
        {"name": "num", "label": "#", "field": "num", "align": "center"},
        {"name": "team", "label": "Team", "field": "team", "align": "left"},
        {"name": "qtr", "label": "Qtr", "field": "qtr", "align": "center"},
        {"name": "start", "label": "Start", "field": "start", "align": "center"},
        {"name": "plays", "label": "Plays", "field": "plays", "align": "center"},
        {"name": "yards", "label": "Yards", "field": "yards", "align": "center"},
        {"name": "result", "label": "Result", "field": "result", "align": "left"},
    ]
    rows = []
    for i, d in enumerate(drives):
        team_label = home_name if d.get("team") == "home" else away_name
        result_lbl = drive_result_label(d.get("result", ""))
        if d.get("delta_drive"):
            result_lbl += " \u0394"
        rows.append({
            "num": i + 1,
            "team": team_label,
            "qtr": f"Q{d.get('quarter', '?')}",
            "start": f"{d.get('start_yard_line', '?')}yd",
            "plays": d.get("plays", 0),
            "yards": d.get("yards", 0),
            "result": result_lbl,
        })
    ui.table(columns=cols, rows=rows, row_key="num").props("dense flat bordered").classes("w-full")


# ── Play-by-Play (CVL feature) ──

def _fiv_render_play_by_play(home_name: str, away_name: str, plays: list):
    if not plays:
        ui.label("No play-by-play data.").classes("text-slate-500 italic")
        return

    ui.label(f"{len(plays)} plays").classes("text-xs text-slate-500 mb-2")

    cols = [
        {"name": "num", "label": "#", "field": "num", "align": "center"},
        {"name": "team", "label": "Team", "field": "team", "align": "left"},
        {"name": "qtr", "label": "Qtr", "field": "qtr", "align": "center"},
        {"name": "time", "label": "Time", "field": "time", "align": "center"},
        {"name": "down", "label": "Down", "field": "down", "align": "center"},
        {"name": "fp", "label": "FP", "field": "fp", "align": "center"},
        {"name": "desc", "label": "Description", "field": "desc", "align": "left"},
        {"name": "yds", "label": "Yds", "field": "yds", "align": "center"},
        {"name": "result", "label": "Result", "field": "result", "align": "left"},
    ]
    rows = []
    for p in plays:
        team_label = home_name if p.get("possession") == "home" else away_name
        rows.append({
            "num": p.get("play_number", ""),
            "team": team_label,
            "qtr": f"Q{p.get('quarter', '?')}",
            "time": format_time(p.get("time_remaining", 0)),
            "down": f"{p.get('down', '')}&{p.get('yards_to_go', '')}",
            "fp": f"{p.get('field_position', '')}yd",
            "desc": p.get("description", ""),
            "yds": p.get("yards", 0),
            "result": p.get("result", ""),
        })
    ui.table(columns=cols, rows=rows, row_key="num").props(
        "dense flat bordered virtual-scroll"
    ).classes("w-full").style("max-height: 600px;")
