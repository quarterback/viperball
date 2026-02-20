"""DraftyQueenz (Fantasy/Betting) page — NiceGUI version.

Migrated from ui/page_modules/draftyqueenz_ui.py. Provides the fantasy
betting interface with predictions, parlay, roster building, and donations.
"""

from __future__ import annotations

from nicegui import ui

from ui import api_client
from nicegui_app.state import UserState
from nicegui_app.helpers import fmt_vb_score
from nicegui_app.components import metric_card, stat_table, notify_error, notify_info, notify_success


def render_dq_bankroll_banner(state: UserState, session_id: str):
    """Show the DraftyQueenz bankroll banner at the top of sim pages."""
    if not session_id:
        return

    try:
        status = api_client.dq_status(session_id)
    except api_client.APIError:
        return

    bankroll = status.get("bankroll", 0)
    tier = status.get("tier", "fan")
    roi = status.get("roi_pct", 0)

    with ui.row().classes("w-full gap-3 bg-indigo-50 p-3 rounded items-center"):
        ui.label("DraftyQueenz").classes("font-bold text-indigo-700")
        metric_card("Bankroll", f"${bankroll:,}")
        metric_card("Tier", tier.title())
        metric_card("ROI", f"{roi:+.1f}%")


def render_dq_pre_sim(state: UserState, session_id: str, week: int):
    """Show pre-simulation betting UI for a given week."""
    if not session_id:
        return

    try:
        odds = api_client.dq_get_odds(session_id, week)
    except api_client.APIError:
        return

    games = odds.get("games", [])
    if not games:
        return

    with ui.expansion(f"DraftyQueenz - Week {week} Predictions", icon="casino").classes("w-full"):
        for i, game in enumerate(games):
            home = game.get("home", "Home")
            away = game.get("away", "Away")
            spread = game.get("spread", 0)
            over_under = game.get("over_under", 0)

            with ui.card().classes("w-full p-3 mb-2"):
                ui.label(f"{away} at {home}").classes("font-bold text-slate-700")
                with ui.row().classes("gap-4"):
                    ui.label(f"Spread: {home} {spread:+.1f}").classes("text-sm")
                    ui.label(f"O/U: {over_under}").classes("text-sm")

                with ui.row().classes("gap-2"):
                    bet_type = ui.radio(
                        {"spread": "Spread", "over_under": "Over/Under", "moneyline": "Moneyline"},
                        value="spread",
                    ).props("inline dense")

                    amount = ui.number("Wager", value=100, min=10, max=10000, step=10).classes("w-32")

                    def _place_bet(game_idx=i, bt=bet_type, amt=amount, hm=home):
                        try:
                            api_client.dq_place_pick(
                                session_id, week,
                                pick_type=bt.value,
                                game_idx=game_idx,
                                selection=hm,
                                amount=int(amt.value),
                            )
                            notify_success("Bet placed!")
                        except api_client.APIError as e:
                            notify_error(f"Bet failed: {e.detail}")

                    ui.button("Place Bet", on_click=_place_bet, icon="payments").props("dense")


def render_dq_post_sim(state: UserState, session_id: str, week: int):
    """Show post-simulation results for DraftyQueenz."""
    if not session_id:
        return

    try:
        status = api_client.dq_status(session_id)
    except api_client.APIError:
        return

    try:
        portfolio = api_client.dq_portfolio(session_id)
    except api_client.APIError:
        portfolio = {}

    picks = portfolio.get("picks", [])
    week_picks = [p for p in picks if p.get("week") == week]

    if not week_picks:
        return

    with ui.expansion(f"DraftyQueenz - Week {week} Results", icon="assessment").classes("w-full"):
        for pick in week_picks:
            result = pick.get("result", "pending")
            amount = pick.get("amount", 0)
            payout = pick.get("payout", 0)

            color = "text-green-600" if result == "win" else "text-red-600" if result == "loss" else "text-gray-500"
            with ui.row().classes("gap-4 items-center"):
                ui.label(f"{pick.get('pick_type', '')} — {pick.get('selection', '')}").classes("font-semibold")
                ui.label(f"${amount:,}").classes("text-sm")
                ui.label(f"{result.upper()} ({'+' if payout > 0 else ''}{payout:,})").classes(f"font-bold {color}")


def render_dq_history(state: UserState, session_id: str):
    """Show full DraftyQueenz betting history."""
    if not session_id:
        return

    try:
        summary = api_client.dq_summary(session_id)
    except api_client.APIError:
        return

    with ui.expansion("DraftyQueenz History", icon="history").classes("w-full"):
        bankroll = summary.get("bankroll", 0)
        total_wagered = summary.get("total_wagered", 0)
        total_won = summary.get("total_won", 0)
        record = summary.get("record", {})

        with ui.row().classes("w-full gap-3 flex-wrap"):
            metric_card("Final Bankroll", f"${bankroll:,}")
            metric_card("Total Wagered", f"${total_wagered:,}")
            metric_card("Total Won", f"${total_won:,}")
            metric_card("Record", f"{record.get('wins', 0)}-{record.get('losses', 0)}")

        picks = summary.get("all_picks", [])
        if picks:
            rows = []
            for p in picks:
                rows.append({
                    "Week": p.get("week", ""),
                    "Type": p.get("pick_type", ""),
                    "Selection": p.get("selection", ""),
                    "Amount": f"${p.get('amount', 0):,}",
                    "Result": p.get("result", "").upper(),
                    "Payout": f"${p.get('payout', 0):,}",
                })
            stat_table(rows)
