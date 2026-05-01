"""Phase 4 tests — spine initialization + adversity boost modulation."""

from __future__ import annotations

import pytest

from engine.chemistry import (
    adversity_boost_with_spine,
    compute_chemistry,
    initialize_spine,
)
from engine.coaching import CoachCard
from engine.game_engine import Player, Team, TeamChemistryState


def mk_player(
    voice: int = 50, glue: int = 50, pull: int = 50, drama: int = 35,
    franchise: bool = False,
) -> Player:
    p = Player(
        number=1, name="X", position="RB",
        speed=80, stamina=80, kicking=70,
        lateral_skill=78, tackling=72,
        agility=75, power=75, awareness=75, hands=75,
        kick_power=75, kick_accuracy=75,
    )
    p.voice = voice
    p.glue = glue
    p.pull = pull
    p.drama_baseline = drama
    p.franchise = franchise
    return p


def mk_team(players) -> Team:
    return Team(
        name="X", abbreviation="X", mascot="X",
        players=players,
        avg_speed=80, avg_stamina=80,
        kicking_strength=70, lateral_proficiency=70, defensive_strength=70,
    )


def mk_hc(composure: int = 70) -> CoachCard:
    return CoachCard(
        coach_id="hc", first_name="A", last_name="B",
        gender="male", age=45, role="head_coach",
        classification="players_coach",
        instincts=70, leadership=70, composure=composure,
        rotations=60, development=70, recruiting=60,
    )


# ──────────────────────────────────────────────────────────────────────
# Spine initialization
# ──────────────────────────────────────────────────────────────────────


def test_spine_includes_fabric_and_composure():
    players = [mk_player(glue=70, pull=70) for _ in range(22)]
    team = mk_team(players)
    compute_chemistry(team, mk_hc(composure=80))
    spine = initialize_spine(team, mk_hc(composure=80))
    # composure 80 → +12, plus fabric (~49)
    assert spine > team.chemistry.fabric


def test_crisis_anchor_bonus():
    plain = [mk_player(voice=50, glue=50) for _ in range(22)]
    anchored = [mk_player(voice=50, glue=50) for _ in range(22)]
    anchored[0] = mk_player(voice=80, glue=80)  # crisis anchor

    t1, t2 = mk_team(plain), mk_team(anchored)
    compute_chemistry(t1, mk_hc())
    compute_chemistry(t2, mk_hc())

    s1 = initialize_spine(t1, mk_hc())
    s2 = initialize_spine(t2, mk_hc())
    assert s2 > s1, f"Crisis anchor should add to spine: plain={s1}, anchored={s2}"


def test_franchise_count_lifts_spine():
    plain = [mk_player(glue=60) for _ in range(22)]
    franchised = [mk_player(glue=60) for _ in range(22)]
    franchised[0].franchise = True
    franchised[1].franchise = True

    t1, t2 = mk_team(plain), mk_team(franchised)
    compute_chemistry(t1, mk_hc())
    compute_chemistry(t2, mk_hc())

    s1 = initialize_spine(t1, mk_hc())
    s2 = initialize_spine(t2, mk_hc())
    # 2 franchise players → +20 to spine, but franchise also boosts fabric
    # via pull-multiplier, so the gap is even larger.
    assert s2 - s1 >= 20


# ──────────────────────────────────────────────────────────────────────
# Adversity draws
# ──────────────────────────────────────────────────────────────────────


def test_high_spine_extends_boost():
    state = TeamChemistryState(spine=80.0, tilt=10.0, fabric=70.0)
    base = 0.10
    boosted, _ = adversity_boost_with_spine(base, state)
    # 80 → +0.16 (20% × 0.8)
    assert boosted > base
    assert boosted == pytest.approx(0.10 + 0.16, rel=0.01)


def test_low_spine_minimal_boost():
    state = TeamChemistryState(spine=10.0, tilt=10.0, fabric=40.0)
    base = 0.10
    boosted, _ = adversity_boost_with_spine(base, state)
    assert boosted == pytest.approx(0.10 + 0.02, rel=0.01)


def test_high_tilt_causes_crumble():
    state = TeamChemistryState(spine=50.0, tilt=80.0, fabric=40.0)
    base = 0.10
    boosted, _ = adversity_boost_with_spine(base, state)
    # tilt 80 → -6%; spine 50 → +5% relief; net ~-1% from base
    assert boosted < base


def test_extreme_tilt_crumbles_below_baseline():
    state = TeamChemistryState(spine=10.0, tilt=100.0, fabric=30.0)
    base = 0.10
    boosted, _ = adversity_boost_with_spine(base, state)
    # tilt 100 → -12%; spine 10 → +1%; net -11%
    assert boosted < base


def test_spine_depletes_per_draw():
    state = TeamChemistryState(spine=80.0, tilt=10.0, fabric=70.0)
    _, state = adversity_boost_with_spine(0.10, state)
    assert state.spine == 75.0
    _, state = adversity_boost_with_spine(0.10, state)
    assert state.spine == 70.0


def test_zero_spine_no_op():
    state = TeamChemistryState(spine=0.0, tilt=10.0, fabric=70.0)
    boosted, _ = adversity_boost_with_spine(0.10, state)
    assert boosted == 0.10


def test_spine_late_game_smaller_than_early():
    """After multiple adversity draws, spine is depleted and boosts shrink."""
    state = TeamChemistryState(spine=80.0, tilt=10.0, fabric=70.0)
    early_boost, state = adversity_boost_with_spine(0.10, state)

    # Drain spine 5 more times
    for _ in range(10):
        _, state = adversity_boost_with_spine(0.10, state)

    late_boost, state = adversity_boost_with_spine(0.10, state)
    assert late_boost < early_boost
