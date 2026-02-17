import os
import random
import tempfile

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from engine.season import load_teams_from_directory, create_season, get_recommended_bowl_count, BOWL_TIERS
from engine.dynasty import create_dynasty, Dynasty
from engine.conference_names import generate_conference_names
from engine.geography import get_geographic_conference_defaults
from engine.injuries import InjuryTracker
from engine.awards import compute_season_awards
from engine.player_card import player_to_card
from engine.export import (
    export_season_standings_csv, export_season_game_log_csv,
    export_dynasty_standings_csv, export_dynasty_awards_csv,
    export_injury_history_csv, export_development_history_csv,
    export_all_american_csv, export_all_conference_csv,
)
from engine.ai_coach import auto_assign_all_teams, get_scheme_label, load_team_identity
from ui.helpers import fmt_vb_score, render_game_detail


def render_dynasty_mode(shared):
    teams = shared["teams"]
    styles = shared["styles"]
    team_names = shared["team_names"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]
    OFFENSE_TOOLTIPS = shared["OFFENSE_TOOLTIPS"]
    DEFENSE_TOOLTIPS = shared["DEFENSE_TOOLTIPS"]

    st.title("Dynasty Mode")
    st.caption("Multi-season career mode with historical tracking, awards, and record books")

    if "dynasty" not in st.session_state:
        st.subheader("Create New Dynasty")

        dynasty_col1, dynasty_col2 = st.columns(2)
        with dynasty_col1:
            dynasty_name = st.text_input("Dynasty Name", value="My Viperball Dynasty", key="dyn_name")
            coach_name = st.text_input("Coach Name", value="Coach", key="coach_name")
        with dynasty_col2:
            coach_team = st.selectbox("Your Team", [t["name"] for t in teams], key="coach_team")
            start_year = st.number_input("Starting Year", min_value=2020, max_value=2050, value=2026, key="start_year")

        st.divider()
        st.subheader("Conference Setup")
        teams_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "teams")
        setup_teams = load_teams_from_directory(teams_dir)
        all_team_names_sorted = sorted(setup_teams.keys())

        total_teams = len(all_team_names_sorted)
        max_conf = max(1, total_teams // 9)
        conf_options = list(range(1, min(max_conf + 1, 13)))
        default_idx = min(len(conf_options) - 1, max(0, total_teams // 12 - 1))
        num_conferences = st.select_slider(
            f"Number of Conferences ({total_teams} teams available)",
            options=conf_options,
            value=conf_options[default_idx],
            key="num_conf",
        )
        teams_per = total_teams // max(1, num_conferences)
        remainder = total_teams % max(1, num_conferences)
        size_note = f"~{teams_per} teams per conference" if remainder == 0 else f"~{teams_per}-{teams_per+1} teams per conference"
        st.caption(size_note)

        if "conf_name_seed" not in st.session_state:
            st.session_state["conf_name_seed"] = random.randint(0, 999999)

        if st.session_state.get("use_geo_names", True):
            geo_clusters = get_geographic_conference_defaults(teams_dir, all_team_names_sorted, num_conferences)
            generated_names = list(geo_clusters.keys())
            if len(generated_names) < num_conferences:
                generated_names.extend(generate_conference_names(count=num_conferences - len(generated_names), seed=st.session_state["conf_name_seed"]))
        else:
            generated_names = generate_conference_names(count=num_conferences, seed=st.session_state["conf_name_seed"])

        conf_assignments = {}
        conf_names_list = []

        name_col, btn_col = st.columns([5, 1])
        with btn_col:
            if st.button("🎲 New Names", key="regen_conf_names", use_container_width=True):
                st.session_state["conf_name_seed"] = random.randint(0, 999999)
                st.session_state["use_geo_names"] = False
                for ci2 in range(20):
                    st.session_state.pop(f"conf_name_{ci2}", None)
                st.rerun()

        if num_conferences == 1:
            with name_col:
                conf_name_single = st.text_input("Conference Name", value=generated_names[0], key="conf_name_0")
            conf_names_list = [conf_name_single]
            for tname in all_team_names_sorted:
                conf_assignments[tname] = conf_name_single
        else:
            cols_per_row = min(num_conferences, 4)
            for row_start in range(0, num_conferences, cols_per_row):
                row_end = min(row_start + cols_per_row, num_conferences)
                conf_cols = st.columns(row_end - row_start)
                for ci_offset, ci in enumerate(range(row_start, row_end)):
                    with conf_cols[ci_offset]:
                        cname = st.text_input(f"Conference {ci+1}", value=generated_names[ci], key=f"conf_name_{ci}")
                        conf_names_list.append(cname)

            geo_clusters = get_geographic_conference_defaults(teams_dir, all_team_names_sorted, num_conferences)
            geo_cluster_list = list(geo_clusters.values())
            default_splits = {}
            for ci in range(num_conferences):
                if ci < len(geo_cluster_list):
                    for tname in geo_cluster_list[ci]:
                        default_splits[tname] = conf_names_list[ci]
            for tname in all_team_names_sorted:
                if tname not in default_splits:
                    default_splits[tname] = conf_names_list[-1]

            with st.expander("Assign Teams to Conferences", expanded=False):
                assign_cols_per_row = 4
                assign_chunks = [all_team_names_sorted[i:i+assign_cols_per_row]
                                 for i in range(0, len(all_team_names_sorted), assign_cols_per_row)]
                for achunk in assign_chunks:
                    acols = st.columns(len(achunk))
                    for acol, tname in zip(acols, achunk):
                        with acol:
                            default_idx = conf_names_list.index(default_splits.get(tname, conf_names_list[0]))
                            assigned = st.selectbox(tname[:20], conf_names_list, index=default_idx,
                                                     key=f"conf_assign_{tname}")
                            conf_assignments[tname] = assigned

        st.divider()
        load_col1, load_col2 = st.columns(2)
        with load_col1:
            create_btn = st.button("Create Dynasty", type="primary", use_container_width=True, key="create_dynasty")
        with load_col2:
            uploaded = st.file_uploader("Load Saved Dynasty", type=["json"], key="load_dynasty")

        if create_btn:
            dynasty = create_dynasty(dynasty_name, coach_name, coach_team, start_year)
            conf_team_lists = {}
            for tname, cname in conf_assignments.items():
                if cname not in conf_team_lists:
                    conf_team_lists[cname] = []
                conf_team_lists[cname].append(tname)
            for cname, cteams in conf_team_lists.items():
                dynasty.add_conference(cname, cteams)
            st.session_state["dynasty"] = dynasty
            st.session_state["dynasty_teams"] = setup_teams
            st.rerun()

        if uploaded:
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                    tmp.write(uploaded.read().decode())
                    tmp_path = tmp.name
                dynasty = Dynasty.load(tmp_path)
                all_teams_loaded = load_teams_from_directory(teams_dir)
                st.session_state["dynasty"] = dynasty
                st.session_state["dynasty_teams"] = all_teams_loaded
                os.unlink(tmp_path)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to load dynasty: {e}")

    else:
        dynasty = st.session_state["dynasty"]
        all_dynasty_teams = st.session_state["dynasty_teams"]

        st.sidebar.divider()
        st.sidebar.markdown(f"**Dynasty:** {dynasty.dynasty_name}")
        st.sidebar.markdown(f"**Coach:** {dynasty.coach.name}")
        st.sidebar.markdown(f"**Team:** {dynasty.coach.team_name}")
        st.sidebar.markdown(f"**Year:** {dynasty.current_year}")
        st.sidebar.markdown(f"**Record:** {dynasty.coach.career_wins}-{dynasty.coach.career_losses}")
        st.sidebar.markdown(f"**Titles:** {dynasty.coach.championships}")

        if st.sidebar.button("End Dynasty", key="end_dynasty"):
            del st.session_state["dynasty"]
            del st.session_state["dynasty_teams"]
            for key in ["last_dynasty_season", "last_dynasty_injury_tracker"]:
                st.session_state.pop(key, None)
            st.rerun()

        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
            "Simulate Season", "Standings & Polls", "Coach Dashboard", "Team History",
            "Record Book", "Awards & Honors", "Injury Report", "Development", "CSV Export"
        ])

        with tab1:
            st.subheader(f"Season {dynasty.current_year}")

            setup_col1, setup_col2 = st.columns(2)
            with setup_col1:
                total_teams = len(all_dynasty_teams)
                games_per_team = st.slider(
                    "Regular Season Games Per Team",
                    min_value=8, max_value=12, value=10,
                    key=f"dyn_games_{dynasty.current_year}"
                )
            with setup_col2:
                dyn_playoff_options = [p for p in [4, 8, 12, 16, 24, 32] if p <= total_teams]
                if not dyn_playoff_options:
                    dyn_playoff_options = [total_teams]
                playoff_format = st.radio("Playoff Format", dyn_playoff_options, index=0, horizontal=True,
                                          key=f"dyn_playoff_{dynasty.current_year}")

            dyn_rec = get_recommended_bowl_count(total_teams, playoff_format)
            dyn_max_bowls = max(0, (total_teams - playoff_format) // 2)
            dyn_bowl_count = st.slider("Number of Bowl Games", min_value=0, max_value=min(12, dyn_max_bowls), value=min(dyn_rec, min(12, dyn_max_bowls)),
                                        key=f"dyn_bowls_{dynasty.current_year}")

            teams_dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "teams")
            team_identities = load_team_identity(teams_dir_path)
            
            st.markdown("**Your Team**")
            user_team = dynasty.coach.team_name
            user_identity = team_identities.get(user_team, {})
            user_mascot = user_identity.get("mascot", "")
            user_conf = user_identity.get("conference", "")
            user_colors = user_identity.get("colors", [])
            user_color_str = " / ".join(user_colors[:2]) if user_colors else ""
            
            if user_mascot or user_conf:
                st.caption(f"{user_mascot} | {user_conf}" + (f" | {user_color_str}" if user_color_str else ""))
            
            user_off_col, user_def_col = st.columns(2)
            with user_off_col:
                user_off = st.selectbox("Offense Style", style_keys, format_func=lambda x: styles[x]["label"],
                                         key=f"dyn_user_off_{dynasty.current_year}")
            with user_def_col:
                user_def = st.selectbox("Defense Style", defense_style_keys,
                                         format_func=lambda x: defense_styles[x]["label"],
                                         key=f"dyn_user_def_{dynasty.current_year}")
            
            ai_seed = hash(f"{dynasty.dynasty_name}_{dynasty.current_year}") % 999999
            ai_configs = auto_assign_all_teams(
                teams_dir_path,
                human_teams=[user_team],
                human_configs={user_team: {"offense_style": user_off, "defense_style": user_def}},
                seed=ai_seed,
            )
            
            dyn_style_configs = {}
            dyn_style_configs[user_team] = {"offense_style": user_off, "defense_style": user_def}
            for tname in all_dynasty_teams:
                if tname != user_team:
                    dyn_style_configs[tname] = ai_configs.get(tname, {"offense_style": "balanced", "defense_style": "base_defense"})
            
            ai_opponent_teams = sorted([t for t in all_dynasty_teams if t != user_team])
            with st.expander(f"AI Coach Assignments ({len(ai_opponent_teams)} teams)", expanded=False):
                ai_data = []
                for tname in ai_opponent_teams:
                    cfg = dyn_style_configs[tname]
                    identity = team_identities.get(tname, {})
                    mascot = identity.get("mascot", "")
                    ai_data.append({
                        "Team": tname,
                        "Mascot": mascot,
                        "Offense": styles.get(cfg["offense_style"], {}).get("label", cfg["offense_style"]),
                        "Defense": defense_styles.get(cfg["defense_style"], {}).get("label", cfg["defense_style"]),
                    })
                st.dataframe(pd.DataFrame(ai_data), hide_index=True, use_container_width=True)

            if st.button(f"Simulate {dynasty.current_year} Season", type="primary", use_container_width=True, key="sim_dynasty_season"):
                conf_dict = dynasty.get_conferences_dict()
                season = create_season(
                    f"{dynasty.current_year} CVL Season",
                    all_dynasty_teams,
                    dyn_style_configs,
                    conferences=conf_dict,
                    games_per_team=games_per_team
                )

                total_games = len(season.schedule)
                injury_tracker = InjuryTracker()
                injury_tracker.seed(hash(f"{dynasty.dynasty_name}_{dynasty.current_year}_inj") % 999999)

                with st.spinner(f"Simulating {dynasty.current_year} season ({total_games} games, {games_per_team}/team)..."):
                    season.simulate_season(generate_polls=True)

                    max_week = max((g.week for g in season.schedule if g.completed), default=0)
                    for wk in range(1, max_week + 1):
                        injury_tracker.process_week(wk, season.teams, season.standings)
                        injury_tracker.resolve_week(wk)

                playoff_count = min(playoff_format, len(all_dynasty_teams))
                if playoff_count >= 4:
                    with st.spinner("Running playoffs..."):
                        season.simulate_playoff(num_teams=playoff_count)

                if dyn_bowl_count > 0:
                    with st.spinner("Running bowl games..."):
                        season.simulate_bowls(bowl_count=dyn_bowl_count, playoff_size=playoff_count)

                player_cards = {}
                for t_name, t_obj in season.teams.items():
                    player_cards[t_name] = [player_to_card(p, t_name) for p in t_obj.players]

                dynasty.advance_season(season, injury_tracker=injury_tracker, player_cards=player_cards)
                st.session_state["dynasty"] = dynasty
                st.session_state["last_dynasty_season"] = season
                st.session_state["last_dynasty_injury_tracker"] = injury_tracker
                st.rerun()

            if "last_dynasty_season" in st.session_state:
                season = st.session_state["last_dynasty_season"]
                prev_year = dynasty.current_year - 1

                st.divider()
                st.subheader(f"{prev_year} Season Results")

                if season.champion:
                    if season.champion == dynasty.coach.team_name:
                        st.balloons()
                        st.success(f"YOUR TEAM {season.champion} WON THE CHAMPIONSHIP!")
                    else:
                        st.info(f"Champion: {season.champion}")

                standings = season.get_standings_sorted()
                standings_data = []
                for i, record in enumerate(standings, 1):
                    is_user = record.team_name == dynasty.coach.team_name
                    pi = season.calculate_power_index(record.team_name)
                    standings_data.append({
                        "Rank": i,
                        "Team": f"{'>>> ' if is_user else ''}{record.team_name}",
                        "Conf": record.conference,
                        "W": record.wins,
                        "L": record.losses,
                        "Conf W-L": f"{record.conf_wins}-{record.conf_losses}",
                        "Win%": f"{record.win_percentage:.3f}",
                        "PI": f"{pi:.1f}",
                        "PF": fmt_vb_score(record.points_for),
                        "PA": fmt_vb_score(record.points_against),
                        "OPI": f"{record.avg_opi:.1f}",
                    })
                st.dataframe(pd.DataFrame(standings_data), hide_index=True, use_container_width=True, height=400)

                if season.bowl_games:
                    st.subheader("Bowl Games")
                    dyn_current_tier = 0
                    for bowl in season.bowl_games:
                        if bowl.tier != dyn_current_tier:
                            dyn_current_tier = bowl.tier
                            tier_label = BOWL_TIERS.get(bowl.tier, "Standard")
                            st.markdown(f"**{tier_label} Bowls**")
                        g = bowl.game
                        hs = g.home_score or 0
                        aws = g.away_score or 0
                        winner = g.home_team if hs > aws else g.away_team
                        loser = g.away_team if hs > aws else g.home_team
                        w_score = max(hs, aws)
                        l_score = min(hs, aws)
                        w_rec = bowl.team_1_record if winner == g.home_team else bowl.team_2_record
                        l_rec = bowl.team_2_record if winner == g.home_team else bowl.team_1_record
                        is_user_bowl = dynasty.coach.team_name in (g.home_team, g.away_team)
                        prefix = ">>> " if is_user_bowl else ""
                        st.markdown(f"{prefix}**{bowl.name}**: **{winner}** ({w_rec}) {fmt_vb_score(w_score)} def. {loser} ({l_rec}) {fmt_vb_score(l_score)}")

                st.subheader("Game Log")
                dyn_all_entries = []
                for g in season.schedule:
                    if g.completed:
                        dyn_all_entries.append({"game": g, "phase": "Regular Season", "label_prefix": f"Wk {g.week}", "sort_key": g.week})

                if season.playoff_bracket:
                    playoff_round_names = {996: "Opening Round", 997: "First Round", 998: "Quarterfinals", 999: "Semifinals", 1000: "Championship"}
                    for g in season.playoff_bracket:
                        if g.completed:
                            round_label = playoff_round_names.get(g.week, f"Playoff R{g.week}")
                            dyn_all_entries.append({"game": g, "phase": "Playoff", "label_prefix": round_label, "sort_key": 900 + g.week})

                if season.bowl_games:
                    for i, bowl in enumerate(season.bowl_games):
                        bg = bowl.game
                        if bg.completed:
                            dyn_all_entries.append({"game": bg, "phase": "Bowl", "label_prefix": bowl.name, "sort_key": 800 + i})

                dyn_all_entries.sort(key=lambda e: e["sort_key"])

                dyn_teams_in_log = set()
                dyn_phases = set()
                for entry in dyn_all_entries:
                    g = entry["game"]
                    dyn_teams_in_log.add(g.home_team)
                    dyn_teams_in_log.add(g.away_team)
                    dyn_phases.add(entry["phase"])

                dyn_fc1, dyn_fc2, dyn_fc3 = st.columns(3)
                with dyn_fc1:
                    dyn_filter_team = st.selectbox("Filter by Team", ["My Team", "All Teams"] + sorted(dyn_teams_in_log), key="dyn_game_filter_team")
                with dyn_fc2:
                    dyn_phase_options = ["All Phases"] + sorted(dyn_phases)
                    dyn_filter_phase = st.selectbox("Filter by Phase", dyn_phase_options, key="dyn_game_filter_phase")
                with dyn_fc3:
                    dyn_reg_weeks = sorted(set(g.week for g in season.schedule if g.completed))
                    dyn_filter_week = st.selectbox("Filter by Week (Reg Season)", ["All Weeks"] + dyn_reg_weeks, key="dyn_game_filter_week")

                dyn_filtered_entries = dyn_all_entries
                if dyn_filter_team == "My Team":
                    my_team = dynasty.coach.team_name
                    dyn_filtered_entries = [e for e in dyn_filtered_entries if e["game"].home_team == my_team or e["game"].away_team == my_team]
                elif dyn_filter_team != "All Teams":
                    dyn_filtered_entries = [e for e in dyn_filtered_entries if e["game"].home_team == dyn_filter_team or e["game"].away_team == dyn_filter_team]
                if dyn_filter_phase != "All Phases":
                    dyn_filtered_entries = [e for e in dyn_filtered_entries if e["phase"] == dyn_filter_phase]
                if dyn_filter_week != "All Weeks":
                    dyn_filtered_entries = [e for e in dyn_filtered_entries if e["phase"] == "Regular Season" and e["game"].week == dyn_filter_week]

                dyn_game_labels = []
                dyn_filtered_games = []
                for entry in dyn_filtered_entries:
                    g = entry["game"]
                    hs = g.home_score or 0
                    aws = g.away_score or 0
                    dyn_game_labels.append(f"{entry['label_prefix']}: {g.home_team} {fmt_vb_score(hs)} vs {g.away_team} {fmt_vb_score(aws)}")
                    dyn_filtered_games.append(g)

                if dyn_game_labels:
                    dyn_sel = st.selectbox("Select a game to view details", dyn_game_labels, key="dyn_game_detail_select")
                    dyn_gi = dyn_game_labels.index(dyn_sel)
                    dyn_sg = dyn_filtered_games[dyn_gi]
                    if dyn_sg.full_result:
                        with st.expander("Game Details", expanded=True):
                            render_game_detail(dyn_sg.full_result, key_prefix=f"dyn_gd_{dyn_gi}")
                    else:
                        st.caption("Detailed game data not available for this game.")
                elif dyn_all_entries:
                    st.caption("No games match the current filter.")

        with tab2:
            st.subheader("Standings & Weekly Poll")

            if "last_dynasty_season" in st.session_state:
                season = st.session_state["last_dynasty_season"]
                prev_year = dynasty.current_year - 1

                view_mode = st.radio("View", ["Conference Standings", "Weekly Poll"], horizontal=True, key="standings_view")

                if view_mode == "Conference Standings":
                    conf_names = list(season.conferences.keys())
                    if conf_names:
                        champions = season.get_conference_champions()
                        for conf_name in sorted(conf_names):
                            champ = champions.get(conf_name, "")
                            champ_label = f" — Champion: {champ}" if champ else ""
                            st.subheader(f"{conf_name}{champ_label}")
                            conf_standings = season.get_conference_standings(conf_name)
                            if conf_standings:
                                conf_data = []
                                for i, record in enumerate(conf_standings, 1):
                                    is_user = record.team_name == dynasty.coach.team_name
                                    pi = season.calculate_power_index(record.team_name)
                                    conf_data.append({
                                        "Rank": i,
                                        "Team": f"{'>>> ' if is_user else ''}{record.team_name}",
                                        "Conf": f"{record.conf_wins}-{record.conf_losses}",
                                        "Overall": f"{record.wins}-{record.losses}",
                                        "Win%": f"{record.win_percentage:.3f}",
                                        "PI": f"{pi:.1f}",
                                        "PF": fmt_vb_score(record.points_for),
                                        "PA": fmt_vb_score(record.points_against),
                                        "OPI": f"{record.avg_opi:.1f}",
                                    })
                                st.dataframe(pd.DataFrame(conf_data), hide_index=True, use_container_width=True)
                    else:
                        st.caption("No conferences configured")

                elif view_mode == "Weekly Poll":
                    if season.weekly_polls:
                        total_weeks = len(season.weekly_polls)
                        selected_week_idx = st.slider("Select Week", 1, total_weeks, total_weeks,
                                                       key="poll_week_slider")
                        poll = season.weekly_polls[selected_week_idx - 1]

                        st.subheader(f"CVL Power Rankings - Week {poll.week}")

                        poll_data = []
                        for r in poll.rankings:
                            change_str = ""
                            if r.rank_change is not None:
                                if r.rank_change > 0:
                                    change_str = f"+{r.rank_change}"
                                elif r.rank_change < 0:
                                    change_str = str(r.rank_change)
                                else:
                                    change_str = "-"
                            else:
                                change_str = "NEW"
                            is_user = r.team_name == dynasty.coach.team_name
                            poll_data.append({
                                "#": r.rank,
                                "Team": f"{'>>> ' if is_user else ''}{r.team_name}",
                                "Record": r.record,
                                "Conf": r.conference,
                                "Power Index": f"{r.power_index:.1f}",
                                "Quality Wins": r.quality_wins,
                                "SOS Rank": r.sos_rank,
                                "Change": change_str,
                            })
                        st.dataframe(pd.DataFrame(poll_data), hide_index=True, use_container_width=True, height=600)

                        if total_weeks >= 2:
                            st.subheader("Poll Movement")
                            track_teams = st.multiselect("Track Teams",
                                                          [r.team_name for r in season.weekly_polls[-1].rankings[:10]],
                                                          default=[dynasty.coach.team_name] if dynasty.coach.team_name in
                                                                   [r.team_name for r in season.weekly_polls[-1].rankings[:25]] else [],
                                                          key="poll_track")
                            if track_teams:
                                movement_data = []
                                for poll in season.weekly_polls:
                                    for r in poll.rankings:
                                        if r.team_name in track_teams:
                                            movement_data.append({
                                                "Week": poll.week,
                                                "Team": r.team_name,
                                                "Rank": r.rank,
                                            })
                                if movement_data:
                                    fig = px.line(pd.DataFrame(movement_data), x="Week", y="Rank",
                                                  color="Team", title="Poll Ranking Over Season",
                                                  markers=True)
                                    fig.update_yaxes(autorange="reversed", title="Rank (#1 = top)")
                                    fig.update_layout(height=400)
                                    st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.caption("No polls generated yet. Simulate a season first.")
            else:
                st.caption("Simulate a season to see standings and polls.")

        with tab3:
            st.subheader("Coach Career Dashboard")
            coach = dynasty.coach

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Career Record", f"{coach.career_wins}-{coach.career_losses}")
            c2.metric("Win%", f"{coach.win_percentage * 100:.1f}%")
            c3.metric("Championships", str(coach.championships))
            c4.metric("Seasons", str(coach.years_experience))

            if coach.season_records:
                st.subheader("Season-by-Season")
                season_hist = []
                for year in sorted(coach.season_records.keys()):
                    rec = coach.season_records[year]
                    season_hist.append({
                        "Year": year,
                        "W-L": f"{rec['wins']}-{rec['losses']}",
                        "PF": fmt_vb_score(rec['points_for']),
                        "PA": fmt_vb_score(rec['points_against']),
                        "Playoff": "Yes" if rec.get("playoff") else "No",
                        "Champion": "Yes" if rec.get("champion") else "No",
                    })
                st.dataframe(pd.DataFrame(season_hist), hide_index=True, use_container_width=True)

                years = sorted(coach.season_records.keys())
                wins = [coach.season_records[y]["wins"] for y in years]
                fig = px.bar(x=years, y=wins, title="Wins Per Season", labels={"x": "Year", "y": "Wins"})
                st.plotly_chart(fig, use_container_width=True)

        with tab4:
            st.subheader("Team History")
            selected_history_team = st.selectbox("Select Team", sorted(dynasty.team_histories.keys()), key="history_team")

            if selected_history_team in dynasty.team_histories:
                hist = dynasty.team_histories[selected_history_team]

                h1, h2, h3, h4 = st.columns(4)
                h1.metric("All-Time Record", f"{hist.total_wins}-{hist.total_losses}")
                h2.metric("Win%", f"{hist.win_percentage * 100:.1f}%")
                h3.metric("Championships", str(hist.total_championships))
                h4.metric("Playoff Apps", str(hist.total_playoff_appearances))

                if hist.championship_years:
                    st.markdown(f"**Championship Years:** {', '.join(str(y) for y in hist.championship_years)}")

                if hist.season_records:
                    st.subheader("Season Records")
                    hist_data = []
                    for year in sorted(hist.season_records.keys()):
                        rec = hist.season_records[year]
                        hist_data.append({
                            "Year": year,
                            "W-L": f"{rec['wins']}-{rec['losses']}",
                            "PF": fmt_vb_score(rec['points_for']),
                            "PA": fmt_vb_score(rec['points_against']),
                            "OPI": f"{rec.get('avg_opi', 0):.1f}",
                            "Champion": "Yes" if rec.get("champion") else "No",
                        })
                    st.dataframe(pd.DataFrame(hist_data), hide_index=True, use_container_width=True)

        with tab5:
            st.subheader("Record Book")
            rb = dynasty.record_book

            st.markdown("**Single-Season Records**")
            rec_data = []
            if rb.most_wins_season.get("team"):
                rec_data.append({"Record": "Most Wins", "Team": rb.most_wins_season["team"],
                                 "Value": str(rb.most_wins_season["wins"]), "Year": str(rb.most_wins_season.get("year", ""))})
            if rb.most_points_season.get("team"):
                rec_data.append({"Record": "Most Points", "Team": rb.most_points_season["team"],
                                 "Value": f"{rb.most_points_season['points']:.1f}", "Year": str(rb.most_points_season.get("year", ""))})
            if rb.best_defense_season.get("team"):
                rec_data.append({"Record": "Best Defense (PPG)", "Team": rb.best_defense_season["team"],
                                 "Value": f"{rb.best_defense_season['ppg_allowed']:.1f}", "Year": str(rb.best_defense_season.get("year", ""))})
            if rb.highest_opi_season.get("team"):
                rec_data.append({"Record": "Highest OPI", "Team": rb.highest_opi_season["team"],
                                 "Value": f"{rb.highest_opi_season['opi']:.1f}", "Year": str(rb.highest_opi_season.get("year", ""))})
            if rb.most_chaos_season.get("team"):
                rec_data.append({"Record": "Most Chaos", "Team": rb.most_chaos_season["team"],
                                 "Value": f"{rb.most_chaos_season['chaos']:.1f}", "Year": str(rb.most_chaos_season.get("year", ""))})
            if rec_data:
                st.dataframe(pd.DataFrame(rec_data), hide_index=True, use_container_width=True)
            else:
                st.caption("No records yet - simulate some seasons!")

            st.markdown("**All-Time Records**")
            alltime_data = []
            if rb.most_championships.get("team"):
                alltime_data.append({"Record": "Most Championships", "Team/Coach": rb.most_championships["team"],
                                     "Value": str(rb.most_championships["championships"])})
            if rb.highest_win_percentage.get("team"):
                alltime_data.append({"Record": "Highest Win%", "Team/Coach": rb.highest_win_percentage["team"],
                                     "Value": f"{rb.highest_win_percentage['win_pct']:.3f}"})
            if rb.most_coaching_wins.get("coach"):
                alltime_data.append({"Record": "Most Coaching Wins", "Team/Coach": rb.most_coaching_wins["coach"],
                                     "Value": str(rb.most_coaching_wins["wins"])})
            if rb.most_coaching_championships.get("coach"):
                alltime_data.append({"Record": "Most Coaching Titles", "Team/Coach": rb.most_coaching_championships["coach"],
                                     "Value": str(rb.most_coaching_championships["championships"])})
            if alltime_data:
                st.dataframe(pd.DataFrame(alltime_data), hide_index=True, use_container_width=True)
            else:
                st.caption("Play more seasons to build records!")

            if dynasty.awards_history:
                st.markdown("**Awards History**")
                awards_data = []
                for year in sorted(dynasty.awards_history.keys()):
                    awards = dynasty.awards_history[year]
                    awards_data.append({
                        "Year": year,
                        "Champion": awards.champion,
                        "Best Record": awards.best_record,
                        "Top Scoring": awards.highest_scoring,
                        "Best Defense": awards.best_defense,
                        "Highest OPI": awards.highest_opi,
                    })
                st.dataframe(pd.DataFrame(awards_data), hide_index=True, use_container_width=True)

            st.divider()
            save_col1, save_col2 = st.columns(2)
            with save_col1:
                if st.button("Save Dynasty", use_container_width=True, key="save_dynasty"):
                    save_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dynasty_save.json")
                    dynasty.save(save_path)
                    st.success(f"Dynasty saved!")
            with save_col2:
                save_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dynasty_save.json")
                if os.path.exists(save_path):
                    with open(save_path, 'r') as f:
                        st.download_button("Download Save File", f.read(),
                                           file_name=f"{dynasty.dynasty_name.replace(' ', '_')}.json",
                                           mime="application/json")

        with tab6:
            st.subheader("Awards & Honors")
            if dynasty.honors_history:
                available_award_years = sorted(dynasty.honors_history.keys(), reverse=True)
                selected_award_year = st.selectbox("Select Season", available_award_years, key="award_year_select")
                honors = dynasty.honors_history.get(selected_award_year, {})

                if honors:
                    st.markdown(f"### {selected_award_year} Individual Awards")
                    indiv = honors.get("individual_awards", [])
                    if indiv:
                        award_rows = []
                        for a in indiv:
                            award_rows.append({
                                "Award": a.get("award_name", ""),
                                "Player": a.get("player_name", ""),
                                "Position": a.get("position", ""),
                                "Year": a.get("year_in_school", ""),
                                "Team": a.get("team_name", ""),
                                "OVR": a.get("overall_rating", 0),
                            })
                        st.dataframe(pd.DataFrame(award_rows), hide_index=True, use_container_width=True)

                    coy = honors.get("coach_of_year", "")
                    improved = honors.get("most_improved", "")
                    if coy or improved:
                        tc1, tc2 = st.columns(2)
                        if coy:
                            tc1.metric("Coach of the Year", coy)
                        if improved:
                            tc2.metric("Most Improved Program", improved)

                    aa_tiers = [
                        ("all_american_first", "1st Team All-CVL"),
                        ("all_american_second", "2nd Team All-CVL"),
                        ("all_american_third", "3rd Team All-CVL"),
                        ("honorable_mention", "Honorable Mention"),
                        ("all_freshman", "All-Freshman Team"),
                    ]
                    for tier_key, tier_label in aa_tiers:
                        team_data = honors.get(tier_key)
                        if team_data and team_data.get("slots"):
                            st.markdown(f"### {tier_label}")
                            slot_rows = []
                            for slot in team_data["slots"]:
                                slot_rows.append({
                                    "Position": slot.get("award_name", ""),
                                    "Player": slot.get("player_name", ""),
                                    "Year": slot.get("year_in_school", "")[:2] if slot.get("year_in_school") else "",
                                    "Team": slot.get("team_name", ""),
                                    "OVR": slot.get("overall_rating", 0),
                                })
                            st.dataframe(pd.DataFrame(slot_rows), hide_index=True, use_container_width=True)

                    all_conf = honors.get("all_conference_teams", {})
                    if all_conf:
                        st.markdown(f"### All-Conference Teams")
                        conf_names_list_awards = list(all_conf.keys())
                        selected_conf_award = st.selectbox("Conference", conf_names_list_awards, key="conf_award_select")
                        conf_tiers = all_conf.get(selected_conf_award, {})
                        for tier_key, tier_label in [("first", "1st Team"), ("second", "2nd Team")]:
                            conf_data = conf_tiers.get(tier_key)
                            if conf_data:
                                slots = conf_data.get("slots", []) if isinstance(conf_data, dict) else []
                                if slots:
                                    st.markdown(f"**{selected_conf_award} - {tier_label} All-Conference**")
                                    conf_slot_rows = []
                                    for slot in slots:
                                        conf_slot_rows.append({
                                            "Position": slot.get("award_name", ""),
                                            "Player": slot.get("player_name", ""),
                                            "Year": slot.get("year_in_school", "")[:2] if slot.get("year_in_school") else "",
                                            "Team": slot.get("team_name", ""),
                                            "OVR": slot.get("overall_rating", 0),
                                        })
                                    st.dataframe(pd.DataFrame(conf_slot_rows), hide_index=True, use_container_width=True)

                    if len(available_award_years) > 1:
                        st.divider()
                        st.markdown("### Award Winners Across Seasons")
                        mvp_history = []
                        for yr in sorted(dynasty.honors_history.keys()):
                            h = dynasty.honors_history[yr]
                            mvp_name = ""
                            best_zb = ""
                            best_vp = ""
                            best_def = ""
                            best_kick = ""
                            best_lat = ""
                            for a in h.get("individual_awards", []):
                                n = a.get("award_name", "")
                                p = a.get("player_name", "")
                                t = a.get("team_name", "")
                                label = f"{p} ({t})" if p else ""
                                if n == "CVL MVP":
                                    mvp_name = label
                                elif n == "Best Zeroback":
                                    best_zb = label
                                elif n == "Best Viper":
                                    best_vp = label
                                elif n == "Best Lateral Specialist":
                                    best_lat = label
                                elif n == "Best Defensive Player":
                                    best_def = label
                                elif n == "Best Kicker":
                                    best_kick = label
                            mvp_history.append({
                                "Year": yr,
                                "CVL MVP": mvp_name,
                                "Best ZB": best_zb,
                                "Best Viper": best_vp,
                                "Best Lat": best_lat,
                                "Best Def": best_def,
                                "Best Kicker": best_kick,
                                "Coach of Year": h.get("coach_of_year", ""),
                            })
                        st.dataframe(pd.DataFrame(mvp_history), hide_index=True, use_container_width=True)
            else:
                st.caption("No awards recorded yet. Simulate a season first.")

        with tab7:
            st.subheader("Injury Report")
            if dynasty.injury_history:
                available_inj_years = sorted(dynasty.injury_history.keys(), reverse=True)
                selected_inj_year = st.selectbox("Select Season", available_inj_years, key="inj_year_select")
                report = dynasty.injury_history.get(selected_inj_year, {})

                if report:
                    total_injuries = sum(len(v) for v in report.values())
                    tier_counts = {"minor": 0, "moderate": 0, "severe": 0}
                    for team_inj_list in report.values():
                        for inj in team_inj_list:
                            tier_counts[inj.get("tier", "minor")] = tier_counts.get(inj.get("tier", "minor"), 0) + 1

                    ic1, ic2, ic3, ic4 = st.columns(4)
                    ic1.metric("Total Injuries", total_injuries)
                    ic2.metric("Minor", tier_counts.get("minor", 0))
                    ic3.metric("Moderate", tier_counts.get("moderate", 0))
                    ic4.metric("Severe", tier_counts.get("severe", 0))

                    st.markdown(f"### {selected_inj_year} Injuries by Team")
                    all_inj_rows = []
                    for team_name in sorted(report.keys()):
                        for inj in report[team_name]:
                            status = "OUT FOR SEASON" if inj.get("is_season_ending") else f"{inj.get('weeks_out', 0)} week(s)"
                            all_inj_rows.append({
                                "Team": team_name,
                                "Player": inj.get("player_name", ""),
                                "Position": inj.get("position", ""),
                                "Injury": inj.get("description", ""),
                                "Severity": inj.get("tier", "").capitalize(),
                                "Week": inj.get("week_injured", 0),
                                "Status": status,
                            })
                    if all_inj_rows:
                        st.dataframe(pd.DataFrame(all_inj_rows), hide_index=True, use_container_width=True, height=500)

                    st.markdown("### Injuries Per Team")
                    team_inj_chart = []
                    for t in sorted(report.keys()):
                        team_inj_chart.append({"Team": t, "Injuries": len(report[t])})
                    if team_inj_chart:
                        fig_inj = px.bar(pd.DataFrame(team_inj_chart), x="Team", y="Injuries",
                                         title=f"{selected_inj_year} Injuries by Team")
                        fig_inj.update_layout(height=350, xaxis_tickangle=-45)
                        st.plotly_chart(fig_inj, use_container_width=True)

                    if len(available_inj_years) > 1:
                        st.divider()
                        st.markdown("### Injury Trends Across Seasons")
                        trend_data = []
                        for yr in sorted(dynasty.injury_history.keys()):
                            yr_report = dynasty.injury_history[yr]
                            yr_total = sum(len(v) for v in yr_report.values())
                            yr_severe = sum(1 for team_inj in yr_report.values() for inj in team_inj if inj.get("tier") == "severe")
                            trend_data.append({"Year": yr, "Total": yr_total, "Severe": yr_severe})
                        fig_trend = px.line(pd.DataFrame(trend_data), x="Year", y=["Total", "Severe"],
                                            title="Injuries Per Season", markers=True)
                        fig_trend.update_layout(height=350)
                        st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    st.caption("No injuries recorded for this season.")
            else:
                st.caption("No injury data yet. Simulate a season first.")

        with tab8:
            st.subheader("Player Development")
            if dynasty.development_history:
                available_dev_years = sorted(dynasty.development_history.keys(), reverse=True)
                selected_dev_year = st.selectbox("Select Offseason", available_dev_years,
                                                  format_func=lambda y: f"{y} offseason",
                                                  key="dev_year_select")
                events = dynasty.development_history.get(selected_dev_year, [])

                if events:
                    breakouts = [e for e in events if e.get("event_type") == "breakout"]
                    declines = [e for e in events if e.get("event_type") == "decline"]

                    dc1, dc2, dc3 = st.columns(3)
                    dc1.metric("Notable Events", len(events))
                    dc2.metric("Breakouts", len(breakouts))
                    dc3.metric("Declines", len(declines))

                    if breakouts:
                        st.markdown("### Breakout Players")
                        bo_rows = []
                        for ev in breakouts:
                            bo_rows.append({
                                "Player": ev.get("player", ""),
                                "Team": ev.get("team", ""),
                                "Description": ev.get("description", ""),
                            })
                        st.dataframe(pd.DataFrame(bo_rows), hide_index=True, use_container_width=True)

                    if declines:
                        st.markdown("### Declining Players")
                        dec_rows = []
                        for ev in declines:
                            dec_rows.append({
                                "Player": ev.get("player", ""),
                                "Team": ev.get("team", ""),
                                "Description": ev.get("description", ""),
                            })
                        st.dataframe(pd.DataFrame(dec_rows), hide_index=True, use_container_width=True)

                    if len(available_dev_years) > 1:
                        st.divider()
                        st.markdown("### Development Trends")
                        dev_trend = []
                        for yr in sorted(dynasty.development_history.keys()):
                            yr_events = dynasty.development_history[yr]
                            yr_bo = sum(1 for e in yr_events if e.get("event_type") == "breakout")
                            yr_dec = sum(1 for e in yr_events if e.get("event_type") == "decline")
                            dev_trend.append({"Year": yr, "Breakouts": yr_bo, "Declines": yr_dec})
                        fig_dev = px.bar(pd.DataFrame(dev_trend), x="Year", y=["Breakouts", "Declines"],
                                         title="Notable Development Events Per Offseason", barmode="group")
                        fig_dev.update_layout(height=350)
                        st.plotly_chart(fig_dev, use_container_width=True)
                else:
                    st.caption("No notable development events this offseason.")
            else:
                st.caption("No development data yet. Simulate a season first.")

        with tab9:
            st.subheader("CSV Export")
            st.caption("Download statistics as CSV files for external analysis.")

            export_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")

            if "last_dynasty_season" in st.session_state:
                st.markdown("### Current Season Exports")
                season = st.session_state["last_dynasty_season"]
                prev_year = dynasty.current_year - 1

                exp_col1, exp_col2 = st.columns(2)
                with exp_col1:
                    if st.button("Export Season Standings", use_container_width=True, key="exp_standings"):
                        path = export_season_standings_csv(season, os.path.join(export_dir, f"season_{prev_year}_standings.csv"))
                        with open(path, 'r') as f:
                            st.download_button("Download Standings CSV", f.read(),
                                               file_name=f"season_{prev_year}_standings.csv", mime="text/csv", key="dl_standings")
                with exp_col2:
                    if st.button("Export Game Log", use_container_width=True, key="exp_gamelog"):
                        path = export_season_game_log_csv(season, os.path.join(export_dir, f"season_{prev_year}_games.csv"))
                        with open(path, 'r') as f:
                            st.download_button("Download Game Log CSV", f.read(),
                                               file_name=f"season_{prev_year}_games.csv", mime="text/csv", key="dl_gamelog")

            if dynasty.seasons:
                st.markdown("### Dynasty-Wide Exports")
                dyn_exp_names = {
                    "Dynasty Standings (All Seasons)": ("standings", export_dynasty_standings_csv),
                    "Awards History": ("awards", export_dynasty_awards_csv),
                    "Injury History": ("injuries", export_injury_history_csv),
                    "Development History": ("development", export_development_history_csv),
                    "All-CVL Selections": ("all_american", export_all_american_csv),
                    "All-Conference Selections": ("all_conference", export_all_conference_csv),
                }

                for i, (label, (fname, export_fn)) in enumerate(dyn_exp_names.items()):
                    if st.button(f"Export {label}", use_container_width=True, key=f"exp_dyn_{fname}"):
                        path = export_fn(dynasty, os.path.join(export_dir, f"dynasty_{fname}.csv"))
                        with open(path, 'r') as f:
                            st.download_button(f"Download {label} CSV", f.read(),
                                               file_name=f"dynasty_{fname}.csv", mime="text/csv",
                                               key=f"dl_dyn_{fname}")
            else:
                st.caption("Simulate at least one season to enable exports.")
