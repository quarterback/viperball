import sys
import os
import random
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from engine import ViperballEngine, load_team_from_json, get_available_teams, get_available_styles, OFFENSE_STYLES

st.set_page_config(
    page_title="Viperball Sandbox",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { max-width: 100%; }
    .block-container { padding-top: 1rem; }
    div[data-testid="stMetric"] {
        background-color: #1e1e2e;
        border: 1px solid #333;
        padding: 12px;
        border-radius: 8px;
    }
    .score-big {
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        line-height: 1;
        margin: 0;
    }
    .team-name {
        font-size: 1.1rem;
        font-weight: 600;
        text-align: center;
        opacity: 0.8;
        margin-bottom: 4px;
    }
    .drive-td { color: #22c55e; font-weight: 700; }
    .drive-kick { color: #3b82f6; font-weight: 700; }
    .drive-fumble { color: #ef4444; font-weight: 700; }
    .drive-downs { color: #f59e0b; font-weight: 700; }
    .drive-punt { color: #94a3b8; }
</style>
""", unsafe_allow_html=True)

teams = get_available_teams()
styles = get_available_styles()
team_names = {t["key"]: t["name"] for t in teams}
style_keys = list(styles.keys())


def load_team(key):
    return load_team_from_json(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams", f"{key}.json"))


def format_time(seconds):
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"


def drive_result_label(result):
    labels = {
        "touchdown": "TD",
        "successful_kick": "FG",
        "fumble": "FUMBLE",
        "turnover_on_downs": "DOWNS",
        "punt": "PUNT",
        "missed_kick": "MISSED FG",
        "stall": "END OF QUARTER",
    }
    return labels.get(result, result.upper())


def drive_result_color(result):
    colors = {
        "touchdown": "#22c55e",
        "successful_kick": "#3b82f6",
        "fumble": "#ef4444",
        "turnover_on_downs": "#f59e0b",
        "punt": "#94a3b8",
        "missed_kick": "#f59e0b",
        "stall": "#64748b",
    }
    return colors.get(result, "#94a3b8")


page = st.sidebar.radio("Navigation", ["Game Simulator", "Debug Tools", "Play Inspector"], index=0)


if page == "Game Simulator":
    st.title("Viperball Game Simulator")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Home Team")
        home_key = st.selectbox("Select Home Team", [t["key"] for t in teams],
                                format_func=lambda x: team_names[x], key="home")
        home_style = st.selectbox("Home Offense Style", style_keys,
                                  format_func=lambda x: styles[x]["label"],
                                  index=style_keys.index(next((t["default_style"] for t in teams if t["key"] == home_key), "balanced")),
                                  key="home_style")
        st.caption(styles[home_style]["description"])

    with col2:
        st.subheader("Away Team")
        away_key = st.selectbox("Select Away Team", [t["key"] for t in teams],
                                format_func=lambda x: team_names[x],
                                index=min(1, len(teams) - 1), key="away")
        away_style = st.selectbox("Away Offense Style", style_keys,
                                  format_func=lambda x: styles[x]["label"],
                                  index=style_keys.index(next((t["default_style"] for t in teams if t["key"] == away_key), "balanced")),
                                  key="away_style")
        st.caption(styles[away_style]["description"])

    col_seed, col_btn = st.columns([1, 2])
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

        engine = ViperballEngine(home_team, away_team, seed=actual_seed, style_overrides=style_overrides)

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

        st.divider()

        sc1, sc2, sc3 = st.columns([2, 1, 2])
        with sc1:
            st.markdown(f'<p class="team-name">{home_name}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="score-big">{home_score}</p>', unsafe_allow_html=True)
        with sc2:
            st.markdown("<p style='text-align:center; padding-top:10px; font-size:1.2rem; opacity:0.5;'>vs</p>", unsafe_allow_html=True)
            st.caption(f"Seed: {actual_seed}")
        with sc3:
            st.markdown(f'<p class="team-name">{away_name}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="score-big">{away_score}</p>', unsafe_allow_html=True)

        if home_score > away_score:
            st.success(f"{home_name} wins by {home_score - away_score}")
        elif away_score > home_score:
            st.success(f"{away_name} wins by {away_score - home_score}")
        else:
            st.info("Game ended in a tie")

        # ====== 1. REAL BOX SCORE ======
        st.subheader("Box Score")

        plays = result["play_by_play"]
        home_q = {1: 0, 2: 0, 3: 0, 4: 0}
        away_q = {1: 0, 2: 0, 3: 0, 4: 0}
        for p in plays:
            q = p["quarter"]
            if q not in home_q:
                continue
            if p["result"] == "touchdown":
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

        qtr_data = {
            "": [home_name, away_name],
            "Q1": [home_q[1], away_q[1]],
            "Q2": [home_q[2], away_q[2]],
            "Q3": [home_q[3], away_q[3]],
            "Q4": [home_q[4], away_q[4]],
            "Final": [home_score, away_score],
        }
        st.dataframe(pd.DataFrame(qtr_data), hide_index=True, use_container_width=True)

        st.markdown("**Scoring Breakdown**")
        scoring_data = {
            "": ["Touchdowns (9pts)", "Drop Kicks (5pts)", "Place Kicks (3pts)",
                 "Total Yards", "Yards/Play", "Total Plays",
                 "Lateral Chains", "Lateral Efficiency",
                 "Fumbles Lost", "Turnovers on Downs",
                 "Longest Play", "Avg Fatigue"],
            home_name: [
                f"{hs['touchdowns']} ({hs['touchdowns'] * 9}pts)",
                f"{hs['drop_kicks_made']} ({hs['drop_kicks_made'] * 5}pts)",
                f"{hs['place_kicks_made']} ({hs['place_kicks_made'] * 3}pts)",
                hs["total_yards"], hs["yards_per_play"], hs["total_plays"],
                hs["lateral_chains"], f'{hs["lateral_efficiency"]}%',
                hs["fumbles_lost"], hs["turnovers_on_downs"],
                max((p["yards"] for p in plays if p["possession"] == "home"), default=0),
                f'{hs["avg_fatigue"]}%',
            ],
            away_name: [
                f"{as_['touchdowns']} ({as_['touchdowns'] * 9}pts)",
                f"{as_['drop_kicks_made']} ({as_['drop_kicks_made'] * 5}pts)",
                f"{as_['place_kicks_made']} ({as_['place_kicks_made'] * 3}pts)",
                as_["total_yards"], as_["yards_per_play"], as_["total_plays"],
                as_["lateral_chains"], f'{as_["lateral_efficiency"]}%',
                as_["fumbles_lost"], as_["turnovers_on_downs"],
                max((p["yards"] for p in plays if p["possession"] == "away"), default=0),
                f'{as_["avg_fatigue"]}%',
            ],
        }
        st.dataframe(pd.DataFrame(scoring_data), hide_index=True, use_container_width=True)

        # ====== 2. PLAY FAMILY DISTRIBUTION ======
        st.subheader("Play Family Distribution")
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
        fig.update_layout(yaxis_ticksuffix="%", height=350)
        st.plotly_chart(fig, use_container_width=True)

        # ====== 3. DRIVE OUTCOME PANEL ======
        st.subheader("Drive Summary")
        drives = result.get("drive_summary", [])
        if drives:
            drive_rows = []
            for i, d in enumerate(drives):
                team_label = home_name if d["team"] == "home" else away_name
                drive_rows.append({
                    "#": i + 1,
                    "Team": team_label,
                    "Qtr": f"Q{d['quarter']}",
                    "Start": f"{d['start_yard_line']}yd",
                    "Plays": d["plays"],
                    "Yards": d["yards"],
                    "Result": drive_result_label(d["result"]),
                })
            st.dataframe(pd.DataFrame(drive_rows), hide_index=True, use_container_width=True, height=350)

            drive_outcomes = {}
            for d in drives:
                r = drive_result_label(d["result"])
                drive_outcomes[r] = drive_outcomes.get(r, 0) + 1

            fig = px.bar(x=list(drive_outcomes.keys()), y=list(drive_outcomes.values()),
                         title="Drive Outcomes",
                         color=list(drive_outcomes.keys()),
                         color_discrete_map={
                             "TD": "#22c55e", "FG": "#3b82f6", "FUMBLE": "#ef4444",
                             "DOWNS": "#f59e0b", "PUNT": "#94a3b8", "MISSED FG": "#f59e0b",
                             "END OF QUARTER": "#64748b",
                         })
            fig.update_layout(showlegend=False, height=300, xaxis_title="Outcome", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)

        # ====== 4. PLAY LOG WITH ROLE TAGS ======
        st.subheader("Play-by-Play")
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
            st.dataframe(display_df[available], hide_index=True, use_container_width=True, height=400)

        # ====== 5. DEBUG PANEL ======
        with st.expander("Debug Panel"):
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
                fig.update_layout(height=300)
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
            kick_plays = [p for p in plays if p["play_type"] in ["drop_kick", "place_kick", "punt"]]
            kc1, kc2, kc3 = st.columns(3)
            punts = [p for p in kick_plays if p["play_type"] == "punt"]
            drops = [p for p in kick_plays if p["play_type"] == "drop_kick"]
            places = [p for p in kick_plays if p["play_type"] == "place_kick"]
            kc1.metric("Punts", len(punts))
            kc2.metric("Drop Kick Attempts", len(drops))
            kc3.metric("Place Kick Attempts", len(places))

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

        with st.expander("Raw JSON"):
            st.json(result)


elif page == "Debug Tools":
    st.title("Debug Tools - Batch Simulation")

    col1, col2 = st.columns(2)
    with col1:
        home_key = st.selectbox("Home Team", [t["key"] for t in teams],
                                format_func=lambda x: team_names[x], key="dbg_home")
        home_style = st.selectbox("Home Style", style_keys,
                                  format_func=lambda x: styles[x]["label"], key="dbg_home_style")
    with col2:
        away_key = st.selectbox("Away Team", [t["key"] for t in teams],
                                format_func=lambda x: team_names[x],
                                index=min(1, len(teams) - 1), key="dbg_away")
        away_style = st.selectbox("Away Style", style_keys,
                                  format_func=lambda x: styles[x]["label"], key="dbg_away_style")

    col_n, col_seed = st.columns(2)
    with col_n:
        num_sims = st.slider("Number of Simulations", 5, 200, 50)
    with col_seed:
        base_seed = st.number_input("Base Seed (0 = random)", min_value=0, max_value=999999, value=42, key="dbg_seed")

    run_batch = st.button("Run Batch Simulation", type="primary", use_container_width=True)

    if run_batch:
        home_team_data = load_team(home_key)
        away_team_data = load_team(away_key)
        style_overrides = {home_team_data.name: home_style, away_team_data.name: away_style}

        results = []
        progress = st.progress(0)
        for i in range(num_sims):
            s = (base_seed + i) if base_seed > 0 else None
            home_t = load_team(home_key)
            away_t = load_team(away_key)
            engine = ViperballEngine(home_t, away_t, seed=s, style_overrides=style_overrides)
            r = engine.simulate_game()
            results.append(r)
            progress.progress((i + 1) / num_sims)
        progress.empty()

        st.session_state["batch_results"] = results

    if "batch_results" in st.session_state:
        results = st.session_state["batch_results"]
        n = len(results)

        home_name = results[0]["final_score"]["home"]["team"]
        away_name = results[0]["final_score"]["away"]["team"]

        home_scores = [r["final_score"]["home"]["score"] for r in results]
        away_scores = [r["final_score"]["away"]["score"] for r in results]
        home_wins = sum(1 for h, a in zip(home_scores, away_scores) if h > a)
        away_wins = sum(1 for h, a in zip(home_scores, away_scores) if a > h)
        ties = n - home_wins - away_wins

        st.divider()
        st.subheader(f"Results: {n} Simulations")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(f"{home_name} Wins", home_wins)
        m2.metric(f"{away_name} Wins", away_wins)
        m3.metric("Ties", ties)
        m4.metric("Tie %", f"{round(ties / n * 100, 1)}%")

        st.subheader("Score Averages")
        avg1, avg2, avg3, avg4 = st.columns(4)
        avg1.metric(f"Avg {home_name}", round(sum(home_scores) / n, 1))
        avg2.metric(f"Avg {away_name}", round(sum(away_scores) / n, 1))

        home_yards = [r["stats"]["home"]["total_yards"] for r in results]
        away_yards = [r["stats"]["away"]["total_yards"] for r in results]
        avg3.metric(f"Avg {home_name} Yards", round(sum(home_yards) / n, 1))
        avg4.metric(f"Avg {away_name} Yards", round(sum(away_yards) / n, 1))

        st.subheader("Scoring Breakdown")
        avg5, avg6, avg7, avg8 = st.columns(4)
        home_tds = [r["stats"]["home"]["touchdowns"] for r in results]
        away_tds = [r["stats"]["away"]["touchdowns"] for r in results]
        avg5.metric("Avg TDs/game", round((sum(home_tds) + sum(away_tds)) / n, 2))
        home_fumbles = [r["stats"]["home"]["fumbles_lost"] for r in results]
        away_fumbles = [r["stats"]["away"]["fumbles_lost"] for r in results]
        avg6.metric("Avg Fumbles/game", round((sum(home_fumbles) + sum(away_fumbles)) / n, 2))

        longest_plays = []
        for r in results:
            max_play = max((p["yards"] for p in r["play_by_play"] if p["play_type"] not in ["punt"]), default=0)
            longest_plays.append(max_play)
        avg7.metric("Avg Longest Play", round(sum(longest_plays) / n, 1))
        avg8.metric("Max Longest Play", max(longest_plays))

        st.subheader("Score Distribution")
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=home_scores, name=home_name, opacity=0.7))
        fig.add_trace(go.Histogram(x=away_scores, name=away_name, opacity=0.7))
        fig.update_layout(barmode="overlay", xaxis_title="Score", yaxis_title="Frequency", height=350)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Drive Outcomes (aggregate)")
        all_drives = []
        for r in results:
            for d in r.get("drive_summary", []):
                all_drives.append(d)
        if all_drives:
            outcome_counts = {}
            for d in all_drives:
                r_label = drive_result_label(d["result"])
                outcome_counts[r_label] = outcome_counts.get(r_label, 0) + 1
            total_drives = len(all_drives)
            fig = px.bar(
                x=list(outcome_counts.keys()),
                y=[round(v / total_drives * 100, 1) for v in outcome_counts.values()],
                title=f"Drive Outcome Distribution ({total_drives} drives across {n} games)",
                labels={"x": "Outcome", "y": "Percentage"},
                color=list(outcome_counts.keys()),
                color_discrete_map={
                    "TD": "#22c55e", "FG": "#3b82f6", "FUMBLE": "#ef4444",
                    "DOWNS": "#f59e0b", "PUNT": "#94a3b8", "MISSED FG": "#f59e0b",
                    "END OF QUARTER": "#64748b",
                })
            fig.update_layout(showlegend=False, height=350, yaxis_ticksuffix="%")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Fatigue Curves")
        home_fatigue = []
        away_fatigue = []
        for r in results:
            plays = r["play_by_play"]
            for p in plays:
                if p["possession"] == "home" and p.get("fatigue") is not None:
                    home_fatigue.append({"play": p["play_number"], "fatigue": p["fatigue"], "team": home_name})
                elif p["possession"] == "away" and p.get("fatigue") is not None:
                    away_fatigue.append({"play": p["play_number"], "fatigue": p["fatigue"], "team": away_name})

        if home_fatigue or away_fatigue:
            fat_df = pd.DataFrame(home_fatigue + away_fatigue)
            avg_fat = fat_df.groupby(["play", "team"])["fatigue"].mean().reset_index()
            fig = px.line(avg_fat, x="play", y="fatigue", color="team",
                          title="Average Fatigue Over Play Number")
            fig.update_yaxes(range=[30, 105])
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Turnover Rates")
        home_tod = [r["stats"]["home"]["turnovers_on_downs"] for r in results]
        away_tod = [r["stats"]["away"]["turnovers_on_downs"] for r in results]

        to_data = {
            "Metric": ["Avg Fumbles", "Avg Turnovers on Downs", "Total Turnovers/Game"],
            home_name: [
                round(sum(home_fumbles) / n, 2),
                round(sum(home_tod) / n, 2),
                round((sum(home_fumbles) + sum(home_tod)) / n, 2),
            ],
            away_name: [
                round(sum(away_fumbles) / n, 2),
                round(sum(away_tod) / n, 2),
                round((sum(away_fumbles) + sum(away_tod)) / n, 2),
            ],
        }
        st.dataframe(pd.DataFrame(to_data), hide_index=True, use_container_width=True)


elif page == "Play Inspector":
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
        down = st.selectbox("Down", [1, 2, 3, 4, 5], key="pi_down")
        ytg = st.number_input("Yards to Go", min_value=1, max_value=99, value=20, key="pi_ytg")

    col_n, col_seed = st.columns(2)
    with col_n:
        num_plays = st.slider("Number of Plays to Run", 1, 500, 50, key="pi_num")
    with col_seed:
        pi_seed = st.number_input("Base Seed (0 = random)", min_value=0, max_value=999999, value=0, key="pi_seed")

    run_plays = st.button("Run Plays", type="primary", use_container_width=True)

    if run_plays:
        home_team = load_team(teams[0]["key"])
        away_team = load_team(teams[1]["key"] if len(teams) > 1 else teams[0]["key"])

        play_results = []
        for i in range(num_plays):
            s = (pi_seed + i) if pi_seed > 0 else None
            engine = ViperballEngine(home_team, away_team, seed=s)
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
