"""DraftyQueenz Standalone Mode — NiceGUI page.

A self-contained sports betting & fantasy experience where the user manages a
DraftyQueenz bankroll while a full CVL season simulates in the background.
Features: predictions/spread betting, fantasy rosters, donations to programs,
bet tracking, and end-of-season/bust screens.
"""

from __future__ import annotations

import random

from nicegui import ui, run

from ui import api_client
from nicegui_app.state import UserState
from nicegui_app.components import metric_card, notify_error, notify_success, notify_warning, notify_info


DARK_BG = "#1a1d23"
CARD_BG = "#242830"
ACCENT = "#00c853"
ACCENT_RED = "#ff1744"
GOLD = "#ffd600"
TEXT_PRIMARY = "#e8eaed"
TEXT_SECONDARY = "#9aa0a6"
BORDER = "#3c4043"


def _betting_card(label: str, value, color: str = ACCENT):
    with ui.card().classes("p-3 min-w-[110px]").style(
        f"background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px;"
    ):
        ui.label(label).classes("text-xs font-semibold tracking-wide").style(f"color: {TEXT_SECONDARY};")
        ui.label(str(value)).classes("text-xl font-bold mt-1").style(f"color: {color};")


def render_dq_setup(state: UserState, shared: dict):
    with ui.column().classes("w-full items-center").style(f"background: {DARK_BG}; min-height: 100vh; padding: 2rem;"):
        ui.label("DRAFTYQUEENZ").classes("text-3xl font-black tracking-widest").style(f"color: {GOLD};")
        ui.label("Sports Betting & Fantasy").classes("text-sm tracking-wide mt-1").style(f"color: {TEXT_SECONDARY};")

        with ui.card().classes("w-full max-w-xl p-6 mt-6").style(
            f"background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 12px;"
        ):
            ui.label("Start a New Season").classes("text-lg font-bold").style(f"color: {TEXT_PRIMARY};")
            ui.label(
                "Place bets on CVL games, build fantasy rosters, donate winnings "
                "to boost programs, and grow your bankroll across the season."
            ).classes("text-sm mt-1").style(f"color: {TEXT_SECONDARY};")

            season_name = ui.input("Season Name", value="2026 DQ Season").classes("w-full mt-4").style(
                f"color: {TEXT_PRIMARY};"
            )

            with ui.row().classes("gap-4 items-end mt-2"):
                ai_seed = ui.number("Seed (0 = random)", value=0, min=0, max=999999).classes("w-48")

                def _reroll():
                    ai_seed.set_value(random.randint(1, 999999))

                ui.button("Re-roll", on_click=_reroll, icon="casino").props("flat text-color=amber")

            ui.separator().classes("my-4").style(f"border-color: {BORDER};")

            with ui.row().classes("gap-3 flex-wrap"):
                _betting_card("Starting Bank", "$10,000", ACCENT)
                _betting_card("Teams", "188", TEXT_PRIMARY)
                _betting_card("Games/Team", "12", TEXT_PRIMARY)
                _betting_card("Season", "~16 Wks", TEXT_PRIMARY)

            ui.separator().classes("my-4").style(f"border-color: {BORDER};")

            async def _create_dq_season():
                if not state.session_id:
                    try:
                        resp = await run.io_bound(api_client.create_session)
                        state.session_id = resp["session_id"]
                    except api_client.APIError as e:
                        notify_error(f"Failed to create session: {e.detail}")
                        return

                create_btn.disable()
                create_btn.text = "Creating season..."

                try:
                    seed_val = int(ai_seed.value or 0)
                    actual_seed = seed_val if seed_val > 0 else random.randint(1, 999999)

                    await run.io_bound(
                        api_client.dq_create_season,
                        state.session_id,
                        name=season_name.value,
                        ai_seed=actual_seed,
                    )

                    state.mode = "dq"
                    state.dq_current_week = 0
                    notify_success("Season created! Place your bets.")
                    ui.navigate.to("/")
                except api_client.APIError as e:
                    notify_error(f"Failed: {e.detail}")
                    create_btn.enable()
                    create_btn.text = "Launch Season"

            create_btn = ui.button(
                "Launch Season", on_click=_create_dq_season, icon="rocket_launch",
            ).props("color=amber text-color=black size=lg").classes("w-full mt-2 font-bold")


async def render_dq_play(state: UserState, shared: dict):
    if not state.session_id:
        ui.label("No active session.").classes("text-gray-400 italic")
        return

    try:
        status = await run.io_bound(api_client.get_season_status, state.session_id)
    except api_client.APIError:
        state.clear_session()
        notify_info("Session expired. Start a new season.")
        return

    try:
        dq_status = await run.io_bound(api_client.dq_status, state.session_id)
    except api_client.APIError:
        dq_status = {}

    current_week = status.get("current_week", 0)
    total_weeks = status.get("total_weeks", 16)
    phase = status.get("phase", "regular")

    bal = dq_status.get("bankroll", 10000)
    tier = dq_status.get("booster_tier", "Sideline Pass")
    roi = dq_status.get("roi", 0)
    peak = dq_status.get("peak_bankroll", bal)

    with ui.column().classes("w-full").style(f"background: {DARK_BG}; min-height: 100vh; padding: 1rem 1.5rem;"):
        with ui.row().classes("w-full items-center justify-between mb-2"):
            ui.label("DRAFTYQUEENZ").classes("text-2xl font-black tracking-widest").style(f"color: {GOLD};")
            with ui.row().classes("gap-2"):
                async def _quit():
                    state.mode = None
                    state.clear_session()
                    ui.navigate.to("/")
                ui.button("Quit", on_click=_quit, icon="logout").props("flat text-color=grey-6 size=sm")

        with ui.row().classes("w-full gap-3 flex-wrap mb-4"):
            bal_color = ACCENT if bal > 0 else ACCENT_RED
            _betting_card("Bankroll", f"${bal:,}", bal_color)
            _betting_card("Week", f"{current_week}/{total_weeks}", TEXT_PRIMARY)
            _betting_card("ROI", f"{roi:+.1f}%", ACCENT if roi >= 0 else ACCENT_RED)
            _betting_card("Peak", f"${peak:,}", GOLD)
            _betting_card("Tier", tier, GOLD)

        if bal <= 0 and current_week > 0:
            await _render_bust_screen(state, dq_status)
            return

        if phase != "regular" or status.get("next_week") is None:
            await _render_season_complete(state, dq_status)
            return

        @ui.refreshable
        async def _dq_week_flow():
            try:
                st = await run.io_bound(api_client.get_season_status, state.session_id)
            except api_client.APIError:
                return

            nxt_wk = st.get("next_week")
            ph = st.get("phase", "regular")
            cur_wk = st.get("current_week", 0)

            try:
                dqs = await run.io_bound(api_client.dq_status, state.session_id)
                balance = dqs.get("bankroll", 0)
            except api_client.APIError:
                balance = 0

            if balance <= 0 and cur_wk > 0:
                await _render_bust_screen(state, dqs or {})
                return

            if ph != "regular" or nxt_wk is None:
                await _render_season_complete(state, dqs or {})
                return

            if cur_wk > 0:
                with ui.expansion(f"Week {cur_wk} Results", icon="assessment").classes("w-full mb-2").style(
                    f"background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px;"
                ):
                    try:
                        resolve_resp = await run.io_bound(api_client.dq_resolve_week, state.session_id, cur_wk)
                        pred_earn = resolve_resp.get("prediction_earnings", 0)
                        fan_earn = resolve_resp.get("fantasy_earnings", 0)
                        jackpot = resolve_resp.get("jackpot_bonus", 0)
                        with ui.row().classes("gap-3 flex-wrap"):
                            _betting_card("Predictions", f"${pred_earn:+,}", ACCENT if pred_earn >= 0 else ACCENT_RED)
                            _betting_card("Fantasy", f"${fan_earn:+,}", ACCENT if fan_earn >= 0 else ACCENT_RED)
                            if jackpot > 0:
                                _betting_card("JACKPOT!", f"${jackpot:,}", GOLD)

                        picks = resolve_resp.get("picks", [])
                        if picks:
                            ui.label("Pick Results").classes("font-semibold mt-2 text-sm").style(f"color: {TEXT_PRIMARY};")
                            for p in picks:
                                icon = "check_circle" if p.get("result") == "win" else "cancel"
                                clr = ACCENT if p.get("result") == "win" else ACCENT_RED
                                with ui.row().classes("items-center gap-1"):
                                    ui.icon(icon, size="xs").style(f"color: {clr};")
                                    ui.label(
                                        f"{p['pick_type'].title()}: {p['selection']} "
                                        f"on {p['matchup']} — ${p['amount']:,}"
                                    ).classes("text-sm").style(f"color: {TEXT_SECONDARY};")
                    except api_client.APIError:
                        ui.label("No results yet.").classes("text-sm").style(f"color: {TEXT_SECONDARY};")

            ui.label(f"Week {nxt_wk} — Place Your Bets").classes("text-lg font-bold mt-2").style(f"color: {TEXT_PRIMARY};")

            try:
                odds_resp = await run.io_bound(api_client.dq_start_week, state.session_id, nxt_wk)
            except api_client.APIError as e:
                notify_warning(f"Could not load week {nxt_wk}: {e.detail}")
                return

            odds_list = odds_resp.get("odds", [])

            with ui.tabs().classes("w-full").style(
                f"background: {CARD_BG}; border-bottom: 2px solid {GOLD};"
            ) as dq_tabs:
                pred_tab = ui.tab("Sportsbook").props("no-caps")
                fantasy_tab = ui.tab("Fantasy").props("no-caps")
                donate_tab = ui.tab("Donate").props("no-caps")
                history_tab = ui.tab("Bet History").props("no-caps")
                advance_tab = ui.tab("Advance").props("no-caps")

            with ui.tab_panels(dq_tabs, value=pred_tab).classes("w-full").style(
                f"background: {DARK_BG};"
            ):
                with ui.tab_panel(pred_tab):
                    await _render_sportsbook(state, state.session_id, nxt_wk, odds_list, balance)

                with ui.tab_panel(fantasy_tab):
                    await _render_fantasy(state, state.session_id, nxt_wk)

                with ui.tab_panel(donate_tab):
                    await _render_donate(state, state.session_id, nxt_wk)

                with ui.tab_panel(history_tab):
                    await _render_bet_history(state, state.session_id)

                with ui.tab_panel(advance_tab):
                    _render_advance(state, nxt_wk, _dq_week_flow)

        await _dq_week_flow()


async def _render_bust_screen(state: UserState, dq_status: dict):
    with ui.card().classes("w-full max-w-lg p-8 mx-auto mt-8").style(
        f"background: {CARD_BG}; border: 2px solid {ACCENT_RED}; border-radius: 12px; text-align: center;"
    ):
        ui.icon("sentiment_very_dissatisfied", size="4rem").style(f"color: {ACCENT_RED};")
        ui.label("YOU'RE BUSTED").classes("text-2xl font-black mt-2").style(f"color: {ACCENT_RED};")
        ui.label("Your bankroll has hit $0. Better luck next season!").classes("text-sm mt-2").style(f"color: {TEXT_SECONDARY};")

        ui.separator().classes("my-4").style(f"border-color: {BORDER};")

        total_wagered = dq_status.get("total_wagered", 0)
        total_earned = dq_status.get("total_earned", 0)
        accuracy = dq_status.get("pick_accuracy", 0)

        with ui.row().classes("gap-3 flex-wrap justify-center"):
            _betting_card("Total Wagered", f"${total_wagered:,}", TEXT_PRIMARY)
            _betting_card("Total Earned", f"${total_earned:,}", TEXT_PRIMARY)
            _betting_card("Accuracy", f"{accuracy:.0f}%", TEXT_PRIMARY)

        ui.separator().classes("my-4").style(f"border-color: {BORDER};")

        async def _new_season():
            state.mode = None
            state.clear_session()
            ui.navigate.to("/")

        ui.button("Start New Season", on_click=_new_season, icon="refresh").props(
            "color=amber text-color=black size=lg"
        ).classes("w-full font-bold")


async def _render_season_complete(state: UserState, dq_status: dict):
    try:
        summary = await run.io_bound(api_client.dq_summary, state.session_id)
    except api_client.APIError:
        summary = {}

    with ui.card().classes("w-full max-w-2xl p-8 mx-auto mt-4").style(
        f"background: {CARD_BG}; border: 2px solid {GOLD}; border-radius: 12px; text-align: center;"
    ):
        ui.icon("emoji_events", size="4rem").style(f"color: {GOLD};")
        ui.label("SEASON COMPLETE").classes("text-2xl font-black mt-2").style(f"color: {GOLD};")

        final_bal = summary.get("bankroll", dq_status.get("bankroll", 0))
        peak = summary.get("peak_bankroll", dq_status.get("peak_bankroll", 0))
        total_earned = summary.get("total_earned", 0)
        total_wagered = summary.get("total_wagered", 0)
        total_donated = summary.get("total_donated", 0)
        accuracy = summary.get("pick_accuracy", 0)
        roi = summary.get("roi", 0)
        tier = summary.get("booster_tier", dq_status.get("booster_tier", ""))

        roi_color = ACCENT if roi >= 0 else ACCENT_RED

        ui.separator().classes("my-4").style(f"border-color: {BORDER};")

        with ui.row().classes("gap-3 flex-wrap justify-center"):
            _betting_card("Final Balance", f"${final_bal:,}", ACCENT if final_bal > 10000 else ACCENT_RED)
            _betting_card("Peak Balance", f"${peak:,}", GOLD)
            _betting_card("Total Earned", f"${total_earned:,}", TEXT_PRIMARY)
            _betting_card("Total Wagered", f"${total_wagered:,}", TEXT_PRIMARY)
            _betting_card("ROI", f"{roi:+.1f}%", roi_color)
            _betting_card("Accuracy", f"{accuracy:.0f}%", TEXT_PRIMARY)
            _betting_card("Donated", f"${total_donated:,}", GOLD)
            _betting_card("Booster Tier", tier, GOLD)

        weeks = summary.get("weeks", [])
        if weeks:
            ui.separator().classes("my-4").style(f"border-color: {BORDER};")
            ui.label("Week-by-Week").classes("text-sm font-bold").style(f"color: {TEXT_PRIMARY};")
            for w in weeks:
                pred_e = w.get("prediction_earnings", 0)
                fan_e = w.get("fantasy_earnings", 0)
                net = pred_e + fan_e
                net_color = ACCENT if net >= 0 else ACCENT_RED
                picks_w = w.get("picks_won", 0)
                picks_m = w.get("picks_made", 0)
                ui.label(
                    f"Wk {w['week']}: {picks_w}/{picks_m} picks | "
                    f"Pred ${pred_e:+,} | Fan ${fan_e:+,} | Net ${net:+,}"
                ).classes("text-xs").style(f"color: {net_color};")

        ui.separator().classes("my-4").style(f"border-color: {BORDER};")

        with ui.row().classes("gap-4 justify-center"):
            async def _new_season():
                state.mode = None
                state.clear_session()
                ui.navigate.to("/")

            ui.button("New Season", on_click=_new_season, icon="refresh").props(
                "color=amber text-color=black"
            ).classes("font-bold")

            async def _back_home():
                state.mode = None
                state.clear_session()
                ui.navigate.to("/")

            ui.button("Main Menu", on_click=_back_home, icon="home").props(
                "flat text-color=grey-6"
            )


async def _render_sportsbook(state, session_id: str, week: int, odds_list: list, balance: int):
    try:
        contest_resp = await run.io_bound(api_client.dq_get_contest, session_id, week)
        existing_picks = contest_resp.get("picks", [])
    except api_client.APIError:
        existing_picks = []

    if existing_picks:
        with ui.card().classes("w-full p-3 mb-3").style(
            f"background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px;"
        ):
            ui.label("Active Bets").classes("font-bold text-sm").style(f"color: {GOLD};")
            for p in existing_picks:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("receipt_long", size="xs").style(f"color: {TEXT_SECONDARY};")
                    ui.label(
                        f"{p['pick_type'].title()}: {p['selection']} on {p['matchup']} — ${p['amount']:,}"
                    ).classes("text-sm").style(f"color: {TEXT_PRIMARY};")

    if not odds_list:
        ui.label("No games available this week.").classes("italic").style(f"color: {TEXT_SECONDARY};")
        return

    ui.label(f"{len(odds_list)} Games").classes("text-sm mb-2").style(f"color: {TEXT_SECONDARY};")

    with ui.card().classes("w-full p-3 mb-3").style(
        f"background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px; max-height: 300px; overflow-y: auto;"
    ):
        ui.label("Lines").classes("font-bold text-sm mb-1").style(f"color: {TEXT_PRIMARY};")
        for i, o in enumerate(odds_list):
            spread_str = f"{o['spread']:+.1f}"
            ou_str = f"{o['over_under']:.1f}"
            away_ctx = o.get("away_ctx", {}) or {}
            home_ctx = o.get("home_ctx", {}) or {}
            away_rec = away_ctx.get("record", "")
            home_rec = home_ctx.get("record", "")
            with ui.row().classes("w-full items-center py-1").style(
                f"border-bottom: 1px solid {BORDER};"
            ):
                ui.label(f"#{i+1}").classes("text-xs w-8").style(f"color: {TEXT_SECONDARY};")
                ui.label(
                    f"{o['away_team']} ({away_rec}) @ {o['home_team']} ({home_rec})"
                ).classes("text-sm flex-1").style(f"color: {TEXT_PRIMARY};")
                ui.label(f"Sprd {spread_str}").classes("text-xs px-2").style(
                    f"color: {GOLD}; background: rgba(255,214,0,0.1); border-radius: 4px; padding: 2px 6px;"
                )
                ui.label(f"O/U {ou_str}").classes("text-xs px-2").style(
                    f"color: {ACCENT}; background: rgba(0,200,83,0.1); border-radius: 4px; padding: 2px 6px;"
                )

    if balance < 250:
        ui.label("Insufficient balance ($250 minimum).").classes("text-sm").style(f"color: {ACCENT_RED};")
        return

    with ui.card().classes("w-full p-4").style(
        f"background: {CARD_BG}; border: 1px solid {GOLD}; border-radius: 8px;"
    ):
        ui.label("Place a Bet").classes("font-bold text-sm mb-2").style(f"color: {GOLD};")

        game_labels = {i: f"#{i+1} {o['away_team']} @ {o['home_team']}" for i, o in enumerate(odds_list)}
        bet_types = {
            "winner": "Moneyline",
            "spread": "Spread",
            "over_under": "Over/Under",
            "chaos": "Chaos Factor",
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
                         on_change=lambda e: bet_state.update(selection=e.value)).props("inline color=amber")

                sel_o = odds_list[bet_state["game_idx"]] if bet_state["game_idx"] < len(odds_list) else {}
                if sel_o:
                    with ui.row().classes("gap-4 text-xs mt-1"):
                        ui.label(f"Spread: {sel_o.get('spread', 0):+.1f}").style(f"color: {TEXT_SECONDARY};")
                        ui.label(f"O/U: {sel_o.get('over_under', 0):.1f}").style(f"color: {TEXT_SECONDARY};")
                        ui.label(f"KP O/U: {sel_o.get('kick_pass_ou', 14.5):.1f}").style(f"color: {TEXT_SECONDARY};")

        ui.select(game_labels, label="Game", value=0,
                  on_change=lambda e: (bet_state.update(game_idx=e.value), _update_picks())
                  ).classes("w-full").style(f"color: {TEXT_PRIMARY};")

        ui.radio(bet_types, value="winner",
                 on_change=lambda e: (bet_state.update(pick_type=e.value), _update_picks())
                 ).props("inline color=amber")

        pick_container

        max_wager = min(25000, balance)
        with ui.row().classes("w-full gap-4 items-end mt-2"):
            ui.slider(min=250, max=max_wager, value=min(500, max_wager), step=250,
                      on_change=lambda e: bet_state.update(amount=int(e.value))).classes("flex-[3]").props("color=amber")
            ui.number("Wager $", min=250, max=max_wager, value=min(500, max_wager), step=250,
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

        ui.button("Place Bet", on_click=_place, icon="casino").props(
            "color=amber text-color=black"
        ).classes("w-full mt-2 font-bold")

        _update_picks()


async def _render_fantasy(state, session_id: str, week: int):
    try:
        roster_resp = await run.io_bound(api_client.dq_get_roster, session_id, week)
        entered = roster_resp.get("entered", False)
    except api_client.APIError:
        entered = False
        roster_resp = {}

    if not entered:
        with ui.card().classes("w-full p-4").style(
            f"background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px;"
        ):
            ui.label("Weekly Fantasy Contest").classes("font-bold text-sm").style(f"color: {TEXT_PRIMARY};")
            ui.label(
                "Entry fee: $2,500 DQ$. Draft a salary-capped roster of real players. "
                "Top scores earn big payouts."
            ).classes("text-sm mt-1").style(f"color: {TEXT_SECONDARY};")

            async def _enter():
                try:
                    await run.io_bound(api_client.dq_enter_fantasy, session_id, week)
                    notify_success("Entered fantasy contest!")
                    ui.navigate.reload()
                except api_client.APIError as e:
                    notify_error(e.detail)

            ui.button("Enter Contest ($2,500)", on_click=_enter, icon="groups").props(
                "color=purple"
            ).classes("mt-2")
        return

    roster = roster_resp.get("roster") or {}
    salary_rem = roster_resp.get("salary_remaining", 15000)

    with ui.card().classes("w-full p-4 mb-3").style(
        f"background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px;"
    ):
        with ui.row().classes("items-center justify-between"):
            ui.label("Your Roster").classes("font-bold text-sm").style(f"color: {TEXT_PRIMARY};")
            ui.label(f"Salary Cap Remaining: ${salary_rem:,}").classes("text-xs").style(f"color: {GOLD};")

        slots_display = {
            "VP": "Viper", "BALL1": "Ball Carrier 1", "BALL2": "Ball Carrier 2",
            "KP": "Keeper", "FLEX": "Flex",
        }

        starters = roster.get("starters", {}) if isinstance(roster, dict) else {}
        for slot, label in slots_display.items():
            player = starters.get(slot) if isinstance(starters, dict) else None
            if player and isinstance(player, dict):
                ui.label(f"  {label}: {player.get('name', '?')} ({player.get('team', '?')}) — ${player.get('salary', 0):,}").classes("text-sm mt-1").style(f"color: {TEXT_PRIMARY};")
            else:
                ui.label(f"  {label}: — Empty —").classes("text-sm mt-1").style(f"color: {TEXT_SECONDARY};")

    try:
        pool_resp = await run.io_bound(api_client.dq_fantasy_pool, session_id, week)
        pool = pool_resp.get("pool", [])
    except api_client.APIError:
        pool = []

    if pool:
        with ui.expansion(f"Player Pool ({len(pool)} available)", icon="people").classes("w-full").style(
            f"background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px;"
        ):
            slot_options = {"VP": "Viper", "BALL1": "Ball 1", "BALL2": "Ball 2", "KP": "Keeper", "FLEX": "Flex"}
            slot_select = ui.select(slot_options, value="VP", label="Set to Slot").classes("w-48")

            for p in pool[:50]:
                with ui.row().classes("items-center gap-2 py-1").style(f"border-bottom: 1px solid {BORDER};"):
                    ui.label(
                        f"{p.get('name', '?')} ({p.get('position', '?')}) — "
                        f"{p.get('team', '?')} | OVR {p.get('overall', 0)} | ${p.get('salary', 0):,}"
                    ).classes("text-sm flex-1").style(f"color: {TEXT_PRIMARY};")

                    async def _set_slot(player=p):
                        try:
                            await run.io_bound(
                                api_client.dq_set_roster_slot,
                                session_id, week, slot_select.value,
                                player.get("player_tag", ""), player.get("team", ""),
                            )
                            notify_success(f"Added {player.get('name', '?')}")
                        except api_client.APIError as e:
                            notify_error(e.detail)

                    ui.button(icon="add", on_click=_set_slot).props("flat round dense size=xs color=amber")


async def _render_donate(state, session_id: str, week: int):
    try:
        dqs = await run.io_bound(api_client.dq_status, session_id)
        balance = dqs.get("bankroll", 0)
        tier = dqs.get("booster_tier", "Sideline Pass")
        tier_desc = dqs.get("booster_tier_desc", "")
        career_donated = dqs.get("career_donated", 0)
        next_tier = dqs.get("next_tier")
    except api_client.APIError:
        balance = 0
        tier = "?"
        tier_desc = ""
        career_donated = 0
        next_tier = None

    try:
        portfolio = await run.io_bound(api_client.dq_portfolio, session_id)
    except api_client.APIError:
        portfolio = {}

    with ui.card().classes("w-full p-4 mb-3").style(
        f"background: {CARD_BG}; border: 1px solid {GOLD}; border-radius: 8px;"
    ):
        ui.label("Booster Program").classes("font-bold text-sm").style(f"color: {GOLD};")
        ui.label(
            "Donate DQ$ to boost a team's recruiting, development, facilities, and more. "
            "Higher career donations unlock booster tiers with prestige benefits."
        ).classes("text-sm mt-1").style(f"color: {TEXT_SECONDARY};")

        with ui.row().classes("gap-3 flex-wrap mt-2"):
            _betting_card("Current Tier", tier, GOLD)
            _betting_card("Career Donated", f"${career_donated:,}", TEXT_PRIMARY)
            _betting_card("Balance", f"${balance:,}", ACCENT)
            if next_tier:
                _betting_card("Next Tier", f"${next_tier['amount_needed']:,} to {next_tier['name']}", TEXT_SECONDARY)

        if tier_desc:
            ui.label(f'"{tier_desc}"').classes("text-xs italic mt-1").style(f"color: {TEXT_SECONDARY};")

    boosts = portfolio.get("boosts", [])
    if boosts:
        with ui.card().classes("w-full p-4 mb-3").style(
            f"background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px;"
        ):
            ui.label("Active Boosts").classes("font-bold text-sm mb-2").style(f"color: {TEXT_PRIMARY};")
            for b in boosts:
                pct = b.get("progress_pct", 0)
                bar_color = ACCENT if pct < 100 else GOLD
                ui.label(f"{b['label']}: {b['current_value']:.1f} / {b['cap']}").classes("text-xs").style(f"color: {TEXT_PRIMARY};")
                ui.linear_progress(value=pct / 100, size="6px").classes("w-full").props(f"color=amber")

    donation_types = portfolio.get("donation_types", {})
    if not donation_types:
        ui.label("No donation options available.").classes("italic text-sm").style(f"color: {TEXT_SECONDARY};")
        return

    if balance < 10000:
        ui.label("Minimum donation is $10,000 DQ$.").classes("text-sm mt-2").style(f"color: {ACCENT_RED};")
        return

    with ui.card().classes("w-full p-4").style(
        f"background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px;"
    ):
        ui.label("Make a Donation").classes("font-bold text-sm mb-2").style(f"color: {TEXT_PRIMARY};")

        dtype_options = {k: f"{v['label']} — {v['description']}" for k, v in donation_types.items()}
        dtype_select = ui.select(dtype_options, value=list(dtype_options.keys())[0], label="Program").classes("w-full")

        try:
            season = await run.io_bound(api_client.get_season_status, session_id)
            team_list = season.get("teams", [])
        except api_client.APIError:
            team_list = []

        target_team = ui.input("Target Team (leave blank for general)", value="").classes("w-full mt-2")

        amount_input = ui.number("Amount (DQ$)", value=10000, min=10000, step=5000,
                                 max=min(balance, 500000)).classes("w-48 mt-2")

        async def _donate():
            try:
                resp = await run.io_bound(
                    api_client.dq_donate, session_id,
                    dtype_select.value, int(amount_input.value or 10000),
                    target_team=target_team.value or "",
                )
                new_bal = resp.get("bankroll", 0)
                new_tier = resp.get("booster_tier", "")
                notify_success(f"Donated! Balance: ${new_bal:,} | Tier: {new_tier}")
            except api_client.APIError as e:
                notify_error(e.detail)

        ui.button("Donate", on_click=_donate, icon="volunteer_activism").props(
            "color=amber text-color=black"
        ).classes("mt-2 font-bold")


async def _render_bet_history(state, session_id: str):
    try:
        history = await run.io_bound(api_client.dq_history, session_id)
    except api_client.APIError:
        history = {}

    picks = history.get("picks", [])
    total_won = history.get("total_won", 0)
    total_lost = history.get("total_lost", 0)
    net = history.get("net", 0)

    with ui.card().classes("w-full p-4 mb-3").style(
        f"background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px;"
    ):
        ui.label("Betting Ledger").classes("font-bold text-sm").style(f"color: {TEXT_PRIMARY};")
        with ui.row().classes("gap-3 flex-wrap mt-2"):
            _betting_card("Total Won", f"${total_won:,}", ACCENT)
            _betting_card("Total Lost", f"${total_lost:,}", ACCENT_RED)
            _betting_card("Net P&L", f"${net:+,}", ACCENT if net >= 0 else ACCENT_RED)
            _betting_card("Bets Placed", str(len(picks)), TEXT_PRIMARY)

    if not picks:
        ui.label("No bets placed yet. Head to the Sportsbook!").classes("text-sm italic").style(f"color: {TEXT_SECONDARY};")
        return

    with ui.card().classes("w-full p-3").style(
        f"background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px; max-height: 400px; overflow-y: auto;"
    ):
        for p in reversed(picks):
            resolved = p.get("resolved", False)
            result = p.get("result", "pending")
            if result == "win":
                icon = "check_circle"
                clr = ACCENT
                result_text = f"+${p.get('payout', 0):,}"
            elif result == "loss":
                icon = "cancel"
                clr = ACCENT_RED
                result_text = f"-${p['amount']:,}"
            else:
                icon = "schedule"
                clr = TEXT_SECONDARY
                result_text = "Pending"

            with ui.row().classes("items-center gap-2 py-1 w-full").style(
                f"border-bottom: 1px solid {BORDER};"
            ):
                ui.icon(icon, size="xs").style(f"color: {clr};")
                ui.label(f"Wk {p['week']}").classes("text-xs w-12").style(f"color: {TEXT_SECONDARY};")
                ui.label(p["pick_type"].title()).classes("text-xs w-20").style(f"color: {GOLD};")
                ui.label(p.get("matchup", "")).classes("text-xs flex-1").style(f"color: {TEXT_PRIMARY};")
                ui.label(f"${p['amount']:,}").classes("text-xs w-16 text-right").style(f"color: {TEXT_PRIMARY};")
                ui.label(result_text).classes("text-xs w-20 text-right font-bold").style(f"color: {clr};")


def _render_advance(state, next_week: int, refresh_fn):
    with ui.card().classes("w-full p-4").style(
        f"background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px;"
    ):
        ui.label("Advance Season").classes("font-bold text-sm").style(f"color: {TEXT_PRIMARY};")
        ui.label(
            f"Done placing bets and managing your roster? "
            f"Simulate Week {next_week} to see results and collect winnings."
        ).classes("text-sm mt-1").style(f"color: {TEXT_SECONDARY};")

        async def _advance():
            advance_btn.disable()
            advance_btn.text = f"Simulating Week {next_week}..."

            try:
                result = await run.io_bound(api_client.dq_advance_week, state.session_id)
                wk = result.get("week", next_week)
                games = result.get("games_count", 0)
                state.dq_current_week = wk
                notify_success(f"Week {wk} done — {games} games simulated!")
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
        ).props("color=amber text-color=black size=lg").classes("w-full mt-3 font-bold")
