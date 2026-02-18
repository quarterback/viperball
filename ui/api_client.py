"""
API client for the Viperball FastAPI backend.
Thin wrapper around requests that handles session management
and provides typed helper methods for all endpoints.
"""

import os
import requests
from typing import Dict, List, Optional, Any

API_BASE = os.environ.get("VIPERBALL_API_URL", "http://127.0.0.1:8000")


class APIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API {status_code}: {detail}")


def _url(path: str) -> str:
    return f"{API_BASE}{path}"


def _handle(resp: requests.Response) -> Any:
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise APIError(resp.status_code, detail)
    return resp.json()


def _get(path: str, params: Optional[dict] = None, timeout: int = 120) -> Any:
    return _handle(requests.get(_url(path), params=params, timeout=timeout))


def _post(path: str, json: Optional[dict] = None, timeout: int = 300) -> Any:
    return _handle(requests.post(_url(path), json=json, timeout=timeout))


def _put(path: str, json: Optional[Any] = None, timeout: int = 120) -> Any:
    return _handle(requests.put(_url(path), json=json, timeout=timeout))


def _delete(path: str, timeout: int = 30) -> Any:
    return _handle(requests.delete(_url(path), timeout=timeout))


def health() -> dict:
    return _get("/health")


def get_teams() -> dict:
    return _get("/teams")


def get_styles() -> dict:
    return _get("/styles")


def get_weather_conditions() -> list:
    return _get("/weather-conditions")


def get_conference_defaults() -> dict:
    return _get("/conference-defaults")


def get_bowl_tiers() -> list:
    return _get("/bowl-tiers")


def create_session() -> dict:
    return _post("/sessions")


def get_session(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}")


def delete_session(session_id: str) -> dict:
    return _delete(f"/sessions/{session_id}")


def create_season(session_id: str, name: str = "2026 CVL Season",
                  games_per_team: int = 10, playoff_size: int = 8,
                  bowl_count: int = 4, human_teams: Optional[List[str]] = None,
                  human_configs: Optional[Dict[str, Dict[str, str]]] = None,
                  num_conferences: int = 10, ai_seed: int = 0,
                  conferences: Optional[Dict[str, List[str]]] = None,
                  style_configs: Optional[Dict[str, Dict[str, str]]] = None,
                  history_years: int = 0) -> dict:
    body = {
        "name": name,
        "games_per_team": games_per_team,
        "playoff_size": playoff_size,
        "bowl_count": bowl_count,
        "human_teams": human_teams or [],
        "human_configs": human_configs or {},
        "num_conferences": num_conferences,
        "ai_seed": ai_seed,
        "history_years": history_years,
    }
    if conferences:
        body["conferences"] = conferences
    if style_configs:
        body["style_configs"] = style_configs
    return _post(f"/sessions/{session_id}/season", json=body)


def simulate_week(session_id: str, week: Optional[int] = None) -> dict:
    body = {"week": week} if week is not None else {}
    return _post(f"/sessions/{session_id}/season/simulate-week", json=body)


def simulate_through_week(session_id: str, target_week: int) -> dict:
    return _post(f"/sessions/{session_id}/season/simulate-through",
                 json={"target_week": target_week})


def simulate_rest(session_id: str) -> dict:
    return _post(f"/sessions/{session_id}/season/simulate-rest")


def run_playoffs(session_id: str) -> dict:
    return _post(f"/sessions/{session_id}/season/playoffs")


def run_bowls(session_id: str) -> dict:
    return _post(f"/sessions/{session_id}/season/bowls")


def get_season_status(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/season/status")


def get_season_history(session_id: str) -> list:
    data = _get(f"/sessions/{session_id}/season/history")
    return data.get("history", [])


def get_standings(session_id: str) -> list:
    return _get(f"/sessions/{session_id}/season/standings")


def get_injuries(session_id: str, team: Optional[str] = None) -> dict:
    params = {}
    if team:
        params["team"] = team
    return _get(f"/sessions/{session_id}/season/injuries", params=params)


def get_roster(session_id: str, team_name: str) -> dict:
    return _get(f"/sessions/{session_id}/season/roster/{team_name}")


def get_player_stats(session_id: str, conference: Optional[str] = None,
                     team: Optional[str] = None, position: Optional[str] = None,
                     min_touches: int = 0) -> dict:
    params: dict = {}
    if conference:
        params["conference"] = conference
    if team:
        params["team"] = team
    if position:
        params["position"] = position
    if min_touches > 0:
        params["min_touches"] = min_touches
    return _get(f"/sessions/{session_id}/season/player-stats", params=params)


def update_roster(session_id: str, team_name: str, updates: list) -> dict:
    return _put(f"/sessions/{session_id}/season/roster/{team_name}", json=updates)


def get_schedule(session_id: str, week: Optional[int] = None,
                 team: Optional[str] = None,
                 completed_only: bool = False,
                 include_full_result: bool = False) -> dict:
    params = {}
    if week is not None:
        params["week"] = week
    if team:
        params["team"] = team
    if completed_only:
        params["completed_only"] = "true"
    if include_full_result:
        params["include_full_result"] = "true"
    return _get(f"/sessions/{session_id}/season/schedule", params=params)


def get_polls(session_id: str, week: Optional[int] = None) -> list:
    params = {"week": week} if week is not None else {}
    return _get(f"/sessions/{session_id}/season/polls", params=params)


def get_conferences(session_id: str) -> dict:
    resp = _get(f"/sessions/{session_id}/season/conferences")
    simple_conferences = {}
    for conf_name, conf_data in resp.get("conferences", {}).items():
        simple_conferences[conf_name] = conf_data.get("teams", [])
    return {"conferences": simple_conferences, "champions": resp.get("champions", {})}


def get_conference_standings(session_id: str) -> dict:
    resp = _get(f"/sessions/{session_id}/season/conferences")
    conference_standings = {}
    for conf_name, conf_data in resp.get("conferences", {}).items():
        conference_standings[conf_name] = conf_data.get("standings", [])
    return {"conference_standings": conference_standings, "champions": resp.get("champions", {})}


def get_power_rankings(session_id: str) -> list:
    return _get(f"/sessions/{session_id}/season/power-rankings")


def get_playoff_bracket(session_id: str) -> list:
    return _get(f"/sessions/{session_id}/season/playoff-bracket")


def get_bowl_results(session_id: str) -> list:
    return _get(f"/sessions/{session_id}/season/bowl-results")


def create_dynasty(session_id: str, dynasty_name: str, coach_name: str,
                   coach_team: str, starting_year: int = 2026,
                   num_conferences: int = 10, history_years: int = 0) -> dict:
    body = {
        "dynasty_name": dynasty_name,
        "coach_name": coach_name,
        "coach_team": coach_team,
        "starting_year": starting_year,
        "num_conferences": num_conferences,
        "history_years": history_years,
    }
    return _post(f"/sessions/{session_id}/dynasty", json=body)


def dynasty_start_season(session_id: str, games_per_team: int = 10,
                         playoff_size: int = 8, bowl_count: int = 4,
                         offense_style: str = "balanced",
                         defense_style: str = "base_defense",
                         ai_seed: Optional[int] = None) -> dict:
    body = {
        "games_per_team": games_per_team,
        "playoff_size": playoff_size,
        "bowl_count": bowl_count,
        "offense_style": offense_style,
        "defense_style": defense_style,
    }
    if ai_seed is not None:
        body["ai_seed"] = ai_seed
    return _post(f"/sessions/{session_id}/dynasty/start-season", json=body)


def dynasty_advance(session_id: str) -> dict:
    return _post(f"/sessions/{session_id}/dynasty/advance")


def get_dynasty_status(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/dynasty/status")


def get_dynasty_team_histories(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/dynasty/team-histories")


def get_dynasty_awards(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/dynasty/awards")


def get_dynasty_record_book(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/dynasty/record-book")


def get_season_awards(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/season/awards")


def get_team_roster(session_id: str, team_name: str) -> dict:
    return _get(f"/sessions/{session_id}/team/{team_name}")


def get_team_schedule(session_id: str, team_name: str) -> list:
    return _get(f"/sessions/{session_id}/team/{team_name}/schedule")


def simulate_quick_game(home: str, away: str,
                        home_offense: str = "balanced",
                        home_defense: str = "base_defense",
                        away_offense: str = "balanced",
                        away_defense: str = "base_defense",
                        weather: str = "clear",
                        seed: Optional[int] = None) -> dict:
    body = {
        "home": home, "away": away,
        "styles": {
            home: home_offense,
            f"{home}_defense": home_defense,
            away: away_offense,
            f"{away}_defense": away_defense,
        },
        "weather": weather,
    }
    if seed is not None:
        body["seed"] = seed
    return _post("/simulate", json=body)
