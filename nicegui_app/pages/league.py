"""League section for the NiceGUI Viperball app.

Migrated from ui/page_modules/section_league.py.
Replaces Streamlit widgets with NiceGUI equivalents.
"""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go

from nicegui import ui
from ui import api_client
from engine.season import BOWL_TIERS
from nicegui_app.helpers import fmt_vb_score
from nicegui_app.components import metric_card, stat_table, notify_error, notify_info


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _team_label(name: str, user_team: str | None) -> str:
    if user_team and name == user_team:
        return f">>> {name}"
    return name


def _game_status_label(inj: dict) -> str:
    if inj.get("is_season_ending") or inj.get("tier") == "severe":
        return "OUT FOR SEASON"
    return (inj.get("game_status") or "OUT").upper()


def _tier_display(tier: str) -> str:
    return (tier or "").replace("_", "-").title()


_CATEGORY_LABELS = {
    "on_field_contact": "Contact",
    "on_field_noncontact": "Non-Contact",
    "practice": "Practice",
    "off_field": "Off-Field",
}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_league_section(state, shared):
    """Render the full League page inside the current NiceGUI layout context."""

    session_id = state.session_id
    mode = state.mode

    if not session_id or not mode:
        ui.label("League").classes("text-2xl font-bold text-slate-800")
        with ui.card().classes("bg-blue-50 p-3 rounded"):
            ui.label("No active season found. Start a new season or dynasty from the Play section to view league data.")
        return

    # -- Parallel initial fetch (5 calls → 1 round-trip) -----------------------
    def _safe(fn, default=None):
        try:
            return fn()
        except api_client.APIError:
            return default

    _fetchers = [
        lambda: _safe(lambda: api_client.get_standings(session_id), {}),
        lambda: _safe(lambda: api_client.get_season_status(session_id), {}),
        lambda: _safe(lambda: api_client.get_schedule(session_id, completed_only=True), {}),
        lambda: _safe(lambda: api_client.get_conferences(session_id), {}),
    ]
    if mode == "dynasty":
        _fetchers.append(
            lambda: _safe(lambda: api_client.get_dynasty_status(session_id), {})
        )

    _results = api_client.fetch_parallel(*_fetchers)
    standings_resp = _results[0] or {}
    status = _results[1] or {}
    schedule_resp = _results[2] or {}
    conf_resp = _results[3] or {}
    dyn_status = _results[4] if len(_results) > 4 else {}

    standings = standings_resp.get("standings", [])
    if not standings:
        ui.label("League").classes("text-2xl font-bold text-slate-800")
        with ui.card().classes("bg-blue-50 p-3 rounded"):
            ui.label("No standings data available yet. Simulate some games first.")
        return

    user_team = None
    if mode == "dynasty" and dyn_status:
        user_team = dyn_status.get("coach", {}).get("team")

    champion = status.get("champion")
    if champion:
        with ui.card().classes("bg-green-50 p-3 rounded w-full"):
            ui.label(f"National Champions: {champion}").classes("font-bold text-green-800")

    # -- Completed games and league-wide stats --
    completed_games = schedule_resp.get("games", [])

    total_games = len(completed_games)
    all_scores: list[float] = []
    for g in completed_games:
        all_scores.extend([g.get("home_score") or 0, g.get("away_score") or 0])
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

    conferences = conf_resp.get("conferences", {})

    has_conferences = bool(conferences) and len(conferences) >= 1

    # -- Summary metric cards --
    with ui.row().classes("w-full flex-wrap gap-3"):
        metric_card("Teams", len(standings))
        metric_card("Games", total_games)
        metric_card("Avg Score", f"{avg_score:.1f}")
        if has_conferences:
            metric_card("Conferences", len(conferences))
        else:
            avg_opi = sum(r.get("avg_opi", 0) for r in standings) / len(standings) if standings else 0
            metric_card("Avg OPI", f"{avg_opi:.1f}")
        best = standings[0] if standings else None
        metric_card(
            "Top Team",
            f"{best['team_name']}" if best else "--",
            f"{best['wins']}-{best['losses']}" if best else "",
        )

    # -- Tabs --
    tab_names = ["Standings", "Power Rankings"]
    if has_conferences:
        tab_names.append("Conferences")
    tab_names.extend(["Player Stats", "Team Browser", "Postseason", "Schedule", "Awards & Stats", "Injury Report"])

    with ui.tabs().classes("w-full") as tabs:
        tab_objects = {}
        for name in tab_names:
            tab_objects[name] = ui.tab(name)

    with ui.tab_panels(tabs).classes("w-full"):

        with ui.tab_panel(tab_objects["Standings"]):
            _render_standings(session_id, standings, has_conferences, user_team)

        with ui.tab_panel(tab_objects["Power Rankings"]):
            _render_power_rankings(session_id, standings, user_team)

        if has_conferences:
            with ui.tab_panel(tab_objects["Conferences"]):
                _render_conferences(session_id, conferences, user_team)

        with ui.tab_panel(tab_objects["Player Stats"]):
            _render_player_stats(session_id, standings, conferences, has_conferences)

        with ui.tab_panel(tab_objects["Team Browser"]):
            _render_team_browser(session_id, standings, conferences, has_conferences)

        with ui.tab_panel(tab_objects["Postseason"]):
            _render_postseason(session_id, user_team)

        with ui.tab_panel(tab_objects["Schedule"]):
            _render_schedule(session_id, completed_games, user_team)

        with ui.tab_panel(tab_objects["Awards & Stats"]):
            _render_awards_stats(session_id, standings, user_team)

        with ui.tab_panel(tab_objects["Injury Report"]):
            _render_injury_report(session_id, standings)


# ---------------------------------------------------------------------------
# Standings
# ---------------------------------------------------------------------------

def _render_standings(session_id, standings, has_conferences, user_team):
    standings_data = []
    for i, record in enumerate(standings, 1):
        row = {
            "#": i,
            "Team": _team_label(record["team_name"], user_team),
        }
        if has_conferences:
            row["Conf"] = record.get("conference", "")
            row["Conf W-L"] = f"{record.get('conf_wins', 0)}-{record.get('conf_losses', 0)}"
        row.update({
            "W": record["wins"],
            "L": record["losses"],
            "Win%": f"{record.get('win_percentage', 0):.3f}",
            "PF": fmt_vb_score(record["points_for"]),
            "PA": fmt_vb_score(record["points_against"]),
            "Diff": fmt_vb_score(record.get("point_differential", 0)),
            "OPI": f"{record.get('avg_opi', 0):.1f}",
        })
        standings_data.append(row)
    stat_table(standings_data)


# ---------------------------------------------------------------------------
# Power Rankings
# ---------------------------------------------------------------------------

def _render_power_rankings(session_id, standings, user_team):
    try:
        polls_resp = api_client.get_polls(session_id)
        all_polls = polls_resp.get("polls", [])
    except api_client.APIError:
        all_polls = []

    poll = None

    if all_polls and len(all_polls) > 1:
        max_week = len(all_polls)
        slider = ui.slider(min=1, max=max_week, value=max_week).classes("w-full").props("label-always")
        week_label = ui.label(f"Poll Week: {max_week}")

        # Container that will hold poll data
        poll_container = ui.column().classes("w-full")

        def _update_poll():
            week_val = int(slider.value)
            week_label.set_text(f"Poll Week: {week_val}")
            selected_poll = all_polls[week_val - 1] if week_val <= len(all_polls) else None
            poll_container.clear()
            with poll_container:
                if selected_poll:
                    _render_poll_table(selected_poll, user_team)
                else:
                    ui.label("No rankings available yet.").classes("text-sm text-gray-500")

        slider.on("update:model-value", lambda: _update_poll())
        # Initial render
        with poll_container:
            _render_poll_table(all_polls[-1], user_team)
    elif all_polls:
        _render_poll_table(all_polls[-1], user_team)
    else:
        ui.label("No rankings available yet.").classes("text-sm text-gray-500")

    # Radar comparison
    with ui.expansion("Team Comparison Radar").classes("w-full"):
        default_teams = []
        if len(standings) > 1:
            default_teams = [standings[0]["team_name"], standings[-1]["team_name"]]
        elif standings:
            default_teams = [standings[0]["team_name"]]

        team_options = {r["team_name"]: r["team_name"] for r in standings}
        radar_select = ui.select(
            options=team_options,
            label="Compare Teams",
            value=default_teams,
        ).props("multiple use-chips").classes("w-full")

        radar_container = ui.column().classes("w-full")

        def _update_radar():
            radar_teams = radar_select.value or []
            if isinstance(radar_teams, str):
                radar_teams = [radar_teams]
            radar_container.clear()
            with radar_container:
                if radar_teams:
                    categories = ["OPI", "Territory", "Pressure", "Chaos", "Kicking", "Drive Quality", "Turnover Impact"]
                    fig = go.Figure()
                    for tname in radar_teams:
                        record = next((r for r in standings if r["team_name"] == tname), None)
                        if record:
                            values = [
                                record.get("avg_opi", 0),
                                record.get("avg_territory", 0),
                                record.get("avg_pressure", 0),
                                record.get("avg_chaos", 0),
                                record.get("avg_kicking", 0),
                                record.get("avg_drive_quality", 0) * 10,
                                record.get("avg_turnover_impact", 0),
                            ]
                            fig.add_trace(go.Scatterpolar(
                                r=values + [values[0]],
                                theta=categories + [categories[0]],
                                fill="toself",
                                name=tname,
                            ))
                    fig.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                        title="Team Metrics Comparison",
                        height=450,
                        template="plotly_white",
                    )
                    ui.plotly(fig).classes("w-full")

        radar_select.on("update:model-value", lambda: _update_radar())
        # Initial render
        with radar_container:
            if default_teams:
                # Trigger initial draw
                pass
        _update_radar()


def _render_poll_table(poll, user_team):
    """Render a single poll's rankings as a stat_table."""
    poll_data = []
    rankings = poll.get("rankings", [])
    for r in rankings:
        prev_rank = r.get("prev_rank")
        rank = r.get("rank", 0)
        if prev_rank is not None:
            diff = prev_rank - rank
            if diff > 0:
                movement = f"+{diff}"
            elif diff < 0:
                movement = str(diff)
            else:
                movement = "--"
        else:
            movement = "NEW"
        entry = {
            "#": rank,
            "Team": _team_label(r.get("team_name", ""), user_team),
            "Record": r.get("record", ""),
            "Conf": r.get("conference", ""),
            "Power Index": f"{r.get('power_index', 0):.1f}",
            "Quality Wins": r.get("quality_wins", 0),
            "SOS Rank": r.get("sos_rank", 0),
            "Move": movement,
        }
        if r.get("prestige") is not None:
            entry["Prestige"] = r["prestige"]
        poll_data.append(entry)
    stat_table(poll_data)


# ---------------------------------------------------------------------------
# Conferences
# ---------------------------------------------------------------------------

def _render_conferences(session_id, conferences, user_team):
    try:
        conf_standings_resp = api_client.get_conference_standings(session_id)
        conf_standings_data = conf_standings_resp.get("conference_standings", {})
        champions = conf_standings_resp.get("champions", {})
    except api_client.APIError:
        conf_standings_data = {}
        champions = {}

    sorted_confs = sorted(conferences.keys())
    with ui.tabs().classes("w-full") as conf_tabs:
        conf_tab_objs = {}
        for cn in sorted_confs:
            conf_tab_objs[cn] = ui.tab(cn)

    with ui.tab_panels(conf_tabs).classes("w-full"):
        for conf_name in sorted_confs:
            with ui.tab_panel(conf_tab_objs[conf_name]):
                conf_standings = conf_standings_data.get(conf_name, [])
                if conf_standings:
                    champ_name = champions.get(conf_name, "")
                    if champ_name:
                        ui.label(f"Conference Champion: {champ_name}").classes("text-sm text-gray-500 font-semibold")
                    conf_data = []
                    for i, record in enumerate(conf_standings, 1):
                        conf_data.append({
                            "#": i,
                            "Team": _team_label(record["team_name"], user_team),
                            "Conf": f"{record.get('conf_wins', 0)}-{record.get('conf_losses', 0)}",
                            "Overall": f"{record['wins']}-{record['losses']}",
                            "Win%": f"{record.get('win_percentage', 0):.3f}",
                            "PF": fmt_vb_score(record["points_for"]),
                            "PA": fmt_vb_score(record["points_against"]),
                            "OPI": f"{record.get('avg_opi', 0):.1f}",
                        })
                    stat_table(conf_data)


# ---------------------------------------------------------------------------
# Postseason
# ---------------------------------------------------------------------------

def _render_postseason(session_id, user_team):
    try:
        bracket_resp = api_client.get_playoff_bracket(session_id)
        bracket = bracket_resp.get("bracket", [])
        bracket_champion = bracket_resp.get("champion")
    except api_client.APIError:
        bracket = []
        bracket_champion = None

    if bracket:
        ui.markdown("**Playoff Field**")
        playoff_team_set = set()
        for g in bracket:
            playoff_team_set.add(g.get("home_team", ""))
            playoff_team_set.add(g.get("away_team", ""))

        try:
            standings_resp = api_client.get_standings(session_id)
            standings = standings_resp.get("standings", [])
            playoff_teams = [s for s in standings if s["team_name"] in playoff_team_set]
        except api_client.APIError:
            playoff_teams = []

        if playoff_teams:
            pf_data = []
            for i, t in enumerate(playoff_teams, 1):
                pf_data.append({
                    "Seed": i,
                    "Team": _team_label(t["team_name"], user_team),
                    "Record": f"{t['wins']}-{t['losses']}",
                    "Conf": t.get("conference", ""),
                    "Conf Record": f"{t.get('conf_wins', 0)}-{t.get('conf_losses', 0)}",
                })
            stat_table(pf_data)

        ui.markdown("**Bracket Results**")
        round_info = [
            ("Opening Round", 996),
            ("First Round", 997),
            ("National Quarterfinals", 998),
            ("National Semi-Finals", 999),
        ]
        for label, week in round_info:
            round_games = [g for g in bracket if g.get("week") == week and g.get("completed")]
            if round_games:
                ui.markdown(f"*{label}*")
                for i, game in enumerate(round_games, 1):
                    hs = game.get("home_score") or 0
                    aws = game.get("away_score") or 0
                    home = game.get("home_team", "")
                    away = game.get("away_team", "")
                    winner = home if hs > aws else away
                    loser = away if hs > aws else home
                    w_score = max(hs, aws)
                    l_score = min(hs, aws)
                    prefix = ">>> " if user_team and user_team in (home, away) else ""
                    ui.markdown(
                        f"{prefix}Game {i}: **{winner}** {fmt_vb_score(w_score)} def. "
                        f"{loser} {fmt_vb_score(l_score)}"
                    )

        championship = [g for g in bracket if g.get("week") == 1000 and g.get("completed")]
        if championship:
            game = championship[0]
            hs = game.get("home_score") or 0
            aws = game.get("away_score") or 0
            home = game.get("home_team", "")
            away = game.get("away_team", "")
            winner = home if hs > aws else away
            loser = away if hs > aws else home
            w_score = max(hs, aws)
            l_score = min(hs, aws)
            with ui.card().classes("bg-green-50 p-3 rounded w-full"):
                ui.label(
                    f"NATIONAL CHAMPIONS: {winner} {fmt_vb_score(w_score)} def. "
                    f"{loser} {fmt_vb_score(l_score)}"
                ).classes("font-bold text-green-800")
    else:
        ui.label("No playoffs ran this season.").classes("text-sm text-gray-500")

    # -- Bowl Games --
    try:
        bowls_resp = api_client.get_bowl_results(session_id)
        bowl_results = bowls_resp.get("bowl_results", [])
    except api_client.APIError:
        bowl_results = []

    if bowl_results:
        ui.separator()
        ui.markdown("**Bowl Games**")
        current_tier = 0
        for bowl in bowl_results:
            tier = bowl.get("tier", 0)
            if tier != current_tier:
                current_tier = tier
                tier_label = BOWL_TIERS.get(tier, "Standard")
                ui.markdown(f"*{tier_label} Bowls*")
            g = bowl.get("game", {})
            hs = g.get("home_score") or 0
            aws = g.get("away_score") or 0
            home = g.get("home_team", "")
            away = g.get("away_team", "")
            winner = home if hs > aws else away
            loser = away if hs > aws else home
            w_score = max(hs, aws)
            l_score = min(hs, aws)
            w_rec = bowl.get("team_1_record", "") if winner == home else bowl.get("team_2_record", "")
            l_rec = bowl.get("team_2_record", "") if winner == home else bowl.get("team_1_record", "")
            prefix = ">>> " if user_team and user_team in (home, away) else ""
            ui.markdown(
                f"{prefix}**{bowl.get('name', 'Bowl')}**: **{winner}** ({w_rec}) "
                f"{fmt_vb_score(w_score)} def. {loser} ({l_rec}) {fmt_vb_score(l_score)}"
            )


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

def _render_schedule(session_id, completed_games, user_team):
    # Fetch ALL games (completed + upcoming)
    try:
        all_schedule_resp = api_client.get_schedule(session_id)
        all_reg_games = all_schedule_resp.get("games", [])
    except api_client.APIError:
        all_reg_games = completed_games

    try:
        bracket_resp = api_client.get_playoff_bracket(session_id)
        bracket = bracket_resp.get("bracket", [])
    except api_client.APIError:
        bracket = []

    try:
        bowls_resp = api_client.get_bowl_results(session_id)
        bowl_results = bowls_resp.get("bowl_results", [])
    except api_client.APIError:
        bowl_results = []

    all_game_entries = []
    for g in all_reg_games:
        is_completed = g.get("completed", False)
        is_conf = g.get("is_conference_game", False)
        game_type = "Conference" if is_conf else "Non-Conference"
        status_str = "Played" if is_completed else "Upcoming"
        all_game_entries.append({
            "game": g,
            "phase": "Regular Season",
            "label_prefix": f"Wk {g.get('week', 0)}",
            "sort_key": g.get("week", 0),
            "game_type": game_type,
            "status": status_str,
        })

    if bracket:
        playoff_round_names = {
            996: "Opening Round",
            997: "First Round",
            998: "National Quarterfinals",
            999: "National Semi-Finals",
            1000: "National Championship",
        }
        for g in bracket:
            is_completed = g.get("completed", False)
            round_label = playoff_round_names.get(g.get("week", 0), f"Playoff R{g.get('week', 0)}")
            all_game_entries.append({
                "game": g,
                "phase": "Playoff",
                "label_prefix": round_label,
                "sort_key": 900 + g.get("week", 0),
                "game_type": "Playoff",
                "status": "Played" if is_completed else "Upcoming",
            })

    if bowl_results:
        for i, bowl in enumerate(bowl_results):
            bg = bowl.get("game", {})
            is_completed = bg.get("completed", False)
            all_game_entries.append({
                "game": bg,
                "phase": "Bowl",
                "label_prefix": bowl.get("name", f"Bowl {i + 1}"),
                "sort_key": 800 + i,
                "game_type": "Bowl",
                "status": "Played" if is_completed else "Upcoming",
            })

    all_game_entries.sort(key=lambda e: e["sort_key"])

    all_teams_in_log: set[str] = set()
    all_phases: set[str] = set()
    for entry in all_game_entries:
        g = entry["game"]
        all_teams_in_log.add(g.get("home_team", ""))
        all_teams_in_log.add(g.get("away_team", ""))
        all_phases.add(entry["phase"])

    # -- Filter controls --
    team_options_list = sorted(all_teams_in_log)
    if user_team:
        team_filter_opts = {"__my__": "My Team", "__all__": "All Teams"}
        team_filter_opts.update({t: t for t in team_options_list})
    else:
        team_filter_opts = {"__all__": "All Teams"}
        team_filter_opts.update({t: t for t in team_options_list})

    phase_filter_opts = {"__all__": "All Phases"}
    phase_filter_opts.update({p: p for p in sorted(all_phases)})

    all_weeks = sorted(set(g.get("week", 0) for g in all_reg_games))
    week_filter_opts = {"__all__": "All Weeks"}
    week_filter_opts.update({str(w): f"Week {w}" for w in all_weeks})

    status_filter_opts = {"All": "All", "Upcoming": "Upcoming", "Played": "Played"}

    with ui.row().classes("w-full flex-wrap gap-2"):
        with ui.column().classes("flex-1 min-w-[160px]"):
            filter_team = ui.select(team_filter_opts, label="Filter by Team", value="__all__").classes("w-full")
        with ui.column().classes("flex-1 min-w-[160px]"):
            filter_phase = ui.select(phase_filter_opts, label="Filter by Phase", value="__all__").classes("w-full")
        with ui.column().classes("flex-1 min-w-[160px]"):
            filter_week = ui.select(week_filter_opts, label="Filter by Week", value="__all__").classes("w-full")
        with ui.column().classes("flex-1 min-w-[160px]"):
            filter_status = ui.select(status_filter_opts, label="Status", value="All").classes("w-full")

    schedule_container = ui.column().classes("w-full")

    def _apply_filters():
        ft = filter_team.value
        fp = filter_phase.value
        fw = filter_week.value
        fs = filter_status.value

        filtered_entries = list(all_game_entries)

        if ft == "__my__" and user_team:
            filtered_entries = [
                e for e in filtered_entries
                if e["game"].get("home_team") == user_team or e["game"].get("away_team") == user_team
            ]
        elif ft not in ("__all__", "__my__"):
            filtered_entries = [
                e for e in filtered_entries
                if e["game"].get("home_team") == ft or e["game"].get("away_team") == ft
            ]

        if fp != "__all__":
            filtered_entries = [e for e in filtered_entries if e["phase"] == fp]

        if fw != "__all__":
            try:
                wk_int = int(fw)
                filtered_entries = [
                    e for e in filtered_entries
                    if e["phase"] == "Regular Season" and e["game"].get("week") == wk_int
                ]
            except (ValueError, TypeError):
                pass

        if fs != "All":
            filtered_entries = [e for e in filtered_entries if e["status"] == fs]

        schedule_data = []
        for entry in filtered_entries:
            g = entry["game"]
            is_completed = g.get("completed", False)
            hs = g.get("home_score") or 0
            aws = g.get("away_score") or 0
            home = g.get("home_team", "")
            away = g.get("away_team", "")

            if is_completed:
                winner = home if hs > aws else away
                home_score_str = fmt_vb_score(hs)
                away_score_str = fmt_vb_score(aws)
                winner_str = _team_label(winner, user_team)
            else:
                home_score_str = "--"
                away_score_str = "--"
                winner_str = "--"

            is_rivalry = g.get("is_rivalry_game", False)
            game_type_str = entry.get("game_type", "")
            if is_rivalry:
                game_type_str = f"{game_type_str} (Rivalry)" if game_type_str else "Rivalry"

            schedule_data.append({
                "Week": entry["label_prefix"],
                "Type": game_type_str,
                "Status": entry["status"],
                "Home": _team_label(home, user_team),
                "Away": _team_label(away, user_team),
                "Home Score": home_score_str,
                "Away Score": away_score_str,
                "Winner": winner_str,
            })

        schedule_container.clear()
        with schedule_container:
            if schedule_data:
                stat_table(schedule_data)
            else:
                with ui.card().classes("bg-blue-50 p-3 rounded"):
                    ui.label("No games scheduled yet.")

    filter_team.on("update:model-value", lambda: _apply_filters())
    filter_phase.on("update:model-value", lambda: _apply_filters())
    filter_week.on("update:model-value", lambda: _apply_filters())
    filter_status.on("update:model-value", lambda: _apply_filters())

    # Initial render
    _apply_filters()


# ---------------------------------------------------------------------------
# Player Stats
# ---------------------------------------------------------------------------

def _render_player_stats(session_id, standings, conferences, has_conferences):
    ui.label("Individual Player Statistics").classes("text-lg font-semibold text-slate-700")

    # -- Filters --
    conf_options: dict = {}
    if has_conferences:
        conf_options = {"__all__": "All Conferences"}
        conf_options.update({c: c for c in sorted(conferences.keys())})
    else:
        conf_options = {"__all__": "All"}

    team_names = sorted(r["team_name"] for r in standings)
    team_options = {"__all__": "All Teams"}
    team_options.update({t: t for t in team_names})

    pos_list = ["All Positions", "HB", "WB", "SB", "ZB", "VP", "LB", "CB", "LA", "KP", "ED", "BK"]
    pos_options = {p: p for p in pos_list}

    with ui.row().classes("w-full flex-wrap gap-2"):
        with ui.column().classes("flex-1 min-w-[160px]"):
            sel_conf = ui.select(conf_options, label="Conference", value="__all__").classes("w-full")
        with ui.column().classes("flex-1 min-w-[160px]"):
            sel_team = ui.select(team_options, label="Team", value="__all__").classes("w-full")
        with ui.column().classes("flex-1 min-w-[160px]"):
            sel_pos = ui.select(pos_options, label="Position", value="All Positions").classes("w-full")

    min_touches_slider = ui.slider(min=0, max=50, value=1).classes("w-full")
    min_touches_label = ui.label("Minimum touches: 1")

    def _update_label():
        min_touches_label.set_text(f"Minimum touches: {int(min_touches_slider.value)}")

    min_touches_slider.on("update:model-value", lambda: _update_label())

    stats_container = ui.column().classes("w-full")

    def _load_player_stats():
        conf_param = sel_conf.value if sel_conf.value != "__all__" else None
        team_param = sel_team.value if sel_team.value != "__all__" else None
        pos_param = sel_pos.value if sel_pos.value != "All Positions" else None
        min_t = int(min_touches_slider.value)

        try:
            resp = api_client.get_player_stats(
                session_id,
                conference=conf_param,
                team=team_param,
                position=pos_param,
                min_touches=min_t,
            )
            players = resp.get("players", [])
        except api_client.APIError:
            stats_container.clear()
            with stats_container:
                with ui.card().classes("bg-yellow-50 p-3 rounded"):
                    ui.label("Could not load player stats. Simulate some games first.")
            return

        stats_container.clear()
        with stats_container:
            if not players:
                with ui.card().classes("bg-blue-50 p-3 rounded"):
                    ui.label("No player stats available. Simulate some games to see individual statistics.")
                return

            ui.label(f"Showing {len(players)} players").classes("text-sm text-gray-500")

            with ui.tabs().classes("w-full") as stat_tabs:
                rush_tab = ui.tab("Rushing & Scoring")
                lat_tab = ui.tab("Lateral Game")
                kp_tab = ui.tab("Kick Pass")
                kick_tab = ui.tab("Kicking")
                def_tab = ui.tab("Defense")
                ret_tab = ui.tab("Returns & Special Teams")

            with ui.tab_panels(stat_tabs).classes("w-full"):

                # -- Rushing & Scoring --
                with ui.tab_panel(rush_tab):
                    rush_data = []
                    for p in sorted(players, key=lambda x: x["yards"], reverse=True)[:100]:
                        rush_data.append({
                            "Player": p["name"],
                            "Team": p["team"],
                            "Pos": p["tag"].split(" ")[0] if " " in p["tag"] else p["tag"][:2],
                            "GP": p["games_played"],
                            "Touches": p["touches"],
                            "Rush Yds": p["rushing_yards"],
                            "Lat Yds": p["lateral_yards"],
                            "Total Yds": p["yards"],
                            "Yds/Touch": p["yards_per_touch"],
                            "TDs": p["tds"],
                            "Fumbles": p["fumbles"],
                        })
                    if rush_data:
                        stat_table(rush_data)

                # -- Lateral Game --
                with ui.tab_panel(lat_tab):
                    lat_data = []
                    lat_sorted = sorted(players, key=lambda x: x["lateral_yards"] + x["lateral_assists"] * 5, reverse=True)
                    for p in lat_sorted[:100]:
                        if p["laterals_thrown"] > 0 or p["lateral_receptions"] > 0 or p["lateral_assists"] > 0:
                            lat_data.append({
                                "Player": p["name"],
                                "Team": p["team"],
                                "Pos": p["tag"].split(" ")[0] if " " in p["tag"] else p["tag"][:2],
                                "GP": p["games_played"],
                                "Lat Thrown": p["laterals_thrown"],
                                "Lat Rec": p["lateral_receptions"],
                                "Lat Assists": p["lateral_assists"],
                                "Lat Yds": p["lateral_yards"],
                                "Lat TDs": p["lateral_tds"],
                            })
                    if lat_data:
                        stat_table(lat_data)
                    else:
                        ui.label("No lateral stats available yet.").classes("text-sm text-gray-500")

                # -- Kick Pass --
                with ui.tab_panel(kp_tab):
                    kp_data = []
                    kp_sorted = sorted(players, key=lambda x: x.get("kick_pass_yards", 0) + x.get("kick_pass_receptions", 0) * 5, reverse=True)
                    for p in kp_sorted[:100]:
                        kpt = p.get("kick_passes_thrown", 0)
                        kpr = p.get("kick_pass_receptions", 0)
                        kpi = p.get("kick_pass_ints", 0)
                        if kpt > 0 or kpr > 0 or kpi > 0:
                            kpc = p.get("kick_passes_completed", 0)
                            kp_data.append({
                                "Player": p["name"],
                                "Team": p["team"],
                                "Pos": p["tag"].split(" ")[0] if " " in p["tag"] else p["tag"][:2],
                                "GP": p["games_played"],
                                "KP Att": kpt,
                                "KP Comp": kpc,
                                "KP %": f"{round(kpc / max(1, kpt) * 100, 1):.1f}%" if kpt > 0 else "--",
                                "KP Yds": p.get("kick_pass_yards", 0),
                                "KP TD": p.get("kick_pass_tds", 0),
                                "KP INT": p.get("kick_pass_interceptions_thrown", 0),
                                "KP Rec": kpr,
                                "Def KP INT": kpi,
                            })
                    if kp_data:
                        stat_table(kp_data)
                    else:
                        ui.label("No kick pass stats available yet.").classes("text-sm text-gray-500")

                # -- Kicking --
                with ui.tab_panel(kick_tab):
                    kick_data = []
                    kick_sorted = sorted(players, key=lambda x: x["kick_att"], reverse=True)
                    for p in kick_sorted[:100]:
                        if p["kick_att"] > 0:
                            kick_data.append({
                                "Player": p["name"],
                                "Team": p["team"],
                                "Pos": p["tag"].split(" ")[0] if " " in p["tag"] else p["tag"][:2],
                                "GP": p["games_played"],
                                "FG Att": p.get("pk_att", 0),
                                "FG Made": p.get("pk_made", 0),
                                "FG %": f"{p.get('pk_pct', 0):.1f}%",
                                "DK Att": p.get("dk_att", 0),
                                "DK Made": p.get("dk_made", 0),
                                "DK %": f"{p.get('dk_pct', 0):.1f}%",
                                "Total Att": p["kick_att"],
                                "Total Made": p["kick_made"],
                                "Deflections": p["kick_deflections"],
                            })
                    if kick_data:
                        stat_table(kick_data)
                    else:
                        ui.label("No kicking stats available yet.").classes("text-sm text-gray-500")

                # -- Defense --
                with ui.tab_panel(def_tab):
                    def_data = []
                    def_sorted = sorted(players, key=lambda x: x.get("tackles", 0), reverse=True)
                    for p in def_sorted[:100]:
                        tkl = p.get("tackles", 0)
                        tfl = p.get("tfl", 0)
                        sacks = p.get("sacks", 0)
                        hurries = p.get("hurries", 0)
                        if tkl > 0 or sacks > 0 or hurries > 0:
                            def_data.append({
                                "Player": p["name"],
                                "Team": p["team"],
                                "Pos": p["tag"].split(" ")[0] if " " in p["tag"] else p["tag"][:2],
                                "GP": p["games_played"],
                                "Tackles": tkl,
                                "TFL": tfl,
                                "Sacks": sacks,
                                "Hurries": hurries,
                                "Tkl/G": round(tkl / max(1, p["games_played"]), 1),
                            })
                    if def_data:
                        stat_table(def_data)
                    else:
                        ui.label("No defensive stats available yet.").classes("text-sm text-gray-500")

                # -- Returns & Special Teams --
                with ui.tab_panel(ret_tab):
                    ret_data = []
                    ret_sorted = sorted(players, key=lambda x: x["total_return_yards"], reverse=True)
                    for p in ret_sorted[:100]:
                        if p["kick_returns"] > 0 or p["punt_returns"] > 0 or p["st_tackles"] > 0:
                            ret_data.append({
                                "Player": p["name"],
                                "Team": p["team"],
                                "Pos": p["tag"].split(" ")[0] if " " in p["tag"] else p["tag"][:2],
                                "GP": p["games_played"],
                                "KR": p["kick_returns"],
                                "KR Yds": p["kick_return_yards"],
                                "KR TDs": p["kick_return_tds"],
                                "PR": p["punt_returns"],
                                "PR Yds": p["punt_return_yards"],
                                "PR TDs": p["punt_return_tds"],
                                "Muffs": p["muffs"],
                                "ST Tackles": p["st_tackles"],
                                "Coverage": p["coverage_snaps"],
                                "Keeper Tackles": p["keeper_tackles"],
                                "Keeper Bells": p["keeper_bells"],
                            })
                    if ret_data:
                        stat_table(ret_data)
                    else:
                        ui.label("No return/special teams stats available yet.").classes("text-sm text-gray-500")

            # -- Stat Leaders Summary --
            with ui.expansion("Stat Leaders Summary").classes("w-full"):
                if players:
                    leaders = [
                        ("Rushing Yards Leader", max(players, key=lambda x: x["rushing_yards"]), "rushing_yards"),
                        ("Total Yards Leader", max(players, key=lambda x: x["yards"]), "yards"),
                        ("Touchdown Leader", max(players, key=lambda x: x["tds"]), "tds"),
                        ("Tackle Leader", max(players, key=lambda x: x.get("tackles", 0)), "tackles"),
                        ("Lateral Yards Leader", max(players, key=lambda x: x["lateral_yards"]), "lateral_yards"),
                        ("Return Yards Leader", max(players, key=lambda x: x["total_return_yards"]), "total_return_yards"),
                    ]
                    with ui.row().classes("w-full flex-wrap gap-3"):
                        for label_text, player, stat_key in leaders:
                            metric_card(label_text, player["name"], f"{player['team']} -- {player[stat_key]}")

    # Wire up the Load button
    load_btn = ui.button("Load Player Stats", on_click=_load_player_stats, icon="refresh").classes("mt-2")
    # Auto-load on first render
    _load_player_stats()


# ---------------------------------------------------------------------------
# Team Browser
# ---------------------------------------------------------------------------

def _render_team_browser(session_id, standings, conferences, has_conferences):
    ui.label("Team Browser").classes("text-lg font-semibold text-slate-700")
    ui.label("Browse any team's roster, view individual player cards with full attributes and season stats").classes("text-sm text-gray-500")

    browse_conf_val = "__all__"
    if has_conferences:
        conf_opts = {"__all__": "All Conferences"}
        conf_opts.update({c: c for c in sorted(conferences.keys())})
    else:
        conf_opts = {"__all__": "All Conferences"}

    all_team_names = sorted(r["team_name"] for r in standings)
    team_opts = {t: t for t in all_team_names}

    with ui.row().classes("w-full gap-2"):
        with ui.column().classes("flex-1"):
            if has_conferences:
                browse_conf = ui.select(conf_opts, label="Conference", value="__all__").classes("w-full")
            else:
                browse_conf = None
        with ui.column().classes("flex-1"):
            browse_team = ui.select(team_opts, label="Select Team", value=all_team_names[0] if all_team_names else None).classes("w-full")

    # Update team options when conference changes
    if has_conferences and browse_conf is not None:
        def _update_teams():
            cv = browse_conf.value
            if cv == "__all__":
                filtered = sorted(r["team_name"] for r in standings)
            else:
                conf_team_set = set(conferences.get(cv, []))
                filtered = sorted(t for t in all_team_names if t in conf_team_set)
            new_opts = {t: t for t in filtered}
            browse_team.options = new_opts
            browse_team.update()
            if filtered and browse_team.value not in filtered:
                browse_team.set_value(filtered[0])

        browse_conf.on("update:model-value", lambda: _update_teams())

    team_detail_container = ui.column().classes("w-full")

    def _load_team():
        selected = browse_team.value
        if not selected:
            return

        team_detail_container.clear()
        with team_detail_container:
            team_record = next((r for r in standings if r["team_name"] == selected), None)
            if team_record:
                with ui.row().classes("w-full flex-wrap gap-3"):
                    metric_card("Record", f"{team_record['wins']}-{team_record['losses']}")
                    if has_conferences:
                        metric_card("Conf Record", f"{team_record.get('conf_wins', 0)}-{team_record.get('conf_losses', 0)}")
                    else:
                        metric_card("Win%", f"{team_record.get('win_percentage', 0):.3f}")
                    metric_card("PF", fmt_vb_score(team_record.get("points_for", 0)))
                    metric_card("PA", fmt_vb_score(team_record.get("points_against", 0)))
                    metric_card("OPI", f"{team_record.get('avg_opi', 0):.1f}")

            try:
                roster_resp = api_client.get_roster(session_id, selected)
                roster = roster_resp.get("roster", [])
                team_prestige = roster_resp.get("prestige")
            except api_client.APIError:
                with ui.card().classes("bg-yellow-50 p-3 rounded"):
                    ui.label("Could not load roster for this team.")
                return

            if not roster:
                with ui.card().classes("bg-blue-50 p-3 rounded"):
                    ui.label("No roster data available.")
                return

            header_parts = [f"**{selected} Roster** ({len(roster)} players)"]
            if team_prestige is not None:
                prestige_label = (
                    "Elite" if team_prestige >= 85
                    else "Strong" if team_prestige >= 70
                    else "Average" if team_prestige >= 50
                    else "Developing" if team_prestige >= 30
                    else "Rebuilding"
                )
                header_parts.append(f"Program Prestige: **{team_prestige}** ({prestige_label})")
            ui.markdown(" | ".join(header_parts))

            # Injury map
            inj_map: dict[str, str] = {}
            try:
                inj_resp = api_client.get_injuries(session_id, team=selected)
                for inj in inj_resp.get("active", []):
                    pname = inj.get("player_name", "")
                    if inj.get("is_season_ending") or inj.get("tier") == "severe":
                        inj_map[pname] = f"OUT FOR SEASON ({inj.get('description', '')})"
                    elif inj.get("tier") in ("moderate", "major"):
                        inj_map[pname] = f"OUT ({inj.get('description', '')}, Wk {inj.get('week_return', '?')})"
                    elif inj.get("tier") == "minor":
                        inj_map[pname] = f"DOUBTFUL ({inj.get('description', '')})"
                    elif inj.get("tier") == "day_to_day":
                        inj_map[pname] = f"QUESTIONABLE ({inj.get('description', '')})"
                    else:
                        inj_map[pname] = f"OUT ({inj.get('description', '')})"
            except api_client.APIError:
                pass

            # Build roster data
            roster_data = []
            for p in roster:
                depth = p.get("depth_rank", 0)
                role = "Starter" if depth == 1 else f"Backup #{depth}" if depth <= 3 else "Reserve"
                rs_status = ""
                if p.get("redshirt", False):
                    rs_status = "RS"
                elif p.get("redshirt_used", False):
                    rs_status = "Used"
                elif p.get("redshirt_eligible", False):
                    rs_status = "Eligible"
                health_status = inj_map.get(p["name"], "HEALTHY")
                roster_data.append({
                    "#": p.get("number", ""),
                    "Name": p["name"],
                    "Position": p["position"],
                    "Status": health_status,
                    "Role": role,
                    "RS": rs_status,
                    "Year": p.get("year_abbr", p.get("year", "")),
                    "Archetype": p.get("archetype", ""),
                    "OVR": p.get("overall", 0),
                    "SPD": p.get("speed", 0),
                    "PWR": p.get("power", 0),
                    "AGI": p.get("agility", 0),
                    "HND": p.get("hands", 0),
                    "AWR": p.get("awareness", 0),
                    "STA": p.get("stamina", 0),
                    "KCK": p.get("kicking", 0),
                    "LAT": p.get("lateral_skill", 0),
                    "TKL": p.get("tackling", 0),
                    "GP": p.get("season_games_played", 0),
                })

            # View toggle
            view_toggle = ui.toggle(["Full Roster", "Depth Chart"], value="Full Roster").classes("mb-2")
            roster_table_container = ui.column().classes("w-full")

            def _render_roster_view():
                roster_table_container.clear()
                with roster_table_container:
                    if view_toggle.value == "Depth Chart" and roster_data:
                        dc_positions = sorted(set(r["Position"] for r in roster_data))
                        for pos in dc_positions:
                            group = sorted(
                                [r for r in roster_data if r["Position"] == pos],
                                key=lambda x: -int(x["OVR"]) if isinstance(x["OVR"], (int, float)) else 0,
                            )
                            ui.markdown(f"**{pos}**")
                            dc_cols = ["#", "Name", "Status", "Role", "RS", "Year", "OVR", "GP", "Archetype", "SPD", "PWR", "AWR"]
                            dc_rows = [{k: r.get(k, "") for k in dc_cols} for r in group]
                            stat_table(dc_rows, columns=dc_cols)
                    else:
                        stat_table(roster_data)

            view_toggle.on("update:model-value", lambda: _render_roster_view())
            _render_roster_view()

            # -- Player Card --
            ui.separator()
            player_names = [p["name"] for p in roster]
            player_opts = {"__none__": "--"}
            player_opts.update({pn: pn for pn in player_names})
            player_select = ui.select(player_opts, label="View Player Card", value="__none__").classes("w-full max-w-md")

            player_card_container = ui.column().classes("w-full")

            def _render_player_card():
                sel = player_select.value
                player_card_container.clear()
                if not sel or sel == "__none__":
                    return

                p = next((pl for pl in roster if pl["name"] == sel), None)
                if not p:
                    return

                with player_card_container:
                    ui.label(f"{p['name']} -- #{p.get('number', '')} {p['position']}").classes("text-lg font-semibold text-slate-700")

                    with ui.row().classes("gap-4"):
                        ui.markdown(f"**Year:** {p.get('year_abbr', p.get('year', ''))}")
                        ui.markdown(f"**Archetype:** {p.get('archetype', 'None')}")
                        ui.markdown(f"**Overall:** {p.get('overall', 0)}")

                    # Bio
                    bio_parts = []
                    if p.get("height"):
                        bio_parts.append(f"**Height:** {p['height']}")
                    if p.get("weight"):
                        bio_parts.append(f"**Weight:** {p['weight']} lbs")
                    hometown_parts = []
                    if p.get("hometown_city"):
                        hometown_parts.append(p["hometown_city"])
                    if p.get("hometown_state"):
                        hometown_parts.append(p["hometown_state"])
                    elif p.get("hometown_country") and p["hometown_country"] != "USA":
                        hometown_parts.append(p["hometown_country"])
                    if hometown_parts:
                        bio_parts.append(f"**Hometown:** {', '.join(hometown_parts)}")
                    if p.get("potential"):
                        dev_label = p.get("development", "normal").replace("_", " ").title()
                        bio_parts.append(f"**Potential:** {'*' * p['potential']} ({dev_label})")
                    if bio_parts:
                        with ui.row().classes("gap-4 flex-wrap"):
                            for part in bio_parts:
                                ui.markdown(part)

                    # Attributes
                    ui.markdown("**Attributes**")
                    attrs = {
                        "Speed": p.get("speed", 0),
                        "Power": p.get("power", 0),
                        "Agility": p.get("agility", 0),
                        "Hands": p.get("hands", 0),
                        "Awareness": p.get("awareness", 0),
                        "Stamina": p.get("stamina", 0),
                        "Kicking": p.get("kicking", 0),
                        "Kick Power": p.get("kick_power", 0),
                        "Kick Accuracy": p.get("kick_accuracy", 0),
                        "Lateral Skill": p.get("lateral_skill", 0),
                        "Tackling": p.get("tackling", 0),
                    }
                    with ui.row().classes("gap-3 flex-wrap"):
                        for attr_name, attr_val in attrs.items():
                            color = "#16a34a" if attr_val >= 80 else ("#f59e0b" if attr_val >= 60 else "#dc2626")
                            with ui.card().classes("p-2").style(f"border-left: 3px solid {color}; min-width: 120px;"):
                                ui.label(attr_name).classes("text-xs text-gray-500")
                                ui.label(str(attr_val)).classes("text-lg font-bold").style(f"color: {color};")

                    # Career Awards
                    p_awards = p.get("career_awards", [])
                    if p_awards:
                        ui.markdown("**Career Awards**")
                        award_rows = []
                        for aw in p_awards:
                            award_rows.append({
                                "Year": aw.get("year", ""),
                                "Award": aw.get("award", ""),
                                "Level": aw.get("level", "").title(),
                                "Team": aw.get("team", ""),
                            })
                        stat_table(award_rows)

                    # Season Stats
                    try:
                        ps_resp = api_client.get_player_stats(session_id, team=selected)
                        team_players = ps_resp.get("players", [])
                        player_season = next((tp for tp in team_players if tp["name"] == sel), None)
                        if player_season and player_season.get("games_played", 0) > 0:
                            ui.markdown("**Season Stats**")
                            with ui.row().classes("w-full flex-wrap gap-3"):
                                metric_card("Games", player_season["games_played"])
                                metric_card("Touches", player_season["touches"])
                                metric_card("Total Yards", player_season["yards"])
                                metric_card("TDs", player_season["tds"])
                                metric_card("Fumbles", player_season["fumbles"])

                            if player_season["rushing_yards"] > 0 or player_season["lateral_yards"] > 0:
                                with ui.row().classes("w-full flex-wrap gap-3"):
                                    metric_card("Rush Yards", player_season["rushing_yards"])
                                    metric_card("Lateral Yards", player_season["lateral_yards"])
                                    metric_card("Yds/Touch", player_season["yards_per_touch"])

                            if player_season["kick_att"] > 0:
                                with ui.row().classes("w-full flex-wrap gap-3"):
                                    metric_card("FG (PK)", f"{player_season.get('pk_made', 0)}/{player_season.get('pk_att', 0)}")
                                    metric_card("Snap Kick (DK)", f"{player_season.get('dk_made', 0)}/{player_season.get('dk_att', 0)}")
                                    metric_card("Total Kicks", f"{player_season['kick_made']}/{player_season['kick_att']} ({player_season['kick_pct']:.1f}%)")

                            if player_season["total_return_yards"] > 0 or player_season["st_tackles"] > 0:
                                with ui.row().classes("w-full flex-wrap gap-3"):
                                    metric_card("KR Yards", player_season["kick_return_yards"])
                                    metric_card("PR Yards", player_season["punt_return_yards"])
                                    metric_card("Return TDs", player_season["total_return_tds"])
                                    metric_card("ST Tackles", player_season["st_tackles"])
                    except api_client.APIError:
                        pass

                    # Career Stats (Year-by-Year)
                    career_seasons = p.get("career_seasons", [])
                    if career_seasons:
                        ui.markdown("**Career Stats (Year-by-Year)**")
                        career_rows = []
                        for cs in career_seasons:
                            row = {
                                "Year": cs.get("season_year", ""),
                                "Team": cs.get("team", ""),
                                "GP": cs.get("games_played", 0),
                                "Touches": cs.get("touches", 0),
                                "Rush Yds": cs.get("rushing_yards", 0),
                                "Lat Yds": cs.get("lateral_yards", 0),
                                "Total Yds": cs.get("total_yards", 0),
                                "TDs": cs.get("touchdowns", 0),
                                "Fumbles": cs.get("fumbles", 0),
                            }
                            if cs.get("kick_attempts", 0) > 0:
                                ka = cs["kick_attempts"]
                                km = cs.get("kick_makes", 0)
                                row["Kicks"] = f"{km}/{ka}"
                            if cs.get("tackles", 0) > 0 or cs.get("sacks", 0) > 0:
                                row["TKL"] = cs.get("tackles", 0)
                                row["Sacks"] = cs.get("sacks", 0)
                            career_rows.append(row)

                        if len(career_rows) > 1:
                            totals = {
                                "Year": "CAREER",
                                "Team": "",
                                "GP": sum(cs.get("games_played", 0) for cs in career_seasons),
                                "Touches": sum(cs.get("touches", 0) for cs in career_seasons),
                                "Rush Yds": sum(cs.get("rushing_yards", 0) for cs in career_seasons),
                                "Lat Yds": sum(cs.get("lateral_yards", 0) for cs in career_seasons),
                                "Total Yds": sum(cs.get("total_yards", 0) for cs in career_seasons),
                                "TDs": sum(cs.get("touchdowns", 0) for cs in career_seasons),
                                "Fumbles": sum(cs.get("fumbles", 0) for cs in career_seasons),
                            }
                            total_ka = sum(cs.get("kick_attempts", 0) for cs in career_seasons)
                            if total_ka > 0:
                                total_km = sum(cs.get("kick_makes", 0) for cs in career_seasons)
                                totals["Kicks"] = f"{total_km}/{total_ka}"
                            total_tkl = sum(cs.get("tackles", 0) for cs in career_seasons)
                            total_sacks = sum(cs.get("sacks", 0) for cs in career_seasons)
                            if total_tkl > 0 or total_sacks > 0:
                                totals["TKL"] = total_tkl
                                totals["Sacks"] = total_sacks
                            career_rows.append(totals)

                        stat_table(career_rows)

            player_select.on("update:model-value", lambda: _render_player_card())

    browse_team.on("update:model-value", lambda: _load_team())
    # Initial load
    _load_team()


# ---------------------------------------------------------------------------
# Awards & Stats
# ---------------------------------------------------------------------------

def _render_awards_stats(session_id, standings, user_team):
    try:
        awards = api_client.get_season_awards(session_id)
    except api_client.APIError:
        awards = {}

    indiv_awards = awards.get("individual_awards", [])
    if indiv_awards:
        ui.label("National Individual Awards").classes("text-lg font-semibold text-slate-700")
        with ui.row().classes("w-full flex-wrap gap-3"):
            for award in indiv_awards:
                metric_card(
                    award.get("award_name", ""),
                    award.get("player_name", ""),
                    f"{award.get('team_name', '')} -- {award.get('position', '')}",
                )
        ui.separator()
        ui.markdown("**Team Awards**")
        with ui.row().classes("w-full flex-wrap gap-3"):
            if awards.get("coach_of_year"):
                metric_card("Coach of the Year", awards["coach_of_year"])
            if awards.get("most_improved"):
                metric_card("Most Improved Program", awards["most_improved"])

    # All-CVL tiers
    for tier_key, tier_label in [
        ("all_american_first", "All-CVL First Team"),
        ("all_american_second", "All-CVL Second Team"),
        ("all_american_third", "All-CVL Third Team"),
        ("honorable_mention", "All-CVL Honorable Mention"),
        ("all_freshman", "All-Freshman Team"),
    ]:
        tier_data = awards.get(tier_key)
        if tier_data and tier_data.get("slots"):
            with ui.expansion(tier_label).classes("w-full"):
                rows = []
                for slot in tier_data["slots"]:
                    rows.append({
                        "Position": slot.get("position", ""),
                        "Player": slot.get("player_name", ""),
                        "Team": slot.get("team_name", ""),
                        "Year": slot.get("year_in_school", ""),
                        "Rating": slot.get("overall_rating", 0),
                    })
                if rows:
                    stat_table(rows)

    # Conference awards
    ac_teams = awards.get("all_conference_teams", {})
    conf_awards = awards.get("conference_awards", {})
    if ac_teams or conf_awards:
        ui.label("Conference Awards").classes("text-lg font-semibold text-slate-700 mt-4")
        conf_names = sorted(set(list(ac_teams.keys()) + list(conf_awards.keys())))
        if conf_names:
            conf_award_select = ui.select(
                {c: c for c in conf_names},
                label="Select Conference",
                value=conf_names[0],
            ).classes("w-full max-w-md")

            conf_award_container = ui.column().classes("w-full")

            def _render_conf_awards():
                selected_conf = conf_award_select.value
                conf_award_container.clear()
                if not selected_conf:
                    return

                with conf_award_container:
                    c_indiv = conf_awards.get(selected_conf, [])
                    if c_indiv:
                        ui.markdown(f"**{selected_conf} Individual Awards**")
                        with ui.row().classes("w-full flex-wrap gap-3"):
                            for ca in c_indiv:
                                metric_card(
                                    ca.get("award_name", ""),
                                    ca.get("player_name", ""),
                                    f"{ca.get('team_name', '')} -- {ca.get('position', '')}",
                                )
                    conf_tiers = ac_teams.get(selected_conf, {})
                    for tier_key in ["first", "second"]:
                        tier = conf_tiers.get(tier_key)
                        if tier and tier.get("slots"):
                            label_text = "First Team" if tier_key == "first" else "Second Team"
                            with ui.expansion(f"All-{selected_conf} {label_text}").classes("w-full"):
                                rows = []
                                for slot in tier["slots"]:
                                    rows.append({
                                        "Position": slot.get("position", ""),
                                        "Player": slot.get("player_name", ""),
                                        "Team": slot.get("team_name", ""),
                                        "Year": slot.get("year_in_school", ""),
                                        "Rating": slot.get("overall_rating", 0),
                                    })
                                if rows:
                                    stat_table(rows)

            conf_award_select.on("update:model-value", lambda: _render_conf_awards())
            _render_conf_awards()

    ui.separator()

    # Statistical Leaders
    ui.markdown("**Statistical Leaders**")
    if standings:
        leader_categories = [
            ("Highest Scoring", lambda r: r.get("points_for", 0) / max(1, r.get("games_played", 1)), "PPG"),
            ("Best Defense", None, "PA/G"),
            ("Top OPI", lambda r: r.get("avg_opi", 0), "OPI"),
            ("Territory King", lambda r: r.get("avg_territory", 0), "Territory"),
            ("Pressure Leader", lambda r: r.get("avg_pressure", 0), "Pressure"),
            ("Chaos Master", lambda r: r.get("avg_chaos", 0), "Chaos"),
            ("Kicking Leader", lambda r: r.get("avg_kicking", 0), "Kicking"),
            ("Best Turnover Impact", lambda r: r.get("avg_turnover_impact", 0), "TO Impact"),
        ]
        leader_rows = []
        for cat_name, key_func, stat_label in leader_categories:
            if cat_name == "Best Defense":
                leader = min(standings, key=lambda r: r.get("points_against", 0) / max(1, r.get("games_played", 1)))
                val = leader.get("points_against", 0) / max(1, leader.get("games_played", 1))
            else:
                leader = max(standings, key=key_func)
                val = key_func(leader)
            leader_rows.append({
                "Category": cat_name,
                "Team": _team_label(leader["team_name"], user_team),
                "Value": f"{abs(val):.1f}",
            })
        stat_table(leader_rows)

    # Score Distribution
    with ui.expansion("Score Distribution").classes("w-full"):
        score_data = []
        try:
            sched_resp = api_client.get_schedule(session_id, completed_only=True)
            for g in sched_resp.get("games", []):
                score_data.append({"Team": g.get("home_team", ""), "Score": g.get("home_score") or 0, "Location": "Home"})
                score_data.append({"Team": g.get("away_team", ""), "Score": g.get("away_score") or 0, "Location": "Away"})
        except api_client.APIError:
            pass
        if score_data:
            import pandas as pd
            fig = px.box(
                pd.DataFrame(score_data),
                x="Team", y="Score", color="Team",
                title="Score Distribution by Team",
            )
            fig.update_layout(showlegend=False, height=400, template="plotly_white")
            ui.plotly(fig).classes("w-full")


# ---------------------------------------------------------------------------
# Injury Report
# ---------------------------------------------------------------------------

def _render_injury_report(session_id, standings):
    try:
        inj_resp = api_client.get_injuries(session_id)
    except api_client.APIError:
        ui.label("Injury data not available.").classes("text-sm text-gray-500")
        return

    active = inj_resp.get("active", [])
    season_log = inj_resp.get("season_log", [])
    counts = inj_resp.get("counts", {})

    dtd_count = sum(1 for i in active if i.get("tier") == "day_to_day")
    out_count = sum(1 for i in active if i.get("tier") not in ("day_to_day", "severe") and not i.get("is_season_ending"))
    se_count = sum(1 for i in active if i.get("is_season_ending") or i.get("tier") == "severe")
    most_injured = max(counts.items(), key=lambda x: x[1])[0] if counts else "--"

    with ui.row().classes("w-full flex-wrap gap-3"):
        metric_card("Active Injuries", len(active))
        metric_card("Day-to-Day", dtd_count)
        metric_card("Out (Minor+)", out_count)
        metric_card("Season-Ending", se_count)
        metric_card("Most Affected Team", most_injured)

    if active:
        ui.label("Currently Injured Players").classes("text-lg font-semibold text-slate-700 mt-3")
        active_rows = []
        for inj in active:
            status_str = _game_status_label(inj)
            active_rows.append({
                "Team": inj.get("team_name", ""),
                "Player": inj.get("player_name", ""),
                "Position": inj.get("position", ""),
                "Injury": inj.get("description", ""),
                "Body Part": (inj.get("body_part") or "").title(),
                "Category": _CATEGORY_LABELS.get(inj.get("category", ""), inj.get("category", "")),
                "Status": status_str,
                "Week Out": inj.get("week_injured", ""),
                "Return": "Season-ending" if status_str == "OUT FOR SEASON" else f"Wk {inj.get('week_return', '?')}",
            })

        inj_team_opts = {"All": "All"}
        inj_team_opts.update({t: t for t in sorted(set(r["Team"] for r in active_rows))})
        inj_team_filter = ui.select(inj_team_opts, label="Filter by Team", value="All").classes("w-full max-w-md")

        inj_table_container = ui.column().classes("w-full")

        def _filter_injuries():
            ft = inj_team_filter.value
            filtered = active_rows if ft == "All" else [r for r in active_rows if r["Team"] == ft]
            inj_table_container.clear()
            with inj_table_container:
                stat_table(filtered)

        inj_team_filter.on("update:model-value", lambda: _filter_injuries())
        _filter_injuries()
    else:
        ui.label("No active injuries.").classes("text-sm text-gray-500")

    # Injuries by Category
    with ui.expansion("Injuries by Category").classes("w-full"):
        if season_log:
            import pandas as pd
            cat_tier_data = []
            for inj in season_log:
                cat_tier_data.append({
                    "Category": _CATEGORY_LABELS.get(inj.get("category", ""), inj.get("category", "")),
                    "Tier": _tier_display(inj.get("tier", "")),
                })
            if cat_tier_data:
                fig_cat = px.histogram(
                    pd.DataFrame(cat_tier_data),
                    x="Category",
                    color="Tier",
                    title="Injuries by Category",
                    color_discrete_map={
                        "Day-To-Day": "#22c55e",
                        "Minor": "#fbbf24",
                        "Moderate": "#f59e0b",
                        "Major": "#dc2626",
                        "Severe": "#991b1b",
                    },
                )
                fig_cat.update_layout(height=350, template="plotly_white")
                ui.plotly(fig_cat).classes("w-full")
        else:
            ui.label("No injury data yet.").classes("text-sm text-gray-500")

    # Injury Counts by Team
    if counts:
        with ui.expansion("Injury Counts by Team").classes("w-full"):
            count_rows = [{"Team": t, "Injuries": c} for t, c in sorted(counts.items(), key=lambda x: -x[1])]
            stat_table(count_rows)

    # Full Season Injury Log
    if season_log:
        with ui.expansion("Full Season Injury Log").classes("w-full"):
            log_rows = []
            for inj in season_log:
                status_str = _game_status_label(inj)
                log_rows.append({
                    "Week": inj.get("week_injured", ""),
                    "Team": inj.get("team_name", ""),
                    "Player": inj.get("player_name", ""),
                    "Position": inj.get("position", ""),
                    "Injury": inj.get("description", ""),
                    "Body Part": (inj.get("body_part") or "").title(),
                    "Category": _CATEGORY_LABELS.get(inj.get("category", ""), inj.get("category", "")),
                    "Severity": _tier_display(inj.get("tier", "")),
                    "In-Game": "Yes" if inj.get("in_game") else "No",
                    "Status": status_str,
                    "Weeks Out": inj.get("weeks_out", ""),
                })
            stat_table(log_rows)
