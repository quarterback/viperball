"""Phase 5 tests — pipeline, drift indicators, UI surfacing."""

from __future__ import annotations

import pytest

from engine.chemistry import (
    compute_chemistry,
    compute_pipeline,
    drift_indicator,
    render_player_card,
    render_team_chemistry,
    update_recent_drift,
)
from engine.coaching import CoachCard
from engine.game_engine import Player, Team


def mk_player(year: str = "Junior", overall: int = 75, **fields) -> Player:
    s = max(25, min(99, overall))
    p = Player(
        number=1, name="Alex Morgan", position="RB",
        speed=s, stamina=s, kicking=s,
        lateral_skill=s, tackling=s,
        agility=s, power=s, awareness=s, hands=s,
        kick_power=s, kick_accuracy=s,
    )
    p.year = year
    for k, v in fields.items():
        setattr(p, k, v)
    return p


def mk_team(players) -> Team:
    return Team(
        name="Demo", abbreviation="DEM", mascot="Demos",
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


# ──────────────────────────────────────────────────────────────────────
# Drift indicators
# ──────────────────────────────────────────────────────────────────────


def test_indicator_states():
    p = mk_player()
    assert drift_indicator(p, "voice") == "stable"

    update_recent_drift(p, "voice", 1.0)
    assert drift_indicator(p, "voice") == "rising"

    p2 = mk_player()
    update_recent_drift(p2, "voice", -1.0)
    assert drift_indicator(p2, "voice") == "declining"


def test_drift_decays_over_time():
    p = mk_player()
    update_recent_drift(p, "voice", 1.0)
    initial = p.chemistry_recent_drift["voice"]
    # Decay-only updates
    for _ in range(10):
        update_recent_drift(p, "voice", 0.0)
    final = p.chemistry_recent_drift["voice"]
    assert final < initial


# ──────────────────────────────────────────────────────────────────────
# Pipeline
# ──────────────────────────────────────────────────────────────────────


def test_pipeline_counts_rising_young_high_ceiling():
    young_riser = mk_player(year="Sophomore")
    young_riser.voice_range = (40, 85)  # high ceiling
    young_riser.chemistry_recent_drift = {"voice": 1.5}

    veteran_riser = mk_player(year="Senior", overall=85)
    veteran_riser.seasons_in_career = 8
    veteran_riser.voice_range = (40, 85)
    veteran_riser.chemistry_recent_drift = {"voice": 1.5}

    young_flat = mk_player(year="Sophomore")
    young_flat.voice_range = (40, 85)
    young_flat.chemistry_recent_drift = {"voice": 0.0}

    young_low_ceiling = mk_player(year="Sophomore")
    young_low_ceiling.voice_range = (40, 60)  # low ceiling
    young_low_ceiling.pull_range = (40, 60)
    young_low_ceiling.chemistry_recent_drift = {"voice": 1.5}

    team = mk_team([young_riser, veteran_riser, young_flat, young_low_ceiling])
    pipeline = compute_pipeline(team)
    # Only young_riser counts.
    assert pipeline > 0
    # Sanity: removing the young_riser zeros it.
    pipeline_no_riser = compute_pipeline(mk_team([veteran_riser, young_flat, young_low_ceiling]))
    assert pipeline_no_riser == 0


def test_pipeline_is_set_on_compute_chemistry():
    young = mk_player(year="Freshman")
    young.voice_range = (40, 85)
    young.chemistry_recent_drift = {"voice": 1.0}
    team = mk_team([young] * 22)
    state = compute_chemistry(team, mk_hc())
    assert state.pipeline > 0


# ──────────────────────────────────────────────────────────────────────
# UI rendering smoke tests
# ──────────────────────────────────────────────────────────────────────


def test_render_player_card_includes_flags_and_attrs():
    p = mk_player(franchise=True, big_stage=True)
    p.voice = 78
    p.glue = 65
    update_recent_drift(p, "voice", 1.0)  # rising
    out = render_player_card(p)
    assert "FRANCHISE" in out
    assert "BIG STAGE" in out
    assert "Voice" in out
    assert "78" in out
    assert "rising" in out


def test_render_player_card_shows_today_when_set():
    p = mk_player()
    p.drama_baseline = 35
    p.drama_current = 28
    out = render_player_card(p)
    assert "today" in out


def test_render_team_chemistry_includes_all_components():
    team = mk_team([mk_player() for _ in range(22)])
    compute_chemistry(team, mk_hc())
    out = render_team_chemistry(team, mk_hc())
    for label in ("Tone", "Fabric", "Drag", "Tilt", "Spine", "Pipeline", "Franchise"):
        assert label in out
    assert "players_coach" in out
