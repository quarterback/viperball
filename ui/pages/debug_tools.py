import json
import io

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from engine import ViperballEngine
from engine.game_engine import WEATHER_CONDITIONS
from ui.helpers import load_team, fmt_vb_score, safe_filename, generate_batch_summary_csv, drive_result_label


def render_debug_tools(shared):
    teams = shared["teams"]
    team_names = shared["team_names"]
    styles = shared["styles"]
    style_keys = shared["style_keys"]

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

    col_n, col_seed, col_wx = st.columns(3)
    with col_n:
        num_sims = st.slider("Number of Simulations", 5, 200, 50)
    with col_seed:
        base_seed = st.number_input("Base Seed (0 = random)", min_value=0, max_value=999999, value=42, key="dbg_seed")
    with col_wx:
        dbg_weather = st.selectbox("Weather", list(WEATHER_CONDITIONS.keys()),
                                   format_func=lambda x: WEATHER_CONDITIONS[x]["label"], key="dbg_weather")

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
            engine = ViperballEngine(home_t, away_t, seed=s, style_overrides=style_overrides, weather=dbg_weather)
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

        home_safe = safe_filename(home_name)
        away_safe = safe_filename(away_name)
        batch_tag = f"batch_{home_safe}_vs_{away_safe}_{n}sims"

        bex1, bex2, bex3 = st.columns(3)
        with bex1:
            batch_csv = generate_batch_summary_csv(results)
            st.download_button(
                "Batch Summary (.csv)",
                data=batch_csv,
                file_name=f"{batch_tag}_summary.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with bex2:
            all_batch_json = json.dumps([{
                "game": i + 1,
                "final_score": r["final_score"],
                "stats": r["stats"],
                "drive_summary": r.get("drive_summary", []),
            } for i, r in enumerate(results)], indent=2, default=str)
            st.download_button(
                "All Games (.json)",
                data=all_batch_json,
                file_name=f"{batch_tag}_all.json",
                mime="application/json",
                use_container_width=True,
            )
        with bex3:
            full_batch_json = json.dumps(results, indent=2, default=str)
            st.download_button(
                "Full Data + Plays (.json)",
                data=full_batch_json,
                file_name=f"{batch_tag}_full.json",
                mime="application/json",
                use_container_width=True,
            )

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
        avg5.metric("Avg TDs/team", round((sum(home_tds) + sum(away_tds)) / (2 * n), 2))
        home_fumbles = [r["stats"]["home"]["fumbles_lost"] for r in results]
        away_fumbles = [r["stats"]["away"]["fumbles_lost"] for r in results]
        avg6.metric("Avg Fumbles/team", round((sum(home_fumbles) + sum(away_fumbles)) / (2 * n), 2))

        longest_plays = []
        for r in results:
            max_play = max((p["yards"] for p in r["play_by_play"] if p["play_type"] not in ["punt"]), default=0)
            longest_plays.append(max_play)
        avg7.metric("Avg Longest Play", round(sum(longest_plays) / n, 1))
        avg8.metric("Max Longest Play", max(longest_plays))

        k1, k2, k3, k4 = st.columns(4)
        home_kick_pct = [r["stats"]["home"].get("kick_percentage", 0) for r in results]
        away_kick_pct = [r["stats"]["away"].get("kick_percentage", 0) for r in results]
        avg_kick_pct = round((sum(home_kick_pct) + sum(away_kick_pct)) / (2 * n), 1)
        k1.metric("Avg Kick %", f"{avg_kick_pct}%")

        home_pindowns = [r["stats"]["home"].get("pindowns", 0) for r in results]
        away_pindowns = [r["stats"]["away"].get("pindowns", 0) for r in results]
        k2.metric("Avg Pindowns/game", round((sum(home_pindowns) + sum(away_pindowns)) / n, 2))

        home_lat_eff = [r["stats"]["home"].get("lateral_efficiency", 0) for r in results]
        away_lat_eff = [r["stats"]["away"].get("lateral_efficiency", 0) for r in results]
        avg_lat_eff = round((sum(home_lat_eff) + sum(away_lat_eff)) / (2 * n), 1)
        k3.metric("Avg Lateral Eff", f"{avg_lat_eff}%")

        home_dk = [r["stats"]["home"].get("drop_kicks_made", 0) for r in results]
        away_dk = [r["stats"]["away"].get("drop_kicks_made", 0) for r in results]
        k4.metric("Avg Snap Kicks/team", round((sum(home_dk) + sum(away_dk)) / (2 * n), 2))

        k5, k6, k7, k8 = st.columns(4)
        home_pk = [r["stats"]["home"].get("place_kicks_made", 0) for r in results]
        away_pk = [r["stats"]["away"].get("place_kicks_made", 0) for r in results]
        k5.metric("Avg FGs Made/team", round((sum(home_pk) + sum(away_pk)) / (2 * n), 2))

        home_bells = [r["stats"]["home"].get("bells", 0) for r in results]
        away_bells = [r["stats"]["away"].get("bells", 0) for r in results]
        k6.metric("Avg Bells/team", round((sum(home_bells) + sum(away_bells)) / (2 * n), 2))

        home_punts = [r["stats"]["home"].get("punts", 0) for r in results]
        away_punts = [r["stats"]["away"].get("punts", 0) for r in results]
        k7.metric("Avg Punts/team", round((sum(home_punts) + sum(away_punts)) / (2 * n), 2))

        home_saf = [r["stats"]["home"].get("safeties_conceded", 0) for r in results]
        away_saf = [r["stats"]["away"].get("safeties_conceded", 0) for r in results]
        k8.metric("Avg Safeties/team", round((sum(home_saf) + sum(away_saf)) / (2 * n), 2))

        st.markdown("**Avg Down Conversions**")
        dc_cols = st.columns(3)
        for idx, d in enumerate([4, 5, 6]):
            rates = []
            for r in results:
                for side in ["home", "away"]:
                    dc = r["stats"][side].get("down_conversions", {})
                    dd = dc.get(d, dc.get(str(d), {"rate": 0}))
                    rates.append(dd["rate"])
            avg_rate = round(sum(rates) / max(1, len(rates)), 1)
            label = f"{'4th' if d == 4 else '5th' if d == 5 else '6th'} Down Conv %"
            dc_cols[idx].metric(label, f"{avg_rate}%")

        st.markdown("**Avg VPA (Viperball Points Added)**")
        vpa_cols = st.columns(4)
        home_total_vpa = [r["stats"]["home"].get("epa", {}).get("total_vpa", r["stats"]["home"].get("epa", {}).get("total_epa", 0)) for r in results]
        away_total_vpa = [r["stats"]["away"].get("epa", {}).get("total_vpa", r["stats"]["away"].get("epa", {}).get("total_epa", 0)) for r in results]
        home_vpa_pp = [r["stats"]["home"].get("epa", {}).get("vpa_per_play", r["stats"]["home"].get("epa", {}).get("epa_per_play", 0)) for r in results]
        away_vpa_pp = [r["stats"]["away"].get("epa", {}).get("vpa_per_play", r["stats"]["away"].get("epa", {}).get("epa_per_play", 0)) for r in results]
        vpa_cols[0].metric(f"Avg {home_name} VPA", round(sum(home_total_vpa) / n, 2))
        vpa_cols[1].metric(f"Avg {away_name} VPA", round(sum(away_total_vpa) / n, 2))
        vpa_cols[2].metric(f"Avg {home_name} VPA/Play", round(sum(home_vpa_pp) / n, 3))
        vpa_cols[3].metric(f"Avg {away_name} VPA/Play", round(sum(away_vpa_pp) / n, 3))

        home_sr = [r["stats"]["home"].get("epa", {}).get("success_rate", 0) for r in results]
        away_sr = [r["stats"]["away"].get("epa", {}).get("success_rate", 0) for r in results]
        home_exp = [r["stats"]["home"].get("epa", {}).get("explosiveness", 0) for r in results]
        away_exp = [r["stats"]["away"].get("epa", {}).get("explosiveness", 0) for r in results]
        sr_cols = st.columns(4)
        sr_cols[0].metric(f"Avg {home_name} Success Rate", f"{round(sum(home_sr) / n, 1)}%")
        sr_cols[1].metric(f"Avg {away_name} Success Rate", f"{round(sum(away_sr) / n, 1)}%")
        sr_cols[2].metric(f"Avg {home_name} Explosiveness", round(sum(home_exp) / n, 3))
        sr_cols[3].metric(f"Avg {away_name} Explosiveness", round(sum(away_exp) / n, 3))

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
                    "END OF QUARTER": "#64748b", "PINDOWN": "#a855f7",
                    "PUNT RET TD": "#22c55e", "CHAOS REC": "#f97316",
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
