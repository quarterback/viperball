"""
Viperball Simulation API
FastAPI wrapper around the Viperball engine
"""

import json
import sys
import os
import uuid
import time
import random
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from dataclasses import asdict
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def _load_pixellab_key() -> str:
    """Return the PixelLab API key from environment (set via Fly.io secrets)."""
    return os.environ.get("PIXELLAB_API_KEY", "")
# --- Core engine imports (loaded eagerly via engine/__init__.py) ---
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
from engine.player_card import player_to_card
from engine.ai_coach import auto_assign_all_teams, get_scheme_label, load_team_identity
from engine.game_engine import WEATHER_CONDITIONS, DEFENSE_STYLES, POSITION_TAGS, Player, assign_archetype, ST_SCHEMES

# --- Deferred imports (loaded on first use to speed up startup) ---
# engine.pro_league, engine.draftyqueenz, engine.recruiting,
# engine.transfer_portal, engine.nil_system, engine.injuries,
# engine.awards, engine.db, engine.conference_names, engine.geography,
# scripts.generate_rosters — all imported inside endpoint functions.


app = FastAPI(title="Viperball Simulation API", version="1.0.0")


from starlette.responses import RedirectResponse as StarletteRedirect


# Pure ASGI middleware instead of BaseHTTPMiddleware — avoids interfering
# with WebSocket upgrade requests (known Starlette BaseHTTPMiddleware issue).
class DomainRedirectMiddleware:
    """Redirect viperball.xyz root to the stats site."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            host = headers.get(b"host", b"").decode().split(":")[0]
            if host == "viperball.xyz" and scope["path"] == "/":
                response = StarletteRedirect("/stats/", status_code=302)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


app.add_middleware(DomainRedirectMiddleware)

# Mount the stats site as a sub-application so its Mount entry takes
# precedence over NiceGUI's catch-all Mount("").  With include_router the
# individual APIRoutes were checked first but /stats (no trailing slash)
# fell through to NiceGUI before the redirect-slashes logic could fire.
from stats_site.router import router as stats_router
from fastapi.responses import RedirectResponse, StreamingResponse

# Redirect /stats → /stats/ (this APIRoute is checked before the Mount below)
@app.get("/stats", include_in_schema=False)
def _stats_redirect():
    return RedirectResponse("/stats/", status_code=301)

_stats_app = FastAPI()
_stats_app.include_router(stats_router)

# Serve generated pixel-art face images at /stats/static/faces/<player_id>.png
from starlette.staticfiles import StaticFiles as _StaticFiles
_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stats_site", "static")
os.makedirs(os.path.join(_STATIC_DIR, "faces"), exist_ok=True)
_stats_app.mount("/static", _StaticFiles(directory=_STATIC_DIR), name="stats-static")

app.mount("/stats", _stats_app)

TEAMS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams")

sessions: Dict[str, dict] = {}
pro_sessions: dict = {}
_pro_session_accessed: Dict[str, float] = {}
wvl_sessions: Dict[str, dict] = {}  # session_id → {"season": WVLMultiTierSeason, "dynasty": WVLDynasty}

SESSION_TTL_SECONDS = 4 * 3600   # 4 hours
SESSION_CLEANUP_INTERVAL = 600   # check every 10 minutes
MAX_SESSIONS = 50                # hard cap per session type

_sim_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="sim")
logger = logging.getLogger("viperball.api")

_league_configs: dict | None = None


def _get_league_configs() -> dict:
    global _league_configs
    if _league_configs is None:
        from engine.pro_league import ALL_LEAGUE_CONFIGS
        _league_configs = dict(ALL_LEAGUE_CONFIGS)
    return _league_configs


@app.get("/api/health")
def health_check():
    """Health check endpoint for Fly.io deployment monitoring.

    Avoids calling get_available_teams() which reads ~199 JSON files from disk,
    blocking the single uvicorn worker and causing request timeouts.
    """
    import resource
    mem_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "status": "ok",
        "sessions": len(sessions),
        "pro_sessions": len(pro_sessions),
        "wvl_sessions": len(wvl_sessions),
        "memory_mb": round(mem_kb / 1024, 1),
    }


async def _session_cleanup_loop():
    """Periodically evict sessions that have not been accessed within the TTL."""
    while True:
        await asyncio.sleep(SESSION_CLEANUP_INTERVAL)
        now = time.time()
        # CVL sessions
        expired = [sid for sid, s in sessions.items()
                   if now - s.get("last_accessed", s.get("created_at", 0)) > SESSION_TTL_SECONDS]
        for sid in expired:
            del sessions[sid]
        # Pro sessions
        expired_pro = [key for key, ts in _pro_session_accessed.items()
                       if now - ts > SESSION_TTL_SECONDS]
        for key in expired_pro:
            pro_sessions.pop(key, None)
            _pro_session_accessed.pop(key, None)
        # WVL sessions
        expired_wvl = [sid for sid, s in wvl_sessions.items()
                       if now - s.get("last_accessed", s.get("created_at", 0)) > SESSION_TTL_SECONDS]
        for sid in expired_wvl:
            del wvl_sessions[sid]
        total = len(expired) + len(expired_pro) + len(expired_wvl)
        if total:
            logger.info("Session cleanup: evicted %d cvl, %d pro, %d wvl",
                        len(expired), len(expired_pro), len(expired_wvl))


@app.on_event("startup")
async def _start_session_cleanup():
    asyncio.create_task(_session_cleanup_loop())


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
    conferences: Optional[Dict[str, List[str]]] = None
    games_per_team: int = 12
    playoff_size: int = 8
    bowl_count: int = 4


class SimulateWeekRequest(BaseModel):
    week: Optional[int] = None
    fast_sim: bool = True


class SimulateThroughRequest(BaseModel):
    target_week: int
    fast_sim: bool = True


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
    pool_size: int = 1500


# ── My Team Roster Builder Request Models ──

class MyTeamInitRequest(BaseModel):
    """Initialize the roster builder for a human team."""
    team_name: str
    session_id: str = ""  # optional, will find active session if empty


class MyTeamRetainRequest(BaseModel):
    """Lock down an at-risk player with NIL retention money."""
    player_id: str
    amount: float


class MyTeamPortalBidRequest(BaseModel):
    """Place a bid on a portal player."""
    entry_index: int
    nil_amount: float


class MyTeamPortalAdvanceRequest(BaseModel):
    """Advance the portal clock to the next round."""
    pass


class MyTeamRecruitScoutRequest(BaseModel):
    """Scout a HS recruit."""
    recruit_id: str
    level: str = "basic"  # "basic" or "full"


class MyTeamRecruitOfferRequest(BaseModel):
    """Offer a scholarship + NIL to a HS recruit."""
    recruit_id: str
    nil_amount: float = 0.0


def _load_team(key: str):
    filepath = os.path.join(TEAMS_DIR, f"{key}.json")
    if not os.path.exists(filepath):
        cleaned = key.lower().replace(" ", "_").replace("-", "_")
        filepath = os.path.join(TEAMS_DIR, f"{cleaned}.json")
    return load_team_from_json(filepath)


def _get_session(session_id: str) -> dict:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    sessions[session_id]["last_accessed"] = time.time()
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
        # Fan-friendly analytics
        "avg_team_rating": round(rec.avg_team_rating, 2),
        "avg_ppd": round(rec.avg_ppd, 2),
        "avg_conversion_pct": round(rec.avg_conversion_pct, 2),
        "avg_lateral_pct": round(rec.avg_lateral_pct, 2),
        "avg_explosive": round(rec.avg_explosive, 2),
        "avg_to_margin": round(rec.avg_to_margin, 2),
        "avg_start_position": round(rec.avg_start_position, 2),
        # Legacy aliases
        "avg_opi": round(rec.avg_opi, 2),
        "avg_territory": round(rec.avg_territory, 2),
        "avg_pressure": round(rec.avg_pressure, 2),
        "avg_chaos": round(rec.avg_chaos, 2),
        "avg_kicking": round(rec.avg_kicking, 2),
        "ties": getattr(rec, "ties", 0),
        "conf_wins": rec.conf_wins,
        "conf_losses": rec.conf_losses,
        "conf_ties": getattr(rec, "conf_ties", 0),
        "conf_win_percentage": round(rec.conf_win_percentage, 4),
        "avg_drive_quality": round(getattr(rec, 'avg_drive_quality', 0), 2),
        "avg_turnover_impact": round(getattr(rec, 'avg_turnover_impact', 0), 2),
        "offense_style": getattr(rec, 'offense_style', ''),
        "defense_style": getattr(rec, 'defense_style', ''),
        "dye": rec.dye_season_summary if hasattr(rec, 'dye_season_summary') else None,
        # Conversion-by-zone and delta analytics
        "season_5d_pct": round(rec.season_5d_pct, 1) if hasattr(rec, 'season_5d_pct') else 0.0,
        "season_5d_own_deep_pct": round(rec.season_5d_own_deep_pct, 1) if hasattr(rec, 'season_5d_own_deep_pct') else 0.0,
        "season_kill_pct": round(rec.season_kill_pct, 1) if hasattr(rec, 'season_kill_pct') else 0.0,
        "avg_delta_yds": round(rec.avg_delta_yds, 1) if hasattr(rec, 'avg_delta_yds') else 0.0,
        "conversion_by_zone": rec.season_conversion_by_zone if hasattr(rec, 'season_conversion_by_zone') else {},
        # KenPom-style efficiency metrics
        "kenpom": rec.kenpom_metrics() if hasattr(rec, 'kenpom_metrics') else {},
        # DTW (Deserve to Win) luck metrics
        "dtw": {
            "expected_wins": round(getattr(rec, 'dtw_expected_wins', 0.0), 1),
            "luck_differential": round(getattr(rec, 'dtw_luck_differential', 0.0), 1),
            "lucky_wins": getattr(rec, 'dtw_lucky_wins', 0),
            "unlucky_losses": getattr(rec, 'dtw_unlucky_losses', 0),
            "expected_win_pct": round(getattr(rec, 'dtw_expected_win_pct', 0.0), 3),
            "avg_pk_efficiency": round(getattr(rec, 'dtw_avg_pk_efficiency', 1.0), 2),
            "avg_mess_rate": round(getattr(rec, 'dtw_avg_mess_rate', 0.0), 1),
            "dtw_record": getattr(rec, 'dtw_record', "0.0-0.0"),
        },
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
        # DTW (Deserve to Win)
        "home_dtw": getattr(game, 'home_dtw', None),
        "away_dtw": getattr(game, 'away_dtw', None),
        "dtw_upset": getattr(game, 'dtw_result', {}).get("upset") if getattr(game, 'dtw_result', None) else None,
        "dtw_deserved_winner": getattr(game, 'dtw_result', {}).get("deserved_winner") if getattr(game, 'dtw_result', None) else None,
        "dtw_result": getattr(game, 'dtw_result', None),
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

    # Count history years from team season_records (years before current_year
    # that exist in any team's history but aren't in dynasty.seasons)
    history_years = 0
    if dynasty.team_histories:
        sample_team = next(iter(dynasty.team_histories.values()))
        history_years = sum(
            1 for yr in sample_team.season_records if yr < dynasty.current_year and yr not in dynasty.seasons
        )

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
            "playoff_wins": getattr(coach, "playoff_wins", 0),
            "conference_titles": getattr(coach, "conference_titles", 0),
            "bowl_wins": getattr(coach, "bowl_wins", 0),
            "bowl_appearances": getattr(coach, "bowl_appearances", 0),
            "years_coached": len(coach.years_coached),
            "years_experience": coach.years_experience,
            "season_records": sr,
        },
        "team_count": team_count,
        "seasons_played": seasons_played,
        "history_years": history_years,
        "phase": session.get("phase", "setup"),
        "conferences": conf_dict,
        "games_per_team": dynasty.games_per_team,
        "playoff_size": dynasty.playoff_size,
        "bowl_count": dynasty.bowl_count,
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
    from engine.geography import get_geographic_conference_defaults
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
    from engine.geography import get_geographic_conference_defaults
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
    from scripts.generate_rosters import PROGRAM_ARCHETYPES
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
async def simulate(req: SimulateRequest):
    home_team = _load_team(req.home)
    away_team = _load_team(req.away)
    engine = ViperballEngine(home_team, away_team, seed=req.seed, style_overrides=req.styles, weather=req.weather)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(_sim_executor, engine.simulate_game)
    return result


@app.post("/simulate_many")
async def simulate_many(req: SimulateManyRequest):
    def _do_sim():
        results = []
        for i in range(req.count):
            home_team = _load_team(req.home)
            away_team = _load_team(req.away)
            game_seed = (req.seed + i) if req.seed is not None else None
            engine = ViperballEngine(home_team, away_team, seed=game_seed, style_overrides=req.styles, weather=req.weather)
            result = engine.simulate_game()
            results.append(result)
        return results

    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(_sim_executor, _do_sim)

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


def _persist_box_scores(session_id: str, games):
    """Save full_result data for completed games to the database.

    Called after simulation endpoints so box scores survive server restarts.
    Runs synchronously (SQLite writes are fast) and is safe to call with
    games that have no full_result — they are skipped.
    """
    try:
        from engine.db import save_box_scores_bulk
        save_box_scores_bulk(session_id, games)
    except Exception:
        logger.debug("Box score persistence skipped (db unavailable)", exc_info=True)


@app.post("/sessions")
def create_session():
    # Evict oldest session if at capacity
    if len(sessions) >= MAX_SESSIONS:
        oldest_sid = min(sessions, key=lambda s: sessions[s].get("last_accessed", sessions[s].get("created_at", 0)))
        del sessions[oldest_sid]
        try:
            from engine.db import delete_box_scores_for_session
            delete_box_scores_for_session(oldest_sid)
        except Exception:
            pass
        logger.info("Evicted oldest session %s (cap=%d)", oldest_sid, MAX_SESSIONS)

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
        "last_accessed": now,
    }
    return {"session_id": session_id, "created_at": now}


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    del sessions[session_id]
    # Clean up persisted box scores for this session
    try:
        from engine.db import delete_box_scores_for_session
        delete_box_scores_for_session(session_id)
    except Exception:
        pass
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
    from engine.geography import get_geographic_conference_defaults
    from engine.injuries import InjuryTracker
    from engine.draftyqueenz import DraftyQueenzManager
    from engine.transfer_portal import estimate_prestige_from_roster, generate_quick_portal
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
        raw_history = fast_generate_history(
            teams=teams,
            conferences=conferences,
            num_years=history_years,
            games_per_team=req.games_per_team,
            playoff_size=req.playoff_size,
            base_seed=req.ai_seed if req.ai_seed else 42,
        )
        # Strip internal fields (not JSON-serializable / not needed by clients)
        history_results = [
            {k: v for k, v in entry.items() if not k.startswith("_")}
            for entry in raw_history
        ]

    session["season"] = season
    session["human_teams"] = req.human_teams or []
    season.human_teams = list(req.human_teams or [])
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
async def simulate_week(session_id: str, req: SimulateWeekRequest):
    session = _get_session(session_id)
    season = _require_season(session)

    if session["phase"] not in ("regular",):
        raise HTTPException(status_code=400, detail=f"Cannot simulate week in phase '{session['phase']}'")

    week = req.week
    dq_mgr = session.get("dq_manager")
    dq_boosts = dq_mgr.get_all_team_boosts() if dq_mgr else None

    loop = asyncio.get_event_loop()
    games = await loop.run_in_executor(
        _sim_executor,
        lambda: season.simulate_week(week=week, dq_team_boosts=dq_boosts, use_fast_sim=req.fast_sim),
    )

    if not games:
        return {"week": week, "games": [], "message": "No games to simulate"}

    actual_week = games[0].week

    _persist_box_scores(session_id, games)

    if season.is_regular_season_complete():
        bowl_count = session["config"].get("bowl_count", 4)
        session["phase"] = "bowls_pending" if bowl_count > 0 else "playoffs_pending"

    return {
        "week": actual_week,
        "games": [_serialize_game(g) for g in games],
        "games_count": len(games),
        "season_complete": season.is_regular_season_complete(),
        "phase": session["phase"],
        "engine": "fast_sim" if req.fast_sim else "full",
    }


@app.post("/sessions/{session_id}/season/simulate-through")
async def simulate_through(session_id: str, req: SimulateThroughRequest):
    session = _get_session(session_id)
    season = _require_season(session)

    if session["phase"] not in ("regular",):
        raise HTTPException(status_code=400, detail=f"Cannot simulate in phase '{session['phase']}'")

    loop = asyncio.get_event_loop()
    all_games = await loop.run_in_executor(
        _sim_executor,
        lambda: season.simulate_through_week(req.target_week, use_fast_sim=req.fast_sim),
    )

    _persist_box_scores(session_id, all_games)

    if season.is_regular_season_complete():
        bowl_count = session["config"].get("bowl_count", 4)
        session["phase"] = "bowls_pending" if bowl_count > 0 else "playoffs_pending"

    return {
        "games": [_serialize_game(g) for g in all_games],
        "games_count": len(all_games),
        "season_complete": season.is_regular_season_complete(),
        "phase": session["phase"],
        "engine": "fast_sim" if req.fast_sim else "full",
    }


class SimulateRestRequest(BaseModel):
    fast_sim: bool = True


@app.post("/sessions/{session_id}/season/simulate-rest")
async def simulate_rest(session_id: str, req: SimulateRestRequest = SimulateRestRequest()):
    session = _get_session(session_id)
    season = _require_season(session)

    if session["phase"] not in ("regular",):
        raise HTTPException(status_code=400, detail=f"Cannot simulate rest in phase '{session['phase']}'")

    def _do_sim():
        games_before = sum(1 for g in season.schedule if g.completed)
        season.simulate_season(generate_polls=True, use_fast_sim=req.fast_sim)
        return sum(1 for g in season.schedule if g.completed) - games_before

    loop = asyncio.get_event_loop()
    games_simulated = await loop.run_in_executor(_sim_executor, _do_sim)

    _persist_box_scores(session_id, season.schedule)

    bowl_count = session["config"].get("bowl_count", 4)
    session["phase"] = "bowls_pending" if bowl_count > 0 else "playoffs_pending"

    return {
        "games_simulated": games_simulated,
        "total_games": len(season.schedule),
        "phase": session["phase"],
        "status": _serialize_season_status(session),
        "engine": "fast_sim" if req.fast_sim else "full",
    }


@app.post("/sessions/{session_id}/season/bowls")
async def run_bowls(session_id: str):
    session = _get_session(session_id)
    season = _require_season(session)

    if session["phase"] not in ("bowls_pending",):
        raise HTTPException(status_code=400, detail=f"Cannot run bowls in phase '{session['phase']}'")

    bowl_count = session["config"].get("bowl_count", 4)
    playoff_size = session["config"].get("playoff_size", 8)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        _sim_executor,
        lambda: season.simulate_bowls(bowl_count=bowl_count, playoff_size=playoff_size),
    )

    _persist_box_scores(session_id, [bg.game for bg in season.bowl_games])

    session["phase"] = "playoffs_pending"

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


@app.post("/sessions/{session_id}/season/playoffs")
async def run_playoffs(session_id: str):
    session = _get_session(session_id)
    season = _require_season(session)

    if session["phase"] not in ("playoffs_pending",):
        raise HTTPException(status_code=400, detail=f"Cannot run playoffs in phase '{session['phase']}'")

    playoff_size = session["config"].get("playoff_size", 8)
    effective_size = min(playoff_size, len(season.teams))
    if effective_size < 4:
        raise HTTPException(status_code=400, detail="Not enough teams for playoffs")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        _sim_executor,
        lambda: season.simulate_playoff(num_teams=effective_size),
    )

    _persist_box_scores(session_id, season.playoff_bracket)

    session["phase"] = "complete"

    bracket = [_serialize_game(g) for g in season.playoff_bracket]
    return {
        "champion": season.champion,
        "bracket": bracket,
        "phase": session["phase"],
    }


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


@app.get("/sessions/{session_id}/season/dtw")
def season_dtw(session_id: str, team: Optional[str] = Query(None),
               sort_by: str = Query("luck_differential")):
    """Deserve to Win — season luck rankings.

    Shows which teams have been lucky or unlucky based on delta-adjusted
    performance quality.  The DTW model strips out the DYE system's
    distortions to reveal who truly played better in each game.

    Query params:
      team:    Filter to a single team's DTW game log
      sort_by: luck_differential (default), expected_wins, lucky_wins,
               unlucky_losses, avg_pk_efficiency, avg_mess_rate
    """
    from engine.dtw import (calculate_game_dtw, calculate_season_luck,
                            get_luck_rankings, calculate_model_accuracy,
                            get_extreme_teams, get_team_dtw_log,
                            generate_dtw_headline)

    session = _get_session(session_id)
    season = _require_season(session)

    # Collect DTW results from all completed games
    game_dtw_results = []
    for game in season.schedule:
        if game.completed and getattr(game, 'dtw_result', None):
            game_dtw_results.append(game.dtw_result)

    if not game_dtw_results:
        return {"error": "No completed games with DTW data yet."}

    if team:
        game_log = get_team_dtw_log(game_dtw_results, team)
        team_luck = calculate_season_luck(game_dtw_results).get(team, {})
        return {
            "team": team,
            "luck": team_luck,
            "game_log": game_log,
        }

    rankings = get_luck_rankings(game_dtw_results, sort_by=sort_by)
    accuracy = calculate_model_accuracy(game_dtw_results)
    extremes = get_extreme_teams(game_dtw_results)

    return {
        "rankings": rankings,
        "model_accuracy": accuracy,
        "extremes": extremes,
        "games_analyzed": len(game_dtw_results),
    }


@app.get("/sessions/{session_id}/season/dtw/game/{week}")
def season_dtw_game(session_id: str, week: int,
                    home: Optional[str] = Query(None)):
    """DTW detail for a specific game by week (and optionally home team)."""
    from engine.dtw import generate_dtw_headline

    session = _get_session(session_id)
    season = _require_season(session)

    for game in season.schedule:
        if game.week == week and game.completed:
            if home and game.home_team != home:
                continue
            dtw = getattr(game, 'dtw_result', None)
            if dtw:
                return {
                    "game": _serialize_game(game),
                    "dtw": dtw,
                    "headline": generate_dtw_headline(dtw),
                }
    return {"error": f"No completed game found for week {week}"}


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


@app.get("/sessions/{session_id}/season/referees")
def season_referees(session_id: str, name: Optional[str] = Query(None)):
    """List all referees or get a specific referee's card."""
    session = _get_session(session_id)
    season = _require_season(session)
    pool = getattr(season, 'referee_pool', None)
    if pool is None:
        return {"referees": [], "total": 0}

    if name:
        card = pool.get_card(name)
        if card is None:
            return {"error": f"Referee '{name}' not found"}
        return {"referee": card.to_dict()}
    else:
        # Return all refs with game activity, sorted by games officiated
        active_refs = [c.to_dict() for c in pool.get_all_cards() if c.career_games > 0]
        return {
            "referees": active_refs,
            "total": len(pool.cards),
            "active": len(active_refs),
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
                        "rush_carries": 0,
                        "yards": 0,
                        "rushing_yards": 0,
                        "rushing_tds": 0,
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
                    "touches", "rush_carries", "yards", "rushing_yards",
                    "rushing_tds", "lateral_yards",
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
        r["yards_per_carry"] = round(r["rushing_yards"] / max(1, r["rush_carries"]), 1)
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


def _apply_awards_to_players(season, honors) -> None:
    """Write computed awards onto Player objects so roster endpoints include them."""
    # Build player lookup: (team_name, player_name) -> Player
    player_lookup = {}
    for team_name, team in season.teams.items():
        for p in team.players:
            player_lookup[(team_name, p.name)] = p

    for winner, level in honors.all_winners():
        key = (winner.team_name, winner.player_name)
        player = player_lookup.get(key)
        if player is not None:
            if not hasattr(player, "career_awards"):
                player.career_awards = []
            # Avoid duplicates on repeated endpoint calls
            entry = {"year": honors.year, "award": winner.award_name, "level": level,
                     "team": winner.team_name, "position": winner.position}
            if entry not in player.career_awards:
                player.career_awards.append(entry)


@app.get("/sessions/{session_id}/season/awards")
def season_awards(session_id: str):
    from engine.awards import compute_season_awards
    session = _get_session(session_id)
    season = _require_season(session)

    try:
        conf_dict = season.conferences if hasattr(season, 'conferences') else None
        season_honors = compute_season_awards(
            season, year=2025,
            conferences=conf_dict,
        )
        # Compute media awards (AP, UPI, The Lateral, TSN)
        try:
            from engine.media_awards import compute_media_awards
            media = compute_media_awards(season=season, year=2025, conferences=conf_dict)
            season_honors.media_awards = media
        except Exception:
            pass  # media awards are non-critical

        # Append awards to Player objects so roster/player-card endpoints can
        # display them (single-season mode has no dynasty card sync).
        _apply_awards_to_players(season, season_honors)

        result = season_honors.to_dict()
        return result
    except Exception as e:
        return {"individual_awards": [], "coach_of_year": None, "most_improved": None, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# SEASON ARCHIVES — persist completed season data to SQLite
# ═══════════════════════════════════════════════════════════════

def _build_college_archive(session: dict, session_id: str) -> dict:
    """Build a self-contained archive snapshot of a college season."""
    from engine.awards import compute_season_awards
    season = _require_season(session)

    standings = _serialize_standings(season)
    schedule = [_serialize_game(g, include_full_result=True) for g in season.schedule]

    polls = []
    prestige_map = {}
    dynasty = session.get("dynasty")
    if dynasty and hasattr(dynasty, "team_prestige"):
        prestige_map = dynasty.team_prestige or {}
    for p in season.weekly_polls:
        polls.append(_serialize_poll(p, prestige_map=prestige_map))

    # Conferences
    conferences = {}
    if season.conferences:
        for conf_name, conf_teams in season.conferences.items():
            conferences[conf_name] = list(conf_teams)

    # Bowl games
    bowl_games = []
    for bg in season.bowl_games:
        bowl_games.append({
            "name": bg.name,
            "tier": bg.tier,
            "game": _serialize_game(bg.game, include_full_result=True),
            "team_1_seed": bg.team_1_seed,
            "team_2_seed": bg.team_2_seed,
            "team_1_record": bg.team_1_record,
            "team_2_record": bg.team_2_record,
        })

    # Playoff bracket
    playoff = [_serialize_game(g, include_full_result=True) for g in season.playoff_bracket]

    # Awards
    awards = None
    try:
        season_honors = compute_season_awards(
            season, year=2025,
            conferences=season.conferences if hasattr(season, 'conferences') else None,
        )
        awards = season_honors.to_dict()
    except Exception:
        pass

    # Team rosters (player snapshots)
    team_rosters = {}
    for team_name, team in season.teams.items():
        team_rosters[team_name] = {
            "players": [_serialize_player(p) for p in team.players],
            "mascot": getattr(team, "mascot", ""),
            "abbreviation": getattr(team, "abbreviation", ""),
        }

    label = season.name
    if dynasty:
        label = f"{dynasty.dynasty_name} ({dynasty.current_year})"

    return {
        "type": "college",
        "label": label,
        "session_id": session_id,
        "season_name": season.name,
        "champion": season.champion,
        "team_count": len(season.teams),
        "total_games": len(season.schedule),
        "games_played": sum(1 for g in season.schedule if g.completed),
        "standings": standings,
        "schedule": schedule,
        "polls": polls,
        "conferences": conferences,
        "bowl_games": bowl_games,
        "playoff_bracket": playoff,
        "awards": awards,
        "team_rosters": team_rosters,
        "is_dynasty": dynasty is not None,
        "dynasty_name": dynasty.dynasty_name if dynasty else None,
        "dynasty_year": dynasty.current_year if dynasty else None,
        "team_conferences": dict(season.team_conferences) if season.team_conferences else {},
        "style_configs": dict(season.style_configs) if season.style_configs else {},
    }


def _build_fiv_archive() -> dict:
    """Build a self-contained archive snapshot of the current FIV cycle."""
    from engine.fiv import load_fiv_rankings
    fiv_data = _get_fiv_cycle_data()
    if not fiv_data:
        raise HTTPException(status_code=404, detail="No active FIV cycle to archive")

    rankings = load_fiv_rankings()
    rankings_data = rankings.to_dict() if rankings else None

    cycle_num = fiv_data.get("cycle_number", 0)
    phase = fiv_data.get("phase", "unknown")
    host = fiv_data.get("host_nation", "")

    return {
        "type": "fiv",
        "label": f"FIV Cycle {cycle_num}",
        "cycle_number": cycle_num,
        "phase": phase,
        "host_nation": host,
        "fiv_data": fiv_data,
        "rankings": rankings_data,
    }


@app.post("/archives/college/{session_id}")
def archive_college_season(session_id: str):
    """Archive a college season to persistent storage."""
    from engine.db import save_season_archive
    session = _get_session(session_id)
    snapshot = _build_college_archive(session, session_id)
    archive_key = f"college_{session_id}_{int(time.time())}"
    save_season_archive(archive_key, snapshot)
    return {"archive_key": archive_key, "label": snapshot["label"], "message": "Season archived successfully"}


@app.post("/archives/fiv")
def archive_fiv_cycle():
    """Archive the current FIV cycle to persistent storage."""
    from engine.db import save_season_archive
    snapshot = _build_fiv_archive()
    archive_key = f"fiv_cycle_{snapshot['cycle_number']}_{int(time.time())}"
    save_season_archive(archive_key, snapshot)
    return {"archive_key": archive_key, "label": snapshot["label"], "message": "FIV cycle archived successfully"}


@app.get("/archives")
def list_archives():
    """List all archived seasons."""
    from engine.db import list_season_archives
    archives = list_season_archives()
    return {"archives": archives}


@app.get("/archives/{archive_key}")
def get_archive(archive_key: str):
    """Load a specific archived season."""
    from engine.db import load_season_archive
    data = load_season_archive(archive_key)
    if data is None:
        raise HTTPException(status_code=404, detail="Archive not found")
    return data


@app.delete("/archives/{archive_key}")
def remove_archive(archive_key: str):
    """Delete an archived season."""
    from engine.db import delete_season_archive
    delete_season_archive(archive_key)
    return {"message": "Archive deleted"}


# ═══════════════════════════════════════════════════════════════
# SAVE HISTORY — browse / restore previous versions of any save
# ═══════════════════════════════════════════════════════════════

@app.get("/history")
def list_history(save_type: Optional[str] = None, limit: int = 100):
    """List all historical save versions, optionally filtered by save_type."""
    from engine.db import list_all_save_history
    entries = list_all_save_history(save_type=save_type, limit=limit)
    return {"history": entries}


@app.get("/history/{save_type}/{save_key}")
def get_save_history(save_type: str, save_key: str, limit: int = 50):
    """List previous versions of a specific save."""
    from engine.db import list_save_history
    entries = list_save_history(save_type, save_key, limit=limit)
    return {"history": entries, "save_type": save_type, "save_key": save_key}


@app.get("/history/entry/{history_id}")
def get_history_entry(history_id: int):
    """Load the full data of a historical save version."""
    from engine.db import load_save_history_entry
    data = load_save_history_entry(history_id)
    if data is None:
        raise HTTPException(status_code=404, detail="History entry not found")
    return data


@app.post("/history/restore/{history_id}")
def restore_history_entry(history_id: int):
    """Restore a historical save version as the current save.

    The current save is snapshotted to history first, so nothing is lost.
    """
    from engine.db import restore_save_from_history
    ok = restore_save_from_history(history_id)
    if not ok:
        raise HTTPException(status_code=404, detail="History entry not found")
    return {"message": "Save restored from history", "restored_history_id": history_id}


@app.post("/history/prune")
def prune_history(keep_per_key: int = 20):
    """Delete old history entries, keeping the newest `keep_per_key` per save."""
    from engine.db import prune_save_history
    prune_save_history(keep_per_key=keep_per_key)
    return {"message": f"Pruned history, kept newest {keep_per_key} per save"}


@app.post("/sessions/{session_id}/dynasty")
def create_dynasty_endpoint(session_id: str, req: CreateDynastyRequest):
    from engine.geography import get_geographic_conference_defaults
    from engine.db import save_dynasty as db_save_dynasty
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
        games_per_team=req.games_per_team,
        playoff_size=req.playoff_size,
        bowl_count=req.bowl_count,
    )

    if req.conferences:
        conferences = req.conferences
    else:
        conferences = get_geographic_conference_defaults(TEAMS_DIR, team_names, req.num_conferences)
    for conf_name, conf_teams in conferences.items():
        dynasty.add_conference(conf_name, conf_teams)

    if req.history_years > 0:
        dynasty.simulate_history(
            num_years=req.history_years,
            teams_dir=TEAMS_DIR,
            games_per_team=req.games_per_team,
            playoff_size=req.playoff_size,
        )

    session["dynasty"] = dynasty
    session["phase"] = "setup"
    session["injury_tracker"] = None
    session["season"] = None
    session["program_archetype"] = req.program_archetype

    # Eagerly initialise the HS league and recruiting pipeline so the
    # Recruiting Hub on the stats site shows data before the first offseason.
    try:
        import random as _rnd
        from engine.hs_league import create_hs_league, simulate_hs_season
        from engine.recruiting import HSRecruitingPipeline

        _year = req.starting_year
        _rng = _rnd.Random(_year)
        dynasty._hs_league = create_hs_league(_year, rng=_rng)
        dynasty._hs_league = simulate_hs_season(dynasty._hs_league, rng=_rng)

        num_teams = len(season.teams) if season and hasattr(season, "teams") else 200
        _class_size = max(300, num_teams * 8)
        _t_names = list(season.teams.keys()) if season and hasattr(season, "teams") else []
        _t_prestige = dynasty.team_prestige if hasattr(dynasty, "team_prestige") else None
        dynasty._hs_pipeline = HSRecruitingPipeline()
        dynasty._hs_pipeline.generate_initial_pipeline(
            base_seed=_year, size_per_class=_class_size,
            team_names=_t_names, team_prestige=_t_prestige,
        )
    except Exception:
        pass  # Non-critical — will be created on first offseason advance

    # Persist dynasty to database
    db_save_dynasty(dynasty, save_key=session_id)

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
    from engine.injuries import InjuryTracker
    from engine.draftyqueenz import DraftyQueenzManager
    session = _get_session(session_id)
    dynasty = _require_dynasty(session)

    if session["phase"] not in ("setup", "finalize"):
        raise HTTPException(status_code=400, detail=f"Cannot start season in phase '{session['phase']}'")

    # Use dynasty-level season settings (set at creation)
    games_per_team = dynasty.games_per_team
    playoff_size = dynasty.playoff_size
    bowl_count = dynasty.bowl_count

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

    # ── Roster continuity: restore developed rosters from previous season ──
    # If offseason_complete() persisted roster data, replace the fresh-loaded
    # players with the developed ones (preserving team metadata like state).
    next_rosters = getattr(dynasty, '_next_season_rosters', None)
    if next_rosters:
        from engine.player_card import PlayerCard, card_to_player
        for team_name, team in teams.items():
            card_dicts = next_rosters.get(team_name)
            if card_dicts:
                restored_players = []
                for cd in card_dicts:
                    try:
                        card = PlayerCard.from_dict(cd)
                        restored_players.append(card_to_player(card))
                    except Exception:
                        pass
                if restored_players:
                    team.players = restored_players
        dynasty._next_season_rosters = None

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

    # Generate coaching staffs if not yet created (first dynasty season)
    if not dynasty._coaching_staffs:
        from engine.coaching import generate_coaching_staff
        all_team_names = list(dynasty.team_histories.keys())
        staff_rng = random.Random(dynasty.current_year + 42)
        for team_name in dynasty.team_histories:
            prestige = dynasty.team_prestige.get(team_name, 50)
            dynasty._coaching_staffs[team_name] = generate_coaching_staff(
                team_name=team_name, prestige=prestige, year=dynasty.current_year, rng=staff_rng,
                all_team_names=all_team_names,
            )

    season = create_season(
        f"{dynasty.current_year} CVL Season",
        teams,
        style_configs,
        conferences=conf_dict,
        games_per_team=games_per_team,
        team_states=team_states,
        pinned_matchups=pinned,
        rivalries=rivalries_dict,
        coaching_staffs=dynasty._coaching_staffs if dynasty._coaching_staffs else None,
        dynasty_year=dynasty.current_year,
    )

    session["season"] = season
    season.human_teams = list(session.get("human_teams", []))
    # Attach live prestige tracking so it updates after every game
    dynasty.attach_prestige_to_season(season)
    session["phase"] = "regular"
    session["config"] = {
        "playoff_size": playoff_size,
        "bowl_count": bowl_count,
        "games_per_team": games_per_team,
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
    from engine.nil_system import NILProgram, auto_nil_program, generate_nil_budget, assess_retention_risks, estimate_market_tier, compute_team_prestige
    from engine.transfer_portal import TransferPortal, populate_portal
    from engine.recruiting import generate_recruit_class, RecruitingBoard
    from engine.db import save_dynasty as db_save_dynasty
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

    # ── HS Recruiting Pipeline (run before recruit pool so graduates feed the pool) ──
    from engine.recruiting import HSRecruitingPipeline
    num_teams = len(season.teams) if hasattr(season, "teams") else 200
    pool_size = max(300, num_teams * 8)
    _t_names = list(season.teams.keys()) if hasattr(season, "teams") else []
    _t_prestige = dynasty.team_prestige if hasattr(dynasty, "team_prestige") else None
    if dynasty._hs_pipeline is None:
        dynasty._hs_pipeline = HSRecruitingPipeline()
        dynasty._hs_pipeline.generate_initial_pipeline(
            base_seed=year, size_per_class=pool_size,
            team_names=_t_names, team_prestige=_t_prestige,
        )
        # First year: no graduates yet, fall back to fresh generation
        recruit_pool = generate_recruit_class(year=year, size=pool_size, rng=random.Random(year))
    else:
        graduates = dynasty._hs_pipeline.advance_year(
            new_9th_seed=year, size=pool_size, rng=rng,
        )
        # Use pipeline graduates (12th graders) as the recruit pool
        recruit_pool = [g.recruit for g in graduates] if graduates else generate_recruit_class(year=year, size=pool_size, rng=random.Random(year))

    recruit_board = RecruitingBoard(team_name=human_team, scholarships_available=8)

    human_nil = dynasty._nil_programs.get(human_team)
    try:
        from engine.db import save_hs_pipeline
        save_hs_pipeline(
            dynasty_name=dynasty.dynasty_name,
            pipeline_data=dynasty._hs_pipeline.to_dict(),
        )
    except Exception:
        pass

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

    # Persist dynasty after advancing
    db_save_dynasty(dynasty, save_key=session_id)

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


@app.get("/dynasties")
def list_dynasties_endpoint():
    """List all saved dynasties."""
    from engine.db import list_dynasties as db_list_dynasties
    return {"dynasties": db_list_dynasties()}


@app.post("/sessions/{session_id}/dynasty/load")
def load_dynasty_endpoint(session_id: str, save_key: str = Query(...)):
    """Load a saved dynasty into the given session."""
    from engine.db import load_dynasty as db_load_dynasty
    session = _get_session(session_id)
    dynasty = db_load_dynasty(save_key=save_key)
    if dynasty is None:
        raise HTTPException(status_code=404, detail=f"No saved dynasty with key '{save_key}'")
    session["dynasty"] = dynasty
    session["phase"] = "setup"
    session["season"] = None
    session["injury_tracker"] = None
    session["human_teams"] = [dynasty.coach.team_name]

    # Restore HS league + pipeline if not already present from the save
    if dynasty._hs_pipeline is None:
        try:
            import random as _rnd
            from engine.hs_league import create_hs_league, simulate_hs_season
            from engine.recruiting import HSRecruitingPipeline

            _year = dynasty.current_year
            _rng = _rnd.Random(_year)
            dynasty._hs_league = create_hs_league(_year, rng=_rng)
            dynasty._hs_league = simulate_hs_season(dynasty._hs_league, rng=_rng)

            _num_teams = len(season.teams) if season and hasattr(season, "teams") else 200
            _class_size = max(300, _num_teams * 8)
            _t_names = list(season.teams.keys()) if season and hasattr(season, "teams") else []
            _t_prestige = dynasty.team_prestige if hasattr(dynasty, "team_prestige") else None
            dynasty._hs_pipeline = HSRecruitingPipeline()
            dynasty._hs_pipeline.generate_initial_pipeline(
                base_seed=_year, size_per_class=_class_size,
                team_names=_t_names, team_prestige=_t_prestige,
            )
        except Exception:
            pass

    return _serialize_dynasty_status(session)


@app.delete("/dynasties/{save_key}")
def delete_dynasty_endpoint(save_key: str):
    """Delete a saved dynasty."""
    from engine.db import delete_dynasty as db_delete_dynasty
    db_delete_dynasty(save_key=save_key)
    return {"deleted": save_key}


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
            "total_bowl_appearances": getattr(history, 'total_bowl_appearances', 0),
            "total_bowl_wins": getattr(history, 'total_bowl_wins', 0),
            "total_points_for": round(history.total_points_for, 1),
            "total_points_against": round(history.total_points_against, 1),
            "win_percentage": round(history.win_percentage, 4),
            "best_season_wins": history.best_season_wins,
            "best_season_year": history.best_season_year,
            "championship_years": history.championship_years,
            "finalist_years": getattr(history, 'finalist_years', []),
            "final_four_years": getattr(history, 'final_four_years', []),
            "sweet_16_years": getattr(history, 'sweet_16_years', []),
            "conference_title_years": getattr(history, 'conference_title_years', []),
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


@app.get("/sessions/{session_id}/dynasty/graduating-class")
def dynasty_graduating_class(session_id: str):
    """Return all graduating seniors/graduates as a WVL-importable list of PlayerCard dicts."""
    session = _get_session(session_id)
    _require_dynasty(session)

    from engine.player_card import player_to_card

    graduates = []

    # Prefer offseason player_cards (available after season ends)
    offseason = session.get("offseason", {})
    player_cards = offseason.get("player_cards", {})
    if player_cards:
        for team_name, cards in player_cards.items():
            for card in cards:
                if getattr(card, "year", "") in ("Senior", "Graduate"):
                    d = card.to_dict()
                    d["graduating_from"] = team_name
                    graduates.append(d)
    else:
        # Fall back to current season rosters
        season_obj = session.get("season")
        if season_obj:
            for team_name, team in season_obj.teams.items():
                for player in team.players:
                    if getattr(player, "year", "") in ("Senior", "Graduate"):
                        card = player_to_card(player, team_name)
                        d = card.to_dict()
                        d["graduating_from"] = team_name
                        graduates.append(d)

    dynasty = session.get("dynasty")
    year = getattr(dynasty, "year", None) if dynasty else None

    return {"graduates": graduates, "count": len(graduates), "year": year}


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


def _serialize_portal_entry(entry: "PortalEntry") -> dict:
    from engine.transfer_portal import PortalEntry  # noqa: F811
    d = entry.get_summary()
    d["position_full"] = d.get("position", "")
    d["position"] = POSITION_TAGS.get(d["position_full"], d["position_full"][:2].upper() if d["position_full"] else "??")
    return d


def _serialize_recruit(recruit: "Recruit") -> dict:
    from engine.recruiting import Recruit  # noqa: F811
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
    dynasty = session.get("dynasty")
    human_team = dynasty.coach.team_name if dynasty else ""
    transfers_rem = portal.transfers_remaining(human_team) if portal and human_team else -1
    return {
        "phase": offseason["phase"],
        "nil_budget": nil_prog.annual_budget if nil_prog else 0,
        "nil_allocated": nil_prog.total_allocated if nil_prog else 0,
        "portal_count": len(portal.entries) if portal else 0,
        "portal_available": len(portal.get_available()) if portal else 0,
        "recruit_pool_size": len(recruit_pool),
        "retention_risks_count": len(offseason.get("retention_risks", [])),
        "graduating_count": sum(len(v) for v in offseason.get("graduating", {}).values()),
        "transfers_remaining": transfers_rem,
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

    # Validate NIL offer against portal budget
    nil_prog = offseason.get("nil_program")
    if nil_prog and req.nil_amount > 0:
        if req.nil_amount > nil_prog.portal_remaining:
            raise HTTPException(
                status_code=400,
                detail=f"NIL offer ${req.nil_amount:,.0f} exceeds remaining portal budget ${nil_prog.portal_remaining:,.0f}",
            )

    entry = portal.entries[req.entry_index]
    human_team = dynasty.coach.team_name
    success = portal.make_offer(human_team, entry, nil_amount=req.nil_amount)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot make offer to this player")

    # Track NIL spend in the budget
    if nil_prog and req.nil_amount > 0:
        nil_prog.make_deal(
            pool="portal",
            player_id=getattr(entry, "player_id", entry.player_name),
            player_name=entry.player_name,
            amount=req.nil_amount,
            year=dynasty.current_year,
        )

    return {
        "offered": True,
        "player": _serialize_portal_entry(entry),
        "portal_remaining": nil_prog.portal_remaining if nil_prog else 0,
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

    # Provide specific error messages
    if entry.committed_to is not None or entry.withdrawn:
        raise HTTPException(status_code=400, detail="This player is no longer available")
    remaining = portal.transfers_remaining(human_team)
    if remaining == 0:
        raise HTTPException(status_code=400, detail="You have reached your transfer cap")

    success = portal.instant_commit(human_team, entry)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot commit this player")

    transfers_left = portal.transfers_remaining(human_team)
    return {
        "committed": True,
        "player": _serialize_portal_entry(entry),
        "transfers_remaining": transfers_left,
    }


@app.post("/sessions/{session_id}/offseason/portal/resolve")
def offseason_portal_resolve(session_id: str):
    from engine.transfer_portal import auto_portal_offers
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
    from engine.recruiting import auto_recruit_team, simulate_recruit_decisions
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
    from engine.db import save_dynasty as db_save_dynasty
    from engine.player_card import card_to_player
    session = _get_session(session_id)
    dynasty = _require_dynasty(session)
    offseason = _require_offseason(session)

    # ── Persist roster state for next season ──
    # Apply portal transfers and recruiting results to player_cards,
    # then save them so dynasty_start_season() can rebuild teams from
    # developed rosters instead of loading fresh from disk.
    player_cards = offseason.get("player_cards", {})

    if player_cards:
        # Apply portal transfers
        portal = offseason.get("portal")
        if portal:
            for entry in portal.entries:
                if entry.committed_to and entry.origin_team and entry.origin_team != entry.committed_to:
                    origin_cards = player_cards.get(entry.origin_team, [])
                    transferred = [c for c in origin_cards if c.full_name == entry.player_name]
                    player_cards[entry.origin_team] = [
                        c for c in origin_cards if c.full_name != entry.player_name
                    ]
                    dest_cards = player_cards.get(entry.committed_to, [])
                    dest_cards.extend(transferred)
                    player_cards[entry.committed_to] = dest_cards

        # Serialize rosters for persistence
        dynasty._next_season_rosters = {}
        for team_name, cards in player_cards.items():
            dynasty._next_season_rosters[team_name] = [c.to_dict() for c in cards]

    session.pop("offseason", None)
    session["phase"] = "setup"

    # Persist dynasty after offseason completes
    db_save_dynasty(dynasty, save_key=session_id)

    return _serialize_dynasty_status(session)


@app.post("/sessions/{session_id}/season/portal/generate")
def season_portal_generate(
    session_id: str,
    req: SeasonPortalGenerateRequest = SeasonPortalGenerateRequest(),
):
    from engine.transfer_portal import estimate_prestige_from_roster, generate_quick_portal
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
    from engine.transfer_portal import estimate_prestige_from_roster
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

    if dynasty:
        if req.team not in dynasty.rivalries:
            dynasty.rivalries[req.team] = {"conference": [], "non_conference": []}
        entry = dynasty.rivalries[req.team]
        for key in ("conference", "non_conference"):
            if isinstance(entry.get(key), str) or entry.get(key) is None:
                entry[key] = [entry[key]] if isinstance(entry.get(key), str) and entry[key] else []
        if req.conference_rival is not None:
            entry["conference"] = [req.conference_rival] if req.conference_rival else []
        if req.non_conference_rival is not None:
            entry["non_conference"] = [req.non_conference_rival] if req.non_conference_rival else []

    if season:
        if req.team not in season.rivalries:
            season.rivalries[req.team] = {"conference": [], "non_conference": []}
        entry = season.rivalries[req.team]
        for key in ("conference", "non_conference"):
            if isinstance(entry.get(key), str) or entry.get(key) is None:
                entry[key] = [entry[key]] if isinstance(entry.get(key), str) and entry[key] else []
        if req.conference_rival is not None:
            entry["conference"] = [req.conference_rival] if req.conference_rival else []
        if req.non_conference_rival is not None:
            entry["non_conference"] = [req.non_conference_rival] if req.non_conference_rival else []

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


def _require_dq(session: dict) -> "DraftyQueenzManager":
    from engine.draftyqueenz import DraftyQueenzManager
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
        odds_resp = dq_get_odds(session_id, week)
        return {
            "week": week,
            "odds": odds_resp.get("odds", [o.to_dict() for o in contest.odds]),
            "pool_size": len(contest.player_pool),
            "already_started": True,
        }

    week_games = [g for g in season.schedule if g.week == week and not g.completed]
    if not week_games:
        raise HTTPException(status_code=400, detail=f"No unplayed games for week {week}")

    prestige_map = _get_prestige_map(session)
    standings_map = {r.team_name: r for r in season.get_standings_sorted()} if season.standings else None

    contest = mgr.start_week(week, week_games, season.teams, prestige_map, standings_map)

    odds_resp = dq_get_odds(session_id, week)
    return {
        "week": week,
        "odds": odds_resp.get("odds", [o.to_dict() for o in contest.odds]),
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
    from engine.draftyqueenz import format_moneyline
    session = _get_session(session_id)
    mgr = _require_dq(session)
    season = _require_season(session)
    contest = mgr.weekly_contests.get(week)
    if contest is None:
        raise HTTPException(status_code=404, detail=f"No contest for week {week}")

    prestige_map = _get_prestige_map(session)
    standings_map = {r.team_name: r for r in season.get_standings_sorted()} if season.standings else {}

    try:
        power_ranked = season.get_all_power_rankings() if season.standings else []
        rank_map: dict[str, int] = {name: idx for idx, (name, _pi, _qw) in enumerate(power_ranked, 1)}
    except Exception:
        rank_map = {}

    def _team_context(team_name: str) -> dict:
        """Build context dict for a team: record, prestige, star player, rank."""
        ctx: dict = {"name": team_name}
        rec = standings_map.get(team_name)
        if rec:
            ctx["record"] = rec.record_str
            ctx["wins"] = rec.wins
            ctx["losses"] = rec.losses
            ctx["ties"] = getattr(rec, "ties", 0)
            ctx["conf"] = getattr(rec, "conference", "") or ""
            ctx["conf_record"] = rec.conf_record_str
            ctx["avg_opi"] = round(getattr(rec, "avg_opi", 0), 1)
        else:
            ctx["record"] = "0-0"
            ctx["wins"] = 0
            ctx["losses"] = 0
            ctx["conf"] = ""
            ctx["conf_record"] = ""
            ctx["avg_opi"] = 0
        rk = rank_map.get(team_name, 0)
        ctx["rank"] = rk if rk <= 25 else 0
        ctx["prestige"] = prestige_map.get(team_name, 50)
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
    from engine.draftyqueenz import FANTASY_ENTRY_FEE
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
    from engine.draftyqueenz import POSITION_NAMES, SALARY_CAP
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
    from engine.draftyqueenz import SALARY_CAP
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
    from engine.draftyqueenz import SALARY_CAP
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
    from engine.draftyqueenz import SALARY_CAP
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
    from engine.draftyqueenz import DONATION_TYPES
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


@app.get("/sessions/{session_id}/dq/history")
def dq_history(session_id: str):
    """Return all picks across all weeks with running P&L totals."""
    session = _get_session(session_id)
    mgr = _require_dq(session)
    all_picks = []
    total_won = 0
    total_lost = 0
    total_pending = 0
    for week_num in sorted(mgr.weekly_contests.keys()):
        contest = mgr.weekly_contests[week_num]
        for pick in contest.picks:
            d = pick.to_dict()
            d["week"] = week_num
            d["resolved"] = contest.resolved
            all_picks.append(d)
            if pick.result == "win":
                total_won += pick.payout
            elif pick.result == "loss":
                total_lost += pick.amount
            elif not contest.resolved:
                total_pending += pick.amount
        for parlay in contest.parlays:
            d = parlay.to_dict()
            d["week"] = week_num
            d["resolved"] = contest.resolved
            d["pick_type"] = "parlay"
            d["matchup"] = f"{len(parlay.legs)}-leg parlay"
            all_picks.append(d)
            if parlay.result == "win":
                total_won += parlay.payout
            elif parlay.result == "loss":
                total_lost += parlay.amount
            elif not contest.resolved:
                total_pending += parlay.amount
    return {
        "picks": all_picks,
        "total_won": total_won,
        "total_lost": total_lost,
        "net": total_won - total_lost,
        "total_pending": total_pending,
    }


@app.get("/sessions/{session_id}/dq/summary")
def dq_summary(session_id: str):
    session = _get_session(session_id)
    mgr = _require_dq(session)
    return mgr.season_summary()


# ---------------------------------------------------------------------------
# DraftyQueenz Standalone Mode
# ---------------------------------------------------------------------------

class DQCreateRequest(BaseModel):
    name: str = "DQ Fantasy Season"
    ai_seed: int = 0
    num_conferences: int = 16
    games_per_team: int = 12
    playoff_size: int = 8
    bowl_count: int = 4


@app.post("/sessions/{session_id}/dq/create-season")
def dq_create_season(session_id: str, req: DQCreateRequest):
    """Create a season specifically for DQ standalone mode (no human teams)."""
    from engine.geography import get_geographic_conference_defaults
    from engine.injuries import InjuryTracker
    from engine.draftyqueenz import DraftyQueenzManager
    session = _get_session(session_id)

    teams, team_states = load_teams_with_states(TEAMS_DIR, fresh=True)
    team_names = list(teams.keys())

    conferences = get_geographic_conference_defaults(TEAMS_DIR, team_names, req.num_conferences)

    ai_configs = auto_assign_all_teams(
        TEAMS_DIR, human_teams=[], human_configs={},
        seed=req.ai_seed if req.ai_seed else None,
    )
    style_configs = {}
    for tname in teams:
        style_configs[tname] = ai_configs.get(
            tname, {"offense_style": "balanced", "defense_style": "swarm", "st_scheme": "aces"}
        )

    rivalries_dict = auto_assign_rivalries(
        conferences=conferences, team_states=team_states,
        human_team=None, existing_rivalries=None,
    )

    coaching_staffs = load_coaching_staffs_from_directory(TEAMS_DIR)

    season = create_season(
        req.name, teams, style_configs,
        conferences=conferences, games_per_team=req.games_per_team,
        team_states=team_states, rivalries=rivalries_dict,
        coaching_staffs=coaching_staffs,
    )

    session["season"] = season
    session["human_teams"] = []
    season.human_teams = []
    session["phase"] = "regular"
    session["config"] = {
        "playoff_size": req.playoff_size,
        "bowl_count": req.bowl_count,
        "games_per_team": req.games_per_team,
    }
    session["injury_tracker"] = InjuryTracker()
    session["injury_tracker"].seed(req.ai_seed if req.ai_seed else 42)
    season.injury_tracker = session["injury_tracker"]
    session["dq_manager"] = DraftyQueenzManager(
        manager_name="Fantasy GM", season_year=2026,
    )
    session["history"] = []
    session["coaching_staffs"] = season.coaching_staffs

    return {
        "status": _serialize_season_status(session),
        "dq": {
            "bankroll": session["dq_manager"].bankroll.balance,
            "booster_tier": session["dq_manager"].booster_tier[0],
        },
        "total_weeks": season.get_total_weeks(),
    }


class DQAdvanceWeekRequest(BaseModel):
    fast_sim: bool = True


@app.post("/sessions/{session_id}/dq/advance-week")
def dq_advance_week(session_id: str, req: DQAdvanceWeekRequest = DQAdvanceWeekRequest()):
    """Simulate the next week and return DQ-relevant results."""
    session = _get_session(session_id)
    season = _require_season(session)
    mgr = _require_dq(session)

    if session["phase"] != "regular":
        raise HTTPException(status_code=400, detail=f"Season not in regular phase: {session['phase']}")

    next_week = season.get_next_unplayed_week()
    if next_week is None:
        raise HTTPException(status_code=400, detail="Regular season is complete")

    dq_boosts = mgr.get_all_team_boosts()
    games = season.simulate_week(week=next_week, dq_team_boosts=dq_boosts,
                                  use_fast_sim=req.fast_sim)

    if season.is_regular_season_complete():
        session["phase"] = "playoffs_pending"

    return {
        "week": next_week,
        "games_count": len(games),
        "season_complete": season.is_regular_season_complete(),
        "phase": session["phase"],
        "status": _serialize_season_status(session),
        "engine": "fast_sim" if req.fast_sim else "full",
    }


def _get_league_config(league: str) -> "ProLeagueConfig":
    from engine.pro_league import ProLeagueConfig
    config = _get_league_configs().get(league.lower())
    if not config:
        raise HTTPException(status_code=404, detail=f"League '{league}' not found. Available: {list(_get_league_configs().keys())}")
    return config


def _get_pro_session(league: str, session_id: str) -> "ProLeagueSeason":
    from engine.db import load_pro_league as db_load_pro_league
    from engine.pro_league import ProLeagueSeason
    key = f"{league.lower()}_{session_id}"
    if key not in pro_sessions:
        # Try restoring from database
        season, _ = db_load_pro_league(league.lower(), session_id)
        if season is not None:
            pro_sessions[key] = season
        else:
            raise HTTPException(status_code=404, detail=f"Pro league session '{key}' not found")
    _pro_session_accessed[key] = time.time()
    return pro_sessions[key]


def _auto_save_pro(league: str, session_id: str):
    """Save pro league state to database after mutations."""
    from engine.db import save_pro_league as db_save_pro_league
    key = f"{league.lower()}_{session_id}"
    season = pro_sessions.get(key)
    if season:
        dq = DraftyQueenzManager(manager_name=f"{season.config.league_name} Bettor")
        try:
            db_save_pro_league(league.lower(), session_id, season, dq)
        except Exception:
            pass  # non-critical, log in production


@app.post("/api/pro/{league}/new")
def pro_league_new(league: str):
    config = _get_league_config(league)
    session_id = str(uuid.uuid4())[:8]
    key = f"{league.lower()}_{session_id}"
    season = ProLeagueSeason(config)
    pro_sessions[key] = season
    _auto_save_pro(league, session_id)
    return {
        "league": league.lower(),
        "session_id": session_id,
        "key": key,
        "status": season.get_status(),
    }


@app.get("/api/pro/{league}/{session_id}/standings")
def pro_league_standings(league: str, session_id: str):
    season = _get_pro_session(league, session_id)
    return season.get_standings()


@app.get("/api/pro/{league}/{session_id}/schedule")
def pro_league_schedule(league: str, session_id: str):
    season = _get_pro_session(league, session_id)
    return season.get_schedule()


@app.post("/api/pro/{league}/{session_id}/sim-week")
async def pro_league_sim_week(league: str, session_id: str):
    season = _get_pro_session(league, session_id)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(_sim_executor, season.sim_week)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    _auto_save_pro(league, session_id)
    return result


@app.post("/api/pro/{league}/{session_id}/sim-all")
async def pro_league_sim_all(league: str, session_id: str):
    season = _get_pro_session(league, session_id)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(_sim_executor, season.sim_all)
    _auto_save_pro(league, session_id)
    return result


@app.get("/api/pro/{league}/{session_id}/game/{week}/{matchup}")
def pro_league_box_score(league: str, session_id: str, week: int, matchup: str):
    season = _get_pro_session(league, session_id)
    box = season.get_box_score(week, matchup)
    if not box:
        raise HTTPException(status_code=404, detail=f"Game not found: week {week}, matchup '{matchup}'")
    return box


@app.post("/api/pro/{league}/{session_id}/playoffs")
async def pro_league_playoffs(league: str, session_id: str):
    season = _get_pro_session(league, session_id)
    loop = asyncio.get_event_loop()
    if season.phase == "regular_season":
        result = await loop.run_in_executor(_sim_executor, season.start_playoffs)
    else:
        result = await loop.run_in_executor(_sim_executor, season.advance_playoffs)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    _auto_save_pro(league, session_id)
    return result


@app.get("/api/pro/{league}/{session_id}/playoffs/bracket")
def pro_league_playoff_bracket(league: str, session_id: str):
    season = _get_pro_session(league, session_id)
    return season.get_playoff_bracket()


@app.get("/api/pro/{league}/{session_id}/stats")
def pro_league_stats(league: str, session_id: str, category: str = "all"):
    season = _get_pro_session(league, session_id)
    return season.get_stat_leaders(category)


@app.get("/api/pro/{league}/{session_id}/team/{team_key}")
def pro_league_team_detail(league: str, session_id: str, team_key: str):
    season = _get_pro_session(league, session_id)
    detail = season.get_team_detail(team_key)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Team '{team_key}' not found")
    return detail


@app.get("/api/pro/active")
def pro_league_active():
    active = []
    for key, season in pro_sessions.items():
        active.append({
            "key": key,
            "league": season.config.league_id,
            "league_name": season.config.league_name,
            "status": season.get_status(),
        })
    return {"active_sessions": active, "count": len(active)}


@app.get("/api/pro/{league}/{session_id}/status")
def pro_league_status(league: str, session_id: str):
    season = _get_pro_session(league, session_id)
    return season.get_status()


# ═══════════════════════════════════════════════════════════════
# FIV — INTERNATIONAL VIPERBALL
# ═══════════════════════════════════════════════════════════════

from engine.fiv import (
    create_fiv_cycle, run_continental_phase, run_playoff_phase,
    run_world_cup_phase, run_full_cycle,
    save_fiv_cycle, save_fiv_rankings, load_fiv_rankings,
    load_fiv_cycle, list_fiv_cycles, find_match_in_cycle,
    FIVRankings,
)

# In-memory active FIV cycle
_fiv_active_cycle = None
_fiv_active_cycle_data = None


class FIVCycleRequest(BaseModel):
    host_nation: Optional[str] = None
    seed: Optional[int] = None
    cvl_session_id: Optional[str] = None


@app.post("/api/fiv/cycle/new")
def fiv_new_cycle(req: FIVCycleRequest):
    """Start a new FIV cycle (optionally linked to a CVL season)."""
    global _fiv_active_cycle, _fiv_active_cycle_data

    # Load existing rankings if available
    existing_rankings = load_fiv_rankings()

    # Determine cycle number
    existing_cycles = list_fiv_cycles()
    cycle_number = len(existing_cycles) + 1

    # Pull CVL players from a completed college season if one exists
    cvl_players = None
    if req.cvl_session_id and req.cvl_session_id in sessions:
        session = sessions[req.cvl_session_id]
        season = session.get("season")
        if season and hasattr(season, "teams"):
            cvl_players = []
            for team_name, team in season.teams.items():
                for p in team.players:
                    # Tag each player with their college team for cvl_source
                    p._team_name = team_name
                    cvl_players.append(p)
    else:
        # Auto-detect: scan all sessions for a completed college season
        for sid, session in sessions.items():
            season = session.get("season")
            if season and hasattr(season, "teams") and hasattr(season, "champion"):
                cvl_players = []
                for team_name, team in season.teams.items():
                    for p in team.players:
                        p._team_name = team_name
                        cvl_players.append(p)
                if cvl_players:
                    break

    cycle = create_fiv_cycle(
        cycle_number=cycle_number,
        host_nation=req.host_nation,
        cvl_players=cvl_players,
        existing_rankings=existing_rankings,
        seed=req.seed,
    )

    # Link cycle to CVL session for auto-sync on completion
    if req.cvl_session_id:
        cycle.cvl_season_id = req.cvl_session_id

    _fiv_active_cycle = cycle
    # Persist initial rankings so Rankings tab works immediately
    if cycle.rankings:
        save_fiv_rankings(cycle.rankings)
    save_fiv_cycle(cycle)
    _fiv_active_cycle_data = cycle.to_dict()

    return {
        "cycle_number": cycle.cycle_number,
        "host_nation": cycle.host_nation,
        "phase": cycle.phase,
        "team_count": len(cycle.national_teams),
        "confederations": list(cycle.confederations_data.keys()),
        "cvl_linked": cvl_players is not None,
        "cvl_player_count": len(cvl_players) if cvl_players else 0,
    }


@app.get("/api/fiv/cycle/active")
def fiv_active_cycle():
    """Get the current active FIV cycle state."""
    global _fiv_active_cycle_data
    if _fiv_active_cycle_data:
        return _fiv_active_cycle_data

    data = load_fiv_cycle()
    if data is None:
        raise HTTPException(status_code=404, detail="No active FIV cycle")
    _fiv_active_cycle_data = data
    return data


@app.get("/api/fiv/rankings")
def fiv_rankings():
    """Get current FIV World Rankings."""
    rankings = load_fiv_rankings()
    if rankings is None:
        raise HTTPException(status_code=404, detail="No rankings available")
    ranked = rankings.get_ranked_list()
    return {
        "rankings": [{"rank": r, "code": c, "rating": round(rt, 1)} for r, c, rt in ranked],
        "total": len(ranked),
    }


@app.post("/api/fiv/continental/{conf}/sim-all")
async def fiv_sim_continental(conf: str):
    """Sim remaining games in a continental championship."""
    global _fiv_active_cycle, _fiv_active_cycle_data

    if _fiv_active_cycle is None:
        data = load_fiv_cycle()
        if data is None:
            raise HTTPException(status_code=404, detail="No active FIV cycle")
        raise HTTPException(status_code=400, detail="Cycle must be loaded in memory. Start a new cycle first.")

    if conf not in _fiv_active_cycle.confederations_data:
        raise HTTPException(status_code=404, detail=f"Confederation '{conf}' not found")

    from engine.fiv import run_continental_championship
    cc = _fiv_active_cycle.confederations_data[conf]

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        _sim_executor,
        lambda: run_continental_championship(cc, _fiv_active_cycle.national_teams, _fiv_active_cycle.rankings),
    )

    _fiv_active_cycle.phase = "continental"
    save_fiv_cycle(_fiv_active_cycle)
    _fiv_active_cycle_data = _fiv_active_cycle.to_dict()

    return {
        "confederation": conf,
        "champion": cc.champion,
        "qualifiers": cc.qualifiers,
        "phase": cc.phase,
        "total_matches": len(cc.all_results),
    }


@app.post("/api/fiv/continental/sim-all")
async def fiv_sim_all_continental():
    """Sim all 5 continental championships."""
    global _fiv_active_cycle, _fiv_active_cycle_data

    if _fiv_active_cycle is None:
        raise HTTPException(status_code=404, detail="No active FIV cycle")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_sim_executor, lambda: run_continental_phase(_fiv_active_cycle))
    # Persist rankings after continental phase so Rankings tab works
    if _fiv_active_cycle.rankings:
        save_fiv_rankings(_fiv_active_cycle.rankings)
    save_fiv_cycle(_fiv_active_cycle)
    _fiv_active_cycle_data = _fiv_active_cycle.to_dict()

    results = {}
    for conf_id, cc in _fiv_active_cycle.confederations_data.items():
        results[conf_id] = {
            "champion": cc.champion,
            "qualifiers": cc.qualifiers,
            "total_matches": len(cc.all_results),
        }

    return {"confederations": results, "phase": _fiv_active_cycle.phase}


@app.get("/api/fiv/continental/{conf}/standings")
def fiv_continental_standings(conf: str):
    """Get group tables and results for a continental championship."""
    data = _get_fiv_cycle_data()
    cc = data.get("confederations_data", {}).get(conf)
    if not cc:
        raise HTTPException(status_code=404, detail=f"Confederation '{conf}' not found")
    return cc


@app.get("/api/fiv/continental/{conf}/bracket")
def fiv_continental_bracket(conf: str):
    """Get knockout bracket for a continental championship."""
    data = _get_fiv_cycle_data()
    cc = data.get("confederations_data", {}).get(conf)
    if not cc:
        raise HTTPException(status_code=404, detail=f"Confederation '{conf}' not found")
    return {"knockout_rounds": cc.get("knockout_rounds", []), "champion": cc.get("champion")}


@app.get("/api/fiv/continental/{conf}/game/{match_id}")
def fiv_continental_game(conf: str, match_id: str):
    """Get full box score for a continental championship match."""
    data = _get_fiv_cycle_data()
    result = find_match_in_cycle(data, match_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Match '{match_id}' not found")
    return result


@app.post("/api/fiv/playoff/sim-all")
async def fiv_sim_playoff():
    """Sim the cross-confederation playoff."""
    global _fiv_active_cycle, _fiv_active_cycle_data

    if _fiv_active_cycle is None:
        raise HTTPException(status_code=404, detail="No active FIV cycle")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_sim_executor, lambda: run_playoff_phase(_fiv_active_cycle))
    # Persist rankings after playoff phase
    if _fiv_active_cycle.rankings:
        save_fiv_rankings(_fiv_active_cycle.rankings)
    save_fiv_cycle(_fiv_active_cycle)
    _fiv_active_cycle_data = _fiv_active_cycle.to_dict()

    return {
        "qualifiers": _fiv_active_cycle.playoff.qualifiers if _fiv_active_cycle.playoff else [],
        "phase": _fiv_active_cycle.phase,
    }


@app.post("/api/fiv/worldcup/draw")
def fiv_world_cup_draw():
    """Generate World Cup group draw."""
    global _fiv_active_cycle, _fiv_active_cycle_data

    if _fiv_active_cycle is None:
        raise HTTPException(status_code=404, detail="No active FIV cycle")

    from engine.fiv import create_world_cup, draw_world_cup_groups

    continental_qualifiers = {}
    for conf_id, cc in _fiv_active_cycle.confederations_data.items():
        continental_qualifiers[conf_id] = cc.qualifiers

    playoff_qualifiers = _fiv_active_cycle.playoff.qualifiers if _fiv_active_cycle.playoff else []

    wc = create_world_cup(
        continental_qualifiers, playoff_qualifiers,
        _fiv_active_cycle.host_nation or "USA",
        _fiv_active_cycle.rankings,
    )
    draw_world_cup_groups(wc, _fiv_active_cycle.national_teams)
    _fiv_active_cycle.world_cup = wc
    _fiv_active_cycle.phase = "wc_draw"

    save_fiv_cycle(_fiv_active_cycle)
    _fiv_active_cycle_data = _fiv_active_cycle.to_dict()

    return {
        "teams": wc.teams,
        "seed_pots": wc.seed_pots,
        "groups": [g.to_dict() for g in wc.groups],
        "phase": _fiv_active_cycle.phase,
    }


@app.post("/api/fiv/worldcup/sim-stage")
async def fiv_sim_world_cup_stage():
    """Sim the entire current World Cup stage (groups or knockout)."""
    global _fiv_active_cycle, _fiv_active_cycle_data

    if _fiv_active_cycle is None:
        raise HTTPException(status_code=404, detail="No active FIV cycle")

    wc = _fiv_active_cycle.world_cup
    if wc is None:
        raise HTTPException(status_code=400, detail="World Cup not yet created. Run draw first.")

    from engine.fiv import run_world_cup_group_stage, run_world_cup_knockout

    loop = asyncio.get_event_loop()
    if wc.phase in ("draw", "not_started"):
        await loop.run_in_executor(
            _sim_executor,
            lambda: run_world_cup_group_stage(wc, _fiv_active_cycle.national_teams, _fiv_active_cycle.rankings),
        )
        _fiv_active_cycle.phase = "wc_groups"
    elif wc.phase == "groups":
        await loop.run_in_executor(
            _sim_executor,
            lambda: run_world_cup_knockout(wc, _fiv_active_cycle.national_teams, _fiv_active_cycle.rankings),
        )
        _fiv_active_cycle.phase = "completed"
        if _fiv_active_cycle.rankings:
            _fiv_active_cycle.rankings.history.append({
                "cycle": _fiv_active_cycle.cycle_number,
                "snapshot": _fiv_active_cycle.rankings.snapshot(),
                "champion": wc.champion,
            })
            # Cap history to prevent unbounded growth
            if len(_fiv_active_cycle.rankings.history) > 20:
                _fiv_active_cycle.rankings.history = _fiv_active_cycle.rankings.history[-20:]
            save_fiv_rankings(_fiv_active_cycle.rankings)

    save_fiv_cycle(_fiv_active_cycle)
    _fiv_active_cycle_data = _fiv_active_cycle.to_dict()

    # Auto-sync FIV results to linked CVL dynasty career tracker
    if _fiv_active_cycle.phase == "completed" and _fiv_active_cycle.cvl_season_id:
        try:
            _auto_sync_fiv_to_dynasty(_fiv_active_cycle)
        except Exception:
            pass  # Best-effort — don't break the FIV flow

    return {
        "phase": wc.phase,
        "champion": wc.champion,
        "total_matches": len(wc.all_results),
    }


def _auto_sync_fiv_to_dynasty(cycle):
    """Auto-sync completed FIV cycle stats to the linked CVL dynasty."""
    sid = cycle.cvl_season_id
    if sid not in sessions:
        return
    sess = sessions[sid]
    dynasty = sess.get("dynasty")
    if not dynasty:
        return

    from engine.player_career_tracker import PlayerCareerTracker
    tracker = getattr(dynasty, "career_tracker", None)
    if not tracker:
        tracker = PlayerCareerTracker()
        dynasty.career_tracker = tracker

    player_stats = {}
    for nation_code, nt in cycle.national_teams.items():
        for ntp in nt.roster:
            pname = ntp.player.name
            player_stats[pname] = {
                "nation": nation_code,
                "caps": ntp.caps,
                "games": ntp.caps,
                "yards": ntp.career_international_stats.get("yards", 0),
                "tds": ntp.career_international_stats.get("tds", 0),
                "competition": "FIV",
                "world_cup": True,
            }

    tracker.record_fiv_cycle(player_stats, dynasty.current_year)

    from engine.db import save_dynasty as db_save_dynasty
    db_save_dynasty(dynasty, save_key=sid)


@app.post("/api/fiv/sync-to-dynasty/{session_id}")
def fiv_sync_to_dynasty(session_id: str):
    """Record FIV cycle player stats into a dynasty's career tracker.

    Call after an FIV cycle completes to update alumni profiles with
    international career data (caps, yards, TDs, national team).
    """
    if not _fiv_active_cycle:
        raise HTTPException(404, "No active FIV cycle")

    sess = _get_session(session_id)
    dynasty = sess.get("dynasty")
    if not dynasty:
        raise HTTPException(400, "Session has no dynasty")

    from engine.player_career_tracker import PlayerCareerTracker
    tracker = getattr(dynasty, "career_tracker", None)
    if not tracker:
        tracker = PlayerCareerTracker()
        dynasty.career_tracker = tracker

    cycle = _fiv_active_cycle
    year = dynasty.current_year

    # Build player stats from national team rosters and game results
    player_stats = {}
    for nation_code, nt in cycle.national_teams.items():
        for ntp in nt.roster:
            pname = ntp.player.name
            player_stats[pname] = {
                "nation": nation_code,
                "caps": ntp.caps,
                "games": ntp.caps,
                "yards": ntp.career_international_stats.get("yards", 0),
                "tds": ntp.career_international_stats.get("tds", 0),
                "competition": "FIV",
                "world_cup": cycle.world_cup is not None and cycle.phase == "completed",
            }

    tracker.record_fiv_cycle(player_stats, year)

    # Persist
    from engine.db import save_dynasty as db_save_dynasty
    db_save_dynasty(dynasty, save_key=session_id)

    return {
        "synced_players": len(player_stats),
        "dynasty": dynasty.dynasty_name,
        "year": year,
    }


@app.get("/api/fiv/worldcup/groups")
def fiv_world_cup_groups():
    """Get World Cup group tables and results."""
    data = _get_fiv_cycle_data()
    wc = data.get("world_cup")
    if not wc:
        raise HTTPException(status_code=404, detail="No World Cup data")
    return {"groups": wc.get("groups", []), "phase": wc.get("phase")}


@app.get("/api/fiv/worldcup/bracket")
def fiv_world_cup_bracket():
    """Get World Cup knockout bracket."""
    data = _get_fiv_cycle_data()
    wc = data.get("world_cup")
    if not wc:
        raise HTTPException(status_code=404, detail="No World Cup data")
    return {
        "knockout_rounds": wc.get("knockout_rounds", []),
        "champion": wc.get("champion"),
        "third_place": wc.get("third_place"),
    }


@app.get("/api/fiv/worldcup/game/{match_id}")
def fiv_world_cup_game(match_id: str):
    """Get full box score for a World Cup match."""
    data = _get_fiv_cycle_data()
    result = find_match_in_cycle(data, match_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Match '{match_id}' not found")
    return result


@app.get("/api/fiv/worldcup/stats")
def fiv_world_cup_stats():
    """Get World Cup tournament stat leaders."""
    global _fiv_active_cycle

    data = _get_fiv_cycle_data()
    wc = data.get("world_cup")
    if not wc:
        raise HTTPException(status_code=404, detail="No World Cup data")

    # Compute full stat leaders from the live cycle object (has MatchResult objs)
    leaders = None
    if _fiv_active_cycle and _fiv_active_cycle.world_cup:
        from engine.fiv import compute_tournament_stat_leaders
        leaders = compute_tournament_stat_leaders(_fiv_active_cycle.world_cup.all_results)

    return {
        "golden_boot": wc.get("golden_boot"),
        "mvp": wc.get("mvp"),
        "leaders": leaders,
    }


@app.get("/api/fiv/continental/{conf}/stats")
def fiv_continental_stats(conf: str):
    """Get tournament stat leaders for a continental championship."""
    global _fiv_active_cycle

    if _fiv_active_cycle is None:
        raise HTTPException(status_code=404, detail="No active FIV cycle in memory")

    cc = _fiv_active_cycle.confederations_data.get(conf)
    if not cc:
        raise HTTPException(status_code=404, detail=f"Confederation '{conf}' not found")

    from engine.fiv import compute_tournament_stat_leaders
    leaders = compute_tournament_stat_leaders(cc.all_results)
    return {
        "confederation": conf,
        "champion": cc.champion,
        "leaders": leaders,
    }


@app.get("/api/fiv/match/{match_id}")
def fiv_match_detail(match_id: str):
    """Get full match detail (box score) for any FIV match by ID."""
    data = _get_fiv_cycle_data()
    result = find_match_in_cycle(data, match_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Match '{match_id}' not found")
    return result


@app.get("/api/fiv/team/{nation_code}")
def fiv_team_detail(nation_code: str):
    """Get national team roster and stats."""
    data = _get_fiv_cycle_data()
    teams = data.get("national_teams", {})
    if nation_code not in teams:
        raise HTTPException(status_code=404, detail=f"Nation '{nation_code}' not found")
    return teams[nation_code]


@app.get("/api/fiv/cycles")
def fiv_list_cycles():
    """List all completed FIV cycles."""
    cycles = list_fiv_cycles()
    return {"cycles": cycles}


def _get_fiv_cycle_data() -> dict:
    """Get active FIV cycle data (from memory or DB)."""
    global _fiv_active_cycle_data
    if _fiv_active_cycle_data:
        return _fiv_active_cycle_data
    data = load_fiv_cycle()
    if data is None:
        raise HTTPException(status_code=404, detail="No active FIV cycle")
    _fiv_active_cycle_data = data
    return data


# ── Pixel-art face pool generation ─────────────────────────────────────

@app.get("/generate-face-pool")
@app.post("/generate-face-pool")
async def generate_face_pool(count: int = 50, force: bool = False):
    """
    Generate the reusable pixel-art face pool via PixelLab API.

    Creates face_000.png … face_N.png in stats_site/static/faces/.
    These persist across dynasty resets — any player maps to a face via hash.

    GET-friendly so you can trigger from a browser:
      http://localhost:5000/generate-face-pool
      http://localhost:5000/generate-face-pool?count=50

    API key loaded from PIXELLAB_API_KEY environment variable (set via Fly.io secrets).
    """
    from engine.face_generator import generate_pool, get_pool_size

    api_key = _load_pixellab_key()
    if not api_key:
        raise HTTPException(400,
            "No PixelLab API key found. "
            "Set PIXELLAB_API_KEY via: fly secrets set PIXELLAB_API_KEY=your-key")

    face_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "stats_site", "static", "faces")
    existing = get_pool_size(face_dir)

    results = await generate_pool(
        count=count, faces_dir=face_dir, api_key=api_key, force=force,
    )

    # Bust the cached pool size in the stats router
    try:
        import stats_site.router as _sr
        _sr._face_pool_size = None
    except Exception:
        pass

    return {
        "message": f"Face pool: {existing} existed, now generating up to {count}",
        "generated": len(results["generated"]),
        "skipped": len(results["skipped"]),
        "failed": len(results["failed"]),
        "errors": results["failed"][:10],
    }


@app.get("/face-pool-status")
def face_pool_status():
    """Check how many faces are in the pool."""
    from engine.face_generator import get_pool_size
    face_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "stats_site", "static", "faces")
    return {"pool_size": get_pool_size(face_dir)}


@app.get("/download-face-pool")
def download_face_pool():
    """Download all generated face PNGs as a zip file.

    Hit this after generating faces on Fly.io to pull them back into the repo:
        curl -o faces.zip https://your-app.fly.dev/download-face-pool
        unzip -o faces.zip -d stats_site/static/faces/
    """
    import io
    import zipfile
    from pathlib import Path

    face_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "stats_site" / "static" / "faces"
    pngs = sorted(face_dir.glob("face_*.png"))
    if not pngs:
        raise HTTPException(404, "No faces generated yet. Call /generate-face-pool first.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in pngs:
            zf.write(p, p.name)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=faces.zip"},
    )


# ── Pixel-art stadium pool generation ─────────────────────────────────

@app.get("/generate-stadium-pool")
@app.post("/generate-stadium-pool")
async def generate_stadium_pool(count: int = 75, force: bool = False):
    """
    Generate the reusable pixel-art stadium pool via PixelLab API.

    Creates stadium_000.png … stadium_N.png in stats_site/static/stadiums/.
    Now generates at 200x200 with highly detailed 16-bit style art.

    GET-friendly:
      http://localhost:5000/generate-stadium-pool
      http://localhost:5000/generate-stadium-pool?count=75&force=true
    """
    from engine.stadium_generator import generate_pool, get_pool_size

    api_key = _load_pixellab_key()
    if not api_key:
        raise HTTPException(400,
            "No PixelLab API key found. "
            "Set PIXELLAB_API_KEY via: fly secrets set PIXELLAB_API_KEY=your-key")

    stadium_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               "stats_site", "static", "stadiums")
    existing = get_pool_size(stadium_dir)

    results = await generate_pool(
        count=count, stadiums_dir=stadium_dir, api_key=api_key, force=force,
    )

    try:
        import stats_site.router as _sr
        _sr._stadium_pool_size = None
    except Exception:
        pass

    return {
        "message": f"Stadium pool: {existing} existed, now generating up to {count}",
        "generated": len(results["generated"]),
        "skipped": len(results["skipped"]),
        "failed": len(results["failed"]),
        "errors": results["failed"][:10],
    }


@app.get("/stadium-pool-status")
def stadium_pool_status():
    """Check how many stadiums are in the pool."""
    from engine.stadium_generator import get_pool_size
    stadium_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               "stats_site", "static", "stadiums")
    return {"pool_size": get_pool_size(stadium_dir)}


@app.get("/download-stadium-pool")
def download_stadium_pool():
    """Download all generated stadium PNGs as a zip file."""
    import io
    import zipfile
    from pathlib import Path

    stadium_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "stats_site" / "static" / "stadiums"
    pngs = sorted(stadium_dir.glob("stadium_*.png"))
    if not pngs:
        raise HTTPException(404, "No stadiums generated yet. Call /generate-stadium-pool first.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in pngs:
            zf.write(p, p.name)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=stadiums.zip"},
    )


# ── Pixel-art team banner pool generation ──────────────────────────────

@app.get("/generate-banner-pool")
@app.post("/generate-banner-pool")
async def generate_banner_pool(count: int = 100, force: bool = False):
    """
    Generate the reusable pixel-art team banner pool via PixelLab API.

    Creates banner_000.png … banner_N.png in stats_site/static/banners/.
    Banners are 320x128 wide panoramic images for team page headers.

    GET-friendly:
      http://localhost:5000/generate-banner-pool
      http://localhost:5000/generate-banner-pool?count=100&force=true
    """
    from engine.banner_generator import generate_pool, get_pool_size

    api_key = _load_pixellab_key()
    if not api_key:
        raise HTTPException(400,
            "No PixelLab API key found. "
            "Set PIXELLAB_API_KEY via: fly secrets set PIXELLAB_API_KEY=your-key")

    banner_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              "stats_site", "static", "banners")
    existing = get_pool_size(banner_dir)

    results = await generate_pool(
        count=count, banners_dir=banner_dir, api_key=api_key, force=force,
    )

    try:
        import stats_site.router as _sr
        _sr._banner_pool_size = None
    except Exception:
        pass

    return {
        "message": f"Banner pool: {existing} existed, now generating up to {count}",
        "generated": len(results["generated"]),
        "skipped": len(results["skipped"]),
        "failed": len(results["failed"]),
        "errors": results["failed"][:10],
    }


@app.get("/banner-pool-status")
def banner_pool_status():
    """Check how many banners are in the pool."""
    from engine.banner_generator import get_pool_size
    banner_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              "stats_site", "static", "banners")
    return {"pool_size": get_pool_size(banner_dir)}


@app.get("/download-banner-pool")
def download_banner_pool():
    """Download all generated banner PNGs as a zip file."""
    import io
    import zipfile
    from pathlib import Path

    banner_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "stats_site" / "static" / "banners"
    pngs = sorted(banner_dir.glob("banner_*.png"))
    if not pngs:
        raise HTTPException(404, "No banners generated yet. Call /generate-banner-pool first.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in pngs:
            zf.write(p, p.name)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=banners.zip"},
    )


# ── Pixel-art coach face pool generation ───────────────────────────────

@app.get("/generate-coach_face-pool")
@app.post("/generate-coach_face-pool")
async def generate_coach_face_pool(count: int = 150, force: bool = False):
    """
    Generate pixel-art coach face pool via PixelLab API.

    Creates coach_m_000.png … coach_m_N.png and coach_f_000.png … coach_f_N.png
    in stats_site/static/coach_faces/.  `count` is per gender.

    GET-friendly:
      http://localhost:5000/generate-coach_face-pool
      http://localhost:5000/generate-coach_face-pool?count=150
    """
    from engine.coach_face_generator import generate_pool, get_pool_size

    api_key = _load_pixellab_key()
    if not api_key:
        raise HTTPException(400,
            "No PixelLab API key found. "
            "Set PIXELLAB_API_KEY via: fly secrets set PIXELLAB_API_KEY=your-key")

    coach_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              "stats_site", "static", "coach_faces")
    existing = get_pool_size(coach_dir)

    results = await generate_pool(
        count=count, faces_dir=coach_dir, api_key=api_key, force=force,
    )

    try:
        import stats_site.router as _sr
        _sr._coach_face_pool_files = None
    except Exception:
        pass

    return {
        "message": f"Coach face pool: {existing} existed, now generating up to {count} per gender",
        "generated": len(results["generated"]),
        "skipped": len(results["skipped"]),
        "failed": len(results["failed"]),
        "errors": results["failed"][:10],
    }


@app.get("/coach_face-pool-status")
def coach_face_pool_status():
    """Check how many coach faces are in the pool."""
    from engine.coach_face_generator import get_pool_size
    coach_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              "stats_site", "static", "coach_faces")
    return get_pool_size(coach_dir)


@app.get("/download-coach_face-pool")
def download_coach_face_pool():
    """Download all generated coach face PNGs as a zip file."""
    import io
    import zipfile
    from pathlib import Path

    coach_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "stats_site" / "static" / "coach_faces"
    pngs = sorted(coach_dir.glob("coach_*.png"))
    if not pngs:
        raise HTTPException(404, "No coach faces generated yet. Call /generate-coach_face-pool first.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in pngs:
            zf.write(p, p.name)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=coach_faces.zip"},
    )


# ── Pixel-art referee face pool generation ─────────────────────────────

@app.get("/generate-referee-pool")
@app.post("/generate-referee-pool")
async def generate_referee_pool(count: int = 300, force: bool = False):
    """
    Generate pixel-art referee face pool via PixelLab API.

    Creates ref_000.png … ref_N.png in stats_site/static/referees/.

    GET-friendly:
      http://localhost:5000/generate-referee-pool
      http://localhost:5000/generate-referee-pool?count=300
    """
    from engine.referee_generator import generate_pool, get_pool_size

    api_key = _load_pixellab_key()
    if not api_key:
        raise HTTPException(400,
            "No PixelLab API key found. "
            "Set PIXELLAB_API_KEY via: fly secrets set PIXELLAB_API_KEY=your-key")

    ref_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "stats_site", "static", "referees")
    existing = get_pool_size(ref_dir)

    results = await generate_pool(
        count=count, refs_dir=ref_dir, api_key=api_key, force=force,
    )

    try:
        import stats_site.router as _sr
        _sr._ref_pool_size = None
    except Exception:
        pass

    return {
        "message": f"Referee pool: {existing} existed, now generating up to {count}",
        "generated": len(results["generated"]),
        "skipped": len(results["skipped"]),
        "failed": len(results["failed"]),
        "errors": results["failed"][:10],
    }


@app.get("/referee-pool-status")
def referee_pool_status():
    """Check how many referee faces are in the pool."""
    from engine.referee_generator import get_pool_size
    ref_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "stats_site", "static", "referees")
    return {"pool_size": get_pool_size(ref_dir)}


@app.get("/download-referee-pool")
def download_referee_pool():
    """Download all generated referee face PNGs as a zip file."""
    import io
    import zipfile
    from pathlib import Path

    ref_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "stats_site" / "static" / "referees"
    pngs = sorted(ref_dir.glob("ref_*.png"))
    if not pngs:
        raise HTTPException(404, "No referee faces generated yet. Call /generate-referee-pool first.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in pngs:
            zf.write(p, p.name)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=referees.zip"},
    )


# ═══════════════════════════════════════════════════════════════════════
# MY TEAM — ROSTER BUILDER  (Pre-season NIL + Portal + Recruiting)
# ═══════════════════════════════════════════════════════════════════════

def _get_my_team_session(session_id: str = ""):
    """Find the session + human team for the roster builder.

    If session_id is empty, uses the first session with a season.
    Returns (session, session_id, team_name, season).
    """
    if session_id and session_id in sessions:
        sess = sessions[session_id]
    else:
        # Find first session with a season
        for sid, sess in sessions.items():
            if sess.get("season") is not None:
                session_id = sid
                break
        else:
            raise HTTPException(400, "No active session found")

    season = sess.get("season")
    if not season:
        raise HTTPException(400, "No season in this session")

    # Determine human team
    team_name = sess.get("portal_human_team", "")
    if not team_name:
        human_teams = sess.get("human_teams", [])
        if human_teams:
            team_name = human_teams[0]
    dynasty = sess.get("dynasty")
    if not team_name and dynasty and hasattr(dynasty, "coach"):
        team_name = dynasty.coach.team_name

    # Last resort: if only one session and we still have no team,
    # pick the first team alphabetically so the user can at least try it
    if not team_name or team_name not in season.teams:
        if season.teams:
            team_name = sorted(season.teams.keys())[0]
            sess["portal_human_team"] = team_name
        else:
            raise HTTPException(400, "No human team found in session")

    return sess, session_id, team_name, season


def _ensure_roster_builder(sess, session_id: str, team_name: str, season):
    """Lazily initialize the roster builder state on the session."""
    if sess.get("roster_builder"):
        return sess["roster_builder"]

    import random as _rnd
    from engine.transfer_portal import estimate_prestige_from_roster, generate_quick_portal
    from engine.nil_system import generate_nil_budget, NILProgram, assess_retention_risks
    from engine.player_card import player_to_card

    team = season.teams[team_name]
    roster_cards = [player_to_card(p, team_name) for p in team.players]
    prestige = estimate_prestige_from_roster(team.players)
    rng = _rnd.Random(hash(session_id) % 999999)

    # Generate NIL budget
    budget = generate_nil_budget(prestige=prestige, rng=rng)
    nil_program = NILProgram(team_name=team_name, annual_budget=budget)
    nil_program.auto_allocate()

    # Assess retention risks
    risks = assess_retention_risks(roster_cards, team_prestige=prestige, team_wins=5, rng=rng)

    # Generate portal (larger pool for competitive bidding)
    portal = generate_quick_portal(
        team_names=list(season.teams.keys()),
        year=2027,
        size=80,
        prestige=prestige,
        rng=rng,
    )
    sess["quick_portal"] = portal
    sess["portal_human_team"] = team_name

    # Portal round state — timed trading engine
    builder = {
        "team_name": team_name,
        "prestige": prestige,
        "nil_program": nil_program,
        "retention_risks": risks,
        "retained_players": [],     # player_ids locked down
        "portal": portal,
        "portal_round": 0,          # current round (0 = not started)
        "portal_max_rounds": 5,     # total rounds
        "portal_bids": {},          # entry_index -> {"amount": float, "team": str}
        "portal_results": [],       # results after each round
        "phase": "dashboard",       # dashboard -> retention -> portal -> recruiting -> finalize
        "roster_cards": roster_cards,
        "scouting_points": 30,
        "scholarship_offers": [],   # recruit_ids offered
        "signed_recruits": [],      # recruit_ids signed
        "max_offers": 15,
    }

    # Seed career backstories so player cards feel lived-in
    for card in roster_cards:
        _seed_player_backstory(card, team_name, current_year=2026, rng=rng)

    sess["roster_builder"] = builder
    return builder


@app.get("/sessions/{session_id}/my-team")
def my_team_dashboard(session_id: str = ""):
    """Get the roster builder dashboard: roster, budget, position gaps."""
    sess, session_id, team_name, season = _get_my_team_session(session_id)
    builder = _ensure_roster_builder(sess, session_id, team_name, season)

    nil = builder["nil_program"]
    team = season.teams[team_name]

    # Position breakdown
    from engine.player_card import player_to_card
    pos_counts = {}
    roster_data = []
    for p in team.players:
        card = player_to_card(p, team_name)
        pos_counts[card.position] = pos_counts.get(card.position, 0) + 1
        roster_data.append({
            "player_id": card.player_id,
            "name": card.full_name,
            "position": card.position,
            "overall": card.overall,
            "potential": card.potential,
            "year": card.year,
            "speed": card.speed,
            "power": card.power,
            "agility": card.agility,
        })

    roster_data.sort(key=lambda x: -x["overall"])

    # Ideal roster template
    ideal = {"Viper": 3, "Zeroback": 3, "Halfback": 4, "Wingback": 4,
             "Slotback": 4, "Keeper": 3, "Offensive Line": 8, "Defensive Line": 7}
    gaps = {}
    for pos, need in ideal.items():
        have = pos_counts.get(pos, 0)
        if have < need:
            gaps[pos] = need - have

    return {
        "session_id": session_id,
        "team_name": team_name,
        "prestige": builder["prestige"],
        "phase": builder["phase"],
        "roster": roster_data,
        "roster_size": len(team.players),
        "position_counts": pos_counts,
        "position_gaps": gaps,
        "nil_budget": {
            "annual_budget": nil.annual_budget,
            "recruiting_pool": nil.recruiting_pool,
            "portal_pool": nil.portal_pool,
            "retention_pool": nil.retention_pool,
            "recruiting_remaining": nil.recruiting_remaining,
            "portal_remaining": nil.portal_remaining,
            "retention_remaining": nil.retention_remaining,
        },
        "retention_risks_count": len(builder["retention_risks"]),
        "portal_size": len(builder["portal"].entries),
        "portal_round": builder["portal_round"],
        "portal_max_rounds": builder["portal_max_rounds"],
        "transfer_cap": builder["portal"].transfer_cap,
    }


@app.get("/sessions/{session_id}/my-team/retention")
def my_team_retention(session_id: str = ""):
    """Get at-risk players and retention options."""
    sess, session_id, team_name, season = _get_my_team_session(session_id)
    builder = _ensure_roster_builder(sess, session_id, team_name, season)

    nil = builder["nil_program"]
    risks = []
    for r in builder["retention_risks"]:
        retained = r.player_id in builder["retained_players"]
        risks.append({
            **r.to_dict(),
            "retained": retained,
        })

    return {
        "risks": risks,
        "retention_remaining": nil.retention_remaining,
        "retention_pool": nil.retention_pool,
        "retained_count": len(builder["retained_players"]),
    }


@app.post("/sessions/{session_id}/my-team/retention/lock")
def my_team_retention_lock(session_id: str, req: MyTeamRetainRequest):
    """Lock down an at-risk player with NIL retention money."""
    sess, session_id, team_name, season = _get_my_team_session(session_id)
    builder = _ensure_roster_builder(sess, session_id, team_name, season)
    nil = builder["nil_program"]

    if req.player_id in builder["retained_players"]:
        raise HTTPException(400, "Player already retained")

    deal = nil.make_deal("retention", req.player_id, req.player_id, req.amount)
    if not deal:
        raise HTTPException(400, "Not enough retention budget")

    builder["retained_players"].append(req.player_id)

    return {
        "retained": True,
        "player_id": req.player_id,
        "amount": req.amount,
        "retention_remaining": nil.retention_remaining,
    }


@app.get("/sessions/{session_id}/my-team/portal")
def my_team_portal(session_id: str = ""):
    """Get portal state: available players, current round, bids."""
    sess, session_id, team_name, season = _get_my_team_session(session_id)
    builder = _ensure_roster_builder(sess, session_id, team_name, season)
    portal = builder["portal"]
    nil = builder["nil_program"]

    available = []
    for i, e in enumerate(portal.entries):
        if e.committed_to or e.withdrawn:
            continue
        d = _serialize_portal_entry(e)
        d["global_index"] = i
        # Show if human has a pending bid
        bid = builder["portal_bids"].get(i)
        d["my_bid"] = bid["amount"] if bid else None
        available.append(d)

    committed = []
    for e in portal.entries:
        if e.committed_to == team_name:
            committed.append(_serialize_portal_entry(e))

    return {
        "available": available,
        "committed": committed,
        "round": builder["portal_round"],
        "max_rounds": builder["portal_max_rounds"],
        "transfer_cap": portal.transfer_cap,
        "transfers_remaining": portal.transfers_remaining(team_name),
        "portal_remaining": nil.portal_remaining,
        "results": builder["portal_results"],
    }


@app.post("/sessions/{session_id}/my-team/portal/bid")
def my_team_portal_bid(session_id: str, req: MyTeamPortalBidRequest):
    """Place or update a bid on a portal player for the current round."""
    sess, session_id, team_name, season = _get_my_team_session(session_id)
    builder = _ensure_roster_builder(sess, session_id, team_name, season)
    portal = builder["portal"]

    if req.entry_index < 0 or req.entry_index >= len(portal.entries):
        raise HTTPException(400, "Invalid entry index")

    entry = portal.entries[req.entry_index]
    if entry.committed_to or entry.withdrawn:
        raise HTTPException(400, "Player no longer available")

    if portal.transfers_remaining(team_name) <= 0:
        raise HTTPException(400, "Transfer cap reached")

    nil = builder["nil_program"]
    if req.nil_amount > nil.portal_remaining:
        raise HTTPException(400, f"Bid exceeds portal budget (${nil.portal_remaining:,.0f} remaining)")

    builder["portal_bids"][req.entry_index] = {
        "amount": req.nil_amount,
        "team": team_name,
    }

    return {
        "bid_placed": True,
        "entry_index": req.entry_index,
        "amount": req.nil_amount,
        "portal_remaining": nil.portal_remaining,
    }


@app.post("/sessions/{session_id}/my-team/portal/advance")
def my_team_portal_advance(session_id: str):
    """Advance to the next portal round. CPU teams make bids, players decide."""
    import random as _rnd
    sess, session_id, team_name, season = _get_my_team_session(session_id)
    builder = _ensure_roster_builder(sess, session_id, team_name, season)
    portal = builder["portal"]
    nil = builder["nil_program"]
    rng = _rnd.Random(hash(session_id) + builder["portal_round"])

    if builder["portal_round"] >= builder["portal_max_rounds"]:
        raise HTTPException(400, "All portal rounds completed")

    builder["portal_round"] += 1
    round_num = builder["portal_round"]
    round_results = []

    # CPU teams make offers on available players
    cpu_teams = [t for t in season.teams if t != team_name]
    prestige_map = {}
    for t in cpu_teams:
        from engine.transfer_portal import estimate_prestige_from_roster
        prestige_map[t] = estimate_prestige_from_roster(season.teams[t].players)

    available_entries = [(i, e) for i, e in enumerate(portal.entries)
                         if not e.committed_to and not e.withdrawn]

    # Each round, CPU teams compete for available players
    # Tiered interest: elite players draw 7-10 teams, low-tier 1-3
    cpu_offers_this_round = {}

    for idx, entry in available_entries:
        card = entry.player_card
        # Nearly all players attract interest
        if rng.random() > 0.98:
            continue

        ovr = card.overall
        if ovr >= 75:
            n_interested = rng.randint(7, min(10, len(cpu_teams)))
        elif ovr >= 65:
            n_interested = rng.randint(5, min(7, len(cpu_teams)))
        elif ovr >= 55:
            n_interested = rng.randint(4, min(6, len(cpu_teams)))
        elif ovr >= 45:
            n_interested = rng.randint(3, min(5, len(cpu_teams)))
        else:
            n_interested = rng.randint(1, min(3, len(cpu_teams)))

        if n_interested == 0:
            continue
        interested = rng.sample(cpu_teams, n_interested)

        # Get coaching quality for CPU teams
        def _cpu_coaching(t):
            try:
                staffs = getattr(season, "coaching_staffs", {}) or {}
                staff = staffs.get(t, {})
                hc = staff.get("head_coach")
                if hc and hasattr(hc, "development"):
                    return (hc.development + hc.recruiting) / 2.0
                elif isinstance(hc, dict):
                    return (hc.get("development", 50) + hc.get("recruiting", 50)) / 2.0
            except Exception:
                pass
            return 50.0

        best_cpu = None
        best_score = -1
        for t in interested:
            p = prestige_map.get(t, 50)
            coaching = _cpu_coaching(t)
            # Decision: prestige (35%) + coaching (25%) + NIL/culture (20%) + geo (20%)
            score = (p * 0.35
                    + coaching * 0.25
                    + rng.uniform(8, 30)
                    + rng.uniform(8, 25))
            if score > best_score:
                best_score = score
                best_cpu = t

        if best_cpu:
            cpu_offers_this_round[idx] = {"team": best_cpu, "score": best_score}

    # Resolve: for each player with bids, compare human bid vs CPU offers
    for idx, entry in available_entries:
        human_bid = builder["portal_bids"].get(idx)
        cpu_offer = cpu_offers_this_round.get(idx)

        if not human_bid and not cpu_offer:
            continue

        human_score = 0
        if human_bid:
            p = builder["prestige"]
            coaching = _cpu_coaching(team_name)
            nil_factor = min(25, (human_bid["amount"] / max(1, nil.portal_pool)) * 35)
            human_score = (p * 0.35
                          + coaching * 0.25
                          + nil_factor
                          + rng.uniform(8, 25)
                          + rng.uniform(-3, 8))

        cpu_score = cpu_offer["score"] if cpu_offer else 0

        # Low threshold = 20-30 signings per round
        commit_threshold = max(0, 18 - round_num * 4)

        winner = None
        if human_score > cpu_score and human_score > commit_threshold and human_bid:
            winner = team_name
        elif cpu_score > commit_threshold and (not human_bid or cpu_score > human_score) and cpu_offer:
            winner = cpu_offer["team"]
        elif round_num >= builder["portal_max_rounds"]:
            # Last round: players just pick the best offer
            if human_score > cpu_score and human_bid:
                winner = team_name
            elif cpu_offer:
                winner = cpu_offer["team"]

        if winner:
            entry.committed_to = winner
            result = {
                "player_name": entry.player_card.full_name,
                "position": entry.player_card.position,
                "overall": entry.player_card.overall,
                "destination": winner,
                "round": round_num,
                "is_human": winner == team_name,
            }

            if winner == team_name and human_bid:
                # Charge NIL budget
                nil.make_deal("portal", entry.player_card.player_id,
                             entry.player_card.full_name, human_bid["amount"])
                # Add to roster
                from engine.game_engine import Player, assign_archetype
                card = entry.player_card
                new_player = Player(
                    number=max((p.number for p in season.teams[team_name].players), default=0) + 1,
                    name=card.full_name, position=card.position,
                    speed=card.speed, stamina=card.stamina, kicking=card.kicking,
                    lateral_skill=card.lateral_skill, tackling=card.tackling,
                    agility=card.agility, power=card.power, awareness=card.awareness,
                    hands=card.hands, kick_power=card.kick_power, kick_accuracy=card.kick_accuracy,
                    player_id=card.player_id, year=card.year,
                    potential=card.potential, development=card.development,
                )
                new_player.archetype = assign_archetype(new_player)
                season.teams[team_name].players.append(new_player)
                result["nil_spent"] = human_bid["amount"]

            round_results.append(result)

    # Clear bids for next round (bids are per-round)
    builder["portal_bids"] = {}
    builder["portal_results"].append({
        "round": round_num,
        "signings": round_results,
    })

    return {
        "round": round_num,
        "max_rounds": builder["portal_max_rounds"],
        "signings": round_results,
        "remaining_available": sum(1 for e in portal.entries if not e.committed_to and not e.withdrawn),
        "transfers_remaining": portal.transfers_remaining(team_name),
        "portal_remaining": nil.portal_remaining,
    }


@app.post("/sessions/{session_id}/my-team/finalize")
def my_team_finalize(session_id: str):
    """Finalize roster and set session to ready for simulation."""
    sess, session_id, team_name, season = _get_my_team_session(session_id)
    builder = sess.get("roster_builder")
    if not builder:
        raise HTTPException(400, "Roster builder not initialized")

    builder["phase"] = "ready"
    sess["phase"] = "regular"

    team = season.teams[team_name]
    return {
        "finalized": True,
        "team_name": team_name,
        "roster_size": len(team.players),
        "phase": "regular",
    }


@app.post("/sessions/{session_id}/my-team/simulate")
async def my_team_simulate(session_id: str):
    """Simulate the entire season in one shot."""
    sess, session_id, team_name, season = _get_my_team_session(session_id)

    if sess["phase"] != "regular":
        raise HTTPException(400, f"Cannot simulate in phase '{sess['phase']}'. Finalize roster first.")

    def _do_sim():
        season.simulate_season(generate_polls=True, use_fast_sim=True)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_sim_executor, _do_sim)

    # Also simulate bowls and playoffs
    bowl_count = sess["config"].get("bowl_count", 4)
    playoff_size = sess["config"].get("playoff_size", 8)

    if bowl_count > 0 and hasattr(season, "run_bowls"):
        try:
            await loop.run_in_executor(_sim_executor, lambda: season.run_bowls())
        except Exception:
            pass

    if playoff_size > 0 and hasattr(season, "run_playoffs"):
        try:
            await loop.run_in_executor(_sim_executor, lambda: season.run_playoffs())
        except Exception:
            pass

    sess["phase"] = "complete"

    # Get human team results
    record = {"wins": 0, "losses": 0}
    if hasattr(season, "standings") and team_name in season.standings:
        rec = season.standings[team_name]
        record = {"wins": getattr(rec, "wins", 0), "losses": getattr(rec, "losses", 0)}

    return {
        "simulated": True,
        "team_name": team_name,
        "record": record,
        "phase": "complete",
    }


def _seed_player_backstory(card, team_name: str, current_year: int, rng):
    """Generate synthetic career history for a player based on their class year.

    Gives sophomores 1 past season, juniors 2, seniors 3, etc. — so every
    player card has stats and a team history that makes them feel real.
    """
    from engine.player_card import SeasonStats

    year_to_past_seasons = {
        "Freshman": 0, "Sophomore": 1, "Junior": 2, "Senior": 3, "Graduate": 4,
    }
    past_count = year_to_past_seasons.get(card.year, 0)
    if past_count == 0 or card.career_seasons:
        return  # Freshman or already has history

    card.current_team = team_name

    # Generate plausible past seasons
    for i in range(past_count):
        season_year = current_year - past_count + i
        # Younger seasons had slightly lower stats
        age_factor = 0.6 + (i / max(1, past_count)) * 0.4

        games = rng.randint(8, 14)
        ovr = card.overall

        # Position-appropriate stats
        is_skill = card.position in ("Viper", "Halfback", "Wingback", "Slotback", "Zeroback")
        is_line = card.position in ("Offensive Line", "Defensive Line")
        is_keeper = card.position == "Keeper"

        touches = int(rng.randint(30, 120) * age_factor) if is_skill else rng.randint(0, 15)
        yards = int(touches * rng.uniform(3.5, 7.0)) if touches > 0 else 0
        tds = int(touches * rng.uniform(0.03, 0.10)) if is_skill else 0
        fumbles = rng.randint(0, max(1, touches // 30)) if is_skill else 0

        tackles = int(rng.randint(15, 60) * age_factor) if is_line or is_keeper else rng.randint(0, 10)
        tfl = int(tackles * rng.uniform(0.05, 0.20)) if is_line else 0
        sacks = rng.randint(0, max(1, tfl // 2)) if is_line else 0

        kick_att = rng.randint(5, 30) if is_keeper or card.kicking > 65 else 0
        kick_makes = int(kick_att * rng.uniform(0.5, 0.85)) if kick_att > 0 else 0

        # Transfer history: ~15% chance they played elsewhere before
        if i == 0 and past_count >= 2 and rng.random() < 0.15:
            prev_team = rng.choice(["Previous School", "Junior College", "Transfer U"])
            origin_team = prev_team
            card.transfer_count = 1
        else:
            origin_team = team_name

        season = SeasonStats(
            season_year=season_year,
            team=origin_team,
            games_played=games,
            touches=touches,
            total_yards=yards,
            rushing_yards=int(yards * 0.7) if is_skill else 0,
            lateral_yards=int(yards * 0.3) if is_skill else 0,
            touchdowns=tds,
            fumbles=fumbles,
            tackles=tackles,
            tfl=tfl,
            sacks=sacks,
            kick_attempts=kick_att,
            kick_makes=kick_makes,
        )
        card.career_seasons.append(season)

    # Generate past awards for elite players
    if ovr >= 80 and past_count >= 2:
        if rng.random() < 0.4:
            card.career_awards.append({
                "year": current_year - 1,
                "award": "All-Conference" if ovr < 88 else "All-American",
                "team": team_name,
            })
    if ovr >= 85 and past_count >= 3:
        if rng.random() < 0.3:
            card.career_awards.append({
                "year": current_year - 2,
                "award": "All-Conference Honorable Mention",
                "team": team_name,
            })


@app.post("/sessions/{session_id}/my-team/run-it-back")
def my_team_run_it_back(session_id: str):
    """Advance to the next season: age players, graduate seniors, update prestige, reset roster builder."""
    import random as _rnd
    sess, session_id, team_name, season = _get_my_team_session(session_id)
    builder = sess.get("roster_builder")

    if sess["phase"] != "complete":
        raise HTTPException(400, "Season must be complete before running it back")

    from engine.player_card import player_to_card, card_to_player, SeasonStats
    from engine.development import apply_offseason_development, _next_year
    from engine.transfer_portal import estimate_prestige_from_roster
    from engine.nil_system import apply_season_end_regression

    rng = _rnd.Random(hash(session_id) + 999)
    team = season.teams[team_name]

    # Get current season record
    wins = 0
    losses = 0
    if hasattr(season, "standings") and team_name in season.standings:
        rec = season.standings[team_name]
        wins = getattr(rec, "wins", 0)
        losses = getattr(rec, "losses", 0)

    is_champion = hasattr(season, "champion") and season.champion == team_name

    # 1. Convert players to cards for development
    cards = []
    for p in team.players:
        card = player_to_card(p, team_name)

        # Record this season's stats from the simulation
        game_stats = getattr(p, "_season_stats", None)
        if game_stats:
            card.career_seasons.append(game_stats)
        else:
            # Generate approximate stats from the season
            is_skill = card.position in ("Viper", "Halfback", "Wingback", "Slotback", "Zeroback")
            games = getattr(p, "season_games_played", wins + losses)
            if games == 0:
                games = wins + losses
            touches = rng.randint(20, 80) if is_skill else rng.randint(0, 10)
            yards = int(touches * rng.uniform(3.5, 6.5))
            card.career_seasons.append(SeasonStats(
                season_year=2026,
                team=team_name,
                games_played=games,
                touches=touches,
                total_yards=yards,
                touchdowns=int(touches * rng.uniform(0.03, 0.08)) if is_skill else 0,
                tackles=rng.randint(10, 45) if card.position in ("Defensive Line", "Keeper") else rng.randint(0, 8),
            ))

        cards.append(card)

    # 2. Apply development to each player (attribute growth + year advance)
    graduating = []
    returning = []
    for card in cards:
        if card.year in ("Senior", "Graduate"):
            graduating.append(card)
        else:
            apply_offseason_development(card, rng=rng)
            returning.append(card)

    # 3. Update prestige
    old_prestige = builder["prestige"] if builder else estimate_prestige_from_roster(team.players)
    new_prestige = apply_season_end_regression(old_prestige)
    if is_champion:
        new_prestige = min(99, new_prestige + 5)
    # Win/loss adjustment
    if wins > losses:
        new_prestige = min(99, new_prestige + min(5, (wins - losses)))
    elif losses > wins:
        new_prestige = max(1, new_prestige - min(5, (losses - wins)))

    # 4. Rebuild the roster from returning players
    new_players = []
    for card in returning:
        p = card_to_player(card)
        p.year = card.year  # Development already advanced the year
        new_players.append(p)

    # 5. Fill gaps with generated freshmen to get back toward 36
    from engine.game_engine import Player, assign_archetype
    from engine.recruiting import generate_single_recruit
    gap = max(0, 36 - len(new_players))
    for i in range(gap):
        recruit = generate_single_recruit(
            recruit_id=f"FR-{rng.randint(10000, 99999)}",
            rng=rng,
        )
        freshman = Player(
            number=max((p.number for p in new_players), default=0) + 1 + i,
            name=recruit.full_name,
            position=recruit.position,
            speed=recruit.true_speed, stamina=recruit.true_stamina,
            kicking=recruit.true_kicking, lateral_skill=recruit.true_lateral_skill,
            tackling=recruit.true_tackling, agility=recruit.true_agility,
            power=recruit.true_power, awareness=recruit.true_awareness,
            hands=recruit.true_hands, kick_power=recruit.true_kick_power,
            kick_accuracy=recruit.true_kick_accuracy,
            player_id=recruit.recruit_id,
            year="Freshman",
            potential=recruit.true_potential,
            development=recruit.true_development,
        )
        freshman.archetype = assign_archetype(freshman)
        new_players.append(freshman)

    # 6. Replace the team roster
    team.players = new_players

    # 7. Reset season state for next year
    # Clear schedule, standings, etc. but keep teams
    if hasattr(season, "schedule"):
        season.schedule = []
    if hasattr(season, "standings"):
        for t in season.standings:
            rec = season.standings[t]
            rec.wins = 0
            rec.losses = 0
            rec.ties = 0
            rec.points_for = 0
            rec.points_against = 0
            rec.conf_wins = 0
            rec.conf_losses = 0
    if hasattr(season, "champion"):
        season.champion = None
    if hasattr(season, "playoff_bracket"):
        season.playoff_bracket = []
    if hasattr(season, "bowl_games"):
        season.bowl_games = []
    if hasattr(season, "polls"):
        season.polls = {}

    # Regenerate schedule
    if hasattr(season, "generate_schedule"):
        games_per_team = sess["config"].get("games_per_team", 12)
        try:
            season.generate_schedule(games_per_team=games_per_team)
        except Exception:
            pass

    # 8. Clear roster builder so it reinitializes with new prestige
    sess["roster_builder"] = None
    sess["quick_portal"] = None
    sess["phase"] = "setup"

    return {
        "advanced": True,
        "team_name": team_name,
        "previous_record": {"wins": wins, "losses": losses},
        "was_champion": is_champion,
        "old_prestige": old_prestige,
        "new_prestige": new_prestige,
        "graduated": len(graduating),
        "returning": len(returning),
        "freshmen_added": gap,
        "roster_size": len(new_players),
    }
