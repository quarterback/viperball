import os
import io
import csv

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from engine.season import BOWL_TIERS
from ui import api_client
from ui.helpers import (
    fmt_vb_score, render_game_detail, generate_box_score_markdown,
    generate_play_log_csv, generate_drives_csv, safe_filename,
)


def _get_session_id():
    return st.session_state.get("api_session_id")


def _get_mode():
    return st.session_state.get("api_mode")


def render_my_team_section(shared):
    session_id = _get_session_id()
    mode = _get_mode()

    if not session_id or not mode:
        st.title("My Team")
        st.info("No active session found. Go to **Play** to start a new season or dynasty.")
        return

    if mode == "dynasty":
        try:
            dyn_status = api_client.get_dynasty_status(session_id)
            human_teams = [dyn_status.get("coach", {}).get("team", "")]
        except api_client.APIError:
            st.title("My Team")
            st.error("Could not load dynasty data.")
            return
    else:
        human_teams = st.session_state.get("season_human_teams_list", [])

    if not human_teams or not any(human_teams):
        st.title("My Team")
        st.info("No human-coached teams in this session. Go to **Play** to start a new one with your team selected.")
        return

    try:
        standings_resp = api_client.get_standings(session_id)
        standings = standings_resp.get("standings", [])
    except api_client.APIError:
        st.title("My Team")
        st.info("No season data available yet. Simulate a season from **Play** to see your team's data.")
        return

    if not standings:
        st.title("My Team")
        st.info("No season data available yet. Simulate a season from **Play** to see your team's data.")
        return

    if len(human_teams) > 1:
        selected_team = st.selectbox("Select Team", human_teams, key="myteam_team_selector")
    else:
        selected_team = human_teams[0]

    tab_names = ["Dashboard", "Roster", "Schedule"]
    if mode == "dynasty":
        tab_names.append("History")

    tabs = st.tabs(tab_names)

    with tabs[0]:
        _render_dashboard(session_id, mode, selected_team, standings)

    with tabs[1]:
        _render_roster(session_id, selected_team)

    with tabs[2]:
        _render_schedule(session_id, mode, selected_team)

    if mode == "dynasty" and len(tabs) > 3:
        with tabs[3]:
            _render_history(session_id)


def _build_dashboard_text(team_name, record, rank, mode):
    lines = [f"{team_name} Team Summary", "=" * 40, ""]
    lines.append(f"Record: {record['wins']}-{record['losses']}")
    lines.append(f"Power Ranking: #{rank}" if rank else "Power Ranking: N/A")
    if record.get("conference"):
        lines.append(f"Conference: {record.get('conference', '')}")
        lines.append(f"Conference Record: {record.get('conf_wins', 0)}-{record.get('conf_losses', 0)}")
    lines.append(f"Points For: {fmt_vb_score(record['points_for'])}")
    lines.append(f"Points Against: {fmt_vb_score(record['points_against'])}")
    lines.append(f"Point Differential: {fmt_vb_score(record.get('point_differential', 0))}")
    lines.append("")
    lines.append("Viperball Metrics:")
    lines.append(f"  OPI: {record.get('avg_opi', 0):.1f}")
    lines.append(f"  Territory: {record.get('avg_territory', 0):.1f}")
    lines.append(f"  Pressure: {record.get('avg_pressure', 0):.1f}")
    lines.append(f"  Chaos: {record.get('avg_chaos', 0):.1f}")
    lines.append(f"  Kicking: {record.get('avg_kicking', 0):.1f}")
    if record.get("offense_style"):
        lines.append(f"\nOffense: {record.get('offense_style', '')}")
    if record.get("defense_style"):
        lines.append(f"Defense: {record.get('defense_style', '')}")
    return "\n".join(lines)


def _render_dashboard(session_id, mode, team_name, standings):
    record = next((r for r in standings if r["team_name"] == team_name), None)
    if not record:
        st.warning(f"No standings data found for {team_name}.")
        return

    rank = next((i for i, r in enumerate(standings, 1) if r["team_name"] == team_name), None)

    st.subheader(f"{team_name}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Record", f"{record['wins']}-{record['losses']}")
    m2.metric("Power Index", f"—", f"Rank #{rank}" if rank else None)
    if record.get("conference"):
        m3.metric("Conference", f"{record.get('conf_wins', 0)}-{record.get('conf_losses', 0)}")
        try:
            conf_resp = api_client.get_conference_standings(session_id)
            conf_standings_data = conf_resp.get("conference_standings", {})
            team_conf = record.get("conference", "")
            conf_teams = conf_standings_data.get(team_conf, [])
            conf_standing = next((i for i, r in enumerate(conf_teams, 1) if r["team_name"] == team_name), None)
            m4.metric("Conf Standing", f"#{conf_standing}" if conf_standing else "—")
        except api_client.APIError:
            m4.metric("Conf Standing", "—")
    else:
        m3.metric("Win %", f"{record.get('win_percentage', 0):.3f}")
        m4.metric("Games", str(record.get("games_played", 0)))

    p1, p2 = st.columns(2)
    p1.metric("Points For", fmt_vb_score(record["points_for"]))
    p2.metric("Points Against", fmt_vb_score(record["points_against"]))

    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    mc1.metric("OPI", f"{record.get('avg_opi', 0):.1f}")
    mc2.metric("Territory", f"{record.get('avg_territory', 0):.1f}")
    mc3.metric("Pressure", f"{record.get('avg_pressure', 0):.1f}")
    mc4.metric("Chaos", f"{record.get('avg_chaos', 0):.1f}")
    mc5.metric("Kicking", f"{record.get('avg_kicking', 0):.1f}")

    if standings:
        n = len(standings)
        avgs = {
            "OPI": sum(r.get("avg_opi", 0) for r in standings) / n,
            "Territory": sum(r.get("avg_territory", 0) for r in standings) / n,
            "Pressure": sum(r.get("avg_pressure", 0) for r in standings) / n,
            "Chaos": sum(r.get("avg_chaos", 0) for r in standings) / n,
            "Kicking": sum(r.get("avg_kicking", 0) for r in standings) / n,
        }
        categories = list(avgs.keys())
        team_values = [record.get("avg_opi", 0), record.get("avg_territory", 0), record.get("avg_pressure", 0),
                        record.get("avg_chaos", 0), record.get("avg_kicking", 0)]
        avg_values = [avgs[c] for c in categories]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=team_values + [team_values[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name=team_name,
        ))
        fig.add_trace(go.Scatterpolar(
            r=avg_values + [avg_values[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name="League Average",
            opacity=0.4,
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title="Team Metrics vs League Average",
            height=420,
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True, key="myteam_radar")

    if mode == "dynasty":
        st.divider()
        st.subheader("Coach Profile")
        try:
            dyn_status = api_client.get_dynasty_status(session_id)
            coach = dyn_status.get("coach", {})
            cc1, cc2, cc3, cc4 = st.columns(4)
            cc1.metric("Career Record", f"{coach.get('career_wins', 0)}-{coach.get('career_losses', 0)}")
            cc2.metric("Win %", f"{coach.get('win_percentage', 0):.3f}")
            cc3.metric("Championships", str(coach.get("championships", 0)))
            cc4.metric("Years Experience", str(coach.get("years_experience", 0)))
        except api_client.APIError:
            pass

    st.divider()
    st.subheader("Injury Report")
    try:
        inj_resp = api_client.get_injuries(session_id, team=team_name)
        active_inj = inj_resp.get("active", [])
        team_log = inj_resp.get("season_log", [])
        penalties = inj_resp.get("penalties", {})

        q_count = sum(1 for i in active_inj if i.get("tier") == "day_to_day")
        out_count = sum(1 for i in active_inj if i.get("tier") not in ("day_to_day", "severe") and not i.get("is_season_ending"))
        se_count = sum(1 for i in active_inj if i.get("is_season_ending") or i.get("tier") == "severe")

        ic1, ic2, ic3, ic4, ic5 = st.columns(5)
        ic1.metric("Active Injuries", len(active_inj))
        ic2.metric("Questionable", q_count)
        ic3.metric("Out", out_count)
        ic4.metric("Season-Ending", se_count)
        ic5.metric("Season Total", len(team_log))

        if active_inj:
            inj_rows = []
            for inj in active_inj:
                status = "OUT FOR SEASON" if inj.get("is_season_ending") or inj.get("tier") == "severe" else (inj.get("game_status") or "OUT").upper()
                inj_rows.append({
                    "Player": inj.get("player_name", ""),
                    "Position": inj.get("position", ""),
                    "Injury": inj.get("description", ""),
                    "Body Part": (inj.get("body_part") or "").title(),
                    "Category": {"on_field_contact": "Contact", "on_field_noncontact": "Non-Contact", "practice": "Practice", "off_field": "Off-Field"}.get(inj.get("category", ""), inj.get("category", "")),
                    "Status": status,
                    "Week Out": inj.get("week_injured", ""),
                    "Return": "Season-ending" if status == "OUT FOR SEASON" else f"Wk {inj.get('week_return', '?')}",
                })
            st.dataframe(pd.DataFrame(inj_rows), hide_index=True, use_container_width=True)
        else:
            st.caption("No active injuries — full health!")

        if penalties and any(v != 1.0 for v in penalties.values()):
            st.markdown("**Injury Impact on Performance**")
            p1, p2, p3 = st.columns(3)
            yards_delta = round((penalties.get("yards_penalty", 1.0) - 1.0) * 100, 1)
            kick_delta = round((penalties.get("kick_penalty", 1.0) - 1.0) * 100, 1)
            lat_delta = round((penalties.get("lateral_penalty", 1.0) - 1.0) * 100, 1)
            p1.metric("Yards Impact", f"{yards_delta:+.1f}%", delta=f"{yards_delta:.1f}%", delta_color="inverse")
            p2.metric("Kicking Impact", f"{kick_delta:+.1f}%", delta=f"{kick_delta:.1f}%", delta_color="inverse")
            p3.metric("Lateral Impact", f"{lat_delta:+.1f}%", delta=f"{lat_delta:.1f}%", delta_color="inverse")

        if team_log:
            with st.expander("Season Injury History"):
                log_rows = []
                for inj in team_log:
                    log_rows.append({
                        "Week": inj.get("week_injured", ""),
                        "Player": inj.get("player_name", ""),
                        "Injury": inj.get("description", ""),
                        "Body Part": (inj.get("body_part") or "").title(),
                        "Severity": (inj.get("tier") or "").replace("_", "-").title(),
                        "In-Game": "Yes" if inj.get("in_game") else "No",
                        "Weeks Out": inj.get("weeks_out", ""),
                    })
                st.dataframe(pd.DataFrame(log_rows), hide_index=True, use_container_width=True)
    except api_client.APIError:
        st.caption("Injury data not available.")

    st.divider()
    summary = _build_dashboard_text(team_name, record, rank, mode)
    ex1, ex2 = st.columns(2)
    with ex1:
        st.download_button(
            "Download Team Summary (Text)",
            summary,
            file_name=f"{safe_filename(team_name)}_summary.txt",
            mime="text/plain",
            key="myteam_dash_txt",
        )
    with ex2:
        if st.button("Copy Team Summary", key="myteam_dash_copy"):
            st.code(summary, language=None)
            st.caption("Select all and copy the text above.")


def _build_roster_csv(team_name, players):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["#", "Name", "Position", "Archetype", "Year", "OVR",
                     "Speed", "Power", "Agility", "Hands", "Awareness", "Kicking", "Stamina"])
    for p in players:
        ovr = int(round((p.get("speed", 0) + p.get("stamina", 0) + p.get("agility", 0) +
                          p.get("power", 0) + p.get("awareness", 0) + p.get("hands", 0)) / 6))
        writer.writerow([
            p.get("number", ""),
            p.get("name", ""),
            p.get("position", ""),
            p.get("archetype", ""),
            p.get("year_abbrev", p.get("year", "")),
            ovr,
            p.get("speed", 0),
            p.get("power", 0),
            p.get("agility", 0),
            p.get("hands", 0),
            p.get("awareness", 0),
            p.get("kicking", 0),
            p.get("stamina", 0),
        ])
    return buf.getvalue()


def _build_roster_text(team_name, players):
    lines = [f"{team_name} Roster", "=" * len(f"{team_name} Roster"), ""]
    lines.append(f"{'#':>3} {'Name':<24} {'Pos':<6} {'Archetype':<18} {'Yr':<6} {'OVR':>3} {'SPD':>3} {'PWR':>3} {'AGI':>3} {'HND':>3} {'AWR':>3} {'KCK':>3} {'STM':>3}")
    lines.append("-" * 100)
    for p in players:
        ovr = int(round((p.get("speed", 0) + p.get("stamina", 0) + p.get("agility", 0) +
                          p.get("power", 0) + p.get("awareness", 0) + p.get("hands", 0)) / 6))
        lines.append(
            f"{p.get('number', ''):>3} {p.get('name', ''):<24} {p.get('position', ''):<6} "
            f"{p.get('archetype', ''):<18} {p.get('year_abbrev', p.get('year', '')):<6} "
            f"{ovr:>3} {p.get('speed', 0):>3} {p.get('power', 0):>3} "
            f"{p.get('agility', 0):>3} {p.get('hands', 0):>3} "
            f"{p.get('awareness', 0):>3} {p.get('kicking', 0):>3} {p.get('stamina', 0):>3}"
        )
    return "\n".join(lines)


def _render_roster(session_id, team_name):
    try:
        roster_resp = api_client.get_team_roster(session_id, team_name)
        players = roster_resp.get("players", [])
    except api_client.APIError:
        st.warning(f"Could not load roster for {team_name}.")
        return

    inj_map = {}
    try:
        inj_resp = api_client.get_injuries(session_id, team=team_name)
        for inj in inj_resp.get("active", []):
            pname = inj.get("player_name", "")
            if inj.get("is_season_ending") or inj.get("tier") == "severe":
                inj_map[pname] = f"OUT FOR SEASON ({inj.get('description', '')})"
            elif inj.get("tier") in ("moderate", "major"):
                inj_map[pname] = f"OUT ({inj.get('description', '')}, Wk {inj.get('week_return', '?')})"
            elif inj.get("tier") == "minor":
                inj_map[pname] = f"DOUBTFUL ({inj.get('description', '')})"
            elif inj.get("tier") == "day_to_day":
                inj_map[pname] = f"QUESTIONABLE ({inj.get('description', '')})"
            else:
                inj_map[pname] = f"OUT ({inj.get('description', '')})"
    except api_client.APIError:
        pass

    view_mode = st.radio("View", ["Full Roster", "Depth Chart"], horizontal=True, key="myteam_roster_view")

    roster_data = []
    for p in players:
        ovr = p.get("overall", int(round((p.get("speed", 0) + p.get("stamina", 0) + p.get("agility", 0) +
                          p.get("power", 0) + p.get("awareness", 0) + p.get("hands", 0)) / 6)))
        depth = p.get("depth_rank", 0)
        role = "Starter" if depth == 1 else f"Backup #{depth}" if depth <= 3 else "Reserve"
        rs_status = ""
        if p.get("redshirt", False):
            rs_status = "RS"
        elif p.get("redshirt_used", False):
            rs_status = "Used"
        elif p.get("redshirt_eligible", False):
            rs_status = "Eligible"
        player_name = p.get("name", "")
        health_status = inj_map.get(player_name, "HEALTHY")
        roster_data.append({
            "Name": f"{player_name} ({p.get('position', '')} #{p.get('number', '')})",
            "Year": p.get("year_abbr", p.get("year_abbrev", p.get("year", ""))),
            "Status": health_status,
            "Role": role,
            "RS": rs_status,
            "Archetype": p.get("archetype", ""),
            "Position": p.get("position", ""),
            "OVR": ovr,
            "GP": p.get("season_games_played", 0),
            "Speed": p.get("speed", 0),
            "Power": p.get("power", 0),
            "Agility": p.get("agility", 0),
            "Hands": p.get("hands", 0),
            "Awareness": p.get("awareness", 0),
            "Kicking": p.get("kicking", 0),
            "Stamina": p.get("stamina", 0),
        })

    if roster_data:
        if view_mode == "Depth Chart":
            positions_order = ["Viper", "VP", "Zeroback", "ZB", "Halfback", "HB",
                               "Wingback", "WB", "Slotback", "SB", "Keeper", "KP",
                               "Offensive Line", "OL", "Defensive Line", "DL"]
            pos_groups = {}
            for r in roster_data:
                pos = r["Position"]
                pos_groups.setdefault(pos, []).append(r)
            for pos in sorted(pos_groups.keys(), key=lambda x: positions_order.index(x) if x in positions_order else 99):
                group = sorted(pos_groups[pos], key=lambda x: -x["OVR"])
                st.markdown(f"**{pos}**")
                dc_df = pd.DataFrame(group)[["Name", "Status", "Role", "Year", "RS", "OVR", "GP", "Archetype", "Speed", "Power", "Awareness"]]
                st.dataframe(dc_df, hide_index=True, use_container_width=True)
        else:
            st.dataframe(pd.DataFrame(roster_data), hide_index=True, use_container_width=True, height=600)

        st.divider()
        ex1, ex2, ex3 = st.columns(3)
        with ex1:
            st.download_button(
                "Download Roster CSV",
                _build_roster_csv(team_name, players),
                file_name=f"{safe_filename(team_name)}_roster.csv",
                mime="text/csv",
                key="myteam_roster_csv",
            )
        with ex2:
            roster_text = _build_roster_text(team_name, players)
            st.download_button(
                "Download Roster (Text)",
                roster_text,
                file_name=f"{safe_filename(team_name)}_roster.txt",
                mime="text/plain",
                key="myteam_roster_txt",
            )
        with ex3:
            if st.button("Copy Roster to Clipboard", key="myteam_roster_copy"):
                roster_text = _build_roster_text(team_name, players)
                st.code(roster_text, language=None)
                st.caption("Select all and copy the text above.")
    else:
        st.info("No players found on this roster.")


def _build_team_schedule_csv(team_name, entries):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Week", "Opponent", "Result", "Score", "Location", "Phase"])
    for e in entries:
        writer.writerow([e["label"], e["opponent"], e["result"], e["score"], e["location"], e["phase"]])
    return buf.getvalue()


def _build_team_schedule_text(team_name, entries, wins, losses):
    lines = [f"{team_name} Schedule ({wins}-{losses})", "=" * 50, ""]
    lines.append(f"{'Week':<20} {'Opponent':<28} {'Result':<4} {'Score':<14} {'Loc':<6} {'Phase'}")
    lines.append("-" * 85)
    for e in entries:
        lines.append(
            f"{e['label']:<20} {e['opponent']:<28} {e['result']:<4} {e['score']:<14} {e['location']:<6} {e['phase']}"
        )
    lines.append("")
    lines.append(f"Season Record: {wins}-{losses}")
    return "\n".join(lines)


def _render_schedule(session_id, mode, team_name):
    try:
        sched_resp = api_client.get_schedule(session_id, team=team_name, completed_only=True, include_full_result=True)
        team_games = sched_resp.get("games", [])
    except api_client.APIError:
        team_games = []

    try:
        bracket_resp = api_client.get_playoff_bracket(session_id)
        bracket = bracket_resp.get("bracket", [])
    except api_client.APIError:
        bracket = []

    try:
        bowls_resp = api_client.get_bowl_results(session_id)
        bowl_results = bowls_resp.get("bowl_results", [])
    except api_client.APIError:
        bowl_results = []

    entries = []

    for g in team_games:
        if g.get("completed") and (g.get("home_team") == team_name or g.get("away_team") == team_name):
            is_home = g.get("home_team") == team_name
            opponent = g.get("away_team") if is_home else g.get("home_team")
            team_score = g.get("home_score") if is_home else g.get("away_score")
            opp_score = g.get("away_score") if is_home else g.get("home_score")
            won = (team_score or 0) > (opp_score or 0)
            entries.append({
                "game": g,
                "week": g.get("week", 0),
                "opponent": opponent,
                "result": "W" if won else "L",
                "score": f"{fmt_vb_score(team_score or 0)} - {fmt_vb_score(opp_score or 0)}",
                "location": "Home" if is_home else "Away",
                "phase": "Regular Season",
                "sort_key": g.get("week", 0),
                "label": f"Wk {g.get('week', 0)}",
            })

    if bracket:
        playoff_round_names = {996: "Opening Round", 997: "First Round", 998: "Quarterfinals", 999: "Semi-Finals", 1000: "Championship"}
        for g in bracket:
            if g.get("completed") and (g.get("home_team") == team_name or g.get("away_team") == team_name):
                is_home = g.get("home_team") == team_name
                opponent = g.get("away_team") if is_home else g.get("home_team")
                team_score = g.get("home_score") if is_home else g.get("away_score")
                opp_score = g.get("away_score") if is_home else g.get("home_score")
                won = (team_score or 0) > (opp_score or 0)
                round_label = playoff_round_names.get(g.get("week", 0), f"Playoff R{g.get('week', 0)}")
                entries.append({
                    "game": g,
                    "week": 900 + g.get("week", 0),
                    "opponent": opponent,
                    "result": "W" if won else "L",
                    "score": f"{fmt_vb_score(team_score or 0)} - {fmt_vb_score(opp_score or 0)}",
                    "location": "Home" if is_home else "Away",
                    "phase": "Playoff",
                    "sort_key": 900 + g.get("week", 0),
                    "label": round_label,
                })

    if bowl_results:
        for i, bowl in enumerate(bowl_results):
            bg = bowl.get("game", {})
            if bg.get("completed") and (bg.get("home_team") == team_name or bg.get("away_team") == team_name):
                is_home = bg.get("home_team") == team_name
                opponent = bg.get("away_team") if is_home else bg.get("home_team")
                team_score = bg.get("home_score") if is_home else bg.get("away_score")
                opp_score = bg.get("away_score") if is_home else bg.get("home_score")
                won = (team_score or 0) > (opp_score or 0)
                entries.append({
                    "game": bg,
                    "week": 800 + i,
                    "opponent": opponent,
                    "result": "W" if won else "L",
                    "score": f"{fmt_vb_score(team_score or 0)} - {fmt_vb_score(opp_score or 0)}",
                    "location": "Home" if is_home else "Away",
                    "phase": "Bowl",
                    "sort_key": 800 + i,
                    "label": bowl.get("name", f"Bowl {i+1}"),
                })

    entries.sort(key=lambda e: e["sort_key"])

    if not entries:
        st.info("No games found for this team in the current season.")
        return

    wins = sum(1 for e in entries if e["result"] == "W")
    losses = len(entries) - wins

    sched_data = []
    for e in entries:
        sched_data.append({
            "Week": e["label"],
            "Opponent": e["opponent"],
            "Result": e["result"],
            "Score": e["score"],
            "Location": e["location"],
            "Phase": e["phase"],
        })
    st.dataframe(pd.DataFrame(sched_data), hide_index=True, use_container_width=True)

    st.divider()
    sched_csv = _build_team_schedule_csv(team_name, entries)
    sched_text = _build_team_schedule_text(team_name, entries, wins, losses)
    ex1, ex2, ex3 = st.columns(3)
    with ex1:
        st.download_button(
            "Download Schedule CSV",
            sched_csv,
            file_name=f"{safe_filename(team_name)}_schedule.csv",
            mime="text/csv",
            key="myteam_sched_csv",
        )
    with ex2:
        st.download_button(
            "Download Schedule (Text)",
            sched_text,
            file_name=f"{safe_filename(team_name)}_schedule.txt",
            mime="text/plain",
            key="myteam_sched_txt",
        )
    with ex3:
        if st.button("Copy Schedule to Clipboard", key="myteam_sched_copy"):
            st.code(sched_text, language=None)
            st.caption("Select all and copy the text above.")

    st.divider()
    game_labels = [f"{e['label']}: vs {e['opponent']} ({e['result']}) {e['score']}" for e in entries]
    selected = st.selectbox("Select a game to view details", game_labels, key="myteam_game_select")
    if selected:
        idx = game_labels.index(selected)
        g = entries[idx]["game"]
        full_result = g.get("full_result")
        if full_result:
            with st.expander("Game Details", expanded=True):
                render_game_detail(full_result, key_prefix=f"myteam_gd_{idx}")

            box_md = generate_box_score_markdown(full_result)
            with st.expander("Share This Game", expanded=False):
                st.caption("Copy the box score below to share on forums or elsewhere.")
                dl1, dl2, dl3 = st.columns(3)
                with dl1:
                    st.download_button(
                        "Download Box Score (Markdown)",
                        box_md,
                        file_name=f"{safe_filename(team_name)}_wk{entries[idx]['week']}_boxscore.md",
                        mime="text/markdown",
                        key=f"myteam_box_md_{idx}",
                    )
                with dl2:
                    st.download_button(
                        "Download Play Log (CSV)",
                        generate_play_log_csv(full_result),
                        file_name=f"{safe_filename(team_name)}_wk{entries[idx]['week']}_plays.csv",
                        mime="text/csv",
                        key=f"myteam_box_plays_{idx}",
                    )
                with dl3:
                    st.download_button(
                        "Download Drives (CSV)",
                        generate_drives_csv(full_result),
                        file_name=f"{safe_filename(team_name)}_wk{entries[idx]['week']}_drives.csv",
                        mime="text/csv",
                        key=f"myteam_box_drives_{idx}",
                    )
                if st.button("Show Box Score for Copying", key=f"myteam_box_copy_{idx}"):
                    st.code(box_md, language="markdown")
                    st.caption("Select all and copy the text above.")


def _render_history(session_id):
    try:
        dyn_status = api_client.get_dynasty_status(session_id)
        coach = dyn_status.get("coach", {})
    except api_client.APIError:
        st.error("Could not load dynasty data.")
        return

    team_name = coach.get("team", "")

    st.subheader("Coach Career")
    hc1, hc2, hc3, hc4 = st.columns(4)
    hc1.metric("Career Record", f"{coach.get('career_wins', 0)}-{coach.get('career_losses', 0)}")
    hc2.metric("Win %", f"{coach.get('win_percentage', 0):.3f}")
    hc3.metric("Championships", str(coach.get("championships", 0)))
    hc4.metric("Seasons", str(coach.get("years_experience", 0)))

    season_records = coach.get("season_records", {})
    if season_records:
        season_rows = []
        for year in sorted(season_records.keys(), key=lambda y: int(y)):
            sr = season_records[year]
            season_rows.append({
                "Year": year,
                "W-L": f"{sr.get('wins', 0)}-{sr.get('losses', 0)}",
                "PF": fmt_vb_score(sr.get("points_for", 0)),
                "PA": fmt_vb_score(sr.get("points_against", 0)),
                "Playoff": "Y" if sr.get("playoff") else "N",
                "Champion": "Y" if sr.get("champion") else "N",
            })
        st.dataframe(pd.DataFrame(season_rows), hide_index=True, use_container_width=True)

        wins_data = [{"Year": str(y), "Wins": season_records[y].get("wins", 0)} for y in sorted(season_records.keys(), key=lambda y: int(y))]
        if wins_data:
            import plotly.express as px
            fig = px.bar(pd.DataFrame(wins_data), x="Year", y="Wins", title="Wins Per Season")
            fig.update_layout(height=350, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True, key="myteam_wins_chart")

    st.divider()
    st.subheader("Coaching History")
    try:
        ch_resp = api_client.get_dynasty_coaching_history(session_id)
        coaching_hist = ch_resp.get("coaching_history", {})
        current_staffs = ch_resp.get("current_staffs", {})
    except api_client.APIError:
        coaching_hist = {}
        current_staffs = {}

    my_staff = current_staffs.get(team_name, {})
    if my_staff:
        cs1, cs2, cs3 = st.columns(3)
        cs1.metric("Head Coach", my_staff.get("hc_name", "Unknown"))
        cs2.metric("Classification", my_staff.get("hc_classification", "unclassified").replace("_", " ").title())
        cs3.metric("HC Record", my_staff.get("hc_record", "0-0"))

    if coaching_hist:
        with st.expander("Coaching Changes by Year"):
            def _safe_year_sort(y):
                try:
                    return int(y)
                except (ValueError, TypeError):
                    return 0
            for year in sorted(coaching_hist.keys(), key=_safe_year_sort):
                yr_data = coaching_hist[year]
                n_changes = yr_data.get("teams_with_changes", 0)
                if n_changes > 0:
                    changes = yr_data.get("changes", {})
                    my_changes = changes.get(team_name, {})
                    if my_changes:
                        st.markdown(f"**Year {year}** — Your team had coaching changes:")
                        for role, info in my_changes.items():
                            if isinstance(info, dict):
                                st.caption(f"  {role}: {info.get('new', 'N/A')} (replaced {info.get('old', 'N/A')})")
                            else:
                                st.caption(f"  {role}: {info}")
                    else:
                        st.caption(f"Year {year}: {n_changes} team(s) had coaching changes (none on your team)")

    st.divider()
    st.subheader("Team History")
    try:
        histories_resp = api_client.get_dynasty_team_histories(session_id)
        team_hist = histories_resp.get("team_histories", {}).get(team_name, {})
    except api_client.APIError:
        team_hist = {}

    if team_hist:
        th1, th2, th3, th4 = st.columns(4)
        th1.metric("All-Time Record", f"{team_hist.get('total_wins', 0)}-{team_hist.get('total_losses', 0)}")
        th2.metric("Win %", f"{team_hist.get('win_percentage', 0):.3f}")
        th3.metric("Championships", str(team_hist.get("total_championships", 0)))
        th4.metric("Playoff Appearances", str(team_hist.get("total_playoff_appearances", 0)))

        champ_years = team_hist.get("championship_years", [])
        if champ_years:
            st.caption(f"Championship Years: {', '.join(str(y) for y in sorted(champ_years))}")

    st.divider()
    st.subheader("Record Book")
    try:
        rb = api_client.get_dynasty_record_book(session_id)
    except api_client.APIError:
        rb = {}

    st.markdown("**Single-Season Records**")
    ss_records = []
    most_wins = rb.get("most_wins_season", {})
    if most_wins.get("team"):
        ss_records.append({"Record": "Most Wins", "Team": most_wins["team"], "Value": str(most_wins.get("wins", 0)), "Year": str(most_wins.get("year", ""))})
    most_points = rb.get("most_points_season", {})
    if most_points.get("team"):
        ss_records.append({"Record": "Most Points", "Team": most_points["team"], "Value": fmt_vb_score(most_points.get("points", 0)), "Year": str(most_points.get("year", ""))})
    best_def = rb.get("best_defense_season", {})
    if best_def.get("team"):
        ss_records.append({"Record": "Best Defense (PPG)", "Team": best_def["team"], "Value": f"{best_def.get('ppg_allowed', 0):.1f}", "Year": str(best_def.get("year", ""))})
    highest_opi = rb.get("highest_opi_season", {})
    if highest_opi.get("team"):
        ss_records.append({"Record": "Highest OPI", "Team": highest_opi["team"], "Value": f"{highest_opi.get('opi', 0):.1f}", "Year": str(highest_opi.get("year", ""))})
    most_chaos = rb.get("most_chaos_season", {})
    if most_chaos.get("team"):
        ss_records.append({"Record": "Most Chaos", "Team": most_chaos["team"], "Value": f"{most_chaos.get('chaos', 0):.1f}", "Year": str(most_chaos.get("year", ""))})

    if ss_records:
        st.dataframe(pd.DataFrame(ss_records), hide_index=True, use_container_width=True)

    st.markdown("**All-Time Records**")
    at_records = []
    most_champs = rb.get("most_championships", {})
    if most_champs.get("team"):
        at_records.append({"Record": "Most Championships", "Team/Coach": most_champs["team"], "Value": str(most_champs.get("championships", 0))})
    highest_win = rb.get("highest_win_percentage", {})
    if highest_win.get("team"):
        at_records.append({"Record": "Highest Win %", "Team/Coach": highest_win["team"], "Value": f"{highest_win.get('win_pct', 0):.3f}"})
    most_coaching = rb.get("most_coaching_wins", {})
    if most_coaching.get("coach"):
        at_records.append({"Record": "Most Coaching Wins", "Team/Coach": most_coaching["coach"], "Value": str(most_coaching.get("wins", 0))})
    most_coach_champs = rb.get("most_coaching_championships", {})
    if most_coach_champs.get("coach"):
        at_records.append({"Record": "Most Coaching Championships", "Team/Coach": most_coach_champs["coach"], "Value": str(most_coach_champs.get("championships", 0))})

    if at_records:
        st.dataframe(pd.DataFrame(at_records), hide_index=True, use_container_width=True)
