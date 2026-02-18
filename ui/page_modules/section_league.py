import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from engine.season import BOWL_TIERS
from engine.awards import compute_season_awards
from ui.helpers import fmt_vb_score, render_game_detail


def _get_season_and_dynasty():
    dynasty = st.session_state.get("dynasty", None)
    if dynasty and "last_dynasty_season" in st.session_state:
        return st.session_state["last_dynasty_season"], dynasty
    if "active_season" in st.session_state:
        return st.session_state["active_season"], None
    return None, None


def render_league_section(shared):
    season, dynasty = _get_season_and_dynasty()

    if season is None:
        st.title("League")
        st.info("No active season found. Start a new season or dynasty from the Play section to view league data.")
        return

    user_team = dynasty.coach.team_name if dynasty else None
    standings = season.get_standings_sorted()
    has_conferences = bool(season.conferences) and len(season.conferences) >= 1

    if season.champion:
        st.success(f"**National Champions: {season.champion}**")

    total_games = sum(1 for g in season.schedule if g.completed)
    all_scores = []
    for g in season.schedule:
        if g.completed:
            all_scores.extend([g.home_score or 0, g.away_score or 0])
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

    sm1, sm2, sm3, sm4, sm5 = st.columns(5)
    sm1.metric("Teams", len(standings))
    sm2.metric("Games", total_games)
    sm3.metric("Avg Score", f"{avg_score:.1f}")
    if has_conferences:
        sm4.metric("Conferences", len(season.conferences))
    else:
        avg_opi = sum(r.avg_opi for r in standings) / len(standings) if standings else 0
        sm4.metric("Avg OPI", f"{avg_opi:.1f}")
    best = standings[0] if standings else None
    sm5.metric("Top Team", f"{best.team_name}" if best else "—", f"{best.wins}-{best.losses}" if best else "")

    tab_names = ["Standings", "Power Rankings"]
    if has_conferences:
        tab_names.append("Conferences")
    tab_names.extend(["Postseason", "Schedule", "Awards & Stats"])
    league_tabs = st.tabs(tab_names)
    tab_idx = 0

    with league_tabs[tab_idx]:
        tab_idx += 1
        _render_standings(season, standings, has_conferences, user_team)

    with league_tabs[tab_idx]:
        tab_idx += 1
        _render_power_rankings(season, standings, user_team)

    if has_conferences:
        with league_tabs[tab_idx]:
            tab_idx += 1
            _render_conferences(season, user_team)

    with league_tabs[tab_idx]:
        tab_idx += 1
        _render_postseason(season, user_team)

    with league_tabs[tab_idx]:
        tab_idx += 1
        _render_schedule(season, user_team)

    with league_tabs[tab_idx]:
        tab_idx += 1
        _render_awards_stats(season, standings, user_team)


def _team_label(name, user_team):
    if user_team and name == user_team:
        return f">>> {name}"
    return name


def _render_standings(season, standings, has_conferences, user_team):
    standings_data = []
    for i, record in enumerate(standings, 1):
        row = {
            "#": i,
            "Team": _team_label(record.team_name, user_team),
        }
        if has_conferences:
            row["Conf"] = record.conference
            row["Conf W-L"] = f"{record.conf_wins}-{record.conf_losses}"
        pi = season.calculate_power_index(record.team_name)
        row.update({
            "W": record.wins,
            "L": record.losses,
            "Win%": f"{record.win_percentage:.3f}",
            "PI": f"{pi:.1f}",
            "PF": fmt_vb_score(record.points_for),
            "PA": fmt_vb_score(record.points_against),
            "Diff": fmt_vb_score(record.point_differential),
            "OPI": f"{record.avg_opi:.1f}",
        })
        standings_data.append(row)
    st.dataframe(pd.DataFrame(standings_data), hide_index=True, use_container_width=True, height=600)


def _render_power_rankings(season, standings, user_team):
    if season.weekly_polls and len(season.weekly_polls) > 1:
        max_week = len(season.weekly_polls)
        selected_week = st.slider("Poll Week", min_value=1, max_value=max_week, value=max_week, key="league_poll_week_slider")
        poll = season.weekly_polls[selected_week - 1] if selected_week <= len(season.weekly_polls) else None
    else:
        poll = season.get_latest_poll()

    if poll:
        poll_data = []
        for r in poll.rankings:
            movement = ""
            if r.prev_rank is not None:
                diff = r.prev_rank - r.rank
                if diff > 0:
                    movement = f"+{diff}"
                elif diff < 0:
                    movement = str(diff)
                else:
                    movement = "--"
            else:
                movement = "NEW"
            poll_data.append({
                "#": r.rank,
                "Team": _team_label(r.team_name, user_team),
                "Record": r.record,
                "Conf": r.conference,
                "Power Index": f"{r.power_index:.1f}",
                "Quality Wins": r.quality_wins,
                "SOS Rank": r.sos_rank,
                "Move": movement,
            })
        st.dataframe(pd.DataFrame(poll_data), hide_index=True, use_container_width=True, height=600)
    else:
        st.caption("No rankings available yet.")

    with st.expander("Team Comparison Radar"):
        default_teams = []
        if len(standings) > 1:
            default_teams = [standings[0].team_name, standings[-1].team_name]
        elif standings:
            default_teams = [standings[0].team_name]
        radar_teams = st.multiselect("Compare Teams", [r.team_name for r in standings],
                                     default=default_teams, key="league_radar_teams")
        if radar_teams:
            categories = ["OPI", "Territory", "Pressure", "Chaos", "Kicking", "Drive Quality", "Turnover Impact"]
            fig = go.Figure()
            for tname in radar_teams:
                record = season.standings[tname]
                values = [record.avg_opi, record.avg_territory, record.avg_pressure,
                          record.avg_chaos, record.avg_kicking, record.avg_drive_quality * 10,
                          record.avg_turnover_impact]
                fig.add_trace(go.Scatterpolar(r=values + [values[0]], theta=categories + [categories[0]],
                                              fill='toself', name=tname))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                              title="Team Metrics Comparison", height=450, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)


def _render_conferences(season, user_team):
    champions = season.get_conference_champions()
    conf_tabs = st.tabs(sorted(season.conferences.keys()))
    for conf_tab, conf_name in zip(conf_tabs, sorted(season.conferences.keys())):
        with conf_tab:
            conf_standings = season.get_conference_standings(conf_name)
            if conf_standings:
                champ_name = champions.get(conf_name, "")
                if champ_name:
                    st.caption(f"Conference Champion: **{champ_name}**")
                conf_data = []
                for i, record in enumerate(conf_standings, 1):
                    pi = season.calculate_power_index(record.team_name)
                    conf_data.append({
                        "#": i,
                        "Team": _team_label(record.team_name, user_team),
                        "Conf": f"{record.conf_wins}-{record.conf_losses}",
                        "Overall": f"{record.wins}-{record.losses}",
                        "Win%": f"{record.win_percentage:.3f}",
                        "PI": f"{pi:.1f}",
                        "PF": fmt_vb_score(record.points_for),
                        "PA": fmt_vb_score(record.points_against),
                        "OPI": f"{record.avg_opi:.1f}",
                    })
                st.dataframe(pd.DataFrame(conf_data), hide_index=True, use_container_width=True)


def _render_postseason(season, user_team):
    if season.playoff_bracket:
        st.markdown("**Playoff Field**")
        num_playoff = len(set(g.home_team for g in season.playoff_bracket) | set(g.away_team for g in season.playoff_bracket))
        playoff_teams = season.get_playoff_teams(num_playoff)
        pf_data = []
        for i, t in enumerate(playoff_teams, 1):
            bid = season.get_playoff_bid_type(t.team_name)
            pi = season.calculate_power_index(t.team_name)
            pf_data.append({
                "Seed": i,
                "Team": _team_label(t.team_name, user_team),
                "Record": f"{t.wins}-{t.losses}",
                "Conf": t.conference,
                "Conf Record": f"{t.conf_wins}-{t.conf_losses}",
                "Power Index": f"{pi:.1f}",
                "Bid": bid.upper() if bid else "",
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
            round_games = [g for g in season.playoff_bracket if g.week == week]
            if round_games:
                st.markdown(f"*{label}*")
                for i, game in enumerate(round_games, 1):
                    hs = game.home_score or 0
                    aws = game.away_score or 0
                    winner = game.home_team if hs > aws else game.away_team
                    loser = game.away_team if hs > aws else game.home_team
                    w_score = max(hs, aws)
                    l_score = min(hs, aws)
                    prefix = ">>> " if user_team and user_team in (game.home_team, game.away_team) else ""
                    st.markdown(f"{prefix}Game {i}: **{winner}** {fmt_vb_score(w_score)} def. {loser} {fmt_vb_score(l_score)}")

        championship = [g for g in season.playoff_bracket if g.week == 1000]
        if championship:
            game = championship[0]
            hs = game.home_score or 0
            aws = game.away_score or 0
            winner = game.home_team if hs > aws else game.away_team
            loser = game.away_team if hs > aws else game.home_team
            w_score = max(hs, aws)
            l_score = min(hs, aws)
            st.success(f"**NATIONAL CHAMPIONS: {winner}** {fmt_vb_score(w_score)} def. {loser} {fmt_vb_score(l_score)}")
    else:
        st.caption("No playoffs ran this season.")

    if season.bowl_games:
        st.markdown("---")
        st.markdown("**Bowl Games**")
        current_tier = 0
        for bowl in season.bowl_games:
            if bowl.tier != current_tier:
                current_tier = bowl.tier
                tier_label = BOWL_TIERS.get(bowl.tier, "Standard")
                st.markdown(f"*{tier_label} Bowls*")
            g = bowl.game
            hs = g.home_score or 0
            aws = g.away_score or 0
            winner = g.home_team if hs > aws else g.away_team
            loser = g.away_team if hs > aws else g.home_team
            w_score = max(hs, aws)
            l_score = min(hs, aws)
            w_rec = bowl.team_1_record if winner == g.home_team else bowl.team_2_record
            l_rec = bowl.team_2_record if winner == g.home_team else bowl.team_1_record
            prefix = ">>> " if user_team and user_team in (g.home_team, g.away_team) else ""
            st.markdown(f"{prefix}**{bowl.name}**: **{winner}** ({w_rec}) {fmt_vb_score(w_score)} def. {loser} ({l_rec}) {fmt_vb_score(l_score)}")


def _render_schedule(season, user_team):
    all_game_entries = []
    for g in season.schedule:
        if g.completed:
            all_game_entries.append({"game": g, "phase": "Regular Season", "label_prefix": f"Wk {g.week}", "sort_key": g.week})

    if season.playoff_bracket:
        playoff_round_names = {996: "Opening Round", 997: "First Round", 998: "National Quarterfinals", 999: "National Semi-Finals", 1000: "National Championship"}
        for g in season.playoff_bracket:
            if g.completed:
                round_label = playoff_round_names.get(g.week, f"Playoff R{g.week}")
                all_game_entries.append({"game": g, "phase": "Playoff", "label_prefix": round_label, "sort_key": 900 + g.week})

    if season.bowl_games:
        for i, bowl in enumerate(season.bowl_games):
            bg = bowl.game
            if bg.completed:
                all_game_entries.append({"game": bg, "phase": "Bowl", "label_prefix": bowl.name, "sort_key": 800 + i})

    all_game_entries.sort(key=lambda e: e["sort_key"])

    all_teams_in_log = set()
    all_phases = set()
    for entry in all_game_entries:
        g = entry["game"]
        all_teams_in_log.add(g.home_team)
        all_teams_in_log.add(g.away_team)
        all_phases.add(entry["phase"])

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        team_options = ["All Teams"] + sorted(all_teams_in_log)
        if user_team:
            team_options = ["My Team", "All Teams"] + sorted(all_teams_in_log)
        filter_team = st.selectbox("Filter by Team", team_options, key="league_game_filter_team")
    with fc2:
        phase_options = ["All Phases"] + sorted(all_phases)
        filter_phase = st.selectbox("Filter by Phase", phase_options, key="league_game_filter_phase")
    with fc3:
        reg_weeks = sorted(set(g.week for g in season.schedule if g.completed))
        filter_week = st.selectbox("Filter by Week (Reg Season)", ["All Weeks"] + reg_weeks, key="league_game_filter_week")

    filtered_entries = all_game_entries
    if filter_team == "My Team" and user_team:
        filtered_entries = [e for e in filtered_entries if e["game"].home_team == user_team or e["game"].away_team == user_team]
    elif filter_team not in ("All Teams", "My Team"):
        filtered_entries = [e for e in filtered_entries if e["game"].home_team == filter_team or e["game"].away_team == filter_team]
    if filter_phase != "All Phases":
        filtered_entries = [e for e in filtered_entries if e["phase"] == filter_phase]
    if filter_week != "All Weeks":
        filtered_entries = [e for e in filtered_entries if e["phase"] == "Regular Season" and e["game"].week == filter_week]

    schedule_data = []
    game_labels = []
    filtered_games = []
    for entry in filtered_entries:
        g = entry["game"]
        hs = g.home_score or 0
        aws = g.away_score or 0
        winner = g.home_team if hs > aws else g.away_team
        schedule_data.append({
            "Phase": entry["phase"],
            "Round": entry["label_prefix"],
            "Home": _team_label(g.home_team, user_team),
            "Away": _team_label(g.away_team, user_team),
            "Home Score": fmt_vb_score(hs),
            "Away Score": fmt_vb_score(aws),
            "Winner": _team_label(winner, user_team),
        })
        game_labels.append(f"{entry['label_prefix']}: {g.home_team} {fmt_vb_score(hs)} vs {g.away_team} {fmt_vb_score(aws)}")
        filtered_games.append(g)

    if schedule_data:
        st.dataframe(pd.DataFrame(schedule_data), hide_index=True, use_container_width=True, height=300)

    if game_labels:
        selected_game_label = st.selectbox("Select a game to view details", game_labels, key="league_game_detail_select")
        game_idx = game_labels.index(selected_game_label)
        selected_game = filtered_games[game_idx]
        if selected_game.full_result:
            with st.expander("Game Details", expanded=True):
                render_game_detail(selected_game.full_result, key_prefix=f"league_gd_{game_idx}")
        else:
            st.caption("Detailed game data not available for this game.")


def _render_awards_stats(season, standings, user_team):
    try:
        season_honors = compute_season_awards(
            season, year=2025,
            conferences=season.conferences if hasattr(season, 'conferences') else None,
        )
        indiv_awards = season_honors.individual_awards
        if indiv_awards:
            st.markdown("**Individual Awards**")
            award_cols = st.columns(min(3, len(indiv_awards)))
            for i, award in enumerate(indiv_awards):
                col = award_cols[i % len(award_cols)]
                col.metric(
                    award.award_name,
                    f"{award.player_name}",
                    f"{award.team_name} — {award.position}"
                )
            st.markdown("---")
            st.markdown("**Team Awards**")
            team_aw1, team_aw2 = st.columns(2)
            if season_honors.coach_of_year:
                team_aw1.metric("Coach of the Year", season_honors.coach_of_year)
            if season_honors.most_improved:
                team_aw2.metric("Most Improved Program", season_honors.most_improved)
    except Exception:
        pass

    st.markdown("**Statistical Leaders**")
    leader_categories = [
        ("Highest Scoring", lambda r: r.points_for / max(1, r.games_played), "PPG"),
        ("Best Defense", lambda r: -(r.points_against / max(1, r.games_played)), "PA/G"),
        ("Top OPI", lambda r: r.avg_opi, "OPI"),
        ("Territory King", lambda r: r.avg_territory, "Territory"),
        ("Pressure Leader", lambda r: r.avg_pressure, "Pressure"),
        ("Chaos Master", lambda r: r.avg_chaos, "Chaos"),
        ("Kicking Leader", lambda r: r.avg_kicking, "Kicking"),
        ("Best Turnover Impact", lambda r: r.avg_turnover_impact, "TO Impact"),
    ]
    leader_rows = []
    for cat_name, key_func, stat_label in leader_categories:
        if cat_name == "Best Defense":
            leader = min(standings, key=lambda r: r.points_against / max(1, r.games_played))
            val = leader.points_against / max(1, leader.games_played)
        else:
            leader = max(standings, key=key_func)
            val = key_func(leader)
        leader_rows.append({
            "Category": cat_name,
            "Team": _team_label(leader.team_name, user_team),
            "Value": f"{abs(val):.1f}",
        })
    st.dataframe(pd.DataFrame(leader_rows), hide_index=True, use_container_width=True)

    with st.expander("Score Distribution"):
        score_data = []
        for game in season.schedule:
            if game.completed:
                score_data.append({"Team": game.home_team, "Score": game.home_score or 0, "Location": "Home"})
                score_data.append({"Team": game.away_team, "Score": game.away_score or 0, "Location": "Away"})
        if score_data:
            fig = px.box(pd.DataFrame(score_data), x="Team", y="Score", color="Team",
                         title="Score Distribution by Team")
            fig.update_layout(showlegend=False, height=400, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
