import os

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from engine.season import load_teams_from_directory, BOWL_TIERS
from ui.helpers import fmt_vb_score, render_game_detail


def _get_season_and_dynasty():
    dynasty = st.session_state.get("dynasty", None)
    if dynasty and "last_dynasty_season" in st.session_state:
        return st.session_state["last_dynasty_season"], dynasty
    if "active_season" in st.session_state:
        return st.session_state["active_season"], None
    return None, None


def _get_human_teams(dynasty):
    if dynasty:
        return [dynasty.coach.team_name]
    return st.session_state.get("season_human_teams_list", [])


def _get_team_rank(season, team_name):
    standings = season.get_standings_sorted()
    for i, r in enumerate(standings, 1):
        if r.team_name == team_name:
            return i
    return None


def _get_conference_standing(season, team_name):
    record = season.standings.get(team_name)
    if not record or not record.conference:
        return None
    conf_standings = season.get_conference_standings(record.conference)
    for i, r in enumerate(conf_standings, 1):
        if r.team_name == team_name:
            return i
    return None


def _league_averages(season):
    standings = season.get_standings_sorted()
    if not standings:
        return {}
    n = len(standings)
    return {
        "OPI": sum(r.avg_opi for r in standings) / n,
        "Territory": sum(r.avg_territory for r in standings) / n,
        "Pressure": sum(r.avg_pressure for r in standings) / n,
        "Chaos": sum(r.avg_chaos for r in standings) / n,
        "Kicking": sum(r.avg_kicking for r in standings) / n,
    }


def _render_dashboard(season, dynasty, team_name):
    record = season.standings.get(team_name)
    if not record:
        st.warning(f"No standings data found for {team_name}.")
        return

    pi = season.calculate_power_index(team_name)
    rank = _get_team_rank(season, team_name)

    st.subheader(f"{team_name}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Record", f"{record.wins}-{record.losses}")
    m2.metric("Power Index", f"{pi:.1f}", f"Rank #{rank}" if rank else None)
    if record.conference:
        m3.metric("Conference", f"{record.conf_wins}-{record.conf_losses}")
        conf_standing = _get_conference_standing(season, team_name)
        m4.metric("Conf Standing", f"#{conf_standing}" if conf_standing else "—")
    else:
        m3.metric("Win %", f"{record.win_percentage:.3f}")
        m4.metric("Games", str(record.games_played))

    p1, p2 = st.columns(2)
    p1.metric("Points For", fmt_vb_score(record.points_for))
    p2.metric("Points Against", fmt_vb_score(record.points_against))

    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    mc1.metric("OPI", f"{record.avg_opi:.1f}")
    mc2.metric("Territory", f"{record.avg_territory:.1f}")
    mc3.metric("Pressure", f"{record.avg_pressure:.1f}")
    mc4.metric("Chaos", f"{record.avg_chaos:.1f}")
    mc5.metric("Kicking", f"{record.avg_kicking:.1f}")

    avgs = _league_averages(season)
    if avgs:
        categories = list(avgs.keys())
        team_values = [record.avg_opi, record.avg_territory, record.avg_pressure, record.avg_chaos, record.avg_kicking]
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

    if dynasty:
        st.divider()
        st.subheader("Coach Profile")
        coach = dynasty.coach
        cc1, cc2, cc3, cc4 = st.columns(4)
        cc1.metric("Career Record", f"{coach.career_wins}-{coach.career_losses}")
        cc2.metric("Win %", f"{coach.win_percentage:.3f}")
        cc3.metric("Championships", str(coach.championships))
        cc4.metric("Years Experience", str(coach.years_experience))


def _render_roster(team_name):
    teams_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "teams")
    all_teams = load_teams_from_directory(teams_dir)
    team_obj = all_teams.get(team_name)
    if not team_obj:
        st.warning(f"Could not load roster for {team_name}.")
        return

    roster_data = []
    for p in team_obj.players:
        ovr = int(round((p.speed + p.stamina + p.agility + p.power + p.awareness + p.hands) / 6))
        roster_data.append({
            "Name": f"{p.name} ({p.position} #{p.number})",
            "Archetype": getattr(p, 'archetype', ''),
            "Position": p.position,
            "OVR": ovr,
            "Speed": p.speed,
            "Power": p.power,
            "Agility": p.agility,
            "Hands": p.hands,
            "Awareness": p.awareness,
            "Kicking": p.kicking,
            "Stamina": p.stamina,
        })

    if roster_data:
        st.dataframe(pd.DataFrame(roster_data), hide_index=True, use_container_width=True, height=600)
    else:
        st.info("No players found on this roster.")


def _render_schedule(season, dynasty, team_name):
    entries = []

    for g in season.schedule:
        if g.completed and (g.home_team == team_name or g.away_team == team_name):
            is_home = g.home_team == team_name
            opponent = g.away_team if is_home else g.home_team
            team_score = g.home_score if is_home else g.away_score
            opp_score = g.away_score if is_home else g.home_score
            won = (team_score or 0) > (opp_score or 0)
            entries.append({
                "game": g,
                "week": g.week,
                "opponent": opponent,
                "result": "W" if won else "L",
                "score": f"{fmt_vb_score(team_score or 0)} - {fmt_vb_score(opp_score or 0)}",
                "location": "Home" if is_home else "Away",
                "phase": "Regular Season",
                "sort_key": g.week,
                "label": f"Wk {g.week}",
            })

    if season.playoff_bracket:
        playoff_round_names = {996: "Opening Round", 997: "First Round", 998: "Quarterfinals", 999: "Semi-Finals", 1000: "Championship"}
        for g in season.playoff_bracket:
            if g.completed and (g.home_team == team_name or g.away_team == team_name):
                is_home = g.home_team == team_name
                opponent = g.away_team if is_home else g.home_team
                team_score = g.home_score if is_home else g.away_score
                opp_score = g.away_score if is_home else g.home_score
                won = (team_score or 0) > (opp_score or 0)
                round_label = playoff_round_names.get(g.week, f"Playoff R{g.week}")
                entries.append({
                    "game": g,
                    "week": 900 + g.week,
                    "opponent": opponent,
                    "result": "W" if won else "L",
                    "score": f"{fmt_vb_score(team_score or 0)} - {fmt_vb_score(opp_score or 0)}",
                    "location": "Home" if is_home else "Away",
                    "phase": "Playoff",
                    "sort_key": 900 + g.week,
                    "label": round_label,
                })

    if season.bowl_games:
        for i, bowl in enumerate(season.bowl_games):
            bg = bowl.game
            if bg.completed and (bg.home_team == team_name or bg.away_team == team_name):
                is_home = bg.home_team == team_name
                opponent = bg.away_team if is_home else bg.home_team
                team_score = bg.home_score if is_home else bg.away_score
                opp_score = bg.away_score if is_home else bg.home_score
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
                    "label": bowl.name,
                })

    entries.sort(key=lambda e: e["sort_key"])

    if not entries:
        st.info("No games found for this team in the current season.")
        return

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

    game_labels = [f"{e['label']}: vs {e['opponent']} ({e['result']}) {e['score']}" for e in entries]
    selected = st.selectbox("Select a game to view details", game_labels, key="myteam_game_select")
    if selected:
        idx = game_labels.index(selected)
        g = entries[idx]["game"]
        if g.full_result:
            with st.expander("Game Details", expanded=True):
                render_game_detail(g.full_result, key_prefix=f"myteam_gd_{idx}")


def _render_history(dynasty):
    coach = dynasty.coach

    st.subheader("Coach Career")
    hc1, hc2, hc3, hc4 = st.columns(4)
    hc1.metric("Career Record", f"{coach.career_wins}-{coach.career_losses}")
    hc2.metric("Win %", f"{coach.win_percentage:.3f}")
    hc3.metric("Championships", str(coach.championships))
    hc4.metric("Seasons", str(coach.years_experience))

    if coach.season_records:
        season_rows = []
        for year in sorted(coach.season_records.keys()):
            sr = coach.season_records[year]
            season_rows.append({
                "Year": year,
                "W-L": f"{sr['wins']}-{sr['losses']}",
                "PF": fmt_vb_score(sr.get("points_for", 0)),
                "PA": fmt_vb_score(sr.get("points_against", 0)),
                "Playoff": "Y" if sr.get("playoff") else "N",
                "Champion": "Y" if sr.get("champion") else "N",
            })
        st.dataframe(pd.DataFrame(season_rows), hide_index=True, use_container_width=True)

        wins_data = [{"Year": str(y), "Wins": coach.season_records[y]["wins"]} for y in sorted(coach.season_records.keys())]
        if wins_data:
            import plotly.express as px
            fig = px.bar(pd.DataFrame(wins_data), x="Year", y="Wins", title="Wins Per Season")
            fig.update_layout(height=350, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True, key="myteam_wins_chart")

    st.divider()
    st.subheader("Team History")
    team_hist = dynasty.team_histories.get(coach.team_name)
    if team_hist:
        th1, th2, th3, th4 = st.columns(4)
        th1.metric("All-Time Record", f"{team_hist.total_wins}-{team_hist.total_losses}")
        th2.metric("Win %", f"{team_hist.win_percentage:.3f}")
        th3.metric("Championships", str(team_hist.total_championships))
        th4.metric("Playoff Appearances", str(team_hist.total_playoff_appearances))

        if team_hist.championship_years:
            st.caption(f"Championship Years: {', '.join(str(y) for y in sorted(team_hist.championship_years))}")

    st.divider()
    st.subheader("Record Book")
    rb = dynasty.record_book

    st.markdown("**Single-Season Records**")
    ss_records = []
    if rb.most_wins_season.get("team"):
        ss_records.append({"Record": "Most Wins", "Team": rb.most_wins_season["team"], "Value": str(rb.most_wins_season["wins"]), "Year": str(rb.most_wins_season.get("year", ""))})
    if rb.most_points_season.get("team"):
        ss_records.append({"Record": "Most Points", "Team": rb.most_points_season["team"], "Value": fmt_vb_score(rb.most_points_season["points"]), "Year": str(rb.most_points_season.get("year", ""))})
    if rb.best_defense_season.get("team"):
        ss_records.append({"Record": "Best Defense (PPG)", "Team": rb.best_defense_season["team"], "Value": f"{rb.best_defense_season['ppg_allowed']:.1f}", "Year": str(rb.best_defense_season.get("year", ""))})
    if rb.highest_opi_season.get("team"):
        ss_records.append({"Record": "Highest OPI", "Team": rb.highest_opi_season["team"], "Value": f"{rb.highest_opi_season['opi']:.1f}", "Year": str(rb.highest_opi_season.get("year", ""))})
    if rb.most_chaos_season.get("team"):
        ss_records.append({"Record": "Most Chaos", "Team": rb.most_chaos_season["team"], "Value": f"{rb.most_chaos_season['chaos']:.1f}", "Year": str(rb.most_chaos_season.get("year", ""))})

    if ss_records:
        st.dataframe(pd.DataFrame(ss_records), hide_index=True, use_container_width=True)

    st.markdown("**All-Time Records**")
    at_records = []
    if rb.most_championships.get("team"):
        at_records.append({"Record": "Most Championships", "Team/Coach": rb.most_championships["team"], "Value": str(rb.most_championships["championships"])})
    if rb.highest_win_percentage.get("team"):
        at_records.append({"Record": "Highest Win %", "Team/Coach": rb.highest_win_percentage["team"], "Value": f"{rb.highest_win_percentage['win_pct']:.3f}"})
    if rb.most_coaching_wins.get("coach"):
        at_records.append({"Record": "Most Coaching Wins", "Team/Coach": rb.most_coaching_wins["coach"], "Value": str(rb.most_coaching_wins["wins"])})
    if rb.most_coaching_championships.get("coach"):
        at_records.append({"Record": "Most Coaching Championships", "Team/Coach": rb.most_coaching_championships["coach"], "Value": str(rb.most_coaching_championships["championships"])})

    if at_records:
        st.dataframe(pd.DataFrame(at_records), hide_index=True, use_container_width=True)


def render_my_team_section(shared):
    season, dynasty = _get_season_and_dynasty()

    if season is None and dynasty is None:
        st.title("My Team")
        st.info("No active session found. Go to **Play** to start a new season or dynasty.")
        return

    if dynasty:
        human_teams = [dynasty.coach.team_name]
    else:
        human_teams = _get_human_teams(dynasty)

    if not human_teams:
        st.title("My Team")
        st.info("No human-coached teams in this session. Go to **Play** to start a new one with your team selected.")
        return

    if season is None:
        st.title("My Team")
        st.info("No season data available yet. Simulate a season from **Play** to see your team's data.")
        return

    if len(human_teams) > 1:
        selected_team = st.selectbox("Select Team", human_teams, key="myteam_team_selector")
    else:
        selected_team = human_teams[0]

    tab_names = ["Dashboard", "Roster", "Schedule"]
    if dynasty:
        tab_names.append("History")

    tabs = st.tabs(tab_names)

    with tabs[0]:
        _render_dashboard(season, dynasty, selected_team)

    with tabs[1]:
        _render_roster(selected_team)

    with tabs[2]:
        _render_schedule(season, dynasty, selected_team)

    if dynasty and len(tabs) > 3:
        with tabs[3]:
            _render_history(dynasty)
