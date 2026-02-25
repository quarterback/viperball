"""DraftyQueenz UI components for the NiceGUI Viperball app.

Renders pre-sim betting/fantasy and post-sim results inline
within the weekly simulation flow. Migrated from
ui/page_modules/draftyqueenz_ui.py.

Key changes from the Streamlit version:
- st.form replaced with event-handler buttons (NiceGUI has no form concept)
- st.tabs replaced with ui.tabs / ui.tab / ui.tab_panels / ui.tab_panel
- st.columns replaced with ui.row / ui.column
- st.metric replaced with metric_card component
- st.progress replaced with ui.linear_progress
- st.markdown(html, unsafe_allow_html=True) replaced with ui.html
- st.session_state replaced with state parameter (UserState)
- st.rerun() removed (NiceGUI is reactive; containers are re-rendered)
"""

from __future__ import annotations

from nicegui import ui, run

from ui import api_client
from nicegui_app.components import (
    metric_card,
    notify_success,
    notify_error,
    notify_warning,
    notify_info,
)


# ---------------------------------------------------------------------------
# DQ-specific CSS injected once per render cycle
# ---------------------------------------------------------------------------

_DQ_CSS = """
<style>
.dq-odds-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 6px;
    font-size: 0.88rem;
    line-height: 1.45;
}
.dq-odds-card .matchup {
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 2px;
}
.dq-odds-card .lines {
    color: #64748b;
    font-size: 0.82rem;
}
.dq-slip {
    background: #fffbeb;
    border: 1px solid #fbbf24;
    border-radius: 8px;
    padding: 12px 16px;
    margin-top: 8px;
}
.dq-slip .slip-title {
    font-weight: 700;
    color: #92400e;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
}
.dq-slip .slip-row {
    color: #78350f;
    font-size: 0.9rem;
}
.dq-roster-slot {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 12px;
    text-align: center;
    min-height: 68px;
}
.dq-roster-slot .slot-label {
    font-weight: 700;
    font-size: 0.75rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.dq-roster-slot .slot-player {
    font-weight: 600;
    color: #0f172a;
    font-size: 0.9rem;
}
.dq-roster-slot .slot-meta {
    color: #64748b;
    font-size: 0.78rem;
}
.dq-roster-slot.empty {
    border-style: dashed;
    border-color: #cbd5e1;
}
.dq-roster-slot.empty .slot-player {
    color: #94a3b8;
    font-style: italic;
}
.dq-tier-badge {
    display: inline-block;
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
    color: #78350f;
    font-weight: 700;
    font-size: 0.85rem;
    padding: 4px 12px;
    border-radius: 20px;
}
</style>
"""


def _inject_dq_css(state):
    """Inject DQ styling once per page render."""
    if not state.dq_css_injected:
        ui.add_head_html(_DQ_CSS)
        state.dq_css_injected = True


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

async def render_dq_bankroll_banner(state, session_id: str):
    try:
        status = await run.io_bound(api_client.dq_status, session_id)
    except api_client.APIError:
        return

    bal = status.get("bankroll", 0)
    tier = status.get("booster_tier", "Sideline Pass")
    roi = status.get("roi", 0)

    with ui.row().classes("w-full gap-4 flex-wrap"):
        metric_card("DQ$ Balance", f"${bal:,}")
        metric_card("Booster Tier", tier)
        metric_card("ROI", f"{roi:+.1f}%")


async def render_dq_pre_sim(state, session_id: str, next_week: int, key_prefix: str = ""):
    _inject_dq_css(state)

    try:
        start_resp = await run.io_bound(api_client.dq_start_week, session_id, next_week)
    except api_client.APIError as e:
        notify_warning(f"DraftyQueenz unavailable: {e.detail}")
        return

    ui.label(f"DraftyQueenz -- Week {next_week}").classes("text-lg font-bold mt-2")

    with ui.tabs().classes("w-full") as dq_tabs:
        pred_tab = ui.tab("Predictions")
        fantasy_tab = ui.tab("Fantasy")
        donate_tab = ui.tab("Donate")

    with ui.tab_panels(dq_tabs, value=pred_tab).classes("w-full"):
        with ui.tab_panel(pred_tab):
            _render_predictions_tab(state, session_id, next_week, key_prefix)

        with ui.tab_panel(fantasy_tab):
            _render_fantasy_tab(state, session_id, next_week, key_prefix)

        with ui.tab_panel(donate_tab):
            _render_donate_tab(state, session_id, key_prefix)


# ---------------------------------------------------------------------------
# Predictions tab
# ---------------------------------------------------------------------------

def _render_predictions_tab(state, session_id: str, week: int, kp: str):
    try:
        odds_resp = api_client.dq_get_odds(session_id, week)
    except api_client.APIError:
        notify_error("Could not load odds.")
        return

    try:
        status = api_client.dq_status(session_id)
        balance = status.get("bankroll", 0)
    except api_client.APIError:
        balance = 0

    odds_list = odds_resp.get("odds", [])
    if not odds_list:
        notify_info("No games available for predictions this week.")
        return

    # -- Balance bar ----------------------------------------------------------
    ui.label(f"Balance: ${balance:,} DQ$ | Min $250 | Max $25,000").classes(
        "text-sm text-gray-500"
    )

    # -- Existing picks -------------------------------------------------------
    try:
        contest_resp = api_client.dq_get_contest(session_id, week)
        existing_picks = contest_resp.get("picks", [])
        existing_parlays = contest_resp.get("parlays", [])
    except api_client.APIError:
        existing_picks = []
        existing_parlays = []

    if existing_picks or existing_parlays:
        with ui.card().classes("w-full p-4").style(
            "border: 1px solid #e2e8f0; border-radius: 10px;"
        ):
            if existing_picks:
                ui.label("Your Picks").classes("font-bold")
                for p in existing_picks:
                    icon = ""
                    if p.get("result") == "win":
                        icon = " [WIN]"
                    elif p.get("result") == "loss":
                        icon = " [LOSS]"
                    ui.label(
                        f"  {p['pick_type'].title()}: {p['selection']} "
                        f"on {p['matchup']} -- ${p['amount']:,}{icon}"
                    ).classes("text-sm")

            if existing_parlays:
                ui.label("Your Parlays").classes("font-bold mt-2")
                for pl in existing_parlays:
                    legs_str = ", ".join(
                        leg['selection'] for leg in pl.get("legs", [])
                    )
                    ui.label(
                        f"  {len(pl.get('legs', []))}-leg "
                        f"({pl['multiplier']}x): {legs_str} -- ${pl['amount']:,}"
                    ).classes("text-sm")

    # -- Odds board (all games at a glance) -----------------------------------
    ui.label("This Week's Lines").classes("font-bold mt-2")
    _render_odds_board(odds_list)

    # -- Place-a-Bet section --------------------------------------------------
    ui.separator()
    ui.label("Place a Bet").classes("font-bold")

    if balance < 250:
        notify_warning("Insufficient balance to place a bet (need at least $250).")
        return

    game_labels = [
        f"{o['away_team']} @ {o['home_team']}"
        for o in odds_list
    ]
    game_options = {i: label for i, label in enumerate(game_labels)}

    bet_type_labels = {
        "winner": "Winner",
        "spread": "Spread",
        "over_under": "Over / Under",
        "chaos": "Lateral % O/U",
        "kick_pass": "Kick Pass O/U",
    }

    # Mutable state holders for the form inputs
    bet_state = {
        "game_idx": 0,
        "pick_type": "winner",
        "selection": "",
        "amount": min(500, min(25000, balance)),
    }

    # Container for dynamic pick options and odds display
    pick_container = ui.column().classes("w-full")
    odds_display_container = ui.column().classes("w-full")

    def _update_pick_options():
        """Rebuild pick options when game or bet type changes."""
        pick_container.clear()
        odds_display_container.clear()

        sel_odds = odds_list[bet_state["game_idx"]] if bet_state["game_idx"] < len(odds_list) else None

        # Show relevant odds for selected game
        if sel_odds:
            with odds_display_container:
                with ui.row().classes("w-full gap-4"):
                    with ui.column().classes("flex-1"):
                        ui.label(f"Spread: {sel_odds['spread']:+.1f}").classes("font-bold text-sm")
                    with ui.column().classes("flex-1"):
                        ui.label(f"O/U: {sel_odds['over_under']:.1f}").classes("font-bold text-sm")
                    with ui.column().classes("flex-1"):
                        ui.label(
                            f"KP O/U: {sel_odds.get('kick_pass_ou', 14.5):.1f}"
                        ).classes("font-bold text-sm")

        if sel_odds:
            if bet_state["pick_type"] in ("winner", "spread"):
                pick_options = [sel_odds["home_team"], sel_odds["away_team"]]
            else:
                pick_options = ["over", "under"]
        else:
            pick_options = ["over", "under"]

        bet_state["selection"] = pick_options[0] if pick_options else ""

        with pick_container:
            ui.radio(
                pick_options, value=pick_options[0] if pick_options else None,
                on_change=lambda e: bet_state.update(selection=e.value),
            ).props("inline")

    # Game selector
    ui.select(
        game_options, label="Game", value=0,
        on_change=lambda e: (
            bet_state.update(game_idx=e.value),
            _update_pick_options(),
        ),
    ).classes("w-full")

    # Bet type selector
    ui.radio(
        bet_type_labels, value="winner",
        on_change=lambda e: (
            bet_state.update(pick_type=e.value),
            _update_pick_options(),
        ),
    ).props("inline")

    # Dynamic odds display
    odds_display_container

    # Dynamic pick options
    pick_container

    # Wager controls
    max_wager = min(25000, balance)
    default_wager = min(500, max_wager)

    with ui.row().classes("w-full gap-4 items-end"):
        with ui.column().classes("flex-[3]"):
            ui.slider(
                min=250, max=max_wager, value=default_wager, step=250,
                on_change=lambda e: bet_state.update(amount=int(e.value)),
            ).classes("w-full")
            ui.label("Wager (DQ$)").classes("text-xs text-gray-500")
        with ui.column().classes("flex-1"):
            ui.number(
                "Exact", min=250, max=max_wager, value=default_wager, step=250,
                on_change=lambda e: bet_state.update(
                    amount=int(e.value) if e.value is not None else default_wager
                ),
            ).classes("w-full")

    async def _place_bet():
        try:
            resp = api_client.dq_place_pick(
                session_id, week, bet_state["pick_type"],
                bet_state["game_idx"], bet_state["selection"],
                bet_state["amount"],
            )
            notify_success(f"Bet placed! Balance: ${resp['bankroll']:,}")
        except api_client.APIError as e:
            notify_error(e.detail)

    ui.button("Place Bet", on_click=_place_bet, icon="casino").props(
        "color=primary"
    ).classes("w-full mt-2")

    # Initialize pick options
    _update_pick_options()


def _render_odds_board(odds_list: list):
    """Odds board with team context: records, prestige, star players."""
    for o in odds_list:
        spread_str = f"{o['spread']:+.1f}"
        ou_str = f"{o['over_under']:.1f}"
        kp_ou = f"{o.get('kick_pass_ou', 14.5):.1f}"
        away_ml = o.get("away_ml_display", "")
        home_ml = o.get("home_ml_display", "")

        # Team context (record, prestige, star)
        away_ctx = o.get("away_ctx", {})
        home_ctx = o.get("home_ctx", {})
        away_rec = away_ctx.get("record", "")
        home_rec = home_ctx.get("record", "")
        away_prs = away_ctx.get("prestige", 50)
        home_prs = home_ctx.get("prestige", 50)
        away_star = away_ctx.get("star", "")
        away_star_pos = away_ctx.get("star_pos", "")
        home_star = home_ctx.get("star", "")
        home_star_pos = home_ctx.get("star_pos", "")

        # Prestige bar width (0-100 mapped to percentage)
        away_prs_w = min(100, max(5, away_prs))
        home_prs_w = min(100, max(5, home_prs))

        ui.html(
            f'<div class="dq-odds-card">'
            # Matchup header
            f'<div class="matchup" style="font-size:1rem; margin-bottom:6px;">'
            f'{o["away_team"]} <span style="color:#64748b;font-weight:400;">({away_rec})</span>'
            f' &nbsp;@&nbsp; '
            f'{o["home_team"]} <span style="color:#64748b;font-weight:400;">({home_rec})</span>'
            f'</div>'
            # Team details row
            f'<div style="display:flex;gap:16px;margin-bottom:6px;">'
            # Away team
            f'<div style="flex:1;">'
            f'<div style="font-size:0.78rem;color:#94a3b8;text-transform:uppercase;">Away</div>'
            f'<div style="font-size:0.85rem;font-weight:600;">{o["away_team"]}'
            f' <span style="color:#64748b;font-weight:400;">{away_ml}</span></div>'
            f'<div style="font-size:0.78rem;color:#64748b;">Prestige: {away_prs}</div>'
            f'<div style="background:#e2e8f0;border-radius:3px;height:4px;margin:2px 0;">'
            f'<div style="background:#3b82f6;height:4px;border-radius:3px;width:{away_prs_w}%;"></div></div>'
            f'<div style="font-size:0.78rem;color:#475569;">'
            f'Star: {away_star} ({away_star_pos})</div>'
            f'</div>'
            # Home team
            f'<div style="flex:1;">'
            f'<div style="font-size:0.78rem;color:#94a3b8;text-transform:uppercase;">Home</div>'
            f'<div style="font-size:0.85rem;font-weight:600;">{o["home_team"]}'
            f' <span style="color:#64748b;font-weight:400;">{home_ml}</span></div>'
            f'<div style="font-size:0.78rem;color:#64748b;">Prestige: {home_prs}</div>'
            f'<div style="background:#e2e8f0;border-radius:3px;height:4px;margin:2px 0;">'
            f'<div style="background:#3b82f6;height:4px;border-radius:3px;width:{home_prs_w}%;"></div></div>'
            f'<div style="font-size:0.78rem;color:#475569;">'
            f'Star: {home_star} ({home_star_pos})</div>'
            f'</div>'
            f'</div>'
            # Lines row
            f'<div class="lines" style="display:flex;gap:16px;padding-top:4px;border-top:1px solid #e2e8f0;">'
            f'<span>Spread <b>{spread_str}</b></span>'
            f'<span>O/U <b>{ou_str}</b></span>'
            f'<span>Lateral O/U <b>{o.get("chaos_ou", 40):.1f}</b></span>'
            f'<span>KP O/U <b>{kp_ou}</b></span>'
            f'</div>'
            f'</div>'
        )


# ---------------------------------------------------------------------------
# Fantasy tab
# ---------------------------------------------------------------------------

def _render_fantasy_tab(state, session_id: str, week: int, kp: str):
    try:
        roster_resp = api_client.dq_get_roster(session_id, week)
    except api_client.APIError:
        roster_resp = {"entered": False}

    entered = roster_resp.get("entered", False)

    # Container that will be rebuilt after entering / drafting
    fantasy_container = ui.column().classes("w-full")

    def _render_fantasy_content():
        fantasy_container.clear()
        with fantasy_container:
            # Re-fetch roster status
            try:
                current_roster_resp = api_client.dq_get_roster(session_id, week)
            except api_client.APIError:
                current_roster_resp = {"entered": False}

            current_entered = current_roster_resp.get("entered", False)

            if not current_entered:
                with ui.card().classes("w-full p-4").style(
                    "border: 1px solid #e2e8f0; border-radius: 10px;"
                ):
                    ui.label("Weekly Fantasy -- Entry fee: $2,500 DQ$").classes("font-bold")
                    ui.label(
                        "Draft a 5-player salary-capped roster. "
                        "Compete against 9 AI managers."
                    ).classes("text-sm")

                    async def _enter_fantasy():
                        try:
                            api_client.dq_enter_fantasy(session_id, week)
                            notify_success("Entered! Now draft your roster.")
                            _render_fantasy_content()
                        except api_client.APIError as e:
                            notify_error(e.detail)

                    ui.button(
                        "Enter Fantasy ($2,500)", on_click=_enter_fantasy,
                    ).props("color=primary").classes("w-full mt-2")
                return

            roster_data = current_roster_resp.get("roster", {})
            entries = roster_data.get("entries", {})
            total_salary = roster_data.get("total_salary", 0)
            from engine.draftyqueenz import SALARY_CAP as _CAP
            cap_remaining = _CAP - total_salary
            slots_filled = len(entries)

            # -- Salary cap progress bar ------------------------------------------
            cap_pct = min(total_salary / _CAP, 1.0)
            ui.label(
                f"Your Roster ({slots_filled}/5) -- "
                f"${total_salary:,} / ${_CAP:,} used -- ${cap_remaining:,} remaining"
            ).classes("font-bold")
            ui.linear_progress(value=cap_pct).classes("w-full")
            ui.label(f"Salary cap: {cap_pct:.0%}").classes("text-xs text-gray-500")

            # -- Roster card grid (5 slots in a row) ------------------------------
            from engine.draftyqueenz import SLOT_LABELS as _SLOTS
            slot_names = ["VP", "BALL1", "BALL2", "KP", "FLEX"]
            with ui.row().classes("w-full gap-4"):
                for slot in slot_names:
                    entry = entries.get(slot)
                    slot_display = _SLOTS.get(slot, slot)
                    with ui.column().classes("flex-1"):
                        if entry:
                            pos_display = entry.get("position_name", entry["position"])
                            ui.html(
                                f'<div class="dq-roster-slot">'
                                f'<div class="slot-label">{slot_display}</div>'
                                f'<div class="slot-player">{entry["name"]}</div>'
                                f'<div class="slot-meta">{entry["team"]} &middot; '
                                f'{pos_display}<br>${entry["salary"]:,}</div>'
                                f'</div>'
                            )
                        else:
                            ui.html(
                                f'<div class="dq-roster-slot empty">'
                                f'<div class="slot-label">{slot_display}</div>'
                                f'<div class="slot-player">Empty</div>'
                                f'<div class="slot-meta">&mdash;</div>'
                                f'</div>'
                            )

            # -- Draft a Player ---------------------------------------------------
            ui.separator()
            ui.label("Draft a Player").classes("font-bold")

            draft_state = {
                "pos_filter": "All",
                "search": "",
                "selected_idx": None,
                "slot": slot_names[0],
                "pool": [],
            }

            # Fetch the full pool once
            try:
                full_pool_resp = api_client.dq_fantasy_pool(session_id, week)
                draft_state["pool"] = full_pool_resp.get("pool", [])
            except api_client.APIError:
                draft_state["pool"] = []

            # Pool table container
            pool_container = ui.column().classes("w-full")

            def _refresh_pool():
                pool_container.clear()
                pool = draft_state["pool"]

                # Apply position filter
                pos_f = draft_state["pos_filter"]
                if pos_f != "All":
                    pool = [p for p in pool if p["position"] == pos_f]

                # Apply search filter
                search = draft_state["search"].strip().lower()
                if search:
                    pool = [
                        p for p in pool
                        if search in p["name"].lower() or search in p["team"].lower()
                    ]

                with pool_container:
                    if not pool:
                        notify_info("No players match your filters.")
                        return

                    # Build table rows
                    rows = []
                    for i, p in enumerate(pool):
                        rows.append({
                            "idx": i,
                            "name": p["name"],
                            "team": p["team"],
                            "pos": p.get("position_name", p["position"]),
                            "ovr": p["overall"],
                            "salary": f"${p['salary']:,}",
                            "salary_raw": p["salary"],
                            "proj": p["projected"],
                            "depth": p.get("depth", ""),
                            "tag": p["tag"],
                        })

                    columns = [
                        {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
                        {"name": "team", "label": "Team", "field": "team", "align": "left", "sortable": True},
                        {"name": "pos", "label": "Position", "field": "pos", "align": "center"},
                        {"name": "depth", "label": "Role", "field": "depth", "align": "center"},
                        {"name": "ovr", "label": "OVR", "field": "ovr", "align": "center", "sortable": True},
                        {"name": "salary", "label": "Salary", "field": "salary", "align": "right", "sortable": True},
                        {"name": "proj", "label": "Proj Pts", "field": "proj", "align": "right", "sortable": True},
                    ]

                    draft_state["selected_idx"] = None
                    draft_state["_filtered_pool"] = pool

                    table = ui.table(
                        columns=columns, rows=rows, selection="single",
                        row_key="idx",
                    ).classes("w-full").props("dense flat")

                    def _on_select(e):
                        selected = e.selection
                        if selected:
                            draft_state["selected_idx"] = selected[0]["idx"]
                        else:
                            draft_state["selected_idx"] = None

                    table.on("selection", _on_select)

                    # Slot selector and draft button
                    slot_options = {s: _SLOTS.get(s, s) for s in slot_names}
                    with ui.row().classes("w-full gap-4 items-end mt-2"):
                        with ui.column().classes("flex-1"):
                            ui.select(
                                slot_options, label="Roster Slot", value=slot_names[0],
                                on_change=lambda e: draft_state.update(slot=e.value),
                            ).classes("w-full")

                    async def _draft_player():
                        sel_idx = draft_state["selected_idx"]
                        filtered = draft_state.get("_filtered_pool", [])
                        if sel_idx is None or sel_idx >= len(filtered):
                            notify_warning("Select a player from the table first.")
                            return
                        selected = filtered[sel_idx]
                        try:
                            api_client.dq_set_roster_slot(
                                session_id, week, draft_state["slot"],
                                selected["tag"], selected["team"],
                            )
                            notify_success(
                                f"Drafted {selected['name']} to {draft_state['slot']}!"
                            )
                            _render_fantasy_content()
                        except api_client.APIError as e:
                            notify_error(e.detail)

                    ui.button("Draft Selected Player", on_click=_draft_player, icon="person_add").props(
                        "color=primary"
                    ).classes("w-full mt-2")

            # Search + filter controls
            with ui.row().classes("w-full gap-4 items-end"):
                with ui.column().classes("flex-[2]"):
                    ui.input(
                        "Search players or teams...",
                        on_change=lambda e: (
                            draft_state.update(search=e.value or ""),
                            _refresh_pool(),
                        ),
                    ).classes("w-full").props('clearable outlined dense')
                with ui.column().classes("flex-1"):
                    ui.select(
                        {"All": "All Positions", "VP": "Viper", "HB": "Halfback",
                         "ZB": "Zeroback", "WB": "Wingback", "SB": "Slotback",
                         "KP": "Keeper"},
                        label="Position", value="All",
                        on_change=lambda e: (
                            draft_state.update(pos_filter=e.value),
                            _refresh_pool(),
                        ),
                    ).classes("w-full")

            _refresh_pool()

    _render_fantasy_content()


# ---------------------------------------------------------------------------
# Donate tab
# ---------------------------------------------------------------------------

def _render_donate_tab(state, session_id: str, kp: str):
    try:
        portfolio = api_client.dq_portfolio(session_id)
    except api_client.APIError:
        notify_info("DraftyQueenz portfolio unavailable.")
        return

    try:
        status = api_client.dq_status(session_id)
        balance = status.get("bankroll", 0)
    except api_client.APIError:
        balance = 0

    tier = portfolio.get("booster_tier", "Sideline Pass")
    tier_desc = portfolio.get("booster_tier_desc", "")
    career = portfolio.get("career_donated", 0)
    next_tier = portfolio.get("next_tier")

    # -- Tier badge -----------------------------------------------------------
    ui.html(f'<span class="dq-tier-badge">{tier}</span> -- {tier_desc}')
    ui.label(f"Career donated: ${career:,} DQ$").classes("font-bold text-sm")

    if next_tier:
        needed = next_tier["amount_needed"]
        if career + needed > 0:
            tier_progress = career / (career + needed)
        else:
            tier_progress = 0.0
        ui.linear_progress(value=min(tier_progress, 1.0)).classes("w-full")
        ui.label(f"Next: {next_tier['name']} (${needed:,} to go)").classes(
            "text-xs text-gray-500"
        )

    # -- Active boosts with real progress bars --------------------------------
    human_teams = portfolio.get("human_teams", [])
    team_boosts = portfolio.get("team_boosts", {})

    if team_boosts:
        ui.label("Active Boosts by Program").classes("font-bold mt-2")
        for team_name, boosts_list in team_boosts.items():
            active = [b for b in boosts_list if b.get("current_value", 0) > 0]
            if active:
                ui.label(team_name).classes("font-bold text-sm mt-1")
                for b in active:
                    pct = b.get("progress_pct", 0)
                    ui.linear_progress(value=min(pct / 100.0, 1.0)).classes("w-full")
                    ui.label(
                        f"{b['label']}: +{b['current_value']:.1f} ({pct:.0f}%)"
                    ).classes("text-xs text-gray-500")
            else:
                ui.label(f"{team_name} -- no active boosts yet").classes(
                    "font-bold text-sm mt-1"
                )
    elif human_teams:
        notify_info("No donations made yet. Donate your DQ$ winnings to boost your program!")

    # -- Donation section -----------------------------------------------------
    ui.separator()
    ui.label(f"Make a Donation (Balance: ${balance:,} | Min: $10,000)").classes("font-bold")

    if not human_teams:
        notify_warning("No coached team found. Start a season or dynasty to donate.")
        return

    if balance < 10000:
        notify_warning("Insufficient balance to donate (need at least $10,000).")
        return

    donate_state = {
        "target_team": human_teams[0],
        "dtype_idx": 0,
        "amount": min(10000, balance),
    }

    team_options = {t: t for t in human_teams}
    ui.select(
        team_options, label="Donate to Program", value=human_teams[0],
        on_change=lambda e: donate_state.update(target_team=e.value),
    ).classes("w-full")

    dtype_options = portfolio.get("donation_types", {})
    dtype_keys = list(dtype_options.keys()) if dtype_options else []

    if dtype_options:
        dtype_radio_options = {
            i: (
                f"{dtype_options[k]['label']} -- "
                f"{dtype_options[k]['description']}"
            )
            for i, k in enumerate(dtype_keys)
        }
        ui.radio(
            dtype_radio_options, value=0,
            on_change=lambda e: donate_state.update(dtype_idx=e.value),
        )

    min_donate = 1000
    if balance < min_donate:
        notify_info(
            f"You need at least DQ${min_donate:,} to donate. "
            f"Current balance: DQ${balance:,}."
        )
    else:
        max_donate = balance
        default_donate = min(10000, max_donate)
        slider_step = max(1, (max_donate - min_donate) // 100) if max_donate > min_donate else 1

        with ui.row().classes("w-full gap-4 items-end"):
            with ui.column().classes("flex-[3]"):
                ui.slider(
                    min=min_donate, max=max_donate, value=default_donate,
                    step=slider_step,
                    on_change=lambda e: donate_state.update(amount=int(e.value)),
                ).classes("w-full")
                ui.label("Amount (DQ$)").classes("text-xs text-gray-500")
            with ui.column().classes("flex-1"):
                ui.number(
                    "Exact", min=min_donate, max=max_donate,
                    value=default_donate, step=1,
                    on_change=lambda e: donate_state.update(
                        amount=int(e.value) if e.value is not None else default_donate
                    ),
                ).classes("w-full")

        target_label = donate_state["target_team"]

        async def _donate():
            if not dtype_keys or donate_state["amount"] <= 0:
                return
            try:
                resp = api_client.dq_donate(
                    session_id, dtype_keys[donate_state["dtype_idx"]],
                    donate_state["amount"],
                    target_team=donate_state["target_team"],
                )
                notify_success(
                    f"Donated ${donate_state['amount']:,} to {donate_state['target_team']}! "
                    f"Balance: ${resp['bankroll']:,}. Tier: {resp['booster_tier']}"
                )
            except api_client.APIError as e:
                notify_error(e.detail)

        ui.button(
            f"Donate to {target_label}", on_click=_donate, icon="volunteer_activism",
        ).props("color=primary").classes("w-full mt-2")


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

def render_dq_history(state, session_id: str, key_prefix: str = ""):
    try:
        summary = api_client.dq_summary(session_id)
    except api_client.APIError:
        notify_info("DraftyQueenz season history not available yet.")
        return

    weeks = summary.get("weeks", [])
    if not weeks:
        notify_info("No completed weeks yet.")
        return

    ui.label("Season History").classes("text-xl font-semibold mt-2")

    with ui.row().classes("w-full gap-4 flex-wrap"):
        metric_card("Balance", f"${summary.get('bankroll', 0):,}")
        metric_card("Total Earned", f"${summary.get('total_earned', 0):,}")
        metric_card("Accuracy", f"{summary.get('pick_accuracy', 0):.0f}%")
        metric_card("ROI", f"{summary.get('roi', 0):+.1f}%")

    ui.label("Week-by-Week Results:").classes("font-bold mt-2")

    # Build table rows
    history_rows = []
    for w in weeks:
        wk = w.get("week", "?")
        pw = w.get("picks_won", 0)
        pm = w.get("picks_made", 0)
        pred_e = w.get("prediction_earnings", 0)
        fpts = w.get("fantasy_points", 0)
        fan_e = w.get("fantasy_earnings", 0)
        net = pred_e + fan_e
        history_rows.append({
            "Week": str(wk),
            "Picks W/L": f"{pw}/{pm}",
            "Pred $": f"${pred_e:,}",
            "Fantasy Pts": f"{fpts:.1f}",
            "Fantasy $": f"${fan_e:,}",
            "Net": f"${net:,}",
        })

    history_columns = [
        {"name": "Week", "label": "Week", "field": "Week", "align": "left"},
        {"name": "Picks W/L", "label": "Picks W/L", "field": "Picks W/L", "align": "center"},
        {"name": "Pred $", "label": "Pred $", "field": "Pred $", "align": "right"},
        {"name": "Fantasy Pts", "label": "Fantasy Pts", "field": "Fantasy Pts", "align": "right"},
        {"name": "Fantasy $", "label": "Fantasy $", "field": "Fantasy $", "align": "right"},
        {"name": "Net", "label": "Net", "field": "Net", "align": "right"},
    ]
    ui.table(columns=history_columns, rows=history_rows).classes("w-full").props("dense flat")

    # -- Copy/Paste Export text area ------------------------------------------
    clipboard_text = "DraftyQueenz Season Report\n"
    clipboard_text += f"Manager: {summary.get('manager', 'Coach')}\n"
    clipboard_text += (
        f"Balance: ${summary.get('bankroll', 0):,} | "
        f"Earned: ${summary.get('total_earned', 0):,} | "
        f"ROI: {summary.get('roi', 0):+.1f}%\n\n"
    )
    clipboard_text += "Wk  Picks  Pred$    FPts   Fan$    Net\n"
    clipboard_text += "-" * 48 + "\n"
    for w in weeks:
        wk = w.get("week", "?")
        pw = w.get("picks_won", 0)
        pm = w.get("picks_made", 0)
        pred_e = w.get("prediction_earnings", 0)
        fpts = w.get("fantasy_points", 0)
        fan_e = w.get("fantasy_earnings", 0)
        net = pred_e + fan_e
        clipboard_text += (
            f"{wk:<4}{pw}/{pm:<5}${pred_e:<8,}{fpts:<7.1f}"
            f"${fan_e:<7,}${net:,}\n"
        )

    ui.textarea(
        "Copy/Paste Export", value=clipboard_text,
    ).classes("w-full").props("readonly").style("min-height: 200px;")


# ---------------------------------------------------------------------------
# Post-sim results
# ---------------------------------------------------------------------------

async def render_dq_post_sim(state, session_id: str, week: int, key_prefix: str = ""):
    try:
        resolve_resp = await run.io_bound(api_client.dq_resolve_week, session_id, week)
    except api_client.APIError:
        return

    pred_earn = resolve_resp.get("prediction_earnings", 0)
    fan_earn = resolve_resp.get("fantasy_earnings", 0)
    jackpot = resolve_resp.get("jackpot_bonus", 0)
    total = pred_earn + fan_earn + jackpot
    balance = resolve_resp.get("bankroll", 0)

    if total == 0 and not resolve_resp.get("picks") and not resolve_resp.get("fantasy_rank"):
        return

    with ui.expansion(
        f"DraftyQueenz Results -- Week {week}", value=(total > 0),
    ).classes("w-full"):
        with ui.row().classes("w-full gap-4 flex-wrap"):
            metric_card("Predictions", f"${pred_earn:,}")
            metric_card("Fantasy", f"${fan_earn:,}")
            if jackpot > 0:
                metric_card("JACKPOT!", f"${jackpot:,}")
            else:
                metric_card("Jackpot", "--")
            metric_card("Balance", f"${balance:,}")

        picks = resolve_resp.get("picks", [])
        if picks:
            ui.label("Prediction Results:").classes("font-bold mt-2")
            for p in picks:
                icon = (
                    "[WIN]" if p["result"] == "win"
                    else ("[PUSH]" if p["result"] == "push" else "[LOSS]")
                )
                payout_str = (
                    f"+${p['payout']:,}" if p["payout"] > 0 else "$0"
                )
                ui.label(
                    f"  {icon} {p['pick_type'].title()}: {p['selection']} "
                    f"on {p['matchup']} -- {payout_str}"
                ).classes("text-sm")

        parlays = resolve_resp.get("parlays", [])
        if parlays:
            ui.label("Parlay Results:").classes("font-bold mt-2")
            for pl in parlays:
                icon = "[WIN]" if pl["result"] == "win" else "[LOSS]"
                payout = pl.get("payout", 0)
                ui.label(
                    f"  {icon} {len(pl.get('legs', []))}-leg "
                    f"({pl['multiplier']}x) -- "
                    f"{'$' + str(payout) if payout else '$0'}"
                ).classes("text-sm")

        fan_rank = resolve_resp.get("fantasy_rank")
        if fan_rank:
            fan_pts = resolve_resp.get("fantasy_points", 0)
            ui.label(
                f"Fantasy: Finished #{fan_rank} with {fan_pts:.1f} pts"
            ).classes("font-bold mt-2")
            user_roster = resolve_resp.get("user_roster", {})
            entries = user_roster.get("entries", {})
            if entries:
                for slot, e in entries.items():
                    ui.label(
                        f"  {slot}: {e['name']} ({e['team']}) "
                        f"-- {e['points']:.1f} pts"
                    ).classes("text-sm")
