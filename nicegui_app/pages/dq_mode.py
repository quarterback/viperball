"""DraftyQueenz Standalone Mode — NiceGUI page.

A self-contained fantasy/betting experience where the user manages a
DraftyQueenz bankroll while a full CVL season simulates in the background.
No coaching or play-by-play — just predictions, fantasy rosters, and results.
"""

from __future__ import annotations

import random

from nicegui import ui, run

from ui import api_client
from nicegui_app.state import UserState
from nicegui_app.components import metric_card, notify_error, notify_success, notify_warning, notify_info


def render_dq_setup(state: UserState, shared: dict):
    """Render the DQ mode setup screen."""
    ui.label("DraftyQueenz").classes("text-2xl font-bold text-slate-800")
    ui.label(
        "Run a fantasy season — place predictions, build fantasy rosters, "
        "and grow your bankroll while the CVL season simulates automatically."
    ).classes("text-sm text-gray-500 mb-4")

    with ui.card().classes("w-full max-w-2xl p-6"):
        ui.label("Fantasy Season Setup").classes("text-lg font-semibold text-slate-700 mb-2")

        season_name = ui.input("Season Name", value="2026 DQ Fantasy Season").classes("w-full")

        with ui.row().classes("gap-4 items-end mt-2"):
            ai_seed = ui.number("AI Seed (0 = random)", value=0, min=0, max=999999).classes("w-48")

            def _reroll():
                ai_seed.set_value(random.randint(1, 999999))

            ui.button("Re-roll", on_click=_reroll, icon="casino").props("flat")

        ui.separator().classes("my-4")

        ui.label("You start with $100,000 DQ$ to bet and build your fantasy empire.").classes(
            "text-sm text-gray-600"
        )

        with ui.row().classes("gap-4 flex-wrap"):
            metric_card("Starting Balance", "$100,000")
            metric_card("Teams", "188")
            metric_card("Games/Team", "12")
            metric_card("Season Length", "~16 weeks")

        ui.separator().classes("my-4")

        async def _create_dq_season():
            if not state.session_id:
                try:
                    resp = await run.io_bound(api_client.create_session)
                    state.session_id = resp["session_id"]
                except api_client.APIError as e:
                    notify_error(f"Failed to create session: {e.detail}")
                    return

            create_btn.disable()
            create_btn.text = "Creating fantasy season..."

            try:
                seed_val = int(ai_seed.value or 0)
                actual_seed = seed_val if seed_val > 0 else random.randint(1, 999999)

                result = await run.io_bound(
                    api_client.dq_create_season,
                    state.session_id,
                    name=season_name.value,
                    ai_seed=actual_seed,
                )

                state.mode = "dq"
                state.dq_current_week = 0
                notify_success("Fantasy season created! Place your picks for Week 1.")
                ui.navigate.to("/")
            except api_client.APIError as e:
                notify_error(f"Failed to create season: {e.detail}")
                create_btn.enable()
                create_btn.text = "Start Fantasy Season"

        create_btn = ui.button(
            "Start Fantasy Season", on_click=_create_dq_season, icon="casino",
        ).props("color=purple size=lg").classes("w-full mt-2")


async def render_dq_play(state: UserState, shared: dict):
    """Render the active DQ mode UI."""
    if not state.session_id:
        ui.label("No active session.").classes("text-gray-400 italic")
        return

    try:
        status = await run.io_bound(api_client.get_season_status, state.session_id)
    except api_client.APIError:
        state.clear_session()
        notify_info("Session expired. Please start a new fantasy season.")
        return

    try:
        dq_status = await run.io_bound(api_client.dq_status, state.session_id)
    except api_client.APIError:
        dq_status = {}

    season_name = status.get("name", "DQ Fantasy Season")
    current_week = status.get("current_week", 0)
    total_weeks = status.get("total_weeks", 16)
    next_week = status.get("next_week")
    phase = status.get("phase", "regular")

    ui.label(f"{season_name}").classes("text-2xl font-bold text-slate-800")

    bal = dq_status.get("bankroll", 100000)
    tier = dq_status.get("booster_tier", "Sideline Pass")
    roi = dq_status.get("roi", 0)

    with ui.row().classes("w-full gap-3 flex-wrap mb-4"):
        metric_card("Week", f"{current_week}/{total_weeks}")
        metric_card("DQ$ Balance", f"${bal:,}")
        metric_card("Booster Tier", tier)
        metric_card("ROI", f"{roi:+.1f}%")
        metric_card("Phase", phase.replace("_", " ").title())

    @ui.refreshable
    async def _dq_week_flow():
        try:
            st = await run.io_bound(api_client.get_season_status, state.session_id)
        except api_client.APIError:
            return

        cur_wk = st.get("current_week", 0)
        nxt_wk = st.get("next_week")
        ph = st.get("phase", "regular")

        try:
            dqs = await run.io_bound(api_client.dq_status, state.session_id)
            balance = dqs.get("bankroll", 0)
            cur_tier = dqs.get("booster_tier", "Sideline Pass")
            cur_roi = dqs.get("roi", 0)
        except api_client.APIError:
            balance = 0
            cur_tier = "?"
            cur_roi = 0

        with ui.row().classes("w-full gap-3 flex-wrap mb-2"):
            metric_card("Balance", f"${balance:,}")
            metric_card("Tier", cur_tier)

        if ph != "regular" or nxt_wk is None:
            ui.label("Regular season complete!").classes("text-xl font-bold text-green-700 mt-4")

            try:
                summary = await run.io_bound(api_client.dq_summary, state.session_id)
                if summary:
                    with ui.card().classes("w-full p-4 mt-2"):
                        ui.label("Season Summary").classes("text-lg font-bold")
                        with ui.row().classes("gap-4 flex-wrap"):
                            metric_card("Final Balance", f"${summary.get('final_bankroll', 0):,}")
                            metric_card("Total Earned", f"${summary.get('total_earned', 0):,}")
                            metric_card("Total Wagered", f"${summary.get('total_wagered', 0):,}")
                            metric_card("Pick Accuracy", f"{summary.get('pick_accuracy', 0):.0f}%")
            except Exception:
                pass
            return

        if cur_wk > 0:
            with ui.expansion(f"Week {cur_wk} Results", icon="assessment").classes("w-full mb-2"):
                try:
                    resolve_resp = await run.io_bound(api_client.dq_resolve_week, state.session_id, cur_wk)
                    pred_earn = resolve_resp.get("prediction_earnings", 0)
                    fan_earn = resolve_resp.get("fantasy_earnings", 0)
                    jackpot = resolve_resp.get("jackpot_bonus", 0)
                    with ui.row().classes("gap-4 flex-wrap"):
                        metric_card("Predictions", f"${pred_earn:,}")
                        metric_card("Fantasy", f"${fan_earn:,}")
                        if jackpot > 0:
                            metric_card("JACKPOT!", f"${jackpot:,}")

                    picks = resolve_resp.get("picks", [])
                    if picks:
                        ui.label("Pick Results:").classes("font-semibold mt-2")
                        for p in picks:
                            result_icon = ""
                            if p.get("result") == "win":
                                result_icon = " ✓"
                            elif p.get("result") == "loss":
                                result_icon = " ✗"
                            ui.label(
                                f"  {p['pick_type'].title()}: {p['selection']} "
                                f"on {p['matchup']} — ${p['amount']:,}{result_icon}"
                            ).classes("text-sm")
                except api_client.APIError:
                    ui.label("No results yet.").classes("text-sm text-gray-400")

        ui.separator().classes("my-4")

        ui.label(f"Week {nxt_wk} — Place Your Picks").classes("text-lg font-bold text-slate-700")

        try:
            odds_resp = await run.io_bound(api_client.dq_start_week, state.session_id, nxt_wk)
        except api_client.APIError as e:
            notify_warning(f"Could not load week {nxt_wk}: {e.detail}")
            return

        odds_list = odds_resp.get("odds", [])

        with ui.tabs().classes("w-full") as dq_tabs:
            pred_tab = ui.tab("Predictions")
            fantasy_tab = ui.tab("Fantasy")
            donate_tab = ui.tab("Donate")
            advance_tab = ui.tab("Advance Week")

        with ui.tab_panels(dq_tabs, value=pred_tab).classes("w-full"):
            with ui.tab_panel(pred_tab):
                await _render_dq_predictions(state, state.session_id, nxt_wk, odds_list, balance)

            with ui.tab_panel(fantasy_tab):
                await _render_dq_fantasy(state, state.session_id, nxt_wk)

            with ui.tab_panel(donate_tab):
                await _render_dq_donate(state, state.session_id)

            with ui.tab_panel(advance_tab):
                _render_advance_controls(state, nxt_wk, _dq_week_flow)

    await _dq_week_flow()


async def _render_dq_predictions(state, session_id: str, week: int, odds_list: list, balance: int):
    """Predictions/betting tab for standalone DQ."""
    try:
        contest_resp = await run.io_bound(api_client.dq_get_contest, session_id, week)
        existing_picks = contest_resp.get("picks", [])
    except api_client.APIError:
        existing_picks = []

    if existing_picks:
        with ui.card().classes("w-full p-3 mb-2").style("border: 1px solid #e2e8f0;"):
            ui.label("Your Picks This Week").classes("font-bold text-sm")
            for p in existing_picks:
                ui.label(
                    f"  {p['pick_type'].title()}: {p['selection']} on {p['matchup']} — ${p['amount']:,}"
                ).classes("text-sm text-gray-600")

    if not odds_list:
        ui.label("No games available this week.").classes("text-gray-400 italic")
        return

    ui.label(f"{len(odds_list)} games this week").classes("text-sm text-gray-500 mb-2")

    with ui.expansion("This Week's Lines", icon="leaderboard").classes("w-full mb-2"):
        for o in odds_list:
            spread_str = f"{o['spread']:+.1f}"
            ou_str = f"{o['over_under']:.1f}"
            away_ctx = o.get("away_ctx", {})
            home_ctx = o.get("home_ctx", {})
            away_rec = away_ctx.get("record", "")
            home_rec = home_ctx.get("record", "")
            ui.label(
                f"{o['away_team']} ({away_rec}) @ {o['home_team']} ({home_rec}) "
                f"| Spread {spread_str} | O/U {ou_str}"
            ).classes("text-sm py-1 border-b border-gray-100")

    if balance < 250:
        ui.label("Insufficient balance to place bets (need $250+).").classes("text-orange-600 text-sm")
        return

    ui.label("Place a Bet").classes("font-bold mt-2")

    game_labels = {i: f"{o['away_team']} @ {o['home_team']}" for i, o in enumerate(odds_list)}
    bet_type_labels = {
        "winner": "Winner", "spread": "Spread",
        "over_under": "Over/Under", "chaos": "Chaos Factor",
        "kick_pass": "Kick Pass O/U",
    }

    bet_state = {"game_idx": 0, "pick_type": "winner", "selection": "", "amount": min(500, balance)}
    pick_container = ui.column().classes("w-full")

    def _update_picks():
        pick_container.clear()
        sel_odds = odds_list[bet_state["game_idx"]] if bet_state["game_idx"] < len(odds_list) else None
        if sel_odds:
            if bet_state["pick_type"] in ("winner", "spread"):
                options = [sel_odds["home_team"], sel_odds["away_team"]]
            else:
                options = ["over", "under"]
        else:
            options = ["over", "under"]

        bet_state["selection"] = options[0] if options else ""
        with pick_container:
            ui.radio(options, value=options[0] if options else None,
                     on_change=lambda e: bet_state.update(selection=e.value)).props("inline")

            sel_o = odds_list[bet_state["game_idx"]] if bet_state["game_idx"] < len(odds_list) else {}
            if sel_o:
                with ui.row().classes("gap-4 text-sm text-gray-600"):
                    ui.label(f"Spread: {sel_o.get('spread', 0):+.1f}")
                    ui.label(f"O/U: {sel_o.get('over_under', 0):.1f}")
                    ui.label(f"KP O/U: {sel_o.get('kick_pass_ou', 14.5):.1f}")

    ui.select(game_labels, label="Game", value=0,
              on_change=lambda e: (bet_state.update(game_idx=e.value), _update_picks())
              ).classes("w-full")

    ui.radio(bet_type_labels, value="winner",
             on_change=lambda e: (bet_state.update(pick_type=e.value), _update_picks())
             ).props("inline")

    pick_container

    max_wager = min(25000, balance)
    with ui.row().classes("w-full gap-4 items-end"):
        ui.slider(min=250, max=max_wager, value=min(500, max_wager), step=250,
                  on_change=lambda e: bet_state.update(amount=int(e.value))).classes("flex-[3]")
        ui.number("Wager", min=250, max=max_wager, value=min(500, max_wager), step=250,
                  on_change=lambda e: bet_state.update(
                      amount=int(e.value) if e.value is not None else 500
                  )).classes("flex-1")

    async def _place():
        try:
            resp = await run.io_bound(
                api_client.dq_place_pick,
                session_id, week, bet_state["pick_type"],
                bet_state["game_idx"], bet_state["selection"],
                bet_state["amount"],
            )
            notify_success(f"Bet placed! Balance: ${resp['bankroll']:,}")
        except api_client.APIError as e:
            notify_error(e.detail)

    ui.button("Place Bet", on_click=_place, icon="casino").props("color=purple").classes("w-full mt-2")
    _update_picks()


async def _render_dq_fantasy(state, session_id: str, week: int):
    """Fantasy roster tab for standalone DQ."""
    try:
        roster_resp = await run.io_bound(api_client.dq_get_roster, session_id, week)
        entered = True
    except api_client.APIError:
        entered = False
        roster_resp = {}

    if not entered:
        ui.label("Enter the fantasy contest for this week to build a roster.").classes("text-sm text-gray-500")

        async def _enter():
            try:
                await run.io_bound(api_client.dq_enter_fantasy, session_id, week)
                notify_success("Entered fantasy contest!")
                ui.navigate.reload()
            except api_client.APIError as e:
                notify_error(e.detail)

        ui.button("Enter Fantasy Contest", on_click=_enter, icon="groups").props("color=purple")
        return

    roster = roster_resp.get("roster", {})
    ui.label("Your Fantasy Roster").classes("font-bold")

    slots = ["zb", "vp1", "vp2", "hb", "wb", "flex", "dst"]
    slot_labels = {"zb": "Zeroback", "vp1": "Viper 1", "vp2": "Viper 2",
                   "hb": "Halfback", "wb": "Wingback", "flex": "FLEX", "dst": "D/ST"}

    for slot in slots:
        player = roster.get(slot)
        label = slot_labels.get(slot, slot.upper())
        if player:
            ui.label(f"  {label}: {player.get('name', '?')} ({player.get('team', '?')})").classes("text-sm")
        else:
            ui.label(f"  {label}: — Empty —").classes("text-sm text-gray-400")

    try:
        pool_resp = await run.io_bound(api_client.dq_fantasy_pool, session_id, week)
        pool = pool_resp.get("pool", [])
    except api_client.APIError:
        pool = []

    if pool:
        with ui.expansion(f"Player Pool ({len(pool)} players)", icon="people").classes("w-full mt-2"):
            slot_select = ui.select(
                {s: slot_labels[s] for s in slots},
                value="zb", label="Set to Slot",
            ).classes("w-48")

            for p in pool[:50]:
                with ui.row().classes("items-center gap-2 py-1 border-b border-gray-100"):
                    ui.label(f"{p.get('name', '?')} ({p.get('position', '?')}) — {p.get('team', '?')} | OVR {p.get('overall', 0)}").classes("text-sm flex-1")

                    async def _set_slot(player=p):
                        try:
                            await run.io_bound(
                                api_client.dq_set_roster_slot,
                                session_id, week, slot_select.value,
                                player.get("player_tag", ""), player.get("team", ""),
                            )
                            notify_success(f"Set {player.get('name', '?')} to {slot_labels.get(slot_select.value, slot_select.value)}")
                        except api_client.APIError as e:
                            notify_error(e.detail)

                    ui.button(icon="add", on_click=_set_slot).props("flat round dense size=xs")


async def _render_dq_donate(state, session_id: str):
    """Donate tab for standalone DQ."""
    try:
        portfolio = await run.io_bound(api_client.dq_portfolio, session_id)
    except api_client.APIError:
        portfolio = {}

    try:
        dqs = await run.io_bound(api_client.dq_status, session_id)
        balance = dqs.get("bankroll", 0)
    except api_client.APIError:
        balance = 0

    ui.label("Donate DQ$ to boost teams").classes("font-bold")
    ui.label(f"Balance: ${balance:,}").classes("text-sm text-gray-500")

    donation_types = portfolio.get("donation_types", {})
    if not donation_types:
        ui.label("No donation types available.").classes("text-gray-400 italic")
        return

    dtype_options = {k: v.get("label", k) for k, v in donation_types.items()}
    dtype_select = ui.select(dtype_options, value=list(dtype_options.keys())[0] if dtype_options else None,
                             label="Donation Type").classes("w-full")

    amount_input = ui.number("Amount (DQ$)", value=10000, min=1000, step=1000).classes("w-48")

    async def _donate():
        try:
            resp = await run.io_bound(
                api_client.dq_donate, session_id,
                dtype_select.value, int(amount_input.value or 10000),
            )
            notify_success(f"Donated! Balance: ${resp.get('bankroll', 0):,}")
        except api_client.APIError as e:
            notify_error(e.detail)

    ui.button("Donate", on_click=_donate, icon="volunteer_activism").props("color=purple")


def _render_advance_controls(state, next_week: int, refresh_fn):
    """Controls to advance to the next week (simulate games)."""
    ui.label("Advance the Season").classes("font-bold")
    ui.label(
        f"When you're done placing picks and managing your fantasy roster, "
        f"simulate Week {next_week} to see your results."
    ).classes("text-sm text-gray-500 mb-2")

    async def _advance():
        advance_btn.disable()
        advance_btn.text = f"Simulating Week {next_week}..."

        try:
            result = await run.io_bound(api_client.dq_advance_week, state.session_id)
            wk = result.get("week", next_week)
            games = result.get("games_count", 0)
            state.dq_current_week = wk
            notify_success(f"Week {wk} complete — {games} games simulated!")
            try:
                refresh_fn.refresh()
            except RuntimeError:
                ui.navigate.reload()
        except api_client.APIError as e:
            notify_error(f"Simulation failed: {e.detail}")
            advance_btn.enable()
            advance_btn.text = f"Simulate Week {next_week}"

    advance_btn = ui.button(
        f"Simulate Week {next_week}", on_click=_advance, icon="fast_forward",
    ).props("color=primary size=lg").classes("w-full")
