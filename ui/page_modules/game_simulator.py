import random
import json

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from engine import ViperballEngine, OFFENSE_STYLES
from engine.game_engine import WEATHER_CONDITIONS, POSITION_ARCHETYPES, get_archetype_info
from engine.viperball_metrics import calculate_viperball_metrics
from ui.helpers import (
    load_team, format_time, fmt_vb_score,
    generate_box_score_markdown, generate_play_log_csv,
    generate_drives_csv, safe_filename, drive_result_label,
    render_game_detail, drive_result_color,
)


def render_game_simulator(shared):
    teams = shared["teams"]
    styles = shared["styles"]
    team_names = shared["team_names"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]
    OFFENSE_TOOLTIPS = shared["OFFENSE_TOOLTIPS"]
    DEFENSE_TOOLTIPS = shared["DEFENSE_TOOLTIPS"]

    st.title("Game Simulator")

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

        home_name = result["final_score"]["home"]["team"]
        away_name = result["final_score"]["away"]["team"]
        home_score = result["final_score"]["home"]["score"]
        away_score = result["final_score"]["away"]["score"]
        hs = result["stats"]["home"]
        as_ = result["stats"]["away"]
        plays = result["play_by_play"]

        st.divider()

        sc1, sc2, sc3 = st.columns([2, 1, 2])
        with sc1:
            st.markdown(f'<p class="team-name">{home_name}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="score-big">{fmt_vb_score(home_score)}</p>', unsafe_allow_html=True)
        with sc2:
            st.markdown("<p style='text-align:center; padding-top:10px; font-size:1.2rem; opacity:0.4;'>vs</p>", unsafe_allow_html=True)
            st.caption(f"Seed: {actual_seed}")
        with sc3:
            st.markdown(f'<p class="team-name">{away_name}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="score-big">{fmt_vb_score(away_score)}</p>', unsafe_allow_html=True)

        margin = abs(home_score - away_score)
        margin_str = fmt_vb_score(margin)
        if home_score > away_score:
            st.success(f"{home_name} wins by {margin_str}")
        elif away_score > home_score:
            st.success(f"{away_name} wins by {margin_str}")
        else:
            st.info("Game ended in a tie")

        game_weather = result.get("weather", "clear")
        weather_label = result.get("weather_label", "Clear")
        weather_desc = result.get("weather_description", "")
        weather_icons = {"clear": "☀️", "rain": "🌧️", "snow": "❄️", "sleet": "🌨️", "heat": "🔥", "wind": "💨"}
        wx_icon = weather_icons.get(game_weather, "☀️")
        if game_weather != "clear":
            st.info(f"{wx_icon} **{weather_label}** — {weather_desc}")

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Total Plays", hs["total_plays"] + as_["total_plays"])
        m2.metric("Total Yards", f"{hs['total_yards'] + as_['total_yards']}")
        m3.metric("Turnovers", f"{hs['fumbles_lost'] + as_['fumbles_lost'] + hs['turnovers_on_downs'] + as_['turnovers_on_downs'] + hs.get('kick_pass_interceptions', 0) + as_.get('kick_pass_interceptions', 0) + hs.get('lateral_interceptions', 0) + as_.get('lateral_interceptions', 0)}")
        m4.metric("Penalties", f"{hs.get('penalties', 0) + as_.get('penalties', 0)}")
        h_dk = hs.get('drop_kicks_made', 0)
        a_dk = as_.get('drop_kicks_made', 0)
        m5.metric("Snap Kicks", f"{h_dk + a_dk}")
        h_td = hs.get('touchdowns', 0)
        a_td = as_.get('touchdowns', 0)
        m6.metric("Touchdowns", f"{h_td + a_td}")

        tab_box, tab_drives, tab_plays, tab_analytics, tab_export = st.tabs([
            "Box Score", "Drives", "Play-by-Play", "Analytics", "Export"
        ])

        with tab_box:
            _render_box_score(result, plays, home_name, away_name, home_score, away_score, hs, as_)

        with tab_drives:
            _render_drives(result, home_name, away_name)

        with tab_plays:
            _render_play_by_play(plays, home_name, away_name)

        with tab_analytics:
            _render_analytics(result, plays, home_name, away_name, hs, as_)

        with tab_export:
            _render_export(result, home_name, away_name, actual_seed)

        with st.expander("Debug Panel"):
            _render_debug(result, plays, home_name, away_name, hs, as_)

        with st.expander("Raw JSON"):
            st.json(result)


def _render_box_score(result, plays, home_name, away_name, home_score, away_score, hs, as_):
    home_q = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    away_q = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    for p in plays:
        q = p["quarter"]
        if q not in home_q:
            continue
        if p["result"] in ("touchdown", "punt_return_td"):
            if p["possession"] == "home":
                home_q[q] += 9
            else:
                away_q[q] += 9
        elif p["result"] == "successful_kick":
            pts = 5 if p["play_type"] == "drop_kick" else 3
            if p["possession"] == "home":
                home_q[q] += pts
            else:
                away_q[q] += pts
        elif p["result"] == "pindown":
            if p["possession"] == "home":
                home_q[q] += 1
            else:
                away_q[q] += 1
        elif p["result"] == "safety":
            if p["possession"] == "home":
                away_q[q] += 2
            else:
                home_q[q] += 2
        elif p["result"] == "fumble":
            if p["possession"] == "home":
                away_q[q] += 0.5
            else:
                home_q[q] += 0.5

    qtr_data = {
        "": [home_name, away_name],
        "Q1": [fmt_vb_score(home_q[1]), fmt_vb_score(away_q[1])],
        "Q2": [fmt_vb_score(home_q[2]), fmt_vb_score(away_q[2])],
        "Q3": [fmt_vb_score(home_q[3]), fmt_vb_score(away_q[3])],
        "Q4": [fmt_vb_score(home_q[4]), fmt_vb_score(away_q[4])],
        "Final": [fmt_vb_score(home_score), fmt_vb_score(away_score)],
    }
    st.dataframe(pd.DataFrame(qtr_data), hide_index=True, use_container_width=True)

    h_frp = hs.get('fumble_recovery_points', 0)
    a_frp = as_.get('fumble_recovery_points', 0)
    h_fr = hs.get('fumble_recoveries', 0)
    a_fr = as_.get('fumble_recoveries', 0)
    h_saf = hs.get('safeties_conceded', 0)
    a_saf = as_.get('safeties_conceded', 0)

    st.markdown("**Scoring**")
    scoring_labels = [
        "TDs (9pts)", "Snap Kicks (5pts)", "FGs (3pts)",
        "Safeties (2pts)", "Pindowns (1pt)", "Strikes (½pt)",
        "PR TDs", "Chaos Rec",
    ]
    scoring_home = [
        f"{hs['touchdowns']} ({hs['touchdowns'] * 9}pts)",
        f"{hs['drop_kicks_made']}/{hs.get('drop_kicks_attempted',0)} ({hs['drop_kicks_made'] * 5}pts)",
        f"{hs['place_kicks_made']}/{hs.get('place_kicks_attempted',0)} ({hs['place_kicks_made'] * 3}pts)",
        f"{a_saf} ({a_saf * 2}pts)",
        f"{hs.get('pindowns',0)} ({hs.get('pindowns',0)}pts)",
        f"{h_fr} ({h_frp:g}pts)",
        str(hs.get("punt_return_tds", 0)),
        str(hs.get("chaos_recoveries", 0)),
    ]
    scoring_away = [
        f"{as_['touchdowns']} ({as_['touchdowns'] * 9}pts)",
        f"{as_['drop_kicks_made']}/{as_.get('drop_kicks_attempted',0)} ({as_['drop_kicks_made'] * 5}pts)",
        f"{as_['place_kicks_made']}/{as_.get('place_kicks_attempted',0)} ({as_['place_kicks_made'] * 3}pts)",
        f"{h_saf} ({h_saf * 2}pts)",
        f"{as_.get('pindowns',0)} ({as_.get('pindowns',0)}pts)",
        f"{a_fr} ({a_frp:g}pts)",
        str(as_.get("punt_return_tds", 0)),
        str(as_.get("chaos_recoveries", 0)),
    ]
    scoring_df = pd.DataFrame({"Stat": scoring_labels, home_name: scoring_home, away_name: scoring_away})
    st.dataframe(scoring_df, hide_index=True, use_container_width=True,
                 column_config={"Stat": st.column_config.TextColumn(width="medium")})

    h_delta_yds = hs.get("delta_yards", 0)
    a_delta_yds = as_.get("delta_yards", 0)
    h_delta_dr = hs.get("delta_drives", 0)
    a_delta_dr = as_.get("delta_drives", 0)
    h_delta_sc = hs.get("delta_scores", 0)
    a_delta_sc = as_.get("delta_scores", 0)
    h_ce = hs.get("compelled_efficiency")
    a_ce = as_.get("compelled_efficiency")
    if h_delta_dr > 0 or a_delta_dr > 0:
        st.markdown("**Delta Yards & Compelled Efficiency**")
        delta_labels = [
            "Delta Yards", "Adjusted Yards",
            "Delta Drives", "Delta Scores",
            "Compelled Eff %",
        ]
        delta_home = [
            str(h_delta_yds),
            str(hs.get("adjusted_yards", hs["total_yards"])),
            str(h_delta_dr), str(h_delta_sc),
            f"{h_ce}%" if h_ce is not None else "—",
        ]
        delta_away = [
            str(a_delta_yds),
            str(as_.get("adjusted_yards", as_["total_yards"])),
            str(a_delta_dr), str(a_delta_sc),
            f"{a_ce}%" if a_ce is not None else "—",
        ]
        delta_df = pd.DataFrame({"Stat": delta_labels, home_name: delta_home, away_name: delta_away})
        st.dataframe(delta_df, hide_index=True, use_container_width=True,
                     column_config={"Stat": st.column_config.TextColumn(width="medium")})

    st.markdown("**Offensive Stats**")
    h_kp_att = hs.get("kick_passes_attempted", 0)
    h_kp_comp = hs.get("kick_passes_completed", 0)
    a_kp_att = as_.get("kick_passes_attempted", 0)
    a_kp_comp = as_.get("kick_passes_completed", 0)
    h_kp_pct = round(h_kp_comp / max(1, h_kp_att) * 100, 1) if h_kp_att else 0
    a_kp_pct = round(a_kp_comp / max(1, a_kp_att) * 100, 1) if a_kp_att else 0
    off_labels = [
        "Total Yards", "Rush Yds", "Lateral Yds", "KP Yds",
        "Yds/Play", "Plays",
        "Lat Chains", "Lat Eff",
        "KP (Comp/Att)", "KP %", "KP TDs", "KP INTs",
        "Long Play",
    ]
    off_home = [
        str(hs["total_yards"]),
        str(hs.get("rushing_yards", 0)),
        str(hs.get("lateral_yards", 0)),
        str(hs.get("kick_pass_yards", 0)),
        str(hs["yards_per_play"]), str(hs["total_plays"]),
        str(hs["lateral_chains"]), f'{hs["lateral_efficiency"]}%',
        f"{h_kp_comp}/{h_kp_att}",
        f"{h_kp_pct}%",
        str(hs.get("kick_pass_tds", 0)),
        str(hs.get("kick_pass_interceptions", 0)),
        str(max((p["yards"] for p in plays if p["possession"] == "home"), default=0)),
    ]
    off_away = [
        str(as_["total_yards"]),
        str(as_.get("rushing_yards", 0)),
        str(as_.get("lateral_yards", 0)),
        str(as_.get("kick_pass_yards", 0)),
        str(as_["yards_per_play"]), str(as_["total_plays"]),
        str(as_["lateral_chains"]), f'{as_["lateral_efficiency"]}%',
        f"{a_kp_comp}/{a_kp_att}",
        f"{a_kp_pct}%",
        str(as_.get("kick_pass_tds", 0)),
        str(as_.get("kick_pass_interceptions", 0)),
        str(max((p["yards"] for p in plays if p["possession"] == "away"), default=0)),
    ]
    off_df = pd.DataFrame({"Stat": off_labels, home_name: off_home, away_name: off_away})
    st.dataframe(off_df, hide_index=True, use_container_width=True,
                 column_config={"Stat": st.column_config.TextColumn(width="medium")})

    st.markdown("**Kicking & Special Teams**")
    kick_labels = [
        "DK (Made/Att)", "DK %",
        "FG (Made/Att)", "FG %",
        "Punts", "Pindowns",
        "Kick %",
    ]
    h_dk_pct = round(hs['drop_kicks_made'] / max(1, hs.get('drop_kicks_attempted', 0)) * 100, 1) if hs.get('drop_kicks_attempted', 0) else 0
    a_dk_pct = round(as_['drop_kicks_made'] / max(1, as_.get('drop_kicks_attempted', 0)) * 100, 1) if as_.get('drop_kicks_attempted', 0) else 0
    h_pk_pct = round(hs['place_kicks_made'] / max(1, hs.get('place_kicks_attempted', 0)) * 100, 1) if hs.get('place_kicks_attempted', 0) else 0
    a_pk_pct = round(as_['place_kicks_made'] / max(1, as_.get('place_kicks_attempted', 0)) * 100, 1) if as_.get('place_kicks_attempted', 0) else 0
    kick_home = [
        f"{hs['drop_kicks_made']}/{hs.get('drop_kicks_attempted',0)}",
        f"{h_dk_pct}%",
        f"{hs['place_kicks_made']}/{hs.get('place_kicks_attempted',0)}",
        f"{h_pk_pct}%",
        str(hs.get("punts", 0)),
        str(hs.get("pindowns", 0)),
        f"{hs.get('kick_percentage', 0)}%",
    ]
    kick_away = [
        f"{as_['drop_kicks_made']}/{as_.get('drop_kicks_attempted',0)}",
        f"{a_dk_pct}%",
        f"{as_['place_kicks_made']}/{as_.get('place_kicks_attempted',0)}",
        f"{a_pk_pct}%",
        str(as_.get("punts", 0)),
        str(as_.get("pindowns", 0)),
        f"{as_.get('kick_percentage', 0)}%",
    ]
    kick_df = pd.DataFrame({"Stat": kick_labels, home_name: kick_home, away_name: kick_away})
    st.dataframe(kick_df, hide_index=True, use_container_width=True,
                 column_config={"Stat": st.column_config.TextColumn(width="medium")})

    st.markdown("**Turnovers & Discipline**")
    turn_labels = [
        "Fumbles Lost", "TOD",
        "Penalties", "Pen Yds",
    ]
    turn_home = [
        str(hs["fumbles_lost"]), str(hs["turnovers_on_downs"]),
        str(hs.get("penalties", 0)), str(hs.get("penalty_yards", 0)),
    ]
    turn_away = [
        str(as_["fumbles_lost"]), str(as_["turnovers_on_downs"]),
        str(as_.get("penalties", 0)), str(as_.get("penalty_yards", 0)),
    ]
    turn_df = pd.DataFrame({"Stat": turn_labels, home_name: turn_home, away_name: turn_away})
    st.dataframe(turn_df, hide_index=True, use_container_width=True,
                 column_config={"Stat": st.column_config.TextColumn(width="medium")})

    st.markdown("**Keeper & Fatigue**")
    keep_labels = [
        "K Deflections", "K Tackles",
        "K Bells", "Fake TDs",
        "Avg Fatigue",
    ]
    keep_home = [
        str(hs.get("keeper_deflections", 0)),
        str(hs.get("keeper_tackles", 0)),
        str(hs.get("keeper_bells_generated", 0)),
        str(hs.get("keeper_fake_tds_allowed", 0)),
        f'{hs["avg_fatigue"]}%',
    ]
    keep_away = [
        str(as_.get("keeper_deflections", 0)),
        str(as_.get("keeper_tackles", 0)),
        str(as_.get("keeper_bells_generated", 0)),
        str(as_.get("keeper_fake_tds_allowed", 0)),
        f'{as_["avg_fatigue"]}%',
    ]
    keep_df = pd.DataFrame({"Stat": keep_labels, home_name: keep_home, away_name: keep_away})
    st.dataframe(keep_df, hide_index=True, use_container_width=True,
                 column_config={"Stat": st.column_config.TextColumn(width="medium")})

    st.markdown("**Down Conversions**")
    h_dc = hs.get("down_conversions", {})
    a_dc = as_.get("down_conversions", {})
    for d in [4, 5, 6]:
        hd = h_dc.get(d, h_dc.get(str(d), {"attempts": 0, "converted": 0, "rate": 0}))
        ad = a_dc.get(d, a_dc.get(str(d), {"attempts": 0, "converted": 0, "rate": 0}))
        label = f"{'4th' if d == 4 else '5th' if d == 5 else '6th'} Down"
        dc1, dc2 = st.columns(2)
        dc1.metric(f"{home_name} {label}", f"{hd['converted']}/{hd['attempts']} ({hd['rate']}%)")
        dc2.metric(f"{away_name} {label}", f"{ad['converted']}/{ad['attempts']} ({ad['rate']}%)")

    penalty_plays = [p for p in plays if p.get("penalty")]
    if penalty_plays:
        st.markdown("**Penalties**")
        pen_home = [p for p in penalty_plays if p["penalty"]["on_team"] == "home" and not p["penalty"]["declined"]]
        pen_away = [p for p in penalty_plays if p["penalty"]["on_team"] == "away" and not p["penalty"]["declined"]]
        pen_dec = [p for p in penalty_plays if p["penalty"]["declined"]]
        pc1, pc2, pc3 = st.columns(3)
        pc1.metric(f"{home_name} Penalties", f"{len(pen_home)} for {sum(p['penalty']['yards'] for p in pen_home)} yds")
        pc2.metric(f"{away_name} Penalties", f"{len(pen_away)} for {sum(p['penalty']['yards'] for p in pen_away)} yds")
        pc3.metric("Declined", len(pen_dec))

        all_accepted = pen_home + pen_away
        if all_accepted:
            pen_data = []
            for p in all_accepted:
                pen_data.append({
                    "Q": p["quarter"],
                    "Time": p["time_remaining"],
                    "Penalty": p["penalty"]["name"],
                    "On": home_name if p["penalty"]["on_team"] == "home" else away_name,
                    "Player": p["penalty"]["player"],
                    "Yards": p["penalty"]["yards"],
                    "Phase": p["penalty"]["phase"],
                })
            st.dataframe(pd.DataFrame(pen_data), hide_index=True, use_container_width=True)

    player_stats = result.get("player_stats", {})
    if player_stats.get("home") or player_stats.get("away"):
        st.markdown("**Player Performance**")
        ptab1, ptab2 = st.tabs([home_name, away_name])
        for ptab, side, tname in [(ptab1, "home", home_name), (ptab2, "away", away_name)]:
            with ptab:
                pstats = player_stats.get(side, [])
                if pstats:
                    pdf = pd.DataFrame(pstats)
                    stab1, stab2, stab3, stab4, stab5, stab6 = st.tabs(
                        ["Rushing & Scoring", "Lateral Game", "Kick Pass", "Kicking", "Defense", "Returns & Special Teams"]
                    )
                    with stab1:
                        rush_cols = ["tag", "name", "archetype", "touches", "yards",
                                     "rushing_yards", "tds", "fumbles"]
                        rush_avail = [c for c in rush_cols if c in pdf.columns]
                        rush_df = pdf[pdf["touches"] > 0][rush_avail].copy() if "touches" in pdf.columns else pdf[rush_avail].copy()
                        rush_df.rename(columns={
                            "tag": "Tag", "name": "Name", "archetype": "Archetype",
                            "touches": "Touches", "yards": "Yards",
                            "rushing_yards": "Rush Yds", "tds": "TDs", "fumbles": "Fum",
                        }, inplace=True)
                        if not rush_df.empty:
                            st.dataframe(rush_df, hide_index=True, use_container_width=True)
                        else:
                            st.caption("No rushing data.")
                    with stab2:
                        lat_cols = ["tag", "name", "archetype", "laterals_thrown",
                                    "lateral_receptions", "lateral_assists",
                                    "lateral_yards", "lateral_tds"]
                        lat_avail = [c for c in lat_cols if c in pdf.columns]
                        lat_df = pdf[lat_avail].copy()
                        has_lat = lat_df.drop(columns=[c for c in ["tag", "name", "archetype"] if c in lat_df.columns], errors="ignore")
                        lat_df = lat_df[has_lat.sum(axis=1) > 0] if not has_lat.empty else lat_df
                        lat_df.rename(columns={
                            "tag": "Tag", "name": "Name", "archetype": "Archetype",
                            "laterals_thrown": "Thrown", "lateral_receptions": "Received",
                            "lateral_assists": "Assists", "lateral_yards": "Lat Yds",
                            "lateral_tds": "Lat TDs",
                        }, inplace=True)
                        if not lat_df.empty:
                            st.dataframe(lat_df, hide_index=True, use_container_width=True)
                        else:
                            st.caption("No lateral data.")
                    with stab3:
                        kp_cols = ["tag", "name", "archetype",
                                   "kick_passes_thrown", "kick_passes_completed",
                                   "kick_pass_yards", "kick_pass_tds",
                                   "kick_pass_interceptions_thrown",
                                   "kick_pass_receptions", "kick_pass_ints"]
                        kp_avail = [c for c in kp_cols if c in pdf.columns]
                        kp_df = pdf[kp_avail].copy()
                        has_kp = kp_df.drop(columns=[c for c in ["tag", "name", "archetype"] if c in kp_df.columns], errors="ignore")
                        kp_df = kp_df[has_kp.sum(axis=1) > 0] if not has_kp.empty else kp_df
                        kp_df.rename(columns={
                            "tag": "Tag", "name": "Name", "archetype": "Archetype",
                            "kick_passes_thrown": "KP Att", "kick_passes_completed": "KP Comp",
                            "kick_pass_yards": "KP Yds", "kick_pass_tds": "KP TD",
                            "kick_pass_interceptions_thrown": "KP INT",
                            "kick_pass_receptions": "KP Rec", "kick_pass_ints": "Def KP INT",
                        }, inplace=True)
                        if not kp_df.empty:
                            st.dataframe(kp_df, hide_index=True, use_container_width=True)
                        else:
                            st.caption("No kick pass data.")
                    with stab4:
                        kick_cols = ["tag", "name", "archetype",
                                     "pk_att", "pk_made", "dk_att", "dk_made",
                                     "kick_att", "kick_made"]
                        kick_avail = [c for c in kick_cols if c in pdf.columns]
                        kick_df = pdf[kick_avail].copy()
                        has_kick = pd.Series([0]*len(kick_df), index=kick_df.index)
                        for kc in ["kick_att", "pk_att", "dk_att"]:
                            if kc in kick_df.columns:
                                has_kick = has_kick + kick_df[kc].fillna(0)
                        kick_df = kick_df[has_kick > 0]
                        kick_df.rename(columns={
                            "tag": "Tag", "name": "Name", "archetype": "Archetype",
                            "pk_att": "FG Att", "pk_made": "FG Made",
                            "dk_att": "Snap Kick Att", "dk_made": "Snap Kick Made",
                            "kick_att": "Total K Att", "kick_made": "Total K Made",
                        }, inplace=True)
                        if not kick_df.empty:
                            for _, row in kick_df.iterrows():
                                st.markdown(f"**{row.get('Name', '')}** ({row.get('Tag', '')})")
                                kc1, kc2, kc3 = st.columns(3)
                                kc1.metric("Field Goals (3pts)", f"{row.get('FG Made', 0)}/{row.get('FG Att', 0)}")
                                kc2.metric("Snap Kicks (5pts)", f"{row.get('Snap Kick Made', 0)}/{row.get('Snap Kick Att', 0)}")
                                kc3.metric("Total Kicks", f"{row.get('Total K Made', 0)}/{row.get('Total K Att', 0)}")
                            st.divider()
                            st.dataframe(kick_df, hide_index=True, use_container_width=True)
                        else:
                            st.caption("No kicking data.")
                    with stab5:
                        def_cols = ["tag", "name", "archetype", "tackles", "tfl",
                                    "sacks", "hurries", "kick_pass_ints"]
                        def_avail = [c for c in def_cols if c in pdf.columns]
                        def_df = pdf[def_avail].copy()
                        has_def = def_df.drop(columns=[c for c in ["tag", "name", "archetype"] if c in def_df.columns], errors="ignore")
                        def_df = def_df[has_def.sum(axis=1) > 0] if not has_def.empty else def_df
                        def_df.rename(columns={
                            "tag": "Tag", "name": "Name", "archetype": "Archetype",
                            "tackles": "Tackles", "tfl": "TFL",
                            "sacks": "Sacks", "hurries": "Hurries",
                            "kick_pass_ints": "KP INT",
                        }, inplace=True)
                        if not def_df.empty:
                            st.dataframe(def_df, hide_index=True, use_container_width=True)
                        else:
                            st.caption("No defensive data.")
                    with stab6:
                        ret_cols = ["tag", "name", "archetype",
                                    "kick_returns", "kick_return_yards", "kick_return_tds",
                                    "punt_returns", "punt_return_yards", "punt_return_tds",
                                    "muffs", "st_tackles",
                                    "kick_deflections", "keeper_bells", "coverage_snaps",
                                    "keeper_tackles", "keeper_return_yards"]
                        ret_avail = [c for c in ret_cols if c in pdf.columns]
                        ret_df = pdf[ret_avail].copy()
                        has_ret = ret_df.drop(columns=[c for c in ["tag", "name", "archetype"] if c in ret_df.columns], errors="ignore")
                        ret_df = ret_df[has_ret.sum(axis=1) > 0] if not has_ret.empty else ret_df
                        ret_df.rename(columns={
                            "tag": "Tag", "name": "Name", "archetype": "Archetype",
                            "kick_returns": "KR", "kick_return_yards": "KR Yds",
                            "kick_return_tds": "KR TD",
                            "punt_returns": "PR", "punt_return_yards": "PR Yds",
                            "punt_return_tds": "PR TD",
                            "muffs": "Muffs", "st_tackles": "ST Tkl",
                            "kick_deflections": "Defl", "keeper_bells": "Bells",
                            "coverage_snaps": "Cov Snaps", "keeper_tackles": "KP Tkl",
                            "keeper_return_yards": "KP Ret Yds",
                        }, inplace=True)
                        if not ret_df.empty:
                            st.dataframe(ret_df, hide_index=True, use_container_width=True)
                        else:
                            st.caption("No returns/special teams data.")
                else:
                    st.caption("No player stat data available.")


def _render_drives(result, home_name, away_name):
    drives = result.get("drive_summary", [])
    if drives:
        home_drives = [d for d in drives if d["team"] == "home"]
        away_drives = [d for d in drives if d["team"] == "away"]

        d1, d2, d3, d4 = st.columns(4)
        d1.metric(f"{home_name} Drives", len(home_drives))
        d2.metric(f"{away_name} Drives", len(away_drives))
        home_avg_plays = sum(d["plays"] for d in home_drives) / max(1, len(home_drives))
        away_avg_plays = sum(d["plays"] for d in away_drives) / max(1, len(away_drives))
        d3.metric(f"{home_name} Avg Plays/Drive", f"{home_avg_plays:.1f}")
        d4.metric(f"{away_name} Avg Plays/Drive", f"{away_avg_plays:.1f}")

        drive_rows = []
        for i, d in enumerate(drives):
            team_label = home_name if d["team"] == "home" else away_name
            result_lbl = drive_result_label(d["result"])
            if d.get("delta_drive"):
                result_lbl += " Δ"
            drive_rows.append({
                "#": i + 1,
                "Team": team_label,
                "Qtr": f"Q{d['quarter']}",
                "Start": f"{d['start_yard_line']}yd",
                "Plays": d["plays"],
                "Yards": d["yards"],
                "Result": result_lbl,
            })
        st.dataframe(pd.DataFrame(drive_rows), hide_index=True, use_container_width=True, height=400)

        drive_outcomes = {}
        for d in drives:
            r = drive_result_label(d["result"])
            drive_outcomes[r] = drive_outcomes.get(r, 0) + 1

        fig = px.bar(x=list(drive_outcomes.keys()), y=list(drive_outcomes.values()),
                     title="Drive Outcomes",
                     color=list(drive_outcomes.keys()),
                     color_discrete_map={
                         "TD": "#16a34a", "FG": "#2563eb", "FUMBLE": "#dc2626",
                         "DOWNS": "#d97706", "PUNT": "#94a3b8", "MISSED FG": "#d97706",
                         "END OF QUARTER": "#64748b", "PINDOWN": "#a855f7",
                         "PUNT RET TD": "#16a34a", "CHAOS REC": "#f97316",
                     })
        fig.update_layout(showlegend=False, height=300, xaxis_title="Outcome", yaxis_title="Count",
                         template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No drive data available.")


def _render_play_by_play(plays, home_name, away_name):
    play_df = pd.DataFrame(plays)

    quarter_filter = st.selectbox("Filter by Quarter", ["All", "Q1", "Q2", "Q3", "Q4"])
    if quarter_filter != "All":
        q = int(quarter_filter[1])
        play_df = play_df[play_df["quarter"] == q]

    if not play_df.empty:
        display_df = play_df.copy()
        if "time_remaining" in display_df.columns:
            display_df["time"] = display_df["time_remaining"].apply(format_time)
        if "possession" in display_df.columns:
            display_df["team"] = display_df["possession"].apply(
                lambda x: home_name if x == "home" else away_name)

        show_cols = ["play_number", "team", "time", "down", "field_position",
                     "play_family", "description", "yards", "result", "fatigue"]
        available = [c for c in show_cols if c in display_df.columns]
        st.dataframe(display_df[available], hide_index=True, use_container_width=True, height=500)
    else:
        st.caption("No plays to display.")


def _render_analytics(result, plays, home_name, away_name, hs, as_):
    st.markdown("**VPA — Viperball Points Added**")
    st.caption("Play efficiency vs league-average expectation from same field position & down.")
    h_vpa = hs.get("epa", {})
    a_vpa = as_.get("epa", {})

    v1, v2 = st.columns(2)
    v1.metric(f"{home_name} Total VPA", h_vpa.get("total_vpa", h_vpa.get("total_epa", 0)))
    v2.metric(f"{away_name} Total VPA", a_vpa.get("total_vpa", a_vpa.get("total_epa", 0)))

    v3, v4, v5, v6 = st.columns(4)
    v3.metric(f"{home_name} VPA/Play", h_vpa.get("vpa_per_play", h_vpa.get("epa_per_play", 0)))
    v4.metric(f"{away_name} VPA/Play", a_vpa.get("vpa_per_play", a_vpa.get("epa_per_play", 0)))
    v5.metric(f"{home_name} Success Rate", f"{h_vpa.get('success_rate', 0)}%")
    v6.metric(f"{away_name} Success Rate", f"{a_vpa.get('success_rate', 0)}%")

    v7, v8, v9, v10 = st.columns(4)
    v7.metric(f"{home_name} Explosiveness", h_vpa.get("explosiveness", 0))
    v8.metric(f"{away_name} Explosiveness", a_vpa.get("explosiveness", 0))
    v9.metric(f"{home_name} Off VPA", h_vpa.get("offense_vpa", h_vpa.get("offense_epa", 0)))
    v10.metric(f"{away_name} Off VPA", a_vpa.get("offense_vpa", a_vpa.get("offense_epa", 0)))

    vpa_plays = [p for p in plays if "epa" in p]
    if vpa_plays:
        home_vpa_plays = [p for p in vpa_plays if p["possession"] == "home"]
        away_vpa_plays = [p for p in vpa_plays if p["possession"] == "away"]

        fig_vpa = go.Figure()
        if home_vpa_plays:
            home_cum = []
            running = 0
            for p in home_vpa_plays:
                running += p["epa"]
                home_cum.append(round(running, 2))
            fig_vpa.add_trace(go.Scatter(
                y=home_cum, mode="lines", name=home_name,
                line=dict(color="#2563eb", width=2)
            ))
        if away_vpa_plays:
            away_cum = []
            running = 0
            for p in away_vpa_plays:
                running += p["epa"]
                away_cum.append(round(running, 2))
            fig_vpa.add_trace(go.Scatter(
                y=away_cum, mode="lines", name=away_name,
                line=dict(color="#dc2626", width=2)
            ))
        fig_vpa.update_layout(
            title="Cumulative VPA Over Game",
            xaxis_title="Play #", yaxis_title="Cumulative VPA",
            height=350, template="plotly_white"
        )
        st.plotly_chart(fig_vpa, use_container_width=True)

    st.markdown("**Play Family Distribution**")
    home_fam = hs.get("play_family_breakdown", {})
    away_fam = as_.get("play_family_breakdown", {})

    all_families = sorted(set(list(home_fam.keys()) + list(away_fam.keys())))
    home_total = sum(home_fam.values()) or 1
    away_total = sum(away_fam.values()) or 1

    fam_chart_data = []
    for f in all_families:
        fam_chart_data.append({"Family": f.replace("_", " ").title(), "Team": home_name,
                               "Pct": round(home_fam.get(f, 0) / home_total * 100, 1)})
        fam_chart_data.append({"Family": f.replace("_", " ").title(), "Team": away_name,
                               "Pct": round(away_fam.get(f, 0) / away_total * 100, 1)})

    fig = px.bar(pd.DataFrame(fam_chart_data), x="Family", y="Pct", color="Team",
                 barmode="group", title="Play Call Distribution (%)",
                 labels={"Pct": "Percentage", "Family": "Play Family"})
    fig.update_layout(yaxis_ticksuffix="%", height=350, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)


def _render_export(result, home_name, away_name, actual_seed):
    st.markdown("Download game data in various formats.")
    home_safe = safe_filename(home_name)
    away_safe = safe_filename(away_name)
    game_tag = f"{home_safe}_vs_{away_safe}_s{actual_seed}"

    ex1, ex2 = st.columns(2)
    with ex1:
        md_content = generate_box_score_markdown(result)
        st.download_button(
            "Box Score (.md)",
            data=md_content,
            file_name=f"{game_tag}_box_score.md",
            mime="text/markdown",
            use_container_width=True,
        )
        csv_plays = generate_play_log_csv(result)
        st.download_button(
            "Play Log (.csv)",
            data=csv_plays,
            file_name=f"{game_tag}_plays.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with ex2:
        csv_drives = generate_drives_csv(result)
        st.download_button(
            "Drives (.csv)",
            data=csv_drives,
            file_name=f"{game_tag}_drives.csv",
            mime="text/csv",
            use_container_width=True,
        )
        json_str = json.dumps(result, indent=2, default=str)
        st.download_button(
            "Full JSON",
            data=json_str,
            file_name=f"{game_tag}_full.json",
            mime="application/json",
            use_container_width=True,
        )


def _render_debug(result, plays, home_name, away_name, hs, as_):
    st.markdown("**Fatigue Over Time**")
    home_fat = []
    away_fat = []
    for p in plays:
        if p.get("fatigue") is not None:
            entry = {"play": p["play_number"], "fatigue": p["fatigue"]}
            if p["possession"] == "home":
                home_fat.append({**entry, "team": home_name})
            else:
                away_fat.append({**entry, "team": away_name})

    if home_fat or away_fat:
        fat_df = pd.DataFrame(home_fat + away_fat)
        fig = px.line(fat_df, x="play", y="fatigue", color="team",
                      title="Fatigue Curve")
        fig.update_yaxes(range=[30, 105])
        fig.update_layout(height=300, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Turnover Triggers**")
    fumble_plays = [p for p in plays if p.get("fumble")]
    tod_plays = [p for p in plays if p["result"] == "turnover_on_downs"]
    tc1, tc2 = st.columns(2)
    tc1.metric("Fumbles", len(fumble_plays))
    tc2.metric("Turnovers on Downs", len(tod_plays))

    if fumble_plays:
        st.markdown("*Fumble locations:*")
        for fp in fumble_plays:
            team_label = home_name if fp["possession"] == "home" else away_name
            st.text(f"  Q{fp['quarter']} {format_time(fp['time_remaining'])} | {team_label} at {fp['field_position']}yd | {fp['description']}")

    st.markdown("**Explosive Plays (15+ yards)**")
    big_plays = [p for p in plays if p["yards"] >= 15 and p["play_type"] not in ["punt"]]
    if big_plays:
        for bp in big_plays:
            team_label = home_name if bp["possession"] == "home" else away_name
            st.text(f"  Q{bp['quarter']} | {team_label} | {bp['yards']}yds | {bp['description']}")
    else:
        st.text("  No explosive plays")

    st.markdown("**Kick Decision Summary**")
    kick_plays = [p for p in plays if p["play_type"] in ["drop_kick", "place_kick", "punt", "kick_pass"]]
    kc1, kc2, kc3, kc4 = st.columns(4)
    punts = [p for p in kick_plays if p["play_type"] == "punt"]
    drops = [p for p in kick_plays if p["play_type"] == "drop_kick"]
    places = [p for p in kick_plays if p["play_type"] == "place_kick"]
    kpasses = [p for p in kick_plays if p["play_type"] == "kick_pass"]
    kc1.metric("Punts", len(punts))
    kc2.metric("Snap Kick Attempts", len(drops))
    kc3.metric("Field Goal Attempts", len(places))
    kc4.metric("Kick Passes", len(kpasses))

    st.markdown("**Style Parameters**")
    sc1, sc2 = st.columns(2)
    h_style_key = result.get("home_style", "balanced")
    a_style_key = result.get("away_style", "balanced")
    h_style = OFFENSE_STYLES.get(h_style_key, OFFENSE_STYLES["balanced"])
    a_style = OFFENSE_STYLES.get(a_style_key, OFFENSE_STYLES["balanced"])
    with sc1:
        st.markdown(f"**{home_name}** ({h_style['label']})")
        st.text(f"  Tempo: {h_style['tempo']}")
        st.text(f"  Lateral Risk: {h_style['lateral_risk']}")
        st.text(f"  Kick Rate: {h_style['kick_rate']}")
        st.text(f"  Option Rate: {h_style['option_rate']}")
    with sc2:
        st.markdown(f"**{away_name}** ({a_style['label']})")
        st.text(f"  Tempo: {a_style['tempo']}")
        st.text(f"  Lateral Risk: {a_style['lateral_risk']}")
        st.text(f"  Kick Rate: {a_style['kick_rate']}")
        st.text(f"  Option Rate: {a_style['option_rate']}")

    st.markdown("**Special Teams Events**")
    blocked_punts = [p for p in plays if p.get("result") == "blocked_punt"]
    muffed_punts = [p for p in plays if p.get("result") == "muffed_punt"]
    blocked_kicks = [p for p in plays if p.get("result") == "blocked_kick"]
    st_c1, st_c2, st_c3 = st.columns(3)
    st_c1.metric("Blocked Punts", len(blocked_punts))
    st_c2.metric("Muffed Punts", len(muffed_punts))
    st_c3.metric("Blocked Kicks", len(blocked_kicks))
    all_st_events = blocked_punts + muffed_punts + blocked_kicks
    if all_st_events:
        for ev in sorted(all_st_events, key=lambda p: p.get("play_number", 0)):
            st.text(f"  Q{ev.get('quarter', '?')} | {ev.get('result', '').replace('_', ' ').upper()} | {ev.get('description', '')}")
    else:
        st.caption("No special teams chaos this game.")

    st.markdown("**Viperball Metrics (0-100)**")
    try:
        home_metrics = calculate_viperball_metrics(result, "home")
        away_metrics = calculate_viperball_metrics(result, "away")
        mc1, mc2 = st.columns(2)
        metric_labels = {
            "opi": "OPI (Overall)",
            "territory_rating": "Territory Rating",
            "pressure_index": "Pressure Index",
            "chaos_factor": "Chaos Factor",
            "kicking_efficiency": "Kicking Efficiency",
            "drive_quality": "Drive Quality",
            "turnover_impact": "Turnover Impact",
        }
        with mc1:
            st.markdown(f"*{home_name}*")
            for k, label in metric_labels.items():
                v = home_metrics.get(k, 0)
                display = f"{v:.1f}" if k != "drive_quality" else f"{v:.2f}/10"
                st.text(f"  {label}: {display}")
        with mc2:
            st.markdown(f"*{away_name}*")
            for k, label in metric_labels.items():
                v = away_metrics.get(k, 0)
                display = f"{v:.1f}" if k != "drive_quality" else f"{v:.2f}/10"
                st.text(f"  {label}: {display}")
    except Exception:
        st.caption("Metrics unavailable for this game result")
