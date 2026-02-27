"""International Viperball (FIV) UI for the NiceGUI Viperball app.

Spectator-only: watch continental championships, the cross-confederation
playoff, and the FIV World Cup.  Browse world rankings, national team
rosters, and full box scores.  Bet via DraftyQueenz integration.
"""

from __future__ import annotations

import logging

_log = logging.getLogger("viperball.international")

from nicegui import ui, run, app

from ui import api_client

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

    # State tracking for sub-tabs
    active_tab = {"current": "dashboard"}

    # Try to load active cycle
    cycle_data = {"data": None}
    try:
        data = await run.io_bound(api_client.fiv_active_cycle)
        cycle_data["data"] = data
    except Exception:
        cycle_data["data"] = None

    # ── Sub-navigation tabs ──
    tab_container = ui.row().classes("w-full mb-4 gap-1 flex-wrap")
    content_area = ui.column().classes("w-full")

    tabs = [
        ("dashboard", "Dashboard", "dashboard"),
        ("rankings", "World Rankings", "leaderboard"),
        ("continental", "Continental", "emoji_events"),
        ("playoff", "Playoff", "sports_score"),
        ("worldcup", "World Cup", "emoji_events"),
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

    # Render initial tab
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
        # No active cycle
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

    # Active cycle info
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
                        result = await run.io_bound(api_client.fiv_sim_all_continental)
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
                        result = await run.io_bound(api_client.fiv_world_cup_draw)
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

    # Continental results summary (if available)
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

    ui.table(columns=columns, rows=rankings, row_key="code").props(
        "flat dense bordered"
    ).classes("w-full max-w-lg")


# ═══════════════════════════════════════════════════════════════
# CONTINENTAL CHAMPIONSHIPS
# ═══════════════════════════════════════════════════════════════

async def _render_continental(cycle_data: dict):
    """Render continental championship results."""
    ui.label("Continental Championships").classes("text-xl font-bold text-slate-800 mb-4")

    data = cycle_data.get("data")
    if data is None:
        ui.label("No active cycle.").classes("text-slate-500 italic")
        return

    confs = data.get("confederations_data", {})
    if not confs:
        ui.label("Continental championships not yet started.").classes("text-slate-500 italic")
        return

    # Sim buttons for individual confederations
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

            # Group tables
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
                            "pf": stats.get("points_for", 0),
                            "pa": stats.get("points_against", 0),
                            "pts": stats.get("points", 0),
                        })

                    ui.table(columns=columns, rows=rows, row_key="team").props(
                        "flat dense bordered"
                    ).classes("w-full max-w-xl mb-2")

            # Knockout bracket
            knockout = cc.get("knockout_rounds", [])
            if knockout:
                ui.label("Knockout Stage").classes("text-sm font-semibold text-slate-600 mt-2 mb-1")
                for kr in knockout:
                    ui.label(kr.get("round_name", "")).classes("text-xs font-semibold text-slate-500")
                    for m in kr.get("matchups", []):
                        home = m.get("home", "?")
                        away = m.get("away", "?")
                        winner = m.get("winner", "")
                        hs = m.get("home_score", "")
                        as_ = m.get("away_score", "")
                        score_text = f"  ({hs} - {as_})" if hs != "" else ""
                        winner_tag = f"  -> {winner}" if winner else ""
                        ui.label(f"{home} vs {away}{score_text}{winner_tag}").classes(
                            "text-xs text-slate-600 ml-4"
                        )


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
            home = m.get("home", "?")
            away = m.get("away", "?")
            winner = m.get("winner", "")
            hs = m.get("home_score", "")
            as_ = m.get("away_score", "")
            score_text = f"  ({hs} - {as_})" if hs != "" else ""
            winner_tag = f"  -> {winner}" if winner else ""
            ui.label(f"{home} vs {away}{score_text}{winner_tag}").classes(
                "text-xs text-slate-600 ml-4"
            )


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
                        "pf": stats.get("points_for", 0),
                        "pa": stats.get("points_against", 0),
                        "pts": stats.get("points", 0),
                    })

                ui.table(columns=columns, rows=rows, row_key="team").props(
                    "flat dense bordered"
                ).classes("w-full max-w-xl mb-2")

    # Knockout bracket
    knockout = wc.get("knockout_rounds", [])
    if knockout:
        with ui.expansion("Knockout Stage", icon="account_tree", value=True).classes("w-full mb-2"):
            for kr in knockout:
                round_name = kr.get("round_name", "")
                ui.label(round_name).classes("text-sm font-bold text-slate-700 mt-2")
                for m in kr.get("matchups", []):
                    home = m.get("home", "?")
                    away = m.get("away", "?")
                    winner = m.get("winner", "")
                    hs = m.get("home_score", "")
                    as_ = m.get("away_score", "")
                    is_winner_home = winner == home

                    with ui.row().classes("gap-2 items-center ml-4 mb-1"):
                        home_cls = "font-bold text-indigo-600" if is_winner_home else "text-slate-600"
                        away_cls = "font-bold text-indigo-600" if not is_winner_home and winner else "text-slate-600"
                        ui.label(home).classes(f"text-sm {home_cls} w-12")
                        if hs != "":
                            ui.label(f"{int(hs)}").classes(f"text-sm font-mono {home_cls}")
                            ui.label("—").classes("text-xs text-slate-400")
                            ui.label(f"{int(as_)}").classes(f"text-sm font-mono {away_cls}")
                        ui.label(away).classes(f"text-sm {away_cls} w-12")
