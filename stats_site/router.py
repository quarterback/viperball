"""
Viperball Stats Site — Bloomberg-terminal-meets-plaintextsports read-only stats browser.

Mounts as a sub-application on the main FastAPI app under /stats/.
All data comes from the in-memory sessions/pro_sessions/FIV state — no extra HTTP calls.
"""

import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates

router = APIRouter()

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Conference abbreviation mapping — auto-generates from first letters if not listed
CONF_ABBREVS = {
    "Southern Sun Conference": "SSC",
    "Yankee Fourteen": "Y14",
    "Big Pacific": "BP",
    "Giant 14": "G14",
    "Collegiate Commonwealth": "CC",
    "Interstate Athletic Association": "IAA",
    "Midwest States Interscholastic Association": "MSIA",
    "Moonshine League": "MSL",
    "National Collegiate League": "NCL",
    "Northern Shield": "NS",
    "Outlands Coast Conference": "OCC",
    "Pioneer Athletic Association": "PAA",
    "Potomac Athletic Conference": "PAC",
    "Prairie Athletic Union": "PAU",
    "Border Conference": "BC",
    "Galactic League": "GL",
    "Pacific Conference": "PAC",
    "Mountain West Conference": "MWC",
    "Plains Athletic Conference": "PlAC",
    "Southwest Conference": "SWC",
    "Great Lakes Conference": "GLC",
    "Southeast Conference": "SEC",
    "Southern Athletic Conference": "SAC",
    "Mid-Atlantic Conference": "MAC",
    "Capital Conference": "CAP",
    "Northeast Conference": "NEC",
    "Heartland Conference": "HLC",
    "Metropolitan Athletic Union": "MAU",
}


def _conf_abbrev(name: str) -> str:
    """Get conference abbreviation, auto-generating from initials if needed."""
    if not name:
        return ""
    if name in CONF_ABBREVS:
        return CONF_ABBREVS[name]
    # Auto-generate from first letters of words
    words = name.replace("-", " ").split()
    return "".join(w[0] for w in words[:4]).upper()


# ── helpers ──────────────────────────────────────────────────────────────

def _get_api():
    """Lazy import to avoid circular imports at module load."""
    from api.main import (
        sessions, pro_sessions, wvl_sessions,
        _fiv_active_cycle, _fiv_active_cycle_data,
        _get_session, _require_season,
        _serialize_standings, _serialize_game, _serialize_team_record,
        _serialize_player, _serialize_poll,
        _get_league_configs,
    )
    return {
        "sessions": sessions,
        "pro_sessions": pro_sessions,
        "wvl_sessions": wvl_sessions,
        "get_session": _get_session,
        "require_season": _require_season,
        "serialize_standings": _serialize_standings,
        "serialize_game": _serialize_game,
        "serialize_team_record": _serialize_team_record,
        "serialize_player": _serialize_player,
        "serialize_poll": _serialize_poll,
        "league_configs": _get_league_configs(),
    }


def _get_fiv_data():
    """Get FIV cycle data, returns None if unavailable."""
    try:
        from api.main import _get_fiv_cycle_data
        return _get_fiv_cycle_data()
    except Exception:
        return None


def _get_fiv_cycle():
    """Get live FIV cycle object (not dict), returns None if unavailable."""
    try:
        from api.main import _fiv_active_cycle
        return _fiv_active_cycle
    except Exception:
        return None


def _get_archives():
    """Get list of archived seasons from the database."""
    try:
        from engine.db import list_season_archives, load_season_archive
        return list_season_archives, load_season_archive
    except Exception:
        return None, None


def _get_archive_meta():
    """Get lightweight archive metadata loader (avoids loading full 50MB blobs)."""
    try:
        from engine.db import load_season_archive_meta
        return load_season_archive_meta
    except Exception:
        return None


def _get_all_saved_data():
    """Get list of all saved data from the database (leagues, dynasties, etc.)."""
    try:
        from datetime import datetime, timezone
        from engine.db import list_saves
        saves = list_saves()
        skip_types = {"dq_manager", "user_prefs", "box_score", "bridge", "season_archive_meta"}
        result = []
        for s in saves:
            if s["save_type"] in skip_types:
                continue
            # Convert unix timestamp to ISO string for template rendering
            if isinstance(s.get("updated_at"), (int, float)):
                s["updated_at"] = datetime.fromtimestamp(
                    s["updated_at"], tz=timezone.utc
                ).isoformat()
            result.append(s)
        return result
    except Exception:
        return []


def _get_fiv_rankings():
    """Get FIV rankings."""
    try:
        from engine.fiv import load_fiv_rankings
        return load_fiv_rankings()
    except Exception:
        return None


def _normalize_box_score_stats(full_result: dict):
    """Flatten nested stat dicts so templates can use them as scalars.

    The game engine stores some stats (e.g. ``epa``) as nested dicts with
    sub-keys.  The box-score template expects flat numeric values.  This
    function promotes the relevant scalar out of the dict and replaces the
    original key in-place.
    """
    stats_data = full_result.get("stats", {})
    for side in ("home", "away"):
        side_stats = stats_data.get(side)
        if not side_stats:
            continue
        # EPA: dict -> total_epa scalar
        epa_val = side_stats.get("epa")
        if isinstance(epa_val, dict):
            side_stats["epa"] = epa_val.get("total_epa", epa_val.get("total_vpa"))


def _find_cross_league_links(player_name: str, exclude_college_session: str = None, exclude_nation: str = None):
    """Find appearances of a player across college sessions and international teams.

    Returns a dict with:
      college: list of {"session_id", "team_name", "season_name"}
      international: list of {"nation_code", "nation_name"}
    """
    links = {"college": [], "international": []}

    # Check college sessions
    api = _get_api()
    for sid, sess in api["sessions"].items():
        if sid == exclude_college_session:
            continue
        season = sess.get("season")
        if not season:
            continue
        for team_name, team in season.teams.items():
            for p in team.players:
                if p.name == player_name:
                    links["college"].append({
                        "session_id": sid,
                        "team_name": team_name,
                        "season_name": getattr(season, "name", "Season"),
                    })
                    break

    # Check international/FIV
    fiv_data = _get_fiv_data()
    if fiv_data:
        national_teams = fiv_data.get("national_teams", {})
        for code, team_data in national_teams.items():
            if code == exclude_nation:
                continue
            roster = team_data.get("roster", [])
            for entry in roster:
                p = entry.get("player", entry) if isinstance(entry, dict) else entry
                pname = p.get("name", "") if isinstance(p, dict) else getattr(p, "name", "")
                if pname == player_name:
                    nation_name = team_data.get("name", code)
                    links["international"].append({
                        "nation_code": code,
                        "nation_name": nation_name,
                    })
                    break

    return links


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


def _find_all_wvl_sessions():
    """Return all active WVL sessions."""
    api = _get_api()
    result = []
    for sid, data in api["wvl_sessions"].items():
        season = data.get("season")
        result.append({
            "session_id": sid,
            "dynasty_name": data.get("dynasty_name", "WVL Dynasty"),
            "year": data.get("year", "?"),
            "club_key": data.get("club_key", ""),
            "tier_count": len(season.tier_seasons) if season else 0,
        })
    return result


def _get_wvl_session(session_id: str):
    """Get a WVL session by ID."""
    api = _get_api()
    data = api["wvl_sessions"].get(session_id)
    if not data:
        raise HTTPException(404, "WVL session not found")
    return data


def _ctx(request, **kwargs):
    """Build template context with request and extras."""
    kwargs["request"] = request
    kwargs["conf_abbrev"] = _conf_abbrev
    return kwargs


# ── HOME ─────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def stats_home(request: Request):
    college = _find_all_sessions()
    pro = _find_all_pro_sessions()
    wvl = _find_all_wvl_sessions()
    fiv_data = _get_fiv_data()
    fiv_rankings = _get_fiv_rankings()

    # Load archived seasons
    archives = []
    list_fn, load_fn = _get_archives()
    if list_fn:
        try:
            for meta in list_fn():
                archives.append(meta)
        except Exception:
            pass

    # Load all saved data from DB (may include leagues no longer in memory)
    all_saved = _get_all_saved_data()

    return templates.TemplateResponse("home.html", _ctx(
        request,
        section="home",
        college_sessions=college,
        pro_sessions=pro,
        wvl_sessions=wvl,
        fiv_data=fiv_data,
        fiv_rankings=fiv_rankings,
        archives=archives,
        all_saved=all_saved,
    ))


# ── DELETE SAVED DATA ────────────────────────────────────────────────────

@router.delete("/api/saved/{save_type}/{save_key}")
def delete_saved_data(save_type: str, save_key: str):
    """Delete a saved item from the database."""
    from engine.db import delete_blob
    allowed_types = {
        "pro_league", "dynasty", "wvl_season",
        "season_archive", "league_archive", "college",
    }
    if save_type not in allowed_types:
        raise HTTPException(400, f"Cannot delete save type: {save_type}")
    delete_blob(save_type, save_key)
    # Also clean up associated metadata
    if save_type == "pro_league":
        delete_blob("dq_manager", save_key)
    elif save_type == "season_archive":
        delete_blob("season_archive_meta", save_key)
    return {"ok": True}


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

    # Recent results (last completed week) with box score indices
    recent_games = []
    if current_week:
        week_counters = {}
        for g in season.schedule:
            w = g.week
            idx = week_counters.get(w, 0)
            if g.week == current_week:
                sg = api["serialize_game"](g)
                sg["week_game_idx"] = idx
                recent_games.append(sg)
            week_counters[w] = idx + 1

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
        recent_games=recent_games,
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


def _all_college_games(season) -> list:
    """Return all completed games: regular season + playoff + bowl."""
    games = list(season.schedule)
    games.extend(season.playoff_bracket or [])
    for bg in (season.bowl_games or []):
        games.append(bg.game)
    return games


@router.get("/college/{session_id}/team/{team_name}", response_class=HTMLResponse)
def college_team(request: Request, session_id: str, team_name: str, sort: str = "yards"):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    if team_name not in season.teams:
        raise HTTPException(404, f"Team '{team_name}' not found")

    team = season.teams[team_name]
    players = [api["serialize_player"](p) for p in team.players]
    record = season.standings.get(team_name)
    team_record = api["serialize_team_record"](record) if record else None

    # Team schedule – compute per-week game index for box score links
    week_counters_all = {}
    game_idx_map = {}  # map (week, home, away) -> week_game_idx
    for g in season.schedule:
        w = g.week
        idx = week_counters_all.get(w, 0)
        game_idx_map[(w, g.home_team, g.away_team)] = idx
        week_counters_all[w] = idx + 1

    # Also index playoff and bowl games for box score links
    for g in (season.playoff_bracket or []):
        w = g.week
        idx = week_counters_all.get(w, 0)
        game_idx_map[(w, g.home_team, g.away_team)] = idx
        week_counters_all[w] = idx + 1
    # Build a bowl name lookup by (week, home, away) for display
    bowl_name_map = {}
    for bg in (season.bowl_games or []):
        g = bg.game
        w = g.week
        idx = week_counters_all.get(w, 0)
        game_idx_map[(w, g.home_team, g.away_team)] = idx
        week_counters_all[w] = idx + 1
        bowl_name_map[(w, g.home_team, g.away_team)] = bg.name

    team_games = []
    for g in season.schedule:
        if g.home_team != team_name and g.away_team != team_name:
            continue
        sg = api["serialize_game"](g)
        sg["week_game_idx"] = game_idx_map.get((g.week, g.home_team, g.away_team), 0)
        team_games.append(sg)

    # Add playoff games
    for g in (season.playoff_bracket or []):
        if g.home_team != team_name and g.away_team != team_name:
            continue
        sg = api["serialize_game"](g)
        sg["week_game_idx"] = game_idx_map.get((g.week, g.home_team, g.away_team), 0)
        sg["is_playoff"] = True
        team_games.append(sg)

    # Add bowl games
    for bg in (season.bowl_games or []):
        g = bg.game
        if g.home_team != team_name and g.away_team != team_name:
            continue
        sg = api["serialize_game"](g)
        sg["week_game_idx"] = game_idx_map.get((g.week, g.home_team, g.away_team), 0)
        sg["is_bowl"] = True
        sg["bowl_name"] = bg.name
        team_games.append(sg)

    dynasty = sess.get("dynasty")
    prestige = None
    if dynasty and hasattr(dynasty, "team_prestige"):
        prestige = dynasty.team_prestige.get(team_name)

    # ── Aggregate team season stats from completed games ──
    team_season_stats = None
    completed_games_with_stats = []
    for game in _all_college_games(season):
        if not game.completed or not getattr(game, "full_result", None):
            continue
        if game.home_team != team_name and game.away_team != team_name:
            continue
        side = "home" if game.home_team == team_name else "away"
        stats = game.full_result.get("stats", {}).get(side)
        if stats:
            completed_games_with_stats.append(stats)

    if completed_games_with_stats:
        n = len(completed_games_with_stats)

        # Sum up totals
        total_yards = sum(s.get("total_yards", 0) for s in completed_games_with_stats)
        rushing_yards = sum(s.get("rushing_yards", 0) for s in completed_games_with_stats)
        rushing_carries = sum(s.get("rushing_carries", 0) for s in completed_games_with_stats)
        rushing_tds = sum(s.get("rushing_touchdowns", 0) for s in completed_games_with_stats)
        kp_yards = sum(s.get("kick_pass_yards", 0) for s in completed_games_with_stats)
        kp_att = sum(s.get("kick_passes_attempted", 0) for s in completed_games_with_stats)
        kp_comp = sum(s.get("kick_passes_completed", 0) for s in completed_games_with_stats)
        kp_tds = sum(s.get("kick_pass_tds", 0) for s in completed_games_with_stats)
        kp_ints = sum(s.get("kick_pass_interceptions", 0) for s in completed_games_with_stats)
        lateral_chains = sum(s.get("lateral_chains", 0) for s in completed_games_with_stats)
        lateral_yards = sum(s.get("lateral_yards", 0) for s in completed_games_with_stats)
        touchdowns = sum(s.get("touchdowns", 0) for s in completed_games_with_stats)
        dk_made = sum(s.get("drop_kicks_made", 0) for s in completed_games_with_stats)
        dk_att = sum(s.get("drop_kicks_attempted", 0) for s in completed_games_with_stats)
        pk_made = sum(s.get("place_kicks_made", 0) for s in completed_games_with_stats)
        pk_att = sum(s.get("place_kicks_attempted", 0) for s in completed_games_with_stats)
        fumbles = sum(s.get("fumbles_lost", 0) for s in completed_games_with_stats)
        tod = sum(s.get("turnovers_on_downs", 0) for s in completed_games_with_stats)
        penalties = sum(s.get("penalties", 0) for s in completed_games_with_stats)
        penalty_yards = sum(s.get("penalty_yards", 0) for s in completed_games_with_stats)
        delta_yards = sum(s.get("delta_yards", 0) for s in completed_games_with_stats)
        adjusted_yards = sum(s.get("adjusted_yards", s.get("total_yards", 0) + s.get("delta_yards", 0)) for s in completed_games_with_stats)
        delta_drives = sum(s.get("delta_drives", 0) for s in completed_games_with_stats)
        delta_scores_total = sum(s.get("delta_scores", 0) for s in completed_games_with_stats)
        bonus_poss = sum(s.get("bonus_possessions", 0) for s in completed_games_with_stats)
        bonus_scores = sum(s.get("bonus_possession_scores", 0) for s in completed_games_with_stats)
        bonus_yards = sum(s.get("bonus_possession_yards", 0) for s in completed_games_with_stats)
        successful_laterals = sum(s.get("successful_laterals", 0) for s in completed_games_with_stats)
        total_plays = sum(s.get("total_plays", 0) for s in completed_games_with_stats)

        # EPA: handle both dict (from calculate_game_epa) and number values
        total_epa = 0
        for s in completed_games_with_stats:
            epa_val = s.get("epa", 0)
            if isinstance(epa_val, dict):
                total_epa += epa_val.get("total_epa", epa_val.get("wpa", 0))
            elif isinstance(epa_val, (int, float)):
                total_epa += epa_val

        # Down conversions (keys are ints 4, 5, 6)
        down_conv = {}
        for d in [4, 5, 6]:
            att_total = 0
            conv_total = 0
            for s in completed_games_with_stats:
                dc = s.get("down_conversions", {})
                dd = dc.get(d, dc.get(str(d), {}))
                att_total += dd.get("attempts", 0)
                conv_total += dd.get("converted", 0)
            down_conv[d] = {
                "att": att_total,
                "conv": conv_total,
                "rate": round(conv_total / max(1, att_total) * 100, 1),
            }

        # Averages from viperball_metrics and viper_efficiency
        viper_eff_vals = [s.get("viper_efficiency", 0) for s in completed_games_with_stats if s.get("viper_efficiency") is not None]
        team_rating_vals = []
        for s in completed_games_with_stats:
            vm = s.get("viperball_metrics", {})
            if vm and vm.get("team_rating") is not None:
                team_rating_vals.append(vm["team_rating"])

        team_season_stats = {
            "games_played": n,
            "total_yards": total_yards,
            "total_plays": total_plays,
            "avg_yards": round(total_yards / n, 1),
            "yards_per_play": round(total_yards / max(1, total_plays), 2),
            "rushing_yards": rushing_yards,
            "avg_rushing": round(rushing_yards / n, 1),
            "rushing_carries": rushing_carries,
            "rushing_tds": rushing_tds,
            "yards_per_carry": round(rushing_yards / max(1, rushing_carries), 1),
            "kick_pass_yards": kp_yards,
            "kp_attempts": kp_att,
            "kp_completions": kp_comp,
            "kp_comp_pct": round(kp_comp / max(1, kp_att) * 100, 1),
            "kp_tds": kp_tds,
            "kp_ints": kp_ints,
            "lateral_chains": lateral_chains,
            "lateral_yards": lateral_yards,
            "successful_laterals": successful_laterals,
            "lateral_pct": round(successful_laterals / max(1, lateral_chains) * 100, 1),
            "touchdowns": touchdowns,
            "dk_made": dk_made,
            "dk_att": dk_att,
            "pk_made": pk_made,
            "pk_att": pk_att,
            "fumbles": fumbles,
            "tod": tod,
            "penalties": penalties,
            "penalty_yards": penalty_yards,
            "delta_yards": delta_yards,
            "adjusted_yards": adjusted_yards,
            "delta_drives": delta_drives,
            "delta_scores": delta_scores_total,
            "kill_rate": round(delta_scores_total / max(1, delta_drives) * 100, 1) if delta_drives > 0 else None,
            "bonus_possessions": bonus_poss,
            "bonus_scores": bonus_scores,
            "bonus_yards": bonus_yards,
            "total_epa": round(total_epa, 1),
            "avg_epa": round(total_epa / n, 2),
            "down_conv_4": down_conv[4],
            "down_conv_5": down_conv[5],
            "down_conv_6": down_conv[6],
            "avg_team_rating": round(sum(team_rating_vals) / max(1, len(team_rating_vals)), 1) if team_rating_vals else None,
            "avg_viper_eff": round(sum(viper_eff_vals) / max(1, len(viper_eff_vals)), 3) if viper_eff_vals else None,
        }

    # ── Aggregate per-player season stats ──
    player_season_stats = {}
    for game in _all_college_games(season):
        if not game.completed or not getattr(game, "full_result", None):
            continue
        if game.home_team != team_name and game.away_team != team_name:
            continue
        side = "home" if game.home_team == team_name else "away"
        ps = game.full_result.get("player_stats", {})
        for p in ps.get(side, []):
            key = p["name"]
            if key not in player_season_stats:
                player_season_stats[key] = {
                    "name": p["name"], "tag": p.get("tag", ""),
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
                    "rush_carries": 0, "rushing_tds": 0,
                    "lateral_receptions": 0, "lateral_assists": 0, "lateral_tds": 0,
                    "kick_pass_interceptions": 0, "kick_pass_receptions": 0,
                    "kick_pass_ints": 0,
                    "kick_returns": 0, "punt_returns": 0,
                    "muffs": 0, "st_tackles": 0,
                    "keeper_tackles": 0, "kick_deflections": 0,
                    "coverage_snaps": 0, "blocks": 0, "pancakes": 0,
                    "wpa": 0.0, "plays_involved": 0,
                }
            agg = player_season_stats[key]
            agg["games_played"] += 1
            if not agg["tag"]:
                agg["tag"] = p.get("tag", "")
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
                "rush_carries", "rushing_tds",
                "lateral_receptions", "lateral_assists", "lateral_tds",
                "kick_pass_interceptions", "kick_pass_receptions",
                "kick_pass_ints",
                "kick_returns", "punt_returns",
                "muffs", "st_tackles",
                "keeper_tackles", "kick_deflections",
                "coverage_snaps", "blocks", "pancakes",
                "plays_involved",
            ]:
                agg[stat] += p.get(stat, 0)
            agg["wpa"] += p.get("wpa", 0.0)

    for r in player_season_stats.values():
        r["yards_per_touch"] = round(r["yards"] / max(1, r["touches"]), 1)
        r["kick_pct"] = round(r["kick_made"] / max(1, r["kick_att"]) * 100, 1)
        r["total_return_yards"] = r["kick_return_yards"] + r["punt_return_yards"]
        r["kp_pct"] = round(r["kick_passes_completed"] / max(1, r["kick_passes_thrown"]) * 100, 1)
        r["wpa"] = round(r["wpa"], 2)

    # Build merged roster: player info + season stats, then sort
    sorted_roster = []
    for p_ser in players:
        ps = player_season_stats.get(p_ser["name"], {})
        entry = {**p_ser, **ps}
        entry.setdefault("games_played", 0)
        entry.setdefault("yards", 0)
        entry.setdefault("touches", 0)
        entry.setdefault("yards_per_touch", 0)
        entry.setdefault("tds", 0)
        entry.setdefault("rushing_tds", 0)
        entry.setdefault("fumbles", 0)
        entry.setdefault("laterals_thrown", 0)
        entry.setdefault("kick_att", 0)
        entry.setdefault("kick_made", 0)
        entry.setdefault("kick_pct", 0)
        entry.setdefault("kick_passes_thrown", 0)
        entry.setdefault("kick_passes_completed", 0)
        entry.setdefault("kick_pass_receptions", 0)
        entry.setdefault("tackles", 0)
        entry.setdefault("tfl", 0)
        entry.setdefault("sacks", 0)
        entry.setdefault("hurries", 0)
        entry.setdefault("total_return_yards", 0)
        entry.setdefault("keeper_bells", 0)
        entry.setdefault("blocks", 0)
        entry.setdefault("pancakes", 0)
        entry.setdefault("wpa", 0)
        entry.setdefault("kick_pass_yards", 0)
        entry.setdefault("kick_pass_tds", 0)
        entry.setdefault("kick_pass_interceptions", 0)
        entry.setdefault("kick_pass_ints", 0)
        entry.setdefault("kick_return_yards", 0)
        entry.setdefault("punt_return_yards", 0)
        entry.setdefault("lateral_receptions", 0)
        entry.setdefault("lateral_tds", 0)
        entry.setdefault("rush_carries", 0)
        entry.setdefault("st_tackles", 0)
        entry.setdefault("kick_deflections", 0)
        entry.setdefault("kp_pct", 0)
        sorted_roster.append(entry)

    roster_sorts = {
        "yards": "yards", "tds": "tds", "touches": "touches",
        "ypc": "yards_per_touch", "rush_carries": "rush_carries",
        "rushing_tds": "rushing_tds", "fumbles": "fumbles",
        "laterals": "laterals_thrown", "lateral_rec": "lateral_receptions",
        "lateral_tds": "lateral_tds",
        "kick_pass_yards": "kick_pass_yards", "kp_tds": "kick_pass_tds",
        "kp_pct": "kp_pct", "kp_ints": "kick_pass_interceptions",
        "kp_rec": "kick_pass_receptions",
        "kick_pct": "kick_pct",
        "tackles": "tackles", "tfl": "tfl", "sacks": "sacks",
        "hurries": "hurries", "def_ints": "kick_pass_ints",
        "kr_yds": "kick_return_yards", "pr_yds": "punt_return_yards",
        "st_tackles": "st_tackles",
        "bells": "keeper_bells", "deflections": "kick_deflections",
        "blocks": "blocks", "pancakes": "pancakes",
        "wpa": "wpa",
    }
    sort_key = roster_sorts.get(sort, "yards")
    sorted_roster.sort(key=lambda x: x.get(sort_key, 0), reverse=True)

    # ── Collect awards for this team ──
    team_awards = []
    # Weekly awards (player & coach of the week) — show as they happen
    for wa in getattr(season, 'weekly_awards', []):
        if wa.get("team_name") == team_name:
            team_awards.append({
                "award": wa["award"], "player": wa["player_name"],
                "position": wa.get("position", ""), "level": f"Week {wa['week']}",
            })
    regular_season_done = season.is_regular_season_complete() if hasattr(season, 'is_regular_season_complete') else all(g.completed for g in season.schedule)
    if regular_season_done:
        try:
            from engine.awards import compute_season_awards
            honors = compute_season_awards(
                season, year=2025,
                conferences=season.conferences if hasattr(season, 'conferences') else None,
            )
            # Individual national awards
            for a in honors.individual_awards:
                if a.team_name == team_name:
                    team_awards.append({"award": a.award_name, "player": a.player_name,
                                        "position": a.position, "level": "National"})
            # All-CVL teams
            for tier_label, tier_obj in [
                ("All-CVL First Team", honors.all_american_first),
                ("All-CVL Second Team", honors.all_american_second),
                ("All-CVL Third Team", honors.all_american_third),
                ("All-CVL Honorable Mention", honors.honorable_mention),
                ("All-Freshman Team", honors.all_freshman),
            ]:
                if tier_obj:
                    for slot in tier_obj.slots:
                        if slot.team_name == team_name:
                            team_awards.append({"award": tier_label, "player": slot.player_name,
                                                "position": slot.position, "level": "National"})
            # Conference awards
            for conf_name, conf_awards_list in honors.conference_awards.items():
                for a in conf_awards_list:
                    if a.team_name == team_name:
                        team_awards.append({"award": a.award_name, "player": a.player_name,
                                            "position": a.position, "level": "Conference"})
            # All-Conference teams
            for conf_name, conf_teams_dict in honors.all_conference_teams.items():
                for tier_key, tier_obj in conf_teams_dict.items():
                    tier_label = f"All-{conf_name} {tier_obj.team_level.replace('_', ' ').title()}"
                    for slot in tier_obj.slots:
                        if slot.team_name == team_name:
                            team_awards.append({"award": tier_label, "player": slot.player_name,
                                                "position": slot.position, "level": "Conference"})
        except Exception:
            pass

    # ── Coaching staff for this team ──
    coaching_staff = []
    staff_dict = (season.coaching_staffs or {}).get(team_name, {})
    if staff_dict:
        from engine.coaching import CoachCard
        for role in ["head_coach", "oc", "dc", "stc"]:
            card = staff_dict.get(role)
            if not card:
                continue
            if isinstance(card, dict):
                card = CoachCard.from_dict(card)
            role_label = {"head_coach": "HC", "oc": "OC", "dc": "DC", "stc": "STC"}.get(role, role)
            coaching_staff.append({
                "role": role, "role_label": role_label,
                "name": card.full_name,
                "overall": round(card.visible_score, 1),
                "classification_label": card.classification_label,
                "composure_label": card.composure_label,
                "career_wins": card.career_wins, "career_losses": card.career_losses,
                "win_pct": round(card.win_percentage, 3),
                "championships": card.championships,
                "philosophy": card.philosophy,
                "coaching_style": card.coaching_style,
            })

    return templates.TemplateResponse("college/team.html", _ctx(
        request, section="college", session_id=session_id,
        team=team, team_name=team_name, players=players,
        record=team_record, games=team_games, prestige=prestige,
        team_stats=team_season_stats,
        sorted_roster=sorted_roster, sort=sort,
        team_awards=team_awards,
        coaching_staff=coaching_staff,
    ))


@router.get("/college/{session_id}/coach/{team_name}/{coach_role}", response_class=HTMLResponse)
def college_coach(request: Request, session_id: str, team_name: str, coach_role: str):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    if team_name not in season.teams:
        raise HTTPException(404, f"Team '{team_name}' not found")

    staff_dict = (season.coaching_staffs or {}).get(team_name, {})
    card = staff_dict.get(coach_role)
    if not card:
        raise HTTPException(404, f"No coach found for role '{coach_role}' at {team_name}")

    from engine.coaching import CoachCard
    if isinstance(card, dict):
        card = CoachCard.from_dict(card)

    role_label = {"head_coach": "Head Coach", "oc": "Offensive Coordinator",
                  "dc": "Defensive Coordinator", "stc": "Special Teams Coordinator"}.get(coach_role, coach_role)

    # Career history
    career_history = []
    for stop in (card.career_history or []):
        if isinstance(stop, dict):
            career_history.append(stop)
        else:
            career_history.append(stop.to_dict())

    # Coaching tree
    coaching_tree = list(card.coaching_tree or [])

    # Team record this season
    record = season.standings.get(team_name)
    season_record = record.record_str if record else "0-0"

    # Collect awards for this coach
    coach_awards = []
    coach_display = card.full_name
    coach_display_paren = f"{card.full_name} ({team_name})"
    # Weekly awards
    for wa in getattr(season, 'weekly_awards', []):
        if wa.get("position") == "Coach" and wa.get("team_name") == team_name:
            coach_awards.append({
                "award": wa["award"], "detail": f"Week {wa['week']}",
                "stat_line": wa.get("stat_line", ""),
            })
    # End-of-season awards
    regular_season_done = season.is_regular_season_complete() if hasattr(season, 'is_regular_season_complete') else all(g.completed for g in season.schedule)
    if regular_season_done:
        try:
            from engine.awards import compute_season_awards
            honors = compute_season_awards(
                season, year=2025,
                conferences=season.conferences if hasattr(season, 'conferences') else None,
            )
            # National Coach of the Year
            if honors.coach_of_year and (team_name in honors.coach_of_year):
                coach_awards.append({"award": "National Coach of the Year", "detail": "Season", "stat_line": season_record})
            # Conference awards
            for conf_name, conf_awards_list in honors.conference_awards.items():
                for a in conf_awards_list:
                    if a.position == "Coach" and a.team_name == team_name:
                        coach_awards.append({"award": a.award_name, "detail": "Season", "stat_line": season_record})
        except Exception:
            pass

    # Personality sliders for display
    sliders = card.personality_sliders or {}

    return templates.TemplateResponse("college/coach.html", _ctx(
        request, section="college", session_id=session_id,
        coach=card, team_name=team_name, role=coach_role, role_label=role_label,
        career_history=career_history, coaching_tree=coaching_tree,
        season_record=season_record, coach_awards=coach_awards,
        sliders=sliders,
    ))


@router.get("/college/{session_id}/game/{week}/{game_idx}", response_class=HTMLResponse)
def college_game(request: Request, session_id: str, week: int, game_idx: int):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    week_games = [g for g in season.schedule if g.week == week]

    # Also search playoff bracket and bowl games for postseason weeks
    bowl_name = None
    is_playoff = False
    if not week_games:
        playoff_games = [g for g in (season.playoff_bracket or []) if g.week == week]
        bowl_game_list = [(bg.game, bg.name) for bg in (season.bowl_games or []) if bg.game.week == week]
        if playoff_games:
            week_games = playoff_games
            is_playoff = True
        elif bowl_game_list:
            week_games = [bg[0] for bg in bowl_game_list]
            if game_idx < len(bowl_game_list):
                bowl_name = bowl_game_list[game_idx][1]

    if game_idx < 0 or game_idx >= len(week_games):
        raise HTTPException(404, "Game not found")

    game = week_games[game_idx]
    game_data = api["serialize_game"](game, include_full_result=True)

    # If the in-memory full_result is gone (e.g. server restart), try the DB.
    if not game_data.get("full_result") and game_data.get("completed"):
        try:
            from engine.db import load_box_score
            db_fr = load_box_score(session_id, week, game.home_team, game.away_team)
            if db_fr:
                game_data["full_result"] = db_fr
                game_data["has_full_result"] = True
        except Exception:
            pass

    # Inject fast_sim metrics as viperball_metrics so templates can find them
    # (mirrors the fix in pro_league.get_box_score)
    fr = game_data.get("full_result")
    if fr and fr.get("_fast_sim"):
        fsm = fr.get("_fast_sim_metrics", {})
        stats_data = fr.get("stats", {})
        for side in ("home", "away"):
            side_stats = stats_data.get(side)
            if side_stats and side in fsm and "viperball_metrics" not in side_stats:
                side_stats["viperball_metrics"] = fsm[side]

    # Normalize nested stat dicts so templates can compare them as scalars.
    # The game engine stores EPA as a dict with sub-keys; the template
    # expects a single number.
    if fr:
        _normalize_box_score_stats(fr)

    return templates.TemplateResponse("college/game.html", _ctx(
        request, section="college", session_id=session_id,
        game=game_data, week=week, game_idx=game_idx,
        bowl_name=bowl_name, is_playoff=is_playoff,
    ))


@router.get("/college/{session_id}/player/{team_name}/{player_name}", response_class=HTMLResponse)
def college_player(request: Request, session_id: str, team_name: str, player_name: str):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    if team_name not in season.teams:
        raise HTTPException(404, f"Team '{team_name}' not found")

    team = season.teams[team_name]
    player = None
    for p in team.players:
        if p.name == player_name:
            player = p
            break
    if not player:
        raise HTTPException(404, f"Player '{player_name}' not found on {team_name}")

    # Basic serialized info
    player_data = api["serialize_player"](player)

    # Build player card if available
    card = None
    try:
        from engine.player_card import player_to_card
        pc = player_to_card(player, team_name)
        card = pc.to_dict()
    except Exception:
        pass

    # Build game log from completed games this season
    game_log = []
    season_totals = {
        "games": 0, "touches": 0, "yards": 0, "rushing_yards": 0,
        "lateral_yards": 0, "tds": 0, "fumbles": 0, "laterals_thrown": 0,
        "kick_att": 0, "kick_made": 0, "pk_att": 0, "pk_made": 0,
        "dk_att": 0, "dk_made": 0, "tackles": 0, "tfl": 0, "sacks": 0,
        "hurries": 0, "kick_pass_yards": 0, "kick_pass_tds": 0,
        "kick_passes_thrown": 0, "kick_passes_completed": 0,
        "kick_return_yards": 0, "punt_return_yards": 0,
        # Rushing detail
        "rush_carries": 0, "rushing_tds": 0,
        # Lateral chain
        "lateral_receptions": 0, "lateral_assists": 0, "lateral_tds": 0,
        # Kick pass detail
        "kick_pass_interceptions_thrown": 0, "kick_pass_receptions": 0,
        "kick_pass_ints": 0,
        # Special teams
        "kick_returns": 0, "kick_return_tds": 0,
        "punt_returns": 0, "punt_return_tds": 0,
        "muffs": 0, "st_tackles": 0,
        # Keeper
        "keeper_tackles": 0, "keeper_bells": 0,
        "kick_deflections": 0, "coverage_snaps": 0,
        "keeper_return_yards": 0,
        # Line play
        "blocks": 0, "pancakes": 0,
        # Impact
        "wpa": 0.0, "plays_involved": 0,
    }
    for game in _all_college_games(season):
        if not game.completed or not getattr(game, "full_result", None):
            continue
        if game.home_team != team_name and game.away_team != team_name:
            continue
        side = "home" if game.home_team == team_name else "away"
        opponent = game.away_team if side == "home" else game.home_team
        is_home = side == "home"
        fr = game.full_result
        ps = fr.get("player_stats", {}).get(side, [])
        for pg in ps:
            if pg.get("name") == player_name:
                entry = {
                    "week": game.week,
                    "opponent": opponent,
                    "is_home": is_home,
                    "won": (game.home_score > game.away_score) == is_home,
                    "team_score": game.home_score if is_home else game.away_score,
                    "opp_score": game.away_score if is_home else game.home_score,
                }
                entry.update(pg)
                game_log.append(entry)
                season_totals["games"] += 1
                for stat in [
                    "touches", "yards", "rushing_yards", "lateral_yards",
                    "tds", "fumbles", "laterals_thrown",
                    "kick_att", "kick_made", "pk_att", "pk_made",
                    "dk_att", "dk_made", "tackles", "tfl", "sacks", "hurries",
                    "kick_pass_yards", "kick_pass_tds",
                    "kick_passes_thrown", "kick_passes_completed",
                    "kick_return_yards", "punt_return_yards",
                    "rush_carries", "rushing_tds",
                    "lateral_receptions", "lateral_assists", "lateral_tds",
                    "kick_pass_interceptions_thrown", "kick_pass_receptions",
                    "kick_pass_ints",
                    "kick_returns", "kick_return_tds",
                    "punt_returns", "punt_return_tds",
                    "muffs", "st_tackles",
                    "keeper_tackles", "keeper_bells",
                    "kick_deflections", "coverage_snaps",
                    "keeper_return_yards",
                    "blocks", "pancakes",
                    "wpa", "plays_involved",
                ]:
                    season_totals[stat] += pg.get(stat, 0)
                break

    # Derived season totals
    season_totals["yards_per_touch"] = round(
        season_totals["yards"] / max(1, season_totals["touches"]), 1
    )
    season_totals["kick_pct"] = round(
        season_totals["kick_made"] / max(1, season_totals["kick_att"]) * 100, 1
    )
    season_totals["total_return_yards"] = (
        season_totals["kick_return_yards"] + season_totals["punt_return_yards"]
    )
    season_totals["kp_pct"] = round(
        season_totals["kick_passes_completed"] / max(1, season_totals["kick_passes_thrown"]) * 100, 1
    )
    season_totals["kick_return_avg"] = round(
        season_totals["kick_return_yards"] / max(1, season_totals["kick_returns"]), 1
    )
    season_totals["punt_return_avg"] = round(
        season_totals["punt_return_yards"] / max(1, season_totals["punt_returns"]), 1
    )
    season_totals["wpa_per_play"] = round(
        season_totals["wpa"] / max(1, season_totals["plays_involved"]), 3
    )

    # Team record for context
    record = season.standings.get(team_name)
    team_record = api["serialize_team_record"](record) if record else None

    dynasty = sess.get("dynasty")
    prestige = None
    if dynasty and hasattr(dynasty, "team_prestige"):
        prestige = dynasty.team_prestige.get(team_name)

    cross_links = _find_cross_league_links(player_name, exclude_college_session=session_id)

    # ── Collect awards for this player ──
    player_awards = []

    # Weekly awards
    for wa in getattr(season, 'weekly_awards', []):
        if wa.get("player_name") == player_name and wa.get("team_name") == team_name:
            player_awards.append({
                "award": wa["award"],
                "detail": f"Week {wa['week']}",
                "stat_line": wa.get("stat_line", ""),
                "level": "weekly",
            })

    # End-of-season awards (only if regular season complete)
    regular_season_done = season.is_regular_season_complete() if hasattr(season, 'is_regular_season_complete') else all(g.completed for g in season.schedule)
    if regular_season_done:
        try:
            from engine.awards import compute_season_awards
            honors = compute_season_awards(
                season, year=2025,
                conferences=season.conferences if hasattr(season, 'conferences') else None,
            )
            for a in honors.individual_awards:
                if a.player_name == player_name and a.team_name == team_name:
                    player_awards.append({"award": a.award_name, "detail": "Season", "stat_line": "", "level": "national"})
            for tier_label, tier_obj in [
                ("All-CVL First Team", honors.all_american_first),
                ("All-CVL Second Team", honors.all_american_second),
                ("All-CVL Third Team", honors.all_american_third),
                ("All-CVL Honorable Mention", honors.honorable_mention),
                ("All-Freshman Team", honors.all_freshman),
            ]:
                if tier_obj:
                    for slot in tier_obj.slots:
                        if slot.player_name == player_name and slot.team_name == team_name:
                            player_awards.append({"award": tier_label, "detail": "Season", "stat_line": "", "level": "national"})
            for conf_name, conf_awards_list in honors.conference_awards.items():
                for a in conf_awards_list:
                    if a.player_name == player_name and a.team_name == team_name:
                        player_awards.append({"award": a.award_name, "detail": "Season", "stat_line": "", "level": "conference"})
            for conf_name, conf_teams_dict in honors.all_conference_teams.items():
                for tier_key, tier_obj in conf_teams_dict.items():
                    tier_label = f"All-{conf_name} {tier_obj.team_level.replace('_', ' ').title()}"
                    for slot in tier_obj.slots:
                        if slot.player_name == player_name and slot.team_name == team_name:
                            player_awards.append({"award": tier_label, "detail": "Season", "stat_line": "", "level": "conference"})
        except Exception:
            pass

    return templates.TemplateResponse("college/player.html", _ctx(
        request, section="college", session_id=session_id,
        player=player_data, card=card, team_name=team_name,
        team=team, game_log=game_log, season_totals=season_totals,
        record=team_record, prestige=prestige, cross_links=cross_links,
        player_awards=player_awards,
    ))


@router.get("/college/{session_id}/players", response_class=HTMLResponse)
def college_players(request: Request, session_id: str, sort: str = "yards", conference: str = ""):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    # Aggregate player stats from completed games (including postseason)
    player_agg = {}
    for game in _all_college_games(season):
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
                        "position": p.get("position", ""),
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
                        "rush_carries": 0, "rushing_tds": 0,
                        "lateral_receptions": 0, "lateral_assists": 0, "lateral_tds": 0,
                        "kick_pass_interceptions": 0, "kick_pass_receptions": 0,
                        "kick_pass_ints": 0,
                        "kick_returns": 0, "punt_returns": 0,
                        "muffs": 0, "st_tackles": 0,
                        "keeper_tackles": 0, "kick_deflections": 0,
                        "coverage_snaps": 0, "blocks": 0, "pancakes": 0,
                        "wpa": 0.0, "plays_involved": 0,
                    }
                agg = player_agg[key]
                agg["games_played"] += 1
                if not agg["tag"]:
                    agg["tag"] = p.get("tag", "")
                if not agg["archetype"] or agg["archetype"] == "—":
                    agg["archetype"] = p.get("archetype", "")
                if not agg["position"]:
                    agg["position"] = p.get("position", "")
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
                    "rush_carries", "rushing_tds",
                    "lateral_receptions", "lateral_assists", "lateral_tds",
                    "kick_pass_interceptions", "kick_pass_receptions",
                    "kick_pass_ints",
                    "kick_returns", "punt_returns",
                    "muffs", "st_tackles",
                    "keeper_tackles", "kick_deflections",
                    "coverage_snaps", "blocks", "pancakes",
                    "plays_involved",
                ]:
                    agg[stat] += p.get(stat, 0)
                agg["wpa"] += p.get("wpa", 0.0)

    from engine.viperball_metrics import calculate_war, calculate_zbr, calculate_vpr

    players = list(player_agg.values())
    for r in players:
        r["yards_per_touch"] = round(r["yards"] / max(1, r["touches"]), 1)
        r["kick_pct"] = round(r["kick_made"] / max(1, r["kick_att"]) * 100, 1)
        r["total_return_yards"] = r["kick_return_yards"] + r["punt_return_yards"]
        r["kp_pct"] = round(r["kick_passes_completed"] / max(1, r["kick_passes_thrown"]) * 100, 1)
        r["kick_return_avg"] = round(r["kick_return_yards"] / max(1, r["kick_returns"]), 1)
        r["punt_return_avg"] = round(r["punt_return_yards"] / max(1, r["punt_returns"]), 1)
        r["wpa_per_play"] = round(r["wpa"] / max(1, r["plays_involved"]), 2)
        r["wpa"] = round(r["wpa"], 2)
        # Sabermetrics
        r["war"] = calculate_war(r, r.get("position", ""))
        r["zbr"] = calculate_zbr(r)
        r["vpr"] = calculate_vpr(r)

    # Sort
    valid_sorts = {
        # Offense
        "yards": "yards", "tds": "tds", "touches": "touches",
        "ypc": "yards_per_touch", "rush_carries": "rush_carries",
        "rushing_tds": "rushing_tds", "fumbles": "fumbles",
        # Lateral
        "laterals": "laterals_thrown", "lateral_rec": "lateral_receptions",
        "lateral_tds": "lateral_tds",
        # Kick Pass
        "kick_pass_yards": "kick_pass_yards", "kp_tds": "kick_pass_tds",
        "kp_pct": "kp_pct", "kp_ints": "kick_pass_interceptions",
        "kp_rec": "kick_pass_receptions",
        # Kicking
        "kick_pct": "kick_pct",
        # Defense
        "tackles": "tackles", "tfl": "tfl", "sacks": "sacks",
        "hurries": "hurries", "def_ints": "kick_pass_ints",
        # Special Teams
        "kr_yds": "kick_return_yards", "pr_yds": "punt_return_yards",
        "st_tackles": "st_tackles",
        # Keeper
        "bells": "keeper_bells", "deflections": "kick_deflections",
        # Line Play
        "blocks": "blocks", "pancakes": "pancakes",
        # Impact
        "wpa": "wpa",
        # Analytics
        "war": "war", "zbr": "zbr", "vpr": "vpr",
    }
    sort_key = valid_sorts.get(sort, "yards")
    players.sort(key=lambda x: x.get(sort_key, 0), reverse=True)

    conferences = sorted(season.conferences.keys())

    return templates.TemplateResponse("college/players.html", _ctx(
        request, section="college", session_id=session_id,
        players=players, sort=sort, conference=conference,
        conferences=conferences,
        season_name=getattr(season, "name", "Season"),
    ))


@router.get("/college/{session_id}/analytics", response_class=HTMLResponse)
def college_analytics(request: Request, session_id: str, sort: str = "war", conference: str = ""):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    from engine.viperball_metrics import calculate_war, calculate_zbr, calculate_vpr

    # Aggregate player stats from completed games (same as players route)
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
                        "tag": p.get("tag", ""), "position": p.get("position", ""),
                        "archetype": p.get("archetype", ""),
                        "games_played": 0, "touches": 0, "yards": 0,
                        "rushing_yards": 0, "lateral_yards": 0, "tds": 0,
                        "fumbles": 0, "laterals_thrown": 0, "lateral_assists": 0,
                        "kick_return_yards": 0, "punt_return_yards": 0,
                        "kick_pass_yards": 0,
                        "wpa": 0.0, "plays_involved": 0,
                    }
                agg = player_agg[key]
                agg["games_played"] += 1
                if not agg["tag"]:
                    agg["tag"] = p.get("tag", "")
                if not agg["position"]:
                    agg["position"] = p.get("position", "")
                if not agg["archetype"] or agg["archetype"] == "—":
                    agg["archetype"] = p.get("archetype", "")
                for stat in [
                    "touches", "yards", "rushing_yards", "lateral_yards",
                    "tds", "fumbles", "laterals_thrown", "lateral_assists",
                    "kick_return_yards", "punt_return_yards", "kick_pass_yards",
                    "plays_involved",
                ]:
                    agg[stat] += p.get(stat, 0)
                agg["wpa"] += p.get("wpa", 0.0)

    players = list(player_agg.values())
    for r in players:
        r["yards_per_touch"] = round(r["yards"] / max(1, r["touches"]), 1)
        r["all_purpose_yards"] = r["rushing_yards"] + r["kick_return_yards"] + r["punt_return_yards"] + r["kick_pass_yards"]
        r["wpa"] = round(r["wpa"], 2)
        r["wpa_per_play"] = round(r["wpa"] / max(1, r["plays_involved"]), 2)
        r["war"] = calculate_war(r, r.get("position", ""))
        r["zbr"] = calculate_zbr(r)
        r["vpr"] = calculate_vpr(r)

    # Filter to players with meaningful activity
    players = [p for p in players if p["touches"] >= 5 or p["plays_involved"] >= 10]

    valid_sorts = {
        "war": "war", "zbr": "zbr", "vpr": "vpr",
        "wpa": "wpa", "wpa_per_play": "wpa_per_play",
        "yards": "yards", "ypc": "yards_per_touch", "tds": "tds",
    }
    sort_key = valid_sorts.get(sort, "war")
    players.sort(key=lambda x: x.get(sort_key, 0), reverse=True)

    conferences = sorted(season.conferences.keys())

    return templates.TemplateResponse("college/analytics.html", _ctx(
        request, section="college", session_id=session_id,
        players=players, sort=sort, conference=conference,
        conferences=conferences,
        season_name=getattr(season, "name", "Season"),
    ))


@router.get("/college/{session_id}/team-stats", response_class=HTMLResponse)
def college_team_stats(request: Request, session_id: str, sort: str = "total_yards", conference: str = ""):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    # Aggregate team stats from completed games (including postseason)
    team_agg = {}
    for game in _all_college_games(season):
        if not game.completed or not getattr(game, "full_result", None):
            continue
        fr = game.full_result
        stats = fr.get("stats", {})
        for side, t_name in [("home", game.home_team), ("away", game.away_team)]:
            conf = season.team_conferences.get(t_name, "")
            if conference and conf != conference:
                continue
            s = stats.get(side)
            if not s:
                continue
            if t_name not in team_agg:
                team_agg[t_name] = {
                    "team": t_name, "conference": conf, "games": 0,
                    "total_yards": 0, "total_plays": 0, "touchdowns": 0,
                    "rushing_yards": 0, "rushing_carries": 0, "rushing_tds": 0,
                    "kp_yards": 0, "kp_att": 0, "kp_comp": 0, "kp_tds": 0, "kp_ints": 0,
                    "lateral_chains": 0, "lateral_yards": 0, "successful_laterals": 0,
                    "dk_made": 0, "dk_att": 0, "pk_made": 0, "pk_att": 0,
                    "fumbles": 0, "tod": 0, "penalties": 0, "penalty_yards": 0,
                    "delta_yards": 0, "bonus_possessions": 0, "bonus_scores": 0,
                    "bonus_yards": 0, "delta_drives": 0, "delta_scores": 0,
                    "epa": 0, "viper_eff_sum": 0, "team_rating_sum": 0,
                    "viper_eff_n": 0, "team_rating_n": 0,
                    "down_4_att": 0, "down_4_conv": 0,
                    "down_5_att": 0, "down_5_conv": 0,
                    "down_6_att": 0, "down_6_conv": 0,
                }
            a = team_agg[t_name]
            a["games"] += 1
            a["total_yards"] += s.get("total_yards", 0)
            a["total_plays"] += s.get("total_plays", 0)
            a["touchdowns"] += s.get("touchdowns", 0)
            a["rushing_yards"] += s.get("rushing_yards", 0)
            a["rushing_carries"] += s.get("rushing_carries", 0)
            a["rushing_tds"] += s.get("rushing_touchdowns", 0)
            a["kp_yards"] += s.get("kick_pass_yards", 0)
            a["kp_att"] += s.get("kick_passes_attempted", 0)
            a["kp_comp"] += s.get("kick_passes_completed", 0)
            a["kp_tds"] += s.get("kick_pass_tds", 0)
            a["kp_ints"] += s.get("kick_pass_interceptions", 0)
            a["lateral_chains"] += s.get("lateral_chains", 0)
            a["lateral_yards"] += s.get("lateral_yards", 0)
            a["successful_laterals"] += s.get("successful_laterals", 0)
            a["dk_made"] += s.get("drop_kicks_made", 0)
            a["dk_att"] += s.get("drop_kicks_attempted", 0)
            a["pk_made"] += s.get("place_kicks_made", 0)
            a["pk_att"] += s.get("place_kicks_attempted", 0)
            a["fumbles"] += s.get("fumbles_lost", 0)
            a["tod"] += s.get("turnovers_on_downs", 0)
            a["penalties"] += s.get("penalties", 0)
            a["penalty_yards"] += s.get("penalty_yards", 0)
            a["delta_yards"] += s.get("delta_yards", 0)
            a["delta_drives"] += s.get("delta_drives", 0)
            a["delta_scores"] += s.get("delta_scores", 0)
            a["bonus_possessions"] += s.get("bonus_possessions", 0)
            a["bonus_scores"] += s.get("bonus_possession_scores", 0)
            a["bonus_yards"] += s.get("bonus_possession_yards", 0)
            # EPA: handle dict or number
            epa_val = s.get("epa", 0)
            if isinstance(epa_val, dict):
                a["epa"] += epa_val.get("total_epa", epa_val.get("wpa", 0))
            elif isinstance(epa_val, (int, float)):
                a["epa"] += epa_val
            ve = s.get("viper_efficiency")
            if ve is not None:
                a["viper_eff_sum"] += ve
                a["viper_eff_n"] += 1
            vm = s.get("viperball_metrics", {})
            tr = vm.get("team_rating") if vm else None
            if tr is not None:
                a["team_rating_sum"] += tr
                a["team_rating_n"] += 1
            # Down conversions
            dc = s.get("down_conversions", {})
            for d in [4, 5, 6]:
                dd = dc.get(d, dc.get(str(d), {}))
                a[f"down_{d}_att"] += dd.get("attempts", 0)
                a[f"down_{d}_conv"] += dd.get("converted", 0)

    teams = list(team_agg.values())
    for t in teams:
        n = max(1, t["games"])
        t["avg_yards"] = round(t["total_yards"] / n, 1)
        t["avg_rushing"] = round(t["rushing_yards"] / n, 1)
        t["yards_per_play"] = round(t["total_yards"] / max(1, t["total_plays"]), 2)
        t["yards_per_carry"] = round(t["rushing_yards"] / max(1, t["rushing_carries"]), 1)
        t["kp_comp_pct"] = round(t["kp_comp"] / max(1, t["kp_att"]) * 100, 1)
        t["lateral_pct"] = round(t["successful_laterals"] / max(1, t["lateral_chains"]) * 100, 1)
        t["avg_epa"] = round(t["epa"] / n, 2)
        t["avg_team_rating"] = round(t["team_rating_sum"] / max(1, t["team_rating_n"]), 1) if t["team_rating_n"] else 0
        t["avg_viper_eff"] = round(t["viper_eff_sum"] / max(1, t["viper_eff_n"]), 3) if t["viper_eff_n"] else 0
        # Down conversion rates
        for d in [4, 5, 6]:
            att = t[f"down_{d}_att"]
            conv = t[f"down_{d}_conv"]
            t[f"down_{d}_rate"] = round(conv / max(1, att) * 100, 1) if att > 0 else 0.0
        t["kill_rate"] = round(t["delta_scores"] / max(1, t["delta_drives"]) * 100, 1) if t["delta_drives"] > 0 else None
        # Get W-L from standings
        rec = season.standings.get(t["team"])
        if rec:
            t["wins"] = rec.wins
            t["losses"] = rec.losses
        else:
            t["wins"] = 0
            t["losses"] = 0

    valid_sorts = {
        "total_yards": "total_yards", "avg_yards": "avg_yards",
        "touchdowns": "touchdowns", "rushing_yards": "rushing_yards",
        "kp_yards": "kp_yards", "lateral_yards": "lateral_yards",
        "epa": "epa", "avg_epa": "avg_epa",
        "avg_team_rating": "avg_team_rating", "avg_viper_eff": "avg_viper_eff",
        "delta_yards": "delta_yards", "fumbles": "fumbles",
        "penalties": "penalties", "yards_per_play": "yards_per_play",
        "bonus_possessions": "bonus_possessions",
    }
    sort_key = valid_sorts.get(sort, "total_yards")
    teams.sort(key=lambda x: x.get(sort_key, 0), reverse=True)

    conferences = sorted(season.conferences.keys())

    return templates.TemplateResponse("college/team_stats.html", _ctx(
        request, section="college", session_id=session_id,
        teams=teams, sort=sort, conference=conference,
        conferences=conferences,
        season_name=getattr(season, "name", "Season"),
    ))


@router.get("/college/{session_id}/playoffs", response_class=HTMLResponse)
def college_playoffs(request: Request, session_id: str):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    # Round labels by week number
    round_labels = {
        995: "Play-In Round",
        996: "Round of 32",
        997: "Round of 16",
        998: "Quarterfinals",
        999: "Semifinals",
        1000: "National Championship",
    }

    # Build bracket rounds
    bracket = season.playoff_bracket or []
    rounds = {}
    week_counters = {}
    for g in bracket:
        sg = api["serialize_game"](g, include_full_result=False)
        wk = sg.get("week", 0)
        idx = week_counters.get(wk, 0)
        sg["week_game_idx"] = idx
        week_counters[wk] = idx + 1
        rounds.setdefault(wk, []).append(sg)

    # Determine total teams for label resolution
    total_teams = 0
    if bracket:
        first_wk = min(g.week for g in bracket)
        first_round = [g for g in bracket if g.week == first_wk]
        total_teams = len(first_round) * 2
        # Check for byes (teams that appear later but not in first round)
        all_teams = set()
        for g in bracket:
            all_teams.add(g.home_team)
            all_teams.add(g.away_team)
        total_teams = max(total_teams, len(all_teams))

    # Use stored playoff seeds if available, otherwise derive from first-round order
    seed_map = getattr(season, 'playoff_seeds', None) or {}
    if not seed_map and bracket:
        first_wk = min(g.week for g in bracket)
        seed_counter = 1
        for g in sorted(bracket, key=lambda x: x.week):
            if g.week == first_wk:
                if g.home_team not in seed_map:
                    seed_map[g.home_team] = seed_counter
                    seed_counter += 1
                if g.away_team not in seed_map:
                    seed_map[g.away_team] = seed_counter
                    seed_counter += 1
        for g in sorted(bracket, key=lambda x: x.week):
            for t in [g.home_team, g.away_team]:
                if t not in seed_map:
                    seed_map[t] = seed_counter
                    seed_counter += 1

    sorted_rounds = sorted(rounds.items())

    # Bowl games
    bowls = []
    for bg in (season.bowl_games or []):
        sg = api["serialize_game"](bg.game, include_full_result=False)
        bowls.append({
            "name": bg.name,
            "tier": bg.tier,
            "tier_label": {1: "Premier", 2: "Major", 3: "Standard"}.get(bg.tier, ""),
            "game": sg,
        })

    return templates.TemplateResponse("college/playoffs.html", _ctx(
        request, section="college", session_id=session_id,
        rounds=sorted_rounds, round_labels=round_labels,
        seed_map=seed_map, champion=season.champion,
        bowls=bowls, total_teams=total_teams,
        has_playoff=bool(bracket),
        has_bowls=bool(season.bowl_games),
        phase=sess.get("phase", ""),
        season_name=getattr(season, "name", "Season"),
    ))


@router.get("/college/{session_id}/bracketology", response_class=HTMLResponse)
def college_bracketology(request: Request, session_id: str):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    playoff_size = sess.get("config", {}).get("playoff_size", 8)
    bracketology = season.get_bracketology(playoff_size)

    return templates.TemplateResponse("college/bracketology.html", _ctx(
        request, section="college", session_id=session_id,
        field=bracketology["field"],
        bracket=bracketology["bracket"],
        bubble_in=bracketology["bubble_in"],
        bubble_out=bracketology["bubble_out"],
        num_teams=bracketology["num_teams"],
        season_name=getattr(season, "name", "Season"),
        phase=sess.get("phase", ""),
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
    except Exception as exc:
        import traceback
        traceback.print_exc()
        awards = {}

    # Weekly awards (player/coach of the week)
    weekly_awards = getattr(season, 'weekly_awards', []) or []

    return templates.TemplateResponse("college/awards.html", _ctx(
        request, section="college", session_id=session_id,
        awards=awards,
        weekly_awards=weekly_awards,
        season_name=getattr(season, "name", "Season"),
    ))


# ── DRAFTYQUEENZ ─────────────────────────────────────────────────────────

@router.get("/college/{session_id}/draftyqueenz", response_class=HTMLResponse)
def college_draftyqueenz(request: Request, session_id: str):
    api = _get_api()
    sess = api["get_session"](session_id)

    dq_mgr = sess.get("dq_manager")
    if not dq_mgr:
        raise HTTPException(404, "DraftyQueenz not active in this session")

    summary = dq_mgr.season_summary()

    # Build pick history
    all_picks = []
    total_won = 0
    total_lost = 0
    for week_num in sorted(dq_mgr.weekly_contests.keys()):
        contest = dq_mgr.weekly_contests[week_num]
        for pick in contest.picks:
            d = pick.to_dict()
            d["week"] = week_num
            d["resolved"] = contest.resolved
            all_picks.append(d)
            if pick.result == "win":
                total_won += pick.payout
            elif pick.result == "loss":
                total_lost += pick.amount
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

    season = api["require_season"](sess)

    return templates.TemplateResponse("college/draftyqueenz.html", _ctx(
        request, section="college", session_id=session_id,
        summary=summary,
        picks=all_picks,
        total_won=total_won,
        total_lost=total_lost,
        net=total_won - total_lost,
        has_dq=True,
        season_name=getattr(season, "name", "Season"),
    ))


# ── DYNASTY DATA ─────────────────────────────────────────────────────────

@router.get("/college/{session_id}/data", response_class=HTMLResponse)
def college_data(request: Request, session_id: str):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)
    dynasty = sess.get("dynasty")
    if not dynasty:
        raise HTTPException(404, "No dynasty active in this session")

    return templates.TemplateResponse("college/data.html", _ctx(
        request, section="college", session_id=session_id,
        dynasty_name=dynasty.dynasty_name,
        year=dynasty.current_year,
        team_count=len(dynasty.team_histories),
        conf_count=len(dynasty.conferences),
        season_name=getattr(season, "name", "Season"),
    ))


@router.get("/college/{session_id}/data/download")
def college_data_download(request: Request, session_id: str):
    import json as _json
    from fastapi.responses import Response
    from engine.db import serialize_dynasty

    api = _get_api()
    sess = api["get_session"](session_id)
    dynasty = sess.get("dynasty")
    if not dynasty:
        raise HTTPException(404, "No dynasty active in this session")

    data = serialize_dynasty(dynasty)
    content = _json.dumps(data, indent=2)
    filename = f"{dynasty.dynasty_name.replace(' ', '_')}_Y{dynasty.current_year}.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/college/{session_id}/data/upload")
async def college_data_upload(request: Request, session_id: str):
    import json as _json
    from fastapi.responses import JSONResponse
    from engine.db import deserialize_dynasty

    api = _get_api()
    sess = api["get_session"](session_id)
    if not sess.get("dynasty"):
        raise HTTPException(404, "No dynasty active in this session")

    form = await request.form()
    file = form.get("file")
    if not file:
        raise HTTPException(400, "No file provided")

    try:
        contents = await file.read()
        data = _json.loads(contents)
        dynasty = deserialize_dynasty(data)
        sess["dynasty"] = dynasty
        return JSONResponse({"message": f"Dynasty '{dynasty.dynasty_name}' loaded (Year {dynasty.current_year})."})
    except Exception as e:
        raise HTTPException(400, f"Failed to load dynasty file: {e}")


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

    _normalize_box_score_stats(box)

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


@router.get("/pro/{league}/{session_id}/team-stats", response_class=HTMLResponse)
def pro_team_stats(request: Request, league: str, session_id: str, sort: str = "total_yards", division: str = ""):
    api = _get_api()
    key = f"{league.lower()}_{session_id}"
    season = api["pro_sessions"].get(key)
    if not season:
        raise HTTPException(404, "Pro league session not found")

    # Aggregate team stats from all completed game results
    team_agg = {}
    for week_num, week_games in season.results.items():
        for matchup_key, game in week_games.items():
            result = game.get("result", {})
            stats = result.get("stats", {})
            for side in ("home", "away"):
                t_key = game.get(f"{side}_key", "")
                t_name = game.get(f"{side}_name", t_key)
                s = stats.get(side)
                if not s or not t_key:
                    continue
                div = season._get_division_for_key(t_key)
                if division and div != division:
                    continue
                if t_key not in team_agg:
                    team_agg[t_key] = {
                        "team_key": t_key, "team": t_name, "division": div, "games": 0,
                        "total_yards": 0, "total_plays": 0, "touchdowns": 0,
                        "rushing_yards": 0, "rushing_carries": 0, "rushing_tds": 0,
                        "kp_yards": 0, "kp_att": 0, "kp_comp": 0, "kp_tds": 0, "kp_ints": 0,
                        "lateral_chains": 0, "lateral_yards": 0, "successful_laterals": 0,
                        "dk_made": 0, "dk_att": 0, "pk_made": 0, "pk_att": 0,
                        "fumbles": 0, "tod": 0, "penalties": 0, "penalty_yards": 0,
                        "delta_yards": 0, "delta_drives": 0, "delta_scores": 0,
                        "bonus_possessions": 0, "bonus_scores": 0, "bonus_yards": 0,
                        "epa": 0, "viper_eff_sum": 0, "team_rating_sum": 0,
                        "viper_eff_n": 0, "team_rating_n": 0,
                        "down_4_att": 0, "down_4_conv": 0,
                        "down_5_att": 0, "down_5_conv": 0,
                        "down_6_att": 0, "down_6_conv": 0,
                    }
                a = team_agg[t_key]
                a["games"] += 1
                a["total_yards"] += s.get("total_yards", 0)
                a["total_plays"] += s.get("total_plays", 0)
                a["touchdowns"] += s.get("touchdowns", 0)
                a["rushing_yards"] += s.get("rushing_yards", 0)
                a["rushing_carries"] += s.get("rushing_carries", 0)
                a["rushing_tds"] += s.get("rushing_touchdowns", 0)
                a["kp_yards"] += s.get("kick_pass_yards", 0)
                a["kp_att"] += s.get("kick_passes_attempted", 0)
                a["kp_comp"] += s.get("kick_passes_completed", 0)
                a["kp_tds"] += s.get("kick_pass_tds", 0)
                a["kp_ints"] += s.get("kick_pass_interceptions", 0)
                a["lateral_chains"] += s.get("lateral_chains", 0)
                a["lateral_yards"] += s.get("lateral_yards", 0)
                a["successful_laterals"] += s.get("successful_laterals", 0)
                a["dk_made"] += s.get("drop_kicks_made", 0)
                a["dk_att"] += s.get("drop_kicks_attempted", 0)
                a["pk_made"] += s.get("place_kicks_made", 0)
                a["pk_att"] += s.get("place_kicks_attempted", 0)
                a["fumbles"] += s.get("fumbles_lost", 0)
                a["tod"] += s.get("turnovers_on_downs", 0)
                a["penalties"] += s.get("penalties", 0)
                a["penalty_yards"] += s.get("penalty_yards", 0)
                a["delta_yards"] += s.get("delta_yards", 0)
                a["delta_drives"] += s.get("delta_drives", 0)
                a["delta_scores"] += s.get("delta_scores", 0)
                a["bonus_possessions"] += s.get("bonus_possessions", 0)
                a["bonus_scores"] += s.get("bonus_possession_scores", 0)
                a["bonus_yards"] += s.get("bonus_possession_yards", 0)
                epa_val = s.get("epa", 0)
                if isinstance(epa_val, dict):
                    a["epa"] += epa_val.get("total_epa", epa_val.get("wpa", 0))
                elif isinstance(epa_val, (int, float)):
                    a["epa"] += epa_val
                ve = s.get("viper_efficiency")
                if ve is not None:
                    a["viper_eff_sum"] += ve
                    a["viper_eff_n"] += 1
                vm = s.get("viperball_metrics", {})
                tr = vm.get("team_rating") if vm else None
                if tr is not None:
                    a["team_rating_sum"] += tr
                    a["team_rating_n"] += 1
                dc = s.get("down_conversions", {})
                for d in [4, 5, 6]:
                    dd = dc.get(d, dc.get(str(d), {}))
                    a[f"down_{d}_att"] += dd.get("attempts", 0)
                    a[f"down_{d}_conv"] += dd.get("converted", 0)

    teams = list(team_agg.values())
    for t in teams:
        n = max(1, t["games"])
        t["avg_yards"] = round(t["total_yards"] / n, 1)
        t["yards_per_play"] = round(t["total_yards"] / max(1, t["total_plays"]), 2)
        t["lateral_pct"] = round(t["successful_laterals"] / max(1, t["lateral_chains"]) * 100, 1)
        t["avg_epa"] = round(t["epa"] / n, 2)
        t["avg_team_rating"] = round(t["team_rating_sum"] / max(1, t["team_rating_n"]), 1) if t["team_rating_n"] else 0
        t["avg_viper_eff"] = round(t["viper_eff_sum"] / max(1, t["viper_eff_n"]), 3) if t["viper_eff_n"] else 0
        t["kp_comp_pct"] = round(t["kp_comp"] / max(1, t["kp_att"]) * 100, 1)
        for d in [4, 5, 6]:
            att = t[f"down_{d}_att"]
            conv = t[f"down_{d}_conv"]
            t[f"down_{d}_rate"] = round(conv / max(1, att) * 100, 1) if att > 0 else 0.0
        t["kill_rate"] = round(t["delta_scores"] / max(1, t["delta_drives"]) * 100, 1) if t["delta_drives"] > 0 else None
        rec = season.standings.get(t["team_key"])
        if rec:
            t["wins"] = rec.wins
            t["losses"] = rec.losses
        else:
            t["wins"] = 0
            t["losses"] = 0

    valid_sorts = {
        "total_yards": "total_yards", "avg_yards": "avg_yards",
        "touchdowns": "touchdowns", "rushing_yards": "rushing_yards",
        "kp_yards": "kp_yards", "lateral_yards": "lateral_yards",
        "epa": "epa", "avg_epa": "avg_epa",
        "avg_team_rating": "avg_team_rating", "avg_viper_eff": "avg_viper_eff",
        "delta_yards": "delta_yards", "fumbles": "fumbles",
        "penalties": "penalties", "yards_per_play": "yards_per_play",
        "bonus_possessions": "bonus_possessions",
    }
    sort_key = valid_sorts.get(sort, "total_yards")
    teams.sort(key=lambda x: x.get(sort_key, 0), reverse=True)

    divisions = sorted(season.config.divisions.keys()) if season.config.divisions else []

    return templates.TemplateResponse("pro/team_stats.html", _ctx(
        request, section="pro", league=league, session_id=session_id,
        teams=teams, sort=sort, division=division,
        divisions=divisions,
        league_name=season.config.league_name,
    ))


@router.get("/pro/{league}/{session_id}/playoffs", response_class=HTMLResponse)
def pro_playoffs(request: Request, league: str, session_id: str):
    api = _get_api()
    key = f"{league.lower()}_{session_id}"
    season = api["pro_sessions"].get(key)
    if not season:
        raise HTTPException(404, "Pro league session not found")

    bracket = season.get_playoff_bracket() if season.phase in ("playoffs", "completed") else {}

    return templates.TemplateResponse("pro/playoffs.html", _ctx(
        request, section="pro", league=league, session_id=session_id,
        bracket=bracket,
        champion=season.champion,
        phase=season.phase,
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


# ── WVL (Women's Viperball League) ──────────────────────────────────────

def _wvl_tier_label(tier_num):
    """Tier number to display name."""
    labels = {1: "Galactic Premiership", 2: "Galactic League 1", 3: "Galactic League 2", 4: "Galactic League 3"}
    return labels.get(tier_num, f"Tier {tier_num}")


def _wvl_zone_class(zone):
    """CSS class for a pro/rel zone."""
    return {"promotion": "stat-good", "relegation": "stat-bad", "playoff": "stat-elite"}.get(zone, "")


@router.get("/wvl/", response_class=HTMLResponse)
def wvl_index(request: Request):
    sessions = _find_all_wvl_sessions()
    return templates.TemplateResponse("wvl/index.html", _ctx(
        request, section="wvl", sessions=sessions,
    ))


@router.get("/wvl/{session_id}/", response_class=HTMLResponse)
def wvl_season(request: Request, session_id: str):
    data = _get_wvl_session(session_id)
    season = data["season"]

    # Gather standings for all tiers with pro/rel zone annotations
    all_standings = season.get_all_standings()

    # Get tier configs for display
    try:
        from engine.wvl_config import TIER_BY_NUMBER, CLUBS_BY_KEY, RIVALRIES
    except ImportError:
        TIER_BY_NUMBER = {}
        CLUBS_BY_KEY = {}
        RIVALRIES = []

    tier_data = []
    for tier_num in sorted(season.tier_seasons.keys()):
        tier_standings = all_standings.get(tier_num, {})
        ranked = tier_standings.get("ranked", [])
        # Enrich with club info
        for team in ranked:
            key = team.get("team_key", "")
            club = CLUBS_BY_KEY.get(key)
            if club:
                team["country"] = club.country
                team["narrative_tag"] = club.narrative_tag
            team["is_owner_club"] = key == data.get("club_key", "")

        tier_season = season.tier_seasons.get(tier_num)
        champion = tier_season.champion if tier_season else None

        tier_data.append({
            "tier_num": tier_num,
            "tier_name": _wvl_tier_label(tier_num),
            "ranked": ranked,
            "champion": champion,
            "divisions": tier_standings.get("divisions", {}),
        })

    return templates.TemplateResponse("wvl/season.html", _ctx(
        request, section="wvl", session_id=session_id,
        tier_data=tier_data,
        dynasty_name=data.get("dynasty_name", "WVL"),
        year=data.get("year", "?"),
        club_key=data.get("club_key", ""),
        zone_class=_wvl_zone_class,
    ))


@router.get("/wvl/{session_id}/schedule", response_class=HTMLResponse)
def wvl_schedule(request: Request, session_id: str, tier: int = 1):
    data = _get_wvl_session(session_id)
    season = data["season"]
    tier_season = season.tier_seasons.get(tier)
    if not tier_season:
        raise HTTPException(404, f"Tier {tier} not found")

    schedule = tier_season.get_schedule()
    tier_list = sorted(season.tier_seasons.keys())

    return templates.TemplateResponse("wvl/schedule.html", _ctx(
        request, section="wvl", session_id=session_id,
        schedule=schedule, selected_tier=tier,
        tier_name=_wvl_tier_label(tier),
        tier_list=tier_list,
        tier_label=_wvl_tier_label,
        dynasty_name=data.get("dynasty_name", "WVL"),
        year=data.get("year", "?"),
    ))


def _compute_wvl_playoff_achievements(bracket_data):
    """Given get_playoff_bracket() output, compute per-team achievement labels."""
    rounds = bracket_data.get("rounds", [])
    champion = bracket_data.get("champion")
    total_rounds = len(rounds)

    team_depth = {}  # team_key → (max_round_idx, team_name)
    for round_idx, rnd in enumerate(rounds):
        for m in rnd.get("matchups", []):
            home = m.get("home", {})
            away = m.get("away")
            if home.get("team_key"):
                k = home["team_key"]
                if k not in team_depth or round_idx > team_depth[k][0]:
                    team_depth[k] = (round_idx, home.get("team_name", k))
            if away and away.get("team_key"):
                k = away["team_key"]
                if k not in team_depth or round_idx > team_depth[k][0]:
                    team_depth[k] = (round_idx, away.get("team_name", k))
        for bt in rnd.get("bye_teams", []):
            k = bt.get("team_key")
            if k and (k not in team_depth or round_idx > team_depth[k][0]):
                team_depth[k] = (round_idx, bt.get("team_name", k))

    results = {}
    for team_key, (depth, name) in team_depth.items():
        if team_key == champion:
            label, css = "Champion", "achievement-champion"
        elif depth == total_rounds - 1 and total_rounds > 0:
            label, css = "Finalist", "achievement-finalist"
        elif total_rounds <= 2:
            label, css = "Playoff Qualifier", "achievement-qualifier"
        elif depth == total_rounds - 2:
            label, css = "Semifinalist", "achievement-semifinalist"
        elif depth == total_rounds - 3:
            label, css = "Quarterfinalist", "achievement-quarterfinalist"
        else:
            label, css = "Playoff Qualifier", "achievement-qualifier"
        results[team_key] = {"label": label, "team_name": name, "round_depth": depth, "css_class": css}
    return results


@router.get("/wvl/{session_id}/playoffs", response_class=HTMLResponse)
def wvl_playoffs(request: Request, session_id: str):
    data = _get_wvl_session(session_id)
    season = data["season"]

    tier_brackets = []
    for tier_num in sorted(season.tier_seasons.keys()):
        ts = season.tier_seasons[tier_num]
        bracket = ts.get_playoff_bracket()
        achievements = _compute_wvl_playoff_achievements(bracket)
        tier_brackets.append({
            "tier_num": tier_num,
            "tier_name": _wvl_tier_label(tier_num),
            "bracket": bracket,
            "achievements": achievements,
        })

    return templates.TemplateResponse("wvl/playoffs.html", _ctx(
        request, section="wvl", session_id=session_id,
        tier_brackets=tier_brackets,
        dynasty_name=data.get("dynasty_name", "WVL"),
        year=data.get("year", "?"),
        club_key=data.get("club_key", ""),
    ))


@router.get("/wvl/{session_id}/game/{tier}/{week}/{matchup}", response_class=HTMLResponse)
def wvl_game(request: Request, session_id: str, tier: int, week: int, matchup: str):
    data = _get_wvl_session(session_id)
    season = data["season"]
    tier_season = season.tier_seasons.get(tier)
    if not tier_season:
        raise HTTPException(404, f"Tier {tier} not found")

    box = tier_season.get_box_score(week, matchup)
    if not box:
        raise HTTPException(404, "Game not found")

    _normalize_box_score_stats(box)

    # Check if it's a rivalry match
    try:
        from engine.wvl_config import is_rivalry_match
        home_key = box.get("home_key", "")
        away_key = box.get("away_key", "")
        rivalry = is_rivalry_match(home_key, away_key)
    except ImportError:
        rivalry = None

    return templates.TemplateResponse("wvl/game.html", _ctx(
        request, section="wvl", session_id=session_id,
        box=box, week=week, matchup=matchup, tier=tier,
        tier_name=_wvl_tier_label(tier),
        rivalry=rivalry,
        dynasty_name=data.get("dynasty_name", "WVL"),
        year=data.get("year", "?"),
    ))


@router.get("/wvl/{session_id}/team/{team_key}", response_class=HTMLResponse)
def wvl_team(request: Request, session_id: str, team_key: str):
    data = _get_wvl_session(session_id)
    season = data["season"]

    # Find which tier this team is in
    team_tier = season.tier_assignments.get(team_key)
    if team_tier is None:
        raise HTTPException(404, f"Team '{team_key}' not found")

    tier_season = season.tier_seasons.get(team_tier)
    if not tier_season:
        raise HTTPException(404, f"Tier {team_tier} not found")

    detail = tier_season.get_team_detail(team_key)
    if not detail:
        raise HTTPException(404, f"Team '{team_key}' not found")

    # Enrich with WVL club info
    try:
        from engine.wvl_config import CLUBS_BY_KEY
        club = CLUBS_BY_KEY.get(team_key)
        if club:
            detail["country"] = club.country
            detail["city"] = club.city
            detail["narrative_tag"] = club.narrative_tag
            detail["prestige"] = club.prestige
    except ImportError:
        pass

    is_owner_club = team_key == data.get("club_key", "")

    # Build financial snapshot for the owner's club page
    financial = None
    if is_owner_club:
        dynasty = data.get("dynasty")
        if dynasty and hasattr(dynasty, "owner"):
            owner = dynasty.owner
            investment = getattr(dynasty, "investment", None)
            current_year = data.get("year", "?")
            fin_hist = getattr(dynasty, "financial_history", {})
            latest_fin = fin_hist.get(current_year) or (
                fin_hist.get(max(fin_hist.keys())) if fin_hist else None
            )
            financial = {
                "bankroll": getattr(owner, "bankroll", None),
                "archetype": getattr(owner, "archetype", ""),
                "investment": {
                    "training": getattr(investment, "training", 0) if investment else 0,
                    "coaching": getattr(investment, "coaching", 0) if investment else 0,
                    "stadium": getattr(investment, "stadium", 0) if investment else 0,
                    "youth": getattr(investment, "youth", 0) if investment else 0,
                    "science": getattr(investment, "science", 0) if investment else 0,
                    "marketing": getattr(investment, "marketing", 0) if investment else 0,
                } if investment else {},
                "season_financials": latest_fin,
            }

    # Compute playoff achievement for this team
    team_achievement = None
    bracket = tier_season.get_playoff_bracket()
    if bracket.get("rounds"):
        achievements = _compute_wvl_playoff_achievements(bracket)
        team_achievement = achievements.get(team_key)

    return templates.TemplateResponse("wvl/team.html", _ctx(
        request, section="wvl", session_id=session_id,
        team=detail, team_key=team_key, tier=team_tier,
        tier_name=_wvl_tier_label(team_tier),
        is_owner_club=is_owner_club,
        dynasty_name=data.get("dynasty_name", "WVL"),
        year=data.get("year", "?"),
        financial=financial,
        team_achievement=team_achievement,
    ))


@router.get("/wvl/{session_id}/stats", response_class=HTMLResponse)
def wvl_stats(request: Request, session_id: str, tier: int = 0, category: str = "all"):
    data = _get_wvl_session(session_id)
    season = data["season"]

    # If tier == 0, aggregate across all tiers
    all_leaders = {}
    tier_list = sorted(season.tier_seasons.keys())

    if tier > 0 and tier in season.tier_seasons:
        leaders = season.tier_seasons[tier].get_stat_leaders(category)
        all_leaders[tier] = leaders
    else:
        for t_num in tier_list:
            leaders = season.tier_seasons[t_num].get_stat_leaders(category)
            all_leaders[t_num] = leaders

    return templates.TemplateResponse("wvl/stats.html", _ctx(
        request, section="wvl", session_id=session_id,
        all_leaders=all_leaders, category=category,
        selected_tier=tier, tier_list=tier_list,
        tier_label=_wvl_tier_label,
        dynasty_name=data.get("dynasty_name", "WVL"),
        year=data.get("year", "?"),
    ))


@router.get("/wvl/{session_id}/economy", response_class=HTMLResponse)
def wvl_economy(request: Request, session_id: str):
    data = _get_wvl_session(session_id)
    dynasty = data.get("dynasty")
    if not dynasty:
        raise HTTPException(503, "Dynasty not loaded in this session")

    # Build team economy table
    from engine.wvl_owner import _BROADCAST_REVENUE, _TIER_STARTING_FANBASE, AI_OWNER_PROFILES
    from engine.wvl_config import ALL_CLUBS, CLUBS_BY_KEY

    eco_rows = []
    for club in sorted(ALL_CLUBS, key=lambda c: (dynasty.tier_assignments.get(c.key, 5), -c.prestige)):
        tier = dynasty.tier_assignments.get(club.key, 4)
        is_owner = club.key == dynasty.owner.club_key
        if is_owner:
            owner_label = f"Human ({dynasty.owner.archetype.replace('_', ' ').title()})"
            fanbase = int(dynasty.fanbase)
            bankroll = round(dynasty.owner.bankroll, 1)
            if dynasty.financial_history:
                last_fin = dynasty.financial_history[max(dynasty.financial_history.keys())]
                revenue = last_fin.get("total_revenue", 0)
                expenses = last_fin.get("total_expenses", 0)
                payroll = last_fin.get("roster_cost", 0)
            else:
                bcast = _BROADCAST_REVENUE.get(tier, 1.0)
                revenue = bcast
                expenses = 5.0
                payroll = 0
        else:
            ai_key = dynasty.ai_team_owners.get(club.key, "balanced")
            owner_label = f"AI ({ai_key.replace('_', ' ').title()})"
            base = _TIER_STARTING_FANBASE.get(tier, 5_000)
            fanbase = int(base * (0.5 + club.prestige / 100))
            ai_p = AI_OWNER_PROFILES.get(ai_key, AI_OWNER_PROFILES["balanced"])
            bcast = _BROADCAST_REVENUE.get(tier, 1.0)
            est_ticket = round(fanbase * 30 * 12 / 1_000_000, 2)
            revenue = round(bcast + est_ticket, 1)
            payroll = round(revenue * ai_p["spending_ratio"], 1)
            expenses = round(payroll + 5.0, 1)
            bankroll = round(club.prestige * 0.5, 1)
        eco_rows.append({
            "club_key": club.key,
            "team": club.name,
            "tier": tier,
            "owner": owner_label,
            "is_owner": is_owner,
            "payroll": payroll,
            "revenue": revenue,
            "expenses": expenses,
            "fanbase": fanbase,
            "bankroll": bankroll,
        })

    # Bourse exchange rate history
    rate_history = []
    bourse_hist = getattr(dynasty, "bourse_rate_history", {})
    for yr in sorted(bourse_hist.keys()):
        rec = bourse_hist[yr]
        rate_history.append({
            "year": yr,
            "rate": rec.get("rate", 1.0),
            "delta_pct": rec.get("delta_pct", 0),
            "label": rec.get("label", ""),
        })

    current_rate = getattr(dynasty, "bourse_rate", 1.0)

    # Build fanbase trend history from financial records
    fanbase_history = []
    fin_hist = getattr(dynasty, "financial_history", {})
    for yr in sorted(fin_hist.keys()):
        fb = fin_hist[yr].get("fanbase_after", fin_hist[yr].get("fanbase_end", 0))
        if fb:
            fanbase_history.append({"year": yr, "fanbase": int(fb)})

    # Build year-by-year financial history for charts
    financial_years = []
    for yr in sorted(fin_hist.keys()):
        rec = fin_hist[yr]
        financial_years.append({
            "year": yr,
            "total_revenue": round(rec.get("total_revenue", 0), 2),
            "ticket_revenue": round(rec.get("ticket_revenue", 0), 2),
            "broadcast_revenue": round(rec.get("broadcast_revenue", 0), 2),
            "sponsorship_revenue": round(rec.get("sponsorship_revenue", 0), 2),
            "merchandise_revenue": round(rec.get("merchandise_revenue", 0), 2),
            "prize_money": round(rec.get("prize_money", 0), 2),
            "total_expenses": round(rec.get("total_expenses", 0), 2),
            "roster_cost": round(rec.get("roster_cost", 0), 2),
            "president_cost": round(rec.get("president_cost", 0), 2),
            "base_ops_cost": round(rec.get("base_ops_cost", 0), 2),
            "investment_spend": round(rec.get("investment_spend", 0), 2),
            "loan_payments": round(rec.get("loan_payments", 0), 2),
            "net_income": round(rec.get("net_income", 0), 2),
            "bankroll_end": round(rec.get("bankroll_end", 0), 2),
            "attendance_avg": rec.get("attendance_avg", 0),
        })

    # Active loans
    loans = getattr(dynasty, "loans", [])

    # Infrastructure levels
    infrastructure = getattr(dynasty, "infrastructure", {})

    return templates.TemplateResponse("wvl/economy.html", _ctx(
        request, section="wvl", session_id=session_id,
        dynasty_name=data.get("dynasty_name", "WVL"),
        year=data.get("year", "?"),
        eco_rows=eco_rows,
        rate_history=rate_history,
        current_rate=current_rate,
        fanbase_history=fanbase_history,
        financial_years=financial_years,
        loans=loans,
        infrastructure=infrastructure,
    ))


@router.get("/wvl/{session_id}/coaching", response_class=HTMLResponse)
def wvl_coaching(request: Request, session_id: str):
    data = _get_wvl_session(session_id)
    dynasty = data.get("dynasty")
    season = data["season"]
    if not dynasty:
        raise HTTPException(503, "Dynasty not loaded in this session")

    # Load coaching staffs from all WVL tier team JSON files
    import json as _json
    from engine.coaching import CoachCard, CLASSIFICATION_LABELS
    from engine.wvl_config import ALL_WVL_TIERS, CLUBS_BY_KEY
    from pathlib import Path

    all_staffs = []
    data_dir = Path(__file__).parent.parent / "data"

    for tier_cfg in ALL_WVL_TIERS:
        tier_dir = data_dir.parent / tier_cfg.teams_dir
        if not tier_dir.exists():
            continue
        for team_file in sorted(tier_dir.glob("*.json")):
            try:
                with open(team_file) as f:
                    raw = _json.load(f)
                team_key = team_file.stem
                team_name = raw.get("team_info", {}).get("school", team_key)
                cs = raw.get("coaching_staff")
                if not cs:
                    continue
                tier = dynasty.tier_assignments.get(team_key, 0)
                is_owner = team_key == dynasty.owner.club_key
                staff_entries = []
                for role in ["head_coach", "oc", "dc", "stc"]:
                    card_data = cs.get(role)
                    if not card_data or not isinstance(card_data, dict):
                        continue
                    card = CoachCard.from_dict(card_data)
                    staff_entries.append({
                        "role": role,
                        "role_label": {"head_coach": "HC", "oc": "OC", "dc": "DC", "stc": "STC"}.get(role, role),
                        "name": card.full_name,
                        "overall": round(card.visible_score, 1),
                        "star_rating": card.star_rating,
                        "classification": card.classification,
                        "classification_label": card.classification_label,
                        "composure_label": card.composure_label,
                        "leadership": card.leadership,
                        "composure": card.composure,
                        "rotations": card.rotations,
                        "development": card.development,
                        "recruiting": card.recruiting,
                        "career_wins": card.career_wins,
                        "career_losses": card.career_losses,
                        "win_pct": round(card.win_percentage, 3),
                        "championships": card.championships,
                        "contract_salary": card.contract_salary,
                        "contract_years": card.contract_years_remaining,
                        "philosophy": card.philosophy,
                        "coaching_style": card.coaching_style,
                    })
                if staff_entries:
                    all_staffs.append({
                        "team_key": team_key,
                        "team_name": team_name,
                        "tier": tier,
                        "is_owner": is_owner,
                        "staff": staff_entries,
                    })
            except Exception:
                continue

    all_staffs.sort(key=lambda s: (s["tier"], s["team_name"]))

    return templates.TemplateResponse("wvl/coaching.html", _ctx(
        request, section="wvl", session_id=session_id,
        dynasty_name=data.get("dynasty_name", "WVL"),
        year=data.get("year", "?"),
        all_staffs=all_staffs,
    ))


@router.get("/wvl/{session_id}/player/{team_key}/{player_name}", response_class=HTMLResponse)
def wvl_player(request: Request, session_id: str, team_key: str, player_name: str):
    data = _get_wvl_session(session_id)
    season = data["season"]

    team_tier = season.tier_assignments.get(team_key)
    if team_tier is None:
        raise HTTPException(404, f"Team '{team_key}' not found")
    tier_season = season.tier_seasons.get(team_tier)
    if not tier_season:
        raise HTTPException(404, f"Tier {team_tier} not found")

    # Find the player on the team
    team = tier_season.teams.get(team_key)
    if not team:
        raise HTTPException(404, f"Team '{team_key}' not found in tier")

    player = None
    for p in getattr(team, "players", []):
        if p.name == player_name:
            player = p
            break
    if not player:
        raise HTTPException(404, f"Player '{player_name}' not found on {team_key}")

    # Build player card
    card = None
    try:
        from engine.player_card import player_to_card
        pc = player_to_card(player, team_key)
        card = pc.to_dict()
    except Exception:
        pass

    # Build season stats from completed games
    season_totals = {
        "games": 0, "touches": 0, "yards": 0, "rushing_yards": 0,
        "lateral_yards": 0, "tds": 0, "fumbles": 0, "laterals_thrown": 0,
        "kick_att": 0, "kick_made": 0, "pk_att": 0, "pk_made": 0,
        "dk_att": 0, "dk_made": 0, "tackles": 0, "tfl": 0, "sacks": 0,
        "hurries": 0, "kick_pass_yards": 0, "kick_pass_tds": 0,
        "kick_passes_thrown": 0, "kick_passes_completed": 0,
        "kick_return_yards": 0, "punt_return_yards": 0,
        # Rushing detail
        "rush_carries": 0, "rushing_tds": 0,
        # Lateral chain
        "lateral_receptions": 0, "lateral_assists": 0, "lateral_tds": 0,
        # Kick pass detail
        "kick_pass_interceptions_thrown": 0, "kick_pass_receptions": 0,
        "kick_pass_ints": 0,
        # Special teams
        "kick_returns": 0, "kick_return_tds": 0,
        "punt_returns": 0, "punt_return_tds": 0,
        "muffs": 0, "st_tackles": 0,
        # Keeper
        "keeper_tackles": 0, "keeper_bells": 0,
        "kick_deflections": 0, "coverage_snaps": 0,
        "keeper_return_yards": 0,
        # Line play
        "blocks": 0, "pancakes": 0,
        # Impact
        "wpa": 0.0, "plays_involved": 0,
    }
    game_log = []
    for week_num, week_games in tier_season.results.items():
        for matchup_key, game_data in week_games.items():
            if not game_data:
                continue
            home_key = game_data.get("home_key", "")
            away_key = game_data.get("away_key", "")
            if home_key != team_key and away_key != team_key:
                continue
            side = "home" if home_key == team_key else "away"
            opponent_key = away_key if side == "home" else home_key
            opponent_name = game_data.get(f"{'away' if side == 'home' else 'home'}_name", opponent_key)
            result = game_data.get("result", {})
            ps = result.get("player_stats", {}).get(side, [])
            for pg in ps:
                if pg.get("name") == player_name:
                    home_score = game_data.get("home_score", 0)
                    away_score = game_data.get("away_score", 0)
                    my_score = home_score if side == "home" else away_score
                    opp_score = away_score if side == "home" else home_score
                    entry = {
                        "week": week_num,
                        "opponent": opponent_name,
                        "is_home": side == "home",
                        "won": my_score > opp_score,
                        "team_score": my_score,
                        "opp_score": opp_score,
                    }
                    entry.update(pg)
                    game_log.append(entry)
                    season_totals["games"] += 1
                    for stat in [
                        "touches", "yards", "rushing_yards", "lateral_yards",
                        "tds", "fumbles", "laterals_thrown",
                        "kick_att", "kick_made", "pk_att", "pk_made",
                        "dk_att", "dk_made", "tackles", "tfl", "sacks",
                        "hurries",
                        "kick_pass_yards", "kick_pass_tds",
                        "kick_passes_thrown", "kick_passes_completed",
                        "kick_return_yards", "punt_return_yards",
                        "rush_carries", "rushing_tds",
                        "lateral_receptions", "lateral_assists", "lateral_tds",
                        "kick_pass_interceptions_thrown", "kick_pass_receptions",
                        "kick_pass_ints",
                        "kick_returns", "kick_return_tds",
                        "punt_returns", "punt_return_tds",
                        "muffs", "st_tackles",
                        "keeper_tackles", "keeper_bells",
                        "kick_deflections", "coverage_snaps",
                        "keeper_return_yards",
                        "blocks", "pancakes",
                        "wpa", "plays_involved",
                    ]:
                        season_totals[stat] += pg.get(stat, 0)
                    break

    season_totals["ypc"] = round(
        season_totals["rushing_yards"] / max(1, season_totals["touches"]), 1
    )
    season_totals["yards_per_touch"] = season_totals["ypc"]
    season_totals["kp_pct"] = round(
        season_totals["kick_passes_completed"] / max(1, season_totals["kick_passes_thrown"]) * 100, 1
    )
    season_totals["kick_pct"] = round(
        season_totals["kick_made"] / max(1, season_totals["kick_att"]) * 100, 1
    )
    season_totals["total_return_yards"] = (
        season_totals["kick_return_yards"] + season_totals["punt_return_yards"]
    )
    season_totals["kick_return_avg"] = round(
        season_totals["kick_return_yards"] / max(1, season_totals["kick_returns"]), 1
    )
    season_totals["punt_return_avg"] = round(
        season_totals["punt_return_yards"] / max(1, season_totals["punt_returns"]), 1
    )
    season_totals["wpa_per_play"] = round(
        season_totals["wpa"] / max(1, season_totals["plays_involved"]), 3
    )

    from engine.wvl_config import CLUBS_BY_KEY
    club = CLUBS_BY_KEY.get(team_key)
    team_name = club.name if club else team_key

    return templates.TemplateResponse("wvl/player.html", _ctx(
        request, section="wvl", session_id=session_id,
        player=player, card=card,
        team_key=team_key, team_name=team_name,
        tier=team_tier, tier_name=_wvl_tier_label(team_tier),
        dynasty_name=data.get("dynasty_name", "WVL"),
        year=data.get("year", "?"),
        game_log=sorted(game_log, key=lambda g: g["week"]),
        season_totals=season_totals,
    ))


@router.get("/wvl/{session_id}/team-stats", response_class=HTMLResponse)
def wvl_team_stats(request: Request, session_id: str, tier: int = 1, sort: str = "total_yards"):
    data = _get_wvl_session(session_id)
    season = data["season"]
    tier_season = season.tier_seasons.get(tier)
    if not tier_season:
        raise HTTPException(404, f"Tier {tier} not found")

    tier_list = sorted(season.tier_seasons.keys())

    # Full aggregate — same logic as pro_team_stats
    team_agg = {}
    for week_num, week_games in tier_season.results.items():
        for matchup_key, game in week_games.items():
            result = game.get("result", {})
            stats = result.get("stats", {})
            for side in ("home", "away"):
                t_key = game.get(f"{side}_key", "")
                t_name = game.get(f"{side}_name", t_key)
                s = stats.get(side)
                if not s or not t_key:
                    continue
                if t_key not in team_agg:
                    team_agg[t_key] = {
                        "team_key": t_key, "team": t_name, "games": 0,
                        "total_yards": 0, "total_plays": 0, "touchdowns": 0,
                        "rushing_yards": 0, "rushing_carries": 0, "rushing_tds": 0,
                        "kp_yards": 0, "kp_att": 0, "kp_comp": 0, "kp_tds": 0, "kp_ints": 0,
                        "lateral_chains": 0, "lateral_yards": 0, "successful_laterals": 0,
                        "dk_made": 0, "dk_att": 0, "pk_made": 0, "pk_att": 0,
                        "fumbles": 0, "tod": 0, "penalties": 0, "penalty_yards": 0,
                        "delta_yards": 0, "delta_drives": 0, "delta_scores": 0,
                        "bonus_possessions": 0, "bonus_scores": 0, "bonus_yards": 0,
                        "epa": 0, "viper_eff_sum": 0, "team_rating_sum": 0,
                        "viper_eff_n": 0, "team_rating_n": 0,
                    }
                a = team_agg[t_key]
                a["games"] += 1
                a["total_yards"] += s.get("total_yards", 0)
                a["total_plays"] += s.get("total_plays", 0)
                a["touchdowns"] += s.get("touchdowns", 0)
                a["rushing_yards"] += s.get("rushing_yards", 0)
                a["rushing_carries"] += s.get("rushing_carries", 0)
                a["rushing_tds"] += s.get("rushing_touchdowns", 0)
                a["kp_yards"] += s.get("kick_pass_yards", 0)
                a["kp_att"] += s.get("kick_passes_attempted", 0)
                a["kp_comp"] += s.get("kick_passes_completed", 0)
                a["kp_tds"] += s.get("kick_pass_tds", 0)
                a["kp_ints"] += s.get("kick_pass_interceptions", 0)
                a["lateral_chains"] += s.get("lateral_chains", 0)
                a["lateral_yards"] += s.get("lateral_yards", 0)
                a["successful_laterals"] += s.get("successful_laterals", 0)
                a["dk_made"] += s.get("drop_kicks_made", 0)
                a["dk_att"] += s.get("drop_kicks_attempted", 0)
                a["pk_made"] += s.get("place_kicks_made", 0)
                a["pk_att"] += s.get("place_kicks_attempted", 0)
                a["fumbles"] += s.get("fumbles_lost", 0)
                a["tod"] += s.get("turnovers_on_downs", 0)
                a["penalties"] += s.get("penalties", 0)
                a["penalty_yards"] += s.get("penalty_yards", 0)
                a["delta_yards"] += s.get("delta_yards", 0)
                a["delta_drives"] += s.get("delta_drives", 0)
                a["delta_scores"] += s.get("delta_scores", 0)
                a["bonus_possessions"] += s.get("bonus_possessions", 0)
                a["bonus_scores"] += s.get("bonus_possession_scores", 0)
                a["bonus_yards"] += s.get("bonus_possession_yards", 0)
                epa_val = s.get("epa", 0)
                if isinstance(epa_val, dict):
                    a["epa"] += epa_val.get("total_epa", epa_val.get("wpa", 0))
                elif isinstance(epa_val, (int, float)):
                    a["epa"] += epa_val
                ve = s.get("viper_efficiency")
                if ve is not None:
                    a["viper_eff_sum"] += ve
                    a["viper_eff_n"] += 1
                vm = s.get("viperball_metrics", {})
                tr = vm.get("team_rating") if vm else None
                if tr is not None:
                    a["team_rating_sum"] += tr
                    a["team_rating_n"] += 1

    teams = list(team_agg.values())
    for t in teams:
        n = max(1, t["games"])
        t["avg_yards"] = round(t["total_yards"] / n, 1)
        t["yards_per_play"] = round(t["total_yards"] / max(1, t["total_plays"]), 2)
        t["kp_comp_pct"] = round(t["kp_comp"] / max(1, t["kp_att"]) * 100, 1)
        t["avg_epa"] = round(t["epa"] / n, 2)
        t["avg_team_rating"] = round(t["team_rating_sum"] / max(1, t["team_rating_n"]), 1) if t["team_rating_n"] else 0
        t["avg_viper_eff"] = round(t["viper_eff_sum"] / max(1, t["viper_eff_n"]), 3) if t["viper_eff_n"] else 0
        rec = tier_season.standings.get(t["team_key"])
        if rec:
            t["wins"] = rec.wins
            t["losses"] = rec.losses
        else:
            t["wins"] = 0
            t["losses"] = 0

    valid_sorts = {
        "total_yards": "total_yards", "avg_yards": "avg_yards",
        "touchdowns": "touchdowns", "rushing_yards": "rushing_yards",
        "kp_yards": "kp_yards", "lateral_yards": "lateral_yards",
        "epa": "epa", "avg_epa": "avg_epa",
        "avg_team_rating": "avg_team_rating", "avg_viper_eff": "avg_viper_eff",
        "delta_yards": "delta_yards", "fumbles": "fumbles",
        "penalties": "penalties", "yards_per_play": "yards_per_play",
        "bonus_possessions": "bonus_possessions",
    }
    sort_key = valid_sorts.get(sort, "total_yards")
    teams.sort(key=lambda x: x.get(sort_key, 0), reverse=True)

    return templates.TemplateResponse("wvl/team_stats.html", _ctx(
        request, section="wvl", session_id=session_id,
        teams=teams, sort=sort, selected_tier=tier,
        tier_name=_wvl_tier_label(tier),
        tier_list=tier_list, tier_label=_wvl_tier_label,
        dynasty_name=data.get("dynasty_name", "WVL"),
        year=data.get("year", "?"),
    ))


# ── WVL DYNASTY DATA ─────────────────────────────────────────────────────

@router.get("/wvl/{session_id}/data", response_class=HTMLResponse)
def wvl_data(request: Request, session_id: str):
    data = _get_wvl_session(session_id)
    dynasty = data.get("dynasty")
    if not dynasty:
        raise HTTPException(404, "No dynasty active in this WVL session")

    return templates.TemplateResponse("wvl/data.html", _ctx(
        request, section="wvl", session_id=session_id,
        dynasty_name=dynasty.dynasty_name,
        year=dynasty.current_year,
        team_count=len(dynasty.team_histories),
    ))


@router.get("/wvl/{session_id}/data/download")
def wvl_data_download(request: Request, session_id: str):
    import json as _json
    from fastapi.responses import Response
    from engine.db import serialize_dynasty

    data = _get_wvl_session(session_id)
    dynasty = data.get("dynasty")
    if not dynasty:
        raise HTTPException(404, "No dynasty active in this WVL session")

    serialized = serialize_dynasty(dynasty)
    content = _json.dumps(serialized, indent=2)
    filename = f"WVL_{dynasty.dynasty_name.replace(' ', '_')}_Y{dynasty.current_year}.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/wvl/{session_id}/data/upload")
async def wvl_data_upload(request: Request, session_id: str):
    import json as _json
    from fastapi.responses import JSONResponse
    from engine.db import deserialize_dynasty

    data = _get_wvl_session(session_id)
    if not data.get("dynasty"):
        raise HTTPException(404, "No dynasty active in this WVL session")

    form = await request.form()
    file = form.get("file")
    if not file:
        raise HTTPException(400, "No file provided")

    try:
        contents = await file.read()
        parsed = _json.loads(contents)
        dynasty = deserialize_dynasty(parsed)
        data["dynasty"] = dynasty
        return JSONResponse({"message": f"Dynasty '{dynasty.dynasty_name}' loaded (Year {dynasty.current_year})."})
    except Exception as e:
        raise HTTPException(400, f"Failed to load dynasty file: {e}")


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


@router.get("/international/game/{match_id}", response_class=HTMLResponse)
def intl_game(request: Request, match_id: str):
    fiv_data = _get_fiv_data()
    if not fiv_data:
        raise HTTPException(404, "No active FIV cycle")

    from engine.fiv import find_match_in_cycle
    match = find_match_in_cycle(fiv_data, match_id)
    if not match:
        raise HTTPException(404, f"Match '{match_id}' not found")

    game_result = match.get("game_result", {})
    home_code = match.get("home_code", match.get("home", "?"))
    away_code = match.get("away_code", match.get("away", "?"))

    teams = fiv_data.get("national_teams", {})
    home_name = home_code
    away_name = away_code
    if isinstance(teams.get(home_code), dict):
        home_name = teams[home_code].get("nation", {}).get("name", home_code)
    if isinstance(teams.get(away_code), dict):
        away_name = teams[away_code].get("nation", {}).get("name", away_code)

    _normalize_box_score_stats(game_result)

    return templates.TemplateResponse("international/game.html", _ctx(
        request, section="international",
        match=match, gr=game_result,
        home_code=home_code, away_code=away_code,
        home_name=home_name, away_name=away_name,
    ))


@router.get("/international/worldcup/stats", response_class=HTMLResponse)
def intl_worldcup_stats(request: Request):
    fiv_data = _get_fiv_data()
    cycle = _get_fiv_cycle()
    if not fiv_data:
        raise HTTPException(404, "No active FIV cycle")

    wc = fiv_data.get("world_cup")
    leaders = None
    golden_boot = wc.get("golden_boot") if wc else None
    mvp = wc.get("mvp") if wc else None

    if cycle and cycle.world_cup and cycle.world_cup.all_results:
        from engine.fiv import compute_tournament_stat_leaders
        leaders = compute_tournament_stat_leaders(cycle.world_cup.all_results)

    return templates.TemplateResponse("international/worldcup_stats.html", _ctx(
        request, section="international",
        leaders=leaders, golden_boot=golden_boot, mvp=mvp,
    ))


@router.get("/international/confederation/{conf}/stats", response_class=HTMLResponse)
def intl_confederation_stats(request: Request, conf: str):
    cycle = _get_fiv_cycle()
    if not cycle:
        raise HTTPException(404, "No active FIV cycle")

    cc = cycle.confederations_data.get(conf)
    if not cc:
        raise HTTPException(404, f"Confederation '{conf}' not found")

    from engine.fiv import compute_tournament_stat_leaders
    leaders = compute_tournament_stat_leaders(cc.all_results)

    conf_name = getattr(cc, "conf_full_name", conf)
    champion = getattr(cc, "champion", None)

    return templates.TemplateResponse("international/confederation_stats.html", _ctx(
        request, section="international",
        leaders=leaders, conf=conf, conf_name=conf_name, champion=champion,
    ))


@router.get("/international/team-stats", response_class=HTMLResponse)
def intl_team_stats(request: Request, sort: str = "total_yards"):
    fiv_data = _get_fiv_data()
    if not fiv_data:
        raise HTTPException(404, "No active FIV cycle")

    team_agg = {}
    all_results = []

    for conf_id, cc_data in fiv_data.get("confederations_data", {}).items():
        for group in cc_data.get("groups", []):
            all_results.extend(group.get("results", []))
        for result in cc_data.get("all_results", []):
            if result not in all_results:
                all_results.append(result)

    wc = fiv_data.get("world_cup")
    if wc:
        for group in wc.get("groups", []):
            all_results.extend(group.get("results", []))
        for kr in wc.get("knockout_rounds", []):
            for m in kr.get("matchups", []):
                r = m.get("result")
                if r:
                    all_results.append(r)

    teams_data = fiv_data.get("national_teams", {})

    for match in all_results:
        gr = match.get("game_result", {})
        if not gr:
            continue
        stats = gr.get("stats", {})
        home_code = match.get("home_code", match.get("home", ""))
        away_code = match.get("away_code", match.get("away", ""))

        for side, code in [("home", home_code), ("away", away_code)]:
            s = stats.get(side)
            if not s or not code:
                continue
            if code not in team_agg:
                td = teams_data.get(code, {})
                nation = td.get("nation", {}) if isinstance(td, dict) else {}
                team_agg[code] = {
                    "code": code, "name": nation.get("name", code),
                    "tier": nation.get("tier", ""),
                    "confederation": nation.get("confederation", ""),
                    "games": 0,
                    "total_yards": 0, "total_plays": 0, "touchdowns": 0,
                    "rushing_yards": 0, "kp_yards": 0, "lateral_yards": 0,
                    "fumbles": 0, "epa": 0, "delta_yards": 0,
                    "viper_eff_sum": 0, "team_rating_sum": 0,
                    "viper_eff_n": 0, "team_rating_n": 0,
                }
            a = team_agg[code]
            a["games"] += 1
            a["total_yards"] += s.get("total_yards", 0)
            a["total_plays"] += s.get("total_plays", 0)
            a["touchdowns"] += s.get("touchdowns", 0)
            a["rushing_yards"] += s.get("rushing_yards", 0)
            a["kp_yards"] += s.get("kick_pass_yards", 0)
            a["lateral_yards"] += s.get("lateral_yards", 0)
            a["fumbles"] += s.get("fumbles_lost", 0)
            epa_val = s.get("epa", 0)
            if isinstance(epa_val, dict):
                a["epa"] += epa_val.get("total_epa", epa_val.get("wpa", 0))
            elif isinstance(epa_val, (int, float)):
                a["epa"] += epa_val
            a["delta_yards"] += s.get("delta_yards", 0)
            ve = s.get("viper_efficiency")
            if ve is not None:
                a["viper_eff_sum"] += ve
                a["viper_eff_n"] += 1
            vm = s.get("viperball_metrics", {})
            tr = vm.get("team_rating") if vm else None
            if tr is not None:
                a["team_rating_sum"] += tr
                a["team_rating_n"] += 1

    teams = list(team_agg.values())
    for t in teams:
        n = max(1, t["games"])
        t["avg_yards"] = round(t["total_yards"] / n, 1)
        t["avg_epa"] = round(t["epa"] / n, 2)
        t["avg_team_rating"] = round(t["team_rating_sum"] / max(1, t["team_rating_n"]), 1) if t["team_rating_n"] else 0
        t["avg_viper_eff"] = round(t["viper_eff_sum"] / max(1, t["viper_eff_n"]), 3) if t["viper_eff_n"] else 0

    valid_sorts = {
        "total_yards": "total_yards", "avg_yards": "avg_yards",
        "touchdowns": "touchdowns", "rushing_yards": "rushing_yards",
        "kp_yards": "kp_yards", "lateral_yards": "lateral_yards",
        "epa": "epa", "avg_epa": "avg_epa",
        "avg_team_rating": "avg_team_rating", "avg_viper_eff": "avg_viper_eff",
        "delta_yards": "delta_yards", "fumbles": "fumbles",
    }
    sort_key = valid_sorts.get(sort, "total_yards")
    teams.sort(key=lambda x: x.get(sort_key, 0), reverse=True)

    return templates.TemplateResponse("international/team_stats.html", _ctx(
        request, section="international", teams=teams, sort=sort,
    ))


@router.get("/international/team/{nation_code}/player/{player_name}", response_class=HTMLResponse)
def intl_player(request: Request, nation_code: str, player_name: str):
    fiv_data = _get_fiv_data()
    if not fiv_data:
        raise HTTPException(404, "No active FIV cycle")

    teams = fiv_data.get("national_teams", {})
    team_data = teams.get(nation_code)
    if not team_data:
        raise HTTPException(404, f"Nation '{nation_code}' not found")

    # Find the player in the roster
    roster = team_data.get("roster", []) if isinstance(team_data, dict) else []
    player = None
    for p in roster:
        if isinstance(p, dict):
            pl = p.get("player", p)
            if pl.get("name") == player_name:
                player = p
                break

    if not player:
        raise HTTPException(404, f"Player '{player_name}' not found on {nation_code}")

    nation = team_data.get("nation", {}) if isinstance(team_data, dict) else {}

    cross_links = _find_cross_league_links(player_name, exclude_nation=nation_code)

    return templates.TemplateResponse("international/player.html", _ctx(
        request, section="international", player=player, nation_code=nation_code,
        nation=nation, team_data=team_data, cross_links=cross_links,
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


# ── ARCHIVES ────────────────────────────────────────────────────────────

@router.get("/archives/", response_class=HTMLResponse)
def archives_index(request: Request):
    """List all archived seasons."""
    archives = []
    list_fn, _ = _get_archives()
    meta_fn = _get_archive_meta()
    if list_fn:
        try:
            for save_row in list_fn():
                key = save_row["save_key"]
                label = save_row.get("label", key)
                # Use lightweight meta blob instead of loading full 50MB archive
                summary = meta_fn(key) if meta_fn else None
                if summary:
                    archives.append({
                        "key": key,
                        "label": label,
                        "type": summary.get("type", "college"),
                        "champion": summary.get("champion"),
                        "team_count": summary.get("team_count", 0),
                        "games_played": summary.get("games_played", 0),
                        "total_games": summary.get("total_games", 0),
                        "created_at": save_row.get("created_at", 0),
                    })
                else:
                    # Fallback for archives saved before meta was added
                    archives.append({
                        "key": key,
                        "label": label,
                        "type": "college",
                        "champion": None,
                        "team_count": 0,
                        "games_played": 0,
                        "total_games": 0,
                        "created_at": save_row.get("created_at", 0),
                    })
        except Exception:
            pass

    return templates.TemplateResponse("archives/index.html", _ctx(
        request, section="archives", archives=archives,
    ))


@router.get("/archives/{archive_key}/", response_class=HTMLResponse)
def archive_detail(request: Request, archive_key: str):
    """View an archived season."""
    _, load_fn = _get_archives()
    if not load_fn:
        raise HTTPException(404, "Archive system unavailable")

    data = load_fn(archive_key)
    if data is None:
        raise HTTPException(404, "Archive not found")

    archive_type = data.get("type", "college")

    if archive_type == "fiv":
        return templates.TemplateResponse("archives/fiv.html", _ctx(
            request, section="archives", archive=data, archive_key=archive_key,
        ))

    # College archive
    return templates.TemplateResponse("archives/college_season.html", _ctx(
        request, section="archives", archive=data, archive_key=archive_key,
    ))


@router.get("/archives/{archive_key}/standings", response_class=HTMLResponse)
def archive_standings(request: Request, archive_key: str):
    _, load_fn = _get_archives()
    if not load_fn:
        raise HTTPException(404, "Archive system unavailable")
    data = load_fn(archive_key)
    if data is None:
        raise HTTPException(404, "Archive not found")

    standings = data.get("standings", [])
    conferences = data.get("conferences", {})

    # Build per-conference standings
    conf_standings = {}
    if conferences:
        team_conf = data.get("team_conferences", {})
        for conf_name in conferences:
            conf_standings[conf_name] = [
                s for s in standings if team_conf.get(s["team_name"]) == conf_name
            ]
            conf_standings[conf_name].sort(
                key=lambda s: (s.get("conf_wins", 0), s.get("wins", 0), s.get("points_for", 0)),
                reverse=True,
            )

    return templates.TemplateResponse("archives/standings.html", _ctx(
        request, section="archives", archive=data, archive_key=archive_key,
        standings=standings, conferences=conferences, conf_standings=conf_standings,
    ))


@router.get("/archives/{archive_key}/schedule", response_class=HTMLResponse)
def archive_schedule(request: Request, archive_key: str, week: int = 0):
    _, load_fn = _get_archives()
    if not load_fn:
        raise HTTPException(404, "Archive system unavailable")
    data = load_fn(archive_key)
    if data is None:
        raise HTTPException(404, "Archive not found")

    schedule = data.get("schedule", [])
    weeks = sorted(set(g["week"] for g in schedule))

    if week > 0:
        week_games = [g for g in schedule if g["week"] == week]
    elif weeks:
        week = weeks[-1]
        week_games = [g for g in schedule if g["week"] == week]
    else:
        week_games = []

    return templates.TemplateResponse("archives/schedule.html", _ctx(
        request, section="archives", archive=data, archive_key=archive_key,
        games=week_games, weeks=weeks, selected_week=week,
    ))


@router.get("/archives/{archive_key}/polls", response_class=HTMLResponse)
def archive_polls(request: Request, archive_key: str, week: int = 0):
    _, load_fn = _get_archives()
    if not load_fn:
        raise HTTPException(404, "Archive system unavailable")
    data = load_fn(archive_key)
    if data is None:
        raise HTTPException(404, "Archive not found")

    polls = data.get("polls", [])
    weeks = sorted(set(p["week"] for p in polls))

    if week > 0:
        selected = [p for p in polls if p["week"] == week]
    elif polls:
        selected = [polls[-1]]
        week = polls[-1]["week"]
    else:
        selected = []

    return templates.TemplateResponse("archives/polls.html", _ctx(
        request, section="archives", archive=data, archive_key=archive_key,
        polls=selected, weeks=weeks, selected_week=week,
    ))


@router.get("/archives/{archive_key}/team/{team_name}", response_class=HTMLResponse)
def archive_team(request: Request, archive_key: str, team_name: str):
    _, load_fn = _get_archives()
    if not load_fn:
        raise HTTPException(404, "Archive system unavailable")
    data = load_fn(archive_key)
    if data is None:
        raise HTTPException(404, "Archive not found")

    # Find team record
    team_record = None
    for s in data.get("standings", []):
        if s["team_name"] == team_name:
            team_record = s
            break
    if not team_record:
        raise HTTPException(404, f"Team '{team_name}' not found in archive")

    # Team schedule
    team_games = [g for g in data.get("schedule", [])
                  if g["home_team"] == team_name or g["away_team"] == team_name]

    # Team roster
    roster_data = data.get("team_rosters", {}).get(team_name, {})
    players = roster_data.get("players", [])

    # Aggregate team stats from full_result data in schedule
    team_season_stats = _aggregate_archive_team_stats(data.get("schedule", []), team_name)

    return templates.TemplateResponse("archives/team.html", _ctx(
        request, section="archives", archive=data, archive_key=archive_key,
        team_name=team_name, record=team_record, games=team_games,
        players=players, team_stats=team_season_stats,
    ))


@router.get("/archives/{archive_key}/playoffs", response_class=HTMLResponse)
def archive_playoffs(request: Request, archive_key: str):
    _, load_fn = _get_archives()
    if not load_fn:
        raise HTTPException(404, "Archive system unavailable")
    data = load_fn(archive_key)
    if data is None:
        raise HTTPException(404, "Archive not found")

    return templates.TemplateResponse("archives/playoffs.html", _ctx(
        request, section="archives", archive=data, archive_key=archive_key,
        playoff_bracket=data.get("playoff_bracket", []),
        bowl_games=data.get("bowl_games", []),
        champion=data.get("champion"),
    ))


@router.get("/archives/{archive_key}/awards", response_class=HTMLResponse)
def archive_awards(request: Request, archive_key: str):
    _, load_fn = _get_archives()
    if not load_fn:
        raise HTTPException(404, "Archive system unavailable")
    data = load_fn(archive_key)
    if data is None:
        raise HTTPException(404, "Archive not found")

    return templates.TemplateResponse("archives/awards.html", _ctx(
        request, section="archives", archive=data, archive_key=archive_key,
        awards=data.get("awards"),
    ))


def _aggregate_archive_team_stats(schedule: list, team_name: str) -> dict | None:
    """Aggregate team season stats from archived schedule data."""
    completed_stats = []
    for game in schedule:
        if not game.get("completed"):
            continue
        if game["home_team"] != team_name and game["away_team"] != team_name:
            continue
        side = "home" if game["home_team"] == team_name else "away"
        fr = game.get("full_result")
        if not fr:
            continue
        stats = fr.get("stats", {}).get(side)
        if stats:
            completed_stats.append(stats)

    if not completed_stats:
        return None

    n = len(completed_stats)
    total_yards = sum(s.get("total_yards", 0) for s in completed_stats)
    rushing_yards = sum(s.get("rushing_yards", 0) for s in completed_stats)
    rushing_carries = sum(s.get("rushing_carries", 0) for s in completed_stats)
    rushing_tds = sum(s.get("rushing_touchdowns", 0) for s in completed_stats)
    kp_yards = sum(s.get("kick_pass_yards", 0) for s in completed_stats)
    kp_att = sum(s.get("kick_passes_attempted", 0) for s in completed_stats)
    kp_comp = sum(s.get("kick_passes_completed", 0) for s in completed_stats)
    kp_tds = sum(s.get("kick_pass_tds", 0) for s in completed_stats)
    kp_ints = sum(s.get("kick_pass_interceptions", 0) for s in completed_stats)
    touchdowns = sum(s.get("touchdowns", 0) for s in completed_stats)
    fumbles = sum(s.get("fumbles_lost", 0) for s in completed_stats)
    penalties = sum(s.get("penalties", 0) for s in completed_stats)
    penalty_yards = sum(s.get("penalty_yards", 0) for s in completed_stats)
    total_plays = sum(s.get("total_plays", 0) for s in completed_stats)

    return {
        "games_played": n,
        "total_yards": total_yards,
        "total_plays": total_plays,
        "avg_yards": round(total_yards / n, 1),
        "yards_per_play": round(total_yards / max(1, total_plays), 2),
        "rushing_yards": rushing_yards,
        "avg_rushing": round(rushing_yards / n, 1),
        "rushing_carries": rushing_carries,
        "rushing_tds": rushing_tds,
        "yards_per_carry": round(rushing_yards / max(1, rushing_carries), 1),
        "kick_pass_yards": kp_yards,
        "kp_attempts": kp_att,
        "kp_completions": kp_comp,
        "kp_comp_pct": round(kp_comp / max(1, kp_att) * 100, 1),
        "kp_tds": kp_tds,
        "kp_ints": kp_ints,
        "touchdowns": touchdowns,
        "fumbles": fumbles,
        "penalties": penalties,
        "penalty_yards": penalty_yards,
    }


# ── RECRUITING ──────────────────────────────────────────────────────────

def _get_recruiting_pipeline():
    """Get the active HS recruiting pipeline, if any dynasty has one."""
    try:
        from api.main import sessions
        for sid, sess in sessions.items():
            dynasty = sess.get("dynasty")
            if dynasty and hasattr(dynasty, "_hs_pipeline") and dynasty._hs_pipeline:
                return dynasty._hs_pipeline, dynasty, sid
        return None, None, None
    except Exception:
        return None, None, None


def _get_dynasty_for_classes():
    """Find a dynasty session with teams for class export viewing."""
    try:
        from api.main import sessions
        for sid, sess in sessions.items():
            dynasty = sess.get("dynasty")
            season = sess.get("season")
            if dynasty and season and hasattr(season, "teams") and season.teams:
                return dynasty, season, sid
        return None, None, None
    except Exception:
        return None, None, None


@router.get("/recruiting/", response_class=HTMLResponse)
def recruiting_index(request: Request):
    pipeline, dynasty, sid = _get_recruiting_pipeline()

    pipeline_summary = None
    top_prospects = []
    if pipeline:
        pipeline_summary = pipeline.pipeline_summary()
        raw_top = pipeline.get_top_prospects(n=25)
        for p in raw_top:
            top_prospects.append({
                "name": p.recruit.full_name,
                "position": p.recruit.position,
                "scouted_stars": p.scouted_stars,
                "grade": p.grade,
                "hometown": p.recruit.hometown,
                "high_school": p.recruit.high_school,
                "position_rank": p.position_rank,
                "regional_rank": p.regional_rank,
                "is_alpha": p.is_alpha,
            })

    # Find sessions with dynasty data for draft classes
    draft_sessions = []
    try:
        from api.main import sessions
        for s_id, sess in sessions.items():
            d = sess.get("dynasty")
            s = sess.get("season")
            if d and s and hasattr(s, "teams"):
                draft_sessions.append({
                    "session_id": s_id,
                    "dynasty_name": d.dynasty_name,
                    "team_count": len(s.teams),
                })
    except Exception:
        pass

    return templates.TemplateResponse("recruiting/index.html", _ctx(
        request,
        section="recruiting",
        pipeline_summary=pipeline_summary,
        top_prospects=top_prospects,
        draft_sessions=draft_sessions,
    ))


@router.get("/recruiting/hs-rankings", response_class=HTMLResponse)
def recruiting_hs_rankings(request: Request):
    from engine.recruiting import POSITIONS

    grade = request.query_params.get("grade", "12th")
    position = request.query_params.get("position", "")

    pipeline, dynasty, sid = _get_recruiting_pipeline()

    board = []
    visible_attrs = []
    if pipeline:
        raw_board = pipeline.get_rankings_board(grade=grade, top_n=100)
        if position:
            raw_board = [p for p in raw_board if p["position"] == position]
        board = raw_board
        # Determine which attributes are visible for this grade
        if board:
            visible_attrs = sorted(board[0].get("visible_attributes", {}).keys())

    return templates.TemplateResponse("recruiting/hs_rankings.html", _ctx(
        request,
        section="recruiting",
        grade=grade,
        position=position,
        positions=POSITIONS,
        board=board,
        visible_attrs=visible_attrs,
    ))


@router.get("/recruiting/draft-classes", response_class=HTMLResponse)
def recruiting_draft_classes(request: Request):
    from engine.player_card import player_to_card

    active_class = request.query_params.get("class_year", "Senior")
    session_id = request.query_params.get("session", "")
    class_years = ["Freshman", "Sophomore", "Junior", "Senior"]

    dynasty, season, sid = _get_dynasty_for_classes()
    if session_id:
        # Try to load specific session
        try:
            from api.main import sessions
            sess = sessions.get(session_id, {})
            dynasty = sess.get("dynasty", dynasty)
            season = sess.get("season", season)
            sid = session_id
        except Exception:
            pass

    players = []
    class_counts = {}
    if dynasty and season and hasattr(season, "teams"):
        for class_year in class_years:
            count = 0
            for team_name, team in season.teams.items():
                conf = dynasty.get_team_conference(team_name) if dynasty else ""
                prestige = dynasty.team_prestige.get(team_name, 50) if dynasty else 50
                for player in team.players:
                    py = getattr(player, "year", "")
                    if py == class_year or (class_year == "Senior" and py == "Graduate"):
                        count += 1
                        if class_year == active_class:
                            card = player_to_card(player, team_name)
                            players.append({
                                "full_name": card.full_name,
                                "player": card.full_name,
                                "position": card.position,
                                "overall": card.overall,
                                "potential": card.potential,
                                "development": card.development,
                                "team": team_name,
                                "conference": conf,
                                "prestige": prestige,
                                "speed": card.speed,
                                "stamina": card.stamina,
                                "agility": card.agility,
                                "power": card.power,
                                "awareness": card.awareness,
                                "hands": card.hands,
                                "kicking": card.kicking,
                                "tackling": card.tackling,
                                "hometown": f"{card.hometown_city}, {card.hometown_state}",
                            })
            class_counts[class_year] = count

        # Sort by overall descending
        players.sort(key=lambda p: -p["overall"])

    return templates.TemplateResponse("recruiting/draft_classes.html", _ctx(
        request,
        section="recruiting",
        active_class=active_class,
        class_years=class_years,
        players=players,
        class_counts=class_counts,
        session_id=sid or "",
    ))


@router.get("/recruiting/pro-pipeline", response_class=HTMLResponse)
def recruiting_pro_pipeline(request: Request):
    pipeline, dynasty, sid = _get_recruiting_pipeline()

    # Build intake preview from pipeline's upcoming 12th graders
    intake_classes = {}
    graduates = []

    if pipeline:
        # Each grade represents a future intake year
        for grade in ["12th", "11th", "10th", "9th"]:
            prospects = pipeline.classes.get(grade, [])
            intake_label = {
                "12th": "intake_1",
                "11th": "intake_2",
                "10th": "intake_3",
                "9th": "intake_4",
            }[grade]
            intake_classes[intake_label] = [
                {
                    "first_name": p.recruit.first_name,
                    "last_name": p.recruit.last_name,
                    "position": p.recruit.position,
                    "stars": p.scouted_stars,
                    "true_overall": p.recruit.true_overall,
                    "true_potential": p.recruit.true_potential,
                    "true_development": p.recruit.true_development,
                    "hometown": p.recruit.hometown,
                    "high_school": p.recruit.high_school,
                    "region": p.recruit.region,
                }
                for p in prospects
            ]

    # Get graduates from dynasty if available
    dynasty_d, season, s_sid = _get_dynasty_for_classes()
    if dynasty_d and season and hasattr(season, "teams"):
        from engine.player_card import player_to_card
        for team_name, team in season.teams.items():
            conf = dynasty_d.get_team_conference(team_name)
            for player in team.players:
                py = getattr(player, "year", "")
                if py in ("Senior", "Graduate"):
                    card = player_to_card(player, team_name)
                    graduates.append({
                        "full_name": card.full_name,
                        "position": card.position,
                        "overall": card.overall,
                        "potential": card.potential,
                        "college_team": team_name,
                        "conference": conf,
                        "speed": card.speed,
                        "power": card.power,
                        "awareness": card.awareness,
                    })
        graduates.sort(key=lambda p: -p["overall"])

    return templates.TemplateResponse("recruiting/pro_pipeline.html", _ctx(
        request,
        section="recruiting",
        intake_classes=intake_classes,
        graduates=graduates,
    ))
