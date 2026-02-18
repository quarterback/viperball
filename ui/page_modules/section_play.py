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

from engine.season import load_teams_from_directory, create_season, get_recommended_bowl_count, BOWL_TIERS
from engine.dynasty import create_dynasty, Dynasty
from engine.conference_names import generate_conference_names
from engine.geography import get_geographic_conference_defaults
from engine.injuries import InjuryTracker
from engine.awards import compute_season_awards
from engine.player_card import player_to_card
from engine.ai_coach import auto_assign_all_teams, get_scheme_label, load_team_identity
from engine import ViperballEngine, OFFENSE_STYLES
from engine.game_engine import WEATHER_CONDITIONS
from ui.helpers import (
    load_team, format_time, fmt_vb_score,
    generate_box_score_markdown, generate_play_log_csv,
    generate_drives_csv, safe_filename, drive_result_label,
    render_game_detail, drive_result_color,
)


def _teams_dir():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "teams")


def _get_active_session():
    if "dynasty" in st.session_state:
        return "dynasty"
    if "active_season" in st.session_state:
        return "season"
    return None


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
    teams = shared["teams"]
    styles = shared["styles"]
    team_names = shared["team_names"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]

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
        dynasty = create_dynasty(dynasty_name, coach_name, coach_team, start_year)
        conf_team_lists = {}
        for tname, cname in conf_assignments.items():
            if cname not in conf_team_lists:
                conf_team_lists[cname] = []
            conf_team_lists[cname].append(tname)
        for cname, cteams in conf_team_lists.items():
            dynasty.add_conference(cname, cteams)

        if history_years > 0:
            progress_bar = st.progress(0, text=f"Simulating league history (0/{history_years} seasons)...")
            def _update_progress(done, total):
                progress_bar.progress(done / total, text=f"Simulating league history ({done}/{total} seasons)...")
            dynasty.simulate_history(
                num_years=history_years,
                teams_dir=teams_dir,
                games_per_team=history_games,
                playoff_size=8,
                progress_callback=_update_progress,
            )
            progress_bar.progress(1.0, text=f"History complete! {history_years} seasons generated.")

        setup_teams_loaded = load_teams_from_directory(teams_dir)
        st.session_state["dynasty"] = dynasty
        st.session_state["dynasty_teams"] = setup_teams_loaded
        st.rerun()

    if uploaded:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                tmp.write(uploaded.read().decode())
                tmp_path = tmp.name
            dynasty = Dynasty.load(tmp_path)
            all_teams_loaded = load_teams_from_directory(_teams_dir())
            st.session_state["dynasty"] = dynasty
            st.session_state["dynasty_teams"] = all_teams_loaded
            os.unlink(tmp_path)
            st.rerun()
        except Exception as e:
            st.error(f"Failed to load dynasty: {e}")


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

    run_season = st.button("Simulate Season", type="primary", use_container_width=True, key="run_season")

    if run_season:
        season = create_season(season_name, all_teams, style_configs,
                               conferences=auto_conferences if auto_conferences else None,
                               games_per_team=season_games)

        with st.spinner(f"Simulating {len(season.schedule)} games..."):
            season.simulate_season(generate_polls=True)

        if playoff_size > 0 and len(all_team_names) >= playoff_size:
            with st.spinner("Running playoffs..."):
                season.simulate_playoff(num_teams=min(playoff_size, len(all_team_names)))

        if bowl_count > 0:
            with st.spinner("Running bowl games..."):
                season.simulate_bowls(bowl_count=bowl_count, playoff_size=playoff_size)

        st.session_state["active_season"] = season
        st.session_state["season_human_teams_list"] = human_teams
        st.rerun()


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
        home_team = load_team(home_key)
        away_team = load_team(away_key)

        style_overrides = {}
        style_overrides[home_team.name] = home_style
        style_overrides[away_team.name] = away_style
        style_overrides[f"{home_team.name}_defense"] = home_def_style
        style_overrides[f"{away_team.name}_defense"] = away_def_style

        engine = ViperballEngine(home_team, away_team, seed=actual_seed, style_overrides=style_overrides, weather=weather)

        with st.spinner("Simulating game..."):
            result = engine.simulate_game()

        st.session_state["last_result"] = result
        st.session_state["last_seed"] = actual_seed

    if "last_result" in st.session_state:
        result = st.session_state["last_result"]
        actual_seed = st.session_state["last_seed"]
        render_game_detail(result, key_prefix="qg")


def _render_dynasty_play(shared):
    styles = shared["styles"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]

    dynasty = st.session_state["dynasty"]
    all_dynasty_teams = st.session_state["dynasty_teams"]

    st.title(f"Play — {dynasty.dynasty_name}")
    st.caption(f"Season {dynasty.current_year} | Coach {dynasty.coach.name} | {dynasty.coach.team_name}")

    play_tabs = st.tabs(["Simulate Season", "Quick Game"])

    with play_tabs[0]:
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

        teams_dir_path = _teams_dir()
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
                    st.success(f"YOUR TEAM {season.champion} ARE THE NATIONAL CHAMPIONS!")
                else:
                    st.info(f"National Champions: {season.champion}")

            standings = season.get_standings_sorted()
            user_rec = next((r for r in standings if r.team_name == dynasty.coach.team_name), None)
            if user_rec:
                ur1, ur2, ur3 = st.columns(3)
                ur_rank = next((i for i, r in enumerate(standings, 1) if r.team_name == dynasty.coach.team_name), 0)
                ur1.metric("Your Record", f"{user_rec.wins}-{user_rec.losses}", f"#{ur_rank} overall")
                ur2.metric("Points For", fmt_vb_score(user_rec.points_for))
                ur3.metric("Points Against", fmt_vb_score(user_rec.points_against))

    with play_tabs[1]:
        _render_quick_game(shared)


def _render_season_play(shared):
    season = st.session_state["active_season"]

    st.title(f"Play — {season.name}")

    if season.champion:
        st.success(f"**National Champions: {season.champion}**")

    standings = season.get_standings_sorted()
    total_games = sum(1 for g in season.schedule if g.completed)
    all_scores = []
    for g in season.schedule:
        if g.completed:
            all_scores.extend([g.home_score or 0, g.away_score or 0])
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

    sm1, sm2, sm3, sm4 = st.columns(4)
    sm1.metric("Teams", len(standings))
    sm2.metric("Games Played", total_games)
    sm3.metric("Avg Score", f"{avg_score:.1f}")
    best = standings[0] if standings else None
    sm4.metric("Top Team", f"{best.team_name}" if best else "—", f"{best.wins}-{best.losses}" if best else "")

    st.divider()
    st.caption("Season is complete. Browse results in the League tab, or start a new session from Play.")

    if st.button("End Season & Start New", key="end_season_btn"):
        for key in ["active_season", "season_human_teams_list"]:
            st.session_state.pop(key, None)
        st.rerun()
