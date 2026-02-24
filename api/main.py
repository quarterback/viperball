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
    load_teams_from_directory, load_teams_with_states, create_season, get_recommended_bowl_count, BOWL_TIERS,
    get_non_conference_slots, get_available_non_conference_opponents,
    estimate_team_prestige_from_roster, is_buy_game, BUY_GAME_NIL_BONUS,
    MAX_CONFERENCE_GAMES,
    auto_assign_rivalries,
    load_coaching_staffs_from_directory,
    fast_generate_history,
)
from engine.dynasty import create_dynasty, Dynasty
from engine.conference_names import generate_conference_names
from engine.geography import get_geographic_conference_defaults
from engine.injuries import InjuryTracker
from engine.awards import compute_season_awards
from engine.player_card import player_to_card
from engine.ai_coach import auto_assign_all_teams, get_scheme_label, load_team_identity
from engine.game_engine import WEATHER_CONDITIONS, DEFENSE_STYLES, POSITION_TAGS, ST_SCHEMES
from scripts.generate_rosters import PROGRAM_ARCHETYPES
from engine.game_engine import WEATHER_CONDITIONS, DEFENSE_STYLES, POSITION_TAGS, Player, assign_archetype, ST_SCHEMES
from engine.nil_system import (
    NILProgram, NILDeal, auto_nil_program, generate_nil_budget,
    assess_retention_risks, estimate_market_tier, compute_team_prestige,
)
from engine.recruiting import (
    generate_recruit_class, RecruitingBoard, Recruit,
    run_full_recruiting_cycle, auto_recruit_team, simulate_recruit_decisions,
    scout_recruit,
)
from engine.transfer_portal import (
    TransferPortal, PortalEntry, populate_portal,
    auto_portal_offers, generate_quick_portal,
    estimate_prestige_from_roster,
)
from engine.draftyqueenz import (
    DraftyQueenzManager, DONATION_TYPES, BOOSTER_TIERS,
    STARTING_BANKROLL, SALARY_CAP, FANTASY_ENTRY_FEE,
    MIN_BET, MAX_BET, MIN_DONATION, PARLAY_MULTIPLIERS,
    POSITION_NAMES, SLOT_LABELS,
    format_moneyline,
)


app = FastAPI(title="Viperball Simulation API", version="1.0.0")

TEAMS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams")

sessions: Dict[str, dict] = {}


@app.get("/api/health")
def health_check():
    """Health check endpoint for Fly.io deployment monitoring."""
    team_count = len(get_available_teams())
    return {"status": "ok", "teams": team_count}


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
    games_per_team: int = 12
    playoff_size: int = 8
    bowl_count: int = 4
    human_teams: List[str] = []
    human_configs: Dict[str, Dict[str, str]] = {}
    num_conferences: int = 10
    ai_seed: int = 0
    conferences: Optional[Dict[str, List[str]]] = None
    style_configs: Optional[Dict[str, Dict[str, str]]] = None
    history_years: int = 0
    pinned_matchups: Optional[List[List[str]]] = None  # [[home, away], ...]
    team_archetypes: Optional[Dict[str, str]] = None  # team_name -> archetype key
    rivalries: Optional[Dict[str, Dict[str, Optional[str]]]] = None


class CreateDynastyRequest(BaseModel):
    dynasty_name: str = "My Viperball Dynasty"
    coach_name: str = "Coach"
    coach_team: str
    starting_year: int = 2026
    num_conferences: int = 10
    history_years: int = 0
    program_archetype: Optional[str] = None  # archetype for coach's team
    rivalries: Optional[Dict[str, Dict[str, Optional[str]]]] = None


class SimulateWeekRequest(BaseModel):
    week: Optional[int] = None


class SimulateThroughRequest(BaseModel):
    target_week: int


class DynastyStartSeasonRequest(BaseModel):
    games_per_team: int = 12
    playoff_size: int = 8
    bowl_count: int = 4
    offense_style: str = "balanced"
    defense_style: str = "swarm"
    st_scheme: str = "aces"
    ai_seed: Optional[int] = None
    pinned_matchups: Optional[List[List[str]]] = None  # [[home, away], ...]
    program_archetype: Optional[str] = None  # archetype for human team
    rivalries: Optional[Dict[str, Dict[str, Optional[str]]]] = None


class QuickGameRequest(BaseModel):
    home: str
    away: str
    home_offense: str = "balanced"
    home_defense: str = "swarm"
    home_st: str = "aces"
    away_offense: str = "balanced"
    away_defense: str = "swarm"
    away_st: str = "aces"
    weather: str = "clear"
    seed: Optional[int] = None


class NILAllocateRequest(BaseModel):
    recruiting_pool: float
    portal_pool: float
    retention_pool: float

class NILDealRequest(BaseModel):
    pool: str
    player_id: str
    player_name: str
    amount: float

class PortalOfferRequest(BaseModel):
    entry_index: int
    nil_amount: float = 0.0

class PortalCommitRequest(BaseModel):
    entry_index: int

class SetRivalriesRequest(BaseModel):
    team: str
    conference_rival: Optional[str] = None
    non_conference_rival: Optional[str] = None

class SeasonPortalGenerateRequest(BaseModel):
    size: int = 40
    human_team: str = ""

class SeasonPortalCommitRequest(BaseModel):
    team_name: str
    entry_index: int

class ScoutRequest(BaseModel):
    recruit_index: int
    level: str = "basic"

class RecruitOfferRequest(BaseModel):
    recruit_index: int

class OffseasonStartRequest(BaseModel):
    pool_size: int = 300


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
        "is_rivalry_game": getattr(game, 'is_rivalry_game', False),
        "is_fcs_game": getattr(game, 'is_fcs_game', False),
        "home_metrics": game.home_metrics if hasattr(game, 'home_metrics') else None,
        "away_metrics": game.away_metrics if hasattr(game, 'away_metrics') else None,
        "has_full_result": bool(getattr(game, 'full_result', None)),
    }
    if include_full_result and getattr(game, 'full_result', None):
        d["full_result"] = game.full_result
    return d


def _serialize_poll(poll: WeeklyPoll, prestige_map: Optional[dict] = None) -> dict:
    rankings = []
    for r in poll.rankings:
        entry = {
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
        }
        if prestige_map:
            entry["prestige"] = prestige_map.get(r.team_name)
        rankings.append(entry)
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

    conf_dict = dynasty.get_conferences_dict() if dynasty.conferences else {}

    sr = {}
    for yr, rec in coach.season_records.items():
        sr[str(yr)] = {
            "wins": rec.get("wins", 0),
            "losses": rec.get("losses", 0),
            "points_for": rec.get("points_for", 0),
            "points_against": rec.get("points_against", 0),
            "playoff": rec.get("playoff", False),
            "champion": rec.get("champion", False),
        }

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
            "years_experience": coach.years_experience,
            "season_records": sr,
        },
        "team_count": team_count,
        "seasons_played": seasons_played,
        "phase": session.get("phase", "setup"),
        "conferences": conf_dict,
    }


_YEAR_ABBREV = {
    "Freshman": "Fr.", "Sophomore": "So.", "Junior": "Jr.",
    "Senior": "Sr.", "Graduate": "Gr.",
    "freshman": "Fr.", "sophomore": "So.", "junior": "Jr.",
    "senior": "Sr.", "graduate": "Gr.",
}


def _serialize_player(player) -> dict:
    year_full = getattr(player, "year", "")
    year_abbr = _YEAR_ABBREV.get(year_full, year_full[:2] + "." if year_full else "")
    redshirt = getattr(player, "redshirt", False)
    if redshirt:
        year_abbr = f"RS {year_abbr}"
    pos_tag = POSITION_TAGS.get(player.position, player.position[:2].upper() if player.position else "??")
    return {
        "name": player.name,
        "number": player.number,
        "position": pos_tag,
        "position_full": player.position,
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
        "year": year_full,
        "year_abbr": year_abbr,
        "redshirt": redshirt,
        "season_games_played": getattr(player, "season_games_played", 0),
        "height": getattr(player, "height", ""),
        "weight": getattr(player, "weight", 0),
        "hometown_city": getattr(player, "hometown_city", ""),
        "hometown_state": getattr(player, "hometown_state", ""),
        "hometown_country": getattr(player, "hometown_country", "USA"),
        "nationality": getattr(player, "nationality", "American"),
        "potential": getattr(player, "potential", 3),
        "development": getattr(player, "development", "normal"),
        "career_awards": getattr(player, "career_awards", []),
        "career_seasons": getattr(player, "career_seasons", []),
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
    st_schemes = {}
    for key, val in ST_SCHEMES.items():
        st_schemes[key] = {"label": val.get("label", key), "description": val.get("description", "")}
    return {"offense_styles": offense_styles, "defense_styles": defense_styles, "st_schemes": st_schemes}


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


@app.get("/non-conference-opponents")
def non_conference_opponents(
    team: str = Query(..., description="Team name to get opponents for"),
    conferences: Optional[str] = Query(None, description="JSON-encoded conference dict"),
    num_conferences: int = Query(10, description="Number of conferences if no explicit dict"),
):
    """Get available non-conference opponents for a team, grouped by prestige tier."""
    all_teams = load_teams_from_directory(TEAMS_DIR)
    team_names = sorted(all_teams.keys())

    if team not in all_teams:
        raise HTTPException(status_code=404, detail=f"Team '{team}' not found")

    if conferences:
        import json as _json
        try:
            conf_dict = _json.loads(conferences)
        except Exception:
            conf_dict = get_geographic_conference_defaults(TEAMS_DIR, team_names, num_conferences)
    else:
        conf_dict = get_geographic_conference_defaults(TEAMS_DIR, team_names, num_conferences)

    team_conf_map = {}
    for conf_name, conf_teams in conf_dict.items():
        for t in conf_teams:
            team_conf_map[t] = conf_name

    opponents = get_available_non_conference_opponents(
        team_name=team,
        all_teams=all_teams,
        conferences=conf_dict,
        team_conferences=team_conf_map,
    )

    my_conf = team_conf_map.get(team, "")
    my_conf_size = 0
    for conf_name, conf_teams in conf_dict.items():
        if team in conf_teams:
            my_conf_size = len(conf_teams)
            break

    return {
        "team": team,
        "conference": my_conf,
        "conference_size": my_conf_size,
        "opponents": opponents,
        "total_opponents": len(opponents),
    }


@app.get("/non-conference-slots")
def non_conference_slots_endpoint(
    games_per_team: int = Query(12),
    conference_size: int = Query(12),
):
    """Calculate how many non-conference slots a team has given league settings."""
    slots = get_non_conference_slots(games_per_team, conference_size)
    conf_games = min(conference_size - 1, MAX_CONFERENCE_GAMES)
    return {
        "non_conference_slots": slots,
        "conference_games": conf_games,
        "total_games": games_per_team,
        "max_conference_games": MAX_CONFERENCE_GAMES,
    }


@app.get("/program-archetypes")
def program_archetypes():
    """List all available program archetypes with descriptions."""
    return {
        "archetypes": {
            key: {
                "label": data["label"],
                "description": data["description"],
                "prestige_range": data["prestige_range"],
            }
            for key, data in PROGRAM_ARCHETYPES.items()
        }
    }


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
        "dq_manager": None,
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
        "has_dq": session.get("dq_manager") is not None,
    }
    if session["season"] is not None:
        result["season_status"] = _serialize_season_status(session)
    if session["dynasty"] is not None:
        result["dynasty_status"] = _serialize_dynasty_status(session)
    return result


@app.post("/sessions/{session_id}/season")
def create_season_endpoint(session_id: str, req: CreateSeasonRequest):
    session = _get_session(session_id)

    teams, team_states = load_teams_with_states(
        TEAMS_DIR, fresh=True,
        team_archetypes=req.team_archetypes,
    )
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
                tname, {"offense_style": "balanced", "defense_style": "swarm", "st_scheme": "aces"}
            )

    pinned = None
    if req.pinned_matchups:
        pinned = [(pair[0], pair[1]) for pair in req.pinned_matchups if len(pair) == 2]

    rivalries_dict = auto_assign_rivalries(
        conferences=conferences,
        team_states=team_states,
        human_team=req.human_teams[0] if req.human_teams else None,
        existing_rivalries=req.rivalries,
    )

    coaching_staffs = load_coaching_staffs_from_directory(TEAMS_DIR)

    season = create_season(
        req.name,
        teams,
        style_configs,
        conferences=conferences,
        games_per_team=req.games_per_team,
        team_states=team_states,
        pinned_matchups=pinned,
        rivalries=rivalries_dict,
        coaching_staffs=coaching_staffs,
    )

    history_results = []
    history_years = max(0, min(100, req.history_years))
    if history_years > 0:
        history_results = fast_generate_history(
            teams=teams,
            conferences=conferences,
            num_years=history_years,
            games_per_team=req.games_per_team,
            playoff_size=req.playoff_size,
            base_seed=req.ai_seed if req.ai_seed else 42,
        )

    session["season"] = season
    session["human_teams"] = req.human_teams or []
    has_human = bool(req.human_teams)
    session["phase"] = "portal" if has_human else "regular"
    session["config"] = {
        "playoff_size": req.playoff_size,
        "bowl_count": req.bowl_count,
        "games_per_team": req.games_per_team,
    }
    session["injury_tracker"] = InjuryTracker()
    inj_seed = req.ai_seed if req.ai_seed else hash(req.name) % 999999
    session["injury_tracker"].seed(inj_seed)
    season.injury_tracker = session["injury_tracker"]
    session["dq_manager"] = DraftyQueenzManager(
        manager_name=req.human_teams[0] if req.human_teams else "Coach",
        season_year=2026,
    )
    session["history"] = history_results

    if has_human:
        ht = req.human_teams[0]
        prestige = 0
        if ht in season.teams:
            prestige = estimate_prestige_from_roster(season.teams[ht].players)
        rng = random.Random()
        portal = generate_quick_portal(
            team_names=list(season.teams.keys()), year=2027,
            size=40, prestige=prestige, rng=rng,
        )
        session["quick_portal"] = portal
        session["portal_human_team"] = ht

    # Coaching staffs are already on season.coaching_staffs (loaded from JSON).
    # Store a session reference so the human can browse/swap via the coaching
    # portal endpoints before starting the season.
    session["coaching_staffs"] = season.coaching_staffs

    result = _serialize_season_status(session)
    if history_results:
        result["history"] = history_results
    return result


@app.post("/sessions/{session_id}/season/simulate-week")
def simulate_week(session_id: str, req: SimulateWeekRequest):
    session = _get_session(session_id)
    season = _require_season(session)

    if session["phase"] not in ("regular",):
        raise HTTPException(status_code=400, detail=f"Cannot simulate week in phase '{session['phase']}'")

    week = req.week
    dq_mgr = session.get("dq_manager")
    dq_boosts = dq_mgr.get_all_team_boosts() if dq_mgr else None
    games = season.simulate_week(week=week, dq_team_boosts=dq_boosts)

    if not games:
        return {"week": week, "games": [], "message": "No games to simulate"}

    actual_week = games[0].week

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


@app.get("/sessions/{session_id}/season/history")
def season_history(session_id: str):
    session = _get_session(session_id)
    _require_season(session)
    return {"history": session.get("history", [])}


@app.get("/sessions/{session_id}/season/standings")
def season_standings(session_id: str):
    session = _get_session(session_id)
    season = _require_season(session)
    return {"standings": _serialize_standings(season)}


@app.get("/sessions/{session_id}/season/injuries")
def season_injuries(session_id: str, team: Optional[str] = Query(None)):
    session = _get_session(session_id)
    season = _require_season(session)
    tracker = session.get("injury_tracker")
    if tracker is None:
        return {"active": [], "season_log": [], "counts": {}}

    current_week = season.get_last_completed_week()
    if team:
        active = tracker.get_active_injuries(team, current_week)
        active_list = [inj.to_dict() for inj in active]
        team_log = [inj.to_dict() for inj in tracker.season_log if inj.team_name == team]
        penalties = tracker.get_team_injury_penalties(team, current_week)
        return {"active": active_list, "season_log": team_log, "penalties": penalties}
    else:
        all_active = []
        for team_name in season.teams:
            for inj in tracker.get_active_injuries(team_name, current_week):
                all_active.append(inj.to_dict())
        counts = tracker.get_season_injury_counts()
        category_report = tracker.get_injury_report_by_category()
        return {
            "active": all_active,
            "season_log": [inj.to_dict() for inj in tracker.season_log],
            "counts": counts,
            "category_report": category_report,
        }


@app.get("/sessions/{session_id}/season/roster/{team_name}")
def get_team_roster(session_id: str, team_name: str):
    session = _get_session(session_id)
    season = _require_season(session)
    team = season.teams.get(team_name)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")

    dynasty = session.get("dynasty")
    prestige = None
    if dynasty and hasattr(dynasty, "team_prestige"):
        prestige = dynasty.team_prestige.get(team_name)

    tracker = session.get("injury_tracker")
    unavail = set()
    dtd = set()
    if tracker:
        current_week = _require_season(session).get_last_completed_week()
        unavail = tracker.get_unavailable_names(team_name, current_week)
        dtd = tracker.get_dtd_names(team_name, current_week)

    from engine.draftyqueenz import compute_depth_chart
    depth = compute_depth_chart(team.players, unavailable_names=unavail, dtd_names=dtd)
    depth_rank_map = {}
    depth_status_map = {}
    for pos, entries in depth.items():
        for p, rank, status in entries:
            pname = getattr(p, 'name', '')
            depth_rank_map[pname] = rank
            depth_status_map[pname] = status

    serialized = []
    for p in team.players:
        d = _serialize_player(p)
        d["depth_rank"] = depth_rank_map.get(p.name, 99)
        d["depth_status"] = depth_status_map.get(p.name, "healthy")
        d["redshirt_used"] = getattr(p, "redshirt_used", False)
        d["redshirt_eligible"] = (
            not getattr(p, "redshirt_used", False)
            and getattr(p, "season_games_played", 0) <= 4
            and getattr(p, "year", "") not in ("Graduate", "graduate")
        )
        serialized.append(d)

    return {
        "team_name": team_name,
        "roster": serialized,
        "players": serialized,
        "roster_size": len(team.players),
        "prestige": prestige,
    }


class UpdatePlayerRequest(BaseModel):
    player_name: str
    number: Optional[int] = None
    position: Optional[str] = None


VALID_POSITIONS = {
    "Viper", "Zeroback", "Halfback", "Wingback",
    "Slotback", "Keeper", "Offensive Line", "Defensive Line",
}


@app.put("/sessions/{session_id}/season/roster/{team_name}")
def update_team_roster(session_id: str, team_name: str, updates: List[UpdatePlayerRequest]):
    session = _get_session(session_id)
    season = _require_season(session)
    team = season.teams.get(team_name)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")

    used_numbers = {p.number for p in team.players}
    updated = []
    errors = []
    for upd in updates:
        player = next((p for p in team.players if p.name == upd.player_name), None)
        if not player:
            errors.append(f"Player '{upd.player_name}' not found")
            continue
        if upd.number is not None:
            if upd.number < 1 or upd.number > 99:
                errors.append(f"Invalid number {upd.number} for {upd.player_name} (must be 1-99)")
                continue
            if upd.number != player.number and upd.number in used_numbers:
                errors.append(f"Number {upd.number} already taken on roster")
                continue
            used_numbers.discard(player.number)
            player.number = upd.number
            used_numbers.add(upd.number)
        if upd.position is not None:
            if upd.position not in VALID_POSITIONS:
                errors.append(f"Invalid position '{upd.position}' for {upd.player_name}")
                continue
            player.position = upd.position
        updated.append(upd.player_name)

    result = {"updated": updated, "roster": [_serialize_player(p) for p in team.players]}
    if errors:
        result["errors"] = errors
    return result


@app.get("/sessions/{session_id}/season/player-stats")
def season_player_stats(
    session_id: str,
    conference: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    position: Optional[str] = Query(None),
    min_touches: int = Query(0),
):
    session = _get_session(session_id)
    season = _require_season(session)

    player_agg: dict = {}

    for game in season.schedule:
        if not game.completed or not getattr(game, "full_result", None):
            continue
        fr = game.full_result
        ps = fr.get("player_stats", {})
        for side, team_name in [("home", game.home_team), ("away", game.away_team)]:
            conf = season.team_conferences.get(team_name, "")
            if conference and conf != conference:
                continue
            if team and team_name != team:
                continue
            for p in ps.get(side, []):
                key = f"{team_name}|{p['name']}"
                if key not in player_agg:
                    player_agg[key] = {
                        "name": p["name"],
                        "team": team_name,
                        "conference": conf,
                        "tag": p.get("tag", ""),
                        "archetype": p.get("archetype", ""),
                        "games_played": 0,
                        "touches": 0,
                        "yards": 0,
                        "rushing_yards": 0,
                        "lateral_yards": 0,
                        "tds": 0,
                        "fumbles": 0,
                        "laterals_thrown": 0,
                        "lateral_receptions": 0,
                        "lateral_assists": 0,
                        "lateral_tds": 0,
                        "kick_att": 0,
                        "kick_made": 0,
                        "pk_att": 0,
                        "pk_made": 0,
                        "dk_att": 0,
                        "dk_made": 0,
                        "kick_deflections": 0,
                        "kick_passes_thrown": 0,
                        "kick_passes_completed": 0,
                        "kick_pass_yards": 0,
                        "kick_pass_tds": 0,
                        "kick_pass_interceptions_thrown": 0,
                        "kick_pass_receptions": 0,
                        "kick_pass_ints": 0,
                        "keeper_bells": 0,
                        "coverage_snaps": 0,
                        "keeper_tackles": 0,
                        "kick_returns": 0,
                        "kick_return_yards": 0,
                        "kick_return_tds": 0,
                        "punt_returns": 0,
                        "punt_return_yards": 0,
                        "punt_return_tds": 0,
                        "muffs": 0,
                        "st_tackles": 0,
                        "tackles": 0,
                        "tfl": 0,
                        "sacks": 0,
                        "hurries": 0,
                    }
                agg = player_agg[key]
                agg["games_played"] += 1
                if not agg["tag"]:
                    agg["tag"] = p.get("tag", "")
                if not agg["archetype"] or agg["archetype"] == "—":
                    agg["archetype"] = p.get("archetype", "")
                for stat in [
                    "touches", "yards", "rushing_yards", "lateral_yards",
                    "tds", "fumbles", "laterals_thrown", "lateral_receptions",
                    "lateral_assists", "lateral_tds", "kick_att", "kick_made",
                    "pk_att", "pk_made", "dk_att", "dk_made",
                    "kick_deflections",
                    "kick_passes_thrown", "kick_passes_completed",
                    "kick_pass_yards", "kick_pass_tds",
                    "kick_pass_interceptions_thrown",
                    "kick_pass_receptions", "kick_pass_ints",
                    "keeper_bells", "coverage_snaps",
                    "keeper_tackles", "kick_returns", "kick_return_yards",
                    "kick_return_tds", "punt_returns", "punt_return_yards",
                    "punt_return_tds", "muffs", "st_tackles",
                    "tackles", "tfl", "sacks", "hurries",
                ]:
                    agg[stat] += p.get(stat, 0)

    results = list(player_agg.values())
    if position:
        pos_upper = position.upper()
        results = [r for r in results if pos_upper in r["tag"].upper()]
    if min_touches > 0:
        results = [r for r in results if r["touches"] >= min_touches or r.get("tackles", 0) > 0 or r.get("sacks", 0) > 0 or r.get("st_tackles", 0) > 0]

    for r in results:
        r["yards_per_touch"] = round(r["yards"] / max(1, r["touches"]), 1)
        r["kick_pct"] = round(r["kick_made"] / max(1, r["kick_att"]) * 100, 1)
        r["pk_pct"] = round(r["pk_made"] / max(1, r["pk_att"]) * 100, 1)
        r["dk_pct"] = round(r["dk_made"] / max(1, r["dk_att"]) * 100, 1)
        r["total_return_yards"] = r["kick_return_yards"] + r["punt_return_yards"]
        r["total_return_tds"] = r["kick_return_tds"] + r["punt_return_tds"]

    results.sort(key=lambda x: x["yards"], reverse=True)

    return {"players": results, "count": len(results)}


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

    dynasty = session.get("dynasty")
    prestige_map = None
    if dynasty and hasattr(dynasty, "team_prestige") and dynasty.team_prestige:
        prestige_map = dynasty.team_prestige

    polls = season.weekly_polls
    if week is not None:
        polls = [p for p in polls if p.week == week]

    return {"polls": [_serialize_poll(p, prestige_map=prestige_map) for p in polls]}


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
        result = season_honors.to_dict()
        return result
    except Exception as e:
        return {"individual_awards": [], "coach_of_year": None, "most_improved": None, "error": str(e)}


@app.post("/sessions/{session_id}/dynasty")
def create_dynasty_endpoint(session_id: str, req: CreateDynastyRequest):
    session = _get_session(session_id)

    teams = load_teams_from_directory(TEAMS_DIR, fresh=True)
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
            games_per_team=12,
            playoff_size=8,
        )

    session["dynasty"] = dynasty
    session["phase"] = "setup"
    session["injury_tracker"] = None
    session["season"] = None
    session["program_archetype"] = req.program_archetype

    return _serialize_dynasty_status(session)


@app.get("/sessions/{session_id}/dynasty/non-conference-opponents")
def dynasty_non_conference_opponents(
    session_id: str,
    team: Optional[str] = Query(None, description="Team name (defaults to coach team)"),
    games_per_team: int = Query(12),
):
    """Get available non-conference opponents for a dynasty team, using dynasty prestige."""
    session = _get_session(session_id)
    dynasty = _require_dynasty(session)

    team_name = team or dynasty.coach.team_name
    all_teams = load_teams_from_directory(TEAMS_DIR)
    if team_name not in all_teams:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")

    conf_dict = dynasty.get_conferences_dict()
    team_conf_map = {}
    for conf_name, conf_teams in conf_dict.items():
        for t in conf_teams:
            team_conf_map[t] = conf_name

    # Use dynasty prestige if available, otherwise estimate from roster
    prestige_map = dynasty.team_prestige if dynasty.team_prestige else None

    opponents = get_available_non_conference_opponents(
        team_name=team_name,
        all_teams=all_teams,
        conferences=conf_dict,
        team_conferences=team_conf_map,
        team_prestige=prestige_map,
    )

    my_conf = team_conf_map.get(team_name, "")
    my_conf_size = 0
    for conf_name, conf_teams in conf_dict.items():
        if team_name in conf_teams:
            my_conf_size = len(conf_teams)
            break

    nc_slots = get_non_conference_slots(games_per_team, my_conf_size)
    my_prestige = dynasty.get_team_prestige(team_name)

    return {
        "team": team_name,
        "conference": my_conf,
        "conference_size": my_conf_size,
        "non_conference_slots": nc_slots,
        "team_prestige": my_prestige,
        "opponents": opponents,
        "total_opponents": len(opponents),
    }


@app.post("/sessions/{session_id}/dynasty/start-season")
def dynasty_start_season(session_id: str, req: DynastyStartSeasonRequest):
    session = _get_session(session_id)
    dynasty = _require_dynasty(session)

    if session["phase"] not in ("setup", "finalize"):
        raise HTTPException(status_code=400, detail=f"Cannot start season in phase '{session['phase']}'")

    # Build archetype map: human team gets the user's chosen archetype,
    # falling back to the archetype stored when the dynasty was created
    arch = req.program_archetype or session.get("program_archetype")
    dyn_archetypes = None
    if arch:
        dyn_archetypes = {dynasty.coach.team_name: arch}

    teams, team_states = load_teams_with_states(
        TEAMS_DIR, fresh=True,
        team_archetypes=dyn_archetypes,
    )

    seed = req.ai_seed if req.ai_seed is not None else random.randint(0, 999999)
    ai_configs = auto_assign_all_teams(
        TEAMS_DIR,
        human_teams=[dynasty.coach.team_name],
        human_configs={
            dynasty.coach.team_name: {
                "offense_style": req.offense_style,
                "defense_style": req.defense_style,
                "st_scheme": req.st_scheme,
            }
        },
        seed=seed,
    )

    style_configs = {}
    for tname in teams:
        style_configs[tname] = ai_configs.get(
            tname, {"offense_style": "balanced", "defense_style": "swarm", "st_scheme": "aces"}
        )

    pinned = None
    if req.pinned_matchups:
        pinned = [(pair[0], pair[1]) for pair in req.pinned_matchups if len(pair) == 2]

    conf_dict = dynasty.get_conferences_dict()

    rivalries_dict = auto_assign_rivalries(
        conferences=conf_dict,
        team_states=team_states,
        human_team=dynasty.coach.team_name,
        existing_rivalries=req.rivalries,
    )
    dynasty.rivalries = rivalries_dict

    season = create_season(
        f"{dynasty.current_year} CVL Season",
        teams,
        style_configs,
        conferences=conf_dict,
        games_per_team=req.games_per_team,
        team_states=team_states,
        pinned_matchups=pinned,
        rivalries=rivalries_dict,
        coaching_staffs=dynasty._coaching_staffs if dynasty._coaching_staffs else None,
        dynasty_year=dynasty.current_year,
    )

    session["season"] = season
    session["phase"] = "regular"
    session["config"] = {
        "playoff_size": req.playoff_size,
        "bowl_count": req.bowl_count,
        "games_per_team": req.games_per_team,
    }
    session["injury_tracker"] = InjuryTracker()
    session["injury_tracker"].seed(hash(f"{dynasty.dynasty_name}_{dynasty.current_year}_inj") % 999999)
    season.injury_tracker = session["injury_tracker"]

    existing_dq = session.get("dq_manager")
    if existing_dq:
        existing_dq.season_year = dynasty.current_year
        existing_dq.weekly_contests = {}
        existing_dq.donations = []
    else:
        session["dq_manager"] = DraftyQueenzManager(
            manager_name=dynasty.coach.team_name,
            season_year=dynasty.current_year,
        )

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
    rng = random.Random(dynasty.current_year + 7)

    dq_manager_pre = session.get("dq_manager")
    dq_team_boosts_map = None
    if dq_manager_pre:
        dq_team_boosts_map = dq_manager_pre.get_all_team_boosts()
    dynasty.advance_season(season, injury_tracker=tracker, player_cards=player_cards, rng=rng,
                           dq_team_boosts=dq_team_boosts_map)

    year = dynasty.current_year
    prev_year = year - 1
    human_team = dynasty.coach.team_name

    for team_name, history in dynasty.team_histories.items():
        recent_wins = 5
        if prev_year in history.season_records:
            recent_wins = history.season_records[prev_year].get("wins", 5)
        dynasty.team_prestige[team_name] = compute_team_prestige(
            all_time_wins=history.total_wins,
            all_time_losses=history.total_losses,
            championships=history.total_championships,
            recent_wins=recent_wins,
        )

    dq_manager = session.get("dq_manager")
    dq_boosts = {}
    if dq_manager:
        dq_boosts = dq_manager.get_active_boosts(team_name=human_team)
        facilities_boost = dq_boosts.get("facilities", 0)
        if facilities_boost > 0 and human_team in dynasty.team_prestige:
            dynasty.team_prestige[human_team] = min(
                100,
                dynasty.team_prestige[human_team] + int(facilities_boost)
            )

    dynasty._nil_programs = {}
    for team_name in dynasty.team_histories:
        prestige = dynasty.team_prestige.get(team_name, 50)
        state = ""
        for conf in dynasty.conferences.values():
            if team_name in conf.teams:
                break
        market = estimate_market_tier(state) if state else "medium"
        prev_wins = 5
        champ = False
        if prev_year in dynasty.awards_history:
            awards = dynasty.awards_history[prev_year]
            if team_name == awards.champion:
                champ = True
        sr = dynasty.team_histories[team_name].season_records.get(prev_year, {})
        prev_wins = sr.get("wins", 5)

        if team_name == human_team:
            budget = generate_nil_budget(
                prestige=prestige, market=market,
                previous_season_wins=prev_wins, championship=champ, rng=rng,
            )
            nil_topup = dq_boosts.get("nil_topup", 0)
            if nil_topup > 0:
                budget += int(nil_topup)
            program = NILProgram(team_name=team_name, annual_budget=budget)
        else:
            program = auto_nil_program(
                team_name=team_name, prestige=prestige, market=market,
                previous_wins=prev_wins, championship=champ, rng=rng,
            )
        dynasty._nil_programs[team_name] = program

    last_season = dynasty.seasons.get(prev_year, season)
    offseason_player_cards = {}
    for t_name, t_obj in last_season.teams.items():
        offseason_player_cards[t_name] = [player_to_card(p, t_name) for p in t_obj.players]

    retention_risks = []
    if human_team in offseason_player_cards:
        ht_prestige = dynasty.team_prestige.get(human_team, 50)
        sr = dynasty.team_histories.get(human_team)
        hw = sr.season_records.get(prev_year, {}).get("wins", 5) if sr else 5
        from engine.nil_system import RetentionRisk
        retention_bonus = dq_boosts.get("retention", 0)
        retention_risks = assess_retention_risks(
            roster=offseason_player_cards[human_team],
            team_prestige=ht_prestige,
            team_wins=hw,
            rng=rng,
            retention_boost=retention_bonus,
        )

    graduating = {}
    for team_name, cards in offseason_player_cards.items():
        grads = [c.full_name for c in cards if c.year == "Graduate"]
        if grads:
            graduating[team_name] = grads

    team_records = {}
    for team_name in offseason_player_cards:
        sr = dynasty.team_histories.get(team_name)
        if sr:
            rec = sr.season_records.get(prev_year, {"wins": 5, "losses": 5})
            team_records[team_name] = (rec.get("wins", 5), rec.get("losses", 5))
        else:
            team_records[team_name] = (5, 5)

    portal = TransferPortal(year=year)
    populate_portal(portal, offseason_player_cards, team_records, rng=rng)

    recruit_pool = generate_recruit_class(year=year, size=300, rng=random.Random(year))
    recruit_board = RecruitingBoard(team_name=human_team, scholarships_available=8)

    human_nil = dynasty._nil_programs.get(human_team)

    session["offseason"] = {
        "portal": portal,
        "recruit_pool": recruit_pool,
        "recruit_board": recruit_board,
        "nil_program": human_nil,
        "nil_offers": {},
        "retention_risks": retention_risks,
        "graduating": graduating,
        "prestige": dict(dynasty.team_prestige),
        "phase": "nil",
        "player_cards": offseason_player_cards,
        "dq_boosts": dq_boosts,
    }
    session["phase"] = "offseason"
    session["season"] = None
    session["injury_tracker"] = None

    return {
        "dynasty": _serialize_dynasty_status(session),
        "offseason_phase": "nil",
        "prestige": {human_team: dynasty.team_prestige.get(human_team, 50)},
        "nil_budget": human_nil.annual_budget if human_nil else 0,
        "retention_risks": [r.to_dict() for r in retention_risks],
        "graduating": graduating.get(human_team, []),
        "portal_entries": len(portal.entries),
        "recruit_pool_size": len(recruit_pool),
    }


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


@app.get("/sessions/{session_id}/dynasty/coaching-history")
def dynasty_coaching_history(session_id: str):
    session = _get_session(session_id)
    dynasty = _require_dynasty(session)

    history = {}
    for year, data in dynasty.coaching_history.items():
        changes = data.get("changes", {})
        summary = data.get("marketplace_summary", {})
        history[str(year)] = {
            "changes": {
                team: roles for team, roles in changes.items()
            },
            "teams_with_changes": len(changes),
            "marketplace_summary": summary,
        }

    staffs = {}
    coaching_staffs = dynasty._coaching_staffs or {}
    for t_name, staff in coaching_staffs.items():
        hc = staff.get("head_coach") if isinstance(staff, dict) else None
        if hc:
            staffs[t_name] = {
                "hc_name": hc.name,
                "hc_classification": hc.classification or "unclassified",
                "hc_overall": hc.overall,
                "hc_seasons": hc.seasons_coached,
                "hc_record": f"{hc.career_wins}-{hc.career_losses}",
            }

    return {"coaching_history": history, "current_staffs": staffs}


@app.get("/sessions/{session_id}/team/{team_name}")
def team_roster(session_id: str, team_name: str):
    session = _get_session(session_id)
    season = _require_season(session)

    if team_name not in season.teams:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")

    team = season.teams[team_name]

    tracker = session.get("injury_tracker")
    unavail = set()
    dtd = set()
    if tracker:
        current_week = season.get_last_completed_week()
        unavail = tracker.get_unavailable_names(team_name, current_week)
        dtd = tracker.get_dtd_names(team_name, current_week)

    from engine.draftyqueenz import compute_depth_chart
    depth = compute_depth_chart(team.players, unavailable_names=unavail, dtd_names=dtd)
    depth_rank_map = {}
    depth_status_map = {}
    for pos, entries in depth.items():
        for p, rank, status in entries:
            pname = getattr(p, 'name', '')
            depth_rank_map[pname] = rank
            depth_status_map[pname] = status

    players = []
    for p in team.players:
        d = _serialize_player(p)
        d["depth_rank"] = depth_rank_map.get(p.name, 99)
        d["depth_status"] = depth_status_map.get(p.name, "healthy")
        d["redshirt_used"] = getattr(p, "redshirt_used", False)
        d["redshirt_eligible"] = (
            not getattr(p, "redshirt_used", False)
            and getattr(p, "season_games_played", 0) <= 4
            and getattr(p, "year", "") not in ("Graduate", "graduate")
        )
        players.append(d)

    record = season.standings.get(team_name)
    team_record = _serialize_team_record(record) if record else None

    dynasty = session.get("dynasty")
    prestige = None
    if dynasty and hasattr(dynasty, "team_prestige"):
        prestige = dynasty.team_prestige.get(team_name)

    return {
        "team_name": team.name,
        "abbreviation": team.abbreviation,
        "mascot": team.mascot,
        "players": players,
        "record": team_record,
        "prestige": prestige,
    }


@app.get("/sessions/{session_id}/team/{team_name}/schedule")
def team_schedule(session_id: str, team_name: str):
    session = _get_session(session_id)
    season = _require_season(session)

    if team_name not in season.teams:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")

    games = [g for g in season.schedule if g.home_team == team_name or g.away_team == team_name]
    return {"team": team_name, "games": [_serialize_game(g) for g in games], "count": len(games)}


def _require_offseason(session: dict) -> dict:
    offseason = session.get("offseason")
    if offseason is None or session.get("phase") != "offseason":
        raise HTTPException(status_code=400, detail="No active offseason in this session")
    return offseason


def _serialize_portal_entry(entry: PortalEntry) -> dict:
    d = entry.get_summary()
    d["position_full"] = d.get("position", "")
    d["position"] = POSITION_TAGS.get(d["position_full"], d["position_full"][:2].upper() if d["position_full"] else "??")
    return d


def _serialize_recruit(recruit: Recruit) -> dict:
    d = recruit.get_visible_attrs()
    d["position_full"] = d.get("position", "")
    d["position"] = POSITION_TAGS.get(d["position_full"], d["position_full"][:2].upper() if d["position_full"] else "??")
    return d


@app.get("/sessions/{session_id}/offseason/status")
def offseason_status(session_id: str):
    session = _get_session(session_id)
    offseason = _require_offseason(session)
    nil_prog = offseason.get("nil_program")
    portal = offseason.get("portal")
    recruit_pool = offseason.get("recruit_pool", [])
    return {
        "phase": offseason["phase"],
        "nil_budget": nil_prog.annual_budget if nil_prog else 0,
        "nil_allocated": nil_prog.total_allocated if nil_prog else 0,
        "portal_count": len(portal.entries) if portal else 0,
        "portal_available": len(portal.get_available()) if portal else 0,
        "recruit_pool_size": len(recruit_pool),
        "retention_risks_count": len(offseason.get("retention_risks", [])),
        "graduating_count": sum(len(v) for v in offseason.get("graduating", {}).values()),
    }


@app.get("/sessions/{session_id}/offseason/nil")
def offseason_nil(session_id: str):
    session = _get_session(session_id)
    offseason = _require_offseason(session)
    nil_prog = offseason.get("nil_program")
    if nil_prog is None:
        raise HTTPException(status_code=400, detail="No NIL program found")
    return nil_prog.get_deal_summary()


@app.post("/sessions/{session_id}/offseason/nil/allocate")
def offseason_nil_allocate(session_id: str, req: NILAllocateRequest):
    session = _get_session(session_id)
    offseason = _require_offseason(session)
    nil_prog = offseason.get("nil_program")
    if nil_prog is None:
        raise HTTPException(status_code=400, detail="No NIL program found")

    total = req.recruiting_pool + req.portal_pool + req.retention_pool
    if total > nil_prog.annual_budget:
        raise HTTPException(status_code=400, detail=f"Total allocation ${total:,.0f} exceeds budget ${nil_prog.annual_budget:,.0f}")

    nil_prog.recruiting_pool = req.recruiting_pool
    nil_prog.portal_pool = req.portal_pool
    nil_prog.retention_pool = req.retention_pool

    offseason["phase"] = "portal"

    return {
        "allocated": True,
        "summary": nil_prog.get_deal_summary(),
        "offseason_phase": "portal",
    }


@app.get("/sessions/{session_id}/offseason/portal")
def offseason_portal(
    session_id: str,
    position: Optional[str] = Query(None),
    min_overall: Optional[int] = Query(None),
):
    session = _get_session(session_id)
    offseason = _require_offseason(session)
    portal = offseason.get("portal")
    if portal is None:
        raise HTTPException(status_code=400, detail="No portal found")

    available = portal.get_available()
    indexed = []
    for e in available:
        try:
            global_idx = portal.entries.index(e)
        except ValueError:
            global_idx = -1
        indexed.append((global_idx, e))

    if position:
        pos_upper = position.upper()
        indexed = [(i, e) for i, e in indexed if POSITION_TAGS.get(e.position, e.position[:2].upper()) == pos_upper or position.lower() in e.position.lower()]
    if min_overall is not None:
        indexed = [(i, e) for i, e in indexed if e.overall >= min_overall]

    result_entries = []
    for gi, e in indexed:
        d = _serialize_portal_entry(e)
        d["global_index"] = gi
        result_entries.append(d)

    return {
        "entries": result_entries,
        "total_available": len(indexed),
        "total_entries": len(portal.entries),
    }


@app.post("/sessions/{session_id}/offseason/portal/offer")
def offseason_portal_offer(session_id: str, req: PortalOfferRequest):
    session = _get_session(session_id)
    dynasty = _require_dynasty(session)
    offseason = _require_offseason(session)
    portal = offseason.get("portal")
    if portal is None:
        raise HTTPException(status_code=400, detail="No portal found")

    if req.entry_index < 0 or req.entry_index >= len(portal.entries):
        raise HTTPException(status_code=400, detail="Invalid entry index")

    entry = portal.entries[req.entry_index]
    human_team = dynasty.coach.team_name
    success = portal.make_offer(human_team, entry, nil_amount=req.nil_amount)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot make offer to this player")

    return {
        "offered": True,
        "player": _serialize_portal_entry(entry),
    }


@app.post("/sessions/{session_id}/offseason/portal/commit")
def offseason_portal_commit(session_id: str, req: PortalCommitRequest):
    session = _get_session(session_id)
    dynasty = _require_dynasty(session)
    offseason = _require_offseason(session)
    portal = offseason.get("portal")
    if portal is None:
        raise HTTPException(status_code=400, detail="No portal found")

    if req.entry_index < 0 or req.entry_index >= len(portal.entries):
        raise HTTPException(status_code=400, detail="Invalid entry index")

    entry = portal.entries[req.entry_index]
    human_team = dynasty.coach.team_name
    success = portal.instant_commit(human_team, entry)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot commit this player")

    return {
        "committed": True,
        "player": _serialize_portal_entry(entry),
    }


@app.post("/sessions/{session_id}/offseason/portal/resolve")
def offseason_portal_resolve(session_id: str):
    session = _get_session(session_id)
    dynasty = _require_dynasty(session)
    offseason = _require_offseason(session)
    portal = offseason.get("portal")
    if portal is None:
        raise HTTPException(status_code=400, detail="No portal found")

    human_team = dynasty.coach.team_name
    rng = random.Random(dynasty.current_year + 11)
    team_regions = dynasty._estimate_team_regions()

    for team_name in dynasty.team_histories:
        if team_name == human_team:
            continue
        prestige = dynasty.team_prestige.get(team_name, 50)
        nil_prog = dynasty._nil_programs.get(team_name)
        portal_budget = nil_prog.portal_pool if nil_prog else 150_000
        auto_portal_offers(
            portal=portal,
            team_name=team_name,
            team_prestige=prestige,
            needs=["Viper", "Halfback", "Lineman"],
            nil_budget=portal_budget,
            max_targets=4,
            rng=rng,
        )

    portal_result = portal.resolve_all(
        team_prestige=dynasty.team_prestige,
        team_regions=team_regions,
        rng=rng,
    )

    offseason["phase"] = "recruiting"

    human_transfers = portal_result.get(human_team, [])
    return {
        "resolved": True,
        "total_transfers": len(portal.transfers_completed),
        "human_transfers": [_serialize_portal_entry(e) for e in human_transfers],
        "all_transfers": portal.get_class_summary(),
        "offseason_phase": "recruiting",
    }


@app.get("/sessions/{session_id}/offseason/recruiting")
def offseason_recruiting(session_id: str):
    session = _get_session(session_id)
    offseason = _require_offseason(session)
    recruit_pool = offseason.get("recruit_pool", [])
    recruit_board = offseason.get("recruit_board")

    available = []
    for idx, r in enumerate(recruit_pool):
        if r.committed_to is None and not r.signed:
            d = _serialize_recruit(r)
            d["pool_index"] = idx
            available.append(d)

    return {
        "recruits": available,
        "total_available": len(available),
        "total_pool": len(recruit_pool),
        "board": recruit_board.to_dict() if recruit_board else None,
    }


@app.post("/sessions/{session_id}/offseason/recruiting/scout")
def offseason_recruiting_scout(session_id: str, req: ScoutRequest):
    session = _get_session(session_id)
    offseason = _require_offseason(session)
    recruit_pool = offseason.get("recruit_pool", [])
    recruit_board = offseason.get("recruit_board")

    if recruit_board is None:
        raise HTTPException(status_code=400, detail="No recruiting board found")
    if req.recruit_index < 0 or req.recruit_index >= len(recruit_pool):
        raise HTTPException(status_code=400, detail="Invalid recruit index")

    recruit = recruit_pool[req.recruit_index]
    result = recruit_board.scout(recruit, level=req.level)
    if result is None:
        raise HTTPException(status_code=400, detail="Not enough scouting points")

    return {
        "scouted": True,
        "recruit": result,
        "scouting_points_remaining": recruit_board.scouting_points,
    }


@app.post("/sessions/{session_id}/offseason/recruiting/offer")
def offseason_recruiting_offer(session_id: str, req: RecruitOfferRequest):
    session = _get_session(session_id)
    offseason = _require_offseason(session)
    recruit_pool = offseason.get("recruit_pool", [])
    recruit_board = offseason.get("recruit_board")

    if recruit_board is None:
        raise HTTPException(status_code=400, detail="No recruiting board found")
    if req.recruit_index < 0 or req.recruit_index >= len(recruit_pool):
        raise HTTPException(status_code=400, detail="Invalid recruit index")

    recruit = recruit_pool[req.recruit_index]
    success = recruit_board.offer(recruit)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot offer this recruit (at limit, already offered, or recruit committed)")

    return {
        "offered": True,
        "recruit": _serialize_recruit(recruit),
        "offers_made": len(recruit_board.offered),
        "max_offers": recruit_board.max_offers,
    }


@app.post("/sessions/{session_id}/offseason/recruiting/resolve")
def offseason_recruiting_resolve(session_id: str):
    session = _get_session(session_id)
    dynasty = _require_dynasty(session)
    offseason = _require_offseason(session)
    recruit_pool = offseason.get("recruit_pool", [])
    recruit_board = offseason.get("recruit_board")

    if recruit_board is None:
        raise HTTPException(status_code=400, detail="No recruiting board found")

    human_team = dynasty.coach.team_name
    rng = random.Random(dynasty.current_year + 13)
    team_regions = dynasty._estimate_team_regions()

    boards = {human_team: recruit_board}
    all_nil = {human_team: offseason.get("nil_offers", {})}

    graduating = offseason.get("graduating", {})
    portal = offseason.get("portal")

    for team_name in dynasty.team_histories:
        if team_name == human_team:
            continue
        prestige = dynasty.team_prestige.get(team_name, 50)
        nil_prog = dynasty._nil_programs.get(team_name)
        nil_budget = nil_prog.recruiting_pool if nil_prog else 300_000

        portal_adds = 0
        if portal:
            portal_adds = sum(1 for e in portal.entries if e.committed_to == team_name)
        grads = len(graduating.get(team_name, []))
        portal_losses = 0
        if portal:
            portal_losses = sum(
                1 for e in portal.entries
                if e.origin_team == team_name and e.committed_to and e.committed_to != team_name
            )
        open_spots = max(3, min(12, grads + portal_losses - portal_adds))

        board, nil = auto_recruit_team(
            team_name=team_name,
            pool=recruit_pool,
            team_prestige=prestige,
            team_region=team_regions.get(team_name, "midwest"),
            scholarships=open_spots,
            nil_budget=nil_budget,
            rng=rng,
        )
        boards[team_name] = board
        all_nil[team_name] = nil

    recruiting_prestige = dict(dynasty.team_prestige)
    dq_boosts_off = offseason.get("dq_boosts", {})
    recruit_boost = dq_boosts_off.get("recruiting", 0)
    if recruit_boost > 0 and human_team in recruiting_prestige:
        recruiting_prestige[human_team] = min(
            100, recruiting_prestige[human_team] + int(recruit_boost)
        )
    recruit_nil_boost = dq_boosts_off.get("nil_topup", 0)
    if recruit_nil_boost > 0:
        human_nil_prog = dynasty._nil_programs.get(human_team)
        if human_nil_prog:
            human_nil_prog.recruiting_pool += int(recruit_nil_boost * 0.3)

    signed = simulate_recruit_decisions(
        pool=recruit_pool,
        team_boards=boards,
        team_prestige=recruiting_prestige,
        team_regions=team_regions,
        nil_offers=all_nil,
        rng=rng,
    )

    rankings = []
    for team, recruits in signed.items():
        if recruits:
            avg = sum(r.stars for r in recruits) / len(recruits)
            rankings.append({"team": team, "avg_stars": round(avg, 2), "count": len(recruits)})
    rankings.sort(key=lambda x: (-x["avg_stars"], -x["count"]))

    offseason["phase"] = "ready"

    human_signed = signed.get(human_team, [])
    return {
        "resolved": True,
        "class_rankings": rankings,
        "human_signed": [_serialize_recruit(r) for r in human_signed],
        "human_signed_count": len(human_signed),
        "total_signed": sum(len(v) for v in signed.values()),
        "offseason_phase": "ready",
    }


@app.post("/sessions/{session_id}/offseason/complete")
def offseason_complete(session_id: str):
    session = _get_session(session_id)
    dynasty = _require_dynasty(session)
    _require_offseason(session)

    session.pop("offseason", None)
    session["phase"] = "setup"

    return _serialize_dynasty_status(session)


@app.post("/sessions/{session_id}/season/portal/generate")
def season_portal_generate(
    session_id: str,
    req: SeasonPortalGenerateRequest = SeasonPortalGenerateRequest(),
):
    size = req.size
    human_team = req.human_team
    session = _get_session(session_id)
    season = _require_season(session)

    team_names = list(season.teams.keys())
    rng = random.Random()

    prestige = 0
    if human_team and human_team in season.teams:
        prestige = estimate_prestige_from_roster(season.teams[human_team].players)
        session["portal_human_team"] = human_team
    else:
        human_teams = session.get("human_teams", [])
        if human_teams:
            ht = human_teams[0]
            if ht in season.teams:
                prestige = estimate_prestige_from_roster(season.teams[ht].players)
                session["portal_human_team"] = ht

    portal = generate_quick_portal(
        team_names=team_names, year=2027, size=size,
        prestige=prestige, rng=rng,
    )
    session["quick_portal"] = portal
    session["phase"] = "portal"

    remaining = portal.transfers_remaining(session.get("portal_human_team", ""))

    entries_serialized = []
    for i, e in enumerate(portal.entries):
        d = _serialize_portal_entry(e)
        d["global_index"] = i
        entries_serialized.append(d)

    return {
        "entries": entries_serialized,
        "total": len(portal.entries),
        "transfer_cap": portal.transfer_cap,
        "transfers_remaining": remaining,
        "prestige": prestige,
    }


@app.get("/sessions/{session_id}/season/portal")
def season_portal_get(session_id: str):
    session = _get_session(session_id)
    portal = session.get("quick_portal")
    if portal is None:
        raise HTTPException(status_code=400, detail="No quick portal generated. POST to /season/portal/generate first.")

    human_team = session.get("portal_human_team", "")
    remaining = portal.transfers_remaining(human_team)

    available = portal.get_available()
    avail_serialized = []
    for e in available:
        idx = portal.entries.index(e)
        d = _serialize_portal_entry(e)
        d["global_index"] = idx
        avail_serialized.append(d)

    committed = [e for e in portal.entries if e.committed_to == human_team]
    committed_serialized = []
    for e in committed:
        d = _serialize_portal_entry(e)
        committed_serialized.append(d)

    return {
        "entries": avail_serialized,
        "committed": committed_serialized,
        "total": len(portal.entries),
        "available_count": len(available),
        "transfer_cap": portal.transfer_cap,
        "transfers_remaining": remaining,
        "human_team": human_team,
    }


@app.post("/sessions/{session_id}/season/portal/commit")
def season_portal_commit(session_id: str, req: SeasonPortalCommitRequest):
    team_name = req.team_name
    entry_index = req.entry_index
    session = _get_session(session_id)
    season = _require_season(session)
    portal = session.get("quick_portal")
    if portal is None:
        raise HTTPException(status_code=400, detail="No quick portal generated. POST to /season/portal/generate first.")

    if entry_index < 0 or entry_index >= len(portal.entries):
        raise HTTPException(status_code=400, detail="Invalid entry index")

    entry = portal.entries[entry_index]
    success = portal.instant_commit(team_name, entry)
    if not success:
        remaining = portal.transfers_remaining(team_name)
        if remaining == 0:
            raise HTTPException(status_code=400, detail="Transfer cap reached — no more portal slots available.")
        raise HTTPException(status_code=400, detail="Cannot commit this player (already committed or withdrawn)")

    if team_name in season.teams:
        card = entry.player_card
        new_player = Player(
            number=max((p.number for p in season.teams[team_name].players), default=0) + 1,
            name=card.full_name,
            position=card.position,
            speed=card.speed,
            stamina=card.stamina,
            kicking=card.kicking,
            lateral_skill=card.lateral_skill,
            tackling=card.tackling,
            agility=card.agility,
            power=card.power,
            awareness=card.awareness,
            hands=card.hands,
            kick_power=card.kick_power,
            kick_accuracy=card.kick_accuracy,
            player_id=card.player_id,
            nationality=card.nationality,
            hometown_city=card.hometown_city,
            hometown_state=card.hometown_state,
            hometown_country=card.hometown_country,
            high_school=card.high_school,
            height=card.height,
            weight=card.weight,
            year=card.year,
            potential=card.potential,
            development=card.development,
        )
        new_player.archetype = assign_archetype(new_player)
        season.teams[team_name].players.append(new_player)

    remaining = portal.transfers_remaining(team_name)

    return {
        "committed": True,
        "player": _serialize_portal_entry(entry),
        "team": team_name,
        "transfers_remaining": remaining,
        "transfer_cap": portal.transfer_cap,
    }


@app.post("/sessions/{session_id}/season/portal/skip")
def season_portal_skip(session_id: str):
    session = _get_session(session_id)
    _require_season(session)
    session["phase"] = "regular"
    return {"phase": "regular", "skipped": True}


# ──────────────────────────────────────────────────────────────────────
# COACHING STAFF ENDPOINTS (season mode — browse & pick staff pre-game)
# ──────────────────────────────────────────────────────────────────────

def _serialize_coach_card(card) -> dict:
    """Serialize a CoachCard for API responses."""
    from engine.coaching import CoachCard, CLASSIFICATION_LABELS, HC_AFFINITY_LABELS
    if isinstance(card, dict):
        return card
    return {
        "coach_id": card.coach_id,
        "name": card.full_name,
        "role": card.role,
        "overall": card.overall,
        "star_rating": card.star_rating,
        "classification": card.classification,
        "classification_label": card.classification_label,
        "sub_archetype": card.sub_archetype,
        "sub_archetype_label": card.sub_archetype_label,
        "hc_affinity": card.hc_affinity,
        "hc_affinity_label": card.hc_affinity_label,
        "composure_label": card.composure_label,
        "leadership": card.leadership,
        "composure": card.composure,
        "rotations": card.rotations,
        "development": card.development,
        "recruiting": card.recruiting,
        "visible_score": card.visible_score,
        "career_wins": card.career_wins,
        "career_losses": card.career_losses,
        "win_percentage": round(card.win_percentage, 3),
        "championships": card.championships,
        "seasons_coached": card.seasons_coached,
        "contract_years_remaining": card.contract_years_remaining,
        "contract_salary": card.contract_salary,
        "philosophy": card.philosophy,
        "coaching_style": card.coaching_style,
        "personality": card.personality,
        "background": card.background,
        "wants_hc": card.wants_hc,
        "alma_mater": card.alma_mater,
    }


@app.get("/sessions/{session_id}/season/coaching-staff")
def season_coaching_staff_get(session_id: str, team: Optional[str] = Query(None)):
    """Get the current coaching staff for a team (or the human team)."""
    session = _get_session(session_id)
    season = _require_season(session)
    staffs = session.get("coaching_staffs", season.coaching_staffs)

    human_teams = session.get("human_teams", [])
    team_name = team or (human_teams[0] if human_teams else "")
    if not team_name:
        raise HTTPException(status_code=400, detail="No team specified")

    staff = staffs.get(team_name, {})
    serialized = {}
    for role, card in staff.items():
        serialized[role] = _serialize_coach_card(card)

    from engine.coaching import compute_dev_aura
    aura = compute_dev_aura(staff)

    return {
        "team": team_name,
        "staff": serialized,
        "dev_aura": round(aura, 4),
        "dev_aura_max_boost_pct": round(aura * 100, 1),
    }


@app.post("/sessions/{session_id}/season/coaching-staff/generate-pool")
def season_coaching_pool_generate(session_id: str):
    """Generate a pool of available coaches the human can pick from."""
    session = _get_session(session_id)
    season = _require_season(session)

    from engine.coaching import generate_coach_card, ROLES

    human_teams = session.get("human_teams", [])
    human_team = human_teams[0] if human_teams else ""
    prestige = 50
    if human_team and human_team in season.teams:
        prestige = estimate_prestige_from_roster(season.teams[human_team].players)

    rng = random.Random()
    pool = []
    # Generate 5 candidates per role (HC, OC, DC, STC) = 20 total
    for role in ROLES:
        for _ in range(5):
            card = generate_coach_card(
                role=role, team_name="", prestige=rng.randint(max(20, prestige - 20), min(95, prestige + 15)),
                year=2026, rng=rng,
            )
            pool.append(card)

    session["coaching_pool"] = pool
    serialized = [_serialize_coach_card(c) for c in pool]

    return {
        "pool": serialized,
        "total": len(pool),
        "team_prestige": prestige,
    }


class CoachHireRequest(BaseModel):
    coach_id: str
    role: str  # role to hire them into


@app.post("/sessions/{session_id}/season/coaching-staff/hire")
def season_coaching_hire(session_id: str, req: CoachHireRequest):
    """Hire a coach from the pool into a specific role on the human team."""
    session = _get_session(session_id)
    season = _require_season(session)

    pool = session.get("coaching_pool", [])
    if not pool:
        raise HTTPException(status_code=400, detail="No coaching pool generated. POST to /season/coaching-staff/generate-pool first.")

    human_teams = session.get("human_teams", [])
    human_team = human_teams[0] if human_teams else ""
    if not human_team:
        raise HTTPException(status_code=400, detail="No human team")

    # Find the coach in the pool
    target = None
    for card in pool:
        if card.coach_id == req.coach_id:
            target = card
            break

    if target is None:
        raise HTTPException(status_code=404, detail="Coach not found in pool")

    from engine.coaching import ROLES
    if req.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role: {req.role}")

    # Set the coach on the team
    target.team_name = human_team
    target.role = req.role
    staffs = session.get("coaching_staffs", season.coaching_staffs)
    if human_team not in staffs:
        staffs[human_team] = {}
    old_coach = staffs[human_team].get(req.role)
    staffs[human_team][req.role] = target
    season.coaching_staffs = staffs

    # Remove from pool
    pool.remove(target)

    from engine.coaching import compute_dev_aura
    aura = compute_dev_aura(staffs[human_team])

    return {
        "hired": True,
        "coach": _serialize_coach_card(target),
        "role": req.role,
        "replaced": _serialize_coach_card(old_coach) if old_coach else None,
        "dev_aura": round(aura, 4),
    }


@app.get("/sessions/{session_id}/rivalries")
def get_rivalries(session_id: str):
    session = _get_session(session_id)
    season = session.get("season")
    dynasty = session.get("dynasty")
    if dynasty:
        return {"rivalries": dynasty.rivalries}
    elif season:
        return {"rivalries": season.rivalries}
    return {"rivalries": {}}


@app.post("/sessions/{session_id}/rivalries")
def set_rivalries(session_id: str, req: SetRivalriesRequest):
    session = _get_session(session_id)
    dynasty = session.get("dynasty")
    season = session.get("season")

    rivalry_update = {}
    if req.conference_rival is not None:
        rivalry_update["conference"] = req.conference_rival
    if req.non_conference_rival is not None:
        rivalry_update["non_conference"] = req.non_conference_rival

    if dynasty:
        if req.team not in dynasty.rivalries:
            dynasty.rivalries[req.team] = {"conference": None, "non_conference": None}
        dynasty.rivalries[req.team].update(rivalry_update)

    if season:
        if req.team not in season.rivalries:
            season.rivalries[req.team] = {"conference": None, "non_conference": None}
        season.rivalries[req.team].update(rivalry_update)

    updated = {}
    if dynasty:
        updated = dynasty.rivalries.get(req.team, {})
    elif season:
        updated = season.rivalries.get(req.team, {})

    return {"team": req.team, "rivalries": updated}


@app.get("/sessions/{session_id}/rivalry-history")
def get_rivalry_history(session_id: str):
    session = _get_session(session_id)
    dynasty = session.get("dynasty")
    if not dynasty:
        raise HTTPException(status_code=400, detail="Rivalry history only available in dynasty mode")
    return {"rivalry_ledger": dynasty.rivalry_ledger}


@app.get("/sessions/{session_id}/rivalry-history/{team}")
def get_team_rivalry_history(session_id: str, team: str):
    session = _get_session(session_id)
    dynasty = session.get("dynasty")
    if not dynasty:
        raise HTTPException(status_code=400, detail="Rivalry history only available in dynasty mode")
    team_rivalries = {}
    for key, entry in dynasty.rivalry_ledger.items():
        if team in key.split("|"):
            team_rivalries[key] = entry
    return {"team": team, "rivalry_history": team_rivalries}


# ═══════════════════════════════════════════════════════════════════════
# DRAFTYQUEENZ ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

class DQPickRequest(BaseModel):
    pick_type: str
    game_idx: int
    selection: str
    amount: int

class DQParlayLeg(BaseModel):
    pick_type: str
    game_idx: int
    selection: str

class DQParlayRequest(BaseModel):
    legs: List[DQParlayLeg]
    amount: int

class DQRosterSlotRequest(BaseModel):
    slot: str
    player_tag: str
    team_name: str

class DQDonateRequest(BaseModel):
    donation_type: str
    amount: int
    target_team: str = ""


def _require_dq(session: dict) -> DraftyQueenzManager:
    mgr = session.get("dq_manager")
    if mgr is None:
        raise HTTPException(status_code=400, detail="DraftyQueenz not active for this session")
    return mgr


def _get_prestige_map(session: dict) -> Dict[str, int]:
    dynasty = session.get("dynasty")
    if dynasty and dynasty.team_prestige:
        return dict(dynasty.team_prestige)
    season = session.get("season")
    if season:
        from engine.season import estimate_team_prestige_from_roster
        return {
            name: estimate_team_prestige_from_roster(t)
            for name, t in season.teams.items()
        }
    return {}


@app.get("/sessions/{session_id}/dq/status")
def dq_status(session_id: str):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    return {
        "bankroll": mgr.bankroll.balance,
        "peak_bankroll": mgr.peak_bankroll,
        "season_year": mgr.season_year,
        "total_earned": mgr.total_earned,
        "total_wagered": mgr.total_wagered,
        "total_donated": mgr.total_donated,
        "career_donated": mgr.career_donated,
        "pick_accuracy": mgr.pick_accuracy,
        "fantasy_top3_rate": mgr.fantasy_top3_rate,
        "roi": mgr.roi,
        "booster_tier": mgr.booster_tier[0],
        "booster_tier_desc": mgr.booster_tier[1],
        "next_tier": {"amount_needed": mgr.next_tier[0], "name": mgr.next_tier[1]} if mgr.next_tier else None,
        "active_boosts": mgr.get_active_boosts(),
        "recent_transactions": mgr.bankroll.history[-10:],
    }


@app.post("/sessions/{session_id}/dq/start-week/{week}")
def dq_start_week(session_id: str, week: int):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    season = _require_season(session)

    if week in mgr.weekly_contests:
        contest = mgr.weekly_contests[week]
        return {
            "week": week,
            "odds": [o.to_dict() for o in contest.odds],
            "pool_size": len(contest.player_pool),
            "already_started": True,
        }

    week_games = [g for g in season.schedule if g.week == week and not g.completed]
    if not week_games:
        raise HTTPException(status_code=400, detail=f"No unplayed games for week {week}")

    prestige_map = _get_prestige_map(session)
    standings_map = {r.team_name: r for r in season.get_standings_sorted()} if season.standings else None

    contest = mgr.start_week(week, week_games, season.teams, prestige_map, standings_map)

    return {
        "week": week,
        "odds": [o.to_dict() for o in contest.odds],
        "pool_size": len(contest.player_pool),
        "bankroll": mgr.bankroll.balance,
        "already_started": False,
    }


@app.get("/sessions/{session_id}/dq/contest/{week}")
def dq_get_contest(session_id: str, week: int):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    contest = mgr.weekly_contests.get(week)
    if contest is None:
        raise HTTPException(status_code=404, detail=f"No contest for week {week}")
    return contest.to_dict()


@app.get("/sessions/{session_id}/dq/odds/{week}")
def dq_get_odds(session_id: str, week: int):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    season = _require_season(session)
    contest = mgr.weekly_contests.get(week)
    if contest is None:
        raise HTTPException(status_code=404, detail=f"No contest for week {week}")

    prestige_map = _get_prestige_map(session)
    standings_map = {r.team_name: r for r in season.get_standings_sorted()} if season.standings else {}

    def _team_context(team_name: str) -> dict:
        """Build context dict for a team: record, prestige, star player."""
        ctx: dict = {"name": team_name}
        rec = standings_map.get(team_name)
        if rec:
            ctx["record"] = f"{rec.wins}-{rec.losses}"
        else:
            ctx["record"] = "0-0"
        ctx["prestige"] = prestige_map.get(team_name, 50)
        # Find the top player (highest overall) on this team
        team_obj = season.teams.get(team_name)
        if team_obj and team_obj.players:
            best = max(team_obj.players, key=lambda p: getattr(p, "overall", 0))
            ctx["star"] = getattr(best, "name", "")
            ctx["star_pos"] = getattr(best, "position", "")
            ctx["star_ovr"] = getattr(best, "overall", 0)
        return ctx

    odds_list = []
    for i, o in enumerate(contest.odds):
        d = o.to_dict()
        d["game_idx"] = i
        d["home_ml_display"] = format_moneyline(o.home_moneyline)
        d["away_ml_display"] = format_moneyline(o.away_moneyline)
        d["home_ctx"] = _team_context(o.home_team)
        d["away_ctx"] = _team_context(o.away_team)
        odds_list.append(d)
    return {"week": week, "odds": odds_list}


@app.post("/sessions/{session_id}/dq/pick/{week}")
def dq_place_pick(session_id: str, week: int, req: DQPickRequest):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    contest = mgr.weekly_contests.get(week)
    if contest is None:
        raise HTTPException(status_code=400, detail=f"No contest for week {week}. Start the week first.")
    if contest.resolved:
        raise HTTPException(status_code=400, detail="This week's contest is already resolved.")

    pick, err = contest.make_pick(mgr.bankroll, req.pick_type, req.game_idx, req.selection, req.amount)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {
        "pick": pick.to_dict(),
        "bankroll": mgr.bankroll.balance,
        "total_picks": len(contest.picks),
    }


@app.post("/sessions/{session_id}/dq/parlay/{week}")
def dq_place_parlay(session_id: str, week: int, req: DQParlayRequest):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    contest = mgr.weekly_contests.get(week)
    if contest is None:
        raise HTTPException(status_code=400, detail=f"No contest for week {week}.")
    if contest.resolved:
        raise HTTPException(status_code=400, detail="This week's contest is already resolved.")

    legs = [(l.pick_type, l.game_idx, l.selection) for l in req.legs]
    parlay, err = contest.make_parlay(mgr.bankroll, legs, req.amount)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {
        "parlay": parlay.to_dict(),
        "bankroll": mgr.bankroll.balance,
        "total_parlays": len(contest.parlays),
    }


@app.post("/sessions/{session_id}/dq/fantasy/enter/{week}")
def dq_enter_fantasy(session_id: str, week: int):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    contest = mgr.weekly_contests.get(week)
    if contest is None:
        raise HTTPException(status_code=400, detail=f"No contest for week {week}.")

    ok, err = mgr.enter_fantasy(week)
    if not ok:
        raise HTTPException(status_code=400, detail=err)
    return {
        "entered": True,
        "bankroll": mgr.bankroll.balance,
        "entry_fee": FANTASY_ENTRY_FEE,
    }


@app.get("/sessions/{session_id}/dq/fantasy/pool/{week}")
def dq_fantasy_pool(session_id: str, week: int, position: Optional[str] = None):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    contest = mgr.weekly_contests.get(week)
    if contest is None:
        raise HTTPException(status_code=404, detail=f"No contest for week {week}")

    pool = contest.player_pool
    if position:
        pool = [fp for fp in pool if fp.position_tag == position.upper()]

    # Add depth rank label for display context
    pool_data = []
    for fp in pool:
        depth_label = ""
        tag_num = "".join(c for c in fp.tag if c.isdigit())
        if tag_num:
            rank = int(tag_num)
            depth_label = ["Starter", "Backup", "3rd string"][min(rank - 1, 2)] if rank <= 3 else "Reserve"
        pool_data.append({
            "tag": fp.tag,
            "name": fp.name,
            "team": fp.team_name,
            "position": fp.position_tag,
            "position_name": POSITION_NAMES.get(fp.position_tag, fp.position_tag),
            "overall": fp.overall,
            "salary": fp.salary,
            "projected": round(fp.projected_pts, 1),
            "depth": depth_label,
        })

    return {
        "week": week,
        "pool": pool_data,
        "salary_cap": SALARY_CAP,
    }


@app.post("/sessions/{session_id}/dq/fantasy/set-slot/{week}")
def dq_set_roster_slot(session_id: str, week: int, req: DQRosterSlotRequest):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    contest = mgr.weekly_contests.get(week)
    if contest is None:
        raise HTTPException(status_code=400, detail=f"No contest for week {week}")
    if contest.user_roster is None:
        raise HTTPException(status_code=400, detail="Enter fantasy first before setting roster slots.")

    player = None
    for fp in contest.player_pool:
        if fp.tag == req.player_tag and fp.team_name == req.team_name:
            player = fp
            break
    if player is None:
        raise HTTPException(status_code=404, detail=f"Player {req.player_tag} ({req.team_name}) not found in pool.")

    err = contest.user_roster.set_slot(req.slot, player)
    if err:
        raise HTTPException(status_code=400, detail=err)

    return {
        "roster": contest.user_roster.to_dict(),
        "salary_remaining": SALARY_CAP - contest.user_roster.total_salary,
    }


@app.delete("/sessions/{session_id}/dq/fantasy/clear-slot/{week}/{slot}")
def dq_clear_roster_slot(session_id: str, week: int, slot: str):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    contest = mgr.weekly_contests.get(week)
    if contest is None:
        raise HTTPException(status_code=400, detail=f"No contest for week {week}")
    if contest.user_roster is None:
        raise HTTPException(status_code=400, detail="No fantasy roster to clear.")
    contest.user_roster.clear_slot(slot)
    return {"roster": contest.user_roster.to_dict(), "salary_remaining": SALARY_CAP - contest.user_roster.total_salary}


@app.get("/sessions/{session_id}/dq/fantasy/roster/{week}")
def dq_get_roster(session_id: str, week: int):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    contest = mgr.weekly_contests.get(week)
    if contest is None:
        raise HTTPException(status_code=404, detail=f"No contest for week {week}")
    if contest.user_roster is None:
        return {"entered": False, "roster": None}
    return {
        "entered": True,
        "roster": contest.user_roster.to_dict(),
        "salary_remaining": SALARY_CAP - contest.user_roster.total_salary,
    }


@app.post("/sessions/{session_id}/dq/resolve/{week}")
def dq_resolve_week(session_id: str, week: int):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    season = _require_season(session)
    contest = mgr.weekly_contests.get(week)
    if contest is None:
        raise HTTPException(status_code=400, detail=f"No contest for week {week}")
    if contest.resolved:
        return {
            "already_resolved": True,
            "prediction_earnings": contest.prediction_earnings,
            "fantasy_earnings": contest.fantasy_earnings,
            "jackpot_bonus": contest.jackpot_bonus,
            "bankroll": mgr.bankroll.balance,
        }

    week_games = [g for g in season.schedule if g.week == week and g.completed]
    if not week_games:
        raise HTTPException(status_code=400, detail=f"Week {week} games haven't been simulated yet.")

    game_results = {}
    for g in week_games:
        if g.full_result:
            key = f"{g.home_team} vs {g.away_team}"
            game_results[key] = g.full_result

    mgr.resolve_week(week, game_results)

    result = {
        "resolved": True,
        "prediction_earnings": contest.prediction_earnings,
        "fantasy_earnings": contest.fantasy_earnings,
        "jackpot_bonus": contest.jackpot_bonus,
        "bankroll": mgr.bankroll.balance,
        "picks": [p.to_dict() for p in contest.picks],
        "parlays": [p.to_dict() for p in contest.parlays],
    }

    if contest.user_roster:
        ai_scores = sorted([r.total_points for r in contest.ai_rosters], reverse=True)
        user_pts = contest.user_roster.total_points
        rank = sum(1 for s in ai_scores if s > user_pts) + 1
        result["fantasy_rank"] = rank
        result["fantasy_points"] = user_pts
        result["user_roster"] = contest.user_roster.to_dict()

    return result


@app.post("/sessions/{session_id}/dq/donate")
def dq_donate(session_id: str, req: DQDonateRequest):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    donation, err = mgr.donate(req.donation_type, req.amount, target_team=req.target_team)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {
        "donation": donation.to_dict(),
        "bankroll": mgr.bankroll.balance,
        "career_donated": mgr.career_donated,
        "booster_tier": mgr.booster_tier[0],
        "active_boosts": mgr.get_active_boosts(),
        "team_boosts": mgr.get_all_team_boosts(),
    }


@app.get("/sessions/{session_id}/dq/portfolio")
def dq_portfolio(session_id: str):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    tier_name, tier_desc = mgr.booster_tier
    next_info = mgr.next_tier
    boosts = mgr.get_active_boosts()

    boost_details = []
    for dtype, info in DONATION_TYPES.items():
        val = boosts.get(dtype, 0)
        pct = min(100, val / info["cap"] * 100) if info["cap"] > 0 else 0
        boost_details.append({
            "type": dtype,
            "label": info["label"],
            "description": info["description"],
            "current_value": round(val, 2),
            "cap": info["cap"],
            "progress_pct": round(pct, 1),
        })

    human_teams = session.get("human_teams", [])

    team_boost_details = {}
    all_team_boosts = mgr.get_all_team_boosts()
    for team_name in (list(all_team_boosts.keys()) + human_teams):
        if team_name in team_boost_details:
            continue
        team_boosts = mgr.get_active_boosts(team_name=team_name)
        details = []
        for dtype, info in DONATION_TYPES.items():
            val = team_boosts.get(dtype, 0)
            pct = min(100, val / info["cap"] * 100) if info["cap"] > 0 else 0
            details.append({
                "type": dtype,
                "label": info["label"],
                "description": info["description"],
                "current_value": round(val, 2),
                "cap": info["cap"],
                "progress_pct": round(pct, 1),
            })
        team_boost_details[team_name] = details

    return {
        "booster_tier": tier_name,
        "booster_tier_desc": tier_desc,
        "career_donated": mgr.career_donated,
        "next_tier": {"amount_needed": next_info[0], "name": next_info[1]} if next_info else None,
        "boosts": boost_details,
        "team_boosts": team_boost_details,
        "human_teams": human_teams,
        "donations": [d.to_dict() for d in mgr.donations],
        "donation_types": {
            k: {"label": v["label"], "description": v["description"], "per_10k": v["per_10k"], "cap": v["cap"]}
            for k, v in DONATION_TYPES.items()
        },
    }


@app.get("/sessions/{session_id}/dq/summary")
def dq_summary(session_id: str):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    return mgr.season_summary()
