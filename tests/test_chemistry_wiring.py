"""Phase 2 wiring tests — verify dynasty.advance_season runs the chemistry pass.

Exercises `Dynasty._apply_season_chemistry` directly (not the full
advance_season flow) so we don't depend on the rest of the dynasty
bootstrap (team histories, conferences, etc.).
"""

from __future__ import annotations

import random

import pytest

from engine.chemistry import log_drift_signal
from engine.coaching import CoachCard
from engine.dynasty import Coach, Dynasty
from engine.game_engine import Player, Team


def mk_player(name: str = "P", overall: int = 75, **fields) -> Player:
    s = max(25, min(99, overall))
    p = Player(
        number=1, name=name, position="RB",
        speed=s, stamina=s, kicking=s,
        lateral_skill=s, tackling=s,
        agility=s, power=s, awareness=s, hands=s,
        kick_power=s, kick_accuracy=s,
    )
    p.player_id = f"pid_{name}"
    for k, v in fields.items():
        setattr(p, k, v)
    return p


def mk_team(name: str, players) -> Team:
    return Team(
        name=name, abbreviation=name[:3], mascot="X",
        players=players,
        avg_speed=80, avg_stamina=80,
        kicking_strength=70, lateral_proficiency=70, defensive_strength=70,
    )


def mk_hc() -> CoachCard:
    return CoachCard(
        coach_id="hc", first_name="A", last_name="B",
        gender="male", age=45, role="head_coach",
        classification="players_coach",
        instincts=70, leadership=70, composure=70,
        rotations=60, development=70, recruiting=60,
    )


class _StubSeason:
    """Minimal season-like object with just the .teams attribute the
    chemistry pass needs."""

    def __init__(self, teams):
        self.teams = teams


def test_apply_season_chemistry_consolidates_buffer_and_clips():
    p = mk_player()
    p.voice = 50
    p.voice_range = (40, 70)
    for _ in range(40):
        log_drift_signal(p, "voice", +1.0)

    team = mk_team("Alpha", [p])
    coach = Coach(name="Test", team_name="Alpha")
    dynasty = Dynasty(dynasty_name="T", coach=coach, current_year=2026)
    dynasty._coaching_staffs = {"Alpha": {"head_coach": mk_hc()}}

    dynasty._apply_season_chemistry(_StubSeason({"Alpha": team}), 2026)

    # Drift should have applied; voice clipped at ceiling.
    assert p.voice == 70
    # Buffer cleared after pass.
    assert len(p.chemistry_drift_log) == 0
    # Tenure counters incremented.
    assert p.seasons_with_team == 1
    assert p.seasons_in_career == 1
    assert "Alpha" in p.teams_played_for


def test_apply_season_chemistry_awards_franchise_at_tenure():
    p = mk_player(overall=85)
    # Pre-seed tenure (4 seasons) and a major award; one more pass should
    # tip into franchise eligibility.
    p.seasons_with_team = 4
    p.seasons_in_career = 4
    p.chemistry_major_awards.append({"type": "mvp", "year": 2025, "team": "Alpha"})

    team = mk_team("Alpha", [p])
    coach = Coach(name="Test", team_name="Alpha")
    dynasty = Dynasty(dynasty_name="T", coach=coach, current_year=2026)
    dynasty._coaching_staffs = {"Alpha": {"head_coach": mk_hc()}}

    dynasty._apply_season_chemistry(_StubSeason({"Alpha": team}), 2026)

    assert p.franchise is True
    assert p.seasons_with_team == 5


def test_apply_season_chemistry_tracks_baggage_via_team_changes():
    p = mk_player()
    p.teams_played_for = ["Beta", "Gamma"]  # already moved twice

    team = mk_team("Delta", [p])  # third team this stretch
    coach = Coach(name="Test", team_name="Delta")
    dynasty = Dynasty(dynasty_name="T", coach=coach, current_year=2026)
    dynasty._coaching_staffs = {"Delta": {"head_coach": mk_hc()}}

    dynasty._apply_season_chemistry(_StubSeason({"Delta": team}), 2026)

    assert "Delta" in p.teams_played_for
    assert p.baggage is True


def test_pro_league_season_end_chemistry():
    """`_run_season_end_chemistry` runs the same pass with no HC."""
    from engine.chemistry import log_drift_signal
    from engine.pro_league import _run_season_end_chemistry

    p = mk_player()
    p.voice = 50
    p.voice_range = (40, 80)
    for _ in range(15):
        log_drift_signal(p, "voice", +1.0)

    team = mk_team("ProTeam", [p])

    # Mock the parts of ProLeagueSeason _run_season_end_chemistry actually uses.
    class _MockConfig:
        league_id = "test_league"

    class _MockSeason:
        def __init__(self):
            self.config = _MockConfig()
            self.teams = {"ProTeam": team}

    season = _MockSeason()
    _run_season_end_chemistry(season)

    # Drift consolidated (with no HC, base_mult=1.0, expected delta ~+15
    # but clipped to ceiling 80).
    assert p.voice > 50
    assert p.voice <= 80
    assert len(p.chemistry_drift_log) == 0
    assert p.seasons_with_team == 1
    assert p.seasons_in_career == 1
    assert "ProTeam" in p.teams_played_for
    # Streak counters initialized on the season.
    assert hasattr(season, "_chem_ceiling_streaks")


def test_pro_league_no_hc_does_not_crash_on_season_end():
    """Season-end pass must run cleanly with HC=None."""
    from engine.chemistry import log_drift_signal
    from engine.pro_league import _run_season_end_chemistry

    p = mk_player(overall=85)
    p.seasons_with_team = 4  # near franchise tenure
    p.chemistry_major_awards.append({"type": "mvp", "year": 2025, "team": "ProTeam"})

    team = mk_team("ProTeam", [p])

    class _MockConfig:
        league_id = "test_league_2"

    class _MockSeason:
        def __init__(self):
            self.config = _MockConfig()
            self.teams = {"ProTeam": team}

    season = _MockSeason()
    _run_season_end_chemistry(season)

    # Tenure ticks → 5 → franchise eligibility met → flag awarded.
    assert p.franchise is True


def test_streak_counters_persist_across_calls():
    """Ceiling/floor pinning streaks need to survive between season passes."""
    p = mk_player()
    p.voice = 70
    p.voice_range = (40, 70)  # already at ceiling

    team = mk_team("Alpha", [p])
    coach = Coach(name="Test", team_name="Alpha")
    dynasty = Dynasty(dynasty_name="T", coach=coach, current_year=2026)
    dynasty._coaching_staffs = {"Alpha": {"head_coach": mk_hc()}}

    for _ in range(2):
        dynasty._apply_season_chemistry(_StubSeason({"Alpha": team}), 2026)

    streaks = dynasty._chem_ceiling_streaks[p.player_id]
    assert streaks.get("voice", 0) == 2
