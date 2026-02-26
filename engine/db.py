"""
Viperball Persistence Layer
============================

SQLite-backed JSON blob store for saving and restoring session state.

Design:
  - Each "save" is a JSON document stored in a single row
  - Tables are keyed by (user_id, save_type, save_key)
  - No ORM — pure sqlite3 + json for zero-dependency operation
  - Thread-safe via WAL mode and connection-per-call pattern

Save types:
  - "pro_league"   → ProLeagueSeason state blob
  - "dq_manager"   → DraftyQueenzManager state blob
  - "college"      → College Season state blob
  - "dynasty"      → Dynasty state blob
  - "user_prefs"   → User preferences and settings
  - "league_archive" → Completed league snapshots for Champions League
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

_log = logging.getLogger("viperball.db")

# Default database location — alongside the data/ directory
_DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "viperball.db"

_db_path: Path = _DEFAULT_DB_PATH


def set_db_path(path: str | Path):
    """Override the database file path (e.g. for testing)."""
    global _db_path
    _db_path = Path(path)


def get_db_path() -> Path:
    return _db_path


def _connect() -> sqlite3.Connection:
    """Open a connection with WAL mode for concurrent read safety."""
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_db_path), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist. Safe to call multiple times."""
    conn = _connect()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS saves (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT    NOT NULL DEFAULT 'default',
                save_type   TEXT    NOT NULL,
                save_key    TEXT    NOT NULL,
                label       TEXT    NOT NULL DEFAULT '',
                data        TEXT    NOT NULL,
                created_at  REAL    NOT NULL,
                updated_at  REAL    NOT NULL,
                UNIQUE(user_id, save_type, save_key)
            );

            CREATE INDEX IF NOT EXISTS idx_saves_user_type
                ON saves(user_id, save_type);

            CREATE INDEX IF NOT EXISTS idx_saves_updated
                ON saves(updated_at DESC);
        """)
        conn.commit()
        _log.info(f"Database initialized at {_db_path}")
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# CORE CRUD
# ═══════════════════════════════════════════════════════════════

def save_blob(
    save_type: str,
    save_key: str,
    data: dict,
    label: str = "",
    user_id: str = "default",
):
    """Upsert a JSON blob. Overwrites if the (user_id, save_type, save_key) already exists."""
    now = time.time()
    blob = json.dumps(data, default=str)
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO saves (user_id, save_type, save_key, label, data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, save_type, save_key)
            DO UPDATE SET data=excluded.data, label=excluded.label, updated_at=excluded.updated_at
            """,
            (user_id, save_type, save_key, label, blob, now, now),
        )
        conn.commit()
        _log.debug(f"Saved {save_type}/{save_key} for user={user_id} ({len(blob)} bytes)")
    finally:
        conn.close()


def load_blob(
    save_type: str,
    save_key: str,
    user_id: str = "default",
) -> Optional[dict]:
    """Load a JSON blob. Returns None if not found."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT data FROM saves WHERE user_id=? AND save_type=? AND save_key=?",
            (user_id, save_type, save_key),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["data"])
    finally:
        conn.close()


def delete_blob(
    save_type: str,
    save_key: str,
    user_id: str = "default",
):
    """Delete a saved blob."""
    conn = _connect()
    try:
        conn.execute(
            "DELETE FROM saves WHERE user_id=? AND save_type=? AND save_key=?",
            (user_id, save_type, save_key),
        )
        conn.commit()
    finally:
        conn.close()


def list_saves(
    save_type: str | None = None,
    user_id: str = "default",
) -> list[dict]:
    """List saved blobs (without loading full data). Returns metadata dicts."""
    conn = _connect()
    try:
        if save_type:
            rows = conn.execute(
                """
                SELECT save_type, save_key, label, created_at, updated_at,
                       length(data) as data_size
                FROM saves WHERE user_id=? AND save_type=?
                ORDER BY updated_at DESC
                """,
                (user_id, save_type),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT save_type, save_key, label, created_at, updated_at,
                       length(data) as data_size
                FROM saves WHERE user_id=?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_all_for_user(user_id: str = "default"):
    """Delete all saves for a user."""
    conn = _connect()
    try:
        conn.execute("DELETE FROM saves WHERE user_id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# PRO LEAGUE SERIALIZATION
# ═══════════════════════════════════════════════════════════════

def serialize_pro_league_season(season) -> dict:
    """Serialize a ProLeagueSeason to a JSON-safe dict.

    Captures the full state needed to reconstruct the season:
    config, standings, schedule, results, player stats, playoffs.
    """
    from engine.pro_league import ProTeamRecord, Matchup

    config = season.config
    config_data = {
        "league_id": config.league_id,
        "league_name": config.league_name,
        "teams_dir": config.teams_dir,
        "divisions": config.divisions,
        "games_per_season": config.games_per_season,
        "playoff_teams": config.playoff_teams,
        "bye_count": config.bye_count,
        "calendar_start": config.calendar_start,
        "calendar_end": config.calendar_end,
        "attribute_range": list(config.attribute_range),
        "franchise_rating_range": list(config.franchise_rating_range),
        "name_pool": config.name_pool,
    }

    standings_data = {}
    for key, rec in season.standings.items():
        standings_data[key] = {
            "team_key": rec.team_key,
            "team_name": rec.team_name,
            "division": rec.division,
            "wins": rec.wins,
            "losses": rec.losses,
            "points_for": rec.points_for,
            "points_against": rec.points_against,
            "div_wins": rec.div_wins,
            "div_losses": rec.div_losses,
            "streak": rec.streak,
            "streak_type": rec.streak_type,
            "last_5": rec.last_5,
        }

    schedule_data = []
    for week_matchups in season.schedule:
        week = []
        for m in week_matchups:
            week.append({
                "home_key": m.home_key,
                "away_key": m.away_key,
                "week": m.week,
                "matchup_key": m.matchup_key,
            })
        schedule_data.append(week)

    # Results: strip the heavy "result" sub-dict (full game sim data) to
    # keep blob size manageable. We store scores, weather, names.
    results_data = {}
    for week_num, week_results in season.results.items():
        week_dict = {}
        for mk, game in week_results.items():
            week_dict[mk] = {
                "matchup_key": game["matchup_key"],
                "home_key": game["home_key"],
                "away_key": game["away_key"],
                "home_name": game["home_name"],
                "away_name": game["away_name"],
                "home_score": game["home_score"],
                "away_score": game["away_score"],
                "weather": game["weather"],
                # Include result for box scores and DQ bet resolution
                "result": _slim_game_result(game.get("result", {})),
            }
        results_data[str(week_num)] = week_dict

    playoff_data = []
    for rd in season.playoff_bracket:
        matchups = []
        for m in rd["matchups"]:
            m_data = {
                "home": m["home"],
                "away": m["away"],
                "round": m["round"],
            }
            if m["result"]:
                m_data["result"] = {
                    "home_score": m["result"]["home_score"],
                    "away_score": m["result"]["away_score"],
                    "winner": m["result"]["winner"],
                    "winner_name": m["result"]["winner_name"],
                }
            else:
                m_data["result"] = None
            matchups.append(m_data)
        playoff_data.append({
            "round_name": rd["round_name"],
            "matchups": matchups,
            "bye_teams": rd.get("bye_teams", []),
            "completed": rd["completed"],
        })

    return {
        "version": 1,
        "config": config_data,
        "standings": standings_data,
        "schedule": schedule_data,
        "results": results_data,
        "player_season_stats": season.player_season_stats,
        "current_week": season.current_week,
        "total_weeks": season.total_weeks,
        "phase": season.phase,
        "playoff_bracket": playoff_data,
        "playoff_round": season.playoff_round,
        "champion": season.champion,
    }


def _slim_game_result(result: dict) -> dict:
    """Strip a full game result to just scores, stats, and player stats.

    Removes play-by-play, drive logs, narrative text — keeps what's needed
    for box scores and DQ resolution.
    """
    if not result:
        return {}
    slim = {}
    if "final_score" in result:
        slim["final_score"] = result["final_score"]
    if "stats" in result:
        slim["stats"] = result["stats"]
    if "player_stats" in result:
        slim["player_stats"] = result["player_stats"]
    return slim


def deserialize_pro_league_season(data: dict):
    """Reconstruct a ProLeagueSeason from a serialized dict."""
    from engine.pro_league import (
        ProLeagueSeason, ProLeagueConfig, ProTeamRecord, Matchup,
    )
    from engine.game_engine import load_team_from_json
    from pathlib import Path as _Path

    cfg_data = data["config"]
    config = ProLeagueConfig(
        league_id=cfg_data["league_id"],
        league_name=cfg_data["league_name"],
        teams_dir=cfg_data["teams_dir"],
        divisions=cfg_data["divisions"],
        games_per_season=cfg_data["games_per_season"],
        playoff_teams=cfg_data["playoff_teams"],
        bye_count=cfg_data["bye_count"],
        calendar_start=cfg_data["calendar_start"],
        calendar_end=cfg_data["calendar_end"],
        attribute_range=tuple(cfg_data["attribute_range"]),
        franchise_rating_range=tuple(cfg_data["franchise_rating_range"]),
        name_pool=cfg_data.get("name_pool", "male_english"),
    )

    # Build without __init__ to avoid re-loading teams and regenerating schedule
    season = ProLeagueSeason.__new__(ProLeagueSeason)
    season.config = config

    # Reload teams from JSON files (teams are stateless configs, always fresh from disk)
    season.teams = {}
    if config.teams_dir:
        from engine.pro_league import DATA_DIR
        teams_path = DATA_DIR.parent / config.teams_dir
        for div_name, team_keys in config.divisions.items():
            for key in team_keys:
                filepath = teams_path / f"{key}.json"
                if filepath.exists():
                    season.teams[key] = load_team_from_json(str(filepath))

    # Restore standings
    season.standings = {}
    for key, rec_data in data["standings"].items():
        rec = ProTeamRecord(
            team_key=rec_data["team_key"],
            team_name=rec_data["team_name"],
            division=rec_data["division"],
            wins=rec_data["wins"],
            losses=rec_data["losses"],
            points_for=rec_data["points_for"],
            points_against=rec_data["points_against"],
            div_wins=rec_data["div_wins"],
            div_losses=rec_data["div_losses"],
            streak=rec_data["streak"],
            streak_type=rec_data["streak_type"],
            last_5=rec_data["last_5"],
        )
        season.standings[key] = rec

    # Restore schedule
    season.schedule = []
    for week_data in data["schedule"]:
        week = []
        for m_data in week_data:
            week.append(Matchup(
                home_key=m_data["home_key"],
                away_key=m_data["away_key"],
                week=m_data["week"],
                matchup_key=m_data["matchup_key"],
            ))
        season.schedule.append(week)

    # Restore results (convert string keys back to ints)
    season.results = {}
    for week_str, week_results in data.get("results", {}).items():
        season.results[int(week_str)] = week_results

    season.player_season_stats = data.get("player_season_stats", {})
    season.current_week = data["current_week"]
    season.total_weeks = data["total_weeks"]
    season.phase = data["phase"]
    season.playoff_round = data.get("playoff_round", 0)
    season.champion = data.get("champion")

    # Restore playoff bracket
    season.playoff_bracket = data.get("playoff_bracket", [])

    return season


# ═══════════════════════════════════════════════════════════════
# DRAFTYQUEENZ SERIALIZATION
# ═══════════════════════════════════════════════════════════════

def serialize_dq_manager(dq) -> dict:
    """Serialize a DraftyQueenzManager to a JSON-safe dict."""
    from engine.draftyqueenz import Pick, Parlay, WeeklyContest

    contests_data = {}
    for week, contest in dq.weekly_contests.items():
        picks = []
        for p in contest.picks:
            picks.append({
                "pick_type": p.pick_type,
                "game_home": p.game_home,
                "game_away": p.game_away,
                "selection": p.selection,
                "amount": p.amount,
                "odds_snapshot": p.odds_snapshot,
                "payout": p.payout,
                "result": p.result,
            })
        parlays = []
        for pl in contest.parlays:
            legs = [{
                "pick_type": leg.pick_type,
                "game_home": leg.game_home,
                "game_away": leg.game_away,
                "selection": leg.selection,
                "amount": leg.amount,
                "odds_snapshot": leg.odds_snapshot,
                "payout": leg.payout,
                "result": leg.result,
            } for leg in pl.legs]
            parlays.append({
                "legs": legs,
                "amount": pl.amount,
                "multiplier": pl.multiplier,
                "payout": pl.payout,
                "result": pl.result,
            })

        odds_data = []
        for o in contest.odds:
            odds_data.append(o.to_dict())

        contests_data[str(week)] = {
            "week": contest.week,
            "picks": picks,
            "parlays": parlays,
            "odds": odds_data,
            "resolved": contest.resolved,
            "jackpot_bonus": contest.jackpot_bonus,
        }

    donations_data = [d.to_dict() for d in dq.donations]

    return {
        "version": 1,
        "manager_name": dq.manager_name,
        "bankroll": dq.bankroll.to_dict(),
        "weekly_contests": contests_data,
        "donations": donations_data,
        "season_year": dq.season_year,
        "total_picks_made": dq.total_picks_made,
        "total_picks_won": dq.total_picks_won,
        "total_parlays_made": dq.total_parlays_made,
        "total_parlays_won": dq.total_parlays_won,
        "total_fantasy_entries": dq.total_fantasy_entries,
        "total_fantasy_top3": dq.total_fantasy_top3,
        "total_jackpots": dq.total_jackpots,
        "career_donated": dq.career_donated,
        "peak_bankroll": dq.peak_bankroll,
    }


def deserialize_dq_manager(data: dict):
    """Reconstruct a DraftyQueenzManager from a serialized dict."""
    from engine.draftyqueenz import (
        DraftyQueenzManager, Bankroll, WeeklyContest, Pick, Parlay,
        GameOdds, BoosterDonation, STARTING_BANKROLL,
    )

    dq = DraftyQueenzManager.__new__(DraftyQueenzManager)
    dq.manager_name = data.get("manager_name", "Coach")

    # Restore bankroll
    br_data = data.get("bankroll", {})
    dq.bankroll = Bankroll(
        balance=br_data.get("balance", STARTING_BANKROLL),
        history=br_data.get("history", []),
    )

    # Restore weekly contests
    dq.weekly_contests = {}
    for week_str, c_data in data.get("weekly_contests", {}).items():
        contest = WeeklyContest(week=c_data["week"])

        # Restore picks
        contest.picks = []
        for p_data in c_data.get("picks", []):
            contest.picks.append(Pick(
                pick_type=p_data["pick_type"],
                game_home=p_data["game_home"],
                game_away=p_data["game_away"],
                selection=p_data["selection"],
                amount=p_data["amount"],
                odds_snapshot=p_data.get("odds_snapshot", {}),
                payout=p_data.get("payout", 0.0),
                result=p_data.get("result", ""),
            ))

        # Restore parlays
        contest.parlays = []
        for pl_data in c_data.get("parlays", []):
            legs = [Pick(
                pick_type=leg["pick_type"],
                game_home=leg["game_home"],
                game_away=leg["game_away"],
                selection=leg["selection"],
                amount=leg["amount"],
                odds_snapshot=leg.get("odds_snapshot", {}),
                payout=leg.get("payout", 0.0),
                result=leg.get("result", ""),
            ) for leg in pl_data.get("legs", [])]
            contest.parlays.append(Parlay(
                legs=legs,
                amount=pl_data["amount"],
                multiplier=pl_data["multiplier"],
                payout=pl_data.get("payout", 0.0),
                result=pl_data.get("result", ""),
            ))

        # Restore odds
        contest.odds = []
        for o_data in c_data.get("odds", []):
            contest.odds.append(GameOdds(
                home_team=o_data["home_team"],
                away_team=o_data["away_team"],
                home_win_prob=o_data["home_win_prob"],
                spread=o_data["spread"],
                over_under=o_data["over_under"],
                home_moneyline=o_data["home_moneyline"],
                away_moneyline=o_data["away_moneyline"],
                chaos_ou=o_data.get("chaos_ou", 40.0),
                kick_pass_ou=o_data.get("kick_pass_ou", 14.5),
            ))

        contest.resolved = c_data.get("resolved", False)
        contest.jackpot_bonus = c_data.get("jackpot_bonus", 0)

        # Restore remaining contest fields with safe defaults
        contest.player_pool = []
        contest.ai_rosters = []
        contest.user_roster = None

        dq.weekly_contests[int(week_str)] = contest

    # Restore donations
    dq.donations = []
    for d_data in data.get("donations", []):
        dq.donations.append(BoosterDonation(
            donation_type=d_data.get("type", d_data.get("donation_type", "")),
            amount=d_data.get("amount", 0),
            boost_value=d_data.get("boost_value", 0.0),
            week=d_data.get("week", 0),
            target_team=d_data.get("target_team", ""),
        ))

    # Restore cumulative stats
    dq.season_year = data.get("season_year", 1)
    dq.total_picks_made = data.get("total_picks_made", 0)
    dq.total_picks_won = data.get("total_picks_won", 0)
    dq.total_parlays_made = data.get("total_parlays_made", 0)
    dq.total_parlays_won = data.get("total_parlays_won", 0)
    dq.total_fantasy_entries = data.get("total_fantasy_entries", 0)
    dq.total_fantasy_top3 = data.get("total_fantasy_top3", 0)
    dq.total_jackpots = data.get("total_jackpots", 0)
    dq.career_donated = data.get("career_donated", 0)
    dq.peak_bankroll = data.get("peak_bankroll", STARTING_BANKROLL)

    return dq


# ═══════════════════════════════════════════════════════════════
# HIGH-LEVEL SAVE/LOAD FOR PRO LEAGUES
# ═══════════════════════════════════════════════════════════════

def save_pro_league(league_id: str, session_id: str, season, dq_manager,
                    user_id: str = "default"):
    """Save a pro league season and its DQ manager to the database."""
    season_data = serialize_pro_league_season(season)
    save_blob("pro_league", f"{league_id}_{session_id}", season_data,
              label=season.config.league_name, user_id=user_id)

    dq_data = serialize_dq_manager(dq_manager)
    save_blob("dq_manager", f"{league_id}_{session_id}", dq_data,
              label=f"{season.config.league_name} DQ", user_id=user_id)

    _log.info(f"Saved pro league {league_id} (session={session_id}) for user={user_id}")


def load_pro_league(league_id: str, session_id: str,
                    user_id: str = "default") -> tuple:
    """Load a pro league season and DQ manager. Returns (season, dq_manager) or (None, None)."""
    season_data = load_blob("pro_league", f"{league_id}_{session_id}", user_id=user_id)
    if season_data is None:
        return None, None

    season = deserialize_pro_league_season(season_data)

    dq_data = load_blob("dq_manager", f"{league_id}_{session_id}", user_id=user_id)
    if dq_data:
        dq_manager = deserialize_dq_manager(dq_data)
    else:
        from engine.draftyqueenz import DraftyQueenzManager
        dq_manager = DraftyQueenzManager(manager_name=f"{season.config.league_name} Bettor")

    return season, dq_manager


def list_pro_league_saves(user_id: str = "default") -> list[dict]:
    """List all saved pro league sessions for a user."""
    return list_saves("pro_league", user_id=user_id)


def delete_pro_league_save(league_id: str, session_id: str,
                           user_id: str = "default"):
    """Delete a saved pro league session and its DQ manager."""
    key = f"{league_id}_{session_id}"
    delete_blob("pro_league", key, user_id=user_id)
    delete_blob("dq_manager", key, user_id=user_id)


# ═══════════════════════════════════════════════════════════════
# LEAGUE ARCHIVE (for Champions League qualifiers)
# ═══════════════════════════════════════════════════════════════

def save_league_archive(league_id: str, snapshot: dict, user_id: str = "default"):
    """Save a completed league's champion/qualifier data for Champions League."""
    save_blob("league_archive", league_id, snapshot,
              label=snapshot.get("league_name", league_id), user_id=user_id)


def load_all_league_archives(user_id: str = "default") -> dict[str, dict]:
    """Load all league archives for Champions League qualification."""
    saves = list_saves("league_archive", user_id=user_id)
    archives = {}
    for save_info in saves:
        data = load_blob("league_archive", save_info["save_key"], user_id=user_id)
        if data:
            archives[save_info["save_key"]] = data
    return archives


# ═══════════════════════════════════════════════════════════════
# AUTO-INITIALIZE on import
# ═══════════════════════════════════════════════════════════════

try:
    init_db()
except Exception as e:
    _log.warning(f"Failed to initialize database on import: {e}")
