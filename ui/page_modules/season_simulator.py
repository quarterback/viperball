import io
import csv
import os
import random

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from engine.season import load_teams_from_directory, create_season, get_recommended_bowl_count, BOWL_TIERS
from engine.conference_names import generate_conference_names
from engine.ai_coach import auto_assign_all_teams, get_scheme_label, load_team_identity
from engine.geography import get_geographic_conference_defaults
from engine.awards import compute_season_awards
from ui.helpers import fmt_vb_score, render_game_detail, safe_filename


def render_season_simulator(shared):
    teams = shared["teams"]
    styles = shared["styles"]
    team_names = shared["team_names"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]
    OFFENSE_TOOLTIPS = shared["OFFENSE_TOOLTIPS"]
    DEFENSE_TOOLTIPS = shared["DEFENSE_TOOLTIPS"]

    st.title("Season Simulator")
    st.caption("Simulate a full round-robin season with standings, metrics, and playoffs")

    teams_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "teams")
    all_teams = load_teams_from_directory(teams_dir)
    all_team_names = sorted(all_teams.keys())

    st.subheader("Season Setup")
    season_name = st.text_input("Season Name", value="2026 CVL Season", key="season_name")

    selected_teams = st.multiselect("Select Teams", all_team_names, default=all_team_names, key="season_teams")

    if len(selected_teams) < 2:
        st.warning("Select at least 2 teams to run a season.")
    else:
        human_teams = st.multiselect(
            "Human-Controlled Teams (configure manually)", 
            selected_teams,
            default=[],
            max_selections=4,
            key="season_human_teams",
            help="Select teams you want to configure manually. All others get AI-assigned schemes."
        )
        
        ai_seed_col, reroll_col = st.columns([3, 1])
        with ai_seed_col:
            ai_seed = st.number_input("AI Coaching Seed (0 = random)", min_value=0, max_value=999999, value=0, key="season_ai_seed")
        with reroll_col:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Re-roll AI", key="reroll_ai_season"):
                st.session_state["season_ai_seed"] = random.randint(1, 999999)
                st.rerun()
        
        actual_seed = ai_seed if ai_seed > 0 else hash(season_name) % 999999
        
        teams_dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "teams")
        team_identities = load_team_identity(teams_dir_path)
        
        style_configs = {}
        
        if human_teams:
            st.subheader("Your Team Configuration")
            h_cols_per_row = min(len(human_teams), 3)
            h_chunks = [human_teams[i:i + h_cols_per_row] for i in range(0, len(human_teams), h_cols_per_row)]
            for chunk in h_chunks:
                cols = st.columns(len(chunk))
                for col, tname in zip(cols, chunk):
                    with col:
                        identity = team_identities.get(tname, {})
                        mascot = identity.get("mascot", "")
                        conf = identity.get("conference", "")
                        colors = identity.get("colors", [])
                        color_str = " / ".join(colors[:2]) if colors else ""
                        
                        st.markdown(f"**{tname}**")
                        if mascot or conf:
                            st.caption(f"{mascot} | {conf}" + (f" | {color_str}" if color_str else ""))
                        
                        off_style = st.selectbox("Offense", style_keys,
                                                  format_func=lambda x: styles[x]["label"],
                                                  key=f"season_off_{tname}")
                        def_style = st.selectbox("Defense", defense_style_keys,
                                                  format_func=lambda x: defense_styles[x]["label"],
                                                  key=f"season_def_{tname}")
                        style_configs[tname] = {"offense_style": off_style, "defense_style": def_style}
        
        ai_teams = [t for t in selected_teams if t not in human_teams]
        if ai_teams:
            ai_configs = auto_assign_all_teams(teams_dir_path, human_teams=human_teams, seed=actual_seed)
            
            with st.expander(f"AI Coach Assignments ({len(ai_teams)} teams)", expanded=False):
                ai_data = []
                for tname in sorted(ai_teams):
                    cfg = ai_configs.get(tname, {"offense_style": "balanced", "defense_style": "base_defense"})
                    style_configs[tname] = cfg
                    identity = team_identities.get(tname, {})
                    mascot = identity.get("mascot", "")
                    ai_data.append({
                        "Team": tname,
                        "Mascot": mascot,
                        "Offense": styles.get(cfg["offense_style"], {}).get("label", cfg["offense_style"]),
                        "Defense": defense_styles.get(cfg["defense_style"], {}).get("label", cfg["defense_style"]),
                        "Scheme": get_scheme_label(cfg["offense_style"], cfg["defense_style"]),
                    })
                st.dataframe(pd.DataFrame(ai_data), hide_index=True, use_container_width=True)
        
        for tname in selected_teams:
            if tname not in style_configs:
                style_configs[tname] = {"offense_style": "balanced", "defense_style": "base_defense"}

        auto_conferences = {}
        for tname in selected_teams:
            identity = team_identities.get(tname, {})
            conf = identity.get("conference", "")
            if conf:
                auto_conferences.setdefault(conf, []).append(tname)
        auto_conferences = {k: v for k, v in auto_conferences.items() if len(v) >= 2}

        if auto_conferences:
            with st.expander("Conference Names", expanded=False):
                st.caption("Edit conference names or click the button to generate new ones.")

                if "season_conf_seed" not in st.session_state:
                    st.session_state["season_conf_seed"] = None

                orig_conf_names = sorted(auto_conferences.keys())

                if st.session_state["season_conf_seed"] is not None:
                    gen_names = generate_conference_names(
                        count=len(orig_conf_names),
                        seed=st.session_state["season_conf_seed"],
                    )
                else:
                    gen_names = list(orig_conf_names)

                regen_col, _ = st.columns([1, 5])
                with regen_col:
                    if st.button("🎲 New Names", key="regen_season_conf"):
                        st.session_state["season_conf_seed"] = random.randint(0, 999999)
                        for ci2 in range(len(orig_conf_names)):
                            st.session_state.pop(f"season_conf_{ci2}", None)
                        st.rerun()

                conf_rename_map = {}
                conf_cols = st.columns(min(len(orig_conf_names), 4))
                for ci, old_name in enumerate(orig_conf_names):
                    with conf_cols[ci % len(conf_cols)]:
                        new_name = st.text_input(
                            old_name, value=gen_names[ci], key=f"season_conf_{ci}"
                        )
                        conf_rename_map[old_name] = new_name

                renamed_conferences = {}
                for old_name, team_list in auto_conferences.items():
                    new_name = conf_rename_map.get(old_name, old_name)
                    renamed_conferences[new_name] = team_list
                auto_conferences = renamed_conferences

        sched_col1, sched_col2 = st.columns(2)
        with sched_col1:
            season_games = st.slider("Regular Season Games Per Team", min_value=8, max_value=12, value=10, key="season_games_per_team")
        with sched_col2:
            playoff_options = [p for p in [4, 8, 12, 16, 24, 32] if p <= len(selected_teams)]
            if not playoff_options:
                playoff_options = [len(selected_teams)]
            playoff_size = st.radio("Playoff Format", playoff_options, index=0, key="playoff_size", horizontal=True)

        rec_bowls = get_recommended_bowl_count(len(selected_teams), playoff_size)
        bowl_count = st.slider("Number of Bowl Games", min_value=0, max_value=min(12, (len(selected_teams) - playoff_size) // 2), value=rec_bowls, key="season_bowl_count")

        run_season = st.button("Simulate Season", type="primary", use_container_width=True, key="run_season")

        if run_season:
            filtered_teams = {name: team for name, team in all_teams.items() if name in selected_teams}

            season = create_season(season_name, filtered_teams, style_configs,
                                   conferences=auto_conferences if auto_conferences else None,
                                   games_per_team=season_games)

            with st.spinner(f"Simulating {len(season.schedule)} games..."):
                season.simulate_season(generate_polls=True)

            num_playoff = playoff_size
            if num_playoff > 0 and len(selected_teams) >= num_playoff:
                with st.spinner("Running playoffs..."):
                    season.simulate_playoff(num_teams=min(num_playoff, len(selected_teams)))

            if bowl_count > 0:
                with st.spinner("Running bowl games..."):
                    season.simulate_bowls(bowl_count=bowl_count, playoff_size=num_playoff)

            st.session_state["last_season"] = season

        if "last_season" in st.session_state:
            season = st.session_state["last_season"]
            standings = season.get_standings_sorted()
            has_conferences = bool(season.conferences) and len(season.conferences) >= 1

            st.divider()

            total_games = sum(1 for g in season.schedule if g.completed)
            all_scores = []
            for g in season.schedule:
                if g.completed:
                    all_scores.extend([g.home_score or 0, g.away_score or 0])
            avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

            if season.champion:
                st.success(f"**Season Champion: {season.champion}**")

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
            tab_names.append("Postseason")
            tab_names.extend(["Awards & Stats", "Game Log", "Export"])
            season_tabs = st.tabs(tab_names)

            tab_idx = 0

            with season_tabs[tab_idx]:
                tab_idx += 1
                standings_data = []
                for i, record in enumerate(standings, 1):
                    row = {
                        "#": i,
                        "Team": record.team_name,
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

            with season_tabs[tab_idx]:
                tab_idx += 1
                final_poll = season.get_latest_poll()
                if final_poll:
                    poll_data = []
                    for r in final_poll.rankings:
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
                            "Team": r.team_name,
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
                    radar_teams = st.multiselect("Compare Teams", [r.team_name for r in standings],
                                                  default=[standings[0].team_name, standings[-1].team_name] if len(standings) > 1 else [standings[0].team_name],
                                                  key="radar_teams")
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

            if has_conferences:
                with season_tabs[tab_idx]:
                    tab_idx += 1
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
                                        "Team": record.team_name,
                                        "Conf": f"{record.conf_wins}-{record.conf_losses}",
                                        "Overall": f"{record.wins}-{record.losses}",
                                        "Win%": f"{record.win_percentage:.3f}",
                                        "PI": f"{pi:.1f}",
                                        "PF": fmt_vb_score(record.points_for),
                                        "PA": fmt_vb_score(record.points_against),
                                        "OPI": f"{record.avg_opi:.1f}",
                                    })
                                st.dataframe(pd.DataFrame(conf_data), hide_index=True, use_container_width=True)

            with season_tabs[tab_idx]:
                tab_idx += 1

                if season.playoff_bracket:
                    st.markdown("**Playoff Field**")
                    playoff_teams = season.get_playoff_teams(num_playoff)
                    pf_data = []
                    for i, t in enumerate(playoff_teams, 1):
                        bid = season.get_playoff_bid_type(t.team_name)
                        pi = season.calculate_power_index(t.team_name)
                        pf_data.append({
                            "Seed": i,
                            "Team": t.team_name,
                            "Record": f"{t.wins}-{t.losses}",
                            "Conf": t.conference,
                            "Conf Record": f"{t.conf_wins}-{t.conf_losses}",
                            "Power Index": f"{pi:.1f}",
                            "Bid": bid.upper() if bid else "",
                        })
                    st.dataframe(pd.DataFrame(pf_data), hide_index=True, use_container_width=True)

                    st.markdown("**Bracket Results**")

                    def _render_round(label, week):
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
                                st.markdown(f"Game {i}: **{winner}** {fmt_vb_score(w_score)} def. {loser} {fmt_vb_score(l_score)}")

                    _render_round("Opening Round", 996)
                    _render_round("First Round", 997)
                    _render_round("Quarterfinals", 998)
                    _render_round("Semifinals", 999)

                    championship = [g for g in season.playoff_bracket if g.week == 1000]
                    if championship:
                        game = championship[0]
                        hs = game.home_score or 0
                        aws = game.away_score or 0
                        winner = game.home_team if hs > aws else game.away_team
                        loser = game.away_team if hs > aws else game.home_team
                        w_score = max(hs, aws)
                        l_score = min(hs, aws)
                        st.success(f"**CHAMPION: {winner}** {fmt_vb_score(w_score)} def. {loser} {fmt_vb_score(l_score)}")
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
                        st.markdown(f"**{bowl.name}**: **{winner}** ({w_rec}) {fmt_vb_score(w_score)} def. {loser} ({l_rec}) {fmt_vb_score(l_score)}")

            with season_tabs[tab_idx]:
                tab_idx += 1

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
                        "Team": leader.team_name,
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

            with season_tabs[tab_idx]:
                tab_idx += 1

                all_game_entries = []
                for g in season.schedule:
                    if g.completed:
                        all_game_entries.append({"game": g, "phase": "Regular Season", "label_prefix": f"Wk {g.week}", "sort_key": g.week})

                if season.playoff_bracket:
                    playoff_round_names = {996: "Opening Round", 997: "First Round", 998: "Quarterfinals", 999: "Semifinals", 1000: "Championship"}
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

                game_filter_col1, game_filter_col2, game_filter_col3 = st.columns(3)
                with game_filter_col1:
                    filter_team = st.selectbox("Filter by Team", ["All Teams"] + sorted(all_teams_in_log), key="season_game_filter_team")
                with game_filter_col2:
                    phase_options = ["All Phases"] + sorted(all_phases)
                    filter_phase = st.selectbox("Filter by Phase", phase_options, key="season_game_filter_phase")
                with game_filter_col3:
                    reg_weeks = sorted(set(g.week for g in season.schedule if g.completed))
                    filter_week = st.selectbox("Filter by Week (Reg Season)", ["All Weeks"] + reg_weeks, key="season_game_filter_week")

                filtered_entries = all_game_entries
                if filter_team != "All Teams":
                    filtered_entries = [e for e in filtered_entries if e["game"].home_team == filter_team or e["game"].away_team == filter_team]
                if filter_phase != "All Phases":
                    filtered_entries = [e for e in filtered_entries if e["phase"] == filter_phase]
                if filter_week != "All Weeks":
                    filtered_entries = [e for e in filtered_entries if e["phase"] == "Regular Season" and e["game"].week == filter_week]

                game_labels = []
                filtered_games = []
                for entry in filtered_entries:
                    g = entry["game"]
                    hs = g.home_score or 0
                    aws = g.away_score or 0
                    game_labels.append(f"{entry['label_prefix']}: {g.home_team} {fmt_vb_score(hs)} vs {g.away_team} {fmt_vb_score(aws)}")
                    filtered_games.append(g)

                schedule_data = []
                for entry in filtered_entries:
                    g = entry["game"]
                    hs = g.home_score or 0
                    aws = g.away_score or 0
                    winner = g.home_team if hs > aws else g.away_team
                    schedule_data.append({
                        "Phase": entry["phase"],
                        "Round": entry["label_prefix"],
                        "Home": g.home_team,
                        "Away": g.away_team,
                        "Home Score": fmt_vb_score(hs),
                        "Away Score": fmt_vb_score(aws),
                        "Winner": winner,
                    })
                if schedule_data:
                    st.dataframe(pd.DataFrame(schedule_data), hide_index=True, use_container_width=True, height=300)

                if game_labels:
                    selected_game_label = st.selectbox("Select a game to view details", game_labels, key="season_game_detail_select")
                    game_idx = game_labels.index(selected_game_label)
                    selected_game = filtered_games[game_idx]
                    if selected_game.full_result:
                        with st.expander("Game Details", expanded=True):
                            render_game_detail(selected_game.full_result, key_prefix=f"season_gd_{game_idx}")
                    else:
                        st.caption("Detailed game data not available for this game.")

            with season_tabs[tab_idx]:
                tab_idx += 1

                st.markdown("Download season data in CSV format.")
                exp_col1, exp_col2 = st.columns(2)
                with exp_col1:
                    standings_csv = io.StringIO()
                    writer = csv.writer(standings_csv)
                    writer.writerow(["Rank", "Team", "W", "L", "Win%", "PF", "PA", "Diff", "OPI"])
                    for i, r in enumerate(standings, 1):
                        writer.writerow([i, r.team_name, r.wins, r.losses, f"{r.win_percentage:.3f}",
                                         fmt_vb_score(r.points_for), fmt_vb_score(r.points_against),
                                         fmt_vb_score(r.point_differential), f"{r.avg_opi:.1f}"])
                    st.download_button("Download Standings (CSV)", standings_csv.getvalue(),
                                       file_name="season_standings.csv", mime="text/csv",
                                       use_container_width=True)
                with exp_col2:
                    schedule_csv = io.StringIO()
                    writer = csv.writer(schedule_csv)
                    writer.writerow(["Week", "Home", "Away", "Home Score", "Away Score", "Winner"])
                    for game in season.schedule:
                        if game.completed:
                            hs = game.home_score or 0
                            aws = game.away_score or 0
                            winner = game.home_team if hs > aws else game.away_team
                            writer.writerow([game.week, game.home_team, game.away_team,
                                             fmt_vb_score(hs), fmt_vb_score(aws), winner])
                    st.download_button("Download Schedule (CSV)", schedule_csv.getvalue(),
                                       file_name="season_schedule.csv", mime="text/csv",
                                       use_container_width=True)
