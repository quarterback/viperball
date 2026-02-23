"""Export section for the NiceGUI Viperball app.

Provides CSV, JSON, and full season context downloads for season
and dynasty data. Migrated from ui/page_modules/section_export.py.
"""

from __future__ import annotations

import io
import csv
import json

from nicegui import ui, run

from engine.season import BOWL_TIERS
from ui import api_client
from nicegui_app.helpers import fmt_vb_score
from nicegui_app.components import metric_card, download_button, notify_info, notify_error


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_standings_csv(standings):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Rank", "Team", "W", "L", "Win%", "PF", "PA", "Diff", "OPI"])
    for i, r in enumerate(standings, 1):
        writer.writerow([
            i,
            r.get("team_name", ""),
            r.get("wins", 0),
            r.get("losses", 0),
            f"{r.get('win_percentage', 0):.3f}",
            fmt_vb_score(r.get("points_for", 0)),
            fmt_vb_score(r.get("points_against", 0)),
            fmt_vb_score(r.get("point_differential", 0)),
            f"{r.get('avg_opi', 0):.1f}",
        ])
    return buf.getvalue()


def _build_schedule_csv(games):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Week", "Home", "Away", "Home Score", "Away Score", "Winner"])
    for g in sorted(games, key=lambda g: g.get("week", 0)):
        if not g.get("completed"):
            continue
        hs = g.get("home_score") or 0
        aws = g.get("away_score") or 0
        home = g.get("home_team", "")
        away = g.get("away_team", "")
        winner = home if hs > aws else away
        writer.writerow([
            g.get("week", 0),
            home,
            away,
            fmt_vb_score(hs),
            fmt_vb_score(aws),
            winner,
        ])
    return buf.getvalue()


async def _build_season_context_json(session_id, standings, games, conferences):
    has_conferences = bool(conferences) and len(conferences) >= 1

    standings_list = []
    for i, r in enumerate(standings, 1):
        standings_list.append({
            "rank": i,
            "team": r.get("team_name", ""),
            "conference": r.get("conference", ""),
            "wins": r.get("wins", 0),
            "losses": r.get("losses", 0),
            "win_pct": round(r.get("win_percentage", 0), 4),
            "conf_record": f"{r.get('conf_wins', 0)}-{r.get('conf_losses', 0)}",
            "points_for": round(r.get("points_for", 0), 1),
            "points_against": round(r.get("points_against", 0), 1),
            "point_differential": round(r.get("point_differential", 0), 1),
            "avg_opi": round(r.get("avg_opi", 0), 2),
            "avg_territory": round(r.get("avg_territory", 0), 2),
            "avg_pressure": round(r.get("avg_pressure", 0), 2),
            "avg_chaos": round(r.get("avg_chaos", 0), 2),
            "avg_kicking": round(r.get("avg_kicking", 0), 2),
            "avg_drive_quality": round(r.get("avg_drive_quality", 0), 2),
            "avg_turnover_impact": round(r.get("avg_turnover_impact", 0), 2),
            "offense_style": r.get("offense_style", ""),
            "defense_style": r.get("defense_style", ""),
            "games_played": r.get("games_played", 0),
        })

    conferences_dict = {}
    if has_conferences:
        try:
            conf_standings_resp = await run.io_bound(api_client.get_conference_standings, session_id)
            champions = conf_standings_resp.get("champions", {})
        except api_client.APIError:
            champions = {}
        for conf_name, team_list in conferences.items():
            conferences_dict[conf_name] = {
                "champion": champions.get(conf_name, ""),
                "teams": team_list,
            }

    games_list = []
    for g in sorted(games, key=lambda g: g.get("week", 0)):
        if not g.get("completed"):
            continue
        hs = g.get("home_score") or 0
        aws = g.get("away_score") or 0
        home = g.get("home_team", "")
        away = g.get("away_team", "")
        winner = home if hs > aws else away
        hm = g.get("home_metrics") or {}
        am = g.get("away_metrics") or {}
        entry = {
            "week": g.get("week", 0),
            "home_team": home,
            "away_team": away,
            "home_score": round(hs, 1),
            "away_score": round(aws, 1),
            "winner": winner,
            "margin": round(abs(hs - aws), 1),
            "conference_game": g.get("is_conference_game", False),
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
        full_result = g.get("full_result")
        if full_result:
            entry["box_score"] = {
                "home": full_result.get("stats", {}).get("home", {}),
                "away": full_result.get("stats", {}).get("away", {}),
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
    try:
        bracket_resp = await run.io_bound(api_client.get_playoff_bracket, session_id)
        bracket = bracket_resp.get("bracket", [])
        champion = bracket_resp.get("champion")
    except api_client.APIError:
        bracket = []
        champion = None

    for g in bracket:
        if not g.get("completed"):
            continue
        hs = g.get("home_score") or 0
        aws = g.get("away_score") or 0
        home = g.get("home_team", "")
        away = g.get("away_team", "")
        winner = home if hs > aws else away
        playoffs_list.append({
            "round": playoff_round_names.get(g.get("week", 0), f"Round {g.get('week', 0)}"),
            "home_team": home,
            "away_team": away,
            "home_score": round(hs, 1),
            "away_score": round(aws, 1),
            "winner": winner,
        })

    bowls_list = []
    try:
        bowls_resp = await run.io_bound(api_client.get_bowl_results, session_id)
        bowl_results = bowls_resp.get("bowl_results", [])
    except api_client.APIError:
        bowl_results = []

    for bowl in bowl_results:
        bg = bowl.get("game", {})
        hs = bg.get("home_score") or 0
        aws = bg.get("away_score") or 0
        home = bg.get("home_team", "")
        away = bg.get("away_team", "")
        winner = home if hs > aws else away
        bowls_list.append({
            "name": bowl.get("name", ""),
            "tier": BOWL_TIERS.get(bowl.get("tier", 0), "Standard"),
            "home_team": home,
            "away_team": away,
            "home_score": round(hs, 1),
            "away_score": round(aws, 1),
            "winner": winner,
        })

    power_rankings = []
    try:
        polls_resp = await run.io_bound(api_client.get_polls, session_id)
        all_polls = polls_resp.get("polls", [])
        if all_polls:
            final_poll = all_polls[-1]
            for r in final_poll.get("rankings", [])[:25]:
                power_rankings.append({
                    "rank": r.get("rank", 0),
                    "team_name": r.get("team_name", ""),
                    "record": r.get("record", ""),
                    "conference": r.get("conference", ""),
                    "power_index": round(r.get("power_index", 0), 2),
                    "quality_wins": r.get("quality_wins", 0),
                    "sos_rank": r.get("sos_rank", 0),
                })
    except api_client.APIError:
        pass

    stat_leaders = {}
    if standings:
        highest_scoring = max(standings, key=lambda r: r.get("points_for", 0) / max(1, r.get("games_played", 1)))
        stat_leaders["highest_scoring"] = {
            "team": highest_scoring.get("team_name", ""),
            "ppg": round(highest_scoring.get("points_for", 0) / max(1, highest_scoring.get("games_played", 1)), 2),
        }
        best_defense = min(standings, key=lambda r: r.get("points_against", 0) / max(1, r.get("games_played", 1)))
        stat_leaders["best_defense"] = {
            "team": best_defense.get("team_name", ""),
            "papg": round(best_defense.get("points_against", 0) / max(1, best_defense.get("games_played", 1)), 2),
        }
        highest_opi = max(standings, key=lambda r: r.get("avg_opi", 0))
        stat_leaders["highest_opi"] = {
            "team": highest_opi.get("team_name", ""),
            "avg_opi": round(highest_opi.get("avg_opi", 0), 2),
        }
        most_chaotic = max(standings, key=lambda r: r.get("avg_chaos", 0))
        stat_leaders["most_chaotic"] = {
            "team": most_chaotic.get("team_name", ""),
            "avg_chaos": round(most_chaotic.get("avg_chaos", 0), 2),
        }
        best_kicking = max(standings, key=lambda r: r.get("avg_kicking", 0))
        stat_leaders["best_kicking"] = {
            "team": best_kicking.get("team_name", ""),
            "avg_kicking": round(best_kicking.get("avg_kicking", 0), 2),
        }

    awards_list = []
    try:
        awards = await run.io_bound(api_client.get_season_awards, session_id)
        for a in awards.get("individual_awards", []):
            awards_list.append({
                "award_name": a.get("award_name", ""),
                "player_name": a.get("player_name", ""),
                "position": a.get("position", ""),
                "team_name": a.get("team_name", ""),
                "overall_rating": a.get("overall_rating", 0),
            })
        if awards.get("coach_of_year"):
            awards_list.append({
                "award_name": "Coach of the Year",
                "player_name": "",
                "position": "",
                "team_name": awards["coach_of_year"],
                "overall_rating": 0,
            })
        if awards.get("most_improved"):
            awards_list.append({
                "award_name": "Most Improved Program",
                "player_name": "",
                "position": "",
                "team_name": awards["most_improved"],
                "overall_rating": 0,
            })
    except api_client.APIError:
        pass

    try:
        status = await run.io_bound(api_client.get_season_status, session_id)
        season_name = status.get("name", "Season")
    except api_client.APIError:
        season_name = "Season"

    completed_games = [g for g in games if g.get("completed")]

    export = {
        "season_name": season_name,
        "national_champion": champion,
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


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

async def render_export_section(state, shared):
    session_id = state.session_id
    mode = state.mode

    if not session_id or not mode:
        ui.label("Export").classes("text-3xl font-bold")
        notify_info("No active season found. Start a new season or dynasty from the Play section to export data.")
        return

    try:
        standings_resp = await run.io_bound(api_client.get_standings, session_id)
        standings = standings_resp.get("standings", [])
    except api_client.APIError:
        ui.label("Export").classes("text-3xl font-bold")
        notify_info("No active season found. Start a new season or dynasty from the Play section to export data.")
        return

    if not standings:
        ui.label("Export").classes("text-3xl font-bold")
        notify_info("No standings data available. Simulate games first.")
        return

    ui.label("Export").classes("text-3xl font-bold")

    is_dynasty = mode == "dynasty"

    tab_names = ["Season Data"]
    if is_dynasty:
        tab_names.append("Dynasty Data")

    with ui.tabs().classes("w-full") as tabs:
        season_tab = ui.tab("Season Data")
        if is_dynasty:
            dynasty_tab = ui.tab("Dynasty Data")

    with ui.tab_panels(tabs, value=season_tab).classes("w-full"):
        with ui.tab_panel(season_tab):
            ui.label("Season Exports").classes("text-xl font-semibold mt-2")

            standings_csv = _build_standings_csv(standings)
            try:
                status = await run.io_bound(api_client.get_season_status, session_id)
                season_name = status.get("name", "season")
            except api_client.APIError:
                season_name = "season"

            download_button(
                "Download Standings CSV",
                standings_csv,
                f"{season_name.lower().replace(' ', '_')}_standings.csv",
                mime="text/csv",
            )

            try:
                sched_resp = await run.io_bound(api_client.get_schedule, session_id, completed_only=True)
                all_games = sched_resp.get("games", [])
            except api_client.APIError:
                all_games = []

            schedule_csv = _build_schedule_csv(all_games)
            download_button(
                "Download Schedule CSV",
                schedule_csv,
                f"{season_name.lower().replace(' ', '_')}_schedule.csv",
                mime="text/csv",
            )

            try:
                conf_resp = await run.io_bound(api_client.get_conferences, session_id)
                conferences = conf_resp.get("conferences", {})
            except api_client.APIError:
                conferences = {}

            try:
                sched_with_details = await run.io_bound(lambda: api_client.get_schedule(
                    session_id, completed_only=True, include_full_result=True
                ))
                games_with_details = sched_with_details.get("games", [])
            except api_client.APIError:
                games_with_details = all_games

            context_json = await _build_season_context_json(
                session_id, standings, games_with_details, conferences
            )
            download_button(
                "Download Full Season Context JSON",
                context_json,
                f"{season_name.lower().replace(' ', '_')}_context.json",
                mime="application/json",
            )

        if is_dynasty:
            with ui.tab_panel(dynasty_tab):
                ui.label("Dynasty Exports").classes("text-xl font-semibold mt-2")

                try:
                    dyn_status = await run.io_bound(api_client.get_dynasty_status, session_id)
                except api_client.APIError:
                    notify_error("Could not load dynasty data.")
                    return

                try:
                    histories_resp = await run.io_bound(api_client.get_dynasty_team_histories, session_id)
                    team_histories = histories_resp.get("team_histories", {})
                except api_client.APIError:
                    team_histories = {}

                if team_histories:
                    buf = io.StringIO()
                    writer = csv.writer(buf)
                    writer.writerow(["Team", "Wins", "Losses", "Win%", "Championships", "Playoff Apps"])
                    for tname, hist in sorted(team_histories.items()):
                        writer.writerow([
                            tname,
                            hist.get("total_wins", 0),
                            hist.get("total_losses", 0),
                            f"{hist.get('win_percentage', 0):.3f}",
                            hist.get("total_championships", 0),
                            hist.get("total_playoff_appearances", 0),
                        ])
                    download_button(
                        "Download Dynasty Team Histories CSV",
                        buf.getvalue(),
                        "dynasty_team_histories.csv",
                        mime="text/csv",
                    )

                try:
                    awards_resp = await run.io_bound(api_client.get_dynasty_awards, session_id)
                    awards_history = awards_resp.get("awards_history", [])
                except api_client.APIError:
                    awards_history = []

                if awards_history:
                    buf = io.StringIO()
                    writer = csv.writer(buf)
                    writer.writerow(["Year", "Award", "Player", "Position", "Team"])
                    for entry in awards_history:
                        year = entry.get("year", "")
                        for a in entry.get("awards", []):
                            writer.writerow([
                                year,
                                a.get("award_name", ""),
                                a.get("player_name", ""),
                                a.get("position", ""),
                                a.get("team_name", ""),
                            ])
                    download_button(
                        "Download Awards History CSV",
                        buf.getvalue(),
                        "dynasty_awards.csv",
                        mime="text/csv",
                    )

                ui.separator()
                ui.label("Dynasty Save").classes("text-xl font-semibold mt-2")
                ui.label("Dynasty save/load through the API is coming soon.").classes(
                    "text-sm text-gray-500"
                )
