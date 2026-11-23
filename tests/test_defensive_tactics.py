"""DEF-01/02/03: tactical read and defensive scheme integration guards.

These tests deliberately construct an uninitialized engine instance: they
exercise the independent calculations without a season or 205-team roster.
The full-game distribution still needs the seeded benchmark described in
docs/ASSESSMENT_PRD_ENGINE_TACTICS_2026-11-23.md.
"""

from types import SimpleNamespace
import random

import pytest

from engine.game_engine import (
    DEFENSE_STYLES,
    FORMATION_VS_DEFENSE,
    OFFENSE_VS_DEFENSE_MATCHUP,
    OFFENSE_STYLES,
    PlayFamily,
    V2_ENGINE_CONFIG,
    ViperballEngine,
)


def make_engine(offense="ground_pound", defense="lockdown"):
    engine = object.__new__(ViperballEngine)
    engine.state = SimpleNamespace(
        possession="home", quarter=1, down=1, yards_to_go=20,
        field_position=50,
    )
    engine.home_team = SimpleNamespace(offense_style=offense, defense_style="swarm")
    engine.away_team = SimpleNamespace(offense_style="balanced", defense_style=defense)
    engine.home_defense = DEFENSE_STYLES["swarm"]
    engine.away_defense = DEFENSE_STYLES[defense]
    engine._current_formation = "spread"
    engine._def_dc_gameplan = lambda: {"instincts_factor": 0.7}
    engine._def_coaching_mods = lambda: {"instincts_factor": 0.6}
    engine._get_defense_personnel_boost = lambda _defense: 0.0
    engine._get_defense_situational_boost = lambda _defense: 0.0
    engine._defense_read_counts = {
        "home": {"attempts": 0, "reads": 0},
        "away": {"attempts": 0, "reads": 0},
    }
    return engine


@pytest.mark.parametrize("formation,scheme", [
    ("spread", "lockdown"),  # defense has advantage, multiplier below 1
    ("heavy", "lockdown"),   # offense has advantage, multiplier above 1
    ("tight", "blitz_pack"),
])
def test_correct_formation_read_moves_halfway_toward_neutral(
    formation, scheme, monkeypatch
):
    engine = make_engine(defense=scheme)
    engine._current_formation = formation
    base = FORMATION_VS_DEFENSE[(formation, scheme)]
    monkeypatch.setattr(random, "random", lambda: 1.0)
    missed_read = engine._formation_defense_multiplier()
    monkeypatch.setattr(random, "random", lambda: 0.0)
    recognized = engine._formation_defense_multiplier()

    assert missed_read == pytest.approx(base)
    assert recognized == pytest.approx(1.0 + (base - 1.0) * 0.5)
    assert min(base, 1.0) <= recognized <= max(base, 1.0)


@pytest.mark.parametrize("offense,scheme,family", [
    ("ground_pound", "lockdown", PlayFamily.POWER),
    ("boot_raid", "lockdown", PlayFamily.KICK_PASS),
    ("ground_pound", "fortress", PlayFamily.POWER),
    ("chain_gang", "swarm", PlayFamily.LATERAL_SPREAD),
])
def test_scheme_effect_has_expected_direction(offense, scheme, family):
    engine = make_engine(offense, scheme)
    multiplier = engine._defense_style_multiplier(family)
    matrix = OFFENSE_VS_DEFENSE_MATCHUP[(offense, scheme)]
    specific = DEFENSE_STYLES[scheme]["play_family_modifiers"][family.value]
    expected = max(0.75, min(1.20, 1 + 0.5 * (matrix - 1) + 0.35 * (specific - 1)))
    assert multiplier == pytest.approx(expected)
    assert 0.75 <= multiplier <= 1.20


def test_scheme_offense_and_defense_tradeoffs():
    # A coverage scheme makes kick passing less productive while conceding
    # better power runs. This is a tactical distinction, not a win-rate test.
    engine = make_engine("ground_pound", "lockdown")
    power_vs_lockdown = engine._defense_style_multiplier(PlayFamily.POWER)
    engine.home_team.offense_style = "boot_raid"
    kick_vs_lockdown = engine._defense_style_multiplier(PlayFamily.KICK_PASS)
    assert power_vs_lockdown > 1.0
    assert kick_vs_lockdown < 1.0


def test_defense_read_roll_uses_scheme_and_records_defender(monkeypatch):
    engine = make_engine()
    monkeypatch.setattr(random, "random", lambda: 0.0)
    assert engine.get_defensive_read(PlayFamily.POWER)
    assert engine._defense_read_counts["away"] == {"attempts": 1, "reads": 1}
    monkeypatch.setattr(random, "random", lambda: 1.0)
    assert not engine.get_defensive_read(PlayFamily.POWER)
    assert engine._defense_read_counts["away"] == {"attempts": 2, "reads": 1}
    assert engine._defense_read_counts["home"] == {"attempts": 0, "reads": 0}


def test_read_reduces_yards_and_can_be_ablation_disabled(monkeypatch):
    engine = make_engine()
    monkeypatch.setattr(random, "random", lambda: 0.0)
    assert engine._defense_read_yard_multiplier(PlayFamily.POWER) == pytest.approx(0.9)
    assert engine._defense_read_counts["away"]["attempts"] == 1
    monkeypatch.setitem(V2_ENGINE_CONFIG, "defensive_reads_enabled", False)
    assert engine._defense_read_yard_multiplier(PlayFamily.POWER) == 1.0
    assert engine._defense_read_counts["away"]["attempts"] == 1


def test_scheme_effect_can_be_ablation_disabled(monkeypatch):
    engine = make_engine("boot_raid", "lockdown")
    assert engine._defense_style_multiplier(PlayFamily.KICK_PASS) < 1.0
    monkeypatch.setitem(V2_ENGINE_CONFIG, "defense_scheme_effects_enabled", False)
    assert engine._defense_style_multiplier(PlayFamily.KICK_PASS) == 1.0


def test_explosive_defense_affects_breakaway_probability(monkeypatch):
    engine = make_engine("ground_pound", "lockdown")
    engine._defensive_fatigue_factor = lambda: 1.0
    # Keep base chance deterministic: speed is rescaled in the real engine,
    # and the same player/matchup is evaluated against two schemes.
    team = SimpleNamespace(avg_speed=92)
    monkeypatch.setattr(random, "random", lambda: 0.17)
    monkeypatch.setattr(random, "randint", lambda low, high: low)
    lock_yards = engine._breakaway_check(6, team, family=PlayFamily.POWER)
    engine.away_team.defense_style = "blitz_pack"
    engine.away_defense = DEFENSE_STYLES["blitz_pack"]
    blitz_yards = engine._breakaway_check(6, team, family=PlayFamily.POWER)
    assert lock_yards == 6
    assert blitz_yards > 6


def test_all_offenses_and_defenses_have_explicit_matchups():
    assert len(OFFENSE_STYLES) == 16
    assert len(DEFENSE_STYLES) == 8
    assert all(
        (offense, defense) in OFFENSE_VS_DEFENSE_MATCHUP
        for offense in OFFENSE_STYLES
        for defense in DEFENSE_STYLES
    )


def test_no_retired_suppression_fields_remain_in_defense_definitions():
    for scheme in DEFENSE_STYLES.values():
        assert "gap_breakdown_bonus" not in scheme
        assert "territory_kick" not in scheme["play_family_modifiers"]
        assert "territory_kick" not in scheme["gameplan_bias"]
