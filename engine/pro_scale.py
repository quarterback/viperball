"""Play pro rosters on the engine's rating scale.

College rosters were moved to the current rating scale (median 35) in
November 2026; the engine converts that scale back to the 60 to 100 scale its
formulas use (game_engine.scale_rating).  Pro and WVL rosters, and the pro
systems around them (development, free agency, valuations), still use the old
60 to 100 scale.  Fed to the engine as they are, a WVL tier 4 player plays like
a college star and teams score about 84 points.

engine_scale() converts a game's two rosters for the length of the game and
restores every rating afterward, so the pro systems keep their scale.
"""
from __future__ import annotations

from contextlib import contextmanager

RATING_ATTRS = (
    "speed", "stamina", "kicking", "lateral_skill", "tackling", "agility",
    "power", "awareness", "hands", "kick_power", "kick_accuracy",
)
# Team level aggregates loaded from the team files, on the same old scale.
TEAM_ATTRS = ("avg_speed", "avg_stamina", "kicking_strength",
              "lateral_proficiency", "defensive_strength")
# Mean overall above this means the roster is on the old 60 to 100 scale.
LEGACY_MEAN_OVERALL = 55


# Where a pro league's average player sits on the current scale.  Fed at its
# old scale level, a whole league of college stars scores about 85 points a
# team and a league of college backups about 62; near the college median
# (35) the engine plays the sport it was calibrated for.
PRO_LEAGUE_CENTER = 38.0
# Rating gaps inside a league keep the full conversion (old 1 point is 2).
PRO_SLOPE = 2.0


def league_scale(season) -> tuple:
    """(old scale league mean, offset) for a pro or WVL season, cached on it.
    WVL tiers sit a few points apart so promotion playoffs keep an edge for
    the higher tier."""
    cached = getattr(season, "_engine_scale", None)
    if cached:
        return cached
    players = [p for t in getattr(season, "teams", {}).values() for p in t.players]
    mean = sum(p.overall for p in players) / len(players) if players else 70.0
    league_id = getattr(getattr(season, "config", None), "league_id", "") or ""
    offset = 0.0
    if league_id.startswith("wvl_tier"):
        try:
            offset = (2.5 - int(league_id[len("wvl_tier"):])) * 3.0
        except ValueError:
            offset = 0.0
    season._engine_scale = (mean, offset)
    return season._engine_scale


def legacy_to_engine(value: float, center: float = 70.0, offset: float = 0.0) -> int:
    """Old scale rating to the current scale around a league center."""
    return int(max(10, min(96, round(PRO_LEAGUE_CENTER + offset + (value - center) * PRO_SLOPE))))


def is_legacy_team(team) -> bool:
    players = getattr(team, "players", None) or []
    if not players:
        return False
    return sum(p.overall for p in players) / len(players) > LEGACY_MEAN_OVERALL


@contextmanager
def engine_scale(*teams, center=None, offsets=None):
    """Convert legacy rosters for one game and restore them afterward.

    center: old scale league mean (defaults to the mean of these teams).
    offsets: per team offset in current scale points (same order as teams).
    """
    legacy = [t for t in teams if is_legacy_team(t)]
    if center is None and legacy:
        players = [p for t in legacy for p in t.players]
        center = sum(p.overall for p in players) / len(players)
    saved = []
    try:
        for idx, team in enumerate(teams):
            if team not in legacy:
                continue
            off = offsets[idx] if offsets else 0.0
            team_values = {a: getattr(team, a) for a in TEAM_ATTRS if hasattr(team, a)}
            saved.append((team, team_values))
            for a, v in team_values.items():
                setattr(team, a, legacy_to_engine(v, center, off))
            for p in team.players:
                values = {a: getattr(p, a) for a in RATING_ATTRS if hasattr(p, a)}
                saved.append((p, values))
                for a, v in values.items():
                    setattr(p, a, legacy_to_engine(v, center, off))
        yield
    finally:
        for obj, values in saved:
            for a, v in values.items():
                setattr(obj, a, v)


def current_to_legacy(value: float) -> int:
    """Current scale rating to the old pro scale (scale_rating's full
    conversion: 35 is 70, slope 0.5).  Used when CVL graduates join a pro
    club, so a pro roster stays on one scale."""
    return int(max(40, min(99, round(70 + (value - 35) * 0.5))))


def card_to_legacy_scale(card) -> None:
    for a in RATING_ATTRS:
        if hasattr(card, a):
            setattr(card, a, current_to_legacy(getattr(card, a)))
