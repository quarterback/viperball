import io
import csv
import json
import os
import tempfile

import streamlit as st

from engine.season import BOWL_TIERS
from engine.awards import compute_season_awards
from engine.export import (
    export_dynasty_standings_csv,
    export_dynasty_awards_csv,
    export_injury_history_csv,
    export_development_history_csv,
    export_all_american_csv,
    export_all_conference_csv,
)
from ui.helpers import fmt_vb_score


def _get_season_and_dynasty():
    dynasty = st.session_state.get("dynasty", None)
    if dynasty and "last_dynasty_season" in st.session_state:
        return st.session_state["last_dynasty_season"], dynasty
    if "active_season" in st.session_state:
        return st.session_state["active_season"], None
    return None, None


def _build_standings_csv(season):
    standings = season.get_standings_sorted()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Rank", "Team", "W", "L", "Win%", "PF", "PA", "Diff", "OPI"])
    for i, r in enumerate(standings, 1):
        writer.writerow([
            i,
            r.team_name,
            r.wins,
            r.losses,
            f"{r.win_percentage:.3f}",
            fmt_vb_score(r.points_for),
            fmt_vb_score(r.points_against),
            fmt_vb_score(r.point_differential),
            f"{r.avg_opi:.1f}",
        ])
    return buf.getvalue()


def _build_schedule_csv(season):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Week", "Home", "Away", "Home Score", "Away Score", "Winner"])
    for g in sorted(season.schedule, key=lambda g: g.week):
        if not g.completed:
            continue
        hs = g.home_score or 0
        aws = g.away_score or 0
        winner = g.home_team if hs > aws else g.away_team
        writer.writerow([
            g.week,
            g.home_team,
            g.away_team,
            fmt_vb_score(hs),
            fmt_vb_score(aws),
            winner,
        ])
    return buf.getvalue()


def _build_season_context_json(season):
    standings = season.get_standings_sorted()
    has_conferences = bool(season.conferences) and len(season.conferences) >= 1

    standings_list = []
    for i, r in enumerate(standings, 1):
        pi = season.calculate_power_index(r.team_name)
        standings_list.append({
            "rank": i,
            "team": r.team_name,
            "conference": r.conference,
            "wins": r.wins,
            "losses": r.losses,
            "win_pct": round(r.win_percentage, 4),
            "conf_record": f"{r.conf_wins}-{r.conf_losses}",
            "points_for": round(r.points_for, 1),
            "points_against": round(r.points_against, 1),
            "point_differential": round(r.point_differential, 1),
            "power_index": round(pi, 2),
            "avg_opi": round(r.avg_opi, 2),
            "avg_territory": round(r.avg_territory, 2),
            "avg_pressure": round(r.avg_pressure, 2),
            "avg_chaos": round(r.avg_chaos, 2),
            "avg_kicking": round(r.avg_kicking, 2),
            "avg_drive_quality": round(r.avg_drive_quality, 2),
            "avg_turnover_impact": round(r.avg_turnover_impact, 2),
            "offense_style": r.offense_style,
            "defense_style": r.defense_style,
            "games_played": r.games_played,
        })

    conferences_dict = {}
    if has_conferences:
        champions = season.get_conference_champions()
        for conf_name, team_list in season.conferences.items():
            conferences_dict[conf_name] = {
                "champion": champions.get(conf_name, ""),
                "teams": team_list,
            }

    games_list = []
    for g in sorted(season.schedule, key=lambda g: g.week):
        if not g.completed:
            continue
        hs = g.home_score or 0
        aws = g.away_score or 0
        winner = g.home_team if hs > aws else g.away_team
        hm = g.home_metrics or {}
        am = g.away_metrics or {}
        entry = {
            "week": g.week,
            "home_team": g.home_team,
            "away_team": g.away_team,
            "home_score": round(hs, 1),
            "away_score": round(aws, 1),
            "winner": winner,
            "margin": round(abs(hs - aws), 1),
            "conference_game": g.is_conference_game,
            "home_stats": {
                "opi": round(hm.get("opi", 0), 2),
                "chaos": round(hm.get("chaos_factor", 0), 2),
                "territory": round(hm.get("territory_rating", 0), 2),
                "pressure": round(hm.get("pressure_index", 0), 2),
                "kicking": round(hm.get("kicking_efficiency", 0), 2),
            },
            "away_stats": {
                "opi": round(am.get("opi", 0), 2),
                "chaos": round(am.get("chaos_factor", 0), 2),
                "territory": round(am.get("territory_rating", 0), 2),
                "pressure": round(am.get("pressure_index", 0), 2),
                "kicking": round(am.get("kicking_efficiency", 0), 2),
            },
        }
        if g.full_result:
            entry["box_score"] = {
                "home": g.full_result.get("stats", {}).get("home", {}),
                "away": g.full_result.get("stats", {}).get("away", {}),
            }
        games_list.append(entry)

    playoff_round_names = {
        996: "Opening Round",
        997: "First Round",
        998: "National Quarterfinals",
        999: "National Semi-Finals",
        1000: "National Championship",
    }
    playoffs_list = []
    if season.playoff_bracket:
        for g in season.playoff_bracket:
            if not g.completed:
                continue
            hs = g.home_score or 0
            aws = g.away_score or 0
            winner = g.home_team if hs > aws else g.away_team
            playoffs_list.append({
                "round": playoff_round_names.get(g.week, f"Round {g.week}"),
                "home_team": g.home_team,
                "away_team": g.away_team,
                "home_score": round(hs, 1),
                "away_score": round(aws, 1),
                "winner": winner,
            })

    bowls_list = []
    if season.bowl_games:
        for bowl in season.bowl_games:
            bg = bowl.game
            hs = bg.home_score or 0
            aws = bg.away_score or 0
            winner = bg.home_team if hs > aws else bg.away_team
            bowls_list.append({
                "name": bowl.name,
                "tier": BOWL_TIERS.get(bowl.tier, "Standard"),
                "home_team": bg.home_team,
                "away_team": bg.away_team,
                "home_score": round(hs, 1),
                "away_score": round(aws, 1),
                "winner": winner,
            })

    power_rankings = []
    final_poll = season.get_latest_poll()
    if final_poll:
        for r in final_poll.rankings[:25]:
            power_rankings.append({
                "rank": r.rank,
                "team_name": r.team_name,
                "record": r.record,
                "conference": r.conference,
                "power_index": round(r.power_index, 2),
                "quality_wins": r.quality_wins,
                "sos_rank": r.sos_rank,
            })

    stat_leaders = {}
    if standings:
        highest_scoring = max(standings, key=lambda r: r.points_for / max(1, r.games_played))
        stat_leaders["highest_scoring"] = {
            "team": highest_scoring.team_name,
            "ppg": round(highest_scoring.points_for / max(1, highest_scoring.games_played), 2),
        }
        best_defense = min(standings, key=lambda r: r.points_against / max(1, r.games_played))
        stat_leaders["best_defense"] = {
            "team": best_defense.team_name,
            "papg": round(best_defense.points_against / max(1, best_defense.games_played), 2),
        }
        highest_opi = max(standings, key=lambda r: r.avg_opi)
        stat_leaders["highest_opi"] = {
            "team": highest_opi.team_name,
            "avg_opi": round(highest_opi.avg_opi, 2),
        }
        most_chaotic = max(standings, key=lambda r: r.avg_chaos)
        stat_leaders["most_chaotic"] = {
            "team": most_chaotic.team_name,
            "avg_chaos": round(most_chaotic.avg_chaos, 2),
        }
        best_kicking = max(standings, key=lambda r: r.avg_kicking)
        stat_leaders["best_kicking"] = {
            "team": best_kicking.team_name,
            "avg_kicking": round(best_kicking.avg_kicking, 2),
        }

    awards_list = []
    try:
        season_honors = compute_season_awards(
            season, year=2025,
            conferences=season.conferences if hasattr(season, "conferences") and season.conferences else {},
        )
        if season_honors.individual_awards:
            for a in season_honors.individual_awards:
                awards_list.append({
                    "award_name": a.award_name,
                    "player_name": a.player_name,
                    "position": a.position,
                    "team_name": a.team_name,
                    "overall_rating": a.overall_rating,
                })
        if season_honors.coach_of_year:
            awards_list.append({
                "award_name": "Coach of the Year",
                "player_name": "",
                "position": "",
                "team_name": season_honors.coach_of_year,
                "overall_rating": 0,
            })
        if season_honors.most_improved:
            awards_list.append({
                "award_name": "Most Improved Program",
                "player_name": "",
                "position": "",
                "team_name": season_honors.most_improved,
                "overall_rating": 0,
            })
    except Exception:
        pass

    completed_games = [g for g in season.schedule if g.completed]

    export = {
        "season_name": season.name,
        "national_champion": season.champion or None,
        "total_teams": len(standings),
        "total_games": len(completed_games),
        "standings": standings_list,
        "conferences": conferences_dict,
        "games": games_list,
        "playoffs": playoffs_list,
        "bowl_games": bowls_list,
        "power_rankings": power_rankings,
        "statistical_leaders": stat_leaders,
        "awards": awards_list,
    }

    return json.dumps(export, indent=2, default=str)


def _read_dynasty_export(export_func, dynasty):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        export_func(dynasty, tmp_path)
        with open(tmp_path, "r", encoding="utf-8") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def render_export_section(shared):
    season, dynasty = _get_season_and_dynasty()

    if season is None:
        st.title("Export")
        st.info("No active season found. Start a new season or dynasty from the Play section to export data.")
        return

    st.title("Export")

    is_dynasty = dynasty is not None

    tab_names = ["Season Data"]
    if is_dynasty:
        tab_names.append("Dynasty Data")

    tabs = st.tabs(tab_names)

    with tabs[0]:
        st.subheader("Season Exports")

        standings_csv = _build_standings_csv(season)
        st.download_button(
            "Download Standings CSV",
            standings_csv,
            file_name=f"{season.name.lower().replace(' ', '_')}_standings.csv",
            mime="text/csv",
            key="export_standings_csv",
        )

        schedule_csv = _build_schedule_csv(season)
        st.download_button(
            "Download Schedule CSV",
            schedule_csv,
            file_name=f"{season.name.lower().replace(' ', '_')}_schedule.csv",
            mime="text/csv",
            key="export_schedule_csv",
        )

        context_json = _build_season_context_json(season)
        st.download_button(
            "Download Full Season Context JSON",
            context_json,
            file_name=f"{season.name.lower().replace(' ', '_')}_context.json",
            mime="application/json",
            key="export_season_context_json",
        )

    if is_dynasty:
        with tabs[1]:
            st.subheader("Dynasty Exports")

            dynasty_standings = _read_dynasty_export(export_dynasty_standings_csv, dynasty)
            st.download_button(
                "Download Dynasty Standings CSV",
                dynasty_standings,
                file_name="dynasty_standings.csv",
                mime="text/csv",
                key="export_dynasty_standings_csv",
            )

            dynasty_awards = _read_dynasty_export(export_dynasty_awards_csv, dynasty)
            st.download_button(
                "Download Awards History CSV",
                dynasty_awards,
                file_name="dynasty_awards.csv",
                mime="text/csv",
                key="export_dynasty_awards_csv",
            )

            dynasty_injuries = _read_dynasty_export(export_injury_history_csv, dynasty)
            st.download_button(
                "Download Injury History CSV",
                dynasty_injuries,
                file_name="dynasty_injuries.csv",
                mime="text/csv",
                key="export_dynasty_injuries_csv",
            )

            dynasty_dev = _read_dynasty_export(export_development_history_csv, dynasty)
            st.download_button(
                "Download Development History CSV",
                dynasty_dev,
                file_name="dynasty_development.csv",
                mime="text/csv",
                key="export_dynasty_development_csv",
            )

            dynasty_aa = _read_dynasty_export(export_all_american_csv, dynasty)
            st.download_button(
                "Download All-CVL Selections CSV",
                dynasty_aa,
                file_name="dynasty_all_cvl.csv",
                mime="text/csv",
                key="export_dynasty_all_american_csv",
            )

            dynasty_ac = _read_dynasty_export(export_all_conference_csv, dynasty)
            st.download_button(
                "Download All-Conference Selections CSV",
                dynasty_ac,
                file_name="dynasty_all_conference.csv",
                mime="text/csv",
                key="export_dynasty_all_conference_csv",
            )

            st.divider()
            st.subheader("Dynasty Save")

            save_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "dynasty_save.json")
            if st.button("Save Dynasty", key="export_save_dynasty"):
                dynasty.save(save_path)
                st.success("Dynasty saved successfully.")

            if os.path.exists(save_path):
                with open(save_path, "r", encoding="utf-8") as f:
                    save_data = f.read()
                st.download_button(
                    "Download Dynasty Save File",
                    save_data,
                    file_name="dynasty_save.json",
                    mime="application/json",
                    key="export_download_dynasty_save",
                )
