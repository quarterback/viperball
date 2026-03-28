"""WVL state management — persistence, caching, and dynasty lifecycle.

Extracted from wvl_mode.py to reduce file size and improve clarity.
"""

from nicegui import ui, app
from typing import Optional
import logging

from engine.wvl_config import CLUBS_BY_KEY
from engine.wvl_dynasty import WVLDynasty
from engine.db import (
    save_wvl_season as _db_save_season,
    load_wvl_season as _db_load_season,
    delete_wvl_season as _db_delete_season,
)

_log = logging.getLogger("viperball.wvl")

_WVL_DYNASTY_KEY = "wvl_dynasty"
_WVL_PHASE_KEY = "wvl_phase"
_WVL_SEASON_KEY = "wvl_last_season"

# In-memory cache for the active WVL season (avoids repeated DB reads)
_wvl_season_cache = {}


def get_wvl_season():
    """Load the WVL season from in-memory cache, then DB, then legacy storage."""
    if "current" in _wvl_season_cache:
        return _wvl_season_cache["current"]
    season = _db_load_season()
    if season is not None:
        _wvl_season_cache["current"] = season
        return season
    legacy = app.storage.user.get(_WVL_SEASON_KEY)
    if legacy and hasattr(legacy, 'tier_seasons'):
        _wvl_season_cache["current"] = legacy
        try:
            _db_save_season(legacy)
            app.storage.user.pop(_WVL_SEASON_KEY, None)
            _log.info("Migrated WVL season from app.storage.user to database")
        except Exception as e:
            _log.warning(f"Failed to migrate WVL season to DB: {e}")
        return legacy
    return None


def save_wvl_season(season):
    """Save the WVL season to in-memory cache and database."""
    _wvl_season_cache["current"] = season
    try:
        _db_save_season(season)
    except Exception as e:
        _log.warning(f"Failed to save WVL season to DB: {e}")


def clear_wvl_season():
    """Clear the WVL season from cache and database."""
    _wvl_season_cache.pop("current", None)
    try:
        _db_delete_season()
    except Exception:
        pass
    app.storage.user.pop(_WVL_SEASON_KEY, None)


def get_dynasty() -> Optional[WVLDynasty]:
    raw = app.storage.user.get(_WVL_DYNASTY_KEY)
    if raw is None:
        return None
    if isinstance(raw, WVLDynasty):
        dynasty = raw
    else:
        try:
            dynasty = WVLDynasty.from_dict(raw)
        except Exception:
            return None
    season = get_wvl_season()
    if season and hasattr(season, 'tier_seasons') and not dynasty._team_rosters:
        dynasty._current_season = season
    return dynasty


def set_dynasty(dynasty: Optional[WVLDynasty]):
    app.storage.user[_WVL_DYNASTY_KEY] = dynasty.to_dict() if dynasty is not None else None


def get_phase() -> str:
    return app.storage.user.get(_WVL_PHASE_KEY, "setup")


def set_phase(phase: str):
    app.storage.user[_WVL_PHASE_KEY] = phase


def extract_args(e) -> dict:
    """Safely extract row dict from NiceGUI table slot event args."""
    args = e.args
    if isinstance(args, list):
        args = args[0] if args else {}
    return args if isinstance(args, dict) else {}


def register_wvl_season(dynasty, season, year=None):
    try:
        import time as _time
        from api.main import wvl_sessions
        effective_year = year if year is not None else dynasty.current_year - 1
        session_id = f"wvl_{dynasty.dynasty_name}_{effective_year}"
        session_id = session_id.lower().replace(" ", "_").replace("'", "")
        wvl_sessions[session_id] = {
            "season": season,
            "dynasty": dynasty,
            "dynasty_name": dynasty.dynasty_name,
            "year": effective_year,
            "club_key": dynasty.owner.club_key,
            "last_accessed": _time.time(),
        }
    except Exception:
        pass


def ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    s = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{s}"


def rating_color(val: int) -> str:
    if val >= 85:
        return "color: #15803d; font-weight: 700;"
    elif val >= 75:
        return "color: #16a34a;"
    elif val >= 65:
        return "color: #ca8a04;"
    elif val >= 55:
        return "color: #ea580c;"
    else:
        return "color: #dc2626;"
