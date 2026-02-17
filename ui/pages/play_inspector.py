import csv
import io

import streamlit as st
import pandas as pd
import plotly.express as px

from engine import ViperballEngine, OFFENSE_STYLES
from engine.game_engine import WEATHER_CONDITIONS
from ui.helpers import load_team


def render_play_inspector(shared):
    teams = shared["teams"]
    styles = shared["styles"]
    style_keys = shared["style_keys"]

    st.title("Play Inspector - Single Play Runner")

    col1, col2 = st.columns(2)
    with col1:
        play_style = st.selectbox("Offense Style", style_keys,
                                  format_func=lambda x: styles[x]["label"], key="pi_style")
        st.caption(styles[play_style]["description"])

        style_info = OFFENSE_STYLES[play_style]
        st.write("**Style Parameters:**")
        st.write(f"- Tempo: {style_info['tempo']}")
        st.write(f"- Lateral Risk: {style_info['lateral_risk']}")
        st.write(f"- Kick Rate: {style_info['kick_rate']}")
        st.write(f"- Option Rate: {style_info['option_rate']}")

    with col2:
        field_pos = st.slider("Field Position (yards from own goal)", 1, 99, 40, key="pi_fp")
        down = st.selectbox("Down", [1, 2, 3, 4, 5, 6], key="pi_down")
        ytg = st.number_input("Yards to Go", min_value=1, max_value=99, value=20, key="pi_ytg")

    col_n, col_seed, col_piwx = st.columns(3)
    with col_n:
        num_plays = st.slider("Number of Plays to Run", 1, 500, 50, key="pi_num")
    with col_seed:
        pi_seed = st.number_input("Base Seed (0 = random)", min_value=0, max_value=999999, value=0, key="pi_seed")
    with col_piwx:
        pi_weather = st.selectbox("Weather", list(WEATHER_CONDITIONS.keys()),
                                  format_func=lambda x: WEATHER_CONDITIONS[x]["label"], key="pi_weather")

    run_plays = st.button("Run Plays", type="primary", use_container_width=True)

    if run_plays:
        home_team = load_team(teams[0]["key"])
        away_team = load_team(teams[1]["key"] if len(teams) > 1 else teams[0]["key"])

        play_results = []
        for i in range(num_plays):
            s = (pi_seed + i) if pi_seed > 0 else None
            engine = ViperballEngine(home_team, away_team, seed=s, weather=pi_weather)
            result = engine.simulate_single_play(
                style=play_style,
                field_position=field_pos,
                down=down,
                yards_to_go=ytg,
            )
            result["run_number"] = i + 1
            play_results.append(result)

        st.session_state["play_results"] = play_results

    if "play_results" in st.session_state:
        play_results = st.session_state["play_results"]
        n = len(play_results)

        st.divider()
        st.subheader(f"Results: {n} Plays")

        pi_output = io.StringIO()
        pi_writer = csv.writer(pi_output)
        pi_writer.writerow(["run", "play_family", "play_type", "yards", "result",
                            "description", "fatigue", "field_position"])
        for pr in play_results:
            pi_writer.writerow([
                pr.get("run_number", ""), pr.get("play_family", ""), pr.get("play_type", ""),
                pr["yards"], pr["result"], pr.get("description", ""),
                pr.get("fatigue", ""), pr.get("field_position", "")
            ])
        st.download_button(
            "Export Plays (.csv)",
            data=pi_output.getvalue(),
            file_name=f"play_inspector_{n}plays.csv",
            mime="text/csv",
        )

        yards_list = [p["yards"] for p in play_results]
        results_list = [p["result"] for p in play_results]
        families = [p.get("play_family", "unknown") for p in play_results]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Avg Yards", round(sum(yards_list) / n, 2))
        m2.metric("Max Yards", max(yards_list))
        m3.metric("Min Yards", min(yards_list))
        td_count = sum(1 for r in results_list if r == "touchdown")
        m4.metric("TD Rate", f"{round(td_count / n * 100, 1)}%")

        m5, m6, m7, m8 = st.columns(4)
        fd_count = sum(1 for r in results_list if r == "first_down")
        fumble_count = sum(1 for r in results_list if r == "fumble")
        m5.metric("First Down Rate", f"{round(fd_count / n * 100, 1)}%")
        m6.metric("Fumble Rate", f"{round(fumble_count / n * 100, 1)}%")
        gain_count = sum(1 for r in results_list if r == "gain")
        m7.metric("Gain (no FD)", f"{round(gain_count / n * 100, 1)}%")
        negative = sum(1 for y in yards_list if y < 0)
        m8.metric("Negative Plays", f"{round(negative / n * 100, 1)}%")

        st.subheader("Yards Distribution")
        fig = px.histogram(x=yards_list, nbins=30, title="Yards Gained Distribution")
        fig.update_xaxes(title="Yards")
        fig.update_yaxes(title="Frequency")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Result Breakdown")
        result_counts = {}
        for r in results_list:
            result_counts[r] = result_counts.get(r, 0) + 1
        fig = px.bar(x=list(result_counts.keys()), y=list(result_counts.values()),
                     title="Play Results")
        fig.update_xaxes(title="Result")
        fig.update_yaxes(title="Count")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Play Family Distribution")
        fam_counts = {}
        for f in families:
            fam_counts[f] = fam_counts.get(f, 0) + 1
        fig = px.pie(values=list(fam_counts.values()), names=list(fam_counts.keys()),
                     title="Play Families Selected")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Play-by-Play Detail")
        df = pd.DataFrame(play_results)
        display_cols = ["run_number", "play_family", "play_type", "yards", "result",
                        "description", "fatigue", "field_position"]
        available = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available], hide_index=True, use_container_width=True, height=400)
