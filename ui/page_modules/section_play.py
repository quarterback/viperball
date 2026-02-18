import io
import csv
import json
import os
import random
import tempfile

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from engine.season import load_teams_from_directory, get_recommended_bowl_count, BOWL_TIERS
from engine.conference_names import generate_conference_names
from engine.geography import get_geographic_conference_defaults
from engine.ai_coach import auto_assign_all_teams, get_scheme_label, load_team_identity
from engine.game_engine import WEATHER_CONDITIONS
from ui import api_client
from ui.helpers import (
    load_team, format_time, fmt_vb_score,
    generate_box_score_markdown, generate_play_log_csv,
    generate_drives_csv, safe_filename, drive_result_label,
    render_game_detail, drive_result_color,
)


def _teams_dir():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "teams")


def _get_active_session():
    mode = st.session_state.get("api_mode")
    session_id = st.session_state.get("api_session_id")
    if not session_id or not mode:
        return None
    return mode


def _ensure_session_id():
    if "api_session_id" not in st.session_state:
        resp = api_client.create_session()
        st.session_state["api_session_id"] = resp["session_id"]
    return st.session_state["api_session_id"]


def render_play_section(shared):
    teams = shared["teams"]
    styles = shared["styles"]
    team_names = shared["team_names"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]
    OFFENSE_TOOLTIPS = shared["OFFENSE_TOOLTIPS"]
    DEFENSE_TOOLTIPS = shared["DEFENSE_TOOLTIPS"]

    mode = _get_active_session()

    if mode == "dynasty":
        _render_dynasty_play(shared)
    elif mode == "season":
        _render_season_play(shared)
    else:
        _render_mode_selection(shared)


def _render_mode_selection(shared):
    st.title("Play")
    st.caption("Start a new dynasty, season, or play a quick exhibition game")

    play_tabs = st.tabs(["New Dynasty", "New Season", "Quick Game"])

    with play_tabs[0]:
        _render_new_dynasty(shared)

    with play_tabs[1]:
        _render_new_season(shared)

    with play_tabs[2]:
        _render_quick_game(shared)


def _render_new_dynasty(shared):
    teams = shared["teams"]
    styles = shared["styles"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]

    st.subheader("Create New Dynasty")
    st.caption("Multi-season career mode with historical tracking, awards, and record books")

    dynasty_col1, dynasty_col2 = st.columns(2)
    with dynasty_col1:
        dynasty_name = st.text_input("Dynasty Name", value="My Viperball Dynasty", key="dyn_name")
        coach_name = st.text_input("Coach Name", value="Coach", key="coach_name")
    with dynasty_col2:
        coach_team = st.selectbox("Your Team", [t["name"] for t in teams], key="coach_team")
        start_year = st.number_input("Starting Year", min_value=2020, max_value=2050, value=2026, key="start_year")

    st.divider()
    st.subheader("Conference Setup")
    teams_dir = _teams_dir()
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
                        didx = conf_names_list.index(default_splits.get(tname, conf_names_list[0]))
                        assigned = st.selectbox(tname[:20], conf_names_list, index=didx,
                                                 key=f"conf_assign_{tname}")
                        conf_assignments[tname] = assigned

    st.divider()
    st.subheader("League History")
    st.caption("Generate past seasons so your dynasty has an established history with champions, records, and rivalries.")
    history_col1, history_col2 = st.columns(2)
    with history_col1:
        history_years = st.slider("Years of History to Simulate", min_value=0, max_value=100, value=0, key="history_years",
                                   help="0 = start fresh with no history. Higher values take longer to generate.")
    with history_col2:
        history_games = st.slider("Games Per Team (History Seasons)", min_value=8, max_value=12, value=10, key="history_games")

    st.divider()
    load_col1, load_col2 = st.columns(2)
    with load_col1:
        create_btn = st.button("Create Dynasty", type="primary", use_container_width=True, key="create_dynasty")
    with load_col2:
        uploaded = st.file_uploader("Load Saved Dynasty", type=["json"], key="load_dynasty")

    if create_btn:
        session_id = _ensure_session_id()
        with st.spinner("Creating dynasty..."):
            try:
                api_client.create_dynasty(
                    session_id,
                    dynasty_name=dynasty_name,
                    coach_name=coach_name,
                    coach_team=coach_team,
                    starting_year=start_year,
                    num_conferences=num_conferences,
                    history_years=history_years,
                )
                st.session_state["api_mode"] = "dynasty"
                st.rerun()
            except api_client.APIError as e:
                st.error(f"Failed to create dynasty: {e.detail}")

    if uploaded:
        st.warning("Dynasty save file loading is not yet supported through the API. This feature is coming soon.")


def _render_new_season(shared):
    teams = shared["teams"]
    styles = shared["styles"]
    team_names = shared["team_names"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]

    st.subheader("New Season")
    st.caption("Simulate a full season with all 125 teams, standings, and playoffs")

    teams_dir = _teams_dir()
    all_teams = load_teams_from_directory(teams_dir)
    all_team_names = sorted(all_teams.keys())

    season_name = st.text_input("Season Name", value="2026 CVL Season", key="season_name")

    if len(all_team_names) < 2:
        st.warning("Not enough teams loaded to run a season.")
        return

    human_teams = st.multiselect(
        "Your Teams (human-coached)",
        all_team_names,
        default=[],
        max_selections=4,
        key="season_human_teams",
        help="Pick up to 4 teams to coach yourself. Everyone else is AI-controlled."
    )

    if "season_ai_seed" not in st.session_state:
        st.session_state["season_ai_seed"] = 0

    def _reroll_season_ai():
        st.session_state["season_ai_seed"] = random.randint(1, 999999)

    ai_seed_col, reroll_col = st.columns([3, 1])
    with ai_seed_col:
        ai_seed = st.number_input("AI Coaching Seed (0 = random)", min_value=0, max_value=999999, key="season_ai_seed")
    with reroll_col:
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("Re-roll AI", key="reroll_ai_season", on_click=_reroll_season_ai)

    actual_seed = ai_seed if ai_seed > 0 else hash(season_name) % 999999

    teams_dir_path = _teams_dir()
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

    ai_teams = [t for t in all_team_names if t not in human_teams]
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

    for tname in all_team_names:
        if tname not in style_configs:
            style_configs[tname] = {"offense_style": "balanced", "defense_style": "base_defense"}

    auto_conferences = {}
    for tname in all_team_names:
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
        playoff_options = [p for p in [4, 8, 12, 16, 24, 32] if p <= len(all_team_names)]
        if not playoff_options:
            playoff_options = [len(all_team_names)]
        playoff_size = st.radio("Playoff Format", playoff_options, index=0, key="playoff_size", horizontal=True)

    rec_bowls = get_recommended_bowl_count(len(all_team_names), playoff_size)
    bowl_count = st.slider("Number of Bowl Games", min_value=0, max_value=min(12, (len(all_team_names) - playoff_size) // 2), value=rec_bowls, key="season_bowl_count")

    start_season = st.button("Start Season", type="primary", use_container_width=True, key="run_season")

    if start_season:
        session_id = _ensure_session_id()
        with st.spinner("Creating season..."):
            try:
                api_client.create_season(
                    session_id,
                    name=season_name,
                    games_per_team=season_games,
                    playoff_size=playoff_size,
                    bowl_count=bowl_count,
                    human_teams=human_teams,
                    conferences=auto_conferences if auto_conferences else None,
                    style_configs=style_configs,
                    ai_seed=actual_seed,
                )
                st.session_state["api_mode"] = "season"
                st.session_state["season_human_teams_list"] = human_teams
                st.rerun()
            except api_client.APIError as e:
                st.error(f"Failed to create season: {e.detail}")


def _render_quick_game(shared):
    teams = shared["teams"]
    styles = shared["styles"]
    team_names = shared["team_names"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]
    OFFENSE_TOOLTIPS = shared["OFFENSE_TOOLTIPS"]
    DEFENSE_TOOLTIPS = shared["DEFENSE_TOOLTIPS"]

    st.subheader("Quick Game")
    st.caption("Play a single exhibition game between any two teams")

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Home Team**")
            home_key = st.selectbox("Select Home Team", [t["key"] for t in teams],
                                    format_func=lambda x: team_names[x], key="home")
            hc1, hc2 = st.columns(2)
            with hc1:
                home_style = st.selectbox("Offense", style_keys,
                                          format_func=lambda x: styles[x]["label"],
                                          index=style_keys.index(next((t["default_style"] for t in teams if t["key"] == home_key), "balanced")),
                                          key="home_style")
            with hc2:
                home_def_style = st.selectbox("Defense", defense_style_keys,
                                               format_func=lambda x: defense_styles[x]["label"],
                                               key="home_def_style")
            st.caption(OFFENSE_TOOLTIPS.get(home_style, styles[home_style]["description"]))

        with col2:
            st.markdown("**Away Team**")
            away_key = st.selectbox("Select Away Team", [t["key"] for t in teams],
                                    format_func=lambda x: team_names[x],
                                    index=min(1, len(teams) - 1), key="away")
            ac1, ac2 = st.columns(2)
            with ac1:
                away_style = st.selectbox("Offense", style_keys,
                                          format_func=lambda x: styles[x]["label"],
                                          index=style_keys.index(next((t["default_style"] for t in teams if t["key"] == away_key), "balanced")),
                                          key="away_style")
            with ac2:
                away_def_style = st.selectbox("Defense", defense_style_keys,
                                               format_func=lambda x: defense_styles[x]["label"],
                                               key="away_def_style")
            st.caption(OFFENSE_TOOLTIPS.get(away_style, styles[away_style]["description"]))

    weather_keys = list(WEATHER_CONDITIONS.keys())
    weather_labels = {k: v["label"] for k, v in WEATHER_CONDITIONS.items()}
    col_weather, col_seed, col_btn = st.columns([1, 1, 2])
    with col_weather:
        weather = st.selectbox("Weather", weather_keys, format_func=lambda x: f"{weather_labels[x]}", key="weather")
    with col_seed:
        seed = st.number_input("Seed (0 = random)", min_value=0, max_value=999999, value=0, key="seed")
    with col_btn:
        st.write("")
        st.write("")
        run_game = st.button("Simulate Game", type="primary", use_container_width=True)

    if run_game:
        actual_seed = seed if seed > 0 else random.randint(1, 999999)
        home_name = team_names[home_key]
        away_name = team_names[away_key]

        with st.spinner("Simulating game..."):
            try:
                result = api_client.simulate_quick_game(
                    home=home_key,
                    away=away_key,
                    home_offense=home_style,
                    home_defense=home_def_style,
                    away_offense=away_style,
                    away_defense=away_def_style,
                    weather=weather,
                    seed=actual_seed,
                )
                st.session_state["last_result"] = result
                st.session_state["last_seed"] = actual_seed
            except api_client.APIError as e:
                st.error(f"Simulation failed: {e.detail}")

    if "last_result" in st.session_state:
        result = st.session_state["last_result"]
        actual_seed = st.session_state["last_seed"]
        render_game_detail(result, key_prefix="qg")


def _render_dynasty_play(shared):
    styles = shared["styles"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]

    session_id = st.session_state["api_session_id"]

    try:
        dynasty_status = api_client.get_dynasty_status(session_id)
    except api_client.APIError:
        st.error("Could not load dynasty data.")
        return

    coach = dynasty_status.get("coach", {})
    current_year = dynasty_status.get("current_year", 2026)
    dynasty_name = dynasty_status.get("dynasty_name", "Dynasty")
    coach_team = coach.get("team", "")
    coach_name_str = coach.get("name", "Coach")

    st.title(f"Play — {dynasty_name}")
    st.caption(f"Season {current_year} | Coach {coach_name_str} | {coach_team}")

    play_tabs = st.tabs(["Simulate Season", "Quick Game"])

    with play_tabs[0]:
        st.subheader(f"Season {current_year}")

        teams_dir = _teams_dir()
        all_teams = load_teams_from_directory(teams_dir)
        total_teams = len(all_teams)

        setup_col1, setup_col2 = st.columns(2)
        with setup_col1:
            games_per_team = st.slider(
                "Regular Season Games Per Team",
                min_value=8, max_value=12, value=10,
                key=f"dyn_games_{current_year}"
            )
        with setup_col2:
            dyn_playoff_options = [p for p in [4, 8, 12, 16, 24, 32] if p <= total_teams]
            if not dyn_playoff_options:
                dyn_playoff_options = [total_teams]
            playoff_format = st.radio("Playoff Format", dyn_playoff_options, index=0, horizontal=True,
                                      key=f"dyn_playoff_{current_year}")

        dyn_rec = get_recommended_bowl_count(total_teams, playoff_format)
        dyn_max_bowls = max(0, (total_teams - playoff_format) // 2)
        dyn_bowl_count = st.slider("Number of Bowl Games", min_value=0, max_value=min(12, dyn_max_bowls), value=min(dyn_rec, min(12, dyn_max_bowls)),
                                    key=f"dyn_bowls_{current_year}")

        teams_dir_path = _teams_dir()
        team_identities = load_team_identity(teams_dir_path)

        st.markdown("**Your Team**")
        user_team = coach_team
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
                                     key=f"dyn_user_off_{current_year}")
        with user_def_col:
            user_def = st.selectbox("Defense Style", defense_style_keys,
                                     format_func=lambda x: defense_styles[x]["label"],
                                     key=f"dyn_user_def_{current_year}")

        ai_seed = hash(f"{dynasty_name}_{current_year}") % 999999
        ai_configs = auto_assign_all_teams(
            teams_dir_path,
            human_teams=[user_team],
            human_configs={user_team: {"offense_style": user_off, "defense_style": user_def}},
            seed=ai_seed,
        )

        ai_opponent_teams = sorted([t for t in all_teams if t != user_team])
        with st.expander(f"AI Coach Assignments ({len(ai_opponent_teams)} teams)", expanded=False):
            ai_data = []
            for tname in ai_opponent_teams:
                cfg = ai_configs.get(tname, {"offense_style": "balanced", "defense_style": "base_defense"})
                identity = team_identities.get(tname, {})
                mascot = identity.get("mascot", "")
                ai_data.append({
                    "Team": tname,
                    "Mascot": mascot,
                    "Offense": styles.get(cfg["offense_style"], {}).get("label", cfg["offense_style"]),
                    "Defense": defense_styles.get(cfg["defense_style"], {}).get("label", cfg["defense_style"]),
                })
            st.dataframe(pd.DataFrame(ai_data), hide_index=True, use_container_width=True)

        phase = dynasty_status.get("phase", "setup")

        try:
            season_status = api_client.get_season_status(session_id)
            season_phase = season_status.get("phase", phase)
        except api_client.APIError:
            season_phase = phase

        if season_phase == "setup":
            if st.button(f"Start {current_year} Season", type="primary", use_container_width=True, key="sim_dynasty_season"):
                with st.spinner("Starting season..."):
                    try:
                        api_client.dynasty_start_season(
                            session_id,
                            games_per_team=games_per_team,
                            playoff_size=playoff_format,
                            bowl_count=dyn_bowl_count,
                            offense_style=user_off,
                            defense_style=user_def,
                            ai_seed=ai_seed,
                        )
                        st.rerun()
                    except api_client.APIError as e:
                        st.error(f"Failed to start season: {e.detail}")

        elif season_phase in ("regular",):
            status = season_status
            total_weeks = status.get("total_weeks", 0)
            current_week = status.get("current_week", 0)
            next_week = status.get("next_week")
            games_played = status.get("games_played", 0)
            total_games = status.get("total_games", 0)

            if next_week is not None:
                sm1, sm2, sm3 = st.columns(3)
                sm1.metric("Current Week", f"Week {next_week} of {total_weeks}")
                sm2.metric("Games Played", f"{games_played} / {total_games}")
                progress_pct = games_played / total_games if total_games > 0 else 0
                sm3.metric("Progress", f"{progress_pct:.0%}")
                st.progress(progress_pct)

                btn_col1, btn_col2, btn_col3 = st.columns(3)
                with btn_col1:
                    if st.button("Sim Next Week", type="primary", use_container_width=True, key="dyn_sim_next_week"):
                        with st.spinner(f"Simulating Week {next_week}..."):
                            try:
                                api_client.simulate_week(session_id, week=next_week)
                                st.rerun()
                            except api_client.APIError as e:
                                st.error(f"Simulation failed: {e.detail}")

                with btn_col2:
                    remaining = list(range(next_week + 1, total_weeks + 1))
                    if remaining:
                        target = st.selectbox("Sim through week...", remaining,
                                               format_func=lambda w: f"Week {w}",
                                               key="dyn_sim_to_week_select")
                        if st.button("Sim to Week", use_container_width=True, key="dyn_sim_to_week_btn"):
                            with st.spinner(f"Simulating through Week {target}..."):
                                try:
                                    api_client.simulate_through_week(session_id, target)
                                    st.rerun()
                                except api_client.APIError as e:
                                    st.error(f"Simulation failed: {e.detail}")

                with btn_col3:
                    if st.button("Sim Rest of Season", use_container_width=True, key="dyn_sim_rest"):
                        with st.spinner("Simulating remaining games..."):
                            try:
                                api_client.simulate_rest(session_id)
                                st.rerun()
                            except api_client.APIError as e:
                                st.error(f"Simulation failed: {e.detail}")

                if current_week > 0:
                    st.divider()
                    try:
                        standings_resp = api_client.get_standings(session_id)
                        standings = standings_resp.get("standings", [])
                        user_rec = next((r for r in standings if r["team_name"] == coach_team), None)
                        if user_rec:
                            ur_rank = next((i for i, r in enumerate(standings, 1) if r["team_name"] == coach_team), 0)
                            ur1, ur2, ur3 = st.columns(3)
                            ur1.metric("Your Record", f"{user_rec['wins']}-{user_rec['losses']}", f"#{ur_rank} overall")
                            ur2.metric("Points For", fmt_vb_score(user_rec['points_for']))
                            ur3.metric("Points Against", fmt_vb_score(user_rec['points_against']))
                    except api_client.APIError:
                        pass

                    st.divider()
                    st.subheader("Recent Results")
                    show_weeks = range(max(1, current_week - 2), current_week + 1)
                    for w in show_weeks:
                        _render_week_results_api(session_id, w)

            else:
                st.rerun()

        elif season_phase == "playoffs_pending":
            st.success("Regular season complete!")
            try:
                standings_resp = api_client.get_standings(session_id)
                standings = standings_resp.get("standings", [])
                user_rec = next((r for r in standings if r["team_name"] == coach_team), None)
                if user_rec:
                    ur_rank = next((i for i, r in enumerate(standings, 1) if r["team_name"] == coach_team), 0)
                    st.metric("Your Final Record", f"{user_rec['wins']}-{user_rec['losses']} (#{ur_rank})")
            except api_client.APIError:
                pass

            if playoff_format >= 4:
                st.subheader(f"Playoff ({playoff_format} teams)")
                if st.button("Run Playoffs", type="primary", use_container_width=True, key="dyn_run_playoffs"):
                    with st.spinner("Running playoffs..."):
                        try:
                            api_client.run_playoffs(session_id)
                            st.rerun()
                        except api_client.APIError as e:
                            st.error(f"Playoffs failed: {e.detail}")

        elif season_phase == "bowls_pending":
            try:
                bracket_resp = api_client.get_playoff_bracket(session_id)
                champion = bracket_resp.get("champion")
                if champion:
                    if champion == coach_team:
                        st.success(f"YOUR TEAM {champion} ARE THE NATIONAL CHAMPIONS!")
                    else:
                        st.info(f"National Champions: {champion}")
            except api_client.APIError:
                pass

            st.subheader(f"Bowl Games ({dyn_bowl_count} bowls)")
            if st.button("Run Bowl Games", type="primary", use_container_width=True, key="dyn_run_bowls"):
                with st.spinner("Running bowl games..."):
                    try:
                        api_client.run_bowls(session_id)
                        st.rerun()
                    except api_client.APIError as e:
                        st.error(f"Bowl games failed: {e.detail}")

        elif season_phase in ("complete", "finalize"):
            try:
                bracket_resp = api_client.get_playoff_bracket(session_id)
                champion = bracket_resp.get("champion")
                if champion:
                    if champion == coach_team:
                        st.balloons()
                        st.success(f"YOUR TEAM {champion} ARE THE NATIONAL CHAMPIONS!")
                    else:
                        st.info(f"National Champions: {champion}")
            except api_client.APIError:
                pass

            st.subheader(f"Advance Dynasty to {current_year + 1}")
            st.caption("This will process offseason development, update records, and move to next year.")

            if st.button("Advance to Next Season", type="primary", use_container_width=True, key="dyn_advance"):
                with st.spinner("Advancing dynasty..."):
                    try:
                        api_client.dynasty_advance(session_id)
                        st.rerun()
                    except api_client.APIError as e:
                        st.error(f"Dynasty advance failed: {e.detail}")

    with play_tabs[1]:
        _render_quick_game(shared)


def _render_week_results_api(session_id, week_num, label=None):
    try:
        resp = api_client.get_schedule(session_id, week=week_num, completed_only=True)
        week_games = resp.get("games", [])
    except api_client.APIError:
        return

    if not week_games:
        return
    header = label or f"Week {week_num} Results"
    with st.expander(header, expanded=True):
        for g in week_games:
            home_score = g.get("home_score") or 0
            away_score = g.get("away_score") or 0
            home_team = g.get("home_team", "")
            away_team = g.get("away_team", "")
            winner = home_team if home_score > away_score else away_team
            marker = "**" if winner == home_team else ""
            marker2 = "**" if winner == away_team else ""
            st.markdown(f"{marker}{home_team}{marker} {fmt_vb_score(home_score)} — {fmt_vb_score(away_score)} {marker2}{away_team}{marker2}")


def _render_season_play(shared):
    session_id = st.session_state["api_session_id"]

    try:
        status = api_client.get_season_status(session_id)
    except api_client.APIError:
        st.error("Could not load season data.")
        return

    phase = status.get("phase", "regular")
    season_name = status.get("name", "Season")
    total_weeks = status.get("total_weeks", 0)
    current_week = status.get("current_week", 0)
    next_week = status.get("next_week")
    games_played = status.get("games_played", 0)
    total_games = status.get("total_games", 0)
    champion = status.get("champion")

    st.title(f"Play — {season_name}")

    if phase == "regular":
        if next_week is not None:
            sm1, sm2, sm3 = st.columns(3)
            sm1.metric("Current Week", f"Week {next_week} of {total_weeks}")
            sm2.metric("Games Played", f"{games_played} / {total_games}")
            progress_pct = games_played / total_games if total_games > 0 else 0
            sm3.metric("Progress", f"{progress_pct:.0%}")

            st.progress(progress_pct)

            st.subheader("Advance Season")

            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("Sim Next Week", type="primary", use_container_width=True, key="sim_next_week"):
                    with st.spinner(f"Simulating Week {next_week}..."):
                        try:
                            api_client.simulate_week(session_id, week=next_week)
                            st.rerun()
                        except api_client.APIError as e:
                            st.error(f"Simulation failed: {e.detail}")

            with btn_col2:
                remaining = list(range(next_week + 1, total_weeks + 1))
                if remaining:
                    target = st.selectbox("Sim through week...", remaining,
                                           format_func=lambda w: f"Week {w}",
                                           key="sim_to_week_select")
                    if st.button("Sim to Week", use_container_width=True, key="sim_to_week_btn"):
                        with st.spinner(f"Simulating through Week {target}..."):
                            try:
                                api_client.simulate_through_week(session_id, target)
                                st.rerun()
                            except api_client.APIError as e:
                                st.error(f"Simulation failed: {e.detail}")

            with btn_col3:
                if st.button("Sim Rest of Season", use_container_width=True, key="sim_rest_season"):
                    with st.spinner(f"Simulating remaining {total_games - games_played} games..."):
                        try:
                            api_client.simulate_rest(session_id)
                            st.rerun()
                        except api_client.APIError as e:
                            st.error(f"Simulation failed: {e.detail}")

            if current_week > 0:
                st.divider()
                try:
                    standings_resp = api_client.get_standings(session_id)
                    standings = standings_resp.get("standings", [])
                    top5 = standings[:5]
                    st.subheader("Current Standings (Top 5)")
                    for i, rec in enumerate(top5, 1):
                        st.markdown(f"{i}. **{rec['team_name']}** — {rec['wins']}-{rec['losses']} (PF: {fmt_vb_score(rec['points_for'])})")
                    st.caption("See full standings in the League tab.")
                except api_client.APIError:
                    pass

                st.divider()
                st.subheader("Recent Results")
                show_weeks = range(max(1, current_week - 2), current_week + 1)
                for w in show_weeks:
                    _render_week_results_api(session_id, w)
        else:
            st.rerun()

    elif phase == "playoffs_pending":
        st.success("Regular season complete!")
        try:
            standings_resp = api_client.get_standings(session_id)
            standings = standings_resp.get("standings", [])
            sm1, sm2, sm3 = st.columns(3)
            sm1.metric("Games Played", games_played)
            best = standings[0] if standings else None
            sm2.metric("#1 Team", best["team_name"] if best else "—")
            sm3.metric("Record", f"{best['wins']}-{best['losses']}" if best else "—")
        except api_client.APIError:
            pass

        playoff_size = st.session_state.get("season_playoff_size", 8)
        if playoff_size > 0:
            st.subheader(f"Playoff ({playoff_size} teams)")
            st.caption("Conference champions get auto-bids, remaining spots filled by Power Index.")
            if st.button("Run Playoffs", type="primary", use_container_width=True, key="run_playoffs_btn"):
                with st.spinner("Running playoffs..."):
                    try:
                        api_client.run_playoffs(session_id)
                        st.rerun()
                    except api_client.APIError as e:
                        st.error(f"Playoffs failed: {e.detail}")

    elif phase == "bowls_pending":
        if champion:
            st.success(f"**National Champions: {champion}**")
        bowl_count = st.session_state.get("season_bowl_count", 0)
        st.subheader(f"Bowl Games ({bowl_count} bowls)")
        if st.button("Run Bowl Games", type="primary", use_container_width=True, key="run_bowls_btn"):
            with st.spinner("Running bowl games..."):
                try:
                    api_client.run_bowls(session_id)
                    st.rerun()
                except api_client.APIError as e:
                    st.error(f"Bowl games failed: {e.detail}")

    elif phase == "complete":
        if champion:
            st.success(f"**National Champions: {champion}**")

        try:
            standings_resp = api_client.get_standings(session_id)
            standings = standings_resp.get("standings", [])
            schedule_resp = api_client.get_schedule(session_id, completed_only=True)
            all_games = schedule_resp.get("games", [])
            all_scores = []
            for g in all_games:
                all_scores.extend([g.get("home_score") or 0, g.get("away_score") or 0])
            avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.metric("Teams", len(standings))
            sm2.metric("Games Played", len(all_games))
            sm3.metric("Avg Score", f"{avg_score:.1f}")
            best = standings[0] if standings else None
            sm4.metric("Top Team", f"{best['team_name']}" if best else "—", f"{best['wins']}-{best['losses']}" if best else "")
        except api_client.APIError:
            pass

        st.divider()
        st.caption("Season is complete. Browse results in the League tab, or start a new session.")

    if st.button("End Season & Start New", key="end_season_btn"):
        try:
            api_client.delete_session(session_id)
        except api_client.APIError:
            pass
        for key in ["api_session_id", "api_mode", "season_human_teams_list",
                     "season_playoff_size", "season_bowl_count"]:
            st.session_state.pop(key, None)
        st.rerun()
