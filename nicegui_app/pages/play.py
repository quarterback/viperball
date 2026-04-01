"""Play section — NiceGUI version.

Orchestrates the main Play tab: mode selection (New Season / Quick Game)
when no session is active, or the active season simulation UI when a
session exists.

All API calls use ``await run.io_bound()`` so that the blocking HTTP
round-trip runs in a thread-pool, keeping the NiceGUI / uvicorn event-loop
free to actually process the request (NiceGUI + FastAPI share one process).
"""

from __future__ import annotations

from nicegui import ui, run

from ui import api_client
from nicegui_app.state import UserState
from nicegui_app.helpers import fmt_vb_score
from nicegui_app.components import metric_card, stat_table, notify_error, notify_info, notify_success, section_header
from nicegui_app.pages.postseason import render_playoff_bracket, render_bowl_games


def render_play_section_sync(state: UserState, shared: dict):
    """Synchronous entry point — used for initial page render in NiceGUI 3.x."""
    if state.mode in ("season", "dynasty", "dq"):
        ui.label("Loading session...").classes("text-slate-400")
        ui.timer(0.1, lambda: _deferred_play_load(state, shared), once=True)
    else:
        _render_mode_selection(state, shared)


async def _deferred_play_load(state: UserState, shared: dict):
    """Load active session content asynchronously after page render."""
    try:
        if state.mode in ("season", "dynasty"):
            await _render_season_play(state, shared)
        elif state.mode == "dq":
            from nicegui_app.pages.dq_mode import render_dq_play
            await render_dq_play(state, shared)
    except Exception as exc:
        ui.label(f"Error: {exc}").classes("text-red-500")


async def render_play_section(state: UserState, shared: dict, *, play_tab: str | None = None):
    """Async entry point — used when switching tabs via nav buttons."""
    if state.mode in ("season", "dynasty"):
        await _render_season_play(state, shared)
    elif state.mode == "dq":
        from nicegui_app.pages.dq_mode import render_dq_play
        await render_dq_play(state, shared)
    else:
        _render_mode_selection(state, shared, play_tab=play_tab)


def _render_mode_selection(state: UserState, shared: dict, *, play_tab: str | None = None):
    """Show mode selection tabs when no active session.

    ``play_tab`` selects which sub-tab to show initially:
    ``"season"`` / ``"dynasty"`` / ``"quick"`` (default) / ``"dq"``.
    """
    ui.label("Play").classes("text-2xl font-bold text-slate-800")
    ui.label("Start a new season or play a quick exhibition game").classes("text-sm text-gray-500 mb-4")

    with ui.tabs().classes("w-full").props("mobile-arrows outside-arrows") as mode_tabs:
        season_tab = ui.tab("New Season")
        dynasty_tab = ui.tab("Dynasty")
        quick_tab = ui.tab("Quick Game")
        dq_tab = ui.tab("DraftyQueenz")

    # Map landing-page card keys to the tab objects
    _tab_map = {
        "season": season_tab,
        "dynasty": dynasty_tab,
        "quick": quick_tab,
        "dq": dq_tab,
    }
    initial_tab = _tab_map.get(play_tab, quick_tab)

    # --- Lazy tab rendering: only build content when a tab is first shown ---
    _rendered: dict[str, bool] = {}

    # Container that holds the active tab's content
    panel_container = ui.column().classes("w-full")

    def _render_tab(tab_key: str):
        """Render the content for the given tab key into panel_container."""
        if tab_key in _rendered:
            return
        _rendered[tab_key] = True
        panel_container.clear()
        with panel_container:
            try:
                if tab_key == "season":
                    from nicegui_app.pages.season_simulator import render_season_simulator
                    render_season_simulator(state, shared)
                elif tab_key == "dynasty":
                    from nicegui_app.pages.dynasty_mode import render_dynasty_mode
                    render_dynasty_mode(state, shared)
                elif tab_key == "quick":
                    from nicegui_app.pages.game_simulator import render_game_simulator
                    render_game_simulator(state, shared)
                elif tab_key == "dq":
                    from nicegui_app.pages.dq_mode import render_dq_setup
                    render_dq_setup(state, shared)
            except Exception as e:
                ui.label(f"Error loading: {e}").classes("text-red-500")

    # Reverse map: tab object → key
    _tab_key_map = {id(v): k for k, v in _tab_map.items()}

    def _on_tab_change(e):
        tab_key = _tab_key_map.get(id(e.value))
        if tab_key:
            _rendered.clear()          # Clear tracked state so we re-render
            _render_tab(tab_key)

    mode_tabs.on_value_change(_on_tab_change)

    # Render initial tab
    initial_key = play_tab if play_tab in _tab_map else "quick"
    mode_tabs.set_value(initial_tab)
    _render_tab(initial_key)


_PORTAL_POSITIONS = ["All", "VP", "HB", "WB", "SB", "ZB", "LB", "CB", "LA", "LM"]

_ROLE_LABELS = {
    "head_coach": "Head Coach",
    "oc": "Off. Coordinator",
    "dc": "Def. Coordinator",
    "stc": "Special Teams",
}


async def _render_coaching_selection(state: UserState, refresh_fn):
    """Coaching staff selection — shown during the portal phase.

    Users can view their current staff, generate a pool of candidates,
    and hire replacements for HC, OC, DC, or STC before the season starts.
    """
    ui.label("Coaching Staff").classes("text-xl font-bold text-slate-700 mt-2")
    ui.label(
        "Review your coaching staff and optionally hire new coaches before the season."
    ).classes("text-sm text-gray-500 mb-2")

    # ── Current staff ────────────────────────────────────────────────
    try:
        staff_resp = await run.io_bound(
            api_client.season_coaching_staff_get, state.session_id,
        )
    except api_client.APIError as e:
        notify_error(f"Could not load coaching staff: {e.detail}")
        return

    staff = staff_resp.get("staff", {})
    team_name = staff_resp.get("team", "")
    dev_aura_pct = staff_resp.get("dev_aura_max_boost_pct", 0)

    with ui.row().classes("w-full gap-3 flex-wrap mb-2"):
        metric_card("Team", team_name)
        metric_card("Dev Aura", f"+{dev_aura_pct}%")

    staff_rows = []
    for role_key, label in _ROLE_LABELS.items():
        coach = staff.get(role_key)
        if coach:
            staff_rows.append({
                "Role": label,
                "Name": coach.get("name", "—"),
                "OVR": coach.get("visible_score", ""),
                "Style": coach.get("classification_label", ""),
                "Stars": coach.get("star_rating", ""),
                "LDR": coach.get("leadership", ""),
                "DEV": coach.get("development", ""),
                "REC": coach.get("recruiting", ""),
            })
        else:
            staff_rows.append({
                "Role": label, "Name": "— Vacant —",
                "OVR": "", "Style": "", "Stars": "",
                "LDR": "", "DEV": "", "REC": "",
            })
    stat_table(staff_rows)

    # ── Pool generation & hiring ─────────────────────────────────────
    pool_container = ui.column().classes("w-full")

    async def _generate_pool():
        try:
            pool_resp = await run.io_bound(
                api_client.season_coaching_pool_generate, state.session_id,
            )
            pool = pool_resp.get("pool", [])
            _show_pool(pool)
        except api_client.APIError as e:
            notify_error(f"Could not generate pool: {e.detail}")

    def _show_pool(pool: list):
        pool_container.clear()
        with pool_container:
            if not pool:
                ui.label("No candidates available.").classes(
                    "text-sm text-gray-400 italic"
                )
                return

            for role_key, label in _ROLE_LABELS.items():
                candidates = [c for c in pool if c.get("role") == role_key]
                if not candidates:
                    continue

                with ui.expansion(
                    f"{label} Candidates ({len(candidates)})",
                    icon="person_search",
                ).classes("w-full mt-2"):
                    rows = []
                    for c in candidates:
                        rows.append({
                            "Name": c.get("name", ""),
                            "OVR": c.get("visible_score", ""),
                            "Style": c.get("classification_label", ""),
                            "Stars": c.get("star_rating", ""),
                            "LDR": c.get("leadership", ""),
                            "CMP": c.get("composure", ""),
                            "DEV": c.get("development", ""),
                            "REC": c.get("recruiting", ""),
                        })
                    stat_table(rows)

                    hire_options = {
                        i: f"{c.get('name', '')} (OVR {c.get('visible_score', '?')}, {c.get('classification_label', '')})"
                        for i, c in enumerate(candidates)
                    }
                    sel = ui.select(
                        hire_options, value=0, label="Select Coach to Hire",
                    ).classes("w-full max-w-lg")

                    async def _hire(sel=sel, candidates=candidates, role_key=role_key):
                        idx = sel.value
                        if idx is None:
                            return
                        coach = candidates[idx]
                        cid = coach.get("coach_id", "")
                        if not cid:
                            notify_error("Missing coach ID.")
                            return
                        try:
                            result = await run.io_bound(
                                api_client.season_coaching_hire,
                                state.session_id,
                                coach_id=cid,
                                role=role_key,
                            )
                            hired_name = result.get("coach", {}).get("name", "")
                            notify_success(f"Hired {hired_name} as {_ROLE_LABELS.get(role_key, role_key)}!")
                            refresh_fn.refresh()
                        except api_client.APIError as e:
                            notify_error(f"Hire failed: {e.detail}")

                    ui.button(
                        f"Hire as {label}", on_click=_hire, icon="how_to_reg",
                    ).props("color=primary").classes("mt-2")

    ui.button(
        "Browse Available Coaches", on_click=_generate_pool, icon="group_add",
    ).classes("mt-2")


async def _render_season_portal(state: UserState, refresh_fn):
    """Render the transfer portal UI for season mode.

    Lets the human player browse available transfers, commit players to
    their roster, and advance past the portal phase to start the regular
    season.
    """
    ui.label("Pre-Season Portal").classes("text-xl font-bold text-slate-700 mt-2")
    ui.label(
        "Pick transfer players and coaching staff, then start the season when ready."
    ).classes("text-sm text-gray-500 mb-2")

    # ── Prominent Start Season bar at top ─────────────────────────
    async def _start_season():
        try:
            await run.io_bound(api_client.season_portal_skip, state.session_id)
            notify_success("Portal complete — starting regular season!")
            refresh_fn.refresh()
        except api_client.APIError as e:
            notify_error(f"Could not advance: {e.detail}")

    with ui.card().classes("w-full bg-green-50 p-4 rounded mb-4"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("When you're done picking transfers and coaches:").classes("text-green-800")
            ui.button(
                "Start Season", on_click=_start_season, icon="sports_football",
            ).props("color=primary size=lg")

    ui.label("Transfer Portal").classes("text-lg font-semibold text-slate-700 mt-2")

    try:
        portal_resp = await run.io_bound(api_client.season_portal_get, state.session_id)
    except api_client.APIError as e:
        notify_error(f"Could not load portal: {e.detail}")
        return

    entries = portal_resp.get("entries", [])
    committed = portal_resp.get("committed", [])
    cap = portal_resp.get("transfer_cap", 0)
    remaining = portal_resp.get("transfers_remaining", 0)
    if remaining == -1:
        remaining = cap

    # ── Metrics ──────────────────────────────────────────────────────
    with ui.row().classes("w-full gap-3 flex-wrap mb-4"):
        metric_card("Available Players", len(entries))
        metric_card("Transfer Cap", cap)
        metric_card("Slots Remaining", remaining)

    # ── Committed players ────────────────────────────────────────────
    if committed:
        ui.label("Your Incoming Transfers").classes("font-bold text-slate-700 mt-2")
        committed_rows = []
        for c in committed:
            committed_rows.append({
                "Name": c.get("name", ""),
                "Pos": c.get("position", ""),
                "OVR": c.get("overall", 0),
                "Year": c.get("year", ""),
                "From": c.get("origin_team", ""),
            })
        stat_table(committed_rows)

    ui.separator().classes("my-4")

    # ── Filters ──────────────────────────────────────────────────────
    with ui.row().classes("gap-4 items-end mb-2"):
        pos_filter = ui.select(
            {p: p for p in _PORTAL_POSITIONS},
            value="All", label="Position Filter",
        ).classes("w-40")
        ovr_filter = ui.number(
            "Min Overall", value=0, min=0, max=99, step=1,
        ).classes("w-32")

    # Container that re-renders the player table when filters change
    table_container = ui.column().classes("w-full")

    def _apply_filters():
        filtered = entries
        pv = pos_filter.value
        ov = ovr_filter.value or 0
        if pv and pv != "All":
            filtered = [e for e in filtered if e.get("position", "") == pv]
        if ov > 0:
            filtered = [e for e in filtered if e.get("overall", 0) >= ov]
        return filtered

    def _rebuild_table():
        table_container.clear()
        filtered = _apply_filters()
        with table_container:
            if not filtered:
                ui.label("No available portal players matching your filters.").classes(
                    "text-sm text-gray-400 italic"
                )
                return

            rows = []
            for e in filtered:
                reason = e.get("reason", "").replace("_", " ").title()
                rows.append({
                    "Name": e.get("name", ""),
                    "Pos": e.get("position", ""),
                    "OVR": e.get("overall", 0),
                    "Year": e.get("year", ""),
                    "From": e.get("origin_team", ""),
                    "Reason": reason,
                    "Stars": e.get("potential", 0),
                })
            stat_table(rows)

            if remaining > 0:
                ui.label("Commit a Player").classes("font-bold text-slate-700 mt-4")
                player_options = {
                    i: f"{e.get('name', '')} ({e.get('position', '')}, OVR {e.get('overall', 0)}) — from {e.get('origin_team', '')}"
                    for i, e in enumerate(filtered)
                }
                sel = ui.select(player_options, value=0, label="Select Player").classes("w-full max-w-lg")

                async def _commit_player():
                    idx = sel.value
                    if idx is None:
                        return
                    selected = filtered[idx]
                    global_idx = selected.get("global_index", -1)
                    if global_idx < 0:
                        notify_error("Cannot interact with this player — try refreshing.")
                        return
                    team_name = portal_resp.get("human_team", "")
                    if not team_name:
                        notify_error("Could not determine your team name.")
                        return
                    try:
                        result = await run.io_bound(
                            api_client.season_portal_commit,
                            state.session_id,
                            team_name=team_name,
                            entry_index=global_idx,
                        )
                        pname = result.get("player", {}).get("name", selected.get("name", ""))
                        slots = result.get("transfers_remaining", 0)
                        notify_success(f"Committed {pname}! ({slots} slots remaining)")
                        refresh_fn.refresh()
                    except api_client.APIError as e:
                        notify_error(f"Commit failed: {e.detail}")

                ui.button(
                    "Commit Selected Player", on_click=_commit_player, icon="person_add",
                ).props("color=primary").classes("mt-2")
            else:
                ui.label("You've used all your transfer slots.").classes(
                    "text-sm text-amber-600 italic mt-2"
                )

    pos_filter.on_value_change(lambda _: _rebuild_table())
    ovr_filter.on_value_change(lambda _: _rebuild_table())
    _rebuild_table()

    # ── Coaching Staff Selection ─────────────────────────────────────
    ui.separator().classes("my-4")
    await _render_coaching_selection(state, refresh_fn)

    # ── Bottom Start Season button (mirrors the top one) ────────────
    ui.separator().classes("my-4")
    with ui.card().classes("w-full bg-green-50 p-4 rounded"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Ready to play? Start the regular season.").classes("text-green-800")
            ui.button(
                "Start Season", on_click=_start_season, icon="sports_football",
            ).props("color=primary size=lg")


async def _fetch_bracket(session_id: str) -> dict:
    try:
        return await run.io_bound(api_client.get_playoff_bracket, session_id)
    except api_client.APIError:
        return {}


async def _fetch_bowls(session_id: str) -> dict:
    try:
        return await run.io_bound(api_client.get_bowl_results, session_id)
    except api_client.APIError:
        return {}


async def _render_offseason_flow(state: UserState, shared: dict, off_status: dict):
    """Render the offseason flow: NIL allocation, transfer portal, recruiting."""
    try:
        dyn_status = await run.io_bound(api_client.get_dynasty_status, state.session_id)
    except api_client.APIError:
        notify_error("Could not load dynasty status.")
        return

    dynasty_name = dyn_status.get("dynasty_name", "Dynasty")
    current_year = dyn_status.get("current_year", "?")
    coach_team = dyn_status.get("coach", {}).get("team", "")
    off_phase = off_status.get("phase", "nil")

    ui.label(f"{dynasty_name} — Offseason (Year {current_year})").classes("text-2xl font-bold text-slate-800")

    # Progress stepper
    phase_labels = {"nil": "NIL Budget", "portal": "Transfer Portal", "recruiting": "Recruiting", "ready": "Finalize"}
    phase_order = ["nil", "portal", "recruiting", "ready"]
    current_idx = phase_order.index(off_phase) if off_phase in phase_order else 0

    with ui.row().classes("w-full gap-2 mb-4"):
        for i, key in enumerate(phase_order):
            label = phase_labels[key]
            if i < current_idx:
                ui.badge(f"{i+1}. {label}", color="green").classes("text-sm")
            elif i == current_idx:
                ui.badge(f"{i+1}. {label}", color="primary").classes("text-sm font-bold")
            else:
                ui.badge(f"{i+1}. {label}", color="grey").classes("text-sm")

    with ui.row().classes("w-full gap-3 flex-wrap mb-4"):
        metric_card("Team", coach_team)
        metric_card("Retention Risks", str(off_status.get("retention_risks_count", 0)))
        metric_card("Portal Players", str(off_status.get("portal_count", 0)))
        metric_card("Recruit Pool", str(off_status.get("recruit_pool_size", 0)))

    if off_phase == "nil":
        await _render_offseason_nil(state, off_status)
    elif off_phase == "portal":
        await _render_offseason_portal(state, coach_team)
    elif off_phase == "recruiting":
        await _render_offseason_recruiting(state, coach_team)
    elif off_phase == "ready":
        await _render_offseason_finalize(state, current_year)


async def _render_offseason_nil(state: UserState, off_status: dict):
    """NIL budget allocation phase."""
    ui.label("NIL Budget Allocation").classes("text-xl font-bold text-slate-700 mt-2")
    ui.label("Allocate your NIL budget across recruiting, transfer portal, and player retention.").classes(
        "text-sm text-slate-500 mb-2"
    )

    try:
        nil_data = await run.io_bound(api_client.get_offseason_nil, state.session_id)
    except api_client.APIError:
        notify_error("Could not load NIL data.")
        return

    budget = nil_data.get("annual_budget", 0)
    metric_card("Annual Budget", f"${budget:,.0f}")

    default_recruit = int(budget * 0.50)
    default_portal = int(budget * 0.30)
    default_retain = budget - default_recruit - default_portal

    recruit_input = ui.number("Recruiting Pool ($)", value=default_recruit, min=0, max=budget, step=10000).classes(
        "w-48"
    )
    portal_input = ui.number("Portal Pool ($)", value=default_portal, min=0, max=budget, step=10000).classes("w-48")
    retain_input = ui.number("Retention Pool ($)", value=default_retain, min=0, max=budget, step=10000).classes("w-48")

    alloc_label = ui.label("").classes("text-sm mt-2")

    def _update_alloc():
        total = int(recruit_input.value or 0) + int(portal_input.value or 0) + int(retain_input.value or 0)
        remaining = budget - total
        if remaining >= 0:
            alloc_label.text = f"Allocated: ${total:,.0f} | Remaining: ${remaining:,.0f}"
            alloc_label.classes(remove="text-red-600", add="text-slate-600")
        else:
            alloc_label.text = f"Over budget by ${abs(remaining):,.0f}!"
            alloc_label.classes(remove="text-slate-600", add="text-red-600")

    recruit_input.on("update:model-value", lambda _: _update_alloc())
    portal_input.on("update:model-value", lambda _: _update_alloc())
    retain_input.on("update:model-value", lambda _: _update_alloc())
    _update_alloc()

    spinner = ui.spinner(size="lg").classes("hidden")

    async def _confirm():
        r = int(recruit_input.value or 0)
        p = int(portal_input.value or 0)
        t = int(retain_input.value or 0)
        if r + p + t > budget:
            notify_error(f"Total allocation exceeds budget (${budget:,.0f}).")
            return
        spinner.classes(remove="hidden")
        try:
            await run.io_bound(api_client.offseason_nil_allocate, state.session_id, r, p, t)
            notify_success("NIL budget allocated! Moving to Transfer Portal.")
            ui.navigate.to("/")
        except api_client.APIError as e:
            notify_error(f"Allocation failed: {e.detail}")
        finally:
            spinner.classes(add="hidden")

    ui.button("Confirm NIL Allocation & Continue to Portal", on_click=_confirm, icon="check").props(
        "color=primary size=lg"
    ).classes("mt-4")


async def _render_offseason_portal(state: UserState, coach_team: str):
    """Transfer portal browsing and offers."""
    ui.label("Transfer Portal").classes("text-xl font-bold text-slate-700 mt-2")
    ui.label("Browse available transfer players, make offers, and commit players to your roster.").classes(
        "text-sm text-slate-500 mb-2"
    )

    # -- Budget info --
    try:
        off_status = await run.io_bound(api_client.get_offseason_status, state.session_id)
        nil_data = await run.io_bound(api_client.get_offseason_nil, state.session_id)
    except api_client.APIError:
        off_status = {}
        nil_data = {}
    portal_pool_budget = nil_data.get("portal_pool", 0)
    portal_pool_spent_ref = {"value": nil_data.get("portal_spent", 0)}
    transfers_remaining = off_status.get("transfers_remaining", -1)

    budget_label = ui.label("").classes("text-sm font-semibold mb-2")

    def _update_budget_label():
        remaining = portal_pool_budget - portal_pool_spent_ref["value"]
        parts = [f"Portal Budget: ${remaining:,.0f} / ${portal_pool_budget:,.0f}"]
        if transfers_remaining >= 0:
            parts.append(f"Transfers Left: {transfers_remaining}")
        budget_label.text = " | ".join(parts)
        if remaining <= 0:
            budget_label.classes(remove="text-slate-700", add="text-red-600")
        else:
            budget_label.classes(remove="text-red-600", add="text-slate-700")

    _update_budget_label()

    # -- Filters row --
    positions = ["All", "VP", "HB", "WB", "SB", "ZB", "LB", "CB", "LA", "LM"]
    with ui.row().classes("gap-3 items-end mb-3"):
        pos_select = ui.select(positions, value="All", label="Position").classes("w-36")
        min_ovr = ui.number("Min OVR", value=0, min=0, max=99).classes("w-28")
        search_input = ui.input(label="Search player name").props("clearable dense outlined").classes("w-56")
        filter_btn = ui.button("Filter", icon="filter_list").props("color=secondary no-caps dense")

    portal_container = ui.column().classes("w-full")

    async def _load_portal():
        portal_container.clear()
        pos_param = pos_select.value if pos_select.value != "All" else None
        ovr_param = int(min_ovr.value) if min_ovr.value and int(min_ovr.value) > 0 else None
        try:
            portal_resp = await run.io_bound(
                api_client.get_offseason_portal, state.session_id, position=pos_param, min_overall=ovr_param
            )
        except api_client.APIError as e:
            with portal_container:
                notify_error(f"Could not load portal: {e.detail}")
            return

        entries = portal_resp.get("entries", [])
        total = portal_resp.get("total_entries", 0)
        available = portal_resp.get("total_available", 0)

        # Client-side name search
        name_query = (search_input.value or "").strip().lower()
        if name_query:
            entries = [e for e in entries if name_query in e.get("name", "").lower()]

        with portal_container:
            with ui.row().classes("gap-3 mb-3"):
                metric_card("Total Entries", str(total))
                metric_card("Available", str(available))
                metric_card("Showing", str(len(entries)))

            if not entries:
                ui.label("No available portal players matching filters.").classes("text-slate-400 italic")
                return

            # Table
            columns = [
                {"name": "name", "label": "Name", "field": "name", "align": "left", "sortable": True},
                {"name": "position", "label": "Pos", "field": "position", "sortable": True},
                {"name": "overall", "label": "OVR", "field": "overall", "sortable": True},
                {"name": "year", "label": "Year", "field": "year", "sortable": True},
                {"name": "origin_team", "label": "From", "field": "origin_team", "align": "left", "sortable": True},
                {"name": "reason", "label": "Reason", "field": "reason", "sortable": True},
                {"name": "stars", "label": "Stars", "field": "stars", "sortable": True},
                {"name": "offers", "label": "Offers", "field": "offers", "sortable": True},
            ]
            rows = [
                {
                    "name": e.get("name", ""),
                    "position": e.get("position", ""),
                    "overall": e.get("overall", 0),
                    "year": e.get("year", ""),
                    "origin_team": e.get("origin_team", ""),
                    "reason": e.get("reason", "").replace("_", " ").title(),
                    "stars": e.get("potential", 0),
                    "offers": e.get("offers_count", 0),
                    "global_index": e.get("global_index", -1),
                }
                for e in entries
            ]
            table = ui.table(
                columns=columns, rows=rows, row_key="global_index", selection="single",
                pagination={"rowsPerPage": 20, "sortBy": "overall", "descending": True},
            ).classes("w-full").props("dense flat bordered")

            # Actions for selected player
            with ui.card().classes("w-full p-3 mt-3 bg-slate-50"):
                ui.label("Player Actions").classes("text-sm font-semibold text-slate-600 mb-2")
                with ui.row().classes("gap-4 items-end"):
                    nil_offer_input = ui.number(
                        "NIL Offer ($)", value=25000, min=0,
                        max=max(0, portal_pool_budget - portal_pool_spent_ref["value"]),
                        step=5000,
                    ).classes("w-44")
                    action_spinner = ui.spinner(size="md").classes("hidden")

                    async def _make_offer():
                        selected = table.selected
                        if not selected:
                            notify_error("Select a player first.")
                            return
                        gidx = selected[0].get("global_index", -1)
                        if gidx < 0:
                            notify_error("Cannot interact with this player.")
                            return
                        offer_amt = int(nil_offer_input.value or 0)
                        remaining_budget = portal_pool_budget - portal_pool_spent_ref["value"]
                        if offer_amt > remaining_budget:
                            notify_error(f"NIL offer ${offer_amt:,} exceeds remaining portal budget ${remaining_budget:,.0f}.")
                            return
                        action_spinner.classes(remove="hidden")
                        try:
                            await run.io_bound(
                                api_client.offseason_portal_offer,
                                state.session_id,
                                entry_index=gidx,
                                nil_amount=offer_amt,
                            )
                            portal_pool_spent_ref["value"] += offer_amt
                            _update_budget_label()
                            notify_success(f"Offer sent to {selected[0]['name']}!")
                            await _load_portal()
                        except api_client.APIError as e:
                            notify_error(f"Offer failed: {e.detail}")
                        finally:
                            action_spinner.classes(add="hidden")

                    async def _commit():
                        selected = table.selected
                        if not selected:
                            notify_error("Select a player first.")
                            return
                        gidx = selected[0].get("global_index", -1)
                        if gidx < 0:
                            notify_error("Cannot interact with this player.")
                            return
                        action_spinner.classes(remove="hidden")
                        try:
                            await run.io_bound(
                                api_client.offseason_portal_commit, state.session_id, entry_index=gidx
                            )
                            notify_success(f"Committed {selected[0]['name']} to {coach_team}!")
                            await _load_portal()
                        except api_client.APIError as e:
                            notify_error(f"Commit failed: {e.detail}")
                        finally:
                            action_spinner.classes(add="hidden")

                    ui.button("Make Offer", on_click=_make_offer, icon="local_offer").props("color=secondary no-caps")
                    ui.button("Commit Player", on_click=_commit, icon="person_add").props("color=primary no-caps")

    filter_btn.on_click(lambda: _load_portal())
    await _load_portal()

    ui.separator().classes("my-4")
    resolve_spinner = ui.spinner(size="lg").classes("hidden")

    async def _resolve_portal():
        resolve_spinner.classes(remove="hidden")
        try:
            result = await run.io_bound(api_client.offseason_portal_resolve, state.session_id)
            total_transfers = result.get("total_transfers", 0)
            human_transfers = result.get("human_transfers", [])
            msg = f"Portal resolved! {total_transfers} total transfers."
            if human_transfers:
                names = ", ".join(f"{t.get('name', '')} ({t.get('position', '')})" for t in human_transfers)
                msg += f" Your transfers: {names}"
            notify_success(msg)
            ui.navigate.to("/")
        except api_client.APIError as e:
            notify_error(f"Portal resolution failed: {e.detail}")
        finally:
            resolve_spinner.classes(add="hidden")

    ui.button("Resolve Portal & Continue to Recruiting", on_click=_resolve_portal, icon="arrow_forward").props(
        "color=primary size=lg"
    )


async def _render_offseason_recruiting(state: UserState, coach_team: str):
    """Recruiting phase: scout, offer, and sign high school recruits."""
    ui.label("Recruiting").classes("text-xl font-bold text-slate-700 mt-2")
    ui.label("Scout, evaluate, and offer scholarships to high school recruits.").classes(
        "text-sm text-slate-500 mb-2"
    )

    rec_container = ui.column().classes("w-full")
    # Positions for filtering
    recruit_positions = ["All", "VP", "HB", "WB", "SB", "ZB", "LB", "CB", "LA", "LM"]

    with ui.row().classes("gap-3 items-end mb-3"):
        rec_pos_select = ui.select(recruit_positions, value="All", label="Position").classes("w-36")
        rec_search = ui.input(label="Search player name").props("clearable dense outlined").classes("w-56")
        rec_stars_min = ui.select(
            {0: "Any Stars", 3: "3+ Stars", 4: "4+ Stars", 5: "5 Stars"},
            value=0, label="Min Stars",
        ).classes("w-36")
        rec_filter_btn = ui.button("Filter", icon="filter_list").props("color=secondary no-caps dense")

    async def _load_recruiting():
        rec_container.clear()
        try:
            rec_resp = await run.io_bound(api_client.get_offseason_recruiting, state.session_id)
        except api_client.APIError as e:
            with rec_container:
                notify_error(f"Could not load recruiting: {e.detail}")
            return

        recruits = rec_resp.get("recruits", [])
        total_pool = rec_resp.get("total_pool", 0)
        board = rec_resp.get("board", {})

        # Client-side filtering
        pos_filter = rec_pos_select.value
        name_query = (rec_search.value or "").strip().lower()
        stars_min = int(rec_stars_min.value or 0)
        filtered = recruits
        if pos_filter and pos_filter != "All":
            filtered = [r for r in filtered if r.get("position", "").upper() == pos_filter.upper()]
        if name_query:
            filtered = [r for r in filtered if name_query in r.get("name", "").lower()]
        if stars_min > 0:
            filtered = [r for r in filtered if r.get("stars", 0) >= stars_min]

        with rec_container:
            with ui.row().classes("gap-3 mb-3"):
                metric_card("Recruit Pool", str(total_pool))
                metric_card("Showing", str(len(filtered)))
                if board:
                    metric_card("Scholarships", str(board.get("scholarships_available", 0)))
                    metric_card("Scouting Pts", str(board.get("scouting_points", 0)))
                    metric_card("Offers Used", f"{len(board.get('offered', []))}/{board.get('max_offers', 15)}")

            if filtered:
                columns = [
                    {"name": "name", "label": "Name", "field": "name", "align": "left", "sortable": True},
                    {"name": "position", "label": "Pos", "field": "position", "sortable": True},
                    {"name": "stars", "label": "Stars", "field": "stars", "sortable": True},
                    {"name": "region", "label": "Region", "field": "region", "sortable": True},
                    {"name": "hometown", "label": "Hometown", "field": "hometown", "align": "left"},
                    {"name": "scout_level", "label": "Scouted", "field": "scout_level", "sortable": True},
                ]
                rows = []
                for r in filtered[:100]:
                    row = {
                        "name": r.get("name", ""),
                        "position": r.get("position", ""),
                        "stars": r.get("stars", 0),
                        "region": r.get("region", "").replace("_", " ").title(),
                        "hometown": r.get("hometown", ""),
                        "pool_index": r.get("pool_index", 0),
                        "scout_level": r.get("scout_level", "none").title(),
                    }
                    scouted = r.get("scouted", {})
                    if scouted:
                        row["spd"] = scouted.get("speed", "?")
                        row["agi"] = scouted.get("agility", "?")
                        row["pwr"] = scouted.get("power", "?")
                        row["hnd"] = scouted.get("hands", "?")
                    if "true_overall" in r:
                        row["ovr"] = r["true_overall"]
                    rows.append(row)

                # Add scouted attribute columns if any recruit has them
                has_scouted = any("spd" in r for r in rows)
                if has_scouted:
                    columns += [
                        {"name": "spd", "label": "SPD", "field": "spd", "sortable": True},
                        {"name": "agi", "label": "AGI", "field": "agi", "sortable": True},
                        {"name": "pwr", "label": "PWR", "field": "pwr", "sortable": True},
                        {"name": "hnd", "label": "HND", "field": "hnd", "sortable": True},
                    ]
                has_ovr = any("ovr" in r for r in rows)
                if has_ovr:
                    columns.append({"name": "ovr", "label": "OVR", "field": "ovr", "sortable": True})

                table = ui.table(
                    columns=columns, rows=rows, row_key="pool_index", selection="single",
                    pagination={"rowsPerPage": 25, "sortBy": "stars", "descending": True},
                ).classes("w-full").props("dense flat bordered")

                with ui.card().classes("w-full p-3 mt-3 bg-slate-50"):
                    ui.label("Recruit Actions").classes("text-sm font-semibold text-slate-600 mb-2")
                    with ui.row().classes("gap-4 items-end"):
                        scout_level = ui.select(
                            {"basic": "Basic (1 pt)", "full": "Full (3 pts)"},
                            value="basic", label="Scout Level",
                        ).classes("w-40")
                        action_spinner = ui.spinner(size="md").classes("hidden")

                        async def _scout():
                            selected = table.selected
                            if not selected:
                                notify_error("Select a recruit first.")
                                return
                            pidx = selected[0].get("pool_index", 0)
                            action_spinner.classes(remove="hidden")
                            try:
                                result = await run.io_bound(
                                    api_client.offseason_recruiting_scout,
                                    state.session_id,
                                    recruit_index=pidx,
                                    level=scout_level.value,
                                )
                                pts_left = result.get("scouting_points_remaining", 0)
                                notify_success(f"Scouted {selected[0]['name']}! ({pts_left} pts remaining)")
                                # Reload data in-place instead of full page refresh
                                await _load_recruiting()
                            except api_client.APIError as e:
                                notify_error(f"Scouting failed: {e.detail}")
                            finally:
                                action_spinner.classes(add="hidden")

                        async def _offer():
                            selected = table.selected
                            if not selected:
                                notify_error("Select a recruit first.")
                                return
                            pidx = selected[0].get("pool_index", 0)
                            action_spinner.classes(remove="hidden")
                            try:
                                result = await run.io_bound(
                                    api_client.offseason_recruiting_offer, state.session_id, recruit_index=pidx
                                )
                                offers_made = result.get("offers_made", 0)
                                max_offers = result.get("max_offers", 0)
                                notify_success(f"Offered {selected[0]['name']}! ({offers_made}/{max_offers} offers used)")
                                # Reload data in-place instead of full page refresh
                                await _load_recruiting()
                            except api_client.APIError as e:
                                notify_error(f"Offer failed: {e.detail}")
                            finally:
                                action_spinner.classes(add="hidden")

                        ui.button("Scout", on_click=_scout, icon="search").props("color=secondary no-caps")
                        ui.button("Offer Scholarship", on_click=_offer, icon="school").props("color=primary no-caps")

            else:
                ui.label("No recruits matching filters.").classes("text-slate-400 italic")

            # Offer board
            if board and board.get("offered"):
                ui.separator().classes("my-3")
                ui.label("Your Offer Board").classes("text-lg font-semibold text-slate-700 mt-2")
                offer_rows = []
                for offered_id in board.get("offered", []):
                    for r in recruits:
                        if r.get("name", "") in offered_id or offered_id in r.get("name", ""):
                            offer_rows.append({
                                "name": r.get("name", ""),
                                "pos": r.get("position", ""),
                                "stars": r.get("stars", 0),
                                "scouted": r.get("scout_level", "none").title(),
                            })
                            break
                if offer_rows:
                    ui.table(
                        columns=[
                            {"name": "name", "label": "Name", "field": "name", "align": "left"},
                            {"name": "pos", "label": "Pos", "field": "pos"},
                            {"name": "stars", "label": "Stars", "field": "stars"},
                            {"name": "scouted", "label": "Scouted", "field": "scouted"},
                        ],
                        rows=offer_rows,
                        row_key="name",
                    ).classes("w-full").props("dense flat bordered")

    rec_filter_btn.on_click(lambda: _load_recruiting())
    await _load_recruiting()

    ui.separator().classes("my-4")
    resolve_spinner = ui.spinner(size="lg").classes("hidden")

    async def _resolve_recruiting():
        resolve_spinner.classes(remove="hidden")
        try:
            result = await run.io_bound(api_client.offseason_recruiting_resolve, state.session_id)
            human_signed = result.get("human_signed", [])
            total_signed = result.get("total_signed", 0)
            msg = f"Signing day complete! {total_signed} total recruits signed."
            if human_signed:
                names = ", ".join(f"{r.get('name', '')} ({r.get('position', '')})" for r in human_signed)
                msg += f" Your class: {names}"
            notify_success(msg)
            ui.navigate.to("/")
        except api_client.APIError as e:
            notify_error(f"Signing day failed: {e.detail}")
        finally:
            resolve_spinner.classes(add="hidden")

    ui.button("Run Signing Day & Continue", on_click=_resolve_recruiting, icon="arrow_forward").props(
        "color=primary size=lg"
    )


async def _render_offseason_finalize(state: UserState, current_year):
    """Offseason ready — finalize and move to season setup."""
    ui.label("Offseason Complete").classes("text-xl font-bold text-green-700 mt-2")
    ui.label(
        "All offseason phases are done! Your roster has been updated with portal transfers and incoming recruits."
    ).classes("text-sm text-slate-600 mb-4")

    spinner = ui.spinner(size="lg").classes("hidden")

    async def _finalize():
        spinner.classes(remove="hidden")
        try:
            await run.io_bound(api_client.offseason_complete, state.session_id)
            notify_success(f"Offseason finalized! Ready to start the {current_year} season.")
            ui.navigate.to("/")
        except api_client.APIError as e:
            notify_error(f"Finalize failed: {e.detail}")
        finally:
            spinner.classes(add="hidden")

    ui.button(f"Start {current_year} Season Setup", on_click=_finalize, icon="sports_football").props(
        "color=primary size=lg"
    )


async def _render_dynasty_start_season(state: UserState, shared: dict):
    """Show dynasty start-season UI when dynasty exists but no active season."""
    try:
        dyn_status = await run.io_bound(api_client.get_dynasty_status, state.session_id)
    except api_client.APIError:
        state.clear_session()
        notify_info("Dynasty session expired. Please create or load a dynasty.")
        _render_mode_selection(state, shared, play_tab="dynasty")
        return

    dynasty_name = dyn_status.get("dynasty_name", "Dynasty")
    current_year = dyn_status.get("current_year", "?")
    coach_info = dyn_status.get("coach", {})
    coach_team = coach_info.get("team", "")
    seasons_played = dyn_status.get("seasons_played", 0)
    history_years = dyn_status.get("history_years", 0)

    ui.label(f"{dynasty_name}").classes("text-2xl font-bold text-slate-800")

    with ui.row().classes("w-full gap-3 flex-wrap mb-4"):
        metric_card("Year", str(current_year))
        metric_card("Seasons Coached", str(seasons_played))
        if history_years > 0:
            metric_card("Program History", f"{history_years} yrs")
        metric_card("Team", coach_team)

    ui.label("Start Next Season").classes("text-xl font-bold text-slate-700 mt-2")

    dyn_games = dyn_status.get("games_per_team", 12)
    dyn_playoff = dyn_status.get("playoff_size", 8)
    dyn_bowls = dyn_status.get("bowl_count", 4)

    with ui.row().classes("gap-4 flex-wrap"):
        metric_card("Games per Team", str(dyn_games))
        metric_card("Playoff Size", f"{dyn_playoff} teams")
        metric_card("Bowl Games", str(dyn_bowls))

    starting_spinner = ui.spinner(size="lg").classes("hidden")

    async def _start():
        starting_spinner.classes(remove="hidden")
        try:
            await run.io_bound(
                api_client.dynasty_start_season,
                state.session_id,
            )
            state.season_phase = "regular"
            notify_success(f"Year {current_year} season started!")
            ui.navigate.to("/")
        except api_client.APIError as e:
            notify_error(f"Failed to start season: {e.detail}")
        finally:
            starting_spinner.classes(add="hidden")

    ui.button("Start Season", on_click=_start, icon="sports_football").props("color=primary size=lg")


async def _render_season_play(state: UserState, shared: dict):
    """Render the active season simulation UI."""
    if not state.session_id:
        ui.label("No active session.").classes("text-gray-400 italic")
        return

    try:
        status = await run.io_bound(api_client.get_season_status, state.session_id)
    except api_client.APIError:
        # Dynasty in setup/offseason — no active season yet
        if state.mode == "dynasty":
            # Check if we're in offseason (has offseason activities to do)
            try:
                off_status = await run.io_bound(api_client.get_offseason_status, state.session_id)
                await _render_offseason_flow(state, shared, off_status)
                return
            except api_client.APIError:
                pass
            # Not in offseason — show start season UI
            await _render_dynasty_start_season(state, shared)
            return
        old_mode = state.mode
        state.clear_session()
        notify_info("Previous session expired. Please start a new one.")
        _render_mode_selection(state, shared, play_tab=old_mode)
        return

    # After dynasty advance, phase is "offseason" and season is gone — show offseason UI
    if state.mode == "dynasty" and status.get("phase") == "offseason":
        try:
            off_status = await run.io_bound(api_client.get_offseason_status, state.session_id)
            await _render_offseason_flow(state, shared, off_status)
            return
        except api_client.APIError:
            await _render_dynasty_start_season(state, shared)
            return

    season_name = status.get("name", "Season")
    ui.label(f"{season_name}").classes("text-2xl font-bold text-slate-800")

    @ui.refreshable
    async def _season_actions():
        try:
            status = await run.io_bound(api_client.get_season_status, state.session_id)
        except api_client.APIError:
            return

        phase = status.get("phase", "regular")
        current_week = status.get("current_week", 0)
        total_weeks = status.get("total_weeks", 10)

        next_week = status.get("next_week")
        games_played = status.get("games_played", 0)
        total_games = status.get("total_games", 0)

        with ui.row().classes("w-full gap-3 flex-wrap mb-4"):
            metric_card("Week", f"{current_week}/{total_weeks}")
            metric_card("Phase", phase.replace("_", " ").title())
            if phase == "regular" and total_games > 0:
                metric_card("Games", f"{games_played}/{total_games}")

        if phase == "portal":
            await _render_season_portal(state, _season_actions)

        elif phase == "regular":
            ui.separator().classes("my-4")

            week_label = f"Simulate Week {next_week}" if next_week else "Season Complete"
            with ui.row().classes("gap-3 items-center"):
                week_btn = ui.button(week_label, icon="play_arrow").props("color=primary")
                rest_btn = ui.button("Sim Rest of Season", icon="fast_forward").props("color=secondary outlined")
                engine_switch = ui.switch("Full Engine (Box Scores)", value=state.full_engine).props("dense").tooltip(
                    "Generate detailed play-by-play & drive summaries for all games. Off = fast sim (stats only, no play-by-play)."
                )

                def _toggle_engine(e):
                    state.full_engine = e.value

                engine_switch.on_value_change(_toggle_engine)

            async def _sim_week():
                use_fast = not state.full_engine
                week_btn.disable()
                rest_btn.disable()
                week_btn.text = "Simulating..."
                try:
                    result = await run.io_bound(api_client.simulate_week, state.session_id, None, use_fast)
                    week = result.get("week", "?")
                    games_count = result.get("games_count", 0)
                    engine_label = "full engine" if not use_fast else "fast sim"
                    notify_success(f"Week {week} simulated — {games_count} games ({engine_label})")
                    try:
                        _season_actions.refresh()
                    except RuntimeError:
                        pass
                except api_client.APIError as e:
                    notify_error(f"Simulation failed: {e.detail}")
                    week_btn.enable()
                    rest_btn.enable()
                    week_btn.text = week_label

            async def _sim_rest():
                use_fast = not state.full_engine
                rest_btn.disable()
                week_btn.disable()
                rest_btn.text = "Simulating season..."
                try:
                    result = await run.io_bound(api_client.simulate_rest, state.session_id, use_fast)
                    engine_label = "full engine" if not use_fast else "fast sim"
                    notify_success(f"Regular season complete! ({engine_label})")
                    try:
                        _season_actions.refresh()
                    except RuntimeError:
                        pass
                except api_client.APIError as e:
                    notify_error(f"Simulation failed: {e.detail}")
                    rest_btn.enable()
                    week_btn.enable()
                    rest_btn.text = "Sim Rest of Season"

            week_btn.on_click(_sim_week)
            rest_btn.on_click(_sim_rest)

        elif phase == "bowls_pending":
            bowl_btn = ui.button("Run Bowl Games", icon="stadium").props("color=primary")

            async def _run_bowls():
                bowl_btn.disable()
                bowl_btn.text = "Running bowls..."
                try:
                    await run.io_bound(api_client.run_bowls, state.session_id)
                    notify_success("Bowl games complete!")
                    try:
                        _season_actions.refresh()
                    except RuntimeError:
                        pass
                except api_client.APIError as e:
                    notify_error(f"Bowls failed: {e.detail}")
                    bowl_btn.enable()
                    bowl_btn.text = "Run Bowl Games"

            bowl_btn.on_click(_run_bowls)

        elif phase == "playoffs_pending":
            user_t = state.human_teams[0] if state.human_teams else None

            bowls_data = await _fetch_bowls(state.session_id)
            if bowls_data.get("bowl_results"):
                render_bowl_games(bowls_data, user_team=user_t)
                ui.separator().classes("my-3")

            playoff_btn = ui.button("Run Playoffs", icon="emoji_events").props("color=primary")

            async def _run_playoffs():
                playoff_btn.disable()
                playoff_btn.text = "Running playoffs..."
                try:
                    await run.io_bound(api_client.run_playoffs, state.session_id)
                    notify_success("Playoffs complete!")
                    try:
                        _season_actions.refresh()
                    except RuntimeError:
                        pass
                except api_client.APIError as e:
                    notify_error(f"Playoffs failed: {e.detail}")
                    playoff_btn.enable()
                    playoff_btn.text = "Run Playoffs"

            playoff_btn.on_click(_run_playoffs)

        elif phase in ("playoffs_complete", "bowls_complete", "complete"):
            user_t = state.human_teams[0] if state.human_teams else None

            bowls_data = await _fetch_bowls(state.session_id)
            if bowls_data.get("bowl_results"):
                render_bowl_games(bowls_data, user_team=user_t)
                ui.separator().classes("my-3")

            bracket_data = await _fetch_bracket(state.session_id)
            render_playoff_bracket(bracket_data, user_team=user_t)

            with ui.card().classes("w-full bg-green-50 p-3 rounded mt-3"):
                ui.label("Season Complete! Check the League tab for full standings and awards.").classes("text-sm text-green-600")

            # Dynasty: advance to next year
            if state.mode == "dynasty":
                async def _advance_dynasty():
                    try:
                        await run.io_bound(api_client.dynasty_advance, state.session_id)
                        notify_success("Advanced to next dynasty year!")
                        ui.navigate.to("/")
                    except api_client.APIError as e:
                        notify_error(f"Advance failed: {e.detail}")

                ui.button(
                    "Advance to Next Year", on_click=_advance_dynasty, icon="fast_forward",
                ).props("color=teal size=lg").classes("mt-2")

        try:
            schedule = await run.io_bound(api_client.get_schedule, state.session_id)
            all_games = schedule.get("games", [])
            if all_games:
                completed = [g for g in all_games if g.get("completed")]
                upcoming = [g for g in all_games if not g.get("completed")]

                if completed:
                    recent = completed[-min(10, len(completed)):]
                    with ui.expansion(
                        f"Recent Results ({len(completed)} games played)",
                        icon="history",
                    ).classes("w-full mt-4"):
                        rows = []
                        for g in reversed(recent):
                            rows.append({
                                "Week": g.get("week", ""),
                                "Home": g.get("home_team", ""),
                                "Score": f"{fmt_vb_score(g.get('home_score', 0))} - {fmt_vb_score(g.get('away_score', 0))}",
                                "Away": g.get("away_team", ""),
                            })
                        stat_table(rows)

                if upcoming:
                    with ui.expansion(
                        f"Upcoming Games ({len(upcoming)} remaining)",
                        icon="event",
                    ).classes("w-full mt-2"):
                        rows = []
                        for g in upcoming[:30]:
                            rows.append({
                                "Week": g.get("week", ""),
                                "Home": g.get("home_team", ""),
                                "Away": g.get("away_team", ""),
                                "Conf": "Yes" if g.get("is_conference_game") else "",
                            })
                        stat_table(rows)
        except api_client.APIError:
            pass

    await _season_actions()


