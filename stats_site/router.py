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
        LEAGUE_CONFIGS,
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
        "league_configs": LEAGUE_CONFIGS,
    }


def _get_fiv_data():
    """Get FIV cycle data, returns None if unavailable."""
    try:
        from api.main import _get_fiv_cycle_data
        return _get_fiv_cycle_data()
    except Exception:
        return None


def _get_archives():
    """Get list of archived seasons from the database."""
    try:
        from engine.db import list_season_archives, load_season_archive
        return list_season_archives, load_season_archive
    except Exception:
        return None, None


def _get_fiv_rankings():
    """Get FIV rankings."""
    try:
        from engine.fiv import load_fiv_rankings
        return load_fiv_rankings()
    except Exception:
        return None


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

    return templates.TemplateResponse("home.html", _ctx(
        request,
        section="home",
        college_sessions=college,
        pro_sessions=pro,
        wvl_sessions=wvl,
        fiv_data=fiv_data,
        fiv_rankings=fiv_rankings,
        archives=archives,
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

    # Team schedule – compute per-week game index for box score links
    week_counters_all = {}
    game_idx_map = {}  # map (week, home, away) -> week_game_idx
    for g in season.schedule:
        w = g.week
        idx = week_counters_all.get(w, 0)
        game_idx_map[(w, g.home_team, g.away_team)] = idx
        week_counters_all[w] = idx + 1

    team_games = []
    for g in season.schedule:
        if g.home_team != team_name and g.away_team != team_name:
            continue
        sg = api["serialize_game"](g)
        sg["week_game_idx"] = game_idx_map.get((g.week, g.home_team, g.away_team), 0)
        team_games.append(sg)

    dynasty = sess.get("dynasty")
    prestige = None
    if dynasty and hasattr(dynasty, "team_prestige"):
        prestige = dynasty.team_prestige.get(team_name)

    # ── Aggregate team season stats from completed games ──
    team_season_stats = None
    completed_games_with_stats = []
    for game in season.schedule:
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
            "compelled_eff": round(delta_scores_total / max(1, delta_drives) * 100, 1) if delta_drives > 0 else None,
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

    return templates.TemplateResponse("college/team.html", _ctx(
        request, section="college", session_id=session_id,
        team=team, team_name=team_name, players=players,
        record=team_record, games=team_games, prestige=prestige,
        team_stats=team_season_stats,
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
    }
    for game in season.schedule:
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

    # Team record for context
    record = season.standings.get(team_name)
    team_record = api["serialize_team_record"](record) if record else None

    dynasty = sess.get("dynasty")
    prestige = None
    if dynasty and hasattr(dynasty, "team_prestige"):
        prestige = dynasty.team_prestige.get(team_name)

    cross_links = _find_cross_league_links(player_name, exclude_college_session=session_id)

    return templates.TemplateResponse("college/player.html", _ctx(
        request, section="college", session_id=session_id,
        player=player_data, card=card, team_name=team_name,
        team=team, game_log=game_log, season_totals=season_totals,
        record=team_record, prestige=prestige, cross_links=cross_links,
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


@router.get("/college/{session_id}/team-stats", response_class=HTMLResponse)
def college_team_stats(request: Request, session_id: str, sort: str = "total_yards", conference: str = ""):
    api = _get_api()
    sess = api["get_session"](session_id)
    season = api["require_season"](sess)

    # Aggregate team stats from completed games
    team_agg = {}
    for game in season.schedule:
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
        t["compelled_eff"] = round(t["delta_scores"] / max(1, t["delta_drives"]) * 100, 1) if t["delta_drives"] > 0 else None
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
    for g in bracket:
        sg = api["serialize_game"](g, include_full_result=False)
        wk = sg.get("week", 0)
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

    # Derive seeds from first-round matchup order
    seed_map = {}
    if bracket:
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
        t["compelled_eff"] = round(t["delta_scores"] / max(1, t["delta_drives"]) * 100, 1) if t["delta_drives"] > 0 else None
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

    return templates.TemplateResponse("wvl/team.html", _ctx(
        request, section="wvl", session_id=session_id,
        team=detail, team_key=team_key, tier=team_tier,
        tier_name=_wvl_tier_label(team_tier),
        is_owner_club=is_owner_club,
        dynasty_name=data.get("dynasty_name", "WVL"),
        year=data.get("year", "?"),
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


@router.get("/wvl/{session_id}/team-stats", response_class=HTMLResponse)
def wvl_team_stats(request: Request, session_id: str, tier: int = 1, sort: str = "total_yards"):
    data = _get_wvl_session(session_id)
    season = data["season"]
    tier_season = season.tier_seasons.get(tier)
    if not tier_season:
        raise HTTPException(404, f"Tier {tier} not found")

    tier_list = sorted(season.tier_seasons.keys())

    # Aggregate team stats from completed game results (same logic as pro)
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
                        "total_yards": 0, "touchdowns": 0,
                        "rushing_yards": 0, "kp_yards": 0,
                        "lateral_yards": 0, "fumbles": 0, "penalties": 0,
                    }
                a = team_agg[t_key]
                a["games"] += 1
                a["total_yards"] += s.get("total_yards", 0)
                a["touchdowns"] += s.get("touchdowns", 0)
                a["rushing_yards"] += s.get("rushing_yards", 0)
                a["kp_yards"] += s.get("kick_pass_yards", 0)
                a["lateral_yards"] += s.get("lateral_yards", 0)
                a["fumbles"] += s.get("fumbles_lost", 0)
                a["penalties"] += s.get("penalties", 0)

    teams = list(team_agg.values())
    for t in teams:
        n = max(1, t["games"])
        t["avg_yards"] = round(t["total_yards"] / n, 1)
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
        "fumbles": "fumbles", "penalties": "penalties",
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

    return templates.TemplateResponse("international/game.html", _ctx(
        request, section="international",
        match=match, gr=game_result,
        home_code=home_code, away_code=away_code,
        home_name=home_name, away_name=away_name,
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
    list_fn, load_fn = _get_archives()
    if list_fn:
        try:
            for meta in list_fn():
                # Load just the header fields from each archive
                data = load_fn(meta["save_key"]) if load_fn else None
                archives.append({
                    "key": meta["save_key"],
                    "label": meta.get("label", meta["save_key"]),
                    "type": data.get("type", "college") if data else "college",
                    "champion": data.get("champion") if data else None,
                    "team_count": data.get("team_count", 0) if data else 0,
                    "games_played": data.get("games_played", 0) if data else 0,
                    "total_games": data.get("total_games", 0) if data else 0,
                    "created_at": meta.get("created_at", 0),
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
