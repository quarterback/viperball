import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from engine.season import BOWL_TIERS
from ui import api_client
from ui.helpers import fmt_vb_score, render_game_detail


def _get_session_id():
    return st.session_state.get("api_session_id")


def _get_mode():
    return st.session_state.get("api_mode")


def render_league_section(shared):
    session_id = _get_session_id()
    mode = _get_mode()

    if not session_id or not mode:
        st.title("League")
        st.info("No active season found. Start a new season or dynasty from the Play section to view league data.")
        return

    try:
        standings_resp = api_client.get_standings(session_id)
        standings = standings_resp.get("standings", [])
    except api_client.APIError:
        st.title("League")
        st.info("No active season found. Start a new season or dynasty from the Play section to view league data.")
        return

    if not standings:
        st.title("League")
        st.info("No standings data available yet. Simulate some games first.")
        return

    try:
        status = api_client.get_season_status(session_id)
    except api_client.APIError:
        status = {}

    user_team = None
    if mode == "dynasty":
        try:
            dyn_status = api_client.get_dynasty_status(session_id)
            user_team = dyn_status.get("coach", {}).get("team")
        except api_client.APIError:
            pass

    champion = status.get("champion")
    if champion:
        st.success(f"**National Champions: {champion}**")

    try:
        schedule_resp = api_client.get_schedule(session_id, completed_only=True)
        completed_games = schedule_resp.get("games", [])
    except api_client.APIError:
        completed_games = []

    total_games = len(completed_games)
    all_scores = []
    for g in completed_games:
        all_scores.extend([g.get("home_score") or 0, g.get("away_score") or 0])
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

    try:
        conf_resp = api_client.get_conferences(session_id)
        conferences = conf_resp.get("conferences", {})
    except api_client.APIError:
        conferences = {}

    has_conferences = bool(conferences) and len(conferences) >= 1

    sm1, sm2, sm3, sm4, sm5 = st.columns(5)
    sm1.metric("Teams", len(standings))
    sm2.metric("Games", total_games)
    sm3.metric("Avg Score", f"{avg_score:.1f}")
    if has_conferences:
        sm4.metric("Conferences", len(conferences))
    else:
        avg_opi = sum(r.get("avg_opi", 0) for r in standings) / len(standings) if standings else 0
        sm4.metric("Avg OPI", f"{avg_opi:.1f}")
    best = standings[0] if standings else None
    sm5.metric("Top Team", f"{best['team_name']}" if best else "—", f"{best['wins']}-{best['losses']}" if best else "")

    tab_names = ["Standings", "Power Rankings"]
    if has_conferences:
        tab_names.append("Conferences")
    tab_names.extend(["Player Stats", "Team Browser", "Postseason", "Schedule", "Awards & Stats"])
    league_tabs = st.tabs(tab_names)
    tab_idx = 0

    with league_tabs[tab_idx]:
        tab_idx += 1
        _render_standings(session_id, standings, has_conferences, user_team)

    with league_tabs[tab_idx]:
        tab_idx += 1
        _render_power_rankings(session_id, standings, user_team)

    if has_conferences:
        with league_tabs[tab_idx]:
            tab_idx += 1
            _render_conferences(session_id, conferences, user_team)

    with league_tabs[tab_idx]:
        tab_idx += 1
        _render_player_stats(session_id, standings, conferences, has_conferences)

    with league_tabs[tab_idx]:
        tab_idx += 1
        _render_team_browser(session_id, standings, conferences, has_conferences)

    with league_tabs[tab_idx]:
        tab_idx += 1
        _render_postseason(session_id, user_team)

    with league_tabs[tab_idx]:
        tab_idx += 1
        _render_schedule(session_id, completed_games, user_team)

    with league_tabs[tab_idx]:
        tab_idx += 1
        _render_awards_stats(session_id, standings, user_team)


def _team_label(name, user_team):
    if user_team and name == user_team:
        return f">>> {name}"
    return name


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
    st.dataframe(pd.DataFrame(standings_data), hide_index=True, use_container_width=True, height=600)


def _render_power_rankings(session_id, standings, user_team):
    try:
        polls_resp = api_client.get_polls(session_id)
        all_polls = polls_resp.get("polls", [])
    except api_client.APIError:
        all_polls = []

    if all_polls and len(all_polls) > 1:
        max_week = len(all_polls)
        selected_week = st.slider("Poll Week", min_value=1, max_value=max_week, value=max_week, key="league_poll_week_slider")
        poll = all_polls[selected_week - 1] if selected_week <= len(all_polls) else None
    elif all_polls:
        poll = all_polls[-1]
    else:
        poll = None

    if poll:
        poll_data = []
        rankings = poll.get("rankings", [])
        for r in rankings:
            movement = ""
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
            poll_data.append({
                "#": rank,
                "Team": _team_label(r.get("team_name", ""), user_team),
                "Record": r.get("record", ""),
                "Conf": r.get("conference", ""),
                "Power Index": f"{r.get('power_index', 0):.1f}",
                "Quality Wins": r.get("quality_wins", 0),
                "SOS Rank": r.get("sos_rank", 0),
                "Move": movement,
            })
        st.dataframe(pd.DataFrame(poll_data), hide_index=True, use_container_width=True, height=600)
    else:
        st.caption("No rankings available yet.")

    with st.expander("Team Comparison Radar"):
        default_teams = []
        if len(standings) > 1:
            default_teams = [standings[0]["team_name"], standings[-1]["team_name"]]
        elif standings:
            default_teams = [standings[0]["team_name"]]
        radar_teams = st.multiselect("Compare Teams", [r["team_name"] for r in standings],
                                     default=default_teams, key="league_radar_teams")
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
                    fig.add_trace(go.Scatterpolar(r=values + [values[0]], theta=categories + [categories[0]],
                                                  fill='toself', name=tname))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                              title="Team Metrics Comparison", height=450, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)


def _render_conferences(session_id, conferences, user_team):
    try:
        conf_standings_resp = api_client.get_conference_standings(session_id)
        conf_standings_data = conf_standings_resp.get("conference_standings", {})
        champions = conf_standings_resp.get("champions", {})
    except api_client.APIError:
        conf_standings_data = {}
        champions = {}

    conf_tabs = st.tabs(sorted(conferences.keys()))
    for conf_tab, conf_name in zip(conf_tabs, sorted(conferences.keys())):
        with conf_tab:
            conf_standings = conf_standings_data.get(conf_name, [])
            if conf_standings:
                champ_name = champions.get(conf_name, "")
                if champ_name:
                    st.caption(f"Conference Champion: **{champ_name}**")
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
                st.dataframe(pd.DataFrame(conf_data), hide_index=True, use_container_width=True)


def _render_postseason(session_id, user_team):
    try:
        bracket_resp = api_client.get_playoff_bracket(session_id)
        bracket = bracket_resp.get("bracket", [])
        champion = bracket_resp.get("champion")
    except api_client.APIError:
        bracket = []
        champion = None

    if bracket:
        st.markdown("**Playoff Field**")
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
            st.dataframe(pd.DataFrame(pf_data), hide_index=True, use_container_width=True)

        st.markdown("**Bracket Results**")
        round_info = [
            ("Opening Round", 996),
            ("First Round", 997),
            ("National Quarterfinals", 998),
            ("National Semi-Finals", 999),
        ]
        for label, week in round_info:
            round_games = [g for g in bracket if g.get("week") == week and g.get("completed")]
            if round_games:
                st.markdown(f"*{label}*")
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
                    st.markdown(f"{prefix}Game {i}: **{winner}** {fmt_vb_score(w_score)} def. {loser} {fmt_vb_score(l_score)}")

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
            st.success(f"**NATIONAL CHAMPIONS: {winner}** {fmt_vb_score(w_score)} def. {loser} {fmt_vb_score(l_score)}")
    else:
        st.caption("No playoffs ran this season.")

    try:
        bowls_resp = api_client.get_bowl_results(session_id)
        bowl_results = bowls_resp.get("bowl_results", [])
    except api_client.APIError:
        bowl_results = []

    if bowl_results:
        st.markdown("---")
        st.markdown("**Bowl Games**")
        current_tier = 0
        for bowl in bowl_results:
            tier = bowl.get("tier", 0)
            if tier != current_tier:
                current_tier = tier
                tier_label = BOWL_TIERS.get(tier, "Standard")
                st.markdown(f"*{tier_label} Bowls*")
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
            st.markdown(f"{prefix}**{bowl.get('name', 'Bowl')}**: **{winner}** ({w_rec}) {fmt_vb_score(w_score)} def. {loser} ({l_rec}) {fmt_vb_score(l_score)}")


def _render_schedule(session_id, completed_games, user_team):
    # Fetch ALL games (completed + upcoming) so users can see their full schedule
    try:
        all_schedule_resp = api_client.get_schedule(session_id)
        all_reg_games = all_schedule_resp.get("games", [])
    except api_client.APIError:
        all_reg_games = completed_games  # fallback to completed only

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
        status = "Played" if is_completed else "Upcoming"
        all_game_entries.append({
            "game": g,
            "phase": "Regular Season",
            "label_prefix": f"Wk {g.get('week', 0)}",
            "sort_key": g.get("week", 0),
            "game_type": game_type,
            "status": status,
        })

    if bracket:
        playoff_round_names = {996: "Opening Round", 997: "First Round", 998: "National Quarterfinals", 999: "National Semi-Finals", 1000: "National Championship"}
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
                "label_prefix": bowl.get("name", f"Bowl {i+1}"),
                "sort_key": 800 + i,
                "game_type": "Bowl",
                "status": "Played" if is_completed else "Upcoming",
            })

    all_game_entries.sort(key=lambda e: e["sort_key"])

    all_teams_in_log = set()
    all_phases = set()
    for entry in all_game_entries:
        g = entry["game"]
        all_teams_in_log.add(g.get("home_team", ""))
        all_teams_in_log.add(g.get("away_team", ""))
        all_phases.add(entry["phase"])

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        team_options = ["All Teams"] + sorted(all_teams_in_log)
        if user_team:
            team_options = ["My Team", "All Teams"] + sorted(all_teams_in_log)
        filter_team = st.selectbox("Filter by Team", team_options, key="league_game_filter_team")
    with fc2:
        phase_options = ["All Phases"] + sorted(all_phases)
        filter_phase = st.selectbox("Filter by Phase", phase_options, key="league_game_filter_phase")
    with fc3:
        all_weeks = sorted(set(g.get("week", 0) for g in all_reg_games))
        filter_week = st.selectbox("Filter by Week", ["All Weeks"] + all_weeks, key="league_game_filter_week")
    with fc4:
        status_options = ["All", "Upcoming", "Played"]
        filter_status = st.selectbox("Status", status_options, key="league_game_filter_status")

    filtered_entries = all_game_entries
    if filter_team == "My Team" and user_team:
        filtered_entries = [e for e in filtered_entries if e["game"].get("home_team") == user_team or e["game"].get("away_team") == user_team]
    elif filter_team not in ("All Teams", "My Team"):
        filtered_entries = [e for e in filtered_entries if e["game"].get("home_team") == filter_team or e["game"].get("away_team") == filter_team]
    if filter_phase != "All Phases":
        filtered_entries = [e for e in filtered_entries if e["phase"] == filter_phase]
    if filter_week != "All Weeks":
        filtered_entries = [e for e in filtered_entries if e["phase"] == "Regular Season" and e["game"].get("week") == filter_week]
    if filter_status != "All":
        filtered_entries = [e for e in filtered_entries if e["status"] == filter_status]

    schedule_data = []
    game_labels = []
    filtered_games = []
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
            home_score_str = "—"
            away_score_str = "—"
            winner_str = "—"

        row = {
            "Week": entry["label_prefix"],
            "Type": entry.get("game_type", ""),
            "Status": entry["status"],
            "Home": _team_label(home, user_team),
            "Away": _team_label(away, user_team),
            "Home Score": home_score_str,
            "Away Score": away_score_str,
            "Winner": winner_str,
        }
        schedule_data.append(row)

        if is_completed:
            game_labels.append(f"{entry['label_prefix']}: {home} {fmt_vb_score(hs)} vs {away} {fmt_vb_score(aws)}")
        else:
            game_labels.append(f"{entry['label_prefix']}: {home} vs {away} (Upcoming)")
        filtered_games.append(g)

    if schedule_data:
        st.dataframe(pd.DataFrame(schedule_data), hide_index=True, use_container_width=True, height=400)
    else:
        st.info("No games scheduled yet.")

    # Game detail viewer (only for completed games)
    completed_labels = [(i, label) for i, label in enumerate(game_labels) if filtered_games[i].get("completed")]
    if completed_labels:
        detail_options = [label for _, label in completed_labels]
        selected_detail = st.selectbox("Select a completed game to view details", detail_options, key="league_game_detail_select")
        detail_idx = detail_options.index(selected_detail)
        actual_idx = completed_labels[detail_idx][0]
        selected_game = filtered_games[actual_idx]
        full_result = selected_game.get("full_result")
        if not full_result and selected_game.get("has_full_result"):
            try:
                detail_resp = api_client.get_schedule(
                    session_id,
                    week=selected_game.get("week"),
                    include_full_result=True,
                )
                detail_games = detail_resp.get("games", [])
                for dg in detail_games:
                    if dg.get("home_team") == selected_game.get("home_team") and dg.get("away_team") == selected_game.get("away_team"):
                        full_result = dg.get("full_result")
                        break
            except api_client.APIError:
                pass
        if full_result:
            with st.expander("Game Details", expanded=True):
                render_game_detail(full_result, key_prefix=f"league_gd_{actual_idx}")
        else:
            st.caption("Detailed game data not available for this game.")


def _render_player_stats(session_id, standings, conferences, has_conferences):
    st.markdown("### Individual Player Statistics")

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        conf_options = ["All Conferences"] + sorted(conferences.keys()) if has_conferences else ["All"]
        sel_conf = st.selectbox("Conference", conf_options, key="ps_conf_filter")
    with fc2:
        team_names = sorted(r["team_name"] for r in standings)
        team_options = ["All Teams"] + team_names
        sel_team = st.selectbox("Team", team_options, key="ps_team_filter")
    with fc3:
        pos_options = ["All Positions", "HB", "WB", "SB", "ZB", "VP", "LB", "CB", "LA", "KP", "ED", "BK"]
        sel_pos = st.selectbox("Position", pos_options, key="ps_pos_filter")

    min_t = st.slider("Minimum touches", 0, 50, 1, key="ps_min_touches")

    conf_param = sel_conf if sel_conf != "All Conferences" and sel_conf != "All" else None
    team_param = sel_team if sel_team != "All Teams" else None
    pos_param = sel_pos if sel_pos != "All Positions" else None

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
        st.warning("Could not load player stats. Simulate some games first.")
        return

    if not players:
        st.info("No player stats available. Simulate some games to see individual statistics.")
        return

    st.caption(f"Showing {len(players)} players")

    stat_views = st.tabs(["Rushing & Scoring", "Lateral Game", "Kicking", "Returns & Special Teams"])

    with stat_views[0]:
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
            st.dataframe(pd.DataFrame(rush_data), hide_index=True, use_container_width=True, height=500)

    with stat_views[1]:
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
            st.dataframe(pd.DataFrame(lat_data), hide_index=True, use_container_width=True, height=500)
        else:
            st.caption("No lateral stats available yet.")

    with stat_views[2]:
        kick_data = []
        kick_sorted = sorted(players, key=lambda x: x["kick_att"], reverse=True)
        for p in kick_sorted[:100]:
            if p["kick_att"] > 0:
                kick_data.append({
                    "Player": p["name"],
                    "Team": p["team"],
                    "Pos": p["tag"].split(" ")[0] if " " in p["tag"] else p["tag"][:2],
                    "GP": p["games_played"],
                    "Kick Att": p["kick_att"],
                    "Kick Made": p["kick_made"],
                    "Kick %": f"{p['kick_pct']:.1f}%",
                    "Deflections": p["kick_deflections"],
                })
        if kick_data:
            st.dataframe(pd.DataFrame(kick_data), hide_index=True, use_container_width=True, height=500)
        else:
            st.caption("No kicking stats available yet.")

    with stat_views[3]:
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
            st.dataframe(pd.DataFrame(ret_data), hide_index=True, use_container_width=True, height=500)
        else:
            st.caption("No return/special teams stats available yet.")

    with st.expander("Stat Leaders Summary"):
        if players:
            leaders = [
                ("Rushing Yards Leader", max(players, key=lambda x: x["rushing_yards"]), "rushing_yards"),
                ("Total Yards Leader", max(players, key=lambda x: x["yards"]), "yards"),
                ("Touchdown Leader", max(players, key=lambda x: x["tds"]), "tds"),
                ("Lateral Yards Leader", max(players, key=lambda x: x["lateral_yards"]), "lateral_yards"),
                ("Return Yards Leader", max(players, key=lambda x: x["total_return_yards"]), "total_return_yards"),
            ]
            lcols = st.columns(len(leaders))
            for i, (label, player, stat_key) in enumerate(leaders):
                lcols[i].metric(label, player["name"], f"{player['team']} — {player[stat_key]}")


def _render_team_browser(session_id, standings, conferences, has_conferences):
    st.markdown("### Team Browser")
    st.caption("Browse any team's roster, view individual player cards with full attributes and season stats")

    bc1, bc2 = st.columns(2)
    with bc1:
        if has_conferences:
            conf_options = ["All Conferences"] + sorted(conferences.keys())
            browse_conf = st.selectbox("Conference", conf_options, key="tb_conf")
        else:
            browse_conf = "All Conferences"

    filtered_teams = sorted(r["team_name"] for r in standings)
    if has_conferences and browse_conf != "All Conferences":
        conf_team_set = set(conferences.get(browse_conf, []))
        filtered_teams = [t for t in filtered_teams if t in conf_team_set]

    with bc2:
        browse_team = st.selectbox("Select Team", filtered_teams, key="tb_team")

    if not browse_team:
        return

    team_record = next((r for r in standings if r["team_name"] == browse_team), None)
    if team_record:
        rc1, rc2, rc3, rc4, rc5 = st.columns(5)
        rc1.metric("Record", f"{team_record['wins']}-{team_record['losses']}")
        if has_conferences:
            rc2.metric("Conf Record", f"{team_record.get('conf_wins', 0)}-{team_record.get('conf_losses', 0)}")
        else:
            rc2.metric("Win%", f"{team_record.get('win_percentage', 0):.3f}")
        rc3.metric("PF", fmt_vb_score(team_record.get("points_for", 0)))
        rc4.metric("PA", fmt_vb_score(team_record.get("points_against", 0)))
        rc5.metric("OPI", f"{team_record.get('avg_opi', 0):.1f}")

    try:
        roster_resp = api_client.get_roster(session_id, browse_team)
        roster = roster_resp.get("roster", [])
    except api_client.APIError:
        st.warning("Could not load roster for this team.")
        return

    if not roster:
        st.info("No roster data available.")
        return

    st.markdown(f"**{browse_team} Roster** ({len(roster)} players)")

    roster_data = []
    for p in roster:
        roster_data.append({
            "#": p.get("number", ""),
            "Name": p["name"],
            "Position": p["position"],
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
    st.dataframe(pd.DataFrame(roster_data), hide_index=True, use_container_width=True, height=500)

    player_names = [p["name"] for p in roster]
    selected_player = st.selectbox("View Player Card", ["—"] + player_names, key="tb_player_card")
    if selected_player and selected_player != "—":
        p = next((pl for pl in roster if pl["name"] == selected_player), None)
        if p:
            st.markdown(f"#### {p['name']} — #{p.get('number', '')} {p['position']}")
            ic1, ic2, ic3 = st.columns(3)
            ic1.markdown(f"**Year:** {p.get('year_abbr', p.get('year', ''))}")
            ic2.markdown(f"**Archetype:** {p.get('archetype', 'None')}")
            ic3.markdown(f"**Overall:** {p.get('overall', 0)}")

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
                bc = st.columns(len(bio_parts))
                for i, part in enumerate(bio_parts):
                    bc[i].markdown(part)

            st.markdown("**Attributes**")
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
            attr_cols = st.columns(4)
            for i, (attr_name, attr_val) in enumerate(attrs.items()):
                col = attr_cols[i % 4]
                color = "green" if attr_val >= 80 else ("orange" if attr_val >= 60 else "red")
                col.markdown(f"**{attr_name}:** :{color}[{attr_val}]")

            try:
                ps_resp = api_client.get_player_stats(session_id, team=browse_team)
                team_players = ps_resp.get("players", [])
                player_season = next((tp for tp in team_players if tp["name"] == selected_player), None)
                if player_season and player_season.get("games_played", 0) > 0:
                    st.markdown("**Season Stats**")
                    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
                    sc1.metric("Games", player_season["games_played"])
                    sc2.metric("Touches", player_season["touches"])
                    sc3.metric("Total Yards", player_season["yards"])
                    sc4.metric("TDs", player_season["tds"])
                    sc5.metric("Fumbles", player_season["fumbles"])

                    if player_season["rushing_yards"] > 0 or player_season["lateral_yards"] > 0:
                        sc6, sc7, sc8 = st.columns(3)
                        sc6.metric("Rush Yards", player_season["rushing_yards"])
                        sc7.metric("Lateral Yards", player_season["lateral_yards"])
                        sc8.metric("Yds/Touch", player_season["yards_per_touch"])

                    if player_season["kick_att"] > 0:
                        kc1, kc2, kc3 = st.columns(3)
                        kc1.metric("Kick Att", player_season["kick_att"])
                        kc2.metric("Kick Made", player_season["kick_made"])
                        kc3.metric("Kick %", f"{player_season['kick_pct']:.1f}%")

                    if player_season["total_return_yards"] > 0 or player_season["st_tackles"] > 0:
                        rt1, rt2, rt3, rt4 = st.columns(4)
                        rt1.metric("KR Yards", player_season["kick_return_yards"])
                        rt2.metric("PR Yards", player_season["punt_return_yards"])
                        rt3.metric("Return TDs", player_season["total_return_tds"])
                        rt4.metric("ST Tackles", player_season["st_tackles"])
            except api_client.APIError:
                pass


def _render_awards_stats(session_id, standings, user_team):
    try:
        awards = api_client.get_season_awards(session_id)
        indiv_awards = awards.get("individual_awards", [])
        if indiv_awards:
            st.markdown("**Individual Awards**")
            award_cols = st.columns(min(3, len(indiv_awards)))
            for i, award in enumerate(indiv_awards):
                col = award_cols[i % len(award_cols)]
                col.metric(
                    award.get("award_name", ""),
                    award.get("player_name", ""),
                    f"{award.get('team_name', '')} — {award.get('position', '')}"
                )
            st.markdown("---")
            st.markdown("**Team Awards**")
            team_aw1, team_aw2 = st.columns(2)
            if awards.get("coach_of_year"):
                team_aw1.metric("Coach of the Year", awards["coach_of_year"])
            if awards.get("most_improved"):
                team_aw2.metric("Most Improved Program", awards["most_improved"])
    except api_client.APIError:
        pass

    st.markdown("**Statistical Leaders**")
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
        st.dataframe(pd.DataFrame(leader_rows), hide_index=True, use_container_width=True)

    with st.expander("Score Distribution"):
        score_data = []
        try:
            sched_resp = api_client.get_schedule(session_id, completed_only=True)
            for g in sched_resp.get("games", []):
                score_data.append({"Team": g.get("home_team", ""), "Score": g.get("home_score") or 0, "Location": "Home"})
                score_data.append({"Team": g.get("away_team", ""), "Score": g.get("away_score") or 0, "Location": "Away"})
        except api_client.APIError:
            pass
        if score_data:
            fig = px.box(pd.DataFrame(score_data), x="Team", y="Score", color="Team",
                         title="Score Distribution by Team")
            fig.update_layout(showlegend=False, height=400, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
