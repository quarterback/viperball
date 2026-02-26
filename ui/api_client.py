"""
API client for the Viperball FastAPI backend.
Thin wrapper around requests that handles session management
and provides typed helper methods for all endpoints.

Performance features:
- Short-TTL cache for GET requests (avoids duplicate loopback calls
  within the same page render cycle)
- fetch_parallel() helper for concurrent initial page loads
"""

import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from typing import Dict, List, Optional, Any, Callable, Tuple

_default_port = os.environ.get("PORT", "5000")
API_BASE = os.environ.get("VIPERBALL_API_URL", f"http://127.0.0.1:{_default_port}")

# ---------------------------------------------------------------------------
# GET cache – avoids duplicate loopback HTTP calls within a render cycle.
# 2-second TTL is enough to deduplicate calls within a single page render
# without serving stale data across user actions.
# ---------------------------------------------------------------------------
_cache_lock = threading.Lock()
_cache: Dict[str, Tuple[float, Any]] = {}
_CACHE_TTL = 2.0  # seconds


def _cache_key(path: str, params: Optional[dict]) -> str:
    key = path
    if params:
        key += "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return key


def _cache_get(key: str) -> Optional[Any]:
    with _cache_lock:
        entry = _cache.get(key)
        if entry and (time.monotonic() - entry[0]) < _CACHE_TTL:
            return entry[1]
        _cache.pop(key, None)
    return None


def _cache_set(key: str, value: Any) -> None:
    with _cache_lock:
        _cache[key] = (time.monotonic(), value)


def invalidate_cache() -> None:
    """Clear the entire GET cache (call after mutations)."""
    with _cache_lock:
        _cache.clear()


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


def _request(method: str, path: str, params: Optional[dict] = None,
             json: Optional[Any] = None, timeout: int = 120) -> Any:
    try:
        resp = requests.request(method, _url(path), params=params, json=json, timeout=timeout)
    except requests.exceptions.ConnectionError:
        raise APIError(503, f"Cannot reach API at {API_BASE}")
    except requests.exceptions.Timeout:
        raise APIError(504, f"API request timed out: {path}")
    return _handle(resp)


def _get(path: str, params: Optional[dict] = None, timeout: int = 120) -> Any:
    key = _cache_key(path, params)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    result = _request("GET", path, params=params, timeout=timeout)
    _cache_set(key, result)
    return result


def _post(path: str, json: Optional[dict] = None, timeout: int = 300) -> Any:
    invalidate_cache()  # mutations invalidate the read cache
    return _request("POST", path, json=json, timeout=timeout)


def _put(path: str, json: Optional[Any] = None, timeout: int = 120) -> Any:
    invalidate_cache()
    return _request("PUT", path, json=json, timeout=timeout)


def _delete(path: str, timeout: int = 30) -> Any:
    invalidate_cache()
    return _request("DELETE", path, timeout=timeout)


# ---------------------------------------------------------------------------
# Parallel fetch helper – runs multiple API calls concurrently.
# Usage:
#   standings, status, conferences = fetch_parallel(
#       lambda: get_standings(sid),
#       lambda: get_season_status(sid),
#       lambda: get_conferences(sid),
#   )
# ---------------------------------------------------------------------------
_pool = ThreadPoolExecutor(max_workers=6)


def fetch_parallel(*calls: Callable[[], Any]) -> tuple:
    """Execute multiple API calls concurrently and return results in order."""
    if len(calls) == 1:
        return (calls[0](),)
    futures = [_pool.submit(fn) for fn in calls]
    return tuple(f.result() for f in futures)


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


def get_program_archetypes() -> dict:
    return _get("/program-archetypes")


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
                  history_years: int = 0,
                  pinned_matchups: Optional[List[List[str]]] = None,
                  team_archetypes: Optional[Dict[str, str]] = None,
                  rivalries: Optional[Dict[str, Dict[str, Optional[str]]]] = None) -> dict:
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
    if pinned_matchups:
        body["pinned_matchups"] = pinned_matchups
    if team_archetypes:
        body["team_archetypes"] = team_archetypes
    if rivalries is not None:
        body["rivalries"] = rivalries
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
                   num_conferences: int = 10, history_years: int = 0,
                   program_archetype: Optional[str] = None,
                   rivalries: Optional[Dict[str, Dict[str, Optional[str]]]] = None) -> dict:
    body = {
        "dynasty_name": dynasty_name,
        "coach_name": coach_name,
        "coach_team": coach_team,
        "starting_year": starting_year,
        "num_conferences": num_conferences,
        "history_years": history_years,
    }
    if program_archetype:
        body["program_archetype"] = program_archetype
    if rivalries is not None:
        body["rivalries"] = rivalries
    return _post(f"/sessions/{session_id}/dynasty", json=body)


def dynasty_start_season(session_id: str, games_per_team: int = 10,
                         playoff_size: int = 8, bowl_count: int = 4,
                         offense_style: str = "balanced",
                         defense_style: str = "swarm",
                         st_scheme: str = "aces",
                         ai_seed: Optional[int] = None,
                         pinned_matchups: Optional[List[List[str]]] = None,
                         program_archetype: Optional[str] = None,
                         rivalries: Optional[Dict[str, Dict[str, Optional[str]]]] = None) -> dict:
    body = {
        "games_per_team": games_per_team,
        "playoff_size": playoff_size,
        "bowl_count": bowl_count,
        "offense_style": offense_style,
        "defense_style": defense_style,
        "st_scheme": st_scheme,
    }
    if ai_seed is not None:
        body["ai_seed"] = ai_seed
    if pinned_matchups:
        body["pinned_matchups"] = pinned_matchups
    if program_archetype:
        body["program_archetype"] = program_archetype
    if rivalries is not None:
        body["rivalries"] = rivalries
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


def get_dynasty_coaching_history(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/dynasty/coaching-history")


def get_team_roster(session_id: str, team_name: str) -> dict:
    return _get(f"/sessions/{session_id}/team/{team_name}")


def get_team_schedule(session_id: str, team_name: str) -> list:
    return _get(f"/sessions/{session_id}/team/{team_name}/schedule")


def get_offseason_status(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/offseason/status")


def get_offseason_nil(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/offseason/nil")


def offseason_nil_allocate(session_id: str, recruiting_pool: float,
                           portal_pool: float, retention_pool: float) -> dict:
    return _post(f"/sessions/{session_id}/offseason/nil/allocate", json={
        "recruiting_pool": recruiting_pool,
        "portal_pool": portal_pool,
        "retention_pool": retention_pool,
    })


def get_offseason_portal(session_id: str, position: Optional[str] = None,
                         min_overall: Optional[int] = None) -> dict:
    params: dict = {}
    if position:
        params["position"] = position
    if min_overall is not None:
        params["min_overall"] = min_overall
    return _get(f"/sessions/{session_id}/offseason/portal", params=params)


def offseason_portal_offer(session_id: str, entry_index: int,
                           nil_amount: float = 0.0) -> dict:
    return _post(f"/sessions/{session_id}/offseason/portal/offer", json={
        "entry_index": entry_index,
        "nil_amount": nil_amount,
    })


def offseason_portal_commit(session_id: str, entry_index: int) -> dict:
    return _post(f"/sessions/{session_id}/offseason/portal/commit", json={
        "entry_index": entry_index,
    })


def offseason_portal_resolve(session_id: str) -> dict:
    return _post(f"/sessions/{session_id}/offseason/portal/resolve")


def get_offseason_recruiting(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/offseason/recruiting")


def offseason_recruiting_scout(session_id: str, recruit_index: int,
                               level: str = "basic") -> dict:
    return _post(f"/sessions/{session_id}/offseason/recruiting/scout", json={
        "recruit_index": recruit_index,
        "level": level,
    })


def offseason_recruiting_offer(session_id: str, recruit_index: int) -> dict:
    return _post(f"/sessions/{session_id}/offseason/recruiting/offer", json={
        "recruit_index": recruit_index,
    })


def offseason_recruiting_resolve(session_id: str) -> dict:
    return _post(f"/sessions/{session_id}/offseason/recruiting/resolve")


def offseason_complete(session_id: str) -> dict:
    return _post(f"/sessions/{session_id}/offseason/complete")


def season_portal_generate(session_id: str, human_team: str = "",
                           size: int = 40) -> dict:
    params: dict = {"size": size}
    if human_team:
        params["human_team"] = human_team
    return _post(f"/sessions/{session_id}/season/portal/generate", json=params)


def season_portal_get(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/season/portal")


def season_portal_commit(session_id: str, team_name: str,
                         entry_index: int) -> dict:
    return _post(f"/sessions/{session_id}/season/portal/commit",
                 json={"team_name": team_name, "entry_index": entry_index})


def season_portal_skip(session_id: str) -> dict:
    return _post(f"/sessions/{session_id}/season/portal/skip")


def season_coaching_staff_get(session_id: str, team: str = "") -> dict:
    params = {"team": team} if team else None
    return _get(f"/sessions/{session_id}/season/coaching-staff", params=params)


def season_coaching_pool_generate(session_id: str) -> dict:
    return _post(f"/sessions/{session_id}/season/coaching-staff/generate-pool")


def season_coaching_hire(session_id: str, coach_id: str, role: str) -> dict:
    return _post(f"/sessions/{session_id}/season/coaching-staff/hire",
                 json={"coach_id": coach_id, "role": role})


def simulate_quick_game(home: str, away: str,
                        home_offense: str = "balanced",
                        home_defense: str = "swarm",
                        home_st: str = "aces",
                        away_offense: str = "balanced",
                        away_defense: str = "swarm",
                        away_st: str = "aces",
                        weather: str = "clear",
                        seed: Optional[int] = None) -> dict:
    body = {
        "home": home, "away": away,
        "styles": {
            home: home_offense,
            f"{home}_defense": home_defense,
            f"{home}_st": home_st,
            away: away_offense,
            f"{away}_defense": away_defense,
            f"{away}_st": away_st,
        },
        "weather": weather,
    }
    if seed is not None:
        body["seed"] = seed
    return _post("/simulate", json=body)


def get_non_conference_opponents(team: str,
                                  conferences: Optional[str] = None,
                                  num_conferences: int = 10) -> dict:
    params: dict = {"team": team, "num_conferences": num_conferences}
    if conferences:
        params["conferences"] = conferences
    return _get("/non-conference-opponents", params=params)


def get_non_conference_slots(games_per_team: int = 10,
                              conference_size: int = 13) -> dict:
    return _get("/non-conference-slots", params={
        "games_per_team": games_per_team,
        "conference_size": conference_size,
    })


def get_dynasty_non_conference_opponents(session_id: str,
                                          team: Optional[str] = None,
                                          games_per_team: int = 10) -> dict:
    params: dict = {"games_per_team": games_per_team}
    if team:
        params["team"] = team
    return _get(f"/sessions/{session_id}/dynasty/non-conference-opponents", params=params)


def get_rivalries(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/rivalries")


def set_rivalry(session_id: str, team: str,
                conference_rival: Optional[str] = None,
                non_conference_rival: Optional[str] = None) -> dict:
    body: Dict[str, Any] = {"team": team}
    if conference_rival is not None:
        body["conference_rival"] = conference_rival
    if non_conference_rival is not None:
        body["non_conference_rival"] = non_conference_rival
    return _post(f"/sessions/{session_id}/rivalries", json=body)


# ── DraftyQueenz ──

def dq_status(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/dq/status")


def dq_start_week(session_id: str, week: int) -> dict:
    return _post(f"/sessions/{session_id}/dq/start-week/{week}")


def dq_get_contest(session_id: str, week: int) -> dict:
    return _get(f"/sessions/{session_id}/dq/contest/{week}")


def dq_get_odds(session_id: str, week: int) -> dict:
    return _get(f"/sessions/{session_id}/dq/odds/{week}")


def dq_place_pick(session_id: str, week: int, pick_type: str, game_idx: int, selection: str, amount: int) -> dict:
    return _post(f"/sessions/{session_id}/dq/pick/{week}", json={
        "pick_type": pick_type,
        "game_idx": game_idx,
        "selection": selection,
        "amount": amount,
    })


def dq_place_parlay(session_id: str, week: int, legs: list, amount: int) -> dict:
    return _post(f"/sessions/{session_id}/dq/parlay/{week}", json={
        "legs": legs,
        "amount": amount,
    })


def dq_enter_fantasy(session_id: str, week: int) -> dict:
    return _post(f"/sessions/{session_id}/dq/fantasy/enter/{week}")


def dq_fantasy_pool(session_id: str, week: int, position: Optional[str] = None) -> dict:
    params = {}
    if position:
        params["position"] = position
    return _get(f"/sessions/{session_id}/dq/fantasy/pool/{week}", params=params or None)


def dq_set_roster_slot(session_id: str, week: int, slot: str, player_tag: str, team_name: str) -> dict:
    return _post(f"/sessions/{session_id}/dq/fantasy/set-slot/{week}", json={
        "slot": slot,
        "player_tag": player_tag,
        "team_name": team_name,
    })


def dq_clear_roster_slot(session_id: str, week: int, slot: str) -> dict:
    return _delete(f"/sessions/{session_id}/dq/fantasy/clear-slot/{week}/{slot}")


def dq_get_roster(session_id: str, week: int) -> dict:
    return _get(f"/sessions/{session_id}/dq/fantasy/roster/{week}")


def dq_resolve_week(session_id: str, week: int) -> dict:
    return _post(f"/sessions/{session_id}/dq/resolve/{week}")


def dq_donate(session_id: str, donation_type: str, amount: int, target_team: str = "") -> dict:
    return _post(f"/sessions/{session_id}/dq/donate", json={
        "donation_type": donation_type,
        "amount": amount,
        "target_team": target_team,
    })


def dq_portfolio(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/dq/portfolio")


def dq_history(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/dq/history")


def dq_summary(session_id: str) -> dict:
    return _get(f"/sessions/{session_id}/dq/summary")


def dq_create_season(session_id: str, name: str = "DQ Fantasy Season",
                     ai_seed: int = 0, games_per_team: int = 12,
                     playoff_size: int = 8, bowl_count: int = 4) -> dict:
    return _post(f"/sessions/{session_id}/dq/create-season", json={
        "name": name,
        "ai_seed": ai_seed,
        "games_per_team": games_per_team,
        "playoff_size": playoff_size,
        "bowl_count": bowl_count,
    })


def dq_advance_week(session_id: str) -> dict:
    return _post(f"/sessions/{session_id}/dq/advance-week")


def pro_league_new(league: str) -> dict:
    return _post(f"/api/pro/{league}/new")


def pro_league_standings(league: str, session_id: str) -> dict:
    return _get(f"/api/pro/{league}/{session_id}/standings")


def pro_league_schedule(league: str, session_id: str) -> dict:
    return _get(f"/api/pro/{league}/{session_id}/schedule")


def pro_league_sim_week(league: str, session_id: str) -> dict:
    return _post(f"/api/pro/{league}/{session_id}/sim-week")


def pro_league_sim_all(league: str, session_id: str) -> dict:
    return _post(f"/api/pro/{league}/{session_id}/sim-all")


def pro_league_box_score(league: str, session_id: str, week: int, matchup: str) -> dict:
    return _get(f"/api/pro/{league}/{session_id}/game/{week}/{matchup}")


def pro_league_playoffs(league: str, session_id: str) -> dict:
    return _post(f"/api/pro/{league}/{session_id}/playoffs")


def pro_league_playoff_bracket(league: str, session_id: str) -> dict:
    return _get(f"/api/pro/{league}/{session_id}/playoffs/bracket")


def pro_league_stats(league: str, session_id: str, category: str = "all") -> dict:
    params = {"category": category} if category != "all" else None
    return _get(f"/api/pro/{league}/{session_id}/stats", params=params)


def pro_league_team_detail(league: str, session_id: str, team_key: str) -> dict:
    return _get(f"/api/pro/{league}/{session_id}/team/{team_key}")


def pro_league_active() -> dict:
    return _get("/api/pro/active")


def pro_league_status(league: str, session_id: str) -> dict:
    return _get(f"/api/pro/{league}/{session_id}/status")
