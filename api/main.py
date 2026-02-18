"""
Viperball Simulation API
FastAPI wrapper around the Viperball engine
"""

import sys
import os
import uuid
import time
import random
from typing import Dict, List, Optional
from dataclasses import asdict
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from engine import ViperballEngine, load_team_from_json, get_available_teams, get_available_styles, OFFENSE_STYLES
from engine.season import (
    Season, TeamRecord, Game, WeeklyPoll, PollRanking,
    load_teams_from_directory, load_teams_with_states, create_season, get_recommended_bowl_count, BOWL_TIERS
)
from engine.dynasty import create_dynasty, Dynasty
from engine.conference_names import generate_conference_names
from engine.geography import get_geographic_conference_defaults
from engine.injuries import InjuryTracker
from engine.awards import compute_season_awards
from engine.player_card import player_to_card
from engine.ai_coach import auto_assign_all_teams, get_scheme_label, load_team_identity
from engine.game_engine import WEATHER_CONDITIONS, DEFENSE_STYLES


app = FastAPI(title="Viperball Simulation API", version="1.0.0")

TEAMS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams")

sessions: Dict[str, dict] = {}


class SimulateRequest(BaseModel):
    home: str
    away: str
    seed: Optional[int] = None
    styles: Optional[Dict[str, str]] = None
    weather: str = "clear"


class SimulateManyRequest(BaseModel):
    home: str
    away: str
    count: int = 10
    seed: Optional[int] = None
    styles: Optional[Dict[str, str]] = None
    weather: str = "clear"


class DebugPlayRequest(BaseModel):
    style: str = "balanced"
    field_position: int = 40
    down: int = 2
    yards_to_go: int = 8


class CreateSeasonRequest(BaseModel):
    name: str = "2026 CVL Season"
    games_per_team: int = 10
    playoff_size: int = 8
    bowl_count: int = 4
    human_teams: List[str] = []
    human_configs: Dict[str, Dict[str, str]] = {}
    num_conferences: int = 10
    ai_seed: int = 0
    conferences: Optional[Dict[str, List[str]]] = None
    style_configs: Optional[Dict[str, Dict[str, str]]] = None


class CreateDynastyRequest(BaseModel):
    dynasty_name: str = "My Viperball Dynasty"
    coach_name: str = "Coach"
    coach_team: str
    starting_year: int = 2026
    num_conferences: int = 10
    history_years: int = 0


class SimulateWeekRequest(BaseModel):
    week: Optional[int] = None


class SimulateThroughRequest(BaseModel):
    target_week: int


class DynastyStartSeasonRequest(BaseModel):
    games_per_team: int = 10
    playoff_size: int = 8
    bowl_count: int = 4
    offense_style: str = "balanced"
    defense_style: str = "base_defense"
    ai_seed: Optional[int] = None


class QuickGameRequest(BaseModel):
    home: str
    away: str
    home_offense: str = "balanced"
    home_defense: str = "base_defense"
    away_offense: str = "balanced"
    away_defense: str = "base_defense"
    weather: str = "clear"
    seed: Optional[int] = None


def _load_team(key: str):
    filepath = os.path.join(TEAMS_DIR, f"{key}.json")
    if not os.path.exists(filepath):
        cleaned = key.lower().replace(" ", "_").replace("-", "_")
        filepath = os.path.join(TEAMS_DIR, f"{cleaned}.json")
    return load_team_from_json(filepath)


def _get_session(session_id: str) -> dict:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]


def _require_season(session: dict) -> Season:
    if session.get("season") is None:
        raise HTTPException(status_code=400, detail="No season created in this session")
    return session["season"]


def _require_dynasty(session: dict) -> Dynasty:
    if session.get("dynasty") is None:
        raise HTTPException(status_code=400, detail="No dynasty created in this session")
    return session["dynasty"]


def _serialize_team_record(rec: TeamRecord) -> dict:
    return {
        "team_name": rec.team_name,
        "wins": rec.wins,
        "losses": rec.losses,
        "points_for": round(rec.points_for, 1),
        "points_against": round(rec.points_against, 1),
        "conference": rec.conference,
        "games_played": rec.games_played,
        "win_percentage": round(rec.win_percentage, 4),
        "point_differential": round(rec.point_differential, 2),
        "avg_opi": round(rec.avg_opi, 2),
        "avg_territory": round(rec.avg_territory, 2),
        "avg_pressure": round(rec.avg_pressure, 2),
        "avg_chaos": round(rec.avg_chaos, 2),
        "avg_kicking": round(rec.avg_kicking, 2),
        "conf_wins": rec.conf_wins,
        "conf_losses": rec.conf_losses,
        "conf_win_percentage": round(rec.conf_win_percentage, 4),
        "avg_drive_quality": round(getattr(rec, 'avg_drive_quality', 0), 2),
        "avg_turnover_impact": round(getattr(rec, 'avg_turnover_impact', 0), 2),
        "offense_style": getattr(rec, 'offense_style', ''),
        "defense_style": getattr(rec, 'defense_style', ''),
    }


def _serialize_game(game: Game, include_full_result: bool = False) -> dict:
    d = {
        "week": game.week,
        "home_team": game.home_team,
        "away_team": game.away_team,
        "home_score": game.home_score,
        "away_score": game.away_score,
        "completed": game.completed,
        "is_conference_game": game.is_conference_game,
        "home_metrics": game.home_metrics if hasattr(game, 'home_metrics') else None,
        "away_metrics": game.away_metrics if hasattr(game, 'away_metrics') else None,
        "has_full_result": bool(getattr(game, 'full_result', None)),
    }
    if include_full_result and getattr(game, 'full_result', None):
        d["full_result"] = game.full_result
    return d


def _serialize_poll(poll: WeeklyPoll) -> dict:
    rankings = []
    for r in poll.rankings:
        rankings.append({
            "rank": r.rank,
            "team_name": r.team_name,
            "record": r.record,
            "conference": r.conference,
            "poll_score": r.poll_score,
            "prev_rank": r.prev_rank,
            "rank_change": r.rank_change,
            "power_index": r.power_index,
            "quality_wins": r.quality_wins,
            "sos_rank": r.sos_rank,
            "bid_type": r.bid_type,
        })
    return {"week": poll.week, "rankings": rankings}


def _serialize_standings(season: Season) -> list:
    sorted_standings = season.get_standings_sorted()
    return [_serialize_team_record(rec) for rec in sorted_standings]


def _serialize_schedule(season: Season) -> list:
    return [_serialize_game(g) for g in season.schedule]


def _serialize_season_status(session: dict) -> dict:
    season = session.get("season")
    if season is None:
        return {"phase": session.get("phase", "setup"), "season_active": False}

    total_games = len(season.schedule)
    games_played = sum(1 for g in season.schedule if g.completed)
    total_weeks = season.get_total_weeks()
    current_week = season.get_last_completed_week()
    next_week = season.get_next_unplayed_week()
    progress_pct = round(games_played / total_games * 100, 1) if total_games > 0 else 0.0

    return {
        "phase": session.get("phase", "setup"),
        "current_week": current_week,
        "next_week": next_week,
        "total_weeks": total_weeks,
        "games_played": games_played,
        "total_games": total_games,
        "progress_pct": progress_pct,
        "champion": season.champion,
        "name": season.name,
        "team_count": len(season.teams),
    }


def _serialize_dynasty_status(session: dict) -> dict:
    dynasty = session.get("dynasty")
    if dynasty is None:
        return {"dynasty_active": False}

    coach = dynasty.coach
    team_count = len(dynasty.team_histories)
    seasons_played = len(dynasty.seasons)

    return {
        "dynasty_name": dynasty.dynasty_name,
        "current_year": dynasty.current_year,
        "coach": {
            "name": coach.name,
            "team": coach.team_name,
            "career_wins": coach.career_wins,
            "career_losses": coach.career_losses,
            "win_percentage": round(coach.win_percentage, 4),
            "championships": coach.championships,
            "playoff_appearances": coach.playoff_appearances,
            "years_coached": len(coach.years_coached),
        },
        "team_count": team_count,
        "seasons_played": seasons_played,
        "phase": session.get("phase", "setup"),
    }


def _serialize_player(player) -> dict:
    return {
        "name": player.name,
        "number": player.number,
        "position": player.position,
        "archetype": player.archetype,
        "overall": player.overall,
        "speed": player.speed,
        "power": player.power,
        "agility": player.agility,
        "hands": player.hands,
        "awareness": player.awareness,
        "stamina": player.stamina,
        "kicking": player.kicking,
        "kick_power": player.kick_power,
        "kick_accuracy": player.kick_accuracy,
        "lateral_skill": player.lateral_skill,
        "tackling": player.tackling,
        "year": getattr(player, "year", ""),
        "height": getattr(player, "height", ""),
        "weight": getattr(player, "weight", 0),
    }


@app.get("/health")
def health():
    return {"status": "ok", "sessions_active": len(sessions)}


@app.get("/teams")
def list_teams():
    teams = get_available_teams()
    styles = get_available_styles()
    return {"teams": teams, "styles": styles}


@app.get("/styles")
def list_styles():
    offense_styles = {}
    for key, val in OFFENSE_STYLES.items():
        offense_styles[key] = {"label": val.get("label", key), "description": val.get("description", "")}
    defense_styles = {}
    for key, val in DEFENSE_STYLES.items():
        defense_styles[key] = {"label": val.get("label", key), "description": val.get("description", "")}
    return {"offense_styles": offense_styles, "defense_styles": defense_styles}


@app.get("/weather-conditions")
def list_weather():
    conditions = []
    for key, val in WEATHER_CONDITIONS.items():
        conditions.append({"key": key, "label": val.get("label", key), "description": val.get("description", "")})
    return {"conditions": conditions}


@app.get("/conference-defaults")
def conference_defaults():
    teams = load_teams_from_directory(TEAMS_DIR)
    team_names = list(teams.keys())
    defaults = get_geographic_conference_defaults(TEAMS_DIR, team_names, 10)
    return {"conferences": defaults}


@app.get("/bowl-tiers")
def bowl_tiers():
    return {"tiers": BOWL_TIERS}


@app.post("/simulate")
def simulate(req: SimulateRequest):
    home_team = _load_team(req.home)
    away_team = _load_team(req.away)
    engine = ViperballEngine(home_team, away_team, seed=req.seed, style_overrides=req.styles, weather=req.weather)
    result = engine.simulate_game()
    return result


@app.post("/simulate_many")
def simulate_many(req: SimulateManyRequest):
    results = []
    for i in range(req.count):
        home_team = _load_team(req.home)
        away_team = _load_team(req.away)
        game_seed = (req.seed + i) if req.seed is not None else None
        engine = ViperballEngine(home_team, away_team, seed=game_seed, style_overrides=req.styles, weather=req.weather)
        result = engine.simulate_game()
        results.append(result)

    home_scores = [r["final_score"]["home"]["score"] for r in results]
    away_scores = [r["final_score"]["away"]["score"] for r in results]
    home_wins = sum(1 for h, a in zip(home_scores, away_scores) if h > a)
    away_wins = sum(1 for h, a in zip(home_scores, away_scores) if a > h)
    ties = req.count - home_wins - away_wins

    home_yards = [r["stats"]["home"]["total_yards"] for r in results]
    away_yards = [r["stats"]["away"]["total_yards"] for r in results]
    home_tds = [r["stats"]["home"]["touchdowns"] for r in results]
    away_tds = [r["stats"]["away"]["touchdowns"] for r in results]
    home_fumbles = [r["stats"]["home"]["fumbles_lost"] for r in results]
    away_fumbles = [r["stats"]["away"]["fumbles_lost"] for r in results]
    home_fatigue = [r["stats"]["home"]["avg_fatigue"] for r in results]
    away_fatigue = [r["stats"]["away"]["avg_fatigue"] for r in results]

    summary = {
        "games_played": req.count,
        "home_team": results[0]["final_score"]["home"]["team"],
        "away_team": results[0]["final_score"]["away"]["team"],
        "record": {"home_wins": home_wins, "away_wins": away_wins, "ties": ties},
        "averages": {
            "home_score": round(sum(home_scores) / req.count, 1),
            "away_score": round(sum(away_scores) / req.count, 1),
            "home_yards": round(sum(home_yards) / req.count, 1),
            "away_yards": round(sum(away_yards) / req.count, 1),
            "home_tds": round(sum(home_tds) / req.count, 2),
            "away_tds": round(sum(away_tds) / req.count, 2),
            "home_fumbles": round(sum(home_fumbles) / req.count, 2),
            "away_fumbles": round(sum(away_fumbles) / req.count, 2),
            "home_fatigue": round(sum(home_fatigue) / req.count, 1),
            "away_fatigue": round(sum(away_fatigue) / req.count, 1),
        },
        "score_distribution": {
            "home_scores": home_scores,
            "away_scores": away_scores,
        },
    }

    return summary


@app.post("/debug/play")
def debug_play(req: DebugPlayRequest):
    teams = get_available_teams()
    if not teams:
        return {"error": "No teams available"}
    home_team = _load_team(teams[0]["key"])
    away_team = _load_team(teams[1]["key"] if len(teams) > 1 else teams[0]["key"])
    engine = ViperballEngine(home_team, away_team, seed=None)
    result = engine.simulate_single_play(
        style=req.style,
        field_position=req.field_position,
        down=req.down,
        yards_to_go=req.yards_to_go,
    )
    return result


@app.post("/sessions")
def create_session():
    session_id = str(uuid.uuid4())
    now = time.time()
    sessions[session_id] = {
        "season": None,
        "dynasty": None,
        "injury_tracker": None,
        "phase": "setup",
        "config": {},
        "created_at": now,
    }
    return {"session_id": session_id, "created_at": now}


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    del sessions[session_id]
    return {"deleted": True}


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    session = _get_session(session_id)
    result = {
        "session_id": session_id,
        "phase": session["phase"],
        "created_at": session["created_at"],
        "has_season": session["season"] is not None,
        "has_dynasty": session["dynasty"] is not None,
    }
    if session["season"] is not None:
        result["season_status"] = _serialize_season_status(session)
    if session["dynasty"] is not None:
        result["dynasty_status"] = _serialize_dynasty_status(session)
    return result


@app.post("/sessions/{session_id}/season")
def create_season_endpoint(session_id: str, req: CreateSeasonRequest):
    session = _get_session(session_id)

    teams, team_states = load_teams_with_states(TEAMS_DIR)
    team_names = list(teams.keys())

    if req.conferences:
        conferences = req.conferences
    else:
        conferences = get_geographic_conference_defaults(TEAMS_DIR, team_names, req.num_conferences)

    if req.style_configs:
        style_configs = req.style_configs
    else:
        ai_configs = auto_assign_all_teams(
            TEAMS_DIR,
            human_teams=req.human_teams,
            human_configs=req.human_configs,
            seed=req.ai_seed if req.ai_seed else None,
        )

        style_configs = {}
        for tname in teams:
            style_configs[tname] = ai_configs.get(
                tname, {"offense_style": "balanced", "defense_style": "base_defense"}
            )

    season = create_season(
        req.name,
        teams,
        style_configs,
        conferences=conferences,
        games_per_team=req.games_per_team,
        team_states=team_states,
    )

    session["season"] = season
    session["phase"] = "regular"
    session["config"] = {
        "playoff_size": req.playoff_size,
        "bowl_count": req.bowl_count,
        "games_per_team": req.games_per_team,
    }
    session["injury_tracker"] = InjuryTracker()

    return _serialize_season_status(session)


@app.post("/sessions/{session_id}/season/simulate-week")
def simulate_week(session_id: str, req: SimulateWeekRequest):
    session = _get_session(session_id)
    season = _require_season(session)

    if session["phase"] not in ("regular",):
        raise HTTPException(status_code=400, detail=f"Cannot simulate week in phase '{session['phase']}'")

    week = req.week
    games = season.simulate_week(week=week)

    if not games:
        return {"week": week, "games": [], "message": "No games to simulate"}

    actual_week = games[0].week

    tracker = session.get("injury_tracker")
    if tracker:
        tracker.process_week(actual_week, season.teams, season.standings)
        tracker.resolve_week(actual_week)

    if season.is_regular_season_complete():
        session["phase"] = "playoffs_pending"

    return {
        "week": actual_week,
        "games": [_serialize_game(g) for g in games],
        "games_count": len(games),
        "season_complete": season.is_regular_season_complete(),
        "phase": session["phase"],
    }


@app.post("/sessions/{session_id}/season/simulate-through")
def simulate_through(session_id: str, req: SimulateThroughRequest):
    session = _get_session(session_id)
    season = _require_season(session)

    if session["phase"] not in ("regular",):
        raise HTTPException(status_code=400, detail=f"Cannot simulate in phase '{session['phase']}'")

    all_games = season.simulate_through_week(req.target_week)

    tracker = session.get("injury_tracker")
    if tracker and all_games:
        weeks_simmed = sorted(set(g.week for g in all_games))
        for wk in weeks_simmed:
            tracker.process_week(wk, season.teams, season.standings)
            tracker.resolve_week(wk)

    if season.is_regular_season_complete():
        session["phase"] = "playoffs_pending"

    return {
        "games": [_serialize_game(g) for g in all_games],
        "games_count": len(all_games),
        "season_complete": season.is_regular_season_complete(),
        "phase": session["phase"],
    }


@app.post("/sessions/{session_id}/season/simulate-rest")
def simulate_rest(session_id: str):
    session = _get_session(session_id)
    season = _require_season(session)

    if session["phase"] not in ("regular",):
        raise HTTPException(status_code=400, detail=f"Cannot simulate rest in phase '{session['phase']}'")

    games_before = sum(1 for g in season.schedule if g.completed)
    season.simulate_season(generate_polls=True)
    games_after = sum(1 for g in season.schedule if g.completed)

    tracker = session.get("injury_tracker")
    if tracker:
        max_week = max((g.week for g in season.schedule if g.completed), default=0)
        for wk in range(1, max_week + 1):
            tracker.process_week(wk, season.teams, season.standings)
            tracker.resolve_week(wk)

    session["phase"] = "playoffs_pending"

    return {
        "games_simulated": games_after - games_before,
        "total_games": len(season.schedule),
        "phase": session["phase"],
        "status": _serialize_season_status(session),
    }


@app.post("/sessions/{session_id}/season/playoffs")
def run_playoffs(session_id: str):
    session = _get_session(session_id)
    season = _require_season(session)

    if session["phase"] not in ("playoffs_pending",):
        raise HTTPException(status_code=400, detail=f"Cannot run playoffs in phase '{session['phase']}'")

    playoff_size = session["config"].get("playoff_size", 8)
    effective_size = min(playoff_size, len(season.teams))
    if effective_size < 4:
        raise HTTPException(status_code=400, detail="Not enough teams for playoffs")

    season.simulate_playoff(num_teams=effective_size)

    bowl_count = session["config"].get("bowl_count", 4)
    if bowl_count > 0:
        session["phase"] = "bowls_pending"
    else:
        session["phase"] = "complete"

    bracket = [_serialize_game(g) for g in season.playoff_bracket]
    return {
        "champion": season.champion,
        "bracket": bracket,
        "phase": session["phase"],
    }


@app.post("/sessions/{session_id}/season/bowls")
def run_bowls(session_id: str):
    session = _get_session(session_id)
    season = _require_season(session)

    if session["phase"] not in ("bowls_pending",):
        raise HTTPException(status_code=400, detail=f"Cannot run bowls in phase '{session['phase']}'")

    bowl_count = session["config"].get("bowl_count", 4)
    playoff_size = session["config"].get("playoff_size", 8)
    season.simulate_bowls(bowl_count=bowl_count, playoff_size=playoff_size)

    session["phase"] = "complete"

    bowl_results = []
    for bg in season.bowl_games:
        bowl_results.append({
            "name": bg.name,
            "tier": bg.tier,
            "game": _serialize_game(bg.game),
            "team_1_seed": bg.team_1_seed,
            "team_2_seed": bg.team_2_seed,
            "team_1_record": bg.team_1_record,
            "team_2_record": bg.team_2_record,
        })

    return {"bowl_results": bowl_results, "phase": session["phase"]}


@app.get("/sessions/{session_id}/season/status")
def season_status(session_id: str):
    session = _get_session(session_id)
    _require_season(session)
    return _serialize_season_status(session)


@app.get("/sessions/{session_id}/season/standings")
def season_standings(session_id: str):
    session = _get_session(session_id)
    season = _require_season(session)
    return {"standings": _serialize_standings(season)}


@app.get("/sessions/{session_id}/season/schedule")
def season_schedule(
    session_id: str,
    week: Optional[int] = Query(None),
    team: Optional[str] = Query(None),
    completed_only: bool = Query(False),
    include_full_result: bool = Query(False),
):
    session = _get_session(session_id)
    season = _require_season(session)

    games = season.schedule
    if week is not None:
        games = [g for g in games if g.week == week]
    if team is not None:
        games = [g for g in games if g.home_team == team or g.away_team == team]
    if completed_only:
        games = [g for g in games if g.completed]

    return {"games": [_serialize_game(g, include_full_result=include_full_result) for g in games], "count": len(games)}


@app.get("/sessions/{session_id}/season/polls")
def season_polls(session_id: str, week: Optional[int] = Query(None)):
    session = _get_session(session_id)
    season = _require_season(session)

    polls = season.weekly_polls
    if week is not None:
        polls = [p for p in polls if p.week == week]

    return {"polls": [_serialize_poll(p) for p in polls]}


@app.get("/sessions/{session_id}/season/conferences")
def season_conferences(session_id: str):
    session = _get_session(session_id)
    season = _require_season(session)

    conf_data = {}
    for conf_name, conf_teams in season.conferences.items():
        conf_standings = season.get_conference_standings(conf_name)
        conf_data[conf_name] = {
            "teams": conf_teams,
            "standings": [_serialize_team_record(r) for r in conf_standings],
        }

    champions = season.get_conference_champions()

    return {"conferences": conf_data, "champions": champions}


@app.get("/sessions/{session_id}/season/power-rankings")
def power_rankings(session_id: str):
    session = _get_session(session_id)
    season = _require_season(session)

    rankings = season.get_all_power_rankings()
    result = []
    for rank, (team_name, power_index, quality_wins) in enumerate(rankings, 1):
        result.append({
            "rank": rank,
            "team_name": team_name,
            "power_index": round(power_index, 2),
            "quality_wins": quality_wins,
        })

    return {"rankings": result}


@app.get("/sessions/{session_id}/season/playoff-bracket")
def playoff_bracket(session_id: str):
    session = _get_session(session_id)
    season = _require_season(session)

    if not season.playoff_bracket:
        return {"bracket": [], "champion": None, "message": "Playoffs have not been run yet"}

    return {
        "bracket": [_serialize_game(g, include_full_result=True) for g in season.playoff_bracket],
        "champion": season.champion,
    }


@app.get("/sessions/{session_id}/season/bowl-results")
def bowl_results(session_id: str):
    session = _get_session(session_id)
    season = _require_season(session)

    if not season.bowl_games:
        return {"bowl_results": [], "message": "Bowl games have not been run yet"}

    results = []
    for bg in season.bowl_games:
        results.append({
            "name": bg.name,
            "tier": bg.tier,
            "game": _serialize_game(bg.game, include_full_result=True),
            "team_1_seed": bg.team_1_seed,
            "team_2_seed": bg.team_2_seed,
            "team_1_record": bg.team_1_record,
            "team_2_record": bg.team_2_record,
        })

    return {"bowl_results": results}


@app.get("/sessions/{session_id}/season/awards")
def season_awards(session_id: str):
    session = _get_session(session_id)
    season = _require_season(session)

    try:
        season_honors = compute_season_awards(
            season, year=2025,
            conferences=season.conferences if hasattr(season, 'conferences') else None,
        )
        result = {"individual_awards": [], "coach_of_year": None, "most_improved": None}
        if season_honors.individual_awards:
            for a in season_honors.individual_awards:
                result["individual_awards"].append({
                    "award_name": a.award_name,
                    "player_name": a.player_name,
                    "position": a.position,
                    "team_name": a.team_name,
                    "overall_rating": a.overall_rating,
                })
        result["coach_of_year"] = season_honors.coach_of_year
        result["most_improved"] = season_honors.most_improved
        return result
    except Exception as e:
        return {"individual_awards": [], "coach_of_year": None, "most_improved": None, "error": str(e)}


@app.post("/sessions/{session_id}/dynasty")
def create_dynasty_endpoint(session_id: str, req: CreateDynastyRequest):
    session = _get_session(session_id)

    teams = load_teams_from_directory(TEAMS_DIR)
    team_names = list(teams.keys())

    if req.coach_team not in teams:
        raise HTTPException(status_code=400, detail=f"Team '{req.coach_team}' not found")

    dynasty = create_dynasty(
        dynasty_name=req.dynasty_name,
        coach_name=req.coach_name,
        coach_team=req.coach_team,
        starting_year=req.starting_year,
    )

    conferences = get_geographic_conference_defaults(TEAMS_DIR, team_names, req.num_conferences)
    for conf_name, conf_teams in conferences.items():
        dynasty.add_conference(conf_name, conf_teams)

    if req.history_years > 0:
        dynasty.simulate_history(
            num_years=req.history_years,
            teams_dir=TEAMS_DIR,
            games_per_team=10,
            playoff_size=8,
        )

    session["dynasty"] = dynasty
    session["phase"] = "setup"
    session["injury_tracker"] = None
    session["season"] = None

    return _serialize_dynasty_status(session)


@app.post("/sessions/{session_id}/dynasty/start-season")
def dynasty_start_season(session_id: str, req: DynastyStartSeasonRequest):
    session = _get_session(session_id)
    dynasty = _require_dynasty(session)

    if session["phase"] not in ("setup", "finalize"):
        raise HTTPException(status_code=400, detail=f"Cannot start season in phase '{session['phase']}'")

    teams, team_states = load_teams_with_states(TEAMS_DIR)

    seed = req.ai_seed if req.ai_seed is not None else random.randint(0, 999999)
    ai_configs = auto_assign_all_teams(
        TEAMS_DIR,
        human_teams=[dynasty.coach.team_name],
        human_configs={
            dynasty.coach.team_name: {
                "offense_style": req.offense_style,
                "defense_style": req.defense_style,
            }
        },
        seed=seed,
    )

    style_configs = {}
    for tname in teams:
        style_configs[tname] = ai_configs.get(
            tname, {"offense_style": "balanced", "defense_style": "base_defense"}
        )

    conf_dict = dynasty.get_conferences_dict()
    season = create_season(
        f"{dynasty.current_year} CVL Season",
        teams,
        style_configs,
        conferences=conf_dict,
        games_per_team=req.games_per_team,
        team_states=team_states,
    )

    session["season"] = season
    session["phase"] = "regular"
    session["config"] = {
        "playoff_size": req.playoff_size,
        "bowl_count": req.bowl_count,
        "games_per_team": req.games_per_team,
    }
    session["injury_tracker"] = InjuryTracker()

    return _serialize_season_status(session)


@app.post("/sessions/{session_id}/dynasty/advance")
def dynasty_advance(session_id: str):
    session = _get_session(session_id)
    dynasty = _require_dynasty(session)
    season = _require_season(session)

    if session["phase"] not in ("complete",):
        raise HTTPException(status_code=400, detail=f"Cannot advance dynasty in phase '{session['phase']}'. Season must be complete.")

    player_cards = {}
    for t_name, t_obj in season.teams.items():
        player_cards[t_name] = [player_to_card(p, t_name) for p in t_obj.players]

    tracker = session.get("injury_tracker")
    dynasty.advance_season(season, injury_tracker=tracker, player_cards=player_cards)

    session["season"] = None
    session["injury_tracker"] = None
    session["phase"] = "setup"

    return _serialize_dynasty_status(session)


@app.get("/sessions/{session_id}/dynasty/status")
def dynasty_status(session_id: str):
    session = _get_session(session_id)
    _require_dynasty(session)
    return _serialize_dynasty_status(session)


@app.get("/sessions/{session_id}/dynasty/team-histories")
def dynasty_team_histories(session_id: str):
    session = _get_session(session_id)
    dynasty = _require_dynasty(session)

    histories = {}
    for team_name, history in dynasty.team_histories.items():
        histories[team_name] = {
            "team_name": history.team_name,
            "total_wins": history.total_wins,
            "total_losses": history.total_losses,
            "total_championships": history.total_championships,
            "total_playoff_appearances": history.total_playoff_appearances,
            "total_points_for": round(history.total_points_for, 1),
            "total_points_against": round(history.total_points_against, 1),
            "win_percentage": round(history.win_percentage, 4),
            "best_season_wins": history.best_season_wins,
            "best_season_year": history.best_season_year,
            "championship_years": history.championship_years,
            "season_records": history.season_records,
        }

    return {"team_histories": histories}


@app.get("/sessions/{session_id}/dynasty/awards")
def dynasty_awards(session_id: str):
    session = _get_session(session_id)
    dynasty = _require_dynasty(session)

    awards = {}
    for year, award in dynasty.awards_history.items():
        awards[year] = {
            "year": award.year,
            "champion": award.champion,
            "best_record": award.best_record,
            "highest_scoring": award.highest_scoring,
            "best_defense": award.best_defense,
            "highest_opi": award.highest_opi,
            "most_chaos": award.most_chaos,
            "best_kicking": award.best_kicking,
            "coach_of_year": award.coach_of_year,
            "most_improved": award.most_improved,
            "honors": award.honors,
        }

    return {"awards_history": awards}


@app.get("/sessions/{session_id}/dynasty/record-book")
def dynasty_record_book(session_id: str):
    session = _get_session(session_id)
    dynasty = _require_dynasty(session)

    rb = dynasty.record_book
    return {
        "record_book": {
            "most_wins_season": rb.most_wins_season,
            "most_points_season": rb.most_points_season,
            "best_defense_season": rb.best_defense_season,
            "highest_opi_season": rb.highest_opi_season,
            "most_chaos_season": rb.most_chaos_season,
            "most_championships": rb.most_championships,
            "highest_win_percentage": rb.highest_win_percentage,
            "most_coaching_wins": rb.most_coaching_wins,
            "most_coaching_championships": rb.most_coaching_championships,
        }
    }


@app.get("/sessions/{session_id}/team/{team_name}")
def team_roster(session_id: str, team_name: str):
    session = _get_session(session_id)
    season = _require_season(session)

    if team_name not in season.teams:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")

    team = season.teams[team_name]
    players = [_serialize_player(p) for p in team.players]

    record = season.standings.get(team_name)
    team_record = _serialize_team_record(record) if record else None

    return {
        "team_name": team.name,
        "abbreviation": team.abbreviation,
        "mascot": team.mascot,
        "players": players,
        "record": team_record,
    }


@app.get("/sessions/{session_id}/team/{team_name}/schedule")
def team_schedule(session_id: str, team_name: str):
    session = _get_session(session_id)
    season = _require_season(session)

    if team_name not in season.teams:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")

    games = [g for g in season.schedule if g.home_team == team_name or g.away_team == team_name]
    return {"team": team_name, "games": [_serialize_game(g) for g in games], "count": len(games)}
