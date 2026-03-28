"""Pro Leagues session management — persistence, caching, multi-league state.

Extracted from pro_leagues.py to reduce file size and improve clarity.
"""

from __future__ import annotations

import logging
import uuid

from nicegui import app

from engine.pro_league import ProLeagueSeason, archive_season
from engine.draftyqueenz import DraftyQueenzManager
from engine.db import (
    save_pro_league as _db_save_league,
    load_pro_league as _db_load_league,
    list_pro_league_saves as _db_list_saves,
    delete_pro_league_save as _db_delete_save,
    save_league_archive as _db_save_archive,
    load_all_league_archives as _db_load_archives,
)

_log = logging.getLogger("viperball.pro_leagues")

# Module-level in-memory stores
pro_sessions: dict[str, ProLeagueSeason] = {}
pro_dq_managers: dict[str, DraftyQueenzManager] = {}


def try_restore_from_db(league_id: str, sid: str) -> bool:
    """Attempt to restore a session from the database into memory."""
    try:
        season, dq = _db_load_league(league_id, sid)
        if season is not None:
            pro_sessions[sid] = season
            pro_dq_managers[sid] = dq
            try:
                from api.main import pro_sessions as _api_pro_sessions
                _api_pro_sessions[f"{league_id}_{sid}"] = season
            except Exception:
                pass
            _log.info(f"Restored {league_id} (session={sid}) from database")
            return True
    except Exception as e:
        _log.warning(f"Failed to restore {league_id} from DB: {e}")
    return False


def auto_save(league_id: str, sid: str):
    """Save the current league state to the database."""
    season = pro_sessions.get(sid)
    dq = pro_dq_managers.get(sid)
    if season is None:
        return
    if dq is None:
        dq = DraftyQueenzManager(manager_name=f"{season.config.league_name} Bettor")
    try:
        _db_save_league(league_id, sid, season, dq)
    except Exception as e:
        _log.warning(f"Auto-save failed for {league_id}: {e}")


def get_all_user_sessions() -> dict[str, tuple[str, ProLeagueSeason, DraftyQueenzManager]]:
    """Return {league_id: (session_id, season, dq_mgr)} for all active leagues."""
    sessions_map: dict = app.storage.user.get("pro_league_sessions") or {}
    result = {}
    stale_keys = []
    for league_id, sid in sessions_map.items():
        if sid in pro_sessions:
            season = pro_sessions[sid]
            dq = pro_dq_managers.get(sid)
            if dq is None:
                dq = DraftyQueenzManager(manager_name=f"{season.config.league_name} Bettor")
                pro_dq_managers[sid] = dq
            result[league_id] = (sid, season, dq)
        elif try_restore_from_db(league_id, sid):
            season = pro_sessions[sid]
            dq = pro_dq_managers[sid]
            result[league_id] = (sid, season, dq)
        else:
            stale_keys.append(league_id)
    if stale_keys:
        for k in stale_keys:
            sessions_map.pop(k, None)
        app.storage.user["pro_league_sessions"] = sessions_map
    return result


def get_active_league_id() -> str | None:
    return app.storage.user.get("pro_league_active")


def set_active_league(league_id: str | None):
    app.storage.user["pro_league_active"] = league_id


def register_session(league_id: str, sid: str, season: ProLeagueSeason, dq: DraftyQueenzManager):
    """Register a new league session."""
    pro_sessions[sid] = season
    pro_dq_managers[sid] = dq
    sessions_map: dict = app.storage.user.get("pro_league_sessions") or {}
    sessions_map[league_id] = sid
    app.storage.user["pro_league_sessions"] = sessions_map
    set_active_league(league_id)
    try:
        from api.main import pro_sessions as _api_pro_sessions
        _api_pro_sessions[f"{league_id}_{sid}"] = season
    except Exception:
        pass
    auto_save(league_id, sid)


def unregister_session(league_id: str):
    """Remove a league session."""
    sessions_map: dict = app.storage.user.get("pro_league_sessions") or {}
    sid = sessions_map.pop(league_id, None)
    app.storage.user["pro_league_sessions"] = sessions_map
    if sid:
        if sid in pro_sessions:
            archive_season(pro_sessions[sid])
            from engine.pro_league import _completed_league_snapshots
            if league_id in _completed_league_snapshots:
                _db_save_archive(league_id, _completed_league_snapshots[league_id])
            del pro_sessions[sid]
        pro_dq_managers.pop(sid, None)
        try:
            from api.main import pro_sessions as _api_pro_sessions
            _api_pro_sessions.pop(f"{league_id}_{sid}", None)
        except Exception:
            pass
        _db_delete_save(league_id, sid)
    if get_active_league_id() == league_id:
        set_active_league(None)


def get_session_and_dq():
    """Get the currently active league's season and DQ manager."""
    active_lid = get_active_league_id()
    if active_lid:
        all_sessions = get_all_user_sessions()
        if active_lid in all_sessions:
            sid, season, dq = all_sessions[active_lid]
            return season, dq, sid

    # Legacy single-session fallback
    sid = app.storage.user.get("pro_league_session_id")
    if sid and sid in pro_sessions:
        season = pro_sessions[sid]
        dq = pro_dq_managers.get(sid)
        if dq is None:
            league_name = season.config.league_name
            dq = DraftyQueenzManager(manager_name=f"{league_name} Bettor")
            pro_dq_managers[sid] = dq
        league_id = season.config.league_id
        sessions_map: dict = app.storage.user.get("pro_league_sessions") or {}
        sessions_map[league_id] = sid
        app.storage.user["pro_league_sessions"] = sessions_map
        set_active_league(league_id)
        return season, dq, sid
    if sid and sid not in pro_sessions:
        app.storage.user["pro_league_session_id"] = None
    return None, None, None


def create_season_sync(config) -> tuple[str, ProLeagueSeason]:
    """CPU-bound season creation."""
    sid = str(uuid.uuid4())[:8]
    season = ProLeagueSeason(config)
    return sid, season
