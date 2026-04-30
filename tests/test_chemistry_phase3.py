"""Phase 3 tests — variable per-game chemistry layer."""

from __future__ import annotations

import pytest

from engine.chemistry import compute_chemistry, compute_pregame_variables
from engine.coaching import CoachCard
from engine.game_engine import Player, Team


def mk_player(
    overall: int = 75,
    voice: int = 50,
    glue: int = 50,
    pull: int = 50,
    drama: int = 35,
    fit: int = 60,
    seasons: int = 3,
    **flags,
) -> Player:
    s = max(25, min(99, overall))
    p = Player(
        number=1, name="X", position="RB",
        speed=s, stamina=s, kicking=s,
        lateral_skill=s, tackling=s,
        agility=s, power=s, awareness=s, hands=s,
        kick_power=s, kick_accuracy=s,
    )
    p.voice = voice
    p.glue = glue
    p.pull = pull
    p.drama_baseline = drama
    p.fit = fit
    p.seasons_in_career = seasons
    for k, v in flags.items():
        setattr(p, k, v)
    return p


def mk_team(players) -> Team:
    return Team(
        name="X", abbreviation="X", mascot="X",
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
# drama_current modifiers
# ──────────────────────────────────────────────────────────────────────


def test_contract_year_losing_streak_spikes_drama():
    p = mk_player(drama=40)
    compute_pregame_variables(p, contract_year=True, team_losing_streak=4)
    assert p.drama_current == 55  # 40 + 15


def test_winning_streak_drops_drama():
    p = mk_player(drama=40)
    compute_pregame_variables(p, team_winning_streak=4)
    assert p.drama_current == 30  # 40 - 10


def test_franchise_caps_drama_at_60():
    p = mk_player(drama=80, franchise=True)
    compute_pregame_variables(
        p, contract_year=True, team_losing_streak=5, recent_demotion=True
    )
    # 80 + 15 + 10 = 105, capped at 60 by franchise flag
    assert p.drama_current == 60


def test_baggage_floors_drama_at_50():
    p = mk_player(drama=20, baggage=True)
    compute_pregame_variables(p, team_winning_streak=10, recent_personal_achievement=True)
    # baggage forces floor at 50 regardless of suppressors
    assert p.drama_current == 50


# ──────────────────────────────────────────────────────────────────────
# head_current
# ──────────────────────────────────────────────────────────────────────


def test_rookie_head_swings_more_than_veteran():
    rookie = mk_player(seasons=1)
    veteran = mk_player(seasons=10)
    compute_pregame_variables(rookie, off_field_noise=3)
    compute_pregame_variables(veteran, off_field_noise=3)
    # rookie: 50 - 3*8 = 26; veteran: 50 - 3*5 = 35
    assert rookie.head_current < veteran.head_current


def test_strong_recent_performance_lifts_head():
    p = mk_player()
    compute_pregame_variables(p, recent_strong_performance=True)
    assert p.head_current > 50


# ──────────────────────────────────────────────────────────────────────
# fit_current
# ──────────────────────────────────────────────────────────────────────


def test_fit_drops_when_usage_mismatches_ideal():
    p = mk_player(fit=70)
    p.fit_range = (40, 90)
    # actual = 0.2, ideal = 0.7 → diff = 0.5 → -30 fit
    compute_pregame_variables(p, snap_share_actual=0.2, snap_share_ideal=0.7)
    assert p.fit_current == 40  # 70 - 30 = 40 (at floor)


def test_recent_scheme_change_penalizes_fit():
    p_old = mk_player(fit=70)
    p_new = mk_player(fit=70)
    compute_pregame_variables(p_old, scheme_change_recency=99,
                              snap_share_actual=0.5, snap_share_ideal=0.5)
    compute_pregame_variables(p_new, scheme_change_recency=1,
                              snap_share_actual=0.5, snap_share_ideal=0.5)
    assert p_new.fit_current < p_old.fit_current


# ──────────────────────────────────────────────────────────────────────
# Drag uses drama_current after Phase 3
# ──────────────────────────────────────────────────────────────────────


def test_drag_uses_drama_current_when_set():
    """Same player, two scenarios: drag should differ if drama_current differs."""
    base_players = [mk_player() for _ in range(22)]
    base_players[0].drama_baseline = 40  # not dramatic
    base_players[0].pull = 70

    # Scenario A: contract year + losing streak spikes drama_current.
    compute_pregame_variables(
        base_players[0], contract_year=True, team_losing_streak=4
    )
    # drama_current = 40 + 15 = 55 (still under 60, won't trigger drag)
    drag_a = compute_chemistry(mk_team(base_players), mk_hc()).drag

    # Reset and create a more extreme scenario: high baseline + spike.
    base_players2 = [mk_player() for _ in range(22)]
    base_players2[0].drama_baseline = 50
    base_players2[0].pull = 70
    compute_pregame_variables(
        base_players2[0], contract_year=True, team_losing_streak=4,
        recent_demotion=True,
    )
    # drama_current = 50 + 15 + 10 = 75 → triggers drag
    drag_b = compute_chemistry(mk_team(base_players2), mk_hc()).drag

    assert drag_b > drag_a, (
        f"drama_current at 75 should produce more drag than at 55: "
        f"a={drag_a}, b={drag_b}"
    )


def test_drag_falls_back_to_baseline_when_current_unset():
    """Without compute_pregame_variables, drag still works via baseline."""
    players = [mk_player() for _ in range(22)]
    players[0].drama_baseline = 80
    # drama_current is 0 (default sentinel)
    state = compute_chemistry(mk_team(players), mk_hc())
    assert state.drag > 0


def test_franchise_cap_visibly_softens_worst_case():
    """A franchise player in worst-case still caps drama_current at 60."""
    plain = mk_player(drama=80, pull=70, glue=40)
    franc = mk_player(drama=80, pull=70, glue=40, franchise=True)

    compute_pregame_variables(
        plain, contract_year=True, team_losing_streak=4, recent_demotion=True
    )
    compute_pregame_variables(
        franc, contract_year=True, team_losing_streak=4, recent_demotion=True
    )
    assert plain.drama_current >= 80
    assert franc.drama_current == 60


def test_baggage_floor_visible_in_best_case():
    """Baggage in best-case still floors drama_current at 50."""
    plain = mk_player(drama=30)
    bagged = mk_player(drama=30, baggage=True)

    compute_pregame_variables(plain, team_winning_streak=4, recent_personal_achievement=True)
    compute_pregame_variables(bagged, team_winning_streak=4, recent_personal_achievement=True)
    assert plain.drama_current < 50
    assert bagged.drama_current == 50
