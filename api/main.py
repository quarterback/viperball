"""
Viperball Simulation API
FastAPI wrapper around the Viperball engine
"""

import sys
import os
from typing import Dict, List, Optional
from fastapi import FastAPI
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from engine import ViperballEngine, load_team_from_json, get_available_teams, get_available_styles, OFFENSE_STYLES


app = FastAPI(title="Viperball Simulation API", version="1.0.0")

TEAMS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams")


class SimulateRequest(BaseModel):
    home: str
    away: str
    seed: Optional[int] = None
    styles: Optional[Dict[str, str]] = None


class SimulateManyRequest(BaseModel):
    home: str
    away: str
    count: int = 10
    seed: Optional[int] = None
    styles: Optional[Dict[str, str]] = None


class DebugPlayRequest(BaseModel):
    style: str = "balanced"
    field_position: int = 40
    down: int = 2
    yards_to_go: int = 8


def _load_team(key: str):
    filepath = os.path.join(TEAMS_DIR, f"{key}.json")
    if not os.path.exists(filepath):
        cleaned = key.lower().replace(" ", "_").replace("-", "_")
        filepath = os.path.join(TEAMS_DIR, f"{cleaned}.json")
    return load_team_from_json(filepath)


@app.get("/teams")
def list_teams():
    teams = get_available_teams()
    styles = get_available_styles()
    return {"teams": teams, "styles": styles}


@app.post("/simulate")
def simulate(req: SimulateRequest):
    home_team = _load_team(req.home)
    away_team = _load_team(req.away)
    engine = ViperballEngine(home_team, away_team, seed=req.seed, style_overrides=req.styles)
    result = engine.simulate_game()
    return result


@app.post("/simulate_many")
def simulate_many(req: SimulateManyRequest):
    results = []
    for i in range(req.count):
        home_team = _load_team(req.home)
        away_team = _load_team(req.away)
        game_seed = (req.seed + i) if req.seed is not None else None
        engine = ViperballEngine(home_team, away_team, seed=game_seed, style_overrides=req.styles)
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
