import os
import json

import streamlit as st
import pandas as pd

from engine.game_engine import POSITION_ARCHETYPES, get_archetype_info
from ui.helpers import load_team


def render_team_roster(shared):
    teams = shared["teams"]
    styles = shared["styles"]
    team_names = shared["team_names"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]
    OFFENSE_TOOLTIPS = shared["OFFENSE_TOOLTIPS"]
    DEFENSE_TOOLTIPS = shared["DEFENSE_TOOLTIPS"]

    st.title("Team Roster Viewer")

    roster_key = st.selectbox("Select Team", [t["key"] for t in teams],
                              format_func=lambda x: team_names[x], key="roster_team")

    team_data = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "teams", f"{roster_key}.json")))
    info = team_data["team_info"]
    roster = team_data["roster"]

    st.subheader(f"{info['school_name']} {info['mascot']}")
    info_cols = st.columns(4)
    with info_cols[0]:
        st.metric("Conference", info["conference"])
    with info_cols[1]:
        st.metric("Location", f"{info['city']}, {info['state']}")
    with info_cols[2]:
        st.metric("Colors", " / ".join(info.get("colors", [])))
    with info_cols[3]:
        st.metric("Roster Size", roster["size"])

    st.divider()

    players = roster["players"]
    all_positions = sorted(set(p["position"] for p in players))
    selected_positions = st.multiselect("Filter by Position", all_positions, default=all_positions)

    view_mode = st.radio("View", ["Full Roster", "Depth Chart"], horizontal=True, key="static_roster_view")

    pos_groups = {}
    for p in players:
        pos_groups.setdefault(p["position"], []).append(p)
    depth_rank_map = {}
    for pos, group in pos_groups.items():
        sorted_group = sorted(group, key=lambda x: x["stats"].get("speed", 0) + x["stats"].get("agility", 0) + x["stats"].get("awareness", 0), reverse=True)
        for i, pl in enumerate(sorted_group, 1):
            depth_rank_map[pl["name"]] = i

    rows = []
    for p in players:
        if p["position"] not in selected_positions:
            continue
        s = p["stats"]
        depth = depth_rank_map.get(p["name"], 99)
        role = "Starter" if depth == 1 else f"Backup #{depth}" if depth <= 3 else "Reserve"
        rows.append({
            "#": p["number"],
            "Name": p["name"],
            "Position": p["position"],
            "Role": role,
            "Archetype": p.get("archetype", ""),
            "Year": p["year"],
            "Height": p["height"],
            "Weight": p["weight"],
            "Hometown": f"{p['hometown']['city']}, {p['hometown']['state']}",
            "Speed": s["speed"],
            "Stamina": s["stamina"],
            "Kicking": s["kicking"],
            "Lateral Skill": s["lateral_skill"],
            "Tackling": s["tackling"],
            "Agility": s["agility"],
            "Power": s["power"],
            "Awareness": s["awareness"],
            "Hands": s["hands"],
        })

    if view_mode == "Depth Chart" and rows:
        dc_positions = sorted(set(r["Position"] for r in rows))
        for pos in dc_positions:
            group = sorted([r for r in rows if r["Position"] == pos], key=lambda x: -(x["Speed"] + x["Agility"] + x["Awareness"]))
            st.markdown(f"**{pos}**")
            dc_df = pd.DataFrame(group)[["#", "Name", "Role", "Year", "Archetype", "Speed", "Agility", "Power", "Awareness"]]
            st.dataframe(dc_df, hide_index=True, use_container_width=True)
    else:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

    st.divider()
    st.subheader("Team Summary Stats")

    if rows:
        stat_cols = st.columns(5)
        avg_speed = sum(r["Speed"] for r in rows) / len(rows)
        avg_stamina = sum(r["Stamina"] for r in rows) / len(rows)
        avg_agility = sum(r["Agility"] for r in rows) / len(rows)
        avg_power = sum(r["Power"] for r in rows) / len(rows)
        avg_awareness = sum(r["Awareness"] for r in rows) / len(rows)
        with stat_cols[0]:
            st.metric("Avg Speed", f"{avg_speed:.1f}")
        with stat_cols[1]:
            st.metric("Avg Stamina", f"{avg_stamina:.1f}")
        with stat_cols[2]:
            st.metric("Avg Agility", f"{avg_agility:.1f}")
        with stat_cols[3]:
            st.metric("Avg Power", f"{avg_power:.1f}")
        with stat_cols[4]:
            st.metric("Avg Awareness", f"{avg_awareness:.1f}")

        stat_cols2 = st.columns(5)
        avg_kicking = sum(r["Kicking"] for r in rows) / len(rows)
        avg_lateral = sum(r["Lateral Skill"] for r in rows) / len(rows)
        avg_tackling = sum(r["Tackling"] for r in rows) / len(rows)
        avg_hands = sum(r["Hands"] for r in rows) / len(rows)
        with stat_cols2[0]:
            st.metric("Avg Kicking", f"{avg_kicking:.1f}")
        with stat_cols2[1]:
            st.metric("Avg Lateral Skill", f"{avg_lateral:.1f}")
        with stat_cols2[2]:
            st.metric("Avg Tackling", f"{avg_tackling:.1f}")
        with stat_cols2[3]:
            st.metric("Avg Hands", f"{avg_hands:.1f}")
        with stat_cols2[4]:
            st.metric("Players Shown", len(rows))
