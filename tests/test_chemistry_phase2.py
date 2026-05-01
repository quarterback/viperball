"""Phase 2 tests — stable-attribute drift, range pressure, flag awards.

Phase 2 doesn't wire into dynasty advance_season yet; these tests
exercise the chemistry functions directly with synthetic inputs that
stand in for season summaries.
"""

from __future__ import annotations

import random

import pytest

from engine.chemistry import (
    apply_innate_range_pressure,
    apply_season_end_drift,
    evaluate_permanent_flags,
    log_drift_signal,
    log_game_drift_signals,
    log_path_event,
    season_end_chemistry_pass,
)
from engine.coaching import CoachCard
from engine.game_engine import Player


def mk_player(
    overall: int = 75,
    year: str = "Junior",
    voice: int = 50,
    glue: int = 50,
    reach: int = 70,
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
    p.reach = reach
    p.year = year
    for k, v in flags.items():
        setattr(p, k, v)
    return p


def mk_hc(classification: str = "players_coach", message: int = 60) -> CoachCard:
    return CoachCard(
        coach_id="hc", first_name="A", last_name="B",
        gender="male", age=45, role="head_coach",
        classification=classification,
        instincts=70, leadership=70, composure=70,
        rotations=60, development=70, recruiting=60,
        message=message,
    )


# ──────────────────────────────────────────────────────────────────────
# Drift accumulator
# ──────────────────────────────────────────────────────────────────────


def test_drift_buffer_accumulates_and_clears():
    p = mk_player()
    log_drift_signal(p, "voice", +0.3)
    log_drift_signal(p, "voice", +0.4)
    assert len(p.chemistry_drift_log) == 2
    apply_season_end_drift(p, mk_hc())
    assert len(p.chemistry_drift_log) == 0


def test_log_game_drift_signals_emits_expected_signals():
    p = mk_player()
    log_game_drift_signals(p, snap_share=0.8, team_won=True, was_comeback=True)
    attrs = {entry["attr"] for entry in p.chemistry_drift_log}
    assert "voice" in attrs
    assert "glue" in attrs
    assert "comeback_win_carried" in p.chemistry_career_events


def test_low_snap_share_emits_negative_signals():
    p = mk_player()
    log_game_drift_signals(p, snap_share=0.10, team_won=False)
    voice_signals = [e for e in p.chemistry_drift_log if e["attr"] == "voice"]
    drama_signals = [e for e in p.chemistry_drift_log if e["attr"] == "drama_baseline"]
    assert any(s["delta"] < 0 for s in voice_signals)
    assert any(s["delta"] > 0 for s in drama_signals)


def test_demotion_suppressed_by_high_reach():
    """High-reach players take demotion in stride."""
    low_reach = mk_player(reach=50)
    high_reach = mk_player(reach=85)
    log_game_drift_signals(low_reach, snap_share=0.4, team_won=True, is_demoted_starter=True)
    log_game_drift_signals(high_reach, snap_share=0.4, team_won=True, is_demoted_starter=True)

    low_drama_delta = sum(e["delta"] for e in low_reach.chemistry_drift_log if e["attr"] == "drama_baseline")
    high_drama_delta = sum(e["delta"] for e in high_reach.chemistry_drift_log if e["attr"] == "drama_baseline")
    assert low_drama_delta > high_drama_delta


# ──────────────────────────────────────────────────────────────────────
# Season-end consolidation
# ──────────────────────────────────────────────────────────────────────


def test_consolidation_applies_aggregated_delta_within_range():
    p = mk_player(voice=50)
    p.voice_range = (40, 70)
    for _ in range(20):
        log_drift_signal(p, "voice", +1.0)
    apply_season_end_drift(p, mk_hc())
    assert p.voice == 70  # clipped at ceiling


def test_clip_at_floor():
    p = mk_player(voice=50)
    p.voice_range = (45, 80)
    for _ in range(20):
        log_drift_signal(p, "voice", -1.0)
    apply_season_end_drift(p, mk_hc())
    assert p.voice == 45  # clipped at floor


def test_mentor_amplifies_young_player_positive_drift():
    """Mentor archetype × young player + positive drift = ×1.25 multiplier."""
    young_under_mentor = mk_player(year="Freshman", voice=50)
    young_under_neutral = mk_player(year="Freshman", voice=50)

    for _ in range(10):
        log_drift_signal(young_under_mentor, "voice", +0.5)
        log_drift_signal(young_under_neutral, "voice", +0.5)

    # motivator → mentor archetype mapping
    apply_season_end_drift(young_under_mentor, mk_hc("motivator"))
    apply_season_end_drift(young_under_neutral, mk_hc("scheme_master"))

    mentor_delta = young_under_mentor.voice - 50
    neutral_delta = young_under_neutral.voice - 50
    assert mentor_delta > neutral_delta, (
        f"Mentor should amplify young player drift: "
        f"mentor={mentor_delta}, neutral={neutral_delta}"
    )


def test_disciplinarian_compounds_negative_drift_for_talent_mismatch():
    mismatch = mk_player(overall=68, voice=60)
    mismatch_no_disc = mk_player(overall=68, voice=60)
    for _ in range(8):
        log_drift_signal(mismatch, "voice", -0.5)
        log_drift_signal(mismatch_no_disc, "voice", -0.5)

    apply_season_end_drift(mismatch, mk_hc("disciplinarian"))
    apply_season_end_drift(mismatch_no_disc, mk_hc("scheme_master"))

    # Disciplinarian should produce a more negative drop.
    assert mismatch.voice < mismatch_no_disc.voice, (
        f"Disciplinarian should compound negatives on mismatch: "
        f"disc={mismatch.voice}, neutral={mismatch_no_disc.voice}"
    )


def test_high_reach_amplifies_coach_influence():
    """Reach mediates how much HC influence reaches the player."""
    high_reach = mk_player(reach=90, voice=50)
    low_reach = mk_player(reach=30, voice=50)
    for _ in range(10):
        log_drift_signal(high_reach, "voice", +0.5)
        log_drift_signal(low_reach, "voice", +0.5)

    hc = mk_hc()
    apply_season_end_drift(high_reach, hc)
    apply_season_end_drift(low_reach, hc)

    assert (high_reach.voice - 50) > (low_reach.voice - 50)


# ──────────────────────────────────────────────────────────────────────
# Innate range pressure
# ──────────────────────────────────────────────────────────────────────


def test_range_pressure_lifts_ceiling_when_pinned():
    """At p=0.20 per call, ~20 lifts expected over 100 trials."""
    rng = random.Random(0)
    lifts = 0
    for _ in range(100):
        p = mk_player()
        p.voice_range = (40, 70)
        before = p.voice_range[1]
        apply_innate_range_pressure(
            p, {"voice": 2}, {"voice": 0}, rng=rng,
        )
        if p.voice_range[1] > before:
            lifts += 1
    # 20% expected — accept anywhere in [10, 35] to allow for variance.
    assert lifts >= 10, f"Expected ~20 lifts over 100 trials, got {lifts}"
    assert lifts <= 35, f"Expected ~20 lifts over 100 trials, got {lifts}"


def test_range_pressure_drops_floor_when_suppressed():
    p = mk_player()
    p.voice_range = (60, 90)
    rng = random.Random(0)
    initial_floor = p.voice_range[0]
    apply_innate_range_pressure(p, {"voice": 0}, {"voice": 3}, rng=rng)
    assert p.voice_range[0] < initial_floor


# ──────────────────────────────────────────────────────────────────────
# Permanent flag awards
# ──────────────────────────────────────────────────────────────────────


def test_franchise_awarded_with_tenure_award_and_elite_production():
    p = mk_player(overall=85)
    p.seasons_with_team = 6
    p.chemistry_major_awards.append({"type": "mvp", "year": 2026, "team": "X"})
    changes = evaluate_permanent_flags(p)
    assert p.franchise is True
    assert changes.get("franchise") is True


def test_franchise_not_awarded_without_award():
    p = mk_player(overall=88)
    p.seasons_with_team = 7
    evaluate_permanent_flags(p)
    assert p.franchise is False


def test_franchise_not_awarded_without_tenure():
    p = mk_player(overall=88)
    p.seasons_with_team = 2
    p.chemistry_major_awards.append({"type": "mvp", "year": 2026, "team": "X"})
    evaluate_permanent_flags(p)
    assert p.franchise is False


def test_franchise_requires_elite_production():
    p = mk_player(overall=72)  # below floor
    p.seasons_with_team = 6
    p.chemistry_major_awards.append({"type": "mvp", "year": 2026, "team": "X"})
    evaluate_permanent_flags(p)
    assert p.franchise is False


def test_big_stage_awarded_on_stacked_roster():
    p = mk_player(overall=85)
    p.chemistry_major_awards.append({
        "type": "mvp", "year": 2026, "team": "X",
        "stacked_roster": True, "deep_playoff_run": True,
    })
    evaluate_permanent_flags(p)
    assert p.big_stage is True


def test_big_stage_requires_stacked_roster():
    p = mk_player(overall=88)
    p.chemistry_major_awards.append({
        "type": "mvp", "year": 2026, "team": "X",
        "stacked_roster": False, "deep_playoff_run": True,
    })
    evaluate_permanent_flags(p)
    assert p.big_stage is False


def test_baggage_awarded_for_team_churn():
    p = mk_player()
    p.teams_played_for = ["A", "B", "C"]  # 3 teams
    evaluate_permanent_flags(p)
    assert p.baggage is True


def test_baggage_awarded_for_incidents():
    p = mk_player()
    p.locker_room_incidents = 3
    evaluate_permanent_flags(p)
    assert p.baggage is True


def test_baggage_recovery_lowers_drama_floor_partially():
    p = mk_player()
    p.baggage = True
    p.drama_baseline_range = (40, 70)
    p.low_drama_seasons_for_baggage_recovery = 3
    evaluate_permanent_flags(p)
    floor, ceiling = p.drama_baseline_range
    assert floor == 35  # 40 - 5
    assert ceiling == 70
    assert p.baggage is True  # NEVER fully removed


# ──────────────────────────────────────────────────────────────────────
# Combined season-end pass
# ──────────────────────────────────────────────────────────────────────


def test_season_end_pass_runs_all_phases():
    p = mk_player(overall=85)
    p.seasons_with_team = 5
    p.chemistry_major_awards.append({"type": "mvp", "year": 2026, "team": "X"})
    log_drift_signal(p, "voice", +5)
    out = season_end_chemistry_pass(
        p, mk_hc("players_coach"),
        consecutive_at_ceiling={"voice": 0},
        consecutive_below_floor={"voice": 0},
    )
    assert "drift_applied" in out
    assert "flag_changes" in out
    assert p.franchise is True


def test_baggage_recovery_only_under_players_coach():
    """Recovery only counts under a players_coach archetype."""
    p = mk_player()
    p.baggage = True
    p.drama_baseline_range = (40, 70)

    # Three seasons under disciplinarian — should not advance recovery.
    for _ in range(3):
        season_end_chemistry_pass(
            p, mk_hc("disciplinarian"),
            is_low_drama_season=True,
        )
    assert p.low_drama_seasons_for_baggage_recovery == 0

    # Three seasons under players_coach — should advance to recovery.
    for _ in range(3):
        season_end_chemistry_pass(
            p, mk_hc("players_coach"),
            is_low_drama_season=True,
        )
    # After the 3rd low-drama season, evaluate_permanent_flags should fire and reset.
    floor, _ = p.drama_baseline_range
    assert floor == 35
