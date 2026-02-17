"""
Viperball Stats Export

Exports season and dynasty statistics to CSV files for external analysis.

Available exports:
    export_season_standings_csv(season, filepath)
        - One row per team: wins, losses, points, all sabermetric averages

    export_season_game_log_csv(season, filepath)
        - One row per completed game: teams, scores, both teams' metrics

    export_dynasty_standings_csv(dynasty, filepath)
        - One row per (year, team): all-time totals and per-season record

    export_dynasty_awards_csv(dynasty, filepath)
        - One row per year: all team and individual award winners

    export_injury_history_csv(dynasty, filepath)
        - One row per injury across all recorded seasons

    export_development_history_csv(dynasty, filepath)
        - One row per notable development event across all offseasons

    export_all_american_csv(dynasty, filepath)
        - One row per All-American selection across all seasons

Usage:
    from engine.export import export_season_standings_csv
    export_season_standings_csv(season, "output/season_2026_standings.csv")
"""

from __future__ import annotations

import csv
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.season import Season
    from engine.dynasty import Dynasty


def _ensure_dir(filepath: str):
    """Create parent directory if it doesn't exist."""
    parent = os.path.dirname(filepath)
    if parent:
        os.makedirs(parent, exist_ok=True)


# ──────────────────────────────────────────────
# SEASON EXPORTS
# ──────────────────────────────────────────────

def export_season_standings_csv(season: "Season", filepath: str) -> str:
    """
    Export end-of-season standings to CSV.

    Columns: team, conference, wins, losses, games_played, win_pct,
             points_for, points_against, point_differential,
             conf_wins, conf_losses, conf_win_pct,
             avg_opi, avg_territory, avg_pressure, avg_chaos,
             avg_kicking, avg_drive_quality, avg_turnover_impact,
             offense_style, defense_style
    """
    _ensure_dir(filepath)
    fieldnames = [
        "team", "conference", "wins", "losses", "games_played", "win_pct",
        "points_for", "points_against", "point_differential",
        "conf_wins", "conf_losses", "conf_win_pct",
        "avg_opi", "avg_territory", "avg_pressure", "avg_chaos",
        "avg_kicking", "avg_drive_quality", "avg_turnover_impact",
        "offense_style", "defense_style",
    ]

    rows = []
    for team_name, record in season.standings.items():
        rows.append({
            "team": team_name,
            "conference": record.conference,
            "wins": record.wins,
            "losses": record.losses,
            "games_played": record.games_played,
            "win_pct": round(record.win_percentage, 4),
            "points_for": round(record.points_for, 1),
            "points_against": round(record.points_against, 1),
            "point_differential": round(record.point_differential, 2),
            "conf_wins": record.conf_wins,
            "conf_losses": record.conf_losses,
            "conf_win_pct": round(record.conf_win_percentage, 4),
            "avg_opi": round(record.avg_opi, 2),
            "avg_territory": round(record.avg_territory, 2),
            "avg_pressure": round(record.avg_pressure, 2),
            "avg_chaos": round(record.avg_chaos, 2),
            "avg_kicking": round(record.avg_kicking, 2),
            "avg_drive_quality": round(record.avg_drive_quality, 2),
            "avg_turnover_impact": round(record.avg_turnover_impact, 2),
            "offense_style": record.offense_style,
            "defense_style": record.defense_style,
        })

    # Sort by win_pct descending
    rows.sort(key=lambda r: r["win_pct"], reverse=True)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return filepath


def export_season_game_log_csv(season: "Season", filepath: str) -> str:
    """
    Export every completed game in the season to CSV.

    Columns: week, home_team, away_team, home_score, away_score, winner,
             is_conference_game, home_opi, home_chaos, home_territory,
             away_opi, away_chaos, away_territory
    """
    _ensure_dir(filepath)
    fieldnames = [
        "week", "home_team", "away_team",
        "home_score", "away_score", "winner", "margin",
        "is_conference_game",
        "home_opi", "home_chaos", "home_territory", "home_pressure", "home_kicking",
        "away_opi", "away_chaos", "away_territory", "away_pressure", "away_kicking",
    ]

    rows = []
    for game in season.schedule:
        if not game.completed:
            continue
        hs = game.home_score or 0
        as_ = game.away_score or 0
        winner = game.home_team if hs > as_ else game.away_team
        hm = game.home_metrics or {}
        am = game.away_metrics or {}
        rows.append({
            "week": game.week,
            "home_team": game.home_team,
            "away_team": game.away_team,
            "home_score": round(hs, 1),
            "away_score": round(as_, 1),
            "winner": winner,
            "margin": round(abs(hs - as_), 1),
            "is_conference_game": int(game.is_conference_game),
            "home_opi": round(hm.get("opi", 0), 2),
            "home_chaos": round(hm.get("chaos_factor", 0), 2),
            "home_territory": round(hm.get("territory_rating", 0), 2),
            "home_pressure": round(hm.get("pressure_index", 0), 2),
            "home_kicking": round(hm.get("kicking_efficiency", 0), 2),
            "away_opi": round(am.get("opi", 0), 2),
            "away_chaos": round(am.get("chaos_factor", 0), 2),
            "away_territory": round(am.get("territory_rating", 0), 2),
            "away_pressure": round(am.get("pressure_index", 0), 2),
            "away_kicking": round(am.get("kicking_efficiency", 0), 2),
        })

    rows.sort(key=lambda r: r["week"])

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return filepath


# ──────────────────────────────────────────────
# DYNASTY EXPORTS
# ──────────────────────────────────────────────

def export_dynasty_standings_csv(dynasty: "Dynasty", filepath: str) -> str:
    """
    Export full dynasty season-by-season standings to CSV.

    Columns: year, team, conference, wins, losses, win_pct,
             points_for, points_against, avg_opi,
             champion, playoff
    """
    _ensure_dir(filepath)
    fieldnames = [
        "year", "team", "conference",
        "wins", "losses", "win_pct",
        "points_for", "points_against", "avg_opi",
        "champion", "playoff",
    ]

    rows = []
    for year in sorted(dynasty.seasons.keys()):
        season = dynasty.seasons[year]
        for team_name, record in season.standings.items():
            history = dynasty.team_histories.get(team_name)
            yr_record = history.season_records.get(year, {}) if history else {}
            rows.append({
                "year": year,
                "team": team_name,
                "conference": record.conference,
                "wins": record.wins,
                "losses": record.losses,
                "win_pct": round(record.win_percentage, 4),
                "points_for": round(record.points_for, 1),
                "points_against": round(record.points_against, 1),
                "avg_opi": round(record.avg_opi, 2),
                "champion": int(yr_record.get("champion", False)),
                "playoff": int(yr_record.get("playoff", False)),
            })

    rows.sort(key=lambda r: (r["year"], -r["win_pct"]))

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return filepath


def export_dynasty_awards_csv(dynasty: "Dynasty", filepath: str) -> str:
    """
    Export all team and individual award winners per year to CSV.

    Columns: year, award_type, award_name, winner, team, position, overall_rating
    """
    _ensure_dir(filepath)
    fieldnames = [
        "year", "award_type", "award_name", "winner", "team", "position", "overall_rating"
    ]

    rows = []

    for year in sorted(dynasty.awards_history.keys()):
        awards = dynasty.awards_history[year]

        # Team-level awards
        team_awards = [
            ("team", "CVL Champion", awards.champion, awards.champion, "", 0),
            ("team", "Best Record", awards.best_record, awards.best_record, "", 0),
            ("team", "Highest Scoring", awards.highest_scoring, awards.highest_scoring, "", 0),
            ("team", "Best Defense", awards.best_defense, awards.best_defense, "", 0),
            ("team", "Highest OPI", awards.highest_opi, awards.highest_opi, "", 0),
            ("team", "Most Chaos", awards.most_chaos, awards.most_chaos, "", 0),
            ("team", "Best Kicking", awards.best_kicking, awards.best_kicking, "", 0),
        ]
        for award_type, award_name, winner, team, pos, ovr in team_awards:
            rows.append({
                "year": year,
                "award_type": award_type,
                "award_name": award_name,
                "winner": winner,
                "team": team,
                "position": pos,
                "overall_rating": ovr,
            })

        # Individual awards from honors
        honors = dynasty.honors_history.get(year, {})
        for a in honors.get("individual_awards", []):
            rows.append({
                "year": year,
                "award_type": "individual",
                "award_name": a.get("award_name", ""),
                "winner": a.get("player_name", ""),
                "team": a.get("team_name", ""),
                "position": a.get("position", ""),
                "overall_rating": a.get("overall_rating", 0),
            })

        # Team-level honors awards
        for award_name, winner in [
            ("Coach of the Year", honors.get("coach_of_year", "")),
            ("Chaos King", honors.get("chaos_king", "")),
            ("Most Improved Team", honors.get("most_improved", "")),
        ]:
            if winner:
                rows.append({
                    "year": year,
                    "award_type": "team_honor",
                    "award_name": award_name,
                    "winner": winner,
                    "team": winner,
                    "position": "",
                    "overall_rating": 0,
                })

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return filepath


def export_injury_history_csv(dynasty: "Dynasty", filepath: str) -> str:
    """
    Export all recorded injuries across all seasons to CSV.

    Columns: year, team, player, position, tier, description,
             week_injured, weeks_out, season_ending
    """
    _ensure_dir(filepath)
    fieldnames = [
        "year", "team", "player", "position", "tier", "description",
        "week_injured", "weeks_out", "season_ending",
    ]

    rows = []
    for year in sorted(dynasty.injury_history.keys()):
        report = dynasty.injury_history[year]
        for team_name, injuries in report.items():
            for inj in injuries:
                rows.append({
                    "year": year,
                    "team": team_name,
                    "player": inj.get("player_name", ""),
                    "position": inj.get("position", ""),
                    "tier": inj.get("tier", ""),
                    "description": inj.get("description", ""),
                    "week_injured": inj.get("week_injured", 0),
                    "weeks_out": inj.get("weeks_out", 0),
                    "season_ending": int(inj.get("is_season_ending", False)),
                })

    rows.sort(key=lambda r: (r["year"], r["team"]))

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return filepath


def export_development_history_csv(dynasty: "Dynasty", filepath: str) -> str:
    """
    Export notable player development events across all offseasons to CSV.

    Columns: offseason_year, team, player, event_type, description
    """
    _ensure_dir(filepath)
    fieldnames = ["offseason_year", "team", "player", "event_type", "description"]

    rows = []
    for year in sorted(dynasty.development_history.keys()):
        for ev in dynasty.development_history[year]:
            rows.append({
                "offseason_year": year,
                "team": ev.get("team", ""),
                "player": ev.get("player", ""),
                "event_type": ev.get("event_type", ""),
                "description": ev.get("description", ""),
            })

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return filepath


def export_all_american_csv(dynasty: "Dynasty", filepath: str) -> str:
    """
    Export All-American selections across all seasons to CSV.

    Columns: year, team_level, position_slot, player, team, position, overall_rating
    """
    _ensure_dir(filepath)
    fieldnames = [
        "year", "team_level", "position_slot",
        "player", "team", "position", "overall_rating",
    ]

    rows = []
    for year in sorted(dynasty.honors_history.keys()):
        honors = dynasty.honors_history[year]
        for team_key, level_label in [("all_american_first", "1st Team"), ("all_american_second", "2nd Team")]:
            team_data = honors.get(team_key) or {}
            for slot in team_data.get("slots", []):
                rows.append({
                    "year": year,
                    "team_level": level_label,
                    "position_slot": slot.get("award_name", ""),
                    "player": slot.get("player_name", ""),
                    "team": slot.get("team_name", ""),
                    "position": slot.get("position", ""),
                    "overall_rating": slot.get("overall_rating", 0),
                })

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return filepath


def export_all_conference_csv(dynasty: "Dynasty", filepath: str) -> str:
    """
    Export All-Conference selections across all seasons to CSV.

    Columns: year, conference, position_slot, player, team, position, overall_rating
    """
    _ensure_dir(filepath)
    fieldnames = [
        "year", "conference", "position_slot",
        "player", "team", "position", "overall_rating",
    ]

    rows = []
    for year in sorted(dynasty.honors_history.keys()):
        honors = dynasty.honors_history[year]
        for conf_name, conf_data in (honors.get("all_conference_teams") or {}).items():
            for slot in conf_data.get("slots", []):
                rows.append({
                    "year": year,
                    "conference": conf_name,
                    "position_slot": slot.get("award_name", ""),
                    "player": slot.get("player_name", ""),
                    "team": slot.get("team_name", ""),
                    "position": slot.get("position", ""),
                    "overall_rating": slot.get("overall_rating", 0),
                })

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return filepath


# ──────────────────────────────────────────────
# CONVENIENCE: EXPORT EVERYTHING
# ──────────────────────────────────────────────

def export_dynasty_full(dynasty: "Dynasty", output_dir: str) -> dict:
    """
    Export all dynasty stats to a directory.

    Creates:
        <output_dir>/standings.csv
        <output_dir>/awards.csv
        <output_dir>/injuries.csv
        <output_dir>/development.csv
        <output_dir>/all_american.csv
        <output_dir>/all_conference.csv

    Returns dict of {export_name: filepath}.
    """
    os.makedirs(output_dir, exist_ok=True)
    exported = {}

    exported["standings"] = export_dynasty_standings_csv(
        dynasty, os.path.join(output_dir, "standings.csv")
    )
    exported["awards"] = export_dynasty_awards_csv(
        dynasty, os.path.join(output_dir, "awards.csv")
    )
    exported["injuries"] = export_injury_history_csv(
        dynasty, os.path.join(output_dir, "injuries.csv")
    )
    exported["development"] = export_development_history_csv(
        dynasty, os.path.join(output_dir, "development.csv")
    )
    exported["all_american"] = export_all_american_csv(
        dynasty, os.path.join(output_dir, "all_american.csv")
    )
    exported["all_conference"] = export_all_conference_csv(
        dynasty, os.path.join(output_dir, "all_conference.csv")
    )

    return exported


def export_season_full(season: "Season", output_dir: str) -> dict:
    """
    Export all single-season stats to a directory.

    Creates:
        <output_dir>/season_standings.csv
        <output_dir>/season_games.csv

    Returns dict of {export_name: filepath}.
    """
    os.makedirs(output_dir, exist_ok=True)
    return {
        "standings": export_season_standings_csv(
            season, os.path.join(output_dir, "season_standings.csv")
        ),
        "games": export_season_game_log_csv(
            season, os.path.join(output_dir, "season_games.csv")
        ),
    }
