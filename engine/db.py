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

            CREATE TABLE IF NOT EXISTS save_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT    NOT NULL DEFAULT 'default',
                save_type   TEXT    NOT NULL,
                save_key    TEXT    NOT NULL,
                label       TEXT    NOT NULL DEFAULT '',
                data        TEXT    NOT NULL,
                saved_at    REAL    NOT NULL,
                superseded_at REAL  NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_history_lookup
                ON save_history(user_id, save_type, save_key, superseded_at DESC);
        """)
        conn.commit()
        _log.info(f"Database initialized at {_db_path}")
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# CORE CRUD
# ═══════════════════════════════════════════════════════════════

# Save types that should NOT generate history (high-volume, low-value)
_NO_HISTORY_TYPES = frozenset({"box_score", "season_archive_meta"})


def save_blob(
    save_type: str,
    save_key: str,
    data: dict,
    label: str = "",
    user_id: str = "default",
):
    """Upsert a JSON blob. Snapshots the old version to save_history before overwriting."""
    now = time.time()
    blob = json.dumps(data, default=str)
    conn = _connect()
    try:
        # Snapshot the existing row into save_history before overwriting
        # (skip for high-volume types like box scores)
        if save_type not in _NO_HISTORY_TYPES:
            conn.execute(
                """
                INSERT INTO save_history (user_id, save_type, save_key, label, data, saved_at, superseded_at)
                SELECT user_id, save_type, save_key, label, data, created_at, ?
                FROM saves
                WHERE user_id=? AND save_type=? AND save_key=?
                """,
                (now, user_id, save_type, save_key),
            )
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
# SAVE HISTORY — browse and restore previous versions
# ═══════════════════════════════════════════════════════════════

def list_save_history(
    save_type: str,
    save_key: str,
    user_id: str = "default",
    limit: int = 50,
) -> list[dict]:
    """List previous versions of a save (metadata only, newest first)."""
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT id, save_type, save_key, label, saved_at, superseded_at,
                   length(data) as data_size
            FROM save_history
            WHERE user_id=? AND save_type=? AND save_key=?
            ORDER BY superseded_at DESC
            LIMIT ?
            """,
            (user_id, save_type, save_key, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def load_save_history_entry(history_id: int) -> Optional[dict]:
    """Load a specific historical save by its history row id."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT data FROM save_history WHERE id=?",
            (history_id,),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["data"])
    finally:
        conn.close()


def restore_save_from_history(history_id: int) -> bool:
    """Restore a historical version as the current save.

    The current save is first snapshotted to history (via save_blob),
    then replaced with the historical data.
    Returns True on success, False if history_id not found.
    """
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT user_id, save_type, save_key, label, data FROM save_history WHERE id=?",
            (history_id,),
        ).fetchone()
        if row is None:
            return False
        data = json.loads(row["data"])
    finally:
        conn.close()
    # save_blob will snapshot the current version before overwriting
    save_blob(row["save_type"], row["save_key"], data,
              label=row["label"], user_id=row["user_id"])
    _log.info(f"Restored history id={history_id} as current {row['save_type']}/{row['save_key']}")
    return True


def list_all_save_history(
    user_id: str = "default",
    save_type: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """List all historical saves for a user, optionally filtered by type."""
    conn = _connect()
    try:
        if save_type:
            rows = conn.execute(
                """
                SELECT id, save_type, save_key, label, saved_at, superseded_at,
                       length(data) as data_size
                FROM save_history
                WHERE user_id=? AND save_type=?
                ORDER BY superseded_at DESC
                LIMIT ?
                """,
                (user_id, save_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, save_type, save_key, label, saved_at, superseded_at,
                       length(data) as data_size
                FROM save_history
                WHERE user_id=?
                ORDER BY superseded_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def prune_save_history(
    keep_per_key: int = 20,
    user_id: str = "default",
):
    """Delete old history entries, keeping the most recent `keep_per_key` per (save_type, save_key).

    Prevents unbounded history growth.
    """
    conn = _connect()
    try:
        # Find distinct (save_type, save_key) combos
        combos = conn.execute(
            "SELECT DISTINCT save_type, save_key FROM save_history WHERE user_id=?",
            (user_id,),
        ).fetchall()
        total_deleted = 0
        for combo in combos:
            # Keep the newest `keep_per_key` rows, delete the rest
            deleted = conn.execute(
                """
                DELETE FROM save_history
                WHERE user_id=? AND save_type=? AND save_key=?
                  AND id NOT IN (
                    SELECT id FROM save_history
                    WHERE user_id=? AND save_type=? AND save_key=?
                    ORDER BY superseded_at DESC
                    LIMIT ?
                  )
                """,
                (user_id, combo["save_type"], combo["save_key"],
                 user_id, combo["save_type"], combo["save_key"],
                 keep_per_key),
            ).rowcount
            total_deleted += deleted
        conn.commit()
        if total_deleted:
            _log.info(f"Pruned {total_deleted} old history entries for user={user_id}")
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# CVL → WVL BRIDGE
# ═══════════════════════════════════════════════════════════════

_BRIDGE_TYPE = "cvl_wvl_bridge"


def save_graduating_pool(
    dynasty_name: str,
    player_cards: list,
    year: int,
    user_id: str = "default",
) -> str:
    """Write CVL graduates to bridge table for automatic WVL import.

    Args:
        dynasty_name: Name of the source CVL dynasty.
        player_cards: List of PlayerCard.to_dict() dicts.
        year: Dynasty calendar year the class graduated.
        user_id: User who owns the dynasty.

    Returns:
        The save_key used (for later consumption/deletion).
    """
    save_key = f"{dynasty_name}_graduates_{year}"
    save_blob(
        _BRIDGE_TYPE,
        save_key,
        {
            "source_dynasty": dynasty_name,
            "source_year": year,
            "player_count": len(player_cards),
            "players": player_cards,
            "consumed": False,
        },
        label=f"CVL graduates {dynasty_name} Y{year}",
        user_id=user_id,
    )
    _log.info(f"Bridge: published {len(player_cards)} graduates from {dynasty_name} Y{year}")
    return save_key


def load_graduating_pools(
    user_id: str = "default",
    dynasty_name: str | None = None,
    unconsumed_only: bool = True,
) -> list[dict]:
    """Read available CVL graduate pools from the bridge.

    Args:
        user_id: User who owns the dynasty.
        dynasty_name: Optional filter by source dynasty name.
        unconsumed_only: If True, only return pools not yet imported by WVL.

    Returns:
        List of dicts with keys: save_key, source_dynasty, source_year,
        player_count, players, consumed.  Sorted oldest-first.
    """
    metas = list_saves(save_type=_BRIDGE_TYPE, user_id=user_id)
    result = []
    for meta in reversed(metas):  # oldest first
        data = load_blob(_BRIDGE_TYPE, meta["save_key"], user_id=user_id)
        if data is None:
            continue
        if dynasty_name and data.get("source_dynasty") != dynasty_name:
            continue
        if unconsumed_only and data.get("consumed", False):
            continue
        data["save_key"] = meta["save_key"]
        result.append(data)
    return result


def consume_graduating_pool(
    save_key: str,
    user_id: str = "default",
) -> bool:
    """Mark a graduate pool as consumed by WVL import.

    Does NOT delete the data — it remains available for re-import if needed.
    Sets consumed=True so it won't appear in unconsumed_only queries.

    Returns True if the pool was found and marked.
    """
    data = load_blob(_BRIDGE_TYPE, save_key, user_id=user_id)
    if data is None:
        return False
    data["consumed"] = True
    save_blob(
        _BRIDGE_TYPE,
        save_key,
        data,
        label=data.get("label", ""),
        user_id=user_id,
    )
    _log.info(f"Bridge: consumed pool {save_key}")
    return True


def save_hs_pipeline(
    dynasty_name: str,
    pipeline_data: dict,
    user_id: str = "default",
) -> str:
    """Write HS recruiting pipeline to bridge for WVL preview access.

    Args:
        dynasty_name: Name of the source CVL dynasty.
        pipeline_data: HSRecruitingPipeline.to_dict() output.
        user_id: User who owns the dynasty.

    Returns:
        The save_key used.
    """
    save_key = f"{dynasty_name}_hs_pipeline"
    save_blob(
        _BRIDGE_TYPE,
        save_key,
        {
            "source_dynasty": dynasty_name,
            "type": "hs_pipeline",
            "pipeline": pipeline_data,
        },
        label=f"HS Pipeline {dynasty_name}",
        user_id=user_id,
    )
    return save_key


def load_hs_pipeline(
    user_id: str = "default",
    dynasty_name: str | None = None,
) -> dict | None:
    """Load the most recent HS pipeline data from the bridge.

    Returns the pipeline dict, or None if not found.
    """
    metas = list_saves(save_type=_BRIDGE_TYPE, user_id=user_id)
    for meta in metas:  # newest first (sorted by updated_at DESC)
        if "_hs_pipeline" not in meta["save_key"]:
            continue
        if dynasty_name and dynasty_name not in meta["save_key"]:
            continue
        data = load_blob(_BRIDGE_TYPE, meta["save_key"], user_id=user_id)
        if data and data.get("type") == "hs_pipeline":
            return data.get("pipeline")
    return None


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
            "ties": rec.ties,
            "points_for": rec.points_for,
            "points_against": rec.points_against,
            "div_wins": rec.div_wins,
            "div_losses": rec.div_losses,
            "div_ties": rec.div_ties,
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
            ties=rec_data.get("ties", 0),
            points_for=rec_data["points_for"],
            points_against=rec_data["points_against"],
            div_wins=rec_data["div_wins"],
            div_losses=rec_data["div_losses"],
            div_ties=rec_data.get("div_ties", 0),
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
# SEASON ARCHIVE (persisted snapshots of completed seasons)
# ═══════════════════════════════════════════════════════════════

def save_season_archive(archive_key: str, snapshot: dict, user_id: str = "default"):
    """Save a completed season snapshot (college or FIV) to the database.

    Also saves a lightweight summary blob (season_archive_meta) so the
    archive index page can display champion / team-count / games-played
    without loading the full 50+ MB snapshot.
    """
    save_blob("season_archive", archive_key, snapshot,
              label=snapshot.get("label", archive_key), user_id=user_id)
    # Save lightweight summary for fast listing
    meta = {
        "type": snapshot.get("type", "college"),
        "label": snapshot.get("label", archive_key),
        "champion": snapshot.get("champion"),
        "team_count": snapshot.get("team_count", 0),
        "games_played": snapshot.get("games_played", 0),
        "total_games": snapshot.get("total_games", 0),
    }
    save_blob("season_archive_meta", archive_key, meta,
              label=snapshot.get("label", archive_key), user_id=user_id)
    _log.info(f"Saved season archive '{archive_key}' for user={user_id}")


def load_season_archive(archive_key: str, user_id: str = "default") -> Optional[dict]:
    """Load a season archive snapshot."""
    return load_blob("season_archive", archive_key, user_id=user_id)


def load_season_archive_meta(archive_key: str, user_id: str = "default") -> Optional[dict]:
    """Load lightweight archive summary (champion, team_count, etc.)."""
    return load_blob("season_archive_meta", archive_key, user_id=user_id)


def list_season_archives(user_id: str = "default") -> list[dict]:
    """List all season archives (metadata only, no full data)."""
    return list_saves("season_archive", user_id=user_id)


def delete_season_archive(archive_key: str, user_id: str = "default"):
    """Delete a season archive."""
    delete_blob("season_archive", archive_key, user_id=user_id)
    delete_blob("season_archive_meta", archive_key, user_id=user_id)


# ═══════════════════════════════════════════════════════════════
# WVL MULTI-TIER SEASON SERIALIZATION
# ═══════════════════════════════════════════════════════════════

def serialize_wvl_season(wvl_season) -> dict:
    """Serialize a WVLMultiTierSeason to a JSON-safe dict.

    Reuses serialize_pro_league_season for each tier's ProLeagueSeason,
    plus WVL-specific fields (tier_assignments, phase, promotion_result).
    """
    tier_data = {}
    for tier_num, season in wvl_season.tier_seasons.items():
        tier_data[str(tier_num)] = serialize_pro_league_season(season)
        # Also serialize the injury tracker if present
        if getattr(season, 'injury_tracker', None) is not None:
            tracker = season.injury_tracker
            tier_data[str(tier_num)]["injury_tracker"] = _serialize_injury_tracker(tracker)

    result = {
        "version": 1,
        "tier_assignments": {k: v for k, v in wvl_season.tier_assignments.items()},
        "tier_seasons": tier_data,
        "phase": wvl_season.phase,
        "current_week": wvl_season.current_week,
    }

    if wvl_season.promotion_result is not None:
        result["promotion_result"] = wvl_season.promotion_result.to_dict()

    return result


def _serialize_injury_tracker(tracker) -> dict:
    """Serialize an InjuryTracker to a JSON-safe dict."""
    active = {}
    for team_name, injuries in tracker.active_injuries.items():
        active[team_name] = [inj.to_dict() for inj in injuries]
    season_log = [inj.to_dict() for inj in tracker.season_log]
    return {"active_injuries": active, "season_log": season_log}


def _deserialize_injury_tracker(data: dict):
    """Reconstruct an InjuryTracker from a serialized dict."""
    from engine.injuries import InjuryTracker, Injury
    import random

    tracker = InjuryTracker()
    tracker.rng = random.Random()

    for team_name, inj_list in data.get("active_injuries", {}).items():
        tracker.active_injuries[team_name] = [
            Injury(**{k: v for k, v in d.items() if k in Injury.__dataclass_fields__})
            for d in inj_list
        ]
    tracker.season_log = [
        Injury(**{k: v for k, v in d.items() if k in Injury.__dataclass_fields__})
        for d in data.get("season_log", [])
    ]
    return tracker


def deserialize_wvl_season(data: dict):
    """Reconstruct a WVLMultiTierSeason from a serialized dict."""
    from engine.wvl_season import WVLMultiTierSeason
    from engine.promotion_relegation import (
        PromotionRelegationResult, TierMovement, PromotionPlayoff,
    )

    # Build without __init__ to avoid re-loading all teams
    wvl = WVLMultiTierSeason.__new__(WVLMultiTierSeason)
    wvl.tier_assignments = data["tier_assignments"]
    wvl.phase = data.get("phase", "regular_season")
    wvl.current_week = data.get("current_week", 0)

    # Deserialize each tier's ProLeagueSeason
    wvl.tier_seasons = {}
    for tier_str, season_data in data.get("tier_seasons", {}).items():
        tier_num = int(tier_str)
        season = deserialize_pro_league_season(season_data)

        # Restore injury tracker if present
        if "injury_tracker" in season_data:
            season.injury_tracker = _deserialize_injury_tracker(season_data["injury_tracker"])
        else:
            season.injury_tracker = None

        # For WVL tiers, teams may span multiple directories. If deserialization
        # didn't find all teams (teams_dir only covers one tier), scan all dirs.
        if not season.teams:
            from engine.wvl_config import ALL_WVL_TIERS
            from engine.game_engine import load_team_from_json
            from engine.wvl_season import DATA_DIR
            all_wvl_teams = {}
            for tc in ALL_WVL_TIERS:
                td = DATA_DIR.parent / tc.teams_dir
                if td.exists():
                    for f in sorted(td.glob("*.json")):
                        key = f.stem
                        if key not in all_wvl_teams:
                            try:
                                all_wvl_teams[key] = load_team_from_json(str(f))
                            except Exception:
                                pass
            for div_keys in season.config.divisions.values():
                for key in div_keys:
                    if key in all_wvl_teams:
                        season.teams[key] = all_wvl_teams[key]

        wvl.tier_seasons[tier_num] = season

    # Restore promotion result if present
    prom_data = data.get("promotion_result")
    if prom_data:
        movements = [
            TierMovement(
                team_key=m["team_key"],
                team_name=m["team_name"],
                from_tier=m["from_tier"],
                to_tier=m["to_tier"],
                reason=m["reason"],
            )
            for m in prom_data.get("movements", [])
        ]
        playoffs = [
            PromotionPlayoff(
                higher_tier=p["higher_tier"],
                higher_tier_team_key=p.get("higher_tier_team", ""),
                higher_tier_team_name=p.get("higher_tier_team_name", ""),
                lower_tier_team_key=p.get("lower_tier_team", ""),
                lower_tier_team_name=p.get("lower_tier_team_name", ""),
                winner_key=p.get("winner"),
                winner_name=p.get("winner_name"),
                score=p.get("score"),
            )
            for p in prom_data.get("playoffs", [])
        ]
        wvl.promotion_result = PromotionRelegationResult(
            movements=movements,
            playoffs=playoffs,
            new_tier_assignments=prom_data.get("new_tier_assignments", {}),
        )
    else:
        wvl.promotion_result = None

    return wvl


# ═══════════════════════════════════════════════════════════════
# HIGH-LEVEL SAVE/LOAD FOR WVL
# ═══════════════════════════════════════════════════════════════

def save_wvl_season(wvl_season, user_id: str = "default"):
    """Save a WVL multi-tier season to the database."""
    data = serialize_wvl_season(wvl_season)
    save_blob("wvl_season", "current", data, label="WVL Season", user_id=user_id)
    _log.info(f"Saved WVL season for user={user_id}")


def load_wvl_season(user_id: str = "default"):
    """Load a WVL multi-tier season. Returns the season or None."""
    data = load_blob("wvl_season", "current", user_id=user_id)
    if data is None:
        return None
    try:
        return deserialize_wvl_season(data)
    except Exception as e:
        _log.warning(f"Failed to deserialize WVL season: {e}")
        return None


def delete_wvl_season(user_id: str = "default"):
    """Delete a saved WVL season."""
    delete_blob("wvl_season", "current", user_id=user_id)


# ═══════════════════════════════════════════════════════════════
# DYNASTY SERIALIZATION
# ═══════════════════════════════════════════════════════════════

def serialize_dynasty(dynasty) -> dict:
    """Serialize a Dynasty to a JSON-safe dict for database storage.

    Follows the same pattern as Dynasty.save() but captures additional
    fields (prestige, histories, rivalries) that the file-based save skips.
    Does NOT serialize Season objects (too large) — only metadata/summaries.
    """
    from dataclasses import asdict

    data = {
        "dynasty_name": dynasty.dynasty_name,
        "coach": asdict(dynasty.coach),
        "current_year": dynasty.current_year,
        "conferences": {name: asdict(conf) for name, conf in dynasty.conferences.items()},
        "team_histories": {name: asdict(h) for name, h in dynasty.team_histories.items()},
        "awards_history": {str(year): asdict(a) for year, a in dynasty.awards_history.items()},
        "record_book": asdict(dynasty.record_book),
        "team_prestige": dict(dynasty.team_prestige) if dynasty.team_prestige else {},
        "games_per_team": dynasty.games_per_team,
        "playoff_size": dynasty.playoff_size,
        "bowl_count": dynasty.bowl_count,
        "rivalries": dynasty.rivalries if dynasty.rivalries else {},
        "rivalry_ledger": dynasty.rivalry_ledger if dynasty.rivalry_ledger else {},
        "player_stats": {
            name: asdict(ps) for name, ps in dynasty.player_stats.items()
        } if dynasty.player_stats else {},
        "honors_history": {str(k): v for k, v in dynasty.honors_history.items()} if dynasty.honors_history else {},
        "injury_history": {str(k): v for k, v in dynasty.injury_history.items()} if dynasty.injury_history else {},
        "development_history": {str(k): v for k, v in dynasty.development_history.items()} if dynasty.development_history else {},
        "recruiting_history": {str(k): v for k, v in dynasty.recruiting_history.items()} if dynasty.recruiting_history else {},
        "portal_history": {str(k): v for k, v in dynasty.portal_history.items()} if dynasty.portal_history else {},
        "nil_history": {str(k): v for k, v in dynasty.nil_history.items()} if dynasty.nil_history else {},
        "coaching_history": {str(k): v for k, v in dynasty.coaching_history.items()} if dynasty.coaching_history else {},
    }

    # Coaching staffs — CoachCard objects need .to_dict()
    if dynasty._coaching_staffs:
        try:
            from engine.coaching import CoachCard
            staffs = {}
            for team_name, staff in dynasty._coaching_staffs.items():
                staffs[team_name] = {
                    role: (card.to_dict() if isinstance(card, CoachCard) else card)
                    for role, card in staff.items()
                }
            data["coaching_staffs"] = staffs
        except Exception:
            data["coaching_staffs"] = {}
    else:
        data["coaching_staffs"] = {}

    # Next-season rosters (persisted by offseason_complete for roster continuity)
    next_rosters = getattr(dynasty, '_next_season_rosters', None)
    if next_rosters:
        data["next_season_rosters"] = next_rosters

    return data


def deserialize_dynasty(data: dict):
    """Reconstruct a Dynasty from a serialized dict."""
    from engine.dynasty import Dynasty, Coach, Conference, TeamHistory, SeasonAwards, RecordBook, PlayerCareerStats

    dynasty = Dynasty(
        dynasty_name=data["dynasty_name"],
        coach=Coach(**data["coach"]),
        current_year=data["current_year"],
    )

    # Conferences
    for name, conf_data in data.get("conferences", {}).items():
        dynasty.conferences[name] = Conference(**conf_data)

    # Team histories
    for name, h_data in data.get("team_histories", {}).items():
        # Convert string year keys back to int in season_records
        if "season_records" in h_data:
            h_data["season_records"] = {int(k): v for k, v in h_data["season_records"].items()}
        dynasty.team_histories[name] = TeamHistory(**h_data)

    # Awards history
    for year_str, a_data in data.get("awards_history", {}).items():
        dynasty.awards_history[int(year_str)] = SeasonAwards(**a_data)

    # Record book
    if "record_book" in data:
        dynasty.record_book = RecordBook(**data["record_book"])

    # Simple dict fields
    dynasty.team_prestige = data.get("team_prestige", {})
    dynasty.games_per_team = data.get("games_per_team", 12)
    dynasty.playoff_size = data.get("playoff_size", 8)
    dynasty.bowl_count = data.get("bowl_count", 4)
    dynasty.rivalries = data.get("rivalries", {})
    dynasty.rivalry_ledger = data.get("rivalry_ledger", {})

    # Int-keyed history dicts
    dynasty.honors_history = {int(k): v for k, v in data.get("honors_history", {}).items()}
    dynasty.injury_history = {int(k): v for k, v in data.get("injury_history", {}).items()}
    dynasty.development_history = {int(k): v for k, v in data.get("development_history", {}).items()}
    dynasty.recruiting_history = {int(k): v for k, v in data.get("recruiting_history", {}).items()}
    dynasty.portal_history = {int(k): v for k, v in data.get("portal_history", {}).items()}
    dynasty.nil_history = {int(k): v for k, v in data.get("nil_history", {}).items()}
    dynasty.coaching_history = {int(k): v for k, v in data.get("coaching_history", {}).items()}

    # Player career stats
    for name, ps_data in data.get("player_stats", {}).items():
        dynasty.player_stats[name] = PlayerCareerStats(**ps_data)

    # Coaching staffs
    if data.get("coaching_staffs"):
        try:
            from engine.coaching import CoachCard
            for team_name, staff_data in data["coaching_staffs"].items():
                dynasty._coaching_staffs[team_name] = {
                    role: CoachCard.from_dict(card_data)
                    for role, card_data in staff_data.items()
                }
        except Exception:
            pass

    # Coach season_records int keys
    if dynasty.coach.season_records:
        dynasty.coach.season_records = {int(k): v for k, v in dynasty.coach.season_records.items()}

    # Conference championship_history int keys
    for conf in dynasty.conferences.values():
        if conf.championship_history:
            conf.championship_history = {int(k): v for k, v in conf.championship_history.items()}

    # Next-season rosters (roster continuity across seasons)
    next_rosters = data.get("next_season_rosters")
    if next_rosters:
        dynasty._next_season_rosters = next_rosters

    return dynasty


# ═══════════════════════════════════════════════════════════════
# HIGH-LEVEL SAVE/LOAD FOR DYNASTY
# ═══════════════════════════════════════════════════════════════

def save_dynasty(dynasty, save_key: str = "current", user_id: str = "default"):
    """Save a dynasty to the database."""
    data = serialize_dynasty(dynasty)
    save_blob("dynasty", save_key, data,
              label=dynasty.dynasty_name, user_id=user_id)
    _log.info(f"Saved dynasty '{dynasty.dynasty_name}' (key={save_key}) for user={user_id}")


def load_dynasty(save_key: str = "current", user_id: str = "default"):
    """Load a dynasty from the database. Returns the Dynasty or None."""
    data = load_blob("dynasty", save_key, user_id=user_id)
    if data is None:
        return None
    try:
        return deserialize_dynasty(data)
    except Exception as e:
        _log.warning(f"Failed to deserialize dynasty: {e}")
        return None


def list_dynasties(user_id: str = "default") -> list[dict]:
    """List saved dynasties (metadata only)."""
    return list_saves("dynasty", user_id=user_id)


def delete_dynasty(save_key: str, user_id: str = "default"):
    """Delete a saved dynasty."""
    delete_blob("dynasty", save_key, user_id=user_id)


# ═══════════════════════════════════════════════════════════════
# BOX SCORES — persist full game results for the stats site
# ═══════════════════════════════════════════════════════════════

_BOX_SCORE_TYPE = "box_score"


def _box_key(session_id: str, week: int, home_team: str, away_team: str) -> str:
    """Deterministic save_key for a single box score."""
    return f"{session_id}__w{week}__{away_team}_at_{home_team}"


def save_box_score(
    session_id: str,
    week: int,
    home_team: str,
    away_team: str,
    full_result: dict,
    user_id: str = "default",
):
    """Persist a single game's full_result to the database."""
    key = _box_key(session_id, week, home_team, away_team)
    label = f"W{week} {away_team} @ {home_team}"
    save_blob(_BOX_SCORE_TYPE, key, full_result, label=label, user_id=user_id)


def load_box_score(
    session_id: str,
    week: int,
    home_team: str,
    away_team: str,
    user_id: str = "default",
) -> Optional[dict]:
    """Load a single box score from the database. Returns None if not found."""
    key = _box_key(session_id, week, home_team, away_team)
    return load_blob(_BOX_SCORE_TYPE, key, user_id=user_id)


def delete_box_scores_for_session(session_id: str, user_id: str = "default"):
    """Delete all box scores belonging to a session."""
    conn = _connect()
    try:
        conn.execute(
            "DELETE FROM saves WHERE user_id=? AND save_type=? AND save_key LIKE ?",
            (user_id, _BOX_SCORE_TYPE, f"{session_id}__%"),
        )
        conn.commit()
    finally:
        conn.close()


def save_box_scores_bulk(
    session_id: str,
    games: list,
    user_id: str = "default",
):
    """Save box scores for a list of completed Game objects in one transaction."""
    now = time.time()
    conn = _connect()
    try:
        rows = []
        for game in games:
            fr = getattr(game, "full_result", None)
            if not fr or not getattr(game, "completed", False):
                continue
            key = _box_key(session_id, game.week, game.home_team, game.away_team)
            label = f"W{game.week} {game.away_team} @ {game.home_team}"
            blob = json.dumps(fr, default=str)
            rows.append((user_id, _BOX_SCORE_TYPE, key, label, blob, now, now))
        if rows:
            conn.executemany(
                """
                INSERT INTO saves (user_id, save_type, save_key, label, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, save_type, save_key)
                DO UPDATE SET data=excluded.data, label=excluded.label, updated_at=excluded.updated_at
                """,
                rows,
            )
            conn.commit()
            _log.debug(f"Bulk-saved {len(rows)} box scores for session {session_id}")
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# AUTO-INITIALIZE on import
# ═══════════════════════════════════════════════════════════════

try:
    init_db()
except Exception as e:
    _log.warning(f"Failed to initialize database on import: {e}")
