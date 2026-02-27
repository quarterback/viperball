"""
Viperball Stats Site — Bloomberg-terminal-meets-plaintextsports read-only stats browser.

Mounts as a sub-application on the main FastAPI app under /stats/.
All data comes from the in-memory sessions/pro_sessions/FIV state — no extra HTTP calls.
"""

import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates

router = APIRouter(prefix="/stats")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ── helpers ──────────────────────────────────────────────────────────────

def _get_api():
    """Lazy import to avoid circular imports at module load."""
    from api.main import (
        sessions, pro_sessions,
        _fiv_active_cycle, _fiv_active_cycle_data,
        _get_session, _require_season,
        _serialize_standings, _serialize_game, _serialize_team_record,
        _serialize_player, _serialize_poll,
        LEAGUE_CONFIGS,
    )
    return {
        "sessions": sessions,
        "pro_sessions": pro_sessions,
        "get_session": _get_session,
        "require_season": _require_season,
        "serialize_standings": _serialize_standings,
        "serialize_game": _serialize_game,
        "serialize_team_record": _serialize_team_record,
        "serialize_player": _serialize_player,
        "serialize_poll": _serialize_poll,
        "league_configs": LEAGUE_CONFIGS,
    }


def _get_fiv_data():
    """Get FIV cycle data, returns None if unavailable."""
    try:
        from api.main import _get_fiv_cycle_data
        return _get_fiv_cycle_data()
    except Exception:
        return None


def _get_fiv_rankings():
    """Get FIV rankings."""
    try:
        from engine.fiv import load_fiv_rankings
        return load_fiv_rankings()
    except Exception:
        return None


def _find_active_session():
    """Find the first session with an active season."""
    api = _get_api()
    for sid, sess in api["sessions"].items():
        if sess.get("season") is not None:
            return sid, sess
    return None, None


def _find_all_sessions():
    """Return all sessions that have a season."""
    api = _get_api()
    result = []
    for sid, sess in api["sessions"].items():
        if sess.get("season") is not None:
            season = sess["season"]
            dynasty = sess.get("dynasty")
            result.append({
                "session_id": sid,
                "name": getattr(season, "name", "Season"),
                "team_count": len(season.teams),
                "games_played": sum(1 for g in season.schedule if g.completed),
                "total_games": len(season.schedule),
                "champion": season.champion,
                "is_dynasty": dynasty is not None,
                "dynasty_name": dynasty.dynasty_name if dynasty else None,
                "dynasty_year": dynasty.current_year if dynasty else None,
            })
    return result


def _find_all_pro_sessions():
    """Return all active pro league sessions."""
    api = _get_api()
    result = []
    for key, season in api["pro_sessions"].items():
        result.append({
            "key": key,
            "league_id": season.config.league_id,
            "league_name": season.config.league_name,
            "status": season.get_status(),
        })
    return result


def _ctx(request, **kwargs):
    """Build template context with request and extras."""
    kwargs["request"] = request
    return kwargs


# ── HOME ─────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def stats_home(request: Request):
    college = _find_all_sessions()
    pro = _find_all_pro_sessions()
    fiv_data = _get_fiv_data()
    fiv_rankings = _get_fiv_rankings()
    return templates.TemplateResponse("home.html", _ctx(
        request,
        section="home",
        college_sessions=college,
        pro_sessions=pro,
        fiv_data=fiv_data,
        fiv_rankings=fiv_rankings,
    ))


# ── COLLEGE ──────────────────────────────────────────────────────────────

@router.get("/college/", response_class=HTMLResponse)
def college_index(request: Request):
    sessions = _find_all_sessions()
    return templates.TemplateResponse("college/index.html", _ctx(
        request, section="college", sessions=sessions,
    ))


@router.get("/college/{session_id}/", response_class=HTMLResponse)
def college_season(request: Request, session_id: str):
    api = _get_api()
    try:
        sess = api["get_session"](session_id)
    except HTTPException:
        raise HTTPException(404, "Session not found")
    season = sess.get("season")
    if not season:
        raise HTTPException(404, "No active season")

    standings = api["serialize_standings"](season)
    dynasty = sess.get("dynasty")

    # Get latest poll
    polls = season.weekly_polls
    latest_poll = None
    if polls:
        latest = polls[-1]
        latest_poll = api["serialize_poll"](latest)

    # Season status
    total_games = len(season.schedule)
    games_played = sum(1 for g in season.schedule if g.completed)
    total_weeks = season.get_total_weeks()
    current_week = season.get_last_completed_week()

    return templates.TemplateResponse("college/season.html", _ctx(
        request,
        section="college",
        session_id=session_id,
        season=season,
        standings=standings,
        latest_poll=latest_poll,
        dynasty=dynasty,
        total_games=total_games,
        games_played=games_played,
        total_weeks=total_weeks,
        current_week=current_week,
        champion=season.champion,
    ))


@router.get("/college/{session_id}/standings", response_class=HTMLResponse)
def college_standings(request: Request, session_id: str):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)
    standings = api["serialize_standings"](season)
    conferences = {}
    for conf_name, conf_teams in season.conferences.items():
        conf_standings = season.get_conference_standings(conf_name)
        conferences[conf_name] = [api["serialize_team_record"](r) for r in conf_standings]

    return templates.TemplateResponse("college/standings.html", _ctx(
        request, section="college", session_id=session_id,
        standings=standings, conferences=conferences,
        season_name=getattr(season, "name", "Season"),
    ))


@router.get("/college/{session_id}/schedule", response_class=HTMLResponse)
def college_schedule(request: Request, session_id: str, week: int = 0):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    games = season.schedule
    weeks = sorted(set(g.week for g in games))

    if week > 0:
        filtered = [g for g in games if g.week == week]
    else:
        filtered = games

    serialized = [api["serialize_game"](g) for g in filtered]

    # Add per-week game index for box score links
    week_counters = {}
    for g in serialized:
        w = g["week"]
        idx = week_counters.get(w, 0)
        g["week_game_idx"] = idx
        week_counters[w] = idx + 1

    return templates.TemplateResponse("college/schedule.html", _ctx(
        request, section="college", session_id=session_id,
        games=serialized, weeks=weeks, selected_week=week,
        season_name=getattr(season, "name", "Season"),
    ))


@router.get("/college/{session_id}/polls", response_class=HTMLResponse)
def college_polls(request: Request, session_id: str, week: int = 0):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    dynasty = sess.get("dynasty")
    prestige_map = None
    if dynasty and hasattr(dynasty, "team_prestige") and dynasty.team_prestige:
        prestige_map = dynasty.team_prestige

    polls = season.weekly_polls
    if not polls:
        return templates.TemplateResponse("college/polls.html", _ctx(
            request, section="college", session_id=session_id,
            polls=[], selected_week=0, weeks=[],
            season_name=getattr(season, "name", "Season"),
        ))

    weeks = sorted(set(p.week for p in polls))
    if week > 0:
        selected = [p for p in polls if p.week == week]
    else:
        selected = [polls[-1]]
        week = polls[-1].week

    serialized = [api["serialize_poll"](p, prestige_map=prestige_map) for p in selected]

    return templates.TemplateResponse("college/polls.html", _ctx(
        request, section="college", session_id=session_id,
        polls=serialized, selected_week=week, weeks=weeks,
        season_name=getattr(season, "name", "Season"),
    ))


@router.get("/college/{session_id}/team/{team_name}", response_class=HTMLResponse)
def college_team(request: Request, session_id: str, team_name: str):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    if team_name not in season.teams:
        raise HTTPException(404, f"Team '{team_name}' not found")

    team = season.teams[team_name]
    players = [api["serialize_player"](p) for p in team.players]
    record = season.standings.get(team_name)
    team_record = api["serialize_team_record"](record) if record else None

    # Team schedule
    team_games = [api["serialize_game"](g) for g in season.schedule
                  if g.home_team == team_name or g.away_team == team_name]

    dynasty = sess.get("dynasty")
    prestige = None
    if dynasty and hasattr(dynasty, "team_prestige"):
        prestige = dynasty.team_prestige.get(team_name)

    return templates.TemplateResponse("college/team.html", _ctx(
        request, section="college", session_id=session_id,
        team=team, team_name=team_name, players=players,
        record=team_record, games=team_games, prestige=prestige,
    ))


@router.get("/college/{session_id}/game/{week}/{game_idx}", response_class=HTMLResponse)
def college_game(request: Request, session_id: str, week: int, game_idx: int):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    week_games = [g for g in season.schedule if g.week == week]
    if game_idx < 0 or game_idx >= len(week_games):
        raise HTTPException(404, "Game not found")

    game = week_games[game_idx]
    game_data = api["serialize_game"](game, include_full_result=True)

    return templates.TemplateResponse("college/game.html", _ctx(
        request, section="college", session_id=session_id,
        game=game_data, week=week, game_idx=game_idx,
    ))


@router.get("/college/{session_id}/players", response_class=HTMLResponse)
def college_players(request: Request, session_id: str, sort: str = "yards", conference: str = ""):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    # Aggregate player stats from completed games
    player_agg = {}
    for game in season.schedule:
        if not game.completed or not getattr(game, "full_result", None):
            continue
        fr = game.full_result
        ps = fr.get("player_stats", {})
        for side, t_name in [("home", game.home_team), ("away", game.away_team)]:
            conf = season.team_conferences.get(t_name, "")
            if conference and conf != conference:
                continue
            for p in ps.get(side, []):
                key = f"{t_name}|{p['name']}"
                if key not in player_agg:
                    player_agg[key] = {
                        "name": p["name"], "team": t_name, "conference": conf,
                        "tag": p.get("tag", ""), "archetype": p.get("archetype", ""),
                        "games_played": 0, "touches": 0, "yards": 0,
                        "rushing_yards": 0, "lateral_yards": 0, "tds": 0,
                        "fumbles": 0, "kick_att": 0, "kick_made": 0,
                        "pk_att": 0, "pk_made": 0, "dk_att": 0, "dk_made": 0,
                        "tackles": 0, "tfl": 0, "sacks": 0, "hurries": 0,
                        "kick_pass_yards": 0, "kick_pass_tds": 0,
                        "kick_passes_thrown": 0, "kick_passes_completed": 0,
                        "keeper_bells": 0, "laterals_thrown": 0,
                        "kick_return_yards": 0, "punt_return_yards": 0,
                        "kick_return_tds": 0, "punt_return_tds": 0,
                    }
                agg = player_agg[key]
                agg["games_played"] += 1
                if not agg["tag"]:
                    agg["tag"] = p.get("tag", "")
                if not agg["archetype"] or agg["archetype"] == "—":
                    agg["archetype"] = p.get("archetype", "")
                for stat in [
                    "touches", "yards", "rushing_yards", "lateral_yards",
                    "tds", "fumbles", "kick_att", "kick_made",
                    "pk_att", "pk_made", "dk_att", "dk_made",
                    "tackles", "tfl", "sacks", "hurries",
                    "kick_pass_yards", "kick_pass_tds",
                    "kick_passes_thrown", "kick_passes_completed",
                    "keeper_bells", "laterals_thrown",
                    "kick_return_yards", "punt_return_yards",
                    "kick_return_tds", "punt_return_tds",
                ]:
                    agg[stat] += p.get(stat, 0)

    players = list(player_agg.values())
    for r in players:
        r["yards_per_touch"] = round(r["yards"] / max(1, r["touches"]), 1)
        r["kick_pct"] = round(r["kick_made"] / max(1, r["kick_att"]) * 100, 1)
        r["total_return_yards"] = r["kick_return_yards"] + r["punt_return_yards"]

    # Sort
    valid_sorts = {
        "yards": "yards", "tds": "tds", "touches": "touches",
        "tackles": "tackles", "sacks": "sacks", "kick_pct": "kick_pct",
        "ypc": "yards_per_touch", "fumbles": "fumbles",
        "kick_pass_yards": "kick_pass_yards",
    }
    sort_key = valid_sorts.get(sort, "yards")
    players.sort(key=lambda x: x.get(sort_key, 0), reverse=True)

    conferences = sorted(season.conferences.keys())

    return templates.TemplateResponse("college/players.html", _ctx(
        request, section="college", session_id=session_id,
        players=players[:200], sort=sort, conference=conference,
        conferences=conferences,
        season_name=getattr(season, "name", "Season"),
    ))


@router.get("/college/{session_id}/awards", response_class=HTMLResponse)
def college_awards(request: Request, session_id: str):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    try:
        from engine.awards import compute_season_awards
        honors = compute_season_awards(
            season, year=2025,
            conferences=season.conferences if hasattr(season, 'conferences') else None,
        )
        awards = honors.to_dict()
    except Exception:
        awards = {}

    return templates.TemplateResponse("college/awards.html", _ctx(
        request, section="college", session_id=session_id,
        awards=awards,
        season_name=getattr(season, "name", "Season"),
    ))


# ── PRO LEAGUES ──────────────────────────────────────────────────────────

@router.get("/pro/", response_class=HTMLResponse)
def pro_index(request: Request):
    sessions = _find_all_pro_sessions()
    return templates.TemplateResponse("pro/index.html", _ctx(
        request, section="pro", sessions=sessions,
    ))


@router.get("/pro/{league}/{session_id}/", response_class=HTMLResponse)
def pro_season(request: Request, league: str, session_id: str):
    api = _get_api()
    key = f"{league.lower()}_{session_id}"
    season = api["pro_sessions"].get(key)
    if not season:
        raise HTTPException(404, "Pro league session not found")

    standings = season.get_standings()
    status = season.get_status()

    return templates.TemplateResponse("pro/season.html", _ctx(
        request, section="pro", league=league, session_id=session_id,
        standings=standings, status=status,
        league_name=season.config.league_name,
    ))


@router.get("/pro/{league}/{session_id}/schedule", response_class=HTMLResponse)
def pro_schedule(request: Request, league: str, session_id: str, week: int = 0):
    api = _get_api()
    key = f"{league.lower()}_{session_id}"
    season = api["pro_sessions"].get(key)
    if not season:
        raise HTTPException(404, "Pro league session not found")

    schedule = season.get_schedule()

    return templates.TemplateResponse("pro/schedule.html", _ctx(
        request, section="pro", league=league, session_id=session_id,
        schedule=schedule, selected_week=week,
        league_name=season.config.league_name,
    ))


@router.get("/pro/{league}/{session_id}/game/{week}/{matchup}", response_class=HTMLResponse)
def pro_game(request: Request, league: str, session_id: str, week: int, matchup: str):
    api = _get_api()
    key = f"{league.lower()}_{session_id}"
    season = api["pro_sessions"].get(key)
    if not season:
        raise HTTPException(404, "Pro league session not found")

    box = season.get_box_score(week, matchup)
    if not box:
        raise HTTPException(404, "Game not found")

    return templates.TemplateResponse("pro/game.html", _ctx(
        request, section="pro", league=league, session_id=session_id,
        box=box, week=week, matchup=matchup,
        league_name=season.config.league_name,
    ))


@router.get("/pro/{league}/{session_id}/team/{team_key}", response_class=HTMLResponse)
def pro_team(request: Request, league: str, session_id: str, team_key: str):
    api = _get_api()
    key = f"{league.lower()}_{session_id}"
    season = api["pro_sessions"].get(key)
    if not season:
        raise HTTPException(404, "Pro league session not found")

    detail = season.get_team_detail(team_key)
    if not detail:
        raise HTTPException(404, f"Team '{team_key}' not found")

    return templates.TemplateResponse("pro/team.html", _ctx(
        request, section="pro", league=league, session_id=session_id,
        team=detail, team_key=team_key,
        league_name=season.config.league_name,
    ))


@router.get("/pro/{league}/{session_id}/stats", response_class=HTMLResponse)
def pro_stats(request: Request, league: str, session_id: str, category: str = "all"):
    api = _get_api()
    key = f"{league.lower()}_{session_id}"
    season = api["pro_sessions"].get(key)
    if not season:
        raise HTTPException(404, "Pro league session not found")

    leaders = season.get_stat_leaders(category)

    return templates.TemplateResponse("pro/stats.html", _ctx(
        request, section="pro", league=league, session_id=session_id,
        leaders=leaders, category=category,
        league_name=season.config.league_name,
    ))


# ── INTERNATIONAL (FIV) ─────────────────────────────────────────────────

@router.get("/international/", response_class=HTMLResponse)
def intl_index(request: Request):
    fiv_data = _get_fiv_data()
    fiv_rankings = _get_fiv_rankings()

    rankings_list = []
    if fiv_rankings:
        rankings_list = fiv_rankings.get_ranked_list()

    return templates.TemplateResponse("international/index.html", _ctx(
        request, section="international",
        fiv_data=fiv_data, rankings=rankings_list,
    ))


@router.get("/international/rankings", response_class=HTMLResponse)
def intl_rankings(request: Request):
    fiv_rankings = _get_fiv_rankings()
    rankings_list = []
    if fiv_rankings:
        rankings_list = fiv_rankings.get_ranked_list()

    return templates.TemplateResponse("international/rankings.html", _ctx(
        request, section="international", rankings=rankings_list,
    ))


@router.get("/international/confederation/{conf}", response_class=HTMLResponse)
def intl_confederation(request: Request, conf: str):
    fiv_data = _get_fiv_data()
    if not fiv_data:
        raise HTTPException(404, "No active FIV cycle")

    cc = fiv_data.get("confederations_data", {}).get(conf)
    if not cc:
        raise HTTPException(404, f"Confederation '{conf}' not found")

    return templates.TemplateResponse("international/confederation.html", _ctx(
        request, section="international", conf=conf, data=cc,
    ))


@router.get("/international/worldcup", response_class=HTMLResponse)
def intl_worldcup(request: Request):
    fiv_data = _get_fiv_data()
    if not fiv_data:
        raise HTTPException(404, "No active FIV cycle")

    wc = fiv_data.get("world_cup")

    return templates.TemplateResponse("international/worldcup.html", _ctx(
        request, section="international", wc=wc, fiv_data=fiv_data,
    ))


# ── SEARCH ───────────────────────────────────────────────────────────────

@router.get("/search", response_class=HTMLResponse)
def search(request: Request, q: str = ""):
    results = {"college_teams": [], "college_players": [], "pro_teams": [], "nations": []}

    if not q or len(q) < 2:
        return templates.TemplateResponse("search.html", _ctx(
            request, section="search", query=q, results=results, searched=False,
        ))

    query = q.lower().strip()
    api = _get_api()

    # Search college teams + players
    for sid, sess in api["sessions"].items():
        season = sess.get("season")
        if not season:
            continue
        dynasty = sess.get("dynasty")
        label = dynasty.dynasty_name if dynasty else getattr(season, "name", "Season")

        for team_name, team in season.teams.items():
            if query in team_name.lower() or query in getattr(team, "mascot", "").lower() or query in getattr(team, "abbreviation", "").lower():
                record = season.standings.get(team_name)
                results["college_teams"].append({
                    "session_id": sid, "session_label": label,
                    "team_name": team_name,
                    "mascot": getattr(team, "mascot", ""),
                    "abbreviation": getattr(team, "abbreviation", ""),
                    "conference": season.team_conferences.get(team_name, ""),
                    "record": f"{record.wins}-{record.losses}" if record else "",
                })

            # Search players on this team
            for p in team.players:
                if query in p.name.lower():
                    results["college_players"].append({
                        "session_id": sid, "session_label": label,
                        "name": p.name,
                        "team_name": team_name,
                        "position": getattr(p, "position", ""),
                        "overall": getattr(p, "overall", 0),
                        "year": getattr(p, "year", ""),
                        "number": getattr(p, "number", ""),
                    })

    # Search pro teams
    for key, season in api["pro_sessions"].items():
        parts = key.split("_")
        league_id = parts[0]
        sess_id = parts[1] if len(parts) > 1 else ""
        league_name = season.config.league_name

        # Pro teams are stored differently per league — get standings to find team names
        try:
            standings = season.get_standings()
            all_teams = []
            if isinstance(standings, dict):
                for div_teams in standings.get("divisions", {}).values():
                    if isinstance(div_teams, list):
                        all_teams.extend(div_teams)
                if standings.get("standings"):
                    all_teams.extend(standings["standings"])
            for t in all_teams:
                tname = t.get("team_name", t.get("name", ""))
                tkey = t.get("team_key", tname)
                if query in tname.lower() or query in tkey.lower():
                    results["pro_teams"].append({
                        "league_id": league_id, "session_id": sess_id,
                        "league_name": league_name,
                        "team_name": tname, "team_key": tkey,
                        "record": f"{t.get('wins', 0)}-{t.get('losses', 0)}",
                        "division": t.get("division", ""),
                    })
        except Exception:
            pass

    # Search FIV nations
    fiv_data = _get_fiv_data()
    if fiv_data:
        nations = fiv_data.get("national_teams", {})
        for code, team in nations.items():
            nation = team.get("nation", {}) if isinstance(team, dict) else {}
            name = nation.get("name", "") if isinstance(nation, dict) else ""
            if query in code.lower() or query in name.lower():
                results["nations"].append({
                    "code": code,
                    "name": name,
                    "confederation": nation.get("confederation", "") if isinstance(nation, dict) else "",
                    "tier": nation.get("tier", "") if isinstance(nation, dict) else "",
                })

    return templates.TemplateResponse("search.html", _ctx(
        request, section="search", query=q, results=results, searched=True,
    ))


@router.get("/international/team/{nation_code}", response_class=HTMLResponse)
def intl_team(request: Request, nation_code: str):
    fiv_data = _get_fiv_data()
    if not fiv_data:
        raise HTTPException(404, "No active FIV cycle")

    teams = fiv_data.get("national_teams", {})
    team = teams.get(nation_code)
    if not team:
        raise HTTPException(404, f"Nation '{nation_code}' not found")

    return templates.TemplateResponse("international/team.html", _ctx(
        request, section="international", team=team, nation_code=nation_code,
    ))
