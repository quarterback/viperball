"""Pro Leagues spectator dashboard for the NiceGUI Viperball app.

Spectator-only mode: browse standings, stats, box scores, playoffs.
No team management. Users watch seasons unfold and bet via DraftyQueenz.
"""

from __future__ import annotations

from nicegui import ui, run, app
from nicegui_app.components import metric_card, stat_table

from engine.pro_league import ProLeagueSeason, NVL_CONFIG
from engine.draftyqueenz import (
    DraftyQueenzManager, generate_game_odds, GameOdds,
    MIN_BET, MAX_BET, STARTING_BANKROLL, PARLAY_MULTIPLIERS,
    _prob_to_american,
)


_pro_sessions: dict[str, ProLeagueSeason] = {}
_pro_dq_managers: dict[str, DraftyQueenzManager] = {}


def _get_session_and_dq():
    sid = app.storage.user.get("pro_league_session_id")
    if sid and sid in _pro_sessions:
        season = _pro_sessions[sid]
        dq = _pro_dq_managers.get(sid)
        if dq is None:
            dq = DraftyQueenzManager(manager_name="NVL Bettor")
            _pro_dq_managers[sid] = dq
        return season, dq, sid
    if sid and sid not in _pro_sessions:
        app.storage.user["pro_league_session_id"] = None
    return None, None, None


def _create_new_season() -> ProLeagueSeason:
    import uuid
    sid = str(uuid.uuid4())[:8]
    season = ProLeagueSeason(NVL_CONFIG)
    _pro_sessions[sid] = season
    _pro_dq_managers[sid] = DraftyQueenzManager(manager_name="NVL Bettor")
    app.storage.user["pro_league_session_id"] = sid
    return season


async def render_pro_leagues_section(state, shared):
    season, dq_mgr, session_id = _get_session_and_dq()

    if not season:
        ui.label("NVL — National Viperball League").classes("text-2xl font-bold text-slate-800")
        ui.label("Men's professional Viperball. 24 teams, 4 divisions. Spectator mode.").classes("text-sm text-slate-500 mb-4")

        with ui.card().classes("p-6 bg-gradient-to-r from-indigo-50 to-blue-50 max-w-2xl"):
            ui.label("Start a New NVL Season").classes("text-lg font-semibold text-indigo-700 mb-2")
            ui.label("Simulate a full NVL season with 24 franchises across 4 divisions. "
                     "Watch games unfold, browse standings, view box scores, and follow the playoffs.").classes("text-sm text-slate-600 mb-4")

            with ui.row().classes("gap-3 flex-wrap"):
                for div, teams in NVL_CONFIG.divisions.items():
                    with ui.card().classes("p-3 min-w-[180px]").style("border: 1px solid #e2e8f0;"):
                        ui.label(f"{div} Division").classes("text-sm font-bold text-indigo-600 mb-1")
                        for key in teams:
                            from engine.pro_league import DATA_DIR
                            import json
                            fp = DATA_DIR.parent / NVL_CONFIG.teams_dir / f"{key}.json"
                            try:
                                with open(fp) as f:
                                    info = json.load(f)
                                name = info["team_info"]["school_name"]
                            except Exception:
                                name = key
                            ui.label(name).classes("text-xs text-slate-600")

            async def _start():
                season = await run.io_bound(_create_new_season)
                ui.navigate.to("/")

            ui.button("Start NVL Season", icon="play_arrow", on_click=_start).props(
                "color=indigo no-caps"
            ).classes("mt-4")
        return

    with ui.row().classes("w-full gap-4 flex-wrap mb-2"):
        metric_card("DQ$ Balance", f"${dq_mgr.bankroll.balance:,}")
        picks_made = dq_mgr.total_picks_made
        picks_won = dq_mgr.total_picks_won
        pct = (picks_won / picks_made * 100) if picks_made > 0 else 0
        metric_card("Pick Record", f"{picks_won}/{picks_made} ({pct:.0f}%)")
        peak = dq_mgr.peak_bankroll
        roi = ((dq_mgr.bankroll.balance - STARTING_BANKROLL) / STARTING_BANKROLL * 100)
        metric_card("ROI", f"{roi:+.1f}%")

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
            await _render_dashboard(season, dq_mgr)
        with ui.tab_panel(tab_betting):
            _render_betting(season, dq_mgr)
        with ui.tab_panel(tab_stand):
            _render_standings(season)
        with ui.tab_panel(tab_sched):
            _render_schedule(season)
        with ui.tab_panel(tab_stats):
            _render_stats(season)
        with ui.tab_panel(tab_playoffs):
            _render_playoffs(season)
        with ui.tab_panel(tab_teams):
            _render_teams(season)


async def _render_dashboard(season: ProLeagueSeason, dq_mgr: DraftyQueenzManager):
    status = season.get_status()

    ui.label("NVL — National Viperball League").classes("text-2xl font-bold text-slate-800")

    with ui.row().classes("w-full gap-4 flex-wrap mb-4"):
        metric_card("Phase", status["phase"].replace("_", " ").title())
        metric_card("Week", f"{status['current_week']} / {status['total_weeks']}")
        metric_card("Teams", status["team_count"])
        if status["champion"]:
            metric_card("Champion", status["champion_name"])

    @ui.refreshable
    def sim_controls():
        st = season.get_status()

        if st["champion"]:
            with ui.card().classes("p-4 bg-green-50 w-full"):
                ui.label(f"Season Complete — {st['champion_name']} are NVL Champions!").classes(
                    "text-lg font-bold text-green-700"
                )
                async def _new():
                    sid = app.storage.user.get("pro_league_session_id")
                    if sid and sid in _pro_sessions:
                        del _pro_sessions[sid]
                    if sid and sid in _pro_dq_managers:
                        del _pro_dq_managers[sid]
                    app.storage.user["pro_league_session_id"] = None
                    ui.navigate.to("/")
                ui.button("Start New Season", icon="replay", on_click=_new).props("color=green no-caps").classes("mt-2")
            return

        with ui.row().classes("gap-3"):
            if st["phase"] == "regular_season" and st["current_week"] < st["total_weeks"]:
                async def _sim_week():
                    next_week = season.current_week + 1
                    await run.io_bound(season.sim_week)
                    _resolve_dq_bets(season, dq_mgr, next_week)
                    sim_controls.refresh()
                    results_display.refresh()
                ui.button("Sim Week", icon="skip_next", on_click=_sim_week).props("color=indigo no-caps")

                async def _sim_all():
                    start_week = season.current_week + 1
                    await run.io_bound(season.sim_all)
                    for w in range(start_week, season.current_week + 1):
                        _resolve_dq_bets(season, dq_mgr, w)
                    sim_controls.refresh()
                    results_display.refresh()
                ui.button("Sim All", icon="fast_forward", on_click=_sim_all).props("color=blue no-caps")

            if st["phase"] == "regular_season" and st["current_week"] >= st["total_weeks"]:
                async def _start_playoffs():
                    await run.io_bound(season.start_playoffs)
                    sim_controls.refresh()
                    results_display.refresh()
                ui.button("Start Playoffs", icon="emoji_events", on_click=_start_playoffs).props("color=amber no-caps")

            if st["phase"] == "playoffs" and not st["champion"]:
                async def _advance():
                    await run.io_bound(season.advance_playoffs)
                    sim_controls.refresh()
                    results_display.refresh()
                ui.button("Advance Playoffs", icon="skip_next", on_click=_advance).props("color=amber no-caps")

    sim_controls()

    @ui.refreshable
    def results_display():
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

    results_display()


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
    ui.label("DraftyQueenz — NVL Betting").classes("text-xl font-bold text-slate-800 mb-2")

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


def _render_standings(season: ProLeagueSeason):
    standings = season.get_standings()

    ui.label("Division Standings").classes("text-xl font-bold text-slate-800 mb-2")
    ui.label(f"Week {standings['week']} of {standings['total_weeks']}").classes("text-sm text-slate-500 mb-4")

    for div_name, teams in standings["divisions"].items():
        ui.label(f"{div_name} Division").classes("text-lg font-semibold text-indigo-600 mt-4 mb-1")

        columns = [
            {"name": "rank", "label": "#", "field": "rank", "align": "center", "sortable": False},
            {"name": "team", "label": "Team", "field": "team_name", "align": "left", "sortable": True},
            {"name": "record", "label": "W-L", "field": "record", "align": "center", "sortable": True},
            {"name": "pct", "label": "PCT", "field": "pct", "align": "center", "sortable": True},
            {"name": "pf", "label": "PF", "field": "pf", "align": "center", "sortable": True},
            {"name": "pa", "label": "PA", "field": "pa", "align": "center", "sortable": True},
            {"name": "diff", "label": "DIFF", "field": "diff", "align": "center", "sortable": True},
            {"name": "div", "label": "DIV", "field": "div_record", "align": "center"},
            {"name": "streak", "label": "STR", "field": "streak", "align": "center"},
            {"name": "l5", "label": "L5", "field": "last_5", "align": "center"},
        ]

        rows = []
        for i, t in enumerate(teams):
            rows.append({
                "rank": i + 1,
                "team_name": t["team_name"],
                "record": f"{t['wins']}-{t['losses']}",
                "pct": f"{t['pct']:.3f}",
                "pf": t["pf"],
                "pa": t["pa"],
                "diff": f"{t['diff']:+d}",
                "div_record": t["div_record"],
                "streak": t["streak"],
                "last_5": t["last_5"],
            })

        ui.table(columns=columns, rows=rows, row_key="rank").classes(
            "w-full"
        ).props("dense flat bordered")


def _render_schedule(season: ProLeagueSeason):
    schedule = season.get_schedule()

    ui.label("Schedule & Results").classes("text-xl font-bold text-slate-800 mb-2")

    selected_week = {"val": season.current_week if season.current_week > 0 else 1}

    week_options = [{"label": f"Week {w['week']}", "value": w["week"]} for w in schedule["weeks"]]

    @ui.refreshable
    def week_display():
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
        week_display.refresh()

    ui.select(
        options=week_options,
        value=selected_week["val"],
        label="Select Week",
        on_change=_on_week_change,
    ).classes("w-48 mb-4")

    week_display()


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
                            _bio_line("Division", f"NVL {div_name}")
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


def _show_box_score_dialog(box: dict, season: ProLeagueSeason = None):
    with ui.dialog() as dlg, ui.card().classes("p-4 min-w-[600px] max-w-4xl"):
        ui.label(f"{box['away_name']} @ {box['home_name']}").classes("text-lg font-bold text-indigo-600")
        ui.label(f"Final: {int(box['away_score'])} - {int(box['home_score'])}").classes("text-xl font-extrabold mb-2")
        ui.label(f"Weather: {box['weather']}").classes("text-xs text-slate-500 mb-3")

        with ui.tabs().classes("w-full") as bs_tabs:
            tab_team = ui.tab("Team Stats")
            tab_players = ui.tab("Players")

        with ui.tab_panels(bs_tabs, value=tab_team).classes("w-full"):
            with ui.tab_panel(tab_team):
                _render_team_stat_comparison(box)
            with ui.tab_panel(tab_players):
                _render_player_stats_table(box, season)

        ui.button("Close", on_click=dlg.close).props("flat no-caps")
    dlg.open()


def _render_team_stat_comparison(box: dict):
    hs = box["home_stats"]
    aws = box["away_stats"]

    stat_keys = [
        ("total_yards", "Total Yards"), ("rushing_yards", "Rush Yards"),
        ("kick_pass_yards", "Kick Pass Yards"), ("turnovers", "Turnovers"),
        ("penalties", "Penalties"), ("touchdowns", "Touchdowns"),
        ("dk_made", "Drop Kicks Made"), ("pk_made", "Place Kicks Made"),
    ]

    columns = [
        {"name": "stat", "label": "Stat", "field": "stat", "align": "left"},
        {"name": "away", "label": box["away_name"], "field": "away", "align": "center"},
        {"name": "home", "label": box["home_name"], "field": "home", "align": "center"},
    ]

    rows = []
    for key, label in stat_keys:
        rows.append({
            "stat": label,
            "away": hs.get(key, aws.get(key, 0)) if key != "away" else 0,
            "home": hs.get(key, 0),
        })

    fixed_rows = []
    for key, label in stat_keys:
        fixed_rows.append({
            "stat": label,
            "away": str(aws.get(key, 0)),
            "home": str(hs.get(key, 0)),
        })

    ui.table(columns=columns, rows=fixed_rows, row_key="stat").classes("w-full").props("dense flat bordered")


def _render_player_stats_table(box: dict, season: ProLeagueSeason = None):
    for side, label in [("away", box["away_name"]), ("home", box["home_name"])]:
        players = box.get(f"{side}_player_stats", [])
        if not players:
            continue

        team_key = box.get(f"{side}_key", "")
        ui.label(label).classes("text-sm font-bold text-indigo-600 mt-3 mb-1")

        columns = [
            {"name": "name", "label": "Player", "field": "name", "align": "left", "sortable": True},
            {"name": "pos", "label": "Pos", "field": "position", "align": "center"},
            {"name": "rush", "label": "Rush", "field": "rush_yds", "align": "center", "sortable": True},
            {"name": "car", "label": "Car", "field": "carries", "align": "center"},
            {"name": "kp", "label": "KP Yds", "field": "kp_yds", "align": "center", "sortable": True},
            {"name": "td", "label": "TD", "field": "td", "align": "center", "sortable": True},
        ]

        rows = []
        for p in players:
            rush = p.get("rushing_yards", p.get("game_rushing_yards", 0))
            carries = p.get("carries", p.get("game_carries", 0))
            kp = p.get("kick_pass_yards", p.get("game_kick_pass_yards", 0))
            td = p.get("touchdowns", p.get("game_touchdowns", 0))
            if rush > 0 or kp > 0 or td > 0:
                rows.append({
                    "name": p.get("name", "???"),
                    "position": p.get("position", ""),
                    "rush_yds": str(rush),
                    "carries": str(carries),
                    "kp_yds": str(kp),
                    "td": str(td),
                    "team_key": team_key,
                })

        if rows:
            tbl = ui.table(columns=columns, rows=rows, row_key="name").classes("w-full").props("dense flat bordered")
            if season and team_key:
                tbl.add_slot("body-cell-name", '''
                    <q-td :props="props">
                        <a class="text-indigo-600 font-semibold cursor-pointer hover:underline"
                           @click="$parent.$emit('player_click', props.row)">
                            {{ props.row.name }}
                        </a>
                    </q-td>
                ''')
                tbl.on("player_click", lambda e, _s=season: _show_player_card(
                    _s, e.args.get("team_key", ""), e.args.get("name", "")
                ))


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
    ui.label("NVL Playoffs").classes("text-xl font-bold text-slate-800 mb-2")

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
            ui.label(f"NVL Champion: {bracket['champion_name']}").classes(
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
    ui.label("NVL Teams").classes("text-xl font-bold text-slate-800 mb-2")

    team_options = []
    for div_name, keys in NVL_CONFIG.divisions.items():
        for key in keys:
            if key in season.teams:
                team_options.append({"label": f"{season.teams[key].name} ({div_name})", "value": key})

    selected = {"key": None}

    @ui.refreshable
    def team_detail():
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
        team_detail.refresh()

    ui.select(
        options=team_options,
        label="Select Team",
        on_change=_on_team_select,
    ).classes("w-72 mb-4")

    team_detail()
